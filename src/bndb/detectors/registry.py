"""Detector registry and factory."""

from __future__ import annotations

from bndb.detectors.base import BaseDetector
from bndb.detectors.oi_shock import OIShockDetector
from bndb.detectors.price_shock import PriceShockDetector
from bndb.detectors.relative_strength import RelativeStrengthDetector
from bndb.detectors.volume_shock import VolumeShockDetector

DETECTOR_CLASSES: dict[str, type[BaseDetector]] = {
    "price_shock": PriceShockDetector,
    "volume_shock": VolumeShockDetector,
    "oi_shock": OIShockDetector,
    "relative_strength": RelativeStrengthDetector,
}


DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "price_shock": {"price_change_pct": 3.0, "atr_multiple": 2.0},
    "volume_shock": {"volume_multiple": 3.0},
    "oi_shock": {},
    "relative_strength": {"excess_return": 2.0},
}


def create_detectors(names: list[str] | None = None) -> list[BaseDetector]:
    detector_names = list(DETECTOR_CLASSES) if not names or names == ["all"] else names
    return [DETECTOR_CLASSES[name](DEFAULT_THRESHOLDS.get(name)) for name in detector_names]


def list_detector_names() -> list[str]:
    return list(DETECTOR_CLASSES)
