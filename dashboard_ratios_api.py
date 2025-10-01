#!/usr/bin/env python3
"""
API endpoint optimizado para obtener datos del dashboard de ratios.
Incluye 3 estrategias diferentes según tus necesidades de rendimiento.
"""

from fastapi import APIRouter
from typing import Dict, List, Any
from datetime import datetime, timedelta
from supabase_client import supabase
import time

router = APIRouter()


# =====================================================================
# ESTRATEGIA 1: VISTA MATERIALIZADA (MÁS RÁPIDA - <10ms)
# =====================================================================
# Requiere crear la vista materializada en Supabase primero
# Ejecutar: consultas_ratios_optimizadas.sql (sección vista materializada)

@router.get("/ratios/dashboard/fast")
async def get_dashboard_fast() -> Dict[str, Any]:
    """
    Obtiene datos del dashboard desde vista materializada.
    
    Ventajas:
    - ULTRA RÁPIDO (<10ms)
    - Ideal para dashboards con muchos usuarios
    - Menor carga en la BD
    
    Desventajas:
    - Requiere refresh periódico (10 segundos de retraso máximo)
    """
    try:
        start = time.time()
        
        # Query simple a la vista materializada
        response = supabase.table("ratios_dashboard_view").select("*").execute()
        
        elapsed = (time.time() - start) * 1000
        
        return {
            "status": "success",
            "data": response.data,
            "count": len(response.data) if response.data else 0,
            "query_time_ms": round(elapsed, 2),
            "method": "materialized_view",
            "freshness": "~10 seconds"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "method": "materialized_view"
        }


def refresh_materialized_view():
    """
    Función helper para refrescar la vista materializada.
    Llamar desde un worker o scheduler cada 10 segundos.
    """
    try:
        # Opción 1: Si tienes permisos para ejecutar SQL directo
        supabase.rpc("refresh_ratios_view").execute()
        return True
    except Exception as e:
        print(f"Error refreshing materialized view: {e}")
        return False


# =====================================================================
# ESTRATEGIA 2: FUNCIÓN POSTGRESQL (BALANCE - 100-500ms)
# =====================================================================
# Requiere crear la función en Supabase primero
# Ejecutar: consultas_ratios_optimizadas.sql (sección función)

@router.get("/ratios/dashboard/balanced")
async def get_dashboard_balanced() -> Dict[str, Any]:
    """
    Obtiene datos del dashboard usando función PostgreSQL optimizada.
    
    NOTA: Usa la vista ratios_dashboard_with_client_id para evitar error de ambigüedad con client_id.
    
    Ventajas:
    - Datos en tiempo real
    - Rápido (100-500ms)
    - No requiere refresh
    - Incluye client_id para separación por cliente
    
    Desventajas:
    - Más lento que vista materializada
    - Mayor carga en BD con muchos usuarios concurrentes
    """
    try:
        start = time.time()
        
        # Llamar a la vista que evita ambigüedad con client_id
        response = supabase.table("ratios_dashboard_with_client_id").select("*").execute()
        
        elapsed = (time.time() - start) * 1000
        
        return {
            "status": "success",
            "data": response.data,
            "count": len(response.data) if response.data else 0,
            "query_time_ms": round(elapsed, 2),
            "method": "postgresql_function",
            "freshness": "real-time"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "method": "postgresql_function"
        }


# =====================================================================
# ESTRATEGIA 3: PYTHON PURO (MÁS FLEXIBLE - 500-2000ms)
# =====================================================================
# No requiere cambios en Supabase, pero es más lento

