from pathlib import Path

from bndb.config import AppConfig
from bndb.storage.sqlite import connect


def test_default_config_values() -> None:
    config = AppConfig()
    assert config.binance_base_url == "https://fapi.binance.com"
    assert config.database_path.name == "bndb.db"


def test_sqlite_connect_creates_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "sample.sqlite3"
    connection = connect(database_path)
    connection.close()
    assert database_path.parent.exists()
