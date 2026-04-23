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
    default_interval: str = "5m"
    default_days: int = 7
    request_pause_seconds: float = 0.2
    outcome_window_minutes: int = 240


def parse_symbols(raw: str, *, default_symbols: list[str]) -> list[str]:
    parts = [item.strip().upper() for item in raw.split(",") if item.strip()]
    return parts or list(default_symbols)
