#!/usr/bin/env python3
"""
WebSocket para dashboard de ratios en tiempo real.
Envía datos actualizados cada 10 segundos desde la vista materializada.
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
from supabase_client import supabase
import threading
from contextlib import asynccontextmanager


class DashboardWebSocketManager:
    """Manager para conexiones WebSocket del dashboard."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.refresh_interval = 10  # segundos
        self.is_refreshing = False
        self.last_data = None
        self.last_refresh = None
        
    async def connect(self, websocket: WebSocket):
        """Acepta una nueva conexión WebSocket."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Cliente conectado. Total conexiones: {len(self.active_connections)}")
        
        # Enviar datos actuales inmediatamente si están disponibles
        if self.last_data:
            await websocket.send_text(json.dumps(self.last_data))
    
    def disconnect(self, websocket: WebSocket):
        """Desconecta un cliente WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Cliente desconectado. Total conexiones: {len(self.active_connections)}")
    
    async def refresh_and_broadcast(self):
        """Refresca los datos y los envía a todos los clientes conectados."""
        if self.is_refreshing:
            return  # Evitar refrescos concurrentes
            
        self.is_refreshing = True
        
        try:
            # 1. Refrescar vista materializada
            await self._refresh_materialized_view()
            
            # 2. Obtener datos actualizados
            start_time = time.time()
            response = supabase.table("ratios_dashboard_view").select("*").execute()
            elapsed = (time.time() - start_time) * 1000
            
            if response.data:
                # Preparar datos para envío
                data_package = {
                    "status": "success",
                    "data": response.data,
                    "count": len(response.data),
                    "query_time_ms": round(elapsed, 2),
                    "method": "materialized_view_websocket",
                    "freshness": "~10 seconds",
                    "timestamp": datetime.now().isoformat(),
                    "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None
                }
                
                # Guardar datos para nuevas conexiones
                self.last_data = data_package
                
                # Enviar a todos los clientes conectados
                await self._broadcast_to_all(data_package)
                
                print(f"[WS] Datos actualizados enviados a {len(self.active_connections)} clientes")
                
            else:
                error_package = {
                    "status": "error",
                    "error": "No data available",
                    "timestamp": datetime.now().isoformat()
                }
                await self._broadcast_to_all(error_package)
                
        except Exception as e:
            error_package = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._broadcast_to_all(error_package)
            print(f"[WS] Error al actualizar datos: {e}")
            
        finally:
            self.is_refreshing = False
    
    async def _refresh_materialized_view(self):
        """Refresca la vista materializada."""
        try:
            # Intentar usar función RPC si existe
            supabase.rpc("refresh_ratios_view").execute()
            self.last_refresh = datetime.now()
            print(f"[WS] Vista materializada refrescada a las {self.last_refresh.strftime('%H:%M:%S')}")
        except Exception as e:
            # Si no existe la función RPC, usar SQL directo
            try:
                supabase.rpc("exec_sql", {"sql": "REFRESH MATERIALIZED VIEW CONCURRENTLY ratios_dashboard_view"}).execute()
                self.last_refresh = datetime.now()
                print(f"[WS] Vista materializada refrescada (SQL directo) a las {self.last_refresh.strftime('%H:%M:%S')}")
            except Exception as e2:
                print(f"[WS] Error al refrescar vista materializada: {e2}")
                # Continuar sin refrescar si no es posible
    
    async def _broadcast_to_all(self, data: Dict[str, Any]):
        """Envía datos a todos los clientes conectados."""
        if not self.active_connections:
            return
            
        message = json.dumps(data)
        disconnected_clients = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"[WS] Error enviando a cliente: {e}")
                disconnected_clients.append(connection)
        
        # Limpiar conexiones desconectadas
        for connection in disconnected_clients:
            self.disconnect(connection)
    
    async def start_refresh_loop(self):
        """Loop principal que refresca datos cada 10 segundos."""
        print(f"[WS] Iniciando loop de refresh cada {self.refresh_interval} segundos")
        
        while True:
            try:
                await self.refresh_and_broadcast()
            except Exception as e:
                print(f"[WS] Error en loop de refresh: {e}")
            
            await asyncio.sleep(self.refresh_interval)


