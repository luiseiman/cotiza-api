#!/usr/bin/env python3
"""
Script para verificar que todos los campos se estén guardando correctamente.
"""

from supabase_client import get_active_pairs, get_last_ratio_data

def verificar_ultimos_registros():
    """Verifica los últimos registros guardados para ver si tienen todos los campos."""
    print("🔍 VERIFICANDO ÚLTIMOS REGISTROS GUARDADOS")
    print("=" * 60)
    
    # Obtener pares disponibles
    pairs = get_active_pairs()
    print(f"📋 Pares encontrados: {len(pairs)}")
    
    # Verificar los últimos registros de cada par
    for i, pair in enumerate(pairs[:3]):  # Solo verificar los primeros 3
        base_symbol = pair["base_symbol"]
        quote_symbol = pair["quote_symbol"]
        user_id = pair.get("user_id")
        
        print(f"\n🔍 Verificando par {i+1}: {base_symbol} / {quote_symbol}")
        
        # Obtener el último registro
        historical_data = get_last_ratio_data(base_symbol, quote_symbol, user_id)
        
        if historical_data:
            # Verificar campos críticos
            campos_criticos = [
                'mid_ratio', 'sma180_bid', 'sma180_offer', 'bb180_bid_upper',
                'bb180_bid_lower', 'bb180_offer_upper', 'bb180_offer_lower',
                'sma180_mid', 'std60_mid', 'std180_mid', 'z_bid', 'z_ask',
                'ratio_spread', 'vol_ratio', 'bb180_mid_upper', 'bb180_mid_lower'
            ]
            
            campos_completos = 0
            campos_null = 0
            
            for campo in campos_criticos:
                valor = historical_data.get(campo)
                if valor is not None:
                    campos_completos += 1
                else:
                    campos_null += 1
            
            print(f"   📊 Campos completos: {campos_completos}/{len(campos_criticos)}")
            print(f"   ❌ Campos NULL: {campos_null}/{len(campos_criticos)}")
            
            if campos_null == 0:
                print(f"   ✅ REGISTRO COMPLETO - Todos los campos tienen valores")
            elif campos_null <= 3:
                print(f"   ⚠️ REGISTRO CASI COMPLETO - Pocos campos NULL")
            else:
                print(f"   ❌ REGISTRO INCOMPLETO - Muchos campos NULL")
            
            # Mostrar algunos valores como ejemplo
            print(f"   📈 Ejemplos de valores:")
            for campo in ['mid_ratio', 'sma180_mid', 'z_bid', 'bb180_mid_upper']:
                valor = historical_data.get(campo)
                if valor is not None:
                    print(f"      {campo}: {valor}")
                else:
                    print(f"      {campo}: NULL")
        else:
            print(f"   ❌ Sin registros en la base de datos")

if __name__ == "__main__":
    verificar_ultimos_registros()
