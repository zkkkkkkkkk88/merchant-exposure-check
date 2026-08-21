from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

import app.data_migrations.merchant_basics as merchant_basics
from app.data_migrations.merchant_basics import (
    EXPECTED_COUNTS,
    MerchantBasicsPackage,
    TargetNotEmptyError,
    import_package,
)
from app.db.base import Base
from app.merchants.models import Merchant, MerchantLocalContext, MerchantProfileFact, MerchantSource


MERCHANT_ONE = "11111111-1111-4111-8111-111111111111"
MERCHANT_TWO = "22222222-2222-4222-8222-222222222222"
TIMESTAMP = "2026-08-21T12:34:56+00:00"


@pytest.fixture
def engine() -> Engine:
    target = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        target,
        tables=[
            Merchant.__table__,
            MerchantSource.__table__,
            MerchantProfileFact.__table__,
            MerchantLocalContext.__table__,
        ],
    )
    return target


@pytest.fixture
def package() -> MerchantBasicsPackage:
    return MerchantBasicsPackage(
        format_version=1,
        exported_at=TIMESTAMP,
        counts=dict(EXPECTED_COUNTS),
        tables={
            "merchants": [
                {
                    "id": MERCHANT_ONE,
                    "name": "Fixture One",
                    "normalized_name": "fixture one",
                    "branch_name": None,
                    "city": "Shanghai",
                    "district": None,
                    "industry": "restaurant",
                    "address": None,
                    "price_range": None,
                    "opening_hours": None,
                    "products": ["fixture-product"],
                    "strengths": ["fixture-strength"],
                    "created_at": TIMESTAMP,
                    "updated_at": TIMESTAMP,
                },
                {
                    "id": MERCHANT_TWO,
                    "name": "Fixture Two",
                    "normalized_name": "fixture two",
                    "branch_name": "Second branch",
                    "city": "Shanghai",
                    "district": "Huangpu",
                    "industry": "restaurant",
                    "address": "2 Fixture Road",
                    "price_range": "$$",
                    "opening_hours": "09:00-21:00",
                    "products": ["second-product"],
                    "strengths": [],
                    "created_at": TIMESTAMP,
                    "updated_at": TIMESTAMP,
                },
            ],
            "merchant_sources": [
                {
                    "id": "33333333-3333-4333-8333-333333333333",
                    "merchant_id": MERCHANT_ONE,
                    "kind": "official",
                    "url": "https://example.test",
                    "is_verified": True,
                    "created_at": TIMESTAMP,
                }
            ],
            "merchant_profile_facts": [
                {
                    "id": f"00000000-0000-4000-8000-{index:012d}",
                    "merchant_id": MERCHANT_ONE if index <= 7 else MERCHANT_TWO,
                    "field_key": f"field-{index}",
                    "value": {"value": index},
                    "confirmation_status": "confirmed",
                    "confidence": None if index == 1 else 0.9,
                    "source_urls": ["https://example.test/fact"],
                    "created_at": TIMESTAMP,
                    "updated_at": TIMESTAMP,
                }
                for index in range(1, 14)
            ],
            "merchant_local_contexts": [
                {
                    "merchant_id": MERCHANT_ONE,
                    "status": "complete",
                    "province": None,
                    "city": "Shanghai",
                    "county": None,
                    "township": None,
                    "normalized_address": None,
                    "landmarks": ["Fixture landmark"],
                    "transport_options": ["metro"],
                    "source_urls": ["https://example.test/context"],
                    "raw_summary": None,
                    "error_message": None,
                    "created_at": TIMESTAMP,
                    "updated_at": TIMESTAMP,
                },
                {
                    "merchant_id": MERCHANT_TWO,
                    "status": "pending",
                    "province": "Shanghai",
                    "city": "Shanghai",
                    "county": "Huangpu",
                    "township": None,
                    "normalized_address": "2 fixture road",
                    "landmarks": [],
                    "transport_options": [],
                    "source_urls": [],
                    "raw_summary": "Pending review",
                    "error_message": None,
                    "created_at": TIMESTAMP,
                    "updated_at": TIMESTAMP,
                },
            ],
        },
    )


