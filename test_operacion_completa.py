#!/usr/bin/env python3
"""
Test completo desde cero - Operación de ratio específica
"""

import asyncio
import websockets
import json
import time

async def test_operacion_completa():
    print("🚀 TEST COMPLETO - OPERACIÓN DE RATIO DESDE CERO")
    print("=" * 70)
    print("📋 PARÁMETROS DE LA OPERACIÓN:")
    print("   Par: TX26/TX28")
    print("   Vender: MERV - XMEV - TX26 - 24hs")
    print("   Nominales: 100.0")
    print("   Ratio objetivo: ≤ 0.976")
    print("   Condición: <=")
    print("   Timeout: 180 segundos (3 minutos)")
    print("=" * 70)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Parámetros exactos proporcionados por el usuario
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": [
                    "MERV - XMEV - TX26 - 24hs",
                    "MERV - XMEV - TX28 - 24hs"
                ],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 100.0,
                "target_ratio": 0.976,
                "condition": "<=",
                "client_id": "test_client_002"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada")
            print(f"   🎯 Objetivo: {ratio_msg['nominales']} nominales")
            print(f"   📈 Ratio objetivo: {ratio_msg['condition']} {ratio_msg['target_ratio']}")
            print(f"   🔄 Estrategia: TX26/TX28 con optimización")
            
            # Monitorear con timeout para evitar bucles infinitos
            print("\n📨 MONITOREO CON TIMEOUT (180 segundos)...")
            timeout = 180  # 3 minutos máximo
            start_time = time.time()
            message_count = 0
            lot_count = 0
            order_reports = 0
            completed_nominales = 0
            target_nominales = 100.0
            last_ratio = 0
            last_weighted_ratio = 0
            execution_count = 0
            wait_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    timestamp = time.strftime("%H:%M:%S")
                    elapsed = int(time.time() - start_time)
                    
                    if msg_type == 'tick':
                        symbol = data.get('symbol', 'N/A')
                        if 'TX26' in symbol or 'TX28' in symbol:
                            bid = data.get('bid', 0)
                            offer = data.get('offer', 0)
                            bid_size = data.get('bid_size', 0)
                            offer_size = data.get('offer_size', 0)
                            
                            # Calcular ratio TX26/TX28
                            if 'TX26' in symbol:
                                tx26_bid = bid
                                tx26_offer = offer
                            elif 'TX28' in symbol:
                                tx28_bid = bid
                                tx28_offer = offer
                            
                            # Mostrar cuando tengamos ambos
                            if 'tx26_bid' in locals() and 'tx28_offer' in locals():
                                current_ratio = tx26_bid / tx28_offer if tx28_offer > 0 else 0
                                condition_met = current_ratio <= 0.976
                                
                                if current_ratio != last_ratio:
                                    print(f"\n[{timestamp}] 📊 {symbol}:")
                                    print(f"   TX26 Bid: {tx26_bid} (liquidez: {bid_size:,})")
                                    print(f"   TX28 Offer: {tx28_offer} (liquidez: {offer_size:,})")
                                    print(f"   Ratio TX26/TX28: {current_ratio:.6f}")
                                    print(f"   Condición ≤ 0.976: {'✅' if condition_met else '❌'}")
                                    last_ratio = current_ratio
                    
                    elif msg_type == 'ratio_operation_started':
                        operation_id = data.get('operation_id')
                        print(f"\n[{timestamp}] ✅ OPERACIÓN INICIADA")
                        print(f"   ID: {operation_id}")
                        print(f"   🚀 Iniciando estrategia de optimización...")
                    
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
                        progress_pct = progress.get('progress_percentage', 0)
                        
                        # Mostrar progreso cada 30 segundos o en cambios importantes
                        if elapsed % 30 == 0 or ratio != last_ratio or weighted_ratio != last_weighted_ratio:
                            print(f"\n[{timestamp}] 📊 PROGRESO ({elapsed}s/180s):")
                            print(f"   Estado: {status}")
                            print(f"   Ratio actual: {ratio:.6f}")
                            print(f"   Ratio ponderado: {weighted_ratio:.6f}")
                            print(f"   Progreso: {progress_pct:.1f}%")
                            print(f"   Completados: {completed}/{target_nominales} ({completed/target_nominales*100:.1f}%)")
                            print(f"   Restantes: {remaining}")
                            print(f"   Órdenes: {sell_orders}V/{buy_orders}C")
                            print(f"   Lotes: {batch_count}")
                            
                            last_ratio = ratio
                            last_weighted_ratio = weighted_ratio
                        
                        # Contar eventos importantes
                        messages = progress.get('messages', [])
                        for msg in messages:
                            if "EJECUTAR" in msg:
                                execution_count += 1
                                print(f"   ✅ Ejecución #{execution_count}")
                            elif "ESPERANDO" in msg:
                                wait_count += 1
                                if wait_count % 5 == 0:  # Mostrar cada 5 esperas
                                    print(f"   ⏳ Esperas: {wait_count}")
                        
                        # Detectar cambios de lote
                        if batch_count > lot_count:
                            lot_count = batch_count
                            print(f"\n[{timestamp}] 🔄 LOTE #{batch_count} DETECTADO")
                        
                        completed_nominales = completed
                        
                        # Si completó todo, terminar
                        if completed >= target_nominales:
                            print(f"\n[{timestamp}] 🎉 ¡OBJETIVO COMPLETADO!")
                            break
                        
                        # Si no hay progreso por mucho tiempo, mostrar advertencia
                        if elapsed > 60 and completed == 0:
                            print(f"\n[{timestamp}] ⚠️ Sin ejecuciones después de {elapsed}s")
                            print("   💡 Posibles causas:")
                            print("   • Ratio actual no cumple condición")
                            print("   • Optimización muy estricta")
                            print("   • Esperando mejores precios")
                    
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
                    remaining_time = timeout - elapsed
                    if elapsed % 60 == 0:  # Mostrar cada minuto
                        print(f"[{timestamp}] ⏳ Esperando... ({elapsed}s/180s) - Restantes: {remaining_time}s")
                        print(f"   Completados: {completed_nominales}/{target_nominales}")
                    continue
                except Exception as e:
                    print(f"\n[{time.strftime('%H:%M:%S')}] ⚠️ Error: {e}")
            
            # RESUMEN FINAL
            elapsed = time.time() - start_time
            print(f"\n🏁 RESUMEN FINAL DE LA OPERACIÓN:")
            print("=" * 50)
            print(f"⏱️ Tiempo total: {elapsed:.1f} segundos")
            print(f"📨 Mensajes recibidos: {message_count}")
            print(f"📦 Lotes ejecutados: {lot_count}")
            print(f"⏳ Intentos de espera: {wait_count}")
            print(f"✅ Ejecuciones: {execution_count}")
            print(f"📋 Order Reports: {order_reports}")
            print(f"💰 Nominales completados: {completed_nominales}/{target_nominales}")
            print(f"📈 Progreso final: {completed_nominales/target_nominales*100:.1f}%")
            
            if completed_nominales >= target_nominales:
                print(f"\n🎉 ¡ÉXITO TOTAL!")
                print("✅ Operación completada exitosamente")
                print("✅ Estrategia de optimización funcionando")
                print("✅ Liquidez adaptativa implementada")
                print("✅ Órdenes reales ejecutadas en ROFEX")
                print("✅ Sin bucles infinitos - timeout respetado")
            elif completed_nominales > 0:
                print(f"\n⚠️ ÉXITO PARCIAL")
                print(f"✅ {completed_nominales}/{target_nominales} nominales ejecutados")
                print("💡 Posibles causas del paro:")
                print("   • Timeout del test (3 minutos)")
                print("   • Optimización muy estricta")
                print("   • Liquidez insuficiente")
                print("   • Condición no cumplida en el tiempo")
            else:
                print("\n❌ No se completaron nominales")
                print("💡 Verificar:")
                print("   • ROFEX conectado correctamente")
                print("   • Condiciones de mercado actuales")
                print("   • Configuración de la operación")
                print("   • Ratio objetivo vs condiciones reales")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("💡 Verificar que el servidor esté ejecutándose")

if __name__ == "__main__":
    asyncio.run(test_operacion_completa())


