# 🔧 CORRECCIÓN: Estado Real de Órdenes en Operaciones de Ratio

## 🚨 **Problema Identificado**

El sistema estaba marcando las operaciones de ratio como "completed" basándose únicamente en que las órdenes fueron aceptadas por el broker (respuesta "ok"), pero **no verificaba el estado real de las órdenes en el mercado**.

### **Síntomas:**
- Operación reportada como "completed" con `status: "completed"`
- Pero las órdenes individuales (TX28, TX26) quedaban **pendientes** en el broker
- El sistema asumía que `status: "ok"` del broker = orden ejecutada
- En realidad, `status: "ok"` solo significa que la orden fue **aceptada**, no **ejecutada**

## 🔧 **Solución Implementada**

### **1. Verificación Real del Estado de Órdenes**

#### **Función `_verify_order_status()`:**
```python
async def _verify_order_status(self, operation_id: str, client_order_id: str, order_execution: OrderExecution) -> str:
    """Verifica el estado real de una orden consultando los order reports"""
    # Intentar múltiples veces para obtener el order report correcto
    max_attempts = 5
    for attempt in range(max_attempts):
        last_report = ws_rofex.manager.last_order_report()
        
        if last_report and report_client_id == client_order_id:
            order_status = last_report.get('status', 'UNKNOWN')
            
            # Mapear estados del broker a estados internos
            if order_status in ['FILLED', 'PARTIALLY_FILLED']:
                order_execution.status = "filled"
            elif order_status in ['PENDING_NEW', 'NEW', 'PENDING_CANCEL']:
                order_execution.status = "pending"
            elif order_status in ['CANCELLED', 'REJECTED']:
                order_execution.status = "rejected"
```

#### **Función `_verify_all_orders_status()`:**
```python
async def _verify_all_orders_status(self, operation_id: str, progress: OperationProgress):
    """Verifica el estado de todas las órdenes de una operación"""
    # Verificar todas las órdenes de venta y compra
    # Contar órdenes por estado (ejecutadas vs pendientes)
```

### **2. Cambio en la Lógica de Ejecución**

#### **Antes:**
```python
if result and result.get('status') == 'ok':
    order_execution = OrderExecution(
        # ...
        status="filled"  # ❌ Asumía que estaba ejecutada
    )
```

#### **Después:**
```python
if result and result.get('status') == 'ok':
    order_execution = OrderExecution(
        # ...
        status="pending"  # ✅ Asume que está pendiente hasta verificar
    )
    
    # Esperar y verificar el estado real de la orden
    await asyncio.sleep(2)
    real_status = await self._verify_order_status(operation_id, client_order_id, order_execution)
```

### **3. Lógica de Completado Actualizada**

#### **Antes:**
```python
if progress.remaining_nominales <= 0:
    progress.status = OperationStatus.COMPLETED  # ❌ Solo basado en cantidad
```

#### **Después:**
```python
# Verificar estado real de todas las órdenes antes de finalizar
await self._verify_all_orders_status(operation_id, progress)

all_orders_filled = True
for sell_order in progress.sell_orders:
    if sell_order.status != "filled":
        all_orders_filled = False

# Determinar estado final basado en órdenes realmente ejecutadas
if all_orders_filled and progress.remaining_nominales <= 0:
    progress.status = OperationStatus.COMPLETED  # ✅ Solo si todas están ejecutadas
elif progress.remaining_nominales <= 0:
    progress.status = OperationStatus.PARTIALLY_COMPLETED  # ✅ Órdenes pendientes
```

## 📊 **Estados de Órdenes Mapeados**

| Estado ROFEX | Estado Interno | Significado |
|--------------|----------------|-------------|
| `FILLED` | `filled` | ✅ Orden ejecutada completamente |
| `PARTIALLY_FILLED` | `filled` | ✅ Orden ejecutada parcialmente |
| `PENDING_NEW` | `pending` | ⏳ Orden pendiente de ejecución |
| `NEW` | `pending` | ⏳ Orden nueva, pendiente |
| `PENDING_CANCEL` | `pending` | ⏳ Orden pendiente de cancelación |
| `CANCELLED` | `rejected` | ❌ Orden cancelada |
| `REJECTED` | `rejected` | ❌ Orden rechazada |

## 🎯 **Resultado Esperado**

### **Antes de la Corrección:**
```json
{
  "type": "ratio_operation_progress",
  "status": "completed",  // ❌ Incorrecto - órdenes pendientes
  "messages": [
    "✅ OPERACIÓN COMPLETADA EXITOSAMENTE"
  ]
}
```

### **Después de la Corrección:**
```json
{
  "type": "ratio_operation_progress",
  "status": "partially_completed",  // ✅ Correcto - órdenes pendientes
  "messages": [
    "🔍 VERIFICANDO ESTADO REAL DE TODAS LAS ÓRDENES...",
    "📊 Estado real de orden op_cdaabfbd5c38_sell_165724: PENDING_NEW",
    "📊 Estado real de orden op_cdaabfbd5c38_buy_165725: PENDING_NEW",
    "⏳ Orden op_cdaabfbd5c38_sell_165724 PENDIENTE en el mercado",
    "⏳ Orden op_cdaabfbd5c38_buy_165725 PENDIENTE en el mercado",
    "⚠️ OPERACIÓN PARCIALMENTE COMPLETADA - ÓRDENES PENDIENTES:",
    "   ⏳ Venta op_cdaabfbd5c38_sell_165724: pending",
    "   ⏳ Compra op_cdaabfbd5c38_buy_165725: pending"
  ]
}
```

## 🧪 **Prueba de la Corrección**

### **Script de Prueba:**
```bash
python test_order_status_fix.py
```

### **Qué Verifica:**
1. ✅ El sistema envía órdenes al broker
2. ✅ El sistema verifica el estado real de las órdenes
3. ✅ El sistema reporta correctamente si las órdenes están pendientes
4. ✅ El sistema no marca como "completed" si hay órdenes pendientes
5. ✅ Los mensajes indican claramente el estado real de cada orden

## 🔄 **Flujo Corregido**

1. **Envío de Orden** → Broker acepta (`status: "ok"`)
2. **Verificación Inicial** → Consulta order report del broker
3. **Mapeo de Estado** → Convierte estado ROFEX a estado interno
4. **Verificación Final** → Revisa todas las órdenes antes de completar
5. **Estado Correcto** → Solo marca "completed" si todas están ejecutadas

## ✅ **Beneficios de la Corrección**

1. **Transparencia Real** → El usuario ve el estado real de sus órdenes
2. **Prevención de Errores** → No se asume que las órdenes están ejecutadas
3. **Mejor UX** → Mensajes claros sobre el estado de cada orden
4. **Confiabilidad** → El sistema refleja la realidad del mercado
5. **Debugging** → Fácil identificar órdenes pendientes vs ejecutadas

## 🚀 **Próximos Pasos**

1. **Probar** la corrección con operaciones reales
2. **Monitorear** el comportamiento en producción
3. **Ajustar** timeouts si es necesario
4. **Documentar** casos edge adicionales
5. **Implementar** notificaciones para órdenes pendientes
