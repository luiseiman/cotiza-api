#!/usr/bin/env python3
"""
Cliente para ejecutar operación de ratio con credenciales reales de ROFEX
"""

import asyncio
import websockets
import json
import os
from datetime import datetime

# Configuración de la operación
OPERATION_CONFIG = {
    "action": "start_ratio_operation",
    "pair": [
        "MERV - XMEV - TX26 - 24hs",
        "MERV - XMEV - TX28 - 24hs"
    ],
    "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
    "nominales": 10.0,
    "target_ratio": 0.98,
    "condition": "<=",
    "client_id": "test_client_002"
}

async def test_ratio_con_credenciales():
    print("🧪 EJECUTANDO OPERACIÓN DE RATIO CON CREDENCIALES REALES")
    print("=" * 60)
    
    # Verificar variables de entorno
    print("🔍 Verificando credenciales de ROFEX...")
    rofex_user = os.getenv('ROFEX_USER')
    rofex_password = os.getenv('ROFEX_PASSWORD') 
    rofex_account = os.getenv('ROFEX_ACCOUNT')
    
    if rofex_user and rofex_password and rofex_account:
        print(f"✅ Credenciales encontradas:")
        print(f"   Usuario: {rofex_user}")
        print(f"   Cuenta: {rofex_account}")
        print(f"   Password: {'*' * len(rofex_password)}")
    else:
        print("⚠️ Credenciales de ROFEX no encontradas en variables de entorno")
        print("   Usando configuración por defecto")
    
    try:
        # Conectar al WebSocket del servidor
        uri = "ws://localhost:8000/ws/cotizaciones"
        print(f"\n🔗 Conectando a {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Conectado al servidor")
            
            # Preparar mensaje de operación (parámetros directamente en el mensaje)
            operation_message = {
                "type": "start_ratio_operation",
                "pair": OPERATION_CONFIG["pair"],
                "instrument_to_sell": OPERATION_CONFIG["instrument_to_sell"],
                "nominales": OPERATION_CONFIG["nominales"],
                "target_ratio": OPERATION_CONFIG["target_ratio"],
                "condition": OPERATION_CONFIG["condition"],
                "client_id": OPERATION_CONFIG["client_id"]
            }
            
            print(f"\n📤 Enviando operación de ratio:")
            print(f"   Par: {OPERATION_CONFIG['pair']}")
            print(f"   Instrumento a vender: {OPERATION_CONFIG['instrument_to_sell']}")
            print(f"   Nominales: {OPERATION_CONFIG['nominales']}")
            print(f"   Ratio objetivo: {OPERATION_CONFIG['target_ratio']}")
            print(f"   Condición: {OPERATION_CONFIG['condition']}")
            print(f"   Client ID: {OPERATION_CONFIG['client_id']}")
            
            await websocket.send(json.dumps(operation_message))
            
            # Recibir respuestas
            print(f"\n📥 Esperando respuestas...")
            timeout_count = 0
            max_timeouts = 20
            operation_started = False
            operation_completed = False
            
            while timeout_count < max_timeouts and not operation_completed:
                try:
                    # Esperar respuesta con timeout
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    response_type = data.get('type', 'unknown')
                    print(f"\n📨 Respuesta: {response_type}")
                    
                    if response_type == 'ratio_operation_started':
                        operation_started = True
                        operation_id = data.get('operation_id')
                        print(f"✅ Operación iniciada exitosamente")
                        print(f"🆔 ID de operación: {operation_id}")
                        
                    elif response_type == 'ratio_operation_progress':
                        progress = data.get('progress', {})
                        status = progress.get('status', 'unknown')
                        print(f"📊 Estado: {status}")
                        print(f"📈 Ratio actual: {progress.get('current_ratio', 0):.6f}")
                        print(f"🎯 Ratio objetivo: {progress.get('target_ratio', 0):.6f}")
                        print(f"✅ Condición cumplida: {progress.get('condition_met', False)}")
                        print(f"💰 Órdenes: Venta={len(progress.get('sell_orders', []))}, Compra={len(progress.get('buy_orders', []))}")
                        
                        # Mostrar órdenes ejecutadas
                        sell_orders = progress.get('sell_orders', [])
                        buy_orders = progress.get('buy_orders', [])
                        
                        if sell_orders:
                            print("📤 Órdenes de venta ejecutadas:")
                            for order in sell_orders:
                                print(f"   {order.get('instrument')} - {order.get('quantity')} @ {order.get('price')} (ID: {order.get('order_id')})")
                        
                        if buy_orders:
                            print("📥 Órdenes de compra ejecutadas:")
                            for order in buy_orders:
                                print(f"   {order.get('instrument')} - {order.get('quantity')} @ {order.get('price')} (ID: {order.get('order_id')})")
                        
                        # Mostrar últimos mensajes
                        messages = progress.get('messages', [])
                        if messages:
                            print("📝 Últimos mensajes:")
                            for msg in messages[-3:]:  # Mostrar últimos 3 mensajes
                                print(f"   {msg}")
                        
                        print("-" * 50)
                        
                        # Si la operación está completada o falló, salir
                        if status in ['completed', 'failed', 'cancelled']:
                            operation_completed = True
                            if status == 'completed':
                                print("🏁 Operación completada exitosamente")
                            elif status == 'failed':
                                print("❌ Operación fallida")
                                error = progress.get('error', 'Error desconocido')
                                print(f"   Error: {error}")
                            elif status == 'cancelled':
                                print("🛑 Operación cancelada")
                            break
                            
                    elif response_type == 'ratio_operation_error':
                        print(f"❌ Error en operación: {data.get('error', 'Error desconocido')}")
                        operation_completed = True
                        break
                        
                    else:
                        print(f"📨 Mensaje: {data}")
                        
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if operation_started:
                        print(f"⏰ Esperando progreso... ({timeout_count}/{max_timeouts})")
                    else:
                        print(f"⏰ Esperando inicio de operación... ({timeout_count}/{max_timeouts})")
                    continue
                    
            if timeout_count >= max_timeouts:
                print("⏰ Tiempo de espera agotado")
            elif not operation_started:
                print("❌ La operación nunca se inició")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🏁 Prueba completada")
    return True

if __name__ == "__main__":
    print(f"🕐 Iniciando prueba a las {datetime.now().strftime('%H:%M:%S')}")
    asyncio.run(test_ratio_con_credenciales())
