# 🤖 Bot de Telegram con Bloqueo Robusto

Este bot de Telegram incluye un sistema de bloqueo de múltiples capas para asegurar que **nunca** haya más de una instancia ejecutándose, ni localmente ni en la red.

## 🚀 Características del Sistema de Bloqueo

### 1. **Lock de Archivo** 📁
- Archivo único basado en token y hostname
- Verificación de timestamp y PID
- Limpieza automática de locks obsoletos (>1 hora)

### 2. **Lock de Proceso** 🐍
- Verificación de PID único
- Detección de otros procesos de Python con "telegram"
- Prevención de instancias duplicadas

### 3. **Lock de Red** 🌐
- Puerto TCP exclusivo (por defecto 12345)
- Verificación de puertos en uso
- Detección de bots remotos

### 4. **Verificación de API** 🔌
- Comprobación de conectividad
- Validación de estado del servicio
- Fallback a modo simple si es necesario

## 📋 Configuración Requerida

### Variables de Entorno (.env)

```env
# OBLIGATORIAS
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui

# OPCIONALES (con valores por defecto)
TELEGRAM_POLLING=1                    # 1=habilitado, 0=deshabilitado
TELEGRAM_LOCK_PORT=12345             # Puerto para lock de red
API_BASE=http://127.0.0.1:8000      # Base de la API
PORT=8000                            # Puerto de la API
```

### Pasos de Configuración

1. **Crear bot en Telegram**
   ```bash
   # Ve a @BotFather en Telegram
   # Envía /newbot
   # Sigue las instrucciones
   # GUARDA EL TOKEN
   ```

2. **Obtener Chat ID**
   ```bash
   # Ve a @userinfobot en Telegram
   # Envía cualquier mensaje
   # GUARDA TU CHAT ID (número)
   ```

3. **Crear archivo .env**
   ```bash
   # Copia env_config_example.txt a .env
   # Completa con tus datos
   ```

4. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

## 🔧 Uso del Sistema

### Iniciar el Bot

```bash
# Iniciar la API
uvicorn main:app --host 127.0.0.1 --port 8000

# El bot se iniciará automáticamente si TELEGRAM_POLLING=1
```

### Verificar Estado

```bash
# Ver estado de locks
curl http://localhost:8000/cotizaciones/telegram_locks_status

# Verificar otros bots
curl http://localhost:8000/cotizaciones/telegram_check_other_bots

# Forzar limpieza de locks
curl -X POST http://localhost:8000/cotizaciones/telegram_force_cleanup
```

### Script de Diagnóstico

```bash
# Verificar todos los locks
python check_locks.py

# Limpiar locks obsoletos
python check_locks.py --cleanup
```

## 🛡️ Prevención de Múltiples Instancias

### Local
- ✅ Lock de archivo único por hostname
- ✅ Verificación de PID del proceso
- ✅ Detección de otros procesos Python

### Red
- ✅ Puerto TCP exclusivo
- ✅ Verificación de conectividad
- ✅ Detección de bots remotos

### API
- ✅ Verificación de estado del servicio
- ✅ Fallback a modo simple si es necesario
- ✅ Limpieza automática de locks obsoletos

## 📊 Monitoreo y Diagnóstico

### Endpoints de API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/cotizaciones/telegram_locks_status` | GET | Estado de todos los locks |
| `/cotizaciones/telegram_check_other_bots` | GET | Verificar otros bots |
| `/cotizaciones/telegram_force_cleanup` | POST | Limpiar locks obsoletos |

### Script de Verificación

```bash
python check_locks.py
```

**Salida de ejemplo:**
```
🔍 VERIFICANDO LOCKS DEL BOT DE TELEGRAM
==================================================

📁 LOCKS DE ARCHIVO:
   telegram_bot_lock_abc12345_DESKTOP-ABC.lock: PID 1234 (DESKTOP-ABC) - 0.5h - ✅ Activo

🐍 PROCESOS DE PYTHON CON TELEGRAM:
   No se encontraron otros procesos de telegram

🌐 PUERTOS EN USO:
   Puerto 12345 libre

📊 RESUMEN:
====================
   Locks de archivo: 1
   Otros procesos: 0
   Puertos ocupados: 0

💡 RECOMENDACIONES:
   ✅ Todos los locks están activos
```

## 🚨 Solución de Problemas

### Bot no inicia

1. **Verificar configuración**
   ```bash
   python config_bot.py
   ```

2. **Verificar locks**
   ```bash
   python check_locks.py
   ```

3. **Limpiar locks obsoletos**
   ```bash
   python check_locks.py --cleanup
   ```

### Error "Puerto ocupado"

1. **Cambiar puerto de lock**
   ```env
   TELEGRAM_LOCK_PORT=12346
   ```

2. **Verificar qué usa el puerto**
   ```bash
   netstat -ano | findstr :12345
   ```

### Múltiples instancias detectadas

1. **Verificar procesos**
   ```bash
   python check_locks.py
   ```

2. **Terminar procesos duplicados**
   ```bash
   taskkill /PID <PID> /F
   ```

3. **Reiniciar bot**
   ```bash
   curl -X POST http://localhost:8000/cotizaciones/telegram_restart
   ```

## 🔒 Seguridad

- **NUNCA** compartas tu `TELEGRAM_TOKEN`
- **NUNCA** subas el archivo `.env` a Git
- Usa puertos únicos para evitar conflictos
- Verifica regularmente el estado de los locks

## 📝 Logs y Debugging

### Habilitar logs detallados

```env
# Agregar al .env
TELEGRAM_DEBUG=1
```

### Ver logs en tiempo real

```bash
# Si usas uvicorn
uvicorn main:app --host 127.0.0.1 --port 8000 --log-level debug

# Ver logs del sistema
tail -f /var/log/syslog | grep telegram
```

## 🤝 Contribución

Para reportar problemas o sugerir mejoras:

1. Verifica que no sea un problema de configuración
2. Ejecuta `python check_locks.py` y adjunta la salida
3. Incluye logs de error relevantes
4. Describe el entorno (OS, Python version, etc.)

---

**⚠️ IMPORTANTE**: Este sistema está diseñado para ser **100% seguro** contra múltiples instancias. Si tienes problemas, siempre ejecuta `python check_locks.py` primero para diagnosticar.
