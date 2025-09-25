#!/usr/bin/env python3
"""
Script de prueba de conexión a todos los servicios del sistema Cotiza API
Verifica: WebSocket ROFEX, Supabase, Telegram Bot, API FastAPI
"""

import os
import sys
import time
import json
import asyncio
import websockets
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv no instalado, usando variables de entorno del sistema")

class ConnectionTester:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_env_variables(self) -> Dict[str, Any]:
        """Verifica que las variables de entorno necesarias estén configuradas"""
        self.log("🔍 Verificando variables de entorno...")
        
        required_vars = {
            "ROFEX_USER": "Usuario de ROFEX",
            "ROFEX_PASSWORD": "Contraseña de ROFEX", 
            "ROFEX_ACCOUNT": "Cuenta de ROFEX",
            "SUPABASE_URL": "URL de Supabase",
            "SUPABASE_KEY": "Clave de Supabase",
            "TELEGRAM_TOKEN": "Token del bot de Telegram",
            "TELEGRAM_CHAT_ID": "Chat ID de Telegram"
        }
        
        results = {"status": "ok", "missing": [], "present": []}
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                # Ocultar valores sensibles
                if "PASSWORD" in var or "TOKEN" in var or "KEY" in var:
                    display_value = f"{value[:8]}..." if len(value) > 8 else "***"
                else:
                    display_value = value
                results["present"].append(f"{var}={display_value}")
                self.log(f"✅ {var}: {display_value}")
            else:
                results["missing"].append(var)
                self.log(f"❌ {var}: NO CONFIGURADO", "ERROR")
                
        if results["missing"]:
            results["status"] = "error"
            self.log(f"❌ Faltan {len(results['missing'])} variables críticas", "ERROR")
        else:
            self.log("✅ Todas las variables de entorno están configuradas")
            
        return results
    
    def test_supabase_connection(self) -> Dict[str, Any]:
        """Prueba la conexión a Supabase"""
        self.log("🗄️ Probando conexión a Supabase...")
        
        try:
            from supabase_client import supabase, get_active_pairs
            
            # Probar conexión básica
            pairs = get_active_pairs()
            
            result = {
                "status": "ok",
                "pairs_count": len(pairs),
                "connection": "successful"
            }
            
            self.log(f"✅ Supabase conectado - {len(pairs)} pares activos encontrados")
            
            # Mostrar algunos pares como ejemplo
            if pairs:
                sample_pairs = pairs[:3]
                for pair in sample_pairs:
                    base = pair.get("base_symbol", "N/A")
                    quote = pair.get("quote_symbol", "N/A")
                    self.log(f"   📊 Par: {base}/{quote}")
                    
            return result
            
        except Exception as e:
            self.log(f"❌ Error conectando a Supabase: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e),
                "connection": "failed"
            }
    
    def test_telegram_bot(self) -> Dict[str, Any]:
        """Prueba la conexión al bot de Telegram"""
        self.log("🤖 Probando bot de Telegram...")
        
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not token or not chat_id:
            return {
                "status": "error",
                "error": "Token o Chat ID no configurados",
                "connection": "failed"
            }
        
        try:
            # Probar API de Telegram
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get("ok"):
                    bot_data = bot_info.get("result", {})
                    result = {
                        "status": "ok",
                        "bot_username": bot_data.get("username"),
                        "bot_name": bot_data.get("first_name"),
                        "connection": "successful"
                    }
                    self.log(f"✅ Bot conectado: @{bot_data.get('username')} ({bot_data.get('first_name')})")
                    
                    # Probar envío de mensaje de prueba
                    try:
                        test_url = f"https://api.telegram.org/bot{token}/sendMessage"
                        test_data = {
                            "chat_id": int(chat_id),
                            "text": f"🧪 Mensaje de prueba - {datetime.now().strftime('%H:%M:%S')}"
                        }
                        test_response = requests.post(test_url, json=test_data, timeout=10)
                        
                        if test_response.status_code == 200:
                            self.log("✅ Mensaje de prueba enviado exitosamente")
                            result["test_message"] = "sent"
                        else:
                            self.log(f"⚠️ Error enviando mensaje de prueba: {test_response.status_code}", "WARNING")
                            result["test_message"] = "failed"
                            
                    except Exception as e:
                        self.log(f"⚠️ Error enviando mensaje de prueba: {e}", "WARNING")
                        result["test_message"] = "error"
                    
                    return result
                else:
                    raise Exception("Respuesta de API inválida")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log(f"❌ Error conectando bot de Telegram: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e),
                "connection": "failed"
            }
    
    def test_fastapi_server(self) -> Dict[str, Any]:
        """Prueba la API FastAPI local"""
        self.log("🚀 Probando servidor FastAPI...")
        
        api_base = os.getenv("API_BASE", "http://127.0.0.1:8000")
        
        try:
            # Probar endpoint de salud
            health_url = f"{api_base}/cotizaciones/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                health_data = response.json()
                result = {
                    "status": "ok",
                    "server_url": api_base,
                    "health_check": "successful",
                    "response": health_data
                }
                self.log(f"✅ Servidor FastAPI funcionando en {api_base}")
                
                # Probar endpoint de estado
                try:
                    status_url = f"{api_base}/cotizaciones/status"
                    status_response = requests.get(status_url, timeout=5)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        result["service_status"] = status_data
                        self.log(f"📊 Estado del servicio: {'🟢 Activo' if status_data.get('started') else '🔴 Inactivo'}")
                    else:
                        self.log(f"⚠️ Error obteniendo estado: {status_response.status_code}", "WARNING")
                except Exception as e:
                    self.log(f"⚠️ Error obteniendo estado: {e}", "WARNING")
                
                return result
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log(f"❌ Error conectando a FastAPI: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e),
                "connection": "failed"
            }
    
    async def test_websocket_connection(self) -> Dict[str, Any]:
        """Prueba la conexión WebSocket local"""
        self.log("🔌 Probando conexión WebSocket...")
        
        api_base = os.getenv("API_BASE", "http://127.0.0.1:8000")
        ws_url = api_base.replace("http://", "ws://").replace("https://", "wss://")
        ws_endpoint = f"{ws_url}/ws/cotizaciones"
        
        try:
            async with websockets.connect(ws_endpoint, timeout=10) as websocket:
                # Esperar mensaje de bienvenida
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data.get("type") == "connection":
                    self.log("✅ Conexión WebSocket establecida")
                    
                    # Probar ping-pong
                    ping_msg = json.dumps({"type": "ping"})
                    await websocket.send(ping_msg)
                    
                    pong_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                    pong_data = json.loads(pong_msg)
                    
                    if pong_data.get("type") == "pong":
                        self.log("✅ Ping-pong WebSocket funcionando")
                        return {
                            "status": "ok",
                            "ws_url": ws_endpoint,
                            "connection": "successful",
                            "ping_pong": "working"
                        }
                    else:
                        raise Exception("Respuesta ping-pong inválida")
                else:
                    raise Exception("Mensaje de bienvenida inválido")
                    
        except Exception as e:
            self.log(f"❌ Error conectando WebSocket: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e),
                "connection": "failed"
            }
    
    def test_rofex_websocket(self) -> Dict[str, Any]:
        """Prueba la conexión WebSocket de ROFEX (requiere credenciales válidas)"""
        self.log("🏦 Probando conexión WebSocket ROFEX...")
        
        user = os.getenv("ROFEX_USER")
        password = os.getenv("ROFEX_PASSWORD")
        account = os.getenv("ROFEX_ACCOUNT")
        
        if not all([user, password, account]):
            return {
                "status": "error",
                "error": "Credenciales ROFEX no configuradas",
                "connection": "skipped"
            }
        
        try:
            # Importar pyRofex
            import pyRofex as pr
            
            # Probar inicialización
            env = getattr(pr.Environment, "LIVE")
            pr.initialize(user=user, password=password, account=account, environment=env)
            
            self.log("✅ pyRofex inicializado correctamente")
            
            # Probar conexión WebSocket (sin mantenerla abierta)
            try:
                pr.init_websocket_connection(
                    market_data_handler=lambda msg: None,
                    order_report_handler=lambda msg: None,
                    error_handler=lambda e: None
                )
                
                # Cerrar inmediatamente
                pr.close_websocket_connection()
                
                result = {
                    "status": "ok",
                    "user": user,
                    "account": account,
                    "connection": "successful",
                    "environment": "LIVE"
                }
                self.log("✅ Conexión WebSocket ROFEX exitosa")
                return result
                
            except Exception as ws_error:
                self.log(f"⚠️ Error WebSocket ROFEX: {ws_error}", "WARNING")
                return {
                    "status": "warning",
                    "error": str(ws_error),
                    "connection": "partial",
                    "user": user,
                    "account": account
                }
                
        except ImportError:
            self.log("❌ pyRofex no instalado", "ERROR")
            return {
                "status": "error",
                "error": "pyRofex no disponible",
                "connection": "failed"
            }
        except Exception as e:
            self.log(f"❌ Error conectando ROFEX: {e}", "ERROR")
            return {
                "status": "error",
                "error": str(e),
                "connection": "failed"
            }
    
    async def run_all_tests(self):
        """Ejecuta todas las pruebas de conexión"""
        self.log("🚀 Iniciando pruebas de conexión completas...")
        self.log("=" * 60)
        
        # 1. Variables de entorno
        self.results["environment"] = self.test_env_variables()
        self.log("-" * 40)
        
        # 2. Supabase
        self.results["supabase"] = self.test_supabase_connection()
        self.log("-" * 40)
        
        # 3. Telegram Bot
        self.results["telegram"] = self.test_telegram_bot()
        self.log("-" * 40)
        
        # 4. FastAPI Server
        self.results["fastapi"] = self.test_fastapi_server()
        self.log("-" * 40)
        
        # 5. WebSocket local
        self.results["websocket"] = await self.test_websocket_connection()
        self.log("-" * 40)
        
        # 6. ROFEX WebSocket
        self.results["rofex"] = self.test_rofex_websocket()
        self.log("-" * 40)
        
        # Resumen final
        self.print_summary()
    
    def print_summary(self):
        """Imprime un resumen de todas las pruebas"""
        self.log("📋 RESUMEN DE PRUEBAS DE CONEXIÓN")
        self.log("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = 0
        failed_tests = 0
        warning_tests = 0
        
        for service, result in self.results.items():
            status = result.get("status", "unknown")
            service_name = service.upper()
            
            if status == "ok":
                successful_tests += 1
                icon = "✅"
            elif status == "error":
                failed_tests += 1
                icon = "❌"
            elif status == "warning":
                warning_tests += 1
                icon = "⚠️"
            else:
                icon = "❓"
            
            self.log(f"{icon} {service_name}: {status}")
            
            if result.get("error"):
                self.log(f"   Error: {result['error']}")
        
        self.log("-" * 40)
        self.log(f"📊 TOTAL: {total_tests} pruebas")
        self.log(f"✅ Exitosas: {successful_tests}")
        self.log(f"⚠️ Advertencias: {warning_tests}")
        self.log(f"❌ Fallidas: {failed_tests}")
        
        elapsed_time = time.time() - self.start_time
        self.log(f"⏱️ Tiempo total: {elapsed_time:.2f} segundos")
        
        # Guardar resultados en archivo
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": timestamp,
                    "elapsed_time": elapsed_time,
                    "summary": {
                        "total": total_tests,
                        "successful": successful_tests,
                        "warnings": warning_tests,
                        "failed": failed_tests
                    },
                    "results": self.results
                }, f, indent=2, ensure_ascii=False)
            
            self.log(f"💾 Resultados guardados en: {filename}")
            
        except Exception as e:
            self.log(f"⚠️ Error guardando resultados: {e}", "WARNING")

async def main():
    """Función principal"""
    print("🧪 PRUEBA DE CONEXIONES - COTIZA API")
    print("=" * 60)
    
    tester = ConnectionTester()
    await tester.run_all_tests()
    
    # Determinar código de salida
    failed_services = [s for s, r in tester.results.items() if r.get("status") == "error"]
    
    if failed_services:
        print(f"\n❌ Servicios con errores: {', '.join(failed_services)}")
        sys.exit(1)
    else:
        print(f"\n✅ Todas las pruebas completadas exitosamente")
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Pruebas interrumpidas por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)

