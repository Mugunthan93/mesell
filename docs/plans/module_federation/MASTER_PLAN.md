# MeeSell Frontend — Module Federation Master Plan

**STATUS: APPROVED 2026-06-10 — ratified by founder. Execution ruling: FEDERATION FIRST (before Wave 6).**

| Field | Value |
|---|---|
| Document type | Master plan (planning only — zero code changes) |
| Source of truth | `docs/FRONTEND_ARCHITECTURE.md` (APPROVED 2026-06-08), `docs/status/STATUS_FRONTEND.md`, `docs/ui_ux/FRONTEND_MODULE_INVENTORY.md`, `docs/ui_ux/FRONTEND_WAVE_EXECUTION_PLAN.md` |
| Author | meesell-frontend-coordinator (master) |
| Purpose | Define the migration from a single Angular 21 app to a federated shell + remotes architecture, optimised for parallel agent work |
| Scope | Frontend only — `frontend/` workspace at `/Users/mugunthansrinivasan/Project/mesell/frontend/` |
| Out of scope | Backend, infra/K3s, AI prompts, mobile (Ionic) — defer to respective coordinators |

---

## 0. Why Federate

Three forcing functions:

1. **Parallel agent work.** Multiple builder agents currently collide on a single repo (auth bypass divergence in Wave 2C, 38 pre-existing test failures rolling forward across waves). Each remote = isolated workspace = zero merge contention.
2. **Independent deploy cadence.** Auth, catalog, pricing, and export have different review/risk profiles. Federation lets each remote ship without rebuilding the shell.
3. **Build-time budget.** CLAUDE.md Decision 12 set a 90 s hard limit; current full build at 2.7–3.2 s leaves headroom, but Wave 6 (real API wiring) + V1.5 features will trend up — federation is the only escape hatch that doesn't penalise users.

CLAUDE.md Decision 12 ("Module Federation deferred to Phase 2") explicitly anchors this plan as a **Phase 2** activity. Wave 5 is now complete, so the trigger condition (Phase 2) is reached.

---

## 1. Current State Assessment

### 1.1 Repo shape

```
frontend/
  src/app/
    design-system/     Layer 1 — SCSS tokens (no library deps)
    ui/                Layer 2 — 17 mee-* PrimeNG wrappers (the abstraction wall)
    shared/            Layer 3 — 5 mee-* composites (stat-card, status-badge, page-header, empty-state, loading-skeleton)
    layouts/           Layer 3 — shell + auth-layout
    features/          Layer 4 — 11 feature pages (landing, account, dashboard, smart-picker,
                       catalog-form, images, preview, pricing, export, profile)
    core/              guards/, interceptors/, services/ (authGuard, jwtInterceptor, errorInterceptor, AuthService)
    app.routes.ts      Single route table — 4 public + 10 shell-child routes
    app.config.ts      bootstrapApplication providers (router, http, primeng theme)
```

### 1.2 What the shell owns today

| Concern | Owner file | Detail |
|---|---|---|
| Top-level routing | `app.routes.ts` | 4 public routes + 1 empty-path parent that mounts `ShellComponent` with `authGuard` and 10 children |
| Auth state | `core/services/auth.service.ts` | AuthService with in-memory access JWT signal + refresh token via HttpOnly cookie (per FE-D5/D6) |
| HTTP plumbing | `core/interceptors/` + `app.config.ts` | `provideHttpClient(withInterceptors([authInterceptor, errorInterceptor]))` |
| Guards | `core/guards/auth.guard.ts` | `authGuard` checks `AuthService.token()` signal, redirects to `/login` if absent |
| Layouts | `layouts/shell/` + `layouts/auth-layout/` | Shell = dark navy sidebar + topbar + `<router-outlet>`; Auth = centered card |
| PrimeNG theme | `app.config.ts` via `providePrimeNG(...)` | Aura preset overridden with MeeSell tokens; loaded once for whole app |
| Tailwind | `styles.css` (`@import "tailwindcss"`) + `postcss.config.mjs` | Single global stylesheet — every component inherits utilities |

