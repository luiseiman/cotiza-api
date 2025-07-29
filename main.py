from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from ws_rofex import MarketDataManager, broadcaster

app = FastAPI()
manager = MarketDataManager()  # Control clásico REST

class RequestBody(BaseModel):
    instrumentos: list[str]
    user: str
    password: str
    account: str

@app.post("/cotizaciones/iniciar")
async def iniciar(data: RequestBody):
    if manager.is_running():
        return {"status": "Ya hay una suscripción activa"}
    manager.start(data.instrumentos, data.user, data.password, data.account)
    return {"status": "Suscripción iniciada"}

@app.post("/cotizaciones/parar")
async def parar():
    if manager.is_running():
        manager.stop()
        return {"status": "Suscripción detenida"}
    return {"status": "No hay suscripción activa"}

@app.get("/cotizaciones/estado")
async def estado():
    if manager.is_running():
        return {"estado": "iniciada"}
    return {"estado": "parada"}

# --- Nuevo endpoint websocket ---
@app.websocket("/ws-cotizaciones")
async def ws_cotizaciones(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Opcional: puede recibir pings, ignoramos
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
