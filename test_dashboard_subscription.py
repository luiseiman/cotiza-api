#!/usr/bin/env python3
"""
Cliente de prueba para suscripción automática al dashboard.
"""

import asyncio
import websockets
import json
from datetime import datetime


async def test_dashboard_subscription():
    """Prueba la suscripción automática al dashboard."""
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        print("🔌 Conectando al WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado exitosamente")
            
            # Recibir mensaje de bienvenida
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"📨 Bienvenida: {welcome_data.get('message', 'N/A')}")
            
            # Suscribirse al dashboard
            subscribe_msg = {"action": "dashboard_subscribe"}
            await websocket.send(json.dumps(subscribe_msg))
            print("📡 Suscripción al dashboard enviada")
            
            # Recibir confirmación de suscripción
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"✅ {response_data.get('message', 'Suscripción confirmada')}")
            
            # Recibir datos automáticos por 60 segundos
            print("\n⏱️  Recibiendo datos automáticos por 60 segundos...")
            print("   (Los datos llegarán cada 10 segundos)")
            
            start_time = asyncio.get_event_loop().time()
            update_count = 0
            
            while (asyncio.get_event_loop().time() - start_time) < 60:
                try:
                    # Esperar mensaje con timeout
                    data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    message = json.loads(data)
                    
                    if message.get("type") == "dashboard_data":
                        update_count += 1
                        timestamp = datetime.fromtimestamp(message.get("timestamp", 0)).strftime("%H:%M:%S")
                        count = message.get("count", 0)
                        query_time = message.get("query_time_ms", 0)
                        
                        print(f"📊 Actualización #{update_count} [{timestamp}]")
                        print(f"   📈 {count} registros en {query_time}ms")
                        
                        # Mostrar algunos ejemplos
                        if message.get("data") and len(message["data"]) > 0:
                            sample = message["data"][0]
                            par = sample.get("par", "N/A")
                            client_id = sample.get("client_id_result", "N/A")
                            ratio = sample.get("ultimo_ratio_operado", "N/A")
                            print(f"   📝 Ejemplo: {par} (cliente: {client_id}) = {ratio}")
                        
                        print()
                        
                    elif message.get("type") == "dashboard_error":
                        print(f"❌ Error en dashboard: {message.get('error', 'Unknown error')}")
                        
                    else:
                        print(f"📨 Otro mensaje: {message.get('type', 'unknown')}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout esperando datos")
                    break
                except Exception as e:
                    print(f"❌ Error recibiendo datos: {e}")
                    break
            
            # Desuscribirse
            unsubscribe_msg = {"action": "dashboard_unsubscribe"}
            await websocket.send(json.dumps(unsubscribe_msg))
            print("📡 Desuscripción enviada")
            
            # Recibir confirmación
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"✅ {response_data.get('message', 'Desuscripción confirmada')}")
            
            print(f"\n🎉 Prueba completada. Recibiste {update_count} actualizaciones automáticas.")
            
    except ConnectionRefusedError:
        print("❌ Error: No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor esté corriendo en localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🧪 Prueba de Suscripción Automática al Dashboard")
    print("=" * 60)
    asyncio.run(test_dashboard_subscription())
