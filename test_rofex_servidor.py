#!/usr/bin/env python3
"""
Script para conectar ROFEX desde el servidor y probar operaciones reales
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

async def conectar_y_probar_rofex():
    print("🚀 CONECTANDO ROFEX DESDE SERVIDOR")
    print("=" * 50)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Paso 1: Conectar ROFEX
            print("\n📡 Conectando ROFEX...")
            connect_msg = {
                "type": "connect_rofex",
                "user": "24239211",
                "password": "GuEtAjEt25ß*",
                "account": "16557",
                "instrumentos": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
            }
            
            await websocket.send(json.dumps(connect_msg))
            print("📤 Mensaje de conexión ROFEX enviado")
            
            # Esperar respuesta de conexión
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 Respuesta: {data}")
            
            # Esperar un poco para que se establezca la conexión
            await asyncio.sleep(3)
            
            # Paso 2: Probar operación de ratio
            print("\n⚡ Probando operación de ratio...")
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 1,  # Cantidad pequeña para prueba
                "target_ratio": 0.95,
                "condition": "<=",
                "client_id": "test_rofex_real"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada")
            
            # Escuchar respuestas por 30 segundos
            timeout = 30
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    
                    print(f"\n📨 Mensaje recibido:")
                    print(f"   Tipo: {data.get('type', 'N/A')}")
                    
                    if data.get('type') == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        print(f"   Estado: {progress.get('status')}")
                        print(f"   Ratio: {progress.get('current_ratio', 0):.6f}")
                        print(f"   Órdenes: {progress.get('sell_orders_count', 0)}V / {progress.get('buy_orders_count', 0)}C")
                        
                        # Mostrar mensajes recientes
                        messages = progress.get('messages', [])
                        if messages:
                            print(f"   Últimos mensajes:")
                            for msg in messages[-3:]:  # Últimos 3 mensajes
                                print(f"     • {msg}")
                    
                    elif data.get('type') == 'order_report':
                        print(f"   📋 Order Report recibido!")
                        report = data.get('report', {})
                        print(f"     Client ID: {report.get('wsClOrdId', 'N/A')}")
                        print(f"     Status: {report.get('status', 'N/A')}")
                        print(f"     Side: {report.get('side', 'N/A')}")
                        print(f"     Quantity: {report.get('orderQty', 0)}")
                        print(f"     Price: {report.get('price', 0)}")
                    
                    elif data.get('type') == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"   ⚠️ Error procesando mensaje: {e}")
            
            print(f"\n⏰ Timeout de {timeout} segundos alcanzado")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(conectar_y_probar_rofex())
