-- =====================================================================
-- MIGRACIÓN: Agregar campos de último valor operado a terminal_ratios_history
-- =====================================================================
-- Descripción: Agrega 3 nuevos campos para almacenar los últimos valores
--              operados de cada instrumento y el ratio calculado desde ellos.
-- Fecha: 2025-09-30
-- Versión: 1.0
-- =====================================================================

-- Agregar campo para el último precio del instrumento base
ALTER TABLE terminal_ratios_history 
ADD COLUMN IF NOT EXISTS last_price_base DOUBLE PRECISION;

-- Agregar campo para el último precio del instrumento quote
ALTER TABLE terminal_ratios_history 
ADD COLUMN IF NOT EXISTS last_price_quote DOUBLE PRECISION;

-- Agregar campo para el ratio calculado desde los últimos valores operados
ALTER TABLE terminal_ratios_history 
ADD COLUMN IF NOT EXISTS last_ratio DOUBLE PRECISION;

-- =====================================================================
-- COMENTARIOS EN LAS COLUMNAS (para documentación en Supabase)
-- =====================================================================

COMMENT ON COLUMN terminal_ratios_history.last_price_base IS 
'Último valor operado del instrumento base (campo "last" del quotes_cache)';

COMMENT ON COLUMN terminal_ratios_history.last_price_quote IS 
'Último valor operado del instrumento quote (campo "last" del quotes_cache)';

COMMENT ON COLUMN terminal_ratios_history.last_ratio IS 
'Ratio calculado desde los últimos valores operados: last_price_base / last_price_quote. Representa el ratio basado en operaciones reales ejecutadas en el mercado.';

-- =====================================================================
-- ÍNDICES OPCIONALES (descomentar si se necesitan para mejorar performance)
-- =====================================================================

-- Índice para búsquedas por last_ratio (útil si se hacen queries frecuentes)
-- CREATE INDEX IF NOT EXISTS idx_terminal_ratios_last_ratio 
-- ON terminal_ratios_history(last_ratio);

-- Índice compuesto para búsquedas por símbolo y last_ratio
-- CREATE INDEX IF NOT EXISTS idx_terminal_ratios_symbols_last_ratio 
-- ON terminal_ratios_history(base_symbol, quote_symbol, last_ratio);

-- Índice para ordenamiento temporal con last_ratio
-- CREATE INDEX IF NOT EXISTS idx_terminal_ratios_asof_last_ratio 
-- ON terminal_ratios_history(asof DESC, last_ratio);

-- =====================================================================
-- VERIFICACIÓN
-- =====================================================================

-- Verificar que las columnas se agregaron correctamente
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'terminal_ratios_history'
    AND column_name IN ('last_price_base', 'last_price_quote', 'last_ratio')
ORDER BY column_name;

-- =====================================================================
-- CONSULTA DE PRUEBA (después de que el sistema guarde datos)
-- =====================================================================

-- Verificar registros recientes con los nuevos campos
-- SELECT 
--     base_symbol,
--     quote_symbol,
--     asof,
--     bid_ratio,
--     ask_ratio,
--     mid_ratio,
--     last_ratio,
--     last_price_base,
--     last_price_quote
-- FROM terminal_ratios_history
-- WHERE last_ratio IS NOT NULL
-- ORDER BY asof DESC
-- LIMIT 10;

-- =====================================================================
-- ROLLBACK (solo si es necesario deshacer los cambios)
-- =====================================================================

-- PRECAUCIÓN: Solo ejecutar si necesitas revertir la migración
-- ALTER TABLE terminal_ratios_history DROP COLUMN IF EXISTS last_price_base;
-- ALTER TABLE terminal_ratios_history DROP COLUMN IF EXISTS last_price_quote;
-- ALTER TABLE terminal_ratios_history DROP COLUMN IF EXISTS last_ratio;

-- =====================================================================
-- FIN DE LA MIGRACIÓN
-- =====================================================================


