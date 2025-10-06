# 📊 Mensajería Completa para Operaciones de Ratios

## 🔗 Conexión WebSocket

**Endpoint:** `ws://localhost:8000/ws/cotizaciones`

### Mensaje de Bienvenida
```json
{
  "type": "connection",
  "status": "connected",
  "timestamp": 1759761110.460844,
  "message": "Conexión WebSocket establecida"
}
```

---

## 🚀 Iniciar Operación de Ratio

### Comando para Iniciar (Formato Recomendado - Array)
```json
{
  "action": "start_ratio_operation",
  "pair": [
    "MERV - XMEV - TX26 - 24hs",
    "MERV - XMEV - TX28 - 24hs"
  ],
  "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
  "nominales": 100.0,
  "target_ratio": 0.95,
  "condition": "<=",
  "client_id": "test_client_002"
}
```

### Comando para Iniciar (Formato Legacy - String)
```json
{
  "action": "start_ratio_operation",
  "pair": "MERV - XMEV - TX26 - 24hs-MERV - XMEV - TX28 - 24hs",
  "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
  "nominales": 100.0,
  "target_ratio": 0.95,
  "condition": "<=",
  "client_id": "test_client_002"
}
```

### Respuesta de Inicio
```json
{
  "type": "ratio_operation_started",
  "operation_id": "RATIO_a1b2c3d4",
  "message": "Operación de ratio iniciada: TX26-TX28",
  "timestamp": 1759761110.465616
}
```

---

## 📈 Progreso de la Operación

### Estructura del Progreso
```json
{
  "type": "ratio_operation_progress",
  "operation_id": "RATIO_a1b2c3d4",
  "status": "running",
  "current_step": "analyzing_market",
  "progress_percentage": 20,
  "current_ratio": 0.0,
  "target_ratio": 0.95,
  "condition_met": false,
  "average_sell_price": 0.0,
  "average_buy_price": 0.0,
  "total_sold_amount": 0.0,
  "total_bought_amount": 0.0,
  "sell_orders_count": 0,
  "buy_orders_count": 0,
  "messages": [
    "[11:34:22] Iniciando operación de ratio: TX26-TX28",
    "[11:34:22] Vender: TX26, Nominales: 100.0"
  ],
  "error": null,
  "timestamp": 1759761111.466885
}
```

### Estados de la Operación
- **`pending`**: Operación en cola
- **`running`**: Operación en ejecución
- **`completed`**: Operación completada exitosamente
- **`failed`**: Operación falló
- **`cancelled`**: Operación cancelada

### Pasos de la Operación
1. **`initializing`** (5%): Inicializando operación
2. **`analyzing_market`** (10%): Analizando condiciones del mercado
3. **`placing_sell_order`** (15%): Colocando orden de venta
4. **`waiting_sell_execution`** (25%): Esperando ejecución de venta
5. **`sell_executed`** (35%): Venta ejecutada
6. **`calculating_buy_amount`** (45%): Calculando monto de compra
7. **🔍 VALIDACIÓN CRÍTICA**: Verificando ratio teórico ANTES de comprar
8. **`placing_buy_order`** (55%): Colocando orden de compra (solo si ratio cumple condición)
9. **`waiting_buy_execution`** (75%): Esperando ejecución de compra
10. **`buy_executed`** (85%): Compra ejecutada
11. **`verifying_ratio`** (95%): Verificando ratio final
12. **`finalizing`** (100%): Finalizando operación

### 🛡️ **Nueva Lógica de Protección:**
- **ANTES**: Ejecutaba venta → ejecutaba compra → verificaba ratio ❌
- **AHORA**: Ejecuta venta → verifica ratio teórico → solo compra si cumple condición ✅

### ♾️ **Intentos Infinitos:**
- **Sin límite**: El sistema intenta indefinidamente hasta completar todos los nominales
- **Cancelación manual**: Solo se detiene cuando se ordena cancelar explícitamente
- **Persistencia**: Continúa esperando mejores condiciones de mercado sin límite de tiempo

---

## 📋 Mensajes de Progreso Detallados

