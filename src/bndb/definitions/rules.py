"""Detector rule functions."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

import yaml

from bndb.fetchers.binance import interval_to_minutes


def load_thresholds(path: str | None = None) -> dict[str, dict[str, float]]:
    if path is None:
        raw = files("bndb.definitions").joinpath("thresholds.yaml").read_text(encoding="utf-8")
    else:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    return (yaml.safe_load(raw) or {})


def price_shock_signal(
    rows: list[dict[str, Any]],
    index: int,
    *,
    interval: str,
    thresholds: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    lookback = max(1, 5 // interval_to_minutes(interval))
    if index < lookback:
        return None
    current = rows[index]
    past = rows[index - lookback]
    price_change_pct = pct_change(float(past["close"]), float(current["close"]))
    current_range_pct = pct_change(float(current["low"]), float(current["high"]))
    atr_window = max(2, 240 // interval_to_minutes(interval))
    if index < atr_window:
        return None
    atr_values = [pct_change(float(item["low"]), float(item["high"])) for item in rows[index - atr_window : index]]
    atr_baseline = sum(atr_values) / len(atr_values) if atr_values else 0.0
    triggered = (
        price_change_pct >= thresholds["price_shock"]["return_pct"]
        or current_range_pct >= atr_baseline * thresholds["price_shock"]["atr_multiplier"]
    )
    if not triggered:
        return None
    score = max(
        price_change_pct / thresholds["price_shock"]["return_pct"],
        0.0 if atr_baseline == 0 else current_range_pct / (atr_baseline * thresholds["price_shock"]["atr_multiplier"]),
    )
    return {
        "score": round(score * 100, 4),
        "detail": {
            "price_change_pct": round(price_change_pct, 4),
            "current_range_pct": round(current_range_pct, 4),
            "atr_baseline_pct": round(atr_baseline, 4),
        },
    }


def volume_shock_signal(
    rows: list[dict[str, Any]],
    index: int,
    *,
    interval: str,
    thresholds: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    lookback = max(2, 240 // interval_to_minutes(interval))
    if index < lookback:
        return None
    baseline_rows = rows[index - lookback : index]
    avg_volume = sum(float(item["volume"]) for item in baseline_rows) / len(baseline_rows)
    current_volume = float(rows[index]["volume"])
    if avg_volume <= 0:
        return None
    volume_ratio = current_volume / avg_volume
    if volume_ratio < thresholds["volume_shock"]["volume_multiplier"]:
        return None
    return {
        "score": round(volume_ratio * 100, 4),
        "detail": {
            "current_volume": round(current_volume, 4),
            "avg_volume_4h": round(avg_volume, 4),
            "volume_ratio": round(volume_ratio, 4),
        },
    }


def relative_strength_signal(
    rows: list[dict[str, Any]],
    benchmark_rows: list[dict[str, Any]],
    index: int,
    *,
    interval: str,
    thresholds: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    lookback = max(1, 5 // interval_to_minutes(interval))
    if index < lookback or len(benchmark_rows) <= index:
        return None
    symbol_return = pct_change(float(rows[index - lookback]["close"]), float(rows[index]["close"]))
    benchmark_return = pct_change(
        float(benchmark_rows[index - lookback]["close"]),
        float(benchmark_rows[index]["close"]),
    )
    relative_return = symbol_return - benchmark_return
    if relative_return < thresholds["relative_strength"]["excess_return_pct"]:
        return None
    return {
        "score": round(relative_return * 100, 4),
        "detail": {
            "symbol_return_pct": round(symbol_return, 4),
            "btc_return_pct": round(benchmark_return, 4),
            "relative_return_pct": round(relative_return, 4),
        },
    }


def pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end / start - 1.0) * 100.0
