from fastapi import FastAPI, Body, WebSocket, WebSocketDisconnect, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import ws_rofex
from ratios_worker import start as start_worker, stop as stop_worker, set_session as set_worker_session
import telegram_control as tg
from pydantic import BaseModel
from typing import List
import threading
import time
import os, json
import requests
import asyncio
from typing import Set, Optional
try:
	from dotenv import load_dotenv
	load_dotenv()
except ImportError:
	pass

from supabase_client import get_active_pairs

app = FastAPI(title="Cotiza API", version="1.0.0")

# Configurar CORS para permitir conexiones WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado global del servicio
_service_status = {
    "started": False,
    "started_at": None,
    "user": None,
    "account": None,
    "instruments": [],
    "worker_running": False,
    "ws_connected": False
}
_status_lock = threading.Lock()

# ---------------------------- Order tracing (in-memory) ----------------------------
_order_logs: list[dict] = []
_order_logs_lock = threading.Lock()

def _append_order_log(entry: dict):
    try:
        entry["ts"] = time.time()
        with _order_logs_lock:
            _order_logs.append(entry)
            # Limitar tamaño para no crecer indefinidamente
            if len(_order_logs) > 500:
                del _order_logs[: len(_order_logs) - 500]
    except Exception:
        pass

def _update_status(**kwargs):
    """Actualiza el estado del servicio de forma thread-safe"""
    global _service_status
    with _status_lock:
        _service_status.update(kwargs)

def _get_status():
    """Obtiene el estado actual del servicio"""
    with _status_lock:
        return _service_status.copy()

def _get_env_creds():
	user = os.getenv("ROFEX_USER")
	password = os.getenv("ROFEX_PASSWORD")
	account = os.getenv("ROFEX_ACCOUNT")
	return user, password, account

def _instruments_from_pairs(pairs) -> list[str]:
	syms: Set[str] = set()
	for p in pairs or []:
		b = p.get("base_symbol")
		q = p.get("quote_symbol")
		if isinstance(b, str) and b.strip():
			syms.add(b.strip())
		if isinstance(q, str) and q.strip():
			syms.add(q.strip())
	return sorted(syms)

class IniciarRequest(BaseModel):
    user: str
    password: str
    account: str
    instrumentos: List[str]

class OrderSubscribeRequest(BaseModel):
    account: str

class SendOrderRequest(BaseModel):
    symbol: str
    side: str  # BUY/SELL
    size: float
    price: float | None = None
    order_type: str = "LIMIT"  # LIMIT/MARKET
    tif: str = "DAY"           # DAY/IOC/FOK (si aplica)
    market: str | None = None
    client_order_id: str | None = None  # ID único del cliente para tracking

@app.on_event("startup")
def _startup():
    print("[main] startup")
    # Capturar event loop para envíos desde otros hilos
    try:
        global _event_loop
        _event_loop = asyncio.get_event_loop()
    except Exception:
        _event_loop = None
    # Habilitar el bot de Telegram solo si TELEGRAM_POLLING=1 (por defecto 1 local, 0 en Render)
    if os.getenv("TELEGRAM_POLLING", "1") == "1":
        try:
            import importlib
            import telegram_control as tg_local
            tg_local = importlib.reload(tg_local)
            print(f"[main] telegram_control file: {getattr(tg_local, '__file__', None)}")
            tg_local.ensure_started(
                start_callback=lambda p: iniciar(p),
                stop_callback=lambda: detener(),
                restart_callback=lambda: reiniciar(),
                status_callback=lambda: estado(),
            )
        except Exception as e:
            print(f"[main] error ensure_started: {e}")
    else:
        print("[main] Telegram polling deshabilitado por TELEGRAM_POLLING!=1")
    # No iniciar worker automáticamente, solo cuando se solicite
    print("[main] Servicio listo. Use /start para iniciar.")

