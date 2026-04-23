"""Backward-compatible re-exports for SQLite helpers."""

from bndb.db import (
    connect,
    count_events_by_type,
    count_outcomes_by_path,
    fetch_event_report,
    get_latest_open_time,
    get_watchlist_markers,
    init_db,
    insert_events,
    insert_features,
    insert_market_data,
    insert_outcomes,
    list_events_without_features,
    list_events_without_outcomes,
    list_watchlist,
    load_market_data,
    upsert_watchlist_entries,
)

__all__ = [
    "connect",
    "count_events_by_type",
    "count_outcomes_by_path",
    "fetch_event_report",
    "get_latest_open_time",
    "get_watchlist_markers",
    "init_db",
    "insert_events",
    "insert_features",
    "insert_market_data",
    "insert_outcomes",
    "list_events_without_features",
    "list_events_without_outcomes",
    "list_watchlist",
    "load_market_data",
    "upsert_watchlist_entries",
]