### 1.3 What is shared across features

| Shared resource | Consumers | Notes |
|---|---|---|
| `@mee/ui` (17 primitives) | All 11 features | Heavy reuse — every feature imports `mee-button`, `mee-input`; tables/forms use 5–8 each |
| `@mee/shared` (5 composites) | All feature pages with a header (10/11) | `mee-page-header` is universal |
| `@mee/design` (SCSS tokens) | Every styled element | CSS custom properties — naturally global |
| `AuthService` (signal-based token) | jwtInterceptor + authGuard + login/signup/otp + topbar (logout) | Critical singleton |
| `app.routes.ts` ordering | Catalog flow (smart-picker → catalog-form → images → preview → pricing → export) | Linked by `:id` route param threaded through 6 pages |
| `MeeToastService` | Almost every async action | Singleton — `<mee-toast>` host placed once in shell |
| Product/Catalog data model | F6–F12 | Same `:id` semantics; current code keeps each feature's model file local — no cross-feature contract yet |

### 1.4 What would break if features were split today (no federation prep)

| Risk | What breaks | Severity |
|---|---|---|
| Auth token sync | Each remote would build its own `AuthService` instance → token signal not shared → API calls 401 | P0 |
| Routing | Deep links like `/catalogs/:id/edit` require shell to lazy-load the remote, then remote owns sub-route | P0 |
| Singletons | `MeeToastService`, `MeeConfirmService` (PrimeNG `MessageService`/`ConfirmationService` under the hood) must be ONE instance — duplicating breaks toast queue | P0 |
| UI Kit duplication | If each remote bundles its own `mee-*` + PrimeNG, bundle size triples and theme drift appears | P1 |
| PrimeNG theme | `providePrimeNG()` must be called once at the host; if remotes also call it, last-write wins and CSS variables flicker | P1 |
| RxJS / Angular core mismatch | Two RxJS instances → `instanceof Observable` fails across remote boundaries; two Angular zones → change detection breaks | P0 |
| Tailwind class purging | Each remote PostCSS pass only sees its own files → utility classes referenced by shared components but defined in remote get purged | P1 |
| Type safety across remote boundary | Federation hands components as `Promise<any>` without explicit shared interfaces → loses TS strict guarantees | P1 |
| Build pipeline | Single `ng build` produces one bundle today — needs per-remote `angular.json` projects + per-remote CI pipelines | P0 |

---

## 2. Target Architecture

### 2.1 Shell responsibility

```
shell (host application)
├── App bootstrap (main.ts, app.config.ts)
├── Top-level router (all V1 routes, lazy-loading remotes via loadRemoteModule)
├── Auth singleton (AuthService — signal-based token + refresh-token cookie flow)
├── HTTP plumbing (authInterceptor + errorInterceptor — one instance, shared with all remotes)
├── Layouts (ShellComponent + AuthLayoutComponent)
├── Global services (MeeToastService, MeeConfirmService, ErrorService, NetworkService)
├── PrimeNG theme load (providePrimeNG(Aura + MeeSell overrides) — called ONCE)
├── Tailwind base layer (preflight + custom utilities — shared, NOT duplicated per remote)
└── Shared dependency manifest (singletons declared to federation runtime)
```

### 2.2 Remote inventory

Six remotes, grouped by user journey + co-change frequency (NOT one-per-page — co-changing pages stay together to minimise cross-remote PRs).