@app.on_event("shutdown")
def _shutdown():
    print("[main] shutdown")
    stop_worker()
    ws_rofex.manager.stop()

@app.post("/cotizaciones/iniciar")
def iniciar(req: IniciarRequest):
    try:
        # Iniciar WebSocket Rofex
        ws_result = ws_rofex.manager.start(
            user=req.user,
            password=req.password,
            account=req.account,
            instrumentos=req.instrumentos,
            force_ws=True
        )
        
        if ws_result.get("status") == "started":
            # Iniciar worker solo si WebSocket se conectó exitosamente
            start_worker()
            set_worker_session(user_id=req.user)
            
            # Actualizar estado del servicio
            _update_status(
                started=True,
                started_at=time.time(),
                user=req.user,
                account=req.account,
                instruments=req.instrumentos,
                worker_running=True,
                ws_connected=True
            )
            
            print(f"[main] Servicio iniciado para usuario {req.user}")
            return {"status": "success", "message": "Servicio iniciado", "details": ws_result}
        else:
            return {"status": "error", "message": "No se pudo iniciar WebSocket", "details": ws_result}
            
    except Exception as e:
        print(f"[main] Error al iniciar: {e}")
        return {"status": "error", "message": f"Error al iniciar: {str(e)}"}

@app.post("/cotizaciones/detener")
def detener():
    try:
        # Detener worker
        stop_worker()
        
        # Detener WebSocket
        ws_result = ws_rofex.manager.stop()
        
        # Actualizar estado del servicio
        _update_status(
            started=False,
            started_at=None,
            user=None,
            account=None,
            instruments=[],
            worker_running=False,
            ws_connected=False
        )
        
        print("[main] Servicio detenido")
        return {"status": "success", "message": "Servicio detenido", "details": ws_result}
        
    except Exception as e:
        print(f"[main] Error al detener: {e}")
        return {"status": "error", "message": f"Error al detener: {str(e)}"}

@app.post("/cotizaciones/reiniciar")
def reiniciar():
    try:
        # Detener primero
        detener()
        
        # Esperar un momento
        time.sleep(2)
        
        # Usar los últimos parámetros guardados
        from params_store import get_last_params
        last_params = get_last_params()
        
        if last_params:
            try:
                # Crear request con los parámetros guardados
                req = IniciarRequest(**last_params)
                return iniciar(req)
            except Exception as e:
                return {"status": "error", "message": f"Error al reiniciar: {str(e)}"}
        else:
            return {"status": "error", "message": "No hay parámetros previos para reiniciar"}
            
    except Exception as e:
        print(f"[main] Error al reiniciar: {e}")
        return {"status": "error", "message": f"Error al reiniciar: {str(e)}"}

@app.post("/cotizaciones/orders/subscribe")
def orders_subscribe(req: OrderSubscribeRequest):
    try:
        _append_order_log({"endpoint": "subscribe", "request": req.model_dump()})
        res = ws_rofex.manager.subscribe_order_reports(account=req.account)
        _append_order_log({"endpoint": "subscribe", "response": res})
        return res
    except Exception as e:
        _append_order_log({"endpoint": "subscribe", "error": str(e)})
        return {"status": "error", "message": str(e)}

