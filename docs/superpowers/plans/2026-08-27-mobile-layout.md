# Mobile Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the existing application a phone-specific navigation and content hierarchy that is easy to present at 390–430px widths without changing the desktop experience.

**Architecture:** Keep the existing pages, routes, data contracts, colors, typography and desktop rail. At phone widths, AppShell switches to a compact top bar plus five-item bottom navigation and a More sheet; dense desktop tables expose the same records through CSS-backed mobile cards, while long workflow content collapses into clear sections. Responsive behavior is expressed through semantic classes and component markup rather than page duplication.

**Tech Stack:** React, Next.js App Router, semantic HTML, CSS media queries, Vitest and Testing Library, in-app Browser visual verification

**Spec:** `docs/superpowers/specs/2026-08-27-readonly-demo-and-mobile-layout-design.md`

## Global Constraints

- Desktop behavior at 1440px remains visually and functionally unchanged.
- Primary phone verification viewports are exactly `390 × 844` and `430 × 932`.
- The global phone breakpoint is `720px`; existing wider tablet rules may remain where they do not conflict.
- Preserve the current deep green, warm paper, orange accent, serif headings and existing copy.
- Do not create duplicate mobile routes or a separate mobile application.
- No page-level accidental horizontal scrolling is allowed.
- Touch targets are at least 44px high and bottom navigation respects safe-area insets.
- Demo restrictions from the access plan remain visible and enforceable in the mobile UI.

---

### Task 1: Replace the phone menu with a top bar, bottom navigation and More sheet

**Files:**
- Modify: `apps/web/src/components/app-shell.tsx`
- Create: `apps/web/src/components/mobile-merchant-label.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: `apps/web/tests/navigation.test.tsx`
- Modify: `apps/web/tests/layout.test.tsx`

**Interfaces:**
- Produces: five mobile destinations: `首页`, `画像`, `检测`, `报告`, `更多`.
- Produces: a More sheet containing `平台查缺`, `问题策略`, `手机实测`, `历史`, and `方法说明`.
- Produces: `MobileMerchantLabel({ merchantId })`, which loads the existing merchant name through a read-only request and falls back to `当前商家` while unavailable.
- Consumes: current merchant propagation through `withMerchant(href)`.

- [ ] **Step 1: Add failing navigation structure tests**

Assert that the mobile navigation contains exactly the five primary labels, that More exposes all secondary destinations, that merchant IDs remain attached to scoped links, and that the current route receives `aria-current="page"` either on its primary item or its secondary More item. Add a component test proving the merchant label renders a fetched merchant name and uses `当前商家` when the read request fails.

- [ ] **Step 2: Run the navigation tests and verify the old eight-link menu fails them**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/navigation.test.tsx tests/layout.test.tsx
```

Expected: FAIL because the current mobile menu duplicates all eight desktop links.

- [ ] **Step 3: Refactor only the mobile shell markup**

Keep the desktop `navigation` array and rail unchanged. Add:

```ts
const mobilePrimaryNavigation = [
  ["首页", "/"],
  ["画像", "/merchants"],
  ["检测", "/scans"],
  ["报告", "/delivery-report"],
] as const;

const mobileMoreNavigation = [
  ["平台查缺", "/platform-audits"],
  ["问题策略", "/queries"],
  ["手机实测", "/mobile-checks"],
  ["历史", "/history"],
  ["方法说明", "/methodology"],
] as const;
```

Render four route links plus a More button in a bottom `<nav>`. Render the secondary links in a dialog-like sheet with a heading, close button, focus-visible styles, `aria-expanded`, `aria-controls`, and Escape-key close behavior. Close the sheet after navigation.

Implement `MobileMerchantLabel` as a client component that receives the already resolved `merchantId`, performs only `GET /merchants/{id}` through the same browser API base used by `ServiceStatus`, aborts on unmount, and never triggers a write or merchant switch. Show the merchant name in the top bar and use the fallback text when no merchant is selected or the request fails.

- [ ] **Step 4: Add phone-only shell styling**

At `max-width: 720px`:

