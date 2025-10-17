#!/usr/bin/env python3
"""
Versión mejorada del sistema de operaciones de ratio que ejecuta órdenes reales
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
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
    original_request: Optional[RatioOperationRequest] = None

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
        self.pending_orders_monitor: Dict[str, List[OrderExecution]] = {}  # operation_id -> pending orders
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}  # operation_id -> monitoring task
    
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
    
    def _calculate_lot_size(self, sell_quotes: Dict, buy_quotes: Dict, remaining_nominales: float, operation_id: str = "") -> float:
        """Calcula el tamaño de lote basado en la liquidez disponible con factor de seguridad"""
        try:
            # Obtener liquidez disponible
            sell_liquidity = sell_quotes.get('bid_size', 0)    # Liquidez en bid TX26 (cantidad disponible para vender)
            buy_liquidity = buy_quotes.get('offer_size', 0)    # Liquidez en offer TX28 (cantidad disponible para comprar)
            
            self._add_message(operation_id, f"📊 Liquidez disponible:")
            self._add_message(operation_id, f"   📈 TX26 (vender): {sell_liquidity} nominales")
            self._add_message(operation_id, f"   📉 TX28 (comprar): {buy_liquidity} nominales")
            
            if sell_liquidity <= 0 or buy_liquidity <= 0:
                self._add_message(operation_id, f"⚠️ Sin liquidez suficiente - TX26: {sell_liquidity}, TX28: {buy_liquidity}")
                return 0.0
            
            # Calcular lote basado en la menor liquidez disponible
            available_liquidity = min(sell_liquidity, buy_liquidity)
            
            # Aplicar factor de seguridad (80% de la liquidez disponible)
            safety_factor = 0.8
            safe_lot_size = available_liquidity * safety_factor
            
            # Verificar si la liquidez es muy baja comparada con lo restante
            if available_liquidity < remaining_nominales * 0.1:  # Menos del 10% de lo restante
                self._add_message(operation_id, f"⚠️ Liquidez muy baja: {available_liquidity} vs {remaining_nominales} restantes")
            
            # Lote final = min(liquidez_segura, nominales_restantes)
            lot_size = min(safe_lot_size, remaining_nominales)
            
            self._add_message(operation_id, f"📊 Lote calculado:")
            self._add_message(operation_id, f"   🎯 Liquidez disponible: {available_liquidity}")
            self._add_message(operation_id, f"   🛡️ Factor de seguridad: {safety_factor*100}%")
            self._add_message(operation_id, f"   📦 Lote seguro: {safe_lot_size:.0f}")
            self._add_message(operation_id, f"   ✅ Lote final: {lot_size:.0f}")
            
            return lot_size
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error calculando tamaño de lote: {e}")
            return 0.0
    
    def _get_current_liquidity(self, instrument: str, side: str) -> float:
        """Obtiene la liquidez actual de un instrumento en tiempo real"""
        try:
            # Obtener cotizaciones actuales
            market_data = ratios_worker.obtener_datos_mercado(instrument)
            if not market_data:
                return 0.0
            
            if side.lower() == "sell":
                # Para venta, necesitamos liquidez en bid (donde vendemos)
                return float(market_data.get('bid_size', 0))
            else:
                # Para compra, necesitamos liquidez en offer (donde compramos)
                return float(market_data.get('offer_size', 0))
                
        except Exception as e:
            print(f"[DEBUG] Error obteniendo liquidez actual: {e}")
            return 0.0
    
    async def _execute_real_order_with_liquidity_check(self, operation_id: str, instrument: str, side: str, quantity: float, price: float) -> Optional[OrderExecution]:
        """Ejecuta orden con verificación de liquidez en tiempo real"""
        try:
            # Verificar liquidez actual ANTES de enviar la orden
            current_liquidity = self._get_current_liquidity(instrument, side)
            
            self._add_message(operation_id, f"🔍 Verificando liquidez actual para {side.upper()} {instrument}:")
            self._add_message(operation_id, f"   📊 Liquidez disponible: {current_liquidity}")
            self._add_message(operation_id, f"   📦 Cantidad solicitada: {quantity}")
            
            if current_liquidity < quantity:
                # Ajustar cantidad a la liquidez disponible
                adjusted_quantity = current_liquidity
                self._add_message(operation_id, f"⚠️ Liquidez insuficiente: {quantity} → {adjusted_quantity}")
                
                if adjusted_quantity <= 0:
                    self._add_message(operation_id, f"❌ Sin liquidez disponible para {side.upper()} {instrument}")
                    return None
                
                # Ejecutar orden con cantidad ajustada
                return await self._execute_real_order(operation_id, instrument, side, adjusted_quantity, price)
            else:
                # Liquidez suficiente, ejecutar orden normal
                return await self._execute_real_order(operation_id, instrument, side, quantity, price)
                
        except Exception as e:
            self._add_message(operation_id, f"❌ Error verificando liquidez: {str(e)}")
            return await self._execute_real_order(operation_id, instrument, side, quantity, price)
    
    async def _handle_partial_execution(self, operation_id: str, expected_quantity: float, actual_quantity: float, instrument: str, side: str) -> float:
        """Maneja ejecuciones parciales cuando la liquidez es insuficiente"""
        try:
            if actual_quantity < expected_quantity:
                self._add_message(operation_id, f"⚠️ Ejecución parcial en {side.upper()} {instrument}:")
                self._add_message(operation_id, f"   📦 Solicitado: {expected_quantity}")
                self._add_message(operation_id, f"   ✅ Ejecutado: {actual_quantity}")
                
                # Calcular cantidad faltante
                remaining_quantity = expected_quantity - actual_quantity
                self._add_message(operation_id, f"   ⚠️ Faltante: {remaining_quantity}")
                
                # Verificar si hay más liquidez disponible
                current_liquidity = self._get_current_liquidity(instrument, side)
                if current_liquidity > 0:
                    self._add_message(operation_id, f"   🔍 Liquidez restante: {current_liquidity}")
                    if current_liquidity >= remaining_quantity:
                        self._add_message(operation_id, f"   🔄 Intentando completar con liquidez restante")
                        return remaining_quantity
                    else:
                        self._add_message(operation_id, f"   ⚠️ Liquidez insuficiente para completar")
                        return 0.0
                else:
                    self._add_message(operation_id, f"   ❌ Sin liquidez restante")
                    return 0.0
            
            return 0.0  # No hay ejecución parcial
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error manejando ejecución parcial: {str(e)}")
            return 0.0
    
    async def _execute_real_order(self, operation_id: str, instrument: str, side: str, quantity: float, price: float) -> Optional[OrderExecution]:
        """Ejecuta una orden real usando ws_rofex"""
        try:
            self._add_message(operation_id, f"📤 Enviando orden {side.upper()} para {instrument}: {quantity} @ {price}")
            
            # Preparar parámetros para la orden
            client_order_id = f"{operation_id}_{side}_{datetime.now().strftime('%H%M%S')}"
            order_params = {
                "instrument": instrument,
                "side": side,
                "quantity": quantity,
                "price": price,
                "client_id": client_order_id
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
                    client_order_id=client_order_id
                )
                print(f"[DEBUG] Resultado de orden: {result}")
                
                if result and result.get('status') == 'ok':
                    # La orden fue aceptada por el broker, pero no necesariamente ejecutada
                    order_execution = OrderExecution(
                        instrument=instrument,
                        quantity=quantity,
                        price=price,
                        order_id=result.get('order_id', client_order_id),
                        timestamp=datetime.now().isoformat(),
                        side=side,
                        status="pending"  # Cambiar a "pending" - no asumir que está ejecutada
                    )
                    self._add_message(operation_id, f"✅ Orden {side.upper()} aceptada por broker: {order_execution.order_id}")
                    
                    # Esperar y verificar el estado real de la orden
                    await asyncio.sleep(2)  # Esperar un poco para que llegue el order report
                    real_status = await self._verify_order_status(operation_id, client_order_id, order_execution)
                    
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
    
    async def _verify_order_status(self, operation_id: str, client_order_id: str, order_execution: OrderExecution) -> str:
        """Verifica el estado real de una orden consultando los order reports"""
        try:
            self._add_message(operation_id, f"🔍 Verificando estado real de orden: {client_order_id}")
            
            # Intentar múltiples veces para obtener el order report correcto
            max_attempts = 5
            for attempt in range(max_attempts):
                if hasattr(ws_rofex, 'manager') and hasattr(ws_rofex.manager, 'last_order_report'):
                    last_report = ws_rofex.manager.last_order_report()
                    
                    if last_report:
                        # Buscar el client order ID en diferentes campos posibles
                        report_client_id = (last_report.get("wsClOrdId") or 
                                          last_report.get("clOrdId") or 
                                          last_report.get("clientId") or 
                                          last_report.get("client_order_id"))
                        
                        if report_client_id == client_order_id:
                            order_status = last_report.get('status', 'UNKNOWN')
                            self._add_message(operation_id, f"📊 Estado real de orden {client_order_id}: {order_status}")
                            
                            # Mapear estados del broker a estados internos
                            if order_status in ['FILLED', 'PARTIALLY_FILLED']:
                                order_execution.status = "filled"
                                self._add_message(operation_id, f"✅ Orden {client_order_id} EJECUTADA en el mercado")
                                return order_execution.status
                            elif order_status in ['PENDING_NEW', 'NEW', 'PENDING_CANCEL']:
                                order_execution.status = "pending"
                                self._add_message(operation_id, f"⏳ Orden {client_order_id} PENDIENTE en el mercado")
                                return order_execution.status
                            elif order_status in ['CANCELLED', 'REJECTED']:
                                order_execution.status = "rejected"
                                self._add_message(operation_id, f"❌ Orden {client_order_id} RECHAZADA/CANCELADA")
                                return order_execution.status
                            else:
                                order_execution.status = "unknown"
                                self._add_message(operation_id, f"❓ Orden {client_order_id} estado desconocido: {order_status}")
                                return order_execution.status
                        else:
                            if attempt < max_attempts - 1:
                                self._add_message(operation_id, f"⏳ Esperando order report para {client_order_id}... (intento {attempt + 1}/{max_attempts})")
                                await asyncio.sleep(1)  # Esperar un poco más
                                continue
                            else:
                                self._add_message(operation_id, f"⚠️ Order report no coincide con {client_order_id} (encontrado: {report_client_id})")
                    else:
                        if attempt < max_attempts - 1:
                            self._add_message(operation_id, f"⏳ Esperando order report... (intento {attempt + 1}/{max_attempts})")
                            await asyncio.sleep(1)
                            continue
                        else:
                            self._add_message(operation_id, f"⚠️ No hay order report disponible para verificar {client_order_id}")
                else:
                    self._add_message(operation_id, f"⚠️ No se puede verificar estado de orden - ws_rofex no disponible")
                    break
            
            # Si no se puede verificar después de todos los intentos, usar lógica alternativa
            return await self._fallback_order_status_check(operation_id, client_order_id, order_execution)
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error verificando estado de orden: {str(e)}")
            order_execution.status = "pending"
            return "pending"
    
    async def _fallback_order_status_check(self, operation_id: str, client_order_id: str, order_execution: OrderExecution) -> str:
        """Verificación alternativa cuando no se puede obtener order report del broker"""
        try:
            self._add_message(operation_id, f"🔄 Usando verificación alternativa para {client_order_id}")
            
            # Estrategia 1: Verificar si la orden fue enviada recientemente (menos de 30 segundos)
            if hasattr(order_execution, 'timestamp') and order_execution.timestamp:
                try:
                    from datetime import datetime
                    order_time = datetime.fromisoformat(order_execution.timestamp)
                    current_time = datetime.now()
                    time_diff = (current_time - order_time).total_seconds()
                    
                    if time_diff < 30:  # Orden muy reciente
                        self._add_message(operation_id, f"⏳ Orden {client_order_id} muy reciente ({time_diff:.1f}s) - asumiendo PENDIENTE")
                        order_execution.status = "pending"
                        return "pending"
                    elif time_diff > 300:  # Orden muy antigua (5 minutos)
                        self._add_message(operation_id, f"⚠️ Orden {client_order_id} muy antigua ({time_diff:.1f}s) - asumiendo EJECUTADA")
                        order_execution.status = "filled"
                        return "filled"
                    else:
                        # Orden de edad intermedia - mantener como pending pero con advertencia
                        self._add_message(operation_id, f"⏳ Orden {client_order_id} de edad intermedia ({time_diff:.1f}s) - asumiendo PENDIENTE")
                        order_execution.status = "pending"
                        return "pending"
                        
                except Exception as e:
                    self._add_message(operation_id, f"⚠️ Error calculando edad de orden: {e}")
            
            # Estrategia 2: Verificar conectividad del WebSocket
            if hasattr(ws_rofex, 'manager') and hasattr(ws_rofex.manager, 'is_connected'):
                if ws_rofex.manager.is_connected():
                    self._add_message(operation_id, f"🔗 WebSocket conectado - asumiendo PENDIENTE para {client_order_id}")
                    order_execution.status = "pending"
                    return "pending"
                else:
                    self._add_message(operation_id, f"⚠️ WebSocket desconectado - asumiendo EJECUTADA para {client_order_id}")
                    order_execution.status = "filled"
                    return "filled"
            
            # Estrategia 3: Por defecto, asumir pending
            self._add_message(operation_id, f"⚠️ No se pudo verificar estado de {client_order_id} - asumiendo PENDIENTE")
            order_execution.status = "pending"
            return "pending"
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error en verificación alternativa: {str(e)}")
            order_execution.status = "pending"
            return "pending"
    
    async def _verify_all_orders_status(self, operation_id: str, progress: OperationProgress):
        """Verifica el estado de todas las órdenes de una operación"""
        try:
            self._add_message(operation_id, "🔄 Verificando estado de todas las órdenes...")
            
            # Verificar todas las órdenes de venta
            for sell_order in progress.sell_orders:
                if sell_order.status == "pending":
                    # Extraer client_order_id del order_id
                    client_order_id = sell_order.order_id
                    await self._verify_order_status(operation_id, client_order_id, sell_order)
            
            # Verificar todas las órdenes de compra
            for buy_order in progress.buy_orders:
                if buy_order.status == "pending":
                    # Extraer client_order_id del order_id
                    client_order_id = buy_order.order_id
                    await self._verify_order_status(operation_id, client_order_id, buy_order)
            
            # Contar órdenes por estado
            filled_sell = len([o for o in progress.sell_orders if o.status == "filled"])
            pending_sell = len([o for o in progress.sell_orders if o.status == "pending"])
            filled_buy = len([o for o in progress.buy_orders if o.status == "filled"])
            pending_buy = len([o for o in progress.buy_orders if o.status == "pending"])
            
            self._add_message(operation_id, f"📊 Estado de órdenes:")
            self._add_message(operation_id, f"   ✅ Ventas ejecutadas: {filled_sell}, pendientes: {pending_sell}")
            self._add_message(operation_id, f"   ✅ Compras ejecutadas: {filled_buy}, pendientes: {pending_buy}")
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error verificando estado de órdenes: {str(e)}")
    
    async def _start_pending_orders_monitoring(self, operation_id: str, progress: OperationProgress):
        """Inicia el monitoreo continuo de órdenes pendientes"""
        try:
            # Recopilar todas las órdenes pendientes
            pending_orders = []
            for sell_order in progress.sell_orders:
                if sell_order.status == "pending":
                    pending_orders.append(sell_order)
            for buy_order in progress.buy_orders:
                if buy_order.status == "pending":
                    pending_orders.append(buy_order)
            
            if not pending_orders:
                self._add_message(operation_id, "✅ No hay órdenes pendientes para monitorear")
                return
            
            self.pending_orders_monitor[operation_id] = pending_orders
            self._add_message(operation_id, f"🔍 Iniciando monitoreo continuo de {len(pending_orders)} órdenes pendientes")
            
            # Crear tarea de monitoreo
            monitoring_task = asyncio.create_task(
                self._monitor_pending_orders_loop(operation_id, progress)
            )
            self.monitoring_tasks[operation_id] = monitoring_task
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error iniciando monitoreo: {str(e)}")
    
    async def _monitor_pending_orders_loop(self, operation_id: str, progress: OperationProgress):
        """Loop de monitoreo continuo de órdenes pendientes"""
        try:
            max_monitoring_time = 1800  # 30 minutos máximo
            check_interval = 10  # Verificar cada 10 segundos
            start_time = time.time()
            
            self._add_message(operation_id, f"⏰ MONITOREO CONTINUO INICIADO")
            self._add_message(operation_id, f"   🎯 Objetivo: Completar TODOS los nominales solicitados")
            self._add_message(operation_id, f"   ⏱️ Duración máxima: {max_monitoring_time/60:.0f} minutos")
            self._add_message(operation_id, f"   🔄 Verificación cada: {check_interval} segundos")
            
            while time.time() - start_time < max_monitoring_time:
                try:
                    # Verificar estado de órdenes pendientes
                    pending_orders = self.pending_orders_monitor.get(operation_id, [])
                    if not pending_orders:
                        self._add_message(operation_id, "✅ Todas las órdenes han sido procesadas - deteniendo monitoreo")
                        break
                    
                    # Verificar cada orden pendiente
                    still_pending = []
                    newly_filled = []
                    
                    for order in pending_orders:
                        if order.status == "pending":
                            # Verificar estado actual
                            await self._verify_order_status(operation_id, order.order_id, order)
                            
                            if order.status == "filled":
                                newly_filled.append(order)
                                self._add_message(operation_id, f"🎉 ¡Orden {order.order_id} EJECUTADA durante el monitoreo!")
                            else:
                                still_pending.append(order)
                    
                    # Actualizar lista de órdenes pendientes
                    self.pending_orders_monitor[operation_id] = still_pending
                    
                    if newly_filled:
                        # Recalcular ratios y notificar progreso
                        await self._recalculate_operation_progress(operation_id, progress)
                        await self._notify_progress(operation_id, progress)
                        
                        # Verificar si necesitamos ejecutar más lotes para completar los nominales
                        # Necesitamos obtener el request original para esto
                        if hasattr(progress, 'original_request'):
                            await self._check_and_execute_additional_lots(operation_id, progress, progress.original_request)
                    
                    if not still_pending:
                        # Verificar si realmente completamos todos los nominales
                        if hasattr(progress, 'original_request'):
                            if progress.completed_nominales >= progress.original_request.nominales:
                                self._add_message(operation_id, "🎉 ¡TODOS LOS NOMINALES EJECUTADOS! Operación completada")
                                progress.status = OperationStatus.COMPLETED
                                await self._notify_progress(operation_id, progress)
                                break
                            else:
                                self._add_message(operation_id, f"⚠️ Órdenes ejecutadas pero faltan nominales: {progress.completed_nominales}/{progress.original_request.nominales}")
                                # Continuar monitoreo para ejecutar más lotes
                    
                    # Esperar antes del siguiente check
                    await asyncio.sleep(check_interval)
                    
                except Exception as e:
                    self._add_message(operation_id, f"❌ Error en monitoreo: {str(e)}")
                    await asyncio.sleep(check_interval)
            
            # Limpiar monitoreo
            if operation_id in self.pending_orders_monitor:
                remaining_pending = len(self.pending_orders_monitor[operation_id])
                if remaining_pending > 0:
                    self._add_message(operation_id, f"⏰ Monitoreo finalizado - {remaining_pending} órdenes aún pendientes")
                del self.pending_orders_monitor[operation_id]
            
            if operation_id in self.monitoring_tasks:
                del self.monitoring_tasks[operation_id]
                
        except Exception as e:
            self._add_message(operation_id, f"❌ Error en loop de monitoreo: {str(e)}")
    
    async def _recalculate_operation_progress(self, operation_id: str, progress: OperationProgress):
        """Recalcula el progreso de la operación basado en órdenes ejecutadas"""
        try:
            # Recalcular totales solo con órdenes ejecutadas
            executed_sell_orders = [o for o in progress.sell_orders if o.status == "filled"]
            executed_buy_orders = [o for o in progress.buy_orders if o.status == "filled"]
            
            if executed_sell_orders:
                progress.total_sold_amount = sum(order.quantity * order.price for order in executed_sell_orders)
                progress.average_sell_price = progress.total_sold_amount / sum(order.quantity for order in executed_sell_orders)
            
            if executed_buy_orders:
                progress.total_bought_amount = sum(order.quantity * order.price for order in executed_buy_orders)
                progress.average_buy_price = progress.total_bought_amount / sum(order.quantity for order in executed_buy_orders)
                progress.completed_nominales = sum(order.quantity for order in executed_buy_orders)
            
            # Recalcular ratio ponderado
            if progress.total_bought_amount > 0:
                progress.weighted_average_ratio = progress.total_sold_amount / progress.total_bought_amount
                progress.condition_met = self._check_condition(
                    progress.weighted_average_ratio, 
                    progress.target_ratio, 
                    progress.condition
                )
            
            self._add_message(operation_id, f"📊 Progreso recalculado:")
            self._add_message(operation_id, f"   ✅ Órdenes ejecutadas: {len(executed_sell_orders)} ventas, {len(executed_buy_orders)} compras")
            self._add_message(operation_id, f"   📈 Ratio actual: {progress.weighted_average_ratio:.6f}")
            self._add_message(operation_id, f"   💰 Nominales ejecutados: {progress.completed_nominales}")
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error recalculando progreso: {str(e)}")
    
    async def _check_and_execute_additional_lots(self, operation_id: str, progress: OperationProgress, request: RatioOperationRequest):
        """Verifica si necesitamos ejecutar lotes adicionales para completar los nominales"""
        try:
            # Calcular nominales restantes
            remaining_nominales = request.nominales - progress.completed_nominales
            
            if remaining_nominales <= 0:
                return  # Ya completamos todos los nominales
            
            # Obtener cotizaciones actuales
            instruments = [request.instrument_to_sell]
            if len(request.pair) > 1:
                for instrument in request.pair:
                    if instrument != request.instrument_to_sell:
                        instruments.append(instrument)
                        break
            
            quotes = self._get_real_quotes(instruments)
            if not quotes:
                self._add_message(operation_id, "⚠️ No se pueden obtener cotizaciones para lotes adicionales")
                return
            
            sell_quotes = quotes.get(request.instrument_to_sell, {})
            buy_instrument = instruments[1] if len(instruments) > 1 else request.pair[1] if len(request.pair) > 1 else "MERV - XMEV - TX28 - 24hs"
            buy_quotes = quotes.get(buy_instrument, {})
            
            # Calcular tamaño de lote adicional con factor de seguridad
            lot_size = self._calculate_lot_size(sell_quotes, buy_quotes, remaining_nominales, operation_id)
            
            if lot_size <= 0:
                self._add_message(operation_id, f"⚠️ Sin liquidez para lote adicional - nominales restantes: {remaining_nominales}")
                return
            
            self._add_message(operation_id, f"🔄 EJECUTANDO LOTE ADICIONAL: {lot_size} nominales (restantes: {remaining_nominales})")
            
            # Ejecutar lote adicional
            await self._execute_additional_lot(operation_id, request, sell_quotes, buy_quotes, lot_size, buy_instrument)
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error ejecutando lote adicional: {str(e)}")
    
    async def _execute_additional_lot(self, operation_id: str, request: RatioOperationRequest, sell_quotes: Dict, buy_quotes: Dict, lot_size: float, buy_instrument: str):
        """Ejecuta un lote adicional para completar los nominales"""
        try:
            # PASO 1: Vender instrumento
            if "TX26" in request.instrument_to_sell:
                sell_price = sell_quotes.get('bid', 0)
                self._add_message(operation_id, f"📤 LOTE ADICIONAL - Vendiendo TX26 @ {sell_price}")
            elif "TX28" in request.instrument_to_sell:
                sell_price = buy_quotes.get('bid', 0)
                self._add_message(operation_id, f"📤 LOTE ADICIONAL - Vendiendo TX28 @ {sell_price}")
            else:
                return
            
            sell_order = await self._execute_real_order_with_liquidity_check(
                operation_id, 
                request.instrument_to_sell, 
                "sell", 
                lot_size, 
                sell_price
            )
            
            if not sell_order:
                self._add_message(operation_id, f"❌ Error en venta del lote adicional")
                return
            
            # Agregar a órdenes de venta
            if operation_id in self.active_operations:
                self.active_operations[operation_id].sell_orders.append(sell_order)
            
            # Esperar un poco
            await asyncio.sleep(1)
            
            # PASO 2: Comprar instrumento complementario
            if "TX26" in request.instrument_to_sell:
                buy_price = buy_quotes.get('offer', 0)
                self._add_message(operation_id, f"📥 LOTE ADICIONAL - Comprando TX28 @ {buy_price}")
            elif "TX28" in request.instrument_to_sell:
                buy_price = sell_quotes.get('offer', 0)
                self._add_message(operation_id, f"📥 LOTE ADICIONAL - Comprando TX26 @ {buy_price}")
            else:
                return
            
            buy_order = await self._execute_real_order_with_liquidity_check(
                operation_id, 
                buy_instrument, 
                "buy", 
                lot_size, 
                buy_price
            )
            
            if not buy_order:
                self._add_message(operation_id, f"❌ Error en compra del lote adicional")
                return
            
            # Agregar a órdenes de compra
            if operation_id in self.active_operations:
                self.active_operations[operation_id].buy_orders.append(buy_order)
            
            # Agregar a monitoreo de órdenes pendientes
            if operation_id in self.pending_orders_monitor:
                self.pending_orders_monitor[operation_id].extend([sell_order, buy_order])
            
            self._add_message(operation_id, f"✅ LOTE ADICIONAL EJECUTADO: {sell_order.order_id}, {buy_order.order_id}")
            
        except Exception as e:
            self._add_message(operation_id, f"❌ Error ejecutando lote adicional: {str(e)}")
    
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
            real_quotes={},
            original_request=request
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
            
            # Calcular tamaño de lote basado en liquidez disponible con factor de seguridad
            lot_size = self._calculate_lot_size(sell_quotes, buy_quotes, progress.remaining_nominales, operation_id)
            
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
            
            sell_order = await self._execute_real_order_with_liquidity_check(
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
            
            buy_order = await self._execute_real_order_with_liquidity_check(
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
        
        # Verificar estado real de todas las órdenes antes de finalizar
        self._add_message(operation_id, "🔍 VERIFICANDO ESTADO REAL DE TODAS LAS ÓRDENES...")
        
        # Verificar estado de todas las órdenes una vez más
        await self._verify_all_orders_status(operation_id, progress)
        
        all_orders_filled = True
        pending_orders = []
        
        # Verificar órdenes de venta
        for sell_order in progress.sell_orders:
            if sell_order.status != "filled":
                all_orders_filled = False
                pending_orders.append(f"Venta {sell_order.order_id}: {sell_order.status}")
        
        # Verificar órdenes de compra
        for buy_order in progress.buy_orders:
            if buy_order.status != "filled":
                all_orders_filled = False
                pending_orders.append(f"Compra {buy_order.order_id}: {buy_order.status}")
        
        # Determinar estado final basado en órdenes realmente ejecutadas
        if all_orders_filled and progress.remaining_nominales <= 0:
            progress.status = OperationStatus.COMPLETED
            self._add_message(operation_id, "✅ OPERACIÓN COMPLETADA EXITOSAMENTE - TODAS LAS ÓRDENES EJECUTADAS")
        else:
            # Hay órdenes pendientes - iniciar monitoreo continuo
            progress.status = OperationStatus.RUNNING  # Mantener como RUNNING hasta completar
            self._add_message(operation_id, f"🔍 ÓRDENES PENDIENTES DETECTADAS - INICIANDO MONITOREO CONTINUO")
            if pending_orders:
                self._add_message(operation_id, f"   ⏳ Órdenes pendientes:")
                for pending in pending_orders:
                    self._add_message(operation_id, f"      {pending}")
            
            # Iniciar monitoreo continuo de órdenes pendientes
            await self._start_pending_orders_monitoring(operation_id, progress)
        
        progress.current_step = OperationStep.FINALIZING
        progress.progress_percentage = 100
        
        # Ratio final de toda la operación (solo órdenes ejecutadas)
        executed_sell_orders = [o for o in progress.sell_orders if o.status == "filled"]
        executed_buy_orders = [o for o in progress.buy_orders if o.status == "filled"]
        
        if executed_buy_orders and executed_sell_orders:
            total_executed_sold = sum(order.quantity * order.price for order in executed_sell_orders)
            total_executed_bought = sum(order.quantity * order.price for order in executed_buy_orders)
            
            if total_executed_bought > 0:
                final_ratio = total_executed_sold / total_executed_bought
                progress.weighted_average_ratio = final_ratio
                progress.condition_met = self._check_condition(final_ratio, request.target_ratio, request.condition)
                
                self._add_message(operation_id, f"📊 RESUMEN FINAL:")
                self._add_message(operation_id, f"   🎯 Nominales objetivo: {request.nominales}")
                self._add_message(operation_id, f"   ✅ Nominales ejecutados: {progress.completed_nominales}")
                self._add_message(operation_id, f"   📈 Ratio final ponderado: {final_ratio:.6f}")
                self._add_message(operation_id, f"   🎯 Condición cumplida: {progress.condition_met}")
                self._add_message(operation_id, f"   📦 Lotes ejecutados: {progress.batch_count}")
                self._add_message(operation_id, f"   ✅ Órdenes ejecutadas: {len(executed_sell_orders)} ventas, {len(executed_buy_orders)} compras")
                if pending_orders:
                    self._add_message(operation_id, f"   ⏳ Órdenes pendientes: {len(pending_orders)}")
        
        # Notificar progreso final
        await self._notify_progress(operation_id, progress)
        
        # Si hay órdenes pendientes, iniciar monitoreo continuo
        if pending_orders:
            self._add_message(operation_id, "🔄 Iniciando monitoreo continuo de órdenes pendientes...")
            await self._start_pending_orders_monitoring(operation_id, progress)
        else:
            self._add_message(operation_id, "✅ Todas las órdenes ejecutadas - no se requiere monitoreo")
        
        print(f"[DEBUG] Operación {operation_id} completada: {progress.completed_nominales}/{request.nominales} nominales")
        return progress
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationProgress]:
        """Obtiene el estado de una operación"""
        return self.active_operations.get(operation_id)

# Instancia global
real_ratio_manager = RealRatioOperationManager()
