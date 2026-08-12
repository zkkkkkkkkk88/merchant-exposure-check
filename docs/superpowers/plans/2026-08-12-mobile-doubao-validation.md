# Mobile Doubao Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a low-labor mobile Doubao validation loop with sampled questions, batch-confirmed results, round-level sources, optional screenshot evidence, separate metrics, and a target-versus-competitor source-gap matrix.

**Architecture:** Add a focused `mobile_checks` backend module with its own models, schemas, service, router, and migration. Expose one merchant-scoped workspace endpoint plus mutation endpoints, then add a `/mobile-checks` Next.js page and a small mobile summary on the existing dashboard. Keep Ark scan data and mobile-confirmed data separate at every API and UI boundary.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, SQLite/PostgreSQL-compatible schema, Next.js 16 App Router, React, TypeScript, Vitest.

## Global Constraints

- Mobile metrics use only confirmed mobile results; Ark results never enter those calculations.
- The source-gap matrix uses mobile-round sources only; Ark sources are auxiliary.
- A validation set contains 8–15 approved enabled questions when available and remains fixed for before/after comparison.
- Screenshots are optional evidence; version one performs no OCR.
- Sources are round-level records and may reference a prior round without duplicating evidence.
- Missing means “not found in the current confirmed mobile evidence,” not “absent from the internet.”
- No new paid model call is required by this workflow.

---

### Task 1: Mobile validation domain and sampling

**Files:**
- Create: `services/api/app/mobile_checks/models.py`
- Create: `services/api/app/mobile_checks/schemas.py`
- Create: `services/api/app/mobile_checks/service.py`
- Create: `services/api/app/mobile_checks/__init__.py`
- Create: `services/api/tests/mobile_checks/test_service.py`
- Create: `services/api/migrations/versions/0007_mobile_checks.py`

**Interfaces:**
- Produces: `MobileCheckService.create_validation_set(merchant_id)`, returning a fixed set of 8–15 approved enabled queries with category coverage.
- Produces models for validation sets, rounds, per-question results, round sources, and evidence metadata.

- [ ] **Step 1: Write failing sampling tests**