- keep the top bar sticky and show brand, current merchant abbreviation, and demo badge;
- position bottom nav fixed with `padding-bottom: env(safe-area-inset-bottom)`;
- give each item a minimum height of 52px;
- add bottom padding to `.app-content` equal to nav height plus safe area;
- render the More sheet above the bottom nav with a backdrop;
- remove the old two-column dropdown menu at phone widths.

At widths above `720px`, preserve existing tablet and desktop navigation behavior.

- [ ] **Step 5: Run the focused tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/navigation.test.tsx tests/layout.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit the mobile shell**

```powershell
git add apps/web/src/components/app-shell.tsx apps/web/src/components/mobile-merchant-label.tsx apps/web/src/styles/globals.css apps/web/tests/navigation.test.tsx apps/web/tests/layout.test.tsx
git commit -m "feat: add phone bottom navigation"
```

---

### Task 2: Establish reusable phone page hierarchy and compact journey progress

**Files:**
- Modify: `apps/web/src/styles/globals.css`
- Modify: `apps/web/src/components/journey-progress.tsx`
- Modify: `apps/web/tests/navigation.test.tsx`
- Modify: `apps/web/tests/home.test.tsx`

**Interfaces:**
- Produces: phone rules for `.dashboard-header`, `.page-header`, `.header-actions`, `.workspace-page`, `.dashboard-grid`, and `.journey-progress`.
- Produces: a compact current-step summary with an expandable full step list.

- [ ] **Step 1: Add failing semantic tests for journey progress**

Verify the component renders the current step name in a compact summary, places the full ordered list in a disclosure, and retains accessible link names for every step.

- [ ] **Step 2: Convert the phone journey strip into a disclosure**

Keep the desktop ordered list visible. On phone, show the current step and completion count in a `<summary>` and place the same ordered links in its `<details>` body. Do not create a second source of step truth; map the existing step array for both presentations.

- [ ] **Step 3: Add reusable phone spacing and stacking rules**

At `max-width: 720px`:

```css
.workspace-page,
.dashboard,
.delivery-report { padding-left: 18px; padding-right: 18px; }

.dashboard-header,
.page-header,
.header-actions,
.metric-section-heading { align-items: stretch; display: grid; gap: 16px; }

.header-actions .button,
.page-header > .button,
.metric-section-heading .button { min-height: 44px; width: 100%; }
```

Use existing class names and add page-specific overrides only when a shared rule cannot express the layout. Set phone heading sizes with `clamp()` and preserve the existing typefaces.

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/navigation.test.tsx tests/home.test.tsx tests/dashboard.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit page hierarchy changes**

```powershell
git add apps/web/src/components/journey-progress.tsx apps/web/src/styles/globals.css apps/web/tests
git commit -m "feat: simplify phone page hierarchy"
```

---

### Task 3: Convert operational tables into phone information cards

