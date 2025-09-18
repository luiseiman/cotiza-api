#!/usr/bin/env python3
"""
Ejemplo completo de procesamiento de órdenes por WebSocket usando client_order_id
"""

import websocket
import json
import threading
import time
import uuid
from typing import Dict, Any, Optional

class OrderProcessor:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.connected = False
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.order_reports: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        
    def connect(self):
        """Conectar al WebSocket"""
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Ejecutar en hilo separado
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Esperar conexión
        timeout = 10
        start_time = time.time()
        while not self.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        if not self.connected:
            raise Exception("No se pudo conectar al WebSocket")
            
        print("✅ Conectado al WebSocket")
        
    def _on_open(self, ws):
        """Callback cuando se abre la conexión"""
        self.connected = True
        print("🔗 Conexión WebSocket establecida")
        
        # Suscribirse a order reports
        self.subscribe_to_order_reports("mi_cuenta")
        
    def _on_message(self, ws, message):
        """Procesar mensajes recibidos"""
        try:
            data = json.loads(message)
            self._handle_message(data)
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            
    def _on_error(self, ws, error):
        print(f"❌ Error WebSocket: {error}")
        
    def _on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        print("🔌 WebSocket cerrado")
        
    def _handle_message(self, data: Dict[str, Any]):
        """Manejar diferentes tipos de mensajes"""
        msg_type = data.get("type")
        
        if msg_type == "connection":
            print(f"📡 {data.get('message', 'Conectado')}")
            
        elif msg_type == "orders_subscribed":
            print(f"📋 Suscrito a order reports para cuenta: {data.get('account')}")
            
        elif msg_type == "order_ack":
            self._handle_order_ack(data)
            
        elif msg_type == "order_report":
            self._handle_order_report(data)
            
        elif msg_type == "error":
            print(f"❌ Error: {data.get('message')}")
            
        else:
            print(f"📨 Mensaje no reconocido: {msg_type}")
            
    def _handle_order_ack(self, data: Dict[str, Any]):
        """Manejar confirmación de orden enviada"""
        request = data.get("request", {})
        result = data.get("result", {})
        client_order_id = request.get("client_order_id")
        
        print(f"📤 Order ACK recibido:")
        print(f"   Client Order ID: {client_order_id}")
        print(f"   Status: {result.get('status')}")
        print(f"   Response: {result.get('response', {})}")
        
        # Marcar como enviada
        with self.lock:
            if client_order_id in self.pending_orders:
                self.pending_orders[client_order_id]["status"] = "sent"
                self.pending_orders[client_order_id]["ack_time"] = time.time()
                
    def _handle_order_report(self, data: Dict[str, Any]):
        """Manejar reporte de orden del broker"""
        report = data.get("report", {})
        
        # Extraer client_order_id del reporte
        client_order_id = (report.get("clOrdId") or 
                         report.get("clientId") or 
                         report.get("client_order_id"))
        
        if client_order_id:
            print(f"📋 Order Report recibido:")
            print(f"   Client Order ID: {client_order_id}")
            print(f"   Status: {report.get('status', 'N/A')}")
            print(f"   Symbol: {report.get('instrument', {}).get('symbol', 'N/A')}")
            print(f"   Side: {report.get('side', 'N/A')}")
            print(f"   Size: {report.get('size', 'N/A')}")
            print(f"   Price: {report.get('price', 'N/A')}")
            print(f"   Timestamp: {report.get('timestamp', 'N/A')}")
            
            # Guardar reporte
            with self.lock:
                self.order_reports[client_order_id] = report
                
                # Actualizar estado de orden pendiente
                if client_order_id in self.pending_orders:
                    self.pending_orders[client_order_id]["status"] = "reported"
                    self.pending_orders[client_order_id]["report"] = report
                    self.pending_orders[client_order_id]["report_time"] = time.time()
                    
    def subscribe_to_order_reports(self, account: str):
        """Suscribirse a order reports de una cuenta"""
        if not self.connected:
            raise Exception("WebSocket no conectado")
            
        message = {
            "type": "orders_subscribe",
            "account": account
        }
        
        self.ws.send(json.dumps(message))
        print(f"📋 Suscribiéndose a order reports para cuenta: {account}")
        
    def send_order(self, symbol: str, side: str, size: float, 
                   price: Optional[float] = None, order_type: str = "LIMIT",
                   tif: str = "DAY", market: Optional[str] = None,
                   client_order_id: Optional[str] = None) -> str:
        """Enviar orden con client_order_id"""
        
        if not self.connected:
            raise Exception("WebSocket no conectado")
            
        # Generar client_order_id si no se proporciona
        if not client_order_id:
            client_order_id = f"ORDER_{uuid.uuid4().hex[:8]}"
            
        # Preparar orden
        order_data = {
            "symbol": symbol,
            "side": side,
            "size": size,
            "order_type": order_type,
            "tif": tif
        }
        
        if price is not None:
            order_data["price"] = price
        if market is not None:
            order_data["market"] = market
            
        # Crear mensaje
        message = {
            "type": "send_order",
            "clOrdId": client_order_id,  # Client Order ID
            "order": order_data
        }
        
        # Guardar orden pendiente
        with self.lock:
            self.pending_orders[client_order_id] = {
                "order": order_data,
                "status": "pending",
                "send_time": time.time()
            }
            
        # Enviar orden
        self.ws.send(json.dumps(message))
        print(f"📤 Orden enviada:")
        print(f"   Client Order ID: {client_order_id}")
        print(f"   Symbol: {symbol}")
        print(f"   Side: {side}")
        print(f"   Size: {size}")
        print(f"   Price: {price}")
        
        return client_order_id
        
    def wait_for_order_report(self, client_order_id: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Esperar reporte de orden específica"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            with self.lock:
                if client_order_id in self.order_reports:
                    return self.order_reports[client_order_id]
            time.sleep(0.1)
            
        return None
        
    def get_order_status(self, client_order_id: str) -> Dict[str, Any]:
        """Obtener estado de una orden"""
        with self.lock:
            if client_order_id in self.pending_orders:
                order_info = self.pending_orders[client_order_id].copy()
                if client_order_id in self.order_reports:
                    order_info["report"] = self.order_reports[client_order_id]
                return order_info
            return {"status": "not_found"}
            
    def list_pending_orders(self) -> Dict[str, Dict[str, Any]]:
        """Listar órdenes pendientes"""
        with self.lock:
            return self.pending_orders.copy()
            
    def close(self):
        """Cerrar conexión"""
        if self.ws:
            self.ws.close()
            self.connected = False

def ejemplo_completo():
    """Ejemplo completo de uso"""
    
    # Configuración
    WS_URL = "ws://localhost:8000/ws/cotizaciones"
    
    try:
        # Crear procesador de órdenes
        processor = OrderProcessor(WS_URL)
        
        # Conectar
        processor.connect()
        
        print("\n=== Ejemplo de procesamiento de órdenes ===\n")
        
        # Enviar varias órdenes con diferentes client_order_id
        orders = [
            {
                "symbol": "GGAL",
                "side": "BUY",
                "size": 100,
                "price": 1500.0,
                "client_order_id": "MI_ORDEN_001"
            },
            {
                "symbol": "PAMP",
                "side": "SELL", 
                "size": 50,
                "price": 2000.0,
                "client_order_id": "MI_ORDEN_002"
            },
            {
                "symbol": "ALUA",
                "side": "BUY",
                "size": 200,
                "price": 800.0,
                "client_order_id": "MI_ORDEN_003"
            }
        ]
        
        # Enviar órdenes
        sent_orders = []
        for order in orders:
            client_id = processor.send_order(**order)
            sent_orders.append(client_id)
            time.sleep(1)  # Esperar entre órdenes
            
        print(f"\n📊 Órdenes enviadas: {len(sent_orders)}")
        
        # Esperar reportes
        print("\n⏳ Esperando reportes de órdenes...")
        time.sleep(5)
        
        # Verificar estado de cada orden
        print("\n📋 Estado de las órdenes:")
        for client_id in sent_orders:
            status = processor.get_order_status(client_id)
            print(f"\n   Orden {client_id}:")
            print(f"   - Estado: {status.get('status', 'unknown')}")
            print(f"   - Tiempo envío: {status.get('send_time', 'N/A')}")
            
            if 'report' in status:
                report = status['report']
                print(f"   - Status broker: {report.get('status', 'N/A')}")
                print(f"   - Symbol: {report.get('instrument', {}).get('symbol', 'N/A')}")
                
        # Listar todas las órdenes pendientes
        print(f"\n📊 Total órdenes procesadas: {len(processor.list_pending_orders())}")
        
        # Mantener conexión abierta para recibir más reportes
        print("\n⏳ Manteniendo conexión abierta para recibir más reportes...")
        print("   Presiona Ctrl+C para salir")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Cerrando conexión...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        if 'processor' in locals():
            processor.close()

if __name__ == "__main__":
    ejemplo_completo()
