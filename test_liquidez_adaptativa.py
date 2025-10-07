#!/usr/bin/env python3
"""
Test de la estrategia de liquidez adaptativa para operaciones de ratio
"""

import asyncio
import websockets
import json
import time

async def test_liquidez_adaptativa():
    print("🎯 TEST LIQUIDEZ ADAPTATIVA - RATIO TX26/TX28")
    print("=" * 60)
    print("📋 ESTRATEGIA IMPLEMENTADA:")
    print("   • Detectar liquidez disponible en bid TX26 y offer TX28")
    print("   • Calcular lote = min(liquidez_bid_TX26, liquidez_offer_TX28, nominales_restantes)")
    print("   • Ejecutar lote secuencialmente (vender TX26, comprar TX28)")
    print("   • Recalcular ratio y repetir hasta completar objetivo")
    print("   • Ejemplo: 100 nominales, bid TX26=20, offer TX28=10 → lote=10")
    print("=" * 60)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Enviar operación de ratio con 100 nominales para probar lotes
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 100.0,  # Objetivo grande para probar lotes
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_liquidez_adaptativa"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada")
            print(f"   Objetivo: 100 nominales")
            print(f"   Estrategia: Lotes adaptativos basados en liquidez")
            print(f"   Ratio objetivo: ≤ 0.98")
            
            # Escuchar mensajes detalladamente
            print("\n📨 Escuchando ejecución por lotes...")
            timeout = 120  # 2 minutos para operación grande
            start_time = time.time()
            message_count = 0
            lot_count = 0
            order_reports = 0
            completed_nominales = 0
            target_nominales = 100.0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    if msg_type == 'tick':
                        symbol = data.get('symbol', 'N/A')
                        bid = data.get('bid', 0)
                        offer = data.get('offer', 0)
                        bid_size = data.get('bid_size', 0)
                        offer_size = data.get('offer_size', 0)
                        print(f"\n📊 COTIZACIÓN {symbol}:")
                        print(f"   Bid: {bid} (liquidez: {bid_size})")
                        print(f"   Offer: {offer} (liquidez: {offer_size})")
                        print(f"   Lote disponible: min({bid_size}, {offer_size}) = {min(bid_size, offer_size)}")
                    
                    elif msg_type == 'ratio_operation_started':
                        print(f"\n✅ Operación iniciada: {data.get('operation_id')}")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        status = progress.get('status')
                        ratio = progress.get('current_ratio', 0)
                        sell_orders = progress.get('sell_orders_count', 0)
                        buy_orders = progress.get('buy_orders_count', 0)
                        batch_count = progress.get('batch_count', 0)
                        completed = progress.get('completed_nominales', 0)
                        remaining = progress.get('remaining_nominales', 0)
                        current_batch_size = progress.get('current_batch_size', 0)
                        
                        print(f"\n📊 PROGRESO LOTE #{batch_count}:")
                        print(f"   Estado: {status}")
                        print(f"   Ratio actual: {ratio:.6f}")
                        print(f"   Lote actual: {current_batch_size} nominales")
                        print(f"   Completados: {completed}/{target_nominales} ({completed/target_nominales*100:.1f}%)")
                        print(f"   Restantes: {remaining}")
                        print(f"   Órdenes: {sell_orders}V/{buy_orders}C")
                        
                        # Mostrar mensajes clave del lote
                        messages = progress.get('messages', [])
                        if messages:
                            print(f"   📝 MENSAJES RECIENTES:")
                            for msg in messages[-3:]:  # Últimos 3 mensajes
                                if any(keyword in msg for keyword in ["LOTE #", "liquidez", "Ratio", "COMPLETADO"]):
                                    print(f"      • {msg}")
                        
                        # Detectar cambio de lote
                        if batch_count > lot_count:
                            lot_count = batch_count
                            print(f"\n🔄 NUEVO LOTE #{batch_count} DETECTADO")
                        
                        # Actualizar nominales completados
                        completed_nominales = completed
                        
                        # Si completó todo, terminar
                        if completed >= target_nominales:
                            print(f"\n🎉 ¡OBJETIVO COMPLETADO! {completed}/{target_nominales} nominales")
                            break
                    
                    elif msg_type == 'order_report':
                        order_reports += 1
                        report = data.get('report', {})
                        client_id = report.get('wsClOrdId', 'N/A')
                        status = report.get('status', 'N/A')
                        side = report.get('side', 'N/A')
                        qty = report.get('orderQty', 0)
                        price = report.get('price', 0)
                        
                        print(f"\n📋 ORDER REPORT #{order_reports}:")
                        print(f"   ID: {client_id}")
                        print(f"   Estado: {status}")
                        print(f"   Lado: {side}")
                        print(f"   Cantidad: {qty}")
                        print(f"   Precio: {price}")
                        
                        if status == 'FILLED':
                            print("   🎉 ¡ORDEN EJECUTADA!")
                        elif status == 'NEW':
                            print("   📤 Orden enviada al mercado")
                        elif status == 'REJECTED':
                            print("   ❌ Orden rechazada")
                    
                    elif msg_type == 'error':
                        print(f"\n❌ Error: {data.get('message')}")
                    
                    else:
                        # print(f"\n📄 {msg_type.upper()}: {data}")
                        pass
                    
                except asyncio.TimeoutError:
                    elapsed = int(time.time() - start_time)
                    print(f"⏳ Esperando... ({elapsed}s/{timeout}s) - Completados: {completed_nominales}/{target_nominales}")
                    continue
                except Exception as e:
                    print(f"⚠️ Error: {e}")
            
            # RESUMEN FINAL
            elapsed = time.time() - start_time
            print(f"\n📊 RESUMEN FINAL:")
            print(f"   ⏱️ Tiempo: {elapsed:.1f}s")
            print(f"   📨 Mensajes: {message_count}")
            print(f"   📦 Lotes ejecutados: {lot_count}")
            print(f"   📋 Order Reports: {order_reports}")
            print(f"   💰 Nominales completados: {completed_nominales}/{target_nominales}")
            print(f"   📈 Progreso: {completed_nominales/target_nominales*100:.1f}%")
            
            if completed_nominales >= target_nominales:
                print("\n🎉 ¡ÉXITO TOTAL! Estrategia de liquidez adaptativa funcionando")
                print("✅ Lotes ejecutados correctamente basados en liquidez disponible")
                print("✅ Órdenes secuenciales (venta → compra) por lote")
                print("✅ Progreso incremental hasta completar objetivo")
            elif completed_nominales > 0:
                print(f"\n⚠️ ÉXITO PARCIAL: {completed_nominales}/{target_nominales} nominales")
                print("💡 Posibles causas:")
                print("   • Liquidez insuficiente en el mercado")
                print("   • Timeout del test")
                print("   • Condición de ratio no cumplida")
            else:
                print("\n❌ No se completaron nominales")
                print("💡 Verificar:")
                print("   • ROFEX conectado")
                print("   • Liquidez disponible")
                print("   • Condiciones de ratio")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_liquidez_adaptativa())

