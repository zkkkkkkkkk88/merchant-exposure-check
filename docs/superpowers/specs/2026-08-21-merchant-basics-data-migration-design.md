# Merchant Basics Data Migration Design

## Goal

Restore the two merchants and their basic profile data from the local SQLite database into the empty production PostgreSQL database without importing scan, query, result, mobile-check, or platform-audit history.

## Confirmed Scope

The migration includes exactly these tables:

- `merchants`: 2 rows
- `merchant_sources`: 1 row
- `merchant_profile_facts`: 13 rows
- `merchant_local_contexts`: 2 rows

All other tables are out of scope. Existing UUIDs and timestamps must be preserved so the restored records retain stable identities.

## Selected Approach

Create a versioned JSON migration package on the local computer, upload that package directly to the Tencent Cloud server, and import it with a purpose-built transactional command.

This approach is preferred over uploading the full SQLite database because the server receives only the approved merchant basics. It is preferred over manual re-entry because it preserves IDs, JSON fields, timestamps, verification state, and related profile information exactly.

The JSON package is a temporary operational artifact. It must be ignored by Git and must never be committed or pushed to GitHub.

## Components

### Exporter

The exporter reads `services/api/merchant-exposure.db` in SQLite read-only mode. It writes a JSON object containing:

- a fixed schema version;
- an export timestamp;
- the four approved table names;
- rows encoded with UUIDs and timestamps as strings;
- expected row counts for each table.

The exporter refuses to run when a required table is missing or the observed counts differ from the explicitly approved source counts. It writes atomically so an interrupted export cannot leave a valid-looking partial package.

### Importer

The importer runs inside the existing API container environment so it uses the production `DATABASE_URL` without exposing PostgreSQL publicly. It validates the package structure, approved table allowlist, row counts, UUIDs, timestamps, JSON values, and foreign-key relationships before writing.

Before importing, it verifies that all four target tables are empty. It does not delete, truncate, overwrite, or upsert. The inserts run in dependency order inside one PostgreSQL transaction:

1. `merchants`
2. `merchant_sources`
3. `merchant_profile_facts`
4. `merchant_local_contexts`

Any validation or database error rolls back the complete transaction.

## Transfer and Production Safety

Before transfer, create a PostgreSQL backup on the server with `pg_dump`. Store both the backup and migration package under a private server directory excluded from Git.

Transfer the JSON package through Tencent Cloud's authenticated file transfer or SCP. Do not use GitHub, a public URL, chat attachment, or the application API for the transfer.

The import command supports a validation-only mode. Production execution follows this order:

1. confirm the four target tables are empty;
2. create and verify the PostgreSQL backup file;
3. upload the migration package;
4. run validation-only mode;
5. run the transactional import once;
6. verify database counts;
7. verify the authenticated `/api/merchants` response and the web merchant selector.

## Error Handling and Recovery

- Invalid or incomplete package: abort before opening a write transaction.
- Non-empty production target: abort without modifying data.
- Insert or constraint failure: roll back the transaction.
- Post-import application problem: retain the backup and migration package, stop further writes, diagnose the cause, and restore from the backup only after confirming the exact target database.
- Never run destructive cleanup commands against the production volume as part of this migration.

## Testing

Automated tests cover:

- export includes only the four approved tables;
- export preserves UUID, timestamp, JSON, boolean, and nullable values;
- malformed packages and wrong row counts are rejected;
- import refuses a non-empty target;
- import is atomic when a child row is invalid;
- a successful round trip restores exactly 2, 1, 13, and 2 rows.

Production verification additionally checks the PostgreSQL counts and reads both merchants through the authenticated API. No scan or audit history is expected in production after this migration.

## Success Criteria

- The cloud application lists both original merchants.
- Merchant basic fields, profile facts, local context, and source link match the local SQLite source.
- The four production table counts are exactly 2, 1, 13, and 2.
- Scan, query, result, mobile-check, and platform-audit tables remain empty.
- The PostgreSQL backup remains available until the user confirms the restored records in the web interface.
