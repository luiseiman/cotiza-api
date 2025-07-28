import pyRofex
import threading
import time
import json
from supabase_client import guardar_en_supabase

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
            guardar_en_supabase(message)
            print("Market Data Message Saved:", message)

        def error_handler(message):
            print("Error Message Received:", message)

        def exception_handler(e):
            print("Exception Occurred:", e)

        pyRofex.initialize(
            user=user,
            password=password,
            account=account,
            environment=pyRofex.Environment.LIVE  # Cambia a REMARKET o LIVE si corresponde
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
