# Module Federation Master Plan — DRAFT authored 2026-06-10

**File:** `docs/plans/module_federation/MASTER_PLAN.md` (newly created directory)
**Status:** DRAFT — awaits founder approval
**Trigger:** Wave 5 complete (11/11 features built); Phase 2 entry condition (CLAUDE.md D12) reached.

## Key locked decisions in the draft

1. **Federation runtime:** `@angular-architects/native-federation` (NOT classic Webpack MF). Rationale: Wave 2B locked `@angular/build:application` esbuild builder; switching to custom-webpack would regress the 2.7 s baseline. Native Federation is builder-agnostic and ESM-first.
2. **Six remotes** — grouped by user-journey + co-change cadence, not one-per-page:
   - `mfe-auth` (login/signup/otp)
   - `mfe-onboarding` (onboarding + profile)
   - `mfe-dashboard` (landing + dashboard)
   - `mfe-catalog` (smart-picker + catalog-form + images + preview)
   - `mfe-pricing` (pricing only)
   - `mfe-export` (export only)
3. **Migration:** strangler-fig (NOT big-bang). Pilot = `mfe-pricing` (most isolated). Last = `mfe-auth` (most connected to shell).
4. **Shared libs:** `@mesell/ui-kit`, `@mesell/composites`, `@mesell/core`, `@mesell/design-tokens` in `libs/`. Path alias `from '../../ui'` becomes `from '@mesell/ui-kit'`.
5. **Auth state:** shared singleton via federation manifest (AuthService lives in shell, remotes inject and receive same instance). Refresh-token flow stays entirely in shell jwtInterceptor. BroadcastChannel reserved for cross-tab logout only.
6. **Tailwind:** ONE build at shell level with `content: ['apps/**','libs/**']`. Per-remote duplication rejected.
7. **PrimeNG theme:** `providePrimeNG()` called ONCE in shell. Lint rule bans the import outside `apps/shell/`.

## Sub-plans queued (NOT YET AUTHORED)

| # | Name | Complexity |
|---|---|---|
| 0 | Workspace Foundation (Nx-style libs + Native Federation install) | M |
| 1 | mfe-pricing extraction (pilot) | S |
| 2 | mfe-export extraction | S |
| 3 | mfe-onboarding extraction | M |
| 4 | mfe-dashboard extraction | M |
| 5 | mfe-catalog extraction (biggest, 5 pages) | L |
| 6 | mfe-auth extraction (last, riskiest) | M |
| 7 | Federation Cutover & Hardening | M |

## Acceptance gates before Sub-plan 0 begins

1. Founder approves MASTER_PLAN.md (DRAFT → APPROVED).
2. Wave 6 (real API wiring) complete OR explicitly deprioritised — don't run both at once.
3. The 38 pre-existing Angular 21 + Vitest TestBed test failures triaged (not fixed, but acknowledged so federation isn't blamed).
4. `meesell-infra-builder` confirms K3s + Traefik can host N+1 services and CSP is editable.

## Risks flagged (top 5)

- R1 P0: Auth singleton drift across remotes
- R2 P1: Accidental `providePrimeNG()` call inside a remote
- R3 P1: Tailwind purge missing remote-only utility classes
- R4 P1: Build-time regression past 90 s budget
- R5 P0: Cross-remote contract drift on `libs/core/models`

## What this task did NOT do

- Zero code changes (planning only).
- No agent dispatch.
- No edits to FRONTEND_ARCHITECTURE.md or any existing arch doc.
- No edits to STATUS_FRONTEND.md (this was an out-of-band planning task; status untouched).
