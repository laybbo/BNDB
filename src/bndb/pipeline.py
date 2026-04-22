"""BNDB pipeline orchestration."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from bndb.config import AppConfig
from bndb.detectors import create_detectors
from bndb.features import calculate_event_outcome, extract_event_features
from bndb.services.binance import fetch_klines, next_start_from_latest_open_time
from bndb.storage.sqlite import (
    count_events_by_type,
    fetch_event_report,
    get_latest_open_time,
    init_db,
    insert_events,
    insert_features,
    insert_market_data,
    insert_outcomes,
    list_events_without_features,
    list_events_without_outcomes,
    load_market_data,
)


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
            print(f"[fetch] {symbol} {interval} {days}d")
            latest_open_time = get_latest_open_time(database_path, symbol, interval)
            rows = fetch_klines(
                symbol,
                interval,
                days,
                config=app_config,
                start_ms=next_start_from_latest_open_time(latest_open_time, interval),
            )
            inserted_rows += insert_market_data(database_path, rows)
            print(f"[fetch] {symbol} inserted {len(rows)} rows")
        except Exception as exc:  # noqa: BLE001
            failures[symbol] = str(exc)
            print(f"[fetch] {symbol} failed: {exc}")

    return FetchResult(inserted_rows=inserted_rows, failures=failures)


def detect_events(
    symbols: list[str],
    detector_names: list[str],
    *,
    database_path: str,
) -> DetectResult:
    init_db(database_path)
    detectors = create_detectors(detector_names)
    inserted_events = 0
    distribution: Counter[str] = Counter()
    failures: dict[str, str] = {}
    btc_klines = load_market_data(database_path, "BTCUSDT", "15m")

    for symbol in symbols:
        try:
            print(f"[detect] {symbol}")
            symbol_klines = load_market_data(database_path, symbol, "15m")
            symbol_events: list[dict[str, Any]] = []
            for detector in detectors:
                events = detector.detect(symbol, symbol_klines, btc_klines)
                symbol_events.extend(events)
                distribution.update(event["event_type"] for event in events)
            inserted_events += insert_events(database_path, symbol_events)
            print(f"[detect] {symbol} produced {len(symbol_events)} raw events")
        except Exception as exc:  # noqa: BLE001
            failures[symbol] = str(exc)
            print(f"[detect] {symbol} failed: {exc}")

    return DetectResult(
        inserted_events=inserted_events,
        distribution=dict(distribution),
        failures=failures,
    )


def analyze_events(*, database_path: str) -> AnalyzeResult:
    init_db(database_path)
    feature_rows: list[dict[str, Any]] = []
    outcome_rows: list[dict[str, Any]] = []
    btc_klines = load_market_data(database_path, "BTCUSDT", "1m")

    for event in list_events_without_features(database_path):
        symbol_klines = load_market_data(database_path, event["symbol"], "1m")
        feature_rows.extend(extract_event_features(event, symbol_klines, btc_klines))

    for event in list_events_without_outcomes(database_path):
        symbol_klines = load_market_data(database_path, event["symbol"], "1m")
        outcome = calculate_event_outcome(event, symbol_klines)
        if outcome is not None:
            outcome_rows.append(outcome)

    inserted_features = insert_features(database_path, feature_rows)
    inserted_outcomes = insert_outcomes(database_path, outcome_rows)
    print(f"[analyze] inserted features={inserted_features}, outcomes={inserted_outcomes}")
    return AnalyzeResult(inserted_features=inserted_features, inserted_outcomes=inserted_outcomes)


def run_pipeline(
    symbols: list[str],
    days: int,
    *,
    database_path: str,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    fetch_1m = fetch_market_data(symbols, "1m", days, database_path=database_path, config=config)
    fetch_15m = fetch_market_data(symbols, "15m", days, database_path=database_path, config=config)
    detect = detect_events(symbols, ["all"], database_path=database_path)
    analyze = analyze_events(database_path=database_path)
    return {
        "fetch_1m_rows": fetch_1m.inserted_rows,
        "fetch_15m_rows": fetch_15m.inserted_rows,
        "events_inserted": detect.inserted_events,
        "distribution": count_events_by_type(database_path),
        "features_inserted": analyze.inserted_features,
        "outcomes_inserted": analyze.inserted_outcomes,
        "failures": {
            "fetch_1m": fetch_1m.failures,
            "fetch_15m": fetch_15m.failures,
            "detect": detect.failures,
        },
    }


def render_report(limit: int, *, database_path: str) -> str:
    rows = fetch_event_report(database_path, limit)
    headers = ("symbol", "type", "score", "outcome", "triggered_at")
    table_rows = [
        (
            row["symbol"],
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
        " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)),
        "-+-".join("-" * width for width in widths),
    ]
    for row in table_rows:
        lines.append(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(lines)