### Ejemplo Completo de Progreso
```json
{
  "type": "ratio_operation_progress",
  "operation_id": "RATIO_a1b2c3d4",
  "status": "running",
  "current_step": "sell_executed",
  "progress_percentage": 35,
  "current_ratio": 0.0,
  "target_ratio": 0.95,
  "condition_met": false,
  "average_sell_price": 245.5,
  "average_buy_price": 0.0,
  "total_sold_amount": 24550.0,
  "total_bought_amount": 0.0,
  "sell_orders_count": 1,
  "buy_orders_count": 0,
  "messages": [
    "[11:34:22] Iniciando operación de ratio: TX26-TX28",
    "[11:34:22] Vender: TX26, Nominales: 100.0",
    "[11:34:22] Ratio objetivo: 0.95 <=",
    "[11:34:23] Analizando condiciones del mercado...",
    "[11:34:23] ✅ Cotizaciones obtenidas exitosamente",
    "[11:34:23] Instrumento a comprar: TX28",
    "[11:34:23] Venta - Bid: 245.5, Offer: 246.0",
    "[11:34:23] Compra - Bid: 258.8, Offer: 259.3",
    "[11:34:24] Colocando orden de venta: 100.0 nominales de TX26",
    "[11:34:24] Orden de venta colocada: RATIO_SELL_a1b2c3d4_1759761264 @ 245.5",
    "[11:34:24] Esperando ejecución de orden de venta...",
    "[11:34:26] Venta ejecutada: 100.0 @ 245.5",
    "[11:34:26] Monto total de venta: $24,550.00"
  ],
  "error": null,
  "timestamp": 1759761126.123456
}
```

---

## ✅ Operación Completada

### Mensaje Final Exitoso
```json
{
  "type": "ratio_operation_progress",
  "operation_id": "RATIO_a1b2c3d4",
  "status": "completed",
  "current_step": "finalizing",
  "progress_percentage": 100,
  "current_ratio": 0.95,
  "target_ratio": 0.95,
  "condition_met": true,
  "average_sell_price": 245.5,
  "average_buy_price": 259.3,
  "total_sold_amount": 24550.0,
  "total_bought_amount": 24550.0,
  "sell_orders_count": 1,
  "buy_orders_count": 1,
  "messages": [
    "[11:34:22] Iniciando operación de ratio: TX26-TX28",
    "[11:34:22] Vender: TX26, Nominales: 100.0",
    "[11:34:22] Ratio objetivo: 0.95 <=",
    "[11:34:23] Analizando condiciones del mercado...",
    "[11:34:23] ✅ Cotizaciones obtenidas exitosamente",
    "[11:34:23] Instrumento a comprar: TX28",
    "[11:34:23] Venta - Bid: 245.5, Offer: 246.0",
    "[11:34:23] Compra - Bid: 258.8, Offer: 259.3",
    "[11:34:24] Colocando orden de venta: 100.0 nominales de TX26",
    "[11:34:24] Orden de venta colocada: RATIO_SELL_a1b2c3d4_1759761264 @ 245.5",
    "[11:34:24] Esperando ejecución de orden de venta...",
    "[11:34:26] Venta ejecutada: 100.0 @ 245.5",
    "[11:34:26] Monto total de venta: $24,550.00",
    "[11:34:27] Calculando compra: $24,550.00 / 259.3 = 94.68 nominales",
    "[11:34:27] Colocando orden de compra: 94.68 nominales de TX28",
    "[11:34:27] Orden de compra colocada: RATIO_BUY_a1b2c3d4_1759761267 @ 259.3",
    "[11:34:27] Esperando ejecución de orden de compra...",
    "[11:34:29] Compra ejecutada: 94.68 @ 259.3",
    "[11:34:29] Monto total de compra: $24,550.00",
    "[11:34:30] Ratio calculado: 0.950000",
    "[11:34:30] Ratio objetivo: 0.95 <=",
    "[11:34:30] Condición cumplida: ✅ SÍ",
    "[11:34:30] ✅ Operación completada exitosamente"
  ],
  "error": null,
  "timestamp": 1759761130.789012
}
```

---

## ❌ Errores Comunes

