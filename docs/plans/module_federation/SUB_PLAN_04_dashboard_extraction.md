# Sub-Plan 04 — `mfe-dashboard` Extraction (F1 landing + F6 dashboard)

**STATUS: DRAFT 2026-06-10 — authored under master-session night-run dispatch (S3, session `mesell-module-federation-frontend-session-3`). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan (planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10, FEDERATION FIRST) §4.2 ordering "4th" + §5 row 4 |
| Predecessors | SP00 (EXECUTED) + SP01 pilot (toolchain PROVEN, §9.A) + SP02 export (lifecycle/polling proven) + SP03 onboarding (AuthService singleton contract D22 C1–C5 FINALISED; AuthLayout promoted to `@mesell/composites`) |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order |
| Author | meesell-frontend-coordinator (Frontend Lead) |
| Feature slug | `mfe-dashboard` |
| Remote ID | R3 (MASTER_PLAN §2.2) |
| Owned features | F1 landing · F6 dashboard |
| Owned routes | `/` (public landing) · `/dashboard` (authenticated) |
| Complexity | **M** (TWO pages; the FIRST public-vs-private split across the federation boundary; landing is the only public-route remote) |
| Scope | Extract `features/landing/` + `features/dashboard/` into a standalone remote exposing TWO components; wire ONE public top-level route (`/`) AND one authenticated shell-child route (`/dashboard`) to `loadRemoteWithFallback`. Frontend-only. |
| Out of scope | Other remotes; backend; AI; mobile/Ionic; real-API wiring (Wave 6); CSP cutover (Sub-plan 7) |
| Execution gates | SP01 + SP02 + SP03 merged to develop + founder approval of THIS sub-plan + infra C-CI-1 ready (`handoff_mf_ci_prep.md`) + GATE4 Option-C confirmed (`docs/plans/infra/GATE4_CONFIRMATION.md`) |

`mfe-dashboard` is the **fourth extraction** and the **first to federate a PUBLIC route** (MASTER_PLAN §4.2: "validates the public/private routing split in federation"). The landing page (`/`) is the app's only fully-public, pre-auth page that becomes a remote; the dashboard (`/dashboard`) is an authenticated shell-child. So one remote spans BOTH sides of the `authGuard` — the new surface this sub-plan validates. By SP04 the toolchain (SP01 §9.A), the lifecycle/polling pattern (SP02 D18), and the AuthService singleton (SP03 D22) are all proven; SP04 reuses every one of them and adds only the public/private routing proof.

Two facts from the post-SP0 integration-branch reality (verified, `feature/mf-workspace-foundation/integration` @ `e51761b`):
- **`landing.component.ts` is fully public and self-contained** — imports only `RouterLink` (`@angular/router`) + `MeeButtonComponent` (`@mesell/ui-kit`). NO AuthService, NO feature service, NO composites. It is the simplest possible remote component.
- **`dashboard.component.ts` is authenticated but does NOT inject AuthService** — it injects `DashboardApiService` (a local `@Injectable()` non-root service — remote-private), `Router`, `MeeConfirmService` (`@mesell/ui-kit`), `DestroyRef`. It uses `takeUntilDestroyed`, a reactive search `FormControl` with `debounceTime`/`distinctUntilChanged`, and a confirm-delete flow. The authentication is enforced by the SHELL's `authGuard` on the parent route, NOT inside the component — so the remote needs no AuthService to be auth-gated.

---

## Decisions

D-numbers append-only and monotonic, continuing from SUB_PLAN_03 (which ended at D24). FOUNDER-FLAG marks founder-level calls.

### Adaptations from the canonical V1-feature pattern

Same structural-extraction-zero-behaviour-change shape as SP01–03. Adaptations: one lead + one specialist (`meesell-angular-component-builder`, MASTER_PLAN §5 row 4) — NO service-builder (dashboard injects only framework primitives + a remote-private `@Injectable()` service + `MeeConfirmService`; it does NOT touch AuthService, so the SP03 singleton verification does not recur here). §3 is dominated by `MOVE` + the established federation scaffolding `NEW` set + TWO route-swap `MODIFY`s (one public, one private). §9 reuses the SP01 acceptance shape minus §9.A (toolchain already proven) PLUS a new public/private routing assertion.

### D25 — SP04 COPIES the pilot recipe; it does NOT re-derive the toolchain (SP02 D15 precedent)

**Decision.** The `apps/mfe-dashboard/` project shape, `federation.config.js` tokens, `public-api.ts` pattern, the `loadRemoteWithFallback` shell helper, the test-discovery `apps/**/*.spec.ts` include, and the Tailwind `content` glob are all COPIED from the as-built `apps/mfe-pricing/` (the pilot) per `sub_plan_01_pricing.md`, exactly as SP02/SP03 did. SP04 does NOT author a new fallback component or a new helper — both already exist in the shell (SP01 D12, reused by SP02/SP03).

**Rationale.** The pilot's entire purpose (§9.A) was to produce a reusable recipe. Re-deriving it would waste the pilot's investment and risk divergence. The strangler-fig cadence (MASTER_PLAN §4.1) front-loaded the learning.

