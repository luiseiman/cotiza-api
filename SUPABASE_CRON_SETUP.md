# Cómo Crear un Cron Job en Supabase

## 📋 ¿Para qué necesitas el Cron?

Para refrescar automáticamente la vista materializada `ratios_dashboard_view` cada 30 segundos, manteniendo los datos actualizados sin intervención manual.

---

## ⚠️ IMPORTANTE: Limitaciones de Supabase

**pg_cron NO está disponible en todos los planes de Supabase:**

| Plan | pg_cron | Alternativas |
|------|---------|--------------|
| **Free** | ❌ No | Worker en Python (recomendado) |
| **Pro** | ✅ Sí | pg_cron o Worker en Python |
| **Team/Enterprise** | ✅ Sí | pg_cron o Worker en Python |

**Si estás en el plan Free:** Salta a la sección "Alternativa: Worker en Python"

---

## ✅ OPCIÓN 1: pg_cron en Supabase (Plan Pro+)

### Paso 1: Habilitar la extensión pg_cron

1. Ir a: https://supabase.com/dashboard
2. Seleccionar tu proyecto
3. Click en **"Database"** → **"Extensions"**
4. Buscar **"pg_cron"**
5. Click en el switch para **habilitarlo**

### Paso 2: Verificar que está habilitado

En SQL Editor, ejecutar:

```sql
SELECT * FROM pg_extension WHERE extname = 'pg_cron';
```

Deberías ver una fila con `pg_cron`.

### Paso 3: Crear la función de refresh (si no existe)

```sql
-- Función para refrescar la vista materializada
CREATE OR REPLACE FUNCTION refresh_ratios_view()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ratios_dashboard_view;
    RAISE NOTICE 'Vista materializada refrescada: %', NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Paso 4: Crear el cron job

```sql
-- Refrescar cada 30 segundos
SELECT cron.schedule(
    'refresh-ratios-dashboard',  -- Nombre del job
    '*/30 * * * * *',             -- Cada 30 segundos (segundos minutos horas día mes día_semana)
    $$SELECT refresh_ratios_view()$$
);
```

**Nota sobre la sintaxis de cron:**
- `*/30 * * * * *` = Cada 30 segundos
- `* * * * *` = Cada minuto (sin segundos)
- `*/5 * * * *` = Cada 5 minutos

### Paso 5: Verificar que el cron está corriendo

```sql
-- Ver todos los cron jobs
SELECT 
    jobid,
    schedule,
    command,
    nodename,
    nodeport,
    database,
    username,
    active
FROM cron.job;
```

### Paso 6: Ver el historial de ejecuciones

```sql
-- Ver últimas ejecuciones (incluye errores)
SELECT 
    jobid,
    runid,
    job_pid,
    database,
    username,
    command,
    status,
    return_message,
    start_time,
    end_time
FROM cron.job_run_details
ORDER BY start_time DESC
LIMIT 20;
```

### Gestión del Cron Job

**Pausar/Despausar:**
```sql
-- Pausar
SELECT cron.alter_job(
    job_id := (SELECT jobid FROM cron.job WHERE jobname = 'refresh-ratios-dashboard'),
    schedule := NULL
);

-- Reactivar
SELECT cron.alter_job(
    job_id := (SELECT jobid FROM cron.job WHERE jobname = 'refresh-ratios-dashboard'),
    schedule := '*/30 * * * * *'
);
```

**Eliminar:**
```sql
SELECT cron.unschedule('refresh-ratios-dashboard');
```

**Cambiar frecuencia:**
```sql
-- Cambiar a cada 1 minuto
SELECT cron.alter_job(
    job_id := (SELECT jobid FROM cron.job WHERE jobname = 'refresh-ratios-dashboard'),
    schedule := '* * * * *'
);
```

---

## 🐍 OPCIÓN 2: Worker en Python (Recomendado para Free Tier)

Esta opción funciona en **CUALQUIER plan de Supabase** (incluido Free).

### Ventajas:
- ✅ Funciona en plan Free
- ✅ No requiere extensiones de Supabase
- ✅ Más control sobre errores y logging
- ✅ Puede ejecutarse en tu servidor o en background

### Implementación:

El código ya está incluido en `dashboard_ratios_api.py`. Solo necesitas:

**1. Asegurarte de que la función existe en Supabase:**

```sql
CREATE OR REPLACE FUNCTION refresh_ratios_view()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ratios_dashboard_view;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**2. En tu `main.py`, agregar el startup:**

```python
from dashboard_ratios_api import start_refresh_worker

@app.on_event("startup")
async def startup():
    # Iniciar worker de refresh automático
    start_refresh_worker()
    print("✅ Refresh worker iniciado - actualizando cada 30 segundos")
```

**3. El worker se ejecutará automáticamente:**

```python
# Ya incluido en dashboard_ratios_api.py
def _refresh_worker_loop():
    """Worker que refresca la vista materializada cada 30 segundos."""
    while not _refresh_stop_event.is_set():
        try:
            # Refrescar vista
            supabase.rpc("refresh_ratios_view").execute()
            print(f"[dashboard_refresh] Vista actualizada: {datetime.now()}")
        except Exception as e:
            print(f"[dashboard_refresh] Error: {e}")
        
        # Esperar 30 segundos
        _refresh_stop_event.wait(30)
```

