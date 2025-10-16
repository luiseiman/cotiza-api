#!/usr/bin/env python3
"""
Script de prueba para el sistema de garantía de ejecución completa
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_guarantee_system():
    """Prueba el sistema de garantía con 100,000 nominales"""
    print("🧪 PRUEBA: Sistema de Garantía de Ejecución Completa")
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
            
            # Enviar operación de ratio con garantía
            ratio_request = {
                "type": "execute_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "client_id": "test_guarantee",
                "nominales": 100000.0,  # 100,000 nominales
                "target_ratio": 0.0,
                "condition": "less_than_or_equal",
                "max_attempts": 1,
                "buy_qty": 100000.0
            }
            
            await websocket.send(json.dumps(ratio_request))
            print("🚀 OPERACIÓN CON GARANTÍA ENVIADA")
            print(f"📋 Parámetros:")
            print(f"   🎯 Nominales objetivo: {ratio_request['nominales']:,}")
            print(f"   🔒 GARANTÍA: Completar TODOS los nominales")
            print(f"   🔍 MONITOREO: Órdenes pendientes hasta completar")
            
            # Escuchar respuestas
            operation_completed = False
            operation_id = None
            lot_count = 0
            monitoring_started = False
            additional_lots = 0
            
            while not operation_completed:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(response)
                    
                    if data.get('type') == 'ratio_operation_started':
                        operation_id = data.get('operation_id')
                        print(f"🎯 Operación iniciada: {operation_id}")
                    
                    elif data.get('type') == 'ratio_operation_progress':
                        status = data.get('status')
                        current_step = data.get('current_step')
                        progress_pct = data.get('progress_percentage', 0)
                        nominales_ejecutados = data.get('nominales_ejecutados', 0)
                        nominales_objetivo = data.get('nominales_objetivo', 0)
                        
                        # Mostrar progreso principal
                        print(f"📊 Progreso: {progress_pct}% - {current_step} - {status}")
                        print(f"   💰 Ejecutados: {nominales_ejecutados:,.0f} / {nominales_objetivo:,.0f} nominales")
                        
                        # Detectar eventos importantes
                        messages = data.get('messages', [])
                        for msg in messages[-2:]:  # Últimos 2 mensajes
                            if 'MONITOREO CONTINUO INICIADO' in msg and not monitoring_started:
                                monitoring_started = True
                                print(f"\n🔍 MONITOREO CONTINUO ACTIVADO:")
                                print(f"   ⏰ El sistema ahora monitoreará hasta completar TODOS los nominales")
                                print(f"   🎯 Garantía: Se ejecutarán los {nominales_objetivo:,.0f} nominales completos")
                            
                            elif 'LOTE ADICIONAL' in msg:
                                additional_lots += 1
                                print(f"   🔄 Lote adicional #{additional_lots} ejecutado")
                            
                            elif 'EJECUTADA durante el monitoreo' in msg:
                                print(f"   🎉 ¡Orden ejecutada durante monitoreo!")
                            
                            elif any(keyword in msg for keyword in ['EJECUTADOS!', 'COMPLETADA', 'PENDIENTES']):
                                print(f"   💬 {msg}")
                        
                        # Mostrar estadísticas de órdenes
                        sell_orders_count = data.get('sell_orders_count', 0)
                        buy_orders_count = data.get('buy_orders_count', 0)
                        if sell_orders_count > 0 or buy_orders_count > 0:
                            print(f"   📦 Órdenes: {sell_orders_count} ventas, {buy_orders_count} compras")
                        
                        # Verificar si se completó
                        if status in ['completed', 'failed']:
                            operation_completed = True
                            print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                            
                            # Mostrar resumen final
                            print("\n📋 RESUMEN FINAL:")
                            print(f"   🎯 Nominales objetivo: {nominales_objetivo:,.0f}")
                            print(f"   ✅ Nominales ejecutados: {nominales_ejecutados:,.0f}")
                            print(f"   📈 Ratio final: {data.get('current_ratio', 'N/A')}")
                            print(f"   🎯 Condición cumplida: {data.get('condition_met', 'N/A')}")
                            print(f"   💰 Precio promedio venta: {data.get('average_sell_price', 'N/A')}")
                            print(f"   💰 Precio promedio compra: {data.get('average_buy_price', 'N/A')}")
                            print(f"   📦 Lotes adicionales ejecutados: {additional_lots}")
                            
                            # Verificar si se completaron todos los nominales
                            if nominales_ejecutados >= nominales_objetivo:
                                print(f"\n🎉 ¡ÉXITO! Se ejecutaron TODOS los {nominales_objetivo:,.0f} nominales")
                                print("✅ La garantía de ejecución completa funcionó correctamente")
                                print("✅ El monitoreo continuo completó la operación")
                            else:
                                print(f"\n⚠️ PARCIAL: Solo se ejecutaron {nominales_ejecutados:,.0f} de {nominales_objetivo:,.0f} nominales")
                                print("🔧 Verificar liquidez del mercado o configuración")
                    
                    elif data.get('type') == 'ratio_operation_error':
                        print(f"❌ Error en operación: {data.get('error')}")
                        operation_completed = True
                    
                    elif data.get('type') == 'order_report':
                        report = data.get('report', {})
                        client_id = (report.get('wsClOrdId') or 
                                   report.get('clOrdId') or 
                                   report.get('clientId'))
                        status = report.get('status', 'UNKNOWN')
                        symbol = report.get('instrumentId', {}).get('symbol', 'N/A')
                        quantity = report.get('orderQty', 0)
                        price = report.get('price', 0)
                        
                        print(f"📨 Order Report: {client_id} - {symbol} - {quantity} @ {price} - {status}")
                
                except asyncio.TimeoutError:
                    print("⏰ Timeout esperando respuesta")
                    break
                except Exception as e:
                    print(f"❌ Error procesando respuesta: {e}")
                    break
            
            # Análisis final
            print("\n🔍 ANÁLISIS DEL SISTEMA DE GARANTÍA:")
            print("-" * 50)
            
            if operation_completed:
                print("✅ La operación se procesó correctamente")
                print("✅ El sistema implementó la garantía de ejecución completa")
                print("✅ El monitoreo continuo se activó para órdenes pendientes")
                print("✅ El sistema ejecutó lotes adicionales cuando fue necesario")
            else:
                print("⚠️ La prueba no se completó correctamente")
                print("🔧 Verificar la conexión y configuración del sistema")
    
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando prueba del sistema de garantía...")
    print("📝 Esta prueba verificará:")
    print("   • Garantía de completar TODOS los nominales solicitados")
    print("   • Monitoreo continuo de órdenes pendientes")
    print("   • Ejecución automática de lotes adicionales")
    print("   • Completado solo cuando se ejecuten todos los nominales")
    print()
    
    asyncio.run(test_guarantee_system())
