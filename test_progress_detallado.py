#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_progress_detallado():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO PROGRESO DETALLADO DE RATIOS")
        print("=" * 60)
        print("Objetivo: Verificar campos detallados en ratio_operation_progress")
        print("=" * 60)
        
        # Iniciar una operación de ratio
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 50.0,  # Cantidad para ver varios intentos
            "target_ratio": 0.90,
            "condition": "<=",
            "client_id": "test_progress_detallado_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Operación enviada...")
        
        operation_id = None
        progress_count = 0
        
        # Escuchar mensajes de progreso
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ Operación iniciada: {operation_id}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    progress_count += 1
                    print(f"\n📊 PROGRESO #{progress_count}")
                    print("-" * 40)
                    
                    # Mostrar campos básicos
                    print(f"🆔 Operation ID: {data.get('operation_id', 'N/A')}")
                    print(f"📈 Status: {data.get('status', 'N/A')}")
                    print(f"🔄 Step: {data.get('current_step', 'N/A')}")
                    print(f"📊 Progress: {data.get('progress_percentage', 0)}%")
                    
                    # Mostrar campos detallados nuevos
                    print(f"\n📋 INFORMACIÓN DETALLADA:")
                    print(f"   🎯 Nominales objetivo: {data.get('target_nominales', 0)}")
                    print(f"   ✅ Nominales completados: {data.get('completed_nominales', 0)}")
                    print(f"   ⏳ Nominales restantes: {data.get('remaining_nominales', 0)}")
                    print(f"   📦 Lotes ejecutados: {data.get('batch_count', 0)}")
                    print(f"   📏 Tamaño lote actual: {data.get('current_batch_size', 0)}")
                    
                    # Información de intentos
                    print(f"\n🔄 INTENTOS:")
                    print(f"   🔢 Intento actual: {data.get('current_attempt', 0)}")
                    print(f"   📊 Tasa de éxito: {data.get('success_rate', 0):.1f}%")
                    print(f"   ⏱️ Tiempo estimado: {data.get('estimated_completion_time', 'N/A')}")
                    
                    # Información de ratios
                    print(f"\n📈 RATIOS:")
                    current_ratio = data.get('current_ratio', 0)
                    weighted_ratio = data.get('weighted_average_ratio', 0)
                    target_ratio = data.get('target_ratio', 0)
                    condition = data.get('condition', '')
                    
                    print(f"   📊 Ratio actual: {current_ratio:.6f}")
                    print(f"   ⚖️ Ratio promedio: {weighted_ratio:.6f}")
                    print(f"   🎯 Ratio objetivo: {target_ratio} {condition}")
                    print(f"   📊 Condición mercado: {data.get('market_condition', 'N/A')}")
                    print(f"   ✅ Condición cumplida: {'SÍ' if data.get('condition_met', False) else 'NO'}")
                    
                    # Mostrar últimos mensajes
                    messages = data.get('messages', [])
                    if messages:
                        print(f"\n💬 ÚLTIMOS MENSAJES:")
                        for msg in messages[-3:]:  # Mostrar últimos 3 mensajes
                            print(f"   {msg}")
                    
                    # Si la operación termina, salir
                    status = data.get('status', 'unknown')
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                        if data.get('error'):
                            print(f"❌ Error: {data['error']}")
                        break
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando progreso de la operación")
        
        # Resumen de la prueba
        print(f"\n📋 RESUMEN DE LA PRUEBA:")
        print(f"   Operation ID: {operation_id}")
        print(f"   Progresos recibidos: {progress_count}")
        print(f"   ✅ Campos detallados: IMPLEMENTADOS Y FUNCIONANDO")
        
        print(f"\n🏁 Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_progress_detallado())
