"""Rule helpers for event detection."""

from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

import yaml


def load_thresholds(path: str | Path | None = None) -> dict[str, dict[str, float]]:
    thresholds_path = Path(path) if path is not None else Path(__file__).with_name("thresholds.yaml")
    with thresholds_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return {
        name: {key: float(value) for key, value in values.items()}
        for name, values in raw.items()
    }


def price_shock_signal(
    current: dict[str, Any],
    history: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> tuple[bool, float, dict[str, float]]:
    if not history:
        return False, 0.0, {}
    price_change_pct = _pct_change(float(current["open"]), float(current["close"]))
    current_tr = _true_range(current)
    avg_tr = mean(_true_range(item) for item in history) if history else 0.0
    atr_ratio = current_tr / avg_tr if avg_tr else 0.0
    triggered = price_change_pct >= thresholds["price_change_pct"] or atr_ratio >= thresholds["atr_multiple"]
    score = min(100.0, max(price_change_pct * 20, atr_ratio * 25))
    return triggered, round(score, 6), {
        "price_change_pct": round(price_change_pct, 6),
        "atr_current": round(current_tr, 6),
        "atr_avg_4h": round(avg_tr, 6),
        "atr_ratio": round(atr_ratio, 6),
    }


def volume_shock_signal(
    current: dict[str, Any],
    history: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> tuple[bool, float, dict[str, float]]:
    if not history:
        return False, 0.0, {}
    current_volume = float(current["volume"])
    avg_volume = mean(float(item["volume"]) for item in history)
    volume_ratio = current_volume / avg_volume if avg_volume else 0.0
    triggered = volume_ratio >= thresholds["volume_multiple"]
    score = min(100.0, volume_ratio * 30)
    return triggered, round(score, 6), {
        "volume_current": round(current_volume, 6),
        "volume_avg_4h": round(avg_volume, 6),
        "volume_ratio": round(volume_ratio, 6),
    }


def relative_strength_signal(
    current: dict[str, Any],
    btc_current: dict[str, Any] | None,
    thresholds: dict[str, float],
) -> tuple[bool, float, dict[str, float]]:
    if btc_current is None:
        return False, 0.0, {}
    asset_return = _pct_change(float(current["open"]), float(current["close"]))
    btc_return = _pct_change(float(btc_current["open"]), float(btc_current["close"]))
    excess_return = asset_return - btc_return
    triggered = excess_return >= thresholds["excess_return"]
    score = min(100.0, max(0.0, excess_return * 25))
    return triggered, round(score, 6), {
        "asset_return": round(asset_return, 6),
        "btc_return": round(btc_return, 6),
        "excess_return": round(excess_return, 6),
    }


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return ((end - start) / start) * 100


def _true_range(kline: dict[str, Any]) -> float:
    return float(kline["high"]) - float(kline["low"])
