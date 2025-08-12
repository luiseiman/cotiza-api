# supabase_client.py
import os
import json
import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode
from dotenv import load_dotenv
import requests

load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")

if not URL or not KEY:
    raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_KEY en el .env")

BASE = f"{URL.rstrip('/')}/rest/v1"

BASE_HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# ---------------- Mini cliente compatible con supabase.table(...).X().execute() ----------------
class _Exec:
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        class _R:
            def __init__(self, data):
                self.data = data
        return _R(self._fn())

class _TableWrapper:
    def __init__(self, name: str):
        self._name = name

    def select(self, query: str = "*"):
        def _run():
            params = {"select": query}
            resp = requests.get(
                f"{BASE}/{self._name}",
                headers=BASE_HEADERS,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        return _Exec(_run)

    def insert(self, rows: Union[Dict[str, Any], List[Dict[str, Any]]]):
        def _run():
            headers = {**BASE_HEADERS, "Prefer": "return=representation"}
            resp = requests.post(
                f"{BASE}/{self._name}",
                headers=headers,
                data=json.dumps(rows),
                timeout=30,
            )
            resp.raise_for_status()
            # Puede devolver lista de filas insertadas
            return resp.json() if resp.text else []
        return _Exec(_run)

    def upsert(
        self,
        rows: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[Union[str, List[str]]] = None,
    ):
        def _run():
            headers = {**BASE_HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"}
            params = {}
            if on_conflict:
                if isinstance(on_conflict, (list, tuple)):
                    on_conflict_val = ",".join(on_conflict)
                else:
                    on_conflict_val = str(on_conflict)
                params["on_conflict"] = on_conflict_val

            resp = requests.post(
                f"{BASE}/{self._name}",
                headers=headers,
                params=params,
                data=json.dumps(rows),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json() if resp.text else []
        return _Exec(_run)

class _CompatClient:
    def table(self, name: str):
        return _TableWrapper(name)

# Objeto “supabase” compatible con el resto del proyecto
supabase = _CompatClient()

# ---------------- Helper que ya usabas para guardar ticks ----------------
def guardar_en_supabase(data: dict):
    """
    Guarda ticks en:
      - cotizaciones_historicas (insert)
      - ultima_cotizacion (upsert por symbol)

    data espera keys:
      symbol, timestamp(ms o iso), bid_price, bid_size, offer_price, offer_size, last_price, last_size, raw
    """
    ts = data.get("timestamp")
    if isinstance(ts, (int, float)):
        ts_iso = datetime.datetime.utcfromtimestamp(ts / 1000).isoformat()
    elif isinstance(ts, str):
        ts_iso = ts
    else:
        ts_iso = datetime.datetime.utcnow().isoformat()

    row = {
        "symbol": data.get("symbol"),
        "timestamp": ts_iso,
        "bid_price": data.get("bid_price"),
        "bid_size": data.get("bid_size"),
        "offer_price": data.get("offer_price"),
        "offer_size": data.get("offer_size"),
        "last_price": data.get("last_price"),
        "last_size": data.get("last_size"),
        "raw": data.get("raw"),
    }

    # Insert histórico
    supabase.table("cotizaciones_historicas").insert(row).execute()
    # Upsert última por symbol
    supabase.table("ultima_cotizacion").upsert(row, on_conflict="symbol").execute()
