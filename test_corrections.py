#!/usr/bin/env python3
"""
Script de prueba para verificar las correcciones implementadas
"""

import asyncio
import json
import websockets
import requests
import time
from datetime import datetime

class CorrectionTester:
    def __init__(self):
        self.ws_url = "ws://127.0.0.1:8000/ws/cotizaciones"
        self.api_url = "http://127.0.0.1:8000"
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_api_endpoints(self):
        """Prueba los endpoints de la API"""
        self.log("🔧 Probando endpoints de la API...")
        
        # Probar endpoint de reconexión
        try:
            response = requests.post(f"{self.api_url}/cotizaciones/reconnect_rofex", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Endpoint reconexión: {data}")
            else:
                self.log(f"⚠️ Endpoint reconexión: {response.status_code}", "WARNING")
        except Exception as e:
            self.log(f"❌ Error endpoint reconexión: {e}", "ERROR")
        
        # Probar estado del sistema
        try:
            response = requests.get(f"{self.api_url}/cotizaciones/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Estado del sistema: WS={data.get('ws_connected')}, Worker={data.get('worker_running')}")
            else:
                self.log(f"⚠️ Error obteniendo estado: {response.status_code}", "WARNING")
        except Exception as e:
            self.log(f"❌ Error obteniendo estado: {e}", "ERROR")
    
    async def test_websocket_corrections(self):
        """Prueba las correcciones del WebSocket"""
        self.log("🔌 Probando correcciones del WebSocket...")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # 1. Conexión y bienvenida
                welcome = await websocket.recv()
                welcome_data = json.loads(welcome)
                self.log(f"✅ Conexión establecida: {welcome_data.get('type')}")
                
                # 2. Probar suscripción a order reports (corregida)
                self.log("📋 Probando suscripción a order reports (corregida)...")
                subscribe_msg = json.dumps({
                    "type": "orders_subscribe",
                    "account": "16557"
                })
                await websocket.send(subscribe_msg)
                
                subscribe_response = await websocket.recv()
                subscribe_data = json.loads(subscribe_response)
                self.log(f"📨 Respuesta suscripción: {subscribe_data}")
                
                # Verificar si la corrección funcionó
                if subscribe_data.get("result", {}).get("status") == "ok":
                    self.log("✅ Corrección de suscripción: EXITOSA")
                else:
                    error_msg = subscribe_data.get("result", {}).get("message", "")
                    if "accounts" in error_msg:
                        self.log("❌ Corrección de suscripción: FALLÓ (aún usa 'accounts')", "ERROR")
                    else:
                        self.log(f"⚠️ Suscripción con otro error: {error_msg}", "WARNING")
                
                # 3. Probar envío de orden con manejo mejorado de errores
                self.log("📤 Probando envío de orden con manejo mejorado...")
                order_msg = {
                    "type": "send_order",
                    "clOrdId": "TEST_CORRECTION_001",
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
                
                order_response = await websocket.recv()
                order_data = json.loads(order_response)
                self.log(f"📨 Respuesta orden: {json.dumps(order_data, indent=2)}")
                
                # Verificar manejo de errores mejorado
                result = order_data.get("result", {})
                if result.get("status") == "error":
                    error_msg = result.get("message", "")
                    if error_msg == "connection_closed":
                        self.log("✅ Manejo de error de conexión: DETECTADO")
                        if "reconnected" in result:
                            self.log("✅ Reconexión automática: EXITOSA")
                        else:
                            self.log("⚠️ Reconexión automática: NO INTENTADA", "WARNING")
                    elif error_msg == "authentication_failed":
                        self.log("✅ Manejo de error de autenticación: DETECTADO")
                    else:
                        self.log(f"⚠️ Otro tipo de error: {error_msg}", "WARNING")
                else:
                    self.log("✅ Orden enviada exitosamente")
                
                # 4. Probar ping-pong
                self.log("🏓 Probando ping-pong...")
                ping_msg = json.dumps({"type": "ping"})
                await websocket.send(ping_msg)
                
                pong_response = await websocket.recv()
                pong_data = json.loads(pong_response)
                if pong_data.get("type") == "pong":
                    self.log("✅ Ping-pong funcionando")
                else:
                    self.log("❌ Ping-pong falló", "ERROR")
                
        except Exception as e:
            self.log(f"❌ Error en prueba WebSocket: {e}", "ERROR")
    
    async def run_correction_tests(self):
        """Ejecuta todas las pruebas de corrección"""
        self.log("🚀 Iniciando pruebas de corrección...")
        self.log("=" * 60)
        
        # 1. Probar endpoints de API
        self.test_api_endpoints()
        self.log("-" * 40)
        
        # 2. Probar correcciones WebSocket
        await self.test_websocket_corrections()
        self.log("-" * 40)
        
        # 3. Resumen
        self.print_correction_summary()
    
    def print_correction_summary(self):
        """Imprime resumen de las correcciones"""
        self.log("📋 RESUMEN DE CORRECCIONES IMPLEMENTADAS")
        self.log("=" * 60)
        
        self.log("✅ CORRECCIONES APLICADAS:")
        self.log("1. Error de suscripción 'accounts' → 'account'")
        self.log("2. Manejo mejorado de errores de conexión")
        self.log("3. Reconexión automática implementada")
        self.log("4. Endpoint de reconexión manual agregado")
        self.log("5. Logging mejorado para debugging")
        
        self.log("\n🔧 FUNCIONALIDADES AGREGADAS:")
        self.log("• Función check_and_reconnect()")
        self.log("• Endpoint POST /cotizaciones/reconnect_rofex")
        self.log("• Reconexión automática en WebSocket")
        self.log("• Manejo específico de errores de autenticación")
        
        self.log("\n🎯 PRÓXIMOS PASOS:")
        self.log("• Probar con credenciales ROFEX válidas")
        self.log("• Verificar reconexión en producción")
        self.log("• Monitorear logs para errores adicionales")

async def main():
    """Función principal"""
    print("🔧 PRUEBAS DE CORRECCIONES IMPLEMENTADAS")
    print("=" * 60)
    
    tester = CorrectionTester()
    await tester.run_correction_tests()
    
    print("\n🎉 PRUEBAS DE CORRECCIÓN COMPLETADAS")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")

