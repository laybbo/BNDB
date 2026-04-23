"""Feature extraction around detected events."""

from __future__ import annotations

from typing import Any

from bndb.fetchers.binance import interval_to_minutes


def extract_event_features(
    event: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    interval: str,
) -> list[dict[str, Any]]:
    event_index = _find_event_index(event["triggered_at"], rows)
    if event_index is None:
        return []
    interval_minutes = interval_to_minutes(interval)
    feature_rows: list[dict[str, Any]] = []
    for window_minutes in (5, 15, 60):
        bars = max(1, window_minutes // interval_minutes)
        if event_index < bars:
            continue
        window = rows[event_index - bars : event_index]
        start_close = float(window[0]["close"])
        end_close = float(rows[event_index]["close"])
        avg_volume = sum(float(item["volume"]) for item in window) / len(window)
        volatility = sum(_range_pct(item) for item in window) / len(window)
        current_volume = float(rows[event_index]["volume"])
        feature_rows.extend(
            [
                _feature(event["id"], "price_change_pct", _pct_change(start_close, end_close), window_minutes),
                _feature(
                    event["id"],
                    "volume_ratio",
                    0.0 if avg_volume == 0 else current_volume / avg_volume,
                    window_minutes,
                ),
                _feature(event["id"], "volatility_pct", volatility, window_minutes),
            ]
        )
    return feature_rows


def _feature(event_id: int, feature_name: str, feature_value: float, window_minutes: int) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "feature_name": feature_name,
        "feature_value": round(feature_value, 6),
        "window_minutes": window_minutes,
    }


def _find_event_index(triggered_at: str, rows: list[dict[str, Any]]) -> int | None:
    for index, row in enumerate(rows):
        if row["open_time"] == triggered_at:
            return index
    return None


def _range_pct(row: dict[str, Any]) -> float:
    return _pct_change(float(row["low"]), float(row["high"]))


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end / start - 1.0) * 100.0
