from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from bndb.pipeline import analyze_events, detect_events, fetch_market_data, render_report, run_pipeline
from bndb.storage.sqlite import connect, init_db, insert_market_data


def test_fetch_market_data_inserts_rows(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "bndb.db"

    def fake_fetch(symbol: str, interval: str, days: int, **_: object) -> list[dict[str, object]]:
        return [_make_kline(symbol, interval, 0)]

    monkeypatch.setattr("bndb.pipeline.fetch_klines", fake_fetch)

    result = fetch_market_data(["BTCUSDT"], "1m", 1, database_path=str(database_path))

    assert result.inserted_rows == 1
    assert result.failures == {}


def test_detect_analyze_and_report_pipeline(tmp_path: Path) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)
    insert_market_data(database_path, _build_symbol_1m("BTCUSDT"))
    insert_market_data(database_path, _build_symbol_1m("ETHUSDT", strong=True))
    insert_market_data(database_path, _build_symbol_15m("BTCUSDT"))
    insert_market_data(database_path, _build_symbol_15m("ETHUSDT", strong=True))

    detect_result = detect_events(["ETHUSDT"], ["price_shock", "volume_shock", "relative_strength"], database_path=str(database_path))
    assert detect_result.inserted_events >= 1

    analyze_result = analyze_events(database_path=str(database_path))
    assert analyze_result.inserted_features > 0
    assert analyze_result.inserted_outcomes >= 0

    report = render_report(10, database_path=str(database_path))
    assert "ETHUSDT" in report
    assert "price_shock" in report or "volume_shock" in report or "relative_strength" in report


def test_run_pipeline_uses_both_fetch_intervals(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "bndb.db"
    calls: list[str] = []

    def fake_fetch(symbol: str, interval: str, days: int, **_: object) -> list[dict[str, object]]:
        calls.append(f"{symbol}:{interval}:{days}")
        if interval == "1m":
            return _build_symbol_1m(symbol, strong=symbol != "BTCUSDT")
        return _build_symbol_15m(symbol, strong=symbol != "BTCUSDT")

    monkeypatch.setattr("bndb.pipeline.fetch_klines", fake_fetch)

    summary = run_pipeline(["BTCUSDT", "ETHUSDT"], 1, database_path=str(database_path))

    assert "BTCUSDT:1m:1" in calls
    assert "BTCUSDT:15m:1" in calls
    assert "ETHUSDT:1m:1" in calls
    assert "ETHUSDT:15m:1" in calls
    assert summary["fetch_1m_rows"] > 0
    assert summary["fetch_15m_rows"] > 0


def _build_symbol_1m(symbol: str, strong: bool = False) -> list[dict[str, object]]:
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    rows = []
    price = 100.0 if symbol == "BTCUSDT" else 80.0
    for index in range(360):
        drift = 0.02 if strong else 0.005
        spike = 0.12 if strong and 110 <= index <= 124 else 0.0
        open_price = price
        close_price = price + drift + spike
        high_price = close_price + (0.03 if strong and 110 <= index <= 124 else 0.01)
        low_price = open_price - 0.01
        volume = 1000 + index * 2 + (300 if strong and 110 <= index <= 124 else 0)
        rows.append(
            {
                "symbol": symbol,
                "interval": "1m",
                "open_time": _iso(base_time + timedelta(minutes=index)),
                "open": round(open_price, 6),
                "high": round(high_price, 6),
                "low": round(low_price, 6),
                "close": round(close_price, 6),
                "volume": round(volume, 6),
                "quote_volume": round(volume * close_price, 6),
                "trades_count": 100 + index,
                "taker_buy_quote_volume": round(volume * close_price * 0.6, 6),
            }
        )
        price = close_price
    return rows


def _build_symbol_15m(symbol: str, strong: bool = False) -> list[dict[str, object]]:
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    rows = []
    price = 100.0 if symbol == "BTCUSDT" else 80.0
    for index in range(20):
        open_price = price
        if strong and index >= 15:
            close_price = price * 1.04
            high_price = close_price + 2.0
            volume = 4000.0
        else:
            close_price = price * (1.002 if symbol == "BTCUSDT" else 1.003)
            high_price = close_price + 0.3
            volume = 1000.0
        low_price = open_price - 0.2
        rows.append(
            {
                "symbol": symbol,
                "interval": "15m",
                "open_time": _iso(base_time + timedelta(minutes=15 * index)),
                "open": round(open_price, 6),
                "high": round(high_price, 6),
                "low": round(low_price, 6),
                "close": round(close_price, 6),
                "volume": volume,
                "quote_volume": round(volume * close_price, 6),
                "trades_count": 10 + index,
                "taker_buy_quote_volume": round(volume * close_price * 0.7, 6),
            }
        )
        price = close_price
    return rows


def _make_kline(symbol: str, interval: str, offset: int) -> dict[str, object]:
    timestamp = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=offset)
    return {
        "symbol": symbol,
        "interval": interval,
        "open_time": _iso(timestamp),
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.5,
        "volume": 1200.0,
        "quote_volume": 120600.0,
        "trades_count": 42,
        "taker_buy_quote_volume": 70000.0,
    }


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
