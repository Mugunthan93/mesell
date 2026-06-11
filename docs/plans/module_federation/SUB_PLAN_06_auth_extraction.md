# Sub-Plan 06 — `mfe-auth` Extraction (F2 login + F3 signup + F4 otp-verify) — THE LAST EXTRACTION

**STATUS: DRAFT 2026-06-10 — authored under master-session night-run dispatch (S3, session `mesell-module-federation-frontend-session-3`). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan (planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10, FEDERATION FIRST) §4.2 ordering "Last" + §5 row 6 |
| Predecessors | SP00–SP05 ALL EXECUTED. Critically: SP03 finalised the AuthService singleton contract (D22 C1–C5) + promoted `AuthLayoutComponent` to `@mesell/composites`; SP03/SP04/SP05 are the **≥3 remotes** across which the singleton + refresh-token flow are proven (SP06's §5-row-6 blocking dependency). |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order |
| Author | meesell-frontend-coordinator (Frontend Lead) |
| Feature slug | `mfe-auth` |
| Remote ID | R1 (MASTER_PLAN §2.2) |
| Owned features | F2 login · F3 signup · F4 otp-verify |
| Owned routes | `/login` · `/signup` · `/otp-verify` (all PUBLIC top-level) |
| Complexity | **M** (THREE PUBLIC pages; the ONLY flow that WRITES `auth.token()` via `setSession`; the most shell-connected remote — extracted LAST so 5 reference implementations + the proven D22 contract de-risk it) |
| Scope | Extract the auth flow into a standalone remote exposing THREE components; CONSUME the SP03 D22 singleton contract (do NOT re-derive); add ONLY the `setSession` WRITE-path proof (C4); wire three PUBLIC top-level routes to `loadRemoteWithFallback`. Frontend-only. |
| Out of scope | Other remotes (all done); backend (the real OTP/JWT API is Wave 6 — SP06 keeps the simulated `setSession('mock-token', ...)`); AI; mobile; CSP cutover (Sub-plan 7); the refresh-token interceptor (lives in the shell, untouched) |
| Execution gates | SP01–SP05 merged to develop + founder approval of THIS sub-plan + the SP03 D22 contract PROVEN across ≥3 remotes (SP03+SP04+SP05) + infra C-CI-1 ready + GATE4 Option-C confirmed |

`mfe-auth` is the **sixth and FINAL extraction** (MASTER_PLAN §4.2: "Most connected to shell. AuthService consumers; the only flow that mutates `auth.token()`; if auth federation breaks, the whole app breaks. Extract last so by the time we touch it we have 5 reference implementations and confidence in singleton handoff"). By SP06 EVERY federation primitive is proven: project shape (SP01), single + multi-expose (SP01/SP03), public/private routing (SP04), the `Routes`-array (SP05), the AuthService singleton READ + LOGOUT cross-boundary (SP03 C5). SP06 adds the ONE remaining unproven surface: the **`setSession` WRITE path** (C4) — a remote MUTATES the shell's token signal, and the shell's guard/navbar must react. This is the migration's auth WRITE go/no-go, the mirror of SP03's READ/LOGOUT go/no-go.

Facts from the post-SP0 integration-branch reality (verified, `feature/mf-workspace-foundation/integration` @ `e51761b`):
- **All 3 auth pages are PUBLIC top-level routes** (`/login`, `/signup`, `/otp-verify` in `app.routes.ts` — NOT shell children, NO `authGuard`). They are reached pre-authentication. This is the all-public mirror of SP04's mixed split (and the public-route recipe SP04 D27 established applies).
- **All 3 import `AuthLayoutComponent` via a RELATIVE `layouts/auth-layout` path** (`login.component.ts`/`signup.component.ts` use `../../layouts/auth-layout/...`; `otp-verify.component.ts` uses `../../../layouts/auth-layout/...`). SP03 D21 PROMOTED `AuthLayoutComponent` to `@mesell/composites` — so by SP06 these relative imports MAY already be re-pointed to `@mesell/composites` (SP03's dispatch optionally re-pointed the shell auth pages "if they currently use the relative path"). SP06 MUST verify + ensure they import from `@mesell/composites` (the remote cannot reach `../../layouts/`).
- **Only `otp-verify.component.ts` touches AuthService** — it `inject(AuthService)` and calls `auth.setSession('mock-token', { id, name, phone })` inside `onSubmit()` (after a `setTimeout(1500)` simulating the OTP-verify API), then `router.navigate(['/dashboard'])`. `login.component.ts` + `signup.component.ts` do NOT inject AuthService (they navigate to `/otp-verify` after collecting credentials). So the WRITE path (C4) lives entirely in the OTP page.
- **`otp-verify` also has a `setInterval` resend-countdown timer** (the `startCountdown()` + `clearInterval` pattern, verified) — the D18 timer-preservation rule (SP02) applies: move it UNCHANGED, verify it clears on navigate-away.
- **ui imports are DEEP** (`@mesell/ui-kit/input/input.component`, `@mesell/ui-kit/button/button.component`, `@mesell/ui-kit/otp-input/otp-input.component`) — the lean-bundle deep-import pattern (MEMORY.md). Preserve as-is; do NOT rewrite to the barrel.

---

## Decisions

D-numbers append-only and monotonic, continuing from SUB_PLAN_05 (which ended at D35). FOUNDER-FLAG marks founder-level calls.

### Adaptations from the canonical V1-feature pattern

Same structural-extraction shape, M-complexity: THREE public single-component exposes + the `setSession` WRITE-path proof + the AuthLayout-import verification (SP03's promotion must be in effect). Lineup is one lead + BOTH specialists (component-builder for the 3 pages; service-builder for the C4 WRITE-path proof — the auth-WRITE go/no-go, MASTER_PLAN §5 row 6 names `meesell-angular-service-builder` as the responsible agent because "auth flow critical"). §3 is dominated by `MOVE` + the standard scaffolding `NEW` set + 3 PUBLIC route-swap `MODIFY`s. §9 carries the C4 WRITE-path smoke test as the auth-WRITE go/no-go (the counterpart to SP03's C5 READ/LOGOUT go/no-go).

### D36 — SP06 COPIES the proven recipe AND CONSUMES the SP03 D22 contract; it does NOT re-derive the singleton — it adds ONLY the `setSession` WRITE-path proof (C4)

**Decision.** Per SP03 D22 C4 + the §5-row-6 dependency ("AuthService singleton + refresh-token flow proven across ≥3 remotes"): SP06 does NOT re-derive the AuthService singleton contract — it is FINALISED in `sub_plan_03_onboarding.md` (C1–C5) and PROVEN across SP03 (READ + LOGOUT), SP04 (uniform shared-set even though unused), and SP05 (uniform shared-set). SP06 CONSUMES it and adds the single remaining unproven operation: **C4's WRITE path** — the OTP remote calls `auth.setSession(...)` and the shell's `isAuthenticated()`/guard/navbar must react.

**Rationale.** SP03 explicitly handed the WRITE path to SP06: D22 C4 says "`setSession` is owned by the auth flow (SP06 `mfe-auth`) … SP03 proves the READ + the LOGOUT cross-boundary; SP06 proves the full WRITE (login → token set → all remotes see authenticated)." Re-deriving the contract would waste SP03's investment and risk drift. The §5-row-6 blocking dependency is satisfied: SP03+SP04+SP05 = the ≥3 remotes.

**Consequence.** SP06's federation scaffolding is the standard SP04-style copy (project shape, fallback helper, manifest, test-discovery — all reused). The ONLY new verification is the C4 WRITE-path smoke test (D38). `@mesell/core` MUST be in the `mfe-auth` shared/singleton set (C1) so the OTP remote's `inject(AuthService)` resolves to the shell's instance — without that, `setSession` mutates a DUPLICATE instance and the shell never sees authentication (the P0 drift, MASTER_PLAN R1). The service-builder VERIFIES this (no skip).

### D37 — The remote exposes THREE PUBLIC components; all three route swaps preserve the public, no-guard, top-level shape (SP04 D27 public-route recipe)

**Decision.** `mfe-auth`'s `federation.config.js` `exposes`:
```
'./LoginComponent':     './apps/mfe-auth/src/app/login.component.ts'
'./SignupComponent':    './apps/mfe-auth/src/app/signup.component.ts'
'./OtpVerifyComponent': './apps/mfe-auth/src/app/otp-verify.component.ts'
```
The shell swaps THREE PUBLIC top-level routes (NO `authGuard`):
- `'login'` → `loadRemoteWithFallback('mfe-auth', './LoginComponent')`
- `'signup'` → `loadRemoteWithFallback('mfe-auth', './SignupComponent')`
- `'otp-verify'` → `loadRemoteWithFallback('mfe-auth', './OtpVerifyComponent')`

**Rationale.** All three are public (reached pre-auth). SP04 D27 proved the public-route swap (preserve top-level placement, add NO guard). SP06 is the all-public, three-expose application of that recipe. Neither page owns a sub-route tree → three single-component exposes (NOT a `Routes` array — contrast SP05's catalog funnel). The `**` wildcard → `login` redirect in the shell (verified) stays in the SHELL (it is shell-routing config, not auth-page content) and now redirects to a route that loads the remote login component.

**Consequence.** Manifest gains ONE entry (`mfe-auth`); three exposes from one entry (the SP03 multi-expose pattern, D20). Three PUBLIC route swaps; the parent protected-shell route + its `authGuard` are UNTOUCHED. **The wildcard redirect (`{ path: '**', redirectTo: 'login' }`) stays in the shell** — verify it still resolves to the remote login after the swap.

### D38 — The `setSession` WRITE-path smoke test (C4) — the migration's auth WRITE go/no-go; authored by service-builder, consumes SP03's C5 test shape

**Decision.** The OTP remote's `setSession` is the only WRITE to `auth.token()`. SP06's service-builder authors + runs the C4 WRITE-path smoke test (the mirror of SP03's C5 READ/LOGOUT test):
```
1. Serve shell + mfe-auth remote (+ ideally one authenticated remote, e.g. mfe-dashboard, to observe the reaction).
2. Start UNAUTHENTICATED: assert shell auth.isAuthenticated() === false; the authGuard blocks /dashboard.
3. Navigate to /otp-verify (remote OtpVerifyComponent), enter a 6-digit OTP, submit.
4. The remote calls auth.setSession('mock-token', { id, name, phone }) — a WRITE to the shell's single AuthService instance.
5. ASSERT: back in the shell, auth.isAuthenticated() === true AND auth.currentUser()?.name === 'Seller'
   (the remote's WRITE crossed the boundary into the shell's signal).
6. ASSERT: the post-setSession router.navigate(['/dashboard']) now PASSES the shell authGuard (it was blocked in step 2).
7. Inspect the mfe-auth remote build output: assert NO duplicate auth.service chunk (C2 static proof — same as SP03).
```

**Rationale.** D22 C4 reserved the WRITE-path proof for SP06. C5 (SP03) proved READ + LOGOUT (the shell writes, the remote reads + clears). SP06 proves the INVERSE: the REMOTE writes, the shell reads. Together C5 (SP03) + this C4 WRITE test (SP06) close the full auth-state-sharing loop — the migration's complete auth go/no-go. If this fails (the remote's `setSession` mutates a duplicate instance), it is the P0 drift (MASTER_PLAN R1) and HALTS the cutover.

**Consequence.** This is SP06's first-class §9 gate. It is the LAST auth proof in the migration; passing it (plus SP03's C5) means the federated auth story is complete and SP07 cutover can proceed. The test REUSES SP03's C5 harness shape (inverted). The `setSession('mock-token', ...)` simulation is preserved EXACTLY (no real OTP/JWT API — that is Wave 6); the test proves the SIGNAL-SHARING mechanism, not the auth backend.

### D39 — `AuthLayoutComponent` is imported from `@mesell/composites` (SP03 D21 promotion); the otp `setInterval` resend-timer is preserved EXACTLY (SP02 D18)

**Decision.**
- **AuthLayout (D21 consumption):** SP03 promoted `AuthLayoutComponent` → `@mesell/composites`. SP06 VERIFIES the 3 auth pages import it from `@mesell/composites` (NOT the old relative `../../layouts/auth-layout`). If SP03's dispatch already re-pointed the shell auth pages (it optionally did), this is a no-op verification; if any page still uses the relative path, SP06 re-points it (the remote CANNOT reach `../../layouts/`). The `<mee-auth-layout>` template usage is unchanged.
- **OTP resend-timer (D18 consumption):** `otp-verify.component.ts`'s `startCountdown()` `setInterval` + `clearInterval` resend-countdown moves UNCHANGED into the remote. Per SP02 D18 (timer preservation): no rewrite to RxJS; verify the timer clears on navigate-away (the remote component's `ngOnDestroy`/`clearInterval` fires when the user leaves `/otp-verify` — the federation boundary does NOT change lifecycle).

**Rationale.** D21 (SP03) made AuthLayout a shared composite precisely so the auth remote could consume it (SP03's FOUNDER-FLAG rationale named SP06 as a beneficiary). D18 (SP02) established that relocated timers are behaviour-preserving. SP06 consumes both — no new decision, just verification + preservation.

**Consequence.** `mfe-auth` imports `@mesell/composites` (AuthLayout) + deep `@mesell/ui-kit/*` (input/button/otp-input) + `@mesell/core` (AuthService — OTP page only). Confirmed import surfaces (integration branch):
```
login:   @angular/forms {FormControl,FormGroup,ReactiveFormsModule,Validators}, @angular/router {Router,RouterLink},
         @mesell/composites {AuthLayoutComponent (via SP03 D21)}, @mesell/ui-kit/input + /button (deep). NO AuthService.
signup:  same shape as login. NO AuthService.
otp:     @angular/router {Router,RouterLink}, @mesell/composites {AuthLayoutComponent}, @mesell/core {AuthService},
         @mesell/ui-kit/otp-input + /button (deep). setSession WRITE (C4) + setInterval resend-timer (D18).
```

### D40 — Option-C deploy mirrors SP01–05; `mfe-auth` is the SIXTH (final) remote at `remotes.mesell.xyz`; ALL 6 remotes now in the manifest

**Decision.** Per `GATE4_CONFIRMATION.md` C-RES-2 / C-ROUTE-1: built `mfe-auth` → `gs://meesell-frontend/{env}/mfe-auth/{version}/`, shell manifest gains the SIXTH and final entry. After SP06, ALL 6 MASTER_PLAN §2.2 remotes (`mfe-pricing`, `mfe-export`, `mfe-onboarding`, `mfe-dashboard`, `mfe-catalog`, `mfe-auth`) are extracted + in the manifest. Dev-validation uses localhost-served remotes.

**Rationale + Consequence.** Identical to D13/D19/D24/D29/D35. The new (and final) surface is the six-remote manifest — the COMPLETE federated topology. **CSP raised-stakes (forward to SP07):** like landing (SP04 R-SP4-5), the auth pages are PUBLIC + pre-auth — an unauthenticated visitor at `/login` fetches `remotes.mesell.xyz` before any session exists. So the SP07 CSP (C-CSP-1) must cover BOTH the public landing (mfe-dashboard) AND the public auth pages (mfe-auth) before staging/prod — recorded for SP07. After SP06, SP07 (cutover) is the only remaining sub-plan: all extractions are done, and SP07 hardens the now-complete topology.

### Founder decisions required

**None new.** Inherited: SP01 D9 (shell stays at `src/` — SP07 decides the relocation) + D14 (dev without CSP, SP07 authors it); SP03 D21 (AuthLayout promoted — already merged, SP06 consumes); SP05 D33 (Product/Catalog promoted — already merged, mfe-auth does not consume models). Apply unchanged. D36–D39 are LEAD/specialist-level technical decisions consuming proven contracts — no founder call, no LOCKED-doc amendment.

---

## Agent lineup

| Lead | Specialist dispatched | What the specialist builds |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | Creates `apps/mfe-auth/` (copy pilot recipe); `git mv`s login + signup + otp-verify into it; VERIFIES/re-points the `AuthLayoutComponent` import to `@mesell/composites` (D39/D21) on all 3 pages; preserves the otp `setInterval` resend-timer UNCHANGED (D39/D18); preserves the deep `@mesell/ui-kit/*` imports; NEW public-api.ts re-exporting all 3 components; NEW federation.config.js name 'mfe-auth' exposing all 3 + `@mesell/core` in the shared set; wires 3 PUBLIC route swaps; patches the manifest with the sixth entry; verifies builds, all 3 routes resolve, the wildcard redirect still hits the remote login, the resend-timer clears on navigate-away. |
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-service-builder` (sonnet) | The auth-WRITE go/no-go: VERIFIES `@mesell/core` is shared+singleton in `mfe-auth` (C1, not skipped); authors + runs the C4 `setSession` WRITE-path smoke test (D38 — unauth shell → OTP remote setSession → shell isAuthenticated true + currentUser correct + guard now passes); inspects the remote build output for a duplicate `auth.service` chunk (C2 static proof). Does NOT change AuthService logic (D22 C2). CONSUMES the SP03 D22 contract — does NOT re-derive it. |

Per MASTER_PLAN §5 row 6 the responsible agent is `meesell-angular-service-builder (auth flow critical)`; SP06 adds `meesell-angular-component-builder` for the 3-page extraction. Dispatch order: component-builder extracts + wires; service-builder runs the C4 WRITE-path proof AFTER the component-builder's build is green. Infra is a cross-lead dependency (D40 memo), not a dispatched specialist.

### Dispatch order

```
PHASE A — extract the 3 auth pages (component-builder)
   A1. Copy apps/mfe-pricing/ shape -> apps/mfe-auth/ (angular.json native-federation:build remote)
   A2. git mv features/auth/login.component.{ts,spec.ts} + signup.component.{ts,spec.ts}
       + features/auth/otp-verify/otp-verify.component.{ts,spec.ts} -> apps/mfe-auth/src/app/
   A3. VERIFY/re-point AuthLayoutComponent import -> @mesell/composites on ALL 3 pages (D39/D21);
       grep to confirm NO relative ../../layouts/auth-layout import remains
   A4. PRESERVE the otp setInterval resend-timer UNCHANGED (D39/D18); PRESERVE the deep @mesell/ui-kit/* imports
   A5. NEW public-api.ts re-exporting Login + Signup + OtpVerify components
   A6. NEW federation.config.js name 'mfe-auth' exposing ALL 3 (D37) + shareAll singletons with @mesell/core in the shared set (D36 C1 — NOT skipped, the OTP page's setSession depends on it)
   A7. BUILD CHECKPOINT — `ng build mfe-auth`. HARD GATE.

PHASE B — wire the shell (component-builder)
   B1. app.routes.ts: 3 PUBLIC top-level swaps (NO guard) — login/signup/otp-verify -> loadRemoteWithFallback('mfe-auth', './LoginComponent' / './SignupComponent' / './OtpVerifyComponent')
   B2. public/federation.manifest.json: add "mfe-auth" (now SIX entries — the complete topology)
   B3. VERIFY — shell build ≤90 s; tests green/count preserved; boundary clean; all 3 routes resolve + render;
       the wildcard '**' -> login redirect still hits the remote login; the otp resend-timer clears on navigate-away (D39/D18)

PHASE C — the auth-WRITE go/no-go (service-builder, AFTER B green)
   C1. Confirm @mesell/core shared+singleton in mfe-auth federation.config.js (C1, not skipped)
   C2. Author + run the C4 setSession WRITE-path smoke test (D38): unauth shell (isAuthenticated false, guard blocks /dashboard)
       -> /otp-verify remote -> setSession -> shell isAuthenticated TRUE + currentUser correct -> navigate /dashboard now PASSES the guard
   C3. Inspect mfe-auth build output: assert NO duplicate auth.service chunk (C2 static proof)

PHASE D — lead, no specialist
   D1. Auth WRITE go/no-go: the C4 test is the migration's final auth gate — if it fails (drift), HALT + escalate (P0)
   D2. 360/1280 screenshots of /login + /signup + /otp-verify (no visual change)
   D3. Infra deploy memo (D40 sixth/final remote + the public-auth-pages CSP escalation for SP07) + merge-gate review + PR
   D4. Confirm the COMPLETE 6-remote topology — note that SP07 (cutover) is now the only remaining sub-plan
```

---

## Code surfaces

Exhaustive inventory. Tags: `MOVE` / `MODIFY` / `NEW`. Source paths verified on `feature/mf-workspace-foundation/integration`.

### Relocation — the 3 auth pages → `apps/mfe-auth/src/app/` (6 files incl. specs)

| # | Source (post-SP0) | Target | Tag | Notes |
|---|---|---|---|---|
| 1 | `frontend/src/app/features/auth/login.component.{ts,spec.ts}` | `apps/mfe-auth/src/app/login.component.{ts,spec.ts}` | MOVE | Public. `AuthLayoutComponent` import → `@mesell/composites` (D39); deep `@mesell/ui-kit/input` + `/button` UNCHANGED; injects `Router`. NO AuthService. |
| 2 | `frontend/src/app/features/auth/signup.component.{ts,spec.ts}` | `apps/mfe-auth/src/app/signup.component.{ts,spec.ts}` | MOVE | Same shape as login. `AuthLayoutComponent` → `@mesell/composites`; deep ui-kit imports; injects `Router`. NO AuthService. |
| 3 | `frontend/src/app/features/auth/otp-verify/otp-verify.component.{ts,spec.ts}` | `apps/mfe-auth/src/app/otp-verify.component.{ts,spec.ts}` | MOVE | Public. `AuthLayoutComponent` → `@mesell/composites`; deep `@mesell/ui-kit/otp-input` + `/button`; injects `Router` + `AuthService` (`@mesell/core`). The `setSession` WRITE (C4) + the `setInterval` resend-timer (D18) — both UNCHANGED. The spec likely provides/mocks AuthService — verify it still resolves `@mesell/core` (R-SP6-5). |

After the moves, `frontend/src/app/features/auth/` is removed.

### Federation scaffolding — `apps/mfe-auth/` (NEW, copies the pilot)

| # | Path | Tag | Description |
|---|---|---|---|
| 4 | `frontend/apps/mfe-auth/src/app/public-api.ts` | NEW | Re-exports `LoginComponent` + `SignupComponent` + `OtpVerifyComponent` (§6.5 — all THREE, D37). |
| 5 | `frontend/apps/mfe-auth/federation.config.js` | NEW | `name: 'mfe-auth'`, THREE `exposes` entries (D37), `shareAll` singletons — **`@mesell/core` MUST be in the shared/singleton set, NOT skipped** (D36 C1 — the OTP `setSession` WRITE depends on resolving the shell's AuthService instance). |
| 6 | `frontend/apps/mfe-auth/src/main.ts` | NEW | Dev-serve bootstrap (router with the 3 routes for standalone dev). |
| 7 | `frontend/apps/mfe-auth/tsconfig.app.json` | NEW | Extends base; `@mesell/*` paths incl. `@mesell/core` + `@mesell/composites`. |

### Shell wiring (MODIFY — reuse SP01 helper)

| # | Path | Tag | Description |
|---|---|---|---|
| 8 | `frontend/src/app/app.routes.ts` | MODIFY | THREE PUBLIC top-level swaps (NO guard): `login` / `signup` / `otp-verify` → `loadRemoteWithFallback('mfe-auth', './LoginComponent' / './SignupComponent' / './OtpVerifyComponent')`. The `**` → `login` wildcard redirect UNCHANGED (now resolves to the remote login). The protected-shell parent + `authGuard` UNCHANGED. |
| 9 | `frontend/public/federation.manifest.json` | MODIFY | Add `"mfe-auth"` (now SIX entries — the complete topology). |
| 10 | `frontend/angular.json` | MODIFY | Add `projects.mfe-auth`. Shell project UNCHANGED. |
| 11 | test-discovery `include` + Tailwind `content` | RE-CONFIRM | `apps/**` globs from SP01 cover the new project. No edit expected. |

### Documentation / status / memory

| # | Path | Tag | Description |
|---|---|---|---|
| 12 | `docs/status/feature_board_frontend.md` | MODIFY | `mfe-auth` row lifecycle + infra inter-lead row (D40). |
| 13 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log — build/test numbers, the C4 WRITE-path smoke-test result (the auth WRITE go/no-go), the complete-6-remote-topology milestone. |
| 14 | `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_06_auth.md` | NEW | The C4 WRITE-path proof result + the complete-topology milestone + the SP07 handoff (all extractions done; cutover is next). |

No backend/AI/data surface (the real OTP/JWT API is Wave 6). No LOCKED-doc amendment.

### Illustrative `federation.config.js` (remote) shape

```js
// frontend/apps/mfe-auth/federation.config.js
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

module.exports = withNativeFederation({
  name: 'mfe-auth',
  exposes: {
    './LoginComponent':     './apps/mfe-auth/src/app/login.component.ts',
    './SignupComponent':    './apps/mfe-auth/src/app/signup.component.ts',
    './OtpVerifyComponent': './apps/mfe-auth/src/app/otp-verify.component.ts',
  },
  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
    // @mesell/core (AuthService) MUST resolve to the shell's instance (D36 C1) —
    // the OTP page's setSession() WRITE depends on mutating the SHELL's single signal.
  },
  skip: ['rxjs/ajax', 'rxjs/fetch', 'rxjs/testing', 'rxjs/webSocket'],
  features: { ignoreUnusedDeps: true },
});
```

---

## Documentation deliverables

Gate conditions in §9. The PR cannot merge to integration without:

1. **`SUB_PLAN_06_auth_extraction.md`** (this document) — referenced from MASTER_PLAN §5 row 6.
2. **`sub_plan_06_auth.md` memo** — the C4 `setSession` WRITE-path proof result (the auth WRITE go/no-go) + the complete-6-remote-topology milestone + the SP07 handoff. CONSUMES (does not re-derive) the SP03 D22 contract.
3. **The C4 WRITE-path smoke test** — authored, run, result recorded (PASS is the migration's auth WRITE go/no-go; together with SP03's C5 it closes the full auth-state loop).
4. **Infra deploy memo** (`handoff_mf_auth_deploy.md`) — sixth/final-remote GCS prefix + matrix fan-out (C-CI-1) + the public-auth-pages CSP escalation for SP07 (C-CSP-1: `/login` first paint fetches `remotes.mesell.xyz` pre-auth).
5. **`feature_board_frontend.md` + `STATUS_FRONTEND.md`** current through the lifecycle.

---

## Branch setup

Feature slug `mfe-auth`. Per F1.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-auth/integration` | `develop` (AFTER SP05 merged) | Integration branch | Frontend Lead |
| `feature/mfe-auth/frontend` | `feature/mfe-auth/integration` | ALL extraction + the C4 WRITE-path verification | `meesell-angular-component-builder`, `meesell-angular-service-builder` |

Both specialists work the SAME `feature/mfe-auth/frontend` branch sequentially (component-builder extraction first, then service-builder the C4 WRITE-path proof). No infra group branch (parallel C-CI-1 effort).

### F1 branch-setup commands (EXECUTION stage)

```bash
git fetch origin develop
git checkout develop && git pull --ff-only          # must include SP05's merge

git checkout -b feature/mfe-auth/integration develop
git push -u origin feature/mfe-auth/integration

git checkout -b feature/mfe-auth/frontend feature/mfe-auth/integration
git push -u origin feature/mfe-auth/frontend

git worktree add /tmp/mesell-wt/mfe-auth feature/mfe-auth/frontend
```

### PR flow

```
feature/mfe-auth/frontend
        │  PR — Frontend Lead reviews+merges (squash)   [D1]
        ▼
feature/mfe-auth/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [D1]
        ▼
develop
```

Group → integration: Frontend Lead. Integration → develop: Founder (lead must NOT approve). F3 protection; re-probe empirically.

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (own memory — the AuthService as-built shape: `providedIn:'root'`, signals `_token`/`_user`, `setSession`, `logout`, `currentUser`; the deep-import bundle landmine; the `apps/**/*.spec.ts` test-discovery gotcha)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_03_onboarding.md` (**THE AuthService singleton contract D22 C1–C5** — SP06 CONSUMES this, adds only the C4 WRITE proof) + `sub_plan_01_pricing.md` (the base recipe) + `sub_plan_04_dashboard.md` (the public-route swap recipe — auth pages are all public) + `sub_plan_02_export.md` (the D18 timer-preservation rule — the otp resend-timer)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md` (alias map — `@mesell/core` = AuthService; `@mesell/composites` = AuthLayout after SP03 D21)
- `docs/plans/module_federation/MASTER_PLAN.md` §2.5 (state sharing), §6.1 (auth token sharing — the contract SP06 closes the WRITE side of), §7 R1 (auth singleton drift P0)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (GATE4 Option-C; C-CI-1; C-CSP-1)

### Cross-feature memos

- **Outgoing → infra:** `handoff_mf_auth_deploy.md` — sixth/final-remote GCS prefix + matrix fan-out (C-CI-1) + the public-auth-pages CSP escalation for SP07. 48h SLA. Board row added.
- **Forward-reference:** `sub_plan_06_auth.md` — the C4 WRITE-path proof + the complete-topology milestone (SP06's gift to SP07 cutover: all 6 remotes extracted, the full auth loop closed).

### Session-close memory entries

Session header (`## Session mesell-mfe-auth-frontend-session-{N}`), D36–D40 outcomes (esp. the C4 WRITE-path go/no-go result + the AuthLayout-import verification + the resend-timer preservation), files-touched count, remote + shell build seconds, test pass count, boundary result, the auth WRITE go/no-go verdict, the COMPLETE-6-remote-topology milestone, blockers, next-step (Sub-plan 7 — the cutover + hardening + the §5.1 compliance audit).

---

## Dispatch templates

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-auth-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_06_auth_extraction.md (this plan — D36-D40, esp. D37 three-public-expose + D39 AuthLayout-import + otp-timer, §3, §9)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md (the recipe) + sub_plan_04_dashboard.md (public-route swap) + sub_plan_02_export.md (D18 timer preservation)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (deep-import bundle landmine; @mesell/ui-kit/* deep imports; apps/**/*.spec.ts test-discovery)
- docs/plans/module_federation/MASTER_PLAN.md §2.4 (routing — public-route rule), §6.4 (error boundary)

## Your mission
PHASE A: Copy apps/mfe-pricing/ shape -> apps/mfe-auth/. `git mv` features/auth/login.component.{ts,spec.ts} + signup.component.{ts,spec.ts} + otp-verify/otp-verify.component.{ts,spec.ts} -> apps/mfe-auth/src/app/. VERIFY/re-point the AuthLayoutComponent import -> @mesell/composites on ALL 3 pages (D39/D21) — grep to confirm NO relative ../../layouts/auth-layout remains. PRESERVE the otp setInterval resend-timer UNCHANGED (D39/D18) + the deep @mesell/ui-kit/* imports (input/button/otp-input). KEEP otp's @mesell/core AuthService import + setSession call UNCHANGED. NEW public-api.ts re-exporting all 3. NEW federation.config.js name 'mfe-auth' exposing all 3 ('./LoginComponent','./SignupComponent','./OtpVerifyComponent') with @mesell/core in the shared/singleton set (NOT skipped — the setSession WRITE depends on it). BUILD CHECKPOINT: `ng build mfe-auth`. HARD GATE.
PHASE B: app.routes.ts -> 3 PUBLIC top-level swaps (NO guard): login/signup/otp-verify -> loadRemoteWithFallback('mfe-auth', './LoginComponent' / './SignupComponent' / './OtpVerifyComponent'). The '**' -> login wildcard UNCHANGED. manifest: add "mfe-auth" (SIX entries). VERIFY: shell build ≤90 s; tests green/count preserved; boundary clean; all 3 routes resolve + render; the wildcard redirect still hits the remote login; the otp resend-timer clears on navigate-away.

## Acceptance criteria
- [ ] apps/mfe-auth/ holds login + signup + otp-verify (+ specs) + public-api + federation.config + main.ts; old features/auth/ removed
- [ ] all 3 pages import AuthLayoutComponent from @mesell/composites; NO relative ../../layouts/auth-layout anywhere (D39)
- [ ] otp setInterval resend-timer UNCHANGED + clears on navigate-away (D39/D18); deep @mesell/ui-kit/* imports preserved
- [ ] otp's @mesell/core AuthService import + setSession call UNCHANGED
- [ ] federation.config exposes all 3; @mesell/core shared+singleton (NOT skipped — D36 C1)
- [ ] `ng build mfe-auth` GREEN -> remoteEntry.json (record seconds)
- [ ] shell `pnpm build` GREEN ≤ 90 s (seconds + bundle delta)
- [ ] `pnpm test` total == prior baseline, 0 failing/skipped (drop = HARD REJECT)
- [ ] boundary clean; all 3 PUBLIC routes resolve + render; the '**' -> login redirect hits the remote login; manifest has SIX entries

## Hard constraints
- ZERO logic/template edits to login/signup/otp (incl. the setSession call + the resend-timer) — relocation + the AuthLayout import re-point only
- Do NOT change AuthService logic or its @Injectable decorator (D36/D22 C2)
- Do NOT add a guard to the public auth routes (D37 — they are pre-auth public)
- Do NOT rewrite the otp timer to RxJS (D39/D18); do NOT rewrite deep @mesell/ui-kit/* imports to the barrel (bundle landmine)
- Do NOT author CSP (D14); do NOT move the shell into apps/shell/ (D9)
- Do NOT touch backend/, k8s/, infra/, OR other remotes/features

## Files you MAY touch
- frontend/apps/mfe-auth/** (new), frontend/angular.json (add project), frontend/public/federation.manifest.json
- frontend/src/app/app.routes.ts (the login/signup/otp-verify entries ONLY)

## Files you must NOT touch
- libs/core/services/auth.service.ts logic; libs/composites/auth-layout/** (consume, don't edit); src/app/core/{remote-failure,load-remote} (reuse); other remotes; backend/k8s/infra

## Final report format
Files moved (count), files new (count), AuthLayout-import-from-composites confirmation (grep proof no relative remains), otp-timer-preserved + clears-on-navigate proof, remote build seconds, shell build seconds + bundle delta, test count, boundary output, all-3-routes-resolve + wildcard-redirect proof, manifest entry count (6). Then STOP for lead review (service-builder runs the C4 WRITE-path proof next).
```

### meesell-angular-service-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-auth-frontend-session-2

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_06_auth_extraction.md (this plan — D36 consume-don't-rederive + D38 C4 WRITE-path smoke test, §9 auth WRITE go/no-go)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_03_onboarding.md (THE D22 C1-C5 contract — CONSUME it; SP03's C5 READ/LOGOUT test is the shape you INVERT for the C4 WRITE test)
- docs/plans/module_federation/MASTER_PLAN.md §2.5 (state sharing), §6.1 (auth token sharing), §7 R1 (auth singleton drift P0)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (AuthService as-built: providedIn:'root', _token/_user signals, setSession, logout, currentUser)

## Your mission
AFTER component-builder's Phase A+B is green. CONSUME the SP03 D22 contract (do NOT re-derive it). Prove the ONLY remaining unproven operation: the setSession WRITE path (C4). (1) Confirm @mesell/core is in the mfe-auth federation.config.js shared set with singleton:true (C1 — NOT skipped). (2) Author + run the C4 WRITE-path smoke test (the INVERSE of SP03's C5): start UNAUTHENTICATED (assert shell auth.isAuthenticated() === false; authGuard blocks /dashboard) -> navigate to /otp-verify (remote) -> submit OTP -> the remote calls auth.setSession('mock-token', {...}) -> ASSERT back in the shell auth.isAuthenticated() === true AND auth.currentUser()?.name correct (the remote's WRITE crossed into the shell's signal) -> ASSERT the post-setSession navigate to /dashboard now PASSES the shell authGuard. (3) Inspect the mfe-auth build output: assert NO duplicate auth.service chunk (C2 static proof).

## Acceptance criteria
- [ ] @mesell/core confirmed shared+singleton in mfe-auth federation.config.js (not skipped) — C1
- [ ] C4 WRITE-path smoke test authored + PASSING: unauth shell -> remote otp setSession -> shell isAuthenticated TRUE + currentUser correct -> guard now passes
- [ ] mfe-auth build output has NO duplicate auth.service chunk (C2 proof — single shared instance)
- [ ] the C4 WRITE proof recorded; together with SP03's C5 the full auth-state loop is CLOSED

## Hard constraints
- ZERO changes to libs/core/services/auth.service.ts (D36/D22 C2 — singleton via import-map, NOT a refactor)
- Do NOT re-derive the D22 contract (it is final in sub_plan_03_onboarding.md) — CONSUME it, add only the C4 WRITE proof
- Do NOT change the otp setSession simulation (mock-token — real OTP/JWT is Wave 6); do NOT add NgRx (CLAUDE.md D10); do NOT use BroadcastChannel for in-app sync (§2.5 cross-tab only)
- Do NOT touch the extraction (component-builder's work); do NOT touch backend/k8s/infra

## Final report format
@mesell/core singleton confirmation, the C4 WRITE-path smoke-test PASS/FAIL with assertion outputs, the no-duplicate-chunk proof, and the statement that the full auth-state loop (SP03 C5 READ/LOGOUT + SP06 C4 WRITE) is closed. If C4 FAILS: STOP — this is the migration's auth WRITE go/no-go; escalate to the lead, do NOT merge (P0 drift, MASTER_PLAN R1).
```

---

## Review + iteration protocol

### meesell-angular-component-builder (extraction)

- **Pre-approval checklist:** (a) history preserved on the 6 moved files; (b) login/signup/otp diffs empty except the AuthLayout import re-point + path context — NO logic change (incl. the setSession call + the resend-timer untouched); (c) all 3 pages import `AuthLayoutComponent` from `@mesell/composites`, grep shows NO relative `../../layouts/auth-layout`; (d) the otp `setInterval` resend-timer is byte-identical + clears on navigate-away; (e) deep `@mesell/ui-kit/*` imports preserved (not barrel-rewritten); (f) `federation.config.js` exposes all 3 + `@mesell/core` shared-singleton (not skipped); (g) the 3 route swaps are PUBLIC top-level with NO guard; (h) the `**` → login wildcard still resolves to the remote login; (i) manifest has SIX entries; (j) test count preserved; (k) shell build ≤90 s.
- **PR-template gate:** complete, no `<>`; build evidence, bundle delta, 360/1280 screenshots of all 3 pages (no visual change), a11y, boundary output, all-3-routes-render + wildcard-redirect proof.
- **Re-dispatch triggers:** "edited auth-page logic / the setSession call / the timer" → re-dispatch quoting the no-logic rule + D39; "left a relative auth-layout import" → re-dispatch with the failing grep + D39; "rewrote the otp timer to RxJS" → quote D39/D18; "barrel-rewrote the deep ui-kit imports" → quote the bundle landmine; "skipped @mesell/core in the remote config" → quote D36 C1 (the WRITE depends on it); "added a guard to a public auth route" → quote D37; "test count dropped" → the `apps/**/*.spec.ts` note.
- **Iteration cap: 3** → founder escalation.

### meesell-angular-service-builder (the C4 WRITE-path go/no-go)

- **Pre-approval checklist:** (a) `git diff libs/core/services/auth.service.ts` is EMPTY (no logic change — D22 C2); (b) the C4 WRITE-path smoke test exists + PASSES with visible assertion output (unauth → setSession → shell authenticated → guard passes); (c) the no-duplicate-`auth.service`-chunk proof attached; (d) `@mesell/core` confirmed shared-singleton (not skipped); (e) the contract was CONSUMED from SP03, not re-derived.
- **Re-dispatch triggers:** "modified AuthService" → quote D22 C2; "C4 not actually run / no assertion output" → re-dispatch demanding the live test result; "re-derived the D22 contract instead of consuming it" → quote D36; "changed the mock-token simulation" → quote the Wave-6 boundary; "used BroadcastChannel for in-app sync" → quote §2.5; "added NgRx" → quote CLAUDE.md D10.
- **HARD STOP (not a re-dispatch):** if the C4 WRITE-path test FAILS (the remote's `setSession` mutated a DUPLICATE AuthService instance, so the shell never sees authentication), this is the migration's auth WRITE go/no-go. HALT, do NOT merge, escalate to the founder. A failed WRITE contract on the LAST remote means the federated auth story is incomplete and blocks the SP07 cutover (MASTER_PLAN R1 P0).
- **Iteration cap: 3** → founder escalation.

---

## Acceptance gate

When every box is `[x]`, `feature/mfe-auth/integration` is ready for the founder's develop PR.

- [ ] PR (`feature/mfe-auth/frontend` → integration) merged by Frontend Lead (squash)
- [ ] `ng build mfe-auth` GREEN — produces `remoteEntry.json` exposing all THREE components (record seconds)
- [ ] Shell `pnpm build` GREEN and **≤ 90 s** (CLAUDE.md Decision 12 / Stop Condition) — seconds + bundle delta recorded
- [ ] `pnpm test` total == **prior baseline, 0 failing, 0 skipped** — new failure or count drop blocks merge (R-SP6-3)
- [ ] **Boundary grep clean** — no new PrimeNG leak from `apps/mfe-auth/`
- [ ] **All 3 PUBLIC routes resolve:** `/login` → `LoginComponent`, `/signup` → `SignupComponent`, `/otp-verify` → `OtpVerifyComponent`, all render in the shell outlet with NO guard (pre-auth reachable)
- [ ] **AuthLayout consumed from `@mesell/composites` (D39/D21):** all 3 pages import it from the shared lib; NO dangling relative `../../layouts/auth-layout` import anywhere
- [ ] **OTP resend-timer preserved (D39/D18):** the `setInterval` countdown is byte-identical + clears on navigate-away (no orphaned timer)
- [ ] **The `**` → login wildcard redirect** still resolves to the remote `LoginComponent`
- [ ] **AuthService singleton WRITE-path smoke test (D38 C4) PASSES** — the migration's auth WRITE go/no-go: unauth shell (guard blocks `/dashboard`) → remote `otp-verify` `setSession` → shell `isAuthenticated()` true + `currentUser()` correct → navigate to `/dashboard` now passes the guard. **A FAIL halts the cutover (P0 drift).**
- [ ] **No duplicate `auth.service` chunk** in the `mfe-auth` build output (D22 C2 static proof)
- [ ] **The full auth-state loop is CLOSED:** SP03 C5 (shell writes → remote reads → remote logout clears shell) + SP06 C4 (remote writes → shell reads) together prove bidirectional singleton sharing
- [ ] **SIX remotes coexist** in the manifest — the COMPLETE MASTER_PLAN §2.2 topology (`mfe-pricing`, `mfe-export`, `mfe-onboarding`, `mfe-dashboard`, `mfe-catalog`, `mfe-auth`). All extractions DONE.
- [ ] FOUNDER-FLAGs: none new; D9 + D14 inherited (SP07 resolves); D21 + D33 inherited (already merged)
- [ ] Infra deploy memo filed (D40 — sixth/final remote + the public-auth-pages CSP escalation for SP07); board inter-lead row added
- [ ] `feature_board_frontend.md` row = MERGED; STATUS_FRONTEND.md appended; `sub_plan_06_auth.md` written
- [ ] **Founder approval** on `feature/mfe-auth/integration` → `develop` (founder's gate, NOT the lead's)

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SP6-1 | **`setSession` WRITE-path singleton drift (MASTER_PLAN R1 P0)** — the `mfe-auth` remote bundles its OWN `@mesell/core`, so the OTP page's `setSession` mutates a DUPLICATE AuthService; the shell never sees authentication and the user is stuck unauthenticated after a "successful" OTP. | Low (5 remotes already proved sharing) | **P0** | D36 C1: `@mesell/core` MUST be shared+singleton (not skipped) — verified by service-builder. The D38 C4 smoke test PROVES the WRITE crosses the boundary; the no-duplicate-chunk inspection PROVES it statically. SP03's C5 already proved READ/LOGOUT across 3 remotes, so the mechanism is battle-tested — but the WRITE direction is exercised for the FIRST time here. A FAIL halts the cutover. |
| R-SP6-2 | **AuthLayout dangling import** — the auth pages still import the OLD relative `../../layouts/auth-layout` (if SP03 did NOT re-point the shell auth pages) → the remote build breaks (it cannot reach `../../layouts/`). | Medium | High | D39: SP06 explicitly verifies + re-points all 3 to `@mesell/composites` (SP03 D21 promoted it). Grep before build; the build fails immediately on a dangling import. SP03's optional re-point may have already done this — verify, don't assume. |
| R-SP6-3 | **Spec-discovery regression** — moving the 3 auth specs into `apps/mfe-auth/`; relies on SP01's `apps/**/*.spec.ts` glob. | Medium | High | RE-CONFIRM the glob; assert exact total count preserved; drop = hard reject. (SP01 §9.A item 6.) |
| R-SP6-4 | **OTP resend-timer orphaned across the boundary** — the `setInterval` countdown is not cleared when the user navigates away from the remote `/otp-verify`, leaking a timer. | Low | Medium | D39/D18 (SP02 precedent): the timer + `clearInterval` move UNCHANGED; the federation boundary does NOT change `ngOnDestroy`. §9 verifies navigate-away clears it. SP02 already proved this for the export polling timer. |
| R-SP6-5 | **OTP spec can't resolve AuthService after the move** — `otp-verify.component.spec.ts` provides/mocks `AuthService`; after relocation the `@mesell/core` import or TestBed provider may not resolve under the new project's tsconfig. | Medium | Medium | The `@mesell/core` alias resolves workspace-wide (SP0). Verify the spec's TestBed still provides AuthService + passes; if it hard-codes a relative path, rewrite to `@mesell/core`. Caught by the preserved-count + green-tests gate. (Same as SP03 R-SP3-5.) |
| R-SP6-6 | **Public-auth-pages CSP gap in staging/prod** — `/login`/`/signup`/`/otp-verify` are public + pre-auth; without the SP07 CSP `script-src https://remotes.mesell.xyz` (C-CSP-1), a new visitor's `/login` is a blank page (the remote never loads). Combined with landing (SP04 R-SP4-5), the TWO most critical entry points both depend on the SP07 CSP. | Low (dev) / High (prod) | High | D40 + inherited D14: dev has NO CSP, validate on dev. The public-auth CSP escalation is recorded in the infra memo + flagged to SP07 (C-CSP-1) alongside the landing escalation — together they are the highest-stakes CSP surfaces (every unauthenticated visitor hits one). Do NOT ship `mfe-auth` to staging/prod until CSP is authored + smoke-tested. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-3` (night-run master-session dispatch) | Initial authoring of Sub-Plan 06 — `mfe-auth` (F2 login + F3 signup + F4 otp-verify), the LAST and riskiest extraction. Grounded in the POST-SP0 integration-branch reality (`e51761b`): all 3 pages are PUBLIC top-level (no guard); all 3 import `AuthLayoutComponent` relatively (SP03 D21 promoted it to `@mesell/composites` — SP06 verifies/re-points); ONLY otp-verify touches AuthService (`setSession('mock-token',...)` WRITE inside `onSubmit` after a `setTimeout`, + a `setInterval` resend-timer); deep `@mesell/ui-kit/*` imports. D36–D40 (CONSUME the SP03 D22 contract, add ONLY the C4 WRITE proof — do NOT re-derive D36; three public single-component exposes D37; the C4 `setSession` WRITE-path smoke test = the auth WRITE go/no-go D38, the inverse of SP03's C5 READ/LOGOUT; AuthLayout-from-composites + otp-timer-preserved D39; Option-C sixth/final remote D40 = the COMPLETE 6-remote topology). Together SP03 C5 (READ/LOGOUT) + SP06 C4 (WRITE) close the full bidirectional auth-state loop. The §5-row-6 dependency ("singleton proven across ≥3 remotes") is satisfied by SP03+SP04+SP05. 6 risks incl. the WRITE-path drift (R-SP6-1 P0), the AuthLayout dangling import (R-SP6-2), and the public-auth CSP gap (R-SP6-6, escalated to SP07 alongside SP04's landing). No new FOUNDER-FLAG (D9/D14/D21/D33 inherited). No LOCKED-doc amendment. After SP06, all extractions are DONE and SP07 (cutover + hardening + the §5.1 compliance audit) is the only remaining sub-plan. Awaits founder approval to EXECUTE; gated on SP01–SP05 merged + infra C-CI-1. |
