# Sub-Plan 03 — `mfe-onboarding` Extraction (F5 onboarding + F13 profile)

**STATUS: DRAFT 2026-06-10 — authored under master-session night-run dispatch (S3, session `mesell-module-federation-frontend-session-2`). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan (planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10) §4.2 ordering "3rd" + §5 row 3 |
| Predecessors | SP00 (EXECUTED) + SP01 pilot (toolchain PROVEN, §9.A) + SP02 export (job-polling pattern proven) |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order |
| Author | meesell-frontend-coordinator (Frontend Lead) |
| Feature slug | `mfe-onboarding` |
| Remote ID | R2 (MASTER_PLAN §2.2) |
| Owned features | F5 onboarding · F13 profile |
| Owned routes | `/onboarding`, `/profile` |
| Complexity | **M** (TWO pages; FIRST real AuthService-across-the-boundary; a shell-layout dependency to break) |
| Scope | Extract `features/account/onboarding/` + `features/profile/` into a standalone remote exposing TWO components; **finalise the AuthService singleton contract** (MASTER_PLAN §5 row 3 dependency); wire two shell routes to `loadRemoteWithFallback`. Frontend-only. |
| Out of scope | Other remotes; backend; AI; mobile; real-API wiring (Wave 6); CSP cutover (Sub-plan 7) |
| Execution gates | SP01 + SP02 merged + founder approval of THIS sub-plan + infra C-CI-1 ready + the AuthService-singleton smoke test designed (see §9) |

`mfe-onboarding` is the **third extraction** and the **first that uses `AuthService` across the federation boundary** (MASTER_PLAN §4.2: "first real test of shared singleton across the federation boundary"). This is why **§5 row 3 names the AuthService singleton contract as this sub-plan's deliverable** — and why the canonical-pattern §1 Decisions section below carries the full singleton specification (D22). The pilot (SP01) proved the federation plumbing; SP02 proved lifecycle/polling; **SP03 proves the auth semantics** — log in via the shell, navigate to the remote `ProfileComponent`, see the same `currentUser()`, and have a `logout()` from the remote clear the shell's token. If this fails, the whole 6-remote migration's auth story is in doubt — so SP03's acceptance gate is the migration's auth go/no-go.

Two real complications surfaced from the post-SP0 integration-branch reality (verified):
- **`profile.component.ts` consumes `AuthService` from `@mesell/core`** — calling `auth.currentUser()` (signal read, used 4×) and `auth.logout()` (1×). These are the exact cross-boundary singleton operations.
- **`onboarding.component.ts` imports `AuthLayoutComponent` via a RELATIVE path** `../../../layouts/auth-layout/auth-layout.component` — a **shell-owned layout**, NOT a `@mesell/*` lib. This relative cross-boundary import CANNOT survive the extraction (the remote has no `../../../layouts/`). It must be resolved (D21).

---

## Decisions

D-numbers append-only and monotonic, continuing from SUB_PLAN_02 (which ended at D19). FOUNDER-FLAG marks founder-level calls.

### Adaptations from the canonical V1-feature pattern

Same structural-extraction shape, but M-complexity: TWO exposed components + the auth-singleton contract + a shell-layout dependency to sever. Lineup is one lead + likely BOTH specialists (component-builder for the two pages; service-builder for the AuthService singleton-registration verification — see §2). §3 adds the `AuthLayoutComponent` resolution surface. §9 carries the auth-singleton smoke test as a NEW first-class gate.

### D20 — The remote exposes TWO components: `./OnboardingComponent` and `./ProfileComponent` (two `exposes` entries, two route swaps)

**Decision.** `mfe-onboarding`'s `federation.config.js` `exposes`:
```
'./OnboardingComponent': './apps/mfe-onboarding/src/app/onboarding.component.ts'
'./ProfileComponent':    './apps/mfe-onboarding/src/app/profile.component.ts'
```
The shell swaps TWO routes: `onboarding` → `loadRemoteWithFallback('mfe-onboarding','./OnboardingComponent')` and `profile` → `loadRemoteWithFallback('mfe-onboarding','./ProfileComponent')`. Both pages live in ONE remote because they share the user/profile schema and field components (MASTER_PLAN §2.2 R2 co-change rationale).

**Rationale.** First multi-expose remote — validates that one remote can expose more than one component (the recipe SP04/SP06 reuse; SP05 goes further with a `Routes` array). Neither onboarding nor profile owns a sub-route tree, so two single-component exposes (not a `./OnboardingRoutes`) is the right shape (MASTER_PLAN §2.4).

**Consequence.** The manifest still gains ONE entry (`mfe-onboarding` → one `remoteEntry.json`); a single remote can expose multiple modules from one entry. Two shell route swaps, one new project, one manifest entry.

### D21 — `onboarding`'s `AuthLayoutComponent` dependency is severed: the remote receives the layout via `@mesell/composites` OR content-projection — NOT a relative `layouts/` import — **FOUNDER-FLAG (layout ownership)**

**Decision.** `onboarding.component.ts` currently imports `AuthLayoutComponent` from `../../../layouts/auth-layout/auth-layout.component` (a shell-owned Layer-3 layout, verified) and wraps its template in `<mee-auth-layout>`. The remote cannot reach `../../../layouts/`. Resolution options, in preference order:

1. **PROMOTE `AuthLayoutComponent` to `@mesell/composites`** (Layer 3 composite) so the remote imports it as `@mesell/composites` (the same way pricing imports `PageHeaderComponent`). This is the cleanest: `AuthLayout` is presentational chrome (logo + centered card), a natural composite. The shell's auth pages (login/signup/otp — SP06) also use it, so promoting it to a shared lib benefits SP06 too.
2. **Content-projection from the shell** — the shell route wraps the remote in `<mee-auth-layout>` via the router outlet. Rejected for the pilot-class simplicity: it couples the shell route config to the remote's visual needs and breaks the "remote owns its page" model.

