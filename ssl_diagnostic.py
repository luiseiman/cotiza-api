#!/usr/bin/env python3
"""
Script para configurar certificados SSL en macOS
"""

import ssl
import os
import subprocess
import sys
from datetime import datetime

def print_ssl_info():
    """Imprime información sobre la configuración SSL actual"""
    print("🔒 INFORMACIÓN SSL ACTUAL")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("🔍 Configuración SSL del sistema:")
    print(f"• Python version: {sys.version}")
    print(f"• SSL version: {ssl.OPENSSL_VERSION}")
    print(f"• SSL version info: {ssl.OPENSSL_VERSION_INFO}")
    print()
    
    print("📁 Certificados del sistema:")
    try:
        cert_path = ssl.get_default_verify_paths()
        print(f"• Certificados por defecto: {cert_path.default_cafile}")
        print(f"• Directorio de certificados: {cert_path.default_capath}")
        print(f"• Certificados del sistema: {cert_path.cafile}")
        print(f"• Directorio del sistema: {cert_path.capath}")
    except Exception as e:
        print(f"❌ Error obteniendo información de certificados: {e}")
    print()
    
    print("🔧 Configuración SSL recomendada para macOS:")
    print("• ssl_context.check_hostname = False")
    print("• ssl_context.verify_mode = ssl.CERT_NONE")
    print("• Usar contexto SSL personalizado")
    print()

def test_ssl_context():
    """Prueba la configuración SSL"""
    print("🧪 PROBANDO CONFIGURACIÓN SSL")
    print("=" * 50)
    
    try:
        # Crear contexto SSL personalizado
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        print("✅ Contexto SSL personalizado creado exitosamente")
        print(f"• check_hostname: {ssl_context.check_hostname}")
        print(f"• verify_mode: {ssl_context.verify_mode}")
        
        return ssl_context
        
    except Exception as e:
        print(f"❌ Error creando contexto SSL: {e}")
        return None

def install_certificates():
    """Instala certificados actualizados en macOS"""
    print("📦 INSTALANDO CERTIFICADOS ACTUALIZADOS")
    print("=" * 50)
    
    try:
        # Comando para actualizar certificados en macOS
        result = subprocess.run([
            "/Applications/Python 3.13/Install Certificates.command"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Certificados actualizados exitosamente")
            print(result.stdout)
        else:
            print("⚠️ Error actualizando certificados:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout ejecutando instalador de certificados")
    except FileNotFoundError:
        print("❌ Instalador de certificados no encontrado")
        print("💡 Intenta ejecutar manualmente:")
        print("   /Applications/Python 3.13/Install Certificates.command")
    except Exception as e:
        print(f"❌ Error ejecutando instalador: {e}")

def create_ssl_fix_script():
    """Crea un script para aplicar la corrección SSL"""
    print("📝 CREANDO SCRIPT DE CORRECCIÓN SSL")
    print("=" * 50)
    
    script_content = '''#!/usr/bin/env python3
"""
Script para aplicar corrección SSL en pyRofex
"""

import ssl
import os

def apply_ssl_fix():
    """Aplica la corrección SSL para macOS"""
    print("🔒 Aplicando corrección SSL...")
    
    # Configurar contexto SSL
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Configurar variables de entorno
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['SSL_VERIFY'] = 'False'
    
    print("✅ Corrección SSL aplicada")
    return ssl_context

if __name__ == "__main__":
    apply_ssl_fix()
'''
    
    try:
        with open('ssl_fix.py', 'w') as f:
            f.write(script_content)
        print("✅ Script ssl_fix.py creado exitosamente")
    except Exception as e:
        print(f"❌ Error creando script: {e}")

def main():
    """Función principal"""
    print("🔒 DIAGNÓSTICO Y CORRECCIÓN SSL PARA macOS")
    print("=" * 60)
    print()
    
    # Información SSL
    print_ssl_info()
    
    # Probar contexto SSL
    ssl_context = test_ssl_context()
    
    # Instalar certificados
    install_certificates()
    
    # Crear script de corrección
    create_ssl_fix_script()
    
    print("🎯 RECOMENDACIONES FINALES:")
    print("=" * 50)
    print("1. 🔧 Usar contexto SSL personalizado en pyRofex")
    print("2. 📦 Actualizar certificados del sistema")
    print("3. 🔄 Reiniciar el servidor después de aplicar correcciones")
    print("4. 🧪 Probar la conexión ROFEX")
    print()
    
    print("💡 COMANDOS ÚTILES:")
    print("• Actualizar certificados: /Applications/Python 3.13/Install Certificates.command")
    print("• Verificar SSL: python3 -c 'import ssl; print(ssl.OPENSSL_VERSION)'")
    print("• Probar contexto: python3 ssl_fix.py")
    print()
    
    if ssl_context:
        print("✅ El contexto SSL personalizado está listo para usar")
    else:
        print("❌ Hay problemas con la configuración SSL")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Diagnóstico SSL interrumpido por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")

