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
    PARTIALLY_COMPLETED = "partially_completed"

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
    buy_qty: float = 0.0  # Cantidad específica a comprar (0 = calcular automáticamente)

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
                    # Sin datos reales - operación fallida
                    print(f"[DEBUG] Sin cotizaciones reales para {instrument} - operación fallida")
                    return {}
            return quotes
        except Exception as e:
            print(f"[DEBUG] Error obteniendo cotizaciones: {e}")
            # Sin cotizaciones - operación fallida
            return {}
    
    def _calculate_current_ratio(self, sell_quotes: Dict, buy_quotes: Dict, instrument_to_sell: str) -> float:
        """Calcula el ratio actual basado en cotizaciones reales y el instrumento a vender"""
        try:
            # DETERMINAR ESTRATEGIA BASADA EN EL INSTRUMENTO A VENDER
            if "TX26" in instrument_to_sell:
                # ESTRATEGIA NORMAL - VENDER TX26:
                # - VENDER TX26 al precio de COMPRA (bid TX26)
                # - COMPRAR TX28 al precio de VENTA (offer TX28)
                # - Ratio de venta = bid TX26 / offer TX28
                sell_price = sell_quotes.get('bid', 0)    # Precio de compra (al que vendemos TX26)
                buy_price = buy_quotes.get('offer', 0)    # Precio de venta (al que compramos TX28)
                
                if buy_price > 0:
                    ratio = sell_price / buy_price
                    print(f"[DEBUG] Ratio TX26/TX28 (Vender TX26): {sell_price} / {buy_price} = {ratio}")
                    return ratio
                else:
                    print(f"[DEBUG] Error: precio offer TX28 es 0")
                    return 0.0
                    
            elif "TX28" in instrument_to_sell:
                # ESTRATEGIA INVERSA - VENDER TX28:
                # - VENDER TX28 al precio de COMPRA (bid TX28)
                # - COMPRAR TX26 al precio de VENTA (offer TX26)
                # - Ratio de venta = bid TX28 / offer TX26
                sell_price = buy_quotes.get('bid', 0)     # Precio de compra (al que vendemos TX28)
                buy_price = sell_quotes.get('offer', 0)   # Precio de venta (al que compramos TX26)
                
                if buy_price > 0:
                    ratio = sell_price / buy_price
                    print(f"[DEBUG] Ratio TX28/TX26 (Vender TX28): {sell_price} / {buy_price} = {ratio}")
                    return ratio
                else:
                    print(f"[DEBUG] Error: precio offer TX26 es 0")
                    return 0.0
            else:
                print(f"[DEBUG] Error: instrumento a vender no reconocido: {instrument_to_sell}")
                return 0.0
                
        except Exception as e:
            print(f"[DEBUG] Error calculando ratio: {e}")
            return 0.0
    
    def _check_condition(self, current_ratio: float, target_ratio: float, condition: str) -> bool:
        """Verifica si se cumple la condición del ratio"""
        try:
            if condition == "less_than_or_equal" or condition == "<=":
                return current_ratio <= target_ratio
            elif condition == "greater_than_or_equal" or condition == ">=":
                return current_ratio >= target_ratio
            elif condition == "less_than" or condition == "<":
                return current_ratio < target_ratio
            elif condition == "greater_than" or condition == ">":
                return current_ratio > target_ratio
            elif condition == "equal" or condition == "==":
                return abs(current_ratio - target_ratio) < 0.001
            else:
                print(f"[DEBUG] Condición no reconocida: {condition}")
                return False
        except Exception as e:
            print(f"[DEBUG] Error verificando condición: {e}")
            return False
    
    def _should_execute_now(self, current_ratio: float, target_ratio: float, condition: str, 
                           weighted_ratio: float, executed_lots: int, lot_size: float, 
                           remaining_nominales: float) -> tuple[bool, str]:
        """Determina si es el momento óptimo de ejecutar basado en la condición y optimización mejorada"""
        try:
            # Si no hay lotes ejecutados, verificar condición simple
            if executed_lots == 0:
                condition_met = self._check_condition(current_ratio, target_ratio, condition)
                if condition_met:
                    return True, "Condición inicial cumplida"
                else:
                    return False, f"Condición inicial no cumple: {current_ratio:.6f} vs {target_ratio:.6f}"
            
            # Si ya hay lotes ejecutados, usar lógica mejorada
            # Calcular el nuevo promedio ponderado si ejecutáramos este lote
            # Fórmula: nuevo_promedio = (promedio_actual * nominales_actuales + ratio_actual * lot_size) / (nominales_actuales + lot_size)
            total_executed = 100.0 - remaining_nominales  # Nominales ya ejecutados
            if total_executed > 0:
                new_weighted_ratio = (weighted_ratio * total_executed + current_ratio * lot_size) / (total_executed + lot_size)
            else:
                new_weighted_ratio = current_ratio
            
            # Verificar que el nuevo promedio ponderado cumpla la condición
            new_weighted_condition_met = self._check_condition(new_weighted_ratio, target_ratio, condition)
            
            if not new_weighted_condition_met:
                return False, f"Nuevo promedio ponderado no cumple: {new_weighted_ratio:.6f} vs {target_ratio:.6f}"
            
            # ESTRATEGIA DE OPTIMIZACIÓN MEJORADA:
            if condition in ["less_than_or_equal", "less_than", "<="]:
                # Para condición <=, buscar el MENOR ratio posible
                if current_ratio <= target_ratio:
                    # Ejecutar si:
                    # 1. Mejora el promedio ponderado, O
                    # 2. El promedio ponderado ya es muy bueno (margen de seguridad), O
                    # 3. Es el último lote significativo
                    margin_threshold = target_ratio * 0.95  # 5% de margen de seguridad
                    is_improvement = current_ratio < weighted_ratio
                    is_safe_margin = weighted_ratio < margin_threshold
                    is_significant_lot = lot_size >= remaining_nominales * 0.3  # Lote > 30% de lo restante
                    
                    if is_improvement:
                        return True, f"Ratio mejora promedio: {current_ratio:.6f} < {weighted_ratio:.6f}"
                    elif is_safe_margin:
                        return True, f"Promedio seguro: {weighted_ratio:.6f} < {margin_threshold:.6f}"
                    elif is_significant_lot:
                        return True, f"Lote significativo: {lot_size} nominales ({lot_size/remaining_nominales*100:.1f}% restante)"
                    else:
                        return False, f"Esperando mejor ratio: {current_ratio:.6f} >= {weighted_ratio:.6f}"
                else:
                    return False, f"Ratio muy alto: {current_ratio:.6f} > {target_ratio:.6f}"
            
            elif condition in ["greater_than_or_equal", "greater_than", ">="]:
                # Para condición >=, buscar el MAYOR ratio posible
                if current_ratio >= target_ratio:
                    # Ejecutar si:
                    # 1. Mejora el promedio ponderado, O
                    # 2. El promedio ponderado ya es muy bueno (margen de seguridad), O
                    # 3. Es el último lote significativo
                    margin_threshold = target_ratio * 1.05  # 5% de margen de seguridad
                    is_improvement = current_ratio > weighted_ratio
                    is_safe_margin = weighted_ratio > margin_threshold
                    is_significant_lot = lot_size >= remaining_nominales * 0.3  # Lote > 30% de lo restante
                    
                    if is_improvement:
                        return True, f"Ratio mejora promedio: {current_ratio:.6f} > {weighted_ratio:.6f}"
                    elif is_safe_margin:
                        return True, f"Promedio seguro: {weighted_ratio:.6f} > {margin_threshold:.6f}"
                    elif is_significant_lot:
                        return True, f"Lote significativo: {lot_size} nominales ({lot_size/remaining_nominales*100:.1f}% restante)"
                    else:
                        return False, f"Esperando mejor ratio: {current_ratio:.6f} <= {weighted_ratio:.6f}"
                else:
                    return False, f"Ratio muy bajo: {current_ratio:.6f} < {target_ratio:.6f}"
            
            else:
                return False, f"Condición no soportada: {condition}"
                
        except Exception as e:
            print(f"[DEBUG] Error en optimización: {e}")
            return False, f"Error en optimización: {e}"
    
    def _calculate_lot_size(self, sell_quotes: Dict, buy_quotes: Dict, remaining_nominales: float) -> float:
        """Calcula el tamaño de lote basado en la liquidez disponible"""
        try:
            # Obtener liquidez disponible
            sell_liquidity = sell_quotes.get('bid_size', 0)    # Liquidez en bid TX26 (cantidad disponible para vender)
            buy_liquidity = buy_quotes.get('offer_size', 0)    # Liquidez en offer TX28 (cantidad disponible para comprar)
            
            print(f"[DEBUG] Liquidez disponible:")
            print(f"   Bid TX26 (vender): {sell_liquidity} nominales")
            print(f"   Offer TX28 (comprar): {buy_liquidity} nominales")
            
            if sell_liquidity <= 0 or buy_liquidity <= 0:
                print(f"[DEBUG] Sin liquidez suficiente - sell: {sell_liquidity}, buy: {buy_liquidity}")
                return 0.0
            
            # Calcular lote basado en la menor liquidez disponible
            available_liquidity = min(sell_liquidity, buy_liquidity)
            lot_size = min(available_liquidity, remaining_nominales)
            
            print(f"[DEBUG] Lote calculado: min({available_liquidity}, {remaining_nominales}) = {lot_size}")
            return lot_size
            
        except Exception as e:
            print(f"[DEBUG] Error calculando tamaño de lote: {e}")
            return 0.0
    
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
        
        current_ratio = self._calculate_current_ratio(sell_quotes, buy_quotes, request.instrument_to_sell)
        progress.current_ratio = current_ratio
        progress.condition_met = self._check_condition(current_ratio, request.target_ratio, request.condition)
        
        self._add_message(operation_id, f"📈 Ratio actual: {current_ratio:.6f}")
        self._add_message(operation_id, f"🎯 Ratio objetivo: {request.target_ratio}")
        self._add_message(operation_id, f"✅ Condición cumplida: {progress.condition_met}")
        
        # Notificar progreso inicial
        await self._notify_progress(operation_id, progress)
        
        if not progress.condition_met:
            self._add_message(operation_id, "⚠️ Condición no cumplida, pero ejecutando operación de todas formas")
        
        # Ejecutar operación por lotes adaptativos basados en liquidez
        progress.current_step = OperationStep.EXECUTING_BATCH
        progress.progress_percentage = 50
        
        self._add_message(operation_id, "⚡ INICIANDO operación por lotes adaptativos")
        self._add_message(operation_id, f"🎯 Objetivo total: {request.nominales} nominales")
        
        # Bucle principal de lotes
        lot_number = 0
        wait_attempts = 0
        max_wait_attempts = 10  # Máximo 10 intentos de espera por lote
        
        while progress.remaining_nominales > 0:
            lot_number += 1
            progress.batch_count = lot_number
            
            self._add_message(operation_id, f"🔄 LOTE #{lot_number} - Nominales restantes: {progress.remaining_nominales}")
            self._add_message(operation_id, f"⏰ Intentos de espera: {wait_attempts}/{max_wait_attempts}")
            
            # Obtener cotizaciones actualizadas para este lote
            quotes = self._get_real_quotes(instruments)
            progress.real_quotes = quotes
            sell_quotes = quotes.get(request.instrument_to_sell, {})
            buy_quotes = quotes.get(buy_instrument, {})
            
            # Calcular tamaño de lote basado en liquidez disponible
            lot_size = self._calculate_lot_size(sell_quotes, buy_quotes, progress.remaining_nominales)
            
            if lot_size <= 0:
                self._add_message(operation_id, "⚠️ Sin liquidez suficiente para continuar")
                progress.status = OperationStatus.PARTIALLY_COMPLETED
                break
            
            progress.current_batch_size = lot_size
            self._add_message(operation_id, f"📊 Lote #{lot_number}: {lot_size} nominales (liquidez adaptativa)")
            
            # Calcular ratio actual para este lote
            current_ratio = self._calculate_current_ratio(sell_quotes, buy_quotes, request.instrument_to_sell)
            progress.current_ratio = current_ratio
            
            # Obtener ratio ponderado actual de todos los lotes ejecutados
            current_weighted_ratio = progress.weighted_average_ratio if progress.weighted_average_ratio > 0 else current_ratio
            
            # EVALUAR OPTIMIZACIÓN - ¿Es el momento óptimo de ejecutar?
            should_execute, execution_reason = self._should_execute_now(
                current_ratio, 
                request.target_ratio, 
                request.condition,
                current_weighted_ratio,
                progress.batch_count - 1,  # lotes ya ejecutados
                lot_size,  # tamaño del lote actual
                progress.remaining_nominales  # nominales restantes
            )
            
            self._add_message(operation_id, f"📈 Ratio actual: {current_ratio:.6f}")
            self._add_message(operation_id, f"📊 Ratio ponderado: {current_weighted_ratio:.6f}")
            self._add_message(operation_id, f"🎯 Decisión: {'✅ EJECUTAR' if should_execute else '⏳ ESPERAR'}")
            self._add_message(operation_id, f"💭 Razón: {execution_reason}")
            
            if not should_execute:
                # Esperar por mejores precios
                wait_attempts += 1
                self._add_message(operation_id, f"⏳ ESPERANDO por mejores precios... (intento {wait_attempts}/{max_wait_attempts})")
                
                if wait_attempts >= max_wait_attempts:
                    # Forzar ejecución después de muchos intentos
                    self._add_message(operation_id, f"⚠️ TIMEOUT: Ejecutando lote después de {max_wait_attempts} intentos de espera")
                    self._add_message(operation_id, f"🎯 Ejecutando con ratio actual: {current_ratio:.6f}")
                    wait_attempts = 0  # Reset para el siguiente lote
                else:
                    self._add_message(operation_id, f"🔄 Reintentando en 5 segundos...")
                    await asyncio.sleep(5)
                    continue
            
            # EJECUTAR LOTE - Condición óptima cumplida
            # PASO 1: Vender instrumento al precio de compra (bid)
            if "TX26" in request.instrument_to_sell:
                # ESTRATEGIA NORMAL - Vender TX26
                sell_price = sell_quotes.get('bid', 0)  # Precio bid TX26
                self._add_message(operation_id, f"📤 LOTE #{lot_number} - PASO 1: Vendiendo TX26 @ {sell_price} (bid)")
            elif "TX28" in request.instrument_to_sell:
                # ESTRATEGIA INVERSA - Vender TX28
                sell_price = buy_quotes.get('bid', 0)   # Precio bid TX28
                self._add_message(operation_id, f"📤 LOTE #{lot_number} - PASO 1: Vendiendo TX28 @ {sell_price} (bid)")
            else:
                self._add_message(operation_id, f"❌ Error: instrumento no reconocido: {request.instrument_to_sell}")
                progress.status = OperationStatus.FAILED
                break
            
            sell_order = await self._execute_real_order(
                operation_id, 
                request.instrument_to_sell, 
                "sell", 
                lot_size, 
                sell_price
            )
            
            if not sell_order:
                self._add_message(operation_id, f"❌ LOTE #{lot_number} - Error en venta")
                progress.status = OperationStatus.FAILED
                progress.error = f"Error ejecutando venta en lote {lot_number}"
                break
            
            # Actualizar progreso de venta
            progress.sell_orders.append(sell_order)
            progress.total_sold_amount += sell_order.quantity * sell_order.price
            progress.average_sell_price = (
                progress.total_sold_amount / sum(order.quantity for order in progress.sell_orders)
                if progress.sell_orders else 0.0
            )
            
            self._add_message(operation_id, f"✅ LOTE #{lot_number} - PASO 1 COMPLETADO: Venta {sell_order.order_id}")
            
            # Esperar un poco para procesar la venta
            await asyncio.sleep(1)
            
            # PASO 2: Comprar instrumento complementario al precio de venta (offer)
            # Usar buy_qty si está especificado y es válido, sino usar cantidad vendida
            if request.buy_qty > 0 and request.buy_qty <= sell_order.quantity:
                buy_quantity = request.buy_qty
                self._add_message(operation_id, f"🎯 LOTE #{lot_number} - Usando buy_qty específico: {buy_quantity}")
            else:
                buy_quantity = sell_order.quantity  # Usar cantidad efectivamente vendida
            
            if "TX26" in request.instrument_to_sell:
                # ESTRATEGIA NORMAL - Comprar TX28
                buy_instrument = "MERV - XMEV - TX28 - 24hs"
                buy_price = buy_quotes.get('offer', 0)  # Precio offer TX28
                self._add_message(operation_id, f"📥 LOTE #{lot_number} - PASO 2: Comprando TX28 @ {buy_price} (offer)")
            elif "TX28" in request.instrument_to_sell:
                # ESTRATEGIA INVERSA - Comprar TX26
                buy_instrument = "MERV - XMEV - TX26 - 24hs"
                buy_price = sell_quotes.get('offer', 0)  # Precio offer TX26
                self._add_message(operation_id, f"📥 LOTE #{lot_number} - PASO 2: Comprando TX26 @ {buy_price} (offer)")
            else:
                self._add_message(operation_id, f"❌ Error: no se puede determinar instrumento a comprar")
                progress.status = OperationStatus.FAILED
                break
            
            buy_order = await self._execute_real_order(
                operation_id, 
                buy_instrument, 
                "buy", 
                buy_quantity, 
                buy_price
            )
            
            if not buy_order:
                self._add_message(operation_id, f"❌ LOTE #{lot_number} - Error en compra")
                progress.status = OperationStatus.FAILED
                progress.error = f"Error ejecutando compra en lote {lot_number}"
                break
            
            # Actualizar progreso de compra
            progress.buy_orders.append(buy_order)
            progress.total_bought_amount += buy_order.quantity * buy_order.price
            progress.average_buy_price = (
                progress.total_bought_amount / sum(order.quantity for order in progress.buy_orders)
                if progress.buy_orders else 0.0
            )
            
            self._add_message(operation_id, f"✅ LOTE #{lot_number} - PASO 2 COMPLETADO: Compra {buy_order.order_id}")
            
            # Actualizar nominales completados y restantes
            progress.completed_nominales += buy_quantity
            progress.remaining_nominales = request.nominales - progress.completed_nominales
            
            # Calcular ratio ponderado de todos los lotes ejecutados
            if progress.total_bought_amount > 0:
                weighted_ratio = progress.total_sold_amount / progress.total_bought_amount
                progress.weighted_average_ratio = weighted_ratio
                
                self._add_message(operation_id, f"📊 LOTE #{lot_number} COMPLETADO:")
                self._add_message(operation_id, f"   💰 Nominales ejecutados: {progress.completed_nominales}/{request.nominales}")
                self._add_message(operation_id, f"   📈 Ratio ponderado: {weighted_ratio:.6f}")
                self._add_message(operation_id, f"   💵 Precio promedio venta: {progress.average_sell_price:.2f}")
                self._add_message(operation_id, f"   💵 Precio promedio compra: {progress.average_buy_price:.2f}")
            
            # Resetear contador de espera para el siguiente lote
            wait_attempts = 0
            
            # Notificar progreso del lote
            progress.progress_percentage = min(90, 50 + (progress.completed_nominales / request.nominales) * 40)
            await self._notify_progress(operation_id, progress)
            
            # Si completamos todos los nominales, terminar
            if progress.remaining_nominales <= 0:
                self._add_message(operation_id, "🎉 ¡TODOS LOS NOMINALES COMPLETADOS!")
                break
            
            # Esperar antes del siguiente lote para obtener nuevas cotizaciones
            self._add_message(operation_id, f"⏳ Esperando 3 segundos antes del siguiente lote...")
            await asyncio.sleep(3)
        
        # Finalizar operación
        if progress.remaining_nominales <= 0:
            progress.status = OperationStatus.COMPLETED
            self._add_message(operation_id, "✅ OPERACIÓN COMPLETADA EXITOSAMENTE")
        else:
            progress.status = OperationStatus.PARTIALLY_COMPLETED
            self._add_message(operation_id, f"⚠️ OPERACIÓN PARCIALMENTE COMPLETADA: {progress.completed_nominales}/{request.nominales}")
        
        progress.current_step = OperationStep.FINALIZING
        progress.progress_percentage = 100
        
        # Ratio final de toda la operación
        if progress.total_bought_amount > 0:
            final_ratio = progress.total_sold_amount / progress.total_bought_amount
            progress.weighted_average_ratio = final_ratio
            progress.condition_met = self._check_condition(final_ratio, request.target_ratio, request.condition)
            
            self._add_message(operation_id, f"📊 RESUMEN FINAL:")
            self._add_message(operation_id, f"   🎯 Nominales objetivo: {request.nominales}")
            self._add_message(operation_id, f"   ✅ Nominales ejecutados: {progress.completed_nominales}")
            self._add_message(operation_id, f"   📈 Ratio final ponderado: {final_ratio:.6f}")
            self._add_message(operation_id, f"   🎯 Condición cumplida: {progress.condition_met}")
            self._add_message(operation_id, f"   📦 Lotes ejecutados: {progress.batch_count}")
        
        # Notificar progreso final
        await self._notify_progress(operation_id, progress)
        
        print(f"[DEBUG] Operación {operation_id} completada: {progress.completed_nominales}/{request.nominales} nominales")
        return progress
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationProgress]:
        """Obtiene el estado de una operación"""
        return self.active_operations.get(operation_id)

# Instancia global
real_ratio_manager = RealRatioOperationManager()
