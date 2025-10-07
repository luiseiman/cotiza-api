#!/usr/bin/env python3
"""
Script para verificar y conectar ROFEX usando credenciales del entorno
"""

import os
import sys
from dotenv import load_dotenv

def verificar_credenciales_rofex():
    print("🔍 VERIFICANDO CREDENCIALES DE ROFEX")
    print("=" * 50)
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar credenciales (usando los nombres correctos del .env)
    user = os.getenv('ROFEX_USERNAME')
    password = os.getenv('ROFEX_PASSWORD') 
    account = os.getenv('ROFEX_ACCOUNT_NUMBER')
    
    print(f"ROFEX_USERNAME: {'✅ Configurado' if user else '❌ No configurado'}")
    print(f"ROFEX_PASSWORD: {'✅ Configurado' if password else '❌ No configurado'}")
    print(f"ROFEX_ACCOUNT_NUMBER: {'✅ Configurado' if account else '❌ No configurado'}")
    
    if not all([user, password, account]):
        print("\n❌ FALTAN CREDENCIALES DE ROFEX")
        print("Necesitas configurar en tu archivo .env:")
        print("ROFEX_USERNAME=tu_usuario")
        print("ROFEX_PASSWORD=tu_password") 
        print("ROFEX_ACCOUNT_NUMBER=tu_cuenta")
        return False
    
    print(f"\n✅ CREDENCIALES ENCONTRADAS:")
    print(f"   Usuario: {user}")
    print(f"   Cuenta: {account}")
    print(f"   Password: {'*' * len(password)}")
    
    return True

def conectar_rofex():
    print("\n🔌 CONECTANDO A ROFEX")
    print("=" * 50)
    
    try:
        # Importar ws_rofex
        import ws_rofex
        
        # Obtener credenciales
        user = os.getenv('ROFEX_USERNAME')
        password = os.getenv('ROFEX_PASSWORD')
        account = os.getenv('ROFEX_ACCOUNT_NUMBER')
        
        print(f"📡 Iniciando conexión con usuario: {user}")
        
        # Intentar conectar (necesita instrumentos)
        instrumentos = ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
        result = ws_rofex.manager.start(user=user, password=password, account=account, instrumentos=instrumentos)
        
        print(f"📊 Resultado de conexión:")
        print(f"   Status: {result.get('status')}")
        print(f"   Error: {result.get('error', 'N/A')}")
        print(f"   WS: {result.get('ws', 'N/A')}")
        
        if result.get('status') == 'ok':
            print("\n✅ ROFEX CONECTADO EXITOSAMENTE")
            
            # Verificar estado de conexión
            status = ws_rofex.manager.status()
            print(f"📈 Estado de conexión: {status}")
            
            return True
        else:
            print(f"\n❌ ERROR CONECTANDO ROFEX: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPCIÓN AL CONECTAR: {e}")
        return False

def probar_envio_orden():
    print("\n📤 PROBANDO ENVÍO DE ORDEN")
    print("=" * 50)
    
    try:
        import ws_rofex
        
        # Verificar si está conectado
        if not ws_rofex.manager._ws_open:
            print("❌ ROFEX no está conectado")
            return False
        
        print("✅ ROFEX conectado, probando envío de orden...")
        
        # Intentar enviar una orden de prueba (pequeña cantidad)
        result = ws_rofex.manager.send_order(
            symbol="GGAL",
            side="BUY", 
            size=1,  # Cantidad mínima
            price=100.0,  # Precio bajo para que no se ejecute
            client_order_id="test_conexion_001"
        )
        
        print(f"📊 Resultado del envío:")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message', 'N/A')}")
        
        if result.get('status') == 'ok':
            print("✅ Orden enviada exitosamente")
            return True
        else:
            print(f"❌ Error enviando orden: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPCIÓN EN ENVÍO: {e}")
        return False

def main():
    print("🚀 CONECTOR ROFEX - VERIFICACIÓN COMPLETA")
    print("=" * 60)
    
    # Paso 1: Verificar credenciales
    if not verificar_credenciales_rofex():
        return
    
    # Paso 2: Conectar ROFEX
    if not conectar_rofex():
        return
    
    # Paso 3: Probar envío de orden
    if not probar_envio_orden():
        return
    
    print("\n🎉 TODOS LOS TESTS PASARON")
    print("✅ ROFEX está listo para operaciones reales")

if __name__ == "__main__":
    main()
