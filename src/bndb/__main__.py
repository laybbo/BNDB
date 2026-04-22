"""Command-line entry point for BNDB."""

from bndb.config import AppConfig


def main() -> None:
    config = AppConfig()
    print(
        f"BNDB scaffold ready. Database path: {config.database_path}. "
        f"Binance base URL: {config.binance_base_url}"
    )


if __name__ == "__main__":
    main()

