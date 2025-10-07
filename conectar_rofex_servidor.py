#!/usr/bin/env python3
"""
Conectar ROFEX en el contexto del servidor FastAPI
"""

import os
from dotenv import load_dotenv

def conectar_rofex_servidor():
    print("🔌 CONECTANDO ROFEX EN CONTEXTO DEL SERVIDOR")
    print("=" * 50)
    
    # Cargar credenciales
    load_dotenv()
    
    user = os.getenv('ROFEX_USERNAME')
    password = os.getenv('ROFEX_PASSWORD')
    account = os.getenv('ROFEX_ACCOUNT_NUMBER')
    
    print(f"📋 Credenciales cargadas:")
    print(f"   Usuario: {user}")
    print(f"   Cuenta: {account}")
    
    try:
        # Importar ws_rofex
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
            print("\n✅ ROFEX conectado exitosamente!")
            
            # Verificar estado
            status = ws_rofex.manager.status()
            print(f"\n📈 Estado actual:")
            for key, value in status.items():
                print(f"   {key}: {value}")
            
            # Probar envío de orden
            print("\n🧪 PROBANDO ENVÍO DE ORDEN...")
            try:
                test_result = ws_rofex.manager.send_order(
                    symbol="MERV - XMEV - TX26 - 24hs",
                    side="SELL",
                    size=1,
                    price=1000.0,
                    order_type="LIMIT",
                    client_order_id="test_servidor"
                )
                print(f"📤 Resultado test: {test_result}")
                
                if test_result.get('status') == 'ok':
                    print("🎉 ¡ROFEX funcionando correctamente en el servidor!")
                    return True
                else:
                    print(f"⚠️ Orden no enviada: {test_result.get('message')}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error en test: {e}")
                return False
        else:
            print(f"\n❌ Error conectando: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Excepción: {e}")
        return False

if __name__ == "__main__":
    conectar_rofex_servidor()
