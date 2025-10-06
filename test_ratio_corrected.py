#!/usr/bin/env python3
import asyncio
import websockets
import json


async def main():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print(await ws.recv())  # welcome
        await ws.send(json.dumps({"action": "check_ws_status"}))
        print(await ws.recv())
        await ws.send(json.dumps({"action": "check_quotes"}))
        print(await ws.recv())

        # FORMATO CORRECTO: Un guión separando los instrumentos
        await ws.send(json.dumps({
            "action": "start_ratio_operation",
            "pair": "MERV - XMEV - TX26 - 24hs-MERV - XMEV - TX28 - 24hs",  # ✅ CORRECTO
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 10.0,
            "target_ratio": 0.95,
            "condition": "<=",
            "client_id": "test_client_003"
        }))
        
        print("\n=== OPERACIÓN INICIADA ===")
        for _ in range(15):
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_progress':
                    print(f"\n📊 PROGRESO: {data['progress_percentage']}%")
                    print(f"   Estado: {data['status']}")
                    print(f"   Paso: {data['current_step']}")
                    if data.get('messages'):
                        print(f"   Último mensaje: {data['messages'][-1]}")
                    if data.get('error'):
                        print(f"   ❌ Error: {data['error']}")
                elif data['type'] == 'ratio_operation_started':
                    print(f"🚀 {data['message']}")
                    print(f"   ID: {data['operation_id']}")
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                
                # Salir si la operación terminó
                if data['type'] == 'ratio_operation_progress' and data['status'] in ['completed', 'failed']:
                    break
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout esperando mensajes")
                break

if __name__ == "__main__":
    asyncio.run(main())

