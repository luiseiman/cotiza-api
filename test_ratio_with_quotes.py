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

        await ws.send(json.dumps({
            "action": "start_ratio_operation",
            "pair": "MERV - XMEV - TX26 - 24hs-MERV - XMEV - TX28 - 24hs",
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 100.0,
            "target_ratio": 0.95,
            "condition": "<=",
            "client_id": "test_client_002"
        }))
        for _ in range(10):
            try:
                print(await asyncio.wait_for(ws.recv(), timeout=10))
            except asyncio.TimeoutError:
                break

if __name__ == "__main__":
    asyncio.run(main())


