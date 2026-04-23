"""SQLite helpers for BNDB."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bndb.db.schema import SCHEMA


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect(database_path: str | Path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(database_path: str | Path) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)


def upsert_market_data(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
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
        return max(cursor.rowcount, 0)


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
    *,
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


def upsert_watchlist(database_path: str | Path, rows: list[dict[str, str]]) -> int:
    if not rows:
        return 0
    with connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT INTO watchlist(symbol, category, added_at, source)
            VALUES (:symbol, :category, :added_at, :source)
            ON CONFLICT(symbol) DO UPDATE SET
                category = excluded.category,
                added_at = excluded.added_at,
                source = excluded.source
            """,
            rows,
        )
        return max(cursor.rowcount, 0)


def remove_watchlist_symbol(database_path: str | Path, symbol: str) -> None:
    with connect(database_path) as connection:
        connection.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))


def list_watchlist(database_path: str | Path) -> list[dict[str, str]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT symbol, category, added_at, source FROM watchlist ORDER BY symbol ASC"
        ).fetchall()
    return [dict(row) for row in rows]


def insert_events(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    inserted = 0
    with connect(database_path) as connection:
        for row in rows:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO events(
                    symbol, event_type, triggered_at, score, trigger_detail, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["symbol"],
                    row["event_type"],
                    row["triggered_at"],
                    row["score"],
                    json.dumps(row["trigger_detail"], sort_keys=True),
                    row.get("created_at", utc_now_iso()),
                ),
            )
            inserted += 1 if cursor.rowcount == 1 else 0
    return inserted


def list_events(database_path: str | Path) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute("SELECT * FROM events ORDER BY triggered_at ASC").fetchall()
    return [_decode_event(dict(row)) for row in rows]


def list_events_without_features(database_path: str | Path) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT e.*
            FROM events e
            LEFT JOIN event_features f ON e.id = f.event_id
            WHERE f.id IS NULL
            ORDER BY e.triggered_at ASC
            """
        ).fetchall()
    return [_decode_event(dict(row)) for row in rows]


def list_events_without_outcomes(database_path: str | Path) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT e.*
            FROM events e
            LEFT JOIN event_outcomes o ON e.id = o.event_id
            WHERE o.id IS NULL
            ORDER BY e.triggered_at ASC
            """
        ).fetchall()
    return [_decode_event(dict(row)) for row in rows]


def replace_event_features(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
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
        return max(cursor.rowcount, 0)


def replace_event_outcomes(database_path: str | Path, rows: list[dict[str, Any]]) -> int:
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
        return max(cursor.rowcount, 0)


def count_events_by_type(database_path: str | Path) -> dict[str, int]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT event_type, COUNT(*) AS total FROM events GROUP BY event_type ORDER BY event_type"
        ).fetchall()
    return {row["event_type"]: row["total"] for row in rows}


def count_outcomes_by_path(database_path: str | Path) -> dict[str, int]:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT path_type, COUNT(*) AS total FROM event_outcomes GROUP BY path_type ORDER BY path_type"
        ).fetchall()
    return {row["path_type"]: row["total"] for row in rows}


def fetch_event_report(database_path: str | Path, limit: int) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                e.symbol,
                e.event_type,
                e.score,
                e.triggered_at,
                o.path_type,
                w.category AS watchlist_category
            FROM events e
            LEFT JOIN event_outcomes o ON o.event_id = e.id
            LEFT JOIN watchlist w ON w.symbol = e.symbol
            ORDER BY e.triggered_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_table_count(database_path: str | Path, table_name: str) -> int:
    with connect(database_path) as connection:
        row = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
    return 0 if row is None else int(row["total"])


def _decode_event(row: dict[str, Any]) -> dict[str, Any]:
    row["trigger_detail"] = json.loads(row["trigger_detail"])
    return row
