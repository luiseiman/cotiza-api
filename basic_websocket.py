#!/usr/bin/env python3
"""
WebSocket básico para dashboard - versión mínima que funciona.
"""

import json
import time
from fastapi import WebSocket, WebSocketDisconnect
from supabase_client import supabase


async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket básico."""
    await websocket.accept()
    
    try:
        # Enviar mensaje de bienvenida
        welcome = {
            "type": "connection",
            "status": "connected",
            "timestamp": time.time(),
            "message": "WebSocket conectado"
        }
        await websocket.send_text(json.dumps(welcome))
        
        while True:
            # Recibir mensaje del cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("action") == "ping":
                    pong = {"action": "pong", "timestamp": time.time()}
                    await websocket.send_text(json.dumps(pong))
                    
                elif message.get("action") == "get_data":
                    # Obtener datos del dashboard
                    try:
                        response = supabase.table("ratios_dashboard_view").select("*").execute()
                        
                        if response.data:
                            result = {
                                "status": "success",
                                "data": response.data,
                                "count": len(response.data),
                                "timestamp": time.time()
                            }
                        else:
                            result = {
                                "status": "error",
                                "error": "No data available",
                                "timestamp": time.time()
                            }
                            
                        await websocket.send_text(json.dumps(result))
                        
                    except Exception as e:
                        error = {
                            "status": "error",
                            "error": str(e),
                            "timestamp": time.time()
                        }
                        await websocket.send_text(json.dumps(error))
                        
                else:
                    error = {
                        "type": "error",
                        "message": "Acción no reconocida",
                        "timestamp": time.time()
                    }
                    await websocket.send_text(json.dumps(error))
                    
            except json.JSONDecodeError:
                error = {
                    "type": "error",
                    "message": "JSON inválido",
                    "timestamp": time.time()
                }
                await websocket.send_text(json.dumps(error))
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error: {e}")
