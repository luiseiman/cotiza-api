#!/usr/bin/env python3
"""
Script de demostración de pruebas de conexión
Simula las pruebas sin requerir configuración real
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

class DemoConnectionTester:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_env_variables_demo(self) -> Dict[str, Any]:
        """Simula verificación de variables de entorno"""
        self.log("🔍 Verificando variables de entorno (DEMO)...")
        
        # Simular variables configuradas
        demo_vars = {
            "ROFEX_USER": "demo_user",
            "ROFEX_PASSWORD": "demo_pass***",
            "ROFEX_ACCOUNT": "demo_account",
            "SUPABASE_URL": "https://demo.supabase.co",
            "SUPABASE_KEY": "demo_key***",
            "TELEGRAM_TOKEN": "demo_token***",
            "TELEGRAM_CHAT_ID": "123456789"
        }
        
        results = {"status": "ok", "missing": [], "present": []}
        
        for var, value in demo_vars.items():
            results["present"].append(f"{var}={value}")
            self.log(f"✅ {var}: {value}")
            
        self.log("✅ Todas las variables de entorno están configuradas (DEMO)")
        return results
    
    def test_supabase_connection_demo(self) -> Dict[str, Any]:
        """Simula prueba de conexión a Supabase"""
        self.log("🗄️ Probando conexión a Supabase (DEMO)...")
        
        # Simular conexión exitosa
        time.sleep(0.5)  # Simular latencia
        
        demo_pairs = [
            {"base_symbol": "GGAL", "quote_symbol": "USD"},
            {"base_symbol": "PAMP", "quote_symbol": "USD"},
            {"base_symbol": "YPF", "quote_symbol": "USD"}
        ]
        
        result = {
            "status": "ok",
            "pairs_count": len(demo_pairs),
            "connection": "successful"
        }
        
        self.log(f"✅ Supabase conectado - {len(demo_pairs)} pares activos encontrados")
        
        for pair in demo_pairs:
            base = pair.get("base_symbol", "N/A")
            quote = pair.get("quote_symbol", "N/A")
            self.log(f"   📊 Par: {base}/{quote}")
            
        return result
    
    def test_telegram_bot_demo(self) -> Dict[str, Any]:
        """Simula prueba del bot de Telegram"""
        self.log("🤖 Probando bot de Telegram (DEMO)...")
        
        # Simular conexión exitosa
        time.sleep(0.3)
        
        result = {
            "status": "ok",
            "bot_username": "cotiza_demo_bot",
            "bot_name": "Cotiza Demo Bot",
            "connection": "successful",
            "test_message": "sent"
        }
        
        self.log("✅ Bot conectado: @cotiza_demo_bot (Cotiza Demo Bot)")
        self.log("✅ Mensaje de prueba enviado exitosamente")
        
        return result
    
    def test_fastapi_server_demo(self) -> Dict[str, Any]:
        """Simula prueba del servidor FastAPI"""
        self.log("🚀 Probando servidor FastAPI (DEMO)...")
        
        api_base = "http://127.0.0.1:8000"
        
        # Simular servidor funcionando
        time.sleep(0.2)
        
        result = {
            "status": "ok",
            "server_url": api_base,
            "health_check": "successful",
            "response": {"status": "healthy", "timestamp": time.time()},
            "service_status": {
                "started": False,
                "user": None,
                "account": None,
                "worker_status": "stopped",
                "ws_connected": False
            }
        }
        
        self.log(f"✅ Servidor FastAPI funcionando en {api_base}")
        self.log("📊 Estado del servicio: 🔴 Inactivo (DEMO)")
        
        return result
    
    async def test_websocket_connection_demo(self) -> Dict[str, Any]:
        """Simula prueba de conexión WebSocket"""
        self.log("🔌 Probando conexión WebSocket (DEMO)...")
        
        ws_url = "ws://127.0.0.1:8000/ws/cotizaciones"
        
        # Simular conexión exitosa
        await asyncio.sleep(0.4)
        
        result = {
            "status": "ok",
            "ws_url": ws_url,
            "connection": "successful",
            "ping_pong": "working"
        }
        
        self.log("✅ Conexión WebSocket establecida")
        self.log("✅ Ping-pong WebSocket funcionando")
        
        return result
    
    def test_rofex_websocket_demo(self) -> Dict[str, Any]:
        """Simula prueba de conexión WebSocket ROFEX"""
        self.log("🏦 Probando conexión WebSocket ROFEX (DEMO)...")
        
        # Simular conexión exitosa
        time.sleep(0.6)
        
        result = {
            "status": "ok",
            "user": "demo_user",
            "account": "demo_account",
            "connection": "successful",
            "environment": "LIVE"
        }
        
        self.log("✅ Conexión WebSocket ROFEX exitosa")
        
        return result
    
    async def run_demo_tests(self):
        """Ejecuta todas las pruebas de demostración"""
        self.log("🚀 Iniciando pruebas de conexión DEMO...")
        self.log("=" * 60)
        
        # 1. Variables de entorno
        self.results["environment"] = self.test_env_variables_demo()
        self.log("-" * 40)
        
        # 2. Supabase
        self.results["supabase"] = self.test_supabase_connection_demo()
        self.log("-" * 40)
        
        # 3. Telegram Bot
        self.results["telegram"] = self.test_telegram_bot_demo()
        self.log("-" * 40)
        
        # 4. FastAPI Server
        self.results["fastapi"] = self.test_fastapi_server_demo()
        self.log("-" * 40)
        
        # 5. WebSocket local
        self.results["websocket"] = await self.test_websocket_connection_demo()
        self.log("-" * 40)
        
        # 6. ROFEX WebSocket
        self.results["rofex"] = self.test_rofex_websocket_demo()
        self.log("-" * 40)
        
        # Resumen final
        self.print_summary()
    
    def print_summary(self):
        """Imprime un resumen de todas las pruebas"""
        self.log("📋 RESUMEN DE PRUEBAS DE CONEXIÓN (DEMO)")
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
            filename = f"demo_test_results_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": timestamp,
                    "elapsed_time": elapsed_time,
                    "demo_mode": True,
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
        
        self.log("=" * 60)
        self.log("🎯 INSTRUCCIONES PARA PRUEBAS REALES:")
        self.log("1. Configurar archivo .env con credenciales reales")
        self.log("2. Iniciar servidor: uvicorn main:app --host 0.0.0.0 --port 8000")
        self.log("3. Ejecutar: python3 test_conexiones.py")
        self.log("4. Para WebSocket específico: python3 test_websocket.py")

async def main():
    """Función principal"""
    print("🧪 PRUEBA DE CONEXIONES - COTIZA API (MODO DEMO)")
    print("=" * 60)
    print("ℹ️ Este es un modo de demostración que simula las pruebas")
    print("ℹ️ Para pruebas reales, configure las variables de entorno")
    print("=" * 60)
    
    tester = DemoConnectionTester()
    await tester.run_demo_tests()
    
    print(f"\n✅ Demostración completada exitosamente")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Demostración interrumpida por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)

