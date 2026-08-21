from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.merchants.models import Merchant, MerchantLocalContext, MerchantProfileFact, MerchantSource

TABLE_ORDER = (
    "merchants",
    "merchant_sources",
    "merchant_profile_facts",
    "merchant_local_contexts",
)
EXPECTED_COUNTS = {
    "merchants": 2,
    "merchant_sources": 1,
    "merchant_profile_facts": 13,
    "merchant_local_contexts": 2,
}
JSON_COLUMNS = {
    "merchants": {"products", "strengths"},
    "merchant_profile_facts": {"value", "source_urls"},
    "merchant_local_contexts": {"landmarks", "transport_options", "source_urls"},
}
BOOLEAN_COLUMNS = {"merchant_sources": {"is_verified"}}

FORMAT_VERSION = 1

COLUMNS = {
    "merchants": (
        "id",
        "name",
        "normalized_name",
        "branch_name",
        "city",
        "district",
        "industry",
        "address",
        "price_range",
        "opening_hours",
        "products",
        "strengths",
        "created_at",
        "updated_at",
    ),
    "merchant_sources": ("id", "merchant_id", "kind", "url", "is_verified", "created_at"),
    "merchant_profile_facts": (
        "id",
        "merchant_id",
        "field_key",
        "value",
        "confirmation_status",
        "confidence",
        "source_urls",
        "created_at",
        "updated_at",
    ),
    "merchant_local_contexts": (
        "merchant_id",
        "status",
        "province",
        "city",
        "county",
        "township",
        "normalized_address",
        "landmarks",
        "transport_options",
        "source_urls",
        "raw_summary",
        "error_message",
        "created_at",
        "updated_at",
    ),
}

NULLABLE_STRING_COLUMNS = {
    "merchants": {"branch_name", "district", "address", "price_range", "opening_hours"},
    "merchant_local_contexts": {
        "province",
        "city",
        "county",
        "township",
        "normalized_address",
        "raw_summary",
        "error_message",
    },
}
TIMESTAMP_COLUMNS = {
    "merchants": {"created_at", "updated_at"},
    "merchant_sources": {"created_at"},
    "merchant_profile_facts": {"created_at", "updated_at"},
    "merchant_local_contexts": {"created_at", "updated_at"},
}


@dataclass(frozen=True)
class MerchantBasicsPackage:
    format_version: int
    exported_at: str
    counts: dict[str, int]
    tables: dict[str, list[dict[str, object]]]


class TargetNotEmptyError(ValueError):
    """Raised when a migration target already contains approved-table rows."""


TABLE_MODELS = {
    "merchants": Merchant,
    "merchant_sources": MerchantSource,
    "merchant_profile_facts": MerchantProfileFact,
    "merchant_local_contexts": MerchantLocalContext,
}
POSTGRESQL_TARGET_TABLE_LOCK = (
    "LOCK TABLE merchants, merchant_sources, merchant_profile_facts, merchant_local_contexts "
    "IN SHARE ROW EXCLUSIVE MODE"
)


def parse_uuid(value: str) -> UUID:
    return UUID(value)


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def import_package(
    engine: Engine, package: MerchantBasicsPackage, *, dry_run: bool = False
) -> dict[str, int]:
    """Import one validated merchant-basics package into an empty target."""
    with Session(engine) as session:
        with session.begin():
            _lock_postgresql_target_tables(session)
            _require_empty_target(session)
            if dry_run:
                return dict(package.counts)
            for table in TABLE_ORDER:
                session.add_all(_build_models(table, package.tables[table]))
            session.flush()
    return dict(package.counts)


def _lock_postgresql_target_tables(session: Session) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text(POSTGRESQL_TARGET_TABLE_LOCK))


def _require_empty_target(session: Session) -> None:
    for table in TABLE_ORDER:
        count = session.scalar(select(func.count()).select_from(TABLE_MODELS[table]))
        if count:
            raise TargetNotEmptyError(f"target table {table} is not empty")


def _build_models(table: str, rows: list[dict[str, object]]) -> list[object]:
    model = TABLE_MODELS[table]
    models: list[object] = []
    for row in rows:
        converted = dict(row)
        for column in {"id", "merchant_id"} & converted.keys():
            converted[column] = parse_uuid(cast(str, converted[column]))
        for column in TIMESTAMP_COLUMNS[table]:
            converted[column] = parse_datetime(cast(str, converted[column]))
        models.append(model(**converted))
    return models


def export_sqlite_package(source: Path, destination: Path) -> dict[str, int]:
    """Export the approved merchant-basic records from SQLite atomically."""
    uri = f"file:{source.resolve().as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        tables = {table: _read_table(connection, table) for table in TABLE_ORDER}

    payload = {
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "counts": {table: len(tables[table]) for table in TABLE_ORDER},
        "tables": tables,
    }
    package = validate_package(payload)
    _write_json_atomically(destination, payload)
    return dict(package.counts)


def load_package(path: Path) -> MerchantBasicsPackage:
    """Load a UTF-8 JSON migration package after validating its contents."""
    with path.open(encoding="utf-8") as package_file:
        return validate_package(json.load(package_file))


def validate_package(payload: object) -> MerchantBasicsPackage:
    """Validate the strict, versioned merchant-basics package contract."""
    payload_mapping = _require_mapping(payload, "package")
    _require_exact_keys(payload_mapping, {"format_version", "exported_at", "counts", "tables"}, "package")

    format_version = payload_mapping["format_version"]
    if format_version != FORMAT_VERSION or isinstance(format_version, bool):
        raise ValueError(f"unsupported format_version: {format_version!r}")
    exported_at = _require_timestamp(payload_mapping["exported_at"], "exported_at")
    counts = _validate_counts(payload_mapping["counts"])
    tables = _validate_tables(payload_mapping["tables"], counts)
    _validate_foreign_keys(tables)
    return MerchantBasicsPackage(
        format_version=format_version,
        exported_at=exported_at,
        counts=counts,
        tables=tables,
    )


