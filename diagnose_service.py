#!/usr/bin/env python3
"""
Diagnóstico completo del servicio para detectar problemas de estabilidad.
"""

import time
import requests
import subprocess
import psutil
import threading
import json
from datetime import datetime
from typing import Dict, List, Any


def check_port_usage(port: int) -> Dict[str, Any]:
    """Verifica qué proceso está usando el puerto."""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    return {
                        "port": port,
                        "in_use": True,
                        "pid": conn.pid,
                        "process_name": proc.name(),
                        "cmdline": ' '.join(proc.cmdline()),
                        "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 2),
                        "cpu_percent": proc.cpu_percent()
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return {"port": port, "in_use": True, "pid": conn.pid, "error": "Access denied"}
        return {"port": port, "in_use": False}
    except Exception as e:
        return {"port": port, "error": str(e)}


def check_service_endpoints(port: int) -> Dict[str, Any]:
    """Verifica todos los endpoints del servicio."""
    endpoints = [
        ("/cotizaciones/health", "GET"),
        ("/health/detailed", "GET"),
        ("/cotizaciones/status", "GET"),
        ("/", "GET")
    ]
    
    results = {}
    
    for endpoint, method in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f"http://localhost:{port}{endpoint}", timeout=10)
            elapsed = round((time.time() - start_time) * 1000, 2)
            
            results[endpoint] = {
                "status": "ok",
                "status_code": response.status_code,
                "response_time_ms": elapsed,
                "response_size": len(response.content)
            }
            
            if elapsed > 5000:  # Más de 5 segundos
                results[endpoint]["warning"] = "Slow response"
                
        except requests.exceptions.Timeout:
            results[endpoint] = {"status": "timeout", "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            results[endpoint] = {"status": "connection_error", "error": "Connection refused"}
        except Exception as e:
            results[endpoint] = {"status": "error", "error": str(e)}
    
    return results


def check_websocket_connection(port: int) -> Dict[str, Any]:
    """Verifica la conexión WebSocket."""
    try:
        import websockets
        import asyncio
        
        async def test_ws():
            uri = f"ws://localhost:{port}/ws/cotizaciones"
            try:
                async with websockets.connect(uri, timeout=10) as websocket:
                    # Enviar ping
                    await websocket.send(json.dumps({"action": "ping"}))
                    
                    # Recibir respuesta
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(response)
                    
                    return {
                        "status": "ok",
                        "connection_time_ms": 0,  # No medido
                        "response": data
                    }
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        # Ejecutar test WebSocket
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_ws())
        loop.close()
        
        return result
        
    except ImportError:
        return {"status": "skipped", "reason": "websockets not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_system_resources() -> Dict[str, Any]:
    """Verifica recursos del sistema."""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memoria
        memory = psutil.virtual_memory()
        
        # Disco
        disk = psutil.disk_usage('/')
        
        # Procesos Python
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
            try:
                if 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline or 'cotiza' in cmdline.lower():
                        python_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cmdline": cmdline,
                            "memory_mb": round(proc.info['memory_info'].rss / 1024 / 1024, 2),
                            "cpu_percent": proc.info['cpu_percent']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
                "available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                "used_percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "used_percent": round((disk.used / disk.total) * 100, 2)
            },
            "python_processes": python_processes
        }
        
    except Exception as e:
        return {"error": str(e)}


def check_database_connection() -> Dict[str, Any]:
    """Verifica la conexión a la base de datos."""
    try:
        from supabase_client import supabase
        
        # Test simple
        start_time = time.time()
        response = supabase.table("terminal_ratios_history").select("id").limit(1).execute()
        elapsed = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": "ok",
            "response_time_ms": elapsed,
            "has_data": len(response.data) > 0 if response.data else False
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_full_diagnosis(port: int = 8000) -> Dict[str, Any]:
    """Ejecuta diagnóstico completo del servicio."""
    print("🔍 INICIANDO DIAGNÓSTICO COMPLETO DEL SERVICIO")
    print("=" * 60)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "port": port
    }
    
    # 1. Verificar puerto
    print("1️⃣ Verificando puerto...")
    results["port_check"] = check_port_usage(port)
    print(f"   {'✅' if results['port_check'].get('in_use') else '❌'} Puerto {port}: {results['port_check'].get('process_name', 'No encontrado')}")
    
    # 2. Verificar endpoints
    print("2️⃣ Verificando endpoints...")
    results["endpoints"] = check_service_endpoints(port)
    for endpoint, data in results["endpoints"].items():
        status = data.get("status", "unknown")
        emoji = "✅" if status == "ok" else "❌"
        print(f"   {emoji} {endpoint}: {status}")
        if "response_time_ms" in data:
            print(f"      Tiempo: {data['response_time_ms']}ms")
    
    # 3. Verificar WebSocket
    print("3️⃣ Verificando WebSocket...")
    results["websocket"] = check_websocket_connection(port)
    ws_status = results["websocket"].get("status", "unknown")
    emoji = "✅" if ws_status == "ok" else "❌"
    print(f"   {emoji} WebSocket: {ws_status}")
    
    # 4. Verificar recursos del sistema
    print("4️⃣ Verificando recursos del sistema...")
    results["system"] = check_system_resources()
    if "error" not in results["system"]:
        cpu = results["system"]["cpu_percent"]
        memory = results["system"]["memory"]["used_percent"]
        print(f"   📊 CPU: {cpu}%")
        print(f"   💾 Memoria: {memory}%")
        print(f"   🐍 Procesos Python: {len(results['system']['python_processes'])}")
    
    # 5. Verificar base de datos
    print("5️⃣ Verificando base de datos...")
    results["database"] = check_database_connection()
    db_status = results["database"].get("status", "unknown")
    emoji = "✅" if db_status == "ok" else "❌"
    print(f"   {emoji} Base de datos: {db_status}")
    
    return results


def print_summary(results: Dict[str, Any]):
    """Imprime resumen del diagnóstico."""
    print("\n" + "=" * 60)
    print("📋 RESUMEN DEL DIAGNÓSTICO")
    print("=" * 60)
    
    # Verificar problemas críticos
    issues = []
    
    # Puerto no en uso
    if not results["port_check"].get("in_use"):
        issues.append("❌ Puerto no está en uso - servicio no corriendo")
    
    # Endpoints fallando
    failed_endpoints = [ep for ep, data in results["endpoints"].items() if data.get("status") != "ok"]
    if failed_endpoints:
        issues.append(f"❌ Endpoints fallando: {', '.join(failed_endpoints)}")
    
    # WebSocket fallando
    if results["websocket"].get("status") != "ok":
        issues.append("❌ WebSocket no funciona")
    
    # Recursos altos
    if "system" in results and "error" not in results["system"]:
        cpu = results["system"]["cpu_percent"]
        memory = results["system"]["memory"]["used_percent"]
        
        if cpu > 80:
            issues.append(f"⚠️  CPU alto: {cpu}%")
        if memory > 90:
            issues.append(f"⚠️  Memoria alta: {memory}%")
    
    # Base de datos fallando
    if results["database"].get("status") != "ok":
        issues.append("❌ Base de datos no accesible")
    
    if issues:
        print("🚨 PROBLEMAS DETECTADOS:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("✅ No se detectaron problemas críticos")
    
    print(f"\n⏰ Diagnóstico completado: {results['timestamp']}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnóstico completo del servicio")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servicio")
    parser.add_argument("--output", help="Archivo para guardar resultados JSON")
    
    args = parser.parse_args()
    
    results = run_full_diagnosis(args.port)
    print_summary(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Resultados guardados en: {args.output}")


if __name__ == "__main__":
    main()

