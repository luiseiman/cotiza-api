#!/usr/bin/env python3
"""
Ejemplo simple de procesamiento de órdenes por WebSocket usando client_order_id
"""

import websocket
import json
import time
import uuid

# Configuración
WS_URL = "ws://localhost:8000/ws/cotizaciones"

def procesar_orden_simple():
    """Ejemplo simple de envío y procesamiento de orden"""
    
    # Variables para tracking
    client_order_id = f"ORDEN_{uuid.uuid4().hex[:8]}"
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
            print(f"📤 Orden confirmada:")
            print(f"   Client Order ID: {client_order_id}")
            print(f"   Status: {data.get('result', {}).get('status')}")
            orden_enviada = True
            
        elif msg_type == "order_report":
            report = data.get("report", {})
            
            # Buscar nuestro client_order_id en el reporte
            report_client_id = (report.get("wsClOrdId") or 
                              report.get("clOrdId") or 
                              report.get("clientId") or 
                              report.get("client_order_id"))
            
            if report_client_id == client_order_id:
                print(f"📋 Reporte de nuestra orden recibido:")
                print(f"   Client Order ID: {report_client_id}")
                print(f"   Status: {report.get('status', 'N/A')}")
                print(f"   Symbol: {report.get('instrument', {}).get('symbol', 'N/A')}")
                print(f"   Side: {report.get('side', 'N/A')}")
                print(f"   Size: {report.get('size', 'N/A')}")
                print(f"   Price: {report.get('price', 'N/A')}")
                reporte_recibido = True
            else:
                print(f"📋 Reporte de otra orden: {report_client_id}")
    
    def on_open(ws):
        print("🔗 Conexión establecida")
        
        # 1. Suscribirse a order reports
        subscribe_msg = {
            "type": "orders_subscribe",
            "account": "mi_cuenta"
        }
        ws.send(json.dumps(subscribe_msg))
        print("📋 Suscripción enviada")
        
        # 2. Enviar orden con client_order_id
        orden_msg = {
            "type": "send_order",
            "clOrdId": client_order_id,  # Nuestro ID único
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
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    print(f"🚀 Iniciando conexión a {WS_URL}")
    print(f"📋 Client Order ID que usaremos: {client_order_id}")
    
    # Ejecutar WebSocket
    ws.run_forever()

def ejemplo_multiple_ordenes():
    """Ejemplo con múltiples órdenes usando diferentes client_order_id"""
    
    ordenes_enviadas = []
    reportes_recibidos = {}
    
    def on_message(ws, message):
        data = json.loads(message)
        msg_type = data.get("type")
        
        if msg_type == "order_ack":
            request = data.get("request", {})
            client_id = request.get("client_order_id")
            print(f"📤 ACK para orden {client_id}")
            
        elif msg_type == "order_report":
            report = data.get("report", {})
            client_id = (report.get("wsClOrdId") or 
                        report.get("clOrdId") or 
                        report.get("clientId") or 
                        report.get("client_order_id"))
            
            if client_id:
                reportes_recibidos[client_id] = report
                print(f"📋 Reporte recibido para orden {client_id}")
                print(f"   Status: {report.get('status', 'N/A')}")
                print(f"   Symbol: {report.get('instrument', {}).get('symbol', 'N/A')}")
    
    def on_open(ws):
        print("🔗 Conectado - enviando múltiples órdenes")
        
        # Suscribirse a order reports
        ws.send(json.dumps({
            "type": "orders_subscribe",
            "account": "mi_cuenta"
        }))
        
        # Enviar múltiples órdenes con diferentes client_order_id
        ordenes = [
            {"symbol": "GGAL", "side": "BUY", "size": 100, "price": 1500.0, "id": "ORD_001"},
            {"symbol": "PAMP", "side": "SELL", "size": 50, "price": 2000.0, "id": "ORD_002"},
            {"symbol": "ALUA", "side": "BUY", "size": 200, "price": 800.0, "id": "ORD_003"}
        ]
        
        for orden in ordenes:
            ws.send(json.dumps({
                "type": "send_order",
                "clOrdId": orden["id"],
                "order": {
                    "symbol": orden["symbol"],
                    "side": orden["side"],
                    "size": orden["size"],
                    "price": orden["price"],
                    "order_type": "LIMIT",
                    "tif": "DAY"
                }
            }))
            ordenes_enviadas.append(orden["id"])
            print(f"📤 Orden {orden['id']} enviada: {orden['symbol']} {orden['side']} {orden['size']} @ {orden['price']}")
            time.sleep(1)  # Esperar entre órdenes
    
    def on_error(ws, error):
        print(f"❌ Error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 Cerrado. Órdenes enviadas: {len(ordenes_enviadas)}, Reportes recibidos: {len(reportes_recibidos)}")
    
    # Crear WebSocket
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    print("🚀 Enviando múltiples órdenes...")
    ws.run_forever()

if __name__ == "__main__":
    print("=== Ejemplos de procesamiento de órdenes por WebSocket ===\n")
    
    print("1. Ejemplo simple (una orden)")
    print("2. Ejemplo múltiple (varias órdenes)")
    
    opcion = input("\nSelecciona opción (1 o 2): ").strip()
    
    if opcion == "1":
        procesar_orden_simple()
    elif opcion == "2":
        ejemplo_multiple_ordenes()
    else:
        print("Opción inválida")
