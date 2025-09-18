#!/usr/bin/env python3
"""
Ejemplos específicos de llamadas al WebSocket para órdenes con client_order_id
"""

import websocket
import json
import time

# URL del WebSocket
WS_URL = "ws://localhost:8000/ws/cotizaciones"

def ejemplo_llamadas_basicas():
    """Ejemplo de las llamadas básicas al WebSocket"""
    
    print("=== Ejemplos de Llamadas al WebSocket ===\n")
    
    # 1. CONEXIÓN
    print("1. 🔗 CONEXIÓN")
    print("   URL: ws://localhost:8000/ws/cotizaciones")
    print("   Método: websocket.WebSocketApp()")
    print()
    
    # 2. SUSCRIPCIÓN A ORDER REPORTS
    print("2. 📋 SUSCRIPCIÓN A ORDER REPORTS")
    subscribe_message = {
        "type": "orders_subscribe",
        "account": "mi_cuenta"
    }
    print("   Mensaje:")
    print(f"   {json.dumps(subscribe_message, indent=2)}")
    print("   Código: ws.send(json.dumps(subscribe_message))")
    print()
    
    # 3. ENVÍO DE ORDEN CON CLIENT_ORDER_ID
    print("3. 📤 ENVÍO DE ORDEN CON CLIENT_ORDER_ID")
    order_message = {
        "type": "send_order",
        "clOrdId": "MI_ORDEN_001",  # ← Este es el client_order_id
        "order": {
            "symbol": "GGAL",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "order_type": "LIMIT",
            "tif": "DAY"
        }
    }
    print("   Mensaje:")
    print(f"   {json.dumps(order_message, indent=2)}")
    print("   Código: ws.send(json.dumps(order_message))")
    print()
    
    # 4. RESPUESTAS ESPERADAS
    print("4. 📨 RESPUESTAS ESPERADAS")
    print()
    
    print("   a) Order ACK (confirmación de envío):")
    ack_response = {
        "type": "order_ack",
        "request": {
            "symbol": "GGAL",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "order_type": "LIMIT",
            "tif": "DAY",
            "client_order_id": "MI_ORDEN_001"
        },
        "result": {
            "status": "ok",
            "response": {
                "orderId": "12345",
                "status": "NEW"
            }
        }
    }
    print(f"   {json.dumps(ack_response, indent=2)}")
    print()
    
    print("   b) Order Report (reporte del broker):")
    report_response = {
        "type": "order_report",
        "report": {
            "clOrdId": "MI_ORDEN_001",  # ← El mismo client_order_id regresa
            "orderId": "12345",
            "status": "NEW",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "instrument": {
                "symbol": "GGAL"
            },
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
    print(f"   {json.dumps(report_response, indent=2)}")
    print()

def ejemplo_codigo_completo():
    """Ejemplo de código completo con las llamadas"""
    
    print("=== Código Completo de Llamadas ===\n")
    
    code_example = '''
import websocket
import json
import time

def procesar_ordenes_ws():
    """Función completa para procesar órdenes por WebSocket"""
    
    # Variables para tracking
    client_order_id = "MI_ORDEN_001"
    orden_enviada = False
    reporte_recibido = False
    
    def on_message(ws, message):
        nonlocal orden_enviada, reporte_recibido
        
        data = json.loads(message)
        msg_type = data.get("type")
        
        print(f"📨 Mensaje recibido: {msg_type}")
        
        if msg_type == "connection":
            print("✅ Conectado al WebSocket")
            
        elif msg_type == "orders_subscribed":
            print("📋 Suscrito a order reports")
            
        elif msg_type == "order_ack":
            # Confirmación de que la orden fue enviada
            request = data.get("request", {})
            result = data.get("result", {})
            
            print(f"📤 Orden confirmada:")
            print(f"   Client Order ID: {request.get('client_order_id')}")
            print(f"   Status: {result.get('status')}")
            orden_enviada = True
            
        elif msg_type == "order_report":
            # Reporte del broker
            report = data.get("report", {})
            
            # Buscar nuestro client_order_id en el reporte
            report_client_id = (report.get("clOrdId") or 
                              report.get("clientId") or 
                              report.get("client_order_id"))
            
            if report_client_id == client_order_id:
                print(f"📋 Reporte de nuestra orden:")
                print(f"   Client Order ID: {report_client_id}")
                print(f"   Status: {report.get('status')}")
                print(f"   Symbol: {report.get('instrument', {}).get('symbol')}")
                reporte_recibido = True
    
    def on_open(ws):
        print("🔗 Conexión establecida")
        
        # 1. SUSCRIPCIÓN A ORDER REPORTS
        subscribe_msg = {
            "type": "orders_subscribe",
            "account": "mi_cuenta"
        }
        ws.send(json.dumps(subscribe_msg))
        print("📋 Suscripción enviada")
        
        # 2. ENVÍO DE ORDEN CON CLIENT_ORDER_ID
        orden_msg = {
            "type": "send_order",
            "clOrdId": client_order_id,  # ← Nuestro ID único
            "order": {
                "symbol": "GGAL",
                "side": "BUY",
                "size": 100,
                "price": 1500.0,
                "order_type": "LIMIT",
                "tif": "DAY"
            }
        }
        
        ws.send(json.dumps(orden_msg))
        print(f"📤 Orden enviada con Client Order ID: {client_order_id}")
    
    def on_error(ws, error):
        print(f"❌ Error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print("🔌 Conexión cerrada")
    
    # Crear WebSocket
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/ws/cotizaciones",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Ejecutar WebSocket
    ws.run_forever()

# Ejecutar
procesar_ordenes_ws()
'''
    
    print(code_example)

def ejemplo_multiple_llamadas():
    """Ejemplo de múltiples llamadas secuenciales"""
    
    print("=== Múltiples Llamadas Secuenciales ===\n")
    
    print("1. 🔗 Conectar")
    print("   ws = websocket.WebSocketApp('ws://localhost:8000/ws/cotizaciones')")
    print("   ws.run_forever()")
    print()
    
    print("2. 📋 Suscribirse a order reports")
    print("   ws.send(json.dumps({")
    print("       'type': 'orders_subscribe',")
    print("       'account': 'mi_cuenta'")
    print("   }))")
    print()
    
    print("3. 📤 Enviar orden 1")
    print("   ws.send(json.dumps({")
    print("       'type': 'send_order',")
    print("       'clOrdId': 'ORD_001',")
    print("       'order': {")
    print("           'symbol': 'GGAL',")
    print("           'side': 'BUY',")
    print("           'size': 100,")
    print("           'price': 1500.0,")
    print("           'order_type': 'LIMIT',")
    print("           'tif': 'DAY'")
    print("       }")
    print("   }))")
    print()
    
    print("4. 📤 Enviar orden 2")
    print("   ws.send(json.dumps({")
    print("       'type': 'send_order',")
    print("       'clOrdId': 'ORD_002',")
    print("       'order': {")
    print("           'symbol': 'PAMP',")
    print("           'side': 'SELL',")
    print("           'size': 50,")
    print("           'price': 2000.0,")
    print("           'order_type': 'LIMIT',")
    print("           'tif': 'DAY'")
    print("       }")
    print("   }))")
    print()
    
    print("5. 📤 Enviar orden 3")
    print("   ws.send(json.dumps({")
    print("       'type': 'send_order',")
    print("       'clOrdId': 'ORD_003',")
    print("       'order': {")
    print("           'symbol': 'ALUA',")
    print("           'side': 'BUY',")
    print("           'size': 200,")
    print("           'price': 800.0,")
    print("           'order_type': 'LIMIT',")
    print("           'tif': 'DAY'")
    print("       }")
    print("   }))")
    print()

def ejemplo_javascript():
    """Ejemplo de llamadas en JavaScript"""
    
    print("=== Llamadas en JavaScript ===\n")
    
    js_code = '''
// 1. CONEXIÓN
const ws = new WebSocket('ws://localhost:8000/ws/cotizaciones');

// 2. SUSCRIPCIÓN A ORDER REPORTS
ws.onopen = function() {
    // Suscribirse a order reports
    ws.send(JSON.stringify({
        type: 'orders_subscribe',
        account: 'mi_cuenta'
    }));
    
    // Enviar orden con client_order_id
    ws.send(JSON.stringify({
        type: 'send_order',
        clOrdId: 'MI_ORDEN_001',  // ← Client Order ID
        order: {
            symbol: 'GGAL',
            side: 'BUY',
            size: 100,
            price: 1500.0,
            order_type: 'LIMIT',
            tif: 'DAY'
        }
    }));
};

// 3. PROCESAR RESPUESTAS
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'order_ack') {
        console.log('Orden confirmada:', data.request.client_order_id);
    }
    
    if (data.type === 'order_report') {
        const report = data.report;
        const clientId = report.clOrdId || report.clientId || report.client_order_id;
        console.log('Reporte recibido para orden:', clientId);
    }
};
'''
    
    print(js_code)

def ejemplo_curl_equivalente():
    """Ejemplo equivalente con curl (para comparación)"""
    
    print("=== Equivalente con cURL (REST API) ===\n")
    
    print("1. 📋 Suscribirse a order reports")
    print("   curl -X POST http://localhost:8000/cotizaciones/orders/subscribe \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"account\": \"mi_cuenta\"}'")
    print()
    
    print("2. 📤 Enviar orden con client_order_id")
    print("   curl -X POST http://localhost:8000/cotizaciones/orders/send \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{")
    print("            \"symbol\": \"GGAL\",")
    print("            \"side\": \"BUY\",")
    print("            \"size\": 100,")
    print("            \"price\": 1500.0,")
    print("            \"order_type\": \"LIMIT\",")
    print("            \"tif\": \"DAY\",")
    print("            \"client_order_id\": \"MI_ORDEN_001\"")
    print("        }'")
    print()
    
    print("3. 📋 Obtener último order report")
    print("   curl -X GET http://localhost:8000/cotizaciones/orders/last_report")
    print()

if __name__ == "__main__":
    print("🚀 Ejemplos de Llamadas al WebSocket\n")
    
    ejemplo_llamadas_basicas()
    print("\n" + "="*50 + "\n")
    
    ejemplo_codigo_completo()
    print("\n" + "="*50 + "\n")
    
    ejemplo_multiple_llamadas()
    print("\n" + "="*50 + "\n")
    
    ejemplo_javascript()
    print("\n" + "="*50 + "\n")
    
    ejemplo_curl_equivalente()
