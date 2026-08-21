# Merchant-basics production migration

This runbook transfers only the approved merchant-basics package. It never deletes,
truncates, overwrites, or upserts data, and it does not expose PostgreSQL publicly.
The included counts must be exactly `merchants=2`, `merchant_sources=1`,
`merchant_profile_facts=13`, and `merchant_local_contexts=2`.

Both `.runtime/merchant-basics.json` and `.runtime/backups/` are ignored by Git and
must remain untracked. Do not transfer the package through GitHub, a public URL, the
application API, or chat attachment.

## Prepare the local package

From the cloud-deployment worktree root, create the package from the local SQLite
source and save its SHA-256 digest:

```powershell
New-Item -ItemType Directory -Force '.runtime' | Out-Null
python services/api/scripts/export_merchant_basics.py '..\..\services\api\merchant-exposure.db' '.runtime\merchant-basics.json'
(Get-FileHash '.runtime\merchant-basics.json' -Algorithm SHA256).Hash.ToLower() | Set-Content '.runtime\merchant-basics.sha256'
```

The export command must print exactly the approved four counts. Validate the package
against a disposable empty local target before upload:

```powershell
$env:PYTHONPATH = (Resolve-Path 'services/api').Path
$env:DATABASE_URL = 'sqlite+pysqlite:///./.runtime/empty-target.db'
& '.runtime\api-test-venv\Scripts\python.exe' -c "from sqlalchemy import create_engine; from app.db.base import Base; import app.merchants.models; Base.metadata.create_all(create_engine('sqlite+pysqlite:///./.runtime/empty-target.db'))"
& '.runtime\api-test-venv\Scripts\python.exe' services/api/scripts/import_merchant_basics.py '.runtime\merchant-basics.json' --dry-run
Remove-Item -LiteralPath '.runtime\empty-target.db'
Remove-Item Env:DATABASE_URL
Remove-Item Env:PYTHONPATH
git status --short --ignored .runtime
```

The validation must report `VALIDATION OK`; the status command must show the package
and digest as `!!`, never `??` or staged.

## Back up and transfer on the server

First deploy the migration code by fast-forwarding the existing private checkout:

```bash
cd ~/nine
git pull --ff-only
git status --short
```

Before uploading or importing, verify that each approved target table is empty. Any
non-zero count stops the migration.

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT '\''merchants='\'' || count(*) FROM merchants UNION ALL SELECT '\''merchant_sources='\'' || count(*) FROM merchant_sources UNION ALL SELECT '\''merchant_profile_facts='\'' || count(*) FROM merchant_profile_facts UNION ALL SELECT '\''merchant_local_contexts='\'' || count(*) FROM merchant_local_contexts;"'
```

Create and verify the PostgreSQL backup before importing anything:

```bash
mkdir -p .runtime/backups
chmod 700 .runtime .runtime/backups
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > .runtime/backups/pre-merchant-basics.dump
chmod 600 .runtime/backups/pre-merchant-basics.dump
test -s .runtime/backups/pre-merchant-basics.dump
ls -lh .runtime/backups/pre-merchant-basics.dump
```

Use Tencent Cloud's authenticated file manager to upload the local
`.runtime/merchant-basics.json` to the private server path
`/home/ubuntu/nine/.runtime/merchant-basics.json`. Then secure and verify it against
the local `.runtime/merchant-basics.sha256` value:

```bash
chmod 600 .runtime/merchant-basics.json
sha256sum .runtime/merchant-basics.json
```

The printed hash must equal the local SHA-256 digest exactly.

## Validate, import once, and verify

Build the existing API image and run validation-only mode while mounting the private
runtime directory read-only:

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml build api
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml run --rm --no-deps -T -v "$PWD/.runtime:/migration:ro" api python scripts/import_merchant_basics.py /migration/merchant-basics.json --dry-run
```

Only if validation reports `VALIDATION OK` with `2/1/13/2`, execute this import
command once. Do not rerun it: the empty-target guard must reject any later attempt.

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml run --rm --no-deps -T -v "$PWD/.runtime:/migration:ro" api python scripts/import_merchant_basics.py /migration/merchant-basics.json
```

It must report `IMPORT OK` with the approved four counts. Verify included and
excluded production tables immediately afterwards:

```bash
docker compose --env-file deploy/.env.production -f docker-compose.prod.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT '\''merchants='\'' || count(*) FROM merchants UNION ALL SELECT '\''merchant_sources='\'' || count(*) FROM merchant_sources UNION ALL SELECT '\''merchant_profile_facts='\'' || count(*) FROM merchant_profile_facts UNION ALL SELECT '\''merchant_local_contexts='\'' || count(*) FROM merchant_local_contexts UNION ALL SELECT '\''scan_runs='\'' || count(*) FROM scan_runs UNION ALL SELECT '\''query_results='\'' || count(*) FROM query_results UNION ALL SELECT '\''mobile_check_rounds='\'' || count(*) FROM mobile_check_rounds UNION ALL SELECT '\''platform_audit_runs='\'' || count(*) FROM platform_audit_runs;"'
```

The first four counts must be `2/1/13/2`; `scan_runs`, `query_results`,
`mobile_check_rounds`, and `platform_audit_runs` must all be zero. Then use the
authenticated application to confirm both merchants are selectable and open
`/api/merchants` in the same authenticated browser session to confirm two records.

Keep `.runtime/backups/pre-merchant-basics.dump` and
`.runtime/merchant-basics.json` until the user confirms both merchant detail views
are correct. Do not delete either recovery artifact during this migration.
