#!/usr/bin/env python3
# Script temporal para crear telegram_control.py con monitoreo automático

content = '''# telegram_control.py - Version final con monitoreo automático
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
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "300"))  # 5 minutos por defecto

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

def _cleanup_lock():
    """Limpia el archivo de lock de forma segura"""
    global _lock_path, _lock_fd
    try:
        if _lock_fd is not None:
            try:
                os.close(_lock_fd)
            except OSError:
                pass
            _lock_fd = None
        
        if _lock_path and os.path.exists(_lock_path):
            try:
                os.remove(_lock_path)
                print(f"[telegram] Lock eliminado: {_lock_path}")
            except OSError:
                pass
            _lock_path = None
    except Exception as e:
        print(f"[telegram] Error limpiando lock: {e}")

def _acquire_lock() -> bool:
    """Adquiere un lock de instancia unica"""
    global _lock_fd, _lock_path
    
    try:
        base = tempfile.gettempdir()
        token_tail = (BOT_TOKEN or "no_token")[-8:]
        _lock_path = os.path.join(base, f"cotiza_telegram_{token_tail}.lock")
        
        # Limpiar locks obsoletos
        if os.path.exists(_lock_path):
            try:
                with open(_lock_path, 'r') as f:
                    old_pid = f.read().strip()
                    try:
                        old_pid_int = int(old_pid)
                        # Verificar si el proceso existe
                        try:
                            import psutil
                            if not psutil.pid_exists(old_pid_int):
                                print(f"[telegram] Limpiando lock obsoleto del PID {old_pid_int}")
                                os.remove(_lock_path)
                            else:
                                print(f"[telegram] Proceso {old_pid_int} aun existe, no puedo adquirir lock")
                                return False
                        except ImportError:
                            # Si no se puede verificar, remover el lock
                            print(f"[telegram] Limpiando lock invalido")
                            os.remove(_lock_path)
                    except ValueError:
                        os.remove(_lock_path)
            except Exception as e:
                print(f"[telegram] Error verificando lock: {e}")
                try:
                    os.remove(_lock_path)
                except:
                    pass
        
        # Crear nuevo lock
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        _lock_fd = os.open(_lock_path, flags)
        os.write(_lock_fd, str(os.getpid()).encode())
        print(f"[telegram] Lock adquirido: {_lock_path}")
        return True
        
    except FileExistsError:
        print(f"[telegram] Otro proceso ya esta pollingeando. No inicio para evitar 409. lock={_lock_path}")
        return False
    except Exception as e:
        print(f"[telegram] No pude crear lock: {e}. Sigo sin bot.")
        return False

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
        kb.row(KeyboardButton("/start"), KeyboardButton("/monitoring"))
        kb.row(KeyboardButton("/help"))
        return kb
    except:
        return None

def _register_handlers(bot):
    if telebot is None:
        return
    menu = _build_menu()
    
    @bot.message_handler(commands=["ping"])
    def _ping(m):
        bot.send_message(m.chat.id, "🏓 Pong - Bot funcionando correctamente", reply_markup=menu)
    
    @bot.message_handler(commands=["help"])
    def _help(m):
        help_text = """🤖 Bot de Control - Comandos disponibles:

• /ping - Verificar que el bot esté funcionando
• /status - Estado del servicio
• /start {json} - Iniciar servicio con credenciales
• /monitoring - Estado del monitoreo automático

🔄 **Monitoreo Automático:**
El bot verifica automáticamente el estado del servicio cada 5 minutos durante el horario activo (10:30 - 17:00) y lo reinicia si está detenido.

Ejemplo: /start {"user":"123","account":"456","password":"***","instrumentos":["MERV - XMEV - TX26 - 24hs"]}"""
        bot.send_message(m.chat.id, help_text, reply_markup=menu)
    
    @bot.message_handler(commands=["status"])
    def _status(m):
        try:
            if callable(_callbacks.get("status")):
                res = _callbacks["status"]()
            else:
                res = _get("/cotizaciones/status")
            
            # Verificar si el servicio está iniciado
            if res.get("started") == True:
                user = res.get("user", "N/A")
                account = res.get("account", "N/A")
                worker_status = res.get("worker_status", "desconocido")
                ws_connected = res.get("ws_connected", False)
                
                status_msg = f"""✅ **Servicio ACTIVO**

👤 Usuario: {user}
🏦 Cuenta: {account}
⚙️ Worker: {worker_status}
🔌 WebSocket: {'✅ Conectado' if ws_connected else '❌ Desconectado'}"""
                
                bot.send_message(m.chat.id, status_msg, reply_markup=menu, parse_mode="HTML")
            else:
                bot.send_message(m.chat.id, "🔴 Servicio detenido", reply_markup=menu)
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Error: {str(e)}", reply_markup=menu)
    
    @bot.message_handler(commands=["monitoring"])
    def _monitoring(m):
        try:
            if _monitoring_active:
                status_msg = f"""🔍 **Monitoreo Automático ACTIVO**

⏰ Horario activo: {ACTIVE_START} - {ACTIVE_END}
🔄 Intervalo de verificación: {MONITORING_INTERVAL} segundos
✅ Estado: Funcionando

El bot verifica automáticamente el estado del servicio cada {MONITORING_INTERVAL} segundos durante el horario activo."""
            else:
                status_msg = "🔴 **Monitoreo Automático INACTIVO**"
            
            bot.send_message(m.chat.id, status_msg, reply_markup=menu, parse_mode="HTML")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Error: {str(e)}", reply_markup=menu)
    
    @bot.message_handler(commands=["start"])
    def _start(m):
        try:
            payload = m.text.partition(" ")[2].strip()
            if not payload:
                bot.send_message(m.chat.id, "🚀 Use: /start {json}", reply_markup=menu)
                return
            data = json.loads(payload)
            bot.send_message(m.chat.id, "🚀 Iniciando servicio...", reply_markup=menu)
            
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
                bot.send_message(m.chat.id, "✅ Servicio iniciado exitosamente!", reply_markup=menu)
            else:
                error_msg = res.get("message", "Error desconocido")
                bot.send_message(m.chat.id, f"❌ Error al iniciar: {error_msg}", reply_markup=menu)
                
        except json.JSONDecodeError:
            bot.send_message(m.chat.id, "❌ JSON invalido", reply_markup=menu)
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Error: {str(e)}", reply_markup=menu)

def _is_active_hours():
    """Verifica si estamos en horario activo"""
    try:
        from datetime import datetime, time
        import pytz
        
        # Obtener zona horaria
        tz_str = os.getenv("TZ", "America/Argentina/Buenos_Aires")
        try:
            tz = pytz.timezone(tz_str)
        except:
            tz = pytz.UTC
        
        now = datetime.now(tz)
        current_time = now.time()
        
        # Parsear horarios
        start_time = time.fromisoformat(ACTIVE_START)
        end_time = time.fromisoformat(ACTIVE_END)
        
        # Verificar si estamos en horario activo
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:  # Horario cruza la medianoche
            return current_time >= start_time or current_time <= end_time
            
    except Exception as e:
        print(f"[telegram] Error verificando horario: {e}")
        return True  # En caso de error, asumir horario activo

def _check_and_restart_service():
    """Verifica el estado del servicio y lo reinicia si es necesario"""
    global _last_restart_attempt
    
    try:
        # Verificar si estamos en horario activo
        if not _is_active_hours():
            print("[telegram] Fuera de horario activo, no verificando servicio")
            return
        
        # Verificar estado del servicio
        res = _get("/cotizaciones/status")
        
        if res.get("started") == True:
            print("[telegram] Servicio funcionando correctamente")
            return
        
        # Servicio detenido, verificar si podemos reiniciarlo
        if _last_restart_attempt:
            from datetime import datetime, timedelta
            time_since_last = datetime.now() - _last_restart_attempt
            if time_since_last < timedelta(minutes=5):  # Esperar 5 minutos entre intentos
                print(f"[telegram] Reinicio reciente ({time_since_last.seconds}s), esperando...")
                return
        
        print("[telegram] Servicio detenido, intentando reiniciar...")
        
        # Obtener ultimos parametros guardados
        last_params = _get("/cotizaciones/last_params")
        
        if last_params and not last_params.get("error"):
            # Reiniciar con ultimos parametros
            restart_res = _post("/cotizaciones/reiniciar")
            
            if restart_res.get("status") == "success":
                _last_restart_attempt = datetime.now()
                print("[telegram] Servicio reiniciado exitosamente")
                
                # Notificar al usuario
                if _bot and ADMIN_CHAT_ID:
                    try:
                        _bot.send_message(int(ADMIN_CHAT_ID), 
                                        "🔄 **Servicio Reiniciado Automáticamente**\n\n"
                                        "✅ El servicio estaba detenido y ha sido reiniciado "
                                        "con los últimos parámetros conocidos.")
                    except:
                        pass
            else:
                print(f"[telegram] Error reiniciando servicio: {restart_res}")
        else:
            print("[telegram] No se pudieron obtener los últimos parámetros")
            
    except Exception as e:
        print(f"[telegram] Error en monitoreo automático: {e}")

def _start_monitoring():
    """Inicia el monitoreo automático del servicio"""
    global _monitoring_thread, _monitoring_active
    
    if _monitoring_active:
        print("[telegram] Monitoreo ya activo")
        return
    
    def _monitoring_loop():
        global _monitoring_active
        _monitoring_active = True
        
        while _monitoring_active:
            try:
                _check_and_restart_service()
                time.sleep(MONITORING_INTERVAL)
            except Exception as e:
                print(f"[telegram] Error en loop de monitoreo: {e}")
                time.sleep(60)  # Esperar 1 minuto en caso de error
    
    _monitoring_thread = threading.Thread(target=_monitoring_loop, daemon=True)
    _monitoring_thread.start()
    print(f"[telegram] Monitoreo automático iniciado (intervalo: {MONITORING_INTERVAL}s)")

def _stop_monitoring():
    """Detiene el monitoreo automático"""
    global _monitoring_active, _monitoring_thread
    
    _monitoring_active = False
    
    if _monitoring_thread and _monitoring_thread.is_alive():
        try:
            _monitoring_thread.join(timeout=5)
            if _monitoring_thread.is_alive():
                print("[telegram] Thread de monitoreo no terminó en 5s")
        except Exception as e:
            print(f"[telegram] Error esperando thread de monitoreo: {e}")
    
    print("[telegram] Monitoreo automático detenido")

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
    
    # Adquirir lock antes de iniciar
    if not _acquire_lock():
        print("[telegram] No se pudo adquirir lock, bot desactivado.")
        _started = True
        return
    
    try:
        _bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
        _bot.delete_webhook(drop_pending_updates=True)
        _register_handlers(_bot)
        
        def _run():
            try:
                print("[telegram] Iniciando polling del bot...")
                _bot.infinity_polling(skip_pending=True, timeout=10, allowed_updates=[])
            except Exception as e:
                print(f"[telegram] Polling detenido: {e}")
            finally:
                _cleanup_lock()
        
        _bot_thread = threading.Thread(target=_run, daemon=True)
        _bot_thread.start()
        print("[telegram] Bot iniciado (polling en background)")
        _started = True
        
        # Iniciar monitoreo automático
        _start_monitoring()
        
        # Registrar limpieza al salir
        atexit.register(shutdown)
        
    except Exception as e:
        print(f"[telegram] Error al crear bot: {e}")
        _cleanup_lock()
        _started = True

def shutdown():
    global _bot, _bot_thread, _started
    print("[telegram] Iniciando shutdown del bot...")
    _started = False
    
    if _bot:
        try:
            print("[telegram] Deteniendo polling del bot...")
            _bot.stop_polling()
        except:
            pass
        finally:
            _bot = None
    
    if _bot_thread and _bot_thread.is_alive():
        try:
            print("[telegram] Esperando finalizacion del thread del bot...")
            _bot_thread.join(timeout=5)
            if _bot_thread.is_alive():
                print("[telegram] Thread del bot no termino en 5s, continuando...")
        except Exception as e:
            print(f"[telegram] Error esperando thread: {e}")
    
    # Detener monitoreo automático
    _stop_monitoring()
    
    _cleanup_lock()
    print("[telegram] Shutdown del bot completado")

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
print(f"📏 Tamaño: {len(content)} bytes")
print("🔄 Incluye sistema de monitoreo automático completo")