Test that only approved enabled questions are selected, all are returned when fewer than 8 exist, at most 15 are returned, recommendation and verification intents are represented, and categories are distributed before duplicates.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m pytest tests/mobile_checks/test_service.py -q`
Expected: collection fails because `app.mobile_checks` does not exist.

- [ ] **Step 3: Implement models, sampling service, and migration**

Create normalized tables with merchant ownership, immutable validation-set items, draft/confirmed rounds, result mention levels (`none`, `supplementary`, `primary`), source classification and optional inherited-round linkage.

- [ ] **Step 4: Run focused tests and verify pass**

Run: `python -m pytest tests/mobile_checks/test_service.py -q`
Expected: PASS.

### Task 2: Confirmed metrics and source-gap matrix

**Files:**
- Modify: `services/api/app/mobile_checks/service.py`
- Modify: `services/api/app/mobile_checks/schemas.py`
- Modify: `services/api/tests/mobile_checks/test_service.py`

**Interfaces:**
- Produces: `MobileCheckService.get_workspace(merchant_id)` with latest round, metrics, source gaps, and round history.
- Metrics: mention rate, primary recommendation rate, category coverage rate, information accuracy rate, source coverage rate.

- [ ] **Step 1: Write failing metric and matrix tests**

Cover exclusion of draft/unconfirmed results, exact rate denominators, competitor names from confirmed results, evidence summaries, `missing` versus `needs_review`, and inherited-source provenance.

- [ ] **Step 2: Run focused tests and verify expected failures**

Run: `python -m pytest tests/mobile_checks/test_service.py -q`
Expected: assertions fail because workspace aggregation is absent.

- [ ] **Step 3: Implement minimal aggregation**

Build the matrix from confirmed mobile sources grouped by source type and entity, append fact rows for address, hours, credentials, services, and equipment, and highlight target gaps where any confirmed competitor has evidence.

- [ ] **Step 4: Run focused tests and verify pass**

Run: `python -m pytest tests/mobile_checks/test_service.py -q`
Expected: PASS.

### Task 3: Merchant-scoped API and optional evidence upload

**Files:**
- Create: `services/api/app/mobile_checks/router.py`
- Modify: `services/api/app/main.py`
- Create: `services/api/tests/mobile_checks/test_router.py`

**Interfaces:**
- `POST /merchants/{merchant_id}/mobile-validation-sets`
- `GET /merchants/{merchant_id}/mobile-checks/workspace`
- `POST /merchants/{merchant_id}/mobile-check-rounds`
- `PUT /merchants/{merchant_id}/mobile-check-rounds/{round_id}`
- `POST /merchants/{merchant_id}/mobile-check-rounds/{round_id}/confirm`
- `POST /merchants/{merchant_id}/mobile-check-rounds/{round_id}/evidence`

- [ ] **Step 1: Write failing router tests**

Test batch round creation, per-question confirmation, source entry, source inheritance, wrong-merchant rejection, optional image upload metadata, and workspace reads.

- [ ] **Step 2: Run router tests and verify expected failures**

Run: `python -m pytest tests/mobile_checks/test_router.py -q`
Expected: 404 before routes are registered.

- [ ] **Step 3: Implement routes and bounded file storage**

Accept JPEG/PNG/WebP files up to 10 MB, generate server-side filenames below a configured `data/mobile-check-evidence` directory, and persist only metadata/path. Return 400 for unsupported types and delete a just-written file if database persistence fails.

- [ ] **Step 4: Run router tests and verify pass**

Run: `python -m pytest tests/mobile_checks/test_router.py -q`
Expected: PASS.

### Task 4: Mobile check workspace UI

**Files:**
- Create: `apps/web/src/app/mobile-checks/page.tsx`
- Create: `apps/web/src/app/mobile-checks/actions.ts`
- Create: `apps/web/src/components/mobile-check-workspace.tsx`
- Create: `apps/web/src/components/source-gap-table.tsx`
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/app-shell.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Create: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Consumes the mobile workspace API and sends one batch payload per save.
- Produces a page with sampled-question copy controls, batch raw-text entry, quick per-question confirmation, source entry/inheritance, optional evidence upload, metrics, and source-gap matrix.

- [ ] **Step 1: Write failing page/component tests**

Assert explicit mobile-versus-Ark wording, fixed question list, batch entry, mention-level controls, optional screenshots, source inheritance, and highlighted target gaps with evidence details.

- [ ] **Step 2: Run focused tests and verify expected failures**

Run: `npm.cmd test -- --run tests/mobile-checks.test.tsx`
Expected: module resolution fails because the page and components do not exist.

- [ ] **Step 3: Implement typed API, actions, page, components, and styles**

Use server loading plus a client workspace form. Keep every mutation merchant-scoped and redirect back with the same merchant ID. Render honest empty and draft states without fabricated metrics.

- [ ] **Step 4: Run focused tests and verify pass**

Run: `npm.cmd test -- --run tests/mobile-checks.test.tsx`
Expected: PASS.

### Task 5: Dashboard separation and verification

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/components/metric-strip.tsx`
- Modify: `apps/web/tests/dashboard.test.tsx`
- Modify: `README.md`

**Interfaces:**
- Dashboard labels existing metrics “方舟联网检测”.
- When mobile data exists, dashboard shows a separate mobile summary linking to `/mobile-checks?merchant=...`; otherwise it shows a setup prompt.

- [ ] **Step 1: Write failing dashboard wording tests**

Assert that Ark and mobile headings are separate and that no Ark percentage is labeled mobile recommendation rate.

- [ ] **Step 2: Run focused tests and verify expected failure**

Run: `npm.cmd test -- --run tests/dashboard.test.tsx`
Expected: missing headings or mobile link.

- [ ] **Step 3: Implement dashboard summary and documentation**

Add the mobile workspace read to dashboard loading, keep failure isolated so existing Ark data remains visible, and document the manual sample workflow and non-equivalence of Ark/App results.

- [ ] **Step 4: Run complete verification once**

Run backend: `python -m pytest -q`
Run frontend: `npm.cmd test -- --run`
Run build: `npm.cmd run build`
Expected: all pass without creating a paid scan.
