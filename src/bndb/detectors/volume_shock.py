"""Volume shock detector."""

from __future__ import annotations

from typing import Any

from bndb.definitions import volume_shock_signal
from bndb.detectors.base import BaseDetector


class VolumeShockDetector(BaseDetector):
    name = "volume_shock"
    description = "Detect unusual 5m volume spikes."

    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        btc_klines: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if len(klines) < 49:
            return []
        events: list[dict[str, Any]] = []
        for index in range(48, len(klines)):
            current = klines[index]
            history = klines[index - 48 : index]
            triggered, score, detail = volume_shock_signal(current, history, self.thresholds)
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
