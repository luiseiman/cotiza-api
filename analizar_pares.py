#!/usr/bin/env python3
"""
Script para analizar qué pares están disponibles y cuáles tienen datos en el cache.
"""

from supabase_client import get_active_pairs
from quotes_cache import quotes_cache

def analizar_situacion():
    """Analiza la situación actual de pares y datos."""
    print("🔍 ANALIZANDO SITUACIÓN ACTUAL")
    print("=" * 60)
    
    # 1. Obtener pares disponibles
    print("📋 Obteniendo pares de la base de datos...")
    pairs = get_active_pairs()
    print(f"✅ Pares encontrados: {len(pairs)}")
    
    # 2. Analizar cada par
    pares_con_datos = []
    pares_sin_datos = []
    
    for i, pair in enumerate(pairs):
        base_symbol = pair["base_symbol"]
        quote_symbol = pair["quote_symbol"]
        
        base_data = quotes_cache.get(base_symbol)
        quote_data = quotes_cache.get(quote_symbol)
        
        if base_data and quote_data:
            pares_con_datos.append({
                "par": pair,
                "base_data": base_data,
                "quote_data": quote_data
            })
        else:
            pares_sin_datos.append({
                "par": pair,
                "base_missing": not base_data,
                "quote_missing": not quote_data
            })
    
    # 3. Mostrar resultados
    print(f"\n📊 RESUMEN:")
    print(f"   Pares CON datos: {len(pares_con_datos)}")
    print(f"   Pares SIN datos: {len(pares_sin_datos)}")
    
    # 4. Mostrar pares con datos
    if pares_con_datos:
        print(f"\n✅ PARES CON DATOS COMPLETOS:")
        for i, item in enumerate(pares_con_datos[:3]):  # Solo mostrar los primeros 3
            pair = item["par"]
            base_data = item["base_data"]
            quote_data = item["quote_data"]
            
            print(f"   {i+1}. {pair['base_symbol']} / {pair['quote_symbol']}")
            print(f"      Base: last={base_data.get('last')}, bid={base_data.get('bid')}, offer={base_data.get('offer')}")
            print(f"      Quote: last={quote_data.get('last')}, bid={quote_data.get('bid')}, offer={quote_data.get('offer')}")
    
    # 5. Mostrar pares sin datos
    if pares_sin_datos:
        print(f"\n❌ PARES SIN DATOS:")
        for i, item in enumerate(pares_sin_datos[:5]):  # Solo mostrar los primeros 5
            pair = item["par"]
            print(f"   {i+1}. {pair['base_symbol']} / {pair['quote_symbol']}")
            if item["base_missing"]:
                print(f"      ❌ Falta: {pair['base_symbol']}")
            if item["quote_missing"]:
                print(f"      ❌ Falta: {pair['quote_symbol']}")
    
    # 6. Mostrar símbolos en cache
    print(f"\n💾 SÍMBOLOS EN CACHE:")
    if quotes_cache:
        for symbol in list(quotes_cache.keys())[:5]:  # Solo mostrar los primeros 5
            data = quotes_cache[symbol]
            print(f"   ✅ {symbol}: last={data.get('last')}, bid={data.get('bid')}, offer={data.get('offer')}")
    else:
        print("   ❌ Cache vacío")
    
    return pares_con_datos, pares_sin_datos

def simular_datos_faltantes():
    """Simula datos para los símbolos que faltan."""
    print(f"\n🔧 SIMULANDO DATOS FALTANTES...")
    
    # Obtener todos los símbolos únicos de los pares
    pairs = get_active_pairs()
    symbols_needed = set()
    
    for pair in pairs:
        symbols_needed.add(pair["base_symbol"])
        symbols_needed.add(pair["quote_symbol"])
    
    # Simular datos para símbolos que no están en cache
    symbols_added = 0
    for symbol in symbols_needed:
        if symbol not in quotes_cache:
            # Generar datos simulados realistas
            import random
            precio_base = random.uniform(80, 130)
            
            quotes_cache[symbol] = {
                "last": round(precio_base, 2),
                "bid": round(precio_base * 0.999, 2),
                "offer": round(precio_base * 1.001, 2),
                "bid_size": random.randint(500, 2000),
                "offer_size": random.randint(500, 2000),
                "timestamp": time.time()
            }
            symbols_added += 1
            print(f"   ✅ {symbol}: last={quotes_cache[symbol]['last']}")
    
    print(f"📊 Símbolos agregados: {symbols_added}")
    print(f"📊 Total en cache: {len(quotes_cache)} símbolos")

if __name__ == "__main__":
    import time
    
    # Analizar situación actual
    pares_con_datos, pares_sin_datos = analizar_situacion()
    
    # Simular datos faltantes si es necesario
    if pares_sin_datos:
        simular_datos_faltantes()
        
        # Analizar nuevamente
        print(f"\n🔄 ANALIZANDO DESPUÉS DE SIMULACIÓN...")
        analizar_situacion()
    
    print(f"\n🎯 ANÁLISIS COMPLETADO")
