# Design QA

## Comparison targets

- Source visual truth:
  - `C:/Users/临渊羡鱼/AppData/Local/Temp/codex-clipboard-1973fc45-99ce-4970-ae93-5bb8636d4c4a.png`
  - `C:/Users/临渊羡鱼/AppData/Local/Temp/codex-clipboard-22c643a5-a339-4fd6-9e9c-ab8a4087f185.png`
- Rendered implementation:
  - `design-qa-profile-desktop.png`
  - `design-qa-profile-mobile.png`
  - `design-qa-queries-desktop-final.png`
  - `design-qa-queries-mobile-final.png`
- Combined comparison evidence:
  - `design-qa-profile-comparison.png`
  - `design-qa-queries-comparison-final.png`
- State: merchant profile and query library for 澜沧皓雅口腔门诊部; authentication disabled only in the local QA runtime.
- Desktop viewport: 1520 × 960 CSS px, device scale factor 1. Captures: source profile 1522 × 965 px, source queries 1497 × 963 px, implementation profile 1520 × 957 px, implementation queries 1505 × 947 px.
- Mobile viewport: 390 × 844 CSS px, device scale factor 1. Browser content captures are 375 × 811 px after scrollbar/chrome reservation.
- Density normalization: desktop source and implementation images were normalized to 1520 px wide before combined comparison.

## Findings

- No remaining P0, P1, or P2 issues.
- Typography: existing serif display hierarchy and compact sans-serif UI labels are preserved. Long question text now wraps to two lines instead of being clipped.
- Spacing and layout rhythm: confirmed facts use a balanced two-column ledger on desktop and a single-column ledger on mobile. Query columns have stable proportions, and pending actions stack with consistent spacing.
- Colors and tokens: the existing paper, ink, green, orange, line, and status colors are unchanged.
- Image quality: these screens contain no content imagery or custom icon assets requiring fidelity review.
- Copy and content: labels, merchant facts, query text, statuses, and actions are unchanged.
- Accessibility: confirmed facts and row actions now expose named groups; desktop and mobile layouts retain readable order.

## Comparison history

1. Initial comparison found two P2 density problems: merchant facts collapsed into a narrow vertical strip, and table type/status/action content wrapped into cramped columns. Fixed with a responsive two-column fact ledger, explicit table column proportions, non-wrapping compact labels, and grouped row actions.
2. Post-fix comparison found one remaining P2: long question inputs were visually clipped on desktop and mobile. Replaced the single-line editor with a two-line wrapping editor. The final desktop and mobile captures show the full long question and no horizontal overflow.

## Browser verification

- Loaded the merchant profile and query library through the local Next.js runtime.
- Verified desktop and mobile responsive states.
- Verified route navigation and page rendering; mutation behavior remains covered by the focused component tests and was not triggered against the local data set.
- Browser console errors checked: none.

## Implementation checklist

- [x] Desktop profile facts use two columns.
- [x] Mobile profile facts remain one column.
- [x] Query table columns no longer collapse labels vertically.
- [x] Pending actions remain visually grouped.
- [x] Long questions wrap instead of clipping.
- [x] Focused tests pass.

## Follow-up polish

- No P3 follow-up is required for this scope.

final result: passed
