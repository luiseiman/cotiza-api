# ratios_worker.py
# Calcula ratios (bid_ratio/ask_ratio/mid_ratio), SMA180, Bollinger y z-scores
# Warmup: carga hasta 180 últimos puntos por par desde terminal_ratios_history.
# Requiere: supabase_client.supabase (wrapper requests) y quotes_cache (dict global)

import time
import math
import datetime as dt
from collections import deque
from typing import Dict, Tuple, Deque, Optional, List

from supabase_client import supabase  # wrapper con .table(...).select(...).insert(...).execute()
from quotes_cache import quotes_cache  # {"SYMBOL": {"bid": float|None, "offer": float|None, "timestamp": int(ms)}}

PRINT_PREFIX = "[ratios_worker]"

# Historial en memoria por par
# key: (base_symbol, quote_symbol)  -> value: dict con deques y última asof
_hist: Dict[Tuple[str, str], Dict[str, Deque[float]]] = {}

# ---- Helpers numéricos ----
def _safe_float(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except Exception:
        return None

def _mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)

def _std(values: List[float]) -> Optional[float]:
    n = len(values)
    if n < 2:
        return None
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / (n - 1)  # sample std
    return math.sqrt(var)

def _bollinger(mean: Optional[float], std: Optional[float], k: float = 2.0):
    if mean is None or std is None:
        return None, None
    return mean + k * std, mean - k * std

def _now_iso_utc() -> str:
    return dt.datetime.utcnow().isoformat()

# ---- Warmup desde historial (tabla terminal_ratios_history) ----
def _warmup_pair(base_symbol: str, quote_symbol: str):
    """
    Carga últimos 180 puntos para (base, quote) y precalienta deques.
    Usa columnas: bid_ratio, ask_ratio, mid_ratio, asof (en tu tabla).
    """
    key = (base_symbol, quote_symbol)
    if key in _hist:
        return  # ya calentado

    bid_hist: Deque[float] = deque(maxlen=180)
    ask_hist: Deque[float] = deque(maxlen=180)
    mid_hist: Deque[float] = deque(maxlen=180)

    try:
        # Nota: tu wrapper permite pasar filtros como params: eq.<valor>, order, limit.
        res = supabase.table("terminal_ratios_history").select(
            "bid_ratio,ask_ratio,mid_ratio,asof",
            base_symbol=f"eq.{base_symbol}",
            quote_symbol=f"eq.{quote_symbol}",
            order="asof.desc",
            limit="180",
        ).execute()
        rows = res.data if hasattr(res, "data") else res  # compat

        # Cargamos en orden cronológico (invertimos)
        for r in reversed(rows or []):
            br = _safe_float(r.get("bid_ratio"))
            ar = _safe_float(r.get("ask_ratio"))
            mr = _safe_float(r.get("mid_ratio"))
            if br is not None:
                bid_hist.append(br)
            if ar is not None:
                ask_hist.append(ar)
            if mr is not None:
                mid_hist.append(mr)

        _hist[key] = {
            "bid_hist": bid_hist,
            "ask_hist": ask_hist,
            "mid_hist": mid_hist,
        }

        print(f"{PRINT_PREFIX} Warmup {base_symbol} / {quote_symbol}: "
              f"bid={len(bid_hist)}, ask={len(ask_hist)}, mid={len(mid_hist)}")

    except Exception as e:
        print(f"{PRINT_PREFIX} Error warmup {base_symbol}/{quote_symbol}: {e}")
        _hist[key] = {
            "bid_hist": bid_hist,
            "ask_hist": ask_hist,
            "mid_hist": mid_hist,
        }

