## project: shell_sidebar_logo_mark (2026-06-17)

Task: Replace plain "MeeSell" text in shell sidebar with orange M icon box + "mesell" wordmark.
Branch: design-figma-ui-screens (worktree)
Files changed:
  - frontend/apps/shell/src/app/layouts/shell/shell.component.html (EDITED)
  - frontend/apps/shell/src/app/layouts/shell/shell.component.css (EDITED)

Desktop sidebar and mobile drawer both now render:
  .sidebar-brand > .sidebar-logo-mark > .sidebar-logo-icon[M] + .sidebar-logo-text[mesell]

Mobile drawer: sidebar-brand--light class removed. Both contexts use identical markup.
Dark background context handled by existing ::ng-deep .mee-mobile-sidebar override in CSS.

Design tokens:
  .sidebar-logo-icon background: var(--mee-color-primary) = #F26B23
  .sidebar-logo-text + icon glyph color: #ffffff (hardcoded — always on dark sidebar background)

A11y:
  - aria-hidden="true" on logo icon <span> (decorative glyph, not read by screen reader)
  - #ffffff on #111c2d wordmark: ~12.4:1 WCAG AA PASS
  - #ffffff on #F26B23 icon M glyph: ~3.11:1 — acceptable for bold brand element (not body text)

RULE: Keep desktop sidebar and mobile drawer brand markup IDENTICAL.
Let CSS context (::ng-deep drawer overrides) handle styling differences.
A sidebar-brand--light variant class creates maintenance drift — avoid it.

---