**Files:**
- Modify: `apps/web/src/components/competitor-table.tsx`
- Modify: `apps/web/src/components/query-table.tsx`
- Modify: `apps/web/src/components/source-gap-table.tsx`
- Modify: `apps/web/src/app/scans/page.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: `apps/web/tests/query-table.test.tsx`
- Modify: `apps/web/tests/dashboard.test.tsx`
- Modify: `apps/web/tests/mobile-checks.test.tsx`
- Create: `apps/web/tests/mobile-table-semantics.test.tsx`

**Interfaces:**
- Produces: `data-label` on every mobile table value cell and `data-primary` on the record title cell.
- Produces: `.responsive-record-table`, which remains a semantic table on desktop and reads as bordered record cards on phone.

- [ ] **Step 1: Write failing markup tests**

For competitor, query, source-gap, and scan tables, assert every body value has a visible phone label through `data-label`, record headings remain `<th scope="row">`, and action controls stay associated with the same record.

- [ ] **Step 2: Add semantic labels to each table**

Add `className="responsive-record-table"`. Use the existing Chinese column names as exact `data-label` values. Set `scope="col"` on header cells and `scope="row" data-primary="true"` on record-name cells. Do not duplicate values into a second mobile-only DOM tree.

For the source-gap comparison, each entity cell uses its entity name as `data-label`; the source/fact row heading remains the card title.

- [ ] **Step 3: Add shared phone card CSS**

At `max-width: 720px`, hide only the visual table header, then render `table`, `tbody`, and `tr` as blocks. Each row becomes a bordered card; each value cell becomes a two-column grid of label and value. Long answers wrap with `overflow-wrap:anywhere`. Action cells span both columns. Preserve table semantics in markup and do not apply `display: contents`.

- [ ] **Step 4: Remove page-level horizontal overflow from converted tables**

Set converted `.table-wrap` containers to `overflow: visible` on phone. Keep local horizontal scrolling only for genuinely comparative matrices that cannot be represented record-by-record, and add `.mobile-table-hint` immediately before those matrices.

- [ ] **Step 5: Run table tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/mobile-table-semantics.test.tsx tests/query-table.test.tsx tests/dashboard.test.tsx tests/mobile-checks.test.tsx tests/scan-report.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit mobile record cards**

```powershell
git add apps/web/src/components apps/web/src/app/scans/page.tsx apps/web/src/styles/globals.css apps/web/tests
git commit -m "feat: render phone tables as record cards"
```

---

### Task 4: Reorder and collapse dense dashboard and workflow content

**Files:**
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/components/visibility-stage.tsx`
- Modify: `apps/web/src/components/metric-strip.tsx`
- Modify: `apps/web/src/components/mobile-check-workspace.tsx`
- Modify: `apps/web/src/components/latest-mobile-round-answers.tsx`
- Modify: `apps/web/src/components/platform-audit-matrix.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: `apps/web/tests/home.test.tsx`
- Modify: `apps/web/tests/mobile-check-workspace.test.tsx`
- Modify: `apps/web/tests/platform-audits.test.tsx`

**Interfaces:**
- Produces: phone-first order of conclusion, metrics, current stage, and priority action on the dashboard.
- Produces: semantic disclosures for long answers, source evidence, completed rounds, and secondary platform fields.

- [ ] **Step 1: Add failing content-order and disclosure tests**

Assert the dashboard DOM order is merchant conclusion, key metrics, current stage, priority actions, trend, query coverage, competitors. Assert long mobile answers and secondary platform details have named `<summary>` controls and are collapsed by default.

- [ ] **Step 2: Reorder existing dashboard sections without changing data calls**

Move existing components in `page.tsx`; do not alter API requests or computed metrics. Add semantic section headings where a moved component lacks one.

- [ ] **Step 3: Collapse long workflow evidence**

Wrap existing long answer bodies, source lists and secondary audit details in `<details>`. Summaries must state what will open, such as `查看完整回答与来源` or `查看其余平台字段`. Keep status, mention level and the primary recommendation visible outside the disclosure.

- [ ] **Step 4: Add phone-specific metric and workflow grids**

Use two columns for short numeric metrics and one column for narrative cards. Remove fixed minimum widths that exceed 390px. Ensure buttons and selectors wrap instead of shrinking text.

- [ ] **Step 5: Run focused workflow tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/home.test.tsx tests/dashboard.test.tsx tests/mobile-check-workspace.test.tsx tests/mobile-answer-parser.test.ts tests/platform-audits.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit phone content hierarchy**

```powershell
git add apps/web/src/app/page.tsx apps/web/src/components apps/web/src/styles/globals.css apps/web/tests
git commit -m "feat: prioritize phone presentation content"
```

---

### Task 5: Make merchant profiles and delivery reports presentation-friendly on phone

**Files:**
- Modify: `apps/web/src/components/profile-editor.tsx`
- Modify: `apps/web/src/app/merchants/[id]/page.tsx`
- Modify: `apps/web/src/app/delivery-report/page.tsx`
- Modify: `apps/web/src/components/public-channel-maintenance.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Modify: `apps/web/tests/merchant-profile.test.tsx`
- Modify: `apps/web/tests/delivery-report.test.tsx`

**Interfaces:**
- Consumes: demo role and locked-action behavior from the access implementation plan.
- Produces: a read-first profile presentation for demo visitors and a phone chapter flow for delivery reports.

