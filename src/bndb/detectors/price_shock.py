"""Price shock detector."""

from __future__ import annotations

from statistics import mean
from typing import Any

from bndb.detectors.base import BaseDetector


class PriceShockDetector(BaseDetector):
    name = "price_shock"
    description = "Detect sharp 15m price expansion with volatility expansion."

    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        btc_klines: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if len(klines) < 16:
            return []

        price_threshold = self.thresholds.get("price_change_pct", 3.0)
        atr_multiple = self.thresholds.get("atr_multiple", 2.0)
        events: list[dict[str, Any]] = []

        for index in range(15, len(klines)):
            window = klines[index - 15 : index + 1]
            current = klines[index]
            price_change_pct = ((current["close"] - window[0]["open"]) / window[0]["open"]) * 100
            atr_values = [_true_range(entry) for entry in window]
            current_atr = mean(atr_values[-3:])
            atr_avg_4h = mean(atr_values[:-1]) if len(atr_values) > 1 else current_atr
            atr_ratio = current_atr / atr_avg_4h if atr_avg_4h else 0.0

            if price_change_pct >= price_threshold and atr_ratio >= atr_multiple:
                score = min(100.0, max(0.0, price_change_pct * 12 + atr_ratio * 20))
                events.append(
                    {
                        "symbol": symbol,
                        "event_type": self.name,
                        "triggered_at": current["open_time"],
                        "score": round(score, 6),
                        "trigger_detail": {
                            "price_change_pct": round(price_change_pct, 6),
                            "atr_current": round(current_atr, 6),
                            "atr_avg_4h": round(atr_avg_4h, 6),
                            "atr_ratio": round(atr_ratio, 6),
                        },
                    }
                )

        return events


def _true_range(kline: dict[str, Any]) -> float:
    return float(kline["high"]) - float(kline["low"])
