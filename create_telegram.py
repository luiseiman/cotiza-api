#!/usr/bin/env python3
# Script temporal para crear telegram_control.py

content = '''# telegram_control.py
import os
import json
import threading
from typing import Any, Dict, Optional, Callable

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import telebot
    from telebot.types import ReplyKeyboardMarkup, KeyboardButton
except ImportError:
    telebot = None

import requests

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

_bot = None
_bot_thread = None
_started = False
_callbacks = {"start": None, "restart": None, "stop": None, "status": None}

def _post(path, data=None):
    url = f"{API_BASE}{path}"
    try:
        r = requests.post(url, json=data or {}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _get(path):
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _build_menu():
    if telebot is None:
        return None
    try:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row(KeyboardButton("/status"), KeyboardButton("/ping"))
        return kb
    except:
        return None

def _register_handlers(bot):
    if telebot is None:
        return
    menu = _build_menu()
    
    @bot.message_handler(commands=["ping"])
    def _ping(m):
        bot.send_message(m.chat.id, "Pong - Bot funcionando", reply_markup=menu)
    
    @bot.message_handler(commands=["start"])
    def _start(m):
        try:
            payload = m.text.partition(" ")[2].strip()
            if not payload:
                bot.send_message(m.chat.id, "Use: /start {json}", reply_markup=menu)
                return
            data = json.loads(payload)
            bot.send_message(m.chat.id, "Iniciando servicio...", reply_markup=menu)
            if callable(_callbacks.get("start")):
                try:
                    from main import IniciarRequest
                    request_obj = IniciarRequest(**data)
                    res = _callbacks["start"](request_obj)
                except Exception as e:
                    res = {"status": "error", "message": f"Error validando datos: {str(e)}"}
            else:
                res = _post("/cotizaciones/iniciar", data)
            if res.get("status") == "success":
                bot.send_message(m.chat.id, "Servicio iniciado exitosamente!", reply_markup=menu)
            else:
                error_msg = res.get("message", "Error desconocido")
                bot.send_message(m.chat.id, f"Error al iniciar: {error_msg}", reply_markup=menu)
        except json.JSONDecodeError:
            bot.send_message(m.chat.id, "JSON invalido", reply_markup=menu)
        except Exception as e:
            bot.send_message(m.chat.id, f"Error: {str(e)}", reply_markup=menu)

def ensure_started(*, start_callback=None, restart_callback=None, stop_callback=None, status_callback=None):
    global _bot, _bot_thread, _started, _callbacks
    if _started:
        print("[telegram] Bot ya iniciado")
        return
    _callbacks["start"] = start_callback
    _callbacks["restart"] = restart_callback
    _callbacks["stop"] = stop_callback
    _callbacks["status"] = status_callback
    if telebot is None:
        print("[telegram] pyTelegramBotAPI no instalado; bot desactivado.")
        _started = True
        return
    if not BOT_TOKEN:
        print("[telegram] TOKEN no configurado, bot desactivado.")
        _started = True
        return
    try:
        _bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
        _bot.delete_webhook()
        _register_handlers(_bot)
        def _run():
            try:
                print("[telegram] Bot iniciado (polling en background)")
                _bot.infinity_polling(skip_pending=True, timeout=10)
            except Exception as e:
                print(f"[telegram] Polling detenido: {e}")
        _bot_thread = threading.Thread(target=_run, daemon=True)
        _bot_thread.start()
        print("[telegram] Bot iniciado (polling en background)")
        _started = True
    except Exception as e:
        print(f"[telegram] Error al crear bot: {e}")
        _started = True

def shutdown():
    global _bot, _bot_thread, _started
    print("[telegram] Shutdown del bot")
    _started = False
    if _bot:
        try:
            _bot.stop_polling()
        except:
            pass
        _bot = None

def notify(text):
    if _bot and ADMIN_CHAT_ID:
        try:
            _bot.send_message(int(ADMIN_CHAT_ID), text)
        except:
            pass
'''

# Escribir el archivo
with open('telegram_control.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Archivo telegram_control.py creado exitosamente")
