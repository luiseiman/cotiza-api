#!/usr/bin/env python3
"""
Script para configurar el bot de Telegram paso a paso.
"""

import os
import sys

# Cargar variables de entorno desde archivo .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Archivo .env cargado correctamente")
except ImportError:
    print("❌ python-dotenv no instalado")
except Exception as e:
    print(f"❌ Error cargando .env: {e}")

def configurar_bot():
    """Configura el bot de Telegram paso a paso"""
    print("🤖 CONFIGURACIÓN DEL BOT DE TELEGRAM")
    print("=" * 50)
    
    # Verificar si ya está configurado
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    
    print(f"🔍 Verificando configuración...")
    print(f"   TELEGRAM_TOKEN: {'✅ Configurado' if token else '❌ No configurado'}")
    print(f"   TELEGRAM_CHAT_ID: {'✅ Configurado' if chat_id else '❌ No configurado'}")
    
    if token and chat_id:
        print("\n✅ Bot ya configurado:")
        print(f"   Token: {token[:10]}...")
        print(f"   Chat ID: {chat_id}")
        return True
    
    print("\n❌ Bot no configurado. Sigue estos pasos:\n")
    
    # Paso 1: Crear bot
    print("📱 PASO 1: Crear bot en Telegram")
    print("   1. Ve a @BotFather en Telegram")
    print("   2. Envía /newbot")
    print("   3. Sigue las instrucciones")
    print("   4. GUARDA EL TOKEN que te da\n")
    
    # Paso 2: Obtener Chat ID
    print("👤 PASO 2: Obtener tu Chat ID")
    print("   1. Ve a @userinfobot en Telegram")
    print("   2. Envía cualquier mensaje")
    print("   3. GUARDA TU CHAT ID (número)\n")
    
    # Solicitar configuración
    print("🔧 PASO 3: Configurar variables de entorno")
    print("   Ejecuta estos comandos en PowerShell:\n")
    
    # Generar comandos de configuración
    print("   # Configurar Token (reemplaza TU_TOKEN_AQUI):")
    print("   $env:TELEGRAM_TOKEN = 'TU_TOKEN_AQUI'")
    print("   [Environment]::SetEnvironmentVariable('TELEGRAM_TOKEN', 'TU_TOKEN_AQUI', 'User')\n")
    
    print("   # Configurar Chat ID (reemplaza TU_CHAT_ID_AQUI):")
    print("   $env:TELEGRAM_CHAT_ID = 'TU_CHAT_ID_AQUI'")
    print("   [Environment]::SetEnvironmentVariable('TELEGRAM_CHAT_ID', 'TU_CHAT_ID_AQUI', 'User')\n")
    
    print("   # Verificar configuración:")
    print("   echo $env:TELEGRAM_TOKEN")
    print("   echo $env:TELEGRAM_CHAT_ID\n")
    
    print("💡 ALTERNATIVA: Crear archivo .env")
    print("   Crea un archivo .env en la carpeta del proyecto con:")
    print("   TELEGRAM_TOKEN=tu_token_aqui")
    print("   TELEGRAM_CHAT_ID=tu_chat_id_aqui\n")
    
    return False

def verificar_configuracion():
    """Verifica si la configuración está completa"""
    print("🔍 VERIFICANDO CONFIGURACIÓN")
    print("=" * 30)
    
    token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    
    if not token:
        print("❌ TELEGRAM_TOKEN no configurado")
        return False
    
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID no configurado")
        return False
    
    print("✅ Configuración completa:")
    print(f"   Token: {token[:10]}...")
    print(f"   Chat ID: {chat_id}")
    
    return True

def probar_bot():
    """Prueba si el bot responde"""
    print("\n🧪 PROBANDO BOT")
    print("=" * 20)
    
    if not verificar_configuracion():
        return False
    
    print("✅ Configuración OK")
    print("📱 Ahora:")
    print("   1. Inicia la API: uvicorn main:app --host 127.0.0.1 --port 8000")
    print("   2. Ve a tu bot en Telegram")
    print("   3. Envía /start")
    print("   4. El bot debería responder")
    
    return True

def main():
    """Función principal"""
    if not configurar_bot():
        return False
    
    if not verificar_configuracion():
        return False
    
    probar_bot()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
