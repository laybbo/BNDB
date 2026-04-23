"""Outcome calculations for detected events."""

from __future__ import annotations

from typing import Any

from bndb.fetchers.binance import interval_to_minutes


def calculate_event_outcome(
    event: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    interval: str,
    outcome_window_minutes: int = 240,
) -> dict[str, Any] | None:
    event_index = _find_event_index(event["triggered_at"], rows)
    if event_index is None or event_index >= len(rows) - 1:
        return None
    bars = max(1, outcome_window_minutes // interval_to_minutes(interval))
    future = rows[event_index + 1 : event_index + 1 + bars]
    if not future:
        return None
    entry_price = float(rows[event_index]["close"])
    max_forward_move = max(_pct_change(entry_price, float(item["high"])) for item in future)
    max_drawdown = max(_pct_change(float(item["low"]), entry_price) for item in future)
    close_at_4h = _pct_change(entry_price, float(future[-1]["close"]))
    path_type = classify_path_type(max_forward_move, max_drawdown)
    return {
        "event_id": event["id"],
        "max_forward_move": round(max_forward_move, 6),
        "max_drawdown": round(max_drawdown, 6),
        "mfe": round(max_forward_move, 6),
        "mae": round(max_drawdown, 6),
        "close_at_4h": round(close_at_4h, 6),
        "path_type": path_type,
    }


def classify_path_type(max_forward_move: float, max_drawdown: float) -> str:
    if max_forward_move > 5.0:
        return "trending"
    if max_forward_move < 2.0 and max_drawdown < 2.0:
        return "sideways"
    if max_drawdown > max_forward_move:
        return "reversal"
    return "sideways"


def _find_event_index(triggered_at: str, rows: list[dict[str, Any]]) -> int | None:
    for index, row in enumerate(rows):
        if row["open_time"] == triggered_at:
            return index
    return None


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end / start - 1.0) * 100.0
