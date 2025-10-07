#!/usr/bin/env python3
import asyncio
import websockets
import json

async def main():
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    async with websockets.connect(uri) as websocket:
        print("✅ Conectado")
        
        msg = {
            "type": "start_ratio_operation",
            "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 100.0,
            "target_ratio": 0.9706,
            "condition": "<=",
            "client_id": "test_client_002"
        }
        
        await websocket.send(json.dumps(msg))
        print("📤 Operación enviada")
        
        for i in range(10):
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                print(f"📨 {data.get('type', 'unknown')}: {data}")
            except asyncio.TimeoutError:
                print("⏳ Timeout")
                break

if __name__ == "__main__":
    asyncio.run(main())

