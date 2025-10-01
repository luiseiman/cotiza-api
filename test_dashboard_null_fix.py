#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la corrección del problema de valores NULL
en el dashboard de ratios, específicamente para promedio_dia_anterior.
"""

import os
from dotenv import load_dotenv
from supabase_client import supabase
from datetime import datetime, timedelta
import json

def test_dashboard_query():
    """Prueba la consulta del dashboard para verificar si los valores NULL están manejados correctamente."""
    
    print("=" * 60)
    print("DIAGNÓSTICO: Dashboard de Ratios - Valores NULL")
    print("=" * 60)
    
    # Verificar datos históricos
    now = datetime.now()
    prev_biz = (now - timedelta(days=1)).date() if now.weekday() > 0 else (now - timedelta(days=3)).date()
    
    print(f"Fecha actual: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Día hábil anterior: {prev_biz}")
    print()
    
    # Probar la función del dashboard
    try:
        print("🔍 Probando función get_ratios_dashboard()...")
        response = supabase.rpc("get_ratios_dashboard").execute()
        
        if response.data:
            print(f"✅ Función ejecutada correctamente. {len(response.data)} pares encontrados.")
            print()
            
            # Analizar resultados
            null_count = 0
            total_count = len(response.data)
            
            for i, row in enumerate(response.data):
                par = row.get('par', 'N/A')
                promedio_dia_anterior = row.get('promedio_dia_anterior')
                dif_dia_anterior_pct = row.get('dif_dia_anterior_pct')
                
                if promedio_dia_anterior is None:
                    null_count += 1
                    status = "❌ NULL"
                else:
                    status = "✅ OK"
                
                print(f"{i+1:2d}. {par}")
                print(f"    promedio_dia_anterior: {promedio_dia_anterior} {status}")
                print(f"    dif_dia_anterior_pct: {dif_dia_anterior_pct}")
                print()
                
                # Mostrar solo los primeros 5 para no saturar
                if i >= 4:
                    remaining = total_count - 5
                    if remaining > 0:
                        print(f"    ... y {remaining} pares más")
                    break
            
            print("=" * 60)
            print("RESUMEN:")
            print(f"Total de pares: {total_count}")
            print(f"Pares con promedio_dia_anterior NULL: {null_count}")
            print(f"Pares con datos históricos: {total_count - null_count}")
            print("=" * 60)
            
            if null_count == total_count:
                print("⚠️  TODOS los pares tienen promedio_dia_anterior NULL")
                print("   Esto indica que no hay datos históricos disponibles.")
                print("   Es normal en sistemas nuevos o pares recientes.")
            elif null_count > 0:
                print("⚠️  Algunos pares tienen promedio_dia_anterior NULL")
                print("   Esto es normal para pares sin datos históricos.")
            else:
                print("✅ Todos los pares tienen datos históricos disponibles")
            
        else:
            print("❌ No se obtuvieron datos de la función")
            
    except Exception as e:
        print(f"❌ Error al ejecutar la función: {e}")
        
        # Fallback: probar consulta directa
        print("\n🔄 Intentando consulta directa...")
        try:
            response = supabase.table("terminal_ratios_history").select("*").not_.is_("last_ratio", "null").order("asof", desc=True).limit(5).execute()
            if response.data:
                print(f"✅ Datos disponibles en terminal_ratios_history: {len(response.data)} registros")
                print("   El problema puede ser que la función no existe en Supabase.")
                print("   Necesitas ejecutar el SQL de consultas_ratios_optimizadas.sql")
            else:
                print("❌ No hay datos en terminal_ratios_history")
        except Exception as e2:
            print(f"❌ Error en consulta directa: {e2}")

def test_historical_data():
    """Verifica qué datos históricos están disponibles."""
    
    print("\n" + "=" * 60)
    print("ANÁLISIS DE DATOS HISTÓRICOS")
    print("=" * 60)
    
    now = datetime.now()
    
    # Verificar últimos 7 días
    print("Verificando datos por día:")
    for days_back in range(7):
        check_date = (now - timedelta(days=days_back)).date()
        
        response = supabase.table('terminal_ratios_history').select('asof, last_ratio').gte('asof', f'{check_date} 00:00:00').lt('asof', f'{check_date} 23:59:59').not_.is_('last_ratio', 'null').limit(1).execute()
        
        count = len(response.data) if response.data else 0
        status = "✅" if count > 0 else "❌"
        print(f"{status} {check_date}: {count} registros con last_ratio válido")
    
    print("\n" + "=" * 60)
    print("RECOMENDACIONES:")
    print("=" * 60)
    
    # Verificar si hay datos de hoy
    today = now.date()
    today_response = supabase.table('terminal_ratios_history').select('asof').gte('asof', f'{today} 00:00:00').not_.is_('last_ratio', 'null').limit(1).execute()
    
    if today_response.data:
        print("✅ Sistema funcionando correctamente - hay datos de hoy")
        print("💡 El problema de NULL en promedio_dia_anterior es normal:")
        print("   - No hay datos históricos para días anteriores")
        print("   - El sistema está recopilando datos desde hoy")
        print("   - Con el tiempo, estos campos se llenarán automáticamente")
    else:
        print("❌ No hay datos de hoy - verificar que el sistema esté funcionando")
    
    print("\n🔧 Para aplicar las correcciones:")
    print("   1. Ejecutar consultas_ratios_optimizadas.sql en Supabase")
    print("   2. Las consultas ahora manejan NULL correctamente")
    print("   3. Usar fallback para datos históricos cuando no hay día hábil anterior")

if __name__ == "__main__":
    load_dotenv()
    test_dashboard_query()
    test_historical_data()
