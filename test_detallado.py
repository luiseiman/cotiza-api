#!/usr/bin/env python3
"""
Test detallado para ver exactamente qué está pasando
"""

import asyncio
import websockets
import json
import time

async def test_detallado():
    print("🔍 TEST DETALLADO - DIAGNÓSTICO COMPLETO")
    print("=" * 50)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Enviar operación de ratio
            print("\n⚡ Enviando operación de ratio...")
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 10.0,
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_detallado_001"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación enviada")
            
            # Escuchar TODOS los mensajes detalladamente
            print("\n📨 Escuchando mensajes detallados...")
            timeout = 30
            start_time = time.time()
            message_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    print(f"\n📨 [{message_count}] {msg_type.upper()}")
                    print(f"   📄 Datos completos: {json.dumps(data, indent=2)}")
                    
                    if msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        messages = progress.get('messages', [])
                        print(f"\n   📝 TODOS LOS MENSAJES ({len(messages)}):")
                        for i, msg in enumerate(messages):
                            print(f"      {i+1:2d}. {msg}")
                        
                        # Verificar si hay mensajes de error
                        error_messages = [msg for msg in messages if "error" in msg.lower() or "❌" in msg or "ws_not_connected" in msg.lower()]
                        if error_messages:
                            print(f"\n   ⚠️ MENSAJES DE ERROR ENCONTRADOS:")
                            for msg in error_messages:
                                print(f"      ❌ {msg}")
                    
                    elif msg_type == 'order_report':
                        print(f"   🎉 ¡ORDER REPORT RECIBIDO!")
                        report = data.get('report', {})
                        print(f"      📋 Detalles completos del reporte")
                    
                except asyncio.TimeoutError:
                    elapsed = int(time.time() - start_time)
                    print(f"⏳ Esperando... ({elapsed}s/{timeout}s)")
                    continue
                except Exception as e:
                    print(f"⚠️ Error: {e}")
            
            print(f"\n📊 RESUMEN:")
            print(f"   📨 Mensajes totales: {message_count}")
            print(f"   ⏱️ Tiempo: {time.time() - start_time:.1f}s")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_detallado())