@router.get("/ratios/dashboard/flexible")
async def get_dashboard_flexible() -> Dict[str, Any]:
    """
    Obtiene datos del dashboard procesando en Python.
    
    Ventajas:
    - No requiere cambios en BD
    - Fácil de modificar
    - Datos en tiempo real
    
    Desventajas:
    - MÁS LENTO (500-2000ms)
    - Mayor consumo de memoria
    - No recomendado para producción con alta carga
    """
    try:
        start = time.time()
        
        # Helper: ejecución con reintentos para manejar EAGAIN/transitorios
        def _execute_with_retry(q, retries: int = 3, delay: float = 0.5):
            for i in range(retries):
                try:
                    return q.execute()
                except Exception as e:
                    msg = str(e)
                    if "Resource temporarily unavailable" in msg and i < retries - 1:
                        time_module.sleep(delay * (i + 1))
                        continue
                    raise

        # Un solo query: últimos 30 días, todos los pares, para evitar N+1
        now = datetime.utcnow()
        base_query = supabase.table("terminal_ratios_history")\
            .select("base_symbol, quote_symbol, user_id, last_ratio, asof")\
            .not_.is_("last_ratio", "null")\
            .gte("asof", (now - timedelta(days=30)).isoformat())\
            .order("asof", desc=False)

        data_response = _execute_with_retry(base_query)
        if not data_response.data:
            return {"status": "success", "data": [], "count": 0}

        # Agrupar en memoria por (base, quote, user_id)
        grouped = {}
        for row in data_response.data:
            key = (row["base_symbol"], row["quote_symbol"], row.get("user_id"))
            grouped.setdefault(key, []).append(
                (datetime.fromisoformat(row["asof"].replace("Z", "+00:00")), row["last_ratio"]) 
            )

        # Procesar cada grupo
        results = []
        for (base, quote, user_id), data_points in grouped.items():
            
            # Último ratio
            ultimo_ratio = data_points[-1][1] if data_points else None
            
            if not ultimo_ratio:
                continue
            
            # Calcular promedios por período
            rueda_cutoff = now - timedelta(hours=24)
            semana_cutoff = now - timedelta(days=7)
            mes_cutoff = now - timedelta(days=30)
            
            # Calcular fecha de negocio anterior (simple: fin de semana salta a viernes)
            def get_prev_biz_date(dt: datetime) -> datetime:
                dow = dt.weekday()  # 0=Lun ... 6=Dom
                if dow == 0:  # Lunes → viernes
                    return (dt - timedelta(days=3)).date()
                elif dow == 6:  # Domingo → viernes
                    return (dt - timedelta(days=2)).date()
                else:
                    return (dt - timedelta(days=1)).date()
            prev_biz = get_prev_biz_date(now)
            
            ratios_rueda = [r for t, r in data_points if t >= rueda_cutoff]
            ratios_prev_biz = [r for t, r in data_points if t.date() == prev_biz]
            ratios_semana = [r for t, r in data_points if t >= semana_cutoff]
            ratios_mes = [r for t, r in data_points if t >= mes_cutoff]
            
            promedio_rueda = sum(ratios_rueda) / len(ratios_rueda) if ratios_rueda else None
            promedio_prev_biz = sum(ratios_prev_biz) / len(ratios_prev_biz) if ratios_prev_biz else None
            promedio_semana = sum(ratios_semana) / len(ratios_semana) if ratios_semana else None
            promedio_mes = sum(ratios_mes) / len(ratios_mes) if ratios_mes else None
            
            minimo_mes = min(ratios_mes) if ratios_mes else None
            maximo_mes = max(ratios_mes) if ratios_mes else None
            
            # Calcular diferencias porcentuales
            def calc_diff_pct(current, avg):
                if not avg or avg == 0:
                    return None
                return round(((current - avg) / avg) * 100, 2)
            
            results.append({
                "par": f"{base}-{quote}",
                "ultimo_ratio_operado": round(ultimo_ratio, 5),
                "promedio_rueda": round(promedio_rueda, 5) if promedio_rueda else None,
                "dif_rueda_pct": calc_diff_pct(ultimo_ratio, promedio_rueda),
                "promedio_dia_anterior": round(promedio_prev_biz, 5) if promedio_prev_biz else None,
                "dif_dia_anterior_pct": calc_diff_pct(ultimo_ratio, promedio_prev_biz),
                "promedio_1semana": round(promedio_semana, 5) if promedio_semana else None,
                "dif_1semana_pct": calc_diff_pct(ultimo_ratio, promedio_semana),
                "promedio_1mes": round(promedio_mes, 5) if promedio_mes else None,
                "dif_1mes_pct": calc_diff_pct(ultimo_ratio, promedio_mes),
                "minimo_mensual": round(minimo_mes, 5) if minimo_mes else None,
                "dif_minimo_pct": calc_diff_pct(ultimo_ratio, minimo_mes),
                "maximo_mensual": round(maximo_mes, 5) if maximo_mes else None,
                "dif_maximo_pct": calc_diff_pct(ultimo_ratio, maximo_mes)
            })
        
        elapsed = (time.time() - start) * 1000
        
        return {
            "status": "success",
            "data": sorted(results, key=lambda x: x["par"]),
            "count": len(results),
            "query_time_ms": round(elapsed, 2),
            "method": "python_processing",
            "freshness": "real-time"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "method": "python_processing"
        }


# =====================================================================
# ENDPOINT RECOMENDADO (AUTO-SELECCIONA LA MEJOR ESTRATEGIA)
# =====================================================================

