#!/usr/bin/env python3
"""
Script simplificado para probar conectividad básica
"""

import requests
import json
import time
from datetime import datetime

def test_basic_connectivity():
    """Prueba conectividad básica sin dependencias externas"""
    print("🔍 PRUEBA DE CONECTIVIDAD BÁSICA")
    print("=" * 50)
    
    # 1. Probar endpoint de salud
    print("1. Probando endpoint de salud...")
    try:
        response = requests.get("http://127.0.0.1:8000/cotizaciones/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Servidor respondiendo: {data}")
        else:
            print(f"⚠️ Servidor respondió con código: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Servidor no está ejecutándose en puerto 8000")
        print("💡 Para iniciar el servidor ejecute:")
        print("   uvicorn main:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("-" * 30)
    
    # 2. Probar endpoint de estado
    print("2. Probando endpoint de estado...")
    try:
        response = requests.get("http://127.0.0.1:8000/cotizaciones/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Estado obtenido: {json.dumps(data, indent=2)}")
        else:
            print(f"⚠️ Estado respondió con código: {response.status_code}")
    except Exception as e:
        print(f"❌ Error obteniendo estado: {e}")
    
    print("-" * 30)
    
    # 3. Probar WebSocket status
    print("3. Probando estado de WebSocket...")
    try:
        response = requests.get("http://127.0.0.1:8000/cotizaciones/websocket_status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WebSocket status: {json.dumps(data, indent=2)}")
        else:
            print(f"⚠️ WebSocket status respondió con código: {response.status_code}")
    except Exception as e:
        print(f"❌ Error obteniendo WebSocket status: {e}")
    
    print("-" * 30)
    
    # 4. Probar endpoint de diagnóstico de Telegram
    print("4. Probando diagnóstico de Telegram...")
    try:
        response = requests.get("http://127.0.0.1:8000/cotizaciones/telegram_diag", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Telegram diagnóstico: {json.dumps(data, indent=2)}")
        else:
            print(f"⚠️ Telegram diagnóstico respondió con código: {response.status_code}")
    except Exception as e:
        print(f"❌ Error obteniendo diagnóstico de Telegram: {e}")

if __name__ == "__main__":
    test_basic_connectivity()

