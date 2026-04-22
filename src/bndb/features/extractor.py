"""Event feature extraction."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def extract_event_features(
    event: dict[str, Any],
    symbol_klines: list[dict[str, Any]],
    btc_klines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    event_time = event["triggered_at"]
    index = next((idx for idx, item in enumerate(symbol_klines) if item["open_time"] == event_time), None)
    if index is None:
        return []

    feature_rows: list[dict[str, Any]] = []
    for window in (15, 60, 240):
        sample = symbol_klines[max(0, index - window + 1) : index + 1]
        if not sample:
            continue
        feature_rows.append(
            _feature_row(
                event["id"],
                f"return_{_window_label(window)}",
                _pct_change(float(sample[0]["open"]), float(sample[-1]["close"])),
                window,
            )
        )

    sample_15 = symbol_klines[max(0, index - 14) : index + 1]
    sample_60 = symbol_klines[max(0, index - 59) : index + 1]
    sample_240 = symbol_klines[max(0, index - 239) : index + 1]
    if sample_15:
        closes = [float(item["close"]) for item in sample_15]
        feature_rows.append(_feature_row(event["id"], "volatility_15m", pstdev(closes) if len(closes) > 1 else 0.0, 15))
        feature_rows.append(_feature_row(event["id"], "atr_15m", _atr(sample_15), 15))
        avg_4h_volume = mean(float(item["volume"]) for item in sample_240) if sample_240 else 0.0
        volume_ratio = (sum(float(item["volume"]) for item in sample_15) / len(sample_15)) / avg_4h_volume if avg_4h_volume else 0.0
        feature_rows.append(_feature_row(event["id"], "volume_ratio_15m", volume_ratio, 15))
        feature_rows.append(_feature_row(event["id"], "volume_trend", _linear_slope([float(item["volume"]) for item in sample_15[-3:]]), 15))

    if sample_60:
        feature_rows.append(_feature_row(event["id"], "atr_1h", _atr(sample_60), 60))

    btc_index = next((idx for idx, item in enumerate(btc_klines) if item["open_time"] == event_time), None)
    if btc_index is not None:
        btc_sample_15 = btc_klines[max(0, btc_index - 14) : btc_index + 1]
        if sample_15 and btc_sample_15:
            asset_return = _pct_change(float(sample_15[0]["open"]), float(sample_15[-1]["close"]))
            btc_return = _pct_change(float(btc_sample_15[0]["open"]), float(btc_sample_15[-1]["close"]))
            feature_rows.append(
                _feature_row(event["id"], "excess_return_vs_btc_15m", asset_return - btc_return, 15)
            )

    return feature_rows


def _window_label(window: int) -> str:
    return {15: "15m", 60: "1h", 240: "4h"}[window]


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return round(((end - start) / start) * 100, 6)


def _atr(sample: list[dict[str, Any]]) -> float:
    if not sample:
        return 0.0
    return round(mean(float(item["high"]) - float(item["low"]) for item in sample), 6)


def _linear_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    x_values = list(range(len(values)))
    x_mean = mean(x_values)
    y_mean = mean(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values, strict=True))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 6)


def _feature_row(event_id: int, name: str, value: float, window: int) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "feature_name": name,
        "feature_value": round(float(value), 6),
        "window_minutes": window,
    }
