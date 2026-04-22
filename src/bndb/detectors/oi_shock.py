"""OI shock detector stub."""

from __future__ import annotations

from typing import Any

from bndb.detectors.base import BaseDetector


class OIShockDetector(BaseDetector):
    name = "oi_shock"
    description = "Placeholder detector until OI history is available."

    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        btc_klines: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        return []
