#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_ejecucion_ordenes():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO EJECUCIÓN DE ÓRDENES")
        print("=" * 60)
        print("Objetivo: Verificar que se ejecuten las órdenes de compra/venta")
        print("=" * 60)
        
        # Iniciar una operación de ratio
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 10.0,
            "target_ratio": 0.9782,
            "condition": "<=",
            "client_id": "test_ejecucion_ordenes_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Operación enviada...")
        
        operation_id = None
        ordenes_ejecutadas = 0
        mensajes_vistos = set()
        
        # Escuchar mensajes de progreso por tiempo limitado
        start_time = asyncio.get_event_loop().time()
        max_duration = 15  # 15 segundos máximo
        
        try:
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                remaining = max_duration - elapsed
                
                if remaining <= 0:
                    print(f"\n⏰ Tiempo límite alcanzado ({max_duration}s)")
                    # Cancelar la operación antes de salir
                    if operation_id:
                        cancel_request = {
                            "action": "cancel_ratio_operation",
                            "operation_id": operation_id
                        }
                        await ws.send(json.dumps(cancel_request))
                        print(f"🛑 Operación cancelada: {operation_id}")
                    break
                
                message = await asyncio.wait_for(ws.recv(), timeout=min(2, remaining))
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ Operación iniciada: {operation_id}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    messages = data.get('messages', [])
                    status = data.get('status', 'unknown')
                    
                    # Mostrar mensajes nuevos relevantes
                    for msg in messages:
                        if msg not in mensajes_vistos:
                            mensajes_vistos.add(msg)
                            
                            if "DEBUG:" in msg or "🔍" in msg:
                                print(f"🔍 {msg}")
                            elif "Ejecutando venta:" in msg:
                                print(f"💰 {msg}")
                                ordenes_ejecutadas += 1
                            elif "Ejecutando compra:" in msg:
                                print(f"💰 {msg}")
                                ordenes_ejecutadas += 1
                            elif "Resultado venta:" in msg:
                                print(f"📊 {msg}")
                            elif "Resultado compra:" in msg:
                                print(f"📊 {msg}")
                            elif "Error ejecutando lote" in msg:
                                print(f"❌ {msg}")
                            elif "Lote" in msg and "ejecutado" in msg:
                                print(f"✅ {msg}")
                            elif "Análisis de Ratio:" in msg:
                                print(f"📈 {msg}")
                            elif "Condición:" in msg:
                                print(f"✅ {msg}")
                            elif "max_batch_size" in msg or "remaining_nominales" in msg:
                                print(f"🔍 {msg}")
                    
                    # Mostrar progreso
                    current_ratio = data.get('current_ratio', 0)
                    condition_met = data.get('condition_met', False)
                    sell_orders_count = data.get('sell_orders_count', 0)
                    buy_orders_count = data.get('buy_orders_count', 0)
                    
                    print(f"📊 Progreso: ratio={current_ratio:.6f}, condición={condition_met}, órdenes={sell_orders_count}/{buy_orders_count}")
                    
                    # Si la operación termina, salir
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                        if data.get('error'):
                            print(f"❌ Error: {data['error']}")
                        break
                    
                    # Si vemos órdenes ejecutándose, esperar un poco más
                    if ordenes_ejecutadas > 0:
                        await asyncio.sleep(3)  # Esperar para ver el resultado
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando progreso de la operación")
        
        # Resumen de la prueba
        print(f"\n📋 RESUMEN DE LA PRUEBA:")
        print(f"   Operation ID: {operation_id}")
        print(f"   Órdenes ejecutadas: {ordenes_ejecutadas}")
        
        if ordenes_ejecutadas > 0:
            print(f"   ✅ Órdenes de compra/venta: EJECUTÁNDOSE")
        else:
            print(f"   ❌ Órdenes de compra/venta: NO SE EJECUTARON")
        
        print(f"\n💡 ANÁLISIS:")
        if ordenes_ejecutadas == 0:
            print(f"   • Las órdenes no se están ejecutando")
            print(f"   • Verificar logs del servidor para ver errores específicos")
            print(f"   • Revisar que ws_rofex.manager.send_order funcione correctamente")
        else:
            print(f"   • Las órdenes se están ejecutando correctamente")
            print(f"   • El sistema está funcionando como esperado")
        
        print(f"\n🏁 Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_ejecucion_ordenes())
