# Mobile Metrics and Platform Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make three-question mobile results understandable as counts and safely adopt verified platform fields into the merchant profile.

**Architecture:** Extend the mobile workspace metrics with explicit numerators and denominators. Persist each platform result's search query and baseline snapshot, expose field-level differences, and add a guarded field-adoption endpoint that writes a confirmed profile fact with its public source URL.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, Next.js Server Actions, React, Vitest, Pytest.

## Global Constraints

- Never modify external map, social, or merchant accounts.
- Never auto-overwrite a confirmed merchant fact; adoption requires an explicit field submission.
- Reject adoption for conflicts, review-only results, missing evidence URLs, and unsupported fields.
- Keep medical-specific copy out of generic merchant flows.

---

### Task 1: Mobile metric counts

**Files:**
- Modify: `services/api/app/mobile_checks/service.py`
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/components/mobile-check-workspace.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `services/api/tests/mobile_checks/test_service.py`
- Test: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Produces `metrics.mentionCount`, `primaryCount`, `categoryCoveredCount`, `categoryTotalCount`, `informationAccurateCount`, and `informationEvaluatedCount`.
- The UI renders each rate with its own count denominator and derives “本轮至少首批推荐一次” from `primaryCount > 0`.

- [ ] Add API and component tests asserting `1/3`, category and accuracy fractions, and the yes/no primary recommendation conclusion.
- [ ] Run the focused tests and verify they fail because count properties and conclusion UI are absent.
- [ ] Add count properties to the workspace response and TypeScript contract.
- [ ] Render percentage plus fraction, with a separate primary-outcome card and no invented values when metrics are absent.
- [ ] Run the focused API and web tests and verify they pass.

### Task 2: Persist platform search evidence and baseline

**Files:**
- Create: `services/api/migrations/versions/0009_platform_audit_evidence.py`
- Modify: `services/api/app/platform_audits/models.py`
- Modify: `services/api/app/platform_audits/schemas.py`
- Modify: `services/api/app/platform_audits/service.py`
- Modify: `services/api/app/platform_audits/worker.py`
- Test: `services/api/tests/platform_audits/test_service.py`
- Test: `services/api/tests/platform_audits/test_worker.py`

**Interfaces:**
- `PlatformAuditResult.search_query: str | None`
- `PlatformAuditResult.baseline_fields: dict`
- `record_platform(..., search_query: str | None = None)` and `record_failure(..., search_query: str | None = None)`.

- [ ] Add service and worker tests asserting the search query and original baseline are returned with each result.
- [ ] Run the focused tests and verify the new fields are missing.
- [ ] Add the SQLAlchemy columns, Alembic migration, schema fields, and worker/service propagation.
- [ ] Run the focused platform service and worker tests and verify they pass.

### Task 3: Guarded field adoption API

**Files:**
- Modify: `services/api/app/platform_audits/schemas.py`
- Modify: `services/api/app/platform_audits/service.py`
- Modify: `services/api/app/platform_audits/router.py`
- Test: `services/api/tests/platform_audits/test_service.py`
- Test: `services/api/tests/platform_audits/test_router.py`

**Interfaces:**
- Request: `POST /merchants/{merchant_id}/platform-audits/results/{result_id}/adopt` with `{ "field_key": "phone" }`.
- Response: updated `PlatformAuditResultRead`.
- Field mapping: `name -> identity.official_name`, `address -> location.address`, `phone -> contact.phone`, `opening_hours -> hours.display`, `products -> product.list`, `credentials -> credential.list`.

- [ ] Add tests for a successful phone adoption, idempotent repeat, wrong merchant, conflict, unsupported field, and missing evidence URL.
- [ ] Run tests and verify adoption is unavailable.
- [ ] Implement validation, confirmed fact upsert with source URL, baseline/status refresh, and HTTP 404/409/422 mappings.
- [ ] Run the focused service and router tests and verify they pass.

### Task 4: Platform evidence and adoption UI

**Files:**
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/platform-audits/actions.ts`
- Modify: `apps/web/src/app/platform-audits/page.tsx`
- Modify: `apps/web/src/components/platform-audit-matrix.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/platform-audits.test.tsx`

**Interfaces:**
- Server action `adoptPlatformField(formData)` posts merchant ID, result ID, and field key, then redirects to the merchant's platform audit page.
- Matrix receives `merchantId` and renders search query, matched name, checked time, source links, current/new values, and guarded adoption buttons.

- [ ] Add frontend tests for evidence metadata, old/new values, enabled adoption, and disabled conflict/no-source states.
- [ ] Run the focused Vitest file and verify the new evidence controls are absent.
- [ ] Extend contracts, server action, page props, component rendering, and existing visual styles.
- [ ] Run focused frontend tests and verify they pass.

### Task 5: Focused regression verification

**Files:**
- Modify only files required by failures directly caused by Tasks 1–4.

- [ ] Run all platform-audit and mobile-check API tests once.
- [ ] Run `apps/web/tests/mobile-checks.test.tsx` and `apps/web/tests/platform-audits.test.tsx` together once.
- [ ] Run `git diff --check` and review the final scoped diff without touching unrelated user changes.
