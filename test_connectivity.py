#!/usr/bin/env python3
"""
Script de prueba de conectividad que funciona sin dependencias externas
"""

import os
import sys
import time
import json
import asyncio
import websockets
import requests
from typing import Dict, Any
from datetime import datetime

def test_imports():
    """Prueba que se puedan importar los módulos principales"""
    print("📦 Probando importación de módulos...")
    
    results = {}
    
    # Probar imports individuales
    modules_to_test = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Servidor ASGI"),
        ("websockets", "WebSocket client"),
        ("requests", "HTTP client"),
        ("pyRofex", "Cliente ROFEX"),
        ("supabase", "Cliente Supabase"),
        ("telebot", "Bot de Telegram")
    ]
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}: {description}")
            results[module_name] = "ok"
        except ImportError as e:
            print(f"❌ {module_name}: No instalado - {e}")
            results[module_name] = "missing"
        except Exception as e:
            print(f"⚠️ {module_name}: Error - {e}")
            results[module_name] = "error"
    
    return results

def test_file_structure():
    """Verifica que los archivos principales existan"""
    print("\n📁 Verificando estructura de archivos...")
    
    required_files = [
        "main.py",
        "ws_rofex.py", 
        "supabase_client.py",
        "telegram_control.py",
        "ratios_worker.py",
        "requirements.txt"
    ]
    
    results = {}
    
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"✅ {file_name}: Existe")
            results[file_name] = "exists"
        else:
            print(f"❌ {file_name}: No encontrado")
            results[file_name] = "missing"
    
    return results

def test_environment_setup():
    """Verifica configuración del entorno"""
    print("\n🔧 Verificando configuración del entorno...")
    
    # Verificar Python version
    python_version = sys.version_info
    print(f"✅ Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Verificar directorio de trabajo
    cwd = os.getcwd()
    print(f"✅ Directorio de trabajo: {cwd}")
    
    # Verificar archivo .env
    env_exists = os.path.exists(".env")
    print(f"{'✅' if env_exists else '⚠️'} Archivo .env: {'Existe' if env_exists else 'No encontrado'}")
    
    # Verificar variables de entorno críticas
    critical_vars = [
        "ROFEX_USER",
        "ROFEX_PASSWORD", 
        "ROFEX_ACCOUNT",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID"
    ]
    
    configured_vars = []
    missing_vars = []
    
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            configured_vars.append(var)
        else:
            missing_vars.append(var)
    
    print(f"✅ Variables configuradas: {len(configured_vars)}/{len(critical_vars)}")
    if missing_vars:
        print(f"⚠️ Variables faltantes: {', '.join(missing_vars)}")
    
    return {
        "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
        "working_directory": cwd,
        "env_file_exists": env_exists,
        "configured_vars": len(configured_vars),
        "total_vars": len(critical_vars),
        "missing_vars": missing_vars
    }

async def test_websocket_client():
    """Prueba el cliente WebSocket básico"""
    print("\n🔌 Probando cliente WebSocket...")
    
    try:
        # Probar conexión a un WebSocket público para verificar que funciona
        async with websockets.connect("wss://echo.websocket.org", timeout=5) as websocket:
            # Enviar mensaje de prueba
            test_message = "Hello WebSocket!"
            await websocket.send(test_message)
            
            # Recibir respuesta
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            
            if response == test_message:
                print("✅ Cliente WebSocket funcionando correctamente")
                return {"status": "ok", "test": "echo_websocket"}
            else:
                print(f"⚠️ Respuesta inesperada: {response}")
                return {"status": "warning", "test": "echo_websocket"}
                
    except Exception as e:
        print(f"❌ Error probando WebSocket: {e}")
        return {"status": "error", "error": str(e)}

def test_http_client():
    """Prueba el cliente HTTP básico"""
    print("\n🌐 Probando cliente HTTP...")
    
    try:
        # Probar conexión a un servicio público
        response = requests.get("https://httpbin.org/get", timeout=10)
        
        if response.status_code == 200:
            print("✅ Cliente HTTP funcionando correctamente")
            return {"status": "ok", "test": "httpbin"}
        else:
            print(f"⚠️ Respuesta inesperada: {response.status_code}")
            return {"status": "warning", "test": "httpbin"}
            
    except Exception as e:
        print(f"❌ Error probando HTTP: {e}")
        return {"status": "error", "error": str(e)}

def create_minimal_test_server():
    """Crea un servidor de prueba mínimo"""
    print("\n🚀 Creando servidor de prueba mínimo...")
    
    test_server_code = '''
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "healthy", "message": "Test server running"}

@app.get("/test")
def test():
    return {"test": "success", "timestamp": "2024-01-01T00:00:00Z"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
'''
    
    try:
        with open("test_server.py", "w") as f:
            f.write(test_server_code)
        print("✅ Servidor de prueba creado: test_server.py")
        print("💡 Para ejecutar: python3 test_server.py")
        return {"status": "ok", "file": "test_server.py"}
    except Exception as e:
        print(f"❌ Error creando servidor de prueba: {e}")
        return {"status": "error", "error": str(e)}

async def main():
    """Función principal"""
    print("🧪 PRUEBA DE CONECTIVIDAD Y CONFIGURACIÓN")
    print("=" * 60)
    
    start_time = time.time()
    results = {}
    
    # 1. Probar imports
    results["imports"] = test_imports()
    
    # 2. Verificar archivos
    results["files"] = test_file_structure()
    
    # 3. Verificar entorno
    results["environment"] = test_environment_setup()
    
    # 4. Probar cliente HTTP
    results["http_client"] = test_http_client()
    
    # 5. Probar cliente WebSocket
    results["websocket_client"] = await test_websocket_client()
    
    # 6. Crear servidor de prueba
    results["test_server"] = create_minimal_test_server()
    
    # Resumen
    elapsed_time = time.time() - start_time
    print(f"\n📋 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r.get("status") == "ok")
    
    print(f"⏱️ Tiempo total: {elapsed_time:.2f} segundos")
    print(f"📊 Pruebas completadas: {total_tests}")
    print(f"✅ Exitosas: {successful_tests}")
    
    print(f"\n🎯 PRÓXIMOS PASOS:")
    print("1. Configurar archivo .env con credenciales reales")
    print("2. Instalar dependencias faltantes: pip install -r requirements.txt")
    print("3. Ejecutar servidor de prueba: python3 test_server.py")
    print("4. Probar conectividad: curl http://127.0.0.1:8001/health")
    print("5. Iniciar servidor principal: uvicorn main:app --port 8000")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")