def _compute_ratios(base_cache: dict, quote_cache: dict):
    """
    Define ratios así:
      - bid_ratio = base_bid / quote_ask
      - ask_ratio = base_ask / quote_bid
      - mid_ratio = mid_base / mid_quote
    Donde mid_x = (bid+ask)/2 si ambos existen.
    """
    b_bid = _safe_float(base_cache.get("bid"))
    b_ask = _safe_float(base_cache.get("offer"))
    q_bid = _safe_float(quote_cache.get("bid"))
    q_ask = _safe_float(quote_cache.get("offer"))

    bid_ratio = None
    ask_ratio = None
    mid_ratio = None

    # bid_ratio: requiere base_bid y quote_ask
    if b_bid is not None and q_ask is not None and q_ask != 0:
        bid_ratio = b_bid / q_ask

    # ask_ratio: requiere base_ask y quote_bid
    if b_ask is not None and q_bid is not None and q_bid != 0:
        ask_ratio = b_ask / q_bid

    # mid_ratio
    b_mid = None
    q_mid = None
    if b_bid is not None and b_ask is not None:
        b_mid = 0.5 * (b_bid + b_ask)
    if q_bid is not None and q_ask is not None:
        q_mid = 0.5 * (q_bid + q_ask)
    if b_mid is not None and q_mid is not None and q_mid != 0:
        mid_ratio = b_mid / q_mid

    return bid_ratio, ask_ratio, mid_ratio, b_bid, b_ask, q_bid, q_ask

def _append_and_metrics(key: Tuple[str, str], bid_ratio: Optional[float], ask_ratio: Optional[float], mid_ratio: Optional[float]):
    """Actualiza deques y calcula métricas derivadas."""
    H = _hist[key]
    bid_hist: Deque[float] = H["bid_hist"]
    ask_hist: Deque[float] = H["ask_hist"]
    mid_hist: Deque[float] = H["mid_hist"]

    if bid_ratio is not None:
        bid_hist.append(bid_ratio)
    if ask_ratio is not None:
        ask_hist.append(ask_ratio)
    if mid_ratio is not None:
        mid_hist.append(mid_ratio)

    # Medias móviles 180
    sma180_bid = _mean(list(bid_hist)) if len(bid_hist) > 0 else None
    sma180_ask = _mean(list(ask_hist)) if len(ask_hist) > 0 else None
    sma180_mid = _mean(list(mid_hist)) if len(mid_hist) > 0 else None

    # Bollinger 180 para bid/ask/mid con std de la misma serie si hay suficientes datos
    std180_bid = _std(list(bid_hist)) if len(bid_hist) >= 2 else None
    std180_ask = _std(list(ask_hist)) if len(ask_hist) >= 2 else None
    std180_mid = _std(list(mid_hist)) if len(mid_hist) >= 2 else None

    bb180_bid_upper, bb180_bid_lower = _bollinger(sma180_bid, std180_bid)
    bb180_ask_upper, bb180_ask_lower = _bollinger(sma180_ask, std180_ask)
    bb180_mid_upper, bb180_mid_lower = _bollinger(sma180_mid, std180_mid)

    # Std 60 para mid
    std60_mid = _std(list(mid_hist)[-60:]) if len(mid_hist) >= 2 else None

    # Z-scores usando std180_mid (consistente con columnas que tenés)
    z_bid = ((bid_ratio - sma180_bid) / std180_mid) if (bid_ratio is not None and sma180_bid is not None and std180_mid not in (None, 0)) else None
    z_ask = ((ask_ratio - sma180_ask) / std180_mid) if (ask_ratio is not None and sma180_ask is not None and std180_mid not in (None, 0)) else None

    # Otros
    ratio_spread = (ask_ratio - bid_ratio) if (ask_ratio is not None and bid_ratio is not None) else None
    vol_ratio = None  # no tenemos volúmenes en quotes_cache (podés completar más adelante)

    return {
        "sma180_bid": sma180_bid,
        "sma180_offer": sma180_ask,  # tu columna se llama 'sma180_offer'
        "bb180_bid_upper": bb180_bid_upper,
        "bb180_bid_lower": bb180_bid_lower,
        "bb180_offer_upper": bb180_ask_upper,
        "bb180_offer_lower": bb180_ask_lower,
        "sma180_mid": sma180_mid,
        "std60_mid": std60_mid,
        "std180_mid": std180_mid,
        "z_bid": z_bid,
        "z_ask": z_ask,
        "ratio_spread": ratio_spread,
        "vol_ratio": vol_ratio,
        "bb180_mid_upper": bb180_mid_upper,
        "bb180_mid_lower": bb180_mid_lower,
    }

