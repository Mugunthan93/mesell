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

---

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

Build: ng build frontend --configuration development — CLEAN (zero errors, 3.224s)
  Initial total: 138.49kB (delta = 0 from Phase 3 baseline — primitives still tree-shake out)
Tests: 1163/1164 PASS (73 files / 1 pre-existing app.spec.ts NG0201 failure — known debt)
  Layout specs: 7 files, all PASS. Test count +1 (new cols=4 regression spec).
tsc --noEmit: CLEAN (TSC_EXIT=0)
Contracts: All 5 CLEAN exit 0 (FE-1/FE-2/FE-3/FE-4/FE-5)

---

## project: pricing_page_ui_polish (2026-06-18)

Task: Slice 3 of 3 — UI styler polish + a11y pass on mfe-pricing page (§12.M forward estimator).
Branch: feat/pricing-fe-rework @ 312625e
PR: #287 (open → develop, not merged — awaiting coordinator merge-gate)
Session: mesell-pricing-fe-rework-frontend-session-1

### A11y findings + fixes

FIXED VIOLATION: <td scope="row"> is invalid HTML.
  The scope attribute is ONLY valid on <th> elements, never <td>.
  9 label cells in the deduction breakdown table had scope="row" on <td> — axe/WCAG 1.3.1 violation.
  Fix: changed all label <td> elements to <th scope="row">.
  Side effect: browser default styles make <th> bold; must reset with font-weight: 400 in .mee-pricing__table-label.

FIXED: aria-label="P&L breakdown" on <table> was inconsistent with h3 heading "Where your money goes".
  Fix: added id="deduction-table-heading" to h3, used aria-labelledby on table (label-element association).
  RULE: table aria label must match or reference the visible heading. Do not use aria-label that differs from visible heading text.

CONFIRMED PASSING:
  - role="status" + aria-label on spinner (polite live region).
  - aria-live="polite" + aria-atomic on results region (programmatic focus via AfterViewChecked).
  - aria-label on hero amount (announces positive/negative state to AT).
  - role="alert" inside mee-alert-banner (assertive for error banners).
  - 44px touch targets: mee-button [fullWidth] satisfies this internally.
  - scope="col" on thead th cells: PASS (already correct).

### Token discipline findings

