#!/usr/bin/env python3
"""
Test completo: Conectar ROFEX via endpoint y probar operación
"""

import requests
import asyncio
import websockets
import json
import time

def conectar_rofex_servidor():
    """Conectar ROFEX usando el endpoint del servidor"""
    print("🔌 CONECTANDO ROFEX VIA ENDPOINT")
    print("=" * 40)
    
    try:
        # Conectar ROFEX usando el endpoint
        url = "http://localhost:8000/cotizaciones/reconnect_rofex"
        response = requests.post(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ROFEX conectado: {result.get('status')}")
            print(f"   WS: {result.get('ws', 'N/A')}")
            return True
        else:
            print(f"❌ Error conectando ROFEX: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_operacion_ratio():
    """Probar operación de ratio via WebSocket"""
    print("\n⚡ PROBANDO OPERACIÓN DE RATIO")
    print("=" * 40)
    
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
                "client_id": "test_completo_001"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación enviada")
            
            # Escuchar respuestas por 20 segundos
            print("📨 Escuchando confirmaciones...")
            timeout = 20
            start_time = time.time()
            order_reports = 0
            message_count = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    message_count += 1
                    
                    print(f"\n📨 [{message_count}] {msg_type.upper()}")
                    
                    if msg_type == 'ratio_operation_started':
                        print(f"   ✅ ID: {data.get('operation_id')}")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        print(f"   📊 Estado: {progress.get('status')}")
                        print(f"   📈 Ratio: {progress.get('current_ratio', 0):.6f}")
                        print(f"   💰 Órdenes: {progress.get('sell_orders_count', 0)}V/{progress.get('buy_orders_count', 0)}C")
                        
                        # Mostrar último mensaje
                        messages = progress.get('messages', [])
                        if messages:
                            last_msg = messages[-1]
                            print(f"   💬 {last_msg}")
                            
                            # Si veo que se ejecutaron órdenes, es buena señal
                            if "ejecutando" in last_msg.lower() or "enviando orden" in last_msg.lower():
                                print("   🎯 ¡Órdenes en ejecución!")
                    
                    elif msg_type == 'order_report':
                        order_reports += 1
                        report = data.get('report', {})
                        print(f"   📋 Order Report #{order_reports}")
                        print(f"      Client ID: {report.get('wsClOrdId', 'N/A')}")
                        print(f"      Estado: {report.get('status', 'N/A')}")
                        print(f"      Lado: {report.get('side', 'N/A')}")
                        print(f"      Cantidad: {report.get('orderQty', 0)}")
                        print(f"      Precio: {report.get('price', 0)}")
                        
                        # Si es FILLED, es excelente
                        if report.get('status') == 'FILLED':
                            print("      🎉 ¡ORDEN EJECUTADA!")
                    
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
                print("   🎉 ¡ÉXITO! Se recibieron confirmaciones de pyRofex")
                print("   ✅ Las órdenes se ejecutaron y se recibieron order reports")
            else:
                print("   ⚠️ No se recibieron order reports")
                print("   💡 Posibles causas:")
                print("      • ROFEX no conectado correctamente")
                print("      • Órdenes no ejecutadas (condición no cumplida)")
                print("      • Order reports no configurados")
                print("      • Timeout muy corto")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🚀 TEST COMPLETO - ROFEX + RATIO OPERATION")
    print("=" * 60)
    
    # Paso 1: Conectar ROFEX via endpoint
    if not conectar_rofex_servidor():
        print("❌ No se pudo conectar ROFEX - terminando test")
        return
    
    # Esperar un poco para que se estabilice
    print("\n⏳ Esperando 3 segundos para estabilizar...")
    await asyncio.sleep(3)
    
    # Paso 2: Probar operación de ratio
    await test_operacion_ratio()
    
    print("\n🏁 Test completado")

if __name__ == "__main__":
    asyncio.run(main())
