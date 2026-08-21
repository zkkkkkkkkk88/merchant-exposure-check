# Merchant Basics Data Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore exactly two merchants and their approved basic profile data from the local SQLite database into the empty production PostgreSQL database without importing historical scan or audit data.

**Architecture:** A pure, versioned JSON package is exported from SQLite in read-only mode, validated against an exact table allowlist and approved counts, transferred privately to the server, and imported through SQLAlchemy in one transaction. Production execution refuses non-empty targets, creates a PostgreSQL backup first, supports validation-only mode, and verifies both included and excluded table counts afterward.

**Tech Stack:** Python 3.13, stdlib `sqlite3`/`json`/`hashlib`, SQLAlchemy 2, pytest, Docker Compose, PostgreSQL 17

**Spec:** `docs/superpowers/specs/2026-08-21-merchant-basics-data-migration-design.md`

## Global Constraints

- Include only `merchants`, `merchant_sources`, `merchant_profile_facts`, and `merchant_local_contexts`.
- Preserve source UUIDs, timestamps, JSON values, booleans, nullable fields, and verification states.
- Approved source counts are exactly 2, 1, 13, and 2 in dependency order.
- Never delete, truncate, overwrite, or upsert production rows.
- Refuse import when any included production table is non-empty.
- Execute all inserts in one transaction and roll back all inserts on any failure.
- Keep the package and PostgreSQL backup under `.runtime/`; never commit either artifact.
- Do not expose PostgreSQL through a host port.

---

### Task 1: Versioned merchant-basics package exporter and validator

**Files:**
- Create: `services/api/app/data_migrations/__init__.py`
- Create: `services/api/app/data_migrations/merchant_basics.py`
- Create: `services/api/tests/data_migrations/test_merchant_basics_package.py`

**Interfaces:**
- Produces: `TABLE_ORDER: tuple[str, ...]`
- Produces: `EXPECTED_COUNTS: dict[str, int]`
- Produces: `MerchantBasicsPackage` immutable dataclass containing `format_version`, `exported_at`, `counts`, and `tables`
- Produces: `export_sqlite_package(source: Path, destination: Path) -> dict[str, int]`
- Produces: `load_package(path: Path) -> MerchantBasicsPackage`
- Produces: `validate_package(payload: object) -> MerchantBasicsPackage`

- [ ] **Step 1: Write the failing package tests**

Create a temporary SQLite database with the four approved tables plus an out-of-scope `scan_runs` table. Insert fixtures containing UUID strings, ISO timestamps, JSON arrays/objects, a boolean, and nullable values. Assert that export:

```python
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
assert payload["tables"]["merchant_sources"][0]["is_verified"] is True
```

Add independent tests that `validate_package` rejects an unexpected table, a missing required field, an invalid UUID, a broken merchant foreign key, and any count other than 2/1/13/2.

- [ ] **Step 2: Run the package tests and verify RED**

Run:

```powershell
python -m pytest services/api/tests/data_migrations/test_merchant_basics_package.py -q
```

Expected: collection fails because `app.data_migrations.merchant_basics` does not exist.

- [ ] **Step 3: Implement the minimal package module**

Implement explicit column allowlists rather than `SELECT *`:

```python
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
```

Open SQLite with `sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True)`. Decode only the declared JSON and boolean columns, preserve all other values, validate exact counts and foreign-key membership, and write through a sibling temporary file followed by `Path.replace()`.

`load_package` must parse UTF-8 JSON and call `validate_package`. Validation must reject extra tables, missing keys, malformed values, duplicate IDs, foreign keys outside the two exported merchant IDs, and count mismatches.

- [ ] **Step 4: Run package tests and verify GREEN**

Run:

```powershell
python -m pytest services/api/tests/data_migrations/test_merchant_basics_package.py -q
```

