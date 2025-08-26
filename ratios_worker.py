# ratios_worker.py — con warm-start de ventanas
import threading
import time
import math
from collections import deque
from datetime import datetime, timezone

from supabase_client import get_active_pairs, guardar_en_supabase  # wrappers
try:
    from strategy_engine import evaluateAndAlert as _evaluate_and_alert
except Exception:
    def _evaluate_and_alert(**kwargs):
        return 0
try:
    # Necesario para hidratar desde DB
    from supabase_client import supabase
except Exception:
    supabase = None

from quotes_cache import quotes_cache

_worker_thread = None
_stop_event = threading.Event()
_session_user = None

# Buffers rodantes por par (clave: (base, quote, user, client))
_rolling: dict[tuple, dict[str, deque]] = {}
_hydrated_keys: set[tuple] = set()  # para no re-hidratar

# --------------------------- Parámetros --------------------------------------
INTERVAL_SECONDS   = 10
SMA_WINDOW         = 180   # 180 ticks * 10s ~ 30 min
STD_SHORT_WINDOW   = 60    # 60 ticks * 10s ~ 10 min
BAND_K             = 1.5   # Bandas ±K·σ (σ180)
WARMSTART_BARS     = 180   # cuántas filas traer para precalcular todo
VERBOSE_FIRST_PAIR = True

# ------------------------------- Helpers -------------------------------------
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
    if n <= 0:
        return None
    sub = list(values)[-n:]
    return sum(sub) / n

def _std_last(values: deque, window: int):
    """σ poblacional (ddof=0); None si no hay ≥2 datos."""
    if not values:
        return None
    sub = list(values)[-min(len(values), window):]
    n = len(sub)
    if n < 2:
        return None
    m = sum(sub) / n
    var = sum((x - m)**2 for x in sub) / n
    return math.sqrt(var)

def set_session(user_id: str):
    """Setea un user_id por sesión si no viene en los pares."""
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

# --------------------------- Warm-start desde DB -----------------------------
def _hydrate_from_db(base_symbol: str, quote_symbol: str, user_id: str, client_id: str, key: tuple):
    """Precarga los últimos WARMSTART_BARS ratios mid/bid/ask desde la tabla."""
    if supabase is None:
        print("[warmstart] supabase=None → sin hidratación")
        return

    try:
        cols = "asof,mid_ratio,bid_ratio,ask_ratio"
        q = (
            supabase.table("terminal_ratios_history")
            .select(cols)
            .eq("user_id", user_id)
            .eq("client_id", client_id)
            .eq("base_symbol", base_symbol)
            .eq("quote_symbol", quote_symbol)
            .order("asof", desc=True)
            .limit(WARMSTART_BARS)
        )
        res = q.execute()
        rows = (res.data or [])
        if not rows:
            print(f"[warmstart] sin historial para {base_symbol}/{quote_symbol}")
            return

        # Ascendente por asof para no “saltear” en las ventanas
        rows.sort(key=lambda r: r.get("asof") or "")

        buf = _rolling.get(key)
        if buf is None:
            buf = {"mid": deque(maxlen=SMA_WINDOW), "bid": deque(maxlen=SMA_WINDOW), "ask": deque(maxlen=SMA_WINDOW)}
            _rolling[key] = buf

        added_mid = added_bid = added_ask = 0
        for r in rows:
            m = r.get("mid_ratio"); b = r.get("bid_ratio"); a = r.get("ask_ratio")
            if _is_num(m): buf["mid"].append(float(m)); added_mid += 1
            if _is_num(b): buf["bid"].append(float(b)); added_bid += 1
            if _is_num(a): buf["ask"].append(float(a)); added_ask += 1

        _hydrated_keys.add(key)
        print(f"[warmstart] {base_symbol}/{quote_symbol} ← {added_mid}/{added_bid}/{added_ask} (mid/bid/ask) filas")
    except Exception as e:
        print(f"[warmstart] error hidratando {base_symbol}/{quote_symbol}: {e}")

