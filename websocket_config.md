# 🔌 Solución al Error WebSocket 403 Forbidden

## 🚨 **Problema Identificado**
El error `403 Forbidden` en el WebSocket indica que la conexión está siendo rechazada por el servidor.

## 🔍 **Causas Posibles**

### 1. **Configuración de CORS**
- FastAPI no tenía middleware CORS configurado
- Los navegadores bloquean conexiones WebSocket sin CORS apropiado

### 2. **Falta de Endpoint WebSocket**
- No había un endpoint `/ws/cotizaciones` definido
- Las conexiones WebSocket eran rechazadas automáticamente

### 3. **Configuración de Uvicorn**
- Uvicorn puede estar bloqueando conexiones WebSocket
- Configuración de host/port incorrecta

## ✅ **Soluciones Implementadas**

### 1. **Middleware CORS**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. **Endpoint WebSocket Funcional**
```python
@app.websocket("/ws/cotizaciones")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Lógica del WebSocket...
```

### 3. **Logs Detallados**
- Logs de conexión/desconexión
- Logs de mensajes recibidos
- Logs de errores específicos

## 🧪 **Cómo Probar**

### 1. **Reiniciar la API**
```bash
# Detener la API actual (Ctrl+C)
# Luego reiniciar
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. **Probar con el Script**
```bash
python test_websocket.py
```

### 3. **Probar Manualmente**
```bash
# Verificar endpoints HTTP
curl http://localhost:8000/cotizaciones/health
curl http://localhost:8000/cotizaciones/websocket_status

# Verificar estado de locks
curl http://localhost:8000/cotizaciones/telegram_locks_status
```

## 🔧 **Configuración Adicional**

### **Variables de Entorno (.env)**
```env
# Configuración WebSocket
WEBSOCKET_ENABLED=1
WEBSOCKET_MAX_CONNECTIONS=100
WEBSOCKET_TIMEOUT=30

# Configuración CORS (opcional)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### **Uvicorn con Configuración Específica**
```bash
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level debug \
  --access-log
```

## 📊 **Monitoreo del WebSocket**

### **Endpoint de Estado**
```bash
GET /cotizaciones/websocket_status
```

**Respuesta:**
```json
{
  "active_connections": 2,
  "connections": [
    {
      "host": "127.0.0.1",
      "port": 54321,
      "state": 1
    }
  ],
  "timestamp": 1640995200.123
}
```

### **Logs en Tiempo Real**
```bash
# Ver logs de WebSocket
uvicorn main:app --log-level debug | grep websocket
```

## 🚨 **Solución de Problemas**

### **Error 403 Persiste**
1. Verificar que la API se reinició con los cambios
2. Verificar logs de Uvicorn
3. Verificar configuración de firewall/antivirus

### **Conexión Rechazada**
1. Verificar que la API esté ejecutándose
2. Verificar puerto y host
3. Verificar que no haya otro servicio usando el puerto

### **CORS en Producción**
```python
# Cambiar en producción
allow_origins=["https://tudominio.com", "https://app.tudominio.com"]
```

## 📝 **Comandos Útiles**

### **Verificar Puertos en Uso**
```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
netstat -tlnp | grep :8000
```

### **Verificar Procesos**
```bash
# Windows
tasklist | findstr python

# Linux/Mac
ps aux | grep uvicorn
```

### **Limpiar y Reiniciar**
```bash
# Detener todos los procesos Python
taskkill /F /IM python.exe

# Reiniciar API
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## 🎯 **Resultado Esperado**
Después de aplicar las soluciones:
- ✅ WebSocket se conecta sin errores 403
- ✅ Mensajes se envían y reciben correctamente
- ✅ Logs muestran conexiones exitosas
- ✅ Endpoint de estado funciona correctamente
