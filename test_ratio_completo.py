#!/usr/bin/env python3
"""
Test completo: Conectar ROFEX y ejecutar operación de ratio real
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_ratio_completo():
    print("🚀 TEST COMPLETO - ROFEX + RATIO OPERATION")
    print("=" * 60)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor WebSocket")
            
            # PASO 1: Conectar ROFEX con credenciales del .env
            print("\n📡 PASO 1: Conectando ROFEX...")
            connect_msg = {
                "type": "connect_rofex",
                "user": "24239211",
                "password": "GuEtAjEt25*",
                "account": "16557",
                "instrumentos": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
            }
            
            await websocket.send(json.dumps(connect_msg))
            print("📤 Mensaje de conexión ROFEX enviado")
            
            # Esperar respuesta de conexión
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                print(f"📨 Respuesta ROFEX: {data.get('type', 'N/A')} - {data.get('status', 'N/A')}")
            except asyncio.TimeoutError:
                print("⏰ Timeout esperando respuesta ROFEX")
            
            # Esperar un poco para que se establezca la conexión
            print("⏳ Esperando 5 segundos para estabilizar conexión...")
            await asyncio.sleep(5)
            
            # PASO 2: Ejecutar operación de ratio (la que me diste)
            print("\n⚡ PASO 2: Ejecutando operación de ratio...")
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": [
                    "MERV - XMEV - TX26 - 24hs",
                    "MERV - XMEV - TX28 - 24hs"
                ],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 10.0,
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_client_002"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada:")
            print(f"   Par: TX26/TX28")
            print(f"   Vender: TX26")
            print(f"   Nominales: 10.0")
            print(f"   Ratio objetivo: ≤ 0.98")
            
            # PASO 3: Escuchar todas las respuestas y confirmaciones
            print("\n📨 PASO 3: Escuchando confirmaciones...")
            timeout = 60  # 1 minuto
            start_time = time.time()
            order_reports_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(response)
                    msg_type = data.get('type', 'N/A')
                    
                    print(f"\n📨 [{datetime.now().strftime('%H:%M:%S')}] {msg_type.upper()}")
                    
                    if msg_type == 'ratio_operation_started':
                        print(f"   ✅ Operación iniciada: {data.get('operation_id')}")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        status = progress.get('status')
                        ratio = progress.get('current_ratio', 0)
                        sell_orders = progress.get('sell_orders_count', 0)
                        buy_orders = progress.get('buy_orders_count', 0)
                        
                        print(f"   📊 Estado: {status}")
                        print(f"   📈 Ratio: {ratio:.6f}")
                        print(f"   💰 Órdenes: {sell_orders}V / {buy_orders}C")
                        
                        # Mostrar últimos mensajes
                        messages = progress.get('messages', [])
                        if messages:
                            last_msg = messages[-1] if messages else ""
                            print(f"   💬 Último: {last_msg}")
                    
                    elif msg_type == 'order_report':
                        order_reports_count += 1
                        report = data.get('report', {})
                        client_id = report.get('wsClOrdId', 'N/A')
                        status = report.get('status', 'N/A')
                        side = report.get('side', 'N/A')
                        qty = report.get('orderQty', 0)
                        price = report.get('price', 0)
                        
                        print(f"   📋 Order Report #{order_reports_count}")
                        print(f"      Client ID: {client_id}")
                        print(f"      Estado: {status}")
                        print(f"      Lado: {side}")
                        print(f"      Cantidad: {qty}")
                        print(f"      Precio: {price}")
                        
                        # Mostrar precio promedio si está disponible
                        avg_price = report.get('avgPrice', 0)
                        if avg_price > 0:
                            print(f"      Precio Promedio: {avg_price}")
                    
                    elif msg_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                    
                    elif msg_type == 'connection':
                        print(f"   🔗 Conexión: {data.get('message')}")
                    
                    else:
                        print(f"   📄 Datos: {data}")
                    
                    # Si recibimos suficientes order reports, podemos terminar antes
                    if order_reports_count >= 4:  # 2 órdenes (sell + buy) con múltiples updates
                        print(f"\n🎯 Recibidos {order_reports_count} order reports - terminando...")
                        break
                    
                except asyncio.TimeoutError:
                    elapsed = time.time() - start_time
                    print(f"⏳ Esperando mensajes... ({elapsed:.0f}s)")
                    continue
                except Exception as e:
                    print(f"⚠️ Error procesando mensaje: {e}")
            
            elapsed = time.time() - start_time
            print(f"\n⏰ Timeout alcanzado después de {elapsed:.0f} segundos")
            print(f"📊 Total Order Reports recibidos: {order_reports_count}")
            
            if order_reports_count > 0:
                print("\n🎉 ¡ÉXITO! Se recibieron confirmaciones de pyRofex")
                print("✅ Las órdenes se ejecutaron y se recibieron order reports")
            else:
                print("\n⚠️ No se recibieron order reports")
                print("❓ Posibles causas:")
                print("   • ROFEX no conectado correctamente")
                print("   • Órdenes no ejecutadas")
                print("   • Order reports no configurados")
            
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    asyncio.run(test_ratio_completo())
