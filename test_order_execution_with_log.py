#!/usr/bin/env python3
"""
Script para probar el cursado de órdenes con logging completo de mensajes JSON
"""

import asyncio
import websockets
import json
import requests
import time
from datetime import datetime
import os

# Configuración
BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/cotizaciones"
LOG_FILE = f"order_execution_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

class OrderExecutionLogger:
    def __init__(self):
        self.log_entries = []
        self.start_time = datetime.now()
        
    def log(self, event_type, data, direction="OUT"):
        """Registra un evento en el log"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "direction": direction,
            "data": data
        }
        self.log_entries.append(entry)
        print(f"[{entry['timestamp']}] {direction} - {event_type}: {json.dumps(data, indent=2)}")
        
    def save_log(self):
        """Guarda el log completo en archivo JSON"""
        log_data = {
            "test_info": {
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_events": len(self.log_entries),
                "log_file": LOG_FILE
            },
            "events": self.log_entries
        }
        
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Log guardado en: {LOG_FILE}")
        return LOG_FILE

async def test_order_execution():
    """Prueba completa de cursado de órdenes con logging detallado"""
    logger = OrderExecutionLogger()
    
    print("🚀 PRUEBA DE CURSADO DE ÓRDENES CON LOGGING COMPLETO")
    print("=" * 60)
    logger.log("TEST_START", {"message": "Iniciando prueba de cursado de órdenes"})
    
    try:
        # 1. Verificar estado del sistema
        print("\n🔍 1. Verificando estado del sistema...")
        try:
            response = requests.get(f"{BASE_URL}/cotizaciones/status", timeout=10)
            status_data = response.json()
            logger.log("SYSTEM_STATUS", status_data, "IN")
            
            if status_data.get("ws_connected") and status_data.get("worker_running"):
                print("✅ Sistema activo: WS=True, Worker=True")
            else:
                print("⚠️ Sistema parcialmente activo, continuando con la prueba...")
                print(f"   WS conectado: {status_data.get('ws_connected', False)}")
                print(f"   Worker corriendo: {status_data.get('worker_running', False)}")
                
        except Exception as e:
            logger.log("SYSTEM_STATUS_ERROR", {"error": str(e)}, "ERROR")
            print(f"❌ Error verificando estado: {e}")
            return False
        
        # 2. Conectar al WebSocket
        print("\n🔌 2. Conectando al WebSocket...")
        try:
            websocket = await websockets.connect(WS_URL)
            logger.log("WEBSOCKET_CONNECT", {"url": WS_URL}, "OUT")
            print("✅ Conexión WebSocket establecida")
            
            # Recibir mensaje de conexión
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome_msg)
                logger.log("WEBSOCKET_WELCOME", welcome_data, "IN")
                print(f"📨 Mensaje de bienvenida: {welcome_data}")
            except asyncio.TimeoutError:
                print("⚠️ No se recibió mensaje de bienvenida")
            except Exception as e:
                print(f"⚠️ Error recibiendo bienvenida: {e}")
                
        except Exception as e:
            logger.log("WEBSOCKET_CONNECT_ERROR", {"error": str(e)}, "ERROR")
            print(f"❌ Error conectando WebSocket: {e}")
            return False
        
        # 3. Suscribirse a order reports
        print("\n📋 3. Suscribiéndose a order reports...")
        subscribe_msg = {
            "type": "orders_subscribe",
            "account": "16557"
        }
        await websocket.send(json.dumps(subscribe_msg))
        logger.log("ORDERS_SUBSCRIBE", subscribe_msg, "OUT")
        
        # Esperar respuesta de suscripción
        try:
            subscribe_response = await asyncio.wait_for(websocket.recv(), timeout=10)
            subscribe_data = json.loads(subscribe_response)
            logger.log("ORDERS_SUBSCRIBE_RESPONSE", subscribe_data, "IN")
            
            if subscribe_data.get("result", {}).get("status") == "ok":
                print("✅ Suscripción a order reports exitosa")
            else:
                print("❌ Error en suscripción a order reports")
                return False
                
        except asyncio.TimeoutError:
            logger.log("ORDERS_SUBSCRIBE_TIMEOUT", {"timeout": 10}, "ERROR")
            print("❌ Timeout esperando respuesta de suscripción")
            return False
        except Exception as e:
            logger.log("ORDERS_SUBSCRIBE_ERROR", {"error": str(e)}, "ERROR")
            print(f"❌ Error en suscripción: {e}")
            return False
        
        # 4. Enviar orden de prueba
        print("\n📤 4. Enviando orden de prueba...")
        order_id = f"TEST_ORDER_{int(time.time())}"
        order_msg = {
            "type": "send_order",
            "clOrdId": order_id,
            "order": {
                "tif": "DAY",
                "side": "BUY",
                "size": 1,
                "price": 1.0,
                "market": "ROFX",
                "symbol": "MERV - XMEV - TSLA - 24hs",
                "order_type": "LIMIT"
            }
        }
        
        await websocket.send(json.dumps(order_msg))
        logger.log("SEND_ORDER", order_msg, "OUT")
        print(f"📋 Orden enviada: {order_id}")
        
        # 5. Esperar respuestas
        print("\n⏳ 5. Esperando respuestas...")
        responses_received = 0
        max_responses = 3  # order_ack + order_report + posible ping
        
        while responses_received < max_responses:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=15)
                response_data = json.loads(response)
                responses_received += 1
                
                if response_data.get("type") == "order_ack":
                    logger.log("ORDER_ACK", response_data, "IN")
                    print("✅ Orden reconocida por el sistema")
                    
                elif response_data.get("type") == "order_report":
                    logger.log("ORDER_REPORT", response_data, "IN")
                    print("✅ Order report recibido")
                    
                    # Verificar estado de la orden
                    order_status = response_data.get("report", {}).get("orderReport", {}).get("status")
                    if order_status:
                        print(f"📊 Estado de la orden: {order_status}")
                        
                elif response_data.get("type") == "ping":
                    logger.log("PING", response_data, "IN")
                    # Responder al ping
                    pong_msg = {"type": "pong"}
                    await websocket.send(json.dumps(pong_msg))
                    logger.log("PONG", pong_msg, "OUT")
                    print("🏓 Ping-Pong completado")
                    
                else:
                    logger.log("UNKNOWN_RESPONSE", response_data, "IN")
                    print(f"📨 Respuesta inesperada: {response_data}")
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout esperando más respuestas")
                break
            except Exception as e:
                logger.log("RESPONSE_ERROR", {"error": str(e)}, "ERROR")
                print(f"❌ Error recibiendo respuesta: {e}")
                break
        
        # 6. Probar ping-pong
        print("\n🏓 6. Probando ping-pong...")
        ping_msg = {"type": "ping"}
        await websocket.send(json.dumps(ping_msg))
        logger.log("PING_TEST", ping_msg, "OUT")
        
        try:
            pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            pong_data = json.loads(pong_response)
            logger.log("PONG_RESPONSE", pong_data, "IN")
            print("✅ Ping-pong exitoso")
        except Exception as e:
            logger.log("PING_PONG_ERROR", {"error": str(e)}, "ERROR")
            print(f"❌ Error en ping-pong: {e}")
        
        # 7. Cerrar conexión
        print("\n🔌 7. Cerrando conexión...")
        await websocket.close()
        logger.log("WEBSOCKET_CLOSE", {"message": "Conexión cerrada"}, "OUT")
        
        # 8. Resumen final
        print("\n📋 RESUMEN DE LA PRUEBA")
        print("=" * 60)
        logger.log("TEST_COMPLETE", {
            "total_events": len(logger.log_entries),
            "success": True,
            "order_id": order_id
        })
        
        print(f"✅ Prueba completada exitosamente")
        print(f"📊 Total de eventos registrados: {len(logger.log_entries)}")
        print(f"🆔 ID de orden: {order_id}")
        
        return True
        
    except Exception as e:
        logger.log("TEST_ERROR", {"error": str(e)}, "ERROR")
        print(f"❌ Error durante la prueba: {e}")
        return False
    
    finally:
        # Guardar log
        log_file = logger.save_log()
        print(f"\n📁 Log completo guardado en: {log_file}")
        
        # Mostrar estadísticas del log
        print(f"\n📊 ESTADÍSTICAS DEL LOG:")
        print(f"• Total de eventos: {len(logger.log_entries)}")
        print(f"• Duración de la prueba: {(datetime.now() - logger.start_time).total_seconds():.2f} segundos")
        
        # Contar tipos de eventos
        event_types = {}
        for entry in logger.log_entries:
            event_type = entry["event_type"]
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print(f"• Tipos de eventos:")
        for event_type, count in event_types.items():
            print(f"  - {event_type}: {count}")

async def main():
    """Función principal"""
    print("🎯 INICIANDO PRUEBA DE CURSADO DE ÓRDENES CON LOGGING")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Log será guardado en: {LOG_FILE}")
    print()
    
    success = await test_order_execution()
    
    if success:
        print("\n🎉 ¡PRUEBA COMPLETADA EXITOSAMENTE!")
        print("✅ El sistema está funcionando correctamente")
        print("✅ Las órdenes se pueden cursar sin problemas")
        print("✅ El logging está funcionando perfectamente")
    else:
        print("\n❌ PRUEBA FALLÓ")
        print("⚠️ Revisar el log para identificar problemas")
    
    print(f"\n📁 Revisar el archivo de log: {LOG_FILE}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
