from fastapi import FastAPI, Body, WebSocket, WebSocketDisconnect, HTTPException, status, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import ws_rofex
from ratios_worker import start as start_worker, stop as stop_worker, set_session as set_worker_session
import telegram_control as tg
from pydantic import BaseModel
from typing import List
import threading
import time
import os, json
import requests
import asyncio
from typing import Set, Optional
try:
	from dotenv import load_dotenv
	load_dotenv()
except ImportError:
	pass

from supabase_client import get_active_pairs
import uuid


def _generate_ratio_operation_id(pair, instrument_to_sell):
    """
    Genera un operation_id con formato: PAR1-PAR2_aleatorio
    Ejemplo: TX26-TX28_a1b2c3d4
    """
    try:
        # Determinar los instrumentos del par
        if isinstance(pair, list):
            # Nuevo formato: array de instrumentos
            instruments = [inst.strip() for inst in pair]
            instrument_to_buy = None
            for inst in instruments:
                if inst != instrument_to_sell:
                    instrument_to_buy = inst
                    break
        else:
            # Formato legacy: string
            pair_parts = pair.split('-')
            if len(pair_parts) < 2:
                # Fallback si no se puede parsear
                return f"RATIO_{uuid.uuid4().hex[:8]}"
            
            sell_inst = instrument_to_sell.strip()
            remaining = pair.replace(sell_inst, '', 1).strip().strip('-').strip()
            instrument_to_buy = remaining
        
        if not instrument_to_buy:
            # Fallback si no se puede determinar el instrumento a comprar
            return f"RATIO_{uuid.uuid4().hex[:8]}"
        
        # Extraer símbolos cortos (ej: TX26, TX28)
        sell_symbol = _extract_symbol_short(instrument_to_sell)
        buy_symbol = _extract_symbol_short(instrument_to_buy)
        
        # Generar número aleatorio de 8 caracteres
        random_part = uuid.uuid4().hex[:8]
        
        # Formato: SELL-BUY_aleatorio
        return f"{sell_symbol}-{buy_symbol}_{random_part}"
        
    except Exception as e:
        print(f"[main] Error generando operation_id: {e}")
        # Fallback en caso de error
        return f"RATIO_{uuid.uuid4().hex[:8]}"


def _extract_symbol_short(instrument_name):
    """
    Extrae el símbolo corto del nombre del instrumento.
    Ejemplo: "MERV - XMEV - TX26 - 24hs" -> "TX26"
    """
    try:
        # Buscar patrones como TX26, TX28, etc.
        import re
        match = re.search(r'([A-Z]{2}\d{2})', instrument_name)
        if match:
            return match.group(1)
        
        # Fallback: usar las primeras letras/números
        parts = instrument_name.split()
        for part in parts:
            if len(part) >= 3 and any(c.isalpha() for c in part) and any(c.isdigit() for c in part):
                return part
        
        # Último fallback: usar las primeras 4 letras
        return instrument_name.replace(' ', '')[:4].upper()
        
    except Exception:
        return "UNKNOWN"

# Lifespan handler para reemplazar @app.on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[main] startup")
    # Capturar event loop para envíos desde otros hilos
    try:
        global _event_loop
        _event_loop = asyncio.get_event_loop()
        print(f"[startup] Event loop capturado: {_event_loop}")
    except Exception as e:
        print(f"[startup] No se pudo capturar event loop: {e}")
        _event_loop = None
    
    # Habilitar el bot de Telegram solo si TELEGRAM_POLLING=1 (por defecto 1 local, 0 en Render)
    if os.getenv("TELEGRAM_POLLING", "1") == "1":
        try:
            import importlib
            import telegram_control as tg_local
            tg_local = importlib.reload(tg_local)
            print(f"[main] telegram_control file: {getattr(tg_local, '__file__', None)}")
            tg_local.ensure_started(
                start_callback=lambda p: iniciar(p),
                stop_callback=lambda: detener(),
                restart_callback=lambda: reiniciar(),
                status_callback=lambda: _get_service_status()
            )
        except Exception as e:
            print(f"[main] error ensure_started: {e}")
    else:
        print("[main] Telegram polling deshabilitado por TELEGRAM_POLLING!=1")
    
    # Iniciar worker de refresh de dashboard (si está disponible)
    try:
        start_refresh_worker()
    except Exception as e:
        print(f"[main] No se pudo iniciar dashboard_refresh worker: {e}")
    
    # Limpiar workers del dashboard al iniciar
    try:
        _stop_dashboard_broadcast_worker()
    except Exception as e:
        print(f"[startup] Error limpiando dashboard worker: {e}")
    
    # No iniciar worker de ratios automáticamente, solo cuando se solicite
    print("[main] Servicio listo. Use /start para iniciar.")
    # Iniciar "dashboard" por defecto para latidos
    try:
        _dashboard_start()
    except Exception as e:
        print(f"[main] Error iniciando dashboard: {e}")
    
    yield
    
    # Shutdown
    print("[main] shutdown iniciado")
    
    # Detener worker del dashboard
    try:
        _stop_dashboard_broadcast_worker()
    except Exception as e:
        print(f"[shutdown] Error deteniendo dashboard worker: {e}")
    
    # Limpiar conexiones WebSocket
    try:
        with _websocket_lock:
            _websocket_connections.clear()
        with _dashboard_lock:
            _dashboard_subscribers.clear()
    except Exception as e:
        print(f"[shutdown] Error limpiando conexiones: {e}")
    
    print("[main] shutdown completado")

app = FastAPI(title="Cotiza API", version="1.0.0", lifespan=lifespan)

