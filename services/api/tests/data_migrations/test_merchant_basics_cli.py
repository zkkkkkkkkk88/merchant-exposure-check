from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.data_migrations.merchant_basics import export_sqlite_package, load_package
from app.db.base import Base
from app.merchants.models import Merchant, MerchantLocalContext, MerchantProfileFact, MerchantSource
from scripts import export_merchant_basics, import_merchant_basics


MERCHANT_ONE = "11111111-1111-4111-8111-111111111111"
MERCHANT_TWO = "22222222-2222-4222-8222-222222222222"
TIMESTAMP = "2026-08-21T12:34:56+00:00"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def create_source_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE merchants (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT NOT NULL,
                branch_name TEXT, city TEXT NOT NULL, district TEXT, industry TEXT NOT NULL,
                address TEXT, price_range TEXT, opening_hours TEXT, products TEXT NOT NULL,
                strengths TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE merchant_sources (
                id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, kind TEXT NOT NULL, url TEXT NOT NULL,
                is_verified INTEGER NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE merchant_profile_facts (
                id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, field_key TEXT NOT NULL, value TEXT NOT NULL,
                confirmation_status TEXT NOT NULL, confidence REAL, source_urls TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE merchant_local_contexts (
                merchant_id TEXT PRIMARY KEY, status TEXT NOT NULL, province TEXT, city TEXT, county TEXT,
                township TEXT, normalized_address TEXT, landmarks TEXT NOT NULL,
                transport_options TEXT NOT NULL, source_urls TEXT NOT NULL, raw_summary TEXT,
                error_message TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO merchants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (MERCHANT_ONE, "Fixture One", "fixture one", None, "Shanghai", None, "restaurant", None, None, None, '["product"]', '["strength"]', TIMESTAMP, TIMESTAMP),
                (MERCHANT_TWO, "Fixture Two", "fixture two", None, "Shanghai", None, "restaurant", None, None, None, '[]', '[]', TIMESTAMP, TIMESTAMP),
            ],
        )
        connection.execute(
            "INSERT INTO merchant_sources VALUES (?, ?, ?, ?, ?, ?)",
            ("33333333-3333-4333-8333-333333333333", MERCHANT_ONE, "official", "https://example.test", 1, TIMESTAMP),
        )
        connection.executemany(
            "INSERT INTO merchant_profile_facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (f"00000000-0000-4000-8000-{index:012d}", MERCHANT_ONE if index <= 7 else MERCHANT_TWO, f"field-{index}", json.dumps({"value": index}), "confirmed", 0.9, '["https://example.test/fact"]', TIMESTAMP, TIMESTAMP)
                for index in range(1, 14)
            ],
        )
        connection.executemany(
            "INSERT INTO merchant_local_contexts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (MERCHANT_ONE, "complete", None, "Shanghai", None, None, None, '[]', '[]', '[]', None, None, TIMESTAMP, TIMESTAMP),
                (MERCHANT_TWO, "complete", None, "Shanghai", None, None, None, '[]', '[]', '[]', None, None, TIMESTAMP, TIMESTAMP),
            ],
        )


def create_target_database(path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(
        engine,
        tables=[
            Merchant.__table__,
            MerchantSource.__table__,
            MerchantProfileFact.__table__,
            MerchantLocalContext.__table__,
        ],
    )
    return database_url


def test_export_cli_writes_exact_merchant_basics_counts(tmp_path: Path, monkeypatch, capsys) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "merchant-basics.json"
    create_source_database(source)
    monkeypatch.setenv("DATABASE_URL", "not-a-database-url")

    assert export_merchant_basics.main([str(source), str(destination)]) == 0

    assert destination.is_file()
    assert capsys.readouterr().out.strip() == (
        "EXPORT OK merchants=2 merchant_sources=1 merchant_profile_facts=13 "
        "merchant_local_contexts=2"
    )


def test_import_cli_dry_run_validates_the_package_without_writing(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    source = tmp_path / "source.db"
    package = tmp_path / "merchant-basics.json"
    target = tmp_path / "target.db"
    create_source_database(source)
    export_sqlite_package(source, package)
    monkeypatch.setenv("DATABASE_URL", create_target_database(target))
    get_settings.cache_clear()

    assert import_merchant_basics.main([str(package), "--dry-run"]) == 0

    assert capsys.readouterr().out.strip() == (
        "VALIDATION OK merchants=2 merchant_sources=1 merchant_profile_facts=13 "
        "merchant_local_contexts=2"
    )
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    with Session(create_engine(create_target_database(target))) as session:
        assert session.scalar(select(func.count()).select_from(Merchant)) == 0


def test_import_cli_reports_a_malformed_package_concisely(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    package = tmp_path / "malformed.json"
    package.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", create_target_database(tmp_path / "target.db"))
    get_settings.cache_clear()

    assert import_merchant_basics.main([str(package)]) == 1

    assert capsys.readouterr().out.strip().startswith("ERROR: package keys are invalid")


def test_import_cli_refuses_a_non_empty_target_concisely(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    source = tmp_path / "source.db"
    package_path = tmp_path / "merchant-basics.json"
    target = tmp_path / "target.db"
    create_source_database(source)
    export_sqlite_package(source, package_path)
    database_url = create_target_database(target)
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    from app.data_migrations.merchant_basics import import_package

    import_package(create_engine(database_url), load_package(package_path))

    assert import_merchant_basics.main([str(package_path)]) == 1

    assert capsys.readouterr().out.strip() == "ERROR: target table merchants is not empty"
