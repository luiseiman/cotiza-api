#!/usr/bin/env python3
"""
Cliente de prueba simple para WebSocket
"""

import asyncio
import websockets
import json

async def test_simple_ws():
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 Conectado al WebSocket")
            
            # Recibir mensaje de bienvenida
            welcome_msg = await websocket.recv()
            print(f"📨 Bienvenida: {welcome_msg}")
            
            # Enviar mensaje simple
            test_msg = {"type": "ping"}
            await websocket.send(json.dumps(test_msg))
            print("📤 Mensaje enviado")
            
            # Esperar respuesta
            response = await websocket.recv()
            print(f"📥 Respuesta: {response}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_simple_ws())
