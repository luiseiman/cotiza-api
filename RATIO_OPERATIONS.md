# Operaciones de Ratio

Este módulo permite iniciar operaciones de ratio por WebSocket. Flujo básico:

1. Venta del instrumento indicado (usa bid).
2. Compra del otro instrumento del par con el monto resultante (usa offer).
3. Cálculo de ratio promedio y verificación de condición (<= o >=).
4. Reporte de progreso en tiempo real.

## Comandos WebSocket

- start_ratio_operation
- get_ratio_operation_status
- cancel_ratio_operation
- list_ratio_operations

Ejemplo de inicio:

```json
{
  "action": "start_ratio_operation",
  "pair": "MERV - XMEV - TX26 - 24hs-MERV - XMEV - TX28 - 24hs",
  "instrument_to_sell": "MERV - XMEV - TX26 - 24hs",
  "nominales": 100.0,
  "target_ratio": 0.95,
  "condition": "<=",
  "client_id": "client_001"
}
```




