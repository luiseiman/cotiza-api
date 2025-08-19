#!/usr/bin/env python3
"""
Script de prueba para verificar que el bot de Telegram funcione correctamente.
"""

import os
import sys
import time
import requests

# Configuración
API_BASE = "http://127.0.0.1:8000"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID")

def test_api_health():
    """Prueba que la API esté funcionando"""
    print("🔍 Probando salud de la API...")
    try:
        # Usar el endpoint de estado en lugar del de salud
        response = requests.get(f"{API_BASE}/cotizaciones/status", timeout=5)
        if response.status_code == 200:
            print("✅ API funcionando correctamente")
            return True
        else:
            print(f"❌ API respondió con código {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando a la API: {e}")
        return False

def test_service_status():
    """Prueba el endpoint de estado"""
    print("\n🔍 Probando endpoint de estado...")
    try:
        response = requests.get(f"{API_BASE}/cotizaciones/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print("✅ Estado obtenido correctamente")
            print(f"   WebSocket: {status.get('ws', 'N/A')}")
            print(f"   Usuario: {status.get('user_id', 'N/A')}")
            print(f"   Suscriptos: {len(status.get('subscribed', []))}")
            return True
        else:
            print(f"❌ Estado respondió con código {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error obteniendo estado: {e}")
        return False

def test_telegram_bot():
    """Prueba que el bot de Telegram esté configurado"""
    print("\n🔍 Verificando configuración del bot...")
    
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN no configurado")
        return False
    
    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID no configurado")
        return False
    
    print("✅ Configuración del bot encontrada")
    print(f"   Token: {TELEGRAM_TOKEN[:10]}...")
    print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
    return True

def test_service_control():
    """Prueba el control del servicio"""
    print("\n🔍 Probando control del servicio...")
    
    # 1. Iniciar servicio
    print("   🚀 Iniciando servicio...")
    start_data = {
        "user": "24239211",
        "password": "test123",
        "account": "16557",
        "instrumentos": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
    }
    
    try:
        response = requests.post(f"{API_BASE}/cotizaciones/iniciar", json=start_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print("   ✅ Servicio iniciado correctamente")
            else:
                print(f"   ❌ Error al iniciar: {result.get('message', 'Error desconocido')}")
                return False
        else:
            print(f"   ❌ Error HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error al iniciar: {e}")
        return False
    
    # 2. Verificar estado
    time.sleep(2)
    print("   📊 Verificando estado...")
    try:
        response = requests.get(f"{API_BASE}/cotizaciones/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            if status.get("ws") == "ok":
                print("   ✅ Servicio confirmado como activo")
            else:
                print("   ❌ Servicio no se inició correctamente")
                return False
        else:
            print(f"   ❌ Error verificando estado: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error verificando estado: {e}")
        return False
    
    # 3. Detener servicio
    print("   🛑 Deteniendo servicio...")
    try:
        response = requests.post(f"{API_BASE}/cotizaciones/detener", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print("   ✅ Servicio detenido correctamente")
            else:
                print(f"   ❌ Error al detener: {result.get('message', 'Error desconocido')}")
                return False
        else:
            print(f"   ❌ Error HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error al detener: {e}")
        return False
    
    return True

def main():
    """Función principal de pruebas"""
    print("🤖 PRUEBAS DEL BOT DE TELEGRAM")
    print("=" * 50)
    
    # Verificar que la API esté corriendo
    if not test_api_health():
        print("\n❌ La API no está funcionando. Asegúrate de que esté corriendo en:")
        print(f"   {API_BASE}")
        print("\n💡 Para iniciar la API, ejecuta:")
        print("   uvicorn main:app --host 127.0.0.1 --port 8000")
        return False
    
    # Verificar configuración del bot
    if not test_telegram_bot():
        print("\n❌ El bot de Telegram no está configurado correctamente.")
        print("💡 Configura las variables de entorno:")
        print("   TELEGRAM_TOKEN=tu_token_aqui")
        print("   TELEGRAM_CHAT_ID=tu_chat_id_aqui")
        return False
    
    # Probar control del servicio
    if not test_service_control():
        print("\n❌ Las pruebas de control del servicio fallaron.")
        return False
    
    # Verificar estado final
    time.sleep(1)
    print("\n🔍 Verificando estado final...")
    try:
        response = requests.get(f"{API_BASE}/cotizaciones/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            if status.get("ws") != "ok":
                print("✅ Servicio correctamente detenido")
            else:
                print("❌ Servicio no se detuvo correctamente")
                return False
        else:
            print(f"❌ Error verificando estado final: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verificando estado final: {e}")
        return False
    
    print("\n🎉 ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    print("\n📱 Ahora puedes usar el bot de Telegram con estos comandos:")
    print("   /start - Iniciar el servicio")
    print("   /status - Ver estado del servicio")
    print("   /restart - Reiniciar el servicio")
    print("   /stop - Detener el servicio")
    print("   /help - Ver ayuda completa")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
