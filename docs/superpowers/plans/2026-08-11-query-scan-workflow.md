# Query Library and Background Scan Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the real query library to persistent review operations and create non-blocking Ark scan jobs that a separate worker processes in the background.

**Architecture:** Keep browser mutations same-origin by calling Next.js server actions, which then use the existing FastAPI endpoints. Use URL-backed category tabs for deterministic filtering and a small client refresh component that calls `router.refresh()` every two seconds while a scan is non-terminal. Keep the existing database schema and independent Python worker.

**Tech Stack:** Next.js 16 App Router, React, TypeScript, Vitest/Testing Library, FastAPI, SQLAlchemy, SQLite, existing Ark Responses adapter.

## Global Constraints

- A scan includes every query in the selected query set where `review_status=approved` and `is_enabled=true`.
- Creating a scan returns immediately; model requests run only in the independent worker.
- Query text saves on blur; review and enabled state save immediately.
- Failed mutations restore the previous visible value and show a readable error.
- Production UI must not introduce simulated merchants, answers, scans, metrics, or reports.
- Do not expose `ARK_API_KEY` to browser code or committed files.

---

### Task 1: Server-side mutation boundary

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/lib/contracts.ts`
- Create: `apps/web/src/app/queries/actions.ts`
- Test: `apps/web/tests/query-actions.test.ts`

**Interfaces:**
- Consumes: existing FastAPI `PATCH /queries/{query_id}` and `POST /scan-runs` endpoints.
- Produces: `updateQueryAction(queryId, changes)` and `createScanAction(merchantId, querySetId)` returning serializable `{ ok, data?, error? }` results.

- [ ] **Step 1: Write failing mutation tests**

Test that `updateQueryAction("q1", { reviewStatus: "approved", isEnabled: true })` sends the API payload `{review_status:"approved", is_enabled:true}` and that `createScanAction("m1", "set1")` sends `{merchant_id:"m1", query_set_id:"set1", adapter_name:"ark"}`. Assert a 409 response becomes the Chinese no-approved-query message instead of throwing an opaque error.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `npm.cmd test -- tests/query-actions.test.ts`

Expected: failure because the action module and mutation functions do not exist.

- [ ] **Step 3: Implement typed API mutations and server actions**

Add `QueryUpdatePayload`, `ActionResult<T>`, and a narrow created-scan result type. Keep API base URL and credentials on the server. Convert component camelCase fields to FastAPI snake_case fields inside the action and return readable error strings for 404, 409, and generic failures.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `npm.cmd test -- tests/query-actions.test.ts`

Expected: all action tests pass.

- [ ] **Step 5: Commit the isolated boundary**

Stage only the four Task 1 files and commit with `feat: add query and scan server actions`.

### Task 2: Persistent query workspace and reliable category navigation

**Files:**
- Modify: `apps/web/src/app/queries/page.tsx`
- Modify: `apps/web/src/components/query-table.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/query-table.test.tsx`
- Test: `apps/web/tests/real-data-pages.test.tsx`

**Interfaces:**
- Consumes: Task 1 `updateQueryAction` and `createScanAction`.
- Produces: query category links with counts, persistent row controls, save-state feedback, and a background-scan launcher.

- [ ] **Step 1: Replace the existing local-only test with failing behavior tests**

Cover these separate cases: category links preserve `merchant` and add `category`; the selected category renders only matching rows; blurring changed text invokes the update action; approving/rejecting/toggling invokes the action and rolls back on `{ok:false}`; the scan button is disabled at zero eligible queries; a successful create action calls `router.push("/scans/<id>")`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `npm.cmd test -- tests/query-table.test.tsx tests/real-data-pages.test.tsx`

Expected: failures for missing persistent actions, count labels, category URL state, and scan launcher.

- [ ] **Step 3: Implement URL-backed category filtering**

Read `category` from page search parameters, validate it against `all|geo|category|product|price|occasion|need`, and render category links such as `/queries?merchant=<id>&category=price`. Display each label with its count. Pass the selected subset and whole-set eligibility metadata to the client workspace.

- [ ] **Step 4: Implement optimistic persistence with rollback**

Track per-row `idle|saving|saved|error`. On blur, skip unchanged text; otherwise call the action. Review buttons and enabled checkboxes call immediately. Disable only the row currently saving. On failure restore the previous row and show the returned error near that row.

- [ ] **Step 5: Implement background scan creation**

Render “开始后台检测（N 条）”. Disable it when `N=0` or while creating. On success push to `/scans/{id}` immediately. On failure keep the page usable and render the action error. Batch approval updates only pending rows and reports a partial failure count if some calls fail.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `npm.cmd test -- tests/query-table.test.tsx tests/real-data-pages.test.tsx`

Expected: query interaction and real-page tests pass.

- [ ] **Step 7: Commit the query workflow**

Stage only Task 2 files and commit with `feat: persist query review workflow`.

### Task 3: Non-blocking scan progress and valid actions

**Files:**
- Create: `apps/web/src/components/scan-auto-refresh.tsx`
- Modify: `apps/web/src/app/scans/[id]/page.tsx`
- Modify: `apps/web/src/app/scans/page.tsx`
- Modify: `apps/web/src/components/scan-progress.tsx`
- Modify: `apps/web/src/components/action-list.tsx`
- Test: `apps/web/tests/scan-auto-refresh.test.tsx`
- Test: `apps/web/tests/real-data-pages.test.tsx`

**Interfaces:**
- Consumes: existing server-rendered `getScanRun` data and Next router refresh.
- Produces: `ScanAutoRefresh({ active, intervalMs?: 2000 })`, terminal-aware progress UI, and only valid navigation targets.

- [ ] **Step 1: Write failing progress tests**

Use fake timers to assert `router.refresh()` runs every two seconds when active and never runs when terminal. Assert failed results no longer render a nonfunctional retry button. Assert completed/partial runs show report links while queued/running runs show only the detail link.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `npm.cmd test -- tests/scan-auto-refresh.test.tsx tests/real-data-pages.test.tsx`

Expected: failure because refresh behavior and terminal-aware actions do not exist.

- [ ] **Step 3: Implement polling through server refresh**

Mount `ScanAutoRefresh` only for `queued` and `running` states. Its effect starts one interval, invokes `router.refresh()`, and clears the interval on unmount or terminal rerender. It makes no direct browser call to port 8000, avoiding CORS and keeping the API key server-side.

- [ ] **Step 4: Remove dead controls and fix report navigation**

Remove the static retry button and the `/reports` index link that has no route. Add explicit report links for completed and partial run IDs. Keep failure counts as non-clickable explanatory text.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `npm.cmd test -- tests/scan-auto-refresh.test.tsx tests/real-data-pages.test.tsx`

Expected: all scan UI tests pass.

- [ ] **Step 6: Commit the scan UI**

Stage only Task 3 files and commit with `feat: show background scan progress`.

### Task 4: Worker startup, integration verification, and operator handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/operator-guide.md`
- Test: existing frontend and backend suites.

