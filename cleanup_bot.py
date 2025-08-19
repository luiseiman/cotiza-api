#!/usr/bin/env python3
"""
Script para limpiar manualmente todos los locks y procesos del bot de Telegram.
Útil cuando el bot se cuelga o hay conflictos de instancias.
"""

import os
import tempfile
import glob
import subprocess
import sys

def cleanup_locks():
    """Limpia todos los archivos de lock del bot"""
    try:
        base = tempfile.gettempdir()
        print(f"🔍 Buscando locks en: {base}")
        
        # Buscar todos los locks del bot
        lock_pattern = "cotiza_telegram_*.lock"
        lock_files = glob.glob(os.path.join(base, lock_pattern))
        
        if not lock_files:
            print("✅ No se encontraron archivos de lock")
            return
        
        print(f"📁 Encontrados {len(lock_files)} archivos de lock:")
        
        for lock_file in lock_files:
            try:
                # Leer PID del lock
                with open(lock_file, 'r') as f:
                    pid = f.read().strip()
                
                print(f"   📄 {os.path.basename(lock_file)} (PID: {pid})")
                
                # Verificar si el proceso existe
                try:
                    import psutil
                    if psutil.pid_exists(int(pid)):
                        print(f"      ⚠️  Proceso {pid} aún existe")
                    else:
                        print(f"      ✅ Proceso {pid} no existe (obsoleto)")
                except ImportError:
                    print(f"      ❓ No se puede verificar proceso {pid} (psutil no disponible)")
                
                # Eliminar lock
                os.remove(lock_file)
                print(f"      🗑️  Lock eliminado")
                
            except Exception as e:
                print(f"      ❌ Error procesando {lock_file}: {e}")
        
        print("✅ Limpieza de locks completada")
        
    except Exception as e:
        print(f"❌ Error en limpieza de locks: {e}")

def cleanup_processes():
    """Limpia procesos de Python/uvicorn relacionados"""
    try:
        print("🔍 Buscando procesos relacionados...")
        
        # Buscar procesos de Python
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                python_processes = [line for line in lines if 'python.exe' in line]
                
                if python_processes:
                    print(f"🐍 Encontrados {len(python_processes)} procesos de Python:")
                    for proc in python_processes:
                        print(f"   {proc}")
                else:
                    print("✅ No se encontraron procesos de Python")
            else:
                print("❌ No se pudo verificar procesos de Python")
        except Exception as e:
            print(f"❌ Error verificando procesos: {e}")
        
        # Buscar procesos de uvicorn
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq uvicorn.exe'], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                uvicorn_processes = [line for line in lines if 'uvicorn.exe' in line]
                
                if uvicorn_processes:
                    print(f"🚀 Encontrados {len(uvicorn_processes)} procesos de uvicorn:")
                    for proc in uvicorn_processes:
                        print(f"   {proc}")
                else:
                    print("✅ No se encontraron procesos de uvicorn")
            else:
                print("❌ No se pudo verificar procesos de uvicorn")
        except Exception as e:
            print(f"❌ Error verificando uvicorn: {e}")
            
    except Exception as e:
        print(f"❌ Error en limpieza de procesos: {e}")

def force_kill_processes():
    """Fuerza la terminación de procesos relacionados"""
    try:
        print("🔄 Forzando terminación de procesos...")
        
        # Terminar procesos de Python
        try:
            result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print("✅ Procesos de Python terminados")
            else:
                print("ℹ️  No se encontraron procesos de Python para terminar")
        except Exception as e:
            print(f"❌ Error terminando Python: {e}")
        
        # Terminar procesos de uvicorn
        try:
            result = subprocess.run(['taskkill', '/F', '/IM', 'uvicorn.exe'], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print("✅ Procesos de uvicorn terminados")
            else:
                print("ℹ️  No se encontraron procesos de uvicorn para terminar")
        except Exception as e:
            print(f"❌ Error terminando uvicorn: {e}")
            
    except Exception as e:
        print(f"❌ Error forzando terminación: {e}")

def main():
    """Función principal"""
    print("🧹 LIMPIEZA DEL BOT DE TELEGRAM")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("⚠️  MODO FORZADO: Se terminarán todos los procesos")
        cleanup_locks()
        cleanup_processes()
        force_kill_processes()
    else:
        print("📋 MODO NORMAL: Solo limpieza de locks")
        cleanup_locks()
        cleanup_processes()
        print("\n💡 Para forzar terminación de procesos, ejecuta:")
        print("   python cleanup_bot.py --force")
    
    print("\n✅ Limpieza completada")
    print("💡 Ahora puedes reiniciar la API sin conflictos")

if __name__ == "__main__":
    main()
