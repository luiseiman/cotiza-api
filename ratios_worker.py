import threading
import time
import random
from supabase_client import get_active_pairs, guardar_en_supabase, get_last_ratio_data
from quotes_cache import quotes_cache

_worker_thread = None
_stop_event = threading.Event()
_session_user = None


def set_session(user_id: str):
    global _session_user
    _session_user = user_id


def generar_datos_simulados(symbol: str) -> dict:
    """Genera datos simulados para un símbolo cuando no están disponibles en el cache."""
    # Precios base realistas para diferentes tipos de instrumentos
    precios_base = {
        'TX': 100.0,  # Futuros de tasa
        'AE': 85.0,   # Acciones argentinas
        'GD': 120.0,  # Bonos en dólares
        'AL': 90.0    # Acciones latinoamericanas
    }
    
    # Determinar el tipo de instrumento basándose en el símbolo
    precio_base = 100.0  # Default
    for tipo, precio in precios_base.items():
        if tipo in symbol:
            precio_base = precio
            break
    
    # Generar variación realista (±3%)
    variacion = random.uniform(-0.03, 0.03)
    precio_actual = precio_base * (1 + variacion)
    
    # Generar bid y offer con spread realista
    spread = precio_actual * 0.001  # 0.1% de spread
    bid = precio_actual - spread/2
    offer = precio_actual + spread/2
    
    # Tamaños de orden realistas
    bid_size = random.randint(500, 2000)
    offer_size = random.randint(500, 2000)
    
    return {
        "last": round(precio_actual, 2),
        "bid": round(bid, 2),
        "offer": round(offer, 2),
        "bid_size": bid_size,
        "offer_size": offer_size,
        "timestamp": time.time()
    }


def obtener_datos_mercado(symbol: str) -> dict:
    """Obtiene datos de mercado del cache o los genera simulados."""
    # Primero intentar obtener del cache
    datos = quotes_cache.get(symbol)
    
    if datos:
        return datos
    
    # Si no hay datos en cache, generar simulados
    print(f"[ratios_worker] 🔧 Generando datos simulados para {symbol}")
    datos_simulados = generar_datos_simulados(symbol)
    
    # Guardar en cache para futuras consultas
    quotes_cache[symbol] = datos_simulados
    
    return datos_simulados


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
                user_id = pair.get("user_id") or pair.get("client_id") or _session_user or "default"
                
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
                    # Campos históricos reutilizados (solo si están disponibles, NULL si no)
                    "sma180_bid": historical_data.get("sma180_bid") if historical_data else None,
                    "sma180_offer": historical_data.get("sma180_offer") if historical_data else None,
                    "bb180_bid_upper": historical_data.get("bb180_bid_upper") if historical_data else None,
                    "bb180_bid_lower": historical_data.get("bb180_bid_lower") if historical_data else None,
                    "bb180_offer_upper": historical_data.get("bb180_offer_upper") if historical_data else None,
                    "bb180_offer_lower": historical_data.get("bb180_offer_lower") if historical_data else None,
                    "sma180_mid": historical_data.get("sma180_mid") if historical_data else None,
                    "std60_mid": historical_data.get("std60_mid") if historical_data else None,
                    "std180_mid": historical_data.get("std180_mid") if historical_data else None,
                    "z_bid": historical_data.get("z_bid") if historical_data else None,
                    "z_ask": historical_data.get("z_ask") if historical_data else None,
                    "ratio_spread": historical_data.get("ratio_spread") if historical_data else None,
                    "vol_ratio": historical_data.get("vol_ratio") if historical_data else None,
                    "bb180_mid_upper": historical_data.get("bb180_mid_upper") if historical_data else None,
                    "bb180_mid_lower": historical_data.get("bb180_mid_lower") if historical_data else None
                }
                
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