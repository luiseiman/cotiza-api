#!/usr/bin/env python3
"""
Ejemplo actualizado con el formato real del broker - wsClOrdId
"""

import websocket
import json
import time
import uuid

def ejemplo_formato_real_broker():
    """Ejemplo con el formato real que devuelve el broker"""
    
    print("🎯 EJEMPLO CON FORMATO REAL DEL BROKER")
    print("="*50)
    
    # Ejemplo de order report real del broker
    order_report_real = {
        "instrumentId": {
            "marketId": "ROFX",
            "symbol": "MERV - XMEV - TX28 - 24hs"
        },
        "price": 1,
        "orderQty": 1,
        "ordType": "LIMIT",
        "side": "BUY",
        "timeInForce": "DAY",
        "transactTime": "20250918-16:18:02.634-0300",
        "status": "PENDING_NEW",
        "text": "Enviada",
        "wsClOrdId": "Client Order ID"  # ← Este es el campo real del broker
    }
    
    print("\n📋 Order Report REAL del broker:")
    print(json.dumps(order_report_real, indent=2, ensure_ascii=False))
    
    print("\n🔑 Campos importantes:")
    print(f"   wsClOrdId: {order_report_real['wsClOrdId']}  ← Client Order ID")
    print(f"   status: {order_report_real['status']}")
    print(f"   side: {order_report_real['side']}")
    print(f"   orderQty: {order_report_real['orderQty']}")
    print(f"   price: {order_report_real['price']}")
    print(f"   symbol: {order_report_real['instrumentId']['symbol']}")
    print(f"   marketId: {order_report_real['instrumentId']['marketId']}")

def ejemplo_websocket_actualizado():
    """Ejemplo de WebSocket actualizado para manejar wsClOrdId"""
    
    print("\n\n🚀 EJEMPLO WEBSOCKET ACTUALIZADO")
    print("="*50)
    
    client_order_id = "MI_ORDEN_001"
    
    def on_message(ws, message):
        data = json.loads(message)
        msg_type = data.get("type")
        
        if msg_type == "order_report":
            report = data.get("report", {})
            
            # Buscar client_order_id en el campo correcto del broker
            report_client_id = report.get("wsClOrdId")  # ← Campo real del broker
            
            if report_client_id == client_order_id:
                print(f"✅ Reporte de nuestra orden recibido:")
                print(f"   Client Order ID: {report_client_id}")
                print(f"   Status: {report.get('status')}")
                print(f"   Symbol: {report.get('instrumentId', {}).get('symbol')}")
                print(f"   Side: {report.get('side')}")
                print(f"   Quantity: {report.get('orderQty')}")
                print(f"   Price: {report.get('price')}")
                print(f"   Time: {report.get('transactTime')}")
    
    def on_open(ws):
        print("🔗 Conectado al WebSocket")
        
        # Suscribirse a order reports
        ws.send(json.dumps({
            "type": "orders_subscribe",
            "account": "mi_cuenta"
        }))
        
        # Enviar orden con client_order_id
        ws.send(json.dumps({
            "type": "send_order",
            "clOrdId": client_order_id,  # Se envía como clOrdId
            "order": {
                "symbol": "TX28",
                "side": "BUY",
                "size": 1,
                "price": 1.0,
                "order_type": "LIMIT",
                "tif": "DAY"
            }
        }))
        
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
    
    print("🚀 Iniciando conexión...")
    ws.run_forever()

def ejemplo_manejo_multiple_campos():
    """Ejemplo de cómo manejar múltiples campos posibles"""
    
    print("\n\n🔄 MANEJO DE MÚLTIPLES CAMPOS POSIBLES")
    print("="*50)
    
    def extraer_client_order_id(report):
        """Extraer client_order_id de diferentes campos posibles"""
        
        # Orden de prioridad: wsClOrdId (real del broker) → clOrdId → clientId → client_order_id
        client_id = (report.get("wsClOrdId") or 
                    report.get("clOrdId") or 
                    report.get("clientId") or 
                    report.get("client_order_id"))
        
        return client_id
    
    # Ejemplos de diferentes formatos que podrían llegar
    ejemplos_reports = [
        {
            "wsClOrdId": "ORD_001",  # Formato real del broker
            "status": "PENDING_NEW",
            "side": "BUY"
        },
        {
            "clOrdId": "ORD_002",    # Formato estándar FIX
            "status": "FILLED",
            "side": "SELL"
        },
        {
            "clientId": "ORD_003",   # Formato alternativo
            "status": "CANCELLED",
            "side": "BUY"
        }
    ]
    
    print("📋 Ejemplos de extracción de Client Order ID:")
    for i, report in enumerate(ejemplos_reports, 1):
        client_id = extraer_client_order_id(report)
        print(f"   Reporte {i}: Client Order ID = '{client_id}', Status = '{report.get('status')}'")

