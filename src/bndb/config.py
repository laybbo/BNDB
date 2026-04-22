"""Application configuration defaults."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    database_path: Path = Path("data") / "bndb.sqlite3"
    binance_base_url: str = "https://api.binance.com"

