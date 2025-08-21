import threading
import time
import math
from collections import deque
from datetime import datetime, timezone

from supabase_client import get_active_pairs, guardar_en_supabase, get_last_ratio_data
from quotes_cache import quotes_cache

_worker_thread = None
_stop_event = threading.Event()
_session_user = None

# Buffers de ventanas rodantes por par (clave: (base, quote, user))
_rolling = {}

# --------------------------- Parámetros de cálculo ---------------------------
INTERVAL_SECONDS   = 10
SMA_WINDOW         = 180   # 180 ticks * 10s ~ 30 min
STD_SHORT_WINDOW   = 60    # 60 ticks * 10s ~ 10 min
BAND_K             = 1.5   # Bandas ±K·σ (sobre σ180)

VERBOSE_FIRST_PAIR = True  # logs extras en el primer par de cada iteración


# ------------------------------- Helpers numéricos ---------------------------
def _is_num(x):
    try:
        return x is not None and float(x) == float(x)
    except Exception:
        return False

def _safe_div(a, b):
    try:
        a = float(a); b = float(b)
        if b == 0 or a != a or b != b:
            return None
        return a / b
    except Exception:
        return None

def _sma_last(values: deque, window: int):
    if not values:
        return None
    n = min(len(values), window)
    if n == 0:
        return None
    sub = list(values)[-n:]
    return sum(sub) / n

def _std_last(values: deque, window: int):
    """σ poblacional (ddof=0). Devuelve None si no hay ≥2 datos."""
    if not values:
        return None
    sub = list(values)[-min(len(values), window):]
    n = len(sub)
    if n < 2:
        return None
    m = sum(sub) / n
    var = sum((x - m) ** 2 for x in sub) / n
    return math.sqrt(var)


# --------------------------------- API pública --------------------------------
def set_session(user_id: str):
    global _session_user
    _session_user = user_id


def obtener_datos_mercado(symbol: str) -> dict | None:
    """Devuelve el dict del cache si hay last/bid/offer; si no, None."""
    datos = quotes_cache.get(symbol)
    if not isinstance(datos, dict):
        return None
    if any(datos.get(k) is not None for k in ("last", "bid", "offer")):
        return datos
    return None


