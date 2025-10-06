#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_campos_operation_progress():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO CAMPOS DE OPERATION_PROGRESS")
        print("=" * 60)
        print("Objetivo: Verificar que los campos se actualizan correctamente")
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
            "client_id": "test_campos_operation_progress_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Operación enviada...")
        
        operation_id = None
        intento_count = 0
        
        # Escuchar mensajes de progreso
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ Operación iniciada: {operation_id}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    intento_count += 1
                    print(f"\n🔄 INTENTO #{intento_count}")
                    print("-" * 50)
                    
                    # Mostrar campos del objeto OperationProgress
                    print(f"📊 CAMPOS DEL OBJETO:")
                    print(f"   current_ratio: {data.get('current_ratio', 'N/A')}")
                    print(f"   target_ratio: {data.get('target_ratio', 'N/A')}")
                    print(f"   condition_met: {data.get('condition_met', 'N/A')}")
                    print(f"   current_step: {data.get('current_step', 'N/A')}")
                    print(f"   progress_percentage: {data.get('progress_percentage', 'N/A')}")
                    print(f"   sell_orders_count: {data.get('sell_orders_count', 'N/A')}")
                    print(f"   buy_orders_count: {data.get('buy_orders_count', 'N/A')}")
                    
                    # Mostrar mensajes relevantes
                    messages = data.get('messages', [])
                    for msg in messages:
                        if "Ratio actual:" in msg and "(" in msg:
                            print(f"📈 {msg}")
                        elif "Condición:" in msg:
                            print(f"✅ {msg}")
                    
                    # Verificar consistencia
                    current_ratio = data.get('current_ratio', 0)
                    condition_met = data.get('condition_met', False)
                    
                    print(f"\n🔍 ANÁLISIS DE CONSISTENCIA:")
                    if current_ratio > 0:
                        print(f"   ✅ current_ratio actualizado: {current_ratio}")
                    else:
                        print(f"   ❌ current_ratio NO actualizado: {current_ratio}")
                    
                    if condition_met is not None:
                        print(f"   ✅ condition_met actualizado: {condition_met}")
                    else:
                        print(f"   ❌ condition_met NO actualizado: {condition_met}")
                    
                    # Si la operación termina o llegamos a 2 intentos, salir
                    status = data.get('status', 'unknown')
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                        if data.get('error'):
                            print(f"❌ Error: {data['error']}")
                        break
                    elif intento_count >= 2:
                        print(f"\n⏹️ Deteniendo después de {intento_count} intentos")
                        break
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando progreso de la operación")
        
        # Resumen de la prueba
        print(f"\n📋 RESUMEN DE LA PRUEBA:")
        print(f"   Operation ID: {operation_id}")
        print(f"   Intentos analizados: {intento_count}")
        
        print(f"\n💡 VERIFICACIÓN:")
        print(f"   • Los campos current_ratio y condition_met deben actualizarse")
        print(f"   • Deben coincidir con los valores mostrados en los mensajes")
        print(f"   • No deben permanecer en 0 o false cuando hay cotizaciones reales")
        
        print(f"\n🏁 Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_campos_operation_progress())
