#!/usr/bin/env python3
"""
Test rápido de ratio - termina automáticamente
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_ratio_rapido():
    print("🚀 TEST RÁPIDO - ROFEX + RATIO")
    print("=" * 50)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # PASO 1: Conectar ROFEX
            print("\n📡 Conectando ROFEX...")
            connect_msg = {
                "type": "connect_rofex",
                "user": "24239211",
                "password": "GuEtAjEt25*",
                "account": "16557",
                "instrumentos": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
            }
            
            await websocket.send(json.dumps(connect_msg))
            print("📤 Conexión ROFEX enviada")
            
            # Esperar respuesta ROFEX
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                print(f"📨 ROFEX: {data.get('type')} - {data.get('status', 'N/A')}")
            except asyncio.TimeoutError:
                print("⏰ Timeout ROFEX")
            
            # Esperar un poco
            await asyncio.sleep(3)
            
            # PASO 2: Enviar operación de ratio
            print("\n⚡ Enviando operación de ratio...")
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 10.0,
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_rapido_001"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Ratio enviado")
            
            # PASO 3: Escuchar mensajes por tiempo limitado
            print("\n📨 Escuchando mensajes (30 segundos)...")
            timeout = 30
            start_time = time.time()
            message_count = 0
            order_reports = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    print(f"\n📨 [{message_count}] {msg_type.upper()}")
                    
                    if msg_type == 'ratio_operation_started':
                        print(f"   ✅ ID: {data.get('operation_id')}")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        print(f"   📊 Estado: {progress.get('status')}")
                        print(f"   📈 Ratio: {progress.get('current_ratio', 0):.6f}")
                        print(f"   💰 Órdenes: {progress.get('sell_orders_count', 0)}V/{progress.get('buy_orders_count', 0)}C")
                        
                        # Mostrar último mensaje
                        messages = progress.get('messages', [])
                        if messages:
                            print(f"   💬 {messages[-1]}")
                    
                    elif msg_type == 'order_report':
                        order_reports += 1
                        report = data.get('report', {})
                        print(f"   📋 Order Report #{order_reports}")
                        print(f"      ID: {report.get('wsClOrdId', 'N/A')}")
                        print(f"      Estado: {report.get('status', 'N/A')}")
                        print(f"      Lado: {report.get('side', 'N/A')}")
                    
                    elif msg_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                    
                    else:
                        print(f"   📄 {data}")
                    
                    # Si recibimos order reports, podemos terminar antes
                    if order_reports >= 2:
                        print(f"\n🎯 Recibidos {order_reports} order reports - terminando...")
                        break
                    
                except asyncio.TimeoutError:
                    elapsed = int(time.time() - start_time)
                    print(f"⏳ Esperando... ({elapsed}s/{timeout}s)")
                    continue
                except Exception as e:
                    print(f"⚠️ Error: {e}")
            
            # RESUMEN FINAL
            elapsed = time.time() - start_time
            print(f"\n📊 RESUMEN FINAL:")
            print(f"   ⏱️ Tiempo: {elapsed:.1f}s")
            print(f"   📨 Mensajes: {message_count}")
            print(f"   📋 Order Reports: {order_reports}")
            
            if order_reports > 0:
                print("   ✅ ÉXITO: Se recibieron confirmaciones de pyRofex!")
            else:
                print("   ⚠️ No se recibieron order reports")
                print("   💡 Posibles causas:")
                print("      • ROFEX no conectado")
                print("      • Órdenes no ejecutadas")
                print("      • Timeout muy corto")
            
            print("\n🏁 Test completado")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ratio_rapido())
