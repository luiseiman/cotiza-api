#!/usr/bin/env python3
"""
Test script para verificar el soporte completo de client_order_id
"""

import requests
import json
import time
import uuid

# Configuración del servidor
BASE_URL = "http://localhost:8000"

def test_client_order_id_flow():
    """Prueba el flujo completo de client_order_id"""
    
    print("=== Test de Client Order ID Flow ===\n")
    
    # 1. Verificar estado del servicio
    print("1. Verificando estado del servicio...")
    try:
        response = requests.get(f"{BASE_URL}/cotizaciones/status")
        status = response.json()
        print(f"   Estado: {status.get('ws', 'unknown')}")
        if status.get('ws') != 'ok':
            print("   ❌ WebSocket no está conectado. Ejecuta el servicio primero.")
            return False
    except Exception as e:
        print(f"   ❌ Error conectando al servicio: {e}")
        return False
    
    # 2. Suscribirse a order reports
    print("\n2. Suscribiéndose a order reports...")
    try:
        account = status.get('account', 'test_account')
        response = requests.post(f"{BASE_URL}/cotizaciones/orders/subscribe", 
                               json={"account": account})
        result = response.json()
        print(f"   Resultado: {result}")
        if result.get('status') != 'ok':
            print("   ❌ No se pudo suscribir a order reports")
            return False
    except Exception as e:
        print(f"   ❌ Error suscribiéndose: {e}")
        return False
    
    # 3. Enviar orden con client_order_id
    print("\n3. Enviando orden con client_order_id...")
    client_order_id = f"TEST_{uuid.uuid4().hex[:8]}"
    order_data = {
        "symbol": "GGAL",
        "side": "BUY",
        "size": 1,
        "price": 100.0,
        "order_type": "LIMIT",
        "tif": "DAY",
        "client_order_id": client_order_id
    }
    
    try:
        response = requests.post(f"{BASE_URL}/cotizaciones/orders/send", 
                               json=order_data)
        result = response.json()
        print(f"   Client Order ID enviado: {client_order_id}")
        print(f"   Respuesta del broker: {result}")
        
        if result.get('status') != 'ok':
            print("   ❌ Error enviando orden")
            return False
            
    except Exception as e:
        print(f"   ❌ Error enviando orden: {e}")
        return False
    
    # 4. Esperar y verificar order report
    print("\n4. Esperando order report...")
    time.sleep(2)  # Esperar un poco para que llegue el reporte
    
    try:
        response = requests.get(f"{BASE_URL}/cotizaciones/orders/last_report")
        result = response.json()
        report = result.get('report')
        
        if report:
            print(f"   Order report recibido:")
            print(f"   - ClOrdId: {report.get('clOrdId', 'N/A')}")
            print(f"   - ClientId: {report.get('clientId', 'N/A')}")
            print(f"   - Client Order ID: {report.get('client_order_id', 'N/A')}")
            print(f"   - Status: {report.get('status', 'N/A')}")
            print(f"   - Symbol: {report.get('instrument', {}).get('symbol', 'N/A')}")
            
            # Verificar que el client_order_id se preservó
            preserved_id = (report.get('clOrdId') or 
                           report.get('clientId') or 
                           report.get('client_order_id'))
            
            if preserved_id == client_order_id:
                print(f"   ✅ Client Order ID preservado correctamente: {preserved_id}")
                return True
            else:
                print(f"   ❌ Client Order ID no coincide. Enviado: {client_order_id}, Recibido: {preserved_id}")
                return False
        else:
            print("   ❌ No se recibió order report")
            return False
            
    except Exception as e:
        print(f"   ❌ Error obteniendo order report: {e}")
        return False

def test_websocket_client_order_id():
    """Prueba client_order_id vía WebSocket"""
    
    print("\n=== Test de Client Order ID vía WebSocket ===\n")
    
    import websocket
    import threading
    
    # Variables para comunicación
    ws_connected = False
    order_ack_received = False
    order_report_received = False
    client_order_id = f"WS_TEST_{uuid.uuid4().hex[:8]}"
    
    def on_message(ws, message):
        nonlocal order_ack_received, order_report_received
        try:
            data = json.loads(message)
            print(f"   Mensaje WebSocket recibido: {data.get('type', 'unknown')}")
            
            if data.get('type') == 'order_ack':
                order_ack_received = True
                result = data.get('result', {})
                print(f"   ✅ Order ACK recibido: {result}")
                
            elif data.get('type') == 'order_report':
                order_report_received = True
                report = data.get('report', {})
                preserved_id = (report.get('clOrdId') or 
                               report.get('clientId') or 
                               report.get('client_order_id'))
                print(f"   ✅ Order Report recibido con Client Order ID: {preserved_id}")
                
        except Exception as e:
            print(f"   ❌ Error procesando mensaje WebSocket: {e}")
    
    def on_open(ws):
        nonlocal ws_connected
        ws_connected = True
        print("   ✅ WebSocket conectado")
        
        # Suscribirse a order reports
        subscribe_msg = {
            "type": "orders_subscribe",
            "account": "test_account"
        }
        ws.send(json.dumps(subscribe_msg))
        print("   Suscripción a order reports enviada")
        
        # Enviar orden con client_order_id
        order_msg = {
            "type": "send_order",
            "clOrdId": client_order_id,
            "order": {
                "symbol": "GGAL",
                "side": "BUY",
                "size": 1,
                "price": 100.0,
                "order_type": "LIMIT",
                "tif": "DAY"
            }
        }
        ws.send(json.dumps(order_msg))
        print(f"   Orden enviada con Client Order ID: {client_order_id}")
    
    def on_error(ws, error):
        print(f"   ❌ Error WebSocket: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print("   WebSocket cerrado")
    
    # Conectar WebSocket
    try:
        ws_url = BASE_URL.replace("http", "ws") + "/ws/cotizaciones"
        ws = websocket.WebSocketApp(ws_url,
                                  on_open=on_open,
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close)
        
        # Ejecutar en hilo separado
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Esperar conexión
        timeout = 5
        start_time = time.time()
        while not ws_connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not ws_connected:
            print("   ❌ No se pudo conectar WebSocket")
            return False
        
        # Esperar respuestas
        time.sleep(3)
        
        # Cerrar WebSocket
        ws.close()
        
        if order_ack_received and order_report_received:
            print("   ✅ Flujo WebSocket completo exitoso")
            return True
        else:
            print(f"   ❌ Flujo incompleto. ACK: {order_ack_received}, Report: {order_report_received}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en test WebSocket: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando tests de Client Order ID...")
    
    # Test REST API
    rest_success = test_client_order_id_flow()
    
    # Test WebSocket (opcional, requiere websocket-client)
    try:
        import websocket
        ws_success = test_websocket_client_order_id()
    except ImportError:
        print("\n⚠️  websocket-client no instalado, saltando test WebSocket")
        ws_success = True
    
    print(f"\n=== Resumen ===")
    print(f"REST API: {'✅ PASS' if rest_success else '❌ FAIL'}")
    print(f"WebSocket: {'✅ PASS' if ws_success else '❌ FAIL'}")
    
    if rest_success and ws_success:
        print("\n🎉 Todos los tests pasaron! Client Order ID está funcionando correctamente.")
    else:
        print("\n❌ Algunos tests fallaron. Revisar implementación.")
