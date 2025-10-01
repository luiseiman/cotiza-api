-- =====================================================================
-- MIGRACIÓN SIMPLE: Agregar campos last a terminal_ratios_history
-- =====================================================================
-- Ejecutar en: SQL Editor de Supabase
-- =====================================================================

-- Agregar las 3 nuevas columnas
ALTER TABLE terminal_ratios_history 
ADD COLUMN IF NOT EXISTS last_price_base DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS last_price_quote DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS last_ratio DOUBLE PRECISION;

-- Verificar que se agregaron correctamente
SELECT column_name, data_type 
FROM information_schema.columns
WHERE table_name = 'terminal_ratios_history'
    AND column_name LIKE 'last%'
ORDER BY column_name;