# Configurar CORS para permitir conexiones WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------- Dashboard ratios API ----------------------------
try:
    from dashboard_ratios_api import router as dashboard_router, start_refresh_worker
    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
except Exception as e:
    print(f"[main] No se pudo incluir dashboard_ratios_api: {e}")

# ---------------------------- Dashboard WebSocket ----------------------------
try:
    from basic_websocket import websocket_endpoint
    
    @app.websocket("/ws/dashboard")
    async def websocket_route(websocket: WebSocket):
        await websocket_endpoint(websocket)
        
except Exception as e:
    print(f"[main] No se pudo incluir basic_websocket: {e}")

# ---------------------------- Dashboard HTML ----------------------------
@app.get("/", response_class=RedirectResponse)
def root_redirect():
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    """Sirve el dashboard estático si existe, si no un mensaje básico."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_path = os.path.join(base_dir, "dashboard.html")
        if os.path.exists(dash_path):
            return FileResponse(dash_path, media_type="text/html")
    except Exception:
        pass
    # Fallback mínimo
    return HTMLResponse("""
    <!doctype html>
    <html lang="es"><head><meta charset="utf-8"><title>Dashboard</title></head>
    <body style="font-family: system-ui; padding: 16px;">
      <h1>Dashboard</h1>
      <p>No se encontró <code>dashboard.html</code>. Endpoints útiles:</p>
      <ul>
        <li><a href="/cotizaciones/health">/cotizaciones/health</a></li>
        <li><a href="/cotizaciones/status">/cotizaciones/status</a></li>
      </ul>
    </body></html>
    """)

@app.get("/ws-test", response_class=HTMLResponse)
def websocket_test_page():
    """Sirve la página de prueba del WebSocket."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        test_file = os.path.join(base_dir, "websocket_test.html")
        
        if os.path.exists(test_file):
            return FileResponse(test_file, media_type="text/html")
        else:
            return HTMLResponse(content="Archivo websocket_test.html no encontrado.", status_code=404)
    except Exception as e:
        return HTMLResponse(content=f"Error: {e}", status_code=500)

# ---------------------------- Dashboard control endpoints ----------------------------
@app.post("/dashboard/start")
def dashboard_start():
    try:
        return _dashboard_start()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/dashboard/stop")
def dashboard_stop():
    try:
        return _dashboard_stop()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/dashboard/status")
def dashboard_status():
    try:
        return _dashboard_status()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Estado global del servicio
_service_status = {
    "started": False,
    "started_at": None,
    "user": None,
    "account": None,
    "instruments": [],
    "worker_running": False,
    "ws_connected": False
}
_status_lock = threading.Lock()

# ---------------------------- Dashboard control (light worker) ----------------------------
_dashboard_worker_thread: threading.Thread | None = None
_dashboard_worker_stop = threading.Event()
_dashboard_last_beat: float | None = None

def _dashboard_worker_loop(interval_seconds: float = 2.0):
    global _dashboard_last_beat
    while not _dashboard_worker_stop.is_set():
        _dashboard_last_beat = time.time()
        _dashboard_worker_stop.wait(interval_seconds)

def _dashboard_start():
    global _dashboard_worker_thread
    if _dashboard_worker_thread and _dashboard_worker_thread.is_alive():
        return {"status": "ok", "message": "Dashboard ya estaba activo"}
    _dashboard_worker_stop.clear()
    _dashboard_worker_thread = threading.Thread(target=_dashboard_worker_loop, daemon=True)
    _dashboard_worker_thread.start()
    return {"status": "ok", "message": "Dashboard iniciado"}

def _dashboard_stop():
    global _dashboard_worker_thread
    _dashboard_worker_stop.set()
    if _dashboard_worker_thread and _dashboard_worker_thread.is_alive():
        try:
            _dashboard_worker_thread.join(timeout=2)
        except Exception:
            pass
    _dashboard_worker_thread = None
    return {"status": "ok", "message": "Dashboard detenido"}

def _dashboard_status():
    running = _dashboard_worker_thread is not None and _dashboard_worker_thread.is_alive()
    return {
        "running": running,
        "last_beat": _dashboard_last_beat,
        "uptime_seconds": (time.time() - (_dashboard_last_beat or time.time())) if running and _dashboard_last_beat else None,
    }

# ---------------------------- Order tracing (in-memory) ----------------------------
_order_logs: list[dict] = []
_order_logs_lock = threading.Lock()

def _append_order_log(entry: dict):
    try:
        entry["ts"] = time.time()
        with _order_logs_lock:
            _order_logs.append(entry)
            # Limitar tamaño para no crecer indefinidamente
            if len(_order_logs) > 500:
                del _order_logs[: len(_order_logs) - 500]
    except Exception:
        pass

def _update_status(**kwargs):
    """Actualiza el estado del servicio de forma thread-safe"""
    global _service_status
    with _status_lock:
        _service_status.update(kwargs)

def _get_status():
    """Obtiene el estado actual del servicio"""
    with _status_lock:
        return _service_status.copy()

def _get_env_creds():
	user = os.getenv("ROFEX_USERNAME")
	password = os.getenv("ROFEX_PASSWORD")
	account = os.getenv("ROFEX_ACCOUNT_NUMBER")
	return user, password, account

def _instruments_from_pairs(pairs) -> list[str]:
	syms: Set[str] = set()
	for p in pairs or []:
		b = p.get("base_symbol")
		q = p.get("quote_symbol")
		if isinstance(b, str) and b.strip():
			syms.add(b.strip())
		if isinstance(q, str) and q.strip():
			syms.add(q.strip())
	return sorted(syms)

class IniciarRequest(BaseModel):
    user: str
    password: str
    account: str
    instrumentos: List[str]

