# Mobile Answer Collapse and Competitor Grouping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bottom “收起答案” control and correctly merge differently-described occurrences of the same competitor.

**Architecture:** Keep the native `<details>` answer container and add a small client-side close control that collapses and scrolls back to its summary. Normalize competitor identity in the backend, count unique question positions, exclude the target merchant explicitly, and preserve the first full answer name for display.

**Tech Stack:** React 19, Next.js, Testing Library/Vitest, Python 3.13, SQLAlchemy, pytest.

## Global Constraints

- Preserve the existing top “查看上一轮问题与答案” entry.
- Show only competitors appearing in at least two questions and limit output to three.
- Sort competitors by question count descending, then first answer appearance.
- Do not include the target merchant in competitor cards.
- Preserve unrelated working-tree changes.

---

### Task 1: Merge competitor aliases and exclude the target merchant

**Files:**
- Modify: `services/api/app/mobile_checks/playbook.py`
- Test: `services/api/tests/mobile_checks/test_playbook.py`

**Interfaces:**
- Consumes: `_entries(answer)` and `_same_entity(left, right)`.
- Produces: `_competitor_reasons(results, sources, merchant_name, exclude_public_oral=False) -> list[dict]`.

- [ ] **Step 1: Write the failing regression test**

Create three confirmed results whose answers contain `澜沧王天佑口腔诊所（县城老牌，医保定点）`, `澜沧王天佑口腔诊所（医保定点）`, and `澜沧王天佑口腔（总店+华庭分店）`. Include the target merchant in all three answers. Assert that `build_recommendation_playbook(...)` returns one 王天佑 card with `questionCount == 3` and no card matching the target merchant.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/mobile_checks/test_playbook.py -q
```

Expected: FAIL because the old grouping treats parenthetical variants as separate entities or because the target merchant is eligible for competitor output.

- [ ] **Step 3: Implement the minimal backend fix**

Change `_competitor_reasons` to accept `merchant_name: str`. Before adding an entry, skip it when `_same_entity(name, merchant_name)` is true. Continue grouping aliases with `_same_entity`, store question positions in a set, and retain the first matched name. Pass `merchant.name` from `build_recommendation_playbook`.

- [ ] **Step 4: Run the focused backend tests and verify GREEN**

Run the command from Step 2. Expected: all tests in `test_playbook.py` pass.

### Task 2: Add a bottom collapse control to complete answers

**Files:**
- Modify: `apps/web/src/components/latest-mobile-round-answers.tsx`
- Modify: `apps/web/src/styles/globals.css`
- Test: `apps/web/tests/mobile-checks.test.tsx`

**Interfaces:**
- Consumes: `MobileWorkspaceData["latestRoundAnswers"]`.
- Produces: the existing answer `<details>` plus a bottom button named `收起答案`.

- [ ] **Step 1: Write the failing interaction test**

In the completed-state test, open `查看上一轮问题与答案`, assert the answer is visible, click `screen.getByRole("button", { name: "收起答案" })`, then assert the answer is no longer visible.

- [ ] **Step 2: Run the focused frontend test and verify RED**

Run:

```powershell
npm test -- tests/mobile-checks.test.tsx
```

Expected: FAIL because no `收起答案` button exists.

- [ ] **Step 3: Implement the minimal client interaction**

Mark `latest-mobile-round-answers.tsx` as a client component. Hold a `details` ref, add a bottom `<button type="button">收起答案</button>`, and on click set `details.open = false` before calling `details.scrollIntoView({ block: "start" })`. Add a focused CSS class that aligns the button at the bottom right and uses the existing accent/line tokens.

- [ ] **Step 4: Run the focused frontend test and verify GREEN**

Run the command from Step 2. Expected: all tests in `mobile-checks.test.tsx` pass.

### Task 3: Verify the current workspace behavior

**Files:**
- No code files.

**Interfaces:**
- Consumes: the running API workspace endpoint.
- Produces: verification evidence for the current merchant.

- [ ] **Step 1: Run both focused suites once after all code changes**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/mobile_checks/test_playbook.py tests/mobile_checks/test_service.py -q
npm test -- tests/mobile-answer-parser.test.ts tests/mobile-checks.test.tsx
```

Expected: zero failures.

- [ ] **Step 2: Restart the API service so it loads the new normalization code**

Use the existing local service launch method under the normal Windows user, retaining the current SQLite database and environment configuration.

- [ ] **Step 3: Check the live workspace response**

Read `/merchants/4e3f2f30-3777-48b3-8b80-dcce11c51841/mobile-checks/workspace` and assert a 王天佑 competitor card has `questionCount == 3` and no competitor card matches `澜沧皓雅口腔门诊部`.