| ID | Remote slug | Owns features | Owned routes | Co-change rationale |
|---|---|---|---|---|
| R1 | `mfe-auth` | F2 login · F3 signup · F4 otp-verify | `/login`, `/signup`, `/otp-verify` | All three share OTP form contract + AuthLayout; ship together |
| R2 | `mfe-onboarding` | F5 onboarding · F13 profile | `/onboarding`, `/profile` | Both consume the same user/profile schema, share field components |
| R3 | `mfe-dashboard` | F1 landing · F6 dashboard | `/`, `/dashboard` | Landing redirects to dashboard once authenticated; share marketing-style hero composites; smallest remote |
| R4 | `mfe-catalog` | F7 smart-picker · F8 catalog-form · F9 images · F10 preview | `/catalogs`, `/catalogs/new`, `/catalogs/:id/edit`, `/catalogs/:id/images`, `/catalogs/:id/preview` | The product creation funnel — they share Product/Catalog model + flow guards |
| R5 | `mfe-pricing` | F11 pricing | `/catalogs/:id/pricing` | Standalone P&L calculator; mathematically isolated; different change cadence (margin tweaks) |
| R6 | `mfe-export` | F12 export | `/catalogs/:id/export` | Standalone job polling + CSV download; different review profile (compliance-adjacent) |

This split tracks the 4 `meesell-angular-component-builder` parallel groups from `FRONTEND_WAVE_EXECUTION_PLAN.md` (A: auth+profile+onboarding+landing, B: dashboard+picker+form, C: images+preview+pricing+export) — close, but tighter on co-change.

### 2.3 Shared library strategy

Three npm-style workspace packages, hosted **inside the same monorepo** to start (npm/pnpm workspaces) — no separate publish step until V1.5.

| Package | Path (target) | Contents | Federation treatment |
|---|---|---|---|
| `@mesell/ui-kit` | `libs/ui-kit/` | The 17 `mee-*` primitives + barrel | Shared singleton, version-pinned. Remotes import; only one copy in browser. |
| `@mesell/composites` | `libs/composites/` | The 5 `mee-*` composites + ProductStatus types | Shared singleton, version-pinned |
| `@mesell/core` | `libs/core/` | AuthService, ApiClient, interceptors, guards, error/network services, shared models (User, Product, Catalog) | Shared singleton — instance lives in shell, remotes consume via injection token |
| `@mesell/design-tokens` | `libs/design-tokens/` | SCSS tokens, typography, motion, elevation (Layer 1) | NOT a singleton — pure CSS; remotes `@use` at build time, runtime is just CSS vars |

This means features in remotes change FROM `from '../../ui'` TO `from '@mesell/ui-kit'`. The barrel contract is preserved — only the path alias moves.

### 2.4 Routing strategy

```
shell app.routes.ts (top level)
├── '' → loadRemoteModule('mfe-dashboard', './LandingComponent')               [public]
├── 'login' → loadRemoteModule('mfe-auth', './LoginComponent')                  [public]
├── 'signup' → loadRemoteModule('mfe-auth', './SignupComponent')                [public]
├── 'otp-verify' → loadRemoteModule('mfe-auth', './OtpVerifyComponent')         [public]
└── '' (ShellComponent + authGuard) — children:
    ├── 'dashboard' → loadRemoteModule('mfe-dashboard', './DashboardComponent')
    ├── 'profile' → loadRemoteModule('mfe-onboarding', './ProfileComponent')
    ├── 'onboarding' → loadRemoteModule('mfe-onboarding', './OnboardingComponent')
    ├── 'catalogs' → loadRemoteModule('mfe-catalog', './CatalogRoutes')         [remote owns sub-tree]
    ├── 'catalogs/:id/pricing' → loadRemoteModule('mfe-pricing', './PricingComponent')
    └── 'catalogs/:id/export' → loadRemoteModule('mfe-export', './ExportComponent')
```

Rule of thumb: **shell owns top-level path, remote owns deep sub-routes when the remote contains a flow.** R4 (`mfe-catalog`) gets a sub-routes export (`./CatalogRoutes`) because it owns 5 connected pages; the rest expose single components.

### 2.5 State sharing strategy

Auth state is the ONLY truly shared runtime state. Three mechanisms in priority order:

1. **Shared singleton via federation** (PRIMARY). `@mesell/core` declares `AuthService` as a singleton dependency in the federation manifest. Remotes `inject(AuthService)` and receive the shell's instance. Token signal (`auth.token()`) is reactive across remote boundaries because the signal lives in shell.
2. **Injection-token contract** for any data the shell wants to push (e.g., current user, plan tier). Remotes import an interface from `@mesell/core` and inject it; shell provides the implementation.
3. **BroadcastChannel** ONLY for cross-tab events (logout in another tab) — not for in-app sync.

