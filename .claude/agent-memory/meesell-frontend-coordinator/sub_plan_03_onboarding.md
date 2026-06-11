# Sub-Plan 03 — mfe-onboarding: the FINALISED AuthService singleton contract (D22 C1–C5)

**Status:** EXECUTED 2026-06-11 (Wave 1 parallel, concurrent with SP02). Group PR #67 squash `e2035330`
(frontend→integration). Founder-gate PR #68 (integration→develop) OPEN. SP01 pilot was on develop (#53, bb37f5f).
**This is THE artefact SP04 (dashboard) / SP05 (catalog) / SP06 (auth) consume — do NOT re-derive the contract.**

## What shipped
- `features/account/onboarding` + `features/profile` → `apps/mfe-onboarding/` Native Federation remote.
- FIRST multi-expose remote (D20): ONE remoteEntry exposing `./OnboardingComponent` + `./ProfileComponent`.
- FIRST remote to inject AuthService across the boundary (profile: `currentUser()` ×4 + `onLogout()→logout()`).
- AuthLayout PROMOTED `layouts/auth-layout` → `libs/composites/auth-layout` + barrel (D21, founder RULED APPROVED).
  All 4 relative consumers re-pointed to `@mesell/composites` (onboarding + shell login/signup/otp-verify).

## THE D22 AuthService singleton contract — FINALISED (verbatim, for SP04/05/06)
AuthService is `@Injectable({ providedIn: 'root' })`, signals `_token`/`_user`, computed `isAuthenticated`/`currentUser`,
`setSession()`/`logout()`/`getToken()`. RETAINED unchanged (C2 — no decorator/logic refactor).

- **C1 — `@mesell/core` MUST be `shared + singleton:true` in EVERY remote that injects AuthService.** Verified in
  the mfe-onboarding remoteEntry: `@mesell/core` → `_mesell_core-*.js`, singleton true. NOT skipped.
- **C2 — singleton via import-map sharing, NOT a decorator change.** Static proof: the AuthService class impl exists
  in EXACTLY ONE chunk (`_mesell_core-*.js`); ProfileComponent imports `from '@mesell/core'` externally; NO duplicate
  `auth.service` chunk in the remote. (Before the fix, AuthService was INLINED into ProfileComponent — see THE FIX.)
- **C3 — signals cross the boundary natively.** Remote reads `auth.currentUser()` = shell's live value; remote
  `logout()` mutates the shell's signal. No serialization, no BroadcastChannel (that's cross-TAB only, §2.5).
- **C4 — `setSession` owned by SP06 (mfe-auth) WRITE path; `logout` callable from anywhere.** SP03 proves READ + LOGOUT.
  SP06 adds ONLY the `setSession` WRITE proof (inverse of C5).
- **C5 — the runtime smoke test = the migration's AUTH GO/NO-GO. PASSED.** Spec:
  `apps/mfe-onboarding/src/app/auth-singleton.smoke.spec.ts`. Asserts: shell `setSession(token,user)` →
  remote ProfileComponent renders `currentUser().name` AND `comp.auth === shellAuth` (one instance) →
  remote `onLogout()` → shell `isAuthenticated()` false + `currentUser()` null + `getToken()` null →
  `authGuard` returns a `/login` redirect `UrlTree` (blocks). Plus C5b: a 2nd `inject(AuthService)` === the same instance.

## THE FIX — R-SP3-1 (P0 auth-singleton drift) root-caused + resolved (CRITICAL forward contract)
**Symptom:** initial build had `@mesell/core` ABSENT from the remote's `shared[]` and the AuthService class
INLINED into `ProfileComponent-*.js` → the remote would get its OWN AuthService instance (drift) → C5 would FAIL.
**Root cause (traced in `@softarc/native-federation` source):** `features.ignoreUnusedDeps:true` runs a Sheriff
(`@softarc/sheriff-core` `getProjectData`) import-graph analysis rooted at the project's `src/main.ts`, then
`removeUnusedDeps` prunes any shared-mapping whose files aren't in that graph. My `main.ts` bootstrapped
`OnboardingComponent` ALONE; onboarding does NOT import `@mesell/core` (only profile does) → core pruned → inlined.
**FIX:** `main.ts` must reference EVERY exposed component (route to BOTH OnboardingComponent + ProfileComponent),
so profile → `@mesell/core` stays in the analysis graph → core stays shared+singleton. ZERO AuthService change.
**FORWARD RULE for SP04/05/06 (and any remote sharing a lib only some exposes consume):** the remote's `main.ts`
MUST reference ALL exposed components/routes, else `ignoreUnusedDeps` silently drops a shared lib that only one
expose uses → inlined → singleton drift. ALWAYS re-run the C2 static check (single `_mesell_core` chunk, no inline)
+ C5 after building any AuthService-consuming remote. SP05 (Routes-array expose) must keep its full route
component set reachable from main.ts. Two non-fixes I ruled out: (a) `@mesell/core/*` tsconfig wildcard — its
subdirs (services/, guards/) have no index.ts so it resolves to ZERO usable mappings; (b) `ignoreUnusedDeps:false`
— breaks because it then tries to share `@mesell/design-tokens` (a CSS folder, no entryPoint) → "Could not resolve".

