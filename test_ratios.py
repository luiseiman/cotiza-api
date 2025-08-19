#!/usr/bin/env python3
"""
Script de prueba para verificar que el worker de ratios funciona correctamente.
Simula datos de mercado en el cache y ejecuta el worker manualmente.
"""

import time
from quotes_cache import quotes_cache
from ratios_worker import start, stop
from supabase_client import get_active_pairs

def simular_datos_mercado():
    """Simula datos de mercado para probar el worker."""
    print("📊 Simulando datos de mercado...")
    
    # Simular datos para algunos símbolos comunes
    quotes_cache["MERV - XMEV - TX26 - 24hs"] = {
        "last": 100.50,
        "bid": 100.45,
        "offer": 100.55,
        "bid_size": 1000,
        "offer_size": 1000,
        "timestamp": time.time()
    }
    
    quotes_cache["MERV - XMEV - TX27 - 24hs"] = {
        "last": 95.20,
        "bid": 95.15,
        "offer": 95.25,
        "bid_size": 800,
        "offer_size": 800,
        "timestamp": time.time()
    }
    
    quotes_cache["MERV - XMEV - TX28 - 24hs"] = {
        "last": 105.80,
        "bid": 105.75,
        "offer": 105.85,
        "bid_size": 1200,
        "offer_size": 1200,
        "timestamp": time.time()
    }
    
    print(f"✅ Datos simulados en cache: {list(quotes_cache.keys())}")
    for symbol, data in quotes_cache.items():
        print(f"   {symbol}: last={data['last']}, bid={data['bid']}, offer={data['offer']}")

def verificar_pares():
    """Verifica que hay pares disponibles para procesar."""
    print("\n🔍 Verificando pares disponibles...")
    pairs = get_active_pairs()
    print(f"📋 Pares encontrados: {len(pairs)}")
    
    for i, pair in enumerate(pairs[:3]):  # Mostrar solo los primeros 3
        print(f"   Par {i+1}: {pair['base_symbol']} / {pair['quote_symbol']} (user_id: {pair.get('user_id')})")
    
    return pairs

def ejecutar_worker_manual():
    """Ejecuta el worker manualmente para procesar un ciclo."""
    print("\n⚙️ Ejecutando worker manualmente...")
    
    # Iniciar el worker
    start()
    
    # Esperar un poco para que procese
    print("⏳ Esperando 15 segundos para que el worker procese...")
    time.sleep(15)
    
    # Detener el worker
    stop()
    print("🛑 Worker detenido")

def main():
    """Función principal de prueba."""
    print("🚀 INICIANDO PRUEBA DEL WORKER DE RATIOS")
    print("=" * 50)
    
    try:
        # 1. Simular datos de mercado
        simular_datos_mercado()
        
        # 2. Verificar pares disponibles
        pairs = verificar_pares()
        
        if not pairs:
            print("❌ No hay pares disponibles para procesar")
            return
        
        # 3. Ejecutar worker manualmente
        ejecutar_worker_manual()
        
        print("\n✅ PRUEBA COMPLETADA")
        print("📊 Verifica en la base de datos si se guardaron los ratios")
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
