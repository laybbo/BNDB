"""Application configuration defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]


@dataclass(slots=True)
class AppConfig:
    database_path: Path = Path("data") / "bndb.db"
    binance_base_url: str = "https://fapi.binance.com"
    default_symbols: list[str] = field(default_factory=lambda: list(DEFAULT_SYMBOLS))
    default_interval: str = "1m"
    default_days: int = 30
    request_pause_seconds: float = 0.2
    outcome_window_minutes: int = 240