class OrderSubscribeRequest(BaseModel):
    account: str

class SendOrderRequest(BaseModel):
    symbol: str
    side: str  # BUY/SELL
    size: float
    price: float | None = None
    order_type: str = "LIMIT"  # LIMIT/MARKET
    tif: str = "DAY"           # DAY/IOC/FOK (si aplica)
    market: str | None = None
    client_order_id: str | None = None  # ID único del cliente para tracking

# Startup y shutdown manejados por lifespan handler

@app.post("/cotizaciones/iniciar")
def iniciar(req: IniciarRequest):
    try:
        # Iniciar WebSocket Rofex
        ws_result = ws_rofex.manager.start(
            user=req.user,
            password=req.password,
            account=req.account,
            instrumentos=req.instrumentos,
            force_ws=True
        )
        
        if ws_result.get("status") == "started":
            # Iniciar worker solo si WebSocket se conectó exitosamente
            start_worker()
            set_worker_session(user_id=req.user)
            
            # Actualizar estado del servicio
            _update_status(
                started=True,
                started_at=time.time(),
                user=req.user,
                account=req.account,
                instruments=req.instrumentos,
                worker_running=True,
                ws_connected=True
            )
            
            print(f"[main] Servicio iniciado para usuario {req.user}")
            return {"status": "success", "message": "Servicio iniciado", "details": ws_result}
        else:
            return {"status": "error", "message": "No se pudo iniciar WebSocket", "details": ws_result}
            
    except Exception as e:
        print(f"[main] Error al iniciar: {e}")
        return {"status": "error", "message": f"Error al iniciar: {str(e)}"}

@app.post("/cotizaciones/detener")
def detener():
    try:
        # Detener worker
        stop_worker()
        
        # Detener WebSocket
        ws_result = ws_rofex.manager.stop()
        
        # Actualizar estado del servicio
        _update_status(
            started=False,
            started_at=None,
            user=None,
            account=None,
            instruments=[],
            worker_running=False,
            ws_connected=False
        )
        
        print("[main] Servicio detenido")
        return {"status": "success", "message": "Servicio detenido", "details": ws_result}
        
    except Exception as e:
        print(f"[main] Error al detener: {e}")
        return {"status": "error", "message": f"Error al detener: {str(e)}"}

@app.post("/cotizaciones/reiniciar")
def reiniciar():
    try:
        # Detener primero
        detener()
        
        # Esperar un momento
        time.sleep(2)
        
        # Usar los últimos parámetros guardados
        from params_store import get_last_params
        last_params = get_last_params()
        
        if last_params:
            try:
                # Crear request con los parámetros guardados
                req = IniciarRequest(**last_params)
                return iniciar(req)
            except Exception as e:
                return {"status": "error", "message": f"Error al reiniciar: {str(e)}"}
        else:
            return {"status": "error", "message": "No hay parámetros previos para reiniciar"}
            
    except Exception as e:
        print(f"[main] Error al reiniciar: {e}")
        return {"status": "error", "message": f"Error al reiniciar: {str(e)}"}

@app.post("/cotizaciones/orders/subscribe")
def orders_subscribe(req: OrderSubscribeRequest):
    try:
        _append_order_log({"endpoint": "subscribe", "request": req.model_dump()})
        res = ws_rofex.manager.subscribe_order_reports(account=req.account)
        _append_order_log({"endpoint": "subscribe", "response": res})
        return res
    except Exception as e:
        _append_order_log({"endpoint": "subscribe", "error": str(e)})
        return {"status": "error", "message": str(e)}

