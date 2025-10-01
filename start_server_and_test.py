#!/usr/bin/env python3
"""
Script para iniciar el servidor y probar el WebSocket automáticamente.
"""

import subprocess
import time
import requests
import asyncio
import websockets
import json
import threading
from datetime import datetime


def check_server_ready(url="http://localhost:8000", timeout=30):
    """Verifica si el servidor está listo."""
    print("🔄 Esperando que el servidor esté listo...")
    
    for i in range(timeout):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print("✅ Servidor listo!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"   ⏳ Intento {i+1}/{timeout}...")
        time.sleep(1)
    
    print("❌ Servidor no respondió en el tiempo esperado")
    return False


def start_server():
    """Inicia el servidor en un subprocess."""
    print("🚀 Iniciando servidor...")
    
    try:
        # Iniciar el servidor
        process = subprocess.Popen(
            ["python3", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"📡 Servidor iniciado con PID: {process.pid}")
        return process
        
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")
        return None


async def test_websocket():
    """Prueba el WebSocket."""
    uri = "ws://localhost:8000/ws/dashboard"
    
    try:
        print("\n🔌 Probando WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket conectado")
            
            # Enviar ping
            ping_msg = {"action": "ping"}
            await websocket.send(json.dumps(ping_msg))
            print("📡 Ping enviado")
            
            # Recibir respuesta
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📡 Respuesta: {data}")
            
            # Solicitar estado
            status_msg = {"action": "get_status"}
            await websocket.send(json.dumps(status_msg))
            print("📊 Estado solicitado")
            
            # Recibir estado
            status_response = await websocket.recv()
            status_data = json.loads(status_response)
            print(f"📊 Estado: {status_data}")
            
            # Esperar datos del dashboard
            print("⏱️  Esperando datos del dashboard...")
            dashboard_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
            dashboard_json = json.loads(dashboard_data)
            
            if dashboard_json.get("status") == "success":
                print(f"✅ Datos del dashboard recibidos:")
                print(f"   📊 Registros: {dashboard_json.get('count', 0)}")
                print(f"   ⚡ Tiempo: {dashboard_json.get('query_time_ms', 0)}ms")
                print(f"   🕒 Timestamp: {dashboard_json.get('timestamp', 'N/A')}")
            else:
                print(f"❌ Error en datos: {dashboard_json.get('error', 'Unknown')}")
                
    except asyncio.TimeoutError:
        print("⏰ Timeout esperando datos del dashboard")
    except Exception as e:
        print(f"❌ Error en WebSocket: {e}")


def main():
    """Función principal."""
    print("🧪 Iniciador y Probador de WebSocket")
    print("=" * 50)
    
    # 1. Iniciar servidor
    server_process = start_server()
    if not server_process:
        return
    
    try:
        # 2. Esperar que esté listo
        if not check_server_ready():
            return
        
        # 3. Probar WebSocket
        asyncio.run(test_websocket())
        
        print("\n🎉 Prueba completada!")
        print("📝 Ahora puedes:")
        print("   1. Ir a http://localhost:8000/ws-test en tu navegador")
        print("   2. Hacer clic en 'Conectar'")
        print("   3. Ver los datos en tiempo real")
        
        # Mantener el servidor corriendo
        print("\n⏸️  Presiona Ctrl+C para detener el servidor")
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo servidor...")
            server_process.terminate()
            server_process.wait()
            print("✅ Servidor detenido")
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor...")
        server_process.terminate()
        server_process.wait()
        print("✅ Servidor detenido")


if __name__ == "__main__":
    main()
