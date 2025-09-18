# 🔄 ACTUALIZACIÓN: Campo Real del Broker - wsClOrdId

## 📋 Cambios Realizados

### ✅ **Campo Real del Broker**
El broker devuelve el Client Order ID en el campo **`wsClOrdId`**, no en `clOrdId` como se pensaba inicialmente.

### 🔧 **Código Actualizado**

#### 1. **ws_rofex.py** - Manejo de Order Reports
```python
def _handle_or(self, message: Dict[str, Any]):
    # Log del order report para debugging
    client_order_id = (message.get("wsClOrdId") or 
                     message.get("clOrdId") or 
                     message.get("clientId") or 
                     message.get("client_order_id"))
    if client_order_id:
        print(f"Order report recibido - Client Order ID: {client_order_id}")
```

#### 2. **ws_rofex.py** - Envío de Órdenes
```python
if client_order_id is not None:
    # Prioridad: wsClOrdId (real del broker) → clientId → clOrdId → client_order_id
    if hasattr(pr, 'wsClOrdId'):
        kwargs["wsClOrdId"] = str(client_order_id)
    elif hasattr(pr, 'clientId'):
        kwargs["clientId"] = str(client_order_id)
    # ... otros campos
```

#### 3. **Ejemplos Actualizados**
Todos los ejemplos ahora buscan el Client Order ID en este orden:
1. `wsClOrdId` (campo real del broker)
2. `clOrdId` (estándar FIX)
3. `clientId` (alternativo)
4. `client_order_id` (genérico)

### 📊 **Formato Real del Order Report**

```json
{
  "instrumentId": {
    "marketId": "ROFX",
    "symbol": "MERV - XMEV - TX28 - 24hs"
  },
  "price": 1,
  "orderQty": 1,
  "ordType": "LIMIT",
  "side": "BUY",
  "timeInForce": "DAY",
  "transactTime": "20250918-16:18:02.634-0300",
  "status": "PENDING_NEW",
  "text": "Enviada",
  "wsClOrdId": "Client Order ID"  ← Campo real del broker
}
```

### 🎯 **Flujo Actualizado**

1. **Cliente → Backend**: Envía orden con `client_order_id`
2. **Backend → Broker**: Intenta enviar como `wsClOrdId` (o fallback a otros campos)
3. **Broker → Backend**: Devuelve order report con `wsClOrdId`
4. **Backend → Cliente**: Preserva y devuelve el order report con `wsClOrdId`

### 🔑 **Campos Clave Actualizados**

- **`wsClOrdId`**: Campo real del broker para Client Order ID
- **`clOrdId`**: Campo alternativo (estándar FIX)
- **`clientId`**: Campo alternativo común
- **`client_order_id`**: Campo genérico de fallback

### 📁 **Archivos Actualizados**

1. **`ws_rofex.py`** - Lógica principal del WebSocket
2. **`ejemplo_simple_ws.py`** - Ejemplos básicos
3. **`formatos_mensajes_completos.py`** - Documentación de formatos
4. **`formatos_mensajes.json`** - Referencia JSON
5. **`ejemplo_formato_real_broker.py`** - Ejemplo con formato real

### ✅ **Compatibilidad**

El código mantiene compatibilidad con múltiples campos para asegurar que funcione independientemente de cómo el broker devuelva el Client Order ID.

### 🚀 **Uso en Producción**

```python
def extract_client_order_id(report):
    """Extraer client_order_id del reporte del broker"""
    return (report.get("wsClOrdId") or 
            report.get("clOrdId") or 
            report.get("clientId") or 
            report.get("client_order_id"))

# En el handler de order reports
client_id = extract_client_order_id(report)
if client_id == my_sent_order_id:
    print(f"✅ Reporte de nuestra orden: {client_id}")
```

## 🎉 **Resultado**

El soporte para `client_order_id` ahora funciona correctamente con el formato real del broker, permitiendo el tracking completo de órdenes desde el cliente hasta el broker y de vuelta.
