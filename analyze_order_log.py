#!/usr/bin/env python3
"""
Resumen ejecutivo del log de cursado de órdenes
"""

import json
from datetime import datetime

def analyze_order_log(log_file):
    """Analiza el log de cursado de órdenes"""
    
    print("📊 RESUMEN EJECUTIVO - CURSADO DE ÓRDENES")
    print("=" * 60)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        # Información general
        test_info = log_data.get("test_info", {})
        events = log_data.get("events", [])
        
        print(f"📅 Fecha de prueba: {test_info.get('start_time', 'N/A')}")
        print(f"⏱️ Duración: {test_info.get('total_events', 0)} eventos")
        print(f"📁 Archivo: {test_info.get('log_file', 'N/A')}")
        print()
        
        # Análisis de eventos
        event_types = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print("📈 ESTADÍSTICAS DE EVENTOS:")
        print("-" * 40)
        for event_type, count in sorted(event_types.items()):
            print(f"• {event_type}: {count}")
        print()
        
        # Análisis específico de órdenes
        orders_sent = []
        order_reports = []
        
        for event in events:
            if event.get("event_type") == "SEND_ORDER":
                orders_sent.append(event.get("data", {}))
            elif event.get("event_type") == "ORDER_REPORT":
                order_reports.append(event.get("data", {}))
        
        print("📤 ÓRDENES ENVIADAS:")
        print("-" * 40)
        for i, order in enumerate(orders_sent, 1):
            order_data = order.get("order", {})
            print(f"{i}. ID: {order.get('clOrdId', 'N/A')}")
            print(f"   Símbolo: {order_data.get('symbol', 'N/A')}")
            print(f"   Lado: {order_data.get('side', 'N/A')}")
            print(f"   Cantidad: {order_data.get('size', 'N/A')}")
            print(f"   Precio: {order_data.get('price', 'N/A')}")
            print(f"   Tipo: {order_data.get('order_type', 'N/A')}")
            print()
        
        print("📨 ORDER REPORTS RECIBIDOS:")
        print("-" * 40)
        for i, report in enumerate(order_reports, 1):
            order_report = report.get("report", {}).get("orderReport", {})
            print(f"{i}. ClOrdId: {order_report.get('clOrdId', 'N/A')}")
            print(f"   OrderId: {order_report.get('orderId', 'N/A')}")
            print(f"   Estado: {order_report.get('status', 'N/A')}")
            print(f"   Símbolo: {order_report.get('instrumentId', {}).get('symbol', 'N/A')}")
            print(f"   Precio: {order_report.get('price', 'N/A')}")
            print(f"   Cantidad: {order_report.get('orderQty', 'N/A')}")
            print(f"   Timestamp: {order_report.get('transactTime', 'N/A')}")
            print()
        
        # Análisis de rendimiento
        if events:
            start_time = datetime.fromisoformat(events[0]["timestamp"])
            end_time = datetime.fromisoformat(events[-1]["timestamp"])
            duration = (end_time - start_time).total_seconds()
            
            print("⚡ RENDIMIENTO:")
            print("-" * 40)
            print(f"• Duración total: {duration:.3f} segundos")
            print(f"• Eventos por segundo: {len(events) / duration:.2f}")
            print(f"• Latencia promedio: {duration / len(events) * 1000:.2f} ms")
            print()
        
        # Verificación de éxito
        success_indicators = {
            "Sistema activo": any(e.get("event_type") == "SYSTEM_STATUS" and 
                                e.get("data", {}).get("ws_connected") and 
                                e.get("data", {}).get("worker_running") for e in events),
            "WebSocket conectado": any(e.get("event_type") == "WEBSOCKET_WELCOME" for e in events),
            "Suscripción exitosa": any(e.get("event_type") == "ORDERS_SUBSCRIBE_RESPONSE" and 
                                     e.get("data", {}).get("result", {}).get("status") == "ok" for e in events),
            "Orden reconocida": any(e.get("event_type") == "ORDER_ACK" and 
                                  e.get("data", {}).get("result", {}).get("status") == "ok" for e in events),
            "Order reports recibidos": len(order_reports) > 0,
            "Ping-pong funcional": any(e.get("event_type") == "PONG_RESPONSE" for e in events)
        }
        
        print("✅ VERIFICACIÓN DE ÉXITO:")
        print("-" * 40)
        for indicator, status in success_indicators.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {indicator}")
        print()
        
        # Resumen final
        total_success = sum(success_indicators.values())
        total_checks = len(success_indicators)
        
        print("🎯 RESUMEN FINAL:")
        print("-" * 40)
        print(f"• Verificaciones exitosas: {total_success}/{total_checks}")
        print(f"• Porcentaje de éxito: {(total_success/total_checks)*100:.1f}%")
        
        if total_success == total_checks:
            print("🎉 ¡PRUEBA COMPLETAMENTE EXITOSA!")
            print("✅ El sistema está funcionando perfectamente")
            print("✅ Las órdenes se cursan correctamente")
            print("✅ El logging está operativo")
        elif total_success >= total_checks * 0.8:
            print("✅ Prueba mayormente exitosa")
            print("⚠️ Algunos componentes pueden necesitar atención")
        else:
            print("❌ Prueba con problemas significativos")
            print("🔧 Revisar configuración del sistema")
        
        return total_success == total_checks
        
    except Exception as e:
        print(f"❌ Error analizando log: {e}")
        return False

def main():
    """Función principal"""
    log_file = "order_execution_log_20250919_150921.json"
    
    print("🔍 ANALIZANDO LOG DE CURSADO DE ÓRDENES")
    print("=" * 60)
    print(f"📁 Archivo: {log_file}")
    print()
    
    success = analyze_order_log(log_file)
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ANÁLISIS COMPLETADO - SISTEMA OPERATIVO")
    else:
        print("⚠️ ANÁLISIS COMPLETADO - REVISAR CONFIGURACIÓN")

if __name__ == "__main__":
    main()

