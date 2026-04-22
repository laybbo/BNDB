"""Base detector contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDetector(ABC):
    name: str
    description: str

    def __init__(self, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = thresholds or {}

    @abstractmethod
    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        btc_klines: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
