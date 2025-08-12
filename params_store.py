# params_store.py
from threading import RLock

_last_params = None
_lock = RLock()

def set_last_params(params: dict):
    """params = {"instrumentos": [...], "user": "...", "password": "...", "account": "..."}"""
    global _last_params
    with _lock:
        _last_params = dict(params) if params else None

def get_last_params():
    with _lock:
        return dict(_last_params) if _last_params else None
