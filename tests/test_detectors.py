from __future__ import annotations

from bndb.definitions.rules import load_thresholds, price_shock_signal, relative_strength_signal, volume_shock_signal


def test_rule_functions_trigger_on_strong_moves() -> None:
    thresholds = load_thresholds()
    btc_rows = _rows(100.0, strong=False)
    eth_rows = _rows(80.0, strong=True)

    price_signal = price_shock_signal(eth_rows, 60, interval="5m", thresholds=thresholds)
    volume_signal = volume_shock_signal(eth_rows, 60, interval="5m", thresholds=thresholds)
    rs_signal = relative_strength_signal(eth_rows, btc_rows, 60, interval="5m", thresholds=thresholds)

    assert price_signal is not None
    assert volume_signal is not None
    assert rs_signal is not None


def _rows(start: float, *, strong: bool) -> list[dict[str, float | str]]:
    rows = []
    price = start
    for index in range(80):
        drift = 0.05 if strong else 0.01
        spike = 2.5 if strong and index == 60 else 0.0
        open_price = price
        close_price = price + drift + spike
        rows.append(
            {
                "open_time": f"2024-01-01T{index:02d}:00:00Z",
                "open": open_price,
                "high": close_price + (0.4 if spike else 0.05),
                "low": open_price - 0.05,
                "close": close_price,
                "volume": 5000.0 if spike else 1000.0,
            }
        )
        price = close_price
    return rows
