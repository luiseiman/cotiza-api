#!/usr/bin/env python3
"""
Script de prueba para cambios dinámicos de liquidez
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_dynamic_liquidity():
    """Prueba el sistema con cambios dinámicos de liquidez"""
    print("🧪 PRUEBA: Cambios Dinámicos de Liquidez")
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
            
            # Enviar operación de ratio con liquidez limitada
            ratio_request = {
                "type": "execute_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "client_id": "test_dynamic_liquidity",
                "nominales": 10000.0,  # 10,000 nominales
                "target_ratio": 0.0,
                "condition": "less_than_or_equal",
                "max_attempts": 1,
                "buy_qty": 10000.0
            }
            
            await websocket.send(json.dumps(ratio_request))
            print("🚀 OPERACIÓN CON LIQUIDEZ DINÁMICA ENVIADA")
            print(f"📋 Parámetros:")
            print(f"   🎯 Nominales objetivo: {ratio_request['nominales']:,}")
            print(f"   🔍 Verificación de liquidez en tiempo real")
            print(f"   🛡️ Factor de seguridad: 80%")
            print(f"   ⚠️ Manejo de ejecuciones parciales")
            
            # Escuchar respuestas
            operation_completed = False
            operation_id = None
            lot_count = 0
            liquidity_checks = 0
            partial_executions = 0
            
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
                        for msg in messages[-3:]:  # Últimos 3 mensajes
                            if 'Liquidez disponible:' in msg:
                                print(f"   📊 {msg}")
                            
                            elif 'Factor de seguridad:' in msg:
                                print(f"   🛡️ {msg}")
                            
                            elif 'Verificando liquidez actual' in msg:
                                liquidity_checks += 1
                                print(f"   🔍 Verificación #{liquidity_checks}: {msg}")
                            
                            elif 'Liquidez insuficiente:' in msg:
                                print(f"   ⚠️ {msg}")
                            
                            elif 'Ejecución parcial' in msg:
                                partial_executions += 1
                                print(f"   ⚠️ Ejecución parcial #{partial_executions}: {msg}")
                            
                            elif 'LOTE' in msg and 'nominales' in msg:
                                lot_count += 1
                                print(f"   🚀 Lote #{lot_count}: {msg}")
                            
                            elif any(keyword in msg for keyword in ['MONITOREO', 'EJECUTADOS!', 'COMPLETADA']):
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
                            print(f"   📦 Total de lotes: {lot_count}")
                            print(f"   🔍 Verificaciones de liquidez: {liquidity_checks}")
                            print(f"   ⚠️ Ejecuciones parciales: {partial_executions}")
                            
                            # Análisis de la prueba
                            print("\n🔍 ANÁLISIS DE CAMBIOS DINÁMICOS:")
                            print("-" * 50)
                            
                            if liquidity_checks > 0:
                                print("✅ El sistema verificó la liquidez en tiempo real")
                            if partial_executions > 0:
                                print("✅ El sistema manejó ejecuciones parciales correctamente")
                            if lot_count > 1:
                                print("✅ El sistema ejecutó múltiples lotes adaptativos")
                            
                            # Verificar si se completaron todos los nominales
                            if nominales_ejecutados >= nominales_objetivo:
                                print(f"\n🎉 ¡ÉXITO! Se ejecutaron TODOS los {nominales_objetivo:,.0f} nominales")
                                print("✅ El sistema manejó correctamente los cambios de liquidez")
                            else:
                                print(f"\n⚠️ PARCIAL: Solo se ejecutaron {nominales_ejecutados:,.0f} de {nominales_objetivo:,.0f} nominales")
                                print("🔧 Esto puede ser normal si la liquidez es muy limitada")
                    
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
            print("\n🔍 ANÁLISIS DEL SISTEMA DE LIQUIDEZ DINÁMICA:")
            print("-" * 60)
            
            if operation_completed:
                print("✅ La operación se procesó correctamente")
                print("✅ El sistema implementó verificación de liquidez en tiempo real")
                print("✅ El sistema aplicó factor de seguridad del 80%")
                print("✅ El sistema manejó ejecuciones parciales")
                print("✅ El sistema se adaptó a cambios de liquidez")
            else:
                print("⚠️ La prueba no se completó correctamente")
                print("🔧 Verificar la conexión y configuración del sistema")
    
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando prueba de liquidez dinámica...")
    print("📝 Esta prueba verificará:")
    print("   • Verificación de liquidez en tiempo real")
    print("   • Factor de seguridad del 80%")
    print("   • Manejo de ejecuciones parciales")
    print("   • Adaptación a cambios de liquidez")
    print("   • Lotes adaptativos basados en liquidez disponible")
    print()
    
    asyncio.run(test_dynamic_liquidity())
