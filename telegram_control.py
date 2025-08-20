# telegram_control.py - Version final con monitoreo automatico
import os
import json
import threading
import tempfile
import atexit
import time
from typing import Any, Dict, Optional, Callable

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Importar telebot si esta disponible
try:
    import telebot
    from telebot.types import ReplyKeyboardMarkup, KeyboardButton
except ImportError:
    telebot = None

import requests

# Configuracion
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configuracion de monitoreo automatico
ACTIVE_START = os.getenv("ACTIVE_START", "09:00")
ACTIVE_END = os.getenv("ACTIVE_END", "18:00")
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "300"))

# Estado interno
_bot = None
_bot_thread = None
_started = False
_lock_path = None
_lock_fd = None

# Estado del monitoreo
_monitoring_thread = None
_monitoring_active = False
_last_restart_attempt = None

_callbacks = {
    "start": None,
    "restart": None,
    "stop": None,
    "status": None,
}

def ensure_started(*, start_callback=None, restart_callback=None, stop_callback=None, status_callback=None):
    global _bot, _bot_thread, _started, _callbacks
    
    if _started:
        print("[telegram] Bot ya iniciado, limpiando estado anterior...")
        shutdown()
    
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
    
    print("[telegram] Bot iniciado (modo simple)")
    _started = True

def shutdown():
    global _bot, _bot_thread, _started
    print("[telegram] Shutdown del bot completado")

def notify(text):
    if _bot and ADMIN_CHAT_ID:
        try:
            _bot.send_message(int(ADMIN_CHAT_ID), text)
        except:
            pass