### Error de Parámetros Faltantes
```json
{
  "type": "ratio_operation_error",
  "error": "Parámetros faltantes: pair, instrument_to_sell",
  "timestamp": 1759761110.465616
}
```

### Error de Cotizaciones
```json
{
  "type": "ratio_operation_error",
  "error": "No se pudieron obtener cotizaciones para: TX26, TX28. Verifique que el WebSocket esté conectado y suscrito a estos instrumentos.",
  "timestamp": 1759761110.465616
}
```

### Error de Orden
```json
{
  "type": "ratio_operation_error",
  "error": "Error colocando orden de venta: Insufficient funds",
  "timestamp": 1759761110.465616
}
```

### ✅ Nuevo Comportamiento: Cancelación Preventiva
```json
{
  "type": "ratio_operation_progress",
  "operation_id": "RATIO_a1b2c3d4",
  "status": "failed",
  "current_step": "finalizing",
  "progress_percentage": 45,
  "current_ratio": 0.0,
  "target_ratio": 0.90,
  "condition_met": false,
  "sell_orders_count": 1,
  "buy_orders_count": 0,
  "error": "Ratio teórico 0.975682 no cumple condición <= 0.90. No se ejecutará la compra para evitar pérdidas.",
  "messages": [
    "[11:52:37] Venta ejecutada: 100.0 @ 1484.5",
    "[11:52:37] Monto total de venta: $148,450.00",
    "[11:52:37] Calculando compra: $148,450.00 / 1521.5 = 97.57 nominales",
    "[11:52:37] 🔍 Verificando ratio teórico antes de comprar...",
    "[11:52:37] Ratio teórico: 0.975682",
    "[11:52:37] Ratio objetivo: 0.90 <=",
    "[11:52:37] Condición cumplida: ❌ NO",
    "[11:52:37] ❌ Operación cancelada: Ratio teórico 0.975682 no cumple condición <= 0.90. No se ejecutará la compra para evitar pérdidas."
  ],
  "timestamp": 1759761137.789012
}
```

### ❌ Comportamiento Anterior (Problemático)
```json
{
  "type": "ratio_operation_progress",
  "operation_id": "RATIO_a1b2c3d4",
  "status": "failed",
  "current_step": "finalizing",
  "progress_percentage": 100,
  "current_ratio": 0.98,
  "target_ratio": 0.95,
  "condition_met": false,
  "sell_orders_count": 1,
  "buy_orders_count": 1,
  "error": "Ratio 0.980000 no cumple condición <= 0.95",
  "messages": [
    "[11:34:30] Venta ejecutada: 100.0 @ 1484.5",
    "[11:34:30] Compra ejecutada: 97.57 @ 1521.5",
    "[11:34:30] Ratio calculado: 0.980000",
    "[11:34:30] Ratio objetivo: 0.95 <=",
    "[11:34:30] Condición cumplida: ❌ NO",
    "[11:34:30] ❌ Operación fallida: Ratio 0.980000 no cumple condición <= 0.95"
  ],
  "timestamp": 1759761130.789012
}
```

---

## 🔍 Consultar Estado de Operación

### Comando para Consultar
```json
{
  "action": "get_ratio_operation_status",
  "operation_id": "RATIO_a1b2c3d4"
}
```

### Respuesta de Estado
```json
{
  "type": "ratio_operation_status",
  "operation_id": "RATIO_a1b2c3d4",
  "status": "running",
  "current_step": "waiting_buy_execution",
  "progress_percentage": 75,
  "current_ratio": 0.0,
  "target_ratio": 0.95,
  "condition_met": false,
  "average_sell_price": 245.5,
  "average_buy_price": 0.0,
  "total_sold_amount": 24550.0,
  "total_bought_amount": 0.0,
  "sell_orders_count": 1,
  "buy_orders_count": 0,
  "messages": [
    "[11:34:22] Iniciando operación de ratio: TX26-TX28",
    "[11:34:26] Venta ejecutada: 100.0 @ 245.5"
  ],
  "error": null,
  "start_time": "2025-01-19T11:34:22",
  "last_update": "2025-01-19T11:34:27",
  "timestamp": 1759761127.123456
}
```

---

## 🛑 Cancelar Operación

