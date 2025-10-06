#!/usr/bin/env python3
import asyncio
import websockets
import json


async def main():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO NUEVO SISTEMA DE OPERACIONES POR LOTES")
        print("=" * 70)
        print("Objetivo: Vender 100 nominales de TX26 con ratio promedio <= 0.95")
        print("El sistema ejecutará múltiples lotes si es necesario")
        print("=" * 70)
        
        # Usar el nuevo formato de array y un ratio objetivo realista
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 100.0,  # 100 nominales objetivo
            "target_ratio": 0.95,  # Ratio objetivo <= 0.95
            "condition": "<=",
            "client_id": "test_batch_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Enviada operación por lotes:")
        print(f"   Par: {operation_request['pair']}")
        print(f"   Vender: {operation_request['instrument_to_sell']}")
        print(f"   Nominales objetivo: {operation_request['nominales']}")
        print(f"   Ratio objetivo: {operation_request['target_ratio']} {operation_request['condition']}")
        
        print("\n📈 ESCUCHANDO PROGRESO DE LOTES...")
        print("=" * 70)
        
        # Escuchar progreso
        for i in range(50):  # Más mensajes esperados para lotes
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=20)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    print(f"✅ {data['message']}")
                    print(f"   ID: {data['operation_id']}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    print(f"\n📊 PROGRESO: {data['progress_percentage']}%")
                    print(f"   Estado: {data['status']}")
                    print(f"   Paso: {data['current_step']}")
                    
                    # Mostrar información específica de lotes si está disponible
                    if 'target_nominales' in data:
                        print(f"   📊 Nominales: {data.get('completed_nominales', 0)}/{data['target_nominales']}")
                        print(f"   🔢 Lotes ejecutados: {data.get('batch_count', 0)}")
                        print(f"   📈 Ratio promedio: {data.get('weighted_average_ratio', 0):.6f}")
                    
                    if data.get('messages'):
                        last_message = data['messages'][-1]
                        print(f"   📝 Último mensaje: {last_message}")
                        
                        # Destacar mensajes importantes de lotes
                        if "Lote" in last_message and "ejecutado" in last_message:
                            print("   ✅ ¡LOTE EJECUTADO EXITOSAMENTE!")
                        elif "Ratio promedio ponderado" in last_message:
                            print("   📊 ¡RATIO PROMEDIO CALCULADO!")
                        elif "OPERACIÓN FINALIZADA" in last_message:
                            print("   🏁 ¡OPERACIÓN COMPLETADA!")
                        elif "Intento" in last_message and "/" in last_message:
                            print("   🔄 ¡NUEVO INTENTO DE LOTE!")
                    
                    if data.get('error'):
                        print(f"   ❌ Error: {data['error']}")
                    
                    # Salir si la operación terminó
                    if data['status'] in ['completed', 'failed']:
                        if data['status'] == 'completed':
                            print(f"\n🎉 ¡OPERACIÓN POR LOTES COMPLETADA EXITOSAMENTE!")
                            print(f"   Nominales ejecutados: {data.get('completed_nominales', 'N/A')}")
                            print(f"   Lotes ejecutados: {data.get('batch_count', 'N/A')}")
                            print(f"   Ratio promedio final: {data.get('weighted_average_ratio', 0):.6f}")
                            print(f"   Condición cumplida: {data.get('condition_met', False)}")
                        else:
                            print(f"\n💥 OPERACIÓN POR LOTES FALLÓ")
                            print(f"   Error: {data.get('error', 'Desconocido')}")
                        break
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout esperando mensajes")
                break
            except Exception as e:
                print(f"❌ Error procesando mensaje: {e}")
                break
        
        print("\n🏁 Prueba de operaciones por lotes completada")

if __name__ == "__main__":
    asyncio.run(main())
