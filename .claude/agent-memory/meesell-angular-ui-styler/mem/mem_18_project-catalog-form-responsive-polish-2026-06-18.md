## project: catalog_form_responsive_polish (2026-06-18)

Task: Responsive polish on catalog-form accordion (Wave 5, worktree design-figma-ui-screens).
File: frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form/catalog-form.component.ts

### Gaps fixed

| # | Gap | Before | After |
|---|-----|--------|-------|
| 1 | Bottom spacing / shell overlap | py-4 (16px) | .mee-form-page: 124px on ≤639px (64+60+safe-area) |
| 2 | Nav buttons position | Inline footer in scroll | <nav class="mee-form-nav"> position:fixed outside scroll |
| 3 | Form nav mobile offset | bottom:0 overlaps shell tab | ≤639px: bottom=calc(60px+safe-area); z-index:110 |
| 4 | Field grid layout | flex always 1-col | .mee-field-list: flex mobile, grid 1fr 1fr ≥768px |
| 5 | Textarea full-width | No spanner | [class.mee-field--full] + .mee-field--full{grid-column:1/-1} |
| 6 | Toggle labels | "Collapse/Expand" text | ▲/▼ glyphs, aria-hidden="true" |
| 7 | Loading a11y | No ARIA live | role="status" aria-live="polite" aria-label |
| 8 | AI fill a11y | No aria-label | aria-label="Fill fields with AI suggestions" |
| 9 | Field region a11y | No label | aria-label on expanded field containers |

### Bugs found (not fixable by ui-styler — component logic)
- mee-input + mee-textarea have NO (blur) output. catalog-form's autosave-on-blur is silently broken.
  Owner: meesell-angular-component-builder.
- --mee-color-warning-light missing from _tokens.css. Hardcoded #fef9c3 as temporary fix.

### z-index stack
| shell bottom-tab | z-100 |
| form sticky nav  | z-110 |
| future dialogs   | z-200+|

### Breakpoints
| 360–639px | 1-col flex; form-nav above shell bottom-tab (bottom=60px+safe-area) |
| 640–767px | 1-col flex; form-nav at bottom:0 |
| 768–1279px | 2-col grid 1fr 1fr; max-width 42rem |
| ≥1280px | 2-col grid; max-width 64rem |

RULE: When a form page has a sticky bottom nav AND the page is inside the shell, the form nav must use
`bottom = 60px (shell-tab height) + env(safe-area-inset-bottom, 0px)` at ≤639px.
The shell bottom-tab uses z-100; form nav uses z-110. Never overlap the persistent shell nav.

tsc result: ZERO errors (mfe-catalog + full frontend).

---
