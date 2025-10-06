#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_analisis_ratio_detallado():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO ANÁLISIS DE RATIO DETALLADO")
        print("=" * 60)
        print("Objetivo: Verificar que se muestra análisis detallado del ratio")
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
            "client_id": "test_analisis_ratio_detallado_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Operación enviada...")
        
        operation_id = None
        analisis_detectado = False
        intento_count = 0
        
        # Escuchar mensajes de progreso
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"✅ Operación iniciada: {operation_id}")
                    
                elif data['type'] == 'ratio_operation_progress':
                    messages = data.get('messages', [])
                    status = data.get('status', 'unknown')
                    
                    # Mostrar solo los mensajes relevantes para el análisis
                    for msg in messages:
                        if "Intento" in msg and "intentos infinitos" in msg:
                            intento_count += 1
                            print(f"\n🔄 INTENTO #{intento_count}")
                            print("-" * 50)
                        elif "Análisis de Ratio:" in msg:
                            print(f"📈 {msg}")
                            analisis_detectado = True
                        elif "Ratio actual:" in msg and "(" in msg:
                            print(f"   {msg}")
                        elif "Ratio objetivo:" in msg and "(" in msg:
                            print(f"   {msg}")
                        elif "Diferencia:" in msg:
                            print(f"   {msg}")
                        elif "Condición:" in msg:
                            print(f"   {msg}")
                        elif "Cotizaciones actuales:" in msg:
                            print(f"📊 {msg}")
                        elif "bid=" in msg and "offer=" in msg:
                            print(f"   {msg}")
                    
                    # Si la operación termina o llegamos a 3 intentos, salir
                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n🏁 OPERACIÓN FINALIZADA: {status.upper()}")
                        if data.get('error'):
                            print(f"❌ Error: {data['error']}")
                        break
                    elif intento_count >= 3:
                        print(f"\n⏹️ Deteniendo después de {intento_count} intentos")
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
        
        if analisis_detectado:
            print(f"   ✅ Análisis detallado de ratio: DETECTADO")
        else:
            print(f"   ❌ Análisis detallado de ratio: NO DETECTADO")
        
        print(f"\n💡 INFORMACIÓN ESPERADA:")
        print(f"   • Ratio actual con porcentaje")
        print(f"   • Ratio objetivo con porcentaje")
        print(f"   • Diferencia en porcentaje")
        print(f"   • Estado de condición (CUMPLE/NO CUMPLE)")
        
        if analisis_detectado:
            print(f"\n✅ PRUEBA EXITOSA: El análisis detallado se muestra correctamente")
        else:
            print(f"\n❌ PRUEBA FALLIDA: No se detectó el análisis detallado")
        
        print(f"\n🏁 Prueba completada")


if __name__ == "__main__":
    asyncio.run(test_analisis_ratio_detallado())