**Decision: option 1.** Promote `AuthLayoutComponent` → `libs/composites/auth-layout/` as part of SP03 (it is a small, dependency-light presentational component). The relative import in `onboarding.component.ts` becomes `import { AuthLayoutComponent } from '@mesell/composites'`.

**Rationale.** MASTER_PLAN §2.3 makes `@mesell/composites` a shared singleton lib. A layout shared by a remote (onboarding) AND the shell's auth pages (SP06) BELONGS there. Promoting it now (SP03) means SP06 inherits it. This is a `MOVE` (git mv into libs/composites) + a barrel re-export + the import rewrite — small and behaviour-preserving.

**FOUNDER-FLAG.** This promotes a file out of `layouts/` (shell-owned) into `libs/composites` (shared). It touches the shell's layout ownership boundary. The founder confirms: **promote `AuthLayoutComponent` to `@mesell/composites` (recommended — it is shared chrome) OR keep it shell-owned and have the shell wrap the remote via content-projection.** Recommendation: promote (it cleanly serves both the onboarding remote AND the SP06 auth remote, and matches the §2.3 shared-composite model). NOTE: this is a `libs/composites` content change (new file) — it is NOT a FRONTEND_ARCHITECTURE.md LOCKED-doc amendment (the SP0 FD1 amendment already documented `libs/composites` as the Layer-3 home), but the layout's MOVE from `layouts/` should be recorded in the lead memory + the §11 history.

> **RULED 2026-06-11 (founder, morning session): APPROVED as recommended.** `AuthLayoutComponent` promotion to `@mesell/composites` approved — executes at SP03 as planned (option 1, PROMOTE). It serves both the onboarding remote and the SP06 auth remote. No LOCKED-doc amendment required (the SP0 FD1 amendment already documented `libs/composites` as the Layer-3 home); the `layouts/` → `libs/composites` MOVE is recorded in the lead memory + this §11 history.

### D22 — AuthService singleton contract (THE §5-row-3 deliverable) — FULL SPECIFICATION

This is the core of SP03. MASTER_PLAN §6.1 + §2.5 mandate `AuthService` be a federation singleton; SP03 is where that contract is first EXERCISED and therefore where it must be FINALISED. The verified post-SP0 reality:

```ts
// frontend/libs/core/services/auth.service.ts (as-built on the integration branch)
@Injectable({ providedIn: 'root' })           // ← THE drift risk (MASTER_PLAN R1 P0)
export class AuthService {
  private readonly _token = signal<string | null>(null);
  private readonly _user  = signal<AuthUser | null>(null);
  readonly isAuthenticated = computed(() => this._token() !== null);
  readonly currentUser     = computed(() => this._user());      // profile reads this 4×
  setSession(token, user): void { ... }
  logout(): void { ... }                                         // profile calls this 1×
  // getter for bearer token (HTTP interceptor) ...
}
```

The contract, finalised:

**C1 — `AuthService` is declared `singleton: true, strictVersion: false` in EVERY `federation.config.js`** (shell host + every remote). It is already covered by the SP0 `shareAll({ singleton: true, ... })` because it lives in `@mesell/core` (a shared dependency). SP03 VERIFIES `@mesell/core` is in the shared set of the `mfe-onboarding` config (not skipped) so the remote's `inject(AuthService)` resolves to the shell's import-map instance.

**C2 — `providedIn: 'root'` is RETAINED but its risk is mitigated by the shared import-map, NOT by changing it to manual providers.** The MASTER_PLAN R1 mitigation text says "move AuthService to `libs/core` with `@Injectable()` (no `providedIn`); shell registers it in providers." The as-built reality kept `providedIn: 'root'`. SP03's call: **with Native Federation's import-map sharing AND `singleton: true`, `providedIn: 'root'` resolves to a SINGLE module instance across the boundary** — because both shell and remote import the SAME `@mesell/core` module URL from the import map, so `providedIn: 'root'` registers ONE provider in ONE module evaluated ONCE. The drift risk (two parallel instances) only materialises if a remote bundles its OWN copy of `@mesell/core` (i.e. the dependency is NOT shared/singleton). Therefore the mitigation is **enforce singleton sharing + a lint/build assertion that `@mesell/core` is never duplicated into a remote chunk**, NOT a refactor of the `@Injectable` decorator. This is verified empirically by the C5 smoke test + a remote-build-output inspection (no second `auth.service` chunk in the remote).

**C3 — Reactive signals cross the boundary natively.** `currentUser()` and `isAuthenticated()` are `computed()` over signals owned by the shell's single AuthService instance. Because the remote injects that SAME instance, reading `auth.currentUser()` inside the remote `ProfileComponent` returns the shell's live value, and a `logout()` from the remote mutates the shell's signal — the shell's navbar/guard react. No serialization, no BroadcastChannel for in-app sync (§2.5: BroadcastChannel is cross-TAB only).

**C4 — `setSession` is owned by the auth flow (SP06 `mfe-auth`), `logout` may be called from anywhere.** SP03's profile remote calls `auth.logout()` — legitimate (any authenticated page may log out). `setSession` is NOT called by onboarding/profile (verified — profile only reads + logs out). The full write path (`setSession` after OTP) is SP06's concern. SP03 proves the READ + the LOGOUT cross-boundary; SP06 proves the full WRITE (login → token set → all remotes see authenticated).

**C5 — The singleton smoke test (the §9 auth go/no-go), authored in SP03 and reused by SP06:**
```
1. Serve shell + mfe-onboarding remote.
2. In the shell (or via a test harness), call auth.setSession(token, user) — simulate login.
3. Navigate to /profile (remote ProfileComponent).
4. ASSERT: the remote renders auth.currentUser()?.name === user.name (the shell's value crossed the boundary).
5. In the remote, click logout (calls auth.logout()).
6. ASSERT: back in the shell, auth.isAuthenticated() === false AND the authGuard now blocks protected routes.
   (Proves the remote mutated the shell's single instance — no drift.)
7. Inspect the mfe-onboarding remote build output: assert NO duplicate auth.service chunk (C2 static proof).
```

