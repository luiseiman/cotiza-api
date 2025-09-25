#!/usr/bin/env python3
"""
Script específico para probar conexiones WebSocket
Incluye pruebas para WebSocket local y ROFEX
"""

import asyncio
import json
import time
import websockets
from typing import Dict, Any
from datetime import datetime

class WebSocketTester:
    def __init__(self):
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    async def test_local_websocket(self, url: str = "ws://127.0.0.1:8000/ws/cotizaciones") -> Dict[str, Any]:
        """Prueba la conexión WebSocket local de la API"""
        self.log(f"🔌 Probando WebSocket local: {url}")
        
        try:
            async with websockets.connect(url, timeout=10) as websocket:
                # 1. Recibir mensaje de bienvenida
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data.get("type") != "connection":
                    raise Exception("Mensaje de bienvenida inválido")
                
                self.log("✅ Conexión WebSocket establecida")
                
                # 2. Probar ping-pong
                ping_msg = json.dumps({"type": "ping"})
                await websocket.send(ping_msg)
                
                pong_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                pong_data = json.loads(pong_msg)
                
                if pong_data.get("type") != "pong":
                    raise Exception("Respuesta ping-pong inválida")
                
                self.log("✅ Ping-pong funcionando")
                
                # 3. Probar suscripción a instrumentos
                subscribe_msg = json.dumps({
                    "type": "subscribe",
                    "instruments": ["GGAL", "PAMP"]
                })
                await websocket.send(subscribe_msg)
                
                subscribe_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                subscribe_data = json.loads(subscribe_response)
                
                if subscribe_data.get("type") != "subscribed":
                    raise Exception("Respuesta de suscripción inválida")
                
                self.log("✅ Suscripción a instrumentos funcionando")
                
                # 4. Probar suscripción a order reports
                order_subscribe_msg = json.dumps({
                    "type": "orders_subscribe",
                    "account": "test_account"
                })
                await websocket.send(order_subscribe_msg)
                
                order_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                order_data = json.loads(order_response)
                
                if order_data.get("type") not in ["orders_subscribed", "error"]:
                    raise Exception("Respuesta de suscripción a orders inválida")
                
                self.log("✅ Suscripción a order reports funcionando")
                
                return {
                    "status": "ok",
                    "url": url,
                    "connection": "successful",
                    "ping_pong": "working",
                    "subscriptions": "working",
                    "order_reports": "working"
                }
                
        except Exception as e:
            self.log(f"❌ Error WebSocket local: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e),
                "connection": "failed"
            }
    
    async def test_rofex_websocket_connection(self) -> Dict[str, Any]:
        """Prueba la conexión WebSocket de ROFEX"""
        self.log("🏦 Probando conexión WebSocket ROFEX...")
        
        try:
            import pyRofex as pr
            
            # Configurar credenciales
            user = "test_user"  # Usar credenciales reales del .env
            password = "test_password"
            account = "test_account"
            
            # Inicializar pyRofex
            env = getattr(pr.Environment, "LIVE")
            pr.initialize(user=user, password=password, account=account, environment=env)
            
            self.log("✅ pyRofex inicializado")
            
            # Variables para capturar datos
            market_data_received = False
            order_report_received = False
            connection_established = False
            
            def market_data_handler(msg):
                nonlocal market_data_received
                market_data_received = True
                self.log(f"📊 Market data recibido: {msg.get('instrumentId', {}).get('symbol', 'N/A')}")
            
            def order_report_handler(msg):
                nonlocal order_report_received
                order_report_received = True
                self.log(f"📋 Order report recibido: {msg.get('status', 'N/A')}")
            
            def error_handler(error):
                self.log(f"⚠️ Error ROFEX: {error}", "WARNING")
            
            # Establecer conexión WebSocket
            pr.init_websocket_connection(
                market_data_handler=market_data_handler,
                order_report_handler=order_report_handler,
                error_handler=error_handler
            )
            
            connection_established = True
            self.log("✅ Conexión WebSocket ROFEX establecida")
            
            # Suscribir a algunos instrumentos
            try:
                entries = [
                    pr.MarketDataEntry.BIDS,
                    pr.MarketDataEntry.OFFERS,
                    pr.MarketDataEntry.LAST
                ]
                pr.market_data_subscription(tickers=["GGAL", "PAMP"], entries=entries)
                self.log("✅ Suscripción a market data establecida")
            except Exception as e:
                self.log(f"⚠️ Error suscribiendo market data: {e}", "WARNING")
            
            # Suscribir a order reports
            try:
                pr.order_report_subscription(account=account)
                self.log("✅ Suscripción a order reports establecida")
            except Exception as e:
                self.log(f"⚠️ Error suscribiendo order reports: {e}", "WARNING")
            
            # Esperar un poco para recibir datos
            await asyncio.sleep(3)
            
            # Cerrar conexión
            pr.close_websocket_connection()
            self.log("✅ Conexión WebSocket ROFEX cerrada")
            
            return {
                "status": "ok",
                "connection": "successful",
                "market_data_received": market_data_received,
                "order_report_received": order_report_received,
                "subscriptions": "working"
            }
            
        except ImportError:
            self.log("❌ pyRofex no instalado", "ERROR")
            return {
                "status": "error",
                "error": "pyRofex no disponible",
                "connection": "failed"
            }
        except Exception as e:
            self.log(f"❌ Error WebSocket ROFEX: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e),
                "connection": "failed"
            }
    
    async def test_websocket_stress(self, url: str = "ws://127.0.0.1:8000/ws/cotizaciones") -> Dict[str, Any]:
        """Prueba de estrés del WebSocket local"""
        self.log(f"💪 Iniciando prueba de estrés WebSocket: {url}")
        
        connections = []
        successful_connections = 0
        failed_connections = 0
        
        try:
            # Crear múltiples conexiones simultáneas
            async def create_connection(conn_id: int):
                nonlocal successful_connections, failed_connections
                try:
                    async with websockets.connect(url, timeout=5) as websocket:
                        # Recibir bienvenida
                        welcome = await asyncio.wait_for(websocket.recv(), timeout=3)
                        welcome_data = json.loads(welcome)
                        
                        if welcome_data.get("type") == "connection":
                            successful_connections += 1
                            self.log(f"✅ Conexión {conn_id} establecida")
                            
                            # Mantener conexión activa
                            await asyncio.sleep(2)
                            
                            # Probar ping
                            ping_msg = json.dumps({"type": "ping"})
                            await websocket.send(ping_msg)
                            
                            pong = await asyncio.wait_for(websocket.recv(), timeout=3)
                            pong_data = json.loads(pong)
                            
                            if pong_data.get("type") == "pong":
                                self.log(f"✅ Ping-pong {conn_id} funcionando")
                            else:
                                self.log(f"⚠️ Ping-pong {conn_id} falló", "WARNING")
                        else:
                            failed_connections += 1
                            self.log(f"❌ Conexión {conn_id} falló: mensaje inválido", "ERROR")
                            
                except Exception as e:
                    failed_connections += 1
                    self.log(f"❌ Conexión {conn_id} falló: {e}", "ERROR")
            
            # Crear 5 conexiones simultáneas
            tasks = [create_connection(i) for i in range(1, 6)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            total_connections = successful_connections + failed_connections
            success_rate = (successful_connections / total_connections * 100) if total_connections > 0 else 0
            
            self.log(f"📊 Prueba de estrés completada:")
            self.log(f"   Total conexiones: {total_connections}")
            self.log(f"   Exitosas: {successful_connections}")
            self.log(f"   Fallidas: {failed_connections}")
            self.log(f"   Tasa de éxito: {success_rate:.1f}%")
            
            return {
                "status": "ok" if success_rate >= 80 else "warning",
                "total_connections": total_connections,
                "successful_connections": successful_connections,
                "failed_connections": failed_connections,
                "success_rate": success_rate
            }
            
        except Exception as e:
            self.log(f"❌ Error en prueba de estrés: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_websocket_tests(self):
        """Ejecuta todas las pruebas de WebSocket"""
        self.log("🚀 Iniciando pruebas específicas de WebSocket...")
        self.log("=" * 60)
        
        # 1. WebSocket local
        self.results["local_websocket"] = await self.test_local_websocket()
        self.log("-" * 40)
        
        # 2. Prueba de estrés
        self.results["stress_test"] = await self.test_websocket_stress()
        self.log("-" * 40)
        
        # 3. WebSocket ROFEX (opcional)
        self.results["rofex_websocket"] = await self.test_rofex_websocket_connection()
        self.log("-" * 40)
        
        # Resumen
        self.print_websocket_summary()
    
    def print_websocket_summary(self):
        """Imprime resumen de pruebas WebSocket"""
        self.log("📋 RESUMEN DE PRUEBAS WEBSOCKET")
        self.log("=" * 60)
        
        for test_name, result in self.results.items():
            status = result.get("status", "unknown")
            test_display = test_name.replace("_", " ").title()
            
            if status == "ok":
                icon = "✅"
            elif status == "warning":
                icon = "⚠️"
            elif status == "error":
                icon = "❌"
            else:
                icon = "❓"
            
            self.log(f"{icon} {test_display}: {status}")
            
            if result.get("error"):
                self.log(f"   Error: {result['error']}")
            elif test_name == "stress_test":
                self.log(f"   Tasa de éxito: {result.get('success_rate', 0):.1f}%")

async def main():
    """Función principal"""
    print("🔌 PRUEBAS ESPECÍFICAS DE WEBSOCKET")
    print("=" * 60)
    
    tester = WebSocketTester()
    await tester.run_websocket_tests()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")