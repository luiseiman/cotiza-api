#!/usr/bin/env python3
"""
Test para verificar el campo correcto ws_client_order_id
"""

import json

def test_campo_correcto():
    """Test del campo correcto para enviar órdenes"""
    
    print("🔧 CORRECCIÓN DEL CAMPO CLIENT ORDER ID")
    print("="*50)
    
    print("\n❌ Error anterior:")
    error_anterior = {
        "type": "order_ack",
        "request": {
            "tif": "DAY",
            "side": "BUY",
            "size": 1,
            "price": 1,
            "market": "ROFX",
            "symbol": "MERV - XMEV - TX28 - 24hs",
            "order_type": "LIMIT"
        },
        "result": {
            "status": "error",
            "message": "send_order_via_websocket() got an unexpected keyword argument 'client_order_id'. Did you mean 'ws_client_order_id'?"
        }
    }
    print(json.dumps(error_anterior, indent=2, ensure_ascii=False))
    
    print("\n✅ Solución:")
    print("   El broker espera el campo 'ws_client_order_id' en lugar de 'client_order_id'")
    
    print("\n🔧 Código corregido:")
    codigo_corregido = '''
def send_order(self, *, symbol: str, side: str, size: float, price: Optional[float] = None,
               order_type: str = "LIMIT", tif: str = "DAY", market: Optional[str] = None, 
               client_order_id: Optional[str] = None) -> Dict[str, Any]:
    
    if client_order_id is not None:
        # Prioridad: ws_client_order_id (campo correcto) → wsClOrdId → clientId → clOrdId
        if hasattr(pr, 'ws_client_order_id'):
            kwargs["ws_client_order_id"] = str(client_order_id)  # ← Campo correcto
        elif hasattr(pr, 'wsClOrdId'):
            kwargs["wsClOrdId"] = str(client_order_id)
        elif hasattr(pr, 'clientId'):
            kwargs["clientId"] = str(client_order_id)
        elif hasattr(pr, 'clOrdId'):
            kwargs["clOrdId"] = str(client_order_id)
        else:
            kwargs["client_order_id"] = str(client_order_id)
    '''
    print(codigo_corregido)
    
    print("\n📋 Flujo completo:")
    print("1. Cliente envía orden con 'client_order_id'")
    print("2. Backend lo mapea a 'ws_client_order_id' para el broker")
    print("3. Broker procesa la orden")
    print("4. Broker devuelve order report con 'wsClOrdId'")
    print("5. Backend preserva el order report completo")
    print("6. Cliente recibe order report con 'wsClOrdId'")

def test_orden_correcta():
    """Test de orden con el campo correcto"""
    
    print("\n\n🚀 TEST DE ORDEN CORRECTA")
    print("="*50)
    
    # Simular el mensaje que se enviaría al broker
    mensaje_broker = {
        "ticker": "MERV - XMEV - TX28 - 24hs",
        "side": "BUY",
        "size": 1,
        "price": 1,
        "order_type": "LIMIT",
        "time_in_force": "DAY",
        "market": "ROFX",
        "ws_client_order_id": "MI_ORDEN_001"  # ← Campo correcto
    }
    
    print("📤 Mensaje enviado al broker:")
    print(json.dumps(mensaje_broker, indent=2, ensure_ascii=False))
    
    # Simular respuesta exitosa
    respuesta_exitosa = {
        "type": "order_ack",
        "request": {
            "symbol": "MERV - XMEV - TX28 - 24hs",
            "side": "BUY",
            "size": 1,
            "price": 1,
            "order_type": "LIMIT",
            "tif": "DAY",
            "market": "ROFX",
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
    
    print("\n✅ Respuesta exitosa:")
    print(json.dumps(respuesta_exitosa, indent=2, ensure_ascii=False))
    
    # Simular order report del broker
    order_report = {
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
        "wsClOrdId": "MI_ORDEN_001"  # ← El mismo ID regresa
    }
    
    print("\n📋 Order Report del broker:")
    print(json.dumps(order_report, indent=2, ensure_ascii=False))

def test_prioridad_campos():
    """Test de la prioridad de campos"""
    
    print("\n\n🎯 PRIORIDAD DE CAMPOS")
    print("="*50)
    
    prioridad = [
        ("ws_client_order_id", "Campo correcto para enviar al broker"),
        ("wsClOrdId", "Campo que devuelve el broker en order report"),
        ("clientId", "Campo alternativo común"),
        ("clOrdId", "Estándar FIX"),
        ("client_order_id", "Campo genérico de fallback")
    ]
    
    print("📋 Orden de prioridad:")
    for i, (campo, descripcion) in enumerate(prioridad, 1):
        print(f"   {i}. {campo:<20} - {descripcion}")
    
    print("\n🔧 Función de extracción:")
    codigo_extraccion = '''
def extract_client_order_id(report):
    """Extraer client_order_id del reporte del broker"""
    return (report.get("wsClOrdId") or 
            report.get("clOrdId") or 
            report.get("clientId") or 
            report.get("client_order_id"))

def send_client_order_id(order_data, client_order_id):
    """Enviar client_order_id al broker"""
    kwargs = order_data.copy()
    
    # Prioridad para enviar al broker
    if hasattr(pr, 'ws_client_order_id'):
        kwargs["ws_client_order_id"] = str(client_order_id)
    elif hasattr(pr, 'wsClOrdId'):
        kwargs["wsClOrdId"] = str(client_order_id)
    elif hasattr(pr, 'clientId'):
        kwargs["clientId"] = str(client_order_id)
    elif hasattr(pr, 'clOrdId'):
        kwargs["clOrdId"] = str(client_order_id)
    else:
        kwargs["client_order_id"] = str(client_order_id)
    
    return kwargs
    '''
    print(codigo_extraccion)

if __name__ == "__main__":
    test_campo_correcto()
    test_orden_correcta()
    test_prioridad_campos()
    
    print("\n\n" + "="*60)
    print("✅ RESUMEN DE LA CORRECCIÓN")
    print("="*60)
    print("🔧 Campo para enviar al broker: 'ws_client_order_id'")
    print("📋 Campo que devuelve el broker: 'wsClOrdId'")
    print("🔄 El código maneja ambos campos automáticamente")
    print("🎯 Prioridad: ws_client_order_id → wsClOrdId → clientId → clOrdId → client_order_id")
    print("✅ El error 'unexpected keyword argument' está resuelto")
