#!/usr/bin/env python3
import asyncio
import websockets
import json


async def test_operation_id_format():
    uri = "ws://localhost:8000/ws/cotizaciones"
    async with websockets.connect(uri) as ws:
        print("🔗 Conectado al WebSocket")
        welcome = await ws.recv()
        print(f"📨 Bienvenida: {welcome}")
        
        print("\n🧪 PROBANDO NUEVO FORMATO DE OPERATION_ID")
        print("=" * 70)
        print("Objetivo: Verificar que el operation_id tiene formato TX26-TX28_a1b2c3d4")
        print("=" * 70)
        
        # Probar con formato array
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
            "client_id": "test_operation_id_001"
        }
        
        await ws.send(json.dumps(operation_request))
        print(f"📤 Enviada operación con formato array:")
        print(f"   Par: {operation_request['pair']}")
        print(f"   Vender: {operation_request['instrument_to_sell']}")
        
        # Escuchar respuesta
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"\n✅ OPERACIÓN INICIADA")
                    print(f"   Operation ID: {operation_id}")
                    
                    # Verificar formato
                    if '-' in operation_id and '_' in operation_id:
                        parts = operation_id.split('_')
                        if len(parts) == 2:
                            pair_part = parts[0]
                            random_part = parts[1]
                            
                            print(f"   ✅ Formato correcto detectado:")
                            print(f"      Par: {pair_part}")
                            print(f"      Aleatorio: {random_part}")
                            
                            # Verificar que contiene TX26-TX28
                            if "TX26" in pair_part and "TX28" in pair_part:
                                print(f"   ✅ Contiene los símbolos correctos (TX26-TX28)")
                            else:
                                print(f"   ⚠️ No contiene los símbolos esperados")
                            
                            # Verificar que el aleatorio es de 8 caracteres
                            if len(random_part) == 8 and random_part.isalnum():
                                print(f"   ✅ Parte aleatoria correcta (8 caracteres alfanuméricos)")
                            else:
                                print(f"   ⚠️ Parte aleatoria no tiene formato esperado")
                                
                        else:
                            print(f"   ❌ Formato incorrecto: debe tener formato PAR_aleatorio")
                    else:
                        print(f"   ❌ Formato incorrecto: debe contener '-' y '_'")
                    
                    break
                    
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando respuesta")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n🧪 PROBANDO FORMATO LEGACY (STRING)")
        print("=" * 50)
        
        # Probar con formato legacy (string)
        operation_request_legacy = {
            "action": "start_ratio_operation",
            "pair": "MERV - XMEV - TX26 - 24hs-MERV - XMEV - TX28 - 24hs",
            "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
            "nominales": 5.0,
            "target_ratio": 0.90,
            "condition": "<=",
            "client_id": "test_operation_id_002"
        }
        
        await ws.send(json.dumps(operation_request_legacy))
        print(f"📤 Enviada operación con formato legacy:")
        print(f"   Par: {operation_request_legacy['pair']}")
        
        # Escuchar respuesta
        try:
            while True:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                if data['type'] == 'ratio_operation_started':
                    operation_id = data['operation_id']
                    print(f"\n✅ OPERACIÓN LEGACY INICIADA")
                    print(f"   Operation ID: {operation_id}")
                    
                    # Verificar formato
                    if '-' in operation_id and '_' in operation_id:
                        print(f"   ✅ Formato correcto detectado para formato legacy")
                    else:
                        print(f"   ❌ Formato incorrecto para formato legacy")
                    
                    break
                    
                elif data['type'] == 'ratio_operation_error':
                    print(f"❌ Error: {data['error']}")
                    break
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout esperando respuesta legacy")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n🏁 Prueba de formato de operation_id completada")

if __name__ == "__main__":
    asyncio.run(test_operation_id_format())
