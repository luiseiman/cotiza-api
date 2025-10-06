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
    max_attempts: int = 0  # 0 = intentos infinitos (hasta cancelar manualmente)
    current_attempt: int = 0  # Intento actual
    condition: str = ""  # Condición de ratio (<= o >=)
    pair: str | List[str] = ""  # Par de instrumentos
    # Campos adicionales para información detallada
    current_batch_size: float = 0.0  # Tamaño del lote actual
    success_rate: float = 0.0  # Porcentaje de éxito (lotes exitosos / intentos)
    estimated_completion_time: str = ""  # Tiempo estimado de finalización
    market_condition: str = ""  # Condición del mercado (favorable/desfavorable)


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
                # Actualizar campos adicionales antes de notificar
                self._update_progress_fields(operation_id, progress)
                await self.callbacks[operation_id](progress)
            except Exception as e:
                print(f"[ratio_ops] Error en callback: {e}")

    def _update_progress_fields(self, operation_id: str, progress: OperationProgress):
        """Actualiza campos adicionales para información detallada"""
        if operation_id not in self.active_operations:
            return
            
        # Usar el lock para actualizar de forma segura
        with self.operation_lock:
            if operation_id not in self.active_operations:
                return
                
            current_progress = self.active_operations[operation_id]
            
            # Calcular porcentaje de éxito
            if progress.current_attempt > 0:
                current_progress.success_rate = (progress.batch_count / progress.current_attempt) * 100
            else:
                current_progress.success_rate = 0.0
            
            # Determinar condición del mercado
            if progress.weighted_average_ratio > 0:
                condition_met = self._check_condition(progress.weighted_average_ratio, progress.target_ratio, progress.condition)
                current_progress.market_condition = "favorable" if condition_met else "desfavorable"
            else:
                current_progress.market_condition = "evaluando"
            
            # Estimar tiempo de finalización (muy básico)
            if progress.current_attempt > 0 and progress.remaining_nominales > 0:
                # Estimación basada en el progreso actual
                avg_nominales_per_attempt = progress.completed_nominales / max(progress.current_attempt, 1)
                remaining_attempts = progress.remaining_nominales / max(avg_nominales_per_attempt, 0.1)
                estimated_seconds = remaining_attempts * 5  # 5 segundos promedio por intento
                
                if estimated_seconds < 60:
                    current_progress.estimated_completion_time = f"{int(estimated_seconds)}s"
                elif estimated_seconds < 3600:
                    current_progress.estimated_completion_time = f"{int(estimated_seconds/60)}m {int(estimated_seconds%60)}s"
                else:
                    current_progress.estimated_completion_time = f"{int(estimated_seconds/3600)}h {int((estimated_seconds%3600)/60)}m"
            else:
                current_progress.estimated_completion_time = "calculando..."
            
            # Actualizar también en el objeto progress que se pasa por parámetro
            progress.success_rate = current_progress.success_rate
            progress.market_condition = current_progress.market_condition
            progress.estimated_completion_time = current_progress.estimated_completion_time

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

    def _add_message_unlocked(self, operation_id: str, message: str):
        """Versión de _add_message que NO adquiere el lock (para usar cuando ya se tiene el lock)"""
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
    
    def _show_current_quotes(self, operation_id: str, instrument_to_sell: str, instrument_to_buy: str, target_ratio: float = None, condition: str = ""):
        """Muestra las cotizaciones actuales en tiempo real con análisis de ratio"""
        from ratios_worker import obtener_datos_mercado
        
        sell_data = obtener_datos_mercado(instrument_to_sell)
        buy_data = obtener_datos_mercado(instrument_to_buy)
        
        if sell_data and buy_data:
            # Calcular ratio actual con cotizaciones reales
            current_ratio = sell_data.get('bid', 0) / buy_data.get('offer', 1) if buy_data.get('offer', 0) > 0 else 0
            
            # Actualizar el objeto OperationProgress con los valores reales
            if operation_id in self.active_operations:
                progress = self.active_operations[operation_id]
                progress.current_ratio = current_ratio
                if target_ratio is not None and condition:
                    progress.condition_met = self._check_condition(current_ratio, target_ratio, condition)
                    print(f"[DEBUG] Actualizando progress: current_ratio={current_ratio}, condition_met={progress.condition_met}")
            
            self._add_message(operation_id, f"📊 Cotizaciones actuales:")
            self._add_message(operation_id, f"   {instrument_to_sell}: bid={sell_data.get('bid', 'N/A')}, offer={sell_data.get('offer', 'N/A')}")
            self._add_message(operation_id, f"   {instrument_to_buy}: bid={buy_data.get('bid', 'N/A')}, offer={buy_data.get('offer', 'N/A')}")
            
            # Mostrar análisis detallado del ratio si se proporciona target_ratio
            if target_ratio is not None and condition:
                current_ratio_pct = current_ratio * 100
                target_ratio_pct = target_ratio * 100
                difference_pct = current_ratio_pct - target_ratio_pct
                
                self._add_message(operation_id, f"📈 Análisis de Ratio:")
                self._add_message(operation_id, f"   Ratio actual: {current_ratio:.6f} ({current_ratio_pct:.2f}%)")
                self._add_message(operation_id, f"   Ratio objetivo: {condition} {target_ratio:.6f} ({target_ratio_pct:.2f}%)")
                
                if difference_pct > 0:
                    self._add_message(operation_id, f"   Diferencia: +{difference_pct:.2f}% por encima del objetivo")
                else:
                    self._add_message(operation_id, f"   Diferencia: {difference_pct:.2f}% por debajo del objetivo")
                
                # Indicar si cumple la condición
                condition_met = self._check_condition(current_ratio, target_ratio, condition)
                status_icon = "✅" if condition_met else "❌"
                self._add_message(operation_id, f"   Condición: {status_icon} {'CUMPLE' if condition_met else 'NO CUMPLE'}")
            else:
                self._add_message(operation_id, f"   Ratio actual: {current_ratio:.6f}")
        else:
            missing_instruments = []
            if not sell_data:
                missing_instruments.append(instrument_to_sell)
            if not buy_data:
                missing_instruments.append(instrument_to_buy)
            
            self._add_message(operation_id, f"⚠️ Sin cotizaciones reales para: {', '.join(missing_instruments)}")
            self._add_message(operation_id, "💡 Verificar que los instrumentos estén suscritos en el sistema")
    
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
        # Determinar instrumentos
        instrument_to_sell = None
        instrument_to_buy = None
        
        if isinstance(progress.pair, list):
            instruments = [inst.strip() for inst in progress.pair]
            instrument_to_sell = progress.sell_orders[0].instrument if progress.sell_orders else instruments[0]
            for inst in instruments:
                if inst != instrument_to_sell:
                    instrument_to_buy = inst
                    break
        else:
            # Para el primer lote, usar los instrumentos del request
            instrument_to_sell = "MERV - XMEV - TX26 - 24hs"  # Fallback
            instrument_to_buy = "MERV - XMEV - TX28 - 24hs"  # Fallback
        
        if not instrument_to_sell or not instrument_to_buy:
            return 0.0
        
        # Obtener cotizaciones actuales usando la función real
        from ratios_worker import obtener_datos_mercado
        
        sell_quote = obtener_datos_mercado(instrument_to_sell)
        buy_quote = obtener_datos_mercado(instrument_to_buy)
        
        if not sell_quote or not buy_quote:
            print(f"[ratio_ops] No hay cotizaciones reales para {instrument_to_sell} o {instrument_to_buy}")
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
        
        # Para la demo, permitir vender al menos 10 nominales por lote
        # En producción, esto sería más sofisticado
        return min(progress.remaining_nominales, max(10.0, progress.target_nominales * 0.1))
    
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
            max_attempts=0,  # Intentos infinitos
            current_attempt=0,
            condition=request.condition,
            pair=request.pair
        )
        # Usar timeout para evitar deadlocks
        if not self.operation_lock.acquire(timeout=30):
            print(f"⚠️ Timeout adquiriendo lock para operación {operation_id}")
            return OperationProgress(
                operation_id=operation_id,
                status=OperationStatus.FAILED,
                current_step=OperationStep.FINALIZING,
                progress_percentage=100,
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
                messages=["❌ Error: Timeout adquiriendo lock del sistema"],
                error="Timeout adquiriendo lock del sistema"
            )
        
        try:
            self.active_operations[operation_id] = progress
        finally:
            self.operation_lock.release()
        
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
            
            # Verificar cotizaciones disponibles usando la función real
            from ratios_worker import obtener_datos_mercado
            
            sell_data = obtener_datos_mercado(request.instrument_to_sell)
            buy_data = obtener_datos_mercado(instrument_to_buy)
            
            if not sell_data or not buy_data:
                missing_instruments = []
                if not sell_data:
                    missing_instruments.append(request.instrument_to_sell)
                if not buy_data:
                    missing_instruments.append(instrument_to_buy)
                
                self._add_message(operation_id, f"❌ No hay cotizaciones reales disponibles para: {', '.join(missing_instruments)}")
                self._add_message(operation_id, "💡 Asegúrate de que los instrumentos estén suscritos en el sistema")
                
                # Para la demo, usar cotizaciones simuladas solo si no hay datos reales
                if not sell_data:
                    quotes_cache[request.instrument_to_sell] = {"bid": 1484.5, "offer": 1485.0, "last": 1484.75}
                    self._add_message(operation_id, f"📊 Usando cotización simulada para {request.instrument_to_sell}")
                if not buy_data:
                    quotes_cache[instrument_to_buy] = {"bid": 1521.0, "offer": 1521.5, "last": 1521.25}
                    self._add_message(operation_id, f"📊 Usando cotización simulada para {instrument_to_buy}")
            else:
                self._add_message(operation_id, f"✅ Cotizaciones reales disponibles:")
                self._add_message(operation_id, f"   {request.instrument_to_sell}: bid={sell_data.get('bid')}, offer={sell_data.get('offer')}")
                self._add_message(operation_id, f"   {instrument_to_buy}: bid={buy_data.get('bid')}, offer={buy_data.get('offer')}")
            
            self._add_message(operation_id, f"📈 Instrumentos: Vender {request.instrument_to_sell} → Comprar {instrument_to_buy}")
            
            # Bucle principal de lotes - continúa indefinidamente hasta completar o cancelar
            # LÍMITE DE SEGURIDAD: máximo 1000 intentos para evitar cuelgues infinitos
            max_safety_attempts = 1000
            safety_attempt = 0
            
            while (progress.remaining_nominales > 0 and 
                   progress.status == OperationStatus.RUNNING and 
                   safety_attempt < max_safety_attempts):
                progress.current_attempt += 1
                safety_attempt += 1
                
                # Verificar límite de seguridad
                if safety_attempt >= max_safety_attempts:
                    self._add_message(operation_id, f"⚠️ Límite de seguridad alcanzado ({max_safety_attempts} intentos)")
                    progress.status = OperationStatus.FAILED
                    progress.error = "Límite de seguridad alcanzado para evitar cuelgue infinito"
                    break
                
                self._update_progress(operation_id, current_step=OperationStep.CALCULATING_BATCH_SIZE)
                await self._notify_progress(operation_id, progress)
                
                self._add_message(operation_id, f"🔄 Intento {progress.current_attempt} (intentos infinitos hasta completar o cancelar)")
                self._add_message(operation_id, f"   Nominales restantes: {progress.remaining_nominales}")
                
                # Mostrar cotizaciones actuales en tiempo real con análisis de ratio
                self._show_current_quotes(operation_id, request.instrument_to_sell, instrument_to_buy, request.target_ratio, request.condition)
                
                # Notificar el progreso actualizado después de calcular los ratios
                await self._notify_progress(operation_id, progress)
                
                # Calcular tamaño del lote
                max_batch_size = self._calculate_max_batch_size(progress, quotes_cache)
                
                if max_batch_size <= 0:
                    self._add_message(operation_id, "⏳ Esperando mejores condiciones de mercado... (continuará indefinidamente)")
                    self._add_message(operation_id, "💡 El ratio actual no cumple la condición o no hay cotizaciones disponibles")
                    self._update_progress(operation_id, current_step=OperationStep.WAITING_FOR_BETTER_PRICES)
                    await self._notify_progress(operation_id, progress)
                    await asyncio.sleep(10)  # Esperar 10 segundos antes del siguiente intento
                    continue
                
                batch_size = min(max_batch_size, progress.remaining_nominales)
                self._add_message(operation_id, f"📊 Lote {progress.batch_count + 1}: {batch_size} nominales")
                
                # Actualizar tamaño del lote actual
                self._update_progress(operation_id, current_batch_size=batch_size)
                
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
            
            # Verificar que realmente se ejecutaron lotes antes de marcar como exitosa
            if progress.batch_count > 0 and progress.completed_nominales > 0 and final_condition_met:
                progress.status = OperationStatus.COMPLETED
                self._add_message(operation_id, "🎉 ¡Operación completada exitosamente!")
            elif progress.batch_count == 0 or progress.completed_nominales == 0:
                progress.status = OperationStatus.FAILED
                progress.error = "No se ejecutaron lotes - operación cancelada o sin cotizaciones disponibles"
                self._add_message(operation_id, "❌ Operación fallida: No se ejecutaron lotes")
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

    def get_operation_status(self, operation_id: str) -> Optional[OperationProgress]:
        # Usar timeout para evitar deadlocks
        if not self.operation_lock.acquire(timeout=5):
            print(f"⚠️ Timeout obteniendo estado de operación {operation_id}")
            return None
        
        try:
            return self.active_operations.get(operation_id)
        finally:
            self.operation_lock.release()

    def get_all_operations(self) -> List[OperationProgress]:
        # Usar timeout para evitar deadlocks
        if not self.operation_lock.acquire(timeout=5):
            print(f"⚠️ Timeout obteniendo todas las operaciones")
            return []
        
        try:
            return list(self.active_operations.values())
        finally:
            self.operation_lock.release()

    def cancel_operation(self, operation_id: str) -> bool:
        # Usar timeout para evitar deadlocks
        if not self.operation_lock.acquire(timeout=5):
            print(f"⚠️ Timeout cancelando operación {operation_id}")
            return False
        
        try:
            if operation_id in self.active_operations:
                progress = self.active_operations[operation_id]
                if progress.status in [OperationStatus.PENDING, OperationStatus.RUNNING]:
                    progress.status = OperationStatus.CANCELLED
                    progress.error = "Operación cancelada por el usuario"
                    # Usar versión sin lock para evitar deadlock
                    self._add_message_unlocked(operation_id, "🛑 Operación cancelada")
                    return True
            return False
        finally:
            self.operation_lock.release()


ratio_manager = RatioOperationManager()

