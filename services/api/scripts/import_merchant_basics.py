from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.data_migrations.merchant_basics import import_package, load_package


def _format_counts(counts: dict[str, int]) -> str:
    return " ".join(f"{table}={count}" for table, count in counts.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate or import one approved merchant-basics package."
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)

    engine = None
    try:
        package = load_package(arguments.package)
        from app.db.session import make_engine

        engine = make_engine(get_settings().database_url)
        counts = import_package(engine, package, dry_run=arguments.dry_run)
    except (OSError, SQLAlchemyError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1
    finally:
        if engine is not None:
            engine.dispose()

    status = "VALIDATION OK" if arguments.dry_run else "IMPORT OK"
    print(f"{status} {_format_counts(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
