"""Price shock detector."""

from __future__ import annotations

from typing import Any

from bndb.db import utc_now_iso
from bndb.definitions import load_thresholds, price_shock_signal
from bndb.detectors.base import BaseDetector


class PriceShockDetector(BaseDetector):
    name = "price_shock"

    def __init__(self, thresholds: dict[str, dict[str, float]] | None = None) -> None:
        self.thresholds = thresholds or load_thresholds()

    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        db_path: str,
        *,
        interval: str,
    ) -> list[dict[str, Any]]:
        del db_path
        events: list[dict[str, Any]] = []
        for index in range(len(klines)):
            signal = price_shock_signal(klines, index, interval=interval, thresholds=self.thresholds)
            if signal is None:
                continue
            events.append(
                {
                    "symbol": symbol,
                    "event_type": self.name,
                    "triggered_at": klines[index]["open_time"],
                    "score": signal["score"],
                    "trigger_detail": signal["detail"],
                    "created_at": utc_now_iso(),
                }
            )
        return events
