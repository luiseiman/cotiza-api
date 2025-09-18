# Ejemplo de uso de Client Order ID

## Descripción
El `client_order_id` permite rastrear órdenes desde el cliente hasta el broker y recibir el mismo ID en los order reports, facilitando la correlación entre órdenes enviadas y confirmaciones recibidas.

## Cambios implementados

### 1. Modelo SendOrderRequest actualizado
```python
class SendOrderRequest(BaseModel):
    symbol: str
    side: str  # BUY/SELL
    size: float
    price: float | None = None
    order_type: str = "LIMIT"  # LIMIT/MARKET
    tif: str = "DAY"           # DAY/IOC/FOK (si aplica)
    market: str | None = None
    client_order_id: str | None = None  # ID único del cliente para tracking
```

### 2. Endpoint REST actualizado
El endpoint `/cotizaciones/orders/send` ahora acepta y pasa el `client_order_id` al broker.

### 3. WebSocket actualizado
El WebSocket ya soportaba `client_order_id` vía el campo `clOrdId` en los mensajes.

## Ejemplos de uso

### REST API
```python
import requests

# Enviar orden con client_order_id
order_data = {
    "symbol": "GGAL",
    "side": "BUY", 
    "size": 100,
    "price": 1500.0,
    "order_type": "LIMIT",
    "tif": "DAY",
    "client_order_id": "MY_ORDER_001"  # ID único del cliente
}

response = requests.post("http://localhost:8000/cotizaciones/orders/send", 
                        json=order_data)
print(response.json())

# Obtener último order report
response = requests.get("http://localhost:8000/cotizaciones/orders/last_report")
report = response.json()["report"]

# El client_order_id debería estar en uno de estos campos:
client_id = (report.get("clOrdId") or 
             report.get("clientId") or 
             report.get("client_order_id"))
print(f"Client Order ID recibido: {client_id}")
```

### WebSocket
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/cotizaciones");

ws.onopen = function() {
    // Suscribirse a order reports
    ws.send(JSON.stringify({
        "type": "orders_subscribe",
        "account": "mi_cuenta"
    }));
    
    // Enviar orden con client_order_id
    ws.send(JSON.stringify({
        "type": "send_order",
        "clOrdId": "WS_ORDER_001",  // Client Order ID
        "order": {
            "symbol": "GGAL",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "order_type": "LIMIT",
            "tif": "DAY"
        }
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === "order_report") {
        const report = data.report;
        const client_id = report.clOrdId || report.clientId || report.client_order_id;
        console.log(`Order report recibido con Client Order ID: ${client_id}`);
    }
};
```

## Flujo completo

1. **Cliente envía orden** con `client_order_id` único
2. **Backend recibe** la orden y pasa el `client_order_id` al broker
3. **Broker procesa** la orden y puede usar el `client_order_id` internamente
4. **Broker envía order_report** con el mismo `client_order_id` (en campo `clOrdId`, `clientId`, o `client_order_id`)
5. **Backend recibe** el order_report y lo preserva sin modificar
6. **Cliente recibe** el order_report con el mismo `client_order_id` que envió

## Campos del Order Report

El broker puede devolver el `client_order_id` en cualquiera de estos campos:
- `clOrdId` (estándar FIX)
- `clientId` (nombre común)
- `client_order_id` (genérico)

El código maneja automáticamente estos diferentes nombres de campo.

## Testing

Ejecutar el script de prueba:
```bash
python test_client_order_id.py
```

Este script verifica:
- Envío de orden con `client_order_id` vía REST
- Recepción de order_report con el mismo ID
- Funcionamiento vía WebSocket
- Preservación del ID a través del flujo completo