**Decision.** C1–C5 ARE the finalised AuthService singleton contract. They are recorded verbatim in `sub_plan_03_onboarding.md` (memory) and referenced by SP04 (dashboard, authenticated), SP05 (catalog), and SP06 (auth — the writer). SP06 does NOT re-derive the contract; it consumes it and adds only the `setSession` write-path proof.

**Rationale.** §5 row 3's blocking dependency is literally "AuthService singleton contract finalised." Onboarding/profile is the first remote that injects AuthService, so it is the natural and earliest place to finalise + prove it. Finalising it earlier (at the pilot) was impossible — pricing/export don't touch AuthService (SP01 R-SP1-6 explicitly handed the auth semantics to SP03).

### D23 — Onboarding's `optionalGstValidator` + profile's local form logic move WITH their components; NO promotion

**Decision.** The GST validator (`GST_PATTERN` regex + `optionalGstValidator()`, verified in `onboarding.component.ts`) and profile's local form-builder logic move into `apps/mfe-onboarding/src/app/` with their components. Not promoted to `@mesell/core` (single-remote use).

**Rationale.** Same as D11/D17 — promote only cross-boundary code. GST validation is onboarding-private; profile's form logic is profile-private.

**Consequence.** Self-contained remote except `@mesell/ui-kit` (MeeButton/MeeInput/MeeSteps for onboarding; MeeCard/MeeBadge/MeeInput/MeeButton for profile), `@mesell/composites` (the newly-promoted `AuthLayoutComponent` for onboarding), and `@mesell/core` (`AuthService` for profile). Confirmed import surfaces (integration branch):
```
onboarding: @mesell/ui-kit {MeeButton, MeeInput, MeeSteps, type MeeStep},
            @mesell/composites {AuthLayoutComponent (PROMOTED in D21)},
            @angular/router {Router}, local optionalGstValidator
profile:    @mesell/ui-kit/* {MeeCard, MeeBadge, MeeInput, MeeButton, type MeeBadgeSeverity} (deep imports),
            @mesell/core {AuthService},
            @angular/router {Router}, local form logic
```
> Note: profile uses DEEP `@mesell/ui-kit/<subpath>` imports (e.g. `@mesell/ui-kit/card/card.component`), not the barrel — the SP0 deep-import pattern (lean-bundle). These deep aliases resolve in the remote exactly as in the shell (SP0 added `@mesell/ui-kit/*` wildcard alias). Preserve them as-is; do NOT rewrite to the barrel (the barrel-at-root bundle landmine — MEMORY.md).

### D24 — Option-C deploy mirrors SP01/SP02; `mfe-onboarding` is the third remote at `remotes.mesell.xyz`

**Decision.** Per `GATE4_CONFIRMATION.md` C-RES-2 / C-ROUTE-1: built `mfe-onboarding` → `gs://meesell-frontend/{env}/mfe-onboarding/{version}/`, manifest gains a third entry. Same infra surface (bucket/CDN/host/cert/matrix) stood up at the pilot. Dev-validation uses localhost-served remotes.

**Rationale + Consequence.** Identical to D13/D19. Three-remote manifest is the new (minor) surface; the auth-singleton resolution across THIS remote is the real new surface (D22 C5).

### Founder decisions required

1. **FOUNDER-FLAG D21** — promote `AuthLayoutComponent` from `layouts/` (shell) to `@mesell/composites` (shared) — recommended, serves onboarding + SP06 auth — OR keep it shell-owned with content-projection. — **RULED 2026-06-11 (founder, morning session): APPROVED as recommended (PROMOTE; executes at SP03).**
2. **Inherited:** SP01 D9 (shell stays at `src/`) + D14 (dev without CSP, deferred to Sub-plan 7) apply unchanged.

D22 (the AuthService singleton contract) is a LEAD-level technical finalisation, not a founder call — it does not change the locked CLAUDE.md D10 (no NgRx) or the FE-D5 refresh-token model; it specifies HOW the existing `providedIn:'root'` AuthService resolves as a singleton under federation. No LOCKED-doc amendment.

---

## Agent lineup

| Lead | Specialist dispatched | What the specialist builds |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | Creates `apps/mfe-onboarding/` (copy pilot recipe); `git mv`s onboarding + profile components into it; PROMOTES `AuthLayoutComponent` → `libs/composites` + rewrites onboarding's import; wires TWO shell route swaps to the existing `loadRemoteWithFallback`; patches the manifest with a third entry; verifies builds, tests, route resolution, both remotes-load. |
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-service-builder` (sonnet) | VERIFIES the AuthService singleton contract (D22 C1–C5): confirms `@mesell/core` is in the `mfe-onboarding` shared/singleton set; authors the C5 singleton smoke test; inspects the remote build output for a duplicate `auth.service` chunk (C2 static proof). Does NOT change `AuthService` logic. |

Per MASTER_PLAN §5 row 3 the responsible agent is `meesell-angular-component-builder`; SP03 adds `meesell-angular-service-builder` for the auth-singleton verification because the singleton contract is the row-3 deliverable and is a service-layer concern. Dispatch order: component-builder does the extraction; service-builder verifies the singleton on the extracted remote (after component-builder's build is green). Infra is a cross-lead dependency (D24 memo), not a dispatched specialist.

### Dispatch order

```
PHASE A — extract the two pages (component-builder)
   A1. Copy apps/mfe-pricing/ shape -> apps/mfe-onboarding/ (angular.json native-federation:build remote)
   A2. git mv features/account/onboarding/onboarding.component.{ts,spec.ts} -> apps/mfe-onboarding/src/app/
       git mv features/profile/profile.component.{ts,spec.ts} -> apps/mfe-onboarding/src/app/
   A3. PROMOTE layouts/auth-layout/auth-layout.component.* -> libs/composites/auth-layout/ + barrel export (D21)
       rewrite onboarding's ../../../layouts/auth-layout import -> @mesell/composites
       (re-confirm the shell's auth pages still import AuthLayout from @mesell/composites — they will in SP06;
        for NOW the shell login/signup/otp keep their existing relative import UNTIL SP06, OR are rewritten
        to @mesell/composites in this same PR if they currently use the relative path — verify + decide minimal diff)
   A4. NEW apps/mfe-onboarding/src/app/public-api.ts re-exporting BOTH components
   A5. NEW apps/mfe-onboarding/federation.config.js name 'mfe-onboarding' exposing BOTH (D20)
   A6. BUILD CHECKPOINT — `ng build mfe-onboarding` -> remoteEntry.json ; HARD GATE