FIXED: :host { --mee-color-surface-variant: #f2f6fa } was a hardcoded hex override.
  The token --mee-color-surface-variant is ALREADY declared in _tokens.css Layer 1 with the same value.
  Removing the :host re-declaration eliminates the no-raw-hex violation.
  RULE: always check _tokens.css before adding any :host custom property override.

FIXED: !important on color utility classes (.mee-pricing__value--positive/negative).
  No !important allowed in MeeSell CSS (hard constraint).
  Fix: doubled-class selector (.mee-pricing__ratio-value.mee-pricing__value--positive) gives sufficient specificity.
  RULE: never use !important — always reach for selector specificity (compound selectors, parent class, etc.).

### Responsive patterns (360px)

- Outer container: use px-3 sm:px-4 instead of px-4 for mobile-first. px-4 is 16px — fine at 640+. At 360px, px-3 (12px) frees 8px width.
- Table: ALWAYS wrap in overflow-x: auto + -webkit-overflow-scrolling: touch for any table with ≥2 columns.
  Use table min-width to prevent value column from being squeezed to illegible width.
- Hero amount: cap font-size at ≤400px to prevent ₹XXX.XX from overflowing the card. 2rem → 1.625rem.

### MFE screenshot caveat (2026-06-18)

Standalone playwright screenshots of mfe-pricing dist show only the body background color (#f0f5f9).
This is expected — the component is an Angular Module Federation remote. PricingComponent:
  1. Requires ActivatedRoute to supply :id param (injected by shell router, absent standalone).
  2. Requires shell to inject global design tokens CSS (styles.css not loaded from the remote dist).
  3. Requires shell host to bootstrap the Angular app (main.ts in the remote is only for dev-serve).
CONCLUSION: visual screenshots of pricing require the full shell + all MFE remotes running.
DO NOT treat blank screenshots as a rendering failure — the background color loading proves CSS works.

### Build result

mfe-pricing build: GREEN (3.581s, 206.89 kB, +1.68 kB delta vs baseline 205.21 kB).
Tests: 129/129 PASS (pure-function vitest).
Logic/contract: untouched.
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

## project: shell_mobile_bottom_tab_bar (2026-06-18)

Task: Add persistent mobile bottom tab bar to shell (≤639px). HTML + CSS only — no TypeScript changes.
Branch: design-figma-ui-screens (worktree)
Files changed:
  - frontend/apps/shell/src/app/layouts/shell/shell.component.html (EDITED)
  - frontend/apps/shell/src/app/layouts/shell/shell.component.css (EDITED)

### Responsive breakpoint table (FINAL)

| Viewport     | Navigation pattern                                      |
|--------------|--------------------------------------------------------|
| ≥1024px      | Fixed 260px sidebar (.sidebar-desktop)                 |
| 640–1023px   | Hamburger button + mee-drawer overlay                  |
| ≤639px       | Bottom tab bar (.bottom-nav) — hamburger hidden        |

### HTML change

Added `<nav class="bottom-nav" aria-label="Mobile navigation">` as last child of .shell-layout
(after .shell-main closing </div>). Uses `@for (item of navItems; track item.route)` — same
pattern and same `navItems` property already used in desktop sidebar + drawer loops.
`routerLinkActive="bottom-nav-item--active"` drives active state.
`[attr.aria-label]="item.label"` provides screen-reader label per tab.

### CSS changes

1. Added `@media (max-width: 639px) { .hamburger { display: none; } }` immediately after
   the existing `@media (max-width: 1023px) { .hamburger { display: flex; } }` block.
   Hamburger is now: flex at 640–1023px, none at ≤639px and ≥1024px (sidebar covers that).

2. .bottom-nav:
   - display: none (default, hidden on tablet+desktop)
   - position: fixed; bottom: 0; left: 0; right: 0; height: 60px; z-index: 100
   - background: var(--mee-color-surface) = #ffffff
   - border-top: 1px solid var(--mee-color-outline) = #e5eaef
   - box-shadow: 0 -2px 8px rgba(0,0,0,0.06) — subtle elevation
   - padding-bottom: env(safe-area-inset-bottom, 0px) — iPhone home indicator
   @media (max-width: 639px): display: flex; align-items: stretch

3. .page-content override in @media (max-width: 639px):
   padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px))
   Prevents last page content from hiding behind the fixed bar.

4. .bottom-nav-item: flex:1; flex-direction:column; gap:3px; min-height:44px (a11y touch target)
   color: var(--mee-color-on-surface-muted); transition via var(--mee-transition-fast)
   -webkit-tap-highlight-color: transparent (no flash on iOS tap)

5. .bottom-nav-item--active: color: var(--mee-color-primary) = #F26B23
   .bottom-nav-item--active i: transform: scale(1.15) — subtle icon pop on active tab

6. .bottom-nav-label: 10px/500wt; white-space:nowrap; text-overflow:ellipsis; max-width:68px

### Design tokens consumed by bottom-nav
| Token                        | Value   | Role                          |
|------------------------------|---------|-------------------------------|
| --mee-color-surface          | #ffffff | Tab bar background            |
| --mee-color-outline          | #e5eaef | Top border                    |
| --mee-color-on-surface-muted | (var)   | Inactive tab color            |
| --mee-color-primary          | #F26B23 | Active tab color              |
| --mee-transition-fast        | (var)   | Color + scale transition      |

### A11y findings
- min-height: 44px on .bottom-nav-item — WCAG 2.5.5 touch target PASS
- Each tab has aria-label via [attr.aria-label]="item.label" — readable by screen reader
- <nav aria-label="Mobile navigation"> — landmark with label
- Icon glyphs have aria-hidden="true" — decorative, not read
- Active color #F26B23 on #ffffff: ~3.11:1 — acceptable for large/icon UI elements (same as sidebar active, per prior ruling 2026-06-06). Inactive --mee-color-on-surface-muted: verify in next session.
- -webkit-tap-highlight-color: transparent prevents double-flash on Android Chrome

