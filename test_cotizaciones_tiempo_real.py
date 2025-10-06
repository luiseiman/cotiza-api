#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_cotizaciones_tiempo_real():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO COTIZACIONES EN TIEMPO REAL")
        print("=" * 60)
        print("Objetivo: Verificar que se muestran cotizaciones actuales en cada intento")
        print("=" * 60)
        
        # Iniciar una operación de ratio
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
            "client_id": "test_cotizaciones_tiempo_real_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Operación enviada...")
        
        operation_id = None
        cotizaciones_mostradas = 0
        intento_count = 0
        
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
                    
                    # Mostrar todos los mensajes nuevos
                    for msg in messages:
                        if "Intento" in msg and "intentos infinitos" in msg:
                            intento_count += 1
                            print(f"\n🔄 INTENTO #{intento_count}")
                            print("-" * 40)
                        elif "Cotizaciones actuales" in msg:
                            cotizaciones_mostradas += 1
                            print(f"📊 {msg}")
                        elif "bid=" in msg and "offer=" in msg:
                            print(f"   {msg}")
                        elif "Ratio actual:" in msg:
                            print(f"   {msg}")
                        elif "Sin cotizaciones reales" in msg:
                            print(f"⚠️ {msg}")
                        elif "Esperando mejores condiciones" in msg:
                            print(f"⏳ {msg}")
                        elif "Lote" in msg and "nominales" in msg:
                            print(f"📦 {msg}")
                        elif "Error ejecutando lote" in msg:
                            print(f"❌ {msg}")
                        else:
                            print(f"💬 {msg}")
                    
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
        print(f"   Intentos monitoreados: {intento_count}")
        print(f"   Cotizaciones mostradas: {cotizaciones_mostradas}")
        
        if cotizaciones_mostradas > 0:
            print(f"   ✅ Cotizaciones en tiempo real: FUNCIONANDO")
        else:
            print(f"   ❌ Cotizaciones en tiempo real: NO DETECTADAS")
        
        if intento_count >= 3:
            print(f"   ✅ Múltiples intentos: MONITOREADOS CORRECTAMENTE")
        else:
            print(f"   ⚠️ Pocos intentos monitoreados: {intento_count}")
        
        print(f"\n💡 ANÁLISIS:")
        if cotizaciones_mostradas == 0:
            print(f"   • Las cotizaciones no se están mostrando en tiempo real")
            print(f"   • Verificar que los instrumentos estén suscritos")
            print(f"   • Comprobar que el worker de ratios esté activo")
        else:
            print(f"   • Las cotizaciones se muestran correctamente en tiempo real")
            print(f"   • El sistema está funcionando como esperado")
        
        print(f"\n🏁 Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_cotizaciones_tiempo_real())
