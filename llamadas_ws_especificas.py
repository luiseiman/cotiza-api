#!/usr/bin/env python3
"""
Llamadas específicas al WebSocket - Ejemplos directos
"""

import websocket
import json

# ============================================================================
# 1. CONEXIÓN BÁSICA
# ============================================================================

def conectar_websocket():
    """Conectar al WebSocket"""
    ws_url = "ws://localhost:8000/ws/cotizaciones"
    
    def on_open(ws):
        print("✅ Conectado al WebSocket")
        
    def on_message(ws, message):
        data = json.loads(message)
        print(f"📨 Mensaje: {data.get('type')}")
        
    def on_error(ws, error):
        print(f"❌ Error: {error}")
        
    def on_close(ws, close_status_code, close_msg):
        print("🔌 Conexión cerrada")
    
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    return ws

# ============================================================================
# 2. SUSCRIPCIÓN A ORDER REPORTS
# ============================================================================

def suscribirse_order_reports(ws, cuenta="mi_cuenta"):
    """Suscribirse a order reports"""
    mensaje = {
        "type": "orders_subscribe",
        "account": cuenta
    }
    
    print("📋 Suscribiéndose a order reports...")
    print(f"   Mensaje: {json.dumps(mensaje, indent=2)}")
    
    ws.send(json.dumps(mensaje))
    return mensaje

# ============================================================================
# 3. ENVÍO DE ORDEN CON CLIENT_ORDER_ID
# ============================================================================

def enviar_orden(ws, symbol="GGAL", side="BUY", size=100, price=1500.0, 
                 client_order_id="MI_ORDEN_001"):
    """Enviar orden con client_order_id"""
    
    mensaje = {
        "type": "send_order",
        "clOrdId": client_order_id,  # ← Este es el client_order_id
        "order": {
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "order_type": "LIMIT",
            "tif": "DAY"
        }
    }
    
    print(f"📤 Enviando orden con Client Order ID: {client_order_id}")
    print(f"   Mensaje: {json.dumps(mensaje, indent=2)}")
    
    ws.send(json.dumps(mensaje))
    return mensaje

# ============================================================================
# 4. PROCESAR RESPUESTAS
# ============================================================================

def procesar_respuestas(ws):
    """Procesar respuestas del WebSocket"""
    
    def on_message(ws, message):
        data = json.loads(message)
        msg_type = data.get("type")
        
        if msg_type == "connection":
            print("📡 Conexión establecida")
            
        elif msg_type == "orders_subscribed":
            print("📋 Suscrito a order reports")
            
        elif msg_type == "order_ack":
            # Confirmación de envío
            request = data.get("request", {})
            result = data.get("result", {})
            client_id = request.get("client_order_id")
            
            print(f"📤 Order ACK recibido:")
            print(f"   Client Order ID: {client_id}")
            print(f"   Status: {result.get('status')}")
            
        elif msg_type == "order_report":
            # Reporte del broker
            report = data.get("report", {})
            client_id = (report.get("clOrdId") or 
                        report.get("clientId") or 
                        report.get("client_order_id"))
            
            print(f"📋 Order Report recibido:")
            print(f"   Client Order ID: {client_id}")
            print(f"   Status: {report.get('status')}")
            print(f"   Symbol: {report.get('instrument', {}).get('symbol')}")
            print(f"   Side: {report.get('side')}")
            print(f"   Size: {report.get('size')}")
            print(f"   Price: {report.get('price')}")
            
        elif msg_type == "error":
            print(f"❌ Error: {data.get('message')}")
            
        else:
            print(f"📨 Mensaje no reconocido: {msg_type}")
    
    return on_message

# ============================================================================
# 5. EJEMPLO COMPLETO DE USO
# ============================================================================

def ejemplo_completo():
    """Ejemplo completo de uso"""
    
    print("🚀 Ejemplo Completo de Llamadas al WebSocket\n")
    
    # 1. Conectar
    ws = conectar_websocket()
    
    # 2. Configurar procesamiento de mensajes
    ws.on_message = procesar_respuestas(ws)
    
    # 3. Ejecutar en hilo separado
    import threading
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    
    # 4. Esperar conexión
    import time
    time.sleep(1)
    
    # 5. Suscribirse a order reports
    suscribirse_order_reports(ws)
    time.sleep(1)
    
    # 6. Enviar órdenes con diferentes client_order_id
    ordenes = [
        {"symbol": "GGAL", "side": "BUY", "size": 100, "price": 1500.0, "id": "ORD_001"},
        {"symbol": "PAMP", "side": "SELL", "size": 50, "price": 2000.0, "id": "ORD_002"},
        {"symbol": "ALUA", "side": "BUY", "size": 200, "price": 800.0, "id": "ORD_003"}
    ]
    
    for orden in ordenes:
        enviar_orden(ws, 
                    symbol=orden["symbol"],
                    side=orden["side"], 
                    size=orden["size"],
                    price=orden["price"],
                    client_order_id=orden["id"])
        time.sleep(2)  # Esperar entre órdenes
    
    # 7. Mantener conexión abierta
    print("\n⏳ Manteniendo conexión abierta para recibir reportes...")
    print("   Presiona Ctrl+C para salir")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Cerrando conexión...")
        ws.close()

# ============================================================================
# 6. EJEMPLOS DE MENSAJES ESPECÍFICOS
# ============================================================================

def mostrar_mensajes_ejemplo():
    """Mostrar ejemplos de mensajes específicos"""
    
    print("📋 Ejemplos de Mensajes Específicos\n")
    
    print("1. 🔗 Mensaje de conexión:")
    conexion = {
        "type": "connection",
        "status": "connected",
        "timestamp": 1642248600.0,
        "message": "Conexión WebSocket establecida"
    }
    print(f"   {json.dumps(conexion, indent=2)}")
    print()
    
    print("2. 📋 Suscripción a order reports:")
    suscripcion = {
        "type": "orders_subscribe",
        "account": "mi_cuenta"
    }
    print(f"   {json.dumps(suscripcion, indent=2)}")
    print()
    
    print("3. 📤 Envío de orden con client_order_id:")
    orden = {
        "type": "send_order",
        "clOrdId": "MI_ORDEN_001",
        "order": {
            "symbol": "GGAL",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "order_type": "LIMIT",
            "tif": "DAY"
        }
    }
    print(f"   {json.dumps(orden, indent=2)}")
    print()
    
    print("4. 📤 Order ACK (confirmación):")
    ack = {
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
    print(f"   {json.dumps(ack, indent=2)}")
    print()
    
    print("5. 📋 Order Report (reporte del broker):")
    reporte = {
        "type": "order_report",
        "report": {
            "clOrdId": "MI_ORDEN_001",
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
    print(f"   {json.dumps(reporte, indent=2)}")
    print()

if __name__ == "__main__":
    print("🎯 Llamadas Específicas al WebSocket\n")
    
    # Mostrar ejemplos de mensajes
    mostrar_mensajes_ejemplo()
    
    print("\n" + "="*60 + "\n")
    
    # Ejecutar ejemplo completo
    ejemplo_completo()
