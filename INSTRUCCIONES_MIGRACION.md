# Instrucciones para Migración de Base de Datos

## 📋 Resumen
Se deben agregar 3 nuevas columnas a la tabla `terminal_ratios_history` en Supabase.

## 🎯 Columnas a Agregar

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `last_price_base` | DOUBLE PRECISION | YES | Último valor operado del instrumento base |
| `last_price_quote` | DOUBLE PRECISION | YES | Último valor operado del instrumento quote |
| `last_ratio` | DOUBLE PRECISION | YES | Ratio calculado: last_price_base / last_price_quote |

## 🚀 Métodos de Migración

### Método 1: Migración Completa (Recomendado)

**Archivo:** `migration_add_last_fields.sql`

Este archivo incluye:
- ✅ Creación de columnas con `IF NOT EXISTS` (seguro para re-ejecutar)
- ✅ Comentarios descriptivos en cada columna
- ✅ Índices opcionales (comentados, descomentar si se necesitan)
- ✅ Consultas de verificación
- ✅ Script de rollback (por si necesitas revertir)

**Pasos:**
1. Ir a Supabase Dashboard
2. Abrir **SQL Editor**
3. Copiar y pegar el contenido de `migration_add_last_fields.sql`
4. Ejecutar el script completo

### Método 2: Migración Simple (Rápida)

**Archivo:** `migration_simple.sql`

Este archivo solo incluye lo esencial:
- ✅ Creación de las 3 columnas
- ✅ Consulta de verificación

**Pasos:**
1. Ir a Supabase Dashboard
2. Abrir **SQL Editor**
3. Copiar y pegar el contenido de `migration_simple.sql`
4. Ejecutar el script

### Método 3: Desde la UI de Supabase

**Pasos:**
1. Ir a Supabase Dashboard
2. Navegar a **Table Editor**
3. Seleccionar la tabla `terminal_ratios_history`
4. Hacer clic en el botón **"+ New column"**
5. Agregar cada columna con estas configuraciones:

   **Columna 1:**
   - Name: `last_price_base`
   - Type: `float8` (DOUBLE PRECISION)
   - Default value: (dejar vacío)
   - ✅ Nullable

   **Columna 2:**
   - Name: `last_price_quote`
   - Type: `float8` (DOUBLE PRECISION)
   - Default value: (dejar vacío)
   - ✅ Nullable

   **Columna 3:**
   - Name: `last_ratio`
   - Type: `float8` (DOUBLE PRECISION)
   - Default value: (dejar vacío)
   - ✅ Nullable

## ✅ Verificación Post-Migración

### 1. Verificar estructura de columnas

```sql
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'terminal_ratios_history'
    AND column_name IN ('last_price_base', 'last_price_quote', 'last_ratio')
ORDER BY column_name;
```

**Resultado esperado:**
```
column_name        | data_type         | is_nullable
-------------------+-------------------+-------------
last_price_base    | double precision  | YES
last_price_quote   | double precision  | YES
last_ratio         | double precision  | YES
```

### 2. Verificar que el sistema guarde datos

Después de ejecutar el `ratios_worker` por unos minutos:

```sql
SELECT 
    base_symbol,
    quote_symbol,
    asof,
    last_price_base,
    last_price_quote,
    last_ratio,
    mid_ratio
FROM terminal_ratios_history
WHERE last_ratio IS NOT NULL
ORDER BY asof DESC
LIMIT 5;
```

## 🔄 Rollback (Revertir Cambios)

Si necesitas deshacer la migración:

```sql
ALTER TABLE terminal_ratios_history 
DROP COLUMN IF EXISTS last_price_base,
DROP COLUMN IF EXISTS last_price_quote,
DROP COLUMN IF EXISTS last_ratio;
```

⚠️ **PRECAUCIÓN**: Esto eliminará las columnas y todos los datos almacenados en ellas.

## 📊 Índices Opcionales (Performance)

Si notas que las consultas por `last_ratio` son lentas, puedes agregar índices:

