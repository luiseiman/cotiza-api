# Cambios en terminal_ratios_history

## Resumen
Se agregaron 3 nuevos campos a la tabla `terminal_ratios_history` para almacenar el último valor operado de cada instrumento del ratio y el ratio calculado desde esos últimos valores.

## Nuevos Campos

### 1. `last_price_base` (float)
- **Descripción**: Último valor operado del instrumento base
- **Fuente**: Campo `last` del instrumento base en el cache de cotizaciones
- **Ejemplo**: Si el par es TX26/TX28, este campo contiene el último precio operado de TX26

### 2. `last_price_quote` (float)
- **Descripción**: Último valor operado del instrumento quote
- **Fuente**: Campo `last` del instrumento quote en el cache de cotizaciones
- **Ejemplo**: Si el par es TX26/TX28, este campo contiene el último precio operado de TX28

### 3. `last_ratio` (float)
- **Descripción**: Ratio calculado desde los últimos valores operados
- **Fórmula**: `last_ratio = last_price_base / last_price_quote`
- **Ejemplo**: Si TX26.last=1521 y TX28.last=1569, entonces last_ratio=0.969407

## Comparación con Campos Existentes

| Campo | Descripción | Cálculo |
|-------|-------------|---------|
| `bid_ratio` | Ratio para comprar el spread | `base.bid / quote.ask` |
| `ask_ratio` | Ratio para vender el spread | `base.ask / quote.bid` |
| `mid_ratio` | Ratio del punto medio | `(base.bid+base.ask)/2 / (quote.bid+quote.ask)/2` |
| **`last_ratio`** ⭐ | **Ratio de últimas operaciones** | **`base.last / quote.last`** |

## Utilidad

Los nuevos campos permiten:

1. **Análisis de operaciones reales**: Mientras que `bid_ratio` y `ask_ratio` representan precios teóricos de ejecución, `last_ratio` refleja el ratio basado en operaciones que realmente se ejecutaron.

2. **Comparación de liquidez**: La diferencia entre `last_ratio` y `mid_ratio` puede indicar hacia dónde se está moviendo el mercado.

3. **Validación de estrategias**: Permite validar si las señales generadas por los ratios teóricos (bid/ask) se alinean con las operaciones reales del mercado.

4. **Histórico completo**: Mantiene un registro de los últimos precios operados de cada instrumento, útil para análisis posteriores.

## Ejemplo de Registro

```python
{
    "user_id": "24239211",
    "base_symbol": "MERV - XMEV - TX26 - 24hs",
    "quote_symbol": "MERV - XMEV - TX28 - 24hs",
    "asof": "2025-09-30T...",
    
    # Ratios
    "bid_ratio": 0.968153,      # Para comprar spread
    "ask_ratio": 0.970663,      # Para vender spread
    "mid_ratio": 0.969407,      # Punto medio
    "last_ratio": 0.969407,     # ⭐ NUEVO: Basado en últimas operaciones
    
    # Precios base (TX26)
    "bid_price_base": 1520.0,
    "offer_price_base": 1522.0,
    "last_price_base": 1521.0,  # ⭐ NUEVO
    
    # Precios quote (TX28)
    "bid_price_quote": 1568.0,
    "offer_price_quote": 1570.0,
    "last_price_quote": 1569.0, # ⭐ NUEVO
    
    # ... otros campos (bandas, volatilidad, etc.)
}
```

## Implementación

### Archivo Modificado: `ratios_worker.py`

#### 1. Cálculo del ratio desde últimos valores (líneas 190-191)
```python
# --- Ratio desde últimos valores operados (last)
last_ratio = _safe_div(A_last, B_last) if (_is_num(A_last) and _is_num(B_last)) else None
```

#### 2. Inclusión en el registro (líneas 250, 257-258)
```python
row = {
    # ... campos existentes ...
    
    # Ratios
    "last_ratio": float(last_ratio) if _is_num(last_ratio) else None,  # NUEVO
    
    # Precios crudos
    "last_price_base": float(A_last) if _is_num(A_last) else None,     # NUEVO
    "last_price_quote": float(B_last) if _is_num(B_last) else None,    # NUEVO
}
```

## Testing

Para probar los cambios:

```bash
python3 test_new_ratio_fields.py
```

Este script simula datos de mercado y muestra cómo se calculan y guardan los nuevos campos.

## Compatibilidad

- ✅ **Retrocompatible**: Los campos existentes no se modifican
- ✅ **Opcional**: Los nuevos campos pueden ser NULL si no hay datos de `last`
- ✅ **Sin breaking changes**: El código existente sigue funcionando sin modificaciones

## Próximos Pasos

1. ✅ Código implementado en `ratios_worker.py`
2. ⏳ Ejecutar el sistema y verificar que los datos se guarden en Supabase
3. ⏳ Opcional: Agregar índices en Supabase para los nuevos campos si se usan en queries frecuentes
4. ⏳ Opcional: Actualizar dashboards/visualizaciones para mostrar `last_ratio`

---

**Fecha de implementación**: 2025-09-30  
**Autor**: Luis Eiman  
**Versión**: 1.0


