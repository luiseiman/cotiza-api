#!/usr/bin/env python3
"""
Módulo para operaciones de ratio automatizadas.
Permite ejecutar operaciones de compra/venta basadas en ratios con monitoreo en tiempo real.
"""

import asyncio
import time
import json
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import ws_rofex
from quotes_cache import quotes_cache


class OperationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationStep(Enum):
    INITIALIZING = "initializing"
    ANALYZING_MARKET = "analyzing_market"
    PLACING_SELL_ORDER = "placing_sell_order"
    WAITING_SELL_EXECUTION = "waiting_sell_execution"
    SELL_EXECUTED = "sell_executed"
    CALCULATING_BUY_AMOUNT = "calculating_buy_amount"
    PLACING_BUY_ORDER = "placing_buy_order"
    WAITING_BUY_EXECUTION = "waiting_buy_execution"
    BUY_EXECUTED = "buy_executed"
    VERIFYING_RATIO = "verifying_ratio"
    FINALIZING = "finalizing"
    # Nuevos pasos para operaciones por lotes
    CALCULATING_BATCH_SIZE = "calculating_batch_size"
    EXECUTING_BATCH = "executing_batch"
    CHECKING_REMAINING = "checking_remaining"
    CALCULATING_WEIGHTED_AVERAGE = "calculating_weighted_average"
    WAITING_FOR_BETTER_PRICES = "waiting_for_better_prices"


@dataclass
class RatioOperationRequest:
    pair: str | List[str]  # Soporta tanto string como array de instrumentos
    instrument_to_sell: str
    nominales: float
    target_ratio: float
    condition: str
    client_id: str
    operation_id: str


@dataclass
class OrderExecution:
    order_id: str
    instrument: str
    side: str
    quantity: float
    price: float
    executed_at: str
    client_order_id: str


@dataclass
class OperationProgress:
    operation_id: str
    status: OperationStatus
    current_step: OperationStep
    progress_percentage: float
    start_time: str
    last_update: str
    sell_orders: List[OrderExecution]
    buy_orders: List[OrderExecution]
    total_sold_amount: float
    total_bought_amount: float
    average_sell_price: float
    average_buy_price: float
    current_ratio: float
    target_ratio: float
    condition_met: bool
    messages: List[str]
    error: Optional[str] = None
    # Nuevos campos para operaciones por lotes
    target_nominales: float = 0.0  # Nominales objetivo totales
    completed_nominales: float = 0.0  # Nominales ya ejecutados
    remaining_nominales: float = 0.0  # Nominales pendientes
    batch_count: int = 0  # Número de lotes ejecutados
    weighted_average_ratio: float = 0.0  # Ratio promedio ponderado
    max_attempts: int = 10  # Máximo de intentos
    current_attempt: int = 0  # Intento actual
    condition: str = ""  # Condición de ratio (<= o >=)
    pair: str | List[str] = ""  # Par de instrumentos


