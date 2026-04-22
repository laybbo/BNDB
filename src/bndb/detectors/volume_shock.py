"""Volume shock detector."""

from __future__ import annotations

from statistics import mean
from typing import Any

from bndb.detectors.base import BaseDetector


class VolumeShockDetector(BaseDetector):
    name = "volume_shock"
    description = "Detect unusual volume spikes."

    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        btc_klines: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if len(klines) < 16:
            return []

        volume_multiple = self.thresholds.get("volume_multiple", 3.0)
        events: list[dict[str, Any]] = []
        for index in range(15, len(klines)):
            current = klines[index]
            previous = klines[index - 15 : index]
            volume_avg_4h = mean(float(item["volume"]) for item in previous)
            volume_current = float(current["volume"])
            volume_ratio = volume_current / volume_avg_4h if volume_avg_4h else 0.0
            if volume_ratio >= volume_multiple:
                score = min(100.0, max(0.0, volume_ratio * 25))
                events.append(
                    {
                        "symbol": symbol,
                        "event_type": self.name,
                        "triggered_at": current["open_time"],
                        "score": round(score, 6),
                        "trigger_detail": {
                            "volume_current": round(volume_current, 6),
                            "volume_avg_4h": round(volume_avg_4h, 6),
                            "volume_ratio": round(volume_ratio, 6),
                        },
                    }
                )
        return events