# --------------------------------- Loop --------------------------------------
def _worker_loop():
    while not _stop_event.is_set():
        try:
            pairs = get_active_pairs()
            print(f"[ratios_worker] pares activos={len(pairs)}")

            for i, pair in enumerate(pairs):
                if VERBOSE_FIRST_PAIR and i == 0:
                    print(f"[ratios_worker] keys par[0]: {list(pair.keys())}")

                base_symbol  = pair.get("base_symbol")
                quote_symbol = pair.get("quote_symbol")
                user_id      = pair.get("user_id") or _session_user
                client_id    = pair.get("client_id") or "default"

                if not (base_symbol and quote_symbol and user_id):
                    print(f"[ratios_worker] ⚠️ par incompleto → {pair}")
                    continue

                key = (base_symbol, quote_symbol, user_id, client_id)

                # --- Warm-start (una sola vez por par)
                if key not in _hydrated_keys:
                    _hydrate_from_db(base_symbol, quote_symbol, user_id, client_id, key)

                base  = obtener_datos_mercado(base_symbol)
                quote = obtener_datos_mercado(quote_symbol)

                if VERBOSE_FIRST_PAIR and i == 0:
                    print(f"[ratios_worker] {base_symbol} => {base}")
                    print(f"[ratios_worker] {quote_symbol} => {quote}")

                if not base or not quote:
                    print(f"[ratios_worker] ❌ No hay datos para {base_symbol}/{quote_symbol}")
                    continue

                # --- Precios L1
                A_bid, A_ask, A_last = base.get("bid"), base.get("offer"), base.get("last")
                B_bid, B_ask, B_last = quote.get("bid"), quote.get("offer"), quote.get("last")

                # --- Tamaños (según cache)
                A_bid_sz = float(base["bid_size"])   if _is_num(base.get("bid_size"))   else None
                A_ask_sz = float(base["offer_size"]) if _is_num(base.get("offer_size")) else None
                B_bid_sz = float(quote["bid_size"])  if _is_num(quote.get("bid_size"))  else None
                B_ask_sz = float(quote["offer_size"])if _is_num(quote.get("offer_size"))else None

                # --- Ratios execution-aware
                bid_ratio = _safe_div(A_bid, B_ask) if (_is_num(A_bid) and _is_num(B_ask)) else None
                ask_ratio = _safe_div(A_ask, B_bid) if (_is_num(A_ask) and _is_num(B_bid)) else None

                # --- mid_ratio (preferentemente mid; si no hay, last)
                mid_A = ((float(A_bid)+float(A_ask))/2.0) if (_is_num(A_bid) and _is_num(A_ask)) else (float(A_last) if _is_num(A_last) else None)
                mid_B = ((float(B_bid)+float(B_ask))/2.0) if (_is_num(B_bid) and _is_num(B_ask)) else (float(B_last) if _is_num(B_last) else None)
                mid_ratio = _safe_div(mid_A, mid_B)

                if not any(x is not None for x in (mid_ratio, bid_ratio, ask_ratio)):
                    print(f"[ratios_worker] ❌ No se pudo calcular ningún ratio para {base_symbol}/{quote_symbol}")
                    continue

                # --- Buffers del par
                buf = _rolling.get(key)
                if buf is None:
                    buf = {"mid": deque(maxlen=SMA_WINDOW), "bid": deque(maxlen=SMA_WINDOW), "ask": deque(maxlen=SMA_WINDOW)}
                    _rolling[key] = buf

                if mid_ratio is not None: buf["mid"].append(mid_ratio)
                if bid_ratio is not None: buf["bid"].append(bid_ratio)
                if ask_ratio is not None: buf["ask"].append(ask_ratio)

                # --- Indicadores (mid para z/vol; bid/ask para bandas de ejecución)
                mid_sma180  = _sma_last(buf["mid"], SMA_WINDOW)
                mid_std60   = _std_last(buf["mid"], STD_SHORT_WINDOW)
                mid_std180  = _std_last(buf["mid"], SMA_WINDOW)

                bid_sma180  = _sma_last(buf["bid"], SMA_WINDOW)
                bid_std180  = _std_last(buf["bid"], SMA_WINDOW)

                ask_sma180  = _sma_last(buf["ask"], SMA_WINDOW)
                ask_std180  = _std_last(buf["ask"], SMA_WINDOW)

                # --- Bandas ±K·σ
                bb_bid_upper = (bid_sma180 + BAND_K * bid_std180) if (_is_num(bid_sma180) and _is_num(bid_std180)) else None
                bb_bid_lower = (bid_sma180 - BAND_K * bid_std180) if (_is_num(bid_sma180) and _is_num(bid_std180)) else None
                bb_mid_upper = (mid_sma180 + BAND_K * mid_std180) if (_is_num(mid_sma180) and _is_num(mid_std180)) else None
                bb_mid_lower = (mid_sma180 - BAND_K * mid_std180) if (_is_num(mid_sma180) and _is_num(mid_std180)) else None
                bb_ask_upper = (ask_sma180 + BAND_K * ask_std180) if (_is_num(ask_sma180) and _is_num(ask_std180)) else None
                bb_ask_lower = (ask_sma180 - BAND_K * ask_std180) if (_is_num(ask_sma180) and _is_num(ask_std180)) else None

                # --- z-scores (vs mid)
                z_bid_val = ((bid_ratio - mid_sma180) / mid_std60) if (_is_num(bid_ratio) and _is_num(mid_sma180) and _is_num(mid_std60) and mid_std60 > 0) else None
                z_ask_val = ((ask_ratio - mid_sma180) / mid_std60) if (_is_num(ask_ratio) and _is_num(mid_sma180) and _is_num(mid_std60) and mid_std60 > 0) else None

                # --- vol_ratio (régimen)
                vol_ratio = (mid_std60 / mid_std180) if (_is_num(mid_std60) and _is_num(mid_std180) and mid_std180 > 0) else None

                # --- spread del ratio
                ratio_spread = (ask_ratio - bid_ratio) if (_is_num(ask_ratio) and _is_num(bid_ratio)) else None
                if _is_num(ratio_spread) and ratio_spread < -1e-9:
                    print(f"[ratios_worker][WARN] ratio_spread NEGATIVO en {base_symbol}/{quote_symbol}: {ratio_spread:.6g}")

                # --- Construir row
                row = {
                    "user_id":        user_id,
                    "client_id":      client_id,
                    "base_symbol":    base_symbol,
                    "quote_symbol":   quote_symbol,
                    "asof":           datetime.now(timezone.utc).isoformat(),

                    # Ratios
                    "mid_ratio":      float(mid_ratio)   if _is_num(mid_ratio)   else None,
                    "bid_ratio":      float(bid_ratio)   if _is_num(bid_ratio)   else None,
                    "ask_ratio":      float(ask_ratio)   if _is_num(ask_ratio)   else None,

                    # Precios crudos
                    "bid_price_base":   float(A_bid) if _is_num(A_bid) else None,
                    "bid_price_quote":  float(B_bid) if _is_num(B_bid) else None,
                    "offer_price_base": float(A_ask) if _is_num(A_ask) else None,
                    "offer_price_quote":float(B_ask) if _is_num(B_ask) else None,

                    # Tamaños
                    "bid_size_base":    A_bid_sz,
                    "bid_size_quote":   B_bid_sz,
                    "offer_size_base":  A_ask_sz,
                    "offer_size_quote": B_ask_sz,

                    # SMA / Bandas
                    "sma180_bid":        float(bid_sma180)  if _is_num(bid_sma180)  else None,
                    "sma180_offer":      float(ask_sma180)  if _is_num(ask_sma180)  else None,
                    "sma180_mid":        float(mid_sma180)  if _is_num(mid_sma180)  else None,
                    "bb180_bid_upper":   float(bb_bid_upper) if _is_num(bb_bid_upper) else None,
                    "bb180_bid_lower":   float(bb_bid_lower) if _is_num(bb_bid_lower) else None,
                    "bb180_offer_upper": float(bb_ask_upper) if _is_num(bb_ask_upper) else None,
                    "bb180_offer_lower": float(bb_ask_lower) if _is_num(bb_ask_lower) else None,
                    "bb180_mid_upper":   float(bb_mid_upper) if _is_num(bb_mid_upper) else None,
                    "bb180_mid_lower":   float(bb_mid_lower) if _is_num(bb_mid_lower) else None,

                    # Volatilidades / z / spread / régimen
                    "std60_mid":         float(mid_std60)   if _is_num(mid_std60)   else None,
                    "std180_mid":        float(mid_std180)  if _is_num(mid_std180)  else None,
                    "z_bid":             float(z_bid_val)   if _is_num(z_bid_val)   else None,
                    "z_ask":             float(z_ask_val)   if _is_num(z_ask_val)   else None,
                    "ratio_spread":      float(ratio_spread)if _is_num(ratio_spread)else None,
                    "vol_ratio":         float(vol_ratio)   if _is_num(vol_ratio)   else None,
                }

                if VERBOSE_FIRST_PAIR and i == 0:
                    print("[sizes-debug]",
                          base_symbol, {"bid": row["bid_size_base"], "ask": row["offer_size_base"]},
                          "|", quote_symbol, {"bid": row["bid_size_quote"], "ask": row["offer_size_quote"]})

                # --- Guardar (si hay algún ratio)
                if any(row[k] is not None for k in ("mid_ratio","bid_ratio","ask_ratio")):
                    try:
                        result = guardar_en_supabase("terminal_ratios_history", row)
                        if result is None:
                            print("[ratios_worker] ❌ Error al guardar row (None)")
                        else:
                            print(f"[ratios_worker] ✅ Guardado {base_symbol}/{quote_symbol} "
                                  f"R_bid={row['bid_ratio']}, R_ask={row['ask_ratio']}, mid={row['mid_ratio']}")
                    except Exception as e:
                        print(f"[ratios_worker] error guardando ratio: {e}")
                else:
                    print(f"[ratios_worker] ⚠️ No hay ratios válidos para guardar en {base_symbol}/{quote_symbol}")

                # --- Evaluar reglas y notificar (Telegram) si matchean
                try:
                    snapshot = {
                        "base": base,
                        "quote": quote,
                        "ratios": {
                            "mid": mid_ratio,
                            "bid": bid_ratio,
                            "ask": ask_ratio,
                            "sma180_mid": mid_sma180,
                            "std60_mid": mid_std60,
                            "std180_mid": mid_std180,
                        }
                    }
                    matched = _evaluate_and_alert(
                        user_id=str(user_id),
                        client_id=str(client_id),
                        base_symbol=str(base_symbol),
                        quote_symbol=str(quote_symbol),
                        snapshot=snapshot,
                    )
                    if matched:
                        print(f"[ratios_worker] 🔔 {matched} regla(s) cumplida(s) para {base_symbol}/{quote_symbol}")
                except Exception as e:
                    print(f"[ratios_worker] error evaluando alertas: {e}")

        except Exception as e:
            print(f"[ratios_worker] error en loop: {e}")

        time.sleep(INTERVAL_SECONDS)

# -------------------------------- Control ------------------------------------
def start():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    print("[ratios_worker] Worker iniciado - procesando pares activos")

def stop():
    _stop_event.set()
