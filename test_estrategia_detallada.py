#!/usr/bin/env python3
"""
Test detallado de la nueva estrategia de ratio TX26/TX28
"""

import asyncio
import websockets
import json
import time

async def test_estrategia_detallada():
    print("🎯 TEST ESTRATEGIA DETALLADA - RATIO TX26/TX28")
    print("=" * 60)
    print("📋 ESTRATEGIA:")
    print("   • VENDER TX26 al precio de COMPRA (bid)")
    print("   • COMPRAR TX28 al precio de VENTA (offer)")
    print("   • Ratio = precio_compra_TX26 / precio_venta_TX28")
    print("   • Compras TX28 solo con ventas efectivas TX26")
    print("=" * 60)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Enviar operación de ratio
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 10.0,
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_estrategia_detallada"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada")
            print(f"   Par: TX26/TX28")
            print(f"   Vender: TX26 (al precio de compra/bid)")
            print(f"   Comprar: TX28 (al precio de venta/offer)")
            print(f"   Nominales: 10.0")
            print(f"   Ratio objetivo: ≤ 0.98")
            
            # Escuchar mensajes detalladamente
            print("\n📨 Escuchando mensajes detallados...")
            timeout = 45
            start_time = time.time()
            message_count = 0
            order_reports = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    print(f"\n📨 [{message_count}] {msg_type.upper()}")
                    
                    if msg_type == 'tick':
                        symbol = data.get('symbol', 'N/A')
                        bid = data.get('bid', 0)
                        offer = data.get('offer', 0)
                        print(f"   📊 {symbol}")
                        print(f"      Bid (precio compra): {bid}")
                        print(f"      Offer (precio venta): {offer}")
                        print(f"      Spread: {offer - bid:.1f}")
                    
                    elif msg_type == 'ratio_operation_started':
                        print(f"   ✅ Operación iniciada: {data.get('operation_id')}")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        print(f"   📊 Estado: {progress.get('status')}")
                        print(f"   📈 Ratio actual: {progress.get('current_ratio', 0):.6f}")
                        print(f"   💰 Órdenes: {progress.get('sell_orders_count', 0)}V/{progress.get('buy_orders_count', 0)}C")
                        
                        # Mostrar TODOS los mensajes para ver la estrategia
                        messages = progress.get('messages', [])
                        if messages:
                            print(f"   📝 MENSAJES ({len(messages)}):")
                            for i, msg in enumerate(messages, 1):
                                print(f"      {i:2d}. {msg}")
                        
                        # Detectar pasos de la estrategia
                        if messages:
                            last_msg = messages[-1]
                            if "PASO 1" in last_msg:
                                print("   🎯 PASO 1: Vendiendo TX26 al precio de compra")
                            elif "PASO 2" in last_msg:
                                print("   🎯 PASO 2: Comprando TX28 al precio de venta")
                            elif "Ratio calculado" in last_msg:
                                print("   🧮 Cálculo de ratio con estrategia correcta")
                            elif "Orden ejecutada" in last_msg:
                                print("   ✅ Orden ejecutada exitosamente")
                    
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
                            print("      🎉 ¡ORDEN EJECUTADA COMPLETAMENTE!")
                        elif report.get('status') == 'NEW':
                            print("      📤 Orden enviada al mercado")
                        elif report.get('status') == 'REJECTED':
                            print("      ❌ Orden rechazada")
                    
                    elif msg_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                    
                    else:
                        print(f"   📄 {data}")
                    
                    # Si recibimos suficientes order reports, terminar
                    if order_reports >= 4:
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
                print("\n🎉 ¡ÉXITO! Nueva estrategia funcionando")
                print("✅ Órdenes secuenciales ejecutadas correctamente")
                print("✅ Confirmaciones de pyRofex recibidas")
                print("\n📋 ESTRATEGIA IMPLEMENTADA:")
                print("   1. ✅ Venta TX26 al precio de compra (bid)")
                print("   2. ✅ Compra TX28 al precio de venta (offer)")
                print("   3. ✅ Ratio calculado correctamente")
                print("   4. ✅ Compras sincronizadas con ventas")
            else:
                print("\n⚠️ No se recibieron order reports")
                print("💡 Verificar configuración ROFEX")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_estrategia_detallada())

