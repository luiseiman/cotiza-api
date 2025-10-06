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
        
        print("\n🧪 PROBANDO NUEVA LÓGICA DE VALIDACIÓN DE RATIO")
        print("=" * 60)
        print("Objetivo: Verificar que NO se ejecute la compra si el ratio no cumple la condición")
        print("=" * 60)
        
        # Usar un ratio objetivo muy estricto que probablemente no se cumpla
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 10.0,
            "target_ratio": 0.90,  # Ratio muy estricto (0.90 <=)
            "condition": "<=",
            "client_id": "test_validation_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Enviada operación con ratio objetivo MUY ESTRICTO:")
        print(f"   Ratio objetivo: {operation_request['target_ratio']} {operation_request['condition']}")
        print(f"   (Ratio actual del mercado ~0.975, por lo que NO debería cumplirse)")
        
        print("\n📈 ESCUCHANDO PROGRESO...")
        print("=" * 60)
        
        # Escuchar progreso
        for i in range(15):
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    print(f"✅ {data['message']}")
                    print(f"   ID: {data['operation_id']}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    print(f"\n📊 PROGRESO: {data['progress_percentage']}%")
                    print(f"   Estado: {data['status']}")
                    print(f"   Paso: {data['current_step']}")
                    
                    if data.get('messages'):
                        last_message = data['messages'][-1]
                        print(f"   📝 Último mensaje: {last_message}")
                        
                        # Destacar mensajes importantes
                        if "Verificando ratio teórico" in last_message:
                            print("   🔍 ¡VERIFICACIÓN CRÍTICA EN CURSO!")
                        elif "Condición cumplida: ✅ SÍ" in last_message:
                            print("   ✅ ¡CONDICIÓN CUMPLIDA! Procediendo con compra...")
                        elif "Condición cumplida: ❌ NO" in last_message:
                            print("   ❌ ¡CONDICIÓN NO CUMPLIDA! Cancelando operación...")
                        elif "Operación cancelada" in last_message:
                            print("   🛑 ¡OPERACIÓN CANCELADA CORRECTAMENTE!")
                    
                    if data.get('error'):
                        print(f"   ❌ Error: {data['error']}")
                    
                    # Salir si la operación terminó
                    if data['status'] in ['completed', 'failed']:
                        if data['status'] == 'completed':
                            print(f"\n🎉 ¡OPERACIÓN COMPLETADA EXITOSAMENTE!")
                            print("   (Esto NO debería pasar con ratio 0.90 <=)")
                        else:
                            print(f"\n✅ OPERACIÓN CANCELADA CORRECTAMENTE")
                            print("   (Esto ES lo esperado con ratio 0.90 <=)")
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
        
        print("\n🏁 Prueba de validación completada")

if __name__ == "__main__":
    asyncio.run(main())
