#!/usr/bin/env python3
"""
Script para probar credenciales ROFEX en ambiente REMARKET (pruebas)
"""

import os
from dotenv import load_dotenv

def probar_credenciales_remarket():
    print("🧪 PROBANDO CREDENCIALES EN AMBIENTE REMARKET (PRUEBAS)")
    print("=" * 60)
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Obtener credenciales
    user = os.getenv('ROFEX_USERNAME')
    password = os.getenv('ROFEX_PASSWORD')
    account = os.getenv('ROFEX_ACCOUNT_NUMBER')
    
    print(f"📋 Credenciales a probar:")
    print(f"   Usuario: {user}")
    print(f"   Cuenta: {account}")
    print(f"   Password: {'*' * len(password)}")
    
    try:
        import pyRofex as pr
        
        print("\n🔧 Configurando ambiente REMARKET...")
        
        # Usar ambiente REMARKET (pruebas) en lugar de LIVE
        pr.initialize(
            user=user,
            password=password, 
            account=account,
            environment=pr.Environment.REMARKET
        )
        
        print("✅ Inicialización exitosa en REMARKET")
        
        # Probar conexión WebSocket básica
        print("\n🔌 Probando conexión WebSocket...")
        
        def test_handler(msg):
            print(f"📨 Mensaje recibido: {msg}")
        
        try:
            pr.init_websocket_connection(
                market_data_handler=test_handler,
                order_report_handler=test_handler,
                error_handler=lambda e: print(f"❌ Error: {e}")
            )
            
            print("✅ Conexión WebSocket establecida")
            
            # Cerrar conexión
            pr.close_websocket_connection()
            print("✅ Conexión cerrada correctamente")
            
            return True
            
        except Exception as e:
            print(f"❌ Error en WebSocket: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

def probar_credenciales_live():
    print("\n🚀 PROBANDO CREDENCIALES EN AMBIENTE LIVE (PRODUCCIÓN)")
    print("=" * 60)
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Obtener credenciales
    user = os.getenv('ROFEX_USERNAME')
    password = os.getenv('ROFEX_PASSWORD')
    account = os.getenv('ROFEX_ACCOUNT_NUMBER')
    
    try:
        import pyRofex as pr
        
        print("🔧 Configurando ambiente LIVE...")
        
        # Usar ambiente LIVE (producción)
        pr.initialize(
            user=user,
            password=password, 
            account=account,
            environment=pr.Environment.LIVE
        )
        
        print("✅ Inicialización exitosa en LIVE")
        return True
        
    except Exception as e:
        print(f"❌ Error en LIVE: {e}")
        return False

def main():
    print("🔐 VERIFICADOR DE CREDENCIALES ROFEX")
    print("=" * 60)
    
    # Probar primero en REMARKET (más seguro)
    if probar_credenciales_remarket():
        print("\n✅ CREDENCIALES VÁLIDAS EN REMARKET")
        
        # Si funciona en REMARKET, probar en LIVE
        if probar_credenciales_live():
            print("\n🎉 CREDENCIALES VÁLIDAS EN AMBOS AMBIENTES")
            print("✅ Puedes usar LIVE para trading real")
        else:
            print("\n⚠️ CREDENCIALES VÁLIDAS SOLO EN REMARKET")
            print("❌ No puedes usar LIVE (posible problema de permisos)")
    else:
        print("\n❌ CREDENCIALES INVÁLIDAS")
        print("🔧 Verifica usuario, password y cuenta")

if __name__ == "__main__":
    main()