@app.post("/cotizaciones/orders/send")
def orders_send(req: SendOrderRequest):
    try:
        _append_order_log({"endpoint": "send", "request": req.model_dump()})
        res = ws_rofex.manager.send_order(
            symbol=req.symbol,
            side=req.side,
            size=req.size,
            price=req.price,
            order_type=req.order_type,
            tif=req.tif,
            market=req.market,
            client_order_id=req.client_order_id,
        )
        _append_order_log({"endpoint": "send", "response": res})
        return res
    except Exception as e:
        _append_order_log({"endpoint": "send", "error": str(e)})
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/orders/last_report")
def orders_last_report():
    try:
        rep = ws_rofex.manager.last_order_report()
        res = {"status": "ok", "report": rep}
        _append_order_log({"endpoint": "last_report", "response": res})
        return res
    except Exception as e:
        _append_order_log({"endpoint": "last_report", "error": str(e)})
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/orders/logs")
def orders_logs(limit: int = 100):
    try:
        with _order_logs_lock:
            data = _order_logs[-limit:]
        return {"status": "ok", "count": len(data), "logs": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/status")
def estado():
    try:
        # Obtener estado del WebSocket
        ws_status = ws_rofex.manager.status()
        
        # Obtener estado del worker
        from ratios_worker import _worker_thread
        worker_status = "running" if _worker_thread and _worker_thread.is_alive() else "stopped"
        
        # Combinar estados
        status = _get_status()
        status.update({
            "worker_status": worker_status,
            "ws_details": ws_status,
            "uptime": time.time() - status["started_at"] if status["started_at"] else None
        })
        
        # Devolver diccionario simple para el bot de Telegram
        return status
        
    except Exception as e:
        print(f"[main] Error al obtener estado: {e}")
        return {"status": "error", "message": f"Error al obtener estado: {str(e)}"}

@app.get("/cotizaciones/health")
def health():
    """Endpoint de salud simple para verificar que la API está funcionando"""
    return {"status": "healthy", "timestamp": time.time()}


# Shutdown manejado por lifespan handler


@app.get("/health/detailed")
def detailed_health():
    """Endpoint de salud detallado con información del sistema."""
    try:
        with _websocket_lock:
            ws_count = len(_websocket_connections)
        with _dashboard_lock:
            dashboard_subs = len(_dashboard_subscribers)
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "websocket_connections": ws_count,
            "dashboard_subscribers": dashboard_subs,
            "dashboard_worker_running": _dashboard_worker_thread and _dashboard_worker_thread.is_alive(),
            "event_loop_available": _event_loop is not None and not _event_loop.is_closed()
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": time.time()}


# WebSocket connections
_websocket_connections = []
_websocket_lock = threading.Lock()
_event_loop: Optional[asyncio.AbstractEventLoop] = None

# Límites de seguridad para conexiones
MAX_WEBSOCKET_CONNECTIONS = 100  # Máximo 100 conexiones WebSocket
MAX_DASHBOARD_SUBSCRIBERS = 50   # Máximo 50 suscriptores del dashboard

# Dashboard subscribers
_dashboard_subscribers = []
_dashboard_lock = threading.Lock()
_last_dashboard_data = None
_last_dashboard_update = None
_dashboard_worker_thread = None
_dashboard_worker_stop = threading.Event()


async def _broadcast_dashboard_data():
    """Envía datos del dashboard a todos los suscriptores."""
    global _last_dashboard_data, _last_dashboard_update
    
    try:
        from supabase_client import supabase
        start_ts = time.time()
        resp = supabase.table("ratios_dashboard_view").select("*").execute()
        data_rows = resp.data or []
        elapsed_ms = int((time.time() - start_ts) * 1000)
        
        dashboard_payload = {
            "type": "dashboard_data",
            "status": "success",
            "method": "materialized_view_websocket",
            "count": len(data_rows),
            "data": data_rows,
            "query_time_ms": elapsed_ms,
            "timestamp": time.time()
        }
        
        # Guardar datos para nuevos suscriptores
        _last_dashboard_data = dashboard_payload
        _last_dashboard_update = time.time()
        
        # Enviar a todos los suscriptores activos
        with _dashboard_lock:
            active_subscribers = []
            for ws in _dashboard_subscribers:
                try:
                    await ws.send_text(json.dumps(dashboard_payload))
                    active_subscribers.append(ws)
                except Exception:
                    # Conexión cerrada, remover
                    pass
            _dashboard_subscribers[:] = active_subscribers
            
        print(f"[dashboard] Datos enviados a {len(active_subscribers)} suscriptores")
        
    except Exception as e:
        error_payload = {
            "type": "dashboard_error",
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }
        
        with _dashboard_lock:
            active_subscribers = []
            for ws in _dashboard_subscribers:
                try:
                    await ws.send_text(json.dumps(error_payload))
                    active_subscribers.append(ws)
                except Exception:
                    pass
            _dashboard_subscribers[:] = active_subscribers


def _start_dashboard_broadcast_worker():
    """Inicia el worker que envía datos del dashboard cada 10 segundos."""
    global _dashboard_worker_thread
    
    # Evitar múltiples workers
    if _dashboard_worker_thread and _dashboard_worker_thread.is_alive():
        print("[dashboard] Worker ya está corriendo")
        return
    
    def worker():
        print("[dashboard] Worker iniciado")
        while not _dashboard_worker_stop.is_set():
            try:
                if _dashboard_subscribers:  # Solo si hay suscriptores
                    # Usar el event loop global si está disponible
                    if _event_loop and not _event_loop.is_closed():
                        asyncio.run_coroutine_threadsafe(_broadcast_dashboard_data(), _event_loop)
                    else:
                        # Crear un nuevo loop solo si es necesario
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(_broadcast_dashboard_data())
                            loop.close()
                        except Exception as e:
                            print(f"[dashboard] Error creando loop: {e}")
            except Exception as e:
                print(f"[dashboard] Error en worker: {e}")
            
            # Usar wait con timeout para poder salir limpiamente
            if _dashboard_worker_stop.wait(10):  # Esperar 10 segundos o hasta que se detenga
                break
    
    _dashboard_worker_stop.clear()
    _dashboard_worker_thread = threading.Thread(target=worker, daemon=True)
    _dashboard_worker_thread.start()
    print("[dashboard] Worker de broadcast iniciado (cada 10 segundos)")


def _stop_dashboard_broadcast_worker():
    """Detiene el worker del dashboard."""
    global _dashboard_worker_thread
    
    if _dashboard_worker_thread and _dashboard_worker_thread.is_alive():
        print("[dashboard] Deteniendo worker...")
        _dashboard_worker_stop.set()
        _dashboard_worker_thread.join(timeout=15)  # Esperar máximo 15 segundos
        
        if _dashboard_worker_thread.is_alive():
            print("[dashboard] Worker no terminó en 15s, forzando...")
        else:
            print("[dashboard] Worker detenido correctamente")
        
        _dashboard_worker_thread = None


def _subscribe_to_dashboard(websocket):
    """Suscribe un WebSocket a los datos del dashboard."""
    with _dashboard_lock:
        if websocket not in _dashboard_subscribers:
            _dashboard_subscribers.append(websocket)
            print(f"[dashboard] Nuevo suscriptor. Total: {len(_dashboard_subscribers)}")
            
            # Si es el primer suscriptor, iniciar el worker
            if len(_dashboard_subscribers) == 1:
                _start_dashboard_broadcast_worker()
            
            # Enviar datos actuales inmediatamente si están disponibles
            if _last_dashboard_data:
                try:
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_text(json.dumps(_last_dashboard_data)), 
                        _event_loop or asyncio.get_event_loop()
                    )
                except Exception:
                    pass


