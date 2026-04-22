"""SQLite helpers for BNDB."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    open_time TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    quote_volume REAL NOT NULL,
    trades_count INTEGER NOT NULL,
    taker_buy_quote_volume REAL NOT NULL DEFAULT 0,
    UNIQUE(symbol, interval, open_time)
);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol_interval_open_time
    ON market_data(symbol, interval, open_time);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    event_type TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    score REAL NOT NULL,
    trigger_detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, event_type, triggered_at)
);

CREATE INDEX IF NOT EXISTS idx_events_symbol_triggered_at
    ON events(symbol, triggered_at);

CREATE TABLE IF NOT EXISTS event_features (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value REAL NOT NULL,
    window_minutes INTEGER NOT NULL,
    FOREIGN KEY(event_id) REFERENCES events(id),
    UNIQUE(event_id, feature_name, window_minutes)
);

CREATE TABLE IF NOT EXISTS event_outcomes (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL UNIQUE,
    max_forward_move REAL NOT NULL,
    max_drawdown REAL NOT NULL,
    mfe REAL NOT NULL,
    mae REAL NOT NULL,
    close_at_4h REAL NOT NULL,
    path_type TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES events(id)
);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_path: str | Path) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)


def insert_market_data(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT OR IGNORE INTO market_data(
                symbol, interval, open_time, open, high, low, close, volume,
                quote_volume, trades_count, taker_buy_quote_volume
            ) VALUES (
                :symbol, :interval, :open_time, :open, :high, :low, :close, :volume,
                :quote_volume, :trades_count, :taker_buy_quote_volume
            )
            """,
            rows,
        )
        return cursor.rowcount if cursor.rowcount != -1 else 0


def get_latest_open_time(database_path: str | Path, symbol: str, interval: str) -> str | None:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT MAX(open_time) AS latest_open_time
            FROM market_data
            WHERE symbol = ? AND interval = ?
            """,
            (symbol, interval),
        ).fetchone()
    return None if row is None else row["latest_open_time"]


def load_market_data(
    database_path: str | Path,
    symbol: str,
    interval: str,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT symbol, interval, open_time, open, high, low, close, volume,
               quote_volume, trades_count, taker_buy_quote_volume
        FROM market_data
        WHERE symbol = ? AND interval = ?
    """
    params: list[Any] = [symbol, interval]
    if start_time is not None:
        query += " AND open_time >= ?"
        params.append(start_time)
    if end_time is not None:
        query += " AND open_time <= ?"
        params.append(end_time)
    query += " ORDER BY open_time ASC"

    with connect(database_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def insert_events(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    inserted = 0
    with connect(database_path) as connection:
        for row in rows:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO events(symbol, event_type, triggered_at, score, trigger_detail)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row["symbol"],
                    row["event_type"],
                    row["triggered_at"],
                    row["score"],
                    json.dumps(row["trigger_detail"], sort_keys=True),
                ),
            )
            inserted += 1 if cursor.rowcount == 1 else 0
    return inserted


def list_events_without_features(database_path: str | Path) -> list[dict[str, Any]]:
    query = """
        SELECT e.*
        FROM events e
        LEFT JOIN event_features f ON e.id = f.event_id
        WHERE f.id IS NULL
        ORDER BY e.triggered_at ASC
    """
    with connect(database_path) as connection:
        rows = connection.execute(query).fetchall()
    return [_decode_event(dict(row)) for row in rows]


def list_events_without_outcomes(database_path: str | Path) -> list[dict[str, Any]]:
    query = """
        SELECT e.*
        FROM events e
        LEFT JOIN event_outcomes o ON e.id = o.event_id
        WHERE o.id IS NULL
        ORDER BY e.triggered_at ASC
    """
    with connect(database_path) as connection:
        rows = connection.execute(query).fetchall()
    return [_decode_event(dict(row)) for row in rows]


def insert_features(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT OR REPLACE INTO event_features(event_id, feature_name, feature_value, window_minutes)
            VALUES (:event_id, :feature_name, :feature_value, :window_minutes)
            """,
            rows,
        )
        return cursor.rowcount if cursor.rowcount != -1 else 0


def insert_outcomes(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT OR REPLACE INTO event_outcomes(
                event_id, max_forward_move, max_drawdown, mfe, mae, close_at_4h, path_type
            ) VALUES (
                :event_id, :max_forward_move, :max_drawdown, :mfe, :mae, :close_at_4h, :path_type
            )
            """,
            rows,
        )
        return cursor.rowcount if cursor.rowcount != -1 else 0


def fetch_event_report(database_path: str | Path, limit: int) -> list[dict[str, Any]]:
    query = """
        SELECT
            e.symbol,
            e.event_type,
            e.score,
            e.triggered_at,
            o.path_type,
            o.close_at_4h
        FROM events e
        LEFT JOIN event_outcomes o ON o.event_id = e.id
        ORDER BY e.triggered_at DESC
        LIMIT ?
    """
    with connect(database_path) as connection:
        rows = connection.execute(query, (limit,)).fetchall()
    return [dict(row) for row in rows]


def count_events_by_type(database_path: str | Path) -> dict[str, int]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT event_type, COUNT(*) AS total FROM events GROUP BY event_type ORDER BY event_type"
        ).fetchall()
    return {row["event_type"]: row["total"] for row in rows}


def _decode_event(row: dict[str, Any]) -> dict[str, Any]:
    row["trigger_detail"] = json.loads(row["trigger_detail"])
    return row
