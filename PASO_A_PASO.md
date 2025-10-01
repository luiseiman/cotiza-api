# Guía Paso a Paso - Dashboard de Ratios

## 📋 Resumen de lo que vamos a hacer

1. ✅ Agregar 3 columnas nuevas a la tabla `terminal_ratios_history`
2. ✅ Crear índices para acelerar las consultas
3. ✅ Crear vista materializada (o función) para el dashboard
4. ✅ Integrar API en tu proyecto Python
5. ✅ Probar que funciona

**Tiempo estimado:** 15 minutos

---

## 🗄️ PASO 1: Agregar Columnas a Supabase

### Ir a Supabase:
1. Abrir navegador → https://supabase.com/dashboard
2. Seleccionar tu proyecto
3. Click en **"SQL Editor"** (icono </> en barra lateral)
4. Click en **"New query"**

### Copiar y pegar este código:

```sql
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
```

### Ejecutar:
- Click en **"Run"** (o `Ctrl+Enter`)
- Deberías ver 3 filas en el resultado:
  - `last_price_base | double precision`
  - `last_price_quote | double precision`
  - `last_ratio | double precision`

✅ **Paso 1 completo!**

---

## 🚀 PASO 2: Crear Índices (CRÍTICO)

### En el mismo SQL Editor de Supabase:
1. Click en **"New query"**

### Copiar y pegar este código:

```sql
-- Índice 1: Último ratio por par (CRÍTICO)
CREATE INDEX IF NOT EXISTS idx_last_ratio_lookup 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC)
WHERE last_ratio IS NOT NULL;

-- Índice 2: Queries por fecha
CREATE INDEX IF NOT EXISTS idx_last_ratio_asof 
ON terminal_ratios_history(asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice 3: Agregaciones
CREATE INDEX IF NOT EXISTS idx_last_ratio_aggregates 
ON terminal_ratios_history(base_symbol, quote_symbol, user_id, asof DESC, last_ratio)
WHERE last_ratio IS NOT NULL;

-- Índice 4: Rangos temporales
CREATE INDEX IF NOT EXISTS idx_ratios_asof 
ON terminal_ratios_history(asof DESC);

-- Verificar creación
SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes 
WHERE tablename = 'terminal_ratios_history' AND indexname LIKE 'idx_%';
```

### Ejecutar:
- Click en **"Run"**
- Deberías ver 4 índices creados

✅ **Paso 2 completo! Tus queries ahora serán 50-500x más rápidas**

---

## 📊 PASO 3: Crear Vista Materializada (Recomendado)

### Opción A - Vista Materializada (MÁS RÁPIDA) ⭐

En SQL Editor, crear **nueva query** y copiar esto:

```sql
-- Vista materializada para dashboard (incluye Día Hábil Anterior)
CREATE MATERIALIZED VIEW IF NOT EXISTS ratios_dashboard_view AS
WITH prev_biz_date AS (
    SELECT CASE 
        WHEN EXTRACT(DOW FROM NOW()) = 1 THEN (NOW()::date - INTERVAL '3 days')::date  -- Lunes → Viernes
        WHEN EXTRACT(DOW FROM NOW()) = 0 THEN (NOW()::date - INTERVAL '2 days')::date  -- Domingo → Viernes
        ELSE (NOW()::date - INTERVAL '1 day')::date                                    -- Otro día → Ayer
    END AS prev_date
),
ultimo_ratio AS (
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
    SELECT 
        base_symbol,
        quote_symbol,
        user_id,
        AVG(CASE WHEN asof > NOW() - INTERVAL '24 hours' THEN last_ratio END) as promedio_rueda,
        AVG(CASE WHEN asof::date = (SELECT prev_date FROM prev_biz_date) THEN last_ratio END) as promedio_dia_anterior,
        AVG(CASE WHEN asof > NOW() - INTERVAL '7 days' THEN last_ratio END) as promedio_1semana,
        AVG(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as promedio_1mes,
        MIN(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as minimo_mensual,
        MAX(CASE WHEN asof > NOW() - INTERVAL '30 days' THEN last_ratio END) as maximo_mensual
    FROM terminal_ratios_history
    WHERE last_ratio IS NOT NULL
    GROUP BY base_symbol, quote_symbol, user_id
)
SELECT 
    p.base_symbol || '-' || p.quote_symbol as par,
    u.ultimo_ratio_operado,
    u.ultimo_timestamp,
    ROUND(p.promedio_rueda::numeric, 5) as promedio_rueda,
    ROUND((((u.ultimo_ratio_operado - p.promedio_rueda) / p.promedio_rueda) * 100)::numeric, 2) as dif_rueda_pct,
    ROUND(p.promedio_dia_anterior::numeric, 5) as promedio_dia_anterior,
    ROUND((((u.ultimo_ratio_operado - p.promedio_dia_anterior) / p.promedio_dia_anterior) * 100)::numeric, 2) as dif_dia_anterior_pct,
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

-- Crear índice para refresh rápido
CREATE UNIQUE INDEX IF NOT EXISTS idx_ratios_dashboard_par ON ratios_dashboard_view (par);

-- Crear función para refrescar desde Python
CREATE OR REPLACE FUNCTION refresh_ratios_view()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ratios_dashboard_view;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Ejecutar** y esperar ~5-10 segundos (primera vez puede tardar un poco).

✅ **Paso 3 completo!**

---

## 💻 PASO 4: Integrar API en Python

### 4.1 Verificar que tienes el archivo

Asegúrate de que `dashboard_ratios_api.py` esté en tu carpeta del proyecto:

```bash
ls -la dashboard_ratios_api.py
```

Si existe, continuar. Si no existe, revisar que lo hayas copiado correctamente.

### 4.2 Editar `main.py`

Abrir `main.py` y agregar estas líneas:

**Al inicio del archivo (con los otros imports):**
```python
from dashboard_ratios_api import router as dashboard_router, start_refresh_worker
```

**Después de `app = FastAPI(...)`, agregar:**
```python
# Agregar router del dashboard
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
```

**Agregar evento de startup (si no existe):**
```python
@app.on_event("startup")
async def startup():
    # Si ya tienes otros startups, agregar esta línea:
    start_refresh_worker()  # Refresh automático cada 30s
