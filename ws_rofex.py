# ===========================
# Archivo: ws_rofex.py
# - Sin Telegram acá (el bot va en telegram_control.py)
# - Health (last_marketdata_at)
# - Broadcaster WebSocket
# - Actualiza quotes_cache
# - Guardado opcional en Supabase (si supabase_client está presente)
# ===========================
import json
import time
import asyncio
import threading
import os

import pyRofex
from quotes_cache import quotes_cache  # dict global: {symbol: {...}}

# --- Guardado opcional en Supabase ---
_GUARDAR_TICKS = True  # poné False si no querés persistir
_guardar_func = None
try:
    from supabase_client import guardar_en_supabase as _guardar_func
except Exception:
    _guardar_func = None
    print("[ws_rofex] supabase_client.guardar_en_supabase no disponible; no se guardarán ticks en DB.")

# -------- Health: último tick recibido --------
last_marketdata_at = 0  # epoch seconds

def get_last_marketdata_age_seconds() -> float:
    """Segundos desde el último tick recibido."""
    if not last_marketdata_at:
        return 1e9
    return time.time() - last_marketdata_at

# -------- Notificador neutro (solo log) --------
def _notify(text: str):
    print("[notify]", text)

# -------- Broadcaster WebSocket --------
class WebSocketBroadcaster:
    def __init__(self):
        self.active_clients = []
        self.queue = asyncio.Queue()
        self.loop = None
        # lanzamos consumidor en el loop actual
        asyncio.get_event_loop().create_task(self._consumer())

    async def connect(self, websocket):
        await websocket.accept()
        self.active_clients.append(websocket)
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        print(f"[ws] Cliente conectado. Total clientes: {len(self.active_clients)}")

    def disconnect(self, websocket):
        if websocket in self.active_clients:
            self.active_clients.remove(websocket)
            print(f"[ws] Cliente desconectado. Total clientes: {len(self.active_clients)}")

    def enqueue(self, message):
        # Convierte dict a JSON string
        msg = json.dumps(message) if isinstance(message, dict) else str(message)
        loop = self.loop or asyncio.get_event_loop()
        loop.call_soon_threadsafe(self.queue.put_nowait, msg)

    async def _consumer(self):
        self.loop = asyncio.get_event_loop()
        while True:
            msg = await self.queue.get()
            # enviar a todos los clientes conectados
            for ws in self.active_clients[:]:
                try:
                    await ws.send_text(msg)
                except Exception as e:
                    print("[ws] Error enviando a cliente:", e)
                    self.disconnect(ws)

broadcaster = WebSocketBroadcaster()

# -------- Manager de market data --------
class MarketDataManager:
    def __init__(self):
        self.thread = None
        self._stop_event = threading.Event()
        self.running = False

    def is_running(self):
        return self.running and self.thread is not None and self.thread.is_alive()

    def start(self, instrumentos, user, password, account):
        if self.is_running():
            print("[ws_rofex] Ya hay una suscripción corriendo.")
            return
        self._stop_event.clear()
        self.thread = threading.Thread(
            target=self._run,
            args=(instrumentos, user, password, account),
            daemon=True
        )
        self.thread.start()
        self.running = True
        _notify("▶️ Servicio iniciado")

    def stop(self):
        if not self.is_running():
            self.running = False
            return
        self._stop_event.set()
        self.running = False
        print("[ws_rofex] Solicitud de detener la suscripción enviada.")
        _notify("⏹️ Servicio detenido")

    def _run(self, instrumentos, user, password, account):
        # Handlers de pyRofex
        def market_data_handler(message):
            # Normalizar a dict
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except Exception:
                    print("[ws_rofex] No se pudo decodificar el mensaje:", message)
                    return
            if not isinstance(message, dict):
                print("[ws_rofex] 🔴 Mensaje no es dict tras decodificar:", type(message))
                return

            try:
                symbol = message["instrumentId"]["symbol"]
                md = message.get("marketData", {})

                # BI puede ser lista o dict
                bi = md.get("BI")
                if isinstance(bi, list) and bi:
                    bid_price = bi[0].get("price")
                    bid_size  = bi[0].get("size")
                elif isinstance(bi, dict):
                    bid_price = bi.get("price")
                    bid_size  = bi.get("size")
                else:
                    bid_price = bid_size = None

                # OF puede ser lista o dict
                of = md.get("OF")
                if isinstance(of, list) and of:
                    offer_price = of[0].get("price")
                    offer_size  = of[0].get("size")
                elif isinstance(of, dict):
                    offer_price = of.get("price")
                    offer_size  = of.get("size")
                else:
                    offer_price = offer_size = None

                # LA último precio operado
                la = md.get("LA") or {}
                last_price = la.get("price")
                last_size  = la.get("size")

                # Actualizar cache
                quotes_cache[symbol] = {
                    "bid": bid_price,
                    "bid_size": bid_size,
                    "offer": offer_price,
                    "offer_size": offer_size,
                    "last": last_price,
                    "last_size": last_size,
                    "timestamp": message.get("timestamp"),
                }

                # Health
                global last_marketdata_at
                last_marketdata_at = time.time()

                # Log útil
                print(f"[ws_rofex] tick {symbol} bid={bid_price} ofr={offer_price} last={last_price}")

                # Guardado opcional en DB
                if _GUARDAR_TICKS and _guardar_func is not None:
                    try:
                        _guardar_func({
                            "symbol": symbol,
                            "timestamp": message.get("timestamp"),
                            "bid_price": bid_price,
                            "bid_size": bid_size,
                            "offer_price": offer_price,
                            "offer_size": offer_size,
                            "last_price": last_price,
                            "last_size": last_size,
                            "raw": message
                        })
                    except Exception as e:
                        print("[ws_rofex] [supabase] error guardando:", e)

            except Exception as e:
                print("[ws_rofex] Error actualizando quotes_cache:", e)

            # Broadcast a clientes WS
            if broadcaster.active_clients:
                print(f"[ws_rofex] broadcasting -> {len(broadcaster.active_clients)} cliente(s)")
            broadcaster.enqueue(message)

        def error_handler(message):
            print("[ws_rofex] Error Message Received:", message)

        def exception_handler(e):
            print("[ws_rofex] Exception Occurred:", e)
            _notify(f"🔴 Error en servicio: {str(e)}")

        # Elegir ambiente desde ENV (LIVE por defecto)
        env_name = os.getenv("ROFEX_ENV", "LIVE").upper().strip()
        env_map = {
            "LIVE": pyRofex.Environment.LIVE,
            "REMARKET": pyRofex.Environment.REMARKET,
        }
        environment = env_map.get(env_name, pyRofex.Environment.LIVE)
        print(f"[ws_rofex] Inicializando pyRofex en entorno: {env_name}")

        # Conexión
        pyRofex.initialize(
            user=user,
            password=password,
            account=account,
            environment=environment
        )
        pyRofex.init_websocket_connection(
            market_data_handler=market_data_handler,
            error_handler=error_handler,
            exception_handler=exception_handler
        )
        entries = [
            pyRofex.MarketDataEntry.BIDS,
            pyRofex.MarketDataEntry.OFFERS,
            pyRofex.MarketDataEntry.LAST
        ]
        pyRofex.market_data_subscription(
            tickers=instrumentos,
            entries=entries
        )
        print("[ws_rofex] Suscripción iniciada, esperando evento de parada...")

        # Espera hasta que pidan detener
        while not self._stop_event.is_set():
            time.sleep(1)

        print("[ws_rofex] Deteniendo suscripción y cerrando conexión websocket.")
        try:
            pyRofex.close_websocket_connection()
        except Exception:
            pass
