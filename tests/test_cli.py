from __future__ import annotations

from pathlib import Path

from bndb.cli import build_parser, main
from bndb.db import init_db, insert_events
from bndb.watchlist import init_watchlist


def test_build_parser_supports_expected_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    assert "fetch" in help_text
    assert "detect" in help_text
    assert "analyze" in help_text
    assert "run" in help_text
    assert "report" in help_text
    assert "watchlist" in help_text
    watchlist_action = next(
        action for action in parser._actions if getattr(action, "dest", None) == "command"
    )
    watchlist_parser = watchlist_action.choices["watchlist"]
    assert "fetch-gainers" in watchlist_parser.format_help()


def test_report_command_prints_watchlist_marker(tmp_path: Path, monkeypatch, capsys) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)
    init_watchlist(str(database_path), [{"symbol": "BTCUSDT", "category": "a", "source": "manual"}])
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
    assert "BNDB Report" in output
    assert "BTCUSDT [WL-a]" in output


def test_watchlist_fetch_gainers_command(tmp_path: Path, monkeypatch, capsys) -> None:
    database_path = tmp_path / "bndb.db"
    init_db(database_path)

    monkeypatch.setattr(
        "bndb.cli.fetch_gainers_watchlist",
        lambda *args, **kwargs: ["AAAUSDT", "BBBUSDT"],
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "bndb",
            "--db",
            str(database_path),
            "watchlist",
            "fetch-gainers",
            "--top-n",
            "2",
            "--min-volume",
            "1000000",
        ],
    )
    main()

    output = capsys.readouterr().out
    assert "Fetched gainers: 2" in output
    assert "AAAUSDT,BBBUSDT" in output