PHASE B — wire the shell (component-builder)
   B1. app.routes.ts: onboarding -> loadRemoteWithFallback('mfe-onboarding','./OnboardingComponent')
       app.routes.ts: profile   -> loadRemoteWithFallback('mfe-onboarding','./ProfileComponent')
   B2. public/federation.manifest.json: add "mfe-onboarding" (now THREE entries)
   B3. VERIFY — shell build ≤90 s ; tests green/count preserved ; boundary clean ; both routes resolve ;
       both remote components render in shell

PHASE C — AuthService singleton verification (service-builder, AFTER B green)
   C1. Confirm @mesell/core is shared+singleton in mfe-onboarding federation.config.js (C1)
   C2. Author + run the C5 singleton smoke test (setSession in shell -> currentUser() in profile remote ->
       logout in remote -> isAuthenticated() false in shell -> guard blocks)
   C3. Inspect mfe-onboarding build output: assert NO duplicate auth.service chunk (C2 static proof)

PHASE D — lead, no specialist
   D1. Auth go/no-go: the C5 smoke test is the migration's auth gate — if it fails, HALT + escalate
   D2. 360/1280 screenshots of /onboarding + /profile (no visual change)
   D3. Infra deploy memo (D24) + AuthLayout-promotion memo note + merge-gate review + PR
