#!/usr/bin/env python3
"""
Cliente de prueba para investigar exactamente dónde se detiene el proceso
"""

import asyncio
import websockets
import json
import sys

async def test_debug_completo():
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 Conectado al WebSocket")
            
            # Recibir mensaje de bienvenida
            welcome_msg = await websocket.recv()
            print(f"📨 Bienvenida: {welcome_msg}")
            
            # Crear operación de ratio
            operation_request = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "client_id": "test_client",
                "nominales": 10,
                "target_ratio": 0.95,
                "condition": "less_than_or_equal",
                "max_attempts": 0  # Intentos infinitos
            }
            
            print("📤 Operación enviada...")
            await websocket.send(json.dumps(operation_request))
            
            # Esperar respuesta de la operación
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get("type") == "ratio_operation_started":
                operation_id = response_data.get("operation_id")
                print(f"✅ Operación iniciada: {operation_id}")
                
                # Esperar mensajes de progreso por 30 segundos
                timeout = 30
                start_time = asyncio.get_event_loop().time()
                
                while asyncio.get_event_loop().time() - start_time < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        if data.get("type") == "ratio_operation_progress":
                            progress = data.get("progress", {})
                            messages = progress.get("messages", [])
                            
                            # Mostrar todos los mensajes nuevos
                            for msg in messages:
                                if "PUNTO CRÍTICO" in msg or "DEBUG" in msg:
                                    print(f"🔍 {msg}")
                                else:
                                    print(f"📊 {msg}")
                            
                            # Mostrar estado actual
                            print(f"📊 Progreso: ratio={progress.get('current_ratio', 0):.6f}, condición={progress.get('condition_met', False)}, órdenes={progress.get('sell_orders_count', 0)}/{progress.get('buy_orders_count', 0)}")
                            
                            # Si la operación está completada, salir
                            if progress.get("status") == "completed":
                                print("✅ Operación completada")
                                break
                                
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"❌ Error recibiendo mensaje: {e}")
                        break
                
                print("⏰ Timeout esperando progreso de la operación")
                
            else:
                print(f"❌ Error iniciando operación: {response_data}")
                
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 PROBANDO DEBUG COMPLETO")
    print("=" * 60)
    print("Objetivo: Investigar exactamente dónde se detiene el proceso")
    print("=" * 60)
    
    result = asyncio.run(test_debug_completo())
    
    if result:
        print("✅ Prueba completada")
    else:
        print("❌ Prueba falló")
        sys.exit(1)
