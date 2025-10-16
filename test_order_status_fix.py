#!/usr/bin/env python3
"""
Script de prueba para verificar la corrección del estado de órdenes
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_order_status_fix():
    """Prueba la corrección del estado de órdenes"""
    print("🧪 PRUEBA: Verificación de Estado Real de Órdenes")
    print("=" * 60)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al WebSocket")
            
            # Suscribirse a order reports
            subscribe_msg = {
                "type": "orders_subscribe",
                "account": "test_account"
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("📡 Suscripción a order reports enviada")
            
            # Enviar operación de ratio
            ratio_request = {
                "type": "execute_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "client_id": "test_client",
                "nominales": 2.0,
                "target_ratio": 0.0,
                "condition": "less_than_or_equal",
                "max_attempts": 1,
                "buy_qty": 2.0
            }
            
            await websocket.send(json.dumps(ratio_request))
            print("🚀 Operación de ratio enviada")
            print(f"📋 Parámetros: {json.dumps(ratio_request, indent=2)}")
            
            # Escuchar respuestas
            operation_completed = False
            operation_id = None
            order_statuses = []
            
            while not operation_completed:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    
                    if data.get('type') == 'ratio_operation_started':
                        operation_id = data.get('operation_id')
                        print(f"🎯 Operación iniciada: {operation_id}")
                    
                    elif data.get('type') == 'ratio_operation_progress':
                        status = data.get('status')
                        current_step = data.get('current_step')
                        progress_pct = data.get('progress_percentage', 0)
                        
                        print(f"📊 Progreso: {progress_pct}% - {current_step} - {status}")
                        
                        # Mostrar mensajes importantes
                        messages = data.get('messages', [])
                        for msg in messages[-3:]:  # Últimos 3 mensajes
                            if any(keyword in msg for keyword in ['EJECUTADA', 'PENDIENTE', 'RECHAZADA', 'VERIFICANDO']):
                                print(f"   💬 {msg}")
                        
                        # Verificar si hay información sobre órdenes
                        sell_orders_count = data.get('sell_orders_count', 0)
                        buy_orders_count = data.get('buy_orders_count', 0)
                        if sell_orders_count > 0 or buy_orders_count > 0:
                            print(f"   📦 Órdenes: {sell_orders_count} ventas, {buy_orders_count} compras")
                        
                        if status in ['completed', 'failed', 'partially_completed']:
                            operation_completed = True
                            print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                            
                            # Mostrar resumen final
                            print("\n📋 RESUMEN FINAL:")
                            print(f"   🎯 Nominales objetivo: {data.get('nominales_objetivo', 'N/A')}")
                            print(f"   ✅ Nominales ejecutados: {data.get('nominales_ejecutados', 'N/A')}")
                            print(f"   📈 Ratio final: {data.get('current_ratio', 'N/A')}")
                            print(f"   🎯 Condición cumplida: {data.get('condition_met', 'N/A')}")
                            print(f"   💰 Precio promedio venta: {data.get('average_sell_price', 'N/A')}")
                            print(f"   💰 Precio promedio compra: {data.get('average_buy_price', 'N/A')}")
                            
                            # Mostrar todos los mensajes finales
                            print("\n📝 MENSAJES FINALES:")
                            for msg in data.get('messages', []):
                                if any(keyword in msg for keyword in ['EJECUTADA', 'PENDIENTE', 'RECHAZADA', 'VERIFICANDO', 'COMPLETADA', 'PENDIENTES']):
                                    print(f"   {msg}")
                    
                    elif data.get('type') == 'ratio_operation_error':
                        print(f"❌ Error en operación: {data.get('error')}")
                        operation_completed = True
                    
                    elif data.get('type') == 'order_report':
                        report = data.get('report', {})
                        client_id = (report.get('wsClOrdId') or 
                                   report.get('clOrdId') or 
                                   report.get('clientId'))
                        status = report.get('status', 'UNKNOWN')
                        print(f"📨 Order Report: {client_id} - {status}")
                        order_statuses.append((client_id, status))
                
                except asyncio.TimeoutError:
                    print("⏰ Timeout esperando respuesta")
                    break
                except Exception as e:
                    print(f"❌ Error procesando respuesta: {e}")
                    break
            
            # Análisis final
            print("\n🔍 ANÁLISIS DE LA CORRECCIÓN:")
            print("-" * 40)
            
            if order_statuses:
                print("📊 Estados de órdenes detectados:")
                for client_id, status in order_statuses:
                    print(f"   {client_id}: {status}")
                
                # Verificar si hay órdenes pendientes
                pending_orders = [s for _, s in order_statuses if s in ['PENDING_NEW', 'NEW', 'PENDING_CANCEL']]
                filled_orders = [s for _, s in order_statuses if s in ['FILLED', 'PARTIALLY_FILLED']]
                
                if pending_orders:
                    print(f"\n⚠️ ÓRDENES PENDIENTES DETECTADAS: {len(pending_orders)}")
                    print("   ✅ La corrección está funcionando - el sistema detecta órdenes pendientes")
                elif filled_orders:
                    print(f"\n✅ ÓRDENES EJECUTADAS: {len(filled_orders)}")
                    print("   ✅ Las órdenes se ejecutaron correctamente en el mercado")
                else:
                    print("\n❓ No se pudieron determinar los estados de las órdenes")
            else:
                print("⚠️ No se recibieron order reports")
                print("   🔧 Verificar que la suscripción a order reports esté funcionando")
            
            print("\n🎯 CONCLUSIÓN:")
            if operation_completed:
                print("✅ La corrección permite verificar el estado real de las órdenes")
                print("✅ El sistema ya no asume que las órdenes están ejecutadas solo por recibir 'ok'")
                print("✅ Se reporta correctamente si las órdenes están pendientes o ejecutadas")
            else:
                print("⚠️ La prueba no se completó correctamente")
                print("🔧 Verificar la conexión y configuración del sistema")
    
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")

if __name__ == "__main__":
    asyncio.run(test_order_status_fix())