```

---

## Code surfaces

Exhaustive. Tags: `MOVE` / `MODIFY` / `NEW`. Source paths verified on `feature/mf-workspace-foundation/integration`.

### Relocation — onboarding + profile → `apps/mfe-onboarding/src/app/` (4 files incl. specs)

| # | Source (post-SP0) | Target | Tag | Notes |
|---|---|---|---|---|
| 1 | `frontend/src/app/features/account/onboarding/onboarding.component.ts` | `frontend/apps/mfe-onboarding/src/app/onboarding.component.ts` | MOVE | Exposed. `@mesell/ui-kit` UNCHANGED; the `../../../layouts/auth-layout` import REWRITTEN to `@mesell/composites` (D21); local `optionalGstValidator` moves inline (D23). |
| 2 | `frontend/src/app/features/account/onboarding/onboarding.component.spec.ts` | `frontend/apps/mfe-onboarding/src/app/onboarding.component.spec.ts` | MOVE | Must stay discovered (R-SP3-3). |
| 3 | `frontend/src/app/features/profile/profile.component.ts` | `frontend/apps/mfe-onboarding/src/app/profile.component.ts` | MOVE | Exposed. Deep `@mesell/ui-kit/*` imports UNCHANGED; `@mesell/core` AuthService import UNCHANGED (it is the singleton); local form logic moves (D23). |
| 4 | `frontend/src/app/features/profile/profile.component.spec.ts` | `frontend/apps/mfe-onboarding/src/app/profile.component.spec.ts` | MOVE | Must stay discovered. The spec likely mocks/provides AuthService — verify it still resolves `@mesell/core` (R-SP3-5). |

After the move, `frontend/src/app/features/account/onboarding/` + `frontend/src/app/features/profile/` are removed.

### AuthLayout promotion (D21) — `layouts/auth-layout/` → `libs/composites/auth-layout/` (MOVE + barrel)

| # | Source | Target | Tag | Notes |
|---|---|---|---|---|
| 5 | `frontend/src/app/layouts/auth-layout/auth-layout.component.ts` (+ spec if present) | `frontend/libs/composites/auth-layout/auth-layout.component.ts` | MOVE | Promoted to shared composite. Behaviour-preserving. |
| 6 | `frontend/libs/composites/index.ts` | MODIFY | Re-export `AuthLayoutComponent` from the composites barrel. |
| 7 | shell auth pages (`features/auth/login`, `signup`, `otp-verify`) IF they import AuthLayout relatively | MODIFY (conditional) | Rewrite their `AuthLayout` import to `@mesell/composites` — ONLY if they currently use a relative `layouts/` import; minimise diff. (These pages are SP06's remote; for now they stay in the shell and just re-point the import.) |

> Verify before moving: `grep -rn "auth-layout" frontend/src frontend/libs` — enumerate ALL consumers of `AuthLayoutComponent` so none is left with a dangling relative import after the promotion.

### Federation scaffolding — `apps/mfe-onboarding/` (NEW, copies the pilot)

| # | Path | Tag | Description |
|---|---|---|---|
| 8 | `frontend/apps/mfe-onboarding/src/app/public-api.ts` | NEW | Re-exports `OnboardingComponent` + `ProfileComponent` (§6.5 — BOTH, D20). |
| 9 | `frontend/apps/mfe-onboarding/federation.config.js` | NEW | `name: 'mfe-onboarding'`, TWO `exposes` entries (D20), `shareAll` singletons — **`@mesell/core` MUST be in the shared/singleton set, NOT skipped** (D22 C1). |
| 10 | `frontend/apps/mfe-onboarding/src/main.ts` | NEW | Dev-serve bootstrap (router with both routes for standalone dev). |
| 11 | `frontend/apps/mfe-onboarding/tsconfig.app.json` | NEW | Extends base; `@mesell/*` paths incl. `@mesell/core`. |

### Shell wiring (MODIFY — reuse SP01 helper)

| # | Path | Tag | Description |
|---|---|---|---|
| 12 | `frontend/src/app/app.routes.ts` | MODIFY | TWO swaps: `onboarding` + `profile` → `loadRemoteWithFallback('mfe-onboarding', './OnboardingComponent' / './ProfileComponent')`. All other routes UNCHANGED. |
| 13 | `frontend/public/federation.manifest.json` | MODIFY | Add `"mfe-onboarding"` (now THREE entries). |
| 14 | `frontend/angular.json` | MODIFY | Add `projects.mfe-onboarding`. |
| 15 | test-discovery `include` + Tailwind `content` | RE-CONFIRM | `apps/**` globs from SP01 already cover the new project. No edit expected. |

### Documentation / status / memory

| # | Path | Tag | Description |
|---|---|---|---|
| 16 | `docs/status/feature_board_frontend.md` | MODIFY | `mfe-onboarding` row lifecycle + infra inter-lead row (D24). |
| 17 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log — build/test numbers, the AuthService singleton smoke-test result (the auth go/no-go). |
| 18 | `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_03_onboarding.md` | NEW | **The finalised AuthService singleton contract (D22 C1–C5)** — the artefact SP04/SP05/SP06 consume; + the AuthLayout promotion record. |

No backend/AI/data surface. No LOCKED-doc amendment (D21's AuthLayout move is a `libs/composites` content change, recorded in memory + history).

### Illustrative `federation.config.js` (remote) shape

```js
// frontend/apps/mfe-onboarding/federation.config.js
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

module.exports = withNativeFederation({
  name: 'mfe-onboarding',
  exposes: {
    './OnboardingComponent': './apps/mfe-onboarding/src/app/onboarding.component.ts',
    './ProfileComponent':    './apps/mfe-onboarding/src/app/profile.component.ts',
  },
  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
    // @mesell/core (AuthService) MUST resolve to the shell's instance (D22 C1/C2) —
    // shareAll + singleton:true guarantees ONE @mesell/core module in the import map.
  },
  skip: ['rxjs/ajax', 'rxjs/fetch', 'rxjs/testing', 'rxjs/webSocket'],
  features: { ignoreUnusedDeps: true },
});
```

---

## Documentation deliverables

Gate conditions in §9. The PR cannot merge to integration without:

1. **`SUB_PLAN_03_onboarding_extraction.md`** (this document) — referenced from MASTER_PLAN §5 row 3.
2. **`sub_plan_03_onboarding.md` memo carrying the FINALISED AuthService singleton contract (D22 C1–C5)** — the §5-row-3 deliverable. SP04/SP05/SP06 read it; SP06 extends it with the `setSession` write-path proof but does NOT re-derive it.
3. **The C5 singleton smoke test** — authored, run, result recorded (PASS is the migration's auth go/no-go).
4. **Infra deploy memo** (`handoff_mf_onboarding_deploy.md`) — third-remote GCS prefix + matrix fan-out (C-CI-1).
5. **AuthLayout-promotion record** — the `layouts/` → `libs/composites` MOVE noted in memory + §11 history (D21).
6. **`feature_board_frontend.md` + `STATUS_FRONTEND.md`** current through the lifecycle.

---

## Branch setup

Feature slug `mfe-onboarding`. Per F1.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-onboarding/integration` | `develop` (AFTER SP02 merged) | Integration branch | Frontend Lead |
| `feature/mfe-onboarding/frontend` | `feature/mfe-onboarding/integration` | ALL extraction + auth-singleton verification | `meesell-angular-component-builder`, `meesell-angular-service-builder` |

Both specialists work the SAME `feature/mfe-onboarding/frontend` branch sequentially (component-builder extraction first, then service-builder verification) — one frontend group branch per feature (repo-management §1.2), same pattern as SP0 Phase A/B. No infra group branch (parallel C-CI-1 effort).

### F1 branch-setup commands (EXECUTION stage)

```bash
git fetch origin develop
git checkout develop && git pull --ff-only          # must include SP02's merge

git checkout -b feature/mfe-onboarding/integration develop
git push -u origin feature/mfe-onboarding/integration

git checkout -b feature/mfe-onboarding/frontend feature/mfe-onboarding/integration
git push -u origin feature/mfe-onboarding/frontend

git worktree add /tmp/mesell-wt/mfe-onboarding feature/mfe-onboarding/frontend
```

### PR flow

```
feature/mfe-onboarding/frontend
        │  PR — Frontend Lead reviews+merges (squash)   [D1]
        ▼
feature/mfe-onboarding/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [D1]
        ▼
develop
```

Group → integration: Frontend Lead. Integration → develop: Founder (lead must NOT approve). F3 protection; re-probe empirically.

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (own memory — esp. deep-import bundle landmine; the `@mesell/ui-kit/*` wildcard alias profile relies on; the AuthService as-built shape)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md` (the recipe) + `sub_plan_02_export.md` (lifecycle pattern)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md` (alias map — `@mesell/core` is `AuthService`+`authGuard`)
- `docs/plans/module_federation/MASTER_PLAN.md` §2.5 (state sharing), §6.1 (auth token sharing — the contract this sub-plan finalises), §7 R1 (auth singleton drift)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (GATE4 Option-C; C-CI-1)

### Cross-feature memos

- **Outgoing → infra:** `handoff_mf_onboarding_deploy.md` — third-remote GCS prefix + matrix fan-out (C-CI-1). 48h SLA. Board row added.
- **Forward-reference (CRITICAL):** `sub_plan_03_onboarding.md` — the FINALISED AuthService singleton contract (D22 C1–C5) + the AuthLayout promotion. This is the artefact SP04 (authenticated dashboard), SP05 (catalog), and SP06 (auth — the token writer) depend on. SP06's blocking dependency ("AuthService singleton + refresh-token flow proven across ≥3 remotes") starts being satisfied HERE.

### Session-close memory entries

Session header (`## Session mesell-mfe-onboarding-frontend-session-{N}`), D20–D24 outcomes (esp. the D21 FOUNDER-FLAG resolution + the full D22 contract + the C5 smoke-test PASS/FAIL), files-touched count, the AuthLayout promotion, remote + shell build seconds, test pass count, boundary result, the auth go/no-go verdict, blockers, next-step (Sub-plan 4 dashboard).

---

## Dispatch templates

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-onboarding-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_03_onboarding_extraction.md (this plan — D20-D24, esp. D21 AuthLayout + D22 AuthService contract, §3, §9)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md (THE recipe) + sub_plan_02_export.md
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (deep-import bundle landmine; @mesell/ui-kit/* wildcard; AuthService shape)
- docs/plans/module_federation/MASTER_PLAN.md §2.4 (routing), §2.5 (state sharing), §6.1 (auth token sharing)

## Your mission
PHASE A: Copy apps/mfe-pricing/ shape -> apps/mfe-onboarding/. `git mv` features/account/onboarding/onboarding.component.{ts,spec.ts} + features/profile/profile.component.{ts,spec.ts} -> apps/mfe-onboarding/src/app/. PROMOTE layouts/auth-layout/auth-layout.component.* -> libs/composites/auth-layout/ + add to the composites barrel; rewrite onboarding's `../../../layouts/auth-layout` import -> `@mesell/composites`; enumerate ALL AuthLayout consumers first (`grep -rn auth-layout frontend/src frontend/libs`) and re-point any relative ones to @mesell/composites (minimal diff — the shell auth pages stay in the shell for now, just re-import). KEEP profile's deep @mesell/ui-kit/* imports + its @mesell/core AuthService import UNCHANGED. NEW public-api.ts re-exporting BOTH components. NEW federation.config.js name 'mfe-onboarding' exposing BOTH ('./OnboardingComponent','./ProfileComponent') with @mesell/core in the shared/singleton set (NOT skipped). BUILD CHECKPOINT: `ng build mfe-onboarding`. HARD GATE.
PHASE B: app.routes.ts -> swap onboarding + profile to loadRemoteWithFallback('mfe-onboarding', './OnboardingComponent' / './ProfileComponent') (reuse the SP01 helper). manifest: add "mfe-onboarding" (THREE entries). VERIFY: shell build ≤90 s; tests green/count preserved; boundary clean; BOTH routes resolve + both remote components render in shell.

## Acceptance criteria
- [ ] apps/mfe-onboarding/ holds onboarding + profile (+ specs) + public-api + federation.config + main.ts; old features removed
- [ ] AuthLayoutComponent promoted to libs/composites + barrel exports it; onboarding imports it from @mesell/composites; NO dangling relative auth-layout import anywhere
- [ ] profile's @mesell/core AuthService import + deep @mesell/ui-kit/* imports UNCHANGED
- [ ] federation.config.js exposes BOTH; @mesell/core is shared+singleton (NOT skipped)
- [ ] `ng build mfe-onboarding` GREEN -> remoteEntry.json (record seconds)
- [ ] shell `pnpm build` GREEN ≤ 90 s (seconds + bundle delta)
- [ ] `pnpm test` total == prior baseline, 0 failing/skipped (drop = spec not discovered = HARD REJECT)
- [ ] boundary clean; both /onboarding + /profile resolve + render the remote components; manifest has THREE entries

## Hard constraints
- ZERO logic/template edits to onboarding/profile (incl. optionalGstValidator) — relocation + import rewrites only
- Do NOT change AuthService logic or its @Injectable decorator (D22 C2 — the singleton resolves via import-map sharing, not a refactor)
- Do NOT promote optionalGstValidator/profile-form-logic to libs/core (D23)
- Do NOT author a new fallback/helper (reuse SP01); do NOT move the shell into apps/shell/ (D9); do NOT author CSP (D14)
- Do NOT touch backend/, k8s/, infra/, OR other remotes/features

## Files you MAY touch
- frontend/apps/mfe-onboarding/** (new), frontend/libs/composites/auth-layout/** (promoted) + libs/composites/index.ts (barrel)
- frontend/angular.json (add project), frontend/public/federation.manifest.json, frontend/src/app/app.routes.ts (2 entries)
- shell auth pages' AuthLayout import line ONLY (if relative -> @mesell/composites)

## Files you must NOT touch
- frontend/apps/mfe-pricing/**, apps/mfe-export/** (done); src/app/core/{remote-failure,load-remote} (reuse); libs/core/services/auth.service.ts logic; backend/k8s/infra

## Final report format
Files moved/new counts, AuthLayout promotion confirmation + all consumers re-pointed, remote build seconds, shell build seconds + bundle delta, test count, boundary output, both-routes-resolve + both-remotes-render proof. Then STOP for lead review (service-builder runs the auth-singleton verification next).
```

### meesell-angular-service-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-onboarding-frontend-session-2

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_03_onboarding_extraction.md (this plan — D22 C1-C5 AuthService singleton contract, §9 auth go/no-go)
- docs/plans/module_federation/MASTER_PLAN.md §2.5 (state sharing), §6.1 (auth token sharing), §7 R1 (auth singleton drift P0)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (AuthService as-built: providedIn:'root', signal _token/_user, currentUser(), logout(), setSession())

## Your mission
AFTER component-builder's Phase A+B is green. VERIFY the AuthService singleton contract (D22) on the extracted mfe-onboarding remote. Do NOT change AuthService logic. (1) Confirm `@mesell/core` is in the mfe-onboarding federation.config.js shared set with singleton:true (C1) — NOT in skip. (2) Author + run the C5 singleton smoke test: setSession(token,user) in the shell context -> navigate to /profile (remote) -> assert auth.currentUser()?.name renders the shell's value -> trigger logout() from the remote -> assert auth.isAuthenticated()===false back in the shell AND the authGuard blocks a protected route. (3) Inspect the mfe-onboarding build output (dist/remote chunks) and assert there is NO duplicate auth.service chunk (C2 static proof — the remote must NOT bundle its own @mesell/core copy).

## Acceptance criteria
- [ ] @mesell/core confirmed shared+singleton in mfe-onboarding federation.config.js (not skipped)
- [ ] C5 smoke test authored + PASSING: shell setSession -> remote profile sees currentUser -> remote logout -> shell isAuthenticated false + guard blocks
- [ ] remote build output has NO duplicate auth.service chunk (single shared instance — C2 proof)
- [ ] the finalised D22 C1-C5 contract recorded for SP04/SP05/SP06 consumption

## Hard constraints
- ZERO changes to libs/core/services/auth.service.ts (D22 C2 — singleton via import-map, NOT a decorator refactor)
- Do NOT add NgRx/any state lib (CLAUDE.md D10); do NOT use BroadcastChannel for in-app sync (§2.5 — cross-tab only)
- Do NOT touch the extraction (component-builder's work); do NOT touch backend/k8s/infra

## Files you MAY touch
- A smoke-test spec under apps/mfe-onboarding/ or a shell integration spec (the C5 test); read-only inspection of build output
- The forward-contract memo content (reported to the lead for memory; you do not write the lead's memory)

## Final report format
@mesell/core singleton confirmation, C5 smoke-test PASS/FAIL with the assertion outputs, the no-duplicate-chunk proof, and the finalised C1-C5 contract text. If C5 FAILS: STOP — this is the migration's auth go/no-go; escalate to the lead, do NOT merge.
```

---

## Review + iteration protocol

### meesell-angular-component-builder (extraction)

- **Pre-approval checklist:** (a) history preserved on the 4 moved + 1 promoted files; (b) onboarding/profile diffs empty except import rewrites (D23 no-logic); (c) `AuthLayoutComponent` in `libs/composites` barrel + NO dangling relative `auth-layout` import (`grep -rn auth-layout` shows only `@mesell/composites` consumers + the lib itself); (d) profile's `@mesell/core` + deep `@mesell/ui-kit/*` imports UNCHANGED; (e) `federation.config.js` has TWO exposes + `@mesell/core` shared-singleton (not skipped); (f) manifest has THREE entries; (g) test count preserved; (h) shell build ≤90 s.
- **PR-template gate:** complete, no `<>`; build evidence, bundle delta, 360/1280 screenshots of BOTH pages (no visual change), a11y, boundary output, both-routes-render proof.
- **Re-dispatch triggers:** "edited onboarding/profile logic" → quote D23; "left a dangling auth-layout import" → re-dispatch with the failing grep; "changed AuthService decorator/logic" → quote D22 C2; "skipped @mesell/core in the remote config" → quote D22 C1; "re-authored fallback/helper" → quote SP02 D15; "test count dropped" → the `apps/**/*.spec.ts` note.
- **Iteration cap: 3** → founder escalation.

### meesell-angular-service-builder (auth-singleton verification)

- **Pre-approval checklist:** (a) `git diff libs/core/services/auth.service.ts` is EMPTY (no logic change — D22 C2); (b) the C5 smoke test exists + PASSES with visible assertion output; (c) the no-duplicate-`auth.service`-chunk proof attached (build-output inspection); (d) `@mesell/core` confirmed shared-singleton.
- **Re-dispatch triggers:** "modified AuthService" → quote D22 C2; "C5 not actually run / no assertion output" → re-dispatch demanding the live test result; "used BroadcastChannel for in-app sync" → quote §2.5; "added NgRx" → quote CLAUDE.md D10.
- **HARD STOP (not a re-dispatch):** if the C5 smoke test FAILS (drift — two AuthService instances), this is the migration's auth go/no-go. HALT, do NOT merge, escalate to the founder. A failed singleton contract blocks SP04/SP05/SP06 and may force a federation-config or architecture rethink (MASTER_PLAN R1 P0).
- **Iteration cap: 3** → founder escalation.

---

## Acceptance gate

When every box is `[x]`, `feature/mfe-onboarding/integration` is ready for the founder's develop PR.

- [ ] PR (`feature/mfe-onboarding/frontend` → integration) merged by Frontend Lead (squash)
- [ ] `ng build mfe-onboarding` GREEN — produces `remoteEntry.json` exposing BOTH components (record seconds)
- [ ] Shell `pnpm build` GREEN and **≤ 90 s** (Stop Condition) — seconds + bundle delta in PR + STATUS
- [ ] `pnpm test` total == **prior baseline, 0 failing, 0 skipped** — new failure or count drop blocks merge (R-SP3-3)
- [ ] **Boundary grep clean** — no new PrimeNG leak from `apps/mfe-onboarding/` or the promoted `libs/composites/auth-layout/`
- [ ] **AuthLayout promoted (D21):** `AuthLayoutComponent` in `libs/composites` + barrel; NO dangling relative `auth-layout` import anywhere (FOUNDER-FLAG D21 resolved)
- [ ] **Both routes resolve:** `/onboarding` → `OnboardingComponent`, `/profile` → `ProfileComponent`, both render in the shell outlet
- [ ] **THREE remotes coexist** in the manifest (`mfe-pricing`, `mfe-export`, `mfe-onboarding`)
- [ ] **AuthService singleton smoke test (D22 C5) PASSES** — the migration's auth go/no-go: shell `setSession` → remote `profile` sees `currentUser()` → remote `logout()` → shell `isAuthenticated()` false → guard blocks. **A FAIL halts the migration.**
- [ ] **No duplicate `auth.service` chunk** in the remote build output (D22 C2 static proof)
- [ ] **The finalised AuthService singleton contract (D22 C1–C5) recorded** in `sub_plan_03_onboarding.md` — the §5-row-3 deliverable consumed by SP04/SP05/SP06
- [ ] FOUNDER-FLAGs: D21 (AuthLayout promotion) resolved; D9 + D14 inherited from SP01 — *(D21 founder RULED APPROVED-as-recommended 2026-06-11; D9/D14 resolved at SP07 via D43/D42, also RULED 2026-06-11)*
- [ ] Infra deploy memo filed (D24); board inter-lead row added
- [ ] `feature_board_frontend.md` row = MERGED; STATUS_FRONTEND.md appended; `sub_plan_03_onboarding.md` written
- [ ] **Founder approval** on `feature/mfe-onboarding/integration` → `develop` (founder's gate, NOT the lead's)

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SP3-1 | **AuthService singleton drift (MASTER_PLAN R1 P0)** — the `mfe-onboarding` remote bundles its OWN copy of `@mesell/core` (because `providedIn:'root'` + a non-shared dependency), creating two parallel token signals; logout in the remote doesn't propagate to the shell. | Medium | **P0** | D22 C1: `@mesell/core` MUST be `shared + singleton:true` (not skipped) — enforced + verified by service-builder. C2: the import-map guarantees ONE module instance. C5 smoke test PROVES it at runtime; the no-duplicate-chunk inspection PROVES it statically. A FAIL halts the migration (this is THE auth go/no-go). |
| R-SP3-2 | **`AuthLayoutComponent` dangling import** — promoting it to `libs/composites` leaves a consumer (a shell auth page, or onboarding) still importing the old relative `layouts/` path → build break or stale duplicate. | Medium | High | D21: enumerate ALL `auth-layout` consumers with grep BEFORE moving; re-point every relative import to `@mesell/composites`; the build fails immediately on a dangling import (caught pre-merge). |
| R-SP3-3 | **Spec-discovery regression** — moving onboarding + profile specs into `apps/mfe-onboarding/`; relies on SP01's `apps/**/*.spec.ts` glob. | Medium | High | RE-CONFIRM the glob; assert exact total count preserved; drop = hard reject. (Same recipe as SP01 §9.A item 6.) |
| R-SP3-4 | **Two-expose remote resolution bug** — the shell loads `OnboardingComponent` from the remote but `ProfileComponent` fails (a multi-expose Native Federation quirk). | Low | High | §9 mandates BOTH routes resolve + both components render in the same session. This is the new surface vs SP01/SP02 single-expose. If it fails, halt + escalate (blocks SP05's `./CatalogRoutes` multi-expose too). |
| R-SP3-5 | **Profile spec can't resolve AuthService after the move** — `profile.component.spec.ts` provides/mocks `AuthService`; after relocation the `@mesell/core` import or the test bed provider may not resolve under the new project's tsconfig. | Medium | Medium | The `@mesell/core` alias resolves workspace-wide (SP0). Verify the spec's TestBed still provides AuthService and passes; if the spec hard-codes a relative path, rewrite to `@mesell/core`. Caught by the preserved-count + green-tests gate. |
| R-SP3-6 | **CSP blocks the third remote in staging/prod.** | Low (dev) / High (prod) | High | Inherited D14 / SP01 R-SP1-4: dev has no CSP; CSP authoring deferred to Sub-plan 7 before staging/prod. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1.1 | 2026-06-11 | `meesell-frontend-coordinator` (founder-ruling landing session) | Landed the founder's 2026-06-11 morning ruling on D21: **`AuthLayoutComponent` promotion to `@mesell/composites` APPROVED as recommended** — executes at SP03 as planned (PROMOTE), serving the onboarding remote + the SP06 auth remote; no LOCKED-doc amendment. Additive RULED annotation on the D21 FOUNDER-FLAG block + the Founder-decisions-required summary + the §9 FOUNDER-FLAGs acceptance line (also noting D9/D14 resolved at SP07 via the same-day D43/D42 rulings). No structural change. |
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-2` (night-run master-session dispatch) | Initial authoring of Sub-Plan 03 — `mfe-onboarding` (F5 onboarding + F13 profile). Grounded in the POST-SP0 integration-branch reality (`e51761b`): profile consumes `AuthService` from `@mesell/core` (`currentUser()` 4×, `logout()` 1×) — the FIRST cross-boundary singleton; onboarding imports `AuthLayoutComponent` via a relative `layouts/` path that CANNOT survive extraction. D20 (two-expose remote), D21 (PROMOTE AuthLayout → `@mesell/composites` — FOUNDER-FLAG, serves onboarding + SP06), **D22 (the FINALISED AuthService singleton contract C1–C5 — the §5-row-3 deliverable: `providedIn:'root'` retained, singleton enforced via import-map sharing + the C5 runtime smoke test + no-duplicate-chunk static proof; the auth go/no-go for the whole migration)**, D23 (remote-private validator/form logic), D24 (third-remote Option-C). Adds `meesell-angular-service-builder` to the lineup for the auth-singleton verification. 6 risks incl. R-SP3-1 the P0 auth-drift (HALT on C5 fail) + R-SP3-2 AuthLayout dangling import. One new FOUNDER-FLAG (D21); D9/D14 inherited. Awaits founder approval; gated on SP01+SP02 merged + the C5 smoke test designed. |
