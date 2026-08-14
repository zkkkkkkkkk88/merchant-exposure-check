# Delivery Report, Journey Progress, and Mobile Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a printable merchant delivery report, an honest six-step global journey, and fully accessible mobile navigation.

**Architecture:** Add one read-only progress aggregation endpoint over existing merchant, query, audit, and mobile tables. Render progress globally through a small client component; build the report by composing existing API responses, and use browser print CSS instead of a PDF dependency.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js, React, Vitest, Pytest, CSS print media.

## Global Constraints

- Never claim external publishing is complete without evidence.
- Never fabricate report sections when source data is missing.
- Do not add a PDF dependency; use browser print/Save as PDF.
- Preserve existing design tokens and merchant scoping.

---

### Task 1: Six-step journey API

**Files:**
- Modify: `services/api/app/reports/schemas.py`
- Modify: `services/api/app/reports/router.py`
- Test: `services/api/tests/reports/test_router.py`

- [ ] Add failing tests for empty, audited, first mobile round, and comparable second-round states.
- [ ] Implement `GET /merchants/{merchant_id}/journey-progress` with six stable step keys and honest statuses.
- [ ] Run the focused API tests.

### Task 2: Global journey and mobile navigation

**Files:**
- Create: `apps/web/src/components/journey-progress.tsx`
- Modify: `apps/web/src/components/app-shell.tsx`
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/app-shell.test.tsx`

- [ ] Add failing component tests for progress links and an accessible expandable mobile menu.
- [ ] Implement the progress fetch/render component and full mobile navigation.
- [ ] Add responsive styling and run focused tests.

### Task 3: Printable merchant delivery report

**Files:**
- Create: `apps/web/src/app/delivery-report/page.tsx`
- Create: `apps/web/src/components/print-report-button.tsx`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/components/app-shell.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/delivery-report.test.tsx`

- [ ] Add failing tests for primary recommendation conclusion, answers, repeated competitors, source gaps, platform audit, actions, comparison, empty states, and print control.
- [ ] Compose the existing merchant/profile/query/mobile/audit data into a merchant-scoped report page.
- [ ] Add print-only layout and disclaimer, then run focused tests.

### Task 4: Verification

- [ ] Run all API tests.
- [ ] Run all web tests and TypeScript checking.
- [ ] Run `git diff --check` and inspect only the scoped diff.
