from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from bndb.db import connect, init_db, insert_events, insert_market_data
from bndb.pipeline import analyze_events, detect_events, fetch_market_data, render_report, run_pipeline
from bndb.watchlist import init_watchlist


def test_fetch_market_data_inserts_rows(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "bndb.db"

    def fake_fetch(symbol: str, interval: str, days: int, **_: object) -> list[dict[str, object]]:
        return [_make_kline(symbol, interval, 0)]

    monkeypatch.setattr("bndb.pipeline.fetch_klines", fake_fetch)

    result = fetch_market_data(["BTCUSDT"], "5m", 1, database_path=str(database_path))

    assert result.inserted_rows == 1
    assert result.failures == {}


def test_detect_analyze_and_report_pipeline(tmp_path: Path) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)
    init_watchlist(str(database_path), [{"symbol": "ETHUSDT", "category": "b", "source": "manual"}])
    insert_market_data(database_path, _build_symbol_5m("BTCUSDT"))
    insert_market_data(database_path, _build_symbol_5m("ETHUSDT", strong=True))

    detect_result = detect_events(
        ["ETHUSDT"],
        ["price_shock", "volume_shock", "relative_strength"],
        database_path=str(database_path),
        interval="5m",
    )
    assert detect_result.inserted_events >= 1

    analyze_result = analyze_events(database_path=str(database_path), interval="5m")
    assert analyze_result.inserted_features > 0
    assert analyze_result.inserted_outcomes > 0

    report = render_report(10, database_path=str(database_path))
    assert "ETHUSDT [WL-b]" in report
    assert "trending" in report or "sideways" in report or "reversal" in report


def test_run_pipeline_uses_5m_interval_only(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "bndb.db"
    calls: list[str] = []

    def fake_fetch(symbol: str, interval: str, days: int, **_: object) -> list[dict[str, object]]:
        calls.append(f"{symbol}:{interval}:{days}")
        return _build_symbol_5m(symbol, strong=symbol != "BTCUSDT")

    monkeypatch.setattr("bndb.pipeline.fetch_klines", fake_fetch)

    summary = run_pipeline(["BTCUSDT", "ETHUSDT"], 1, database_path=str(database_path), interval="5m")

    assert "BTCUSDT:5m:1" in calls
    assert "ETHUSDT:5m:1" in calls
    assert summary["fetch_rows"] > 0
    assert "price_shock" in summary["event_distribution"]


def test_outcomes_use_next_bar_entry_not_same_bar(tmp_path: Path) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)
    rows = _build_signal_then_reversal("ETHUSDT")
    insert_market_data(database_path, _build_symbol_5m("BTCUSDT"))
    insert_market_data(database_path, rows)
    insert_events(
        database_path,
        [
            {
                "symbol": "ETHUSDT",
                "event_type": "price_shock",
                "triggered_at": rows[48]["open_time"],
                "score": 90.0,
                "trigger_detail": {"price_change_pct": 4.0},
            }
        ],
    )

    analyze = analyze_events(database_path=str(database_path), interval="5m")
    assert analyze.inserted_outcomes == 1

    with connect(database_path) as connection:
        outcome = connection.execute("SELECT close_at_4h, path_type FROM event_outcomes").fetchone()
    assert outcome["path_type"] == "reversal"
    assert outcome["close_at_4h"] < 0


def _build_symbol_5m(symbol: str, strong: bool = False) -> list[dict[str, object]]:
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    rows = []
    price = 100.0 if symbol == "BTCUSDT" else 80.0
    for index in range(120):
        if strong and index == 48:
            close_price = round(price * 1.04, 6)
            high_price = round(price * 1.05, 6)
            low_price = round(price * 0.995, 6)
            volume = 9000.0
        elif strong and 49 <= index < 97:
            close_price = round(price * 1.0025, 6)
            high_price = round(close_price * 1.002, 6)
            low_price = round(price * 0.999, 6)
            volume = 2500.0
        else:
            close_price = round(price * (1.0003 if symbol == "BTCUSDT" else 1.0006), 6)
            high_price = round(close_price * 1.001, 6)
            low_price = round(price * 0.999, 6)
            volume = 1000.0
        open_price = round(price, 6)
        rows.append(
            {
                "symbol": symbol,
                "interval": "5m",
                "open_time": _iso(base_time + timedelta(minutes=5 * index)),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "quote_volume": round(volume * close_price, 6),
                "trades_count": 100 + index,
                "taker_buy_quote_volume": round(volume * close_price * 0.6, 6),
            }
        )
        price = close_price
    return rows


def _build_signal_then_reversal(symbol: str) -> list[dict[str, object]]:
    rows = _build_symbol_5m(symbol, strong=False)
    event_row = rows[48].copy()
    event_row["close"] = round(float(event_row["open"]) * 1.04, 6)
    event_row["high"] = round(float(event_row["open"]) * 1.08, 6)
    event_row["volume"] = 8000.0
    event_row["quote_volume"] = round(event_row["volume"] * event_row["close"], 6)
    rows[48] = event_row

    next_row = rows[49].copy()
    next_row["open"] = event_row["close"]
    next_row["close"] = round(float(next_row["open"]) * 0.97, 6)
    next_row["high"] = round(float(next_row["open"]) * 1.001, 6)
    next_row["low"] = round(float(next_row["open"]) * 0.96, 6)
    next_row["quote_volume"] = round(next_row["volume"] * next_row["close"], 6)
    rows[49] = next_row

    price = float(next_row["close"])
    for index in range(50, 98):
        row = rows[index].copy()
        row["open"] = round(price, 6)
        row["close"] = round(price * 0.999, 6)
        row["high"] = round(price * 1.001, 6)
        row["low"] = round(price * 0.997, 6)
        row["quote_volume"] = round(row["volume"] * row["close"], 6)
        rows[index] = row
        price = row["close"]
    return rows


def _make_kline(symbol: str, interval: str, offset: int) -> dict[str, object]:
    timestamp = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=offset * 5)
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
