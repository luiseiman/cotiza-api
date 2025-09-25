from __future__ import annotations
import time
import threading
import json
from typing import Any, Dict, Iterable, Optional, Tuple

try:
    from quotes_cache import quotes_cache
except ImportError:
    quotes_cache = {}

try:
    from params_store import set_last_params
except ImportError:
    def set_last_params(params): pass

PRINT_PREFIX = "[ws_rofex]"

class SimpleBroadcaster:
    def __init__(self) -> None:
        self._subscribers = []
        self._lock = threading.Lock()

    async def subscribe(self):
        import asyncio
        q = asyncio.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    async def publish(self, message: Dict[str, Any]):
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(message)
            except Exception:
                pass

    def subscribers(self) -> int:
        with self._lock:
            return len(self._subscribers)


broadcaster = SimpleBroadcaster()

_guardar_tick = None
try:
    from supabase_client import guardar_en_supabase as _guardar_tick
except Exception:
    print(f"{PRINT_PREFIX} supabase_client.guardar_en_supabase no disponible; no se guardarán ticks en DB.")

# Callback opcional para difundir ticks a otros componentes (p.ej. WebSocket HTTP)
_broadcast_callback = None  # type: Optional[callable]

def set_broadcast_callback(callback):
    """Registra un callback que reciba un dict con el tick y lo difunda."""
    global _broadcast_callback
    _broadcast_callback = callback

def _first_price_and_size(levels: Any) -> Tuple[Optional[float], Optional[float]]:
    if not levels:
        return None, None
    if isinstance(levels, dict):
        price = levels.get("price") or levels.get("p")
        size = levels.get("size") or levels.get("s")
        try:
            return float(price) if price else None, float(size) if size else None
        except Exception:
            return None, None
    if isinstance(levels, list):
        first = levels[0]
        if isinstance(first, dict):
            price = first.get("price") or first.get("p")
            size = first.get("size") or first.get("s")
            try:
                return float(price) if price else None, float(size) if size else None
            except Exception:
                return None, None
    return None, None

def _extract_symbol(message: Dict[str, Any]) -> Optional[str]:
    inst = message.get("instrumentId")
    if isinstance(inst, dict) and "symbol" in inst:
        return inst["symbol"]
    return message.get("symbol")

def _extract_ts(message: Dict[str, Any]) -> int:
    for k in ("timestamp", "ts", "mdTimestamp", "time"):
        v = message.get(k)
        if isinstance(v, (int, float)):
            if v < 10_000_000_000:
                return int(v * 1000)
            return int(v)
    return int(time.time() * 1000)

def _extract_levels(message: Dict[str, Any]):
    md = message.get("marketData") or message.get("md") or message
    bids = md.get("BI") or md.get("bids") or md.get("bid")
    offs = md.get("OF") or md.get("offers") or md.get("ask") or md.get("offer")
    last = md.get("LA") or md.get("last")
    b_price, b_size = _first_price_and_size(bids)
    a_price, a_size = _first_price_and_size(offs)
    l_price, l_size = _first_price_and_size(last)
    return (b_price, b_size), (a_price, a_size), (l_price, l_size)

def _extract_closing_price(message: Dict[str, Any]) -> Optional[float]:
    """Intenta extraer el precio de cierre de la rueda anterior.
    Soporta varias claves posibles según la fuente del mensaje.
    """
    md = message.get("marketData") or message.get("md") or message
    for key in ("CL", "cl", "closingPrice", "previousClose", "prev_close"):
        v = md.get(key)
        try:
            if v is None:
                continue
            # Puede venir como dict {"price": x}
            if isinstance(v, dict):
                vp = v.get("price") or v.get("p")
                return float(vp) if vp is not None else None
            # O valor directo
            return float(v)
        except Exception:
            continue
    return None

def _extract_opening_price(message: Dict[str, Any]) -> Optional[float]:
    """Intenta extraer el precio de apertura de la rueda actual.
    Acepta claves comunes: OP/op/openPrice/open.
    """
    md = message.get("marketData") or message.get("md") or message
    for key in ("OP", "op", "openPrice", "open"):
        v = md.get(key)
        try:
            if v is None:
                continue
            if isinstance(v, dict):
                vp = v.get("price") or v.get("p")
                return float(vp) if vp is not None else None
            return float(v)
        except Exception:
            continue
    return None

