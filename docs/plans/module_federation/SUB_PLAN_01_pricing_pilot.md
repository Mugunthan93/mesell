# Sub-Plan 01 — Pilot: `mfe-pricing` Extraction (F11)

**STATUS: DRAFT 2026-06-10 — authored under master-session night-run dispatch (S3, session `mesell-module-federation-frontend-session-2`). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan (planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10, FEDERATION FIRST) §4.2 ordering "1st (pilot)" + §5 row 1 |
| Predecessor | `SUB_PLAN_00_workspace_foundation.md` (EXECUTED — PR#40 squash `e51761b` to `feature/mf-workspace-foundation/integration`; PR#41 integration→develop OPEN on founder gate) |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order |
| Author | meesell-frontend-coordinator (Frontend Lead) |
| Feature slug | `mfe-pricing` |
| Remote ID | R5 (MASTER_PLAN §2.2) |
| Owned feature | F11 pricing (P&L calculator) |
| Owned route | `/catalogs/:id/pricing` |
| Complexity | **S** (single page, mathematically isolated, no AuthService dependency, no neighbour flow) |
| Scope | Extract `features/pricing/` into a standalone Native-Federation remote project; wire the shell route to `loadRemoteModule` with fallback; prove the toolchain end-to-end. Frontend-only. |
| Out of scope | Any other remote (Sub-plans 2–7); backend; AI; mobile/Ionic; real-API wiring (Wave 6); CSP hardening cutover (deferred to Sub-plan 7, C-CSP-1) |
| Execution gates | PR#41 (SP0) merged to develop + founder approval of THIS sub-plan + infra C-CI-1 ready (`handoff_mf_ci_prep.md`) + GATE4 Option-C confirmed (`docs/plans/infra/GATE4_CONFIRMATION.md`) |

This is **the pilot**. It is the first sub-plan to introduce a `loadRemoteModule` call (SP0 has zero), the first independently-built Angular project, the first GCS/CDN-hosted remote bundle, and the first cross-boundary federation resolution. Its job is not just to ship `mfe-pricing` — it is to **prove the toolchain** so Sub-plans 02–06 can copy a known-good recipe. The §9 acceptance gate doubles as the toolchain-validation checklist that every later extraction depends on (see §9.A "Pilot validation criteria").

`mfe-pricing` was chosen as pilot (MASTER_PLAN §4.2) because it is the lowest-blast-radius surface: a single page, self-contained P&L math (`pricing.utils.ts` + `pricing.model.ts`), **no AuthService dependency** (verified — the component injects only `FormBuilder`, `ActivatedRoute`, `Router`), and no flow shared with a neighbour. A toolchain bug surfaces here without endangering auth or the catalog funnel.

---

## Decisions

D-numbers are append-only and monotonic, continuing from SUB_PLAN_00 (which ended at D7). Founder-level calls are marked **FOUNDER-FLAG** per the stop-condition protocol.

### Adaptations from the canonical V1-feature pattern

`_CANONICAL_PATTERN.md` v2.1 targets a user-facing product slice. This sub-plan is a **structural extraction with zero behaviour change** — the pricing page must render and compute identically before and after. Adaptations:

- **§2 Agent lineup** — one lead (frontend) + one specialist (`meesell-angular-component-builder`, per MASTER_PLAN §5 row 1). No service-builder (pricing has no service/interceptor work). No cross-track lineup.
- **§3 Code surfaces** — dominated by `MOVE` (relocating `features/pricing/**` into a new `apps/mfe-pricing/` project) + `NEW` federation scaffolding (project config, `public-api.ts`, `federation.config.js`) + one `MODIFY` (shell route swap to `loadRemoteModule`).
- **§9 Acceptance gate** — substance is "no regression + remote loads in shell": build green ≤90 s, pricing tests green, the 401-baseline preserved, boundary clean, route resolves AND the component renders when loaded as a remote.

### D8 — Remote project shape: a SECOND Angular project in the SAME workspace, built with Native Federation `dynamic-host`→`remote`

**Decision.** `mfe-pricing` is added to `frontend/angular.json` as a **new project** under `apps/mfe-pricing/` (sibling of the shell, which SP0 named `shell`). It is built by the Native Federation **remote** builder (`@angular-architects/native-federation:build` with a `federation.config.js` of `kind: 'remote'`), producing its own `remoteEntry.json` + ESM chunks. The shell stays the `dynamic-host`. The shared `libs/` are consumed by BOTH projects via the `@mesell/*` aliases established in SP0.

**Rationale.** MASTER_PLAN §4.3 ("One Angular workspace with N+1 projects … each remote builds independently") + §2.3 (shared libs hosted inside the same monorepo). Keeping `mfe-pricing` in the same workspace (not a separate repo) means it reuses the SP0 `tsconfig` paths, the single `node_modules`, and the single Tailwind build owned by the shell (§6.3) — no per-remote dependency duplication for V1.

**Consequence.** `frontend/apps/mfe-pricing/` is the new home. The MASTER_PLAN §2.3 "apps/" prefix (referenced in the §2.4 routing block and the §6.3 Tailwind `content: ['apps/**','libs/**']` glob) is now realised for the first time. SP0 created `libs/` but no `apps/` dir — D8 creates `apps/` (both `apps/shell/` conceptually and `apps/mfe-pricing/`). **See D9 for whether the shell physically moves into `apps/shell/`.**

### D9 — The shell does NOT physically relocate into `apps/shell/` in this sub-plan; `apps/` holds only the new remote — **FOUNDER-FLAG (scope reconciliation)**

**Decision.** SP0 left the shell at `frontend/src/` (the default `@angular/build:application` source root) with `libs/` as siblings. Moving the shell into `apps/shell/src/` is a large mechanical churn (every shell-relative path, `angular.json` `sourceRoot`, `tsconfig` references) with zero behaviour benefit for the pilot. **For Sub-plan 01 the shell stays at `frontend/src/`; only `apps/mfe-pricing/` is created.** The Tailwind `content` glob is set to cover BOTH `src/**` (shell) and `apps/**` + `libs/**` (remotes + shared) rather than the idealised `apps/shell/**`.

**Rationale.** Smallest-diff rule. The pilot's purpose is toolchain validation, not a second relocation. The MASTER_PLAN §2.1/§6.3 prose says `apps/shell/` but the as-built SP0 reality is `frontend/src/`. Relocating the shell is a clean later step (a candidate for Sub-plan 7 hardening) that changes no import specifier the remotes care about (remotes resolve the shell only via the federation manifest URL + `@mesell/*` aliases, never via a relative path to `src/` or `apps/shell/`).

**FOUNDER-FLAG.** This is a deviation from MASTER_PLAN §2.1's literal `apps/shell/` topology. It does not change architecture (the shell is still the single host; libs are still shared; the remote is still independently built) — it only defers a cosmetic directory move. The founder should confirm: **accept shell-at-`src/` for the pilot and defer the `apps/shell/` relocation to Sub-plan 7, OR mandate the shell move now.** Recommendation: defer (the relocation is orthogonal to federation correctness and adds risk to the pilot).

### D10 — The remote exposes a single component (`./PricingComponent`), NOT a sub-route tree

**Decision.** `mfe-pricing`'s `federation.config.js` `exposes` block exports exactly one entry: `'./PricingComponent': './apps/mfe-pricing/src/app/pricing.component.ts'`. The shell's route `catalogs/:id/pricing` swaps from `loadComponent` to `loadRemoteModule({ remoteName: 'mfe-pricing', exposedModule: './PricingComponent' })`.

**Rationale.** MASTER_PLAN §2.4 rule of thumb: "shell owns top-level path, remote owns deep sub-routes ONLY when the remote contains a flow." Pricing is a single leaf page with no sub-routes — it exposes a component, not a `Routes` array. (Contrast: `mfe-catalog` in Sub-plan 5 will expose `./CatalogRoutes`.) The `:id` param is read by the remote component from `ActivatedRoute` exactly as today — the shell passes the route param transparently because `loadRemoteModule` mounts the remote component INTO the shell's router outlet, preserving the activated-route context.

**Consequence.** The exposed component keeps its `inject(ActivatedRoute)` / `inject(Router)` usage unchanged. No inputs are passed across the boundary for the pilot (the `:id` flows via the router, not a federation typed-input). This keeps the pilot maximally simple and validates the most common extraction shape (single-component remote) that Sub-plans 02/03(profile)/04 will reuse.

### D11 — `pricing.utils.ts` + `pricing.model.ts` move WITH the component into the remote; they are NOT promoted to `libs/core`

**Decision.** The P&L math (`computePnlBreakdown`, `formatRupee`) and the `PnlBreakdown` type are pricing-private. They move into `apps/mfe-pricing/src/app/` alongside the component. They are NOT extracted into `@mesell/core` because no other remote consumes them (verified: grep for `pricing.utils`/`pricing.model`/`PnlBreakdown` imports outside `features/pricing/` returns zero).

**Rationale.** MASTER_PLAN §6.5 (type sharing) only promotes types that cross the remote boundary. Pricing's math is internal. Promoting it would pollute `@mesell/core` (the federation singleton) with a non-shared concern, increasing the shared-bundle size for every remote. Keep it remote-local.

**Consequence.** `apps/mfe-pricing/` is fully self-contained except for its `@mesell/ui-kit` (MeeBadge/MeeButton/MeeCard/MeeInput) + `@mesell/composites` (PageHeader) imports, which resolve via the shared singleton libs. Confirmed import surface (from the integration branch):
```
@mesell/ui-kit      → MeeBadgeComponent, MeeButtonComponent, MeeCardComponent, MeeInputComponent
@mesell/composites  → PageHeaderComponent
./pricing.utils     → computePnlBreakdown, formatRupee   (moves with component)
./pricing.model     → PnlBreakdown (type)                (moves with component)
@angular/router     → ActivatedRoute, Router             (framework singleton via shareAll)
```

### D12 — Shell route gets a `.catch()` fallback to a `RemoteFailureComponent`; the pilot defines that fallback for all later remotes

**Decision.** The shell route's `loadRemoteModule(...)` is wrapped so a remote-entry 404 / network failure resolves to a shell-owned `RemoteFailureComponent` rendering `<mee-empty-state>` ("Module unavailable, retry in a moment") per MASTER_PLAN §6.4 failure-mode 1. This `RemoteFailureComponent` is authored ONCE in the shell during the pilot and reused by Sub-plans 02–06.

**Rationale.** MASTER_PLAN §6.4 mandates a `.catch(...)` on every `loadRemoteModule`. Building it in the pilot establishes the reusable error-boundary pattern and is itself a toolchain-validation item (§9.A): the pilot must demonstrate that a deliberately-broken manifest URL degrades gracefully, not white-screens.

**Consequence.** NEW shell file `src/app/core/remote-failure.component.ts` (or `libs/core` if later shared — but for the pilot it lives in the shell, since it consumes `@mesell/composites` empty-state and is shell-routing concern). The `app.routes.ts` pricing entry becomes a small helper `loadRemoteWithFallback('mfe-pricing', './PricingComponent')` so Sub-plans 02+ call the same helper.

### D13 — Option-C deploy: `mfe-pricing` ships as a static GCS bundle at `remotes.mesell.xyz`, deployed by `gsutil rsync`, NOT a K3s pod

**Decision.** Per `GATE4_CONFIRMATION.md` C-RES-2 + C-ROUTE-1, the built `mfe-pricing` `remoteEntry.json` + chunks are uploaded to `gs://meesell-frontend/{env}/mfe-pricing/{version}/` and served via Cloud CDN at `https://remotes.mesell.xyz/{env}/mfe-pricing/{version}/remoteEntry.json`. The shell's `public/federation.manifest.json` is patched from `{}` to point at that URL. The remote is NOT an in-cluster Nginx pod (Option A is INFEASIBLE on the current `e2-standard-2` node per C-RES-1).

**Rationale.** GATE4 locked Option C as the only resource-safe hosting model on current hardware (6 remotes off-cluster = 0 in-cluster CPU). The pilot validates the deploy surface (GCS upload + manifest patch + CDN fetch) on a single remote before 5 more follow.

**Consequence.** Infra owns the GCS bucket + Cloud CDN + the `remotes.mesell.xyz` Namecheap A record + GCP-managed cert (C-ROUTE-1) + the `cloudbuild.remote.yaml` GCS-upload pipeline (C-CI-1). This is the cross-lead boundary: **frontend produces the build artefact + the manifest entry; infra hosts it.** A memo (§6) hands the pilot's deploy requirements to infra. For local-dev/CI validation the manifest may point at a localhost-served `remoteEntry.json` so the pilot's federation resolution is provable WITHOUT the GCS surface being live (the shell-loads-remote acceptance test runs against a locally-served remote).

### D14 — CSP is NOT hardened in the pilot; the dev environment runs with the existing (absent) CSP — **FOUNDER-FLAG (deferred to Sub-plan 7)**

**Decision.** Per `GATE4_CONFIRMATION.md` C-CSP-1, no CSP exists today. The pilot does NOT author the production CSP `script-src https://remotes.mesell.xyz` allowlist — that is a joint infra↔frontend Sub-plan-7 deliverable. The pilot validates federation resolution on `dev` where no CSP blocks the cross-origin `remoteEntry.json` fetch.

**Rationale.** C-CSP-1 explicitly says CSP "must be authored and smoke-tested on `dev` BEFORE the first remote is wired" — BUT it also scopes the CSP authoring to Sub-plan 7 (joint deliverable). There is a tension: the pilot wires the first remote, yet CSP is a Sub-plan-7 item. Resolution: because dev has NO CSP today, the cross-origin fetch is not blocked, so the pilot can prove federation resolution on dev without a CSP. The CSP must, however, be authored before the **production** cutover.

**FOUNDER-FLAG.** Confirm the sequencing: **the pilot is permitted to wire the first remote on `dev` (no CSP) for toolchain validation, with CSP authoring formally deferred to Sub-plan 7 BEFORE any staging/prod remote ships.** If the founder requires CSP-first, the pilot blocks on a C-CSP-1 mini-deliverable from infra. Recommendation: permit dev-pilot without CSP (the GATE4 C-CSP-1 "before the first remote is wired" clause is satisfiable as "before the first remote is wired IN STAGING/PROD", since dev has no CSP to violate).

### Founder decisions required (summary)

1. **FOUNDER-FLAG D9** — accept shell-at-`src/` for the pilot, defer `apps/shell/` relocation to Sub-plan 7 (recommended) OR mandate the move now.
2. **FOUNDER-FLAG D14** — permit dev-pilot remote wiring without CSP (recommended), with CSP authoring deferred to Sub-plan 7 before staging/prod.

Both are sequencing/scope calls, not architecture changes. No LOCKED-doc amendment is required by this sub-plan (SP0's FD1 already amended FRONTEND_ARCHITECTURE §2 for the `libs/` boundary).

---

## Agent lineup

| Lead | Specialist dispatched | What the specialist builds |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | Creates `apps/mfe-pricing/` project (angular.json entry + `federation.config.js` `kind:'remote'` exposing `./PricingComponent`); `git mv`s `features/pricing/**` into it; rewrites the `app.routes.ts` pricing entry to `loadRemoteWithFallback`; authors the shell `RemoteFailureComponent` + the `loadRemoteWithFallback` helper; patches `public/federation.manifest.json`; verifies remote builds, shell builds, pricing tests green, route resolves, remote loads in shell. |

Only the Frontend Lead has frontend work. No service-builder (pricing has no service/interceptor/guard surface — it injects only framework primitives). Infra is a cross-lead dependency (D13 deploy surface, §6 memo), NOT a dispatched specialist of this lead.

### Dispatch order (single specialist, serialized phases)

```
PHASE A — scaffold the remote project        meesell-angular-component-builder
   A1. Create apps/mfe-pricing/ project in angular.json (native-federation:build, kind remote)
   A2. git mv features/pricing/** -> apps/mfe-pricing/src/app/ (component+spec+utils+model)
   A3. NEW apps/mfe-pricing/src/app/public-api.ts re-exporting PricingComponent (§6.5 typed boundary)
   A4. federation.config.js for the remote: name 'mfe-pricing', exposes { './PricingComponent': ... }
   A5. Tailwind content glob extended to apps/** ; tsconfig.spec include extended to apps/**/*.spec.ts
   A6. BUILD CHECKPOINT — `ng build mfe-pricing` produces remoteEntry.json ≤... s ; HARD GATE

PHASE B — wire the shell                      meesell-angular-component-builder
   B1. NEW shell RemoteFailureComponent (<mee-empty-state>) + loadRemoteWithFallback() helper
   B2. app.routes.ts: catalogs/:id/pricing -> loadRemoteWithFallback('mfe-pricing','./PricingComponent')
   B3. public/federation.manifest.json: {} -> { "mfe-pricing": "http://localhost:PORT/remoteEntry.json" } (dev)
   B4. FULL VERIFY — shell build ≤90 s ; pricing tests green ; total test count preserved ;
       boundary grep clean ; route resolves ; remote LOADS in shell (served remote + served shell) ;
       deliberate-404 manifest -> RemoteFailureComponent renders (D12 fallback proof)

PHASE C — lead, no specialist                 meesell-frontend-coordinator
   C1. Pilot validation criteria audit (§9.A) — the toolchain-proof checklist SP02+ depend on
   C2. 360/1280 screenshots of /catalogs/:id/pricing (no visual change) + fallback-state screenshot
   C3. Infra deploy memo (D13 GCS/CDN surface) + merge-gate review + integration PR
```

---

## Code surfaces

Exhaustive inventory. Tags: `MOVE` (git mv, history-preserving, no logic change), `MODIFY` (in-place edit), `NEW` (net-new file). Source paths verified on `feature/mf-workspace-foundation/integration` (post-SP0 reality).

### Relocation — `features/pricing/` → `apps/mfe-pricing/src/app/` (4 files + spec)

| # | Source (post-SP0) | Target | Tag | Notes |
|---|---|---|---|---|
| 1 | `frontend/src/app/features/pricing/pricing/pricing.component.ts` | `frontend/apps/mfe-pricing/src/app/pricing.component.ts` | MOVE | The exposed component. `@mesell/ui-kit` + `@mesell/composites` imports UNCHANGED (resolve via shared libs). `./pricing.utils` + `./pricing.model` relative imports stay relative (they move alongside). |
| 2 | `frontend/src/app/features/pricing/pricing/pricing.utils.ts` | `frontend/apps/mfe-pricing/src/app/pricing.utils.ts` | MOVE | `computePnlBreakdown`, `formatRupee` — remote-private (D11). |
| 3 | `frontend/src/app/features/pricing/pricing/pricing.model.ts` | `frontend/apps/mfe-pricing/src/app/pricing.model.ts` | MOVE | `PnlBreakdown` type — remote-private (D11). |
| 4 | `frontend/src/app/features/pricing/pricing/pricing.component.spec.ts` | `frontend/apps/mfe-pricing/src/app/pricing.component.spec.ts` | MOVE | Moves with component; MUST stay discovered (R-SP1-3). |

After the move, `frontend/src/app/features/pricing/` is empty and removed.

### Federation scaffolding — `apps/mfe-pricing/` (NEW)

| # | Path | Tag | Description |
|---|---|---|---|
| 5 | `frontend/apps/mfe-pricing/src/app/public-api.ts` | NEW | Re-exports `PricingComponent` for the typed boundary (MASTER_PLAN §6.5). The federation `exposes` points here or at the component directly; `public-api.ts` keeps the public surface explicit. |
| 6 | `frontend/apps/mfe-pricing/federation.config.js` | NEW | `withNativeFederation({ name: 'mfe-pricing', exposes: { './PricingComponent': './apps/mfe-pricing/src/app/pricing.component.ts' }, shared: shareAll({singleton:true,strictVersion:false,requiredVersion:'auto'}) })`. Shares `@angular/*`, `rxjs`, `@mesell/*` as singletons so the remote consumes the shell's instances. |
| 7 | `frontend/apps/mfe-pricing/src/main.ts` | NEW | Remote bootstrap — `bootstrapApplication(PricingComponent, { providers: [provideRouter([])] })` for standalone dev-serve of the remote; in federation it is mounted by the host, so this is the dev-serve entry only. |
| 8 | `frontend/apps/mfe-pricing/tsconfig.app.json` (+ `tsconfig.spec.json` if the project needs its own) | NEW | Extends the workspace base; references `@mesell/*` paths. |

### Shell wiring (MODIFY + NEW)

| # | Path | Tag | Description |
|---|---|---|---|
| 9 | `frontend/src/app/app.routes.ts` | MODIFY | `catalogs/:id/pricing` entry: `loadComponent: () => import('./features/pricing/...')` → `...loadRemoteWithFallback('mfe-pricing', './PricingComponent')`. ALL other routes UNCHANGED. |
| 10 | `frontend/src/app/core/remote-failure.component.ts` | NEW | `RemoteFailureComponent` — renders `<mee-empty-state>` ("Module unavailable, retry in a moment", retry button reloads). Reused by SP02–06 (D12). |
| 11 | `frontend/src/app/core/load-remote.ts` | NEW | `loadRemoteWithFallback(remoteName, exposedModule)` helper wrapping `loadRemoteModule(...).catch(() => RemoteFailureComponent)` (MASTER_PLAN §6.4). The single reusable extraction primitive. |
| 12 | `frontend/public/federation.manifest.json` | MODIFY | `{}` → `{ "mfe-pricing": "<remoteEntry.json URL>" }`. Dev: localhost-served. Prod: `https://remotes.mesell.xyz/{env}/mfe-pricing/{version}/remoteEntry.json` (D13). |
| 13 | `frontend/angular.json` | MODIFY | Add `projects.mfe-pricing` (build target `@angular-architects/native-federation:build`, serve target for dev). Shell project UNCHANGED except — none. |
| 14 | `frontend/tsconfig.spec.json` (or `angular.json` shell test `include`) | MODIFY | Extend test discovery to `apps/**/*.spec.ts` (R-SP1-3 — the SP0 `../libs/**` discovery gotcha recurs per project; see memory). |
| 15 | `frontend/postcss.config.mjs` / Tailwind `content` | MODIFY | Extend `content` to include `apps/**/*.{html,ts}` (MASTER_PLAN §6.3, Risk R3 purge guard). SP0 already added `libs/**`; this adds `apps/**`. |

### Documentation / status / memory

| # | Path | Tag | Description |
|---|---|---|---|
| 16 | `docs/status/feature_board_frontend.md` | MODIFY | `mfe-pricing` row lifecycle (IN PROGRESS → IN REVIEW → MERGED) + infra inter-lead row (D13 deploy). |
| 17 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log chunk — pilot build/test numbers, the validated toolchain recipe. |
| 18 | `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md` | NEW | The validated-toolchain recipe for SP02+ (the pilot's forward contract). |

No backend/AI/data/OpenAPI/prompt-registry surface. No LOCKED-doc amendment (SP0 FD1 covered the `libs/` boundary).

### Illustrative `federation.config.js` (remote) shape

```js
// frontend/apps/mfe-pricing/federation.config.js
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

module.exports = withNativeFederation({
  name: 'mfe-pricing',
  exposes: {
    './PricingComponent': './apps/mfe-pricing/src/app/pricing.component.ts',
  },
  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
    // @mesell/core, @mesell/ui-kit, @mesell/composites resolve to the shell's instances.
    // @mesell/core declared singleton:true so AuthService (NOT used by pricing, but the
    // contract is uniform) is never duplicated.
  },
  skip: ['rxjs/ajax', 'rxjs/fetch', 'rxjs/testing', 'rxjs/webSocket'],
  features: { ignoreUnusedDeps: true },
});
```

### Illustrative shell `load-remote.ts` helper

```ts
// frontend/src/app/core/load-remote.ts
import { loadRemoteModule } from '@angular-architects/native-federation';
import { RemoteFailureComponent } from './remote-failure.component';

export function loadRemoteWithFallback(remoteName: string, exposedModule: string) {
  return () =>
    loadRemoteModule({ remoteName, exposedModule })
      .then(m => m[Object.keys(m)[0]])          // the exposed default/named component
      .catch(() => RemoteFailureComponent);      // MASTER_PLAN §6.4 failure-mode 1
}
```

---

## Documentation deliverables

Gate conditions in §9. The pilot PR cannot merge to integration without:

1. **`SUB_PLAN_01_pricing_pilot.md`** (this document) — referenced from MASTER_PLAN §5 row 1.
2. **The validated-toolchain recipe** appended to `sub_plan_01_pricing.md` memo — the exact `angular.json` remote-project shape, `federation.config.js` tokens, the manifest URL pattern, the test-discovery `include` fix, and the measured build seconds. This is THE artefact Sub-plans 02–06 copy.
3. **Infra deploy memo** (`handoff_mf_pricing_deploy.md`) — hands the GCS bucket + Cloud CDN + `remotes.mesell.xyz` + `cloudbuild.remote.yaml` requirements (D13, C-CI-1, C-ROUTE-1) to `meesell-infra-builder`.
4. **`feature_board_frontend.md` + `STATUS_FRONTEND.md`** kept current through the lifecycle.
5. **No MASTER_PLAN edit required** beyond a §5 row-1 status note (DRAFT → IN PROGRESS → DONE) recorded in the §11 revision history.

---

## Branch setup

Per repo-management §1.2 as amended F1 (integration branch = `feature/{name}/integration`). The feature slug is `mfe-pricing` (the remote name, not `mf-pricing`).

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-pricing/integration` | `develop` (AFTER SP0's PR#41 merges) | Integration branch for the pilot; merge commits + §6.5 status-only board flips only | Frontend Lead (merge approval) |
| `feature/mfe-pricing/frontend` | `feature/mfe-pricing/integration` | ALL pilot extraction + federation-wiring work | `meesell-angular-component-builder` |

No infra group branch is cut by THIS sub-plan: the infra deploy work (GCS/CDN/cloudbuild) is owned by `meesell-infra-builder` as a parallel infra effort triggered by the §6 memo (C-CI-1 lands when the first remote needs hosting — i.e. NOW, at the pilot). Whether infra cuts `feature/mfe-pricing/infra` is the infra lead's call per repo-management §1.2 ("a group only gets a branch if it has work"). The pilot's FRONTEND merge does not block on infra: dev-validation uses a localhost-served remote (D13), so the federation resolution is provable before the GCS surface is live.

### F1 branch-setup commands (EXECUTION stage — NOT run in this authoring session)

```bash
git fetch origin develop
git checkout develop && git pull --ff-only          # must include SP0's PR#41 merge

git checkout -b feature/mfe-pricing/integration develop
git push -u origin feature/mfe-pricing/integration

git checkout -b feature/mfe-pricing/frontend feature/mfe-pricing/integration
git push -u origin feature/mfe-pricing/frontend

git worktree add /tmp/mesell-wt/mfe-pricing feature/mfe-pricing/frontend
```

### PR flow

```
feature/mfe-pricing/frontend
        │  PR — Frontend Lead reviews+merges (squash)   [repo-mgmt §2.1 / D1]
        ▼
feature/mfe-pricing/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [repo-mgmt §2.2 / D1]
        ▼
develop  (deploys shell to dev namespace; remote to GCS dev bucket via infra)
```

Group → integration: **Frontend Lead** reviewer. Integration → develop: **Founder** reviewer (the lead must NOT approve this gate). Branch protection F3 profile on the integration branch (PR-only, review-count 0, force-push off, delete off) — re-probe empirically (PILOT_REPORT learning 4).

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (own memory — esp. the SP0 session entry: `@mesell/*` aliases, the `../libs/**` test-discovery gotcha, the pnpm-worktree native-build fix `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract`, the deep-import bundle landmine)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md` (the as-merged SP0 contract — alias map, federation init shape, SP1 preconditions)
- `.claude/agent-memory/meesell-frontend-coordinator/module_federation_master_plan_2026_06_10.md`
- `docs/plans/module_federation/SUB_PLAN_00_workspace_foundation.md` (the executed baseline)
- `docs/plans/module_federation/MASTER_PLAN.md` §2.4 (routing), §4.2 (pilot ordering), §6.1 (auth singleton — uniform contract even though pricing skips it), §6.4 (error boundary)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (GATE4 conditions C-RES-1/2, C-ROUTE-1, C-CI-1, C-CSP-1; Option-C deploy)

### Cross-feature memos

- **Outgoing → infra:** `handoff_mf_pricing_deploy.md` — GCS bucket + Cloud CDN + `remotes.mesell.xyz` A record + GCP cert (C-ROUTE-1) + `cloudbuild.remote.yaml` upload pipeline (C-CI-1). 48h SLA. Board inter-lead row added (outgoing); infra adds its own incoming row to its own board.
- **Forward-reference:** `sub_plan_01_pricing.md` — the validated-toolchain recipe (the pilot's gift to SP02+).

### Session-close memory entries

Each agent appends at coding-session close: session header (`## Session mesell-mfe-pricing-frontend-session-{N}`), D8–D14 outcomes (esp. the two FOUNDER-FLAG resolutions), files-touched count, the measured remote build + shell build seconds, test pass count (must equal the SP0 baseline), boundary-grep result, the deliberate-404 fallback proof, blockers, next-step (Sub-plan 2 export readiness).

---

## Dispatch templates

One `### h3` per specialist. Paste-able for the EXECUTION session (runs after PR#41 + founder approval of this sub-plan + the two FOUNDER-FLAGs resolved).

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-pricing-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_01_pricing_pilot.md (this plan — D8-D14, §3 code surfaces, §9 incl. §9.A pilot validation)
- docs/plans/module_federation/SUB_PLAN_00_workspace_foundation.md (the executed baseline — the @mesell/* alias map + federation init shape)
- docs/plans/module_federation/MASTER_PLAN.md §2.4 (routing), §6.4 (error boundary)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (SP0 session: ../libs/** test-discovery gotcha; pnpm rebuild fix; deep-import bundle landmine)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md

## Your mission
PHASE A: (1) Add an `mfe-pricing` project to frontend/angular.json built by @angular-architects/native-federation:build (kind remote). (2) `git mv` features/pricing/pricing/{pricing.component.ts,pricing.utils.ts,pricing.model.ts,pricing.component.spec.ts} -> apps/mfe-pricing/src/app/ (preserve history; @mesell/* imports UNCHANGED; ./pricing.utils + ./pricing.model stay relative). (3) NEW apps/mfe-pricing/src/app/public-api.ts re-exporting PricingComponent. (4) NEW apps/mfe-pricing/federation.config.js name 'mfe-pricing' exposing { './PricingComponent': './apps/mfe-pricing/src/app/pricing.component.ts' } + shareAll singletons. (5) NEW apps/mfe-pricing/src/main.ts dev-serve bootstrap. (6) Extend Tailwind content to apps/** ; extend test-discovery include to apps/**/*.spec.ts. BUILD CHECKPOINT: `ng build mfe-pricing` produces a remoteEntry.json — record seconds. HARD GATE.
PHASE B: (1) NEW shell src/app/core/remote-failure.component.ts (<mee-empty-state> "Module unavailable, retry in a moment") + src/app/core/load-remote.ts loadRemoteWithFallback(). (2) app.routes.ts: catalogs/:id/pricing -> loadRemoteWithFallback('mfe-pricing','./PricingComponent'). ALL other routes UNCHANGED. (3) public/federation.manifest.json: {} -> { "mfe-pricing": "<localhost remoteEntry.json url for dev>" }. (4) FULL VERIFY (see acceptance).

## Acceptance criteria
- [ ] apps/mfe-pricing/ holds the 4 moved files + public-api + federation.config + main.ts; old features/pricing/ removed
- [ ] `ng build mfe-pricing` GREEN, produces remoteEntry.json (record seconds)
- [ ] shell `pnpm build` (ng build) GREEN ≤ 90 s (record seconds; initial bundle delta noted)
- [ ] `pnpm test` total spec/assertion count == SP0 baseline (40 files / 401 tests) — a DROP means pricing spec stopped being discovered = HARD REJECT
- [ ] boundary grep: `grep -rn "from 'primeng" frontend/src frontend/apps frontend/libs | grep -v 'libs/ui-kit/'` returns ONLY the SP0-enumerated carve-outs — NO new leak
- [ ] route /catalogs/:id/pricing resolves; serve shell + serve remote -> PricingComponent RENDERS in shell outlet, :id param read correctly
- [ ] deliberate-broken manifest URL -> RemoteFailureComponent renders (NOT a white screen) — D12 fallback proof
- [ ] `grep -rn loadRemoteModule frontend/src` shows EXACTLY the pricing wiring (the first loadRemoteModule in the codebase)

## Hard constraints
- ZERO logic/template edits to pricing.component/utils/model — relocation only (compute output identical)
- Do NOT promote pricing.utils/model to libs/core (D11 — remote-private)
- Do NOT move the shell into apps/shell/ (D9 — shell stays at src/ for the pilot)
- Do NOT author CSP (D14 — Sub-plan 7)
- Do NOT touch backend/, k8s/, infra/, OR any other feature

## Files you MAY touch
- frontend/apps/mfe-pricing/** (new), frontend/angular.json (add mfe-pricing project), frontend/tsconfig.spec.json (include), frontend/postcss.config.mjs (Tailwind content)
- frontend/src/app/app.routes.ts (pricing entry only), frontend/src/app/core/remote-failure.component.ts (new), frontend/src/app/core/load-remote.ts (new), frontend/public/federation.manifest.json

## Files you must NOT touch
- Any other feature; libs/** (consumed, not edited); federation.config.js of the SHELL (only the remote's is new); backend/k8s/infra

## Final report format
Files moved (count), files new (count), remote build seconds, shell build seconds + initial bundle delta, test pass count (must equal SP0 baseline), boundary-grep output, route-resolution + remote-loads-in-shell proof, fallback proof. Then STOP for lead review + PR.
```

---

## Review + iteration protocol

### meesell-angular-component-builder

- **Pre-approval checklist (lead inspects):** (a) `git log --follow` on the 4 moved files shows preserved history; (b) `pricing.component.ts` diff is empty except path context — NO compute/template change (D11 no-logic rule); (c) `apps/mfe-pricing/federation.config.js` has `name:'mfe-pricing'` + exactly one `exposes` entry; (d) the shell `federation.config.js` is UNCHANGED (still `name:'shell'`, remotes resolved via manifest not config); (e) `public/federation.manifest.json` has exactly one entry; (f) the deliberate-404 fallback was demonstrated (screenshot/log); (g) test count == SP0 baseline (a drop = spec-discovery regression, hard reject — R-SP1-3); (h) shell build ≤90 s recorded; (i) `grep -rn loadRemoteModule frontend/src` shows ONLY pricing.
- **PR-template gate:** `.github/PULL_REQUEST_TEMPLATE/frontend.md` filled completely, no `<>` placeholders. Build evidence (remote + shell seconds), bundle delta, 360/1280 screenshots of the pricing page (no visual change) + a fallback-state screenshot, a11y confirmed, boundary-grep output, the remote-loads-in-shell proof.
- **Re-dispatch triggers:** "edited pricing compute/template" → re-dispatch quoting D11; "moved the shell into apps/shell/" → re-dispatch quoting D9; "test count dropped" → re-dispatch with the failing count + the `apps/**/*.spec.ts` include fix; "no fallback / white-screen on bad manifest" → re-dispatch quoting D12 + §6.4; "authored CSP" → re-dispatch quoting D14; "promoted utils/model to libs/core" → re-dispatch quoting D11; "shell federation.config.js mutated" → re-dispatch (remotes go in the manifest, not the host config).
- **Re-dispatch prompt shape:** original prompt + "Previous run failed on X (paste grep/test/build output); fix only that; re-run build + test + boundary-grep + remote-loads proof."
- **Iteration cap: 3.** Third re-dispatch auto-escalates to founder.

---

## Acceptance gate

When every box is `[x]`, `feature/mfe-pricing/integration` is ready for the founder's develop PR.

- [ ] Phase A + B PR (`feature/mfe-pricing/frontend` → integration) merged by Frontend Lead (squash)
- [ ] `ng build mfe-pricing` GREEN — produces `remoteEntry.json` + chunks (record seconds)
- [ ] Shell `pnpm build` GREEN and **≤ 90 s** (CLAUDE.md Decision 12 / Stop Condition) — seconds + initial bundle delta recorded in PR + STATUS
- [ ] `pnpm test` total == **SP0 baseline (40 spec files / 401 tests), 0 failing, 0 skipped** — any new failure OR a count DROP blocks merge (R-SP1-3)
- [ ] **Boundary grep clean:** PrimeNG imports appear ONLY under `libs/ui-kit/` + the SP0-enumerated carve-outs. No new leak from `apps/mfe-pricing/`.
- [ ] **Route resolves:** `/catalogs/:id/pricing` activates; the remote `PricingComponent` renders in the shell outlet; the `:id` route param is read correctly inside the remote
- [ ] **Remote loads in shell:** with the shell served + the remote served (localhost), navigating to the pricing route fetches `remoteEntry.json` and mounts the remote component — proven, not assumed
- [ ] **Fallback proven (D12):** a deliberately-broken manifest URL degrades to `RemoteFailureComponent` (`<mee-empty-state>`), NOT a white screen (MASTER_PLAN §6.4 failure-mode 1)
- [ ] `grep -rn loadRemoteModule frontend/src` shows EXACTLY the pricing wiring (the codebase's first `loadRemoteModule`)
- [ ] FOUNDER-FLAG D9 (shell stays at `src/`) + D14 (dev-pilot without CSP) resolved by founder
- [ ] Infra deploy memo filed (D13 — GCS/CDN/`remotes.mesell.xyz`/`cloudbuild.remote.yaml`); board inter-lead row added
- [ ] `feature_board_frontend.md` row = MERGED; STATUS_FRONTEND.md Updates Log appended; `sub_plan_01_pricing.md` recipe memo written
- [ ] **§9.A Pilot validation criteria ALL green** (below) — the toolchain is PROVEN before Sub-plan 2 starts
- [ ] **Founder approval** on `feature/mfe-pricing/integration` → `develop` (founder's gate, NOT the lead's)

### §9.A — Pilot validation criteria (what MUST be PROVEN before Sub-plan 02 starts)

The pilot's special mandate (MASTER_PLAN §4.2: "validate the federation toolchain on a low-risk surface"). Sub-plans 02–06 do NOT start until every item here is demonstrated and recorded in `sub_plan_01_pricing.md`. These are the reusable recipe + the go/no-go for the whole migration.

1. **Remote builds independently.** `ng build mfe-pricing` produces a valid `remoteEntry.json` without rebuilding the shell. (Proves the N+1-project workspace, MASTER_PLAN §4.3.)
2. **Shell builds with esbuild preserved.** Shell build stays on `@angular/build:application` (Native Federation wraps, does not replace) and ≤90 s. (Proves R4 build-budget headroom holds with a real remote, not just the empty SP0 init.)
3. **Cross-boundary singleton resolution works.** Even though pricing skips AuthService, the shared `@mesell/ui-kit` + `@mesell/composites` resolve to the shell's single instances at runtime (no duplicate PrimeNG/component bundle in the remote chunk — inspect the remote build output). (Proves the §6.1 singleton mechanism for SP03's AuthService.)
4. **Route swap + param passing.** `loadRemoteModule` mounts the remote into the shell outlet AND the `:id` activated-route param reaches the remote component. (Proves the §2.4 routing strategy.)
5. **Error boundary degrades gracefully.** Broken manifest → `RemoteFailureComponent`, not a white screen. (Proves §6.4 — the reusable fallback for SP02–06.)
6. **Test discovery survives the new project.** The relocated spec runs under the new `apps/**/*.spec.ts` glob; total count unchanged. (Proves the per-project test-discovery fix recipe — the single most-recurring gotcha, SP0 R6.)
7. **Tailwind purge holds.** The pricing page renders with no purged utility (360/1280 screenshots = no visual change). (Proves §6.3 single-build + `apps/**` content glob.)
8. **Deploy surface validated (or explicitly deferred).** The GCS/CDN upload + manifest-patch path is documented (D13) and either smoke-tested on dev or formally handed to infra with a localhost-validated fallback. (Proves Option-C, C-RES-2/C-ROUTE-1.)

If ANY of 1–7 fails, the pilot does NOT merge and the toolchain choice (Native Federation) is re-evaluated with the founder BEFORE any further extraction — this is the strangler-fig reversibility guarantee (MASTER_PLAN §4.1).

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SP1-1 | **`loadRemoteModule` returns the wrong export shape** — the helper's `m[Object.keys(m)[0]]` picks the wrong symbol if `public-api.ts` re-exports more than the component. | Medium | Medium | `public-api.ts` re-exports ONLY `PricingComponent`; the `exposes` key maps directly to the component file. Prefer the explicit `m.PricingComponent` over index-0 once the export name is confirmed at build. The remote-loads-in-shell test catches a wrong shape immediately. |
| R-SP1-2 | **Build-budget regression** — a real remote (vs SP0's empty init) pushes the shell build past 90 s. | Low | High | §9.A item 2 measures it. Stop Condition: shell build >90 s → HALT, do not merge, escalate (CLAUDE.md D12). SP0 baseline 2.9 s leaves large headroom; one small remote adds a manifest fetch, not bundle weight (the remote chunk is separate). |
| R-SP1-3 | **Spec-discovery regression** — moving `pricing.component.spec.ts` into `apps/mfe-pricing/` breaks the `@angular/build:unit-test` glob (cwd = sourceRoot, NOT workspace root — the SP0 gotcha recurs per project). Test silently stops running; "green" is false. | High | High | Extend the test target `include` to `apps/**/*.spec.ts` (mirroring SP0's `../libs/**` fix — see MEMORY.md). Assert the EXACT total count == SP0 baseline; a drop is a hard reject. This is the single most likely failure and the §9.A item-6 recipe for every later extraction. |
| R-SP1-4 | **CSP blocks the cross-origin `remoteEntry.json` fetch in a non-dev env.** | Low (dev) / High (prod) | High | D14 + C-CSP-1: dev has NO CSP, so the pilot validates on dev. CSP authoring is deferred to Sub-plan 7 BEFORE staging/prod. FOUNDER-FLAG D14 confirms the sequencing. Do NOT ship the remote to staging/prod until CSP is authored + smoke-tested. |
| R-SP1-5 | **Manifest URL drift between dev (localhost) and prod (`remotes.mesell.xyz`).** | Medium | Medium | The manifest is per-environment (GATE4 recommends per-env GCS buckets). Dev manifest points at localhost or the dev CDN bucket; prod at `remotes.mesell.xyz/prod/...`. Infra owns the per-env manifest templating (C-CI-1). The pilot documents the URL pattern in `sub_plan_01_pricing.md` so it is not re-invented per remote. |
| R-SP1-6 | **Pilot proves the toolchain on a too-simple surface** — pricing has no AuthService, so the §6.1 singleton-across-boundary mechanism is NOT exercised until SP03 (onboarding/profile). A latent singleton bug ships undetected through SP01/SP02. | Medium | High | §9.A item 3 inspects the remote build output to confirm `@mesell/*` are NOT duplicated into the remote chunk (the singleton mechanism's static proof, even without AuthService runtime use). SP03 carries the FULL runtime AuthService cross-boundary test (login in shell → profile remote sees `currentUser()` → logout propagates). The pilot proves the plumbing; SP03 proves the auth semantics. This is why SP03 (not SP01) finalises the AuthService singleton contract (MASTER_PLAN §5 row 3 dependency). |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-2` (night-run master-session dispatch) | Initial authoring of Sub-Plan 01 — `mfe-pricing` pilot. Grounded in the POST-SP0 integration-branch reality (`e51761b`): pricing is 4 self-contained files (component+spec+utils+model) consuming only `@mesell/ui-kit`+`@mesell/composites`, NO AuthService. D8–D14 (remote project shape; shell-stays-at-src FOUNDER-FLAG D9; single-component expose D10; remote-private utils D11; reusable fallback D12; Option-C GCS deploy D13; CSP-deferred FOUNDER-FLAG D14). §9.A pilot-validation criteria (8 items) = the toolchain-proof gate SP02–06 depend on. 6 risks incl. spec-discovery regression (R-SP1-3, the recurring SP0 gotcha) + the too-simple-pilot singleton-blindness (R-SP1-6, handed to SP03). Two FOUNDER-FLAGs (D9, D14). Awaits founder approval to EXECUTE; gated on SP0 PR#41 merge + infra C-CI-1. |