@router.get("/ratios/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """
    Endpoint principal del dashboard.
    Intenta usar el método más rápido disponible.
    """
    # Intentar método 1: Vista materializada
    try:
        result = await get_dashboard_fast()
        if result["status"] == "success":
            return result
    except Exception:
        pass
    
    # Fallback a método 2: Función PostgreSQL
    try:
        result = await get_dashboard_balanced()
        if result["status"] == "success":
            return result
    except Exception:
        pass
    
    # Último recurso: Python puro
    return await get_dashboard_flexible()


# =====================================================================
# WORKER PARA REFRESH DE VISTA MATERIALIZADA
# =====================================================================

import threading
import time as time_module

_refresh_worker_thread = None
_refresh_stop_event = threading.Event()

def _is_market_hours():
    """
    Verifica si estamos en horario de mercado.
    
    Lee la configuración desde dashboard_config.py
    
    Returns:
        bool: True si estamos en horario de mercado
    """
    try:
        from dashboard_config import (
            DIAS_HABILES, 
            HORA_INICIO, 
            MINUTO_INICIO, 
            HORA_FIN, 
            MINUTO_FIN,
            FERIADOS
        )
    except ImportError:
        # Valores por defecto si no existe el archivo de config
        DIAS_HABILES = [0, 1, 2, 3, 4]  # Lun-Vie
        HORA_INICIO = 10
        MINUTO_INICIO = 0
        HORA_FIN = 17
        MINUTO_FIN = 0
        FERIADOS = []
    
    now = datetime.now()
    
    # Verificar si es feriado
    fecha_hoy = now.strftime("%Y-%m-%d")
    if fecha_hoy in FERIADOS:
        return False
    
    # Verificar día de la semana (0=Lunes, 6=Domingo)
    if now.weekday() not in DIAS_HABILES:
        return False
    
    # Verificar horario (formato 24h)
    hora_actual = now.hour * 60 + now.minute
    hora_inicio_min = HORA_INICIO * 60 + MINUTO_INICIO
    hora_fin_min = HORA_FIN * 60 + MINUTO_FIN
    
    return hora_inicio_min <= hora_actual < hora_fin_min

def _refresh_worker_loop():
    """Worker que refresca la vista materializada cada 10 segundos."""
    print("[dashboard_refresh] Worker iniciado - refresh cada 10 segundos")
    
    while not _refresh_stop_event.is_set():
        try:
            # Verificar si estamos en horario de mercado
            if _is_market_hours():
                # Intentar refrescar la vista
                success = refresh_materialized_view()
                if success:
                    print(f"[dashboard_refresh] Vista actualizada a las {datetime.now().strftime('%H:%M:%S')}")
                else:
                    print("[dashboard_refresh] Error al actualizar vista")
            else:
                # Fuera de horario, solo mostrar cada 5 minutos para no llenar logs
                now = datetime.now()
                if now.second < 10:  # Solo en los primeros 10 segundos de cada minuto
                    print(f"[dashboard_refresh] Fuera de horario de mercado - {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[dashboard_refresh] Excepción: {e}")
        
        # Esperar 10 segundos
        _refresh_stop_event.wait(10)
    
    print("[dashboard_refresh] Worker detenido")

def start_refresh_worker():
    """Inicia el worker de refresh en background."""
    global _refresh_worker_thread
    
    if _refresh_worker_thread and _refresh_worker_thread.is_alive():
        print("[dashboard_refresh] Worker ya está corriendo")
        return
    
    _refresh_stop_event.clear()
    _refresh_worker_thread = threading.Thread(target=_refresh_worker_loop, daemon=True)
    _refresh_worker_thread.start()
    print("[dashboard_refresh] Worker iniciado")

def stop_refresh_worker():
    """Detiene el worker de refresh."""
    _refresh_stop_event.set()
    if _refresh_worker_thread:
        _refresh_worker_thread.join(timeout=5)
    print("[dashboard_refresh] Worker detenido")


# =====================================================================
# EJEMPLO DE USO EN main.py
# =====================================================================

"""
# En tu main.py, agregar:

from dashboard_ratios_api import router as dashboard_router, start_refresh_worker

app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])

@app.on_event("startup")
async def startup():
    # Iniciar el worker de refresh (solo si usas vista materializada)
    start_refresh_worker()

# Luego puedes acceder a:
# GET /api/ratios/dashboard           -> Auto-selecciona mejor método
# GET /api/ratios/dashboard/fast      -> Vista materializada
# GET /api/ratios/dashboard/balanced  -> Función PostgreSQL
# GET /api/ratios/dashboard/flexible  -> Python puro
"""

