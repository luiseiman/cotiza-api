# strategy_engine.py
# Evaluación de reglas basadas en 'expr' (en params) y envío de alertas.
# - Carga reglas desde Supabase (trading_rules) filtradas por user/client/símbolos
# - Evalúa expr con contexto: base.*, quote.* y helpers
# - Notifica vía telegram_control.notify si existe; si no, imprime

from __future__ import annotations

from typing import Any, Dict, Optional, List
from supabase_client import list_rules

# Notificador opcional (Telegram)
def _get_notifier():
    try:
        from telegram_control import notify  # type: ignore
        return notify
    except Exception:
        def _fallback(msg: str):
            print(f"[notify] {msg}")
        return _fallback

_notify = _get_notifier()

# Helpers disponibles en las expresiones
def _mid(d: Dict[str, Any]) -> Optional[float]:
    bid = d.get("bid")
    ask = d.get("offer")
    if bid is not None and ask is not None:
        return (bid + ask) / 2.0
    last = d.get("last")
    return float(last) if last is not None else None

def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    try:
        if a is None or b is None:
            return None
        if b == 0:
            return None
        return float(a) / float(b)
    except Exception:
        return None

_ALLOWED_FUNCS = {
    "mid": _mid,
    "div": _safe_div,
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
}

def _eval_expr(expr: str, *, base: Dict[str, Any], quote: Dict[str, Any], ratios: Dict[str, Any]) -> bool:
    """
    Evalúa expr en un entorno muy limitado.
    Variables disponibles:
      - base (dict con bid/offer/last/bid_size/offer_size/...)
      - quote (...)
      - ratios (mid, bid, ask, sma180_mid, std60_mid, std180_mid, ...)
      - funciones: mid(), div(), abs(), min(), max(), round()
    """
    safe_globals = {"__builtins__": {}}
    safe_locals = {
        "base": base,
        "quote": quote,
        "ratios": ratios,
        **_ALLOWED_FUNCS,
    }
    try:
        result = eval(expr, safe_globals, safe_locals)
        return bool(result)
    except Exception:
        return False

def evaluateAndAlert(
    *,
    user_id: str,
    client_id: str,
    base_symbol: str,
    quote_symbol: str,
    snapshot: Dict[str, Any],
) -> int:
    """
    Carga reglas para (user_id, client_id, base_symbol, quote_symbol),
    evalúa y dispara alertas. Retorna cantidad de reglas que matchearon.
    """
    rules = list_rules(user_id=user_id, client_id=client_id, active=True)
    if not rules:
        return 0

    # Filtrar por símbolos
    filtered = [
        r for r in rules
        if r.get("base_symbol") == base_symbol and r.get("quote_symbol") == quote_symbol
        and r.get("rule_type", "expr") == "expr"
    ]
    if not filtered:
        return 0

    base = snapshot.get("base", {})
    quote = snapshot.get("quote", {})
    ratios = snapshot.get("ratios", {})

    matched = 0
    for r in filtered:
        params = r.get("params") or {}
        expr = params.get("expr")
        if not isinstance(expr, str) or not expr.strip():
            continue

        ok = _eval_expr(expr, base=base, quote=quote, ratios=ratios)
        if ok:
            matched += 1
            try:
                _notify(
                    f"✅ Regla #{r.get('id')} cumplida\n"
                    f"{base_symbol} / {quote_symbol}\n"
                    f"expr: {expr}\n"
                    f"ratios.mid={ratios.get('mid')}, sma180_mid={ratios.get('sma180_mid')}, std180_mid={ratios.get('std180_mid')}"
                )
            except Exception:
                # No hacemos fail del flujo si notificar falla
                pass

    return matched