@app.post("/cotizaciones/orders/send")
def orders_send(req: SendOrderRequest):
    try:
        _append_order_log({"endpoint": "send", "request": req.model_dump()})
        res = ws_rofex.manager.send_order(
            symbol=req.symbol,
            side=req.side,
            size=req.size,
            price=req.price,
            order_type=req.order_type,
            tif=req.tif,
            market=req.market,
            client_order_id=req.client_order_id,
        )
        _append_order_log({"endpoint": "send", "response": res})
        return res
    except Exception as e:
        _append_order_log({"endpoint": "send", "error": str(e)})
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/orders/last_report")
def orders_last_report():
    try:
        rep = ws_rofex.manager.last_order_report()
        res = {"status": "ok", "report": rep}
        _append_order_log({"endpoint": "last_report", "response": res})
        return res
    except Exception as e:
        _append_order_log({"endpoint": "last_report", "error": str(e)})
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/orders/logs")
def orders_logs(limit: int = 100):
    try:
        with _order_logs_lock:
            data = _order_logs[-limit:]
        return {"status": "ok", "count": len(data), "logs": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/status")
def estado():
    try:
        # Obtener estado del WebSocket
        ws_status = ws_rofex.manager.status()
        
        # Obtener estado del worker
        from ratios_worker import _worker_thread
        worker_status = "running" if _worker_thread and _worker_thread.is_alive() else "stopped"
        
        # Combinar estados
        status = _get_status()
        status.update({
            "worker_status": worker_status,
            "ws_details": ws_status,
            "uptime": time.time() - status["started_at"] if status["started_at"] else None
        })
        
        # Devolver diccionario simple para el bot de Telegram
        return status
        
    except Exception as e:
        print(f"[main] Error al obtener estado: {e}")
        return {"status": "error", "message": f"Error al obtener estado: {str(e)}"}

@app.get("/cotizaciones/health")
def health():
    """Endpoint de salud simple para verificar que la API está funcionando"""
    return {"status": "healthy", "timestamp": time.time()}


# WebSocket connections
_websocket_connections = []
_websocket_lock = threading.Lock()
_event_loop: Optional[asyncio.AbstractEventLoop] = None

@app.websocket("/ws/cotizaciones")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para cotizaciones en tiempo real"""
    try:
        # Aceptar la conexión
        await websocket.accept()
        print(f"[websocket] Nueva conexión desde {websocket.client.host}:{websocket.client.port}")
        
        # Agregar a la lista de conexiones activas
        with _websocket_lock:
            _websocket_connections.append(websocket)
        
        # Enviar mensaje de bienvenida
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": "connected",
            "timestamp": time.time(),
            "message": "Conexión WebSocket establecida"
        }))
        
        # Mantener la conexión activa y escuchar mensajes
        try:
            while True:
                # Esperar mensajes del cliente
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    print(f"[websocket] Mensaje recibido: {message}")
                    
                    # Procesar mensaje según el tipo
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": time.time()
                        }))
                    elif message.get("type") == "subscribe":
                        # Suscribir a cotizaciones específicas
                        await websocket.send_text(json.dumps({
                            "type": "subscribed",
                            "instruments": message.get("instruments", []),
                            "timestamp": time.time()
                        }))
                    elif message.get("type") == "orders_subscribe":
                        # Suscribir a order reports de una cuenta
                        account = message.get("account")
                        if not account:
                            await websocket.send_text(json.dumps({
                                "type": "error", "message": "missing account"
                            }))
                        else:
                            res = ws_rofex.manager.subscribe_order_reports(account=account)
                            await websocket.send_text(json.dumps({
                                "type": "orders_subscribed", "account": account, "result": res
                            }))
                    elif message.get("type") == "send_order":
                        # Envío de orden directa
                        payload = message.get("order") or {}
                        client_order_id = message.get("clOrdId") or payload.get("client_order_id")
                        try:
                            res = ws_rofex.manager.send_order(
                                symbol=payload.get("symbol"),
                                side=payload.get("side"),
                                size=payload.get("size"),
                                price=payload.get("price"),
                                order_type=payload.get("order_type", "LIMIT"),
                                tif=payload.get("tif", "DAY"),
                                market=payload.get("market"),
                                client_order_id=client_order_id,
                            )
                            await websocket.send_text(json.dumps({
                                "type": "order_ack",
                                "request": payload,
                                "result": res
                            }))
                        except Exception as e:
                            await websocket.send_text(json.dumps({
                                "type": "error", "message": f"send_order failed: {str(e)}"
                            }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Tipo de mensaje no reconocido",
                            "timestamp": time.time()
                        }))
                        
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "JSON inválido",
                        "timestamp": time.time()
                    }))
                    
        except WebSocketDisconnect:
            print(f"[websocket] Cliente desconectado: {websocket.client.host}:{websocket.client.port}")
        except Exception as e:
            print(f"[websocket] Error en WebSocket: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error interno: {str(e)}",
                "timestamp": time.time()
            }))
            
    except Exception as e:
        print(f"[websocket] Error al aceptar conexión: {e}")
    finally:
        # Remover de la lista de conexiones activas
        with _websocket_lock:
            if websocket in _websocket_connections:
                _websocket_connections.remove(websocket)
        print(f"[websocket] Conexión cerrada: {websocket.client.host}:{websocket.client.port}")


def broadcast_to_websockets(message: dict):
    """Envía un mensaje a todos los clientes WebSocket conectados"""
    disconnected = []
    
    with _websocket_lock:
        for websocket in _websocket_connections:
            try:
                # Verificar si la conexión sigue activa
                if websocket.client_state.value == 1:  # WebSocketState.CONNECTED
                    try:
                        # Enviar desde cualquier hilo usando el loop principal
                        if _event_loop is not None:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send_text(json.dumps(message)), _event_loop
                            )
                        else:
                            # Fallback si no hay loop registrado
                            asyncio.create_task(websocket.send_text(json.dumps(message)))
                    except Exception as e:
                        print(f"[websocket] Error programando envío: {e}")
                        disconnected.append(websocket)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                print(f"[websocket] Error enviando mensaje: {e}")
                disconnected.append(websocket)
    
    # Limpiar conexiones desconectadas
    if disconnected:
        with _websocket_lock:
            for ws in disconnected:
                if ws in _websocket_connections:
                    _websocket_connections.remove(ws)
        print(f"[websocket] {len(disconnected)} conexiones desconectadas removidas")

# Registrar callback para difundir ticks provenientes de ws_rofex
def _tick_broadcast_callback(tick: dict):
    try:
        # Enviar a todos los clientes conectados
        broadcast_to_websockets(tick)
    except Exception as e:
        print(f"[websocket] error enviando tick: {e}")

try:
    ws_rofex.set_broadcast_callback(_tick_broadcast_callback)
except Exception as e:
    print(f"[main] No se pudo registrar broadcast_callback: {e}")


@app.get("/cotizaciones/websocket_status")
def websocket_status():
    """Obtiene el estado de las conexiones WebSocket"""
    with _websocket_lock:
        active_connections = len(_websocket_connections)
        connections_info = []
        
        for ws in _websocket_connections:
            try:
                connections_info.append({
                    "host": ws.client.host,
                    "port": ws.client.port,
                    "state": ws.client_state.value
                })
            except Exception:
                pass
    
    return {
        "active_connections": active_connections,
        "connections": connections_info,
        "timestamp": time.time()
    }

@app.get("/cotizaciones/telegram_diag")
def telegram_diag():
    try:
        import importlib
        import telegram_control as tg
        try:
            tg = importlib.reload(tg)
        except Exception:
            pass
        # evitar depender de atributos nuevos si el modulo no esta actualizado en runtime
        info = {
            "has_library": getattr(tg, "telebot", None) is not None,
            "has_token": bool(getattr(tg, "BOT_TOKEN", None)),
        }
        info["module_file"] = getattr(tg, "__file__", None)
        try:
            info.update(getattr(tg, "current_status")())
        except Exception:
            pass
        try:
            info["me"] = getattr(tg, "get_me")()
        except Exception:
            pass
        return info
    except Exception as e:
        return {"error": str(e)}

@app.post("/cotizaciones/telegram_restart")
def telegram_restart():
    try:
        import telegram_control as tg
        try:
            tg.shutdown()
        except Exception:
            pass
        tg.ensure_started(
            start_callback=lambda p: iniciar(p),
            stop_callback=lambda: detener(),
            restart_callback=lambda: reiniciar(),
            status_callback=lambda: estado(),
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/cotizaciones/telegram_sync_commands")
def telegram_sync_commands():
    try:
        import importlib
        import telegram_control as tg
        try:
            tg = importlib.reload(tg)
        except Exception:
            pass
        # Intento 1: usar la función del módulo si existe
        if hasattr(tg, "sync_commands"):
            return tg.sync_commands()
        # Intento 2: fallback directo a la API de Telegram
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            return {"status": "error", "message": "Falta TELEGRAM_TOKEN"}
        url = f"https://api.telegram.org/bot{token}/setMyCommands"
        commands = [
            {"command": "ping", "description": "Comprobar que estoy vivo"},
            {"command": "status", "description": "Ver estado del servicio"},
            {"command": "start", "description": "Iniciar servicio {json}"},
            {"command": "stop", "description": "Detener servicio"},
            {"command": "restart", "description": "Reiniciar servicio"},
            {"command": "help", "description": "Ayuda"}
        ]
        r = requests.post(url, json={"commands": commands})
        ok = r.status_code == 200 and r.json().get("ok") is True
        return {"status": "ok" if ok else "error", "http": r.status_code, "resp": r.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/cotizaciones/telegram_locks_status")
def telegram_locks_status():
    """Verifica el estado de todos los locks del bot"""
    try:
        import telegram_control as tg
        if hasattr(tg, "current_status"):
            return tg.current_status()
        else:
            return {"status": "error", "message": "Función no disponible"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/cotizaciones/telegram_check_other_bots")
def telegram_check_other_bots():
    """Verifica si hay otros bots ejecutándose en el sistema"""
    try:
        import telegram_control as tg
        if hasattr(tg, "check_other_bots"):
            return tg.check_other_bots()
        else:
            return {"status": "error", "message": "Función no disponible"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/cotizaciones/telegram_force_cleanup")
def telegram_force_cleanup():
    """Fuerza la limpieza de todos los locks obsoletos"""
    try:
        import telegram_control as tg
        if hasattr(tg, "force_cleanup_locks"):
            return tg.force_cleanup_locks()
        else:
            return {"status": "error", "message": "Función no disponible"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/cotizaciones/telegram_send_test")
def telegram_send_test(msg: str = "test desde API"):
    try:
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return {"status": "error", "message": "Faltan TELEGRAM_TOKEN/TELEGRAM_CHAT_ID"}
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": int(chat_id), "text": msg})
        ok = r.status_code == 200 and r.json().get("ok") is True
        return {"status": "ok" if ok else "error", "http": r.status_code, "resp": r.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/cotizaciones/last_params")
def last_params():
	try:
		from params_store import get_last_params
		return get_last_params() or {}
	except Exception as e:
		return {"error": str(e)}

@app.post("/cotizaciones/iniciar_auto")
def iniciar_auto():
	try:
		user, password, account = _get_env_creds()
		if not all([user, password, account]):
			return {"status": "error", "message": "Faltan ROFEX_USER/ROFEX_PASSWORD/ROFEX_ACCOUNT en .env"}

		pairs = get_active_pairs()
		instrumentos = _instruments_from_pairs(pairs)

		# Fallback: si DB devuelve 0, usar INSTRUMENTS_JSON del .env (si está)
		if not instrumentos:
			try:
				instrumentos = json.loads(os.getenv("INSTRUMENTS_JSON", "[]"))
			except Exception:
				instrumentos = []

		if not instrumentos:
			return {"status": "error", "message": "No hay instrumentos (DB y .env vacíos)"}

		req = IniciarRequest(user=user, password=password, account=account, instrumentos=instrumentos)
		return iniciar(req)
	except Exception as e:
		return {"status": "error", "message": f"Error en iniciar_auto: {str(e)}"}