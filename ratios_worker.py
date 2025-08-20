import threading
import time
import random
import math
from collections import deque
from supabase_client import get_active_pairs, guardar_en_supabase, get_last_ratio_data
from quotes_cache import quotes_cache

_worker_thread = None
_stop_event = threading.Event()
_session_user = None
# Buffers de ventanas rodantes por par (clave: (base, quote, user))
_rolling = {}


def set_session(user_id: str):
    global _session_user
    _session_user = user_id


def obtener_datos_mercado(symbol: str) -> dict | None:
    """Devuelve datos solo si hay al menos un precio válido; si no, None."""
    datos = quotes_cache.get(symbol)
    if not datos:
        return None
    if any(datos.get(k) is not None for k in ("last", "bid", "offer")):
        return datos
    return None


def _worker_loop():
    while not _stop_event.is_set():
        try:
            # Obtener todos los pares activos (sin filtrar por user_id específico)
            pairs = get_active_pairs()
            print(f"[ratios_worker] pares activos={len(pairs)}")

            for pair in pairs:
                # Debug: mostrar la estructura del par
                if len(pairs) > 0 and pairs.index(pair) == 0:
                    print(f"[ratios_worker] Estructura del primer par: {list(pair.keys())}")
                
                # Obtener datos de mercado (del cache o simulados)
                base = obtener_datos_mercado(pair["base_symbol"])
                quote = obtener_datos_mercado(pair["quote_symbol"])
                
                # Debug: mostrar qué datos están disponibles
                if len(pairs) > 0 and pairs.index(pair) == 0:
                    print(f"[ratios_worker] Datos para {pair['base_symbol']}: {base}")
                    print(f"[ratios_worker] Datos para {pair['quote_symbol']}: {quote}")
                
                if not base or not quote:
                    print(f"[ratios_worker] ❌ No se pudieron obtener datos para {pair['base_symbol']} o {pair['quote_symbol']}")
                    continue

                ratio = None
                bid_ratio = None
                ask_ratio = None
                
                # Calcular diferentes tipos de ratios
                if base.get("last") and quote.get("last"):
                    ratio = base["last"] / quote["last"]
                    print(f"[ratios_worker] ✅ mid_ratio calculado: {base['last']} / {quote['last']} = {ratio}")
                
                if base.get("bid") and quote.get("bid"):
                    bid_ratio = base["bid"] / quote["bid"]
                    print(f"[ratios_worker] ✅ bid_ratio calculado: {base['bid']} / {quote['bid']} = {bid_ratio}")
                
                if base.get("offer") and quote.get("offer"):
                    ask_ratio = base["offer"] / quote["offer"]
                    print(f"[ratios_worker] ✅ ask_ratio calculado: {base['offer']} / {quote['offer']} = {ask_ratio}")
                
                # Solo continuar si hay al menos un ratio válido
                if not any([ratio, bid_ratio, ask_ratio]):
                    print(f"[ratios_worker] ❌ No se pudo calcular ningún ratio")
                    continue

                # Actualizar buffers rodantes
                user_id_key = pair.get("user_id") or pair.get("client_id") or _session_user or "default"
                key = (pair["base_symbol"], pair["quote_symbol"], user_id_key)
                buf = _rolling.get(key)
                if buf is None:
                    buf = {
                        "mid": deque(maxlen=180),
                        "bid": deque(maxlen=180),
                        "ask": deque(maxlen=180),
                    }
                    _rolling[key] = buf
                if ratio is not None:
                    buf["mid"].append(ratio)
                if bid_ratio is not None:
                    buf["bid"].append(bid_ratio)
                if ask_ratio is not None:
                    buf["ask"].append(ask_ratio)

                def _sma_last(values: deque, window: int):
                    if not values:
                        return None
                    n = min(len(values), window)
                    sub = list(values)[-n:]
                    return (sum(sub) / n) if n > 0 else None

                def _std_last(values: deque, window: int):
                    if not values:
                        return None
                    sub = list(values)[-min(len(values), window):]
                    n = len(sub)
                    if n < 2:
                        return 0.0
                    mean = sum(sub) / n
                    var = sum((x - mean) ** 2 for x in sub) / n
                    return math.sqrt(var)

                # Calcular indicadores con ventanas
                mid_sma180 = _sma_last(buf["mid"], 180)
                mid_std60 = _std_last(buf["mid"], 60)
                mid_std180 = _std_last(buf["mid"], 180)
                bid_sma180 = _sma_last(buf["bid"], 180)
                bid_std180 = _std_last(buf["bid"], 180)
                ask_sma180 = _sma_last(buf["ask"], 180)
                ask_std180 = _std_last(buf["ask"], 180)

                # Obtener datos históricos del último registro para reutilizar valores calculados
                historical_data = get_last_ratio_data(
                    pair["base_symbol"], 
                    pair["quote_symbol"], 
                    pair.get("user_id")
                )
                
                if historical_data:
                    print(f"[ratios_worker] 📊 Datos históricos encontrados, reutilizando valores calculados")
                else:
                    print(f"[ratios_worker] ⚠️ No hay datos históricos, algunos campos serán NULL")

                # Construir row según la estructura real de la tabla
                # Manejar el caso cuando no hay user_id en el par
                user_id = user_id_key
                
                row = {
                    "user_id": user_id,  # ✅ user_id del par o fallback
                    "client_id": pair.get("client_id", user_id),  # Usar user_id como fallback
                    "base_symbol": pair["base_symbol"],
                    "quote_symbol": pair["quote_symbol"],
                    "asof": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    # Ratios calculados en tiempo real
                    "mid_ratio": ratio,
                    "bid_ratio": bid_ratio,
                    "ask_ratio": ask_ratio,
                    # Campos opcionales que podrían estar disponibles
                    "bid_price_base": base.get("bid"),
                    "bid_price_quote": quote.get("bid"),
                    "offer_price_base": base.get("offer"),
                    "offer_price_quote": quote.get("offer"),
                    "bid_size_base": base.get("bid_size"),
                    "bid_size_quote": quote.get("bid_size"),
                    "offer_size_base": base.get("offer_size"),
                    "offer_size_quote": quote.get("offer_size"),
                    # Indicadores calculados (fallback a historicos si faltan)
                    "sma180_bid": bid_sma180 if bid_sma180 is not None else (historical_data.get("sma180_bid") if historical_data else None),
                    "sma180_offer": ask_sma180 if ask_sma180 is not None else (historical_data.get("sma180_offer") if historical_data else None),
                    "sma180_mid": mid_sma180 if mid_sma180 is not None else (historical_data.get("sma180_mid") if historical_data else None),
                    "std60_mid": mid_std60 if mid_std60 is not None else (historical_data.get("std60_mid") if historical_data else None),
                    "std180_mid": mid_std180 if mid_std180 is not None else (historical_data.get("std180_mid") if historical_data else None),
                }

                # Bollinger y z
                bb_bid_upper = bb_bid_lower = bb_ask_upper = bb_ask_lower = None
                bb_mid_upper = bb_mid_lower = None
                z_bid_val = z_ask_val = None
                if bid_sma180 is not None and bid_std180 is not None:
                    bb_bid_upper = bid_sma180 + 2 * bid_std180
                    bb_bid_lower = bid_sma180 - 2 * bid_std180
                    if bid_ratio is not None and bid_std180 > 0:
                        z_bid_val = (bid_ratio - bid_sma180) / bid_std180
                if ask_sma180 is not None and ask_std180 is not None:
                    bb_ask_upper = ask_sma180 + 2 * ask_std180
                    bb_ask_lower = ask_sma180 - 2 * ask_std180
                    if ask_ratio is not None and ask_std180 > 0:
                        z_ask_val = (ask_ratio - ask_sma180) / ask_std180
                if mid_sma180 is not None and mid_std180 is not None:
                    bb_mid_upper = mid_sma180 + 2 * mid_std180
                    bb_mid_lower = mid_sma180 - 2 * mid_std180

                row.update({
                    "bb180_bid_upper": bb_bid_upper if bb_bid_upper is not None else (historical_data.get("bb180_bid_upper") if historical_data else None),
                    "bb180_bid_lower": bb_bid_lower if bb_bid_lower is not None else (historical_data.get("bb180_bid_lower") if historical_data else None),
                    "bb180_offer_upper": bb_ask_upper if bb_ask_upper is not None else (historical_data.get("bb180_offer_upper") if historical_data else None),
                    "bb180_offer_lower": bb_ask_lower if bb_ask_lower is not None else (historical_data.get("bb180_offer_lower") if historical_data else None),
                    "bb180_mid_upper": bb_mid_upper if bb_mid_upper is not None else (historical_data.get("bb180_mid_upper") if historical_data else None),
                    "bb180_mid_lower": bb_mid_lower if bb_mid_lower is not None else (historical_data.get("bb180_mid_lower") if historical_data else None),
                    "z_bid": z_bid_val if z_bid_val is not None else (historical_data.get("z_bid") if historical_data else None),
                    "z_ask": z_ask_val if z_ask_val is not None else (historical_data.get("z_ask") if historical_data else None),
                    "ratio_spread": (ask_ratio - bid_ratio) if (ask_ratio is not None and bid_ratio is not None) else (historical_data.get("ratio_spread") if historical_data else None),
                    "vol_ratio": historical_data.get("vol_ratio") if historical_data else None,
                })
                
                # Solo guardar si hay al menos un ratio válido
                if any([ratio, bid_ratio, ask_ratio]):
                    try:
                        result = guardar_en_supabase("terminal_ratios_history", row)
                        if result is None:
                            print(f"[ratios_worker] Error al guardar ratio en terminal_ratios_history")
                        else:
                            print(f"[ratios_worker] ✅ Ratio guardado exitosamente")
                    except Exception as e:
                        print(f"[ratios_worker] error guardando ratio: {e}")
                else:
                    print(f"[ratios_worker] ⚠️ No hay ratios válidos para guardar")
        except Exception as e:
            print(f"[ratios_worker] error en loop: {e}")

        time.sleep(10)


def start():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    print("[ratios_worker] Worker iniciado - procesando todos los pares activos (solo datos reales)")


def stop():
    _stop_event.set()