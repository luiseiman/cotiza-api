#!/usr/bin/env python3
"""
Script de prueba para verificar que la función get_ratios_dashboard() 
incluye correctamente el campo client_id.
"""

import os
from dotenv import load_dotenv
from supabase_client import supabase
import json

def test_function_with_client_id():
    """Prueba la función actualizada con client_id."""
    
    print("=" * 70)
    print("PRUEBA: Función get_ratios_dashboard() con client_id")
    print("=" * 70)
    
    try:
        print("🔍 Ejecutando función get_ratios_dashboard()...")
        response = supabase.rpc("get_ratios_dashboard").execute()
        
        if response.data:
            print(f"✅ Función ejecutada correctamente. {len(response.data)} registros encontrados.")
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
                print("✅ Campo 'client_id' presente en la función")
                
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
                    print(f"    {i+1}. {par} (client: {client_id}) → ratio: {ultimo_ratio}")
                
                if len(response.data) > 5:
                    print(f"    ... y {len(response.data) - 5} registros más")
                    
            else:
                print("❌ Campo 'client_id' NO encontrado en la función")
                print("   Necesitas ejecutar el SQL actualizado en Supabase")
            
        else:
            print("❌ No se obtuvieron datos de la función")
            
    except Exception as e:
        print(f"❌ Error al ejecutar la función: {e}")
        print("\n🔧 Posibles soluciones:")
        print("   1. Ejecutar el SQL actualizado en Supabase")
        print("   2. Verificar que la función existe")
        print("   3. Verificar permisos de ejecución")

def test_different_client_ids():
    """Verifica si hay datos de diferentes client_ids en la base de datos."""
    
    print("\n" + "=" * 70)
    print("ANÁLISIS: Client IDs en terminal_ratios_history")
    print("=" * 70)
    
    try:
        # Obtener client_ids únicos de la tabla
        response = supabase.table("terminal_ratios_history").select("client_id").not_.is_("last_ratio", "null").execute()
        
        if response.data:
            client_ids = set()
            for record in response.data:
                client_id = record.get('client_id')
                if client_id:
                    client_ids.add(client_id)
            
            print(f"📊 Client IDs únicos en terminal_ratios_history: {len(client_ids)}")
            for cid in sorted(client_ids):
                count = sum(1 for r in response.data if r.get('client_id') == cid)
                print(f"    - {cid}: {count} registros con last_ratio válido")
            
            if len(client_ids) > 1:
                print("\n💡 Hay múltiples client_ids, la función debería distinguirlos correctamente")
            else:
                print("\n💡 Solo hay un client_id, pero la función ahora está preparada para múltiples")
                
        else:
            print("❌ No hay datos en terminal_ratios_history")
            
    except Exception as e:
        print(f"❌ Error al consultar terminal_ratios_history: {e}")

def show_sql_instructions():
    """Muestra las instrucciones para aplicar el SQL actualizado."""
    
    print("\n" + "=" * 70)
    print("INSTRUCCIONES PARA APLICAR CAMBIOS")
    print("=" * 70)
    
    print("📝 Para aplicar los cambios en Supabase:")
    print()
    print("1. Abrir el SQL Editor en Supabase")
    print("2. Ejecutar el contenido de 'consultas_ratios_optimizadas.sql'")
    print("3. Esto actualizará la función get_ratios_dashboard()")
    print("4. La función ahora incluye el campo 'client_id'")
    print()
    print("🔄 Después de ejecutar el SQL:")
    print("   - La función distinguirá entre diferentes client_ids")
    print("   - Cada par podrá tener múltiples entradas por cliente")
    print("   - Los índices estarán optimizados para client_id")
    print()
    print("🧪 Para probar:")
    print("   python3 test_client_id_function.py")

if __name__ == "__main__":
    load_dotenv()
    test_function_with_client_id()
    test_different_client_ids()
    show_sql_instructions()
