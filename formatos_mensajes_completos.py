#!/usr/bin/env python3
"""
Formato completo de todos los mensajes del WebSocket
"""

import json

def mostrar_formatos_mensajes():
    """Mostrar el formato de todos los mensajes del WebSocket"""
    
    print("📡 FORMATO COMPLETO DE MENSAJES DEL WEBSOCKET\n")
    print("="*60)
    
    # ============================================================================
    # 1. MENSAJES DE CONEXIÓN
    # ============================================================================
    
    print("\n1. 🔗 MENSAJES DE CONEXIÓN")
    print("-" * 30)
    
    print("\n   a) Mensaje de bienvenida (servidor → cliente):")
    conexion = {
        "type": "connection",
        "status": "connected",
        "timestamp": 1642248600.0,
        "message": "Conexión WebSocket establecida"
    }
    print(f"   {json.dumps(conexion, indent=2, ensure_ascii=False)}")
    
    print("\n   b) Mensaje de ping (cliente → servidor):")
    ping = {
        "type": "ping",
        "timestamp": 1642248600.0
    }
    print(f"   {json.dumps(ping, indent=2, ensure_ascii=False)}")
    
    print("\n   c) Mensaje de pong (servidor → cliente):")
    pong = {
        "type": "pong",
        "timestamp": 1642248600.0
    }
    print(f"   {json.dumps(pong, indent=2, ensure_ascii=False)}")
    
    # ============================================================================
    # 2. MENSAJES DE SUSCRIPCIÓN
    # ============================================================================
    
    print("\n\n2. 📋 MENSAJES DE SUSCRIPCIÓN")
    print("-" * 30)
    
    print("\n   a) Suscribirse a cotizaciones (cliente → servidor):")
    subscribe_tickers = {
        "type": "subscribe",
        "instruments": ["GGAL", "PAMP", "ALUA"]
    }
    print(f"   {json.dumps(subscribe_tickers, indent=2, ensure_ascii=False)}")
    
    print("\n   b) Confirmación de suscripción (servidor → cliente):")
    subscribed = {
        "type": "subscribed",
        "instruments": ["GGAL", "PAMP", "ALUA"],
        "timestamp": 1642248600.0
    }
    print(f"   {json.dumps(subscribed, indent=2, ensure_ascii=False)}")
    
    print("\n   c) Suscribirse a order reports (cliente → servidor):")
    subscribe_orders = {
        "type": "orders_subscribe",
        "account": "mi_cuenta"
    }
    print(f"   {json.dumps(subscribe_orders, indent=2, ensure_ascii=False)}")
    
    print("\n   d) Confirmación de suscripción a orders (servidor → cliente):")
    orders_subscribed = {
        "type": "orders_subscribed",
        "account": "mi_cuenta",
        "result": {
            "status": "ok"
        }
    }
    print(f"   {json.dumps(orders_subscribed, indent=2, ensure_ascii=False)}")
    
    # ============================================================================
    # 3. MENSAJES DE COTIZACIONES (MARKET DATA)
    # ============================================================================
    
    print("\n\n3. 📊 MENSAJES DE COTIZACIONES (MARKET DATA)")
    print("-" * 30)
    
    print("\n   a) Tick de cotización (servidor → cliente):")
    tick = {
        "type": "tick",
        "symbol": "GGAL",
        "bid": 1500.0,
        "bid_size": 1000,
        "offer": 1501.0,
        "offer_size": 500,
        "last": 1500.5,
        "last_size": 200,
        "ts_ms": 1642248600000
    }
    print(f"   {json.dumps(tick, indent=2, ensure_ascii=False)}")
    
    # ============================================================================
    # 4. MENSAJES DE ÓRDENES
    # ============================================================================
    
    print("\n\n4. 📤 MENSAJES DE ÓRDENES")
    print("-" * 30)
    
    print("\n   a) Enviar orden (cliente → servidor):")
    send_order = {
        "type": "send_order",
        "clOrdId": "MI_ORDEN_001",  # Client Order ID
        "order": {
            "symbol": "GGAL",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "order_type": "LIMIT",
            "tif": "DAY",
            "market": "ROFEX"
        }
    }
    print(f"   {json.dumps(send_order, indent=2, ensure_ascii=False)}")
    
    print("\n   b) Confirmación de orden enviada (servidor → cliente):")
    order_ack = {
        "type": "order_ack",
        "request": {
            "symbol": "GGAL",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "order_type": "LIMIT",
            "tif": "DAY",
            "market": "ROFEX",
            "client_order_id": "MI_ORDEN_001"
        },
        "result": {
            "status": "ok",
            "response": {
                "orderId": "12345",
                "status": "NEW",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    }
    print(f"   {json.dumps(order_ack, indent=2, ensure_ascii=False)}")
    
    print("\n   c) Reporte de orden del broker (servidor → cliente):")
    order_report = {
        "type": "order_report",
        "report": {
            "wsClOrdId": "MI_ORDEN_001",  # El mismo Client Order ID regresa en wsClOrdId
            "orderId": "12345",
            "status": "NEW",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "instrument": {
                "symbol": "GGAL",
                "marketId": "ROFEX"
            },
            "timestamp": "2024-01-15T10:30:00Z",
            "account": "mi_cuenta",
            "timeInForce": "DAY",
            "orderType": "LIMIT"
        }
    }
    print(f"   {json.dumps(order_report, indent=2, ensure_ascii=False)}")
    
    print("\n   d) Reporte de orden parcialmente ejecutada:")
    order_report_partial = {
        "type": "order_report",
        "report": {
            "wsClOrdId": "MI_ORDEN_001",
            "orderId": "12345",
            "status": "PARTIALLY_FILLED",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "filledSize": 50,
            "remainingSize": 50,
            "lastFillPrice": 1500.0,
            "instrument": {
                "symbol": "GGAL",
                "marketId": "ROFEX"
            },
            "timestamp": "2024-01-15T10:31:00Z",
            "account": "mi_cuenta"
        }
    }
    print(f"   {json.dumps(order_report_partial, indent=2, ensure_ascii=False)}")
    
    print("\n   e) Reporte de orden completamente ejecutada:")
    order_report_filled = {
        "type": "order_report",
        "report": {
            "wsClOrdId": "MI_ORDEN_001",
            "orderId": "12345",
            "status": "FILLED",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "filledSize": 100,
            "remainingSize": 0,
            "lastFillPrice": 1500.0,
            "averagePrice": 1500.0,
            "instrument": {
                "symbol": "GGAL",
                "marketId": "ROFEX"
            },
            "timestamp": "2024-01-15T10:32:00Z",
            "account": "mi_cuenta"
        }
    }
    print(f"   {json.dumps(order_report_filled, indent=2, ensure_ascii=False)}")
    
    print("\n   f) Reporte de orden cancelada:")
    order_report_cancelled = {
        "type": "order_report",
        "report": {
            "wsClOrdId": "MI_ORDEN_001",
            "orderId": "12345",
            "status": "CANCELLED",
            "side": "BUY",
            "size": 100,
            "price": 1500.0,
            "filledSize": 0,
            "remainingSize": 100,
            "instrument": {
                "symbol": "GGAL",
                "marketId": "ROFEX"
            },
            "timestamp": "2024-01-15T10:33:00Z",
            "account": "mi_cuenta",
            "cancelReason": "USER_REQUEST"
        }
    }
    print(f"   {json.dumps(order_report_cancelled, indent=2, ensure_ascii=False)}")
    
    # ============================================================================
    # 5. MENSAJES DE ERROR
    # ============================================================================
    
    print("\n\n5. ❌ MENSAJES DE ERROR")
    print("-" * 30)
    
    print("\n   a) Error genérico:")
    error_generic = {
        "type": "error",
        "message": "Error interno del servidor",
        "timestamp": 1642248600.0
    }
    print(f"   {json.dumps(error_generic, indent=2, ensure_ascii=False)}")
    
    print("\n   b) Error de validación:")
    error_validation = {
        "type": "error",
        "message": "Datos de orden inválidos",
        "code": "VALIDATION_ERROR",
        "details": {
            "field": "price",
            "reason": "Price must be greater than 0"
        },
        "timestamp": 1642248600.0
    }
    print(f"   {json.dumps(error_validation, indent=2, ensure_ascii=False)}")
    
    print("\n   c) Error de conexión:")
    error_connection = {
        "type": "error",
        "message": "WebSocket no conectado",
        "code": "WS_NOT_CONNECTED",
        "timestamp": 1642248600.0
    }
    print(f"   {json.dumps(error_connection, indent=2, ensure_ascii=False)}")
    
    # ============================================================================
    # 6. MENSAJES DE ESTADO
    # ============================================================================
    
    print("\n\n6. 📊 MENSAJES DE ESTADO")
    print("-" * 30)
    
    print("\n   a) Estado del servicio:")
    status = {
        "type": "status",
        "service": {
            "started": True,
            "started_at": 1642248000.0,
            "user": "mi_usuario",
            "account": "mi_cuenta",
            "instruments": ["GGAL", "PAMP", "ALUA"],
            "worker_running": True,
            "ws_connected": True
        },
        "ws_details": {
            "ws": "ok",
            "user_id": "mi_usuario",
            "subscribed": ["GGAL", "PAMP", "ALUA"],
            "last_md_ms": 1642248600000,
            "subscribers": 2,
            "last_order_report": {
                "wsClOrdId": "MI_ORDEN_001",
                "status": "FILLED"
            }
        },
        "timestamp": 1642248600.0
    }
    print(f"   {json.dumps(status, indent=2, ensure_ascii=False)}")

def mostrar_campos_importantes():
    """Mostrar campos importantes y su significado"""
    
    print("\n\n" + "="*60)
    print("🔑 CAMPOS IMPORTANTES Y SU SIGNIFICADO")
    print("="*60)
    
    campos = {
        "type": "Tipo de mensaje (connection, order_ack, order_report, etc.)",
        "wsClOrdId": "Client Order ID - ID único del cliente para tracking (campo real del broker)",
        "clOrdId": "Client Order ID - ID único del cliente para tracking (alternativo)",
        "orderId": "Order ID - ID interno del broker",
        "status": "Estado de la orden (NEW, PARTIALLY_FILLED, FILLED, CANCELLED)",
        "symbol": "Símbolo del instrumento (GGAL, PAMP, ALUA, etc.)",
        "side": "Lado de la orden (BUY, SELL)",
        "size": "Cantidad total de la orden",
        "price": "Precio de la orden",
        "filledSize": "Cantidad ejecutada",
        "remainingSize": "Cantidad pendiente",
        "lastFillPrice": "Último precio de ejecución",
        "averagePrice": "Precio promedio de ejecución",
        "timestamp": "Timestamp del evento",
        "ts_ms": "Timestamp en milisegundos",
        "account": "Cuenta del usuario",
        "instrument": "Información del instrumento",
        "marketId": "ID del mercado (ROFEX, MERV, etc.)",
        "orderType": "Tipo de orden (LIMIT, MARKET)",
        "timeInForce": "Tiempo en vigor (DAY, IOC, FOK)",
        "bid": "Precio de compra",
        "offer": "Precio de venta",
        "last": "Último precio",
        "bid_size": "Cantidad en compra",
        "offer_size": "Cantidad en venta",
        "last_size": "Cantidad del último precio"
    }
    
    for campo, significado in campos.items():
        print(f"   {campo:<20} - {significado}")

def mostrar_estados_orden():
    """Mostrar todos los estados posibles de una orden"""
    
    print("\n\n" + "="*60)
    print("📋 ESTADOS POSIBLES DE UNA ORDEN")
    print("="*60)
    
    estados = {
        "NEW": "Orden nueva, enviada al broker",
        "PENDING_NEW": "Orden pendiente de confirmación",
        "PARTIALLY_FILLED": "Orden parcialmente ejecutada",
        "FILLED": "Orden completamente ejecutada",
        "CANCELLED": "Orden cancelada",
        "REJECTED": "Orden rechazada",
        "EXPIRED": "Orden expirada",
        "PENDING_CANCEL": "Cancelación pendiente",
        "PENDING_REPLACE": "Modificación pendiente",
        "REPLACED": "Orden modificada"
    }
    
    for estado, descripcion in estados.items():
        print(f"   {estado:<20} - {descripcion}")

def mostrar_tipos_orden():
    """Mostrar tipos de orden disponibles"""
    
    print("\n\n" + "="*60)
    print("📤 TIPOS DE ORDEN DISPONIBLES")
    print("="*60)
    
    tipos = {
        "LIMIT": "Orden limitada - se ejecuta solo al precio especificado o mejor",
        "MARKET": "Orden de mercado - se ejecuta al mejor precio disponible",
        "STOP": "Orden stop - se activa cuando se alcanza un precio",
        "STOP_LIMIT": "Orden stop limitada - combinación de stop y limit"
    }
    
    for tipo, descripcion in tipos.items():
        print(f"   {tipo:<15} - {descripcion}")
    
    print("\n   Tiempo en vigor (TIF):")
    tif_opciones = {
        "DAY": "Válida durante el día de trading",
        "IOC": "Immediate or Cancel - ejecutar inmediatamente o cancelar",
        "FOK": "Fill or Kill - ejecutar completamente o cancelar",
        "GTC": "Good Till Cancelled - válida hasta cancelar"
    }
    
    for tif, descripcion in tif_opciones.items():
        print(f"   {tif:<15} - {descripcion}")

if __name__ == "__main__":
    mostrar_formatos_mensajes()
    mostrar_campos_importantes()
    mostrar_estados_orden()
    mostrar_tipos_orden()
    
    print("\n\n" + "="*60)
    print("✅ RESUMEN COMPLETO DE FORMATOS DE MENSAJES")
    print("="*60)
    print("\n📡 Todos los mensajes del WebSocket están documentados arriba.")
    print("🔑 Los campos más importantes son 'type', 'clOrdId', 'status' y 'timestamp'.")
    print("📋 El Client Order ID ('clOrdId') es clave para el tracking de órdenes.")
    print("🔄 Los estados de orden van desde NEW hasta FILLED o CANCELLED.")
