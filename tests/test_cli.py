from __future__ import annotations

from pathlib import Path

from bndb.cli import build_parser, main
from bndb.db import init_db, insert_events
from bndb.watchlist import add_watchlist_symbols


def test_build_parser_supports_expected_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    assert "fetch" in help_text
    assert "detect" in help_text
    assert "analyze" in help_text
    assert "run" in help_text
    assert "report" in help_text


def test_report_command_prints_table(tmp_path: Path, monkeypatch, capsys) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)
    add_watchlist_symbols(str(database_path), ["BTCUSDT"], category="a")
    insert_events(
        database_path,
        [
            {
                "symbol": "BTCUSDT",
                "event_type": "price_shock",
                "triggered_at": "2024-01-01T00:00:00Z",
                "score": 88.0,
                "trigger_detail": {"price_change_pct": 4.0},
            }
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        ["bndb", "--db", str(database_path), "report", "--limit", "5"],
    )
    main()

    output = capsys.readouterr().out
    assert "detectors:" in output
    assert "BTCUSDT [WL-a]" in output