Expected: all package tests pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add services/api/app/data_migrations services/api/tests/data_migrations/test_merchant_basics_package.py
git commit -m "feat: export validated merchant basics packages"
```

---

### Task 2: Transactional importer with empty-target guard

**Files:**
- Modify: `services/api/app/data_migrations/merchant_basics.py`
- Create: `services/api/tests/data_migrations/test_merchant_basics_import.py`

**Interfaces:**
- Consumes: `MerchantBasicsPackage` and `load_package(path)` from Task 1
- Produces: `TargetNotEmptyError`
- Produces: `import_package(engine: Engine, package: MerchantBasicsPackage, *, dry_run: bool = False) -> dict[str, int]`

- [ ] **Step 1: Write failing importer tests**

Use an in-memory SQLite target with only the four merchant model tables created from SQLAlchemy metadata. Test these observable behaviors:

```python
assert import_package(engine, package) == EXPECTED_COUNTS
assert count_rows(engine) == EXPECTED_COUNTS
```

Add a non-empty-target test that inserts one merchant first and asserts `TargetNotEmptyError` while preserving that row. Add an atomicity test with a duplicate `(merchant_id, field_key)` profile fact that reaches the database uniqueness constraint and assert all four target tables remain empty after the raised exception. Add a dry-run test that returns the expected counts while leaving every target table empty.

- [ ] **Step 2: Run importer tests and verify RED**

Run:

```powershell
python -m pytest services/api/tests/data_migrations/test_merchant_basics_import.py -q
```

Expected: fail because `import_package` and `TargetNotEmptyError` are absent.

- [ ] **Step 3: Implement the minimal transactional importer**

Create SQLAlchemy model instances with explicit UUID and timestamp conversion:

```python
def parse_uuid(value: str) -> UUID:
    return UUID(value)

def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
```

Before writing, count every included target table with `select(func.count())`; raise `TargetNotEmptyError` if any count is non-zero. For a dry run, stop after package and target validation. For a real import, use one `Session.begin()` block, add models in `TABLE_ORDER`, flush before returning, and allow any exception to escape so SQLAlchemy rolls back the transaction.

- [ ] **Step 4: Run importer tests and verify GREEN**

Run:

```powershell
python -m pytest services/api/tests/data_migrations/test_merchant_basics_import.py -q
```

Expected: all importer tests pass, including atomic rollback.

- [ ] **Step 5: Run both data-migration test files**

```powershell
python -m pytest services/api/tests/data_migrations -q
```

Expected: all data-migration tests pass.

- [ ] **Step 6: Commit Task 2**

```powershell
git add services/api/app/data_migrations/merchant_basics.py services/api/tests/data_migrations/test_merchant_basics_import.py
git commit -m "feat: import merchant basics transactionally"
```

---

### Task 3: Safe command-line entry points and production image support

**Files:**
- Create: `services/api/scripts/export_merchant_basics.py`
- Create: `services/api/scripts/import_merchant_basics.py`
- Create: `services/api/tests/data_migrations/test_merchant_basics_cli.py`
- Modify: `services/api/Dockerfile`
- Create: `docs/deployment/merchant-basics-migration.md`

**Interfaces:**
- Consumes: `export_sqlite_package`, `load_package`, and `import_package`
- Produces: local command `python scripts/export_merchant_basics.py SOURCE DESTINATION`
- Produces: container command `python scripts/import_merchant_basics.py PACKAGE [--dry-run]`

- [ ] **Step 1: Write failing CLI tests**

Call each script's `main(argv: list[str] | None = None) -> int` directly. Assert the export CLI prints the four exact counts and creates its destination. Assert the import CLI passes `--dry-run` through, prints `VALIDATION OK`, returns zero on success, and returns non-zero with a concise message for malformed packages or a non-empty target. Do not assert on mocks; use temporary real files and a real temporary SQLite engine URL supplied through `DATABASE_URL`.

- [ ] **Step 2: Run CLI tests and verify RED**

```powershell
python -m pytest services/api/tests/data_migrations/test_merchant_basics_cli.py -q
```

Expected: fail because both CLI modules are absent.

- [ ] **Step 3: Implement the CLIs and image inclusion**

The export CLI accepts exactly two positional paths and never reads `DATABASE_URL`. The import CLI accepts the package path, reads the target URL from existing settings, creates an engine with `make_engine`, and supports `--dry-run`.

Add this production image line after copying the application:

```dockerfile
COPY scripts ./scripts
```

Document the exact backup, upload destination, validation, import, and verification commands from Tasks 4 and 5. Explicitly state that `.runtime/merchant-basics.json` and `.runtime/backups/` remain untracked.

- [ ] **Step 4: Run CLI and production-stack tests**

```powershell
python -m pytest services/api/tests/data_migrations services/api/tests/test_production_stack.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Run web and API regression tests once**