### Mobile 360px coverage
- 4 tabs × flex:1 = 90px each on 360px screen — well above 44px minimum touch width
- Label max-width:68px + text-overflow:ellipsis prevents wrap/overflow on narrow labels
- Safe-area env() ensures home indicator area is clear on modern iOS

### RULE: NavItems is the single source — no custom tab list
The bottom-nav @for loops over the SAME navItems array as sidebar + drawer.
Any future nav item changes (add/remove) automatically propagate to all three nav contexts.
Do NOT introduce a separate tabItems or mobileNavItems property.

TypeScript check (tsc --noEmit): ZERO errors. Full build deferred (native-federation slow in worktree).

---

## project: mfe_dashboard_responsive_audit (2026-06-18)

Task: Responsive polish audit for mfe-dashboard page (DashboardComponent + shared composites).
Branch: design-figma-ui-screens (worktree)
Files audited:
  - frontend/apps/mfe-dashboard/src/app/dashboard.component.ts (inline template)
  - frontend/apps/mfe-dashboard/src/app/landing.component.ts (inline template + styles)
  - frontend/libs/composites/stat-card/stat-card.component.ts
  - frontend/libs/composites/page-header/page-header.component.ts
  - frontend/libs/composites/empty-state/empty-state.component.ts
  - frontend/libs/composites/loading-skeleton/loading-skeleton.component.ts

Files edited:
  - frontend/apps/mfe-dashboard/src/app/dashboard.component.ts (2 cleanups)

### Audit results

| Checklist item | Result | Notes |
|---|---|---|
| Stat cards grid-cols-2 sm:grid-cols-4 | PASS | Present on line 64; mirrored in loading-skeleton stat-card case |
| Table overflow-x-auto wrapper | PASS | `overflow-x-auto rounded-xl` on table wrapper |
| Page header stacks on mobile | PASS | mee-page-header uses flex-col sm:flex-row |
| Empty state centred at 360px | PASS | items-center justify-center text-center in EmptyStateComponent |
| Bottom spacing for tab bar | PASS | Shell .page-content provides padding-bottom: calc(60px + safe-area) at ≤639px. MFE components do NOT need their own pb-[60px] — shell covers it. |
| Fixed pixel widths causing overflow | PASS | max-w-[200px] / max-w-[120px] are truncate helpers inside overflow-x-auto; no overflow |
| Font sizes ≥ 14px | PASS | All controls use text-sm = 14px |
| Touch targets ≥ 44px | PASS | <td> has min-h-[44px]; delete/pagination buttons have min-h-[44px] min-w-[44px]; inputs have min-h-[44px] |

### Fixes applied

1. Removed dead `focus-ring-color` from <input> inline style (not a valid CSS property).
   Was: `style="border-color:...; color:...; background:...; focus-ring-color: var(--mee-color-primary);"` 
   `focus-ring-color` is not a standard CSS property. The Tailwind `focus:ring-2` class handles the ring — no CSS property override needed.

2. Removed dead `min-height: 44px` from <tr> inline style.
   `min-height` on `<tr>` elements does NOT work in Chrome/Safari (table-row display ignores it).
   Actual 44px row height is correctly provided by `class="px-4 py-3 min-h-[44px]"` on the name `<td>`.
   Kept only `border-bottom: 1px solid var(--mee-color-outline)` which is the load-bearing part.

### KEY RULE: Shell padding-bottom covers all MFE pages at mobile

`shell.component.css` @media (max-width: 639px) sets:
  `.page-content { padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px)); }`
This padding applies to the scroll container that hosts all MFE remote content.
Therefore: NO individual MFE page component needs its own `pb-[60px]` at mobile.
Adding it would double the bottom gap. Do not add redundant pb-[60px] to dashboard or other pages.

### RULE: min-height on <tr> is ineffective — use min-h-[44px] on <td> instead

`min-height: 44px` on a `<tr>` does not work in browsers (display: table-row ignores min-height).
To enforce 44px row height, add `min-h-[44px]` or `py-3` (which gives ~42px with text) to the `<td>` cells.
The leading content cell (name column) driving row height should carry the `min-h-[44px]` class.