**Consequence.** SP04's NEW files are the now-standard subset: `apps/mfe-dashboard/{federation.config.js, src/main.ts, src/app/public-api.ts, tsconfig.app.json}` + the moved components + their remote-private model/service. NO new shell infrastructure. The shell route swaps call the EXISTING helper.

### D26 — The remote exposes TWO components: `./LandingComponent` and `./DashboardComponent` (two `exposes` entries, two route swaps — one public, one private)

**Decision.** `mfe-dashboard`'s `federation.config.js` `exposes`:
```
'./LandingComponent':   './apps/mfe-dashboard/src/app/landing.component.ts'
'./DashboardComponent': './apps/mfe-dashboard/src/app/dashboard.component.ts'
```
The shell swaps TWO routes:
- **Public (top-level, NO guard):** `'' (pathMatch: 'full')` → `loadRemoteWithFallback('mfe-dashboard', './LandingComponent')`
- **Private (shell-child, behind `authGuard`):** `'dashboard'` → `loadRemoteWithFallback('mfe-dashboard', './DashboardComponent')`

**Rationale.** First multi-expose-across-the-auth-boundary remote. SP03 already proved one remote can expose two components (D20); SP04 adds the twist that the two exposed components live on OPPOSITE sides of `authGuard`. Both pages are in ONE remote because landing redirects to dashboard once authenticated and they share marketing-style hero composites + co-change cadence (MASTER_PLAN §2.2 R3 rationale). Neither owns a sub-route tree → two single-component exposes (not a `Routes` array), same shape as SP03.

**Consequence.** The manifest gains ONE entry (`mfe-dashboard` → one `remoteEntry.json`); one remote exposes both. The KEY new surface: the **public** `/` route swap. In the as-built `app.routes.ts`, `/` is a top-level route (NOT a shell child) with `pathMatch: 'full'` and NO `authGuard`. The swap MUST preserve `pathMatch: 'full'` and MUST NOT add a guard. The `/dashboard` swap is a shell child and inherits the parent's `authGuard` exactly as today — the guard runs in the SHELL before the remote is even loaded.

### D27 — `authGuard` enforcement stays in the SHELL; the remote `DashboardComponent` is NOT self-guarding — the public/private split is a ROUTING concern, not a remote concern

