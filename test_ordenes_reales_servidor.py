#!/usr/bin/env python3
"""
Cliente de prueba para verificar que el servidor ejecute órdenes reales
"""

import asyncio
import websockets
import json

async def test_ordenes_reales_servidor():
    print("🧪 PROBANDO SERVIDOR CON ÓRDENES REALES")
    print("=" * 50)
    
    try:
        # Conectar al WebSocket del servidor
        uri = "ws://localhost:8000/ws/cotizaciones"
        print(f"🔗 Conectando a {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Enviar operación de ratio
            operation_request = {
                "type": "start_ratio_operation",
                "operation": {
                    "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                    "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                    "client_id": "test_real_orders",
                    "nominales": 3,
                    "target_ratio": 0.95,
                    "condition": "less_than_or_equal",
                    "max_attempts": 0
                }
            }
            
            print("📤 Enviando operación de ratio con órdenes reales...")
            await websocket.send(json.dumps(operation_request))
            
            # Recibir respuestas
            print("📥 Esperando respuestas...")
            timeout_count = 0
            max_timeouts = 15
            
            while timeout_count < max_timeouts:
                try:
                    # Esperar respuesta con timeout
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(response)
                    
                    print(f"📨 Respuesta: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'ratio_operation_started':
                        print("✅ Operación iniciada exitosamente")
                        operation_id = data.get('operation_id')
                        print(f"🆔 ID de operación: {operation_id}")
                        
                    elif data.get('type') == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        print(f"📊 Estado: {progress.get('status', 'unknown')}")
                        print(f"📈 Ratio: {progress.get('current_ratio', 0):.6f}")
                        print(f"🎯 Condición: {progress.get('condition_met', False)}")
                        print(f"💰 Órdenes: Venta={len(progress.get('sell_orders', []))}, Compra={len(progress.get('buy_orders', []))}")
                        
                        # Mostrar órdenes ejecutadas
                        sell_orders = progress.get('sell_orders', [])
                        buy_orders = progress.get('buy_orders', [])
                        
                        if sell_orders:
                            print("📤 Órdenes de venta ejecutadas:")
                            for order in sell_orders:
                                print(f"   {order.get('instrument')} - {order.get('quantity')} @ {order.get('price')} (ID: {order.get('order_id')})")
                        
                        if buy_orders:
                            print("📥 Órdenes de compra ejecutadas:")
                            for order in buy_orders:
                                print(f"   {order.get('instrument')} - {order.get('quantity')} @ {order.get('price')} (ID: {order.get('order_id')})")
                        
                        # Mostrar últimos mensajes
                        messages = progress.get('messages', [])
                        if messages:
                            print("📝 Últimos mensajes:")
                            for msg in messages[-3:]:  # Mostrar últimos 3 mensajes
                                print(f"   {msg}")
                        
                        print("-" * 40)
                        
                        # Si la operación está completada, salir
                        if progress.get('status') == 'completed':
                            print("🏁 Operación completada")
                            break
                            
                    elif data.get('type') == 'error':
                        print(f"❌ Error: {data.get('message', 'Error desconocido')}")
                        break
                        
                    else:
                        print(f"📨 Mensaje: {data}")
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"⏰ Timeout {timeout_count}/{max_timeouts}")
                    continue
                    
            if timeout_count >= max_timeouts:
                print("⏰ Tiempo de espera agotado")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🏁 Prueba completada")
    return True

if __name__ == "__main__":
    asyncio.run(test_ordenes_reales_servidor())
