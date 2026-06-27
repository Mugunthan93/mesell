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
