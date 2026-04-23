"""Watchlist helpers."""

from __future__ import annotations

from typing import Iterable

from bndb.db import list_watchlist, remove_watchlist_symbol, upsert_watchlist, utc_now_iso


INITIAL_WATCHLIST: list[dict[str, str]] = []


def init_watchlist(db_path: str) -> int:
    rows = [
        {
            "symbol": row["symbol"],
            "category": row.get("category", "c"),
            "added_at": row.get("added_at", utc_now_iso()),
            "source": row.get("source", "bootstrap"),
        }
        for row in INITIAL_WATCHLIST
    ]
    return upsert_watchlist(db_path, rows)


def add_watchlist_symbols(
    db_path: str,
    symbols: Iterable[str],
    *,
    category: str = "c",
    source: str = "manual",
) -> int:
    rows = [
        {"symbol": symbol, "category": category, "added_at": utc_now_iso(), "source": source}
        for symbol in symbols
    ]
    return upsert_watchlist(db_path, rows)


def remove_watchlist(db_path: str, symbol: str) -> None:
    remove_watchlist_symbol(db_path, symbol)


def get_watchlist(db_path: str) -> list[dict[str, str]]:
    return list_watchlist(db_path)
