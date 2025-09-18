# 📡 Llamadas al WebSocket - Resumen Visual

## 🔄 Flujo de Llamadas al WebSocket

```
Cliente                    WebSocket                    Broker
  │                           │                           │
  │─── 1. CONECTAR ──────────▶│                           │
  │                           │                           │
  │◀─── CONNECTION ───────────│                           │
  │                           │                           │
  │─── 2. SUSCRIBIR ─────────▶│                           │
  │                           │                           │
  │◀─── ORDERS_SUBSCRIBED ────│                           │
  │                           │                           │
  │─── 3. ENVIAR ORDEN ──────▶│─── send_order ──────────▶│
  │                           │                           │
  │◀─── ORDER_ACK ───────────│◀─── order_ack ───────────│
  │                           │                           │
  │◀─── ORDER_REPORT ────────│◀─── order_report ────────│
  │                           │                           │
```

## 📋 Llamadas Específicas

### 1. 🔗 CONEXIÓN
```python
ws = websocket.WebSocketApp("ws://localhost:8000/ws/cotizaciones")
ws.run_forever()
```

### 2. 📋 SUSCRIPCIÓN A ORDER REPORTS
```python
mensaje = {
    "type": "orders_subscribe",
    "account": "mi_cuenta"
}
ws.send(json.dumps(mensaje))
```

### 3. 📤 ENVÍO DE ORDEN CON CLIENT_ORDER_ID
```python
mensaje = {
    "type": "send_order",
    "clOrdId": "MI_ORDEN_001",  # ← Client Order ID
    "order": {
        "symbol": "GGAL",
        "side": "BUY",
        "size": 100,
        "price": 1500.0,
        "order_type": "LIMIT",
        "tif": "DAY"
    }
}
ws.send(json.dumps(mensaje))
```

## 📨 Respuestas Esperadas

### 1. 📤 ORDER_ACK (Confirmación de envío)
```json
{
    "type": "order_ack",
    "request": {
        "symbol": "GGAL",
        "side": "BUY",
        "size": 100,
        "price": 1500.0,
        "order_type": "LIMIT",
        "tif": "DAY",
        "client_order_id": "MI_ORDEN_001"
    },
    "result": {
        "status": "ok",
        "response": {
            "orderId": "12345",
            "status": "NEW"
        }
    }
}
```

### 2. 📋 ORDER_REPORT (Reporte del broker)
```json
{
    "type": "order_report",
    "report": {
        "clOrdId": "MI_ORDEN_001",  // ← El mismo client_order_id regresa
        "orderId": "12345",
        "status": "NEW",
        "side": "BUY",
        "size": 100,
        "price": 1500.0,
        "instrument": {
            "symbol": "GGAL"
        },
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

## 🎯 Puntos Clave

1. **Client Order ID**: Se envía en el campo `clOrdId` del mensaje
2. **Preservación**: El broker devuelve el mismo ID en el campo `clOrdId` del reporte
3. **Tracking**: Permite correlacionar órdenes enviadas con reportes recibidos
4. **Múltiples órdenes**: Cada orden puede tener su propio `client_order_id` único

## 🔧 Código de Ejemplo Completo

```python
import websocket
import json
import time

def procesar_ordenes():
    client_order_id = "MI_ORDEN_001"
    
    def on_message(ws, message):
        data = json.loads(message)
        
        if data.get("type") == "order_ack":
            print(f"✅ Orden confirmada: {data['request']['client_order_id']}")
            
        elif data.get("type") == "order_report":
            report = data["report"]
            client_id = report.get("clOrdId")
            if client_id == client_order_id:
                print(f"📋 Reporte recibido para orden: {client_id}")
    
    def on_open(ws):
        # Suscribirse a order reports
        ws.send(json.dumps({
            "type": "orders_subscribe",
            "account": "mi_cuenta"
        }))
        
        # Enviar orden con client_order_id
        ws.send(json.dumps({
            "type": "send_order",
            "clOrdId": client_order_id,
            "order": {
                "symbol": "GGAL",
                "side": "BUY",
                "size": 100,
                "price": 1500.0,
                "order_type": "LIMIT",
                "tif": "DAY"
            }
        }))
    
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/ws/cotizaciones",
        on_open=on_open,
        on_message=on_message
    )
    
    ws.run_forever()

# Ejecutar
procesar_ordenes()
```
