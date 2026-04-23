"""Base detector contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDetector(ABC):
    name: str

    @abstractmethod
    def detect(
        self,
        symbol: str,
        klines: list[dict[str, Any]],
        db_path: str,
        *,
        interval: str,
    ) -> list[dict[str, Any]]:
        """Return triggered events for one symbol."""
