# Configuración de Horarios Personalizados para el Dashboard

## 📋 ¿Qué hace esto?

El refresh automático del dashboard ahora puede configurarse para ejecutarse **solo en ciertos días y horarios**, evitando consumo innecesario de recursos fuera del horario de mercado.

---

## 🎯 Características

- ✅ Ejecuta refresh solo en días específicos (ej: Lunes a Viernes)
- ✅ Ejecuta solo en horarios específicos (ej: 10:00 a 17:00)
- ✅ Soporte para feriados (no ejecuta en fechas específicas)
- ✅ Configuración simple en un solo archivo
- ✅ Valores por defecto si no hay configuración

---

## 🚀 Uso Básico

### Paso 1: Configurar horarios

Editar el archivo `dashboard_config.py`:

```python
# Días en que se ejecuta (0=Lun, 1=Mar, ..., 6=Dom)
DIAS_HABILES = [0, 1, 2, 3, 4]  # Lunes a Viernes

# Horario de inicio
HORA_INICIO = 10      # 10:00 AM
MINUTO_INICIO = 0

# Horario de fin
HORA_FIN = 17         # 5:00 PM
MINUTO_FIN = 0

# Intervalo de refresh (en segundos)
REFRESH_INTERVAL_SECONDS = 10
```

### Paso 2: Reiniciar el servidor

```bash
pkill -f "uvicorn main:app"
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Paso 3: Verificar en logs

**Dentro del horario:**
```
[dashboard_refresh] Vista actualizada a las 14:23:33
[dashboard_refresh] Vista actualizada a las 14:23:43
```

**Fuera del horario:**
```
[dashboard_refresh] Fuera de horario de mercado - 20:15:42
```

---

## 📅 Ejemplos de Configuración

### Ejemplo 1: Mercado Argentino Estándar
```python
DIAS_HABILES = [0, 1, 2, 3, 4]  # Lunes a Viernes
HORA_INICIO = 10
MINUTO_INICIO = 0
HORA_FIN = 17
MINUTO_FIN = 0
```

### Ejemplo 2: Con Pre-Apertura y Post-Cierre
```python
DIAS_HABILES = [0, 1, 2, 3, 4]
HORA_INICIO = 8       # 8:00 AM (pre-apertura)
MINUTO_INICIO = 30
HORA_FIN = 18         # 6:00 PM (post-cierre)
MINUTO_FIN = 30
```

### Ejemplo 3: Solo algunos días
```python
DIAS_HABILES = [0, 2, 4]  # Solo Lunes, Miércoles y Viernes
HORA_INICIO = 9
HORA_FIN = 18
```

### Ejemplo 4: 24/7 (Siempre activo)
```python
DIAS_HABILES = [0, 1, 2, 3, 4, 5, 6]  # Todos los días
HORA_INICIO = 0
HORA_FIN = 23
MINUTO_FIN = 59
```

### Ejemplo 5: Solo fines de semana
```python
DIAS_HABILES = [5, 6]  # Sábado y Domingo
HORA_INICIO = 10
HORA_FIN = 20
```

---

## 🎉 Configuración de Feriados

Agregar fechas en formato `YYYY-MM-DD` en el archivo `dashboard_config.py`:

```python
FERIADOS = [
    "2025-01-01",  # Año Nuevo
    "2025-03-24",  # Día Nacional de la Memoria
    "2025-04-02",  # Día del Veterano
    "2025-05-01",  # Día del Trabajador
    "2025-05-25",  # Revolución de Mayo
    "2025-06-20",  # Día de la Bandera
    "2025-07-09",  # Día de la Independencia
    "2025-12-25",  # Navidad
]
```

El worker **NO se ejecutará** en estas fechas, incluso si caen en días hábiles.

---

## ⚙️ Configuración Avanzada

### Cambiar intervalo de refresh

En `dashboard_config.py`:

```python
REFRESH_INTERVAL_SECONDS = 5   # Cada 5 segundos
REFRESH_INTERVAL_SECONDS = 10  # Cada 10 segundos (default)
REFRESH_INTERVAL_SECONDS = 30  # Cada 30 segundos
REFRESH_INTERVAL_SECONDS = 60  # Cada 1 minuto
```

### Múltiples ventanas horarias

Si necesitas múltiples períodos (pre-market, market, post-market), puedes modificar la función `_is_market_hours()` en `dashboard_ratios_api.py`:

```python
def _is_market_hours():
    now = datetime.now()
    day = now.weekday()
    hour = now.hour
    minute = now.minute
    
    # Pre-Market: Lun-Vie 8:30-10:00
    if day in [0,1,2,3,4] and (hour == 8 and minute >= 30) or (hour == 9):
        return True
    
    # Market: Lun-Vie 10:00-17:00
    if day in [0,1,2,3,4] and 10 <= hour < 17:
        return True
    
    # Post-Market: Lun-Vie 17:00-18:30
    if day in [0,1,2,3,4] and (hour == 17 or (hour == 18 and minute < 30)):
        return True
    
    return False
