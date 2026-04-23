"""Event outcome calculations."""

from __future__ import annotations

from typing import Any


def calculate_event_outcome(
    event: dict[str, Any],
    symbol_klines: list[dict[str, Any]],
    *,
    interval_minutes: int = 5,
    outcome_window_minutes: int = 240,
) -> dict[str, Any] | None:
    event_time = event["triggered_at"]
    event_index = next((idx for idx, item in enumerate(symbol_klines) if item["open_time"] == event_time), None)
    if event_index is None:
        return None

    future_bars = outcome_window_minutes // interval_minutes
    entry_index = event_index + 1
    future_window = symbol_klines[entry_index : entry_index + future_bars]
    if len(future_window) < future_bars:
        return None

    entry_price = float(future_window[0]["open"])
    max_forward_move = max(_pct_change(entry_price, float(item["high"])) for item in future_window)
    max_drawdown = max(abs(_pct_change(entry_price, float(item["low"]))) for item in future_window)
    close_at_4h = _pct_change(entry_price, float(future_window[-1]["close"]))
    mfe = max_forward_move
    mae = max_drawdown

    if max_forward_move > 5.0:
        path_type = "trending"
    elif max_forward_move < 2.0 and max_drawdown < 2.0:
        path_type = "sideways"
    elif max_drawdown > max_forward_move:
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
