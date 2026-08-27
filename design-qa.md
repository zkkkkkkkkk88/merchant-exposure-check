# Login split-screen design QA

## Evidence

- Source visual truth: `C:\\Users\\临渊羡鱼\\AppData\\Local\\Temp\\codex-clipboard-8b0fa24d-6bdf-4232-b7f2-c1bc6162de01.png`
- Desktop implementation: `C:\\Users\\临渊羡鱼\\Documents\\ChatGPT\\nine\\docs\\audits\\login-split-desktop.png`
- Mobile implementation: `C:\\Users\\临渊羡鱼\\Documents\\ChatGPT\\nine\\docs\\audits\\login-split-mobile.png`
- Full-view comparison: `C:\\Users\\临渊羡鱼\\Documents\\ChatGPT\\nine\\docs\\audits\\login-split-comparison.png`
- Source pixels: 1487 x 1058
- Desktop implementation pixels / CSS viewport: 1440 x 1024 at device scale 1
- Mobile implementation pixels / CSS viewport: 390 x 844 at device scale 1
- Normalization: source was resized to 1440 x 1024 beside the 1440 x 1024 desktop capture.
- State: default unauthenticated login screen.

## Findings

- No actionable P0, P1, or P2 mismatch remains.
- Typography: the serif display hierarchy, spaced English labels, restrained UI weights, and Chinese copy wrapping match the reference closely.
- Spacing and layout: the 41/59 split, left copy inset, right form width, vertical alignment, input heights, and button placement match after the alignment pass.
- Colors and tokens: the existing dark green, warm ivory, muted gray, and rust accent tokens reproduce the reference balance without introducing a second visual system.
- Image quality and assets: the target contains no photographic product imagery. Its dense lower-left editorial linework and password eye are intentionally omitted instead of being approximated with CSS art or an unapproved glyph; this is accepted as P3 polish.
- Copy and content: the brand, title, access explanation, labels, placeholders, and login CTA match the selected target. The previous role-description rows were removed as requested by the focused layout.
- Responsive behavior: the mobile layout converts the left brand cover into a compact top masthead. At 390 x 844, the page and viewport are both 390 x 844 and the CTA ends at 692.7px, so the screen does not scroll.

## Full-view comparison

The combined source/implementation image shows equivalent major-region proportions, content order, form scale, visual hierarchy, and above-the-fold density. The implementation uses a plain divider on the brand panel in place of the source's decorative line grid.

## Focused region comparison

A separate crop was not needed: at the original 2880 x 1024 comparison size, the title, labels, inputs, CTA, and brand lockup remain readable enough to judge alignment, type hierarchy, borders, and spacing.

## Comparison history

1. Initial implementation finding (P2): both brand content and the login block sat visibly lower than the source.
2. Fix: changed the left panel from vertical centering to a measured top inset and shifted the desktop form block upward by 5vh; mobile keeps a neutral transform.
3. Post-fix evidence: `docs/audits/login-split-desktop.png` measures brand top at 245.75px and form block top at 196.34px in the 1440 x 1024 viewport, matching the normalized source composition. The combined evidence is `docs/audits/login-split-comparison.png`.

## Primary checks

- Username and password controls render with associated labels.
- Login button remains a POST form submission to `/api/access/login`.
- Desktop viewport: 1440 x 1024 with document size 1440 x 1024.
- Mobile viewport: 390 x 844 with document size 390 x 844.
- Focused login and access tests: 29 passed.
- Production build: passed.

## Follow-up polish

- P3: add a licensed/source decorative line asset and an icon-library password visibility control if exact ornamental fidelity is later required.

final result: passed
