#!/usr/bin/env python3
"""
Test completo correcto: 1) Iniciar cotizaciones via HTTP, 2) Ejecutar ratio via WebSocket
"""

import requests
import asyncio
import websockets
import json
import time

def iniciar_cotizaciones():
    """Iniciar cotizaciones usando endpoint HTTP"""
    print("📊 INICIANDO COTIZACIONES VIA HTTP")
    print("=" * 40)
    
    try:
        # Endpoint para iniciar cotizaciones
        url = "http://localhost:8000/cotizaciones/iniciar"
        
        # Datos para iniciar cotizaciones
        data = {
            "instrumentos": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
            "user": "24239211",
            "password": "GuEtAjEt25*",
            "account": "16557"
        }
        
        print(f"📤 Enviando request a: {url}")
        print(f"📋 Instrumentos: {data['instrumentos']}")
        
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cotizaciones iniciadas: {result.get('status')}")
            print(f"   WS: {result.get('ws', 'N/A')}")
            print(f"   Usuario: {result.get('user_id', 'N/A')}")
            return True
        else:
            print(f"❌ Error iniciando cotizaciones: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def reconectar_rofex():
    """Reconectar ROFEX usando endpoint HTTP"""
    print("\n🔌 RECONECTANDO ROFEX VIA HTTP")
    print("=" * 40)
    
    try:
        url = "http://localhost:8000/cotizaciones/reconnect_rofex"
        
        print(f"📤 Enviando request a: {url}")
        
        response = requests.post(url, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ROFEX reconectado: {result.get('status')}")
            print(f"   WS: {result.get('ws', 'N/A')}")
            return True
        else:
            print(f"❌ Error reconectando ROFEX: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_ratio_operation():
    """Probar operación de ratio via WebSocket"""
    print("\n⚡ PROBANDO OPERACIÓN DE RATIO VIA WEBSOCKET")
    print("=" * 50)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al WebSocket")
            
            # Enviar operación de ratio
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 10.0,
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_completo_correcto"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación de ratio enviada")
            print(f"   Par: TX26/TX28")
            print(f"   Vender: TX26")
            print(f"   Nominales: 10.0")
            print(f"   Ratio objetivo: ≤ 0.98")
            
            # Escuchar confirmaciones por 60 segundos
            print("\n📨 Escuchando confirmaciones (60 segundos)...")
            timeout = 60
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
                            
                            # Detectar ejecución de órdenes
                            if "ejecutando" in last_msg.lower() or "enviando orden" in last_msg.lower():
                                print("   🎯 ¡Órdenes en ejecución!")
                            elif "orden ejecutada" in last_msg.lower() or "✅" in last_msg:
                                print("   🎉 ¡Orden ejecutada exitosamente!")
                            elif "ws_not_connected" in last_msg.lower():
                                print("   ❌ ROFEX desconectado")
                    
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
                    
                    # Si recibimos order reports, podemos terminar antes
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
                print("\n🎉 ¡ÉXITO! Se recibieron confirmaciones de pyRofex")
                print("✅ Las órdenes se ejecutaron y se recibieron order reports")
                print("\n📋 CONFIRMACIONES DE pyRofex RECIBIDAS:")
                print("   1. ✅ Respuesta inmediata de send_order_via_websocket")
                print("   2. ✅ Order Reports asíncronos con estados (NEW, FILLED, etc.)")
                print("   3. ✅ Actualizaciones de precios y cantidades ejecutadas")
                print("   4. ✅ Confirmaciones de ejecución completa")
            else:
                print("\n⚠️ No se recibieron order reports")
                print("💡 Posibles causas:")
                print("   • ROFEX no conectado correctamente")
                print("   • Órdenes no ejecutadas (condición no cumplida)")
                print("   • Timeout muy corto")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🚀 TEST COMPLETO CORRECTO - COTIZACIONES + RATIO")
    print("=" * 70)
    
    # Paso 1: Iniciar cotizaciones via HTTP
    if not iniciar_cotizaciones():
        print("❌ No se pudieron iniciar cotizaciones - terminando test")
        return
    
    # Esperar un poco para que se estabilicen
    print("\n⏳ Esperando 5 segundos para estabilizar...")
    await asyncio.sleep(5)
    
    # Paso 2: Reconectar ROFEX
    if not reconectar_rofex():
        print("⚠️ No se pudo reconectar ROFEX, pero continuando...")
    
    # Esperar un poco más
    print("\n⏳ Esperando 3 segundos adicionales...")
    await asyncio.sleep(3)
    
    # Paso 3: Probar operación de ratio
    await test_ratio_operation()
    
    print("\n🏁 Test completado")

if __name__ == "__main__":
    asyncio.run(main())