def count_rows(engine: Engine) -> dict[str, int]:
    models = {
        "merchants": Merchant,
        "merchant_sources": MerchantSource,
        "merchant_profile_facts": MerchantProfileFact,
        "merchant_local_contexts": MerchantLocalContext,
    }
    with engine.connect() as connection:
        return {
            table: connection.scalar(select(func.count()).select_from(model)) or 0
            for table, model in models.items()
        }


def test_import_package_inserts_the_complete_validated_package(
    engine: Engine, package: MerchantBasicsPackage
) -> None:
    assert import_package(engine, package) == EXPECTED_COUNTS
    assert count_rows(engine) == EXPECTED_COUNTS


def test_import_package_checks_the_target_in_the_same_transaction_as_its_inserts(
    engine: Engine, package: MerchantBasicsPackage
) -> None:
    statements: list[tuple[int, str]] = []

    def record_statement(
        connection, cursor, statement, parameters, context, executemany
    ) -> None:
        if statement.startswith("SELECT count") or statement.startswith("INSERT INTO"):
            statements.append((id(connection), statement))

    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        import_package(engine, package)
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)

    count_connection_ids = {
        connection_id for connection_id, statement in statements if statement.startswith("SELECT count")
    }
    insert_connection_ids = {
        connection_id for connection_id, statement in statements if statement.startswith("INSERT INTO")
    }
    assert count_connection_ids == insert_connection_ids
    assert len(count_connection_ids) == 1


def test_import_package_locks_postgresql_target_tables_before_counting(
    monkeypatch: pytest.MonkeyPatch, package: MerchantBasicsPackage
) -> None:
    events: list[tuple[str, str]] = []

    class RecordingConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def scalar(self, statement):
            events.append(("count", str(statement)))
            return 0

    class RecordingEngine:
        def connect(self) -> RecordingConnection:
            return RecordingConnection()

    class RecordingPostgresSession:
        def __init__(self, engine) -> None:
            self.engine = engine

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            return None

        def begin(self):
            return self

        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def execute(self, statement) -> None:
            events.append(("lock", str(statement)))

        def scalar(self, statement):
            events.append(("count", str(statement)))
            return 0

    monkeypatch.setattr(merchant_basics, "Session", RecordingPostgresSession)

    assert import_package(RecordingEngine(), package, dry_run=True) == EXPECTED_COUNTS
    assert events[0] == (
        "lock",
        "LOCK TABLE merchants, merchant_sources, merchant_profile_facts, "
        "merchant_local_contexts IN SHARE ROW EXCLUSIVE MODE",
    )
    assert [event_name for event_name, _ in events[1:]] == ["count"] * 4


def test_import_package_refuses_a_non_empty_target_without_changing_it(
    engine: Engine, package: MerchantBasicsPackage
) -> None:
    with engine.begin() as connection:
        connection.execute(
            Merchant.__table__.insert().values(
                id=UUID(MERCHANT_ONE),
                name="Existing merchant",
                normalized_name="existing merchant",
                city="Shanghai",
                industry="restaurant",
                products=[],
                strengths=[],
                created_at=datetime(2026, 8, 21, tzinfo=UTC),
                updated_at=datetime(2026, 8, 21, tzinfo=UTC),
            )
        )

    with pytest.raises(TargetNotEmptyError):
        import_package(engine, package)

    assert count_rows(engine) == {
        "merchants": 1,
        "merchant_sources": 0,
        "merchant_profile_facts": 0,
        "merchant_local_contexts": 0,
    }


def test_import_package_rolls_back_every_table_when_profile_fact_uniqueness_fails(
    engine: Engine, package: MerchantBasicsPackage
) -> None:
    invalid_tables = deepcopy(package.tables)
    invalid_tables["merchant_profile_facts"][1]["field_key"] = invalid_tables[
        "merchant_profile_facts"
    ][0]["field_key"]
    duplicate_fact_package = MerchantBasicsPackage(
        format_version=package.format_version,
        exported_at=package.exported_at,
        counts=package.counts,
        tables=invalid_tables,
    )

    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        import_package(engine, duplicate_fact_package)

    assert count_rows(engine) == {table: 0 for table in EXPECTED_COUNTS}


def test_import_package_dry_run_returns_counts_without_writing(
    engine: Engine, package: MerchantBasicsPackage
) -> None:
    assert import_package(engine, package, dry_run=True) == EXPECTED_COUNTS
    assert count_rows(engine) == {table: 0 for table in EXPECTED_COUNTS}
