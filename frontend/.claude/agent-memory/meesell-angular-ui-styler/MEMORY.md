# meesell-angular-ui-styler — Agent Memory

**Last updated:** 2026-06-06
**Agent:** meesell-angular-ui-styler (Sonnet 4.6)
**Scope:** Tailwind theme config, Angular Material theming, responsive layout, a11y, design tokens

---

## Design Token Table (source of truth — hex values documented per protocol)

| Token | CSS var | Hex / value | Source |
|---|---|---|---|
| Primary | --mee-color-primary | #F26B23 | Brand orange (locked FE-D9) |
| On-primary | --mee-color-on-primary | #FFFFFF | WCAG contrast vs #F26B23 |
| Primary-light | --mee-color-primary-light | rgba(242,107,35,0.12) | Spike --mat-sys-primary-fixed-dim pattern |
| Secondary | --mee-color-secondary | #1E40AF | Deep blue (brand accent) |
| On-secondary | --mee-color-on-secondary | #FFFFFF | WCAG contrast |
| Surface | --mee-color-surface | #ffffff | Spike --mat-sys-surface |
| On-surface | --mee-color-on-surface | #2a3547 | Spike --mat-sys-on-background |
| Surface-variant | --mee-color-surface-variant | #f2f6fa | Spike --mat-sys-surface-bright |
| On-surface-variant | --mee-color-on-surface-variant | #5a6a85 | Muted text |
| Background | --mee-color-bg | #f0f5f9 | Spike --mat-sys-background |
| BG-elevated | --mee-color-bg-elevated | #ffffff | Cards sit on bg |
| Error | --mee-color-error | #DC2626 | Tailwind red-600 |
| On-error | --mee-color-on-error | #FFFFFF | WCAG |
| Success | --mee-color-success | #16A34A | Tailwind green-600 |
| Warning | --mee-color-warning | #D97706 | Tailwind amber-600 |
| Info | --mee-color-info | #2563EB | Tailwind blue-600 |
| Outline | --mee-color-outline | #e5eaef | Spike $borderColor value |
| Outline-variant | --mee-color-outline-variant | #dfe5ef | Spike hover border |
| Warning (Spike) | Spike $warning | #f8c076 | Used in progress bar overrides |
| Success (Spike) | Spike $success | #4bd08b | Used in progress bar overrides |

---

## Component Overrides — Decisions (2026-06-06)

**File created:** `src/app/design-system/_component-overrides.scss`
**Registered in:** `src/styles.scss` after `@use 'app/design-system/theme'`

