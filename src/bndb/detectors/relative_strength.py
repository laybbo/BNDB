"""Relative strength detector."""

from __future__ import annotations

from typing import Any

from bndb.db import load_market_data, utc_now_iso
from bndb.definitions import load_thresholds, relative_strength_signal
from bndb.detectors.base import BaseDetector


class RelativeStrengthDetector(BaseDetector):
    name = "relative_strength"

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
        benchmark = load_market_data(db_path, "BTCUSDT", interval)
        if not benchmark:
            return []
        events: list[dict[str, Any]] = []
        for index in range(min(len(klines), len(benchmark))):
            signal = relative_strength_signal(
                klines,
                benchmark,
                index,
                interval=interval,
                thresholds=self.thresholds,
            )
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
