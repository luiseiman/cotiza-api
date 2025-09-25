#!/usr/bin/env python3
"""
Prueba específica de WebSocket: Suscripción a Order Reports y Envío de Orden
"""

import asyncio
import json
import websockets
import time
from datetime import datetime
from typing import Dict, Any

class WebSocketOrderTest:
    def __init__(self):
        self.ws_url = "ws://127.0.0.1:8000/ws/cotizaciones"
        self.messages_received = []
        self.order_responses = []
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def test_websocket_order_flow(self):
        """Prueba completa del flujo de órdenes via WebSocket"""
        self.log("🚀 Iniciando prueba de WebSocket - Order Reports y Envío de Orden")
        self.log("=" * 70)
        
        try:
            # Conectar al WebSocket
            self.log(f"🔌 Conectando a {self.ws_url}...")
            
            # Usar connect sin timeout para evitar problemas con Python 3.13
            async with websockets.connect(self.ws_url) as websocket:
                self.log("✅ Conexión WebSocket establecida")
                
                # 1. Recibir mensaje de bienvenida
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                self.log(f"📨 Mensaje de bienvenida: {welcome_data}")
                
                # 2. Probar ping-pong
                self.log("🏓 Probando ping-pong...")
                ping_msg = json.dumps({"type": "ping"})
                await websocket.send(ping_msg)
                
                pong_msg = await websocket.recv()
                pong_data = json.loads(pong_msg)
                self.log(f"📨 Pong recibido: {pong_data}")
                
                # 3. Suscribirse a order reports
                self.log("📋 Suscribiéndose a order reports...")
                order_subscribe_msg = json.dumps({
                    "type": "orders_subscribe",
                    "account": "16557"  # Usar la cuenta del .env
                })
                await websocket.send(order_subscribe_msg)
                
                # Esperar respuesta de suscripción
                subscribe_response = await websocket.recv()
                subscribe_data = json.loads(subscribe_response)
                self.log(f"📨 Respuesta suscripción: {subscribe_data}")
                
                # 4. Enviar orden de prueba
                self.log("📤 Enviando orden de prueba...")
                order_msg = {
                    "type": "send_order",
                    "clOrdId": "MI_ORDEN_001", 
                    "order": {
                        "tif": "DAY",
                        "side": "BUY",
                        "size": 1,
                        "price": 1,
                        "market": "ROFX",
                        "symbol": "MERV - XMEV - TSLA - 24hs",
                        "order_type": "LIMIT"
                    }
                }
                
                await websocket.send(json.dumps(order_msg))
                self.log(f"📤 Orden enviada: {json.dumps(order_msg, indent=2)}")
                
                # 5. Esperar respuesta de la orden
                self.log("⏳ Esperando respuesta de la orden...")
                try:
                    order_response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    order_data = json.loads(order_response)
                    self.log(f"📨 Respuesta de orden: {json.dumps(order_data, indent=2)}")
                    self.order_responses.append(order_data)
                except asyncio.TimeoutError:
                    self.log("⚠️ Timeout esperando respuesta de orden", "WARNING")
                
                # 6. Esperar order report (si llega)
                self.log("⏳ Esperando order report...")
                try:
                    report_response = await asyncio.wait_for(websocket.recv(), timeout=15)
                    report_data = json.loads(report_response)
                    self.log(f"📨 Order report recibido: {json.dumps(report_data, indent=2)}")
                    self.order_responses.append(report_data)
                except asyncio.TimeoutError:
                    self.log("⚠️ Timeout esperando order report", "WARNING")
                
                # 7. Probar otra orden para verificar flujo continuo
                self.log("📤 Enviando segunda orden de prueba...")
                order_msg_2 = {
                    "type": "send_order",
                    "clOrdId": "MI_ORDEN_002", 
                    "order": {
                        "tif": "IOC",
                        "side": "SELL",
                        "size": 2,
                        "price": 100,
                        "market": "ROFX",
                        "symbol": "MERV - XMEV - TSLA - 24hs",
                        "order_type": "LIMIT"
                    }
                }
                
                await websocket.send(json.dumps(order_msg_2))
                self.log(f"📤 Segunda orden enviada: {json.dumps(order_msg_2, indent=2)}")
                
                # Esperar respuesta de la segunda orden
                try:
                    order_response_2 = await asyncio.wait_for(websocket.recv(), timeout=10)
                    order_data_2 = json.loads(order_response_2)
                    self.log(f"📨 Respuesta segunda orden: {json.dumps(order_data_2, indent=2)}")
                    self.order_responses.append(order_data_2)
                except asyncio.TimeoutError:
                    self.log("⚠️ Timeout esperando respuesta segunda orden", "WARNING")
                
                self.log("✅ Prueba de WebSocket completada")
                
        except Exception as e:
            self.log(f"❌ Error en prueba WebSocket: {e}", "ERROR")
            return False
        
        return True
    
    def print_summary(self):
        """Imprime resumen de la prueba"""
        self.log("📋 RESUMEN DE PRUEBA WEBSOCKET")
        self.log("=" * 50)
        
        self.log(f"📊 Total respuestas recibidas: {len(self.order_responses)}")
        
        for i, response in enumerate(self.order_responses, 1):
            self.log(f"📨 Respuesta {i}: {response.get('type', 'unknown')}")
            if 'result' in response:
                result = response['result']
                if isinstance(result, dict):
                    status = result.get('status', 'unknown')
                    self.log(f"   Estado: {status}")
                    if 'message' in result:
                        self.log(f"   Mensaje: {result['message']}")
        
        self.log("=" * 50)
        
        if self.order_responses:
            self.log("✅ Prueba completada con respuestas")
        else:
            self.log("⚠️ Prueba completada sin respuestas", "WARNING")

async def main():
    """Función principal"""
    print("🧪 PRUEBA ESPECÍFICA: WEBSOCKET ORDER REPORTS Y ENVÍO DE ÓRDENES")
    print("=" * 80)
    
    tester = WebSocketOrderTest()
    
    # Verificar que el servidor esté funcionando
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/cotizaciones/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor FastAPI funcionando")
        else:
            print("❌ Servidor FastAPI no responde correctamente")
            return
    except Exception as e:
        print(f"❌ Error verificando servidor: {e}")
        return
    
    # Ejecutar prueba
    success = await tester.test_websocket_order_flow()
    
    # Mostrar resumen
    tester.print_summary()
    
    if success:
        print("\n🎉 PRUEBA COMPLETADA EXITOSAMENTE")
    else:
        print("\n❌ PRUEBA COMPLETADA CON ERRORES")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")

