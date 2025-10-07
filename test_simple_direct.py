#!/usr/bin/env python3
"""
Cliente de prueba que usa directamente la versión simplificada
"""

import asyncio
from ratio_operations_simple import simple_ratio_manager, RatioOperationRequest

async def test_simple_direct():
    print("🧪 PROBANDO VERSIÓN SIMPLIFICADA DIRECTA")
    print("=" * 50)
    
    # Crear operación de ratio
    request = RatioOperationRequest(
        operation_id="TEST_001",
        pair=["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
        instrument_to_sell="MERV - XMEV - TX26 - 24hs",
        client_id="test_client",
        nominales=10,
        target_ratio=0.95,
        condition="less_than_or_equal",
        max_attempts=0
    )
    
    # Callback para recibir progreso
    async def progress_callback(progress):
        print(f"📊 Progreso: ratio={progress.current_ratio:.6f}, condición={progress.condition_met}")
        for msg in progress.messages[-5:]:  # Mostrar últimos 5 mensajes
            print(f"📝 {msg}")
    
    # Registrar callback
    simple_ratio_manager.register_callback(request.operation_id, progress_callback)
    
    # Ejecutar operación
    print("🚀 Iniciando operación...")
    result = await simple_ratio_manager.execute_ratio_operation_batch(request)
    
    print(f"✅ Operación completada: {result.status}")
    print(f"📊 Ratio final: {result.current_ratio:.6f}")
    print(f"🎯 Condición cumplida: {result.condition_met}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_simple_direct())