def ejemplo_codigo_produccion():
    """Ejemplo de código para producción"""
    
    print("\n\n🏭 CÓDIGO PARA PRODUCCIÓN")
    print("="*50)
    
    codigo_produccion = '''
import websocket
import json
from typing import Optional, Dict, Any

class OrderProcessor:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.pending_orders = {}
        
    def extract_client_order_id(self, report: Dict[str, Any]) -> Optional[str]:
        """Extraer client_order_id del reporte del broker"""
        return (report.get("wsClOrdId") or 
                report.get("clOrdId") or 
                report.get("clientId") or 
                report.get("client_order_id"))
    
    def handle_order_report(self, report: Dict[str, Any]):
        """Manejar order report del broker"""
        client_id = self.extract_client_order_id(report)
        
        if client_id and client_id in self.pending_orders:
            order_info = self.pending_orders[client_id]
            order_info["status"] = report.get("status")
            order_info["report"] = report
            
            print(f"📋 Order report para {client_id}:")
            print(f"   Status: {report.get('status')}")
            print(f"   Symbol: {report.get('instrumentId', {}).get('symbol')}")
            print(f"   Side: {report.get('side')}")
            print(f"   Quantity: {report.get('orderQty')}")
            print(f"   Price: {report.get('price')}")
            
            # Notificar a la aplicación
            self.on_order_update(client_id, report)
    
    def on_order_update(self, client_id: str, report: Dict[str, Any]):
        """Callback cuando se actualiza una orden"""
        # Implementar lógica específica de la aplicación
        pass
    
    def send_order(self, symbol: str, side: str, size: float, 
                   price: float, client_order_id: str):
        """Enviar orden con client_order_id"""
        
        # Guardar orden pendiente
        self.pending_orders[client_order_id] = {
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "status": "pending"
        }
        
        # Enviar orden
        message = {
            "type": "send_order",
            "clOrdId": client_order_id,  # Se envía como clOrdId
            "order": {
                "symbol": symbol,
                "side": side,
                "size": size,
                "price": price,
                "order_type": "LIMIT",
                "tif": "DAY"
            }
        }
        
        self.ws.send(json.dumps(message))
        print(f"📤 Orden enviada: {client_order_id}")
    
    def on_message(self, ws, message):
        """Procesar mensajes del WebSocket"""
        data = json.loads(message)
        
        if data.get("type") == "order_report":
            self.handle_order_report(data.get("report", {}))
    
    def connect(self):
        """Conectar al WebSocket"""
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=lambda ws: self.ws.send(json.dumps({
                "type": "orders_subscribe",
                "account": "mi_cuenta"
            })),
            on_message=self.on_message
        )
        self.ws.run_forever()

# Uso
processor = OrderProcessor("ws://localhost:8000/ws/cotizaciones")
processor.connect()
'''
    
    print(codigo_produccion)

if __name__ == "__main__":
    ejemplo_formato_real_broker()
    ejemplo_manejo_multiple_campos()
    ejemplo_codigo_produccion()
    
    print("\n\n" + "="*60)
    print("✅ RESUMEN DE CAMBIOS IMPORTANTES")
    print("="*60)
    print("🔑 El campo real del broker es 'wsClOrdId' (no 'clOrdId')")
    print("📋 El broker devuelve el Client Order ID en 'wsClOrdId'")
    print("🔄 El código maneja múltiples campos para compatibilidad")
    print("🎯 Prioridad: wsClOrdId → clOrdId → clientId → client_order_id")
    print("📤 Se envía como 'clOrdId' pero se recibe como 'wsClOrdId'")
