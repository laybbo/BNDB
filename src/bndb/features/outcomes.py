"""Event outcome calculations."""

from __future__ import annotations

from typing import Any


def calculate_event_outcome(event: dict[str, Any], symbol_klines: list[dict[str, Any]]) -> dict[str, Any] | None:
    event_time = event["triggered_at"]
    index = next((idx for idx, item in enumerate(symbol_klines) if item["open_time"] == event_time), None)
    if index is None:
        return None

    future_window = symbol_klines[index + 1 : index + 1 + 240]
    if len(future_window) < 240:
        return None

    entry_price = float(symbol_klines[index]["close"])
    max_forward_move = max(_pct_change(entry_price, float(item["high"])) for item in future_window)
    max_drawdown = min(_pct_change(entry_price, float(item["low"])) for item in future_window)
    close_at_4h = _pct_change(entry_price, float(future_window[-1]["close"]))
    mfe = max_forward_move
    mae = abs(max_drawdown)

    if mfe > 2 and close_at_4h > 0:
        path_type = "trending"
    elif mae > mfe and close_at_4h < 0:
        path_type = "reversal"
    else:
        path_type = "sideways"

    return {
        "event_id": event["id"],
        "max_forward_move": round(max_forward_move, 6),
        "max_drawdown": round(max_drawdown, 6),
        "mfe": round(mfe, 6),
        "mae": round(mae, 6),
        "close_at_4h": round(close_at_4h, 6),
        "path_type": path_type,
    }


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return ((end - start) / start) * 100