def _worker_loop():
    while not _stop_event.is_set():
        try:
            pairs = get_active_pairs()
            print(f"[ratios_worker] pares activos={len(pairs)}")

            for i, pair in enumerate(pairs):
                # ---- Logs de depuración (solo primer par por iteración)
                if VERBOSE_FIRST_PAIR and i == 0:
                    print(f"[ratios_worker] keys par[0]: {list(pair.keys())}")

                base_symbol  = pair.get("base_symbol")
                quote_symbol = pair.get("quote_symbol")
                base  = obtener_datos_mercado(base_symbol)
                quote = obtener_datos_mercado(quote_symbol)

                if VERBOSE_FIRST_PAIR and i == 0:
                    print(f"[ratios_worker] {base_symbol} => {base}")
                    print(f"[ratios_worker] {quote_symbol} => {quote}")

                if not base or not quote:
                    print(f"[ratios_worker] ❌ No hay datos para {base_symbol} / {quote_symbol}")
                    continue

                # ------ Extraer lados
                A_bid   = base.get("bid")
                A_ask   = base.get("offer")
                A_last  = base.get("last")

                B_bid   = quote.get("bid")
                B_ask   = quote.get("offer")
                B_last  = quote.get("last")

                # ------ Ratios execution-aware
                # SELL ratio ahora: vendés A al bid y comprás B al ask
                bid_ratio = _safe_div(A_bid, B_ask) if (_is_num(A_bid) and _is_num(B_ask)) else None
                # BUY ratio ahora: comprás A al ask y vendés B al bid
                ask_ratio = _safe_div(A_ask, B_bid) if (_is_num(A_ask) and _is_num(B_bid)) else None

                # ------ mid_ratio preferente: mid = (bid+ask)/2; si no hay, fallback a last
                mid_A = ((float(A_bid) + float(A_ask)) / 2.0) if (_is_num(A_bid) and _is_num(A_ask)) else (float(A_last) if _is_num(A_last) else None)
                mid_B = ((float(B_bid) + float(B_ask)) / 2.0) if (_is_num(B_bid) and _is_num(B_ask)) else (float(B_last) if _is_num(B_last) else None)
                mid_ratio = _safe_div(mid_A, mid_B)

                if not any(x is not None for x in (mid_ratio, bid_ratio, ask_ratio)):
                    print(f"[ratios_worker] ❌ No se pudo calcular ningún ratio para {base_symbol}/{quote_symbol}")
                    continue

                # ------ Rolling buffers
                user_id_key = pair.get("user_id") or pair.get("client_id") or _session_user or "default"
                key = (base_symbol, quote_symbol, user_id_key)
                buf = _rolling.get(key)
                if buf is None:
                    buf = {"mid": deque(maxlen=SMA_WINDOW), "bid": deque(maxlen=SMA_WINDOW), "ask": deque(maxlen=SMA_WINDOW)}
                    _rolling[key] = buf

                if mid_ratio is not None: buf["mid"].append(mid_ratio)
                if bid_ratio is not None: buf["bid"].append(bid_ratio)
                if ask_ratio is not None: buf["ask"].append(ask_ratio)

                # ------ Indicadores (mid para z/vol; bid/ask para bandas de ejecución)
                mid_sma180  = _sma_last(buf["mid"], SMA_WINDOW)
                mid_std60   = _std_last(buf["mid"], STD_SHORT_WINDOW)
                mid_std180  = _std_last(buf["mid"], SMA_WINDOW)

                bid_sma180  = _sma_last(buf["bid"], SMA_WINDOW)
                bid_std180  = _std_last(buf["bid"], SMA_WINDOW)

                ask_sma180  = _sma_last(buf["ask"], SMA_WINDOW)
                ask_std180  = _std_last(buf["ask"], SMA_WINDOW)

                # ------ Bandas ±K·σ (K=1.5 por default)
                bb_bid_upper = (bid_sma180 + BAND_K * bid_std180) if (_is_num(bid_sma180) and _is_num(bid_std180)) else None
                bb_bid_lower = (bid_sma180 - BAND_K * bid_std180) if (_is_num(bid_sma180) and _is_num(bid_std180)) else None
                bb_ask_upper = (ask_sma180 + BAND_K * ask_std180) if (_is_num(ask_sma180) and _is_num(ask_std180)) else None
                bb_ask_lower = (ask_sma180 - BAND_K * ask_std180) if (_is_num(ask_sma180) and _is_num(ask_std180)) else None
                bb_mid_upper = (mid_sma180 + BAND_K * mid_std180) if (_is_num(mid_sma180) and _is_num(mid_std180)) else None
                bb_mid_lower = (mid_sma180 - BAND_K * mid_std180) if (_is_num(mid_sma180) and _is_num(mid_std180)) else None

                # ------ z-scores (vs mid: SMA180_mid / σ60_mid)
                z_bid_val = ((bid_ratio - mid_sma180) / mid_std60) if (_is_num(bid_ratio) and _is_num(mid_sma180) and _is_num(mid_std60) and mid_std60 > 0) else None
                z_ask_val = ((ask_ratio - mid_sma180) / mid_std60) if (_is_num(ask_ratio) and _is_num(mid_sma180) and _is_num(mid_std60) and mid_std60 > 0) else None

                # ------ vol_ratio (régimen)
                vol_ratio = (mid_std60 / mid_std180) if (_is_num(mid_std60) and _is_num(mid_std180) and mid_std180 > 0) else None

                # ------ spread del ratio (debe ser ≥ 0)
                ratio_spread = (ask_ratio - bid_ratio) if (_is_num(ask_ratio) and _is_num(bid_ratio)) else None
                if _is_num(ratio_spread) and ratio_spread < -1e-9:
                    print(f"[ratios_worker][WARN] ratio_spread NEGATIVO en {base_symbol}/{quote_symbol}: {ratio_spread:.6g} (revisar lados)")

                # (Opcional) datos históricos SOLO para campos no críticos en frío de arranque
                historical_data = get_last_ratio_data(base_symbol, quote_symbol, pair.get("user_id")) or {}

                # ------ Construcción de row
                asof_utc = datetime.now(timezone.utc).isoformat()
                user_id  = user_id_key
                client_id = pair.get("client_id", user_id)

                row = {
                    "user_id": user_id,
                    "client_id": client_id,
                    "base_symbol": base_symbol,
                    "quote_symbol": quote_symbol,
                    "asof": asof_utc,

                    # Ratios
                    "mid_ratio":   float(mid_ratio) if _is_num(mid_ratio) else None,
                    "bid_ratio":   float(bid_ratio) if _is_num(bid_ratio) else None,
                    "ask_ratio":   float(ask_ratio) if _is_num(ask_ratio) else None,

                    # Precios crudos (auditoría)
                    "bid_price_base":   float(A_bid)  if _is_num(A_bid)  else None,
                    "bid_price_quote":  float(B_bid)  if _is_num(B_bid)  else None,
                    "offer_price_base": float(A_ask)  if _is_num(A_ask)  else None,
                    "offer_price_quote":float(B_ask)  if _is_num(B_ask)  else None,

                    # SMA / Bandas (bid/ask/mid)
                    "sma180_bid":        float(bid_sma180)  if _is_num(bid_sma180)  else None,
                    "sma180_offer":      float(ask_sma180)  if _is_num(ask_sma180)  else None,
                    "sma180_mid":        float(mid_sma180)  if _is_num(mid_sma180)  else None,

                    "bb180_bid_upper":   float(bb_bid_upper) if _is_num(bb_bid_upper) else None,
                    "bb180_bid_lower":   float(bb_bid_lower) if _is_num(bb_bid_lower) else None,
                    "bb180_offer_upper": float(bb_ask_upper) if _is_num(bb_ask_upper) else None,
                    "bb180_offer_lower": float(bb_ask_lower) if _is_num(bb_ask_lower) else None,
                    "bb180_mid_upper":   float(bb_mid_upper) if _is_num(bb_mid_upper) else None,
                    "bb180_mid_lower":   float(bb_mid_lower) if _is_num(bb_mid_lower) else None,

                    # Volatilidades y z (mid framework)
                    "std60_mid":         float(mid_std60)   if _is_num(mid_std60)   else None,
                    "std180_mid":        float(mid_std180)  if _is_num(mid_std180)  else None,
                    "z_bid":             float(z_bid_val)   if _is_num(z_bid_val)   else None,
                    "z_ask":             float(z_ask_val)   if _is_num(z_ask_val)   else None,
                    "ratio_spread":      float(ratio_spread)if _is_num(ratio_spread)else None,
                    "vol_ratio":         float(vol_ratio)   if _is_num(vol_ratio)   else None,
                }

                # ------ Guardar (si hay al menos algún ratio)
                if any(x is not None for x in (row["mid_ratio"], row["bid_ratio"], row["ask_ratio"])):
                    try:
                        result = guardar_en_supabase("terminal_ratios_history", row)
                        if result is None:
                            print(f"[ratios_worker] ❌ Error al guardar row (None)")
                        else:
                            print(f"[ratios_worker] ✅ Guardado {base_symbol}/{quote_symbol} "
                                  f"R_bid={row['bid_ratio']}, R_ask={row['ask_ratio']}, mid={row['mid_ratio']}")
                    except Exception as e:
                        print(f"[ratios_worker] error guardando ratio: {e}")
                else:
                    print(f"[ratios_worker] ⚠️ No hay ratios válidos para guardar en {base_symbol}/{quote_symbol}")

        except Exception as e:
            print(f"[ratios_worker] error en loop: {e}")

        time.sleep(INTERVAL_SECONDS)


def start():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    print("[ratios_worker] Worker iniciado - procesando todos los pares activos")


def stop():
    _stop_event.set()