```powershell
python -m venv .runtime/api-test-venv
& '.runtime\api-test-venv\Scripts\python.exe' -m pip install -e 'services/api[dev]'
Set-Location apps/web
npm test
Set-Location ../..
& '.runtime\api-test-venv\Scripts\python.exe' -m pytest services/api -q
```

Expected: 83 web tests and the full API suite pass with zero failures in the configured development environment.

- [ ] **Step 6: Commit Task 3**

```powershell
git add services/api/scripts services/api/tests/data_migrations services/api/Dockerfile docs/deployment/merchant-basics-migration.md
git commit -m "build: add merchant basics migration commands"
```

---

### Task 4: Generate and verify the local migration package

**Files:**
- Read only: `services/api/merchant-exposure.db`
- Create ignored artifact: `.runtime/merchant-basics.json`
- Create ignored artifact: `.runtime/merchant-basics.sha256`

- [ ] **Step 1: Confirm the source database is unchanged and readable**

From the repository worktree root, run:

```powershell
Get-Item '..\..\services\api\merchant-exposure.db' | Select-Object FullName,Length,LastWriteTime
```

Expected: the source file exists and remains 937984 bytes unless the user has intentionally added local records since discovery. If it changed, stop and re-count before exporting.

- [ ] **Step 2: Export only the approved package**

```powershell
New-Item -ItemType Directory -Force '.runtime' | Out-Null
python services/api/scripts/export_merchant_basics.py '..\..\services\api\merchant-exposure.db' '.runtime\merchant-basics.json'
```

Expected output: `merchants=2 merchant_sources=1 merchant_profile_facts=13 merchant_local_contexts=2`.

- [ ] **Step 3: Hash and locally re-validate the artifact**

```powershell
(Get-FileHash '.runtime\merchant-basics.json' -Algorithm SHA256).Hash.ToLower() | Set-Content '.runtime\merchant-basics.sha256'
$env:PYTHONPATH = (Resolve-Path 'services/api').Path
$env:DATABASE_URL = 'sqlite+pysqlite:///./.runtime/empty-target.db'
& '.runtime\api-test-venv\Scripts\python.exe' -c "from sqlalchemy import create_engine; from app.db.base import Base; import app.merchants.models; Base.metadata.create_all(create_engine('sqlite+pysqlite:///./.runtime/empty-target.db'))"
& '.runtime\api-test-venv\Scripts\python.exe' services/api/scripts/import_merchant_basics.py '.runtime\merchant-basics.json' --dry-run
Remove-Item -LiteralPath '.runtime\empty-target.db'
Remove-Item Env:DATABASE_URL
Remove-Item Env:PYTHONPATH
```

Expected: `VALIDATION OK` and no target rows written. The temporary empty target is deleted only after validation succeeds.

- [ ] **Step 4: Verify Git cannot see the artifacts**

```powershell
git status --short --ignored .runtime
```

Expected: both artifacts are marked `!!`, never `??` or staged.

---

### Task 5: Back up production, upload, import once, and verify

**Files:**
- Create ignored server artifact: `/home/ubuntu/nine/.runtime/merchant-basics.json`
- Create ignored server artifact: `/home/ubuntu/nine/.runtime/backups/pre-merchant-basics.dump`

