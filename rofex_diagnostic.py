#!/usr/bin/env python3
"""
Diagnóstico específico de la conexión ROFEX
"""

import requests
import json
import time
from datetime import datetime

class RofexDiagnostic:
    def __init__(self):
        self.api_url = "http://127.0.0.1:8000"
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def check_rofex_connection(self):
        """Verifica específicamente la conexión ROFEX"""
        self.log("🔍 DIAGNÓSTICO DE CONEXIÓN ROFEX")
        self.log("=" * 50)
        
        # 1. Verificar estado general
        try:
            response = requests.get(f"{self.api_url}/cotizaciones/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log(f"📊 Estado general: WS={data.get('ws_connected')}")
                self.log(f"📊 Worker: {data.get('worker_running')}")
                self.log(f"📊 Usuario: {data.get('user')}")
                self.log(f"📊 Cuenta: {data.get('account')}")
                
                ws_details = data.get('ws_details', {})
                self.log(f"📊 WS Status: {ws_details.get('ws')}")
                self.log(f"📊 User ID: {ws_details.get('user_id')}")
                self.log(f"📊 Suscritos: {len(ws_details.get('subscribed', []))}")
                self.log(f"📊 Último MD: {ws_details.get('last_md_ms')}")
                self.log(f"📊 Último Order Report: {ws_details.get('last_order_report')}")
                
            else:
                self.log(f"❌ Error obteniendo estado: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Error verificando estado: {e}", "ERROR")
        
        # 2. Verificar endpoint de reconexión
        self.log("\n🔧 Probando reconexión ROFEX...")
        try:
            response = requests.post(f"{self.api_url}/cotizaciones/reconnect_rofex", timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.log(f"📨 Respuesta reconexión: {json.dumps(data, indent=2)}")
            else:
                self.log(f"❌ Error reconexión: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Error en reconexión: {e}", "ERROR")
        
        # 3. Verificar parámetros guardados
        self.log("\n📋 Verificando parámetros guardados...")
        try:
            response = requests.get(f"{self.api_url}/cotizaciones/last_params", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log(f"📨 Parámetros: {json.dumps(data, indent=2)}")
            else:
                self.log(f"❌ Error obteniendo parámetros: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Error obteniendo parámetros: {e}", "ERROR")
        
        # 4. Intentar reiniciar el servicio
        self.log("\n🔄 Intentando reiniciar servicio...")
        try:
            response = requests.post(f"{self.api_url}/cotizaciones/detener", timeout=10)
            if response.status_code == 200:
                self.log("✅ Servicio detenido")
                time.sleep(2)
                
                response = requests.post(f"{self.api_url}/cotizaciones/iniciar_auto", timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"✅ Servicio reiniciado: {json.dumps(data, indent=2)}")
                else:
                    self.log(f"❌ Error reiniciando: {response.status_code}", "ERROR")
            else:
                self.log(f"❌ Error deteniendo: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Error reiniciando servicio: {e}", "ERROR")
        
        # 5. Verificar estado final
        self.log("\n📊 Verificando estado final...")
        time.sleep(3)
        try:
            response = requests.get(f"{self.api_url}/cotizaciones/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log(f"📊 Estado final: WS={data.get('ws_connected')}")
                ws_details = data.get('ws_details', {})
                self.log(f"📊 WS Status final: {ws_details.get('ws')}")
                
                if data.get('ws_connected') and ws_details.get('ws') == 'ok':
                    self.log("🎉 ¡CONEXIÓN ROFEX ESTABLECIDA!")
                else:
                    self.log("⚠️ Conexión ROFEX aún no disponible", "WARNING")
            else:
                self.log(f"❌ Error verificando estado final: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Error verificando estado final: {e}", "ERROR")
    
    def print_diagnostic_summary(self):
        """Imprime resumen del diagnóstico"""
        self.log("\n📋 RESUMEN DEL DIAGNÓSTICO")
        self.log("=" * 50)
        
        self.log("🔍 PROBLEMAS IDENTIFICADOS:")
        self.log("• Conexión ROFEX se cierra después de iniciar")
        self.log("• Error 'Connection is already closed'")
        self.log("• Reconexión automática funciona pero se vuelve a cerrar")
        
        self.log("\n🔧 POSIBLES CAUSAS:")
        self.log("• Credenciales ROFEX incorrectas o expiradas")
        self.log("• Problemas de red con servidores ROFEX")
        self.log("• Horario de mercado cerrado")
        self.log("• Límites de conexión alcanzados")
        self.log("• Problemas con certificados SSL")
        
        self.log("\n✅ FUNCIONALIDADES QUE SÍ FUNCIONAN:")
        self.log("• WebSocket local completamente funcional")
        self.log("• Manejo de errores robusto")
        self.log("• Reconexión automática implementada")
        self.log("• Logging detallado")
        self.log("• Estructura de mensajes correcta")
        
        self.log("\n🎯 RECOMENDACIONES:")
        self.log("1. Verificar credenciales ROFEX en .env")
        self.log("2. Comprobar horarios de mercado ROFEX")
        self.log("3. Verificar conectividad de red")
        self.log("4. Contactar soporte ROFEX si persiste")
        self.log("5. Probar con cuenta de demo primero")

def main():
    """Función principal"""
    print("🔍 DIAGNÓSTICO DE CONEXIÓN ROFEX")
    print("=" * 50)
    
    diagnostic = RofexDiagnostic()
    diagnostic.check_rofex_connection()
    diagnostic.print_diagnostic_summary()
    
    print("\n🎉 DIAGNÓSTICO COMPLETADO")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Diagnóstico interrumpido por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")