def _unsubscribe_from_dashboard(websocket):
    """Desuscribe un WebSocket de los datos del dashboard."""
    with _dashboard_lock:
        if websocket in _dashboard_subscribers:
            _dashboard_subscribers.remove(websocket)
            print(f"[dashboard] Suscriptor removido. Total: {len(_dashboard_subscribers)}")
            
            # Si no hay más suscriptores, detener el worker
            if len(_dashboard_subscribers) == 0:
                _stop_dashboard_broadcast_worker()

@app.websocket("/ws/cotizaciones")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para cotizaciones en tiempo real"""
    try:
        # Aceptar la conexión
        await websocket.accept()
        print(f"[websocket] Nueva conexión desde {websocket.client.host}:{websocket.client.port}")
        
        # Verificar límite de conexiones antes de agregar
        with _websocket_lock:
            if len(_websocket_connections) >= MAX_WEBSOCKET_CONNECTIONS:
                await websocket.close(code=1013, reason="Too many connections")
                print(f"[websocket] Conexión rechazada: límite de {MAX_WEBSOCKET_CONNECTIONS} alcanzado")
                return
            
            _websocket_connections.append(websocket)
            print(f"[websocket] Conexiones activas: {len(_websocket_connections)}/{MAX_WEBSOCKET_CONNECTIONS}")
        
        # Enviar mensaje de bienvenida
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": "connected",
            "timestamp": time.time(),
            "message": "Conexión WebSocket establecida"
        }))
        
        # Mantener la conexión activa y escuchar mensajes
        try:
            # LÍMITE DE SEGURIDAD: máximo 10,000 mensajes por conexión
            max_messages_per_connection = 10000
            message_count = 0
            
            while message_count < max_messages_per_connection:
                try:
                    # Esperar mensajes del cliente con timeout
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=300)  # 5 minutos timeout
                    message_count += 1
                except asyncio.TimeoutError:
                    # Enviar ping para mantener conexión viva
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": time.time(),
                        "message": "Keep-alive ping"
                    }))
                    continue
                try:
                    message = json.loads(data)
                    print(f"[websocket] Mensaje recibido: {message}")
                    
                    # Normalizar comando (acepta 'type' o 'action')
                    _cmd = (message.get("action") or message.get("type") or "").lower()
                    
                    # Procesar mensaje según el tipo/comando
                    if _cmd == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": time.time()
                        }))
                    elif message.get("type") == "subscribe":
                        # Suscribir a cotizaciones específicas
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "instruments": message.get("instruments", []),
                            "timestamp": time.time()
                        }))
                    elif _cmd in ("get_status", "dashboard_status"):
                        # Estado básico del canal WS
                        with _websocket_lock:
                            conn_count = len(_websocket_connections)
                        await websocket.send_text(json.dumps({
                            "type": "status",
                            "active_connections": conn_count,
                            "timestamp": time.time()
                        }))
                    elif _cmd in ("get_data", "dashboard_get_data"):
                        # Devolver datos del dashboard desde la vista materializada
                        try:
                            from supabase_client import supabase
                            start_ts = time.time()
                            resp = supabase.table("ratios_dashboard_view").select("*").execute()
                            data_rows = resp.data or []
                            elapsed_ms = int((time.time() - start_ts) * 1000)
                            await websocket.send_text(json.dumps({
                                "status": "success",
                                "method": "materialized_view_websocket",
                                "count": len(data_rows),
                                "data": data_rows,
                                "query_time_ms": elapsed_ms,
                                "timestamp": time.time()
                            }))
                        except Exception as e:
                            await websocket.send_text(json.dumps({
                                "status": "error",
                                "error": str(e),
                                "timestamp": time.time()
                            }))
                    elif _cmd in ("dashboard_subscribe", "subscribe_dashboard"):
                        # Suscribirse a datos automáticos del dashboard
                        _subscribe_to_dashboard(websocket)
                        await websocket.send_text(json.dumps({
                            "type": "dashboard_subscribed",
                            "message": "Suscripción al dashboard activa - recibirás datos cada 10 segundos",
                            "timestamp": time.time()
                        }))
                    elif _cmd in ("dashboard_unsubscribe", "unsubscribe_dashboard"):
                        # Desuscribirse de los datos automáticos del dashboard
                        _unsubscribe_from_dashboard(websocket)
                        await websocket.send_text(json.dumps({
                            "type": "dashboard_unsubscribed",
                            "message": "Suscripción al dashboard desactivada",
                            "timestamp": time.time()
                        }))
                    elif message.get("type") == "orders_subscribe":
                        # Suscribir a order reports de una cuenta
                        account = message.get("account")
                        if not account:
                            await websocket.send_text(json.dumps({
                                "type": "error", "message": "missing account"
                            }))
                        else:
                            res = ws_rofex.manager.subscribe_order_reports(account=account)
                            await websocket.send_text(json.dumps({
                                "type": "orders_subscribed", "account": account, "result": res
                            }))
                    elif message.get("type") == "send_order":
                        # Envío de orden directa
                        payload = message.get("order") or {}
                        client_order_id = message.get("clOrdId") or payload.get("client_order_id")
                        try:
                            res = ws_rofex.manager.send_order(
                                symbol=payload.get("symbol"),
                                side=payload.get("side"),
                                size=payload.get("size"),
                                price=payload.get("price"),
                                order_type=payload.get("order_type", "LIMIT"),
                                tif=payload.get("tif", "DAY"),
                                market=payload.get("market"),
                                client_order_id=client_order_id,
                            )
                            
                            # Si hay error de conexión, intentar reconectar
                            if res.get("status") == "error" and res.get("message") == "connection_closed":
                                print(f"[websocket] Intentando reconectar ROFEX...")
                                reconnect_res = ws_rofex.manager.check_and_reconnect()
                                if reconnect_res.get("status") == "ok":
                                    # Reintentar la orden después de reconectar
                                    res = ws_rofex.manager.send_order(
                                        symbol=payload.get("symbol"),
                                        side=payload.get("side"),
                                        size=payload.get("size"),
                                        price=payload.get("price"),
                                        order_type=payload.get("order_type", "LIMIT"),
                                        tif=payload.get("tif", "DAY"),
                                        market=payload.get("market"),
                                        client_order_id=client_order_id,
                                    )
                                    res["reconnected"] = True
                            
                            await websocket.send_text(json.dumps({
                                "type": "order_ack",
                                "request": payload,
                                "result": res
                            }))
                        except Exception as e:
                            await websocket.send_text(json.dumps({
                                "type": "error", "message": f"send_order failed: {str(e)}"
                            }))
                    elif _cmd in ("start_ratio_operation", "ratio_operation"):
                        try:
                            from ratio_operations import ratio_manager
                            from ratio_operations_simple import simple_ratio_manager, RatioOperationRequest
                            from ratio_operations_real import real_ratio_manager
                            import uuid
                            required_params = ["pair", "instrument_to_sell", "nominales", "target_ratio", "condition", "client_id", "operation_id"]
                            missing_params = [p for p in required_params if p not in message]
                            if missing_params:
                                await websocket.send_text(json.dumps({
                                    "type": "ratio_operation_error",
                                    "error": f"Parámetros faltantes: {', '.join(missing_params)}",
                                    "timestamp": time.time()
                                }))
                                continue
                            # Usar operation_id proporcionado por el cliente
                            operation_id = message["operation_id"]
                            
                            # Obtener buy_qty (opcional, default 0.0)
                            buy_qty = float(message.get("buy_qty", 0.0))
                            
                            request = RatioOperationRequest(
                                pair=message["pair"],
                                instrument_to_sell=message["instrument_to_sell"],
                                nominales=float(message["nominales"]),
                                target_ratio=float(message["target_ratio"]),
                                condition=message["condition"],
                                client_id=message["client_id"],
                                operation_id=operation_id,
                                buy_qty=buy_qty
                            )
                            async def progress_callback(progress):
                                # Calcular nominales comprados sumando las cantidades de las órdenes de compra
                                nominales_comprados = sum(order.quantity for order in progress.buy_orders)
                                
                                await websocket.send_text(json.dumps({
                                    "type": "ratio_operation_progress",
                                    "operation_id": progress.operation_id,
                                    "status": progress.status.value,
                                    "current_step": progress.current_step.value,
                                    "progress_percentage": progress.progress_percentage,
                                    "current_ratio": progress.current_ratio,
                                    "target_ratio": progress.target_ratio,
                                    "condition_met": progress.condition_met,
                                    "average_sell_price": progress.average_sell_price,
                                    "average_buy_price": progress.average_buy_price,
                                    "total_sold_amount": progress.total_sold_amount,
                                    "total_bought_amount": progress.total_bought_amount,
                                    "sell_orders_count": len(progress.sell_orders),
                                    "buy_orders_count": len(progress.buy_orders),
                                    "nominales_objetivo": request.nominales,
                                    "nominales_ejecutados": progress.completed_nominales,
                                    "nominales_comprados": nominales_comprados,
                                    "buy_qty_solicitado": request.buy_qty,
                                    "buy_qty_usado": request.buy_qty if request.buy_qty > 0 and request.buy_qty <= request.nominales else 0,
                                    "messages": progress.messages[-10:],
                                    "error": progress.error,
                                    "timestamp": time.time()
                                }))
                            real_ratio_manager.register_callback(operation_id, progress_callback)
                            asyncio.create_task(real_ratio_manager.execute_ratio_operation_batch(request))
                            await websocket.send_text(json.dumps({
                                "type": "ratio_operation_started",
                                "operation_id": operation_id,
                                "message": f"Operación de ratio iniciada: {request.pair}",
                                "timestamp": time.time()
                            }))
                        except Exception as e:
                            await websocket.send_text(json.dumps({
                                "type": "ratio_operation_error",
                                "error": str(e),
                                "timestamp": time.time()
                            }))
                    elif _cmd in ("get_ratio_operation_status", "ratio_status"):
                        try:
                            from ratio_operations import ratio_manager
                            from ratio_operations_simple import simple_ratio_manager
                            from ratio_operations_real import real_ratio_manager
                            operation_id = message.get("operation_id")
                            if not operation_id:
                                await websocket.send_text(json.dumps({
                                    "type": "ratio_operation_error",
                                    "error": "operation_id requerido",
                                    "timestamp": time.time()
                                }))
                                continue
                            progress = real_ratio_manager.get_operation_status(operation_id)
                            if progress:
                                await websocket.send_text(json.dumps({
                                    "type": "ratio_operation_status",
                                    "operation_id": progress.operation_id,
                                    "status": progress.status.value,
                                    "current_step": progress.current_step.value,
                                    "progress_percentage": progress.progress_percentage,
                                    "current_ratio": progress.current_ratio,
                                    "target_ratio": progress.target_ratio,
                                    "condition_met": progress.condition_met,
                                    "average_sell_price": progress.average_sell_price,
                                    "average_buy_price": progress.average_buy_price,
                                    "total_sold_amount": progress.total_sold_amount,
                                    "total_bought_amount": progress.total_bought_amount,
                                    "sell_orders_count": len(progress.sell_orders),
                                    "buy_orders_count": len(progress.buy_orders),
                                    "messages": progress.messages[-20:],
                                    "error": progress.error,
                                    "start_time": progress.start_time,
                                    "last_update": progress.last_update,
                                    "timestamp": time.time()
                                }))
                            else:
                                await websocket.send_text(json.dumps({
                                    "type": "ratio_operation_error",
                                    "error": f"Operación {operation_id} no encontrada",
                                    "timestamp": time.time()
                                }))
                        except Exception as e:
                            await websocket.send_text(json.dumps({
                                "type": "ratio_operation_error",
                                "error": str(e),
                                "timestamp": time.time()
                            }))
                    elif _cmd in ("cancel_ratio_operation", "ratio_cancel"):
                        try:
                            from ratio_operations import ratio_manager
                            from ratio_operations_simple import simple_ratio_manager
                            operation_id = message.get("operation_id")
                            if not operation_id:
                                await websocket.send_text(json.dumps({
                                    "type": "ratio_operation_error",
                                    "error": "operation_id requerido",
                                    "timestamp": time.time()
                                }))
                                continue
                            cancelled = ratio_manager.cancel_operation(operation_id)
                            await websocket.send_text(json.dumps({
                                "type": "ratio_operation_cancelled" if cancelled else "ratio_operation_error",
                                "operation_id": operation_id,
                                "message": "Operación cancelada exitosamente" if cancelled else f"No se pudo cancelar la operación {operation_id}",
                                "timestamp": time.time()
                            }))
                        except Exception as e:
                            await websocket.send_text(json.dumps({
                                "type": "ratio_operation_error",
                                "error": str(e),
                                "timestamp": time.time()
                            }))
                    elif _cmd in ("list_ratio_operations", "ratio_list"):
                        try:
                            from ratio_operations import ratio_manager
                            from ratio_operations_simple import simple_ratio_manager
                            operations = ratio_manager.get_all_operations()
                            operations_data = []
                            for op in operations:
                                operations_data.append({
                                    "operation_id": op.operation_id,
                                    "status": op.status.value,
                                    "current_step": op.current_step.value,
                                    "progress_percentage": op.progress_percentage,
                                    "current_ratio": op.current_ratio,
                                    "target_ratio": op.target_ratio,
                                    "condition_met": op.condition_met,
                                    "start_time": op.start_time,
                                    "last_update": op.last_update,
                                    "error": op.error
                                })
                            await websocket.send_text(json.dumps({
                                "type": "ratio_operations_list",
                                "operations": operations_data,
                                "count": len(operations_data),
                                "timestamp": time.time()
                            }))
                        except Exception as e:
                            await websocket.send_text(json.dumps({
                                "type": "ratio_operation_error",
                                "error": str(e),
                                "timestamp": time.time()
                            }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Tipo de mensaje no reconocido",
                            "timestamp": time.time()
                        }))
                        
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "JSON inválido",
                        "timestamp": time.time()
                    }))
                    
            # Si llegamos aquí, se alcanzó el límite de mensajes
            if message_count >= max_messages_per_connection:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Límite de mensajes alcanzado ({max_messages_per_connection}). Reconectando...",
                    "timestamp": time.time()
                }))
                await websocket.close(code=1008, reason="Message limit exceeded")
                    
        except WebSocketDisconnect:
            print(f"[websocket] Cliente desconectado: {websocket.client.host}:{websocket.client.port}")
        except Exception as e:
            print(f"[websocket] Error en WebSocket: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error interno: {str(e)}",
                "timestamp": time.time()
            }))
            
    except Exception as e:
        print(f"[websocket] Error al aceptar conexión: {e}")
    finally:
        # Remover de la lista de conexiones activas
        with _websocket_lock:
            if websocket in _websocket_connections:
                _websocket_connections.remove(websocket)
        
        # Remover de suscriptores del dashboard
        _unsubscribe_from_dashboard(websocket)
        
        print(f"[websocket] Conexión cerrada: {websocket.client.host}:{websocket.client.port}")


def broadcast_to_websockets(message: dict):
    """Envía un mensaje a todos los clientes WebSocket conectados"""
    disconnected = []
    
    with _websocket_lock:
        for websocket in _websocket_connections:
            try:
                # Verificar si la conexión sigue activa
                if websocket.client_state.value == 1:  # WebSocketState.CONNECTED
                    try:
                        # Enviar desde cualquier hilo usando el loop principal
                        if _event_loop is not None:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send_text(json.dumps(message)), _event_loop
                            )
                        else:
                            # Fallback si no hay loop registrado
                            asyncio.create_task(websocket.send_text(json.dumps(message)))
                    except Exception as e:
                        print(f"[websocket] Error programando envío: {e}")
                        disconnected.append(websocket)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                print(f"[websocket] Error enviando mensaje: {e}")
                disconnected.append(websocket)
    
    # Limpiar conexiones desconectadas
    if disconnected:
        with _websocket_lock:
            for ws in disconnected:
                if ws in _websocket_connections:
                    _websocket_connections.remove(ws)
        print(f"[websocket] {len(disconnected)} conexiones desconectadas removidas")

# Registrar callback para difundir ticks provenientes de ws_rofex
def _tick_broadcast_callback(tick: dict):
    try:
        # Enviar a todos los clientes conectados
        broadcast_to_websockets(tick)
    except Exception as e:
        print(f"[websocket] error enviando tick: {e}")

try:
    ws_rofex.set_broadcast_callback(_tick_broadcast_callback)
except Exception as e:
    print(f"[main] No se pudo registrar broadcast_callback: {e}")


@app.get("/cotizaciones/websocket_status")
def websocket_status():
    """Obtiene el estado de las conexiones WebSocket"""
    with _websocket_lock:
        active_connections = len(_websocket_connections)
        connections_info = []
        
        for ws in _websocket_connections:
            try:
                connections_info.append({
                    "host": ws.client.host,
                    "port": ws.client.port,
                    "state": ws.client_state.value
                })
            except Exception:
                pass
    
    return {
        "active_connections": active_connections,
        "connections": connections_info,
        "timestamp": time.time()
    }

@app.get("/cotizaciones/telegram_diag")
def telegram_diag():
    try:
        import importlib
        import telegram_control as tg
        try:
            tg = importlib.reload(tg)
        except Exception:
            pass
        # evitar depender de atributos nuevos si el modulo no esta actualizado en runtime
        info = {
            "has_library": getattr(tg, "telebot", None) is not None,
            "has_token": bool(getattr(tg, "BOT_TOKEN", None)),
        }
        info["module_file"] = getattr(tg, "__file__", None)
        try:
            info.update(getattr(tg, "current_status")())
        except Exception:
            pass
        try:
            info["me"] = getattr(tg, "get_me")()
        except Exception:
            pass
        return info
    except Exception as e:
        return {"error": str(e)}

@app.post("/cotizaciones/telegram_restart")
def telegram_restart():
    try:
        import telegram_control as tg
        try:
            tg.shutdown()
        except Exception:
            pass
        tg.ensure_started(
            start_callback=lambda p: iniciar(p),
            stop_callback=lambda: detener(),
            restart_callback=lambda: reiniciar(),
            status_callback=lambda: estado(),
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/cotizaciones/telegram_sync_commands")
def telegram_sync_commands():
    try:
        import importlib
        import telegram_control as tg
        try:
            tg = importlib.reload(tg)
        except Exception:
            pass
        # Intento 1: usar la función del módulo si existe
        if hasattr(tg, "sync_commands"):
            return tg.sync_commands()
        # Intento 2: fallback directo a la API de Telegram
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            return {"status": "error", "message": "Falta TELEGRAM_TOKEN"}
        url = f"https://api.telegram.org/bot{token}/setMyCommands"
        commands = [
            {"command": "ping", "description": "Comprobar que estoy vivo"},
            {"command": "status", "description": "Ver estado del servicio"},
            {"command": "start", "description": "Iniciar servicio {json}"},
            {"command": "stop", "description": "Detener servicio"},
            {"command": "restart", "description": "Reiniciar servicio"},
            {"command": "help", "description": "Ayuda"}
        ]
        r = requests.post(url, json={"commands": commands})
        ok = r.status_code == 200 and r.json().get("ok") is True
        return {"status": "ok" if ok else "error", "http": r.status_code, "resp": r.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/cotizaciones/telegram_locks_status")
def telegram_locks_status():
    """Verifica el estado de todos los locks del bot"""
    try:
        import telegram_control as tg
        if hasattr(tg, "current_status"):
            return tg.current_status()
        else:
            return {"status": "error", "message": "Función no disponible"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/cotizaciones/telegram_check_other_bots")
def telegram_check_other_bots():
    """Verifica si hay otros bots ejecutándose en el sistema"""
    try:
        import telegram_control as tg
        if hasattr(tg, "check_other_bots"):
            return tg.check_other_bots()
        else:
            return {"status": "error", "message": "Función no disponible"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/cotizaciones/telegram_force_cleanup")
def telegram_force_cleanup():
    """Fuerza la limpieza de todos los locks obsoletos"""
    try:
        import telegram_control as tg
        if hasattr(tg, "force_cleanup_locks"):
            return tg.force_cleanup_locks()
        else:
            return {"status": "error", "message": "Función no disponible"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/cotizaciones/telegram_send_test")
def telegram_send_test(msg: str = "test desde API"):
    try:
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return {"status": "error", "message": "Faltan TELEGRAM_TOKEN/TELEGRAM_CHAT_ID"}
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": int(chat_id), "text": msg})
        ok = r.status_code == 200 and r.json().get("ok") is True
        return {"status": "ok" if ok else "error", "http": r.status_code, "resp": r.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/last_params")
def last_params():
	try:
		from params_store import get_last_params
		return get_last_params() or {}
	except Exception as e:
		return {"error": str(e)}

@app.post("/cotizaciones/reconnect_rofex")
def reconnect_rofex():
	"""Reconecta la conexión ROFEX si es necesario"""
	try:
		result = ws_rofex.manager.check_and_reconnect()
		return result
	except Exception as e:
		return {"status": "error", "message": f"Error reconectando: {str(e)}"}

@app.post("/cotizaciones/iniciar_auto")
def iniciar_auto():
	try:
		user, password, account = _get_env_creds()
		if not all([user, password, account]):
			return {"status": "error", "message": "Faltan ROFEX_USERNAME/ROFEX_PASSWORD/ROFEX_ACCOUNT_NUMBER en .env"}

		pairs = get_active_pairs()
		instrumentos = _instruments_from_pairs(pairs)

		# Fallback: si DB devuelve 0, usar INSTRUMENTS_JSON del .env (si está)
		if not instrumentos:
			try:
				instrumentos = json.loads(os.getenv("INSTRUMENTS_JSON", "[]"))
			except Exception:
				instrumentos = []

		if not instrumentos:
			return {"status": "error", "message": "No hay instrumentos (DB y .env vacíos)"}

		req = IniciarRequest(user=user, password=password, account=account, instrumentos=instrumentos)
		return iniciar(req)
	except Exception as e:
		return {"status": "error", "message": f"Error en iniciar_auto: {str(e)}"}