```sql
-- Índice simple por last_ratio
CREATE INDEX idx_terminal_ratios_last_ratio 
ON terminal_ratios_history(last_ratio);

-- Índice compuesto para búsquedas por símbolo y last_ratio
CREATE INDEX idx_terminal_ratios_symbols_last_ratio 
ON terminal_ratios_history(base_symbol, quote_symbol, last_ratio);

-- Índice para ordenamiento temporal con last_ratio
CREATE INDEX idx_terminal_ratios_asof_last_ratio 
ON terminal_ratios_history(asof DESC, last_ratio);
```

**Nota:** Los índices mejoran la velocidad de lectura pero ocupan espacio y ralentizan ligeramente las escrituras. Solo agregar si es necesario.

## 🎯 Consultas Útiles Post-Migración

### Ver registros más recientes con todos los ratios
```sql
SELECT 
    base_symbol || '/' || quote_symbol as par,
    asof::timestamp(0),
    ROUND(bid_ratio::numeric, 6) as bid_r,
    ROUND(ask_ratio::numeric, 6) as ask_r,
    ROUND(mid_ratio::numeric, 6) as mid_r,
    ROUND(last_ratio::numeric, 6) as last_r
FROM terminal_ratios_history
WHERE last_ratio IS NOT NULL
ORDER BY asof DESC
LIMIT 10;
```

### Comparar mid_ratio vs last_ratio
```sql
SELECT 
    base_symbol || '/' || quote_symbol as par,
    asof::timestamp(0),
    ROUND(mid_ratio::numeric, 6) as mid_r,
    ROUND(last_ratio::numeric, 6) as last_r,
    ROUND((last_ratio - mid_ratio)::numeric, 6) as diferencia,
    ROUND((((last_ratio - mid_ratio) / mid_ratio) * 100)::numeric, 3) || '%' as diferencia_pct
FROM terminal_ratios_history
WHERE last_ratio IS NOT NULL 
    AND mid_ratio IS NOT NULL
    AND asof > NOW() - INTERVAL '1 hour'
ORDER BY asof DESC
LIMIT 20;
```

### Estadísticas por par
```sql
SELECT 
    base_symbol || '/' || quote_symbol as par,
    COUNT(*) as registros,
    COUNT(last_ratio) as con_last_ratio,
    ROUND(AVG(last_ratio)::numeric, 6) as avg_last_ratio,
    ROUND(MIN(last_ratio)::numeric, 6) as min_last_ratio,
    ROUND(MAX(last_ratio)::numeric, 6) as max_last_ratio
FROM terminal_ratios_history
WHERE asof > NOW() - INTERVAL '1 day'
GROUP BY base_symbol, quote_symbol
ORDER BY par;
```

## 📝 Notas Importantes

1. **Seguridad**: Los scripts usan `IF NOT EXISTS` para evitar errores si las columnas ya existen.

2. **Nullable**: Las columnas son nullable porque pueden no tener valor si no hay datos de `last` disponibles.

3. **Compatibilidad**: Los registros antiguos tendrán `NULL` en estos campos, lo cual es esperado.

4. **Performance**: No debería haber impacto significativo en el rendimiento. Las escrituras seguirán siendo rápidas.

5. **Backup**: Supabase hace backups automáticos, pero si tienes datos críticos, considera hacer un backup manual antes de la migración.

## 🆘 Troubleshooting

### Error: "column already exists"
**Solución**: Las columnas ya fueron agregadas. Ejecutar la consulta de verificación para confirmar.

### Error: "permission denied"
**Solución**: Asegurarte de tener permisos de administrador en Supabase.

### No se están guardando datos en los nuevos campos
**Solución**: 
1. Verificar que el código en `ratios_worker.py` esté actualizado
2. Reiniciar el servicio/worker
3. Verificar logs para errores

### Las columnas aparecen pero siempre están en NULL
**Solución**: 
1. Verificar que haya datos de `last` en el `quotes_cache`
2. Verificar logs del worker para errores
3. Esperar al menos un ciclo completo del worker (10 segundos)

---

**Última actualización:** 2025-09-30  
**Autor:** Luis Eiman  
**Contacto:** [tu contacto]


