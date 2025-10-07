#!/usr/bin/env python3
"""
Cliente para simular y mostrar las confirmaciones que devuelve pyRofex
"""

import json
from datetime import datetime
from typing import Dict, Any

def mostrar_confirmaciones_pyrofex():
    print("🔍 CONFIRMACIONES QUE DEVUELVE pyRofex")
    print("=" * 60)
    
    print("\n📤 1. RESPUESTA INMEDIATA DE send_order_via_websocket():")
    print("-" * 50)
    respuesta_inmediata = {
        "status": "ok",
        "response": {
            "clientOrderId": "TX26-TX28_e2dc02b4_sell_112209",
            "proprietary": "12345",
            "instrumentId": {
                "marketId": "ROFX",
                "symbol": "MERV - XMEV - TX26 - 24hs"
            },
            "orderId": "987654321",
            "side": "SELL",
            "ordType": "LIMIT",
            "orderQty": 10.0,
            "price": 1000.5,
            "timeInForce": "DAY",
            "status": "NEW",
            "timestamp": "2025-10-07T11:22:09.123Z"
        }
    }
    print(json.dumps(respuesta_inmediata, indent=2, ensure_ascii=False))
    
    print("\n📋 2. ORDER REPORT (confirmación asíncrona):")
    print("-" * 50)
    order_report = {
        "type": "order_report",
        "report": {
            "wsClOrdId": "TX26-TX28_e2dc02b4_sell_112209",  # Client Order ID
            "clOrdId": "TX26-TX28_e2dc02b4_sell_112209",     # Alternativo
            "orderId": "987654321",                           # Order ID del broker
            "instrumentId": {
                "marketId": "ROFX",
                "symbol": "MERV - XMEV - TX26 - 24hs"
            },
            "side": "SELL",
            "ordType": "LIMIT",
            "orderQty": 10.0,
            "price": 1000.5,
            "status": "NEW",                                  # Estado de la orden
            "executedQty": 0.0,                              # Cantidad ejecutada
            "avgPrice": 0.0,                                 # Precio promedio
            "lastQty": 0.0,                                  # Última cantidad
            "lastPrice": 0.0,                                # Último precio
            "timestamp": "2025-10-07T11:22:09.123Z",
            "proprietary": "12345"                           # ID interno del broker
        }
    }
    print(json.dumps(order_report, indent=2, ensure_ascii=False))
    
    print("\n✅ 3. ORDER REPORT CUANDO SE EJECUTA:")
    print("-" * 50)
    order_executed = {
        "type": "order_report",
        "report": {
            "wsClOrdId": "TX26-TX28_e2dc02b4_sell_112209",
            "orderId": "987654321",
            "instrumentId": {
                "marketId": "ROFX",
                "symbol": "MERV - XMEV - TX26 - 24hs"
            },
            "side": "SELL",
            "ordType": "LIMIT",
            "orderQty": 10.0,
            "price": 1000.5,
            "status": "FILLED",                              # Orden ejecutada
            "executedQty": 10.0,                             # Cantidad ejecutada
            "avgPrice": 1000.5,                              # Precio promedio
            "lastQty": 10.0,                                 # Última cantidad
            "lastPrice": 1000.5,                             # Último precio
            "timestamp": "2025-10-07T11:22:10.456Z",
            "proprietary": "12345"
        }
    }
    print(json.dumps(order_executed, indent=2, ensure_ascii=False))
    
    print("\n❌ 4. ORDER REPORT CUANDO FALLA:")
    print("-" * 50)
    order_rejected = {
        "type": "order_report",
        "report": {
            "wsClOrdId": "TX26-TX28_e2dc02b4_sell_112209",
            "orderId": "987654321",
            "instrumentId": {
                "marketId": "ROFX",
                "symbol": "MERV - XMEV - TX26 - 24hs"
            },
            "side": "SELL",
            "ordType": "LIMIT",
            "orderQty": 10.0,
            "price": 1000.5,
            "status": "REJECTED",                            # Orden rechazada
            "executedQty": 0.0,
            "avgPrice": 0.0,
            "lastQty": 0.0,
            "lastPrice": 0.0,
            "timestamp": "2025-10-07T11:22:09.789Z",
            "proprietary": "12345",
            "text": "Insufficient funds"                     # Razón del rechazo
        }
    }
    print(json.dumps(order_rejected, indent=2, ensure_ascii=False))
    
    print("\n🔄 5. ESTADOS POSIBLES DE ÓRDENES:")
    print("-" * 50)
    estados = [
        "NEW - Orden nueva, enviada al mercado",
        "PARTIALLY_FILLED - Orden parcialmente ejecutada", 
        "FILLED - Orden completamente ejecutada",
        "CANCELLED - Orden cancelada",
        "REJECTED - Orden rechazada por el broker",
        "EXPIRED - Orden expirada",
        "PENDING_CANCEL - Cancelación pendiente",
        "PENDING_REPLACE - Modificación pendiente"
    ]
    for estado in estados:
        print(f"   • {estado}")
    
    print("\n📊 6. CAMPOS CLAVE PARA SEGUIMIENTO:")
    print("-" * 50)
    campos_clave = [
        "wsClOrdId / clOrdId - ID de la orden del cliente",
        "orderId - ID de la orden en el broker",
        "status - Estado actual de la orden",
        "executedQty - Cantidad ejecutada",
        "orderQty - Cantidad total de la orden",
        "avgPrice - Precio promedio de ejecución",
        "lastPrice - Último precio de ejecución",
        "timestamp - Momento del reporte",
        "text - Mensaje adicional (errores, etc.)"
    ]
    for campo in campos_clave:
        print(f"   • {campo}")
    
    print("\n🎯 7. FLUJO TÍPICO DE UNA ORDEN:")
    print("-" * 50)
    print("   1. 📤 Envío: send_order_via_websocket() → respuesta inmediata")
    print("   2. 📋 Confirmación: Order Report con status 'NEW'")
    print("   3. ⚡ Ejecución: Order Report con status 'FILLED'")
    print("   4. 📊 Seguimiento: Múltiples Order Reports con actualizaciones")
    
    print("\n" + "=" * 60)
    print("✅ RESUMEN: pyRofex devuelve confirmaciones asíncronas via Order Reports")
    print("📋 Cada Order Report contiene el estado actualizado de la orden")
    print("🔄 El sistema debe escuchar estos reports para saber si se ejecutó")

if __name__ == "__main__":
    mostrar_confirmaciones_pyrofex()
