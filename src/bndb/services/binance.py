"""Helpers for talking to the Binance API."""

from __future__ import annotations

from typing import Any

import requests

from bndb.config import AppConfig


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "bndb/0.1.0"})
    return session


def ping(config: AppConfig | None = None, session: requests.Session | None = None) -> dict[str, Any]:
    app_config = config or AppConfig()
    http = session or build_session()
    response = http.get(f"{app_config.binance_base_url}/api/v3/ping", timeout=10)
    response.raise_for_status()
    return response.json() if response.content else {}

