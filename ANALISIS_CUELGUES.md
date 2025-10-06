# 🚨 ANÁLISIS COMPLETO DE POSIBLES CAUSAS DE CUELGUE EN EL SERVICIO

## 📋 **RESUMEN EJECUTIVO**

He realizado un análisis exhaustivo del código y he identificado **múltiples puntos críticos** que pueden causar cuelgues en el servicio. Los problemas están distribuidos en varios componentes y van desde **loops infinitos mal controlados** hasta **deadlocks potenciales**.

---

## 🔴 **PROBLEMAS CRÍTICOS DETECTADOS**

### 1. **LOOPS INFINITOS SIN CONTROL DE PARADA** ⚠️ CRÍTICO

#### **A. Ratio Operations - Bucle Principal**
**Archivo**: `ratio_operations.py` líneas 439-495
```python
# PROBLEMA: Bucle infinito sin límite de tiempo
while progress.remaining_nominales > 0 and progress.status == OperationStatus.RUNNING:
    progress.current_attempt += 1
    # ... código ...
    await asyncio.sleep(10)  # Esperar 10 segundos entre intentos
```

**Riesgo**: ⚠️ **ALTO** - Si una operación nunca completa, el bucle continúa indefinidamente.

#### **B. Telegram Bot - Polling Infinito**
**Archivo**: `telegram_control.py` líneas 283, 423
```python
# PROBLEMA: Polling infinito sin timeout de emergencia
_bot.infinity_polling(skip_pending=True, timeout=10, allowed_updates=[])
```

**Riesgo**: ⚠️ **MEDIO** - Si el bot se cuelga, no se puede detener fácilmente.

#### **C. Worker de Ratios - Loop Principal**
**Archivo**: `ratios_worker.py` líneas 135-335
```python
# PROBLEMA: Loop sin verificación de estado de parada
def _worker_loop():
    while not _stop_event.is_set():
        # ... procesamiento ...
        time.sleep(INTERVAL_SECONDS)  # 10 segundos
```

**Riesgo**: ⚠️ **MEDIO** - Depende del `_stop_event` que podría no funcionar correctamente.

#### **D. Dashboard WebSocket - Loop de Refresh**
**Archivo**: `dashboard_websocket.py` líneas 141-147
```python
# PROBLEMA: Loop infinito sin control de excepción adecuado
while True:
    try:
        await self.refresh_and_broadcast()
    except Exception as e:
        print(f"[WS] Error en loop de refresh: {e}")
    await asyncio.sleep(self.refresh_interval)
```

**Riesgo**: ⚠️ **MEDIO** - Si `refresh_and_broadcast()` falla repetidamente, consume CPU.

#### **E. Simulador de Datos - Múltiples Loops**
**Archivo**: `simulador_datos.py` líneas 69, 87, 133
```python
# PROBLEMA: Múltiples loops infinitos en threads separados
def actualizar_cache():
    while True:  # ❌ Sin control de parada
        # ... código ...
        time.sleep(5)

def mostrar_estado_cache():
    while True:  # ❌ Sin control de parada
        # ... código ...
        time.sleep(30)

def main():
    while True:  # ❌ Loop principal sin control
        time.sleep(1)
```

**Riesgo**: ⚠️ **ALTO** - Múltiples loops infinitos pueden consumir recursos.

---

### 2. **DEADLOCKS POTENCIALES** ⚠️ CRÍTICO

#### **A. Ratio Operations Manager**
**Archivo**: `ratio_operations.py` líneas 103, 387
```python
# PROBLEMA: Lock usado en múltiples lugares sin timeout
self.operation_lock = threading.Lock()

# Uso problemático:
with self.operation_lock:
    # ... código que puede tardar mucho ...
    await self._notify_progress(operation_id, progress)  # ❌ I/O dentro del lock
```

**Riesgo**: ⚠️ **ALTO** - Si `_notify_progress` se cuelga, el lock nunca se libera.

#### **B. WebSocket Manager**
**Archivo**: `main.py` líneas 506, 511
```python
# PROBLEMA: Múltiples locks que pueden interactuar
_websocket_lock = threading.Lock()
_dashboard_lock = threading.Lock()

# Uso simultáneo sin orden definido puede causar deadlock
```

**Riesgo**: ⚠️ **MEDIO** - Deadlock si se adquieren en orden diferente.

#### **C. Quotes Cache**
**Archivo**: `quotes_cache.py` línea 6
```python
# PROBLEMA: RLock usado globalmente
_lock = threading.RLock()

# Si hay excepciones no manejadas, el lock puede quedarse bloqueado
```

**Riesgo**: ⚠️ **MEDIO** - RLock puede causar deadlock si se adquiere recursivamente.

---

### 3. **OPERACIONES BLOQUEANTES EN HILOS PRINCIPALES** ⚠️ CRÍTICO

#### **A. Requests HTTP Síncronos**
**Archivo**: `telegram_control.py` líneas 134, 143
```python
# PROBLEMA: Requests síncronos en threads del bot
def _post(path, data=None):
    r = requests.post(url, json=data or {}, timeout=15)  # ❌ Bloqueante

def _get(path):
    r = requests.get(url, timeout=10)  # ❌ Bloqueante
```

**Riesgo**: ⚠️ **ALTO** - Si la API no responde, bloquea el bot de Telegram.

