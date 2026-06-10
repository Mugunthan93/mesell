# Memory — meesell-angular-ui-styler

## Agent Identity
Angular UI styling specialist for MeeSell. Owns Tailwind config, PrimeNG/Material theming, responsive layout, a11y polish, mobile-first design for Tirupur sellers. Decentralized memory ecosystem.

NOTE: Stack upgraded from Angular Material → PrimeNG 21 + Sakai-ng (Wave 2A decision, 2026-06-08). Design token values are PRESERVED — only the theming mechanism changes.

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

## project: wave_1b_template_shortlist (2026-06-08)

Task: Research Wave 1B — identify replacement Angular admin template now that Spike Pro layouts are paywalled.
Output: docs/ui_ux/WAVE_1B_TEMPLATE_SHORTLIST.md

Mandatory criteria applied:
  - Angular 18+ (standalone components)
  - Angular Material (not Bootstrap)
  - MIT LICENSE file confirmed (not just package.json field)
  - No paywall on any page/layout
  - Tailwind CSS present (preferred, not hard-block)

Candidates evaluated: 14 total (3 shortlisted, 11 rejected)

Key rejection patterns discovered:
  - CodedThemes Berry/Mantis/CoreUI use Bootstrap 5 despite Angular branding — always verify CSS framework
  - AdminMart (Modernize) + WrapPixel/Material Pro share Spike author lineage — auto-reject on conflict-of-interest
  - Angular 11-15 templates: too old (standalone = Angular 14+, but 14 is borderline; target 18+)
  - Tailwind-only templates (TailAdmin, lannodev) have no Angular Material — valid for layout reference only

PRIMARY RECOMMENDATION: Signal Admin
  - Repo: https://github.com/codebangla/signal-admin
  - Stack: Angular 20 + Angular Material 20 + Tailwind 3.4 + standalone + MIT 2025
  - Layout: two-layout pattern (auth + main with sidebar) — matches MeeSell shell exactly
  - Pages: 12 pre-built pages covering all 8 required MeeSell page types
  - Weakness: 7 stars (brand new, 2025) — may have rough edges; verify via local clone
  - Material Icons via CDN — swap to Material Symbols by changing font URL (one-line change)

SECONDARY: ng-matero
  - Stack: Angular 21 + Angular Material 21 + NO Tailwind (would need manual addition)
  - Strength: 1,500+ stars, last commit May 2026, RTL + dark mode support
  - Best used as Material component pattern reference, not primary template

CONDITIONAL: lannodev/angular-tailwind
  - Stack: Angular 20 + Signals + Tailwind v4 + NO Angular Material
  - Useful as Tailwind layout scaffold reference only

Ecosystem learning: Angular Material + Tailwind + Angular 18+ + standalone + MIT + no-paywall is a very thin
space (2025-2026). Signal Admin is the only native fit. If Signal Admin proves too rough, the fallback is
ng-matero (add Tailwind manually) or starting from the Angular CLI scaffold with ng-matero as a component
pattern reference.

Screenshots directory created: docs/ui_ux/wave_1b_screenshots/signal-admin/

---

## project: wave_1b_ratified_template_spec (2026-06-08)

Task: Write WAVE_1B_RATIFIED_TEMPLATE_SPEC.md — founder ratification of Signal Admin as the Wave 1B reference template.

Output file: docs/ui_ux/WAVE_1B_RATIFIED_TEMPLATE_SPEC.md

Key ratified decisions:
  - Signal Admin (github.com/codebangla/signal-admin) is the MeeSell reference template
  - Angular upgrade: Angular 18 → Angular 20 (matches Signal Admin; code reuse, not visual reference)
  - Template stack: Angular 20 + Angular Material 20 + Tailwind 3.4 + standalone: true + MIT 2025
  - License verified: MIT, Copyright 2025 Md Sajedul Haque Romy
  - No paywall: zero pro/premium/locked mentions in src/

Reuse map (locked):
  - /dashboard: REUSE — stat cards + chart layout
  - /catalogs: REUSE — table + search + pagination pattern (from /users page)
  - /catalogs/:id/edit: REUSE — form layout pattern (from /forms page)
  - /images: REUSE — card grid + badge pattern (from /ui page)
  - /export: REUSE — summary + history table (from /reports page)
  - /profile: REUSE — settings form + profile card pattern (from /settings + /profile)
  - /login, /signup: REPLACE — MeeSell OTP flow already built

