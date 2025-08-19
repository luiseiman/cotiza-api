#!/usr/bin/env python3
"""
Simulador de datos de mercado que mantiene el cache lleno para que el worker pueda procesar.
"""

import time
import random
import threading
from quotes_cache import quotes_cache

# Símbolos que necesitamos simular basándonos en los pares de la base
SYMBOLS = [
    'MERV - XMEV - TX26 - 24hs',
    'MERV - XMEV - TX27 - 24hs', 
    'MERV - XMEV - TX28 - 24hs',
    'MERV - XMEV - AE38 - 24hs',
    'MERV - XMEV - GD41 - 24hs',
    'MERV - XMEV - AL41 - 24hs',
    'MERV - XMEV - AL30 - 24hs',
    'MERV - XMEV - GD30 - 24hs',
    'MERV - XMEV - AL29 - 24hs',
    'MERV - XMEV - GD29 - 24hs',
    'MERV - XMEV - GD38 - 24hs',
    'MERV - XMEV - GD46 - 24hs'
]

# Precios base para cada símbolo
PRECIOS_BASE = {
    'MERV - XMEV - TX26 - 24hs': 100.0,
    'MERV - XMEV - TX27 - 24hs': 95.0,
    'MERV - XMEV - TX28 - 24hs': 105.0,
    'MERV - XMEV - AE38 - 24hs': 85.0,
    'MERV - XMEV - GD41 - 24hs': 120.0,
    'MERV - XMEV - AL41 - 24hs': 110.0,
    'MERV - XMEV - AL30 - 24hs': 90.0,
    'MERV - XMEV - GD30 - 24hs': 115.0,
    'MERV - XMEV - AL29 - 24hs': 88.0,
    'MERV - XMEV - GD29 - 24hs': 112.0,
    'MERV - XMEV - GD38 - 24hs': 118.0,
    'MERV - XMEV - GD46 - 24hs': 125.0
}

def generar_precio_simulado(symbol: str, precio_base: float) -> dict:
    """Genera un precio simulado con variación realista."""
    # Variación aleatoria del precio base (±2%)
    variacion = random.uniform(-0.02, 0.02)
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

def actualizar_cache():
    """Actualiza el cache con datos simulados."""
    while True:
        try:
            for symbol in SYMBOLS:
                precio_base = PRECIOS_BASE[symbol]
                datos = generar_precio_simulado(symbol, precio_base)
                quotes_cache[symbol] = datos
                
            print(f"📊 Cache actualizado: {len(quotes_cache)} símbolos - {time.strftime('%H:%M:%S')}")
            
            # Esperar 5 segundos antes de la siguiente actualización
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Error actualizando cache: {e}")
            time.sleep(5)

def mostrar_estado_cache():
    """Muestra el estado actual del cache."""
    while True:
        try:
            print(f"\n🔍 ESTADO DEL CACHE ({time.strftime('%H:%M:%S')})")
            print("=" * 60)
            
            for symbol in SYMBOLS[:3]:  # Mostrar solo los primeros 3
                if symbol in quotes_cache:
                    data = quotes_cache[symbol]
                    print(f"✅ {symbol}:")
                    print(f"   Last: {data['last']}, Bid: {data['bid']}, Offer: {data['offer']}")
                    print(f"   Bid Size: {data['bid_size']}, Offer Size: {data['offer_size']}")
                else:
                    print(f"❌ {symbol}: Sin datos")
            
            print(f"📊 Total en cache: {len(quotes_cache)} símbolos")
            print("=" * 60)
            
            # Mostrar cada 30 segundos
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ Error mostrando estado: {e}")
            time.sleep(30)

def main():
    """Función principal del simulador."""
    print("🚀 INICIANDO SIMULADOR DE DATOS DE MERCADO")
    print("=" * 60)
    print("Este simulador mantendrá el cache lleno para que el worker pueda procesar")
    print("Los datos se actualizan cada 5 segundos")
    print("=" * 60)
    
    try:
        # Iniciar thread de actualización de cache
        cache_thread = threading.Thread(target=actualizar_cache, daemon=True)
        cache_thread.start()
        print("✅ Thread de actualización de cache iniciado")
        
        # Iniciar thread de monitoreo
        monitor_thread = threading.Thread(target=mostrar_estado_cache, daemon=True)
        monitor_thread.start()
        print("✅ Thread de monitoreo iniciado")
        
        print("\n⏳ Simulador ejecutándose... Presiona Ctrl+C para detener")
        
        # Mantener el programa principal vivo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulador detenido por el usuario")
    except Exception as e:
        print(f"❌ Error en simulador: {e}")

if __name__ == "__main__":
    main()
