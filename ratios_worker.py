# -----------------------------------------------------------------------------
# ratios_worker.py
# Calcula ratios base/quote cada 10s y guarda en public.terminal_ratios_history.
#
# Definiciones *execution-aware*:
#   bid_ratio = base_bid   / quote_offer   # vender el ratio ahora (sell)
#   ask_ratio = base_offer / quote_bid     # comprar el ratio ahora (buy)
#
# Métricas extendidas:
#   mid_ratio, sma180_mid, std60_mid, std180_mid, z_bid, z_ask, ratio_spread,
#   vol_ratio (STD60/STD180), bb180_mid_upper/lower
#
# Requisitos:
#   - quotes_cache: dict global {symbol: {"bid": float|None, "offer": float|None, "timestamp": int|None}}
#   - supabase_client.supabase: wrapper con .table(...).insert(row).execute()
#   - Tablas:
#       terminal_ratio_pairs(user_id, client_id, base_symbol, quote_symbol)
#       terminal_ratios_history(*) según tu schema actual
# -----------------------------------------------------------------------------

import time
import datetime
from collections import defaultdict, deque
from statistics import mean, pstdev

print(">>> [ratios_worker] INIT MODULE")

# ---------------------------- Dependencias externas ---------------------------
try:
    from quotes_cache import quotes_cache
    print(">>> [ratios_worker] quotes_cache importado")
except Exception as e:
    print(f"[ratios_worker] ERROR importando quotes_cache: {e}")
    quotes_cache = {}

try:
    from supabase_client import supabase
except Exception as e:
    print(f"[ratios_worker] ERROR importando supabase_client: {e}")
    supabase = None

# --------------------------------- Parámetros --------------------------------
INTERVAL_SECONDS   = 10
SMA_WINDOW         = 180   # 180*10s ~ 30m
STD_SHORT_WINDOW   = 60    # 60*10s ~ 10m
VERBOSE            = False
LOG_INSERT_COLUMNS = False  # ponelo True si necesitás ver exactamente qué se inserta

# Historias en memoria por par (base, quote)
_hist_bid = defaultdict(lambda: deque(maxlen=SMA_WINDOW))  # serie para vender (R_bid)
_hist_ask = defaultdict(lambda: deque(maxlen=SMA_WINDOW))  # serie para comprar (R_ask)
_hist_mid = defaultdict(lambda: deque(maxlen=SMA_WINDOW))  # serie mid (para z/vol)

# ---------------------------------- Helpers ----------------------------------
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

def _boll(values):
    """Devuelve (mean, upper, lower) con 2σ. Con <2 datos no hay bandas."""
    n = len(values)
    if n == 0:
        return (None, None, None)
    m = mean(values)
    if n < 2:
        return (m, None, None)
    s = pstdev(values)
    return (m, m + 2*s, m - 2*s)

def _now_utc_iso():
    # ISO con zona explícita +00:00, evita ambigüedad en timestamptz
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