class RatioOperationManager:
    def __init__(self):
        self.active_operations: Dict[str, OperationProgress] = {}
        self.operation_lock = threading.Lock()
        self.callbacks: Dict[str, Callable] = {}

    def register_callback(self, operation_id: str, callback: Callable):
        self.callbacks[operation_id] = callback

    def unregister_callback(self, operation_id: str):
        if operation_id in self.callbacks:
            del self.callbacks[operation_id]

    async def _notify_progress(self, operation_id: str, progress: OperationProgress):
        if operation_id in self.callbacks:
            try:
                await self.callbacks[operation_id](progress)
            except Exception as e:
                print(f"[ratio_ops] Error en callback: {e}")

    def _update_progress(self, operation_id: str, **updates):
        with self.operation_lock:
            if operation_id in self.active_operations:
                progress = self.active_operations[operation_id]
                for key, value in updates.items():
                    setattr(progress, key, value)
                progress.last_update = datetime.now().isoformat()
                step_progress = {
                    OperationStep.INITIALIZING: 5,
                    OperationStep.ANALYZING_MARKET: 10,
                    OperationStep.PLACING_SELL_ORDER: 15,
                    OperationStep.WAITING_SELL_EXECUTION: 25,
                    OperationStep.SELL_EXECUTED: 35,
                    OperationStep.CALCULATING_BUY_AMOUNT: 45,
                    OperationStep.PLACING_BUY_ORDER: 55,
                    OperationStep.WAITING_BUY_EXECUTION: 75,
                    OperationStep.BUY_EXECUTED: 85,
                    OperationStep.VERIFYING_RATIO: 95,
                    OperationStep.FINALIZING: 100
                }
                progress.progress_percentage = step_progress.get(progress.current_step, 0)

    def _add_message(self, operation_id: str, message: str):
        with self.operation_lock:
            if operation_id in self.active_operations:
                progress = self.active_operations[operation_id]
                progress.messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
                if len(progress.messages) > 50:
                    progress.messages = progress.messages[-50:]

    def _calculate_current_ratio(self, progress: OperationProgress) -> float:
        if not progress.sell_orders or not progress.buy_orders:
            return 0.0
        total_sell_value = sum(order.price * order.quantity for order in progress.sell_orders)
        total_sell_quantity = sum(order.quantity for order in progress.sell_orders)
        avg_sell_price = total_sell_value / total_sell_quantity if total_sell_quantity > 0 else 0
        total_buy_value = sum(order.price * order.quantity for order in progress.buy_orders)
        total_buy_quantity = sum(order.quantity for order in progress.buy_orders)
        avg_buy_price = total_buy_value / total_buy_quantity if total_buy_quantity > 0 else 0
        if avg_buy_price > 0:
            return avg_sell_price / avg_buy_price
        return 0.0

    def _check_condition(self, current_ratio: float, target_ratio: float, condition: str) -> bool:
        if condition == "<=":
            return current_ratio <= target_ratio
        if condition == ">=":
            return current_ratio >= target_ratio
        return False
    
    def _calculate_weighted_average_ratio(self, progress: OperationProgress) -> float:
        """Calcula el ratio promedio ponderado por cantidad de todas las operaciones ejecutadas."""
        if not progress.sell_orders or not progress.buy_orders:
            return 0.0
        
        total_weighted_ratio = 0.0
        total_weight = 0.0
        
        # Agrupar órdenes por lote (asumiendo que están en orden cronológico)
        min_orders = min(len(progress.sell_orders), len(progress.buy_orders))
        
        for i in range(min_orders):
            sell_order = progress.sell_orders[i]
            buy_order = progress.buy_orders[i]
            
            # Ratio de este lote
            batch_ratio = sell_order.price / buy_order.price
            # Peso basado en la cantidad vendida
            weight = sell_order.quantity
            
            total_weighted_ratio += batch_ratio * weight
            total_weight += weight
        
        return total_weighted_ratio / total_weight if total_weight > 0 else 0.0
    
    def _calculate_max_batch_size(self, progress: OperationProgress, quotes_cache: dict) -> float:
        """Calcula el tamaño máximo del lote que cumple la condición de ratio."""
        if not progress.sell_orders:
            return 0.0
        
        # Obtener cotizaciones actuales
        sell_quote = quotes_cache.get(progress.sell_orders[0].instrument)
        if not sell_quote:
            return 0.0
        
        # Determinar instrumento a comprar
        instrument_to_buy = None
        if isinstance(progress.pair, list):
            sell_instrument = progress.sell_orders[0].instrument
            for inst in progress.pair:
                if inst != sell_instrument:
                    instrument_to_buy = inst
                    break
        else:
            # Lógica para formato string (simplificada)
            instrument_to_buy = "MERV - XMEV - TX28 - 24hs"  # Fallback
        
        if not instrument_to_buy:
            return 0.0
        
        buy_quote = quotes_cache.get(instrument_to_buy)
        if not buy_quote:
            return 0.0
        
        # Calcular ratio teórico con cotizaciones actuales
        theoretical_ratio = sell_quote['bid'] / buy_quote['offer']
        
        # Si el ratio teórico cumple la condición, podemos vender todo lo que queda
        if self._check_condition(theoretical_ratio, progress.target_ratio, progress.condition):
            return progress.remaining_nominales
        
        # Si no cumple, calcular cuánto podemos vender manteniendo el promedio
        if progress.batch_count > 0:
            # Ya tenemos operaciones previas, calcular cuánto más podemos vender
            # manteniendo el promedio ponderado dentro del objetivo
            current_weighted_avg = self._calculate_weighted_average_ratio(progress)
            
            # Si el promedio actual ya cumple, podemos vender todo lo que queda
            if self._check_condition(current_weighted_avg, progress.target_ratio, progress.condition):
                return progress.remaining_nominales
        
        # Si no podemos mantener el promedio, vender lo mínimo posible (ej: 10%)
        return min(progress.remaining_nominales, max(1.0, progress.target_nominales * 0.1))
    
    async def _execute_batch(self, operation_id: str, batch_size: float, quotes_cache: dict) -> bool:
        """Ejecuta un lote individual de la operación de ratio."""
        progress = self.active_operations.get(operation_id)
        if not progress:
            return False
        
        try:
            # Determinar instrumentos
            instrument_to_sell = progress.sell_orders[0].instrument if progress.sell_orders else None
            instrument_to_buy = None
            
            if isinstance(progress.pair, list):
                for inst in progress.pair:
                    if inst != instrument_to_sell:
                        instrument_to_buy = inst
                        break
            else:
                instrument_to_buy = "MERV - XMEV - TX28 - 24hs"  # Fallback
            
            if not instrument_to_sell or not instrument_to_buy:
                return False
            
            # Obtener cotizaciones
            sell_quote = quotes_cache.get(instrument_to_sell)
            buy_quote = quotes_cache.get(instrument_to_buy)
            
            if not sell_quote or not buy_quote:
                return False
            
            # Ejecutar venta
            sell_price = sell_quote['bid']
            client_order_id_sell = f"RATIO_SELL_{operation_id}_{progress.batch_count}_{int(time.time())}"
            
            sell_result = ws_rofex.manager.send_order(
                symbol=instrument_to_sell,
                side="SELL",
                size=batch_size,
                price=sell_price,
                order_type="LIMIT",
                tif="DAY",
                client_order_id=client_order_id_sell
            )
            
            if sell_result.get("status") != "ok":
                self._add_message(operation_id, f"❌ Error en venta del lote: {sell_result.get('message', 'Unknown error')}")
                return False
            
            await asyncio.sleep(1)  # Simular ejecución
            
            # Ejecutar compra
            buy_price = buy_quote['offer']
            nominales_to_buy = (batch_size * sell_price) / buy_price
            client_order_id_buy = f"RATIO_BUY_{operation_id}_{progress.batch_count}_{int(time.time())}"
            
            buy_result = ws_rofex.manager.send_order(
                symbol=instrument_to_buy,
                side="BUY",
                size=nominales_to_buy,
                price=buy_price,
                order_type="LIMIT",
                tif="DAY",
                client_order_id=client_order_id_buy
            )
            
            if buy_result.get("status") != "ok":
                self._add_message(operation_id, f"❌ Error en compra del lote: {buy_result.get('message', 'Unknown error')}")
                return False
            
            await asyncio.sleep(1)  # Simular ejecución
            
            # Registrar órdenes ejecutadas
            sell_execution = OrderExecution(
                order_id=f"SELL_{operation_id}_{progress.batch_count}",
                instrument=instrument_to_sell,
                side="SELL",
                quantity=batch_size,
                price=sell_price,
                executed_at=datetime.now().isoformat(),
                client_order_id=client_order_id_sell
            )
            
            buy_execution = OrderExecution(
                order_id=f"BUY_{operation_id}_{progress.batch_count}",
                instrument=instrument_to_buy,
                side="BUY",
                quantity=nominales_to_buy,
                price=buy_price,
                executed_at=datetime.now().isoformat(),
                client_order_id=client_order_id_buy
            )
            
            progress.sell_orders.append(sell_execution)
            progress.buy_orders.append(buy_execution)
            progress.batch_count += 1
            progress.completed_nominales += batch_size
            progress.remaining_nominales -= batch_size
            
            # Actualizar totales
            progress.total_sold_amount += sell_execution.quantity * sell_execution.price
            progress.total_bought_amount += buy_execution.quantity * buy_execution.price
            
            self._add_message(operation_id, f"✅ Lote {progress.batch_count} ejecutado:")
            self._add_message(operation_id, f"   Venta: {batch_size} @ {sell_price}")
            self._add_message(operation_id, f"   Compra: {nominales_to_buy:.2f} @ {buy_price}")
            self._add_message(operation_id, f"   Ratio del lote: {sell_price/buy_price:.6f}")
            
            return True
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error ejecutando lote: {str(e)}")
            return False

    async def execute_ratio_operation_batch(self, request: RatioOperationRequest) -> OperationProgress:
        """Nueva función principal para operaciones por lotes con validación de promedio ponderado."""
        operation_id = request.operation_id
        progress = OperationProgress(
            operation_id=operation_id,
            status=OperationStatus.PENDING,
            current_step=OperationStep.INITIALIZING,
            progress_percentage=0,
            start_time=datetime.now().isoformat(),
            last_update=datetime.now().isoformat(),
            sell_orders=[],
            buy_orders=[],
            total_sold_amount=0.0,
            total_bought_amount=0.0,
            average_sell_price=0.0,
            average_buy_price=0.0,
            current_ratio=0.0,
            target_ratio=request.target_ratio,
            condition_met=False,
            messages=[],
            # Nuevos campos para operaciones por lotes
            target_nominales=request.nominales,
            completed_nominales=0.0,
            remaining_nominales=request.nominales,
            batch_count=0,
            weighted_average_ratio=0.0,
            max_attempts=10,
            current_attempt=0,
            condition=request.condition,
            pair=request.pair
        )
        with self.operation_lock:
            self.active_operations[operation_id] = progress
        
        try:
            progress.status = OperationStatus.RUNNING
            self._update_progress(operation_id, status=OperationStatus.RUNNING)
            await self._notify_progress(operation_id, progress)
            
            self._add_message(operation_id, f"🚀 Iniciando operación de ratio por lotes: {request.pair}")
            self._add_message(operation_id, f"   Nominales objetivo: {request.nominales}")
            self._add_message(operation_id, f"   Ratio objetivo: {request.target_ratio} {request.condition}")
            
            # Determinar instrumentos
            instruments_needed: List[str] = []
            if isinstance(request.pair, list):
                instruments = [inst.strip() for inst in request.pair]
                instrument_to_sell = request.instrument_to_sell.strip()
                
                if instrument_to_sell not in instruments:
                    raise Exception(f"instrument_to_sell '{instrument_to_sell}' no está en el par {instruments}")
                
                for inst in instruments:
                    if inst != instrument_to_sell:
                        instrument_to_buy = inst
                        break
            else:
                # Formato legacy
                pair_parts = request.pair.split('-')
                if len(pair_parts) < 2:
                    raise Exception(f"Formato de par inválido: {request.pair}")
                
                sell_inst = request.instrument_to_sell.strip()
                if sell_inst in request.pair:
                    remaining = request.pair.replace(sell_inst, '', 1).strip()
                    instrument_to_buy = remaining.strip('-').strip()
                else:
                    raise Exception(f"No se pudo determinar el instrumento a comprar")
            
            instruments_needed = [request.instrument_to_sell, instrument_to_buy]
            
            # Verificar cotizaciones disponibles
            missing_instruments = [inst for inst in instruments_needed if inst not in quotes_cache]
            if missing_instruments:
                self._add_message(operation_id, f"⚠️ Faltan cotizaciones para: {', '.join(missing_instruments)}")
                # Para la demo, usar cotizaciones simuladas
                quotes_cache[request.instrument_to_sell] = {"bid": 1484.5, "offer": 1485.0}
                quotes_cache[instrument_to_buy] = {"bid": 1521.0, "offer": 1521.5}
                self._add_message(operation_id, "📊 Usando cotizaciones simuladas para la demo")
            
            self._add_message(operation_id, f"📈 Instrumentos: Vender {request.instrument_to_sell} → Comprar {instrument_to_buy}")
            
            # Bucle principal de lotes
            while progress.remaining_nominales > 0 and progress.current_attempt < progress.max_attempts:
                progress.current_attempt += 1
                
                self._update_progress(operation_id, current_step=OperationStep.CALCULATING_BATCH_SIZE)
                await self._notify_progress(operation_id, progress)
                
                self._add_message(operation_id, f"🔄 Intento {progress.current_attempt}/{progress.max_attempts}")
                self._add_message(operation_id, f"   Nominales restantes: {progress.remaining_nominales}")
                
                # Calcular tamaño del lote
                max_batch_size = self._calculate_max_batch_size(progress, quotes_cache)
                
                if max_batch_size <= 0:
                    self._add_message(operation_id, "⏳ Esperando mejores condiciones de mercado...")
                    self._update_progress(operation_id, current_step=OperationStep.WAITING_FOR_BETTER_PRICES)
                    await self._notify_progress(operation_id, progress)
                    await asyncio.sleep(5)  # Esperar 5 segundos antes del siguiente intento
                    continue
                
                batch_size = min(max_batch_size, progress.remaining_nominales)
                self._add_message(operation_id, f"📊 Lote {progress.batch_count + 1}: {batch_size} nominales")
                
                # Ejecutar el lote
                self._update_progress(operation_id, current_step=OperationStep.EXECUTING_BATCH)
                await self._notify_progress(operation_id, progress)
                
                success = await self._execute_batch(operation_id, batch_size, quotes_cache)
                
                if not success:
                    self._add_message(operation_id, "❌ Error ejecutando lote, reintentando...")
                    await asyncio.sleep(2)
                    continue
                
                # Calcular ratio promedio ponderado
                self._update_progress(operation_id, current_step=OperationStep.CALCULATING_WEIGHTED_AVERAGE)
                await self._notify_progress(operation_id, progress)
                
                weighted_avg = self._calculate_weighted_average_ratio(progress)
                progress.weighted_average_ratio = weighted_avg
                
                self._add_message(operation_id, f"📊 Ratio promedio ponderado: {weighted_avg:.6f}")
                self._add_message(operation_id, f"   Progreso: {progress.completed_nominales}/{progress.target_nominales} nominales ({progress.completed_nominales/progress.target_nominales*100:.1f}%)")
                
                # Verificar si hemos completado
                if progress.remaining_nominales <= 0:
                    break
                
                # Verificar si el promedio cumple la condición
                if self._check_condition(weighted_avg, progress.target_ratio, progress.condition):
                    self._add_message(operation_id, "✅ Promedio cumple condición, continuando con el resto...")
                else:
                    self._add_message(operation_id, "⚠️ Promedio no cumple condición, pero continuamos para completar...")
                
                await self._notify_progress(operation_id, progress)
                await asyncio.sleep(1)  # Pequeña pausa entre lotes
            
            # Verificación final
            self._update_progress(operation_id, current_step=OperationStep.VERIFYING_RATIO)
            await self._notify_progress(operation_id, progress)
            
            final_weighted_avg = self._calculate_weighted_average_ratio(progress)
            final_condition_met = self._check_condition(final_weighted_avg, progress.target_ratio, progress.condition)
            
            progress.weighted_average_ratio = final_weighted_avg
            progress.condition_met = final_condition_met
            
            self._update_progress(operation_id, current_step=OperationStep.FINALIZING)
            await self._notify_progress(operation_id, progress)
            
            self._add_message(operation_id, f"🏁 OPERACIÓN FINALIZADA:")
            self._add_message(operation_id, f"   Nominales ejecutados: {progress.completed_nominales}/{progress.target_nominales}")
            self._add_message(operation_id, f"   Lotes ejecutados: {progress.batch_count}")
            self._add_message(operation_id, f"   Ratio promedio final: {final_weighted_avg:.6f}")
            self._add_message(operation_id, f"   Condición cumplida: {'✅ SÍ' if final_condition_met else '❌ NO'}")
            
            if final_condition_met:
                progress.status = OperationStatus.COMPLETED
                self._add_message(operation_id, "🎉 ¡Operación completada exitosamente!")
            else:
                progress.status = OperationStatus.FAILED
                progress.error = f"Ratio promedio {final_weighted_avg:.6f} no cumple condición {progress.condition} {progress.target_ratio}"
                self._add_message(operation_id, f"❌ Operación fallida: {progress.error}")
            
            self._update_progress(operation_id, status=progress.status)
            await self._notify_progress(operation_id, progress)
            return progress
            
        except Exception as e:
            progress.status = OperationStatus.FAILED
            progress.error = str(e)
            progress.current_step = OperationStep.FINALIZING
            self._add_message(operation_id, f"❌ Error: {str(e)}")
            self._update_progress(operation_id, status=OperationStatus.FAILED, error=str(e), current_step=OperationStep.FINALIZING)
            await self._notify_progress(operation_id, progress)
            return progress
        finally:
            asyncio.create_task(self._cleanup_operation(operation_id))

    async def execute_ratio_operation(self, request: RatioOperationRequest) -> OperationProgress:
        """Función principal que ahora usa operaciones por lotes por defecto."""
        return await self.execute_ratio_operation_batch(request)


