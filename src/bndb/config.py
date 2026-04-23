"""Application configuration defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]


@dataclass(slots=True)
class AppConfig:
    database_path: Path = Path("data") / "bndb.db"
    binance_base_url: str = "https://fapi.binance.com"
    default_symbols: list[str] = field(default_factory=lambda: list(DEFAULT_SYMBOLS))
    default_interval: str = "5m"
    default_days: int = 30
    request_pause_seconds: float = 0.2
    outcome_window_minutes: int = 240
    top_gainers_limit: int = 10
    manual_watchlist: list[dict[str, str]] = field(default_factory=list)
