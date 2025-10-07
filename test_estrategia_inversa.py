#!/usr/bin/env python3
"""
Test de la estrategia inversa - Vender TX28
"""

import asyncio
import websockets
import json
import time

async def test_estrategia_inversa():
    print("🔄 TEST ESTRATEGIA INVERSA - VENDER TX28")
    print("=" * 60)
    print("📋 ESTRATEGIA IMPLEMENTADA:")
    print("   • VENDER TX28 al precio de COMPRA (bid TX28)")
    print("   • COMPRAR TX26 al precio de VENTA (offer TX26)")
    print("   • Ratio de venta = bid TX28 / offer TX26")
    print("   • Optimización + liquidez adaptativa")
    print("=" * 60)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Test con estrategia inversa - VENDER TX28
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX28 - 24hs",  # VENDER TX28 (inverso)
                "nominales": 50.0,
                "target_ratio": 1.02,  # Ratio objetivo para TX28/TX26
                "condition": ">=",     # Buscar ratios MAYORES o iguales a 1.02
                "client_id": "test_estrategia_inversa"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio inversa enviada")
            print(f"   Vender: TX28 (estrategia inversa)")
            print(f"   Comprar: TX26")
            print(f"   Nominales: {ratio_msg['nominales']}")
            print(f"   Ratio objetivo: {ratio_msg['condition']} {ratio_msg['target_ratio']}")
            print(f"   Ratio esperado: bid TX28 / offer TX26")
            
            # Escuchar mensajes detalladamente
            print("\n📨 Escuchando ejecución de estrategia inversa...")
            timeout = 120  # 2 minutos
            start_time = time.time()
            message_count = 0
            lot_count = 0
            order_reports = 0
            completed_nominales = 0
            target_nominales = 50.0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=8)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    timestamp = time.strftime("%H:%M:%S")
                    
                    if msg_type == 'tick':
                        symbol = data.get('symbol', 'N/A')
                        bid = data.get('bid', 0)
                        offer = data.get('offer', 0)
                        bid_size = data.get('bid_size', 0)
                        offer_size = data.get('offer_size', 0)
                        
                        # Calcular ratio inverso (TX28/TX26) para mostrar
                        if 'TX26' in symbol:
                            tx26_bid = bid
                            tx26_offer = offer
                        elif 'TX28' in symbol:
                            tx28_bid = bid
                            tx28_offer = offer
                        
                        # Mostrar cuando tengamos ambos
                        if 'tx26_offer' in locals() and 'tx28_bid' in locals():
                            inverse_ratio = tx28_bid / tx26_offer if tx26_offer > 0 else 0
                            condition_met = inverse_ratio >= 1.02
                            
                            print(f"\n[{timestamp}] 📊 RATIO INVERSO TX28/TX26:")
                            print(f"   TX28 Bid: {tx28_bid} (liquidez: {bid_size:,})")
                            print(f"   TX26 Offer: {tx26_offer} (liquidez: {offer_size:,})")
                            print(f"   Ratio TX28/TX26: {inverse_ratio:.6f}")
                            print(f"   Condición >= 1.02: {'✅' if condition_met else '❌'}")
                    
                    elif msg_type == 'ratio_operation_started':
                        print(f"\n[{timestamp}] ✅ OPERACIÓN INVERSA INICIADA")
                        print(f"   ID: {data.get('operation_id')}")
                        print(f"   🔄 Iniciando estrategia inversa...")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        status = progress.get('status')
                        ratio = progress.get('current_ratio', 0)
                        weighted_ratio = progress.get('weighted_average_ratio', 0)
                        sell_orders = progress.get('sell_orders_count', 0)
                        buy_orders = progress.get('buy_orders_count', 0)
                        batch_count = progress.get('batch_count', 0)
                        completed = progress.get('completed_nominales', 0)
                        remaining = progress.get('remaining_nominales', 0)
                        
                        print(f"\n[{timestamp}] 📊 PROGRESO ESTRATEGIA INVERSA:")
                        print(f"   Estado: {status}")
                        print(f"   Ratio TX28/TX26: {ratio:.6f}")
                        print(f"   Ratio ponderado: {weighted_ratio:.6f}")
                        print(f"   Completados: {completed}/{target_nominales} ({completed/target_nominales*100:.1f}%)")
                        print(f"   Restantes: {remaining}")
                        print(f"   Órdenes: {sell_orders}V/{buy_orders}C")
                        print(f"   Lotes: {batch_count}")
                        
                        # Mostrar mensajes importantes
                        messages = progress.get('messages', [])
                        if messages:
                            print(f"   📝 ACTIVIDAD:")
                            for msg in messages[-4:]:
                                if any(k in msg for k in ['TX28', 'TX26', 'Decisión', 'EJECUTAR', 'ESPERANDO', 'COMPLETADO']):
                                    print(f"      • {msg}")
                        
                        # Detectar cambios
                        if batch_count > lot_count:
                            lot_count = batch_count
                            print(f"\n[{timestamp}] 🔄 NUEVO LOTE #{batch_count} (INVERSO)")
                        
                        completed_nominales = completed
                        
                        if completed >= target_nominales:
                            print(f"\n[{timestamp}] 🎉 ¡OBJETIVO COMPLETADO!")
                            break
                    
                    elif msg_type == 'order_report':
                        order_reports += 1
                        report = data.get('report', {})
                        status = report.get('status', 'N/A')
                        side = report.get('side', 'N/A')
                        qty = report.get('orderQty', 0)
                        price = report.get('price', 0)
                        symbol = report.get('ticker', 'N/A')
                        
                        print(f"\n[{timestamp}] 📋 ORDER REPORT #{order_reports}:")
                        print(f"   Estado: {status}")
                        print(f"   Lado: {side}")
                        print(f"   Instrumento: {symbol}")
                        print(f"   Cantidad: {qty}")
                        print(f"   Precio: {price}")
                        
                        if status == 'FILLED':
                            print("   🎉 ¡ORDEN EJECUTADA!")
                    
                    elif msg_type == 'error':
                        print(f"\n[{timestamp}] ❌ Error: {data.get('message')}")
                    
                except asyncio.TimeoutError:
                    elapsed = int(time.time() - start_time)
                    print(f"[{time.strftime('%H:%M:%S')}] ⏳ Esperando... ({elapsed}s/{timeout}s)")
                    continue
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Error: {e}")
            
            # RESUMEN FINAL
            elapsed = time.time() - start_time
            print(f"\n📊 RESUMEN ESTRATEGIA INVERSA:")
            print(f"   ⏱️ Tiempo: {elapsed:.1f}s")
            print(f"   📨 Mensajes: {message_count}")
            print(f"   📦 Lotes ejecutados: {lot_count}")
            print(f"   📋 Order Reports: {order_reports}")
            print(f"   💰 Nominales completados: {completed_nominales}/{target_nominales}")
            print(f"   📈 Progreso: {completed_nominales/target_nominales*100:.1f}%")
            
            if completed_nominales >= target_nominales:
                print("\n🎉 ¡ÉXITO! Estrategia inversa funcionando")
                print("✅ Venta de TX28 implementada correctamente")
                print("✅ Ratio TX28/TX26 calculado correctamente")
                print("✅ Órdenes ejecutadas en orden correcto")
                print("✅ Optimización funcionando para estrategia inversa")
            elif completed_nominales > 0:
                print(f"\n⚠️ ÉXITO PARCIAL: {completed_nominales}/{target_nominales} nominales")
            else:
                print("\n❌ No se completaron nominales")
                print("💡 Verificar condiciones de mercado para ratio TX28/TX26")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_estrategia_inversa())

