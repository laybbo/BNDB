"""Relative strength detector."""

from __future__ import annotations

from typing import Any

from bndb.detectors.base import BaseDetector


class RelativeStrengthDetector(BaseDetector):
    name = "relative_strength"
    description = "Detect sustained outperformance versus BTC."

    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        btc_klines: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if btc_klines is None or len(klines) < 3 or len(btc_klines) < 3:
            return []

        btc_by_time = {entry["open_time"]: entry for entry in btc_klines}
        excess_threshold = self.thresholds.get("excess_return", 2.0)
        events: list[dict[str, Any]] = []

        streak: list[bool] = []
        for current in klines:
            btc_current = btc_by_time.get(current["open_time"])
            if btc_current is None:
                continue
            asset_return = _return_pct(current)
            btc_return = _return_pct(btc_current)
            excess_return = asset_return - btc_return
            is_strong = excess_return >= excess_threshold
            streak.append(is_strong)
            if len(streak) > 3:
                streak.pop(0)
            streak_count = sum(1 for flag in streak if flag)
            if len(streak) == 3 and streak_count >= 2:
                score = min(100.0, max(0.0, excess_return * 20 + streak_count * 10))
                events.append(
                    {
                        "symbol": symbol,
                        "event_type": self.name,
                        "triggered_at": current["open_time"],
                        "score": round(score, 6),
                        "trigger_detail": {
                            "excess_return": round(excess_return, 6),
                            "btc_return": round(btc_return, 6),
                            "streak_count": streak_count,
                        },
                    }
                )
        return events


def _return_pct(kline: dict[str, Any]) -> float:
    return ((float(kline["close"]) - float(kline["open"])) / float(kline["open"])) * 100
