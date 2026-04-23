"""Helpers for talking to the Binance Futures API."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import requests

from bndb.config import AppConfig


INTERVAL_TO_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
}


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "bndb/0.1.0"})
    return session


def fetch_klines(
    symbol: str,
    interval: str,
    days: int,
    *,
    config: AppConfig | None = None,
    session: requests.Session | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> list[dict[str, Any]]:
    app_config = config or AppConfig()
    http = session or build_session()
    interval_ms = interval_to_minutes(interval) * 60 * 1000
    end_time = end_ms or int(datetime.now(tz=UTC).timestamp() * 1000)
    default_start = end_time - days * 24 * 60 * 60 * 1000
    next_start = start_ms or default_start
    rows: list[dict[str, Any]] = []

    while next_start < end_time:
        response = http.get(
            f"{app_config.binance_base_url}/fapi/v1/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": next_start,
                "endTime": end_time,
                "limit": 1500,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload:
            break

        rows.extend(_normalize_klines(payload, symbol, interval))
        last_open_ms = int(payload[-1][0])
        next_start = last_open_ms + interval_ms
        sleep_fn(app_config.request_pause_seconds)
        if len(payload) < 1500:
            break

    return rows


def next_start_from_latest_open_time(latest_open_time: str | None, interval: str) -> int | None:
    if latest_open_time is None:
        return None
    latest_dt = datetime.fromisoformat(latest_open_time.replace("Z", "+00:00"))
    return int((latest_dt + timedelta(minutes=interval_to_minutes(interval))).timestamp() * 1000)


def interval_to_minutes(interval: str) -> int:
    try:
        return INTERVAL_TO_MINUTES[interval]
    except KeyError as exc:
        raise ValueError(f"unsupported interval: {interval}") from exc


def _normalize_klines(payload: list[list[Any]], symbol: str, interval: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in payload:
        rows.append(
            {
                "symbol": symbol,
                "interval": interval,
                "open_time": datetime.fromtimestamp(entry[0] / 1000, tz=UTC)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
                "open": float(entry[1]),
                "high": float(entry[2]),
                "low": float(entry[3]),
                "close": float(entry[4]),
                "volume": float(entry[5]),
                "quote_volume": float(entry[7]),
                "trades_count": int(entry[8]),
                "taker_buy_quote_volume": float(entry[10]),
            }
        )
    return rows