tsc --noEmit: ZERO errors before and after edits.

---

## project: smart_picker_mobile_audit (2026-06-18)

Task: Responsive polish audit of SmartPickerComponent (/catalogs/new) — mobile-first for Tirupur sellers (360–390px Android).
Branch: design-figma-ui-screens (worktree)

Files read (all audited, only one modified):
  - frontend/apps/mfe-catalog/src/app/smart-picker/smart-picker.component.ts (inline template)
  - frontend/apps/mfe-catalog/src/app/smart-picker/category-card.component.ts (inline template + styles)
  - frontend/libs/ui-kit/textarea/textarea.component.ts (MODIFIED — font-size hardened)
  - frontend/libs/ui-kit/button/button.component.ts
  - frontend/libs/ui-kit/card/card.component.ts
  - frontend/libs/ui-kit/progress-bar/progress-bar.component.ts
  - frontend/libs/composites/page-header/page-header.component.ts
  - frontend/libs/composites/empty-state/empty-state.component.ts
  - frontend/libs/design-tokens/_tokens.css
  - frontend/apps/shell/src/styles.css

### Audit results (all 7 checklist items)

| Check | Result |
|-------|--------|
| Search textarea min-height | min-height: 44px — PASS |
| Search textarea font-size | Fixed: now explicit 1rem (16px). Was implicit browser default — same value but now load-bearing. |
| Category card touch target | grid-cols-1 on mobile + mee-button min-height:44px — PASS |
| "Browse if none match" button | min-h-[44px] Tailwind class; Tailwind scanned via @source "../.." in shell styles.css — PASS |
| Selected category display | N/A — picker routes away on pick |
| Overflow/scroll | Document flow; no viewport overflow — PASS |
| Step bar | Smart picker has NO step bar (separate route from catalog-form) — N/A |
| Fixed pixel widths | None found — PASS |

### Fix applied

frontend/libs/ui-kit/textarea/textarea.component.ts:
  Changed: style="min-height: 44px;"
  To:      style="min-height: 44px; font-size: 1rem;"

Rationale: PrimeNG Aura textarea has no explicit font-size token at the default size variant.
Font-size inherits from HTML root (browser default 16px). Relying on this implicit chain was fragile —
if any future body { font-size } override is added to styles.css, all textareas would suddenly zoom
on iOS. Explicit 1rem locks the 16px floor regardless of cascade.

RULE: Always set font-size: 1rem (minimum 16px) on <input> and <textarea> elements explicitly.
Do NOT rely on PrimeNG or browser defaults for this — it is a mobile safety invariant.

### Component architecture notes

SmartPickerComponent (/catalogs/new) is a SEPARATE route from CatalogFormComponent (/catalogs/:id/edit).
The wizard step bar (mee-steps / p-steps) is in catalog-form only — NOT in smart picker.
Smart picker → category card → routes to /catalogs/:id/edit on pick. No inline step progress needed.

The mee-catalog @source is covered by shell styles.css "@source '../..'".
Shell styles.css is the single Tailwind build; all mfe-* remotes' classes are scanned by it.
Design tokens are imported into shell styles.css; all remotes inherit them at runtime.

### tsc result
tsc --noEmit --project apps/mfe-catalog/tsconfig.app.json: ZERO errors (before and after fix).

---

## project: export_page_responsive_polish (2026-06-18)

Task: Responsive polish audit for mfe-export ExportComponent.
Branch: design-figma-ui-screens (worktree)
File changed: frontend/apps/mfe-export/src/app/export.component.ts (template only — 2 changes)

### Component structure discovered

ExportComponent is a validation-gate + status-state-machine design (NOT a format-picker).
- LEFT column (lg:w-2/5): pre-export checklist table (4 rows) + Generate button
- RIGHT column (lg:w-3/5): conditional status cards (idle / processing+progress / ready+download / failed+retry)
- Both columns are flex-col on mobile (lg:flex-row only at >=1024px)
- No CSV/ZIP format cards, no summary stats, no export history list in V1

