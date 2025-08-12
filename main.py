# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from typing import List
import os
import json
import threading
import time
from datetime import datetime, time as dtime

# Módulos propios
from ws_rofex import (
    MarketDataManager,
    broadcaster,
    get_last_marketdata_age_seconds,
)
from telegram_control import build_bot
from params_store import set_last_params, get_last_params
from quotes_cache import quotes_cache  # para /debug/cache

load_dotenv()

app = FastAPI()
manager = MarketDataManager()

# ---------------------------
# Configuración de horario
# ---------------------------
TZ = ZoneInfo(os.getenv("TZ", "America/Argentina/Buenos_Aires"))

def _parse_hhmm(s: str) -> dtime:
    hh, mm = s.split(":")
    return dtime(int(hh), int(mm), tzinfo=TZ)

ACTIVE_START = _parse_hhmm(os.getenv("ACTIVE_START", "10:30"))
ACTIVE_END   = _parse_hhmm(os.getenv("ACTIVE_END", "17:00"))

def _now_tz():
    return datetime.now(TZ)

def _within_window(now: datetime) -> bool:
    st = now.replace(hour=ACTIVE_START.hour, minute=ACTIVE_START.minute, second=0, microsecond=0)
    en = now.replace(hour=ACTIVE_END.hour, minute=ACTIVE_END.minute, second=0, microsecond=0)
    return st <= now <= en

# ---------------------------
# Modelos REST
# ---------------------------
class RequestBody(BaseModel):
    instrumentos: List[str]
    user: str
    password: str
    account: str

# ---------------------------
# Endpoints REST (start/stop/estado)
# ---------------------------
@app.post("/cotizaciones/iniciar")
async def iniciar(data: RequestBody):
    if manager.is_running():
        return {"status": "Ya hay una suscripción activa"}
    # Guardamos los últimos parámetros para reinicios posteriores (bot/guardián)
    set_last_params(data.model_dump())
    manager.start(data.instrumentos, data.user, data.password, data.account)
    return {"status": "Suscripción iniciada (solo por REST). Bot y guardián usarán estos mismos parámetros para reiniciar."}

@app.post("/cotizaciones/parar")
async def parar():
    if manager.is_running():
        manager.stop()
        return {"status": "Suscripción detenida"}
    return {"status": "No hay suscripción activa"}

@app.get("/cotizaciones/estado")
async def estado():
    return {"estado": "iniciada" if manager.is_running() else "parada"}

# ---------------------------
# Endpoints de observabilidad
# ---------------------------
@app.get("/health")
async def health():
    """Edad del último tick y estado del manager."""
    return {
        "last_tick_age_s": int(get_last_marketdata_age_seconds()),
        "running": manager.is_running(),
        "active_window": {
            "start": ACTIVE_START.strftime("%H:%M"),
            "end": ACTIVE_END.strftime("%H:%M"),
            "tz": str(TZ),
        },
    }

@app.get("/debug/cache")
async def debug_cache():
    """Lista los símbolos presentes en cache (primeros 50)."""
    return {"symbols": list(quotes_cache.keys())[:50]}

# ---------------------------
# WebSocket: broadcast de ticks
# ---------------------------
@app.websocket("/ws-cotizaciones")
async def ws_cotizaciones(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            # Ignoramos mensajes del cliente (solo push server->cliente)
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)

# ---------------------------
# Telegram bot (solo reinicia; no inicia)
# ---------------------------
telegram_notify = build_bot(manager, get_last_marketdata_age_seconds)

def notify(text: str):
    # build_bot devuelve un callable tipo notify; si no, usamos print
    if callable(telegram_notify):
        try:
            telegram_notify(text)
        except Exception as e:
            print("[notify] error:", e, "|", text)
    else:
        print("[notify]", text)

# ---------------------------
# Guardián (solo reinicia; NO inicia)
# ---------------------------
def guardian_loop():
    print("[guardian] iniciado. Ventana activa:",
          ACTIVE_START.strftime("%H:%M"), "->", ACTIVE_END.strftime("%H:%M"),
          "TZ:", TZ)
    alerted_down = False
    while True:
        try:
            now = _now_tz()
            in_window = _within_window(now)

            if in_window:
                if manager.is_running():
                    # Health: si pasan >120s sin ticks => reiniciar con últimos params REST
                    age = get_last_marketdata_age_seconds()
                    if age > 120 and not alerted_down:
                        alerted_down = True
                        notify(f"🔴 Sin ticks hace {int(age)}s. Reiniciando feed con los últimos parámetros REST…")
                        try:
                            params = get_last_params()
                            if not params:
                                notify("⚠️ No hay parámetros previos (aún no se inició por REST). No se puede reiniciar.")
                            else:
                                manager.stop()
                                time.sleep(2)
                                manager.start(params["instrumentos"], params["user"], params["password"], params["account"])
                                notify("✅ Feed reiniciado.")
                        except Exception as e:
                            notify(f"❌ Falló reinicio: {e}")
                    if age <= 120:
                        alerted_down = False
                # Si NO está corriendo, NO auto-iniciamos (respeta “solo por REST”)
            else:
                if manager.is_running():
                    manager.stop()
                    notify(f"⏹️ Servicio detenido fuera de ventana ({ACTIVE_START.strftime('%H:%M')}–{ACTIVE_END.strftime('%H:%M')}).")
                    alerted_down = False

        except Exception as e:
            print("[guardian] error:", e)

        time.sleep(15)

# Lanzar guardián en background al levantar la app
threading.Thread(target=guardian_loop, daemon=True).start()

# >>>>>>>>>>>>>>>>>  ACTIVAR WORKER DE RATIOS  <<<<<<<<<<<<<<<<<
from ratios_worker import periodic_ratios_job
threading.Thread(target=periodic_ratios_job, daemon=True).start()
