#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_cancel_operation_fix():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO CORRECCIÓN DE CANCELACIÓN")
        print("=" * 60)
        print("Objetivo: Verificar que cancel_ratio_operation NO cuelga el servicio")
        print("=" * 60)
        
        # Iniciar una operación de ratio
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 100.0,  # Cantidad grande para que dure
            "target_ratio": 0.90,
            "condition": "<=",
            "client_id": "test_cancel_fix_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Iniciando operación de ratio...")
        
        operation_id = None
        
        # Esperar confirmación de inicio
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ Operación iniciada: {operation_id}")
                    break
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error iniciando operación: {data['error']}")
                    return
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando inicio de operación")
            return
        
        # Esperar un poco para que la operación se ejecute
        print("⏳ Esperando 3 segundos para que la operación se ejecute...")
        await asyncio.sleep(3)
        
        # Ahora intentar cancelar la operación
        print(f"\n🛑 CANCELANDO OPERACIÓN {operation_id}")
        cancel_request = {
            "action": "cancel_ratio_operation",
            "operation_id": operation_id
        }
        
        await ws.send(json.dumps(cancel_request))
        print(f"📤 Enviada solicitud de cancelación")
        
        # Esperar respuesta de cancelación
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_cancelled':
                    print(f"✅ OPERACIÓN CANCELADA EXITOSAMENTE")
                    print(f"   Operation ID: {data['operation_id']}")
                    print(f"   Mensaje: {data['message']}")
                    break
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error cancelando: {data['error']}")
                    break
                elif data['type'] == 'ratio_operation_progress':
                    # Recibir progreso mientras esperamos cancelación
                    status = data.get('status', 'unknown')
                    print(f"📊 Progreso recibido: {status}")
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando respuesta de cancelación")
        
        # Verificar que el servicio sigue funcionando
        print(f"\n🔍 VERIFICANDO QUE EL SERVICIO SIGUE FUNCIONANDO")
        
        # Intentar iniciar otra operación para verificar que el servicio responde
        test_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 5.0,
            "target_ratio": 0.95,
            "condition": "<=",
            "client_id": "test_service_alive_001"
        }
        
        await ws.send(json.dumps(test_request))
        print(f"📤 Enviando operación de prueba para verificar servicio...")
        
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    print(f"✅ SERVICIO FUNCIONANDO: Nueva operación iniciada: {data['operation_id']}")
                    break
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error en operación de prueba: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("❌ SERVICIO COLGADO: No responde a nuevas operaciones")
        
        print(f"\n🏁 Prueba de cancelación completada")


if __name__ == "__main__":
    asyncio.run(test_cancel_operation_fix())
