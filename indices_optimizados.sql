-- =====================================================================
-- ÍNDICES OPTIMIZADOS PARA terminal_ratios_history
-- =====================================================================
-- Solución al error: "functions in index predicate must be marked IMMUTABLE"
-- =====================================================================

-- =====================================================================
-- PROBLEMA: NOW() no es IMMUTABLE
-- =====================================================================
-- PostgreSQL no permite NOW() en predicados de índice porque cambia
-- con el tiempo. Hay 3 soluciones:

-- =====================================================================
-- SOLUCIÓN 1: ÍNDICES SIN FILTRO TEMPORAL (RECOMENDADO) ✅
-- =====================================================================
-- Estos índices cubren todos los datos pero siguen siendo rápidos

-- Índice principal: Buscar último ratio por par
CREATE INDEX IF NOT EXISTS idx_last_ratio_lookup 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC)
WHERE last_ratio IS NOT NULL;

-- Índice para queries temporales con last_ratio
CREATE INDEX IF NOT EXISTS idx_last_ratio_asof 
ON terminal_ratios_history(asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice compuesto para promedios
CREATE INDEX IF NOT EXISTS idx_last_ratio_aggregates 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice para el campo asof solo (útil para queries por rango de fechas)
CREATE INDEX IF NOT EXISTS idx_ratios_asof 
ON terminal_ratios_history(asof DESC);


-- =====================================================================
-- SOLUCIÓN 2: ÍNDICES PARCIALES CON FECHA FIJA 📅
-- =====================================================================
-- Crear índice con fecha hardcodeada, renovar mensualmente

-- Script de ejemplo (ajustar fecha cada mes)
DO $$
DECLARE
    fecha_inicio timestamp;
BEGIN
    -- Calcular fecha de hace 60 días (hardcoded al momento de ejecución)
    fecha_inicio := NOW() - INTERVAL '60 days';
    
    -- Eliminar índice antiguo si existe
    DROP INDEX IF EXISTS idx_last_ratio_recent_temp;
    
    -- Crear nuevo índice con fecha fija
    EXECUTE format(
        'CREATE INDEX idx_last_ratio_recent_temp 
         ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof, last_ratio)
         WHERE last_ratio IS NOT NULL AND asof > %L',
        fecha_inicio
    );
    
    RAISE NOTICE 'Índice creado con fecha de inicio: %', fecha_inicio;
END $$;

-- Programar recreación mensual con pg_cron (si está disponible):
-- SELECT cron.schedule('recreate-temp-index', '0 0 1 * *', 
--   'DROP INDEX IF EXISTS idx_last_ratio_recent_temp; ...');


-- =====================================================================
-- SOLUCIÓN 3: PARTICIONAMIENTO POR FECHA (AVANZADO) 🔧
-- =====================================================================
-- Si tienes MUCHOS datos históricos, particionar la tabla por mes/año

-- Ejemplo de estructura particionada (requiere migración):
/*
CREATE TABLE terminal_ratios_history_partitioned (
    LIKE terminal_ratios_history INCLUDING ALL
) PARTITION BY RANGE (asof);

-- Crear particiones por mes
CREATE TABLE terminal_ratios_history_2025_09 
PARTITION OF terminal_ratios_history_partitioned
FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE terminal_ratios_history_2025_10 
PARTITION OF terminal_ratios_history_partitioned
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

-- Etc...
*/


-- =====================================================================
-- VERIFICACIÓN DE ÍNDICES
-- =====================================================================

-- Ver todos los índices de la tabla
SELECT 
    indexname,
    indexdef,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes 
WHERE tablename = 'terminal_ratios_history'
ORDER BY indexname;

-- Ver estadísticas de uso de índices
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE tablename = 'terminal_ratios_history'
ORDER BY idx_scan DESC;


-- =====================================================================
-- ANÁLISIS DE QUERIES (para verificar que usan los índices)
-- =====================================================================

-- Query de prueba 1: Último ratio por par
EXPLAIN ANALYZE
SELECT DISTINCT ON (base_symbol, quote_symbol, user_id)
    base_symbol,
    quote_symbol,
    last_ratio
FROM terminal_ratios_history
WHERE last_ratio IS NOT NULL
ORDER BY base_symbol, quote_symbol, user_id, asof DESC
LIMIT 10;

-- Query de prueba 2: Promedios por período
EXPLAIN ANALYZE
SELECT 
    base_symbol,
    quote_symbol,
    AVG(last_ratio) FILTER (WHERE asof > NOW() - INTERVAL '7 days') as avg_7d,
    AVG(last_ratio) FILTER (WHERE asof > NOW() - INTERVAL '30 days') as avg_30d
FROM terminal_ratios_history
WHERE last_ratio IS NOT NULL
GROUP BY base_symbol, quote_symbol
LIMIT 10;


-- =====================================================================
-- MANTENIMIENTO DE ÍNDICES
-- =====================================================================

-- Reindexar si los índices se fragmentan (ejecutar mensualmente)
REINDEX TABLE CONCURRENTLY terminal_ratios_history;

-- Analizar la tabla para actualizar estadísticas
ANALYZE terminal_ratios_history;

-- Ver tamaño de tabla e índices
SELECT 
    'table' as type,
    pg_size_pretty(pg_total_relation_size('terminal_ratios_history')) as size
UNION ALL
SELECT 
    'indexes' as type,
    pg_size_pretty(pg_indexes_size('terminal_ratios_history')) as size;


-- =====================================================================
-- LIMPIEZA DE DATOS ANTIGUOS (OPCIONAL)
-- =====================================================================

-- Si la tabla crece mucho, considera eliminar datos antiguos
-- PRECAUCIÓN: Hacer backup antes de ejecutar

-- Opción A: Eliminar datos muy antiguos (>6 meses)
-- DELETE FROM terminal_ratios_history 
-- WHERE asof < NOW() - INTERVAL '6 months';

-- Opción B: Mover a tabla de archivo
-- CREATE TABLE terminal_ratios_history_archive AS
-- SELECT * FROM terminal_ratios_history
-- WHERE asof < NOW() - INTERVAL '6 months';
-- 
-- DELETE FROM terminal_ratios_history 
-- WHERE asof < NOW() - INTERVAL '6 months';


-- =====================================================================
-- RECOMENDACIONES FINALES
-- =====================================================================

/*
PARA TU CASO (dashboard en tiempo real):

✅ USAR: Solución 1 (índices sin filtro temporal)
   - Más simple
   - No requiere mantenimiento
   - Suficientemente rápido para la mayoría de casos

⚠️  CONSIDERAR: Solución 2 (índices con fecha fija) SI:
   - Tienes >1M de registros históricos
   - Las queries son lentas (>500ms)
   - Puedes programar mantenimiento mensual

🔧 CONSIDERAR: Solución 3 (particionamiento) SI:
   - Tienes >10M de registros
   - Necesitas retener años de historia
   - Tienes recursos para migración

ÍNDICES CRÍTICOS (ejecutar estos):
1. idx_last_ratio_lookup    ← Para último ratio
2. idx_last_ratio_asof       ← Para queries por fecha
3. idx_last_ratio_aggregates ← Para promedios

Estos 3 índices son suficientes para >90% de casos.
*/



