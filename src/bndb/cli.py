"""Command-line interface for BNDB."""

from __future__ import annotations

import argparse

from bndb import __version__
from bndb.config import AppConfig, parse_symbols
from bndb.pipeline import analyze_events, detect_events, fetch_market_data, render_report, run_pipeline
from bndb.db import init_db


def build_parser() -> argparse.ArgumentParser:
    config = AppConfig()
    parser = argparse.ArgumentParser(prog="bndb")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--db", default=str(config.database_path))
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    _add_common_market_args(fetch_parser, config)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument("--symbols", default=",".join(config.default_symbols))
    detect_parser.add_argument("--detectors", default="all")

    subparsers.add_parser("analyze")

    run_parser = subparsers.add_parser("run")
    _add_common_market_args(run_parser, config)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--limit", type=int, default=50)
    return parser


def main() -> None:
    parser = build_parser()
    config = AppConfig()
    args = parser.parse_args()
    init_db(args.db)

    if args.command == "fetch":
        result = fetch_market_data(
            parse_symbols(args.symbols, default_symbols=config.default_symbols),
            args.interval,
            args.days,
            database_path=args.db,
            config=config,
        )
        print(f"Inserted market rows: {result.inserted_rows}")
        if result.failures:
            print(f"Failures: {result.failures}")
        return

    if args.command == "detect":
        detector_names = _parse_csv(args.detectors)
        result = detect_events(
            parse_symbols(args.symbols, default_symbols=config.default_symbols),
            detector_names,
            database_path=args.db,
            interval=config.default_interval,
        )
        print(f"Inserted events: {result.inserted_events}")
        print(f"Distribution: {result.distribution}")
        if result.failures:
            print(f"Failures: {result.failures}")
        return

    if args.command == "analyze":
        result = analyze_events(database_path=args.db, interval=config.default_interval, config=config)
        print(f"Inserted features: {result.inserted_features}")
        print(f"Inserted outcomes: {result.inserted_outcomes}")
        return

    if args.command == "run":
        summary = run_pipeline(
            parse_symbols(args.symbols, default_symbols=config.default_symbols),
            args.interval,
            args.days,
            database_path=args.db,
            config=config,
        )
        print("Pipeline summary:")
        print(summary)
        return

    if args.command == "report":
        print(render_report(args.limit, database_path=args.db))
        return

    parser.error(f"unknown command: {args.command}")


def _add_common_market_args(parser: argparse.ArgumentParser, config: AppConfig) -> None:
    parser.add_argument("--symbols", default=",".join(config.default_symbols))
    parser.add_argument("--interval", default=config.default_interval)
    parser.add_argument("--days", type=int, default=config.default_days)


def _parse_csv(raw: str) -> list[str]:
    if raw == "all":
        return ["all"]
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    return parts or ["all"]
