from pathlib import Path

from bndb.config import AppConfig
from bndb.db import connect, init_db, list_watchlist
from bndb.watchlist import fetch_gainers_watchlist


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


def test_init_db_creates_watchlist_table(tmp_path: Path) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)
    assert list_watchlist(database_path) == []


def test_fetch_gainers_watchlist_filters_and_upserts(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)

    monkeypatch.setattr(
        "bndb.watchlist.list_top_gainers",
        lambda *args, **kwargs: [
            {"symbol": "AAAUSDT", "category": "a", "source": "binance_24h_ticker"},
            {"symbol": "BBBUSDT", "category": "a", "source": "binance_24h_ticker"},
        ],
    )

    symbols = fetch_gainers_watchlist(str(database_path), top_n=2, min_volume=1_000_000)

    assert symbols == ["AAAUSDT", "BBBUSDT"]
    assert [row["symbol"] for row in list_watchlist(database_path)] == ["AAAUSDT", "BBBUSDT"]
