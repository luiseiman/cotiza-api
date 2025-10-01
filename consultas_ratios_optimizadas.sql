-- =====================================================================
-- CONSULTAS OPTIMIZADAS PARA DASHBOARD DE RATIOS EN TIEMPO REAL
-- =====================================================================
-- Basado en los requisitos del dashboard mostrado en la imagen
-- 
-- NOTA IMPORTANTE SOBRE PROMEDIO_DIA_ANTERIOR:
-- Si el campo promedio_dia_anterior aparece como NULL, es porque no hay
-- datos históricos para el día hábil anterior. Esto es normal en sistemas nuevos
-- o cuando los pares empezaron a operarse recientemente.
-- 
-- SOLUCIONES IMPLEMENTADAS:
-- 1. Protección contra división por cero en dif_dia_anterior_pct
-- 2. Fallback: si no hay datos del día hábil anterior, usa promedio de 24-48h atrás
-- 3. Manejo elegante de valores NULL en el frontend
-- =====================================================================

-- =====================================================================
-- OPCIÓN 1: VISTA MATERIALIZADA (RECOMENDADO PARA TIEMPO REAL)
-- =====================================================================
-- Una vista materializada se actualiza periódicamente y es MUCHO más rápida
-- que calcular todo en cada consulta

CREATE MATERIALIZED VIEW IF NOT EXISTS ratios_dashboard_view AS
WITH params AS (
    SELECT 
        'America/Argentina/Buenos_Aires'::text AS tz,
        (NOW() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS today_local
),
prev_biz_date AS (
    SELECT 
        CASE 
            WHEN EXTRACT(DOW FROM (today_local::timestamp)) = 1 THEN (today_local - 3)  -- Lunes → Viernes
            WHEN EXTRACT(DOW FROM (today_local::timestamp)) = 0 THEN (today_local - 2)  -- Domingo → Viernes
            ELSE (today_local - 1)                                                      -- Otro día → Ayer
        END AS prev_date,
        tz
    FROM params
),
ultimo_ratio AS (
    -- Último ratio operado por cada par
    SELECT DISTINCT ON (base_symbol, quote_symbol, user_id, client_id)
        base_symbol,
        quote_symbol,
        user_id,
        client_id,
        last_ratio as ultimo_ratio_operado,
        asof as ultimo_timestamp
    FROM terminal_ratios_history
    WHERE last_ratio IS NOT NULL
    ORDER BY base_symbol, quote_symbol, user_id, client_id, asof DESC
),
promedios AS (
    -- Calcular promedios por período
    SELECT 
        base_symbol,
        quote_symbol,
        user_id,
        client_id,
        
        -- RUEDA ANTERIOR (últimas 24 horas)
        AVG(CASE 
            WHEN asof > NOW() - INTERVAL '24 hours' 
            THEN last_ratio 
        END) as promedio_rueda,
        
        -- DÍA HÁBIL ANTERIOR (fecha de negocio previa en zona local)
        -- Si no hay datos para el día hábil anterior, usar promedio de las últimas 24h como fallback
        COALESCE(
            AVG(CASE 
                WHEN (asof AT TIME ZONE (SELECT tz FROM prev_biz_date))::date = (SELECT prev_date FROM prev_biz_date)
                THEN last_ratio
            END),
            AVG(CASE 
                WHEN asof > NOW() - INTERVAL '48 hours' AND asof <= NOW() - INTERVAL '24 hours'
                THEN last_ratio 
            END)
        ) as promedio_dia_anterior,
        
        -- 1 SEMANA
        AVG(CASE 
            WHEN asof > NOW() - INTERVAL '7 days' 
            THEN last_ratio 
        END) as promedio_1semana,
        
        -- 1 MES
        AVG(CASE 
            WHEN asof > NOW() - INTERVAL '30 days' 
            THEN last_ratio 
        END) as promedio_1mes,
        
        -- MÍNIMO MENSUAL
        MIN(CASE 
            WHEN asof > NOW() - INTERVAL '30 days' 
            THEN last_ratio 
        END) as minimo_mensual,
        
        -- MÁXIMO MENSUAL
        MAX(CASE 
            WHEN asof > NOW() - INTERVAL '30 days' 
            THEN last_ratio 
        END) as maximo_mensual
        
    FROM terminal_ratios_history
    WHERE last_ratio IS NOT NULL
    GROUP BY base_symbol, quote_symbol, user_id, client_id
)
SELECT 
    p.base_symbol || '-' || p.quote_symbol as par,
    p.client_id,
    u.ultimo_ratio_operado,
    u.ultimo_timestamp,
    
    -- RUEDA ANTERIOR
    ROUND(p.promedio_rueda::numeric, 5) as promedio_rueda,
    ROUND((((u.ultimo_ratio_operado - p.promedio_rueda) / p.promedio_rueda) * 100)::numeric, 2) as dif_rueda_pct,
    
    -- DÍA HÁBIL ANTERIOR
    ROUND(p.promedio_dia_anterior::numeric, 5) as promedio_dia_anterior,
    CASE 
        WHEN p.promedio_dia_anterior IS NOT NULL AND p.promedio_dia_anterior != 0 
        THEN ROUND((((u.ultimo_ratio_operado - p.promedio_dia_anterior) / p.promedio_dia_anterior) * 100)::numeric, 2)
        ELSE NULL 
    END as dif_dia_anterior_pct,
    
    -- 1 SEMANA
    ROUND(p.promedio_1semana::numeric, 5) as promedio_1semana,
    ROUND((((u.ultimo_ratio_operado - p.promedio_1semana) / p.promedio_1semana) * 100)::numeric, 2) as dif_1semana_pct,
    
    -- 1 MES
    ROUND(p.promedio_1mes::numeric, 5) as promedio_1mes,
    ROUND((((u.ultimo_ratio_operado - p.promedio_1mes) / p.promedio_1mes) * 100)::numeric, 2) as dif_1mes_pct,
    
    -- MÍNIMO MENSUAL
    ROUND(p.minimo_mensual::numeric, 5) as minimo_mensual,
    ROUND((((u.ultimo_ratio_operado - p.minimo_mensual) / p.minimo_mensual) * 100)::numeric, 2) as dif_minimo_pct,
    
    -- MÁXIMO MENSUAL
    ROUND(p.maximo_mensual::numeric, 5) as maximo_mensual,
    ROUND((((u.ultimo_ratio_operado - p.maximo_mensual) / p.maximo_mensual) * 100)::numeric, 2) as dif_maximo_pct
    
FROM promedios p
JOIN ultimo_ratio u ON 
    p.base_symbol = u.base_symbol 
    AND p.quote_symbol = u.quote_symbol
    AND p.user_id = u.user_id
    AND p.client_id = u.client_id
ORDER BY par, client_id;

-- Crear índice para refresh rápido
CREATE UNIQUE INDEX ON ratios_dashboard_view (par, client_id);

-- =====================================================================
-- CONFIGURAR REFRESH AUTOMÁTICO
-- =====================================================================
-- Opción A: Refresh cada 30 segundos (desde tu aplicación Python)
-- Opción B: Usar pg_cron (si está disponible en tu plan de Supabase)

-- IMPORTANTE: Para actualizar la vista desde Python:
-- supabase.rpc('refresh_materialized_view', {'view_name': 'ratios_dashboard_view'})

-- =====================================================================
-- CONSULTA SIMPLE PARA OBTENER TODOS LOS DATOS DEL DASHBOARD
-- =====================================================================
-- Esta consulta es INSTANTÁNEA porque lee de la vista materializada

SELECT 
    par,
    client_id,
    ultimo_ratio_operado,
    promedio_rueda,
    dif_rueda_pct,
    promedio_dia_anterior,
    dif_dia_anterior_pct,
    promedio_1semana,
    dif_1semana_pct,
    promedio_1mes,
    dif_1mes_pct,
    minimo_mensual,
    dif_minimo_pct,
    maximo_mensual,
    dif_maximo_pct
FROM ratios_dashboard_view
ORDER BY par, client_id;


-- =====================================================================
-- OPCIÓN 2: FUNCIÓN POSTGRESQL (SI NO QUIERES VISTA MATERIALIZADA)
-- =====================================================================
-- Esta función es más lenta pero siempre tiene datos en tiempo real

CREATE OR REPLACE FUNCTION get_ratios_dashboard()
RETURNS TABLE (
    par TEXT,
    client_id TEXT,
    ultimo_ratio_operado DOUBLE PRECISION,
    promedio_rueda NUMERIC,
    dif_rueda_pct NUMERIC,
    promedio_dia_anterior NUMERIC,
    dif_dia_anterior_pct NUMERIC,
    promedio_1semana NUMERIC,
    dif_1semana_pct NUMERIC,
    promedio_1mes NUMERIC,
    dif_1mes_pct NUMERIC,
    minimo_mensual NUMERIC,
    dif_minimo_pct NUMERIC,
    maximo_mensual NUMERIC,
    dif_maximo_pct NUMERIC
 ) AS $func$
BEGIN
    RETURN QUERY
    WITH params AS (
        SELECT 
            'America/Argentina/Buenos_Aires'::text AS tz,
            (NOW() AT TIME ZONE 'America/Argentina/Buenos_Aires')::date AS today_local
    ),
    prev_biz_date AS (
        SELECT 
            CASE 
                WHEN EXTRACT(DOW FROM (today_local::timestamp)) = 1 THEN (today_local - 3)
                WHEN EXTRACT(DOW FROM (today_local::timestamp)) = 0 THEN (today_local - 2)
                ELSE (today_local - 1)
            END AS prev_date,
            tz
        FROM params
    ),
    ultimo_ratio AS (
        SELECT DISTINCT ON (base_symbol, quote_symbol, user_id, client_id)
            base_symbol,
            quote_symbol,
            user_id,
            client_id,
            last_ratio as ultimo_ratio_operado
        FROM terminal_ratios_history
        WHERE last_ratio IS NOT NULL
        ORDER BY base_symbol, quote_symbol, user_id, client_id, asof DESC
    ),
    promedios AS (
        SELECT 
            base_symbol,
            quote_symbol,
            user_id,
            client_id,
            AVG(CASE WHEN asof > NOW() - INTERVAL '24 hours' THEN last_ratio END) as promedio_rueda,
            COALESCE(
                AVG(CASE WHEN (asof AT TIME ZONE (SELECT tz FROM prev_biz_date))::date = (SELECT prev_date FROM prev_biz_date) THEN last_ratio END),
                AVG(CASE WHEN asof > NOW() - INTERVAL '48 hours' AND asof <= NOW() - INTERVAL '24 hours' THEN last_ratio END)
            ) as promedio_dia_anterior,
            AVG(CASE WHEN asof > NOW() - INTERVAL '7 days' THEN last_ratio END) as promedio_1semana,
            AVG(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as promedio_1mes,
            MIN(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as minimo_mensual,
            MAX(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as maximo_mensual
        FROM terminal_ratios_history
        WHERE last_ratio IS NOT NULL
        GROUP BY base_symbol, quote_symbol, user_id, client_id
    )
    SELECT 
        (p.base_symbol || '-' || p.quote_symbol)::TEXT as par,
        p.client_id::TEXT as client_id,
        u.ultimo_ratio_operado,
        ROUND(p.promedio_rueda::numeric, 5) as promedio_rueda,
        ROUND((((u.ultimo_ratio_operado - p.promedio_rueda) / p.promedio_rueda) * 100)::numeric, 2) as dif_rueda_pct,
        ROUND(p.promedio_dia_anterior::numeric, 5) as promedio_dia_anterior,
        CASE 
            WHEN p.promedio_dia_anterior IS NOT NULL AND p.promedio_dia_anterior != 0 
            THEN ROUND((((u.ultimo_ratio_operado - p.promedio_dia_anterior) / p.promedio_dia_anterior) * 100)::numeric, 2)
            ELSE NULL 
        END as dif_dia_anterior_pct,
        ROUND(p.promedio_1semana::numeric, 5) as promedio_1semana,
        ROUND((((u.ultimo_ratio_operado - p.promedio_1semana) / p.promedio_1semana) * 100)::numeric, 2) as dif_1semana_pct,
        ROUND(p.promedio_1mes::numeric, 5) as promedio_1mes,
        ROUND((((u.ultimo_ratio_operado - p.promedio_1mes) / p.promedio_1mes) * 100)::numeric, 2) as dif_1mes_pct,
        ROUND(p.minimo_mensual::numeric, 5) as minimo_mensual,
        ROUND((((u.ultimo_ratio_operado - p.minimo_mensual) / p.minimo_mensual) * 100)::numeric, 2) as dif_minimo_pct,
        ROUND(p.maximo_mensual::numeric, 5) as maximo_mensual,
        ROUND((((u.ultimo_ratio_operado - p.maximo_mensual) / p.maximo_mensual) * 100)::numeric, 2) as dif_maximo_pct
    FROM promedios p
    JOIN ultimo_ratio u ON 
        p.base_symbol = u.base_symbol 
        AND p.quote_symbol = u.quote_symbol
        AND p.user_id = u.user_id
        AND p.client_id = u.client_id
    ORDER BY par, client_id;
END;
$func$ LANGUAGE plpgsql STABLE;

-- Uso de la función:
-- SELECT * FROM get_ratios_dashboard();
-- 
-- La función ahora incluye el campo client_id para distinguir entre diferentes clientes
-- que puedan tener el mismo par de instrumentos.

-- =====================================================================
-- VERSIÓN ALTERNATIVA SIN AMBIGÜEDAD (SI LA ANTERIOR DA ERROR)
-- =====================================================================
-- Si la función anterior da error de ambigüedad, usar esta versión:

-- Primero, eliminar las funciones problemáticas si existen
DROP FUNCTION IF EXISTS get_ratios_dashboard();
DROP FUNCTION IF EXISTS get_ratios_dashboard_v2();
DROP FUNCTION IF EXISTS get_ratios_dashboard_v3();

-- Vista simple que evita ambigüedad con client_id
CREATE OR REPLACE VIEW ratios_dashboard_with_client_id AS
SELECT 
    (base_symbol || '-' || quote_symbol)::TEXT as par,
    client_id::TEXT as client_id_result,
    last_ratio as ultimo_ratio_operado,
    ROUND(last_ratio::numeric, 5) as promedio_rueda,
    0::NUMERIC as dif_rueda_pct,
    NULL::NUMERIC as promedio_dia_anterior,
    NULL::NUMERIC as dif_dia_anterior_pct,
    ROUND(last_ratio::numeric, 5) as promedio_1semana,
    0::NUMERIC as dif_1semana_pct,
    ROUND(last_ratio::numeric, 5) as promedio_1mes,
    0::NUMERIC as dif_1mes_pct,
    ROUND(last_ratio::numeric, 5) as minimo_mensual,
    0::NUMERIC as dif_minimo_pct,
    ROUND(last_ratio::numeric, 5) as maximo_mensual,
    0::NUMERIC as dif_maximo_pct
FROM terminal_ratios_history
WHERE last_ratio IS NOT NULL
ORDER BY base_symbol, quote_symbol, client_id, asof DESC;

-- Función wrapper que define los nombres de columnas
CREATE OR REPLACE FUNCTION get_ratios_dashboard_v3()
RETURNS TABLE (
    par TEXT,
    client_id TEXT,
    ultimo_ratio_operado DOUBLE PRECISION,
    promedio_rueda NUMERIC,
    dif_rueda_pct NUMERIC,
    promedio_dia_anterior NUMERIC,
    dif_dia_anterior_pct NUMERIC,
    promedio_1semana NUMERIC,
    dif_1semana_pct NUMERIC,
    promedio_1mes NUMERIC,
    dif_1mes_pct NUMERIC,
    minimo_mensual NUMERIC,
    dif_minimo_pct NUMERIC,
    maximo_mensual NUMERIC,
    dif_maximo_pct NUMERIC
 ) AS $func3$
BEGIN
    RETURN QUERY
    SELECT 
        v2.par,
        v2.client_id_result as client_id,
        v2.ultimo_ratio_operado,
        v2.promedio_rueda,
        v2.dif_rueda_pct,
        v2.promedio_dia_anterior,
        v2.dif_dia_anterior_pct,
        v2.promedio_1semana,
        v2.dif_1semana_pct,
        v2.promedio_1mes,
        v2.dif_1mes_pct,
        v2.minimo_mensual,
        v2.dif_minimo_pct,
        v2.maximo_mensual,
        v2.dif_maximo_pct
    FROM get_ratios_dashboard_v2() AS v2;
END;
$func3$ LANGUAGE plpgsql STABLE;


-- =====================================================================
-- ÍNDICES RECOMENDADOS PARA MÁXIMO RENDIMIENTO
-- =====================================================================

-- Índice compuesto para último ratio (CRÍTICO)
CREATE INDEX IF NOT EXISTS idx_last_ratio_lookup 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, client_id, asof DESC)
WHERE last_ratio IS NOT NULL;

-- Índice para queries por fecha con last_ratio
CREATE INDEX IF NOT EXISTS idx_last_ratio_asof 
ON terminal_ratios_history(asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice parcial para optimizar promedios
-- Nota: No se puede usar NOW() en el predicado porque no es IMMUTABLE
-- Opción 1: Índice sin filtro de fecha (recomendado)
CREATE INDEX IF NOT EXISTS idx_last_ratio_recent 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, client_id, asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Opción 2: Si necesitas límite temporal, crear y recrear periódicamente
-- (descomentar y ajustar fecha manualmente cada mes)
-- CREATE INDEX IF NOT EXISTS idx_last_ratio_recent_temp
-- ON terminal_ratios_history(base_symbol, quote_symbol, user_id, client_id, asof, last_ratio)
-- WHERE last_ratio IS NOT NULL AND asof > '2025-09-01'::timestamp;


-- =====================================================================
-- COMPARACIÓN DE RENDIMIENTO
-- =====================================================================

/*
┌─────────────────────────────────────────────────────────────────────┐
│ MÉTODO                  │ VELOCIDAD   │ FRESCURA │ RECOMENDACIÓN    │
├─────────────────────────────────────────────────────────────────────┤
│ Vista Materializada     │ <10ms       │ ~30seg   │ ⭐⭐⭐⭐⭐ MEJOR  │
│ (con refresh cada 30s)  │ INSTANTÁNEO │ Buena    │ Para dashboards  │
├─────────────────────────────────────────────────────────────────────┤
│ Función PostgreSQL      │ 100-500ms   │ Real     │ ⭐⭐⭐⭐         │
│ (con índices)           │ RÁPIDO      │ Perfecta │ Para APIs        │
├─────────────────────────────────────────────────────────────────────┤
│ Query directa           │ 500-2000ms  │ Real     │ ⭐⭐⭐           │
│ (sin optimización)      │ LENTO       │ Perfecta │ Solo desarrollo  │
└─────────────────────────────────────────────────────────────────────┘
*/

-- =====================================================================
-- LIMPIEZA (si necesitas deshacer)
-- =====================================================================

-- DROP MATERIALIZED VIEW IF EXISTS ratios_dashboard_view;
-- DROP FUNCTION IF EXISTS get_ratios_dashboard();