# Instancia global del manager
websocket_manager = DashboardWebSocketManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para el dashboard.
    
    Los clientes se conectan y reciben datos cada 10 segundos.
    """
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Mantener la conexión viva
            data = await websocket.receive_text()
            
            # Procesar comandos del cliente si es necesario
            try:
                command = json.loads(data)
                if command.get("action") == "ping":
                    await websocket.send_text(json.dumps({"action": "pong", "timestamp": datetime.now().isoformat()}))
                elif command.get("action") == "get_status":
                    status = {
                        "active_connections": len(websocket_manager.active_connections),
                        "last_refresh": websocket_manager.last_refresh.isoformat() if websocket_manager.last_refresh else None,
                        "is_refreshing": websocket_manager.is_refreshing,
                        "refresh_interval": websocket_manager.refresh_interval
                    }
                    await websocket.send_text(json.dumps(status))
            except json.JSONDecodeError:
                # Ignorar mensajes que no sean JSON válido
                pass
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Error en conexión: {e}")
        websocket_manager.disconnect(websocket)


def start_websocket_refresh_task():
    """Inicia la tarea de refresh en background."""
    async def refresh_task():
        await websocket_manager.start_refresh_loop()
    
    # Crear tarea en el event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(refresh_task())
    
    # Ejecutar en thread separado
    def run_loop():
        loop.run_forever()
    
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    print("[WS] Tarea de refresh iniciada en background")


# =====================================================================
# EJEMPLO DE USO EN main.py
# =====================================================================

"""
# En tu main.py, agregar:

from fastapi import FastAPI
from dashboard_websocket import websocket_endpoint, start_websocket_refresh_task

app = FastAPI()

@app.websocket("/ws/dashboard")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)

@app.on_event("startup")
async def startup():
    # Iniciar la tarea de refresh en background
    start_websocket_refresh_task()

# Luego los clientes pueden conectarse a:
# ws://localhost:8000/ws/dashboard

# Ejemplo de cliente JavaScript:
const ws = new WebSocket('ws://localhost:8000/ws/dashboard');
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Datos del dashboard:', data);
};

# Comandos disponibles:
ws.send(JSON.stringify({action: "ping"}));     // Ping/Pong
ws.send(JSON.stringify({action: "get_status"})); // Estado del servidor
"""


# =====================================================================
# CLIENTE DE PRUEBA
# =====================================================================

async def test_websocket_client():
    """Cliente de prueba para el WebSocket."""
    import websockets
    
    uri = "ws://localhost:8000/ws/dashboard"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[CLIENTE] Conectado al WebSocket")
            
            # Enviar ping
            await websocket.send(json.dumps({"action": "ping"}))
            response = await websocket.recv()
            print(f"[CLIENTE] Ping response: {response}")
            
            # Recibir datos por 30 segundos
            for i in range(3):  # 3 actualizaciones (30 segundos)
                print(f"[CLIENTE] Esperando actualización {i+1}...")
                data = await websocket.recv()
                parsed_data = json.loads(data)
                
                if parsed_data.get("status") == "success":
                    print(f"[CLIENTE] Recibidos {parsed_data.get('count', 0)} registros")
                    print(f"[CLIENTE] Query time: {parsed_data.get('query_time_ms', 0)}ms")
                else:
                    print(f"[CLIENTE] Error: {parsed_data.get('error', 'Unknown error')}")
                
                # Solicitar estado
                await websocket.send(json.dumps({"action": "get_status"}))
                status = await websocket.recv()
                print(f"[CLIENTE] Estado: {status}")
                
    except Exception as e:
        print(f"[CLIENTE] Error: {e}")


if __name__ == "__main__":
    # Ejecutar cliente de prueba
    asyncio.run(test_websocket_client())