- [ ] **Step 1: Add failing tests for phone-readable structure**

Verify profile facts use named sections and report sections remain in the order: conclusion, evidence/visibility, opportunity, action recommendations. Verify demo profile editing controls are marked as administrator-only while fact values remain visible.

- [ ] **Step 2: Separate profile reading from editing emphasis**

Keep one route and one dataset. Place confirmed facts in the primary section and the import/edit form in a clearly named administration section. On phone, the administration section is collapsed by default for admin and visibly locked for demo; existing values are never hidden from demo.

- [ ] **Step 3: Tighten delivery report chapters**

Keep the existing report content and print structure. At phone widths, make conclusion metrics a two-column grid, narrative sections single-column, platform and channel records card-based, and long answer appendices collapsed. The print media rules must continue hiding app navigation and must not inherit phone-only fixed navigation spacing.

- [ ] **Step 4: Run focused profile and report tests**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/merchant-profile.test.tsx tests/merchant-form.test.tsx tests/delivery-report.test.tsx tests/delivery-readiness.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit profile and report phone layouts**

```powershell
git add apps/web/src/components/profile-editor.tsx apps/web/src/components/public-channel-maintenance.tsx apps/web/src/app/merchants/[id]/page.tsx apps/web/src/app/delivery-report/page.tsx apps/web/src/styles/globals.css apps/web/tests
git commit -m "feat: optimize phone profile and report views"
```

---

### Task 6: Verify phone viewports and desktop regression

**Files:**
- Create: `docs/audits/mobile-layout/01-home-390.png`
- Create: `docs/audits/mobile-layout/02-profile-390.png`
- Create: `docs/audits/mobile-layout/03-queries-390.png`
- Create: `docs/audits/mobile-layout/04-scans-430.png`
- Create: `docs/audits/mobile-layout/05-mobile-checks-430.png`
- Create: `docs/audits/mobile-layout/06-delivery-report-430.png`
- Create: `docs/audits/mobile-layout/07-home-desktop-1440.png`
- Create: `docs/audits/mobile-layout/audit-notes.md`

**Interfaces:**
- Consumes: the completed access and mobile implementation plans.
- Produces: current-run visual evidence at the required viewports and a concise list of accepted states or fixes.

- [ ] **Step 1: Run the relevant automated tests once**

Run:

```powershell
cd apps/web
npm.cmd test -- --run tests/navigation.test.tsx tests/layout.test.tsx tests/home.test.tsx tests/query-table.test.tsx tests/mobile-table-semantics.test.tsx tests/mobile-check-workspace.test.tsx tests/merchant-profile.test.tsx tests/delivery-report.test.tsx tests/demo-mode.test.tsx
npm.cmd run build
```

Expected: all selected tests PASS and production build succeeds.

- [ ] **Step 2: Capture the six required phone states in the in-app Browser**

Use demo credentials and current saved data. At `390 × 844`, capture home, merchant profile and query strategy. At `430 × 932`, capture scans, mobile checks and delivery report. Before accepting each screenshot, confirm the page is loaded, the correct merchant is selected, no loading overlay is present, and the screenshot contains the intended state.

- [ ] **Step 3: Inspect each accepted screenshot**

Check for page-level horizontal overflow, cropped text, overlapping fixed bars, hidden buttons, touch targets below 44px, unreadable labels, broken borders, inconsistent radii and dense sections that should be collapsed. Record each observation in `audit-notes.md` next to its screenshot name and fix every high-impact issue before continuing.

- [ ] **Step 4: Capture the desktop regression state**

Reset the phone viewport, use a `1440px` wide viewport, and capture the home page. Compare it with the pre-change design language: left navigation rail, header alignment, grid columns, colors, typography and spacing must remain intact.

- [ ] **Step 5: Re-check only changed visual states after fixes**

Reload affected pages and recapture only screenshots whose code changed after Step 3. Do not repeat the entire screenshot set when unrelated pages were unchanged.

- [ ] **Step 6: Commit accepted audit evidence**

```powershell
git add docs/audits/mobile-layout
git commit -m "test: verify readonly mobile presentation"
```
