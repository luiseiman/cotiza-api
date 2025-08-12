# telegram_control.py
import os
import json
import threading
import requests
from dotenv import load_dotenv

from params_store import get_last_params

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

_bot_started = False  # anti doble arranque

def notify_http(text: str):
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("[telegram] notify_http skipped:", text)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=5,
        )
    except Exception as e:
        print("[telegram] HTTP send error:", e)

def build_bot(manager, get_health_age_seconds):
    global _bot_started
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("[telegram] Sin TELEGRAM_TOKEN/CHAT_ID. Bot deshabilitado.")
        return notify_http

    try:
        import telebot  # pyTelegramBotAPI
    except Exception as e:
        print("[telegram] pyTelegramBotAPI no instalada. Usando HTTP fallback. Error:", e)
        return notify_http

    if _bot_started:
        print("[telegram] Bot ya estaba iniciado, reutilizando notify.")
        return notify_http

    bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)

    # eliminar webhook por si estaba activo (evita error 409)
    try:
        bot.remove_webhook()
        print("[telegram] webhook eliminado (si existía)")
    except Exception as e:
        print("[telegram] no se pudo eliminar webhook:", e)

    @bot.message_handler(commands=["restart_feed"])
    def restart_feed(message):
        params = get_last_params()
        if not params:
            bot.send_message(TELEGRAM_CHAT_ID, "❌ No hay parámetros previos. El inicio solo es por REST.")
            return
        if manager.is_running():
            manager.stop()
        bot.send_message(TELEGRAM_CHAT_ID, "♻️ Reiniciando feed con los últimos parámetros REST...")
        manager.start(params["instrumentos"], params["user"], params["password"], params["account"])
        bot.send_message(TELEGRAM_CHAT_ID, f"✅ Reiniciado con: {params['instrumentos']}")

    @bot.message_handler(commands=["stop_feed"])
    def stop_feed(message):
        if manager.is_running():
            manager.stop()
            bot.send_message(TELEGRAM_CHAT_ID, "🛑 Suscripción detenida por comando.")
        else:
            bot.send_message(TELEGRAM_CHAT_ID, "ℹ️ No hay suscripción activa.")

    @bot.message_handler(commands=["status"])
    def status(message):
        running = manager.is_running()
        age = int(get_health_age_seconds()) if running else None
        txt = f"📊 Estado: {'ACTIVO' if running else 'PARADO'}"
        if running:
            txt += f"\n⏱️ Último tick hace {age}s"
        bot.send_message(TELEGRAM_CHAT_ID, txt)

    @bot.message_handler(commands=["help"])
    def help_cmd(message):
        bot.send_message(TELEGRAM_CHAT_ID, "/restart_feed – Reinicia con últimos parámetros del REST\n/stop_feed – Detiene\n/status – Estado")

    def _poll():
        print("[telegram] Bot polling (telebot) iniciado")
        bot.infinity_polling(skip_pending=True, long_polling_timeout=30)

    _bot_started = True
    threading.Thread(target=_poll, daemon=True).start()

    def notify(text: str):
        try:
            bot.send_message(TELEGRAM_CHAT_ID, text)
        except Exception as e:
            print("[telegram] send_message error, fallback HTTP:", e)
            notify_http(text)

    return notify
