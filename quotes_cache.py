import time
import threading
from typing import Dict, Any, Optional

quotes_cache: Dict[str, Dict[str, Any]] = {}
_lock = threading.RLock()

def now_ms() -> int:
    return int(time.time() * 1000)

def set_quote(symbol: str, data: Dict[str, Any]) -> None:
    if not symbol:
        return
    d = dict(data or {})
    if "ts_ms" not in d or not isinstance(d["ts_ms"], int):
        d["ts_ms"] = now_ms()
    with _lock:
        quotes_cache[symbol] = d

def get_quote(symbol: str) -> Optional[Dict[str, Any]]:
    with _lock:
        q = quotes_cache.get(symbol)
        return dict(q) if q else None

def get_snapshot() -> Dict[str, Dict[str, Any]]:
    with _lock:
        return {k: dict(v) for k, v in quotes_cache.items()}
