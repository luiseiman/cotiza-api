#!/usr/bin/env python3
"""
Iniciar ROFEX en el servidor usando credenciales del .env
"""

import os
from dotenv import load_dotenv

def iniciar_rofex():
    print("🚀 INICIANDO ROFEX EN SERVIDOR")
    print("=" * 40)
    
    # Cargar credenciales del .env
    load_dotenv()
    
    user = os.getenv('ROFEX_USERNAME')
    password = os.getenv('ROFEX_PASSWORD')
    account = os.getenv('ROFEX_ACCOUNT_NUMBER')
    
    print(f"📋 Credenciales:")
    print(f"   Usuario: {user}")
    print(f"   Cuenta: {account}")
    print(f"   Password: {'*' * len(password)}")
    
    try:
        # Importar ws_rofex del servidor
        import ws_rofex
        
        print("\n📡 Iniciando conexión ROFEX...")
        instrumentos = ["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"]
        
        result = ws_rofex.manager.start(
            user=user,
            password=password,
            account=account,
            instrumentos=instrumentos
        )
        
        print(f"\n📊 Resultado:")
        print(f"   Status: {result.get('status')}")
        print(f"   Error: {result.get('error', 'N/A')}")
        print(f"   WS: {result.get('ws', 'N/A')}")
        
        if result.get('status') == 'started':
            print("\n✅ ROFEX iniciado exitosamente en el servidor!")
            
            # Verificar estado
            status = ws_rofex.manager.status()
            print(f"📈 Estado actual: {status}")
            
            return True
        else:
            print(f"\n❌ Error iniciando ROFEX: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Excepción: {e}")
        return False

if __name__ == "__main__":
    iniciar_rofex()
