#!/usr/bin/env python3
"""
Test de ejecución en vivo con parámetros específicos
"""

import asyncio
import websockets
import json
import time

async def test_live_execution():
    print("🚀 EJECUCIÓN EN VIVO - OPERACIÓN DE RATIO")
    print("=" * 70)
    print("📋 PARÁMETROS DE LA OPERACIÓN:")
    print("   Par: TX26/TX28")
    print("   Vender: MERV - XMEV - TX26 - 24hs")
    print("   Nominales: 100.0")
    print("   Ratio objetivo: ≤ 0.9706")
    print("   Condición: <=")
    print("   Estrategia: Optimización + Liquidez adaptativa")
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
                "target_ratio": 0.9706,
                "condition": "<=",
                "client_id": "test_client_002"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada al servidor")
            print(f"   🎯 Objetivo: {ratio_msg['nominales']} nominales")
            print(f"   📈 Ratio objetivo: {ratio_msg['condition']} {ratio_msg['target_ratio']}")
            print(f"   🔄 Estrategia: Optimización + Liquidez adaptativa")
            
            # Escuchar mensajes en tiempo real
            print("\n📨 MONITOREO EN TIEMPO REAL...")
            timeout = 300  # 5 minutos para operación grande
            start_time = time.time()
            message_count = 0
            lot_count = 0
            wait_attempts = 0
            executions = 0
            order_reports = 0
            completed_nominales = 0
            target_nominales = 100.0
            last_ratio = 0
            last_weighted_ratio = 0
            
            print(f"⏰ Iniciando monitoreo por {timeout} segundos...")
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
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
                        
                        # Calcular ratio actual
                        current_ratio = bid / offer if offer > 0 else 0
                        condition_met = current_ratio <= 0.9706
                        
                        print(f"\n[{timestamp}] 📊 {symbol}:")
                        print(f"   Bid: {bid} (liquidez: {bid_size:,})")
                        print(f"   Offer: {offer} (liquidez: {offer_size:,})")
                        print(f"   Ratio: {current_ratio:.6f}")
                        print(f"   Condición ≤ 0.9706: {'✅' if condition_met else '❌'}")
                        
                        if condition_met and current_ratio != last_ratio:
                            print(f"   🎯 ¡OPORTUNIDAD! Ratio {current_ratio:.6f} cumple condición")
                        
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
                        
                        print(f"\n[{timestamp}] 📊 PROGRESO:")
                        print(f"   Estado: {status}")
                        print(f"   Ratio actual: {ratio:.6f}")
                        print(f"   Ratio ponderado: {weighted_ratio:.6f}")
                        print(f"   Progreso: {progress_pct:.1f}%")
                        print(f"   Completados: {completed}/{target_nominales} ({completed/target_nominales*100:.1f}%)")
                        print(f"   Restantes: {remaining}")
                        print(f"   Órdenes: {sell_orders}V/{buy_orders}C")
                        print(f"   Lotes: {batch_count}")
                        
                        # Mostrar mensajes importantes
                        messages = progress.get('messages', [])
                        if messages:
                            print(f"   📝 ACTIVIDAD RECIENTE:")
                            for msg in messages[-3:]:  # Últimos 3 mensajes
                                if any(keyword in msg for keyword in ["Decisión", "EJECUTAR", "ESPERANDO", "COMPLETADO", "LOTE"]):
                                    print(f"      • {msg}")
                        
                        # Detectar cambios importantes
                        if batch_count > lot_count:
                            lot_count = batch_count
                            print(f"\n[{timestamp}] 🔄 NUEVO LOTE #{batch_count}")
                        
                        if weighted_ratio != last_weighted_ratio and weighted_ratio > 0:
                            print(f"\n[{timestamp}] 📈 Ratio ponderado actualizado: {weighted_ratio:.6f}")
                            last_weighted_ratio = weighted_ratio
                        
                        # Contar eventos
                        for msg in messages:
                            if "ESPERANDO por mejores precios" in msg:
                                wait_attempts += 1
                                print(f"   ⏳ Espera #{wait_attempts}")
                            elif "EJECUTAR" in msg:
                                executions += 1
                                print(f"   ✅ Ejecución #{executions}")
                        
                        completed_nominales = completed
                        
                        # Si completó todo, terminar
                        if completed >= target_nominales:
                            print(f"\n[{timestamp}] 🎉 ¡OPERACIÓN COMPLETADA!")
                            print(f"   ✅ {completed}/{target_nominales} nominales ejecutados")
                            break
                    
                    elif msg_type == 'order_report':
                        order_reports += 1
                        report = data.get('report', {})
                        client_id = report.get('wsClOrdId', 'N/A')
                        status = report.get('status', 'N/A')
                        side = report.get('side', 'N/A')
                        qty = report.get('orderQty', 0)
                        price = report.get('price', 0)
                        symbol = report.get('ticker', 'N/A')
                        
                        print(f"\n[{timestamp}] 📋 ORDER REPORT #{order_reports}:")
                        print(f"   ID: {client_id}")
                        print(f"   Estado: {status}")
                        print(f"   Lado: {side}")
                        print(f"   Instrumento: {symbol}")
                        print(f"   Cantidad: {qty}")
                        print(f"   Precio: {price}")
                        
                        if status == 'FILLED':
                            print("   🎉 ¡ORDEN EJECUTADA COMPLETAMENTE!")
                        elif status == 'NEW':
                            print("   📤 Orden enviada al mercado")
                        elif status == 'REJECTED':
                            print("   ❌ Orden rechazada")
                    
                    elif msg_type == 'error':
                        print(f"\n[{timestamp}] ❌ ERROR: {data.get('message')}")
                    
                except asyncio.TimeoutError:
                    elapsed = int(time.time() - start_time)
                    remaining_time = timeout - elapsed
                    print(f"[{time.strftime('%H:%M:%S')}] ⏳ Esperando... ({elapsed}s/{timeout}s) - Restantes: {remaining_time}s")
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
            print(f"⏳ Intentos de espera: {wait_attempts}")
            print(f"✅ Ejecuciones: {executions}")
            print(f"📋 Order Reports: {order_reports}")
            print(f"💰 Nominales completados: {completed_nominales}/{target_nominales}")
            print(f"📈 Progreso final: {completed_nominales/target_nominales*100:.1f}%")
            
            if completed_nominales >= target_nominales:
                print(f"\n🎉 ¡ÉXITO TOTAL!")
                print("✅ Operación completada exitosamente")
                print("✅ Estrategia de optimización funcionando")
                print("✅ Liquidez adaptativa implementada")
                print("✅ Órdenes reales ejecutadas en ROFEX")
            elif completed_nominales > 0:
                print(f"\n⚠️ ÉXITO PARCIAL")
                print(f"✅ {completed_nominales}/{target_nominales} nominales ejecutados")
                print("💡 Posibles causas del paro:")
                print("   • Timeout del test")
                print("   • Optimización muy estricta")
                print("   • Liquidez insuficiente")
            else:
                print("\n❌ No se completaron nominales")
                print("💡 Verificar:")
                print("   • ROFEX conectado")
                print("   • Condiciones de mercado")
                print("   • Configuración de la operación")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("💡 Verificar que el servidor esté ejecutándose")

if __name__ == "__main__":
    asyncio.run(test_live_execution())