```

---

## 📊 Comportamiento del Sistema

| Situación | Comportamiento |
|-----------|----------------|
| **Dentro del horario** | Refresh cada 10 segundos + logs detallados |
| **Fuera del horario** | No ejecuta refresh + log cada 5 minutos |
| **Día no hábil** | No ejecuta refresh + log ocasional |
| **Feriado** | No ejecuta refresh + log ocasional |

---

## 🔍 Verificación

### Probar horario actual

Crear un script temporal `test_horario.py`:

```python
from dashboard_ratios_api import _is_market_hours
from datetime import datetime

print(f"Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Día de la semana: {datetime.now().strftime('%A')}")
print(f"¿En horario de mercado? {_is_market_hours()}")
```

Ejecutar:
```bash
python test_horario.py
```

### Ver configuración activa

Agregar endpoint en `main.py`:

```python
@app.get("/api/ratios/market-status")
def get_market_status():
    from dashboard_ratios_api import _is_market_hours
    from datetime import datetime
    
    return {
        "timestamp": datetime.now().isoformat(),
        "is_market_hours": _is_market_hours(),
        "day_of_week": datetime.now().strftime('%A'),
        "time": datetime.now().strftime('%H:%M:%S')
    }
```

Luego consultar:
```bash
curl http://localhost:8000/api/ratios/market-status
```

---

## 🎯 Casos de Uso Comunes

### Caso 1: Trading de Acciones Argentinas
```python
DIAS_HABILES = [0, 1, 2, 3, 4]  # Lun-Vie
HORA_INICIO = 10
HORA_FIN = 17
FERIADOS = ["2025-05-01", "2025-07-09", ...]  # Feriados argentinos
```

### Caso 2: Trading Crypto 24/7
```python
DIAS_HABILES = [0, 1, 2, 3, 4, 5, 6]  # Todos los días
HORA_INICIO = 0
HORA_FIN = 23
MINUTO_FIN = 59
```

### Caso 3: Solo Sesión de la Tarde
```python
DIAS_HABILES = [0, 1, 2, 3, 4]
HORA_INICIO = 14  # 2:00 PM
HORA_FIN = 17     # 5:00 PM
```

### Caso 4: Fines de Semana para Análisis
```python
DIAS_HABILES = [5, 6]  # Sáb-Dom
HORA_INICIO = 10
HORA_FIN = 20
```

---

## 🆘 Troubleshooting

### El worker no respeta los horarios

**Problema:** Sigue ejecutándose fuera del horario  
**Solución:** Verificar que `dashboard_config.py` esté en la misma carpeta que `dashboard_ratios_api.py`

```bash
ls -la dashboard_config.py
```

### No ejecuta en días que debería

**Problema:** No ejecuta en Miércoles pero está en DIAS_HABILES  
**Solución:** Verificar que los números de días sean correctos (0=Lun, 1=Mar, 2=Mie, ...)

```python
# Verificar día actual
from datetime import datetime
print(f"Hoy es: {datetime.now().weekday()}")  # 0=Lun, 1=Mar, etc.
```

### Se ejecuta en feriados

**Problema:** Se ejecuta en feriados aunque están en la lista  
**Solución:** Verificar formato de fecha `YYYY-MM-DD`

```python
# Verificar fecha actual
from datetime import datetime
print(datetime.now().strftime("%Y-%m-%d"))
```

### No veo logs "Fuera de horario"

**Problema:** No aparecen logs cuando está fuera de horario  
**Solución:** Los logs fuera de horario solo aparecen ocasionalmente (cada ~5 minutos) para no llenar el archivo de logs.

---

## 📚 Referencia Rápida

### Días de la Semana
```
0 = Lunes
1 = Martes
2 = Miércoles
3 = Jueves
4 = Viernes
5 = Sábado
6 = Domingo
```

### Formato de Hora
```
HORA_INICIO = 9      # 9:00 AM
MINUTO_INICIO = 30   # 9:30 AM

HORA_FIN = 17        # 5:00 PM
MINUTO_FIN = 30      # 5:30 PM
```

### Formato de Feriados
```
"YYYY-MM-DD"
"2025-12-25"  # 25 de Diciembre de 2025
```

---

## ✅ Resumen

1. ✅ Editar `dashboard_config.py` con tus horarios
2. ✅ Agregar feriados si es necesario
3. ✅ Reiniciar el servidor
4. ✅ Verificar en logs que funciona correctamente

El sistema ahora ejecutará el refresh **SOLO** en los días y horarios que especificaste, ahorrando recursos y optimizando el rendimiento.