5 changes for MeeSell (locked in spec):
  1. Color tokens: sidebar #111c2d, primary #F26B23, bg #f0f5f9, border #e5eaef
  2. Icon font: Material+Icons CDN → Material+Symbols+Outlined (one-line index.html change)
  3. Auth flow: email+password → phone+OTP (already implemented)
  4. Mobile sidebar: Signal Admin no 360px collapse → MeeSell mat-sidenav mode switching (already implemented)
  5. Angular version: both at Angular 20 (upgrade complete)

Wave 1C sequence: dashboard → catalog-list → catalog-form → images → preview → export → profile
Source path: themes/signal-admin/src/app/features/<feature>/
Target path: frontend/src/app/features/<feature>/

Angular upgrade gate: Angular version bump from 18 → 20 must complete before Wave 1C page work begins.
This affects component-builder and service-builder dispatch sequencing.

---

## project: signal_admin_rejected (2026-06-08)

Signal Admin (codebangla/signal-admin) was reviewed by founder on 2026-06-08 and rejected as not suitable for MeeSell. Founder will source the theme himself and provide it directly. Wave 1C is BLOCKED pending new theme source.

Angular 20 upgrade remains in effect — it is theme-independent.
themes/signal-admin/ remains on disk until explicitly deleted.

When a new theme source is provided: run fresh evaluation (license + Angular version + standalone + page count + screenshots) before starting Wave 1C. Do not carry over Signal Admin reuse map or patterns.

---

## project: wave_2a_framework_shortlist (2026-06-08)

Task: Research Wave 2A — identify Angular UI framework candidates for full frontend reset from Angular Material.
Output: docs/ui_ux/WAVE_2A_FRAMEWORK_SHORTLIST.md
Status update: docs/status/STATUS_DESIGN_SYSTEM.md prepended with Wave 2A block.

Mandatory criteria applied:
  - Angular 18+ (standalone components)
  - MIT license verified from package.json / LICENSE file (not README)
  - No paywall on any page/layout
  - Tailwind CSS presence noted (preferred)
  - Pre-built admin shell (preferred — reduces Wave 2B effort)

Candidates evaluated: 8 total (3 shortlisted, 5 rejected)

Rejected candidates:
  1. Clarity Design (vmware-archive/clarity) — archived 2023, no Angular 18+ support
  2. taiga-ui-admin (AAVision) — Angular 16.1.4, only 11 stars
  3. Signal Admin (Wave 1B) — rejected by founder 2026-06-08
  4. CoreUI Angular — Bootstrap 5, not a component library
  5. ngx-admin (Akveo) — Angular 15 + Nebular (non-standard UI library)

PRIMARY RECOMMENDATION: PrimeNG + Sakai-ng Free
  - Repo: https://github.com/primefaces/sakai-ng
  - Stack: Angular 21 + PrimeNG 21.0.2 + Tailwind CSS 4.1.11 + @primeuix/themes 2.0.0 + standalone + MIT
  - Stars: 941 (Sakai) / 10k+ (PrimeNG library itself)
  - Last release: v21.0.0 — Feb 2, 2026
  - Page types pre-built: 13 (shell, login, error/access, dashboard, forms, tables, lists, CRUD, landing, charts, dialogs, empty, 404)
  - No paywall: Apollo is a separate paid product; Sakai itself is fully free
  - MeeSell-relevant components: p-fileUpload, p-dataTable, p-steps, p-dialog, p-confirmDialog, p-tag, p-treeSelect, p-inputOtp, p-progressBar, p-toast
  - Minor concern: primeclt ^0.1.5 Vue dep — removable before Wave 2B scaffold, not a blocker

SECONDARY: NG-ZORRO (ng-zorro-antd) + ng-alain
  - ng-zorro 21.3.1 = Angular 21, MIT, standalone
  - ng-alain v21.2.0 = Angular 21.2.11, MIT, standalone
  - Strength: most pages pre-built (3 dashboard variants, 3 form variants, 3 list variants)
  - Weakness: NO Tailwind (uses Less CSS); Ant Design is desktop-first

CONDITIONAL: Taiga UI 5.10.0
  - Angular >= 19, Apache-2.0 (NOT MIT — fails auto-reject criterion)
  - No admin starter template — full shell must be built from scratch
  - Best component for MeeSell: TuiInputPhone (phone+OTP auth)

