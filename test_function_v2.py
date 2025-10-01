#!/usr/bin/env python3
"""
Script de prueba para la función get_ratios_dashboard_v2() que evita 
el error de ambigüedad con client_id.
"""

import os
from dotenv import load_dotenv
from supabase_client import supabase
import json

def test_function_v2():
    """Prueba la función v2 que evita la ambigüedad."""
    
    print("=" * 70)
    print("PRUEBA: Función get_ratios_dashboard_v2() (sin ambigüedad)")
    print("=" * 70)
    
    try:
        print("🔍 Ejecutando función get_ratios_dashboard_v2()...")
        response = supabase.rpc("get_ratios_dashboard_v2").execute()
        
        if response.data:
            print(f"✅ Función v2 ejecutada correctamente. {len(response.data)} registros encontrados.")
            print()
            
            # Verificar que el campo client_id está presente
            first_record = response.data[0]
            has_client_id = 'client_id' in first_record
            
            print(f"📋 Campos en el primer registro:")
            for key, value in first_record.items():
                marker = "🆕" if key == 'client_id' else "✅"
                print(f"    {marker} {key}: {value}")
            
            print()
            print("=" * 70)
            print("ANÁLISIS DE RESULTADOS:")
            print("=" * 70)
            
            if has_client_id:
                print("✅ Campo 'client_id' presente en la función v2")
                
                # Analizar client_ids únicos
                client_ids = set()
                for record in response.data:
                    client_id = record.get('client_id')
                    if client_id:
                        client_ids.add(client_id)
                
                print(f"📊 Client IDs únicos encontrados: {len(client_ids)}")
                for cid in sorted(client_ids):
                    count = sum(1 for r in response.data if r.get('client_id') == cid)
                    print(f"    - {cid}: {count} pares")
                
                # Mostrar algunos ejemplos
                print("\n📝 Ejemplos de registros:")
                for i, record in enumerate(response.data[:5]):
                    par = record.get('par', 'N/A')
                    client_id = record.get('client_id', 'N/A')
                    ultimo_ratio = record.get('ultimo_ratio_operado', 'N/A')
                    promedio_dia_anterior = record.get('promedio_dia_anterior', 'N/A')
                    print(f"    {i+1}. {par} (client: {client_id})")
                    print(f"        → ratio: {ultimo_ratio}, día anterior: {promedio_dia_anterior}")
                
                if len(response.data) > 5:
                    print(f"    ... y {len(response.data) - 5} registros más")
                    
                print("\n✅ FUNCIÓN V2 FUNCIONA CORRECTAMENTE")
                print("💡 Puedes usar get_ratios_dashboard_v2() en lugar de get_ratios_dashboard()")
                    
            else:
                print("❌ Campo 'client_id' NO encontrado en la función v2")
                print("   Necesitas ejecutar el SQL actualizado en Supabase")
            
        else:
            print("❌ No se obtuvieron datos de la función v2")
            
    except Exception as e:
        print(f"❌ Error al ejecutar la función v2: {e}")
        
        # Probar también la función original
        print("\n🔄 Probando función original...")
        try:
            response_orig = supabase.rpc("get_ratios_dashboard").execute()
            if response_orig.data:
                print("✅ Función original funciona, pero sin client_id")
                print("💡 Usa la función v2 para incluir client_id")
            else:
                print("❌ Función original también tiene problemas")
        except Exception as e2:
            print(f"❌ Error en función original: {e2}")

def show_sql_instructions():
    """Muestra las instrucciones para aplicar el SQL corregido."""
    
    print("\n" + "=" * 70)
    print("INSTRUCCIONES PARA APLICAR CAMBIOS CORREGIDOS")
    print("=" * 70)
    
    print("📝 Para resolver el error de ambigüedad:")
    print()
    print("1. Abrir el SQL Editor en Supabase")
    print("2. Ejecutar el contenido de 'consultas_ratios_optimizadas.sql'")
    print("3. Esto creará DOS funciones:")
    print("   - get_ratios_dashboard()     (puede dar error de ambigüedad)")
    print("   - get_ratios_dashboard_v2()  (sin ambigüedad)")
    print()
    print("4. Usar get_ratios_dashboard_v2() en tu aplicación")
    print()
    print("🔄 En dashboard_ratios_api.py, cambiar:")
    print("   response = supabase.rpc('get_ratios_dashboard').execute()")
    print("   por:")
    print("   response = supabase.rpc('get_ratios_dashboard_v2').execute()")
    print()
    print("🧪 Para probar:")
    print("   python3 test_function_v2.py")

if __name__ == "__main__":
    load_dotenv()
    test_function_v2()
    show_sql_instructions()