**Interfaces:**
- Consumes: `python -m app.scans.worker`, FastAPI API, and Next.js frontend.
- Produces: a documented three-process startup and verified end-to-end workflow.

- [ ] **Step 1: Update startup documentation**

Document three separate PowerShell windows: API with Uvicorn on port 8000, worker with `python -m app.scans.worker`, and frontend with `npm.cmd run dev` on port 3000. Explain that the page returns immediately while the worker continues, and that stopping the worker leaves tasks queued rather than losing them.

- [ ] **Step 2: Run the complete automated verification once**

Run frontend: `npm.cmd test` and `npm.cmd run build` in `apps/web`.

Run backend: `.\.venv\Scripts\python.exe -m pytest -q` and `.\.venv\Scripts\python.exe -m ruff check app tests scripts` in `services/api`.

Expected: every command exits zero with no test failures.

- [ ] **Step 3: Start or restart the three runtime processes**

Start API, worker, and frontend against `merchant-exposure.db`. Confirm `/health` returns `{"status":"ok"}` and the frontend returns HTTP 200.

- [ ] **Step 4: Perform one bounded UI integration check without creating a paid scan**

Verify all six category URLs show five rows, change one rejected query to approved/enabled and reload to prove persistence, then restore that query to its original rejected/disabled state. Verify the scan button becomes enabled without clicking it, so no external Ark request or cost is incurred.

- [ ] **Step 5: Commit documentation and handoff**

Stage only README and operator guide changes and commit with `docs: explain background worker workflow`.