Key design-system change for Wave 2B:
  PrimeNG does NOT use Angular Material mat-* selectors or CDK.
  All Wave 1 overrides (_theme.scss, _component-overrides.scss, M3 theme) will not apply.
  Wave 2B must use @primeuix/themes presets + Tailwind utilities for design tokens.
  Color tokens (#F26B23 primary, #111c2d sidebar, #f0f5f9 bg) must be re-wired via PrimeUI preset.

Gate A: COMPLETE. Awaiting founder pick for Wave 2B scaffold.

---

## project: wave_2b_architecture_doc (2026-06-08)

Task: Write docs/FRONTEND_ARCHITECTURE.md — founder-approved abstraction-first frontend architecture for MeeSell Wave 2B+.

This document SUPERSEDES the prior Angular Material-based FRONTEND_ARCHITECTURE.md.

Key architecture decisions locked:
  - Stack: Angular 21 + PrimeNG 21 + Sakai-ng Free + Tailwind CSS 4 + TypeScript strict
  - 4-layer architecture pattern:
    Layer 1: Design System (pure CSS/SCSS — no library imports)
    Layer 2: MeeSell UI Kit (PrimeNG wrappers — the ONLY place PrimeNG is imported)
    Layer 3: Layouts (MeeShellComponent, MeeAuthLayoutComponent) + Shared composites
    Layer 4: Features (ZERO direct PrimeNG imports — use @mee/ui only)
  - SOLID DIP pattern: Features → @mee/ui abstractions ← PrimeNG
  - 17 UI Kit components specified with TypeScript contracts
  - Path aliases: @mee/ui, @mee/shared, @mee/design, @mee/core
  - Wave sequence: 2B scaffold → 2C UI Kit → 2D Shared → 2E+ Features

Design token values UNCHANGED from Wave 1 work:
  - #F26B23 primary (MeeSell orange)
  - #111c2d sidebar (dark navy)
  - #f0f5f9 bg (page background)
  - #2a3547 on-surface (body text)
  - #e5eaef outline (border)

For Wave 2B theming:
  - Angular Material _theme.scss + _component-overrides.scss are RETIRED
  - New theming: @primeuix/themes preset + CSS custom properties in _tokens.scss
  - Tailwind config extends design tokens via CSS custom property references
  - No @primeuix/themes import allowed in Layer 1 (_tokens.scss is pure :root vars)
  - PrimeNG preset customisation goes in a new file: src/app/ui/prime-preset.ts (Layer 2)

Files written:
  - docs/FRONTEND_ARCHITECTURE.md (full rewrite)
  - docs/status/STATUS_FRONTEND.md (prepended update block)

---

## project: wave_2b_step2_primeng_theme (2026-06-08)

Task: Wave 2B Step 2 — PrimeNG theme preset + design tokens on fresh Angular 21 scaffold.

Files created/modified:
  - frontend/src/app/design-system/_tokens.css (CREATED — Layer 1 CSS custom properties)
  - frontend/src/app/core/theme/meesell-preset.ts (CREATED — PrimeNG Aura-based preset)
  - frontend/src/app/app.config.ts (UPDATED — providePrimeNG + provideAnimationsAsync)
  - frontend/src/styles.css (UPDATED — tokens import + global body styles)
  - frontend/src/index.html (UPDATED — Plus Jakarta Sans + PrimeIcons CDN)

Build result: ZERO errors, 2.073 seconds. Initial total 86.61 kB transfer.

Key learnings:

LEARNING: @primeuix/themes 2.0.3 component token structure
  All component tokens MUST be nested under the section key (root, header, headerCell, etc.)
  WRONG:  components: { card: { borderRadius: '16px' } }
  RIGHT:  components: { card: { root: { borderRadius: '16px' } } }
  The TS type for each ComponentDesignTokens interface exposes root?: ComponentTokenSections.Root
  (and other sections like header, headerCell). Flat keys at component level are NOT accepted.

LEARNING: datatable.headerCell has no borderRadius token
  DataTableTokenSections.HeaderCell does NOT include borderRadius.
  borderRadius in datatable exists only on row-level elements (row.toggleButton).
  Remove headerCell borderRadius overrides from presets — they will cause TS2353.

LEARNING: @angular/animations must be explicitly installed for provideAnimationsAsync
  Angular 21 scaffold from `ng new` does NOT include @angular/animations by default.
  provideAnimationsAsync() requires @angular/animations/browser at runtime.
  Install: pnpm add @angular/animations@<match-angular-framework-version>
  Version match is critical — installing @22.x alongside @21.x framework causes peer warnings.
  Installed @angular/animations@21.2.16 to match Angular 21.2.16 framework.

LEARNING: @primeuix/themes/aura import path
  The exports map pattern './*' in @primeuix/themes/package.json resolves:
    @primeuix/themes/aura → ./dist/aura/index.mjs
  The import `import Aura from '@primeuix/themes/aura'` works correctly with
  Angular's esbuild builder (no aliasing or path rewrite needed).

LEARNING: PrimeNG CSS layer order for Tailwind 4 compatibility
  cssLayer order: 'tailwind-base, primeng, tailwind-utilities'
  This ensures PrimeNG styles sit between Tailwind base reset and utility classes.
  Tailwind 4 with PostCSS emits @layer cascade — this order prevents utility override conflicts.

Design token file: frontend/src/app/design-system/_tokens.css
Token count: 52 CSS custom properties
Zero Angular Material / PrimeNG dependency — pure :root CSS vars.
Survives any future UI library swap.

---

## project: wave_2c_hotfix_layer_wiring (2026-06-09)

Task: Wave 2C Hotfix — fix Tailwind v4 + PrimeNG CSS @layer conflict causing unstyled auth controls.

Root cause: bare `@import "tailwindcss"` emits CSS into Tailwind v4 native layers (theme/base/components/utilities).
app.config.ts cssLayer.order = 'tailwind-base, primeng, tailwind-utilities' references DIFFERENT layer names.
These phantom empty layers let Preflight's `base` layer outrank `primeng` → bare-text buttons, no-border inputs.

Fix approach (Layer 1 — styles.css):
  - Declared @layer tailwind-base, primeng, tailwind-utilities;
  - Split imports: theme.css + preflight.css into tailwind-base; utilities.css into tailwind-utilities
  - This places Tailwind CSS into the exact layer names that PrimeNG config expects

CRITICAL LEARNING: @source does NOT work with @angular/build:application esbuild pipeline
  When using split imports (not bare `@import "tailwindcss"`), Tailwind v4 sets root = "none"
  and generates no utilities unless @source provides files to scan.
  @source glob paths ARE resolved relative to the CSS file, and the `base` postcss option works.
  BUT: the Angular esbuild builder's PostCSS invocation virtualizes or restricts file access such
  that Tailwind's glob scanner finds zero files regardless of the @source path pattern tried.
  Patterns tried that ALL failed: "@source ./app", "@source ./app/**/*.ts", "@source ./**/*.{ts,html}",
  "@source ../src/**/*.ts", "@source ./app/**/*.ts" — all produce 0 generated utility classes.

Workaround: explicit @layer tailwind-utilities { .util {} } block in styles.css
  Instead of relying on @source scanning, declare critical utility classes directly in the
  tailwind-utilities layer in styles.css. These are properly layered and beat PrimeNG's primeng layer.
  Current safelist: w-full, flex, justify-center, items-center, block, hidden, min-h-screen, h-full.
  RULE: if any component template uses a new Tailwind utility, add it to this block.

Fix approach (Layer 4 — auth component styles):
  - Added class="w-full" to all <input pInputText> elements and <p-button> host elements
  - Added display:block to standalone inputs (PrimeNG sets display:inline-block by default)
  - Added .phone-field input { flex: 1 } to fill row beside +91 prefix
  - Added ::ng-deep p-button { display:block; width:100% } for host-level expansion
  - Added ::ng-deep .p-button { width:100%; justify-content:center } for inner button
  - Added ::ng-deep .p-inputotp { display:flex; justify-content:center; gap:8px; width:100% } for OTP

Files modified:
  - frontend/src/styles.css (REWRITTEN)
  - frontend/postcss.config.mjs (base option added)
  - frontend/src/app/features/auth/login.component.ts (fluid classes + styles)
  - frontend/src/app/features/auth/signup.component.ts (fluid classes + styles)
  - frontend/src/app/features/auth/otp-verify/otp-verify.component.ts (fluid classes + styles)

Probe result (login):
  button.bg = rgb(242, 107, 35) orange PASS
  button.padding = 10px 14px PASS
  button.borderRadius = 999px PASS
  button.width = 376px full-width PASS
  input.width = 345.953px (flex-remaining) PASS
  input.border = 1px solid rgb(205, 215, 229) PASS

Build: ZERO errors. Tests: 17/17 PASS.
Screenshots: /tmp/mesell-shots-fixed/ (6 files — 3 pages x 2 breakpoints).

---

## project: tailwind_safelist_debt_eliminated (2026-06-09)

Task: Eliminate manual Tailwind utility safelist in styles.css — enable true auto-detection.

### Root cause (took deep investigation to find)

@angular/build:application does NOT load postcss.config.mjs or postcss.config.js.
  Source: Angular reads ONLY postcss.config.json or .postcssrc.json.
  File: @angular/build/src/utils/postcss-configuration.js → const postcssConfigurationFiles = ['postcss.config.json', '.postcssrc.json']

When no JSON PostCSS config exists AND tailwind.config.js exists (v3-style detection):
  Angular tries: require('tailwindcss').default({ config: path }) — v3 style
  Tailwind v4 exports: { Features, Polyfills, compile, compileAst } — NO .default export
  Result: tailwind.default is not a function → silent fail → NO PostCSS Tailwind processing
  But @import "tailwindcss" is resolved by esbuild → tailwindcss/index.css via 'style' condition
  This gives Preflight (base CSS reset) but EMPTY utilities layer → zero utility classes

When tailwind.config.js does NOT exist (our project):
  tailwindConfiguration = undefined
  postcssConfiguration = undefined (postcss.config.mjs ignored)
  Angular applies NO PostCSS at all
  @import "tailwindcss" → esbuild static resolution → tailwindcss/index.css → Preflight only
  Utilities = empty

### Fix applied

Created frontend/postcss.config.json:
  { "plugins": { "@tailwindcss/postcss": { "base": "/Users/mugunthansrinivasan/Project/mesell/frontend/" } } }

Effect:
  Angular detects postcss.config.json → sets postcssConfiguration → skips Tailwind v3 path
  Loads @tailwindcss/postcss with base pointing to frontend/
  Plugin scans all .ts/.html files in frontend/src → generates utilities on demand
  Verified: @tailwindcss/postcss satisfies Angular's check (typeof plugin === 'function' && plugin.postcss === true)

Other changes:
  - styles.css: removed manual @layer tailwind-utilities { .w-full {} ... } safelist block (DELETED)
  - styles.css: added @layer theme, base, primeng, components, utilities (before @import)
  - styles.css: bare @import "tailwindcss" retained (auto-detection now works via postcss.config.json)
  - app.config.ts: cssLayer.order updated from 'tailwind-base, primeng, tailwind-utilities' to 'theme, base, primeng, components, utilities' (matches Tailwind v4 native layer names)
  - postcss.config.mjs: kept for tooling compatibility; annotated as NOT used by Angular's builder

### Proof of auto-detection

Added mt-10 (margin-top:2.5rem=40px) to login h1 template (not in any safelist).
Build → dev server → Playwright probe: h1_marginTop = 40px PASS.
Test class removed after proof.
Button/input styles intact: bg rgb(242,107,35), borderRadius 999px, width 376px, border 1px.

### What does NOT work (prior failed approaches)

1. postcss.config.mjs — IGNORED by Angular builder (not a JSON file)
2. Bare @import "tailwindcss" without postcss.config.json — esbuild resolves statically to tailwindcss/index.css, no utility scanning
3. @source "./app/**/*.ts" in CSS — PostCSS @source at-rule cannot precede @import in CSS spec; after @import it is silently dropped by Angular's esbuild
4. @import "tailwindcss" source("/absolute/path") — treated as CSS @media source() query, not Tailwind source modifier; utilities never generated
5. Prepended @layer + bare import ALONE — without postcss.config.json, still zero utilities

### Final file states

frontend/postcss.config.json — CREATED (key file; sole reason auto-detection works)
frontend/src/styles.css — NO safelist, NO @source directive, bare @import "tailwindcss" + @layer declaration
frontend/src/app/app.config.ts — cssLayer.order = 'theme, base, primeng, components, utilities'
frontend/postcss.config.mjs — comment-only update (angular ignores it)

Build: ZERO errors, 1.649s. Tests: 17/17 PASS. Screenshots: 3 auth pages clean.

---

## breakpoint notes (2026-06-06)

- All changes are cosmetic (colors, border-radius, font-family).
- No layout or dimension changes that could break 360px baseline.
- Token changes propagate to all breakpoints uniformly via CSS custom properties.
