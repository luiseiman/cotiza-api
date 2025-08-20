#!/usr/bin/env python3
"""
Script para verificar y limpiar locks del bot de Telegram.
Útil para diagnosticar problemas de múltiples instancias.
Funciona sin dependencias externas (solo librerías estándar).
"""

import os
import sys
import json
import time
import tempfile
import socket
import subprocess
import platform

def check_process_exists(pid):
    """Verifica si un proceso existe usando comandos del sistema"""
    try:
        if platform.system() == "Windows":
            # Windows: usar tasklist
            result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                  capture_output=True, text=True, timeout=5)
            return str(pid) in result.stdout
        else:
            # Linux/Mac: usar ps
            result = subprocess.run(['ps', '-p', str(pid)], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
    except Exception:
        return False

def get_process_info(pid):
    """Obtiene información básica de un proceso"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'], 
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].split(',')[0].strip('"')  # Nombre del proceso
        else:
            result = subprocess.run(['ps', '-p', str(pid), '-o', 'comm='], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
    except Exception:
        pass
    return "N/A"

def check_network_connections(port):
    """Verifica conexiones de red usando comandos del sistema"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['netstat', '-ano'], 
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        return int(parts[-1])  # PID
        else:
            result = subprocess.run(['netstat', '-tlnp'], 
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) >= 7:
                        pid_part = parts[-1].split('/')[0]
                        return int(pid_part) if pid_part.isdigit() else None
    except Exception:
        pass
    return None

def check_telegram_locks():
    """Verifica todos los locks relacionados con Telegram"""
    print("🔍 VERIFICANDO LOCKS DEL BOT DE TELEGRAM")
    print("=" * 50)
    
    # Verificar locks de archivo
    print("\n📁 LOCKS DE ARCHIVO:")
    temp_dir = tempfile.gettempdir()
    telegram_locks = []
    
    for file in os.listdir(temp_dir):
        if file.startswith('telegram_bot_lock_') and file.endswith('.lock'):
            lock_path = os.path.join(temp_dir, file)
            try:
                with open(lock_path, 'r') as f:
                    lock_data = json.loads(f.read())
                    age_hours = round((time.time() - lock_data.get("timestamp", 0)) / 3600, 2)
                    pid = lock_data.get("pid")
                    hostname = lock_data.get("hostname")
                    
                    # Verificar si el proceso existe
                    process_exists = False
                    if pid:
                        process_exists = check_process_exists(pid)
                    
                    telegram_locks.append({
                        "file": file,
                        "pid": pid,
                        "hostname": hostname,
                        "age_hours": age_hours,
                        "process_exists": process_exists,
                        "status": "✅ Activo" if process_exists else "❌ Obsoleto"
                    })
            except Exception as e:
                telegram_locks.append({
                    "file": file,
                    "error": str(e),
                    "status": "⚠️ Error"
                })
    
    if not telegram_locks:
        print("   No se encontraron locks de archivo")
    else:
        for lock in telegram_locks:
            if "error" in lock:
                print(f"   {lock['file']}: {lock['error']} - {lock['status']}")
            else:
                print(f"   {lock['file']}: PID {lock['pid']} ({lock['hostname']}) - {lock['age_hours']}h - {lock['status']}")
    
    # Verificar procesos de Python con telegram (simplificado)
    print("\n🐍 PROCESOS DE PYTHON CON TELEGRAM:")
    telegram_processes = []
    
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], 
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Saltar header
                if 'telegram' in line.lower():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        pid = parts[1].strip('"')
                        if pid.isdigit() and int(pid) != os.getpid():
                            telegram_processes.append({
                                "pid": int(pid),
                                "cmdline": line,
                                "age_hours": "N/A"
                            })
        else:
            result = subprocess.run(['ps', 'aux'], 
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Saltar header
                if 'python' in line and 'telegram' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        if pid.isdigit() and int(pid) != os.getpid():
                            telegram_processes.append({
                                "pid": int(pid),
                                "cmdline": line,
                                "age_hours": "N/A"
                            })
    except Exception as e:
        print(f"   Error verificando procesos: {e}")
    
    if not telegram_processes:
        print("   No se encontraron otros procesos de telegram")
    else:
        for proc in telegram_processes:
            print(f"   PID {proc['pid']}: {proc['cmdline'][:100]}...")
    
    # Verificar puertos en uso
    print("\n🌐 PUERTOS EN USO:")
    lock_port = int(os.getenv("TELEGRAM_LOCK_PORT", "12345"))
    used_pid = check_network_connections(lock_port)
    
    if used_pid is None:
        print(f"   Puerto {lock_port} libre")
    else:
        process_name = get_process_info(used_pid)
        print(f"   Puerto {lock_port}: PID {used_pid} ({process_name})")
    
    return telegram_locks, telegram_processes, [{"port": lock_port, "pid": used_pid}] if used_pid else []

def cleanup_obsolete_locks():
    """Limpia locks obsoletos"""
    print("\n🧹 LIMPIANDO LOCKS OBSOLETOS:")
    print("=" * 30)
    
    temp_dir = tempfile.gettempdir()
    cleaned = []
    
    for file in os.listdir(temp_dir):
        if file.startswith('telegram_bot_lock_') and file.endswith('.lock'):
            lock_path = os.path.join(temp_dir, file)
            try:
                with open(lock_path, 'r') as f:
                    lock_data = json.loads(f.read())
                    old_timestamp = lock_data.get("timestamp", 0)
                    old_pid = lock_data.get("pid")
                    
                    # Si es muy viejo (>1 hora) o el proceso no existe
                    if (time.time() - old_timestamp > 3600 or 
                        (old_pid and not check_process_exists(old_pid))):
                        os.remove(lock_path)
                        cleaned.append(file)
                        print(f"   ✅ Removido: {file}")
            except Exception:
                # Si no se puede leer, remover
                try:
                    os.remove(lock_path)
                    cleaned.append(file)
                    print(f"   ✅ Removido (invalido): {file}")
                except Exception as e:
                    print(f"   ❌ Error removiendo {file}: {e}")
    
    if not cleaned:
        print("   No se encontraron locks obsoletos para limpiar")
    else:
        print(f"\n   Total de locks limpiados: {len(cleaned)}")
    
    return cleaned

def main():
    """Función principal"""
    print("🤖 DIAGNÓSTICO DE LOCKS DEL BOT DE TELEGRAM")
    print("=" * 60)
    print("📋 Usando solo librerías estándar de Python")
    print("=" * 60)
    
    # Verificar locks
    locks, processes, ports = check_telegram_locks()
    
    # Resumen
    print("\n📊 RESUMEN:")
    print("=" * 20)
    print(f"   Locks de archivo: {len(locks)}")
    print(f"   Otros procesos: {len(processes)}")
    print(f"   Puertos ocupados: {len(ports)}")
    
    # Recomendaciones
    print("\n💡 RECOMENDACIONES:")
    if locks:
        obsolete_locks = [l for l in locks if not l.get("process_exists", True)]
        if obsolete_locks:
            print(f"   ⚠️  {len(obsolete_locks)} locks obsoletos detectados")
            print("   💡 Ejecuta: python check_locks.py --cleanup")
        else:
            print("   ✅ Todos los locks están activos")
    
    if processes:
        print(f"   ⚠️  {len(processes)} otros procesos de telegram detectados")
        print("   💡 Verifica si son instancias legítimas")
    
    if ports and ports[0]["pid"]:
        print(f"   ⚠️  Puerto {ports[0]['port']} ocupado")
        print("   💡 Otro bot puede estar ejecutándose")
    
    # Limpiar si se solicita
    if "--cleanup" in sys.argv:
        print("\n" + "=" * 60)
        cleaned = cleanup_obsolete_locks()
        if cleaned:
            print(f"\n✅ Limpieza completada. {len(cleaned)} locks removidos.")
        else:
            print("\n✅ No se requirió limpieza.")

if __name__ == "__main__":
    main()