**Explicitly rejected:** NgRx, custom DOM events between remotes, `window`-mounted globals. They violate CLAUDE.md Decision 10.

Per-remote local state stays in component signals (already the pattern in F6–F12 today).

---

## 3. Federation Technology Choice

| Option | Pro | Con |
|---|---|---|
| **Angular Module Federation (`@angular-architects/module-federation`)** — Webpack 5 | Mature, large ecosystem, the original Angular MF wrapper, well-documented | Tied to Webpack; Angular 17+ moved the default builder to esbuild/Vite. Using MF on Angular 21 requires switching back to `@angular-devkit/build-angular:browser` (custom-webpack) — loses esbuild's 10x build speedup currently powering the 2.7 s baseline. |
| **Native Federation (`@angular-architects/native-federation`)** | Builder-agnostic, works with the new esbuild/Vite builder (which MeeSell is on — `@angular/build:application` per Wave 2B), import-maps based, future-proof, smaller runtime | Newer (2.0+ stable); less Stack-Overflow surface; some advanced features (synchronous shared deps) still maturing |

**Recommendation: Native Federation.**

Rationale:
- Wave 2B locked `@angular/build:application` (esbuild) — switching to custom-webpack to use Webpack MF would regress build performance and silently change behaviour for the 11 already-built features.
- Native Federation is the path Angular itself signals support for (deprecation of old `browser` builder).
- Import-maps model maps cleanly onto our singleton story (`@mesell/core` declared once, shell provides).
- The PrimeNG 21 + Tailwind 4 + Sakai-ng stack is ESM-native — fits Native Federation's ESM-first approach.

Acceptance gate: Native Federation version compatible with Angular 21 (confirm `@angular-architects/native-federation@^21`).

---

## 4. Migration Strategy

### 4.1 Approach: strangler-fig extraction

**Chosen.** Reasons:

- Risk: low — each remote extraction is isolated, testable end-to-end before the next.
- Reversible: an extraction can be rolled back by toggling the route back to a `loadComponent` import.
- Aligns with the locked "ship in small batches" culture (Wave 2/3/4/5 cadence).

**Rejected alternative:** scaffold a new federation skeleton + migrate all 11 features in one cutover. Too risky for a 1-founder shop; tests are already brittle (38 pre-existing failures noted in STATUS).

### 4.2 Ordering: first → last

| Order | Remote | Why this position |
|---|---|---|
| **1st (pilot)** | `mfe-pricing` | **Most isolated.** Single page, self-contained P&L math, no flow with neighbours, smallest blast radius, fastest learning loop. Used to validate the federation toolchain on a low-risk surface. |
| 2nd | `mfe-export` | Same isolation profile as pricing; reinforces toolchain confidence; introduces job-polling pattern which will recur in remote-side data services. |
| 3rd | `mfe-onboarding` | Adds a remote that uses AuthService heavily (profile reads/writes via JWT) — first real test of shared singleton across the federation boundary. |
| 4th | `mfe-dashboard` | Includes landing (public) + dashboard (authenticated) — validates the public/private routing split in federation. |
| 5th | `mfe-catalog` | The biggest, most connected remote (5 pages, shared `:id`). Done after the toolchain has been battle-tested by 4 prior extractions. |
| **Last** | `mfe-auth` | **Most connected to shell.** AuthService consumers; the only flow that mutates `auth.token()`; if auth federation breaks, the whole app breaks. Extract last so by the time we touch it we have 5 reference implementations and confidence in singleton handoff. |

### 4.3 Build pipeline changes

