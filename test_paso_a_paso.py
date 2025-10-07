#!/usr/bin/env python3
"""
Test paso a paso: 1) Iniciar cotizaciones, 2) Ejecutar ratio operation
"""

import asyncio
import websockets
import json
import time

async def test_paso_a_paso():
    print("🚀 TEST PASO A PASO - COTIZACIONES + RATIO")
    print("=" * 60)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor WebSocket")
            
            # PASO 1: Iniciar cotizaciones con instrumentos necesarios
            print("\n📊 PASO 1: Iniciando cotizaciones...")
            instrumentos = ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
            
            # Mensaje para iniciar cotizaciones
            cotizaciones_msg = {
                "type": "start_quotes",
                "instruments": instrumentos
            }
            
            await websocket.send(json.dumps(cotizaciones_msg))
            print(f"📤 Iniciando cotizaciones para: {instrumentos}")
            
            # Escuchar confirmación de cotizaciones
            print("📨 Esperando confirmación de cotizaciones...")
            cotizaciones_iniciadas = False
            
            for _ in range(10):  # Esperar hasta 20 segundos
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    
                    print(f"📨 {msg_type.upper()}: {data.get('message', data.get('status', 'N/A'))}")
                    
                    if msg_type == 'quotes_started' or 'cotizaciones' in str(data).lower():
                        print("✅ Cotizaciones iniciadas exitosamente!")
                        cotizaciones_iniciadas = True
                        break
                    elif msg_type == 'connection':
                        print("🔗 Conexión establecida")
                    elif msg_type == 'error':
                        print(f"❌ Error: {data.get('message')}")
                        
                except asyncio.TimeoutError:
                    print("⏳ Esperando confirmación...")
                    continue
            
            if not cotizaciones_iniciadas:
                print("⚠️ No se recibió confirmación de cotizaciones, pero continuando...")
            
            # Esperar un poco para que se estabilicen las cotizaciones
            print("\n⏳ Esperando 5 segundos para estabilizar cotizaciones...")
            await asyncio.sleep(5)
            
            # PASO 2: Conectar ROFEX
            print("\n🔌 PASO 2: Conectando ROFEX...")
            rofex_msg = {
                "type": "connect_rofex",
                "user": "24239211",
                "password": "GuEtAjEt25*",
                "account": "16557",
                "instrumentos": instrumentos
            }
            
            await websocket.send(json.dumps(rofex_msg))
            print("📤 Conexión ROFEX enviada")
            
            # Escuchar confirmación de ROFEX
            print("📨 Esperando confirmación de ROFEX...")
            rofex_conectado = False
            
            for _ in range(10):  # Esperar hasta 20 segundos
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    
                    print(f"📨 {msg_type.upper()}: {data.get('message', data.get('status', 'N/A'))}")
                    
                    if msg_type == 'connection' and 'rofex' in str(data).lower():
                        print("✅ ROFEX conectado exitosamente!")
                        rofex_conectado = True
                        break
                    elif msg_type == 'error':
                        print(f"❌ Error ROFEX: {data.get('message')}")
                        
                except asyncio.TimeoutError:
                    print("⏳ Esperando ROFEX...")
                    continue
            
            if not rofex_conectado:
                print("⚠️ No se recibió confirmación de ROFEX, pero continuando...")
            
            # Esperar un poco más para que se estabilice ROFEX
            print("\n⏳ Esperando 3 segundos para estabilizar ROFEX...")
            await asyncio.sleep(3)
            
            # PASO 3: Ejecutar operación de ratio
            print("\n⚡ PASO 3: Ejecutando operación de ratio...")
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": instrumentos,
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 10.0,
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_paso_a_paso"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada")
            print(f"   Par: {instrumentos}")
            print(f"   Vender: TX26")
            print(f"   Nominales: 10.0")
            print(f"   Ratio objetivo: ≤ 0.98")
            
            # PASO 4: Escuchar confirmaciones y order reports
            print("\n📨 PASO 4: Escuchando confirmaciones...")
            timeout = 45  # 45 segundos para order reports
            start_time = time.time()
            order_reports = 0
            message_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    print(f"\n📨 [{message_count}] {msg_type.upper()}")
                    
                    if msg_type == 'ratio_operation_started':
                        print(f"   ✅ Operación iniciada: {data.get('operation_id')}")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        print(f"   📊 Estado: {progress.get('status')}")
                        print(f"   📈 Ratio: {progress.get('current_ratio', 0):.6f}")
                        print(f"   💰 Órdenes: {progress.get('sell_orders_count', 0)}V/{progress.get('buy_orders_count', 0)}C")
                        
                        # Mostrar últimos mensajes
                        messages = progress.get('messages', [])
                        if messages:
                            last_msg = messages[-1]
                            print(f"   💬 {last_msg}")
                            
                            # Detectar si se están ejecutando órdenes
                            if "ejecutando" in last_msg.lower() or "enviando orden" in last_msg.lower():
                                print("   🎯 ¡Órdenes en ejecución!")
                            elif "ws_not_connected" in last_msg.lower():
                                print("   ❌ ROFEX desconectado durante ejecución")
                    
                    elif msg_type == 'order_report':
                        order_reports += 1
                        report = data.get('report', {})
                        print(f"   📋 Order Report #{order_reports}")
                        print(f"      Client ID: {report.get('wsClOrdId', 'N/A')}")
                        print(f"      Estado: {report.get('status', 'N/A')}")
                        print(f"      Lado: {report.get('side', 'N/A')}")
                        print(f"      Cantidad: {report.get('orderQty', 0)}")
                        print(f"      Precio: {report.get('price', 0)}")
                        
                        if report.get('status') == 'FILLED':
                            print("      🎉 ¡ORDEN EJECUTADA!")
                    
                    elif msg_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                    
                    elif msg_type == 'quotes_update':
                        quotes = data.get('quotes', {})
                        print(f"   📊 Cotizaciones actualizadas: {len(quotes)} instrumentos")
                    
                    else:
                        print(f"   📄 {data}")
                    
                    # Si recibimos order reports, podemos terminar antes
                    if order_reports >= 4:  # 2 órdenes con múltiples updates
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
            print(f"   📊 Cotizaciones: {'✅' if cotizaciones_iniciadas else '❌'}")
            print(f"   🔌 ROFEX: {'✅' if rofex_conectado else '❌'}")
            
            if order_reports > 0:
                print("\n🎉 ¡ÉXITO! Se recibieron confirmaciones de pyRofex")
                print("✅ Las órdenes se ejecutaron y se recibieron order reports")
                print("\n📋 TIPOS DE CONFIRMACIONES RECIBIDAS:")
                print("   1. Respuesta inmediata de send_order_via_websocket")
                print("   2. Order Reports asíncronos con estados (NEW, FILLED, etc.)")
                print("   3. Actualizaciones de precios y cantidades ejecutadas")
            else:
                print("\n⚠️ No se recibieron order reports")
                print("💡 Verificar:")
                print("   • Cotizaciones activas")
                print("   • ROFEX conectado")
                print("   • Órdenes ejecutándose")
            
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    asyncio.run(test_paso_a_paso())
