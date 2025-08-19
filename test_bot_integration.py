#!/usr/bin/env python3
"""
Script para probar la integración del bot exactamente como lo hace ensure_started.
"""

import os
import sys
import threading
import time

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Archivo .env cargado")
except Exception as e:
    print(f"❌ Error cargando .env: {e}")
    sys.exit(1)

# Verificar configuración
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print(f"Token: {BOT_TOKEN[:10] if BOT_TOKEN else 'No configurado'}...")
print(f"Chat ID: {ADMIN_CHAT_ID}")

if not BOT_TOKEN or not ADMIN_CHAT_ID:
    print("❌ Configuración incompleta")
    sys.exit(1)

# Probar importación de telebot
try:
    import telebot
    from telebot.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
    print("✅ telebot importado correctamente")
except ImportError as e:
    print(f"❌ Error importando telebot: {e}")
    sys.exit(1)

# Simular ensure_started paso a paso
print("\n🔧 SIMULANDO ensure_started...")

# 1. Crear bot
try:
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
    print("✅ Bot creado correctamente")
except Exception as e:
    print(f"❌ Error al crear bot: {e}")
    sys.exit(1)

# 2. Eliminar webhook (simular _safe_delete_webhook)
try:
    bot.delete_webhook()
    print("✅ Webhook eliminado correctamente")
except Exception as e:
    print(f"❌ Error eliminando webhook: {e}")

# 3. Configurar comandos (simular _set_bot_commands)
try:
    commands = [
        BotCommand("start", "Iniciar servicio"),
        BotCommand("stop", "Detener servicio"),
        BotCommand("restart", "Reiniciar servicio"),
        BotCommand("status", "Estado del servicio"),
        BotCommand("rules", "Ver reglas"),
        BotCommand("addrule", "Agregar regla"),
        BotCommand("delrule", "Eliminar regla"),
        BotCommand("help", "Ayuda"),
        BotCommand("ping", "Ping del bot")
    ]
    bot.set_my_commands(commands)
    print("✅ Comandos configurados correctamente")
except Exception as e:
    print(f"❌ Error configurando comandos: {e}")

# 4. Registrar handlers básicos (simular _register_handlers)
@bot.message_handler(commands=['ping'])
def ping_handler(message):
    try:
        bot.reply_to(message, "🏓 ¡Pong! Bot funcionando correctamente.")
        print(f"✅ Comando /ping respondido a chat {message.chat.id}")
    except Exception as e:
        print(f"❌ Error respondiendo /ping: {e}")

@bot.message_handler(commands=['start'])
def start_handler(message):
    try:
        bot.reply_to(message, "🚀 Comando /start recibido correctamente.")
        print(f"✅ Comando /start respondido a chat {message.chat.id}")
    except Exception as e:
        print(f"❌ Error respondiendo /start: {e}")

print("✅ Handlers registrados correctamente")

# 5. Iniciar polling en background
def run_polling():
    try:
        print("🔄 Iniciando polling...")
        bot.infinity_polling(skip_pending=True, allowed_updates=[], timeout=10)
    except Exception as e:
        print(f"❌ Error en polling: {e}")

bot_thread = threading.Thread(target=run_polling, daemon=True)
bot_thread.start()
print("✅ Polling iniciado en background")

# 6. Enviar mensaje de prueba
try:
    print("📱 Enviando mensaje de prueba...")
    result = bot.send_message(ADMIN_CHAT_ID, "🧪 Bot de integración funcionando correctamente!")
    print(f"✅ Mensaje enviado: {result.message_id}")
except Exception as e:
    print(f"❌ Error enviando mensaje: {e}")

# 7. Esperar un poco y verificar
print("\n⏳ Esperando 10 segundos para verificar funcionamiento...")
time.sleep(10)

print("\n🎯 INSTRUCCIONES:")
print("1. Ve a tu bot en Telegram")
print("2. Envía /ping")
print("3. Envía /start")
print("4. Verifica que responda correctamente")

print("\n🔍 Si no responde, el problema está en el polling o en la configuración del bot.")
print("🔍 Si responde, el problema está en la integración con la API.")