- [ ] **Step 1: Push the migration code and fast-forward the server branch**

Push `codex/cloud-deployment` once, verify its remote HEAD once, then on the server run:

```bash
cd ~/nine
git pull --ff-only
git status --short
```

Expected: fast-forward succeeds and status is empty.

- [ ] **Step 2: Reconfirm all approved target tables are empty**

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT '\''merchants='\'' || count(*) FROM merchants UNION ALL SELECT '\''merchant_sources='\'' || count(*) FROM merchant_sources UNION ALL SELECT '\''merchant_profile_facts='\'' || count(*) FROM merchant_profile_facts UNION ALL SELECT '\''merchant_local_contexts='\'' || count(*) FROM merchant_local_contexts;"'
```

Expected: all four counts are zero. Any non-zero count stops the migration.

- [ ] **Step 3: Create and verify the production backup**

```bash
mkdir -p .runtime/backups
chmod 700 .runtime .runtime/backups
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > .runtime/backups/pre-merchant-basics.dump
chmod 600 .runtime/backups/pre-merchant-basics.dump
test -s .runtime/backups/pre-merchant-basics.dump
ls -lh .runtime/backups/pre-merchant-basics.dump
```

Expected: `test -s` exits successfully and the dump has a non-zero size.

- [ ] **Step 4: Upload and verify the private package**

Use Tencent Cloud's authenticated file manager to upload local `.runtime/merchant-basics.json` to `/home/ubuntu/nine/.runtime/merchant-basics.json`. Then run:

```bash
chmod 600 .runtime/merchant-basics.json
sha256sum .runtime/merchant-basics.json
```

Expected: the SHA-256 output equals the local `.runtime/merchant-basics.sha256` value exactly.

- [ ] **Step 5: Build the importer image and run validation-only mode**

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml build api
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml run --rm --no-deps -T -v "$PWD/.runtime:/migration:ro" api python scripts/import_merchant_basics.py /migration/merchant-basics.json --dry-run
```

Expected: `VALIDATION OK` with counts 2, 1, 13, and 2. No production counts change.

- [ ] **Step 6: Execute the transactional import once**

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml run --rm --no-deps -T -v "$PWD/.runtime:/migration:ro" api python scripts/import_merchant_basics.py /migration/merchant-basics.json
```

Expected: `IMPORT OK` with counts 2, 1, 13, and 2. Do not rerun this command; the empty-target guard must reject any second attempt.

- [ ] **Step 7: Verify included and excluded production counts**

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT '\''merchants='\'' || count(*) FROM merchants UNION ALL SELECT '\''merchant_sources='\'' || count(*) FROM merchant_sources UNION ALL SELECT '\''merchant_profile_facts='\'' || count(*) FROM merchant_profile_facts UNION ALL SELECT '\''merchant_local_contexts='\'' || count(*) FROM merchant_local_contexts UNION ALL SELECT '\''scan_runs='\'' || count(*) FROM scan_runs UNION ALL SELECT '\''query_results='\'' || count(*) FROM query_results UNION ALL SELECT '\''mobile_check_rounds='\'' || count(*) FROM mobile_check_rounds UNION ALL SELECT '\''platform_audit_runs='\'' || count(*) FROM platform_audit_runs;"'
```

Expected: included counts are 2/1/13/2 and all four excluded history counts are zero.

- [ ] **Step 8: Verify through the authenticated application**

Open the existing TryCloudflare URL, authenticate, and confirm the merchant selector lists both original merchants. Open `/api/merchants` in the same authenticated browser session and confirm it returns two records. Keep the backup until the user confirms both merchant detail views are correct.

- [ ] **Step 9: Record completion without deleting recovery artifacts**

Run:

```bash
git status --short
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml ps
```

Expected: Git status is empty; `db`, `api`, and `web` remain healthy; `gateway`, `tunnel`, and `worker` remain running. Do not delete `.runtime/backups/pre-merchant-basics.dump` or `.runtime/merchant-basics.json` during this task.
