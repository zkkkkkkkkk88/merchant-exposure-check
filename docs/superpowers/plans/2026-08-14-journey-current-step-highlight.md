# Journey Current-Step Highlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the six-step journey bar visibly and accessibly identify the page or anchored section the user is currently viewing.

**Architecture:** The existing `JourneyProgress` client component derives a presentation-only current step from `usePathname()` and `window.location.hash`. Backend completion and readiness statuses remain unchanged; a separate `journey-current` class and `aria-current="step"` override their presentation only for the active location.

**Tech Stack:** Next.js 16, React, TypeScript, Vitest, Testing Library, CSS.

## Global Constraints

- Current location is determined from the actual URL, not `progress.current_step`.
- Current styling takes precedence over completed, ready, and pending styling without changing those status values.
- Hash changes update the highlight without a page refresh.
- `/delivery-report` does not highlight a journey step.

---

### Task 1: Route-aware current-step highlight

**Files:**
- Modify: `apps/web/tests/navigation.test.tsx`
- Modify: `apps/web/src/components/journey-progress.tsx`
- Modify: `apps/web/src/styles/globals.css`

**Interfaces:**
- Consumes: `usePathname(): string`, `window.location.hash`, and `JourneyProgressData.steps`.
- Produces: one journey link with `aria-current="step"` and one journey list item with class `journey-current` when the URL maps to a step.

- [ ] **Step 1: Write the failing route and hash tests**

Add assertions inside the real `AppShell` integration test that scope queries to `section[aria-label="商家提升进度"]`:

```tsx
expect(within(progress).getByRole("link", { name: /平台查缺/ }))
  .toHaveAttribute("aria-current", "step");
expect(within(progress).getByRole("link", { name: /手机实测/ }))
  .not.toHaveAttribute("aria-current");
```

Add a second test with `window.history.replaceState({}, "", "/mobile-checks?merchant=m1#improvement-playbook")` and assert only “执行优化” has `aria-current="step"`.

- [ ] **Step 2: Run the test to verify RED**

Run:

```powershell
npm.cmd test -- --run tests/navigation.test.tsx
```

Expected: FAIL because no journey link currently exposes `aria-current="step"`.

- [ ] **Step 3: Implement URL-to-step mapping**

In `journey-progress.tsx`, use `usePathname()` plus hash state and a `hashchange` listener. Map merchant, query, platform audit, mobile check, action anchor, and retest anchor URLs to their corresponding keys. Add `journey-current` and `aria-current="step"` only to the matching step.

- [ ] **Step 4: Add high-contrast current styles**

In `globals.css`, style `.journey-current` after all status selectors with a thicker accent top border, pale accent background, solid accent number, bold accent label, and a visible hover/focus treatment. Keep completed green and pending gray for non-current steps.

- [ ] **Step 5: Run focused and full frontend verification**

Run:

```powershell
npm.cmd test -- --run tests/navigation.test.tsx
npm.cmd test
npx.cmd tsc --noEmit
```

Expected: navigation tests pass, all frontend tests pass, and TypeScript exits with code 0.

- [ ] **Step 6: Commit**

```powershell
git add apps/web/tests/navigation.test.tsx apps/web/src/components/journey-progress.tsx apps/web/src/styles/globals.css docs/superpowers/plans/2026-08-14-journey-current-step-highlight.md
git commit -m "fix: highlight current journey step"
```
