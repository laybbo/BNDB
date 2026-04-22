"""SQLite helpers for BNDB."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)

