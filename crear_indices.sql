-- =====================================================================
-- SCRIPT SIMPLE: CREAR ÍNDICES PARA terminal_ratios_history
-- =====================================================================
-- Este script es SEGURO y NO dará errores
-- Ejecutar en Supabase SQL Editor
-- =====================================================================

-- Índice 1: Buscar último ratio por par (CRÍTICO)
CREATE INDEX IF NOT EXISTS idx_last_ratio_lookup 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC)
WHERE last_ratio IS NOT NULL;

-- Índice 2: Queries por fecha con last_ratio
CREATE INDEX IF NOT EXISTS idx_last_ratio_asof 
ON terminal_ratios_history(asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice 3: Promedios y agregaciones
CREATE INDEX IF NOT EXISTS idx_last_ratio_aggregates 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice 4: Queries por fecha (para rangos temporales)
CREATE INDEX IF NOT EXISTS idx_ratios_asof 
ON terminal_ratios_history(asof DESC);

-- =====================================================================
-- VERIFICACIÓN
-- =====================================================================

SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes 
WHERE tablename = 'terminal_ratios_history'
  AND indexname LIKE 'idx_%'
ORDER BY indexname;

-- =====================================================================
-- FIN
-- =====================================================================



