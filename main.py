from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
import ws_rofex
from ratios_worker import start as start_worker, stop as stop_worker, set_session as set_worker_session
import telegram_control as tg
from pydantic import BaseModel
from typing import List
import threading
import time

app = FastAPI()

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

class IniciarRequest(BaseModel):
    user: str
    password: str
    account: str
    instrumentos: List[str]

def _update_status(**kwargs):
    """Actualiza el estado del servicio de forma thread-safe"""
    global _service_status
    with _status_lock:
        _service_status.update(kwargs)

def _get_status():
    """Obtiene el estado actual del servicio"""
    with _status_lock:
        return _service_status.copy()

@app.on_event("startup")
def _startup():
    print("[main] startup")
    tg.ensure_started(
        start_callback=lambda p: iniciar(p),
        stop_callback=lambda: detener(),
        restart_callback=lambda: reiniciar(),
        status_callback=lambda: estado(),
    )
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