**Decision.** The `authGuard` (`@mesell/core`, applied to the shell's empty-path protected parent) continues to gate `/dashboard` in the SHELL's route config. The remote `DashboardComponent` does NOT add its own guard, does NOT inject AuthService, and does NOT check authentication — it assumes it is only mounted when the shell's guard has already passed (exactly its current behaviour as a `loadComponent` child). The public `LandingComponent` is mounted with no guard.

**Rationale.** MASTER_PLAN §2.4 routing rule: the shell owns top-level routing and guards; the remote owns its page content. Moving guard logic INTO the remote would (a) duplicate the auth check, (b) force `DashboardComponent` to inject AuthService unnecessarily (it currently does not — verified), and (c) break the "guard runs before the remote is fetched" optimisation (an unauthenticated user hitting `/dashboard` is redirected by the shell guard WITHOUT downloading the dashboard remoteEntry — a real bandwidth + security win). The federation boundary does NOT change where guards run.

**Consequence.** This is the public/private routing proof (§9 item): an unauthenticated user at `/` sees the landing remote (no guard, remote loads); an unauthenticated user at `/dashboard` is redirected to `/login` by the shell guard BEFORE the dashboard remoteEntry is fetched (verify the remote is NOT downloaded on the blocked navigation); an authenticated user at `/dashboard` sees the dashboard remote. This validates the §2.4 split and is the pattern SP05 (catalog, all-private) and SP06 (auth, all-public) lean on.

### D28 — `dashboard.model.ts` + the local `DashboardApiService` (`@Injectable()` non-root) move WITH the component; NOT promoted to `libs/core`

**Decision.** The dashboard-private model (`formatRelativeTime` + the dashboard list/product types in `dashboard.model.ts`, verified) and the local `DashboardApiService` (`@Injectable()` with **no** `providedIn` — a route-scoped simulated-data service returning `of(...).pipe(delay(...))`, verified) move into `apps/mfe-dashboard/src/app/` with the component. They are NOT promoted to `@mesell/core` (no other remote consumes them; grep confirms zero external importers).

**Rationale.** Same as D11/D17/D23: MASTER_PLAN §6.5 promotes only cross-boundary types. The dashboard service + model are remote-private. **NOTE (forward):** when Wave 6 wires the real dashboard/catalog-list API, the product/catalog list types MAY converge with `mfe-catalog`'s model — at THAT point they are a candidate for `@mesell/core/models` + a frontend↔backend contract memo. For V1 (simulated `of().delay()` data) they stay remote-local. Recorded as a forward note, not an SP04 action.

**Consequence.** `DashboardApiService` being `@Injectable()` (NOT `providedIn:'root'`) means it MUST be provided where the dashboard component is mounted. Today the `loadComponent` child has no explicit `providers` array — verify HOW the as-built dashboard obtains `DashboardApiService` (likely a component-level `providers: [DashboardApiService]` on `@Component`, OR a route `providers`). **D28a (sub-decision):** the specialist MUST preserve the EXACT provider registration when moving the component — if it is a `@Component({ providers: [...] })` it moves with the component automatically; if it is a route-level `providers`, the remote's exposed component must carry it (component-level `providers`) since the remote exposes a component, not a route with providers. Verify on extraction; a missing provider = runtime NullInjectorError. This is the SP04 analogue of catalog-form's route-scoped `CatalogFormApiService` that SP05 must handle.

**Confirmed import surfaces (integration branch):**
```
landing:    @angular/router {RouterLink}, @mesell/ui-kit {MeeButtonComponent}.  NO AuthService, NO service, NO composites.
dashboard:  @angular/core {..., DestroyRef, inject}, @angular/core/rxjs-interop {takeUntilDestroyed},
            @angular/forms {ReactiveFormsModule, FormControl}, @angular/router {Router},
            rxjs/operators {debounceTime, distinctUntilChanged},
            @mesell/ui-kit {MeeConfirmService, + card/badge/button/etc.},
            @mesell/composites {... header/composites},
            ./dashboard.model {formatRelativeTime + types}   (moves with component),
            ./services/dashboard-api.service {DashboardApiService @Injectable()}  (moves with component).
            NO AuthService.
```

### D29 — Option-C deploy mirrors SP01–03; `mfe-dashboard` is the fourth remote at `remotes.mesell.xyz`

**Decision.** Per `GATE4_CONFIRMATION.md` C-RES-2 / C-ROUTE-1: built `mfe-dashboard` → `gs://meesell-frontend/{env}/mfe-dashboard/{version}/`, shell manifest gains a fourth entry. Same infra surface (bucket/CDN/host/cert/matrix) stood up at the pilot. Dev-validation uses localhost-served remotes.

**Rationale + Consequence.** Identical to D13/D19/D24. The new (minor) surface is the four-remote manifest; the real new surface is the public-route remote (does a remote serve a PUBLIC, pre-auth route correctly? — the landing remote is fetched with no Authorization header, no guard, which is fine because remoteEntry.json is a static public asset). **CSP note (forward to SP07):** the public landing being a remote means even the FIRST paint for an unauthenticated visitor fetches `remotes.mesell.xyz/.../remoteEntry.json` — so the CSP `script-src https://remotes.mesell.xyz` (C-CSP-1) MUST be live before landing ships to staging/prod, or unauthenticated users get a blank landing page. This raises the stakes of the SP07 CSP deliverable and is recorded for SP07.

### Founder decisions required

**None new.** SP01's FOUNDER-FLAGs D9 (shell stays at `src/`) + D14 (dev-pilot without CSP, deferred to Sub-plan 7) and SP03's D21 (AuthLayout promoted — already merged by SP03) are inherited and apply unchanged. No new founder call. No LOCKED-doc amendment.

---

## Agent lineup

| Lead | Specialist dispatched | What the specialist builds |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | Creates `apps/mfe-dashboard/` (copying the pilot's `apps/mfe-pricing/` shape); `git mv`s `features/landing/**` + `features/dashboard/**` (incl. `dashboard.model.ts` + `services/dashboard-api.service.ts`) into it; rewrites TWO `app.routes.ts` entries — the PUBLIC `''` (pathMatch:full, no guard) and the PRIVATE `dashboard` (shell child) — to the EXISTING `loadRemoteWithFallback`; patches the manifest with a fourth entry; verifies remote builds, shell builds, both pages' tests green, both routes resolve, the public/private split holds (unauth `/` loads landing; unauth `/dashboard` redirects to `/login` WITHOUT fetching the dashboard remote), and `DashboardApiService` still resolves (D28a). |

One lead, one specialist (MASTER_PLAN §5 row 4). NO service-builder — neither page touches AuthService; the SP03 singleton verification does not recur. Infra is a cross-lead dependency (D29 memo), not a dispatched specialist.

### Dispatch order (single specialist, serialized phases)

```
PHASE A — scaffold the remote (copy pilot recipe)   meesell-angular-component-builder
   A1. Copy apps/mfe-pricing/ project shape -> apps/mfe-dashboard/ in angular.json (native-federation:build, remote)
   A2. git mv features/landing/{landing.component.ts,landing.component.spec.ts} -> apps/mfe-dashboard/src/app/
       git mv features/dashboard/{dashboard.component.ts,dashboard.component.spec.ts,dashboard.model.ts} -> apps/mfe-dashboard/src/app/
       git mv features/dashboard/services/dashboard-api.service.ts -> apps/mfe-dashboard/src/app/services/
       (preserve the relative ./dashboard.model + ./services/dashboard-api.service import paths)
   A3. NEW apps/mfe-dashboard/src/app/public-api.ts re-exporting BOTH LandingComponent + DashboardComponent
   A4. NEW apps/mfe-dashboard/federation.config.js name 'mfe-dashboard' exposing BOTH (D26) + shareAll singletons (@mesell/core in shared set — uniform contract even though neither page uses AuthService)
   A5. test-discovery include + Tailwind content already cover apps/** (from SP01) — RE-CONFIRM, do not duplicate
   A6. VERIFY DashboardApiService provider registration survives the move (D28a — component-level providers, NOT a lost route provider)
   A7. BUILD CHECKPOINT — `ng build mfe-dashboard` produces remoteEntry.json — record seconds ; HARD GATE

PHASE B — wire the shell (reuse pilot helper)        meesell-angular-component-builder
   B1. app.routes.ts PUBLIC swap: '' (pathMatch:'full', NO guard) -> loadRemoteWithFallback('mfe-dashboard','./LandingComponent')
   B2. app.routes.ts PRIVATE swap: shell-child 'dashboard' -> loadRemoteWithFallback('mfe-dashboard','./DashboardComponent')
       (the parent authGuard is UNCHANGED — guard stays in the shell, D27)
   B3. public/federation.manifest.json: add "mfe-dashboard" (now FOUR entries)
   B4. FULL VERIFY — shell build ≤90 s ; both pages' tests green ; total count preserved ; boundary clean ;
       PUBLIC: unauth visitor at '/' renders the landing remote (no guard, no redirect) ;
       PRIVATE-blocked: unauth visitor at '/dashboard' is redirected to /login by the shell guard WITHOUT fetching the dashboard remoteEntry ;
       PRIVATE-allowed: authenticated visitor at '/dashboard' renders the dashboard remote ;
       DashboardApiService resolves (no NullInjectorError) ; FOUR remotes coexist in the manifest

PHASE C — lead, no specialist                         meesell-frontend-coordinator
   C1. Re-confirm SP01 toolchain still holds (no §9.A re-derivation; just no-regression)
   C2. 360/1280 screenshots of '/' (landing) + '/dashboard' (no visual change) + the public/private routing proof
   C3. Infra deploy memo (D29 fourth-remote GCS prefix + matrix fan-out + the public-landing CSP note for SP07) + merge-gate review + integration PR
```

---

## Code surfaces

Exhaustive inventory. Tags: `MOVE` (git mv, history-preserving, no logic change), `MODIFY` (in-place edit), `NEW` (net-new file). Source paths verified on `feature/mf-workspace-foundation/integration` (post-SP0 reality).

### Relocation — `features/landing/` + `features/dashboard/` → `apps/mfe-dashboard/src/app/` (6 files incl. specs + model + service)

| # | Source (post-SP0) | Target | Tag | Notes |
|---|---|---|---|---|
| 1 | `frontend/src/app/features/landing/landing.component.ts` | `frontend/apps/mfe-dashboard/src/app/landing.component.ts` | MOVE | Exposed (public). `@mesell/ui-kit` (MeeButton) + `RouterLink` UNCHANGED. The simplest remote component — no service, no AuthService. |
| 2 | `frontend/src/app/features/landing/landing.component.spec.ts` | `frontend/apps/mfe-dashboard/src/app/landing.component.spec.ts` | MOVE | Must stay discovered (R-SP4-3). |
| 3 | `frontend/src/app/features/dashboard/dashboard.component.ts` | `frontend/apps/mfe-dashboard/src/app/dashboard.component.ts` | MOVE | Exposed (private). `@mesell/ui-kit` (MeeConfirmService + others) + `@mesell/composites` imports UNCHANGED; `./dashboard.model` + `./services/dashboard-api.service` relative imports stay relative (move alongside). NO AuthService. |
| 4 | `frontend/src/app/features/dashboard/dashboard.component.spec.ts` | `frontend/apps/mfe-dashboard/src/app/dashboard.component.spec.ts` | MOVE | Must stay discovered. Verify it provides `DashboardApiService` (it is `@Injectable()` non-root). |
| 5 | `frontend/src/app/features/dashboard/dashboard.model.ts` | `frontend/apps/mfe-dashboard/src/app/dashboard.model.ts` | MOVE | `formatRelativeTime` + list/product types — remote-private (D28). |
| 6 | `frontend/src/app/features/dashboard/services/dashboard-api.service.ts` | `frontend/apps/mfe-dashboard/src/app/services/dashboard-api.service.ts` | MOVE | `DashboardApiService` `@Injectable()` (non-root) — remote-private. Preserve the `services/` subdir so the relative import (`./services/dashboard-api.service`) is unchanged (D28). |

After the move, `frontend/src/app/features/landing/` + `frontend/src/app/features/dashboard/` are removed.

### Federation scaffolding — `apps/mfe-dashboard/` (NEW, copies the pilot)

| # | Path | Tag | Description |
|---|---|---|---|
| 7 | `frontend/apps/mfe-dashboard/src/app/public-api.ts` | NEW | Re-exports `LandingComponent` + `DashboardComponent` (§6.5 — BOTH, D26). |
| 8 | `frontend/apps/mfe-dashboard/federation.config.js` | NEW | `name: 'mfe-dashboard'`, TWO `exposes` entries (D26), `shareAll` singletons — `@mesell/core` in the shared/singleton set (uniform contract, D22 C1, even though neither page uses AuthService). |
| 9 | `frontend/apps/mfe-dashboard/src/main.ts` | NEW | Dev-serve bootstrap (router with both routes for standalone dev). |
| 10 | `frontend/apps/mfe-dashboard/tsconfig.app.json` | NEW | Extends base; `@mesell/*` paths. |

### Shell wiring (MODIFY — reuse SP01 helper)

| # | Path | Tag | Description |
|---|---|---|---|
| 11 | `frontend/src/app/app.routes.ts` | MODIFY | TWO swaps: PUBLIC `''` (pathMatch:'full', NO guard) → `loadRemoteWithFallback('mfe-dashboard','./LandingComponent')`; PRIVATE shell-child `dashboard` → `loadRemoteWithFallback('mfe-dashboard','./DashboardComponent')`. The parent `authGuard` UNCHANGED (D27). ALL other routes UNCHANGED. |
| 12 | `frontend/public/federation.manifest.json` | MODIFY | Add `"mfe-dashboard"` (now FOUR entries: pricing, export, onboarding, dashboard). |
| 13 | `frontend/angular.json` | MODIFY | Add `projects.mfe-dashboard` (native-federation:build remote + serve target). Shell project UNCHANGED. |
| 14 | test-discovery `include` + Tailwind `content` | RE-CONFIRM | `apps/**` globs from SP01 already cover the new project. No edit expected. |

### Documentation / status / memory

| # | Path | Tag | Description |
|---|---|---|---|
| 15 | `docs/status/feature_board_frontend.md` | MODIFY | `mfe-dashboard` row lifecycle (IN PROGRESS → IN REVIEW → MERGED) + infra inter-lead row (D29). |
| 16 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log chunk — build/test numbers, the public/private routing-proof result. |
| 17 | `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_04_dashboard.md` | NEW | The public/private routing recipe (the SP04 forward contract — consumed by SP05 all-private + SP06 all-public) + the `@Injectable()` non-root provider-preservation note (D28a). |

No backend/AI/data/OpenAPI/prompt-registry surface. No LOCKED-doc amendment.

### Illustrative `federation.config.js` (remote) shape

```js
// frontend/apps/mfe-dashboard/federation.config.js
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

module.exports = withNativeFederation({
  name: 'mfe-dashboard',
  exposes: {
    './LandingComponent':   './apps/mfe-dashboard/src/app/landing.component.ts',
    './DashboardComponent': './apps/mfe-dashboard/src/app/dashboard.component.ts',
  },
  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
    // @mesell/core kept in the shared/singleton set for contract uniformity (D22 C1),
    // even though neither landing nor dashboard injects AuthService.
  },
  skip: ['rxjs/ajax', 'rxjs/fetch', 'rxjs/testing', 'rxjs/webSocket'],
  features: { ignoreUnusedDeps: true },
});
```

### Illustrative shell route swaps (public + private)

```ts
// frontend/src/app/app.routes.ts (excerpt — TWO swaps, all else unchanged)
// PUBLIC top-level (NO authGuard, pathMatch preserved):
{ path: '', pathMatch: 'full',
  loadComponent: loadRemoteWithFallback('mfe-dashboard', './LandingComponent') },
// ...
// PRIVATE shell child (parent authGuard already gates this — UNCHANGED):
{ path: 'dashboard',
  loadComponent: loadRemoteWithFallback('mfe-dashboard', './DashboardComponent') },
```

---

## Documentation deliverables

Gate conditions in §9. The PR cannot merge to integration without:

1. **`SUB_PLAN_04_dashboard_extraction.md`** (this document) — referenced from MASTER_PLAN §5 row 4.
2. **`sub_plan_04_dashboard.md` memo** — the public/private routing recipe (unauth `/` loads landing; unauth `/dashboard` redirects WITHOUT fetching the remote; auth `/dashboard` renders) + the `@Injectable()` non-root provider-preservation note (D28a). Consumed by SP05 (all-private catalog) + SP06 (all-public auth).
3. **Infra deploy memo** (`handoff_mf_dashboard_deploy.md`) — fourth-remote GCS prefix + matrix fan-out (C-CI-1) + the public-landing CSP escalation note for SP07 (C-CSP-1: landing's first paint fetches `remotes.mesell.xyz` even for unauthenticated visitors).
4. **`feature_board_frontend.md` + `STATUS_FRONTEND.md`** kept current through the lifecycle.
5. **No MASTER_PLAN edit required** beyond a §5 row-4 status note recorded in the §11 revision history.

---

## Branch setup

Per repo-management §1.2 as amended F1 (integration branch = `feature/{name}/integration`). The feature slug is `mfe-dashboard`.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-dashboard/integration` | `develop` (AFTER SP03 merged) | Integration branch; merge commits + status-only board flips | Frontend Lead (merge approval) |
| `feature/mfe-dashboard/frontend` | `feature/mfe-dashboard/integration` | ALL extraction + federation-wiring work | `meesell-angular-component-builder` |

No infra group branch is cut by THIS sub-plan: infra deploy work is owned by `meesell-infra-builder` as a parallel effort triggered by the §6 memo. The frontend merge does not block on infra (dev-validation uses localhost-served remotes, D29).

### F1 branch-setup commands (EXECUTION stage — NOT run in this authoring session)

```bash
git fetch origin develop
git checkout develop && git pull --ff-only          # must include SP03's merge

git checkout -b feature/mfe-dashboard/integration develop
git push -u origin feature/mfe-dashboard/integration

git checkout -b feature/mfe-dashboard/frontend feature/mfe-dashboard/integration
git push -u origin feature/mfe-dashboard/frontend

git worktree add /tmp/mesell-wt/mfe-dashboard feature/mfe-dashboard/frontend
```

### PR flow

```
feature/mfe-dashboard/frontend
        │  PR — Frontend Lead reviews+merges (squash)   [repo-mgmt §2.1 / D1]
        ▼
feature/mfe-dashboard/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [repo-mgmt §2.2 / D1]
        ▼
develop
```

Group → integration: **Frontend Lead** reviewer. Integration → develop: **Founder** reviewer (the lead must NOT approve this gate). Branch protection F3 profile on the integration branch — re-probe empirically.

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (own memory — esp. the `../libs/**` / `apps/**` test-discovery gotcha; the pnpm-worktree native-build fix `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract`; the deep-import bundle landmine)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md` (THE recipe) + `sub_plan_02_export.md` (lifecycle) + `sub_plan_03_onboarding.md` (the AuthService singleton contract — NOT exercised here, but read for the uniform `@mesell/core` shared-set rule)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md` (the alias map)
- `docs/plans/module_federation/MASTER_PLAN.md` §2.2 (R3 co-change rationale), §2.4 (routing — the public/private rule), §6.4 (error boundary)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (GATE4 Option-C; C-CI-1; C-CSP-1)

### Cross-feature memos

- **Outgoing → infra:** `handoff_mf_dashboard_deploy.md` — fourth-remote GCS prefix + matrix fan-out (C-CI-1) + the public-landing CSP escalation for SP07. 48h SLA. Board inter-lead row added (outgoing); infra adds its own incoming row.
- **Forward-reference:** `sub_plan_04_dashboard.md` — the public/private routing recipe + the `@Injectable()` non-root provider note (SP04's gift to SP05/SP06).

### Session-close memory entries

Session header (`## Session mesell-mfe-dashboard-frontend-session-{N}`), D25–D29 outcomes (esp. the public/private routing proof + the D28a provider preservation), files-touched count, remote + shell build seconds, test pass count (must equal the prior baseline), boundary-grep result, the public/private routing proof (unauth `/` loads; unauth `/dashboard` redirects without fetching the remote; auth `/dashboard` renders), blockers, next-step (Sub-plan 5 catalog readiness).

---

## Dispatch templates

One `### h3` per specialist. Paste-able for the EXECUTION session (runs after SP03 merged + founder approval of this sub-plan).

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-dashboard-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_04_dashboard_extraction.md (this plan — D25-D29, esp. D26 two-expose + D27 guard-stays-in-shell + D28/D28a provider preservation, §3, §9)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md (THE recipe) + sub_plan_02_export.md + sub_plan_03_onboarding.md (uniform @mesell/core shared-set rule)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (apps/**/*.spec.ts test-discovery gotcha; pnpm rebuild fix; deep-import bundle landmine)
- docs/plans/module_federation/MASTER_PLAN.md §2.4 (routing — public/private rule), §6.4 (error boundary)

## Your mission
PHASE A: Copy apps/mfe-pricing/ shape -> apps/mfe-dashboard/ in angular.json (native-federation:build, kind remote). `git mv` features/landing/{landing.component.ts,.spec.ts} + features/dashboard/{dashboard.component.ts,.spec.ts,dashboard.model.ts} + features/dashboard/services/dashboard-api.service.ts -> apps/mfe-dashboard/src/app/ (keep the services/ subdir so ./services/dashboard-api.service stays relative; keep ./dashboard.model relative; @mesell/* imports UNCHANGED). NEW public-api.ts re-exporting BOTH LandingComponent + DashboardComponent. NEW federation.config.js name 'mfe-dashboard' exposing BOTH ('./LandingComponent','./DashboardComponent') + shareAll singletons with @mesell/core in the shared set. VERIFY DashboardApiService (@Injectable() non-root) provider registration survives the move (component-level providers, NOT a dropped route provider — D28a). BUILD CHECKPOINT: `ng build mfe-dashboard`. HARD GATE.
PHASE B: app.routes.ts -> (1) PUBLIC swap: '' (pathMatch:'full', NO guard) -> loadRemoteWithFallback('mfe-dashboard','./LandingComponent'); (2) PRIVATE swap: shell-child 'dashboard' -> loadRemoteWithFallback('mfe-dashboard','./DashboardComponent') (parent authGuard UNCHANGED — guard stays in the shell, D27). manifest: add "mfe-dashboard" (FOUR entries). VERIFY (see acceptance).

## Acceptance criteria
- [ ] apps/mfe-dashboard/ holds landing + dashboard (+ specs + model + service in services/) + public-api + federation.config + main.ts; old features removed
- [ ] federation.config exposes BOTH; @mesell/core shared+singleton
- [ ] DashboardApiService resolves at runtime (no NullInjectorError) — D28a provider preserved
- [ ] `ng build mfe-dashboard` GREEN -> remoteEntry.json (record seconds)
- [ ] shell `pnpm build` GREEN ≤ 90 s (seconds + initial bundle delta noted)
- [ ] `pnpm test` total == prior baseline, 0 failing/skipped (drop = spec not discovered = HARD REJECT)
- [ ] boundary grep clean — no new PrimeNG leak from apps/mfe-dashboard/
- [ ] PUBLIC: unauth visitor at '/' renders the landing remote (no guard, no redirect)
- [ ] PRIVATE-blocked: unauth visitor at '/dashboard' is redirected to /login by the shell guard WITHOUT fetching the dashboard remoteEntry
- [ ] PRIVATE-allowed: authenticated visitor at '/dashboard' renders the dashboard remote
- [ ] manifest has FOUR entries (pricing, export, onboarding, dashboard)

## Hard constraints
- ZERO logic/template edits to landing/dashboard/model/service — relocation only
- Do NOT add a guard or AuthService into the remote — guard stays in the shell (D27); dashboard does NOT inject AuthService today, keep it that way
- Do NOT promote dashboard.model/DashboardApiService to libs/core (D28)
- Do NOT author a new fallback/helper (reuse SP01); do NOT move the shell into apps/shell/ (D9); do NOT author CSP (D14)
- Do NOT touch backend/, k8s/, infra/, OR other remotes/features

## Files you MAY touch
- frontend/apps/mfe-dashboard/** (new), frontend/angular.json (add project), frontend/public/federation.manifest.json
- frontend/src/app/app.routes.ts (the '' public + 'dashboard' private entries ONLY)

## Files you must NOT touch
- frontend/apps/mfe-pricing|export|onboarding/** (done); src/app/core/{remote-failure,load-remote} (reuse); libs/** (consumed); backend/k8s/infra

## Final report format
Files moved (count), files new (count), remote build seconds, shell build seconds + initial bundle delta, test pass count (must equal prior baseline), boundary-grep output, the public/private routing proof (3 cases), DashboardApiService-resolves proof, manifest entry count. Then STOP for lead review + PR.
```

---

## Review + iteration protocol

### meesell-angular-component-builder

- **Pre-approval checklist (lead inspects):** (a) `git log --follow` on the 6 moved files shows preserved history; (b) landing/dashboard/model/service diffs empty except path context — NO logic/template change; (c) `federation.config.js` has `name:'mfe-dashboard'` + exactly two `exposes` entries; (d) the shell `federation.config.js` is UNCHANGED (still `name:'shell'`); (e) `public/federation.manifest.json` has FOUR entries; (f) the PUBLIC `''` route swap preserved `pathMatch:'full'` and added NO guard; the PRIVATE `dashboard` swap kept the parent `authGuard` UNCHANGED (D27); (g) the public/private routing proof was demonstrated (3 cases incl. the remote-NOT-fetched-on-redirect case); (h) `DashboardApiService` resolves (no NullInjectorError — D28a); (i) test count == prior baseline; (j) shell build ≤90 s.
- **PR-template gate:** `.github/PULL_REQUEST_TEMPLATE/frontend.md` filled completely, no `<>` placeholders. Build evidence (remote + shell seconds), bundle delta, 360/1280 screenshots of `/` (landing) + `/dashboard` (no visual change), a11y confirmed, boundary-grep output, the public/private routing proof.
- **Re-dispatch triggers:** "edited landing/dashboard logic" → re-dispatch quoting the no-logic rule; "added a guard/AuthService into the remote" → re-dispatch quoting D27; "broke the public `''` route (added a guard or dropped pathMatch:full)" → re-dispatch quoting D26/D27; "unauth `/dashboard` fetched the remote before redirecting" → re-dispatch quoting D27 (guard must run before the fetch); "DashboardApiService NullInjectorError" → re-dispatch quoting D28a (preserve the provider); "re-authored fallback/helper" → re-dispatch quoting SP02 D15; "test count dropped" → the `apps/**/*.spec.ts` include note; "promoted model/service to libs/core" → re-dispatch quoting D28.
- **Re-dispatch prompt shape:** original prompt + "Previous run failed on X (paste grep/test/build/routing output); fix only that; re-run build + test + boundary-grep + the 3-case routing proof."
- **Iteration cap: 3.** Third re-dispatch auto-escalates to founder.

---

## Acceptance gate

When every box is `[x]`, `feature/mfe-dashboard/integration` is ready for the founder's develop PR.

- [ ] PR (`feature/mfe-dashboard/frontend` → integration) merged by Frontend Lead (squash)
- [ ] `ng build mfe-dashboard` GREEN — produces `remoteEntry.json` exposing BOTH components (record seconds)
- [ ] Shell `pnpm build` GREEN and **≤ 90 s** (CLAUDE.md Decision 12 / Stop Condition) — seconds + initial bundle delta recorded in PR + STATUS
- [ ] `pnpm test` total == **prior baseline, 0 failing, 0 skipped** — any new failure OR a count DROP blocks merge (R-SP4-3)
- [ ] **Boundary grep clean:** PrimeNG imports appear ONLY under `libs/ui-kit/` + the SP0-enumerated carve-outs. No new leak from `apps/mfe-dashboard/`.
- [ ] **Public route works:** an unauthenticated visitor at `/` renders the remote `LandingComponent` (no guard, no redirect, `pathMatch:'full'` preserved)
- [ ] **Private route guarded in the shell (D27):** an unauthenticated visitor at `/dashboard` is redirected to `/login` by the shell `authGuard` WITHOUT fetching the dashboard `remoteEntry` (verify the remote is NOT downloaded on the blocked navigation)
- [ ] **Private route works when authenticated:** an authenticated visitor at `/dashboard` renders the remote `DashboardComponent`
- [ ] **`DashboardApiService` resolves** (no NullInjectorError) — the `@Injectable()` non-root provider survived the move (D28a)
- [ ] **FOUR remotes coexist** in the manifest (`mfe-pricing`, `mfe-export`, `mfe-onboarding`, `mfe-dashboard`)
- [ ] **Fallback still works (SP01 D12):** a deliberately-broken `mfe-dashboard` manifest URL degrades to `RemoteFailureComponent`, not a white screen
- [ ] FOUNDER-FLAGs: D9 + D14 inherited from SP01; D21 inherited from SP03 (no new founder call)
- [ ] Infra deploy memo filed (D29 — GCS prefix/matrix + the public-landing CSP escalation for SP07); board inter-lead row added
- [ ] `feature_board_frontend.md` row = MERGED; STATUS_FRONTEND.md Updates Log appended; `sub_plan_04_dashboard.md` recipe memo written
- [ ] **Founder approval** on `feature/mfe-dashboard/integration` → `develop` (founder's gate, NOT the lead's)

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SP4-1 | **Public `''` route swap breaks** — the swap drops `pathMatch:'full'` (catching every path) or accidentally inherits a guard, so the public landing is no longer reachable pre-auth (or every route resolves to landing). | Medium | High | D26/D27: the swap preserves `pathMatch:'full'` and adds NO guard; the `''` route stays a TOP-LEVEL route (not a shell child). §9 verifies an unauth visitor at `/` renders landing AND that other routes still resolve. The deliberate test: load `/` and `/login` unauth — both must render their own pages. |
| R-SP4-2 | **Guard moved into the remote** — the specialist adds an `authGuard` or an AuthService check inside `DashboardComponent`, duplicating the shell guard and forcing an AuthService injection the page never had. | Medium | Medium | D27: guard stays in the shell. Pre-approval checklist item (f)+(g). The dashboard component must NOT import AuthService (it doesn't today — verify the diff adds no AuthService import). |
| R-SP4-3 | **Spec-discovery regression** — moving landing + dashboard specs into `apps/mfe-dashboard/`; relies on SP01's `apps/**/*.spec.ts` glob. | Medium | High | RE-CONFIRM the glob (do not re-add); assert exact total count preserved; a drop is a hard reject. (Same recipe as SP01 §9.A item 6 / R-SP1-3.) |
| R-SP4-4 | **`DashboardApiService` lost on the move (NullInjectorError)** — the `@Injectable()` non-root service's provider registration is dropped during relocation (e.g. it was a route-level provider that doesn't travel with a component-only expose). | Medium | High | D28a: the specialist verifies the provider survives — if it is a `@Component({providers:[...]})` it moves automatically; if route-scoped, it must become component-level on the exposed remote component. §9 verifies the dashboard renders + the API call resolves (no NullInjectorError). This is the SP04 analogue of catalog-form's route-scoped service SP05 must handle. |
| R-SP4-5 | **Public-landing CSP gap in staging/prod** — landing as a remote means an UNAUTHENTICATED visitor's first paint fetches `remotes.mesell.xyz`; without the CSP `script-src` allowlist (C-CSP-1) the landing page is blank for every new visitor. | Low (dev) / High (prod) | High | D29 + inherited D14: dev has NO CSP, so the pilot/SP04 validate on dev. The public-landing CSP escalation is recorded in the infra memo + flagged to SP07 (C-CSP-1) as a RAISED-STAKES item: landing is the highest-traffic, lowest-tolerance page for a CSP miss. Do NOT ship `mfe-dashboard` to staging/prod until CSP is authored + smoke-tested. |
| R-SP4-6 | **Landing → dashboard redirect breaks across the boundary** — if landing programmatically redirects authenticated users to `/dashboard`, that navigation now crosses from one exposed component to another within the same remote. | Low | Medium | Both components are in the SAME remote (one `remoteEntry.json`); a `router.navigate(['/dashboard'])` from landing resolves via the shell router → loads the dashboard expose from the already-fetched remote. Verify the authenticated-landing-redirect path still lands on the dashboard remote (if such a redirect exists in `landing.component.ts` — it currently uses `RouterLink`, so navigation is declarative and shell-routed). |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-3` (night-run master-session dispatch) | Initial authoring of Sub-Plan 04 — `mfe-dashboard` (F1 landing + F6 dashboard). Grounded in the POST-SP0 integration-branch reality (`e51761b`): landing is fully public + self-contained (RouterLink + MeeButton only, no AuthService/service); dashboard is authenticated-via-shell-guard but does NOT inject AuthService (it injects a remote-private `@Injectable()` non-root `DashboardApiService` + `MeeConfirmService` + Router). D25–D29 (copy-the-recipe; two-expose D26; guard-stays-in-shell public/private split D27; remote-private model+service D28 + provider-preservation D28a; Option-C fourth-remote D29). The new validated surface = the public/private routing split (unauth `/` loads landing; unauth `/dashboard` redirects WITHOUT fetching the remote; auth `/dashboard` renders) — the recipe SP05 (all-private) + SP06 (all-public) consume. 6 risks incl. the public `''`-route break (R-SP4-1), the `@Injectable()` non-root provider loss (R-SP4-4), and the raised-stakes public-landing CSP gap (R-SP4-5, escalated to SP07). No new FOUNDER-FLAG (D9/D14/D21 inherited). No LOCKED-doc amendment. Awaits founder approval to EXECUTE; gated on SP03 merge + infra C-CI-1. |
