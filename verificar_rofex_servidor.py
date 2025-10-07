#!/usr/bin/env python3
"""
Verificar estado de ROFEX en el contexto del servidor
"""

def verificar_rofex():
    print("🔍 VERIFICANDO ROFEX EN CONTEXTO DEL SERVIDOR")
    print("=" * 50)
    
    try:
        # Importar ws_rofex
        import ws_rofex
        
        print("✅ ws_rofex importado correctamente")
        
        # Verificar si tiene manager
        if hasattr(ws_rofex, 'manager'):
            print("✅ ws_rofex.manager existe")
            
            # Verificar estado
            status = ws_rofex.manager.status()
            print(f"📊 Estado de ROFEX:")
            for key, value in status.items():
                print(f"   {key}: {value}")
            
            # Verificar si está conectado
            if hasattr(ws_rofex.manager, '_ws_open'):
                print(f"🔌 _ws_open: {ws_rofex.manager._ws_open}")
            
            if hasattr(ws_rofex.manager, '_pyrofex'):
                print(f"🐍 _pyrofex: {ws_rofex.manager._pyrofex is not None}")
            
            # Probar envío de orden
            print("\n🧪 PROBANDO ENVÍO DE ORDEN...")
            try:
                result = ws_rofex.manager.send_order(
                    symbol="MERV - XMEV - TX26 - 24hs",
                    side="SELL",
                    size=1,
                    price=1000.0,
                    order_type="LIMIT",
                    client_order_id="test_verificacion"
                )
                print(f"📤 Resultado: {result}")
            except Exception as e:
                print(f"❌ Error enviando orden: {e}")
            
        else:
            print("❌ ws_rofex.manager no existe")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verificar_rofex()
