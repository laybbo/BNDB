from pathlib import Path

from bndb.config import AppConfig
from bndb.db import connect, init_db


def test_default_config_values() -> None:
    config = AppConfig()
    assert config.binance_base_url == "https://fapi.binance.com"
    assert config.database_path.name == "bndb.db"
    assert config.default_interval == "5m"


def test_sqlite_connect_creates_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "sample.sqlite3"
    connection = connect(database_path)
    connection.close()
    assert database_path.parent.exists()


def test_init_db_creates_required_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)
    connection = connect(database_path)
    tables = {
        row["name"]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    connection.close()
    assert {"market_data", "watchlist", "events", "event_features", "event_outcomes"} <= tables
