"""Relative strength detector."""

from __future__ import annotations

from typing import Any

from bndb.definitions import relative_strength_signal
from bndb.detectors.base import BaseDetector


class RelativeStrengthDetector(BaseDetector):
    name = "relative_strength"
    description = "Detect 5m outperformance versus BTC."

    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        btc_klines: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if btc_klines is None or len(klines) < 1:
            return []
        btc_by_time = {entry["open_time"]: entry for entry in btc_klines}
        events: list[dict[str, Any]] = []
        for current in klines:
            btc_current = btc_by_time.get(current["open_time"])
            triggered, score, detail = relative_strength_signal(current, btc_current, self.thresholds)
            if triggered:
                events.append(
                    {
                        "symbol": symbol,
                        "event_type": self.name,
                        "triggered_at": current["open_time"],
                        "score": score,
                        "trigger_detail": detail,
                    }
                )
        return events
