# Memory — meesell-angular-service-builder

## Agent Identity
Angular 18 service specialist for MeeSell. Owns services + RxJS state + HttpClient + JWT interceptor + auth guards + typed ApiClientService + typed models. Decentralized memory ecosystem.

## Session: F-001 federation subpath fix (2026-06-13)

**Branch/commit:** fix/frontend/f001-federation-subpath @ 3ae9fd3
**PR:** #203 (→ develop, IN REVIEW at merge-gate)

### Root cause (F-001)
- Native Federation registers ONE import-map key per shared package ROOT. Subpath imports
  (e.g. @mesell/ui-kit/providers, @mesell/ui-kit/input/input.component) compile fine via
  tsconfig wildcard alias but fail at runtime in the browser — es-module-shims cannot resolve
  them because no subpath key exists in the import map.
- @primeuix/themes/aura is imported INSIDE libs/ui-kit/theme.ts (inside the shared chunk).
  @primeuix/themes root is in the import map but /aura is not → second crash on chunk load.

### Fix (a)+(c) per SPEC
- (a) Rewrote all @mesell/ui-kit/<subpath> imports → barrel root @mesell/ui-kit. 4 files touched.
  libs/ui-kit/index.ts was already complete — zero new exports added.
- (c) Added @primeuix/themes + @primeuix/themes/aura to skip[] in all 7 federation configs.
  libs/ui-kit/theme.ts NOT touched — Aura import stays, bundles into _mesell_ui_kit.js (204 kB).

### Evidence
- Grep proof: 3 greps all return empty
- remoteEntry.json proof: 161 shared entries, 0 @primeuix entries in shell + mfe-auth + mfe-onboarding
- Boot smoke: 6/6 PASS (headless chromium 148.0.7778.96), zero resolveErrors

### Key learnings

**BARREL-ONLY import rule (P0 for federation):**
  RIGHT: import { MeeCardComponent } from '@mesell/ui-kit';
  WRONG: import { MeeCardComponent } from '@mesell/ui-kit/card/card.component';
  Subpaths compile via tsconfig wildcard but fail at runtime in the browser (no import-map key).

**build-green != boot-green for federation:**
  esbuild resolves tsconfig aliases at compile time. Runtime failure is browser-only (es-module-shims).
  Always run a headless browser smoke after federation changes.

**playwright on macOS arm64:**
  PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers npx playwright install chromium
  Executable: /tmp/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell
  Install playwright package in /tmp/smoke-runner (NOT in frontend/ — not a frontend dep)

