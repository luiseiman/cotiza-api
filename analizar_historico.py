#!/usr/bin/env python3
"""
Script para analizar qué pares tienen datos históricos completos y cuáles no.
"""

from supabase_client import get_active_pairs, get_last_ratio_data

def analizar_datos_historicos():
    """Analiza qué pares tienen datos históricos completos."""
    print("🔍 ANALIZANDO DATOS HISTÓRICOS")
    print("=" * 60)
    
    # 1. Obtener pares disponibles
    pairs = get_active_pairs()
    print(f"📋 Pares encontrados: {len(pairs)}")
    
    # 2. Analizar cada par
    pares_con_historico = []
    pares_sin_historico = []
    
    for i, pair in enumerate(pairs):
        base_symbol = pair["base_symbol"]
        quote_symbol = pair["quote_symbol"]
        user_id = pair.get("user_id")
        
        print(f"\n🔍 Analizando par {i+1}: {base_symbol} / {quote_symbol}")
        
        # Obtener datos históricos
        historical_data = get_last_ratio_data(base_symbol, quote_symbol, user_id)
        
        if historical_data:
            # Verificar qué campos históricos están disponibles
            campos_historicos = [
                'sma180_bid', 'sma180_offer', 'bb180_bid_upper', 'bb180_bid_lower',
                'bb180_offer_upper', 'bb180_offer_lower', 'sma180_mid', 'std60_mid',
                'std180_mid', 'z_bid', 'z_ask', 'ratio_spread', 'vol_ratio',
                'bb180_mid_upper', 'bb180_mid_lower'
            ]
            
            campos_disponibles = []
            for campo in campos_historicos:
                if historical_data.get(campo) is not None:
                    campos_disponibles.append(campo)
            
            print(f"   ✅ Datos históricos encontrados: {len(campos_disponibles)}/{len(campos_historicos)} campos")
            print(f"   📊 Campos disponibles: {campos_disponibles[:3]}...")
            
            if len(campos_disponibles) >= 10:  # Al menos 10 campos históricos
                pares_con_historico.append({
                    "par": pair,
                    "historical_data": historical_data,
                    "campos_disponibles": campos_disponibles
                })
            else:
                pares_sin_historico.append({
                    "par": pair,
                    "historical_data": historical_data,
                    "campos_disponibles": campos_disponibles
                })
        else:
            print(f"   ❌ Sin datos históricos")
            pares_sin_historico.append({
                "par": pair,
                "historical_data": None,
                "campos_disponibles": []
            })
    
    # 3. Mostrar resumen
    print(f"\n📊 RESUMEN FINAL:")
    print(f"   Pares CON histórico completo: {len(pares_con_historico)}")
    print(f"   Pares SIN histórico completo: {len(pares_sin_historico)}")
    
    # 4. Mostrar pares con histórico completo
    if pares_con_historico:
        print(f"\n✅ PARES CON HISTÓRICO COMPLETO:")
        for i, item in enumerate(pares_con_historico):
            pair = item["par"]
            campos = item["campos_disponibles"]
            print(f"   {i+1}. {pair['base_symbol']} / {pair['quote_symbol']}")
            print(f"      Campos: {len(campos)} disponibles")
            print(f"      Ejemplos: {campos[:3]}")
    
    # 5. Mostrar pares sin histórico completo
    if pares_sin_historico:
        print(f"\n❌ PARES SIN HISTÓRICO COMPLETO:")
        for i, item in enumerate(pares_sin_historico):
            pair = item["par"]
            if item["historical_data"]:
                campos = item["campos_disponibles"]
                print(f"   {i+1}. {pair['base_symbol']} / {pair['quote_symbol']} - Solo {len(campos)} campos")
            else:
                print(f"   {i+1}. {pair['base_symbol']} / {pair['quote_symbol']} - Sin datos históricos")
    
    return pares_con_historico, pares_sin_historico

if __name__ == "__main__":
    analizar_datos_historicos()
