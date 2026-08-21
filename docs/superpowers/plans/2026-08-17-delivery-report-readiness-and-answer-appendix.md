# Delivery Report Readiness and Answer Appendix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make completed three-answer reports deliverable without requiring a first-batch recommendation, add visibility levels, and move complete answers into a web-only collapsed appendix.

**Architecture:** Keep delivery acceptance as a pure function in `delivery-readiness.ts` and add a second pure visibility-level helper there. Render only result summaries in the report body, render native per-question accordions in a final appendix, and hide that appendix with the existing print media stylesheet.

**Tech Stack:** TypeScript, React 19, Next.js, Testing Library, Vitest, CSS print media.

## Global Constraints

- The only blocking condition is fewer than 3 confirmed independent answers.
- First-batch recommendation remains visible as a non-blocking advanced goal.
- PDF output excludes complete raw answers.
- Web output retains complete raw answers in keyboard-accessible native disclosure controls.
- Preserve unrelated working-tree changes.

---

### Task 1: Readiness and visibility-level rules

**Files:**
- Modify: `apps/web/src/lib/delivery-readiness.ts`
- Test: `apps/web/tests/delivery-readiness.test.ts`

**Interfaces:**
- Consumes: `DeliveryReadinessInput` with confirmed answer, mention, and primary counts.
- Produces: `buildDeliveryReadiness(input)` and `deliveryVisibilityLevel(input) -> "等待完整实测" | "尚未建立可见性" | "初步可见" | "稳定可见" | "强势可见"`.

- [ ] **Step 1: Add failing rule tests**

Assert that 3 confirmed answers and 0 primary recommendations produce `accepted === true`, that the primary item has `blocking === false`, and that visibility levels map as follows: incomplete → `等待完整实测`, 0 mentions → `尚未建立可见性`, 1 mention → `初步可见`, 2 mentions → `稳定可见`, and any primary recommendation → `强势可见`.

- [ ] **Step 2: Run the focused test and verify RED**

```powershell
npm test -- tests/delivery-readiness.test.ts
```

Expected: failure because primary recommendation currently blocks delivery and the visibility helper does not exist.

- [ ] **Step 3: Implement the pure rules**

Add `mentionCount` to `DeliveryReadinessInput`, make the primary item non-blocking, remove the primary blocking reason, and export `deliveryVisibilityLevel`. The helper first checks `confirmedAnswerCount === 3`, then `primaryCount >= 1`, then mention thresholds 2, 1, and 0.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: all readiness tests pass.

### Task 2: Report summary, appendix, and print behavior

**Files:**
- Modify: `apps/web/src/app/delivery-report/page.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/delivery-report.test.tsx`

**Interfaces:**
- Consumes: `deliveryVisibilityLevel`, `workspace.latestRoundAnswers`, and readiness output.
- Produces: result-summary rows in section 02 and `.report-answer-appendix` native accordions after section 06.

- [ ] **Step 1: Add failing report behavior tests**

Use a mocked workspace with 3 confirmed answers, 3 supplementary mentions, and 0 primary recommendations. Assert that the print button is enabled, `稳定可见` is rendered, section 02 contains `补充提及 · 第 6 位`, the complete answer is initially not visible, and clicking the corresponding appendix summary reveals it.

- [ ] **Step 2: Run the focused report test and verify RED**

```powershell
npm test -- tests/delivery-report.test.tsx
```

Expected: failure because the report is blocked, has no visibility level, and renders full answers directly in section 02.

- [ ] **Step 3: Implement the report structure**

Pass `mentionCount` into readiness, calculate the visibility label, replace the first conclusion card, update section 02 to summary-only articles, and add a `.report-answer-appendix` section after section 06. Each answer uses `<details><summary>Q… · label · position</summary><p>full answer</p></details>` and defaults closed.

- [ ] **Step 4: Add print styling**

Inside `@media print`, set `.report-answer-appendix { display: none; }`. Keep the summary section visible and preserve existing report print layout rules.

- [ ] **Step 5: Run the focused report test and verify GREEN**

Run the command from Step 2. Expected: all delivery report tests pass.

### Task 3: Full verification and live-page inspection

**Files:**
- No code files.

**Interfaces:**
- Consumes: the complete web test suite and running local report.
- Produces: evidence that tests and the current merchant report match the approved design.

- [ ] **Step 1: Run the full web suite**

```powershell
npm test
```

Expected: zero failed tests.

- [ ] **Step 2: Inspect the current local delivery report**

Open the current merchant report and verify it reads “核心检测已完成”, “稳定可见”, permits printing, keeps all three summaries visible, and keeps full answers collapsed in the web-only appendix.

- [ ] **Step 3: Verify print CSS contract**

Confirm `.report-answer-appendix` is hidden under `@media print` and the result-summary class is not hidden by any print rule.