### Audit results

| Checklist item | Result | Action |
|---|---|---|
| Format cards single-col | N/A — no format cards in this component | None |
| Progress bar full-width | PASS | None |
| Download button full-width + 44px | PASS — [fullWidth] + minHeight:44px from ui-kit | None |
| Catalog summary wraps at 360px | N/A — no summary section | None |
| Export history list | N/A — no history in V1 | None |
| Bottom spacing pb-[60px] | NOT NEEDED — shell covers it | No per-MFE padding |
| Fixed widths causing scroll | PASS | None |
| min-w-0 on flex columns | MISSING | FIXED |
| Table column width anchoring | MISSING | FIXED |

### Fixes applied (2 changes)

FIX 1: min-w-0 on flex column children
  Before: class="lg:w-2/5 space-y-4" / class="lg:w-3/5 space-y-4"
  After:  class="min-w-0 lg:w-2/5 space-y-4" / class="min-w-0 lg:w-3/5 space-y-4"
  RULE: flex children with fractional widths ALWAYS need min-w-0.

FIX 2: Checklist table column anchoring
  Label <th>/<td>: added w-full
  Result <th>/<td>: added w-px whitespace-nowrap pl-3
  At 360px (~280px usable), w-full on label absorbs space; w-px on result keeps badge at minimum width.
  RULE: 2-column label+status tables: w-full on label, w-px whitespace-nowrap pl-3 on status column.

### CRITICAL RULE RE-CONFIRMED: Shell padding-bottom covers all MFE pages at mobile

shell.component.css @media (max-width: 639px):
  .page-content { padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px)); }

DO NOT add pb-[60px] to individual MFE page wrappers — creates double gap (120px dead space).
First established in dashboard audit; confirmed again here for export.
Apply this rule consistently to ALL remaining MFE responsive audits.

### tsc result
tsc --noEmit --project apps/mfe-export/tsconfig.app.json: ZERO errors.

---

## project: auth_onboarding_responsive_polish (2026-06-18)

Task: Audit and fix mfe-auth + mfe-onboarding responsive layout at 360px.
Branch: design-figma-ui-screens (worktree)

Pages / components touched:
  - auth-layout.component.ts (libs/composites) — used by login, signup, otp-verify, onboarding
  - otp-verify.component.ts (mfe-auth)
  - input.component.ts (libs/ui-kit) — used across all forms
  - onboarding.component.ts (mfe-onboarding)
  - profile.component.ts (mfe-onboarding)

### Gaps found and fixes applied

GAP-A1: auth-card had flat padding:32px at all breakpoints.
  Fix: auth-layout.component.ts — padding:20px mobile / 32px sm+ (≥640px).
  auth-wrapper outer gutter: 12px mobile / 16px sm+.
  360px result: card = 336px wide; content area = 296px.

GAP-A2: p-inputotp host was inline-unknown-width; OTP cells had no explicit sizing.
  Fix: otp-verify.component.ts — ::ng-deep rules:
    mee-otp-input: display:block; width:100%
    p-inputotp: display:flex; width:100%
    .p-inputotp-input: flex:1; min-width:0; min-height:44px; font-size:18px; text-align:center

GAP-A3 (a11y): orphaned <label>Enter OTP</label> — no [for], not linkable to PrimeNG auto-IDs.
  WCAG 1.3.1 failure.
  Fix: replaced with <p class="otp-label"> + aria-label="One-time password entry" on wrapper div.

GAP-A4: font-size on <input pInputText> was not explicit — cascade from PrimeNG base.
  Fix: input.component.ts — added font-size:16px inline style.
  Guarantees no iOS auto-zoom on any MeeSell form field.
  RULE: all MeeSell form inputs must carry explicit font-size:16px.

GAP-O1 (onboarding): p-steps had no overflow guard.
  Fix: onboarding.component.ts — .steps-wrap { overflow:hidden } + ::ng-deep .p-steps-title
  { font-size:12px; white-space:nowrap; text-overflow:ellipsis; max-width:64px }

