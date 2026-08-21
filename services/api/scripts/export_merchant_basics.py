from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.data_migrations.merchant_basics import export_sqlite_package


def _format_counts(counts: dict[str, int]) -> str:
    return " ".join(f"{table}={count}" for table, count in counts.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the approved merchant-basics SQLite records."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args(argv)

    try:
        counts = export_sqlite_package(arguments.source, arguments.destination)
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    print(f"EXPORT OK {_format_counts(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
