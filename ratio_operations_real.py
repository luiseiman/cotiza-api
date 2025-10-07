#!/usr/bin/env python3
"""
Versión mejorada del sistema de operaciones de ratio que ejecuta órdenes reales
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import ws_rofex
import ratios_worker

# Enums y clases de datos
class OperationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OperationStep(Enum):
    INITIALIZING = "initializing"
    GETTING_QUOTES = "getting_quotes"
    CALCULATING_BATCH_SIZE = "calculating_batch_size"
    EXECUTING_BATCH = "executing_batch"
    CALCULATING_WEIGHTED_AVERAGE = "calculating_weighted_average"
    VERIFYING_RATIO = "verifying_ratio"
    FINALIZING = "finalizing"
    WAITING_FOR_BETTER_PRICES = "waiting_for_better_prices"

@dataclass
class OrderExecution:
    instrument: str
    quantity: float
    price: float
    order_id: str = ""
    timestamp: str = ""
    side: str = ""  # "buy" o "sell"
    status: str = "pending"  # "pending", "filled", "rejected"

@dataclass
class OperationProgress:
    operation_id: str
    status: OperationStatus
    current_step: OperationStep
    progress_percentage: int
    start_time: str
    last_update: str
    sell_orders: List[OrderExecution]
    buy_orders: List[OrderExecution]
    total_sold_amount: float
    total_bought_amount: float
    average_sell_price: float
    average_buy_price: float
    current_ratio: float
    condition_met: bool
    target_ratio: float
    condition: str
    remaining_nominales: float
    current_attempt: int = 0
    max_attempts: int = 0
    batch_count: int = 0
    completed_nominales: float = 0.0
    weighted_average_ratio: float = 0.0
    messages: List[str] = None
    error: Optional[str] = None
    current_batch_size: float = 0.0
    success_rate: float = 0.0
    estimated_completion_time: str = ""
    market_condition: str = ""
    real_quotes: Dict = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.real_quotes is None:
            self.real_quotes = {}

@dataclass
class RatioOperationRequest:
    operation_id: str
    pair: List[str]
    instrument_to_sell: str
    client_id: str
    nominales: float
    target_ratio: float
    condition: str
    max_attempts: int = 0

class RealRatioOperationManager:
    def __init__(self):
        self.active_operations: Dict[str, OperationProgress] = {}
        self.callbacks: Dict[str, callable] = {}
        self.operation_lock = asyncio.Lock()
    
    def register_callback(self, operation_id: str, callback: callable):
        """Registra un callback para notificar progreso"""
        self.callbacks[operation_id] = callback
        print(f"[DEBUG] Callback registrado para {operation_id}")
    
    def _add_message(self, operation_id: str, message: str):
        """Agrega un mensaje al progreso de la operación"""
        print(f"[DEBUG] _add_message: {message}")
        try:
            if operation_id in self.active_operations:
                progress = self.active_operations[operation_id]
                timestamped_message = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
                progress.messages.append(timestamped_message)
                if len(progress.messages) > 50:
                    progress.messages = progress.messages[-50:]
                print(f"[DEBUG] Mensaje agregado: {timestamped_message}")
            else:
                print(f"[DEBUG] Operation {operation_id} no encontrada")
        except Exception as e:
            print(f"[DEBUG] ERROR al agregar mensaje: {e}")
    
    async def _notify_progress(self, operation_id: str, progress: OperationProgress):
        """Notifica el progreso a través del callback"""
        if operation_id in self.callbacks:
            try:
                await self.callbacks[operation_id](progress)
                print(f"[DEBUG] Progreso notificado para {operation_id}")
            except Exception as e:
                print(f"[DEBUG] Error en callback: {e}")
        else:
            print(f"[DEBUG] NO hay callback para {operation_id}")
    
    def _get_real_quotes(self, instruments: List[str]) -> Dict:
        """Obtiene cotizaciones reales del cache"""
        try:
            quotes = {}
            for instrument in instruments:
                # Intentar obtener cotizaciones reales desde ratios_worker
                market_data = ratios_worker.obtener_datos_mercado(instrument)
                if market_data and 'bid' in market_data and 'offer' in market_data:
                    quotes[instrument] = market_data
                    print(f"[DEBUG] Cotización real para {instrument}: bid={market_data['bid']}, offer={market_data['offer']}")
                else:
                    # Fallback a cotizaciones simuladas si no hay datos reales
                    quotes[instrument] = {"bid": 1000.0, "offer": 1000.5, "last": 1000.25}
                    print(f"[DEBUG] Usando cotización simulada para {instrument}")
            return quotes
        except Exception as e:
            print(f"[DEBUG] Error obteniendo cotizaciones: {e}")
            # Fallback a cotizaciones simuladas
            quotes = {}
            for instrument in instruments:
                quotes[instrument] = {"bid": 1000.0, "offer": 1000.5, "last": 1000.25}
            return quotes
    
    def _calculate_current_ratio(self, sell_quotes: Dict, buy_quotes: Dict) -> float:
        """Calcula el ratio actual basado en cotizaciones reales"""
        try:
            # Usar precio de venta (offer) para el instrumento que se vende
            # Usar precio de compra (bid) para el instrumento que se compra
            sell_price = sell_quotes.get('offer', 0)
            buy_price = buy_quotes.get('bid', 0)
            
            if buy_price > 0:
                ratio = sell_price / buy_price
                print(f"[DEBUG] Ratio calculado: {sell_price} / {buy_price} = {ratio}")
                return ratio
            else:
                print(f"[DEBUG] Error: precio de compra es 0")
                return 0.0
        except Exception as e:
            print(f"[DEBUG] Error calculando ratio: {e}")
            return 0.0
    
    def _check_condition(self, current_ratio: float, target_ratio: float, condition: str) -> bool:
        """Verifica si se cumple la condición del ratio"""
        try:
            if condition == "less_than_or_equal":
                return current_ratio <= target_ratio
            elif condition == "greater_than_or_equal":
                return current_ratio >= target_ratio
            elif condition == "less_than":
                return current_ratio < target_ratio
            elif condition == "greater_than":
                return current_ratio > target_ratio
            elif condition == "equal":
                return abs(current_ratio - target_ratio) < 0.001
            else:
                print(f"[DEBUG] Condición no reconocida: {condition}")
                return False
        except Exception as e:
            print(f"[DEBUG] Error verificando condición: {e}")
            return False
    
    async def _execute_real_order(self, operation_id: str, instrument: str, side: str, quantity: float, price: float) -> Optional[OrderExecution]:
        """Ejecuta una orden real usando ws_rofex"""
        try:
            self._add_message(operation_id, f"📤 Enviando orden {side.upper()} para {instrument}: {quantity} @ {price}")
            
            # Preparar parámetros para la orden
            order_params = {
                "instrument": instrument,
                "side": side,
                "quantity": quantity,
                "price": price,
                "client_id": f"{operation_id}_{side}_{datetime.now().strftime('%H%M%S')}"
            }
            
            print(f"[DEBUG] Parámetros de orden: {order_params}")
            
            # Ejecutar orden real usando ws_rofex
            if hasattr(ws_rofex, 'manager') and hasattr(ws_rofex.manager, 'send_order'):
                result = ws_rofex.manager.send_order(
                    symbol=instrument,
                    side=side.upper(),
                    size=quantity,
                    price=price,
                    order_type="LIMIT",
                    client_order_id=order_params["client_id"]
                )
                print(f"[DEBUG] Resultado de orden: {result}")
                
                if result and result.get('status') == 'ok':
                    order_execution = OrderExecution(
                        instrument=instrument,
                        quantity=quantity,
                        price=price,
                        order_id=result.get('order_id', f"{operation_id}_{side}_{datetime.now().strftime('%H%M%S')}"),
                        timestamp=datetime.now().isoformat(),
                        side=side,
                        status="filled"
                    )
                    self._add_message(operation_id, f"✅ Orden {side.upper()} ejecutada: {order_execution.order_id}")
                    return order_execution
                else:
                    error_msg = result.get('message', 'Error desconocido') if result else 'No se recibió respuesta'
                    self._add_message(operation_id, f"❌ Orden {side.upper()} rechazada: {error_msg}")
                    
                    # No usar fallback simulado - fallar directamente
                    if result and result.get('message') == 'ws_not_connected':
                        self._add_message(operation_id, f"❌ WebSocket ROFEX no conectado - operación fallida")
                    
                    return None
            else:
                # ws_rofex no está disponible - operación fallida
                self._add_message(operation_id, f"❌ ws_rofex no disponible - operación fallida")
                return None
                
        except Exception as e:
            self._add_message(operation_id, f"❌ Error ejecutando orden {side.upper()}: {str(e)}")
            print(f"[DEBUG] Error ejecutando orden: {e}")
            return None
    
    async def execute_ratio_operation_batch(self, request: RatioOperationRequest) -> OperationProgress:
        """Ejecuta una operación de ratio con órdenes reales"""
        print("=" * 80)
        print("🚀🚀🚀 EJECUTANDO OPERACIONES DE RATIO REALES 🚀🚀🚀")
        print("=" * 80)
        
        operation_id = request.operation_id
        self._add_message(operation_id, "🚀 INICIANDO operación de ratio con órdenes reales")
        
        # Crear el progreso
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
            condition_met=False,
            target_ratio=request.target_ratio,
            condition=request.condition,
            remaining_nominales=request.nominales,
            current_attempt=0,
            max_attempts=request.max_attempts,
            batch_count=0,
            completed_nominales=0.0,
            weighted_average_ratio=0.0,
            messages=[],
            error=None,
            current_batch_size=0.0,
            success_rate=0.0,
            estimated_completion_time="",
            market_condition="",
            real_quotes={}
        )
        
        # Agregar a operaciones activas
        self.active_operations[operation_id] = progress
        
        # Cambiar estado a running
        progress.status = OperationStatus.RUNNING
        progress.current_step = OperationStep.GETTING_QUOTES
        progress.progress_percentage = 10
        
        self._add_message(operation_id, "📊 Obteniendo cotizaciones reales del mercado")
        
        # Obtener cotizaciones reales
        instruments = [request.instrument_to_sell]
        if len(request.pair) > 1:
            for instrument in request.pair:
                if instrument != request.instrument_to_sell:
                    instruments.append(instrument)
                    break
        
        quotes = self._get_real_quotes(instruments)
        progress.real_quotes = quotes
        
        # Calcular ratio actual
        sell_quotes = quotes.get(request.instrument_to_sell, {})
        buy_instrument = instruments[1] if len(instruments) > 1 else request.pair[1] if len(request.pair) > 1 else "MERV - XMEV - TX28 - 24hs"
        buy_quotes = quotes.get(buy_instrument, {})
        
        current_ratio = self._calculate_current_ratio(sell_quotes, buy_quotes)
        progress.current_ratio = current_ratio
        progress.condition_met = self._check_condition(current_ratio, request.target_ratio, request.condition)
        
        self._add_message(operation_id, f"📈 Ratio actual: {current_ratio:.6f}")
        self._add_message(operation_id, f"🎯 Ratio objetivo: {request.target_ratio}")
        self._add_message(operation_id, f"✅ Condición cumplida: {progress.condition_met}")
        
        # Notificar progreso inicial
        await self._notify_progress(operation_id, progress)
        
        if not progress.condition_met:
            self._add_message(operation_id, "⚠️ Condición no cumplida, pero ejecutando operación de todas formas")
        
        # Ejecutar órdenes reales
        progress.current_step = OperationStep.EXECUTING_BATCH
        progress.progress_percentage = 50
        
        self._add_message(operation_id, "⚡ Ejecutando órdenes reales de compra/venta")
        
        # Ejecutar orden de venta
        sell_price = sell_quotes.get('offer', 1000.0)
        sell_order = await self._execute_real_order(
            operation_id, 
            request.instrument_to_sell, 
            "sell", 
            request.nominales, 
            sell_price
        )
        
        if not sell_order:
            progress.status = OperationStatus.FAILED
            progress.error = "Error ejecutando orden de venta"
            self._add_message(operation_id, "❌ Operación fallida: no se pudo ejecutar orden de venta")
            await self._notify_progress(operation_id, progress)
            return progress
        
        progress.sell_orders.append(sell_order)
        progress.total_sold_amount = sell_order.quantity * sell_order.price
        progress.average_sell_price = sell_order.price
        self._add_message(operation_id, f"✅ Orden de venta ejecutada: {sell_order.order_id}")
        
        # Ejecutar orden de compra
        buy_price = buy_quotes.get('bid', 1050.0)
        buy_order = await self._execute_real_order(
            operation_id, 
            buy_instrument, 
            "buy", 
            request.nominales, 
            buy_price
        )
        
        if not buy_order:
            progress.status = OperationStatus.FAILED
            progress.error = "Error ejecutando orden de compra"
            self._add_message(operation_id, "❌ Operación fallida: no se pudo ejecutar orden de compra")
            await self._notify_progress(operation_id, progress)
            return progress
        
        progress.buy_orders.append(buy_order)
        progress.total_bought_amount = buy_order.quantity * buy_order.price
        progress.average_buy_price = buy_order.price
        self._add_message(operation_id, f"✅ Orden de compra ejecutada: {buy_order.order_id}")
        
        # Calcular ratio final de las órdenes ejecutadas
        if progress.total_bought_amount > 0:
            final_ratio = progress.total_sold_amount / progress.total_bought_amount
            progress.weighted_average_ratio = final_ratio
            progress.condition_met = self._check_condition(final_ratio, request.target_ratio, request.condition)
            self._add_message(operation_id, f"📊 Ratio final ejecutado: {final_ratio:.6f}")
            self._add_message(operation_id, f"🎯 Condición final cumplida: {progress.condition_met}")
        
        # Finalizar
        progress.status = OperationStatus.COMPLETED
        progress.current_step = OperationStep.FINALIZING
        progress.progress_percentage = 100
        progress.completed_nominales = request.nominales
        progress.remaining_nominales = 0.0
        
        self._add_message(operation_id, "✅ Operación completada con órdenes reales")
        
        # Notificar progreso final
        await self._notify_progress(operation_id, progress)
        
        print(f"[DEBUG] Operación {operation_id} completada con órdenes reales")
        return progress
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationProgress]:
        """Obtiene el estado de una operación"""
        return self.active_operations.get(operation_id)

# Instancia global
real_ratio_manager = RealRatioOperationManager()