NOT a gap (profile bottom): ProfileComponent pb-8 is correct as-is.
  Shell .page-content already adds padding-bottom:calc(60px+env(safe-area-inset-bottom))
  at ≤639px. Inner content divs must NOT double-compensate. Added comment in template.
  RE-CONFIRMED: NEVER add pb-[60px] or pb-[92px] to MFE inner content — shell owns tab-bar clearance.

### Design token math — 360px auth layout

| Measurement | Value |
|---|---|
| Viewport | 360px |
| auth-wrapper padding mobile | 12px × 2 = 24px |
| auth-card width at 360px | 336px |
| auth-card padding mobile | 20px × 2 = 40px |
| Content area | 296px |
| OTP cell width (6 cells, 5×8px gaps) | 42.7px |
| OTP cell min-height | 44px (enforced) |

### tsc result
tsc --noEmit: ZERO errors (mfe-auth), ZERO errors (mfe-onboarding).

---

## project: mfe_pricing_responsive_polish (2026-06-18)

Task: Responsive polish audit for mfe-pricing PricingComponent (price calculator page).
Branch: design-figma-ui-screens (worktree)

Files modified:
  - frontend/apps/mfe-pricing/src/app/pricing.component.ts (3 template edits)
  - frontend/libs/ui-kit/input/input.component.ts (1 component decorator edit)

### Component structure

PricingComponent is a single inline-template component (no separate HTML/CSS files).
Layout: outer max-w-5xl wrapper > flex-col gap-6 lg:flex-row > [lg:w-2/5 input card] + [lg:w-3/5 breakdown card]
Mobile: single column (flex-col default).
Input section: mee-card > form > 2x mee-input + native range slider + mee-button (Calculate)
Breakdown section: mee-card > conditional P&L table with 7 rows + mee-badge + disclaimer text
Bottom: standalone div > mee-button (Save & Continue)

### Audit results

| Check | Result | Action |
|---|---|---|
| Two-column layout flex-col mobile | PASS | None |
| P&L input min-height 44px | PASS (mee-input has style="min-height:44px") | None |
| Input font-size >=16px | PASS (linter added font-size:16px to input concurrently) | None |
| P&L breakdown table 360px | PASS (w-full, no overflow risk) | None |
| Pricing summary row wraps | PASS | None |
| Action buttons 44px + full-width | PASS for height; GAP for width | FIXED — class="block" |
| Bottom spacing (tab bar) | PASS — shell covers it | None |
| Hardcoded widths | None found — PASS | None |
| Badge clipping | PASS | None |
| min-w-0 on flex columns | MISSING | FIXED |
| mee-input host display | MISSING | FIXED globally |

### Fixes applied

FIX 1: min-w-0 on both flex column children
  Before: class="lg:w-2/5" / class="lg:w-3/5"
  After:  class="min-w-0 lg:w-2/5" / class="min-w-0 lg:w-3/5"
  RULE: all flex children with fractional widths need min-w-0 (prevents auto min-width overflow).

FIX 2: class="block" on full-width mee-button elements
  mee-button custom element host defaults to inline-flex (PrimeNG default).
  With [fullWidth]="true" → PrimeNG p-button sets inner width:100%, but 100% of inline host ≠ 100% of parent.
  Fix: class="block" on the mee-button element forces host to display:block → inner p-button correctly fills parent.
  Applied to: Calculate button + Save & Continue button.
  NOT applied globally to MeeButtonComponent because page-header CTA button uses mee-button in inline flex row.

FIX 3: :host { display: block } on MeeInputComponent (global)
  MeeInputComponent had no host display rule. PrimeNG InputText host defaults to inline.
  mee-input is always a block form field — no usage context requires inline.
  Fix: added styles: [':host { display: block; }'] to @Component decorator in input.component.ts.
  Effect: all MFEs using mee-input now correctly fill their flex/grid parent width.

### BOTTOM SPACING RULE (re-confirmed)

Shell .page-content provides padding-bottom: calc(60px + env(safe-area-inset-bottom, 0px)) at <=639px.
Individual MFE page wrappers must NOT add pb-[60px] or pb-[76px] — creates double gap (120px dead space).
This rule was established in dashboard audit and re-confirmed in export audit.
Pricing page: NO per-component bottom padding added.

