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
        
        # Verificar estado del WebSocket
        await ws.send(json.dumps({"action": "check_ws_status"}))
        ws_status = await ws.recv()
        print(f"📊 Estado WS: {ws_status}")
        
        # Verificar cotizaciones disponibles
        await ws.send(json.dumps({"action": "check_quotes"}))
        quotes_status = await ws.recv()
        print(f"💰 Cotizaciones: {quotes_status}")
        
        print("\n🚀 INICIANDO OPERACIÓN CON NUEVO FORMATO DE ARRAY")
        print("=" * 60)
        
        # NUEVO FORMATO: Array de instrumentos
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 10.0,
            "target_ratio": 0.95,
            "condition": "<=",
            "client_id": "test_array_format_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Enviada operación con formato array:")
        print(f"   Pair: {operation_request['pair']}")
        print(f"   Vender: {operation_request['instrument_to_sell']}")
        print(f"   Nominales: {operation_request['nominales']}")
        print(f"   Ratio objetivo: {operation_request['target_ratio']} {operation_request['condition']}")
        
        print("\n📈 ESCUCHANDO PROGRESO...")
        print("=" * 60)
        
        # Escuchar progreso
        for i in range(20):  # Máximo 20 mensajes
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    print(f"✅ {data['message']}")
                    print(f"   ID de operación: {data['operation_id']}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    print(f"\n📊 PROGRESO: {data['progress_percentage']}%")
                    print(f"   Estado: {data['status']}")
                    print(f"   Paso: {data['current_step']}")
                    print(f"   Ratio actual: {data['current_ratio']}")
                    print(f"   Condición cumplida: {data['condition_met']}")
                    
                    if data.get('messages'):
                        print(f"   📝 Último mensaje: {data['messages'][-1]}")
                    
                    if data.get('error'):
                        print(f"   ❌ Error: {data['error']}")
                    
                    # Salir si la operación terminó
                    if data['status'] in ['completed', 'failed']:
                        if data['status'] == 'completed':
                            print(f"\n🎉 ¡OPERACIÓN COMPLETADA EXITOSAMENTE!")
                            print(f"   Ratio final: {data['current_ratio']}")
                            print(f"   Condición cumplida: {data['condition_met']}")
                        else:
                            print(f"\n💥 OPERACIÓN FALLÓ")
                            print(f"   Error: {data.get('error', 'Desconocido')}")
                        break
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error en operación: {data['error']}")
                    break
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout esperando mensajes")
                break
            except Exception as e:
                print(f"❌ Error procesando mensaje: {e}")
                break
        
        print("\n🏁 Prueba completada")

if __name__ == "__main__":
    asyncio.run(main())

