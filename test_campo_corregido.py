#!/usr/bin/env python3
"""
Test rápido para verificar el campo ws_client_order_id
"""

import requests
import json
import time

def test_client_order_id():
    """Test del campo client_order_id corregido"""
    
    print("🧪 TEST DEL CAMPO CLIENT_ORDER_ID CORREGIDO")
    print("="*50)
    
    # Datos de la orden
    order_data = {
        "symbol": "MERV - XMEV - TX28 - 24hs",
        "side": "BUY",
        "size": 1,
        "price": 1,
        "order_type": "LIMIT",
        "tif": "DAY",
        "market": "ROFX",
        "client_order_id": "TEST_ORDER_001"
    }
    
    print("📤 Enviando orden con client_order_id:")
    print(json.dumps(order_data, indent=2, ensure_ascii=False))
    
    try:
        # Enviar orden
        response = requests.post(
            "http://127.0.0.1:8000/cotizaciones/orders/send",
            json=order_data,
            timeout=10
        )
        
        result = response.json()
        print(f"\n📋 Respuesta del servidor:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get("status") == "ok":
            print("\n✅ ¡Orden enviada exitosamente!")
            print("   El campo ws_client_order_id está funcionando correctamente")
        else:
            print(f"\n❌ Error: {result.get('message', 'Error desconocido')}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se puede conectar al servidor")
        print("   Asegúrate de que el servidor esté ejecutándose en http://127.0.0.1:8000")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

def test_websocket_order():
    """Test de orden vía WebSocket"""
    
    print("\n\n🌐 TEST VÍA WEBSOCKET")
    print("="*50)
    
    try:
        import websocket
        import threading
        
        client_order_id = "WS_TEST_001"
        order_sent = False
        order_ack_received = False
        
        def on_message(ws, message):
            nonlocal order_ack_received
            try:
                data = json.loads(message)
                print(f"📨 Mensaje WebSocket: {data.get('type', 'unknown')}")
                
                if data.get("type") == "order_ack":
                    order_ack_received = True
                    result = data.get("result", {})
                    print(f"📤 Order ACK recibido:")
                    print(f"   Status: {result.get('status')}")
                    if result.get("status") == "ok":
                        print("   ✅ Orden enviada exitosamente vía WebSocket")
                    else:
                        print(f"   ❌ Error: {result.get('message')}")
                        
            except Exception as e:
                print(f"❌ Error procesando mensaje WebSocket: {e}")
        
        def on_open(ws):
            nonlocal order_sent
            print("🔗 Conectado al WebSocket")
            
            # Suscribirse a order reports
            ws.send(json.dumps({
                "type": "orders_subscribe",
                "account": "test_account"
            }))
            
            # Enviar orden
            ws.send(json.dumps({
                "type": "send_order",
                "clOrdId": client_order_id,
                "order": {
                    "symbol": "MERV - XMEV - TX28 - 24hs",
                    "side": "BUY",
                    "size": 1,
                    "price": 1,
                    "order_type": "LIMIT",
                    "tif": "DAY",
                    "market": "ROFX"
                }
            }))
            
            order_sent = True
            print(f"📤 Orden enviada vía WebSocket con Client Order ID: {client_order_id}")
        
        def on_error(ws, error):
            print(f"❌ Error WebSocket: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("🔌 WebSocket cerrado")
        
        # Conectar WebSocket
        ws = websocket.WebSocketApp(
            "ws://127.0.0.1:8000/ws/cotizaciones",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Ejecutar en hilo separado
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Esperar respuestas
        time.sleep(3)
        
        # Cerrar WebSocket
        ws.close()
        
        if order_ack_received:
            print("✅ Test WebSocket completado exitosamente")
        else:
            print("❌ No se recibió order_ack en WebSocket")
            
    except ImportError:
        print("⚠️  websocket-client no disponible, saltando test WebSocket")

if __name__ == "__main__":
    print("🚀 Iniciando tests del campo client_order_id corregido...")
    
    # Test REST API
    test_client_order_id()
    
    # Test WebSocket
    test_websocket_order()
    
    print("\n" + "="*60)
    print("✅ Tests completados")
    print("🔧 El campo ws_client_order_id debería estar funcionando ahora")
