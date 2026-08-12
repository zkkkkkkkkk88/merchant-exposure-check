# Visibility Dossier Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the “见序 / Visibility Dossier” workflow with confirmed merchant profiles, restaurant-specific query generation, dual-track visibility metrics, correct navigation, back controls, and the selected editorial visual system.

**Architecture:** Preserve the FastAPI/SQLAlchemy/Next.js architecture and versioned query sets. Add normalized merchant profile facts and query intent metadata, keep scans asynchronous, derive transparent readiness metrics from persisted evidence, and expose the new contracts to focused Next.js components.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, Next.js 16, React, TypeScript, Vitest.

## Global Constraints

- Product name is “见序 / Visibility Dossier”.
- First-position recommendation is absent from all new UI and API contracts.
- Unknown or unconfirmed merchant facts never generate questions.
- The first complete industry pack is restaurant; the engine remains extensible.
- Existing merchants, query sets, scans, raw answers, and reports remain readable.
- The selected visual direction uses deep green, warm white, terracotta, editorial typography, thin rules, and minimal rounding.

---

### Task 1: Confirmed merchant profile model and API

**Files:**
- Create: `services/api/migrations/versions/0005_visibility_profiles.py`
- Create: `services/api/app/merchants/profile.py`
- Modify: `services/api/app/merchants/models.py`
- Modify: `services/api/app/merchants/schemas.py`
- Modify: `services/api/app/merchants/service.py`
- Modify: `services/api/app/merchants/router.py`
- Test: `services/api/tests/merchants/test_profile.py`
- Test: `services/api/tests/merchants/test_router.py`

**Interfaces:**
- Produces `MerchantProfileFact(field_key, value, confirmation_status, confidence, source_urls)`.
- Produces `GET/PUT /merchants/{merchant_id}/profile` and typed Pydantic profile contracts.
- Existing merchant columns are returned as pending candidates until confirmed.

- [ ] Write failing tests proving pending facts do not count as confirmed and profile updates persist source URLs.
- [ ] Run `pytest tests/merchants/test_profile.py tests/merchants/test_router.py -q` and confirm failure.
- [ ] Add the non-destructive migration, profile model, schemas, service methods, and routes.
- [ ] Run the focused tests and confirm they pass.
- [ ] Commit only Task 1 files with `feat: add confirmed merchant profiles`.

### Task 2: Restaurant rule pack and precise query generation

**Files:**
- Create: `services/api/app/queries/rules/base.py`
- Create: `services/api/app/queries/rules/restaurant.py`
- Modify: `services/api/app/queries/generator.py`
- Modify: `services/api/app/queries/models.py`
- Modify: `services/api/app/queries/schemas.py`
- Modify: `services/api/app/queries/service.py`
- Modify: `services/api/migrations/versions/0005_visibility_profiles.py`
- Test: `services/api/tests/queries/test_restaurant_rules.py`
- Test: `services/api/tests/queries/test_generator.py`

**Interfaces:**
- Produces `QueryDraft.intent_type: Literal["recommendation", "verification"]`.
- Produces `QueryDraft.fact_keys: list[str]` and persists them with each query.
- `RestaurantRulePack.generate(profile, count)` uses only confirmed facts.

- [ ] Write failing O'eat tests that reject low-price, generic “餐饮”, unconfirmed service, and duplicate-location questions.
- [ ] Add positive tests for 西餐厅, 万象城, ¥300–450, 宝宝椅, and traffic-related questions.
- [ ] Run focused query tests and confirm failure.
- [ ] Implement the rule-pack protocol, restaurant rules, quality gates, and query metadata persistence.
- [ ] Run focused tests and confirm they pass.
- [ ] Commit Task 2 with `feat: generate profile-aware restaurant queries`.

### Task 3: Dual-track analysis and transparent growth metrics