**Ventajas adicionales:**
- Se ejecuta mientras tu API esté corriendo
- Logs visibles en tu consola
- Fácil de debuggear
- No consume recursos de Supabase

---

## 📊 OPCIÓN 3: GitHub Actions (Para despliegues serverless)

Si tu aplicación no está siempre corriendo, puedes usar GitHub Actions:

**Crear archivo `.github/workflows/refresh-dashboard.yml`:**

```yaml
name: Refresh Dashboard View

on:
  schedule:
    # Cada 5 minutos
    - cron: '*/5 * * * *'
  workflow_dispatch: # Permite ejecutar manualmente

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - name: Refresh Materialized View
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: |
          curl -X POST "$SUPABASE_URL/rest/v1/rpc/refresh_ratios_view" \
            -H "apikey: $SUPABASE_KEY" \
            -H "Authorization: Bearer $SUPABASE_KEY" \
            -H "Content-Type: application/json"
```

**Configurar secrets:**
1. Ir a tu repo en GitHub
2. Settings → Secrets and variables → Actions
3. Agregar:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

---

## 🔄 OPCIÓN 4: Trigger en INSERT (Refresh automático)

Refrescar la vista cada vez que se inserta un nuevo dato:

```sql
-- Crear función trigger
CREATE OR REPLACE FUNCTION trigger_refresh_dashboard()
RETURNS TRIGGER AS $$
BEGIN
    -- Refrescar solo si el cambio es significativo
    PERFORM refresh_ratios_view();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear trigger
CREATE TRIGGER auto_refresh_dashboard
AFTER INSERT OR UPDATE ON terminal_ratios_history
FOR EACH STATEMENT
EXECUTE FUNCTION trigger_refresh_dashboard();
```

**⚠️ Advertencia:** Esto puede ser costoso si insertas datos muy frecuentemente.

**Mejor opción: Trigger con throttling:**

```sql
CREATE OR REPLACE FUNCTION trigger_refresh_dashboard_throttled()
RETURNS TRIGGER AS $$
DECLARE
    last_refresh timestamp;
BEGIN
    -- Obtener última actualización
    SELECT MAX(ultimo_timestamp) INTO last_refresh 
    FROM ratios_dashboard_view LIMIT 1;
    
    -- Solo refrescar si pasaron más de 30 segundos
    IF last_refresh IS NULL OR NOW() - last_refresh > INTERVAL '30 seconds' THEN
        PERFORM refresh_ratios_view();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 📈 Comparación de Opciones

| Opción | Costo | Complejidad | Plan Supabase | Recomendación |
|--------|-------|-------------|---------------|---------------|
| **pg_cron** | Medio | Baja | Pro+ | ⭐⭐⭐⭐ Si tienes Pro |
| **Worker Python** | Bajo | Media | Free/Pro | ⭐⭐⭐⭐⭐ Mejor para Free |
| **GitHub Actions** | Gratis | Media | Free/Pro | ⭐⭐⭐ Si no tienes servidor |
| **Trigger** | Alto | Alta | Free/Pro | ⭐⭐ Solo casos específicos |

---

## 🎯 Recomendación Final

### Si estás en plan Free de Supabase:
✅ **USAR: Worker en Python** (Opción 2)
- Ya está implementado en `dashboard_ratios_api.py`
- Solo agregar `start_refresh_worker()` en el startup
- Funciona mientras tu API esté corriendo

### Si estás en plan Pro o superior:
✅ **USAR: pg_cron** (Opción 1)
- Más robusto
- Se ejecuta aunque tu API esté caída
- No consume recursos de tu servidor

---

## ✅ Verificación

**Para pg_cron:**
```sql
SELECT * FROM cron.job_run_details 
WHERE jobname = 'refresh-ratios-dashboard'
ORDER BY start_time DESC LIMIT 10;
```

**Para Worker Python:**
Verás en la consola:
```
[dashboard_refresh] Vista actualizada: 2025-09-30 17:23:33
```

**Probar manualmente:**
```sql
-- Ejecutar refresh manual
SELECT refresh_ratios_view();

-- Ver datos actualizados
SELECT * FROM ratios_dashboard_view;
```

---

## 🆘 Troubleshooting

### Error: "extension pg_cron is not available"
**Solución:** Tu plan no incluye pg_cron. Usa Worker en Python.

### Error: "permission denied for function refresh_ratios_view"
**Solución:** Agregar `SECURITY DEFINER` a la función:
```sql
CREATE OR REPLACE FUNCTION refresh_ratios_view()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ratios_dashboard_view;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### El cron job no se ejecuta
**Solución:** Verificar que esté activo:
```sql
SELECT jobid, active FROM cron.job WHERE jobname = 'refresh-ratios-dashboard';
```

### El worker Python no arranca
**Solución:** Verificar logs del servidor y que `start_refresh_worker()` esté en startup.

---

## 📚 Referencias

- [Documentación pg_cron](https://github.com/citusdata/pg_cron)
- [Supabase Database Extensions](https://supabase.com/docs/guides/database/extensions)
- [Cron syntax](https://crontab.guru/)