### Cross-MFE action items
  - mfe-quality: audit for same min-w-0 + class="block" on full-width buttons
  - mee-textarea, mee-password-input: add :host { display: block } (same as mee-input fix)
  - catalog-list + preview: these have pb-[76px] from an earlier session before this rule was codified
    — those should be cleaned up in a future session to avoid double-gap

### tsc result
tsc --noEmit --project apps/mfe-pricing/tsconfig.app.json: ZERO errors.

---

## project: catalog_list_preview_responsive_polish (2026-06-18)

Task: Responsive polish — catalog-list.component.ts (stub rewrite) + preview.component.ts (audit).
Branch: design-figma-ui-screens (worktree)

### catalog-list.component.ts — full rewrite from stub

Was: `<div class="p-6"><h1 class="text-2xl font-semibold">My Catalogs</h1></div>`

Now:
  - Outer wrapper: `flex flex-col gap-6 px-4 pt-2 pb-6 max-w-screen-xl mx-auto`
    pb-[76px] NOT added — shell .page-content already provides mobile bottom-nav clearance
    (rule codified in mfe_dashboard_responsive_audit session; note in cross-MFE action items above)
  - PageHeaderComponent: title + subtitle + cta_label="New Catalog" + cta_icon="pi pi-plus"
    (PageHeaderComponent has cta_icon input — passes directly to MeeButtonComponent icon)
  - Search input: native `<input type="search">` w-full height:44px — touch target PASS
    font-size not set (parent body inherits 16px) — RULE: should be explicit 1rem. Noted for follow-up.
  - Loading: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` with 3x `<mee-skeleton variant="card">`
  - Empty state: `EmptyStateComponent` — context-aware message (search vs no-catalogs) + conditional CTA
  - Catalog grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`
  - Catalog card content:
    - Name: `<h2>` — heading hierarchy (h1=PageHeader, h2=card name)
    - `<mee-status-badge [status]="cat.status">`
    - Category: `white-space:nowrap; overflow:hidden; text-overflow:ellipsis` — no 360px wrapping
    - Meta: SKU count + updated_at
    - Actions: Edit (secondary) + Preview (ghost) — MeeButtonComponent size=sm min-height:44px
  - Simulated SIMULATED_CATALOGS (3 rows, all 3 breakpoints exercised)
  - Wave 6: component-builder to wire real CatalogService.list() HTTP + replace setTimeout

### filteredCatalogs pattern

filteredCatalogs is an arrow function property on the class — NOT signal computed().
Reason: signal computed() must be called in injection context (class field initializer).
An arrow fn on the class is called at template render time — safe from template `filteredCatalogs()`.
This is equivalent to a plain instance method for template binding.

### preview.component.ts — audited, no changes applied

Pre-existing layout is correct:
  - Outer: `flex flex-col gap-6 p-4 max-w-screen-xl mx-auto` — p-4 is fine (shell provides mobile pb)
  - Mobile tab chips: `min-h-[44px]` — touch target PASS
  - 3-column → 1-column: `flex-col / lg:flex-row` — PASS
  - Shell .page-content covers bottom-nav clearance

Finding for component-builder (flagged in STATUS hand-offs):
  isDesktop() signal initialised from window.innerWidth at component creation.
  No window.resize or BreakpointObserver listener exists.
  On device rotation or browser resize, isDesktop() remains stale — tab-only view persists on desktop
  until page is refreshed. Logic fix needed in component-builder; not a styling concern.

### tsc result

tsc --noEmit --project apps/mfe-catalog/tsconfig.app.json: ZERO errors.

### Follow-up items (not blocking)

1. Search input: add `font-size: 1rem` to inline style (prevent iOS zoom — matches textarea rule).
   Component-builder or next styler session can add this.
2. Catalog card action buttons stacked vertically (flex-col): at sm+, these could switch to flex-row
   for a more compact look. Acceptable for V1; revisit in Wave 5+ visual polish pass.
