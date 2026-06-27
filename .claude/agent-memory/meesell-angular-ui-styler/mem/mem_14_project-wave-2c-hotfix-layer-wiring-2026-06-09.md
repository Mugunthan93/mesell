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