class MarketDataManager:
    def __init__(self) -> None:
        self._pyrofex = None
        self._ws_open = False
        self._lock = threading.RLock()
        self.user: Optional[str] = None
        self._subscribed: set[str] = set()
        self.last_marketdata_at_ms: Optional[int] = None
        self._last_params: Optional[Dict[str, Any]] = None
        # Order reports buffer
        self._last_order_report: Optional[Dict[str, Any]] = None

    def start(
        self,
        *,
        user: str,
        password: str,
        account: str,
        instrumentos: Iterable[str],
        force_ws: bool = True,
    ):
        with self._lock:
            # Guardar parámetros para restart
            params = {
                "user": user,
                "password": password,
                "account": account,
                "instrumentos": list(instrumentos)
            }
            self._last_params = params
            set_last_params(params)
            
            try:
                import pyRofex as pr
                self._pyrofex = pr
                
                # Deshabilitar verificación SSL para macOS
                import ssl
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                ssl._create_default_https_context = ssl._create_unverified_context
                print(f"{PRINT_PREFIX} SSL verification disabled for macOS")
                
            except Exception as e:
                print(f"{PRINT_PREFIX} No se pudo importar pyRofex: {e}")
                return {"status": "error", "error": "pyRofex not available", "ws": "disabled"}

            self.user = user

            try:
                # Usar LIVE por defecto para trading real
                env = getattr(self._pyrofex.Environment, "LIVE")
                self._pyrofex.initialize(user=user, password=password, account=account, environment=env)
                print(f"{PRINT_PREFIX} pyRofex inicializado con ambiente LIVE")
                
            except Exception as e:
                print(f"{PRINT_PREFIX} Error inicializando pyRofex con LIVE: {e}")
                return {"status": "error", "error": str(e), "ws": "disabled"}

            def md_handler(msg: Dict[str, Any]):
                self._handle_md(msg)

            def error_handler(msg):
                print(f"{PRINT_PREFIX} Error Message Received: {msg}")

            def exception_handler(e):
                print(f"{PRINT_PREFIX} Exception Occurred: {e}")

            try:
                # Configurar contexto SSL para WebSocket
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Inicializar WebSocket siguiendo el ejemplo oficial con contexto SSL
                self._pyrofex.init_websocket_connection(
                    market_data_handler=md_handler,
                    order_report_handler=self._handle_or,
                    error_handler=error_handler,
                    exception_handler=exception_handler,
                    ssl_context=ssl_context
                )
                self._ws_open = True
                print(f"{PRINT_PREFIX} WebSocket connection initialized with SSL context")
                
                # Suscribirse a order reports primero (como en el ejemplo oficial)
                try:
                    self._pyrofex.order_report_subscription()
                    print(f"{PRINT_PREFIX} Suscripción a order reports exitosa")
                except Exception as e:
                    print(f"{PRINT_PREFIX} Error en suscripción order reports: {e}")
                    
            except Exception as e:
                print(f"{PRINT_PREFIX} Error inicializando WebSocket: {e}")
                # Si falla con ssl_context, intentar sin él
                try:
                    print(f"{PRINT_PREFIX} Intentando sin contexto SSL...")
                    self._pyrofex.init_websocket_connection(
                        market_data_handler=md_handler,
                        order_report_handler=self._handle_or,
                        error_handler=error_handler,
                        exception_handler=exception_handler
                    )
                    self._ws_open = True
                    print(f"{PRINT_PREFIX} WebSocket connection initialized without SSL context")
                    
                    # Suscribirse a order reports
                    try:
                        self._pyrofex.order_report_subscription()
                        print(f"{PRINT_PREFIX} Suscripción a order reports exitosa")
                    except Exception as e2:
                        print(f"{PRINT_PREFIX} Error en suscripción order reports: {e2}")
                        
                except Exception as e2:
                    print(f"{PRINT_PREFIX} Error inicializando WebSocket sin SSL: {e2}")
                    return {"status": "error", "error": str(e2), "ws": "disabled"}

            self._subscribe_many(instrumentos)

            return {
                "status": "started",
                "user_id": self.user,
                "instruments": list(instrumentos),
                "ws": "ok" if self._ws_open else "disabled",
            }

    def stop(self):
        with self._lock:
            if self._pyrofex and self._ws_open:
                self._pyrofex.close_websocket_connection()
            self._ws_open = False
            self._subscribed.clear()
            return {"status": "stopped", "ws": "disabled"}

    def restart_last(self):
        """Reinicia con los últimos parámetros usados"""
        if not self._last_params:
            return {"status": "error", "error": "No hay parámetros previos para reiniciar"}
        
        # Detener primero
        self.stop()
        
        # Reiniciar con últimos parámetros
        return self.start(**self._last_params)

    def status(self):
        with self._lock:
            return {
                "ws": "ok" if self._ws_open else "disabled",
                "user_id": self.user,
                "subscribed": sorted(self._subscribed),
                "last_md_ms": self.last_marketdata_at_ms,
                "subscribers": broadcaster.subscribers(),
                "last_order_report": self._last_order_report,
            }

    def _subscribe_many(self, instrumentos: Iterable[str]):
        if not self._pyrofex or not self._ws_open:
            return
        entries = [
            self._pyrofex.MarketDataEntry.BIDS,
            self._pyrofex.MarketDataEntry.OFFERS,
            self._pyrofex.MarketDataEntry.LAST,
            self._pyrofex.MarketDataEntry.CLOSING_PRICE,
            self._pyrofex.MarketDataEntry.OPENING_PRICE
        ]
        for sym in instrumentos:
            if sym not in self._subscribed:
                try:
                    self._pyrofex.market_data_subscription(tickers=[sym], entries=entries)
                    self._subscribed.add(sym)
                    print(f"{PRINT_PREFIX} Suscripto {sym}")
                except Exception as e:
                    print(f"{PRINT_PREFIX} Error al suscribir {sym}: {e}")

    def _handle_md(self, message: Dict[str, Any]):
        global _guardar_tick  # Declarar global al inicio
        
        symbol = _extract_symbol(message)
        if not symbol:
            return
        (bid_p, bid_sz), (ask_p, ask_sz), (last_p, last_sz) = _extract_levels(message)
        ts_ms = _extract_ts(message)
        cl_price = _extract_closing_price(message)
        op_price = _extract_opening_price(message)
        self.last_marketdata_at_ms = ts_ms
        quotes_cache[symbol] = {
            "bid": bid_p, "bid_size": bid_sz,
            "offer": ask_p, "offer_size": ask_sz,
            "last": last_p, "last_size": last_sz,
            "cl": cl_price,
            "op": op_price,
            "timestamp": ts_ms,
        }

        # Construir payload de tick estandarizado para difusión
        tick = {
            "type": "tick",
            "symbol": symbol,
            "bid": bid_p,
            "bid_size": bid_sz,
            "offer": ask_p,
            "offer_size": ask_sz,
            "last": last_p,
            "last_size": last_sz,
            "cl": cl_price,
            "op": op_price,
            "ts_ms": ts_ms,
        }

        # Difundir a clientes internos (si hay callback registrado)
        try:
            if _broadcast_callback:
                _broadcast_callback(tick)
        except Exception as e:
            print(f"{PRINT_PREFIX} error broadcast tick: {e}")
        if _guardar_tick:
            try:
                # Solo guardar si la tabla existe y hay datos válidos
                if symbol and (bid_p is not None or ask_p is not None or last_p is not None):
                    tick_data = {
                        "symbol": symbol, 
                        "bid": bid_p, 
                        "offer": ask_p, 
                        "last": last_p, 
                        "cl": cl_price,
                        "op": op_price,
                        "ts_ms": ts_ms,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
                    }
                    # Intentar guardar pero no fallar si la tabla no existe
                    result = _guardar_tick("ticks", tick_data)
                    if result is None:
                        # La tabla no existe, desactivar guardado
                        print(f"{PRINT_PREFIX} Tabla 'ticks' no existe, desactivando guardado de ticks")
                        # Desactivar guardado para futuras llamadas
                        _guardar_tick = None
            except Exception as e:
                print(f"{PRINT_PREFIX} fallo insert: {e}")
                # Desactivar guardado en caso de error
                _guardar_tick = None

    def _handle_or(self, message: Dict[str, Any]):
        """Order Report handler: guarda último reporte."""
        try:
            with self._lock:
                self._last_order_report = message
            
            # Log del order report para debugging
            client_order_id = (message.get("wsClOrdId") or 
                             message.get("clOrdId") or 
                             message.get("clientId") or 
                             message.get("client_order_id"))
            if client_order_id:
                print(f"{PRINT_PREFIX} Order report recibido - Client Order ID: {client_order_id}, Status: {message.get('status', 'N/A')}")
            
            # Difundir order report a interesados (vía callback genérico)
            try:
                if _broadcast_callback:
                    _broadcast_callback({
                        "type": "order_report",
                        "report": message
                    })
            except Exception as e:
                print(f"{PRINT_PREFIX} error broadcast order_report: {e}")
        except Exception:
            pass

    def subscribe_order_reports(self, account: str) -> Dict[str, Any]:
        with self._lock:
            if not self._pyrofex or not self._ws_open:
                return {"status": "error", "message": "ws_not_connected"}
            try:
                # Seguir el ejemplo oficial - sin parámetros
                self._pyrofex.order_report_subscription()
                print(f"{PRINT_PREFIX} Suscripción a order reports exitosa")
                return {"status": "ok"}
            except Exception as e:
                print(f"{PRINT_PREFIX} Error en suscripción order reports: {e}")
                return {"status": "error", "message": str(e)}

    def send_order(self, *, symbol: str, side: str, size: float, price: Optional[float] = None,
                   order_type: str = "LIMIT", tif: str = "DAY", market: Optional[str] = None, 
                   client_order_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if not self._pyrofex or not self._ws_open:
                return {"status": "error", "message": "ws_not_connected"}
            try:
                pr = self._pyrofex
                # Mapear enums
                _side = pr.Side.BUY if str(side).upper() in ("BUY", "B") else pr.Side.SELL
                _otype = pr.OrderType.LIMIT if str(order_type).upper() == "LIMIT" else pr.OrderType.MARKET
                # Tiempo en vigor si existe
                tif_arg = None
                try:
                    tif_map = {
                        "DAY": getattr(pr, "TimeInForce").DAY,
                        "IOC": getattr(pr, "TimeInForce").IMMEDIATE_OR_CANCEL if hasattr(getattr(pr, "TimeInForce"), "IMMEDIATE_OR_CANCEL") else getattr(pr, "TimeInForce").IOC,
                        "FOK": getattr(pr, "TimeInForce").FILL_OR_KILL if hasattr(getattr(pr, "TimeInForce"), "FILL_OR_KILL") else getattr(pr, "TimeInForce").FOK,
                    }
                    tif_arg = tif_map.get(str(tif).upper(), getattr(pr, "TimeInForce").DAY)
                except Exception:
                    tif_arg = None

                # Construir parámetros siguiendo el ejemplo oficial
                kwargs = {
                    "ticker": symbol,
                    "side": _side,
                    "size": int(size),  # Usar int como en el ejemplo
                    "order_type": _otype,
                }
                
                # Agregar precio si es LIMIT
                if price is not None and _otype == pr.OrderType.LIMIT:
                    kwargs["price"] = float(price)
                
                # Agregar client_order_id si se proporciona (usar ws_client_order_id como indica el error)
                if client_order_id:
                    kwargs["ws_client_order_id"] = str(client_order_id)
                
                print(f"{PRINT_PREFIX} Enviando orden: {symbol} {side} {size} @ {price}")

                res = pr.send_order_via_websocket(**kwargs)
                print(f"{PRINT_PREFIX} Orden enviada exitosamente: {symbol} {side} {size} @ {price}")
                return {"status": "ok", "response": res}
            except Exception as e:
                error_msg = str(e)
                print(f"{PRINT_PREFIX} Error enviando orden: {error_msg}")
                
                # Manejar errores específicos de conexión
                if "Connection is already closed" in error_msg:
                    print(f"{PRINT_PREFIX} Conexión ROFEX cerrada, intentando reconectar...")
                    self._ws_open = False
                    return {"status": "error", "message": "connection_closed", "details": error_msg}
                elif "Authentication fails" in error_msg:
                    print(f"{PRINT_PREFIX} Error de autenticación ROFEX")
                    return {"status": "error", "message": "authentication_failed", "details": error_msg}
                else:
                    return {"status": "error", "message": error_msg}

    def check_and_reconnect(self) -> Dict[str, Any]:
        """Verifica la conexión y reconecta si es necesario"""
        with self._lock:
            if not self._pyrofex:
                return {"status": "error", "message": "pyRofex not initialized"}
            
            if not self._ws_open:
                print(f"{PRINT_PREFIX} Conexión cerrada, intentando reconectar...")
                try:
                    # Intentar reconectar con los últimos parámetros
                    if self._last_params:
                        result = self.start(**self._last_params)
                        if result.get("status") == "started":
                            print(f"{PRINT_PREFIX} Reconexión exitosa")
                            return {"status": "ok", "message": "reconnected"}
                        else:
                            return {"status": "error", "message": "reconnection_failed", "details": result}
                    else:
                        return {"status": "error", "message": "no_last_params_for_reconnect"}
                except Exception as e:
                    return {"status": "error", "message": f"reconnect_error: {str(e)}"}
            else:
                return {"status": "ok", "message": "connection_alive"}

    def last_order_report(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._last_order_report
manager = MarketDataManager()