---
name: section-3-locked
description: FRONTEND_ARCHITECTURE.md §3 (File Structure) LOCKED 2026-06-05 with one founder correction — design-system/ reframed as style architecture surface (not SCSS-only)
metadata:
  type: project
---

# FRONTEND_ARCHITECTURE.md §3 LOCKED 2026-06-05

## Founder correction (the one substantive amendment)

**`design-system/` is the style architecture surface, not a SCSS-only folder.**

My original framing was "SCSS only — no TypeScript." Founder corrected: design-system is the architecture surface for style — anything that shapes how the app looks, feels, moves, or responds to breakpoints. That includes:
- SCSS primary: tokens, theme, typography, elevation, motion (the canonical source of truth)
- TypeScript permitted: runtime token mirrors for JS-driven layout decisions, animation timing constants, semantic colors for canvas/chart.js rendering
- Tailwind plugin extensions when `tailwind.config.js` is insufficient

Concretely added to the tree:
- `breakpoints.ts` — TS mirror of SCSS breakpoint tokens; used by lazy-load triggers, virtual-scroll item-size calculations
- `tokens.ts` — TS mirror of selected runtime-readable tokens (motion durations for Angular animations, semantic colors for chart.js)
- `tailwind/` subfolder — custom utility generators

**Discipline rule:** SCSS is the source of truth. TS mirrors are derived. **Never hand-edit only the TS file** — always update SCSS first, then re-derive the TS mirror. V1 ships both hand-maintained with a smoke test asserting parity (Vitest test that imports both, compares numeric values). V1.5 considers a build-time codegen step.

## The 5 locked decisions

1. **Four top-level peers under `app/`**: `core/`, `shared/`, `design-system/`, `features/`. Nothing else. No `pages/`, no `components/`, no `services/`, no `utils/` at the top level. Type-first patterns are explicitly rejected.

2. **Uniform 7-file per-feature pattern**:
   - `<feature>.routes.ts` (required)
   - `<feature>-api.service.ts` (required except `landing`)
   - `<page>/` folder per route (required) — 4 files: `*.component.ts/html/scss/spec.ts`
   - `components/` — optional, feature-private sub-components
   - `<feature>.model.ts` — optional, feature-private types
   - `<feature>-state.service.ts` — optional, feature-private state
   - `<feature>.utils.ts` — optional, feature-private pure functions

3. **`core/api/ApiClient` is a typed HttpClient wrapper.** Features MUST inject `ApiClient`, never raw `HttpClient`. No axios per §6.

4. **The 11 form primitives live INSIDE `catalog-form/primitives/`**, NOT in `shared/`. Reasoning: they exist solely for the wizard renderer and consume a contract tied to `templates.schema_jsonb`. Promote to `shared/` only if V2 surfaces a second use site.

5. **Path aliases**: `@core/*`, `@shared/*`, `@features/*`, `@design-system/*`, `@env`. Relative imports only WITHIN a feature. Cross-feature imports (e.g., `@features/pricing/...` from inside `@features/catalog-form/`) are forbidden per §17.

## Naming conventions (locked in §3.E)

- Files: `kebab-case.{component|service|interceptor|guard|pipe|directive|model|enum|token}.ts`
- Classes: `PascalCase` with type suffix (`AuthService`, `CatalogFormComponent`, `InrCurrencyPipe`, `JwtInterceptor`)
- Selector prefix: `mee-` (MeeSell)
- Test files: `*.spec.ts` (Vitest); `*.e2e.spec.ts` (Playwright)
- SCSS: `kebab-case.scss`; partials prefix with underscore

Angular CLI generators produce these by default. No exceptions for hand-written files.

## How to apply when dispatching specialists

**For `meesell-angular-service-builder` (the recommended first dispatch):**
- Scaffold `app/core/` per §3.C.1 — every file listed
- Scaffold `app/shared/` per §3.C.2 — empty folders for components subfolders, full impl for pipes/directives/enums
- Scaffold each `app/features/<feature>/` per the uniform 7-file pattern §3.D — `*.routes.ts` + `*-api.service.ts` minimum
- Wire `tsconfig.json` paths per §3.F
- DO NOT scaffold `design-system/` files — that's `meesell-angular-ui-styler`'s scope (§5A)
- DO NOT implement any component bodies — those belong to `meesell-angular-component-builder` per the per-feature sections §7-§15

**For `meesell-angular-ui-styler`:**
- Scaffold `app/design-system/` per §3.C.3 — SCSS files + TS mirrors
- Wire `tailwind.config.js` to consume design-system tokens
- Wire `styles.scss` to `@use` design-system/_theme.scss
- DO NOT write component-scoped SCSS — that's the component builder's responsibility

**For `meesell-angular-component-builder`:**
- Implement components inside the scaffolded folders the service-builder created
- Use `mee-` selector prefix
- Use `@if @for @switch @defer` template syntax (per §21 modern techniques)
- Reference design-system tokens via Tailwind classes (preferred) or `@use '@design-system/_tokens' as tokens` in component SCSS

## Dispatch order implication

The locked §3 + §6 (third-party tools) together unblock the first 3 dispatches in order:

1. **`meesell-angular-service-builder`** — scaffolds `core/`, `shared/` (non-design folders), and the 7-file pattern for each feature
2. **`meesell-angular-ui-styler`** — populates `design-system/`, wires Tailwind + Material theme
3. **`meesell-angular-component-builder`** — implements component bodies feature-by-feature (gated on the per-feature §7-§15 LOCKs)
