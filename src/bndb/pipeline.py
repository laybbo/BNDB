"""BNDB pipeline orchestration."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from bndb.analysis import calculate_event_outcome, extract_event_features
from bndb.config import AppConfig
from bndb.detectors import create_detectors
from bndb.db import (
    count_events_by_type,
    count_outcomes_by_path,
    fetch_event_report,
    fetch_table_count,
    get_latest_open_time,
    init_db,
    insert_events,
    list_events_without_features,
    list_events_without_outcomes,
    load_market_data,
    replace_event_features,
    replace_event_outcomes,
    upsert_market_data,
)
from bndb.fetchers import fetch_klines, next_start_from_latest_open_time
from bndb.watchlist import init_watchlist


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

    for symbol in symbols:
        try:
            latest_open_time = get_latest_open_time(database_path, symbol, interval)
            rows = fetch_klines(
                symbol,
                interval,
                days,
                config=app_config,
                start_ms=next_start_from_latest_open_time(latest_open_time, interval),
            )
            inserted_rows += upsert_market_data(database_path, rows)
        except Exception as exc:  # noqa: BLE001
            failures[symbol] = str(exc)

    return FetchResult(inserted_rows=inserted_rows, failures=failures)


def detect_events(
    symbols: list[str],
    detector_names: list[str],
    *,
    database_path: str,
    interval: str,
) -> DetectResult:
    init_db(database_path)
    detectors = create_detectors(detector_names)
    inserted_events = 0
    distribution: Counter[str] = Counter()
    failures: dict[str, str] = {}

    for symbol in symbols:
        try:
            symbol_klines = load_market_data(database_path, symbol, interval)
            if not symbol_klines:
                failures[symbol] = f"no market data for interval {interval}"
                continue
            symbol_events: list[dict[str, Any]] = []
            for detector in detectors:
                events = detector.detect(symbol, symbol_klines, database_path, interval=interval)
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


def analyze_events(*, database_path: str, interval: str, config: AppConfig | None = None) -> AnalyzeResult:
    init_db(database_path)
    app_config = config or AppConfig()
    feature_rows: list[dict[str, Any]] = []
    outcome_rows: list[dict[str, Any]] = []

    for event in list_events_without_features(database_path):
        symbol_klines = load_market_data(database_path, event["symbol"], interval)
        feature_rows.extend(extract_event_features(event, symbol_klines, interval=interval))

    for event in list_events_without_outcomes(database_path):
        symbol_klines = load_market_data(database_path, event["symbol"], interval)
        outcome = calculate_event_outcome(
            event,
            symbol_klines,
            interval=interval,
            outcome_window_minutes=app_config.outcome_window_minutes,
        )
        if outcome is not None:
            outcome_rows.append(outcome)

    inserted_features = replace_event_features(database_path, feature_rows)
    inserted_outcomes = replace_event_outcomes(database_path, outcome_rows)
    return AnalyzeResult(inserted_features=inserted_features, inserted_outcomes=inserted_outcomes)


def run_pipeline(
    symbols: list[str],
    interval: str,
    days: int,
    *,
    database_path: str,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    init_watchlist(database_path)
    fetch = fetch_market_data(symbols, interval, days, database_path=database_path, config=config)
    detect = detect_events(symbols, ["all"], database_path=database_path, interval=interval)
    analyze = analyze_events(database_path=database_path, interval=interval, config=config)
    return {
        "fetch_rows": fetch.inserted_rows,
        "events_inserted": detect.inserted_events,
        "distribution": count_events_by_type(database_path),
        "outcomes": count_outcomes_by_path(database_path),
        "features_inserted": analyze.inserted_features,
        "outcomes_inserted": analyze.inserted_outcomes,
        "failures": {
            "fetch": fetch.failures,
            "detect": detect.failures,
        },
    }


def render_report(limit: int, *, database_path: str) -> str:
    rows = fetch_event_report(database_path, limit)
    event_counts = count_events_by_type(database_path)
    outcome_counts = count_outcomes_by_path(database_path)
    headers = ("symbol", "type", "score", "outcome", "triggered_at")
    table_rows = [
        (
            _symbol_label(row["symbol"], row["watchlist_category"]),
            row["event_type"],
            f"{row['score']:.2f}",
            row["path_type"] or "-",
            row["triggered_at"],
        )
        for row in rows
    ]
    widths = [
        max(len(header), *(len(str(item[index])) for item in table_rows)) if table_rows else len(header)
        for index, header in enumerate(headers)
    ]
    lines = [
        f"market_data={fetch_table_count(database_path, 'market_data')} events={fetch_table_count(database_path, 'events')}",
        f"detectors: {_format_counts(event_counts)}",
        f"outcomes: {_format_counts(outcome_counts)}",
        "",
        " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "-+-".join("-" * width for width in widths),
    ]
    for row in table_rows:
        lines.append(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(lines)


def _symbol_label(symbol: str, category: str | None) -> str:
    if category is None:
        return symbol
    return f"{symbol} [WL-{category}]"


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    total = sum(counts.values())
    parts = []
    for name, value in counts.items():
        share = value / total * 100 if total else 0.0
        parts.append(f"{name}={value} ({share:.1f}%)")
    return ", ".join(parts)
