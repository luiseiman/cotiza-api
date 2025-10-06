#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_debug_flow():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 DEBUGGING FLUJO DE EJECUCIÓN")
        print("=" * 60)
        print("Objetivo: Verificar si _show_current_quotes se ejecuta")
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
            "client_id": "test_debug_flow_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Operación enviada...")
        
        operation_id = None
        mensajes_vistos = set()
        
        # Escuchar mensajes de progreso
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ Operación iniciada: {operation_id}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    messages = data.get('messages', [])
                    
                    # Mostrar todos los mensajes nuevos
                    for msg in messages:
                        if msg not in mensajes_vistos:
                            mensajes_vistos.add(msg)
                            print(f"💬 {msg}")
                            
                            # Verificar si se ejecuta _show_current_quotes
                            if "Cotizaciones actuales:" in msg:
                                print(f"✅ _show_current_quotes se ejecutó")
                            elif "Análisis de Ratio:" in msg:
                                print(f"✅ Análisis de ratio se ejecutó")
                    
                    # Mostrar campos del objeto
                    current_ratio = data.get('current_ratio', 0)
                    condition_met = data.get('condition_met', False)
                    current_step = data.get('current_step', 'unknown')
                    
                    print(f"📊 Campos: current_ratio={current_ratio}, condition_met={condition_met}, step={current_step}")
                    
                    # Si la operación termina, salir
                    status = data.get('status', 'unknown')
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                        if data.get('error'):
                            print(f"❌ Error: {data['error']}")
                        break
                    
                    # Si vemos el mensaje de cotizaciones, esperar un poco más
                    if any("Cotizaciones actuales:" in msg for msg in messages):
                        await asyncio.sleep(2)  # Esperar un poco más para ver actualizaciones
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando progreso de la operación")
        
        print(f"\n📋 RESUMEN:")
        print(f"   Operation ID: {operation_id}")
        print(f"   Mensajes únicos vistos: {len(mensajes_vistos)}")
        
        if any("Cotizaciones actuales:" in msg for msg in mensajes_vistos):
            print(f"   ✅ _show_current_quotes se ejecutó")
        else:
            print(f"   ❌ _show_current_quotes NO se ejecutó")
        
        print(f"\n🏁 Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_debug_flow())
