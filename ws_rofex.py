import pyRofex
import threading
import time
import json
import asyncio
from supabase_client import guardar_en_supabase

class WebSocketBroadcaster:
    def __init__(self):
        self.active_clients = []
        self.queue = asyncio.Queue()
        self.loop = None
        # Lanzamos el task consumidor apenas se crea el objeto
        asyncio.get_event_loop().create_task(self._consumer())

    async def connect(self, websocket):
        await websocket.accept()
        self.active_clients.append(websocket)
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        print(f"Cliente websocket conectado. Total: {len(self.active_clients)}")

    def disconnect(self, websocket):
        if websocket in self.active_clients:
            self.active_clients.remove(websocket)
            print(f"Cliente websocket desconectado. Total: {len(self.active_clients)}")

    def enqueue(self, message):
        # Convertir a JSON string si es dict
        msg = json.dumps(message) if isinstance(message, dict) else str(message)
        loop = self.loop or asyncio.get_event_loop()
        loop.call_soon_threadsafe(self.queue.put_nowait, msg)

    async def _consumer(self):
        self.loop = asyncio.get_event_loop()
        while True:
            msg = await self.queue.get()
            for ws in self.active_clients[:]:
                try:
                    await ws.send_text(msg)
                except Exception as e:
                    print("Error enviando por websocket:", e)
                    self.disconnect(ws)

# Instancia global de broadcaster
broadcaster = WebSocketBroadcaster()

class MarketDataManager:
    def __init__(self):
        self.thread = None
        self._stop_event = threading.Event()

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, instrumentos, user, password, account):
        if self.is_running():
            print("Ya hay una suscripción corriendo.")
            return
        self._stop_event.clear()
        self.thread = threading.Thread(
            target=self._run,
            args=(instrumentos, user, password, account),
            daemon=True
        )
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        print("Solicitud de detener la suscripción enviada.")

    def _run(self, instrumentos, user, password, account):
        def market_data_handler(message):
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except Exception:
                    print("No se pudo decodificar el mensaje:", message)
                    return
            if not isinstance(message, dict):
                print("🔴 Mensaje no es dict tras decodificar:", type(message))
                return

            #guardar_en_supabase(message)
            broadcaster.enqueue(message)
            print("Market Data Message Saved y enviado a WebSockets:", message)

        def error_handler(message):
            print("Error Message Received:", message)

        def exception_handler(e):
            print("Exception Occurred:", e)

        pyRofex.initialize(
            user=user,
            password=password,
            account=account,
            environment=pyRofex.Environment.LIVE  # Cambiá a REMARKET o LIVE si corresponde
        )
        pyRofex.init_websocket_connection(
            market_data_handler=market_data_handler,
            error_handler=error_handler,
            exception_handler=exception_handler
        )
        entries = [
            pyRofex.MarketDataEntry.BIDS,
            pyRofex.MarketDataEntry.OFFERS,
            pyRofex.MarketDataEntry.LAST
        ]
        pyRofex.market_data_subscription(
            tickers=instrumentos,
            entries=entries
        )
        print("Suscripción iniciada, esperando evento de parada...")
        while not self._stop_event.is_set():
            time.sleep(1)
        print("Deteniendo suscripción y cerrando conexión websocket.")
        pyRofex.close_websocket_connection()