### Comando para Cancelar
```json
{
  "action": "cancel_ratio_operation",
  "operation_id": "RATIO_a1b2c3d4"
}
```

### Respuesta de Cancelación
```json
{
  "type": "ratio_operation_cancelled",
  "operation_id": "RATIO_a1b2c3d4",
  "message": "Operación cancelada exitosamente",
  "timestamp": 1759761127.123456
}
```

---

## 📋 Listar Todas las Operaciones

### Comando para Listar
```json
{
  "action": "list_ratio_operations"
}
```

### Respuesta de Lista
```json
{
  "type": "ratio_operations_list",
  "operations": [
    {
      "operation_id": "RATIO_a1b2c3d4",
      "status": "completed",
      "current_step": "finalizing",
      "progress_percentage": 100,
      "current_ratio": 0.95,
      "target_ratio": 0.95,
      "condition_met": true,
      "start_time": "2025-01-19T11:34:22",
      "last_update": "2025-01-19T11:34:30",
      "error": null
    },
    {
      "operation_id": "RATIO_b2c3d4e5",
      "status": "running",
      "current_step": "placing_sell_order",
      "progress_percentage": 15,
      "current_ratio": 0.0,
      "target_ratio": 1.05,
      "condition_met": false,
      "start_time": "2025-01-19T11:35:00",
      "last_update": "2025-01-19T11:35:02",
      "error": null
    }
  ],
  "count": 2,
  "timestamp": 1759761127.123456
}
```

---

## 🎯 Otros Comandos Útiles

### Verificar Estado del WebSocket
```json
{
  "action": "check_ws_status"
}
```

### Verificar Cotizaciones Disponibles
```json
{
  "action": "check_quotes"
}
```

### Ping/Pong
```json
{
  "action": "ping"
}
```

### Respuesta Pong
```json
{
  "type": "pong",
  "timestamp": 1759761110.460844
}
```

---

## 📝 Notas Importantes

### 🆕 Formato de Pares Recomendado (Array)
```json
{
  "pair": [
    "MERV - XMEV - TX26 - 24hs",
    "MERV - XMEV - TX28 - 24hs"
  ]
}
```

**Ventajas del formato array:**
- ✅ **Sin ambigüedad**: No hay problemas de parsing con guiones internos
- ✅ **Más claro**: Cada instrumento está claramente definido
- ✅ **Más robusto**: Elimina errores de formato
- ✅ **Fácil validación**: Se puede verificar fácilmente que hay exactamente 2 instrumentos

### 📜 Formato Legacy (String)
```json
{
  "pair": "MERV - XMEV - TX26 - 24hs-MERV - XMEV - TX28 - 24hs"
}
```

**Notas adicionales:**
1. **Condiciones**: Solo se soportan `<=` y `>=`
2. **Client ID**: Debe ser único para cada cliente
3. **Operation ID**: Se genera automáticamente con formato `RATIO_[8_caracteres_hex]`
4. **Mensajes**: Se mantienen los últimos 50 mensajes por operación
5. **Cleanup**: Las operaciones se eliminan automáticamente después de 5 minutos
6. **WebSocket**: Debe estar conectado y suscrito a los instrumentos antes de iniciar operaciones

---

## 🔧 Ejemplo de Cliente Python

```python
import asyncio
import websockets
import json

async def ratio_operation_client():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        # Recibir mensaje de bienvenida
        welcome = await ws.recv()
        print("Conexión:", welcome)
        
        # Iniciar operación de ratio
        await ws.send(json.dumps({
            "action": "start_ratio_operation",
            "pair": "TX26-TX28",
            "instrument_to_sell": "TX26",
            "nominales": 100.0,
            "target_ratio": 0.95,
            "condition": "<=",
            "client_id": "mi_cliente_001"
        }))
        
        # Escuchar progreso
        while True:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(message)
                print(f"[{data['type']}] {data.get('message', '')}")
                
                if data['type'] == 'ratio_operation_progress':
                    if data['status'] in ['completed', 'failed']:
                        break
            except asyncio.TimeoutError:
                print("Timeout esperando mensajes")
                break

if __name__ == "__main__":
    asyncio.run(ratio_operation_client())
```
