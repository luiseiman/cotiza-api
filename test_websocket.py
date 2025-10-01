#!/usr/bin/env python3
"""
Script de prueba para el WebSocket del dashboard.
"""

import asyncio
import websockets
import json
from datetime import datetime


async def test_websocket():
    """Prueba el WebSocket del dashboard."""
    uri = "ws://localhost:8000/ws/dashboard"
    
    try:
        print("🔌 Conectando al WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado exitosamente")
            
            # Enviar ping
            ping_msg = {"action": "ping"}
            await websocket.send(json.dumps(ping_msg))
            print("📡 Ping enviado")
            
            # Recibir respuesta del ping
            response = await websocket.recv()
            ping_response = json.loads(response)
            print(f"📡 Pong recibido: {ping_response}")
            
            # Solicitar estado
            status_msg = {"action": "get_status"}
            await websocket.send(json.dumps(status_msg))
            print("📊 Estado solicitado")
            
            # Recibir datos por 30 segundos (3 actualizaciones)
            for i in range(3):
                print(f"\n⏱️  Esperando actualización {i+1}/3...")
                
                try:
                    # Esperar datos con timeout
                    data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    parsed_data = json.loads(data)
                    
                    if parsed_data.get("status") == "success":
                        print(f"✅ Datos recibidos:")
                        print(f"   📊 Registros: {parsed_data.get('count', 0)}")
                        print(f"   ⚡ Tiempo query: {parsed_data.get('query_time_ms', 0)}ms")
                        print(f"   🕒 Timestamp: {parsed_data.get('timestamp', 'N/A')}")
                        print(f"   🔄 Método: {parsed_data.get('method', 'N/A')}")
                        
                        # Mostrar algunos ejemplos
                        if parsed_data.get('data') and len(parsed_data['data']) > 0:
                            print(f"   📝 Primer registro:")
                            first_record = parsed_data['data'][0]
                            print(f"      Par: {first_record.get('par', 'N/A')}")
                            print(f"      Client ID: {first_record.get('client_id_result', 'N/A')}")
                            print(f"      Último ratio: {first_record.get('ultimo_ratio_operado', 'N/A')}")
                    else:
                        print(f"❌ Error en datos: {parsed_data.get('error', 'Unknown error')}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout esperando datos")
                    break
                except Exception as e:
                    print(f"❌ Error recibiendo datos: {e}")
                    break
                    
            print("\n🔌 Desconectando...")
            
    except ConnectionRefusedError:
        print("❌ Error: No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor esté corriendo en localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🧪 Prueba del WebSocket del Dashboard")
    print("=" * 50)
    asyncio.run(test_websocket())