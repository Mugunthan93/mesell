# Wave 2B Step 1 — Angular 21 clean-slate scaffold (2026-06-08)

Founder-directed clean re-scaffold replacing the archived Angular 18/20 + Material stack
(now at archive/frontend_angular_material/). New locked stack per FRONTEND_ARCHITECTURE.md
rewrite (2026-06-08): Angular 21 + PrimeNG 21 + Sakai-ng Free + Tailwind CSS 4.

## What got built (verified)
- themes/sakai-ng/ — cloned read-only visual reference (HEAD 96d7149, 57 TS files)
- frontend/ — ng new @ Angular CLI 21.2.14 / framework 21.2.16 / TS 5.9.3
  flags: --standalone --routing --style=css --skip-git --package-manager=pnpm
- primeng 21.1.9 + @primeuix/themes 2.0.3 (runtime deps)
- tailwindcss 4.3.0 + @tailwindcss/postcss 4.3.0 (dev deps)

## Key technical facts to remember
- Angular 21 builder = `@angular/build:application` (esbuild/Vite). NOT webpack.
- Angular 21 ng new default test runner = vitest 4.x (NOT Karma/Jasmine). Old stack used vitest too.
- Angular 21 ng new defaults: zoneless change detection (provideZonelessChangeDetection),
  provideBrowserGlobalErrorListeners, TS strict mode ON.
- Tailwind 4 wiring that WORKED first try: PostCSS path.
  - postcss.config.mjs: `export default { plugins: { "@tailwindcss/postcss": {} } };`
  - src/styles.css: single line `@import "tailwindcss";`
  - The @tailwindcss/vite fallback was NOT needed.
- Tailwind 4 emits utilities on-demand (only classes used in templates). A fresh scaffold's
  built styles-*.css is ~21 kB = base/theme @layer only, no .flex{} yet. This is correct/healthy,
  NOT a broken wiring. Verify wiring via presence of `@layer` marker, not specific utility classes.
- PrimeNG v18+ is styled/themeless mode: theme applied via providePrimeNG({ theme: preset })
  in app.config.ts, NOT via a CSS @import. @primeuix/themes provides Aura/Lara/etc presets.
- primeclt was never installed (CLEAN). Watch for it — it is unwanted.

## Build result
pnpm run build: ZERO errors, 2.278s (well under 90s gate).
main 58.48 kB transfer + styles 4.62 kB transfer = 63.11 kB initial transfer.
Output: dist/frontend/browser/.

## Dispatch discipline note
Founder instruction was explicit: COORDINATOR executes this scaffold directly via Bash
(no specialist dispatch). meesell-angular-ui-styler takes Wave 2B-2 (PrimeNG preset + Tailwind
theme tokens + providePrimeNG wiring). Stopped at green build per instruction.
Design tokens to carry forward: #F26B23 primary, #111c2d sidebar, #f0f5f9 bg.
