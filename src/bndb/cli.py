"""Command-line interface for BNDB."""

from __future__ import annotations

import argparse

from bndb import __version__
from bndb.config import AppConfig
from bndb.db import init_db, list_watchlist
from bndb.pipeline import analyze_events, detect_events, fetch_market_data, render_report, run_pipeline
from bndb.watchlist import fetch_gainers_watchlist, init_watchlist, sync_watchlist


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
    detect_parser.add_argument("--interval", default=config.default_interval)

    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--interval", default=config.default_interval)

    run_parser = subparsers.add_parser("run")
    _add_common_market_args(run_parser, config)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--limit", type=int, default=50)

    watchlist_parser = subparsers.add_parser("watchlist")
    watchlist_subparsers = watchlist_parser.add_subparsers(dest="watchlist_command", required=True)
    watchlist_add = watchlist_subparsers.add_parser("add")
    watchlist_add.add_argument("--symbol", required=True)
    watchlist_add.add_argument("--category", default="c")
    watchlist_add.add_argument("--source", default="manual")
    watchlist_fetch = watchlist_subparsers.add_parser("fetch-gainers")
    watchlist_fetch.add_argument("--top-n", type=int, default=50)
    watchlist_fetch.add_argument("--min-volume", type=float, default=1_000_000)
    watchlist_subparsers.add_parser("list")
    watchlist_sync = watchlist_subparsers.add_parser("sync")
    watchlist_sync.add_argument("--top-gainers", type=int, default=config.top_gainers_limit)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    init_db(args.db)
    config = AppConfig(database_path=args.db)

    if args.command == "fetch":
        result = fetch_market_data(
            _parse_csv(args.symbols),
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
        result = detect_events(
            _parse_csv(args.symbols),
            _parse_csv(args.detectors),
            database_path=args.db,
            interval=args.interval,
        )
        print(f"Inserted events: {result.inserted_events}")
        print(f"Distribution: {result.distribution}")
        if result.failures:
            print(f"Failures: {result.failures}")
        return

    if args.command == "analyze":
        result = analyze_events(database_path=args.db, interval=args.interval, config=config)
        print(f"Inserted features: {result.inserted_features}")
        print(f"Inserted outcomes: {result.inserted_outcomes}")
        return

    if args.command == "run":
        summary = run_pipeline(
            _parse_csv(args.symbols),
            args.days,
            database_path=args.db,
            interval=args.interval,
            config=config,
        )
        print("Pipeline summary:")
        print(summary)
        return

    if args.command == "report":
        print(render_report(args.limit, database_path=args.db))
        return

    if args.command == "watchlist":
        if args.watchlist_command == "add":
            inserted = init_watchlist(
                args.db,
                [{"symbol": args.symbol, "category": args.category, "source": args.source}],
            )
            print(f"Watchlist upserts: {inserted}")
            return
        if args.watchlist_command == "list":
            for entry in list_watchlist(args.db):
                print(f"{entry['symbol']} [WL-{entry['category']}] {entry['source']}")
            return
        if args.watchlist_command == "fetch-gainers":
            symbols = fetch_gainers_watchlist(
                args.db,
                top_n=args.top_n,
                min_volume=args.min_volume,
                config=config,
            )
            print(f"Fetched gainers: {len(symbols)}")
            if symbols:
                print(",".join(symbols))
            return
        if args.watchlist_command == "sync":
            inserted = sync_watchlist(
                args.db,
                config=AppConfig(database_path=args.db, top_gainers_limit=args.top_gainers),
            )
            print(f"Watchlist upserts: {inserted}")
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
