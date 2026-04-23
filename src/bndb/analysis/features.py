"""Event feature extraction."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def extract_event_features(
    event: dict[str, Any],
    symbol_klines: list[dict[str, Any]],
    btc_klines: list[dict[str, Any]],
    *,
    interval_minutes: int = 5,
) -> list[dict[str, Any]]:
    event_time = event["triggered_at"]
    index = next((idx for idx, item in enumerate(symbol_klines) if item["open_time"] == event_time), None)
    if index is None:
        return []

    feature_rows: list[dict[str, Any]] = []
    for window_minutes in (15, 60, 240):
        bar_count = max(1, window_minutes // interval_minutes)
        sample = symbol_klines[max(0, index - bar_count + 1) : index + 1]
        if not sample:
            continue
        closes = [float(item["close"]) for item in sample]
        volumes = [float(item["volume"]) for item in sample]
        feature_rows.append(
            _feature_row(
                event["id"],
                f"return_{_window_label(window_minutes)}",
                _pct_change(float(sample[0]["open"]), float(sample[-1]["close"])),
                window_minutes,
            )
        )
        feature_rows.append(
            _feature_row(
                event["id"],
                f"volatility_{_window_label(window_minutes)}",
                pstdev(closes) if len(closes) > 1 else 0.0,
                window_minutes,
            )
        )
        feature_rows.append(
            _feature_row(
                event["id"],
                f"volume_mean_{_window_label(window_minutes)}",
                mean(volumes),
                window_minutes,
            )
        )

    recent_15 = symbol_klines[max(0, index - (15 // interval_minutes) + 1) : index + 1]
    baseline_4h = symbol_klines[max(0, index - (240 // interval_minutes) + 1) : index + 1]
    if recent_15 and baseline_4h:
        short_volume = mean(float(item["volume"]) for item in recent_15)
        long_volume = mean(float(item["volume"]) for item in baseline_4h)
        feature_rows.append(
            _feature_row(
                event["id"],
                "volume_ratio_15m_vs_4h",
                short_volume / long_volume if long_volume else 0.0,
                15,
            )
        )

    btc_index = next((idx for idx, item in enumerate(btc_klines) if item["open_time"] == event_time), None)
    if btc_index is not None:
        btc_sample = btc_klines[max(0, btc_index - (15 // interval_minutes) + 1) : btc_index + 1]
        if recent_15 and btc_sample:
            asset_return = _pct_change(float(recent_15[0]["open"]), float(recent_15[-1]["close"]))
            btc_return = _pct_change(float(btc_sample[0]["open"]), float(btc_sample[-1]["close"]))
            feature_rows.append(
                _feature_row(event["id"], "excess_return_vs_btc_15m", asset_return - btc_return, 15)
            )

    return feature_rows


def _window_label(window_minutes: int) -> str:
    return {15: "15m", 60: "1h", 240: "4h"}[window_minutes]


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return round(((end - start) / start) * 100, 6)


def _feature_row(event_id: int, name: str, value: float, window: int) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "feature_name": name,
        "feature_value": round(float(value), 6),
        "window_minutes": window,
    }