def periodic_ratios_job():
    print(f">> {PRINT_PREFIX} Arrancando job de cálculo de ratios cada 10 segundos")

    while True:
        try:
            # 1) Leer todos los pares configurados
            try:
                res = supabase.table("terminal_ratio_pairs").select("*").execute()
                pairs = res.data if hasattr(res, "data") else res
            except Exception as e:
                print(f"{PRINT_PREFIX} Error consultando terminal_ratio_pairs: {e}")
                pairs = []

            # 2) Debug de cache
            try:
                cache_keys = list(quotes_cache.keys())
                print(f"{PRINT_PREFIX} Claves en quotes_cache: {cache_keys}")
            except Exception as e:
                print(f"{PRINT_PREFIX} Error leyendo quotes_cache: {e}")

            # 3) Procesar cada par
            for p in pairs or []:
                user_id = p.get("user_id")
                client_id = p.get("client_id")
                base_symbol = p.get("base_symbol")
                quote_symbol = p.get("quote_symbol")

                if not base_symbol or not quote_symbol:
                    continue

                # Warmup por par (si no existe en _hist)
                _warmup_pair(base_symbol, quote_symbol)
                key = (base_symbol, quote_symbol)

                base_cache = quotes_cache.get(base_symbol)
                quote_cache = quotes_cache.get(quote_symbol)
                print(f"{PRINT_PREFIX} Revisando par {base_symbol} / {quote_symbol}: "
                      f"base_cache={'OK' if base_cache else None}, quote_cache={'OK' if quote_cache else None}")
                if not base_cache or not quote_cache:
                    print(f"{PRINT_PREFIX} SIN DATOS en cache para {base_symbol} / {quote_symbol}")
                    continue

                bid_ratio, ask_ratio, mid_ratio, b_bid, b_ask, q_bid, q_ask = _compute_ratios(base_cache, quote_cache)

                # No guardamos si falta alguno de los dos ratios principales
                if bid_ratio is None or ask_ratio is None:
                    print(f"{PRINT_PREFIX} Datos incompletos para {base_symbol} / {quote_symbol} "
                          f"(bid_ratio={bid_ratio}, ask_ratio={ask_ratio}). No se guarda.")
                    continue

                metrics = _append_and_metrics(key, bid_ratio, ask_ratio, mid_ratio)

                row = {
                    "user_id": user_id,
                    "client_id": client_id,
                    "base_symbol": base_symbol,
                    "quote_symbol": quote_symbol,
                    "asof": _now_iso_utc(),
                    "bid_ratio": bid_ratio,
                    "ask_ratio": ask_ratio,
                    "bid_price_base": b_bid,
                    "bid_price_quote": q_bid,
                    "offer_price_base": b_ask,
                    "offer_price_quote": q_ask,
                    "sma180_bid": metrics["sma180_bid"],
                    "sma180_offer": metrics["sma180_offer"],
                    "bb180_bid_upper": metrics["bb180_bid_upper"],
                    "bb180_bid_lower": metrics["bb180_bid_lower"],
                    "bb180_offer_upper": metrics["bb180_offer_upper"],
                    "bb180_offer_lower": metrics["bb180_offer_lower"],
                    "mid_ratio": mid_ratio,
                    "sma180_mid": metrics["sma180_mid"],
                    "std60_mid": metrics["std60_mid"],
                    "std180_mid": metrics["std180_mid"],
                    "z_bid": metrics["z_bid"],
                    "z_ask": metrics["z_ask"],
                    "ratio_spread": metrics["ratio_spread"],
                    "vol_ratio": metrics["vol_ratio"],
                    "bb180_mid_upper": metrics["bb180_mid_upper"],
                    "bb180_mid_lower": metrics["bb180_mid_lower"],
                }

                try:
                    supabase.table("terminal_ratios_history").insert(row).execute()
                    print(f"{PRINT_PREFIX} Guardado OK {base_symbol} / {quote_symbol}: "
                          f"BID {bid_ratio:.6f}, ASK {ask_ratio:.6f}, MID {mid_ratio if mid_ratio is not None else 'NA'}")
                except Exception as e:
                    print(f"{PRINT_PREFIX} Error insertando terminal_ratios_history: {e}")

        except Exception as loop_e:
            print(f"{PRINT_PREFIX} Error en loop principal: {loop_e}")

        time.sleep(10)