#### **B. Operaciones de Base de Datos**
**Archivo**: `supabase_client.py` (referenciado en múltiples lugares)
```python
# PROBLEMA: Operaciones de DB síncronas sin timeout
# Si Supabase no responde, bloquea el hilo
```

**Riesgo**: ⚠️ **ALTO** - Conexiones de DB colgadas pueden bloquear el servicio.

---

### 4. **MANEJO INADECUADO DE EXCEPCIONES** ⚠️ MEDIO

#### **A. Try-Catch Demasiado Amplios**
**Archivo**: `main.py` líneas 687-720
```python
# PROBLEMA: Catch de Exception muy amplio
try:
    data = await websocket.receive_text()
    # ... mucho código ...
except Exception as e:
    print(f"Error: {e}")  # ❌ No maneja casos específicos
```

**Riesgo**: ⚠️ **MEDIO** - Errores críticos pueden pasar desapercibidos.

#### **B. Excepciones Silenciosas**
**Archivo**: `telegram_control.py` líneas 454, 478
```python
# PROBLEMA: Excepciones silenciadas
try:
    _bot.stop_polling()
except:
    pass  # ❌ Ignora todos los errores
```

**Riesgo**: ⚠️ **MEDIO** - Errores importantes no se reportan.

---

### 5. **ACUMULACIÓN DE RECURSOS** ⚠️ MEDIO

#### **A. Conexiones WebSocket No Limpiadas**
**Archivo**: `main.py` líneas 505, 687
```python
# PROBLEMA: Conexiones WebSocket pueden acumularse
_websocket_connections = []  # ❌ Lista global sin límite

# Si las conexiones no se cierran correctamente, se acumulan
```

**Riesgo**: ⚠️ **MEDIO** - Acumulación de conexiones puede consumir memoria.

#### **B. Operaciones de Ratio Acumuladas**
**Archivo**: `ratio_operations.py` líneas 102, 833
```python
# PROBLEMA: Operaciones se limpian después de 5 minutos
async def _cleanup_operation(self, operation_id: str):
    await asyncio.sleep(300)  # ❌ 5 minutos de delay
```

**Riesgo**: ⚠️ **BAJO** - Delay en limpieza, pero no crítico.

---

## 🛠️ **RECOMENDACIONES DE SOLUCIÓN**

### **INMEDIATAS (Críticas)**

#### 1. **Agregar Timeouts a Loops Infinitos**
```python
# ANTES (problemático)
while progress.remaining_nominales > 0:
    await asyncio.sleep(10)

# DESPUÉS (seguro)
max_attempts = 100  # Límite de seguridad
attempt = 0
while progress.remaining_nominales > 0 and attempt < max_attempts:
    attempt += 1
    await asyncio.sleep(10)
```

#### 2. **Usar Locks con Timeout**
```python
# ANTES (problemático)
with self.operation_lock:
    # código que puede colgarse

# DESPUÉS (seguro)
if self.operation_lock.acquire(timeout=30):
    try:
        # código
    finally:
        self.operation_lock.release()
else:
    raise TimeoutError("Lock timeout")
```

#### 3. **Mover I/O Fuera de Locks**
```python
# ANTES (problemático)
with self.operation_lock:
    # ... código ...
    await self._notify_progress()  # ❌ I/O dentro del lock

# DESPUÉS (seguro)
with self.operation_lock:
    # ... solo código crítico ...
    progress_data = copy.copy(progress)  # Copiar datos

# Fuera del lock
await self._notify_progress(progress_data)
```

### **MEDIANO PLAZO**

#### 1. **Implementar Circuit Breakers**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
```

#### 2. **Agregar Health Checks**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "websocket_connections": len(_websocket_connections),
        "active_operations": len(ratio_manager.active_operations),
        "memory_usage": psutil.Process().memory_info().rss
    }
```

#### 3. **Implementar Graceful Shutdown**
```python
import signal

def signal_handler(signum, frame):
    print("🛑 Recibida señal de parada, iniciando shutdown graceful...")
    # Limpiar recursos
    # Cerrar conexiones
    # Finalizar operaciones pendientes
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

---

## 📊 **PRIORIDADES DE IMPLEMENTACIÓN**

### **🔥 CRÍTICO (Implementar INMEDIATAMENTE)**
1. ✅ Agregar timeouts a loops de ratio operations
2. ✅ Implementar locks con timeout
3. ✅ Mover I/O fuera de locks críticos
4. ✅ Agregar límites a conexiones WebSocket

### **⚠️ ALTO (Implementar en 1-2 días)**
1. ✅ Implementar circuit breakers para requests HTTP
2. ✅ Agregar health checks detallados
3. ✅ Mejorar manejo de excepciones específicas
4. ✅ Implementar graceful shutdown

### **📋 MEDIO (Implementar en 1 semana)**
1. ✅ Refactorizar simulador de datos con control de parada
2. ✅ Agregar métricas de rendimiento
3. ✅ Implementar alertas automáticas
4. ✅ Documentar procedimientos de recuperación

---

## 🎯 **CONCLUSIÓN**

El servicio tiene **múltiples puntos de falla críticos** que pueden causar cuelgues. Los problemas más graves son:

1. **Loops infinitos sin control** en ratio operations
2. **Deadlocks potenciales** en el manejo de locks
3. **Operaciones bloqueantes** en threads principales
4. **Acumulación de recursos** sin límites

**Recomendación**: Implementar las soluciones críticas **inmediatamente** para evitar cuelgues en producción.
