"""Watchlist management."""

from __future__ import annotations

from typing import Iterable

from bndb.config import AppConfig
from bndb.db import get_watchlist_markers, list_watchlist, upsert_watchlist_entries, utc_now_iso
from bndb.fetchers import list_top_gainers


def init_watchlist(database_path: str, entries: Iterable[dict[str, str]] | None = None) -> int:
    payload = [
        {
            "symbol": entry["symbol"],
            "category": entry["category"],
            "source": entry.get("source", "manual"),
            "added_at": entry.get("added_at", utc_now_iso()),
        }
        for entry in (entries or [])
    ]
    return upsert_watchlist_entries(database_path, payload)


def fetch_gainers_watchlist(
    db_path: str,
    top_n: int = 50,
    min_volume: float = 1_000_000,
    *,
    config: AppConfig | None = None,
) -> list[str]:
    app_config = config or AppConfig()
    entries = list_top_gainers(
        top_n,
        min_quote_volume=min_volume,
        config=app_config,
    )
    init_watchlist(db_path, entries)
    return [entry["symbol"] for entry in entries]


def sync_watchlist(
    database_path: str,
    *,
    config: AppConfig | None = None,
    include_top_gainers: bool = True,
) -> int:
    app_config = config or AppConfig()
    entries = list(app_config.manual_watchlist)
    if include_top_gainers:
        entries.extend(
            list_top_gainers(
                app_config.top_gainers_limit,
                config=app_config,
            )
        )
    return init_watchlist(database_path, entries)


def marker_for_symbol(database_path: str, symbol: str) -> str | None:
    category = get_watchlist_markers(database_path).get(symbol)
    if category is None:
        return None
    return f"[WL-{category}]"


__all__ = [
    "fetch_gainers_watchlist",
    "init_watchlist",
    "list_watchlist",
    "marker_for_symbol",
    "sync_watchlist",
]
