#!/usr/bin/env python3
import asyncio
import websockets
import json
import time

async def monitorear():
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    async with websockets.connect(uri) as websocket:
        print("🚀 MONITOREO DE OPERACIÓN EN VIVO")
        print("=" * 50)
        
        # Buscar la operación existente
        msg = {
            "type": "get_ratio_operation_status",
            "operation_id": "TX26-TX28_c271ef85"  # ID de la operación anterior
        }
        
        await websocket.send(json.dumps(msg))
        print("📤 Consultando estado de la operación...")
        
        # Monitorear por 2 minutos
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < 120:  # 2 minutos
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                msg_type = data.get('type', 'unknown')
                message_count += 1
                
                timestamp = time.strftime("%H:%M:%S")
                
                if msg_type == 'ratio_operation_progress':
                    progress = data.get('progress', {})
                    status = progress.get('status')
                    ratio = progress.get('current_ratio', 0)
                    weighted_ratio = progress.get('weighted_average_ratio', 0)
                    completed = progress.get('completed_nominales', 0)
                    remaining = progress.get('remaining_nominales', 0)
                    batch_count = progress.get('batch_count', 0)
                    sell_orders = progress.get('sell_orders_count', 0)
                    buy_orders = progress.get('buy_orders_count', 0)
                    
                    print(f"\n[{timestamp}] 📊 ESTADO:")
                    print(f"   Status: {status}")
                    print(f"   Ratio actual: {ratio:.6f}")
                    print(f"   Ratio ponderado: {weighted_ratio:.6f}")
                    print(f"   Completados: {completed}/100 ({completed/100*100:.1f}%)")
                    print(f"   Restantes: {remaining}")
                    print(f"   Lotes: {batch_count}")
                    print(f"   Órdenes: {sell_orders}V/{buy_orders}C")
                    
                    # Mostrar mensajes recientes
                    messages = progress.get('messages', [])
                    if messages:
                        print("   📝 ACTIVIDAD:")
                        for msg in messages[-3:]:
                            if any(k in msg for k in ['Decisión', 'EJECUTAR', 'ESPERANDO', 'COMPLETADO', 'LOTE', 'Ratio']):
                                print(f"      • {msg}")
                    
                    if completed >= 100:
                        print(f"\n🎉 ¡OPERACIÓN COMPLETADA!")
                        break
                
                elif msg_type == 'order_report':
                    report = data.get('report', {})
                    status = report.get('status', 'N/A')
                    side = report.get('side', 'N/A')
                    qty = report.get('orderQty', 0)
                    price = report.get('price', 0)
                    symbol = report.get('ticker', 'N/A')
                    
                    print(f"\n[{timestamp}] 📋 ORDER REPORT:")
                    print(f"   Estado: {status}")
                    print(f"   Lado: {side}")
                    print(f"   Instrumento: {symbol}")
                    print(f"   Cantidad: {qty}")
                    print(f"   Precio: {price}")
                    
                    if status == 'FILLED':
                        print("   🎉 ¡ORDEN EJECUTADA!")
                
                elif msg_type == 'tick':
                    symbol = data.get('symbol', '')
                    if 'TX26' in symbol or 'TX28' in symbol:
                        bid = data.get('bid', 0)
                        offer = data.get('offer', 0)
                        ratio = bid / offer if offer > 0 else 0
                        condition_met = ratio <= 0.9706
                        print(f"\n[{timestamp}] 📈 {symbol}:")
                        print(f"   Bid: {bid} / Offer: {offer}")
                        print(f"   Ratio: {ratio:.6f}")
                        print(f"   Condición ≤ 0.9706: {'✅' if condition_met else '❌'}")
                
                else:
                    print(f"\n[{timestamp}] 📄 {msg_type.upper()}: {data}")
                
            except asyncio.TimeoutError:
                elapsed = int(time.time() - start_time)
                print(f"[{time.strftime('%H:%M:%S')}] ⏳ Esperando... ({elapsed}s/120s)")
                continue
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Error: {e}")
        
        print(f"\n📊 RESUMEN:")
        print(f"   Mensajes: {message_count}")
        print(f"   Tiempo: {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    asyncio.run(monitorear())

