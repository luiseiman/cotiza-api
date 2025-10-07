#!/usr/bin/env python3
"""
Verificar si el servidor tiene ROFEX conectado y probar operación
"""

import asyncio
import websockets
import json
import time

async def verificar_rofex():
    print("🔍 VERIFICANDO ESTADO DE ROFEX EN SERVIDOR")
    print("=" * 50)
    
    uri = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Verificar estado de ROFEX
            print("\n📡 Verificando estado de ROFEX...")
            status_msg = {"type": "get_status"}
            await websocket.send(json.dumps(status_msg))
            
            # Intentar conectar ROFEX si no está conectado
            print("📡 Intentando conectar ROFEX...")
            connect_msg = {
                "type": "connect_rofex",
                "user": "24239211",
                "password": "GuEtAjEt25*",
                "account": "16557",
                "instrumentos": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
            }
            await websocket.send(json.dumps(connect_msg))
            
            # Escuchar respuestas por 10 segundos
            print("📨 Escuchando respuestas...")
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    
                    print(f"📨 {msg_type.upper()}: {data.get('message', data.get('status', 'N/A'))}")
                    
                    if msg_type == 'connection' and 'connected' in str(data).lower():
                        print("✅ ROFEX conectado exitosamente!")
                        break
                    elif msg_type == 'error' and 'rofex' in str(data).lower():
                        print("❌ Error conectando ROFEX")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏳ Esperando respuesta...")
                    continue
            
            # Ahora probar operación de ratio
            print("\n⚡ Probando operación de ratio...")
            ratio_msg = {
                "type": "start_ratio_operation",
                "pair": ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
                "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
                "nominales": 1.0,  # Cantidad pequeña para prueba
                "target_ratio": 0.98,
                "condition": "<=",
                "client_id": "test_verificacion"
            }
            
            await websocket.send(json.dumps(ratio_msg))
            print("📤 Operación enviada")
            
            # Escuchar por 15 segundos más
            print("📨 Escuchando confirmaciones...")
            timeout = 15
            start_time = time.time()
            order_reports = 0
            
            while time.time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    
                    if msg_type == 'ratio_operation_started':
                        print(f"✅ Operación iniciada: {data.get('operation_id')}")
                    
                    elif msg_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        messages = progress.get('messages', [])
                        if messages:
                            print(f"📊 {messages[-1]}")
                    
                    elif msg_type == 'order_report':
                        order_reports += 1
                        report = data.get('report', {})
                        print(f"📋 Order Report #{order_reports}: {report.get('status')} - {report.get('side')}")
                    
                    elif msg_type == 'error':
                        print(f"❌ Error: {data.get('message')}")
                    
                except asyncio.TimeoutError:
                    continue
            
            print(f"\n📊 RESUMEN:")
            print(f"   📋 Order Reports: {order_reports}")
            if order_reports > 0:
                print("   ✅ ¡ÉXITO! Se recibieron confirmaciones de pyRofex")
            else:
                print("   ⚠️ No se recibieron order reports")
                print("   💡 El problema puede ser:")
                print("      • ROFEX no está realmente conectado en el servidor")
                print("      • Las órdenes no se están ejecutando")
                print("      • El servidor no está usando real_ratio_manager")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(verificar_rofex())
