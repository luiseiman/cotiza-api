#!/usr/bin/env python3
"""
WebSocket simple para dashboard de ratios.
Versión simplificada que no causa problemas al iniciar el servidor.
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
from supabase_client import supabase


class SimpleWebSocketManager:
    """Manager simple para conexiones WebSocket del dashboard."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        """Acepta una nueva conexión WebSocket."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Cliente conectado. Total: {len(self.active_connections)}")
        
        # Enviar mensaje de bienvenida
        welcome_msg = {
            "type": "connection",
            "status": "connected",
            "timestamp": time.time(),
            "message": "Conexión WebSocket establecida"
        }
        await websocket.send_text(json.dumps(welcome_msg))
    
    def disconnect(self, websocket: WebSocket):
        """Desconecta un cliente WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] Cliente desconectado. Total: {len(self.active_connections)}")
    
    async def send_dashboard_data(self):
        """Envía datos del dashboard a todos los clientes conectados."""
        if not self.active_connections:
            return
            
        try:
            # Obtener datos de la vista materializada
            start_time = time.time()
            response = supabase.table("ratios_dashboard_view").select("*").execute()
            elapsed = (time.time() - start_time) * 1000
            
            if response.data:
                data_package = {
                    "status": "success",
                    "data": response.data,
                    "count": len(response.data),
                    "query_time_ms": round(elapsed, 2),
                    "method": "materialized_view_websocket",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Enviar a todos los clientes
                message = json.dumps(data_package)
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
                    
                print(f"[WS] Datos enviados a {len(self.active_connections)} clientes")
            else:
                error_package = {
                    "status": "error",
                    "error": "No data available",
                    "timestamp": datetime.now().isoformat()
                }
                await self._broadcast_to_all(json.dumps(error_package))
                
        except Exception as e:
            error_package = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._broadcast_to_all(json.dumps(error_package))
            print(f"[WS] Error obteniendo datos: {e}")
    
    async def _broadcast_to_all(self, message: str):
        """Envía mensaje a todos los clientes conectados."""
        disconnected_clients = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                disconnected_clients.append(connection)
        
        # Limpiar conexiones desconectadas
        for connection in disconnected_clients:
            self.disconnect(connection)


# Instancia global
websocket_manager = SimpleWebSocketManager()


async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket simple para el dashboard."""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Recibir mensajes del cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("action") == "ping":
                    pong_msg = {
                        "action": "pong",
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(pong_msg))
                    
                elif message.get("action") == "get_status":
                    status_msg = {
                        "active_connections": len(websocket_manager.active_connections),
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(status_msg))
                    
                elif message.get("action") == "get_data":
                    # Enviar datos inmediatamente
                    await websocket_manager.send_dashboard_data()
                    
                else:
                    error_msg = {
                        "type": "error",
                        "message": "Tipo de mensaje no reconocido",
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(error_msg))
                    
            except json.JSONDecodeError:
                error_msg = {
                    "type": "error",
                    "message": "JSON inválido",
                    "timestamp": time.time()
                }
                await websocket.send_text(json.dumps(error_msg))
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Error en conexión: {e}")
        websocket_manager.disconnect(websocket)


# Función para enviar datos periódicamente
async def send_periodic_data():
    """Envía datos cada 10 segundos."""
    while True:
        await websocket_manager.send_dashboard_data()
        await asyncio.sleep(10)


def start_periodic_data_task():
    """Inicia la tarea de envío periódico de datos."""
    try:
        def run_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_periodic_data())
        
        import threading
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        print("[WS] Tarea de datos periódicos iniciada")
    except Exception as e:
        print(f"[WS] Error iniciando tarea periódica: {e}")