**Files:**
- Modify: `services/api/app/analysis/contracts.py`
- Modify: `services/api/app/analysis/extractor.py`
- Modify: `services/api/app/analysis/metrics.py`
- Modify: `services/api/app/analysis/service.py`
- Modify: `services/api/app/reports/schemas.py`
- Modify: `services/api/app/reports/router.py`
- Modify: `services/api/app/reports/service.py`
- Test: `services/api/tests/analysis/test_extractor.py`
- Test: `services/api/tests/analysis/test_metrics.py`
- Test: `services/api/tests/reports/test_router.py`

**Interfaces:**
- Produces `visibility_stage` with `unrecognized | relevant | mentioned | recommended`.
- Produces `profile_completeness`, `public_verifiability`, `high_intent_hit_rate`, `competitor_gap_closure`, and `readiness_score`.
- Removes `first_position_rate` from new report/dashboard/history responses while preserving old stored data.

- [ ] Write failing tests for the four stages and the 25/35/25/15 readiness formula.
- [ ] Write failing history tests for missing-data behavior and removal of first-position deltas.
- [ ] Run the focused analysis/report tests and confirm failure.
- [ ] Implement explicit recommendation classification, evidence-aware stages, component scores, dashboard output, and history deltas.
- [ ] Run focused tests and confirm they pass.
- [ ] Commit Task 3 with `feat: add visibility growth metrics`.

### Task 4: Merchant profile and query strategy workflow

**Files:**
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/merchants/[id]/page.tsx`
- Create: `apps/web/src/components/profile-editor.tsx`
- Modify: `apps/web/src/app/queries/page.tsx`
- Modify: `apps/web/src/components/query-table.tsx`
- Test: `apps/web/tests/merchant-profile.test.tsx`
- Test: `apps/web/tests/query-table.test.tsx`

**Interfaces:**
- Profile editor confirms, edits, or excludes parsed facts before generation.
- Query table visibly separates recommendation and verification questions.
- Existing approval, enablement, and asynchronous scan creation remain intact.

- [ ] Write failing UI tests for pending/confirmed profile facts and query intent labels.
- [ ] Run the focused Vitest files and confirm failure.
- [ ] Implement typed API calls, profile editor, missing-field guidance, and intent-aware query review.
- [ ] Run focused tests and confirm they pass.
- [ ] Commit Task 4 with `feat: add merchant profile workflow`.

### Task 5: Navigation, back controls, branding, and selected visual system

**Files:**
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/components/app-shell.tsx`
- Create: `apps/web/src/components/back-link.tsx`
- Modify: all route pages under `apps/web/src/app/`
- Modify: `apps/web/src/styles/globals.css`
- Modify: dashboard/history/report components that expose old metrics
- Test: `apps/web/tests/navigation.test.tsx`
- Modify: `apps/web/tests/dashboard.test.tsx`
- Modify: `apps/web/tests/real-data-pages.test.tsx`

**Interfaces:**
- `AppShell` derives its active item from `usePathname()`.
- `BackLink({ fallbackHref })` uses browser history when available and a stable parent fallback otherwise.
- Dashboard consumes the Task 3 readiness contract and never renders first-position copy.

- [ ] Write failing tests for active navigation, back fallback, “见序”, and absence of first-position copy.
- [ ] Run focused frontend tests and confirm failure.
- [ ] Implement the route-aware shell, back control, revised information architecture, dashboard/history content, and visual tokens from selected concept 3.
- [ ] Run focused tests and confirm they pass.
- [ ] Commit Task 5 with `feat: redesign visibility dossier workspace`.

### Task 6: Migration, end-to-end verification, and handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/operator-guide.md`
- Modify: `apps/web/e2e/demo-flow.spec.ts`

**Interfaces:**
- Existing database upgrades with `alembic upgrade head` without losing rows.
- A user can complete merchant profile → precise questions → background scan → report → history.

- [ ] Upgrade a copy of the current SQLite database and confirm merchant, query, scan, result, and citation counts are unchanged.
- [ ] Run `pytest -q` and `ruff check app tests` in `services/api`.
- [ ] Run `npm.cmd test` and `npm.cmd run build` in `apps/web`.
- [ ] Run the focused Playwright flow against local API, worker, and frontend processes.
- [ ] Update operating documentation and commit with `docs: document visibility dossier workflow`.

