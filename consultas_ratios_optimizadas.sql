-- =====================================================================
-- CONSULTAS OPTIMIZADAS PARA DASHBOARD DE RATIOS EN TIEMPO REAL
-- =====================================================================
-- Basado en los requisitos del dashboard mostrado en la imagen
-- =====================================================================

-- =====================================================================
-- OPCIÓN 1: VISTA MATERIALIZADA (RECOMENDADO PARA TIEMPO REAL)
-- =====================================================================
-- Una vista materializada se actualiza periódicamente y es MUCHO más rápida
-- que calcular todo en cada consulta

CREATE MATERIALIZED VIEW IF NOT EXISTS ratios_dashboard_view AS
WITH ultimo_ratio AS (
    -- Último ratio operado por cada par
    SELECT DISTINCT ON (base_symbol, quote_symbol, user_id)
        base_symbol,
        quote_symbol,
        user_id,
        last_ratio as ultimo_ratio_operado,
        asof as ultimo_timestamp
    FROM terminal_ratios_history
    WHERE last_ratio IS NOT NULL
    ORDER BY base_symbol, quote_symbol, user_id, asof DESC
),
promedios AS (
    -- Calcular promedios por período
    SELECT 
        base_symbol,
        quote_symbol,
        user_id,
        
        -- RUEDA ANTERIOR (últimas 24 horas)
        AVG(CASE 
            WHEN asof > NOW() - INTERVAL '24 hours' 
            THEN last_ratio 
        END) as promedio_rueda,
        
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
    GROUP BY base_symbol, quote_symbol, user_id
)
SELECT 
    p.base_symbol || '-' || p.quote_symbol as par,
    u.ultimo_ratio_operado,
    u.ultimo_timestamp,
    
    -- RUEDA ANTERIOR
    ROUND(p.promedio_rueda::numeric, 5) as promedio_rueda,
    ROUND((((u.ultimo_ratio_operado - p.promedio_rueda) / p.promedio_rueda) * 100)::numeric, 2) as dif_rueda_pct,
    
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
ORDER BY par;

-- Crear índice para refresh rápido
CREATE UNIQUE INDEX ON ratios_dashboard_view (par);

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
    ultimo_ratio_operado,
    promedio_rueda,
    dif_rueda_pct,
    promedio_1semana,
    dif_1semana_pct,
    promedio_1mes,
    dif_1mes_pct,
    minimo_mensual,
    dif_minimo_pct,
    maximo_mensual,
    dif_maximo_pct
FROM ratios_dashboard_view
ORDER BY par;


-- =====================================================================
-- OPCIÓN 2: FUNCIÓN POSTGRESQL (SI NO QUIERES VISTA MATERIALIZADA)
-- =====================================================================
-- Esta función es más lenta pero siempre tiene datos en tiempo real

CREATE OR REPLACE FUNCTION get_ratios_dashboard()
RETURNS TABLE (
    par TEXT,
    ultimo_ratio_operado DOUBLE PRECISION,
    promedio_rueda NUMERIC,
    dif_rueda_pct NUMERIC,
    promedio_1semana NUMERIC,
    dif_1semana_pct NUMERIC,
    promedio_1mes NUMERIC,
    dif_1mes_pct NUMERIC,
    minimo_mensual NUMERIC,
    dif_minimo_pct NUMERIC,
    maximo_mensual NUMERIC,
    dif_maximo_pct NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH ultimo_ratio AS (
        SELECT DISTINCT ON (base_symbol, quote_symbol, user_id)
            base_symbol,
            quote_symbol,
            user_id,
            last_ratio as ultimo_ratio_operado
        FROM terminal_ratios_history
        WHERE last_ratio IS NOT NULL
        ORDER BY base_symbol, quote_symbol, user_id, asof DESC
    ),
    promedios AS (
        SELECT 
            base_symbol,
            quote_symbol,
            user_id,
            AVG(CASE WHEN asof > NOW() - INTERVAL '24 hours' THEN last_ratio END) as promedio_rueda,
            AVG(CASE WHEN asof > NOW() - INTERVAL '7 days' THEN last_ratio END) as promedio_1semana,
            AVG(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as promedio_1mes,
            MIN(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as minimo_mensual,
            MAX(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as maximo_mensual
        FROM terminal_ratios_history
        WHERE last_ratio IS NOT NULL
        GROUP BY base_symbol, quote_symbol, user_id
    )
    SELECT 
        (p.base_symbol || '-' || p.quote_symbol)::TEXT as par,
        u.ultimo_ratio_operado,
        ROUND(p.promedio_rueda::numeric, 5) as promedio_rueda,
        ROUND((((u.ultimo_ratio_operado - p.promedio_rueda) / p.promedio_rueda) * 100)::numeric, 2) as dif_rueda_pct,
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
    ORDER BY par;
END;
$$ LANGUAGE plpgsql STABLE;

-- Uso de la función:
-- SELECT * FROM get_ratios_dashboard();


-- =====================================================================
-- ÍNDICES RECOMENDADOS PARA MÁXIMO RENDIMIENTO
-- =====================================================================

-- Índice compuesto para último ratio (CRÍTICO)
CREATE INDEX IF NOT EXISTS idx_last_ratio_lookup 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC)
WHERE last_ratio IS NOT NULL;

-- Índice para queries por fecha con last_ratio
CREATE INDEX IF NOT EXISTS idx_last_ratio_asof 
ON terminal_ratios_history(asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice parcial para optimizar promedios
-- Nota: No se puede usar NOW() en el predicado porque no es IMMUTABLE
-- Opción 1: Índice sin filtro de fecha (recomendado)
CREATE INDEX IF NOT EXISTS idx_last_ratio_recent 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Opción 2: Si necesitas límite temporal, crear y recrear periódicamente
-- (descomentar y ajustar fecha manualmente cada mes)
-- CREATE INDEX IF NOT EXISTS idx_last_ratio_recent_temp
-- ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof, last_ratio)
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

