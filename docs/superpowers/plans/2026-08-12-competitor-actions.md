# Competitor Reference and Recommendation Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add focused competitor-reference and actionable recommendation-rate pages while keeping the dashboard concise and merchant-scoped.

**Architecture:** Extend the existing dashboard response with deterministic action instructions derived from real coverage gaps. Reuse that response in two server-rendered detail pages, while dashboard components render only compact previews and merchant-preserving links.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Next.js App Router, React, TypeScript, Vitest, Testing Library.

## Global Constraints

- Use only latest real scan data; never create simulated competitors or evidence.
- Describe recommendation-rate improvement as increased retrieval, verification, and citation opportunity; never guarantee ranking.
- Preserve the selected merchant ID in every new link and page.
- Do not add a database table for this feature.

---

### Task 1: Action instruction contract

**Files:**
- Modify: `services/api/app/reports/router.py`
- Modify: `services/api/app/reports/schemas.py`
- Modify: `services/api/tests/reports/test_router.py`

**Interfaces:**
- Produces dashboard action fields: `description`, `steps`, `channels`, `materials`, `example`, `completionCriteria`, and `questions`.

- [ ] Add a failing dashboard route test that checks one real coverage gap returns all execution fields.
- [ ] Run `pytest tests/reports/test_router.py -q` and confirm the new assertion fails because fields are missing.
- [ ] Add deterministic per-category action templates and include their fields in dashboard output.
- [ ] Run the focused backend test and confirm it passes.

### Task 2: Dashboard previews and detail pages

**Files:**
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/components/action-list.tsx`
- Modify: `apps/web/src/components/competitor-table.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/competitors/page.tsx`
- Create: `apps/web/src/app/actions/page.tsx`
- Modify: `apps/web/src/components/app-shell.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: `apps/web/tests/dashboard.test.tsx`
- Modify: `apps/web/tests/real-data-pages.test.tsx`

**Interfaces:**
- Consumes: extended `DashboardData.actions` and existing `DashboardData.competitors`.
- Produces routes `/competitors?merchant=<id>` and `/actions?merchant=<id>`.

- [ ] Add failing component/page tests proving previews are capped, links preserve merchant ID, and detail pages expose complete evidence and steps.
- [ ] Run focused frontend tests and confirm failures are caused by missing links/pages/details.
- [ ] Extend TypeScript contracts and implement compact previews.
- [ ] Implement both detail pages with real-data empty/error states.
- [ ] Add focused styles for readable cards and collapsible evidence.
- [ ] Run focused frontend tests and confirm they pass.

### Task 3: Integrated verification

**Files:**
- Verify all files above.

- [ ] Run the complete API test suite.
- [ ] Run the complete web test suite and production build.
- [ ] Use the live browser to verify `总览 → 同类参照 → 返回 → 完整行动方案` while retaining the oral-clinic merchant.

