#!/usr/bin/env python3
"""
Cliente de prueba para verificar órdenes reales
"""

import asyncio
from ratio_operations_real import real_ratio_manager, RatioOperationRequest

async def test_ordenes_reales():
    print("🧪 PROBANDO ÓRDENES REALES")
    print("=" * 50)
    
    # Crear operación de ratio
    request = RatioOperationRequest(
        operation_id="REAL_TEST_001",
        pair=["MERV - XMEV - TX26 - 24hs", "MERV - XMEV - TX28 - 24hs"],
        instrument_to_sell="MERV - XMEV - TX26 - 24hs",
        client_id="test_client_real",
        nominales=10,
        target_ratio=0.95,
        condition="less_than_or_equal",
        max_attempts=0
    )
    
    # Callback para recibir progreso
    async def progress_callback(progress):
        print(f"📊 Progreso: ratio={progress.current_ratio:.6f}, condición={progress.condition_met}")
        print(f"📈 Órdenes: Venta={len(progress.sell_orders)}, Compra={len(progress.buy_orders)}")
        
        # Mostrar cotizaciones reales
        if progress.real_quotes:
            print("💰 Cotizaciones reales:")
            for instrument, quotes in progress.real_quotes.items():
                print(f"   {instrument}: bid={quotes.get('bid')}, offer={quotes.get('offer')}")
        
        # Mostrar últimos mensajes
        for msg in progress.messages[-3:]:
            print(f"📝 {msg}")
        print("-" * 40)
    
    # Registrar callback
    real_ratio_manager.register_callback(request.operation_id, progress_callback)
    
    # Ejecutar operación
    print("🚀 Iniciando operación con órdenes reales...")
    result = await real_ratio_manager.execute_ratio_operation_batch(request)
    
    print("\n" + "=" * 50)
    print("📋 RESUMEN FINAL:")
    print(f"✅ Estado: {result.status}")
    print(f"📊 Ratio final: {result.current_ratio:.6f}")
    print(f"🎯 Condición cumplida: {result.condition_met}")
    print(f"💰 Órdenes de venta ejecutadas: {len(result.sell_orders)}")
    print(f"💰 Órdenes de compra ejecutadas: {len(result.buy_orders)}")
    
    if result.sell_orders:
        for order in result.sell_orders:
            print(f"   📤 Venta: {order.instrument} - {order.quantity} @ {order.price} (ID: {order.order_id})")
    
    if result.buy_orders:
        for order in result.buy_orders:
            print(f"   📥 Compra: {order.instrument} - {order.quantity} @ {order.price} (ID: {order.order_id})")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_ordenes_reales())
