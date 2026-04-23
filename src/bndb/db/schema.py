"""Database schema definitions for BNDB."""

from __future__ import annotations


SCHEMA_STATEMENTS = [
    """
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
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_data_symbol_interval_open_time
        ON market_data(symbol, interval, open_time)
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist (
        symbol TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        added_at TEXT NOT NULL,
        source TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        symbol TEXT NOT NULL,
        event_type TEXT NOT NULL,
        triggered_at TEXT NOT NULL,
        score REAL NOT NULL,
        trigger_detail TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(symbol, event_type, triggered_at)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_events_symbol_triggered_at
        ON events(symbol, triggered_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS event_features (
        id INTEGER PRIMARY KEY,
        event_id INTEGER NOT NULL,
        feature_name TEXT NOT NULL,
        feature_value REAL NOT NULL,
        window_minutes INTEGER NOT NULL,
        FOREIGN KEY(event_id) REFERENCES events(id),
        UNIQUE(event_id, feature_name, window_minutes)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_outcomes (
        id INTEGER PRIMARY KEY,
        event_id INTEGER NOT NULL,
        max_forward_move REAL NOT NULL,
        max_drawdown REAL NOT NULL,
        mfe REAL NOT NULL,
        mae REAL NOT NULL,
        close_at_4h REAL NOT NULL,
        path_type TEXT NOT NULL,
        FOREIGN KEY(event_id) REFERENCES events(id),
        UNIQUE(event_id)
    )
    """,
]

SCHEMA = ";\n".join(statement.strip().rstrip(";") for statement in SCHEMA_STATEMENTS) + ";"