```

### 4.3 Guardar el archivo

`Ctrl+S` o `Cmd+S`

✅ **Paso 4 completo!**

---

## 🔄 PASO 5: Reiniciar el Servidor

### En la terminal:

```bash
cd /Users/luiseiman/Documents/GitHub/cotiza-api

# Detener servidor actual
pkill -f "uvicorn main:app"

# Activar entorno virtual
source .venv/bin/activate

# Iniciar servidor
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Deberías ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
[dashboard_refresh] Worker iniciado
```

✅ **Paso 5 completo!**

---

## ✅ PASO 6: Probar que Funciona

### Opción A - Con curl (en otra terminal):

```bash
curl http://localhost:8000/api/ratios/dashboard
```

### Opción B - En el navegador:

Abrir: http://localhost:8000/api/ratios/dashboard

### Resultado esperado:

```json
{
  "status": "success",
  "data": [
    {
      "par": "AL30D-AL30C",
      "ultimo_ratio_operado": 1.03399,
      "promedio_rueda": 1.02424,
      "dif_rueda_pct": 0.95,
      "promedio_1semana": 1.01606,
      "dif_1semana_pct": 1.76,
      "promedio_1mes": 1.00740,
      "dif_1mes_pct": 2.64,
      "minimo_mensual": 0.99759,
      "dif_minimo_pct": 3.52,
      "maximo_mensual": 1.02657,
      "dif_maximo_pct": 0.72
    },
    // ... más pares
  ],
  "count": 13,
  "query_time_ms": 8.5,  // ← Debe ser < 100ms
  "method": "materialized_view"
}
```

### Verificar rendimiento:
- `query_time_ms` debe ser **< 100ms** (idealmente < 50ms)
- Si es > 500ms, revisar que los índices se crearon correctamente

✅ **¡TODO COMPLETO! 🎉**

---

## 🎯 Endpoints Disponibles

Una vez completados todos los pasos, tienes estos endpoints:

| Endpoint | Velocidad | Descripción |
|----------|-----------|-------------|
| `/api/ratios/dashboard` | Auto | Elige automáticamente el mejor método |
| `/api/ratios/dashboard/fast` | <10ms | Vista materializada (más rápido) |
| `/api/ratios/dashboard/balanced` | 100-500ms | Función PostgreSQL (tiempo real) |
| `/api/ratios/dashboard/flexible` | 500-2000ms | Python puro (desarrollo) |

**Recomendado:** Usar `/api/ratios/dashboard` (sin sufijo)

---

## 🆘 Solución de Problemas

### ❌ Error: "table ratios_dashboard_view does not exist"
**Causa:** No se ejecutó el Paso 3  
**Solución:** Ejecutar el código SQL del Paso 3 en Supabase

### ❌ Error: "cannot import name 'router' from 'dashboard_ratios_api'"
**Causa:** El archivo `dashboard_ratios_api.py` no está en la carpeta correcta  
**Solución:** Copiar el archivo a la misma carpeta que `main.py`

### ❌ Query muy lenta (>1000ms)
**Causa:** Los índices no se crearon  
**Solución:** Ejecutar de nuevo el Paso 2 y verificar con:
```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'terminal_ratios_history';
```

### ❌ Error: "column last_ratio does not exist"
**Causa:** No se ejecutó el Paso 1  
**Solución:** Ejecutar el código SQL del Paso 1 en Supabase

### ❌ Los datos no se actualizan
**Causa:** El refresh worker no está corriendo  
**Solución:** Verificar que `start_refresh_worker()` esté en el startup de `main.py`

---

## 📚 Archivos de Referencia

- `migration_simple.sql` - Paso 1 (agregar columnas)
- `crear_indices.sql` - Paso 2 (crear índices)
- `consultas_ratios_optimizadas.sql` - Paso 3 (vista materializada)
- `dashboard_ratios_api.py` - Paso 4 (código Python)
- `RECOMENDACIONES_DASHBOARD.md` - Documentación completa

---

## 📞 Siguiente Paso

Una vez que todo funcione, puedes:
1. Integrar el endpoint en tu frontend
2. Agregar autenticación si es necesario
3. Personalizar los períodos de tiempo
4. Agregar más campos calculados

¡Disfruta de tu dashboard ultra-rápido! 🚀



