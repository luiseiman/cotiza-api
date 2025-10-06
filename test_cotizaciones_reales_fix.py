#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_cotizaciones_reales_fix():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO CORRECCIÓN DE COTIZACIONES REALES")
        print("=" * 60)
        print("Objetivo: Verificar que se usan cotizaciones reales y no se marcan como exitosas sin ejecutar")
        print("=" * 60)
        
        # Primero verificar el estado del sistema
        print("🔍 Verificando estado del sistema...")
        status_request = {"action": "get_status"}
        await ws.send(json.dumps(status_request))
        
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(message)
                
                if data.get('type') == 'status':
                    print(f"📊 Estado del sistema:")
                    print(f"   WebSocket ROFEX: {data.get('ws_connected', 'N/A')}")
                    print(f"   Worker activo: {data.get('worker_running', 'N/A')}")
                    print(f"   Instrumentos suscritos: {len(data.get('instruments', []))}")
                    if data.get('instruments'):
                        print(f"   Instrumentos: {', '.join(data.get('instruments', [])[:5])}...")
                    break
        except asyncio.TimeoutError:
            print("⏰ Timeout obteniendo estado del sistema")
        
        # Iniciar una operación de ratio
        print(f"\n🚀 Iniciando operación de ratio...")
        operation_request = {
            "action": "start_ratio_operation",
            "pair": [
                "MERV - XMEV - TX26 - 24hs",
                "MERV - XMEV - TX28 - 24hs"
            ],
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 10.0,
            "target_ratio": 0.95,
            "condition": "<=",
            "client_id": "test_cotizaciones_reales_fix_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Operación enviada...")
        
        operation_id = None
        cotizaciones_reales_detectadas = False
        lotes_ejecutados = 0
        
        # Escuchar mensajes de progreso
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ Operación iniciada: {operation_id}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    messages = data.get('messages', [])
                    status = data.get('status', 'unknown')
                    
                    # Buscar mensajes sobre cotizaciones
                    for msg in messages:
                        if "Cotizaciones reales disponibles" in msg:
                            print(f"🎉 {msg}")
                            cotizaciones_reales_detectadas = True
                        elif "Usando cotización simulada" in msg:
                            print(f"⚠️ {msg}")
                        elif "No hay cotizaciones reales disponibles" in msg:
                            print(f"❌ {msg}")
                        elif "Lote" in msg and "ejecutado" in msg:
                            lotes_ejecutados += 1
                            print(f"✅ {msg}")
                    
                    # Mostrar progreso
                    print(f"📊 Progreso: {status} - {data.get('current_step', 'unknown')}")
                    print(f"   Nominales: {data.get('completed_nominales', 0)}/{data.get('target_nominales', 0)}")
                    print(f"   Lotes ejecutados: {data.get('batch_count', 0)}")
                    
                    # Si la operación termina, salir
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                        if data.get('error'):
                            print(f"❌ Error: {data['error']}")
                        break
                        
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando progreso de la operación")
        
        # Resumen de la prueba
        print(f"\n📋 RESUMEN DE LA PRUEBA:")
        print(f"   Operation ID: {operation_id}")
        if cotizaciones_reales_detectadas:
            print(f"   ✅ Cotizaciones reales: DETECTADAS Y USADAS")
        else:
            print(f"   ⚠️ Cotizaciones reales: NO DETECTADAS (usando simuladas)")
        
        print(f"   📦 Lotes ejecutados: {lotes_ejecutados}")
        
        if lotes_ejecutados == 0:
            print(f"   ❌ PROBLEMA: No se ejecutaron lotes pero la operación se marcó como completada")
        else:
            print(f"   ✅ CORRECTO: Se ejecutaron lotes antes de marcar como completada")
        
        print(f"\n💡 RECOMENDACIONES:")
        if not cotizaciones_reales_detectadas:
            print(f"   • Verificar que los instrumentos estén suscritos en ROFEX")
            print(f"   • Comprobar que el WebSocket ROFEX esté conectado")
            print(f"   • Revisar que el worker de ratios esté activo")
        else:
            print(f"   • ✅ Sistema funcionando correctamente con cotizaciones reales")
        
        print(f"\n🏁 Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_cotizaciones_reales_fix())