def _read_table(connection: sqlite3.Connection, table: str) -> list[dict[str, object]]:
    columns = COLUMNS[table]
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    order_column = "id" if "id" in columns else "merchant_id"
    query = f'SELECT {quoted_columns} FROM "{table}" ORDER BY "{order_column}"'
    rows: list[dict[str, object]] = []
    for source_row in connection.execute(query):
        row = dict(source_row)
        for column in JSON_COLUMNS.get(table, set()):
            row[column] = json.loads(row[column])
        for column in BOOLEAN_COLUMNS.get(table, set()):
            row[column] = _decode_sqlite_boolean(row[column], f"{table}.{column}")
        rows.append(row)
    return rows


def _write_json_atomically(destination: Path, payload: Mapping[str, object]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_counts(value: object) -> dict[str, int]:
    counts = _require_mapping(value, "counts")
    _require_exact_keys(counts, set(TABLE_ORDER), "counts")
    validated_counts: dict[str, int] = {}
    for table in TABLE_ORDER:
        count = counts[table]
        if not isinstance(count, int) or isinstance(count, bool) or count != EXPECTED_COUNTS[table]:
            raise ValueError(f"counts for {table} must be {EXPECTED_COUNTS[table]}")
        validated_counts[table] = count
    return validated_counts


def _validate_tables(value: object, counts: Mapping[str, int]) -> dict[str, list[dict[str, object]]]:
    tables = _require_mapping(value, "tables")
    _require_exact_keys(tables, set(TABLE_ORDER), "tables")
    validated_tables: dict[str, list[dict[str, object]]] = {}
    for table in TABLE_ORDER:
        source_rows = tables[table]
        if not isinstance(source_rows, list) or len(source_rows) != counts[table]:
            raise ValueError(f"counts do not match rows for {table}")
        rows = [_validate_row(table, row) for row in source_rows]
        _validate_unique_identifiers(table, rows)
        validated_tables[table] = rows
    return validated_tables


def _validate_row(table: str, value: object) -> dict[str, object]:
    row = _require_mapping(value, f"{table} row")
    expected_columns = set(COLUMNS[table])
    _require_exact_keys(row, expected_columns, f"{table} row")
    validated = dict(row)

    identifier_columns = {"merchant_id"} if table == "merchant_local_contexts" else {"id"}
    if table != "merchants":
        identifier_columns.add("merchant_id")
    for column in identifier_columns:
        validated[column] = _require_uuid(validated[column], f"{table}.{column}")
    for column in TIMESTAMP_COLUMNS[table]:
        validated[column] = _require_timestamp(validated[column], f"{table}.{column}")
    for column in BOOLEAN_COLUMNS.get(table, set()):
        if not isinstance(validated[column], bool):
            raise ValueError(f"{table}.{column} must be a boolean")
    for column in JSON_COLUMNS.get(table, set()):
        _validate_json_column(table, column, validated[column])
    if table == "merchant_profile_facts":
        confidence = validated["confidence"]
        if confidence is not None and (
            not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
        ):
            raise ValueError("merchant_profile_facts.confidence must be a number or null")
    for column in COLUMNS[table]:
        if column in identifier_columns | TIMESTAMP_COLUMNS[table] | JSON_COLUMNS.get(table, set()):
            continue
        if column in BOOLEAN_COLUMNS.get(table, set()) or column == "confidence":
            continue
        _require_string_or_null(
            validated[column],
            f"{table}.{column}",
            nullable=column in NULLABLE_STRING_COLUMNS.get(table, set()),
        )
    return validated


def _validate_foreign_keys(tables: Mapping[str, list[dict[str, object]]]) -> None:
    merchant_ids = {row["id"] for row in tables["merchants"]}
    for table in TABLE_ORDER[1:]:
        for row in tables[table]:
            if row["merchant_id"] not in merchant_ids:
                raise ValueError(f"{table}.merchant_id does not reference an exported merchant")


def _validate_unique_identifiers(table: str, rows: list[dict[str, object]]) -> None:
    identity_column = "merchant_id" if table == "merchant_local_contexts" else "id"
    identifiers = [row[identity_column] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{table} contains duplicate {identity_column} values")


def _validate_json_column(table: str, column: str, value: object) -> None:
    if column == "value" and table == "merchant_profile_facts":
        if not _is_json_value(value):
            raise ValueError(f"{table}.{column} must be JSON")
        return
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{table}.{column} must be a JSON array of strings")


def _decode_sqlite_boolean(value: object, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if type(value) is int and value in {0, 1}:
        return bool(value)
    raise ValueError(f"{name} must be SQLite 0 or 1 (or a boolean)")


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{name} must be an object")
    return value


def _require_exact_keys(value: Mapping[str, object], expected: set[str], name: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ValueError(f"{name} keys are invalid; missing={missing}, unexpected={unexpected}")


def _require_uuid(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a UUID string")
    try:
        UUID(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a valid UUID") from error
    return value


def _require_timestamp(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return value


def _require_string_or_null(value: object, name: str, *, nullable: bool) -> None:
    if isinstance(value, str) or (nullable and value is None):
        return
    expected = "a string or null" if nullable else "a string"
    raise ValueError(f"{name} must be {expected}")
