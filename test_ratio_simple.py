#!/usr/bin/env python3
"""
Cliente simplificado para probar operación de ratio
"""

import asyncio
import websockets
import json

async def test_ratio_simple():
    print("🧪 PRUEBA SIMPLE DE RATIO")
    
    try:
        async with websockets.connect("ws://localhost:8000/ws/cotizaciones") as websocket:
            print("✅ Conectado")
            
            # Enviar operación
            message = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 10.0,
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_client_002"
            }
            
            await websocket.send(json.dumps(message))
            print("📤 Operación enviada")
            
            # Recibir respuestas
            for i in range(5):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    data = json.loads(response)
                    print(f"📨 {data.get('type', 'unknown')}: {data.get('message', '')}")
                    
                    if data.get('type') == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        print(f"   Estado: {progress.get('status')}")
                        print(f"   Ratio: {progress.get('current_ratio', 0):.6f}")
                        print(f"   Órdenes: {len(progress.get('sell_orders', []))}V / {len(progress.get('buy_orders', []))}C")
                        
                        if progress.get('status') in ['completed', 'failed']:
                            break
                            
                except asyncio.TimeoutError:
                    print("⏰ Timeout")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ratio_simple())
