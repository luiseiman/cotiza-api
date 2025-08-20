#!/usr/bin/env python3
"""
Script para probar la conexión WebSocket del bot de cotizaciones.
"""

import asyncio
import websockets
import json
import time

async def test_websocket():
    """Prueba la conexión WebSocket"""
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    print(f"🔌 Conectando a WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conexión WebSocket establecida")
            
            # Enviar mensaje de ping
            ping_message = {
                "type": "ping",
                "timestamp": time.time()
            }
            print(f"📤 Enviando ping: {ping_message}")
            await websocket.send(json.dumps(ping_message))
            
            # Recibir respuesta
            response = await websocket.recv()
            print(f"📥 Respuesta recibida: {response}")
            
            # Suscribirse a cotizaciones
            subscribe_message = {
                "type": "subscribe",
                "instruments": ["GGAL", "PAMP", "YPF"],
                "timestamp": time.time()
            }
            print(f"📤 Suscribiéndose: {subscribe_message}")
            await websocket.send(json.dumps(subscribe_message))
            
            # Recibir confirmación
            response = await websocket.recv()
            print(f"📥 Confirmación: {response}")
            
            # Mantener conexión activa por un momento
            print("⏳ Manteniendo conexión activa por 5 segundos...")
            await asyncio.sleep(5)
            
            print("✅ Prueba completada exitosamente")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ Conexión rechazada. ¿Está la API ejecutándose?")
        print("💡 Ejecuta: uvicorn main:app --host 127.0.0.1 --port 8000")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Error de estado HTTP: {e}")
        if e.status_code == 403:
            print("🔒 Error 403: Acceso prohibido")
            print("💡 Verifica la configuración de CORS y autenticación")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print(f"💡 Tipo de error: {type(e).__name__}")

def test_http_endpoints():
    """Prueba los endpoints HTTP relacionados"""
    import requests
    
    base_url = "http://localhost:8000"
    
    print("\n🌐 Probando endpoints HTTP:")
    
    # Health check
    try:
        response = requests.get(f"{base_url}/cotizaciones/health")
        print(f"✅ Health: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Health: {e}")
    
    # WebSocket status
    try:
        response = requests.get(f"{base_url}/cotizaciones/websocket_status")
        print(f"✅ WebSocket status: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ WebSocket status: {e}")
    
    # Telegram locks status
    try:
        response = requests.get(f"{base_url}/cotizaciones/telegram_locks_status")
        print(f"✅ Telegram locks: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Telegram locks: {e}")

def main():
    """Función principal"""
    print("🧪 PRUEBA DE WEBSOCKET Y ENDPOINTS")
    print("=" * 50)
    
    # Probar endpoints HTTP primero
    test_http_endpoints()
    
    print("\n" + "=" * 50)
    
    # Probar WebSocket
    asyncio.run(test_websocket())
    
    print("\n" + "=" * 50)
    print("🏁 Prueba completada")

if __name__ == "__main__":
    main()