**pnpm-workspace.yaml allowBuilds fix (PR #203):**
  Placeholder values were in develop until PR #203. Now all 5 entries = true.
  DO NOT overwrite this file on branch checkout — already correct.

### Re-spin evidence session (2026-06-13) — PR #203 prior evidence was FALSE PASS

**FALSE PASS ANATOMY:**
- Prior smoke served `dist/` with `python -m http.server` — NO SPA history-fallback
- `/login` and `/profile` returned Python 404 page (not Angular) → screenshots showed "Error response / Error code: 404"
- `body.length > 0` and `zeroSpecifierErrors` passed trivially on 404 bodies (Angular never ran)

**CORRECT SERVING PATTERN for SPA smoke:**
- Use `ng serve <project> --port <N> --no-open` for each app
- native-federation builder provides proper SPA history-fallback (all paths → index.html)
- Verify: `curl http://localhost:4200/login` MUST return 200 (not 404) before driving browser
- Wait for each remote's `remoteEntry.json` → 200 before running assertions

**PORT MAP (confirmed from angular.json architect.serve-original.options.port):**
- shell (frontend): 4200 | mfe-pricing: 4201 | mfe-export: 4202 | mfe-onboarding: 4203
- mfe-dashboard: 4204 | mfe-catalog: 4205 | mfe-auth: 4206

**Playwright global installation pattern:**
- `npx playwright install chromium` → downloads headless shell to ~/Library/Caches/ms-playwright/
- `npm install -g playwright` → installs globally
- Run script via: `NODE_PATH=/usr/local/lib/node_modules node smoke-script.js`
- `/Applications/Google Chrome.app` symlink may be broken — always re-install via npx

**Worktree + node_modules pattern:**
- Isolated worktree has NO node_modules — `ln -s /main/project/frontend/node_modules worktree/frontend/node_modules`
- Verify main project and fix branch are at compatible angular.json versions

**Local develop vs origin/develop divergence trap:**
- Local `develop` can be N commits behind `origin/develop`
- Check: `git log HEAD..origin/develop | wc -l`
- Fix: apply files from fix branch via `git show <sha>:<path> > <path>`
- If app.config.ts imports jwtInterceptor/refreshInterceptor from @mesell/core → need origin/develop version of libs/core/index.ts

**F-001 smoke re-run results (6/6 PASS, commit f35ea3d):**
- / @ 360+1280px: RemoteFailureComponent (cloud_off/Retry) — D12 fallback, shell booted
- /login @ 360+1280px: real LoginComponent — "Welcome back", mee-input, Continue button rendered
- /profile @ 360+1280px: authGuard fired → redirect to /login → LoginComponent (proves guard + singleton cross)
- Zero "Unable to resolve specifier" across all routes/widths
- @primeuix/themes absent from mfe-auth + mfe-onboarding + shell remoteEntry.json
- PR #203 updated; comment added: https://github.com/Mugunthan93/mesell/pull/203#issuecomment-4697814639

## Session: auth-refresh-stampede fix (2026-06-18)

**Branch/commit:** fix/auth-refresh-stampede @ 26a32ba
**PR:** #281 (→ develop, IN REVIEW — coordinator merge-gate step 3)
**Worktree:** /private/tmp/mesell-wt/auth-stampede

### Root cause (confirmed by coordinator SPEC)
- THREE callers called authApi.refresh() independently: refreshInterceptor (gated),
  _doSilentRefresh (ungated), bootstrap() (ungated).
- Rotating refresh cookies → 2nd+ concurrent refresh uses a revoked cookie → 401 cascade.
- Secondary defects: D-A (_refreshToken$ never reset after success), D-B (_isRefreshing
  never reset on logout), D-C (_doSilentRefresh swallowed 401 as EMPTY), D-D (Math.max(…,0)
  allowed 0ms delay → immediate refire loop on tiny TTLs).

### Fix (all 4 secondaries fixed)
- AuthService.refreshShared(): ONLY path to POST /auth/refresh. Single-flight Observable
  stored in _refreshInFlight. shareReplay({bufferSize:1, refCount:false}) so late subscribers
  get the cached result. finalize() clears _refreshInFlight (D-A/D-B fixed by construction).
- AuthService.forceLogout(): logout-once guard (_loggedOut bool). navigate(['/login']) ONCE.
  Subsequent calls no-op. setSession() resets _loggedOut for new login windows.
- _doSilentRefresh catchError: status===401 → forceLogout(); other errors swallowed (D-C fix).
- scheduleRefresh delay: skew=min(30,expiresIn*0.1), delayMs=max((expiresIn-skew)*1000, 5000).
  MIN_REFRESH_DELAY_MS=5000 prevents 0ms loop (D-D fix).
  IMPORTANT: changed behavior — expiresIn=60 now fires at 54s (was 30s). Specs updated.
- refreshInterceptor: thin — delegates to auth.refreshShared(), calls auth.forceLogout() on
  refresh-401. Removed module-level _isRefreshing/_refreshToken$ entirely.

### Test patterns
- Tests (a)-(g) use lightweight mock AuthService with refreshShared as vi.fn() routing
  to HttpClient so controller.expectOne('/api/v1/auth/refresh') still works.
- Tests (d),(h),(i),(j),(k) use setupReal() with real AuthService + real AuthApiService —
  REQUIRED to exercise actual shareReplay single-flight behavior. Mock AuthService cannot
  replicate shareReplay semantics (each vi.fn() call creates a new Observable).
- afterEach: only controller.verify() — NOT vi.useRealTimers() (no fake timers in interceptor specs).
- Auth service specs: provideRouter required now (AuthService injects Router for forceLogout).

### Key learnings
**Mock vs real for single-flight tests:** If your test asserts "N concurrent callers → 1 HTTP call",
  you MUST use the real service. A vi.fn() mock creates a new Observable per call — no sharing.
  Only the real refreshShared() with shareReplay provides the single-flight guarantee.

**shareReplay({refCount:false}) hazard:** refCount:true would re-subscribe the source when ref
  count drops to 0 between emission and a late subscriber — producing a second HTTP call.
  refCount:false keeps the multicast alive until finalize() clears it. This is the correct
  pattern for a refresh gate.

**finalize() placement:** finalize() must be OUTSIDE the shareReplay (piped after). If placed
  inside, it fires for each subscriber's teardown, not once for the multicast source.

**forceLogout() vs logout():** forceLogout = "involuntary logout, navigate once"; logout = "user
  pressed logout button, caller handles navigation". Components calling explicit logout action
  should call logout(); auth infra cascade paths call forceLogout().

**D-D delay formula change is observable in specs:** Old formula (expiresIn-30)*1000 floor 0 gave
  30s for expiresIn=60. New formula gives 54s. All existing timer-based specs needed update.

**Build note:** ng build frontend exits 0 for core lib changes. The "ERRR Could not find xlsx"
  is a pre-existing native-federation warning (xlsx is intentionally skipped dep). Not a new error.

## Session: pricing-fe-rework slice 1 (2026-06-18)

**Branch/commit:** feat/pricing-fe-rework @ eca463e
**PR:** #287 (→ develop, open — do NOT merge, slices 2+3 follow)
**Worktree:** /private/tmp/mesell-wt/pricing-fe-rework

### Contract confirmed (backend fd4331d / PR #285 §12.M)

PriceCalcRequest: meesho_price (primary), input_cost, commission_pct (default "4"),
  return_rate_pct (default "0"), mrp (optional), override_shipping, override_logistics_fee,
  override_fixed_fee, override_gst_pct, override_tcs_pct, override_tds_pct.
  DEAD: target_margin_pct.

PriceCalcResponse: mrp (nullable), meesho_price, wdrp_price, input_cost, commission_pct,
  referral_commission, shipping_charge, logistics_fee, fixed_fee, gst_pct, gst_on_fees,
  tcs, tds, return_rate_pct, rto_expected_loss, total_deductions, estimated_payout,
  estimated_payout_wdrp, profit, margin_pct, markup_pct, alerts[], calculated_at.
  DEAD: seller_price, commission_amount, gst_amount, profit_pct.

Alert codes: NEGATIVE_PAYOUT | LOW_MARGIN | SHIPPING_DOMINATES.
  DEAD: HIGH_MRP_MULTIPLIER, THIN_PROFIT.
ALERT_MESSAGES keys: pricing.alert.negative_payout / .low_margin / .shipping_dominates.
422 path: DEAD (§12.M (4)). PriceCalcCommissionMissingError DELETED.

### Key learnings

**Forward estimator contract shift:** §12.E was backward (input_cost+target_margin → mrp output).
  §12.M is forward (meesho_price input → estimated_payout output). Model contracts are INVERSE.
  component forms must be rebuilt top-to-bottom for this flip.

**Pre-existing TS errors block ng test on origin/develop:** The worktree off origin/develop
  has pre-existing TS errors in mfe-auth (errorMessage signal), mfe-onboarding, shell specs.
  These errors are from modified working-tree files (shown in git status) that haven't been
  pushed to origin. Pure-function pricing specs still run via bare vitest run.
  Service specs (with @mesell/core) require ng test runner for tsconfig path resolution.
  Strategy: confirm 0 mfe-pricing errors via tsc --noEmit + run component spec via vitest.

**pricing.component.spec.ts must be updated in slice 1, not slice 2:**
  The component spec imports model types directly. Removing PriceCalcCommissionMissingError
  from the model breaks the spec compile immediately — must fix in the same slice as the model.
  Pattern: always update the spec that imports the model IMMEDIATELY when the model changes.

**TODO(slice-2) casting pattern for dead switch cases:**
  When a union case is removed from a type (commission_missing deleted from PriceCalcErrorShape),
  TypeScript raises an error on any switch case that matches it. Temporary fix until slice 2:
  cast the dead case label: `case 'commission_missing' as 'validation':`. This compiles but
  is clearly marked for deletion. Do not leave this in for longer than one slice.

**vitest vs ng test resolution:** bare `vitest run <file>` resolves relative + rxjs imports
  but NOT tsconfig path aliases (@mesell/*). ng test resolves everything via tsconfig.
  For specs that only import from local files + standard libs: use bare vitest.
  For specs that import @mesell/core ApiClient: must use ng test (fails when suite-wide TS errors block build).

## Session: boot-smoke CI gate — confirmed GREEN (2026-06-14)

**Branch:** ci/frontend/boot-smoke @ 88e6262
**PR:** #213 (→ develop, READY FOR FOUNDER MERGE — D1 gate)
**CI Run:** 27477214257 — conclusion: success
**URL:** https://github.com/Mugunthan93/mesell/actions/runs/27477214257/job/81218610137

### Root cause of original hang (CI run 27476389960)
- `ng build --configuration development` ALSO hangs on NF cold-start (~31 min before timeout).
  The stall is NOT production-only: NF's "Preparing shared npm packages" runs in BOTH dev and
  production build modes. The `--configuration development` fix was NOT sufficient.
- `ng serve` (webpack-dev-server) avoids this stall entirely: it defers the shared-package
  scan to lazy first-request rather than doing it upfront at build time.

### Lockfile drift: macOS pnpm vs Linux CI (LOCKED PATTERN)
- Running `pnpm install --lockfile-only` on macOS (pnpm 11.5.2) injects `esbuild@0.27.3` as
  optional peer of webpack into 15+ Angular build-webpack snapshot key strings.
  Linux CI does not include this peer → frozen-lockfile install fails with hash mismatch.
- RULE: NEVER regenerate pnpm-lock.yaml on macOS for this project. Always restore
  origin/develop baseline, then HAND-PATCH the 3 sections (importers/packages/snapshots)
  for any new devDep additions.
- Validated: lockfile surgical patch (19 additions, 0 drift removals) → `pnpm install --frozen-lockfile`
  SUCCESS on CI Linux runner.

### CI boot-smoke performance achieved (ng serve path)
- All 7 dev servers ready in ~2 min (step 9: 19:48:27 → 19:50:24 UTC)
- Total job time: 4m 10s (was 90m+ timeout → conclusion: cancelled)
- Timeout headroom: 10m 50s remaining out of 15m budget
- Readiness gate: 480s max budget, actual: ~120s

### start-all.mjs pattern (validated)
- Zero-dependency Node.js script, 190 lines
- Spawns 7 named pnpm scripts (start:shell, start:mfe-*) via child_process.spawn
- Per-line ANSI prefix by server label for CI log readability
- SIGTERM → 3s grace → SIGKILL teardown on SIGINT/SIGTERM
- Path: frontend/tools/dev/start-all.mjs

### setsid + PGID pattern (validated on GitHub Actions Ubuntu)
- `setsid pnpm run start:all > /tmp/start-all.log 2>&1 &` creates new process group
- Store `$!` → that IS the PGID leader
- Teardown: `kill -- -"$PGID"` kills all children + parent atomically
- Fallback `kill "$PGID"` handles edge cases

### Boot smoke readiness gate assertions
- Poll `localhost:4200/` (root) for shell — NOT /index.html
- Poll `localhost:420{1..6}/remoteEntry.json` for each remote
- Assert `curl localhost:4200/login` → HTTP 200 (SPA history fallback proof)
- Playwright test step unchanged from original harness

### Hand-off
PR #213 is waiting for founder D1 merge. Do NOT merge without founder approval.

## Session: federation-version-pin (2026-06-20)

**Branch/commit:** fix/federation-shared-version-pin @ 38c7934 (PUSHED)
**Worktree:** /private/tmp/mesell-wt/fed-version-pin

### Root cause (BUG from master-session memory)
@mesell/* libs had NO package.json → version="" in every remoteEntry.json → NF cannot dedup
by version → each remote loaded its own @mesell/core instance → second instance has null
in-memory token → authGuard redirects to /login on shell→remote navigation.

### Fix applied
1. Added libs/{core,env,composites,ui-kit}/package.json with version "1.0.0".
2. Added explicit mesellShared overrides in all 7 federation.config.js:
   singleton:true, strictVersion:true, requiredVersion:'1.0.0', version:'1.0.0'.

### NF framework limitation (critical learning — P0)
@mesell/* workspace libs are processed via sharedMappings (tsconfig path aliases), NOT via
the `shared` npm-packages pipeline. The function bundle-exposed-and-mappings.js in
@softarc/native-federation@3.5.5 HARDCODES:
  requiredVersion: '',
  singleton: true,
  strictVersion: false,
for ALL sharedMappings entries regardless of federation.config.js shared{} overrides.

CONSEQUENCE: strictVersion and requiredVersion CANNOT be set via config for workspace libs.
The federation.config.js mesellShared entries for strictVersion/requiredVersion are silently
ignored — they only affect npm packages in node_modules, not workspace path-aliased libs.

WHAT WORKS: version IS populated from libs/*/package.json (package-info.js reads it).
singleton:true IS passed through from shareAll() defaults.

DEDUP MECHANISM: NF runtime deduplicates by packageName + version + singleton=true.
With ALL 7 remotes showing v=1.0.0 + singleton=true, the shell's @mesell/core instance
wins and remotes reuse it → single AuthService instance → no logout on nav.

### Verification output
All 7 remotes: v=1.0.0 sing=True strict=False req='' (HTTP 200).
strictVersion=false and req='' are framework-imposed, NOT a bug in this fix.
The dedup works via version match — strict is irrelevant when versions ARE consistent.

### Sequential build pattern (memory-lean, 8GB machine)
  cd /Users/mugunthansrinivasan/Project/mesell/frontend
  for app in frontend mfe-pricing mfe-catalog mfe-export mfe-onboarding mfe-dashboard mfe-auth; do
    ./node_modules/.bin/ng build $app --configuration development 2>&1 | tail -5
    pkill -9 -f "esbuild --service" 2>/dev/null
  done
  Kill ALL stale serve.js PIDs before restart (kill -9 all 4200-4206 PIDs).
  Restart: node tools/boot-smoke/serve.js dist/<app>/browser <port> &

### Port map (confirmed)
shell:4200 | mfe-pricing:4201 | mfe-export:4202 | mfe-onboarding:4203
mfe-dashboard:4204 | mfe-catalog:4205 | mfe-auth:4206

### Credential fix for worktree push
Worktrees don't inherit global gitconfig. Fix:
  git -C <worktree> config credential.https://github.com.helper '!/opt/homebrew/bin/gh auth git-credential'
  git -C <worktree> push origin HEAD:<branch>

## Session: razorpay-dev-mock FE model (2026-06-20)

**Branch/commit:** feature/razorpay-dev-mock @ b3d60f0
**Worktree:** /tmp/mesell-wt/razorpay-dev-mock
**Spec:** docs/plans/features/razorpay-integration/DEV_MOCK_MODE_SPEC.md §4.2

### Change summary
Added `mock?: boolean` (optional) to the `BillingCheckout` interface in
`frontend/apps/mfe-billing/src/app/billing.model.ts` (line 68, after `tier`).

### Why optional (not required)
Backend sets `mock: bool = Field(default=False)` — it is always present on the wire but
defaults False. TypeScript optional (`?`) makes existing test fixtures that omit the field
still structurally valid, avoiding spec churn. A non-optional `boolean` would also work
since the backend always includes it, but optional is more defensive for any mock stubs.

### DTO mapping: none needed
`BillingApiService.subscribe()` uses `api.post<BillingSubscribeResponse>(...)` — raw typed
generic pass-through. No explicit DTO transform exists in the service. `mock` flows from
JSON → typed interface automatically. RULE: when adding a field to a billing model, always
grep the service for explicit `{ checkout: { ... } }` construction or `map()` operators
that would drop the new field. In this case: none found.

### tsc pattern for worktree (no node_modules)
Worktrees have no node_modules. Pattern: `ln -s /main/project/frontend/node_modules worktree/frontend/node_modules`
Then: `cd worktree/frontend && node_modules/.bin/tsc --noEmit -p apps/<mfe>/tsconfig.app.json`

### ng test isolation problem on 8GB machine
`ng test mfe-billing` builds entire workspace → hits pre-existing mfe-pricing spec TS errors
(TS2352 / TS2367 — confirmed pre-existing from pricing-fe-rework session). Cannot be isolated.
WORKAROUND: use `vitest run --globals <spec-file>` for specs that only use local imports.
Specs needing TestBed (Angular DI / jsdom / `window`) or `@mesell/*` path aliases MUST use
`ng test` and cannot be run safely bare. For model-only changes, confirm clean via:
  1. tsc --noEmit on tsconfig.app.json (compile gate)
  2. tsc --noEmit on tsconfig.spec.json (spec type gate, filter known pre-existing)
  3. vitest run on any pure-function spec that imports from the changed model

### Hand-off
Component builder next: add `if (resp.checkout.mock)` branch in plans.component.ts
`subscribe()` next: handler per DEV_MOCK_MODE_SPEC.md §4.3.

## Session: otp-verify-pending-phone — AuthService pendingPhone signal (2026-06-20)

**Branch/commit:** fix/otp-verify-pending-phone @ e7e919c
**Worktree:** /tmp/mesell-wt/otp-fix

### Root cause (diagnosed by coordinator SPEC)
history.state is wiped by Native Federation's full-document reload on first remote fetch.
otp-verify.component.ts ngOnInit (L176) hard-redirects to /login when state.phone is missing.
Fix: carry the pending phone in an in-memory signal on AuthService (the existing root singleton)
so it survives across the step navigation. FE-D5: never persisted.

### API added to AuthService

Location: `frontend/libs/core/services/auth.service.ts`
Private field: `private readonly _pendingPhone: WritableSignal<string | null> = signal<string | null>(null);`

Public methods:
  - `setPendingPhone(phone: string): void` — call in login.component.ts after OTP send success,
    before router.navigate(['/otp-verify'])
  - `pendingPhone(): string | null` — call in otp-verify.component.ts ngOnInit instead of
    history.state?.phone; returns null when no phone is waiting
  - `clearPendingPhone(): void` — call in otp-verify.component.ts after consuming the phone
    (success + ngOnDestroy) to prevent stale state

Barrel export: no change needed — `export { AuthService }` in `frontend/libs/core/index.ts`
already re-exports all public methods. Components import via `@mesell/core` alias as always.

CRITICAL design choices:
  - DOES NOT clear on logout() or forceLogout() — the component owns the lifecycle.
    A forceLogout during OTP verification must not lose the phone before the component
    can redirect cleanly. The component calls clearPendingPhone() in ngOnDestroy.
  - WritableSignal<string|null> not BehaviorSubject — matches the existing signal style
    on _token and _user. Consistent with Decision 10 (no NgRx; signals for component-local
    reactive state; BehaviorSubject for shared Observable streams — phone is not a stream).
  - This is strictly in-memory. Adding a signal field to AuthService is zero-cost and
    cheaper than a new dedicated PendingAuthService (avoided the extra barrel export + DI token).

### Spec coverage (6 new tests, auth.service.spec.ts)
- pendingPhone() is null by default
- setPendingPhone sets; pendingPhone() returns it
- clearPendingPhone resets to null
- setPendingPhone overwrites a previous value
- pendingPhone does NOT clear on logout()
- pendingPhone does NOT clear on forceLogout()

### tsc results
- mfe-auth tsconfig.app.json: EXIT 0
- shell tsconfig.app.json: EXIT 0
- workspace tsconfig.spec.json: 0 NEW errors (only pre-existing mfe-pricing TS2352/TS2367)
- ng test: blocked by same pre-existing mfe-pricing build error (known, unrelated)

### Component-builder hand-off spec (for next dispatch)
login.component.ts:
  1. Inject AuthService (already injected).
  2. After OTP send API succeeds (before navigating), call: `this.auth.setPendingPhone(this.phoneForm.value.phone)`.
  3. Then: `this.router.navigate(['/otp-verify'])`.

otp-verify.component.ts:
  1. Inject AuthService (already injected).
  2. In ngOnInit, REPLACE: `const phone = this.route.snapshot.data?.['phone'] ?? history.state?.phone`
     WITH: `const phone = this.auth.pendingPhone();`
  3. If phone is null/empty → redirect to /login (existing behaviour preserved).
  4. Else → proceed with OTP verify using the phone.
  5. After consuming phone (on success path): call `this.auth.clearPendingPhone()`.
  6. In ngOnDestroy (or DestroyRef): call `this.auth.clearPendingPhone()` to handle back-nav.
