# Mobile Checks Three-Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 15-question manual mobile Doubao workflow with three independent conversations, one pasted batch, automatic draft recognition, and safe legacy query-set cleanup.

**Architecture:** Keep the existing mobile-check persistence model, but constrain validation-set creation to three recommendation queries from the newest query-set only. Add deterministic answer-block parsing in the web layer so the browser can prefill results without an external API, and add an archive flag plus reference-aware cleanup service for legacy query sets.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, Next.js App Router, React, TypeScript, Vitest, pytest.

## Global Constraints

- A new mobile validation set contains exactly three recommendation questions from one latest query-set.
- Never use an older query-set to fill a shortage in the latest query-set.
- Never delete a query-set referenced by scans, manual checks, reports, or mobile validation records.
- A missing `merchant` query parameter must not silently select the first merchant.
- Answer recognition is local and deterministic; no paid or external parsing calls are introduced.

---

### Task 1: Latest-only three-question validation sets

**Files:**
- Modify: `services/api/app/mobile_checks/service.py`
- Modify: `services/api/tests/mobile_checks/test_service.py`
- Modify: `services/api/tests/mobile_checks/test_router.py`

**Interfaces:**
- Produces: `MobileCheckService.create_validation_set(merchant_id)` that returns exactly three recommendation items from the newest query-set or raises `NoApprovedQueriesError`.

- [ ] Add failing tests with two query-set versions and assert all three selected query IDs belong to the newest version.
- [ ] Add a failing shortage test asserting fewer than three approved enabled recommendation queries raises `NoApprovedQueriesError`.
- [ ] Change `_approved_queries` to resolve the newest `QuerySet` first and filter by recommendation, approved, and enabled.
- [ ] Change `_sample` to select three distinct categories when possible, then fill to exactly three.
- [ ] Run `pytest services/api/tests/mobile_checks/test_service.py services/api/tests/mobile_checks/test_router.py -q` and confirm it passes.

### Task 2: Archive and safely clean legacy query sets

**Files:**
- Create: `services/api/migrations/versions/0008_query_set_archiving.py`
- Modify: `services/api/app/queries/models.py`
- Modify: `services/api/app/queries/service.py`
- Modify: `services/api/app/queries/router.py`
- Modify: `services/api/app/queries/schemas.py`
- Modify: `services/api/tests/queries/test_router.py`

**Interfaces:**
- Produces: `QuerySet.is_archived: bool` and `QueryLibraryService.cleanup_legacy_sets(session, merchant_id) -> dict[str, int]`.
- Produces: `POST /merchants/{merchant_id}/query-sets/cleanup` returning `deleted`, `archived`, and `kept` counts.

- [ ] Add tests proving an unreferenced old version is deleted and a referenced old version is archived without deleting history.
- [ ] Add the `is_archived` migration and ORM/schema field with a false default.
- [ ] Implement reference checks across scan runs, manual checks, report references, and mobile validation items before deletion.
- [ ] Exclude archived sets from the ordinary list endpoint while historical relationships remain readable.
- [ ] Add the cleanup endpoint and run `pytest services/api/tests/queries/test_router.py -q`.

### Task 3: One-paste automatic draft recognition

**Files:**
- Create: `apps/web/src/lib/mobile-answer-parser.ts`
- Create: `apps/web/tests/mobile-answer-parser.test.ts`
- Modify: `apps/web/src/components/mobile-check-workspace.tsx`
- Modify: `apps/web/src/app/mobile-checks/actions.ts`
- Modify: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Produces: `parseMobileAnswers(rawText, items, merchantName)` returning one draft per validation item with `mentionLevel`, `competitors`, `answerExcerpt`, and `needsReview`.

- [ ] Add parser tests for `Q1/Q2/Q3` blocks, target-name detection, missing blocks, and competitor candidates.
- [ ] Implement deterministic splitting and target-name matching without network calls.
- [ ] Replace per-question default manual entry with one textarea, “识别三份回答” preview, editable exception rows, and one final confirm button.
- [ ] Add an “一键复制全部问题” button and explicit three-new-conversation guidance.
- [ ] Keep the independent source-audit textarea and source-gap table.
- [ ] Run `npm test -- --run apps/web/tests/mobile-answer-parser.test.ts apps/web/tests/mobile-checks.test.tsx` from `apps/web` with the repository test paths adjusted to the package runner.

### Task 4: Explicit merchant selection and live-data cleanup

**Files:**
- Modify: `apps/web/src/app/mobile-checks/page.tsx`
- Modify: `apps/web/src/components/merchant-switcher.tsx`
- Modify: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Consumes: the existing `merchant` URL query parameter.
- Produces: `/mobile-checks` selection state and path-preserving merchant switching.

- [ ] Add a page test that no `merchant` parameter renders a selection prompt and does not fetch mobile data.
- [ ] Make the switcher preserve `/mobile-checks` and update only the `merchant` query parameter.
- [ ] Show selected merchant name, validation count, and newest query-set identity near the questions.
- [ ] Run the focused web tests once.
- [ ] Apply migration `0008`, call cleanup for the oral-clinic merchant, remove the unused 15-question mobile validation set, approve three valid newest-version recommendation queries, and create a fresh three-question set.
- [ ] Verify `/mobile-checks?merchant=<id>` renders three corrected questions and the source-gap table.

