#!/usr/bin/env python3
"""
Simulador simple de datos de mercado.
"""

import time
from quotes_cache import quotes_cache

def llenar_cache():
    """Llena el cache con datos simulados."""
    print("📊 Llenando cache con datos simulados...")
    
    # Datos para los símbolos principales
    datos = {
        "MERV - XMEV - TX26 - 24hs": {
            "last": 100.50,
            "bid": 100.45,
            "offer": 100.55,
            "bid_size": 1000,
            "offer_size": 1000,
            "timestamp": time.time()
        },
        "MERV - XMEV - TX28 - 24hs": {
            "last": 105.80,
            "bid": 105.75,
            "offer": 105.85,
            "bid_size": 1200,
            "offer_size": 1200,
            "timestamp": time.time()
        },
        "MERV - XMEV - AE38 - 24hs": {
            "last": 85.20,
            "bid": 85.15,
            "offer": 85.25,
            "bid_size": 800,
            "offer_size": 800,
            "timestamp": time.time()
        },
        "MERV - XMEV - GD41 - 24hs": {
            "last": 120.50,
            "bid": 120.45,
            "offer": 120.55,
            "bid_size": 1500,
            "offer_size": 1500,
            "timestamp": time.time()
        }
    }
    
    # Llenar el cache
    for symbol, data in datos.items():
        quotes_cache[symbol] = data
        print(f"✅ {symbol}: last={data['last']}, bid={data['bid']}, offer={data['offer']}")
    
    print(f"📊 Cache llenado: {len(quotes_cache)} símbolos")
    return datos

if __name__ == "__main__":
    llenar_cache()
    print("\n🎯 Cache listo para el worker!")
