"""Detector registry and factory."""

from __future__ import annotations

from bndb.definitions import load_thresholds
from bndb.detectors.base import BaseDetector
from bndb.detectors.price_shock import PriceShockDetector
from bndb.detectors.relative_strength import RelativeStrengthDetector
from bndb.detectors.volume_shock import VolumeShockDetector

DETECTOR_CLASSES: dict[str, type[BaseDetector]] = {
    "price_shock": PriceShockDetector,
    "volume_shock": VolumeShockDetector,
    "relative_strength": RelativeStrengthDetector,
}


def create_detectors(names: list[str] | None = None) -> list[BaseDetector]:
    detector_names = list(DETECTOR_CLASSES) if not names or names == ["all"] else names
    thresholds = load_thresholds()
    return [DETECTOR_CLASSES[name](thresholds.get(name, {})) for name in detector_names]


def list_detector_names() -> list[str]:
    return list(DETECTOR_CLASSES)