| Today | After federation |
|---|---|
| One `angular.json` project; one `ng build` produces one bundle; one Dockerfile; one K8s Deployment | One Angular workspace with N+1 projects (shell + N remotes); each remote builds independently (`ng build mfe-pricing`); each produces its own remote-entry; shell builds with manifest pointing at remote-entry URLs |
| One CI pipeline (lint → test → build → deploy) | One CI pipeline PER remote, triggered on `libs/` or `apps/<remote>/` path changes; shell pipeline triggered on `apps/shell/` or `libs/core` changes |
| One CDN URL serves the whole app | Shell CDN URL + N remote CDN URLs; shell loads remote-entries at runtime; CSP must whitelist remote origins |
| Single version | Each remote versioned independently (`mfe-pricing@1.4.0`); manifest pins versions per environment (dev/staging/prod) |
| `pnpm run build` ~2.7 s | Per-remote build target: <5 s; shell build: <8 s; full pipeline (parallel): <15 s wall-clock |

Infrastructure delta (escalate to `meesell-infra-builder`):
- K3s ingress: one Service per remote (or one Service + path-based routing on Traefik)
- GCS bucket layout: `gs://meesell-frontend/{env}/{remote}/{version}/` — versioned remote-entries enable rollback
- CSP header in shell ingress: `script-src 'self' https://cdn.meesell.in` (remote origin)

---

## 5. Sub-Plans List

Each sub-plan = one remote extraction = one downstream dispatch doc (`SUB_PLAN_<NN>_<remote>.md`) to be authored after this master plan is ratified. The Workspace Foundation sub-plan precedes all extractions.

| # | Sub-plan name | Feature(s) in remote | Complexity | Blocking dependencies | Responsible agent |
|---|---|---|---|---|---|
| 0 | **Workspace Foundation** — convert single-app to Nx-style workspace, create `libs/ui-kit`, `libs/composites`, `libs/core`, `libs/design-tokens`, install Native Federation, scaffold empty shell project, set up per-remote angular.json | none — reorganises shell only | M | none | meesell-frontend-coordinator + meesell-angular-component-builder + meesell-angular-service-builder |
| 1 | **Pilot: mfe-pricing extraction** | F11 pricing | S | Sub-plan 0 | meesell-angular-component-builder |
| 2 | **mfe-export extraction** | F12 export | S | Sub-plan 1 (toolchain validated) | meesell-angular-component-builder |
| 3 | **mfe-onboarding extraction** | F5 onboarding · F13 profile | M | Sub-plan 1; AuthService singleton contract finalised | meesell-angular-component-builder |
| 4 | **mfe-dashboard extraction** | F1 landing · F6 dashboard | M | Sub-plan 1; public-vs-private routing pattern validated | meesell-angular-component-builder |
| 5 | **mfe-catalog extraction** | F7 smart-picker · F8 catalog-form · F9 images · F10 preview | L | Sub-plans 1–4 complete; shared Product/Catalog model promoted to `libs/core/models` | meesell-angular-component-builder + meesell-angular-service-builder (for catalog services) |
| 6 | **mfe-auth extraction (last)** | F2 login · F3 signup · F4 otp-verify | M | Sub-plans 1–5 complete; AuthService singleton + refresh-token flow proven across at least 3 remotes | meesell-angular-service-builder (auth flow critical) |
| 7 | **Federation Cutover & Hardening** — turn off shell-internal fallbacks, enforce CSP, version-pin manifest for staging/prod, smoke test full app | all remotes | M | Sub-plans 1–6 complete | meesell-frontend-coordinator + meesell-infra-builder |

Estimates use S = single session, M = 1–2 sessions, L = 2–3 sessions.

---

## 6. Cross-Cutting Concerns

### 6.1 Auth token sharing — shell → remote

**Mechanism:** shared singleton via Native Federation's import-map. `@mesell/core` exports `AuthService`. Federation manifest declares it `singleton: true, strictVersion: false`. Remotes inject `AuthService`; runtime resolves to the shell's instance. The signal `auth.token()` is reactive in remotes because it IS the shell's signal.

**Why not custom events / BroadcastChannel for in-app sync:** they introduce eventual consistency, race conditions on first paint, and break TypeScript's type safety at the boundary.

