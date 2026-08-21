from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from app.data_migrations.merchant_basics import (
    EXPECTED_COUNTS,
    TABLE_ORDER,
    export_sqlite_package,
    validate_package,
)


MERCHANT_ONE = "11111111-1111-4111-8111-111111111111"
MERCHANT_TWO = "22222222-2222-4222-8222-222222222222"
SOURCE_ID = "33333333-3333-4333-8333-333333333333"
FACT_IDS = [f"00000000-0000-4000-8000-{number:012d}" for number in range(1, 14)]
TIMESTAMP = "2026-08-21T12:34:56+00:00"


def create_source_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE merchants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                branch_name TEXT,
                city TEXT NOT NULL,
                district TEXT,
                industry TEXT NOT NULL,
                address TEXT,
                price_range TEXT,
                opening_hours TEXT,
                products TEXT NOT NULL,
                strengths TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE merchant_sources (
                id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                url TEXT NOT NULL,
                is_verified INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE merchant_profile_facts (
                id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                field_key TEXT NOT NULL,
                value TEXT NOT NULL,
                confirmation_status TEXT NOT NULL,
                confidence REAL,
                source_urls TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE merchant_local_contexts (
                merchant_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                province TEXT,
                city TEXT,
                county TEXT,
                township TEXT,
                normalized_address TEXT,
                landmarks TEXT NOT NULL,
                transport_options TEXT NOT NULL,
                source_urls TEXT NOT NULL,
                raw_summary TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE scan_runs (id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL);
            """
        )
        connection.executemany(
            """
            INSERT INTO merchants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    MERCHANT_ONE,
                    "Fixture One",
                    "fixture one",
                    None,
                    "Shanghai",
                    None,
                    "restaurant",
                    None,
                    None,
                    None,
                    '["fixture-product"]',
                    '["fixture-strength"]',
                    TIMESTAMP,
                    TIMESTAMP,
                ),
                (
                    MERCHANT_TWO,
                    "Fixture Two",
                    "fixture two",
                    "Second branch",
                    "Shanghai",
                    "Huangpu",
                    "restaurant",
                    "2 Fixture Road",
                    "$$",
                    "09:00-21:00",
                    '["second-product"]',
                    '[]',
                    TIMESTAMP,
                    TIMESTAMP,
                ),
            ],
        )
        connection.execute(
            """
            INSERT INTO merchant_sources VALUES (?, ?, ?, ?, ?, ?)
            """,
            (SOURCE_ID, MERCHANT_ONE, "official", "https://example.test", 1, TIMESTAMP),
        )
        connection.executemany(
            """
            INSERT INTO merchant_profile_facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    fact_id,
                    MERCHANT_ONE if index < 7 else MERCHANT_TWO,
                    f"field-{index}",
                    json.dumps({"value": index}),
                    "confirmed",
                    0.9 if index else None,
                    '["https://example.test/fact"]',
                    TIMESTAMP,
                    TIMESTAMP,
                )
                for index, fact_id in enumerate(FACT_IDS)
            ],
        )
        connection.executemany(
            """
            INSERT INTO merchant_local_contexts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    MERCHANT_ONE,
                    "complete",
                    None,
                    "Shanghai",
                    None,
                    None,
                    None,
                    '["Fixture landmark"]',
                    '["metro"]',
                    '["https://example.test/context"]',
                    None,
                    None,
                    TIMESTAMP,
                    TIMESTAMP,
                ),
                (
                    MERCHANT_TWO,
                    "pending",
                    "Shanghai",
                    "Shanghai",
                    "Huangpu",
                    None,
                    "2 fixture road",
                    '[]',
                    '[]',
                    '[]',
                    "Pending review",
                    None,
                    TIMESTAMP,
                    TIMESTAMP,
                ),
            ],
        )
        connection.execute("INSERT INTO scan_runs VALUES (?, ?)", ("scan-1", MERCHANT_ONE))


@pytest.fixture
def exported_payload(tmp_path: Path) -> dict[str, object]:
    source_path = tmp_path / "source.db"
    package_path = tmp_path / "merchant-basics.json"
    create_source_database(source_path)
    export_sqlite_package(source_path, package_path)
    return json.loads(package_path.read_text(encoding="utf-8"))


def test_export_includes_only_approved_tables_and_preserves_values(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    package_path = tmp_path / "merchant-basics.json"
    create_source_database(source_path)

    counts = export_sqlite_package(source_path, package_path)

    assert counts == {
        "merchants": 2,
        "merchant_sources": 1,
        "merchant_profile_facts": 13,
        "merchant_local_contexts": 2,
    }
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    assert set(payload["tables"]) == set(TABLE_ORDER)
    assert "scan_runs" not in payload["tables"]
    assert payload["counts"] == counts
    assert payload["tables"]["merchants"][0]["products"] == ["fixture-product"]
    assert payload["tables"]["merchants"][0]["branch_name"] is None
    assert payload["tables"]["merchant_sources"][0]["is_verified"] is True
    assert payload["tables"]["merchant_profile_facts"][0]["value"] == {"value": 0}
    assert payload["tables"]["merchant_profile_facts"][0]["confidence"] is None
    assert payload["tables"]["merchant_local_contexts"][0]["landmarks"] == ["Fixture landmark"]


def test_validate_package_rejects_unexpected_table(exported_payload: dict[str, object]) -> None:
    payload = deepcopy(exported_payload)
    payload["tables"]["scan_runs"] = []

    with pytest.raises(ValueError, match="tables"):
        validate_package(payload)


def test_validate_package_rejects_missing_required_field(exported_payload: dict[str, object]) -> None:
    payload = deepcopy(exported_payload)
    del payload["tables"]["merchants"][0]["name"]

    with pytest.raises(ValueError, match="name"):
        validate_package(payload)


def test_validate_package_rejects_invalid_uuid(exported_payload: dict[str, object]) -> None:
    payload = deepcopy(exported_payload)
    payload["tables"]["merchants"][0]["id"] = "not-a-uuid"

    with pytest.raises(ValueError, match="UUID"):
        validate_package(payload)


def test_validate_package_rejects_broken_merchant_foreign_key(
    exported_payload: dict[str, object],
) -> None:
    payload = deepcopy(exported_payload)
    payload["tables"]["merchant_sources"][0]["merchant_id"] = (
        "99999999-9999-4999-8999-999999999999"
    )

    with pytest.raises(ValueError, match="merchant_id"):
        validate_package(payload)


def test_validate_package_rejects_unapproved_counts(exported_payload: dict[str, object]) -> None:
    payload = deepcopy(exported_payload)
    payload["counts"] = {**EXPECTED_COUNTS, "merchant_profile_facts": 12}

    with pytest.raises(ValueError, match="counts"):
        validate_package(payload)


def test_export_rejects_malformed_sqlite_boolean_value(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    package_path = tmp_path / "merchant-basics.json"
    create_source_database(source_path)
    with sqlite3.connect(source_path) as connection:
        connection.execute("UPDATE merchant_sources SET is_verified = 2")

    with pytest.raises(ValueError, match="is_verified.*0 or 1"):
        export_sqlite_package(source_path, package_path)