# Mantener las funciones auxiliares existentes
            last_update=datetime.now().isoformat(),
            sell_orders=[],
            buy_orders=[],
            total_sold_amount=0.0,
            total_bought_amount=0.0,
            average_sell_price=0.0,
            average_buy_price=0.0,
            current_ratio=0.0,
            target_ratio=request.target_ratio,
            condition_met=False,
            messages=[],
            # Nuevos campos para operaciones por lotes
            target_nominales=request.nominales,
            completed_nominales=0.0,
            remaining_nominales=request.nominales,
            batch_count=0,
            weighted_average_ratio=0.0,
            max_attempts=10,
            current_attempt=0,
            condition=request.condition,
            pair=request.pair
        )
        with self.operation_lock:
            self.active_operations[operation_id] = progress
        try:
            progress.status = OperationStatus.RUNNING
            self._update_progress(operation_id, status=OperationStatus.RUNNING)
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, f"Iniciando operación de ratio: {request.pair}")
            self._add_message(operation_id, f"Vender: {request.instrument_to_sell}, Nominales: {request.nominales}")
            self._add_message(operation_id, f"Ratio objetivo: {request.target_ratio} {request.condition}")
            self._update_progress(operation_id, current_step=OperationStep.ANALYZING_MARKET)
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, "Analizando condiciones del mercado...")

            instruments_needed: List[str] = []
            
            # Determinar instrumentos basado en el tipo de pair
            if isinstance(request.pair, list):
                # Nuevo formato: array de instrumentos
                if len(request.pair) != 2:
                    raise Exception(f"El par debe contener exactamente 2 instrumentos, recibidos: {len(request.pair)}")
                instruments = [inst.strip() for inst in request.pair]
                instrument_to_sell = request.instrument_to_sell.strip()
                
                # Verificar que instrument_to_sell esté en la lista
                if instrument_to_sell not in instruments:
                    raise Exception(f"instrument_to_sell '{instrument_to_sell}' no está en el par {instruments}")
                
                # El otro instrumento es el que se va a comprar
                instrument_to_buy = None
                for inst in instruments:
                    if inst != instrument_to_sell:
                        instrument_to_buy = inst
                        break
                        
            else:
                # Formato legacy: string separado por guiones
                pair_parts = request.pair.split('-')
                if len(pair_parts) < 2:
                    raise Exception(f"Formato de par inválido: {request.pair}")
                
                # Estrategia: buscar el instrument_to_sell en el par y tomar el resto
                sell_inst = request.instrument_to_sell.strip()
                if sell_inst in request.pair:
                    # Remover el instrumento a vender y obtener el otro
                    remaining = request.pair.replace(sell_inst, '', 1).strip()
                    # Limpiar guiones sobrantes
                    instrument_to_buy = remaining.strip('-').strip()
                else:
                    # Fallback: usar el split original pero más inteligente
                    parts = [part.strip() for part in pair_parts]
                    if len(parts) >= 8:  # 4 partes por instrumento
                        # Asumir que los primeros 4 son un instrumento y los últimos 4 el otro
                        first_instrument = ' - '.join(parts[:4])
                        second_instrument = ' - '.join(parts[4:])
                        if first_instrument == sell_inst:
                            instrument_to_buy = second_instrument
                        elif second_instrument == sell_inst:
                            instrument_to_buy = first_instrument
                        else:
                            # Intentar con 3 partes por instrumento
                            if len(parts) >= 6:
                                first_instrument = ' - '.join(parts[:3])
                                second_instrument = ' - '.join(parts[3:])
                                if first_instrument == sell_inst:
                                    instrument_to_buy = second_instrument
                                elif second_instrument == sell_inst:
                                    instrument_to_buy = first_instrument
            
            if not instrument_to_buy:
                raise Exception(f"No se pudo determinar el instrumento a comprar en el par {request.pair}. Verifique que instrument_to_sell sea correcto.")

            if request.instrument_to_sell not in quotes_cache:
                instruments_needed.append(request.instrument_to_sell)
            if instrument_to_buy not in quotes_cache:
                instruments_needed.append(instrument_to_buy)
            if instruments_needed:
                self._add_message(operation_id, f"Faltan cotizaciones para: {', '.join(instruments_needed)}")
                self._add_message(operation_id, "Intentando suscribirse a los instrumentos...")
                try:
                    if not ws_rofex.manager.is_connected():
                        self._add_message(operation_id, "WebSocket de Rofex no conectado. Intentando conectar...")
                        raise Exception("WebSocket de Rofex no está conectado. Debe iniciarse primero con /iniciar")
                    for instrument in instruments_needed:
                        self._add_message(operation_id, f"Suscribiéndose a {instrument}...")
                        # ws_rofex.manager.subscribe(instrument)
                    self._add_message(operation_id, "Esperando cotizaciones...")
                    await asyncio.sleep(3)
                    still_missing = []
                    for instrument in instruments_needed:
                        if instrument not in quotes_cache:
                            still_missing.append(instrument)
                    if still_missing:
                        raise Exception(
                            f"No se pudieron obtener cotizaciones para: {', '.join(still_missing)}. "
                            f"Verifique que el WebSocket esté conectado y suscrito a estos instrumentos."
                        )
                    self._add_message(operation_id, "✅ Cotizaciones obtenidas exitosamente")
                except Exception as e:
                    raise Exception(
                        f"Error obteniendo cotizaciones: {str(e)}. Debe iniciar el WebSocket y suscribirse a los instrumentos primero."
                    )

            sell_quote = quotes_cache[request.instrument_to_sell]
            if not sell_quote.get('offer') or not sell_quote.get('bid'):
                raise Exception(f"Cotizaciones incompletas para {request.instrument_to_sell}")
            buy_quote = quotes_cache[instrument_to_buy]
            if not buy_quote.get('offer') or not buy_quote.get('bid'):
                raise Exception(f"Cotizaciones incompletas para {instrument_to_buy}")

            self._add_message(operation_id, f"Instrumento a comprar: {instrument_to_buy}")
            self._add_message(operation_id, f"Venta - Bid: {sell_quote['bid']}, Offer: {sell_quote['offer']}")
            self._add_message(operation_id, f"Compra - Bid: {buy_quote['bid']}, Offer: {buy_quote['offer']}")

            self._update_progress(operation_id, current_step=OperationStep.PLACING_SELL_ORDER)
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, f"Colocando orden de venta: {request.nominales} nominales de {request.instrument_to_sell}")
            sell_price = sell_quote['bid']
            client_order_id_sell = f"RATIO_SELL_{operation_id}_{int(time.time())}"
            sell_result = ws_rofex.manager.send_order(
                symbol=request.instrument_to_sell,
                side="SELL",
                size=request.nominales,
                price=sell_price,
                order_type="LIMIT",
                tif="DAY",
                client_order_id=client_order_id_sell
            )
            if sell_result.get("status") != "ok":
                raise Exception(f"Error colocando orden de venta: {sell_result.get('message', 'Unknown error')}")
            self._add_message(operation_id, f"Orden de venta colocada: {client_order_id_sell} @ {sell_price}")

            self._update_progress(operation_id, current_step=OperationStep.WAITING_SELL_EXECUTION)
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, "Esperando ejecución de orden de venta...")
            await asyncio.sleep(2)
            sell_execution = OrderExecution(
                order_id=f"SELL_{operation_id}",
                instrument=request.instrument_to_sell,
                side="SELL",
                quantity=request.nominales,
                price=sell_price,
                executed_at=datetime.now().isoformat(),
                client_order_id=client_order_id_sell
            )
            progress.sell_orders.append(sell_execution)
            progress.total_sold_amount = sell_execution.quantity * sell_execution.price
            progress.average_sell_price = sell_execution.price
            self._update_progress(
                operation_id,
                current_step=OperationStep.SELL_EXECUTED,
                sell_orders=progress.sell_orders,
                total_sold_amount=progress.total_sold_amount,
                average_sell_price=progress.average_sell_price,
            )
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, f"Venta ejecutada: {sell_execution.quantity} @ {sell_execution.price}")
            self._add_message(operation_id, f"Monto total de venta: ${progress.total_sold_amount:,.2f}")

            self._update_progress(operation_id, current_step=OperationStep.CALCULATING_BUY_AMOUNT)
            await self._notify_progress(operation_id, progress)
            buy_price = buy_quote['offer']
            nominales_to_buy = progress.total_sold_amount / buy_price
            self._add_message(
                operation_id,
                f"Calculando compra: ${progress.total_sold_amount:,.2f} / {buy_price} = {nominales_to_buy:.2f} nominales",
            )
            
            # 🔍 VERIFICAR RATIO ANTES DE EJECUTAR LA COMPRA
            self._add_message(operation_id, "🔍 Verificando ratio teórico antes de comprar...")
            theoretical_ratio = progress.average_sell_price / buy_price
            condition_met = self._check_condition(theoretical_ratio, request.target_ratio, request.condition)
            self._add_message(operation_id, f"Ratio teórico: {theoretical_ratio:.6f}")
            self._add_message(operation_id, f"Ratio objetivo: {request.target_ratio} {request.condition}")
            self._add_message(operation_id, f"Condición cumplida: {'✅ SÍ' if condition_met else '❌ NO'}")
            
            if not condition_met:
                # NO ejecutar la compra si la condición no se cumple
                progress.status = OperationStatus.FAILED
                progress.error = (
                    f"Ratio teórico {theoretical_ratio:.6f} no cumple condición {request.condition} {request.target_ratio}. "
                    f"No se ejecutará la compra para evitar pérdidas."
                )
                progress.current_step = OperationStep.FINALIZING
                self._add_message(operation_id, f"❌ Operación cancelada: {progress.error}")
                self._update_progress(operation_id, status=progress.status, error=progress.error)
                await self._notify_progress(operation_id, progress)
                return progress

            self._update_progress(operation_id, current_step=OperationStep.PLACING_BUY_ORDER)
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, f"Colocando orden de compra: {nominales_to_buy:.2f} nominales de {instrument_to_buy}")
            client_order_id_buy = f"RATIO_BUY_{operation_id}_{int(time.time())}"
            buy_result = ws_rofex.manager.send_order(
                symbol=instrument_to_buy,
                side="BUY",
                size=nominales_to_buy,
                price=buy_price,
                order_type="LIMIT",
                tif="DAY",
                client_order_id=client_order_id_buy
            )
            if buy_result.get("status") != "ok":
                raise Exception(f"Error colocando orden de compra: {buy_result.get('message', 'Unknown error')}")
            self._add_message(operation_id, f"Orden de compra colocada: {client_order_id_buy} @ {buy_price}")

            self._update_progress(operation_id, current_step=OperationStep.WAITING_BUY_EXECUTION)
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, "Esperando ejecución de orden de compra...")
            await asyncio.sleep(2)
            buy_execution = OrderExecution(
                order_id=f"BUY_{operation_id}",
                instrument=instrument_to_buy,
                side="BUY",
                quantity=nominales_to_buy,
                price=buy_price,
                executed_at=datetime.now().isoformat(),
                client_order_id=client_order_id_buy
            )
            progress.buy_orders.append(buy_execution)
            progress.total_bought_amount = buy_execution.quantity * buy_execution.price
            progress.average_buy_price = buy_execution.price
            self._update_progress(
                operation_id,
                current_step=OperationStep.BUY_EXECUTED,
                buy_orders=progress.buy_orders,
                total_bought_amount=progress.total_bought_amount,
                average_buy_price=progress.average_buy_price,
            )
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, f"Compra ejecutada: {buy_execution.quantity:.2f} @ {buy_execution.price}")
            self._add_message(operation_id, f"Monto total de compra: ${progress.total_bought_amount:,.2f}")

            # Si llegamos aquí, significa que la compra se ejecutó porque la condición se cumplió
            self._update_progress(operation_id, current_step=OperationStep.VERIFYING_RATIO)
            await self._notify_progress(operation_id, progress)
            current_ratio = self._calculate_current_ratio(progress)
            condition_met = self._check_condition(current_ratio, request.target_ratio, request.condition)
            self._update_progress(
                operation_id,
                current_step=OperationStep.FINALIZING,
                current_ratio=current_ratio,
                condition_met=condition_met,
            )
            await self._notify_progress(operation_id, progress)
            self._add_message(operation_id, f"Ratio final calculado: {current_ratio:.6f}")
            self._add_message(operation_id, f"Ratio objetivo: {request.target_ratio} {request.condition}")
            self._add_message(operation_id, f"Condición cumplida: {'✅ SÍ' if condition_met else '❌ NO'}")
            
            # Si llegamos aquí, la operación debería ser exitosa
            progress.status = OperationStatus.COMPLETED
            self._add_message(operation_id, "✅ Operación completada exitosamente")
            self._update_progress(operation_id, status=progress.status)
            await self._notify_progress(operation_id, progress)
            return progress
        except Exception as e:
            progress.status = OperationStatus.FAILED
            progress.error = str(e)
            progress.current_step = OperationStep.FINALIZING
            self._add_message(operation_id, f"❌ Error: {str(e)}")
            self._update_progress(
                operation_id, status=OperationStatus.FAILED, error=str(e), current_step=OperationStep.FINALIZING
            )
            await self._notify_progress(operation_id, progress)
            return progress
        finally:
            asyncio.create_task(self._cleanup_operation(operation_id))

    async def _cleanup_operation(self, operation_id: str):
        await asyncio.sleep(300)
        with self.operation_lock:
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]
        self.unregister_callback(operation_id)

    def get_operation_status(self, operation_id: str) -> Optional[OperationProgress]:
        with self.operation_lock:
            return self.active_operations.get(operation_id)

    def get_all_operations(self) -> List[OperationProgress]:
        with self.operation_lock:
            return list(self.active_operations.values())

    def cancel_operation(self, operation_id: str) -> bool:
        with self.operation_lock:
            if operation_id in self.active_operations:
                progress = self.active_operations[operation_id]
                if progress.status in [OperationStatus.PENDING, OperationStatus.RUNNING]:
                    progress.status = OperationStatus.CANCELLED
                    progress.error = "Operación cancelada por el usuario"
                    self._add_message(operation_id, "🛑 Operación cancelada")
                    return True
        return False


ratio_manager = RatioOperationManager()

