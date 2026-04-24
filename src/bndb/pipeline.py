"""BNDB pipeline orchestration."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bndb.analysis import calculate_event_outcome, extract_event_features
from bndb.config import AppConfig
from bndb.db import (
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
    list_symbols,
    load_market_data,
)
from bndb.detectors import create_detectors
from bndb.fetchers import fetch_klines, next_start_from_latest_open_time


@dataclass(slots=True)
class FetchResult:
    inserted_rows: int
    failures: dict[str, str]


@dataclass(slots=True)
class DetectResult:
    inserted_events: int
    distribution: dict[str, int]
    failures: dict[str, str]


@dataclass(slots=True)
class AnalyzeResult:
    inserted_features: int
    inserted_outcomes: int


def fetch_market_data(
    symbols: list[str],
    interval: str,
    days: int,
    *,
    database_path: str,
    config: AppConfig | None = None,
) -> FetchResult:
    app_config = config or AppConfig()
    init_db(database_path)
    inserted_rows = 0
    failures: dict[str, str] = {}

    for symbol in _ensure_btc_symbol(symbols):
        try:
            latest_open_time = get_latest_open_time(database_path, symbol, interval)
            rows = fetch_klines(
                symbol,
                interval,
                days,
                config=app_config,
                start_ms=next_start_from_latest_open_time(latest_open_time, interval),
            )
            inserted_rows += insert_market_data(database_path, rows)
        except Exception as exc:  # noqa: BLE001
            failures[symbol] = str(exc)

    return FetchResult(inserted_rows=inserted_rows, failures=failures)


def _resolve_symbols(symbols: list[str], database_path: str | Path, interval: str) -> list[str]:
    if symbols and symbols[0] == "all":
        return list_symbols(database_path, interval)
    return symbols


def detect_events(
    symbols: list[str],
    detector_names: list[str],
    *,
    database_path: str,
    interval: str = "5m",
) -> DetectResult:
    init_db(database_path)
    detectors = create_detectors(detector_names)
    inserted_events = 0
    distribution: Counter[str] = Counter()
    failures: dict[str, str] = {}
    btc_klines = load_market_data(database_path, "BTCUSDT", interval)
    resolved_symbols = _resolve_symbols(symbols, database_path, interval)

    for symbol in resolved_symbols:
        try:
            symbol_klines = load_market_data(database_path, symbol, interval)
            symbol_events: list[dict[str, Any]] = []
            for detector in detectors:
                events = detector.detect(symbol, symbol_klines, btc_klines)
                symbol_events.extend(events)
                distribution.update(event["event_type"] for event in events)
            inserted_events += insert_events(database_path, symbol_events)
        except Exception as exc:  # noqa: BLE001
            failures[symbol] = str(exc)

    return DetectResult(
        inserted_events=inserted_events,
        distribution=dict(distribution),
        failures=failures,
    )


def analyze_events(
    *,
    database_path: str,
    interval: str = "5m",
    config: AppConfig | None = None,
) -> AnalyzeResult:
    app_config = config or AppConfig()
    init_db(database_path)
    interval_minutes = _interval_minutes(interval)

    # Pre-load all market data once per symbol (not once per event)
    btc_klines = load_market_data(database_path, "BTCUSDT", interval)
    btc_index: dict[str, int] = {item["open_time"]: idx for idx, item in enumerate(btc_klines)}

    events_for_features = list_events_without_features(database_path)
    events_for_outcomes = list_events_without_outcomes(database_path)
    all_symbols = {e["symbol"] for e in events_for_features} | {e["symbol"] for e in events_for_outcomes}

    kline_cache: dict[str, list[dict[str, Any]]] = {}
    index_cache: dict[str, dict[str, int]] = {}
    total_symbols = len(all_symbols)
    for i, symbol in enumerate(all_symbols, 1):
        print(f"  Loading market data [{i}/{total_symbols}]: {symbol}")
        klines = load_market_data(database_path, symbol, interval)
        kline_cache[symbol] = klines
        index_cache[symbol] = {item["open_time"]: idx for idx, item in enumerate(klines)}

    # Phase 1: Features
    feature_rows: list[dict[str, Any]] = []
    total_feat = len(events_for_features)
    for i, event in enumerate(events_for_features):
        if (i + 1) % 10000 == 0 or i + 1 == total_feat:
            print(f"  Features: {i + 1}/{total_feat}")
        symbol = event["symbol"]
        feature_rows.extend(
            extract_event_features(
                event,
                kline_cache[symbol],
                btc_klines,
                interval_minutes=interval_minutes,
            )
        )

    # Phase 2: Outcomes
    outcome_rows: list[dict[str, Any]] = []
    total_out = len(events_for_outcomes)
    for i, event in enumerate(events_for_outcomes):
        if (i + 1) % 10000 == 0 or i + 1 == total_out:
            print(f"  Outcomes: {i + 1}/{total_out}")
        symbol = event["symbol"]
        outcome = calculate_event_outcome(
            event,
            kline_cache[symbol],
            interval_minutes=interval_minutes,
            outcome_window_minutes=app_config.outcome_window_minutes,
        )
        if outcome is not None:
            outcome_rows.append(outcome)

    inserted_features = insert_features(database_path, feature_rows)
    inserted_outcomes = insert_outcomes(database_path, outcome_rows)
    return AnalyzeResult(inserted_features=inserted_features, inserted_outcomes=inserted_outcomes)


def run_pipeline(
    symbols: list[str],
    days: int,
    *,
    database_path: str,
    interval: str = "5m",
    config: AppConfig | None = None,
) -> dict[str, Any]:
    fetch = fetch_market_data(symbols, interval, days, database_path=database_path, config=config)
    detect = detect_events(symbols, ["all"], database_path=database_path, interval=interval)
    analyze = analyze_events(database_path=database_path, interval=interval, config=config)
    return {
        "fetch_rows": fetch.inserted_rows,
        "events_inserted": detect.inserted_events,
        "event_distribution": count_events_by_type(database_path),
        "outcome_distribution": count_outcomes_by_path(database_path),
        "features_inserted": analyze.inserted_features,
        "outcomes_inserted": analyze.inserted_outcomes,
        "failures": {
            "fetch": fetch.failures,
            "detect": detect.failures,
        },
    }


def render_report(limit: int, *, database_path: str) -> str:
    detector_counts = count_events_by_type(database_path)
    outcome_counts = count_outcomes_by_path(database_path)
    watchlist_markers = get_watchlist_markers(database_path)
    rows = fetch_event_report(database_path, limit)
    lines = [
        "BNDB Report",
        f"Detectors: {_render_counter(detector_counts)}",
        f"Outcomes: {_render_counter(outcome_counts)}",
        "",
        "Recent events:",
    ]
    if not rows:
        lines.append("(empty)")
        return "\n".join(lines)

    headers = ("symbol", "type", "score", "outcome", "triggered_at")
    table_rows = []
    for row in rows:
        marker = watchlist_markers.get(row["symbol"])
        display_symbol = f"{row['symbol']} [WL-{marker}]" if marker else row["symbol"]
        table_rows.append(
            (
                display_symbol,
                row["event_type"],
                f"{row['score']:.2f}",
                row["path_type"] or "-",
                row["triggered_at"],
            )
        )
    widths = [
        max(len(header), *(len(str(item[index])) for item in table_rows))
        for index, header in enumerate(headers)
    ]
    lines.append(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    lines.append("-+-".join("-" * width for width in widths))
    for row in table_rows:
        lines.append(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(lines)


def _ensure_btc_symbol(symbols: list[str]) -> list[str]:
    ordered = []
    seen: set[str] = set()
    for symbol in [*symbols, "BTCUSDT"]:
        if symbol not in seen:
            seen.add(symbol)
            ordered.append(symbol)
    return ordered


def _interval_minutes(interval: str) -> int:
    return {"1m": 1, "5m": 5, "15m": 15, "1h": 60}[interval]


def _render_counter(counter: dict[str, int]) -> str:
    if not counter:
        return "(empty)"
    return ", ".join(f"{key}={value}" for key, value in sorted(counter.items()))