## Why ui-kit/composites shared but core didn't (the asymmetry, for diagnosis reuse)
The 3 barrels (ui-kit/composites/core) have identical tsconfig mapping shape (`@mesell/X` → `libs/X/index.ts`).
The `/*` wildcards all resolve to ZERO usable mappings (subdir barrels lack index.ts → "[shared-mappings] Internal
lib does not contain an entryPoint" warns ×N — benign, IGNORE). So sharing is decided PURELY by `findUsedDeps`:
a barrel `libs/X/index.ts` is "used" iff its `index.ts` is in the Sheriff graph from main.ts. onboarding imports
ui-kit + composites (incl. promoted auth-layout) → their index.ts in graph → shared. Nothing in onboarding's graph
imported core → core dropped. Fix = put profile (the core consumer) in the graph via main.ts routing.

## Evidence (as-run)
- Remote build 2.85–2.88s; shell build 3.37–3.49s (≤90s Decision-12, huge margin). Shell initial 60.80 kB /
  18.48 kB transfer; onboarding+profile chunks LEFT the shell.
- Tests 43 files / 408 (SP01 baseline 406 + 2 new C5 smoke tests). 0 failed / 0 skipped. Moved specs discovered
  at `spec-apps-mfe-onboarding-src-app-{onboarding,profile,auth-singleton.smoke}` + `spec-libs-composites-auth-layout-*`.
- Boundary grep ZERO. Headless: remoteEntry 200 + both exposed chunks 200 + `_mesell_core` chunk 200 + broken-url 404.
- Moved-file integrity: profile.component.ts BYTE-IDENTICAL to develop; auth-layout.component.ts BYTE-IDENTICAL;
  onboarding.component.ts differs ONLY in the AuthLayout import line (relative → `@mesell/composites`).

## Recipe deltas vs SP01 (record for SP04+)
- **`tsconfig.federation.json` is a build artefact** auto-generated per remote build (lists shared lib entry points).
  mfe-pricing did NOT commit one. I added `**/tsconfig.federation.json` to `frontend/.gitignore` (additive). Never commit it.
- **Parallel-wave:** manifest went 1→2 entries (pricing+onboarding), NOT 3 — SP02 (export) had NOT merged to develop
  (only its memos landed). My shared-file edits (manifest/app.routes/angular.json) were additive + disjoint from SP02's
  export route; `git merge origin/develop` into integration was CONFLICT-FREE (SP02's remote not yet on develop).
- **C5 smoke test gotcha:** `comp.onLogout()` calls `router.navigate(['/login'])`; the test router needs a `/login`
  (+`/dashboard`) stub route or you get an unhandled NavigationError (NG04002, code 4002) → suite exits 1 despite
  "408 passed". Provide the stub routes. Use `runInInjectionContext(envInjector, () => authGuard(...))` to test the guard.
- **pnpm worktree:** `pnpm install --config.dangerously-allow-all-builds=true` then `pnpm rebuild esbuild` (the flag
  alone did NOT extract the darwin-arm64 esbuild binary this session — `pnpm rebuild esbuild` did, into the .pnpm store,
  with NO pnpm-workspace.yaml drift). Then `./node_modules/.bin/ng build <proj>` directly.

## Merge mechanics
- Group PR #67 frontend→integration: LEAD-GATE APPROVE comment (full checklist) + `gh pr merge --squash --admin
  --delete-branch` → MERGED e2035330; local branch-delete errored (worktree held it) → recovered via
  `git worktree remove --force` + `git push origin --delete feature/mfe-onboarding/frontend`.
- Before founder gate: synced local integration to origin (`git reset --hard origin/...`) then `git merge origin/develop`
  (conflict-free) → pushed a981a22 → re-built shell+remote on the merged branch to certify (green) → opened #68.
- Founder-gate PR #68 integration→develop: title `[FOUNDER GATE — DO NOT MERGE]`, full §9 scorecard, LEFT OPEN.
  I did NOT approve it (D1 — founder's gate).

## Forward contract for SP04 (mfe-dashboard, R3)
- landing = fully PUBLIC self-contained (RouterLink + MeeButton). dashboard = shell-guard-protected, injects a
  remote-private `DashboardApiService` (`@Injectable()` NON-root, route/component provider — preserve) + MeeConfirmService
  + Router; does NOT inject AuthService. New surface = public/private routing split (unauth `/` landing; unauth
  `/dashboard` redirects WITHOUT fetching the remote — guard in shell). SP04 CONSUMES this D22 contract (no AuthService
  injection itself, so the main.ts-reachability rule is moot for core there — but applies if any future expose adds it).
- COPY the recipe: new apps/mfe-dashboard project (same target shape + index.html!), git mv, public-api, federation.config
  (name mfe-dashboard, exposes the components/routes), manifest += entry, REUSE load-remote.ts + remote-failure.component.ts,
  re-confirm the apps glob. If ANY exposed component injects a shared lib, ensure main.ts routes to it (the R-SP3-1 rule).