**Cross-tab logout:** BroadcastChannel(`mesell-auth`) — shell broadcasts on logout; other tabs' shells listen and clear their `AuthService.token()`. Remotes never touch BroadcastChannel directly.

**Refresh-token flow (HttpOnly cookie, per FE-D5 in `cross_track_contracts.md`):** stays entirely in shell. `jwtInterceptor` (in `libs/core/interceptors`) executes for every HTTP call from any remote → handles 401 → POSTs refresh → retries. Remotes don't know refresh exists.

### 6.2 PrimeNG theme

Shell calls `providePrimeNG({ theme: { preset: Aura, options: { ... } } })` ONCE in `app.config.ts`. Remotes do NOT call `providePrimeNG()`. The theme injects CSS variables onto `:root`, so every component (shell or remote) reads the same variables via `--p-*` and `--mee-*`.

Sakai-ng layout assets stay in shell; remotes never import Sakai paths.

### 6.3 Tailwind CSS strategy

**Single Tailwind build owned by the shell** (NOT per-remote). Why:

- Tailwind 4's `@import "tailwindcss"` produces a global utility layer — duplicating it per remote balloons CSS by ~50KB × N remotes.
- Purging across remotes requires the Tailwind config to see ALL source files. Shell's `postcss.config.mjs` is configured with `content: ['apps/**/*.{html,ts}', 'libs/**/*.{html,ts}']`.
- Risk: a remote uses a Tailwind class the shell hasn't seen → purged → broken UI. Mitigation: Tailwind safelist for runtime-composed classes; CI lint rule that scans remote `.ts/.html` for utilities.

**Per-remote SCSS** (component-scoped styles, mee-* internal styles) stays inside the remote bundle — no global pollution.

### 6.4 Error boundaries — remote load failure

Failure modes:
1. Remote-entry 404 (CDN miss, deploy in progress) → shell shows `<mee-empty-state>` with "Module unavailable, retry in a moment."
2. Remote loads but component throws during init → shell ErrorHandler catches, logs to backend, shows toast via `MeeToastService` ("Something went wrong, refresh to retry.")
3. Network offline during remote load → shell `NetworkService` detects, shows offline banner; queues navigation; retries on reconnect.

Implementation: wrap every `loadRemoteModule(...)` in shell route with `.catch(...)` that returns a `RemoteFailureComponent`. Provide a global ErrorHandler in shell that knows about remote errors.

### 6.5 Type sharing across remote boundary

Native Federation hands components as `Promise<any>` by default. To preserve TS strict mode:
- Every remote exposes a `public-api.ts` that re-exports its public components + interfaces.
- `libs/core/contracts/` holds the typed interfaces (e.g., `PricingPageInputs`) — both shell and remote import from there.
- A shared `tsconfig.base.json` references `libs/*` paths so the typecheck is end-to-end even though runtime resolution is via federation.

### 6.6 Version compatibility

Federation manifest pins shared singleton versions: `@mesell/core@1.2.x`, `@mesell/ui-kit@1.x.x`. If a remote ships against a newer minor than the shell, federation runtime warns. Strategy: shell always ships shared libs at OR AHEAD OF every remote. Enforced in CI via a "shared-libs-version-gate" check.

---

## 7. Risk Register

| # | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| R1 | **Auth singleton drift** — a remote accidentally provides its own `AuthService` (e.g., via `providedIn: 'root'` in a feature that gets bundled into the remote), creating two parallel token signals. Logout in one doesn't propagate. | P0 | Medium | Sub-plan 0 mandates moving `AuthService` to `libs/core` with `@Injectable()` (no `providedIn`); shell registers it in providers. Lint rule: `no-providedin-root` in any `apps/mfe-*/` source. Smoke test: log in via shell, navigate to remote, then log out — assert token is null in BOTH. |
| R2 | **PrimeNG theme duplication** — a remote accidentally calls `providePrimeNG()` (templates copied from feature wave) → CSS variables flicker on remote load → visual regressions only catchable by user. | P1 | High | Lint rule banning `providePrimeNG` imports outside `apps/shell/`. Manual review checklist in each sub-plan. Visual smoke test (Percy/Chromatic deferred — manual founder pass for V1). |
| R3 | **Tailwind purge bug** — a remote-only utility class gets purged because shell's PostCSS scan misses the path. UI breaks only in production. | P1 | Medium | Tailwind config `content` includes `apps/**` + `libs/**` globs (verified in Sub-plan 0). CI runs `ng build` for shell + every remote AND asserts a known utility (`bg-mee-orange-100`) appears in produced CSS. Per-remote `safelist` for dynamic class composition. |
| R4 | **Build-time regression** — Native Federation overhead pushes per-remote build past the 90 s budget (currently 2.7 s baseline). | P1 | Low | Per Sub-plan 1 (pilot), measure cold/warm build times and write them to STATUS file. Stop condition: if shell build > 30 s or any remote > 15 s after Sub-plan 5, halt and re-evaluate. |
| R5 | **Cross-remote contract drift** — a Product/Catalog interface change in `libs/core/models` ships in shell but a remote built against the old shape is still in the manifest. Type mismatch causes runtime crash. | P0 | Medium | CI gate that builds the WHOLE workspace on every shared-lib change; manifest version-pin (shell points at exact remote build hashes per env); deprecation flag on old fields for 1 release before removal. |

Additional watch-list (severity P2, not in top-5):
- Test brittleness during migration (the 38 pre-existing Angular 21 + Vitest TestBed failures need to be sorted before federation, not added to).
- CSP misconfiguration blocking remote-entry script load — coordinate with `meesell-infra-builder` in Sub-plan 7.
- SEO impact of public landing being lazy-loaded from a remote (R4: `mfe-dashboard`) — SSR remains deferred per current arch; landing federates client-side only.

---

## 8. What This Plan Does NOT Cover

- Backend changes (no API contract changes from federation; `meesell-backend-coordinator` not impacted).
- Mobile / Ionic — CLAUDE.md Decision 13 keeps it deferred; federation does not change that.
- Production K3s topology changes — drafted at high level in §4.3, owned by `meesell-infra-builder` in Sub-plan 7.
- Legal copy strings — owned by `meesell-legal-writer`; copy lives in whichever remote renders it.
- AI prompt rotation — no impact (AI engine is backend).

---

## 9. Acceptance Gate to Begin Execution

Before Sub-plan 0 begins, the following must be true:

1. Founder reviews and approves this MASTER_PLAN.md (status: DRAFT → APPROVED).
2. Wave 6 (real API wiring for all 11 features) is either complete OR explicitly deprioritised in favour of federation. Mixing both at once is the single biggest risk to schedule.
3. The 38 pre-existing Angular 21 + Vitest TestBed test failures are triaged — not necessarily fixed, but acknowledged as pre-existing so federation does not get blamed.
4. `meesell-infra-builder` confirms K3s + Traefik can host N+1 services and CSP is editable.

---

## 10. Revision History

| Date | Change | Author |
|---|---|---|
| 2026-06-10 | Initial DRAFT — strangler-fig migration, 6 remotes, Native Federation, pricing pilot, auth last | meesell-frontend-coordinator |
| 2026-06-10 | v1.0 — Ratified DRAFT → APPROVED. Founder ruling: federation executes BEFORE Wave 6 — §9 Gate 2 satisfied via its "explicitly deprioritised" branch. Lead's calculated cost of this ordering (+2 agent-sessions ≈ 28% Wave-6 rework; auth-singleton P0 risk Med→High) acknowledged and accepted; offset: API wiring lands once in its final per-remote home. Gates 3 (38 TestBed failures triaged) and 4 (infra confirms K3s/Traefik N+1 + editable CSP) remain hard preconditions for Sub-plan 0. | founder + master Director session |

---

*End of MASTER_PLAN.md — DRAFT.*
*Next step on approval: author Sub-plan 0 (Workspace Foundation) at `docs/plans/module_federation/SUB_PLAN_00_WORKSPACE_FOUNDATION.md`.*
