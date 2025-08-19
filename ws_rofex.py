from __future__ import annotations
import time
import threading
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

class MarketDataManager:
    def __init__(self) -> None:
        self._pyrofex = None
        self._ws_open = False
        self._lock = threading.RLock()
        self.user: Optional[str] = None
        self._subscribed: set[str] = set()
        self.last_marketdata_at_ms: Optional[int] = None
        self._last_params: Optional[Dict[str, Any]] = None

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
            except Exception as e:
                print(f"{PRINT_PREFIX} No se pudo importar pyRofex: {e}")
                return {"status": "error", "error": "pyRofex not available", "ws": "disabled"}

            self.user = user

            try:
                env = getattr(self._pyrofex.Environment, "LIVE")
                self._pyrofex.initialize(user=user, password=password, account=account, environment=env)
            except Exception as e:
                return {"status": "error", "error": str(e), "ws": "disabled"}

            def md_handler(msg: Dict[str, Any]):
                self._handle_md(msg)

            try:
                self._pyrofex.init_websocket_connection(
                    market_data_handler=md_handler,
                    order_report_handler=lambda m: None,
                    error_handler=lambda e: print(f"{PRINT_PREFIX} WS error: {e}")
                )
                self._ws_open = True
            except Exception as e:
                return {"status": "error", "error": str(e), "ws": "disabled"}

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
            }

    def _subscribe_many(self, instrumentos: Iterable[str]):
        if not self._pyrofex or not self._ws_open:
            return
        entries = [
            self._pyrofex.MarketDataEntry.BIDS,
            self._pyrofex.MarketDataEntry.OFFERS,
            self._pyrofex.MarketDataEntry.LAST
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
        self.last_marketdata_at_ms = ts_ms
        quotes_cache[symbol] = {
            "bid": bid_p, "bid_size": bid_sz,
            "offer": ask_p, "offer_size": ask_sz,
            "last": last_p, "last_size": last_sz,
            "timestamp": ts_ms,
        }
        if _guardar_tick:
            try:
                # Solo guardar si la tabla existe y hay datos válidos
                if symbol and (bid_p is not None or ask_p is not None or last_p is not None):
                    tick_data = {
                        "symbol": symbol, 
                        "bid": bid_p, 
                        "offer": ask_p, 
                        "last": last_p, 
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

manager = MarketDataManager()