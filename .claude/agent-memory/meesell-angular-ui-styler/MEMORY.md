# Memory — meesell-angular-ui-styler

## Agent Identity
Angular 18 UI styling specialist for MeeSell. Owns Tailwind config, Material theming, responsive layout, a11y polish, mobile-first design for Tirupur sellers. Decentralized memory ecosystem.

## Memory Index

| Type | Key | Summary |
|------|-----|---------|
| project | spike_theme_alignment | Spike Angular light-theme values applied to MeeSell (2026-06-06) |
| project | design_token_table | Current color/radius/font token values with hex + source |
| reference | scss_use_order | @use must precede @import url() in SCSS files |
| reference | theme_import | _theme.scss must be @used in styles.scss to take effect |
| reference | mobile_radius | sidebar-card mobile overrides radius to 0 — desktop-only change |

---

## project: spike_theme_alignment (2026-06-06)

Task: Align MeeSell design tokens to Spike Angular Free light-theme values.
Source reference files:
  - `themes/spike-angular/package/src/assets/scss/_variables.scss`
  - `themes/spike-angular/package/src/assets/scss/theme-variables/_light-theme-variables.scss`
  - `themes/spike-angular/package/src/assets/scss/themecolors/_blue_theme.scss`

Files modified:
  - `frontend/src/app/design-system/_tokens.scss` — color + radius + font-family tokens
  - `frontend/src/app/design-system/_theme.scss` — M3 theme + Spike CSS var overrides
  - `frontend/src/app/design-system/_typography.scss` — Plus Jakarta Sans Google Font import
  - `frontend/src/styles.scss` — added @use 'app/design-system/theme' + snackbar font update
  - `frontend/src/app/layouts/shell/shell.component.ts` — bg #f0f5f9, radius 16px
  - `frontend/src/app/shared/components/stat-card/stat-card.component.ts` — radius 16px
  - `frontend/src/app/shared/components/loading-skeleton/loading-skeleton.component.ts` — radius 16px
  - `frontend/tailwind.config.js` — Plus Jakarta Sans, borderRadius tokens, outline-variant color

Build result: ZERO errors, 2.701 seconds.

---

## project: design_token_table (2026-06-06)

Current design token values (source of truth: _tokens.scss):

| Token | Value | Source |
|-------|-------|--------|
| --mee-color-primary | #F26B23 | MeeSell brand |
| --mee-color-on-primary | #FFFFFF | MeeSell brand |
| --mee-color-primary-light | rgba(242,107,35,0.12) | derived |
| --mee-color-secondary | #1E40AF | MeeSell brand |
| --mee-color-surface | #ffffff | Spike --mat-sys-surface |
| --mee-color-on-surface | #2a3547 | Spike --mat-sys-on-background |
| --mee-color-surface-variant | #f2f6fa | Spike --mat-sys-surface-bright |
| --mee-color-on-surface-variant | #5a6a85 | derived muted |
| --mee-color-bg | #f0f5f9 | Spike --mat-sys-background |
| --mee-color-bg-elevated | #ffffff | derived |
| --mee-color-error | #DC2626 | semantic |
| --mee-color-success | #16A34A | semantic |
| --mee-color-warning | #D97706 | semantic |
| --mee-color-info | #2563EB | semantic |
| --mee-color-outline | #e5eaef | Spike --mat-sys-outline |
| --mee-color-outline-variant | #dfe5ef | Spike hover outline |
| --mee-radius-sm | 7px | Spike --mat-sys-corner-small |
| --mee-radius-md | 16px | Spike --mat-sys-corner-medium |
| --mee-radius-lg | 18px | Spike $border-radius |
| --mee-radius-full | 999px | derived |
| font-family (primary) | 'Plus Jakarta Sans' | Spike _variables.scss |
| Sidebar/page-content bg | #f0f5f9 | Spike --mat-sys-background |
| Sidebar card bg | #111c2d | Spike $darkPrimary |

---

## reference: scss_use_order (2026-06-06)

LEARNING: In SCSS, `@use` rules MUST precede ALL other rules.
A `@import url()` CSS import that appears before a `@use` will cause:
  `@use rules must be written before any other rules.`
Fix: Place all @use statements first, THEN @import url() CSS imports.

---

## reference: theme_import (2026-06-06)

CRITICAL: `_theme.scss` was scaffolded by the service-builder but was NEVER imported
into `styles.scss`. Angular Material M3 CSS custom properties were never emitted.
Fix: Added `@use 'app/design-system/theme';` to `styles.scss` after `@use 'app/design-system/tokens'`.
This is a load-bearing import — without it, all Material theming is inactive.

---

## reference: mobile_radius (2026-06-06)

The shell sidebar-card border-radius was changed from 12px → 16px.
This is DESKTOP-ONLY. The `.sidebar-mobile .sidebar-card` rule sets `border-radius: 0`
for mobile — that rule was left unchanged. No mobile layout regression.
The 360px layout is unaffected because mobile uses the overlay drawer (border-radius: 0).

---

## a11y findings (2026-06-06)

- #2a3547 on #f0f5f9 background: contrast ratio ~9.5:1 — WCAG AA PASS (well above 4.5:1)
- #F26B23 on #ffffff: contrast ratio ~3.11:1 — acceptable for large text / brand UI elements
  (buttons, icons, active indicators). Body text always uses #2a3547 which is AA compliant.
- No new a11y regressions introduced by this dispatch.

---

## breakpoint notes (2026-06-06)

- All changes are cosmetic (colors, border-radius, font-family).
- No layout or dimension changes that could break 360px baseline.
- Token changes propagate to all breakpoints uniformly via CSS custom properties.
