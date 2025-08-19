#!/usr/bin/env python3
# Script simple para probar el bot de Telegram

import requests
import json

def test_bot():
    print("🤖 PROBANDO BOT DE TELEGRAM")
    print("=" * 50)
    
    # Probar endpoint de salud
    try:
        response = requests.get("http://127.0.0.1:8000/cotizaciones/health")
        if response.status_code == 200:
            print("✅ API funcionando correctamente")
        else:
            print(f"❌ API error: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ No se puede conectar a la API: {e}")
        return
    
    # Probar endpoint de estado
    try:
        response = requests.get("http://127.0.0.1:8000/cotizaciones/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Estado del servicio: {data.get('worker_status', 'desconocido')}")
        else:
            print(f"❌ Error obteniendo estado: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎯 Ahora puedes probar el bot en Telegram:")
    print("1. Envía /ping al bot")
    print("2. Envía /start con tus datos JSON")
    print("3. Verifica que responda correctamente")

if __name__ == "__main__":
    test_bot()
