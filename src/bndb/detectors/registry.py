"""Detector registry helpers."""

from __future__ import annotations

from bndb.detectors.base import BaseDetector
from bndb.detectors.price_shock import PriceShockDetector
from bndb.detectors.relative_strength import RelativeStrengthDetector
from bndb.detectors.volume_shock import VolumeShockDetector

def create_detectors(names: list[str] | None = None) -> list[BaseDetector]:
    registry: dict[str, BaseDetector] = {
        "price_shock": PriceShockDetector(),
        "volume_shock": VolumeShockDetector(),
        "relative_strength": RelativeStrengthDetector(),
    }
    requested = names or ["all"]
    if requested == ["all"] or "all" in requested:
        return list(registry.values())
    return [registry[name] for name in requested if name in registry]
