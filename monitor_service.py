#!/usr/bin/env python3
"""
Monitor de servicio para detectar cuelgues y reiniciar automáticamente.
"""

import time
import requests
import subprocess
import psutil
import signal
import os
from datetime import datetime
from typing import Optional


class ServiceMonitor:
    def __init__(self, port: int = 8000, check_interval: int = 30, max_restarts: int = 3):
        self.port = port
        self.check_interval = check_interval
        self.max_restarts = max_restarts
        self.restart_count = 0
        self.last_restart = None
        self.main_process: Optional[psutil.Process] = None
        
    def find_main_process(self) -> Optional[psutil.Process]:
        """Encuentra el proceso principal de main.py."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'python' in cmdline and 'main.py' in cmdline and 'uvicorn' not in cmdline:
                    return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def check_service_health(self) -> bool:
        """Verifica la salud del servicio."""
        try:
            # Verificar endpoint básico
            response = requests.get(f"http://localhost:{self.port}/cotizaciones/health", timeout=10)
            if response.status_code != 200:
                return False
            
            # Verificar endpoint detallado
            response = requests.get(f"http://localhost:{self.port}/health/detailed", timeout=10)
            if response.status_code != 200:
                return False
                
            data = response.json()
            
            # Verificar que no haya demasiadas conexiones WebSocket
            ws_connections = data.get('websocket_connections', 0)
            if ws_connections > 100:  # Límite razonable
                print(f"⚠️  Demasiadas conexiones WebSocket: {ws_connections}")
                return False
            
            # Verificar que el worker del dashboard no esté corriendo sin suscriptores
            dashboard_subs = data.get('dashboard_subscribers', 0)
            dashboard_worker = data.get('dashboard_worker_running', False)
            
            if dashboard_worker and dashboard_subs == 0:
                print(f"⚠️  Worker del dashboard corriendo sin suscriptores")
                return False
            
            print(f"✅ Servicio saludable - WS: {ws_connections}, Dashboard subs: {dashboard_subs}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error verificando servicio: {e}")
            return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False
    
    def restart_service(self):
        """Reinicia el servicio."""
        try:
            print("🔄 Reiniciando servicio...")
            
            # Detener proceso actual si existe
            if self.main_process:
                try:
                    print(f"🛑 Deteniendo proceso PID {self.main_process.pid}")
                    self.main_process.terminate()
                    self.main_process.wait(timeout=10)
                except psutil.TimeoutExpired:
                    print("⚠️  Forzando terminación del proceso")
                    self.main_process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                finally:
                    self.main_process = None
            
            # Esperar un momento
            time.sleep(5)
            
            # Iniciar nuevo proceso
            print("🚀 Iniciando nuevo proceso...")
            subprocess.Popen(['python3', 'main.py'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            self.restart_count += 1
            self.last_restart = datetime.now()
            
            # Esperar a que el servicio esté listo
            for i in range(30):  # Esperar máximo 30 segundos
                time.sleep(1)
                if self.check_service_health():
                    print(f"✅ Servicio reiniciado exitosamente (intento {self.restart_count})")
                    return True
            
            print("❌ El servicio no respondió después del reinicio")
            return False
            
        except Exception as e:
            print(f"❌ Error reiniciando servicio: {e}")
            return False
    
    def monitor_loop(self):
        """Loop principal de monitoreo."""
        print(f"🔍 Iniciando monitor del servicio en puerto {self.port}")
        print(f"⏰ Intervalo de verificación: {self.check_interval} segundos")
        print(f"🔄 Máximo reinicios: {self.max_restarts}")
        print("=" * 60)
        
        consecutive_failures = 0
        
        while True:
            try:
                # Encontrar proceso principal
                if not self.main_process:
                    self.main_process = self.find_main_process()
                    if self.main_process:
                        print(f"📋 Proceso encontrado: PID {self.main_process.pid}")
                
                # Verificar salud del servicio
                is_healthy = self.check_service_health()
                
                if is_healthy:
                    consecutive_failures = 0
                    if self.main_process and not self.main_process.is_running():
                        print("⚠️  Proceso principal no está corriendo")
                        self.main_process = None
                else:
                    consecutive_failures += 1
                    print(f"❌ Verificación fallida #{consecutive_failures}")
                    
                    # Si falla 2 veces consecutivas, reiniciar
                    if consecutive_failures >= 2:
                        if self.restart_count < self.max_restarts:
                            if self.restart_service():
                                consecutive_failures = 0
                                self.main_process = self.find_main_process()
                            else:
                                print(f"❌ Reinicio falló. Restantes: {self.max_restarts - self.restart_count}")
                        else:
                            print(f"❌ Máximo de reinicios alcanzado ({self.max_restarts})")
                            print("🛑 Deteniendo monitor")
                            break
                
                # Esperar antes de la siguiente verificación
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n🛑 Monitor detenido por el usuario")
                break
            except Exception as e:
                print(f"❌ Error en loop de monitoreo: {e}")
                time.sleep(30)  # Esperar antes de reintentar


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor de servicio para detectar cuelgues")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servicio")
    parser.add_argument("--interval", type=int, default=30, help="Intervalo de verificación en segundos")
    parser.add_argument("--max-restarts", type=int, default=3, help="Máximo número de reinicios")
    
    args = parser.parse_args()
    
    monitor = ServiceMonitor(
        port=args.port,
        check_interval=args.interval,
        max_restarts=args.max_restarts
    )
    
    monitor.monitor_loop()


if __name__ == "__main__":
    main()