# ---------------------------------- Core -------------------------------------
def periodic_ratios_job():
    print(f">> [ratios_worker] Arrancando job cada {INTERVAL_SECONDS}s")
    if supabase is None:
        print("[ratios_worker] ADVERTENCIA: supabase no disponible -> dry-run")

    while True:
        try:
            # 1) Leer pares a procesar
            pairs = []
            if supabase:
                try:
                    res = supabase.table("terminal_ratio_pairs").select(
                        "user_id,client_id,base_symbol,quote_symbol"
                    ).execute()
                    pairs = res.data or []
                except Exception as e:
                    print(f"[ratios_worker] Error consultando terminal_ratio_pairs: {e}")
                    pairs = []
            else:
                time.sleep(INTERVAL_SECONDS)
                continue

            # 2) Procesar cada par
            for pair in pairs:
                user_id     = pair.get("user_id")
                client_id   = pair.get("client_id")
                base_symbol  = (pair.get("base_symbol")  or "").strip()
                quote_symbol = (pair.get("quote_symbol") or "").strip()

                if not (user_id and client_id and base_symbol and quote_symbol):
                    if VERBOSE:
                        print(f"[ratios_worker] Par inválido/ incompleto: {pair}")
                    continue

                base  = quotes_cache.get(base_symbol,  {})
                quote = quotes_cache.get(quote_symbol, {})

                A_bid  = base.get("bid");   A_ask  = base.get("offer")
                B_bid  = quote.get("bid");  B_ask  = quote.get("offer")

                # Ratios execution-aware
                bid_ratio = _safe_div(A_bid, B_ask)   # vender ratio ahora
                ask_ratio = _safe_div(A_ask, B_bid)   # comprar ratio ahora

                # Ratio mid (para medir desvíos/volatilidad)
                mid_ratio = None
                if all(_is_num(x) for x in (A_bid, A_ask, B_bid, B_ask)):
                    mid_A = (float(A_bid) + float(A_ask)) / 2.0
                    mid_B = (float(B_bid) + float(B_ask)) / 2.0
                    mid_ratio = _safe_div(mid_A, mid_B)

                # Requisitos mínimos
                if bid_ratio is None or ask_ratio is None or mid_ratio is None:
                    if VERBOSE:
                        print(f"[ratios_worker] Datos incompletos {base_symbol}/{quote_symbol}")
                    continue

                key = (base_symbol, quote_symbol)
                _hist_bid[key].append(bid_ratio)
                _hist_ask[key].append(ask_ratio)
                _hist_mid[key].append(mid_ratio)

                # Bandas/SMA sobre series de ejecución
                sma180_bid,   bb180_bid_upper,   bb180_bid_lower = _boll(_hist_bid[key])
                sma180_ask,   bb180_ask_upper,   bb180_ask_lower = _boll(_hist_ask[key])

                # Stats sobre MID (para z-score y régimen)
                mid_vals   = list(_hist_mid[key])
                sma180_mid = mean(mid_vals) if len(mid_vals) >= 1 else None
                std180_mid = pstdev(mid_vals) if len(mid_vals) >= 2 else None
                last60     = mid_vals[-STD_SHORT_WINDOW:]
                std60_mid  = pstdev(last60) if len(last60) >= 2 else None

                vol_ratio       = (std60_mid / std180_mid) if (std60_mid not in (None, 0) and std180_mid not in (None, 0)) else None
                bb180_mid_upper = (sma180_mid + 2*std180_mid) if (sma180_mid is not None and std180_mid is not None) else None
                bb180_mid_lower = (sma180_mid - 2*std180_mid) if (sma180_mid is not None and std180_mid is not None) else None

                ratio_spread = (ask_ratio - bid_ratio) if (_is_num(ask_ratio) and _is_num(bid_ratio)) else None
                z_bid = ((bid_ratio - sma180_mid) / std60_mid) if (sma180_mid is not None and std60_mid not in (None, 0)) else None
                z_ask = ((ask_ratio - sma180_mid) / std60_mid) if (sma180_mid is not None and std60_mid not in (None, 0)) else None

                # 3) Insert en DB
                if supabase:
                    row = {
                        "user_id":       user_id,
                        "client_id":     client_id,
                        "base_symbol":   base_symbol,
                        "quote_symbol":  quote_symbol,
                        "asof":          _now_utc_iso(),  # o podés omitir y usar DEFAULT now()

                        # Ratios execution-aware
                        "bid_ratio": float(bid_ratio),
                        "ask_ratio":  float(ask_ratio),

                        # Precios crudos (auditoría)
                        "bid_price_base":    float(A_bid)  if _is_num(A_bid)  else None,
                        "bid_price_quote":   float(B_bid)  if _is_num(B_bid)  else None,
                        "offer_price_base":  float(A_ask)  if _is_num(A_ask)  else None,  # mantiene nombre histórico
                        "offer_price_quote": float(B_ask)  if _is_num(B_ask)  else None,

                        # Bandas/SMA en execution series (nota: "offer" = ask-series)
                        "sma180_bid":         float(sma180_bid)        if _is_num(sma180_bid)        else None,
                        "sma180_offer":       float(sma180_ask)        if _is_num(sma180_ask)        else None,
                        "bb180_bid_upper":    float(bb180_bid_upper)   if _is_num(bb180_bid_upper)   else None,
                        "bb180_bid_lower":    float(bb180_bid_lower)   if _is_num(bb180_bid_lower)   else None,
                        "bb180_offer_upper":  float(bb180_ask_upper)   if _is_num(bb180_ask_upper)   else None,
                        "bb180_offer_lower":  float(bb180_ask_lower)   if _is_num(bb180_ask_lower)   else None,

                        # Métricas extendidas (tu tabla ya las tiene)
                        "mid_ratio":        float(mid_ratio),
                        "sma180_mid":       float(sma180_mid)   if _is_num(sma180_mid)   else None,
                        "std60_mid":        float(std60_mid)    if _is_num(std60_mid)    else None,
                        "std180_mid":       float(std180_mid)   if _is_num(std180_mid)   else None,
                        "z_bid":            float(z_bid)        if _is_num(z_bid)        else None,
                        "z_ask":            float(z_ask)        if _is_num(z_ask)        else None,
                        "ratio_spread":     float(ratio_spread) if _is_num(ratio_spread) else None,
                        "vol_ratio":        float(vol_ratio)    if _is_num(vol_ratio)    else None,
                        "bb180_mid_upper":  float(bb180_mid_upper) if _is_num(bb180_mid_upper) else None,
                        "bb180_mid_lower":  float(bb180_mid_lower) if _is_num(bb180_mid_lower) else None,
                    }

                    if LOG_INSERT_COLUMNS:
                        print("[ratios_worker] insert columns:", sorted(row.keys()))

                    try:
                        supabase.table("terminal_ratios_history").insert(row).execute()
                        if VERBOSE:
                            print(f"[ratios_worker] {base_symbol}/{quote_symbol} "
                                  f"R_bid={bid_ratio:.6f} R_ask={ask_ratio:.6f} mid={mid_ratio:.6f}")
                    except Exception as e:
                        # Intentamos mostrar detalle de Supabase si existe
                        detail = None
                        try:
                            detail = getattr(e, "response", None)
                            if detail is not None:
                                detail = detail.text
                        except Exception:
                            pass
                        print(f"[ratios_worker] Error insertando terminal_ratios_history: {e}")
                        if detail:
                            print(f"[ratios_worker] Detail: {detail}")

        except Exception as loop_e:
            print(f"[ratios_worker] EXCEPCIÓN en loop: {loop_e}")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    periodic_ratios_job()
