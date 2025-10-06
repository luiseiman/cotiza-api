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
        
        print("\n♾️ PROBANDO SISTEMA DE INTENTOS INFINITOS")
        print("=" * 70)
        print("Objetivo: Vender 100 nominales de TX26 con ratio promedio <= 0.95")
        print("El sistema intentará indefinidamente hasta completar o cancelar")
        print("=" * 70)
        
        # Usar un ratio objetivo muy estricto para demostrar los intentos infinitos
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 100.0,
            "target_ratio": 0.90,  # Ratio muy estricto para demostrar intentos infinitos
            "condition": "<=",
            "client_id": "test_infinite_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Enviada operación con intentos infinitos:")
        print(f"   Ratio objetivo: {operation_request['target_ratio']} {operation_request['condition']}")
        print(f"   (Ratio actual ~0.977, por lo que necesitará muchos intentos)")
        
        print("\n📈 ESCUCHANDO INTENTOS INFINITOS...")
        print("=" * 70)
        print("💡 Presiona Ctrl+C para cancelar la operación")
        print("=" * 70)
        
        operation_id = None
        attempt_count = 0
        
        # Escuchar progreso
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ {data['message']}")
                    print(f"   ID: {operation_id}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    # Contar intentos
                    if "Intento" in str(data.get('messages', [])):
                        attempt_count += 1
                    
                    print(f"\n📊 PROGRESO: {data['progress_percentage']}%")
                    print(f"   Estado: {data['status']}")
                    print(f"   Paso: {data['current_step']}")
                    print(f"   Intento: #{attempt_count}")
                    
                    if data.get('messages'):
                        last_message = data['messages'][-1]
                        print(f"   📝 Último mensaje: {last_message}")
                        
                        # Destacar mensajes importantes
                        if "Esperando mejores condiciones" in last_message:
                            print("   ⏳ ¡ESPERANDO INDEFINIDAMENTE!")
                        elif "Lote" in last_message and "ejecutado" in last_message:
                            print("   ✅ ¡LOTE EJECUTADO!")
                        elif "OPERACIÓN FINALIZADA" in last_message:
                            print("   🏁 ¡OPERACIÓN COMPLETADA!")
                    
                    if data.get('error'):
                        print(f"   ❌ Error: {data['error']}")
                    
                    # Salir si la operación terminó
                    if data['status'] in ['completed', 'failed']:
                        if data['status'] == 'completed':
                            print(f"\n🎉 ¡OPERACIÓN COMPLETADA EXITOSAMENTE!")
                            print(f"   Total de intentos: {attempt_count}")
                            print(f"   Nominales ejecutados: {data.get('completed_nominales', 'N/A')}")
                            print(f"   Lotes ejecutados: {data.get('batch_count', 'N/A')}")
                        else:
                            print(f"\n💥 OPERACIÓN FALLÓ")
                            print(f"   Total de intentos: {attempt_count}")
                            print(f"   Error: {data.get('error', 'Desconocido')}")
                        break
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except KeyboardInterrupt:
            print(f"\n🛑 CANCELACIÓN MANUAL SOLICITADA")
            if operation_id:
                print(f"   Cancelando operación {operation_id}...")
                await ws.send(json.dumps({
                    "action": "cancel_ratio_operation",
                    "operation_id": operation_id
                }))
                
                # Esperar confirmación de cancelación
                try:
                    while True:
                        message = await asyncio.wait_for(ws.recv(), timeout=5)
                        data = json.loads(message)
                        
                        if data['type'] == 'ratio_operation_cancelled':
                            print(f"✅ {data['message']}")
                            break
                        elif data['type'] == 'ratio_operation_progress':
                            if data['status'] in ['cancelled', 'failed']:
                                print(f"✅ Operación cancelada: {data['status']}")
                                break
                except asyncio.TimeoutError:
                    print("⏰ Timeout esperando confirmación de cancelación")
            
            print(f"   Total de intentos realizados: {attempt_count}")
            
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando mensajes")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n🏁 Prueba de intentos infinitos completada")

if __name__ == "__main__":
    asyncio.run(main())