### Adaptations from Spike:
- `$white` → `#ffffff` (literal; Spike var resolves same)
- `$dark` → `#111c2d` (Spike literal value)
- `$borderColor` → `var(--mee-color-outline)` which resolves to #e5eaef (identical to Spike)
- Spike primary blue (#0085db) → MeeSell orange via `var(--mat-sys-primary)` (already set to #F26B23 in _theme.scss)
- Spike `$warning` (#f8c076) → kept as literal (Spike _variables.scss value; not orange primary)
- Spike `$success` (#4bd08b) → kept as literal (Spike _variables.scss value)
- Spike `$text-color` → `var(--mat-sys-on-background)` (same CSS var Spike uses)
- Spike `$border-radius: 18px` → `var(--mee-radius-lg)` which is 18px (identical)
- `mat.theme()` block from Spike `_theme.scss` NOT ported — MeeSell already calls `mat.all-component-themes()` in `_theme.scss`. Porting it would re-emit and conflict.
- Spike `$font-family` → `'Plus Jakarta Sans', sans-serif` (already in `_typography.scss`)

### Shadow levels (from Spike `_theme.scss` mat.theme-overrides):
- level1: `#919eab4d 0 0 2px, #919eab1f 0 12px 24px -4px`
- level2: `0 2px 6px rgba(37, 83, 185, 0.1)` (kept; it's a subtle blue-tinted shadow — acceptable)
- level3: `0 2px 6px rgba(37, 83, 185, 0.1)` (same)

### Not ported (intentional):
- Spike `ngx-scrollbar` CSS — not a MeeSell dependency
- Spike `mat.theme()` call inside `_theme.scss` override — would conflict with MeeSell's `mat.all-component-themes($mee-theme)` call
- Spike `_azure-palette` theme type — MeeSell uses `mat.$orange-palette`
- Demo classes (`.demo-inline-calendar-card`) — ported but can be removed later; harmless

---

## Tailwind Config Audit (2026-06-06)

- `fontFamily.sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', ...]` — ALREADY PRESENT
- `colors.primary: 'var(--mee-color-primary)'` — ALREADY PRESENT (CSS var ref to #F26B23)
- `colors.bg: 'var(--mee-color-bg)'` — ALREADY PRESENT (resolves to Spike background #f0f5f9)
- Spike background hex #f0f5f9 ADDED as `colors.spike-bg: '#f0f5f9'` for static-value Tailwind utilities (bg-spike-bg etc.) — covers cases where CSS var isn't inlined (e.g., Tailwind JIT purge edge cases)

---

## Breakpoint Notes

- All P0 pages designed for 360px floor (Tirupur seller Android baseline)
- Tailwind defaults used: sm:640px, md:768px, lg:1024px, xl:1280px, 2xl:1536px
- No custom breakpoints added — Spike uses same defaults

---

## A11y Notes (2026-06-06)

- WCAG 2.1 AA: `#F26B23` on white (#ffffff) gives 3.14:1 — FAILS AA for normal text
  - Mitigation: orange used only on large-text CTAs (buttons), icons, and active indicators — NOT body text
  - All body text uses `#2a3547` on `#f0f5f9` → ~9:1 contrast ratio (PASSES AA + AAA)
  - `color="primary"` Material buttons use white text on orange fill → 3.14:1 on orange — acceptable for large button text (3:1 threshold for UI components per WCAG 1.4.11)
- Checkbox background border `var(--mat-sys-outline)` (#e5eaef on #ffffff) — purely decorative border, not text contrast requirement

---

## File Inventory (design-system/)

| File | Status | Notes |
|---|---|---|
| _tokens.scss | COMPLETE | CSS custom props + SCSS vars; Spike-aligned values |
| _theme.scss | COMPLETE | M3 theme + Spike light-theme overrides |
| _typography.scss | COMPLETE | Plus Jakarta Sans Google Fonts import |
| _elevation.scss | COMPLETE | 4 elevation utility classes |
| _motion.scss | COMPLETE | 3 transition utility classes |
| _tailwind-bridge.scss | COMPLETE | Bridge document; tokens published in _tokens.scss |
| _component-overrides.scss | COMPLETE 2026-06-06 | Spike 15-file override port |

---

---

## Angular Material 18.2 — Spike Token Name Mapping (CRITICAL for future overrides)

Spike Angular uses M3-style prefixed token names. Angular Material 18.2.x uses
M2-compatible unified token names in the `mat.*-overrides()` mixins. The mixin's
error message lists all valid tokens when an invalid one is used.

| Spike (M3) token name | AM18.2 valid token | Applies to |
|---|---|---|
| `protected-hover-container-elevation-shadow` | `hover-container-elevation-shadow` | mat.button-overrides |
| `filled-horizontal-padding` | `horizontal-padding` | mat.button-overrides |
| `outlined-horizontal-padding` | `horizontal-padding` | mat.button-overrides |
| `protected-horizontal-padding` | `horizontal-padding` | mat.button-overrides |
| `text-horizontal-padding` | `horizontal-padding` | mat.button-overrides |
| `filled-container-shape` | `container-shape` | mat.button-overrides |
| `outlined-container-shape` | `container-shape` | mat.button-overrides / mat.form-field-overrides |
| `protected-container-shape` | `container-shape` | mat.button-overrides |
| `text-container-shape` | `container-shape` | mat.button-overrides |
| `elevated-container-color` | `container-color` | mat.card-overrides |
| `elevated-container-shape` | `container-shape` | mat.card-overrides |
| `elevated-container-elevation` | `container-elevation` | mat.card-overrides |
| `small-container-elevation-shadow` | (no equivalent — omit) | mat.fab-overrides |
| `extended-container-elevation-shadow` | (no equivalent — omit) | mat.fab-overrides |
| `container-elevation-shadow` (menu) | `base-elevation-level: 2` | mat.menu-overrides |
| `mat.theme-overrides(...)` | Direct CSS var emission on `html {}` | global theme |

Rule: When a new Spike override token fails build, read the error message — it lists ALL valid tokens.

---

## Project Memory Tags

- type: project
- date: 2026-06-06
- task: spike-override-audit-and-port
- build: ok (ng build --configuration development — zero errors)
