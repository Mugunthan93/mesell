# SP06 TASK SPEC — mfe-auth extraction (login + signup + otp-verify) — THE LAST & RISKIEST EXTRACTION

**Authored:** 2026-06-11 by meesell-frontend-coordinator (Frontend Lead). HYBRID step 1 of 3.
**Ground truth:** `docs/plans/module_federation/SUB_PLAN_06_auth_extraction.md` (authoritative) + develop tip `90e3f0e` (all 5 other remotes merged; SP03 D22 C1–C5 PASSED).
**Executes:** a sonnet specialist runs this verbatim (step 2). Lead reviews (step 3).
**Port:** mfe-auth = **4206** (final registry slot). **Remote ID:** R1. **Slug:** `mfe-auth`.

> **GROUND-TRUTH RECONCILIATIONS baked into this spec (verified against develop@90e3f0e, NOT assumed):**
> 1. **D39 AuthLayout re-point is a VERIFY-ONLY NO-OP.** All 3 pages ALREADY import `AuthLayoutComponent from '@mesell/composites'` (login L10, signup L10, otp L11). NO relative `../../layouts/auth-layout` remains anywhere. SP03's optional re-point landed. The spec's "re-point" step degrades to a grep-assertion (no edit). [Flagged for master confirm — resolution: the SP06 plan's D39 conditional ("if any page still uses the relative path") is FALSE on develop; no edit needed.]
> 2. **Test baseline is a HARD NUMBER: 43 spec files** on develop@90e3f0e (libs/ui-kit 19, libs/composites 6, apps 11 [pricing1/export1/onboarding3/dashboard2/catalog4], src 7 — the src 7 INCLUDES the 3 auth specs that will MOVE). After Phase A+B the count stays **43** (the 3 auth specs relocate src→apps, net zero). After Phase C the service-builder adds the C4 smoke test → **44**. So: Phase-B gate expects **43**; Phase-C gate expects **44**. A DROP below 43 = silent non-discovery = HARD REJECT.
> 3. **angular.json has exactly TWO port keys** for a remote: `serve.options.port` AND `serve-original.options.port` (verified on mfe-dashboard: both 4204). Both set to 4206.
> 4. **R-SP6-5 (otp spec AuthService resolution) is LOW risk** — the spec imports `AuthService from '@mesell/core'` (alias, not relative) and does `TestBed.inject(AuthService)`. Resolves workspace-wide post-move. No rewrite needed; verify it still passes.
> 5. **R-SP6-6 (public-auth CSP gap) stays escalated to SP07** — note only, no action this sub-plan.

---

## 1. EXACT FILE MOVES (rename-only vs modified)

Source paths verified on develop@90e3f0e. Use `git mv` to preserve history (R100 blob-identity expected on the rename-only files).

| # | Source (develop) | Target | Tag | Edit allowed |
|---|---|---|---|---|
| 1 | `frontend/src/app/features/auth/login.component.ts` | `frontend/apps/mfe-auth/src/app/login.component.ts` | MOVE — **rename-only, ZERO edits** | None. AuthLayout already `@mesell/composites` (L10); deep ui-kit imports already correct (L11-12). Blob hash MUST equal develop. |
| 2 | `frontend/src/app/features/auth/login.component.spec.ts` | `frontend/apps/mfe-auth/src/app/login.component.spec.ts` | MOVE — rename-only | None |
| 3 | `frontend/src/app/features/auth/signup.component.ts` | `frontend/apps/mfe-auth/src/app/signup.component.ts` | MOVE — **rename-only, ZERO edits** | None. AuthLayout already `@mesell/composites` (L10). Blob hash MUST equal develop. |
| 4 | `frontend/src/app/features/auth/signup.component.spec.ts` | `frontend/apps/mfe-auth/src/app/signup.component.spec.ts` | MOVE — rename-only | None |
| 5 | `frontend/src/app/features/auth/otp-verify/otp-verify.component.ts` | `frontend/apps/mfe-auth/src/app/otp-verify.component.ts` | MOVE — **rename-only, ZERO edits** | None. AuthLayout `@mesell/composites` (L11); `AuthService from '@mesell/core'` (L12); deep ui-kit (L13-14); `setSession('mock-token', {id:1,name:'Seller',phone:'+91XXXXXXXXXX'})` (L148-152); `setInterval`/`clearInterval` resend-timer (L123/130/139/158/162). ALL byte-identical. Blob hash MUST equal develop. **NOTE: flattens the `otp-verify/` subdir** — target is `apps/mfe-auth/src/app/otp-verify.component.ts` (no nested folder). |
| 6 | `frontend/src/app/features/auth/otp-verify/otp-verify.component.spec.ts` | `frontend/apps/mfe-auth/src/app/otp-verify.component.spec.ts` | MOVE — rename-only | None. Imports `AuthService from '@mesell/core'` (alias) + `TestBed.inject(AuthService)` — resolves post-move. |

After moves: `frontend/src/app/features/auth/` (incl. the `otp-verify/` subdir) is **removed entirely** (git mv leaves the dir empty → gone).

**D39 re-point step = NO-OP VERIFY.** Run after the moves:
```bash
grep -rn "layouts/auth-layout" frontend/apps/mfe-auth/   # MUST return ZERO lines
grep -rn "@mesell/composites" frontend/apps/mfe-auth/src/app/*.component.ts  # MUST show all 3 pages
```
If (and only if) a relative `../../layouts/auth-layout` appears (it will NOT on develop@90e3f0e), re-point that line to `@mesell/composites` — that single line is then the ONLY permitted content edit. Expectation: zero edits, all 3 already correct.

**D39 resend-timer + setSession preservation = NO EDIT.** The otp `setInterval` timer and the `setSession('mock-token', {...})` call move byte-identical (rule already enforced by "rename-only, blob hash equal").

---

## 2. EXACT NEW FILES (verbatim — copy mfe-dashboard shape, swap names + port + 3 exposes)

### 2.1 `frontend/apps/mfe-auth/src/app/public-api.ts`
```ts
// mfe-auth — public surface (the federation typed boundary, MASTER_PLAN §6.5).
// THREE-expose remote (D37): re-exports all three exposed components. The shell's
// loadRemoteWithFallback helper resolves each exposed symbol from one remoteEntry.json.
export { LoginComponent } from './login.component';
export { SignupComponent } from './signup.component';
export { OtpVerifyComponent } from './otp-verify.component';
```

### 2.2 `frontend/apps/mfe-auth/federation.config.js`
```js
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 06 — remote `mfe-auth` (F2 login + F3 signup + F4 otp-verify; routes
// /login + /signup + /otp-verify, all PUBLIC pre-auth). The SIXTH and FINAL extraction
// and the most shell-connected remote: otp-verify is the ONLY flow that WRITES the shell's
// auth.token() via setSession (the C4 WRITE path, D38). Extracted last so 5 reference
// implementations + the proven D22 C1–C5 contract de-risk it.
//
// R-SP3-1 (P0): @mesell/core (AuthService) is consumed by otp-verify.component — its
// setSession() WRITE depends on resolving the SHELL's single AuthService instance via the
// import map. main.ts MUST route to OtpVerifyComponent (the core consumer) so the Sheriff
// import-graph analysis (ignoreUnusedDeps) keeps @mesell/core shared+singleton and does NOT
// inline it into the otp chunk (which would be the P0 drift, MASTER_PLAN R1). shareAll +
// main.ts-routes-to-all-3 = uniform shared set; @mesell/ui-kit, @mesell/composites,
// @mesell/core, @angular/*, rxjs all resolve to the shell's instances (MASTER_PLAN §6.1).
module.exports = withNativeFederation({
  name: 'mfe-auth',

  exposes: {
    './LoginComponent': './apps/mfe-auth/src/app/login.component.ts',
    './SignupComponent': './apps/mfe-auth/src/app/signup.component.ts',
    './OtpVerifyComponent': './apps/mfe-auth/src/app/otp-verify.component.ts',
  },

  shared: {
    ...shareAll({ singleton: true, strictVersion: false, requiredVersion: 'auto' }),
  },

  skip: [
    'rxjs/ajax',
    'rxjs/fetch',
    'rxjs/testing',
    'rxjs/webSocket',
  ],

  features: {
    ignoreUnusedDeps: true,
  },
});
```
> Note: exposes paths are RELATIVE TO `frontend/` root (the angular.json cwd), NOT to the apps dir — matches every prior remote. `@mesell/core` is in the shareAll set; ignoreUnusedDeps will KEEP it in `mfe-auth`'s remoteEntry shared[] BECAUSE otp-verify imports it AND main.ts routes to otp-verify (unlike pricing/export/dashboard which omit core — they never consume it). The `_mesell_core-*.js` chunk MUST appear and otp MUST NOT inline AuthService (C2 static proof, Phase C).

### 2.3 `frontend/apps/mfe-auth/src/main.ts`
```ts
// mfe-auth — dev-serve / standalone bootstrap entry ONLY.
// In federation each component is mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 (P0): main.ts MUST reference ALL THREE exposed components. Native Federation's
// `ignoreUnusedDeps` analyzer (Sheriff) prunes shared-mappings from the import graph rooted
// at THIS main.ts. OtpVerifyComponent is the @mesell/core (AuthService) consumer — routing
// to it keeps @mesell/core in the analysis graph so it stays shared+singleton and resolves
// to the SHELL's import-map instance. Without otp-verify reachable here, @mesell/core would
// be inlined into the otp chunk → setSession would mutate a DUPLICATE AuthService → the shell
// never sees authentication = the P0 WRITE-path drift (R-SP6-1 / MASTER_PLAN R1). Login + Signup
// are routed too for completeness (they consume @mesell/composites + @mesell/ui-kit). (Mirrors
// mfe-onboarding / mfe-dashboard.)
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, type Routes } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { LoginComponent } from './app/login.component';
import { SignupComponent } from './app/signup.component';
import { OtpVerifyComponent } from './app/otp-verify.component';

const devRoutes: Routes = [
  { path: '', component: LoginComponent },
  { path: 'signup', component: SignupComponent },
  { path: 'otp-verify', component: OtpVerifyComponent },
];

bootstrapApplication(LoginComponent, {
  providers: [
    provideRouter(devRoutes),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));
```

### 2.4 `frontend/apps/mfe-auth/src/index.html`
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>mfe-auth</title>
  <base href="/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/primeicons/primeicons.css">
</head>
<body>
  <!-- Standalone dev-serve host only. In federation the Login/Signup/OtpVerify components
       are mounted INTO the shell's router outlet via loadRemoteModule; this index is not
       used there. main.ts bootstraps LoginComponent for the dev server.
       Host element = LoginComponent selector (mee-login). -->
  <mee-login></mee-login>
</body>
</html>
```
> **GOTCHA (cost a build cycle on SP01):** `@angular/build:application` REQUIRES `index.html` + the `index` key in the esbuild options (set in §3.3) or the build fails "Failed to read index HTML file". Host element MUST be the bootstrapped component's selector — `mee-login` (verified selector, NOT the `app-*` default).

### 2.5 `frontend/apps/mfe-auth/tsconfig.app.json`
```json
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "../../out-tsc/mfe-auth",
    "types": []
  },
  "include": [
    "src/**/*.ts",
    "../../libs/**/*.ts"
  ],
  "exclude": [
    "src/**/*.spec.ts",
    "../../libs/**/*.spec.ts"
  ]
}
```

---

## 3. EXACT SHARED-FILE DIFFS

### 3.1 `frontend/src/app/app.routes.ts` — 3 PUBLIC route swaps (NO guard added)

Replace the three top-level public auth route blocks (currently lazy `import('./features/auth/...')`) with `loadRemoteWithFallback`. The blocks sit between the public `''` landing route and the protected shell parent. The helper is ALREADY imported at the top of the file (`loadRemoteWithFallback` from `./core/load-remote`). NO new import needed.

**Remove:**
```ts
  // Auth pages — top-level routes (each page wraps itself in AuthLayoutComponent)
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    loadComponent: () =>
      import('./features/auth/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'otp-verify',
    loadComponent: () =>
      import('./features/auth/otp-verify/otp-verify.component').then(m => m.OtpVerifyComponent),
  },
```
**Replace with:**
```ts
  // MF Sub-Plan 06 — mfe-auth remote (apps/mfe-auth/). The THREE auth pages (login,
  // signup, otp-verify) now live in one Native-Federation remote exposing THREE
  // components, loaded at runtime via the manifest. ALL THREE are PUBLIC top-level
  // routes — NO authGuard (reached pre-authentication, D37). otp-verify is the only
  // flow that WRITES the shell's auth state: its setSession() mutates the shared
  // @mesell/core AuthService singleton across the boundary (the C4 WRITE path, D38).
  // D12 fallback on remote-load failure. The '**' -> 'login' wildcard below now
  // resolves to this remote LoginComponent.
  {
    path: 'login',
    loadComponent: loadRemoteWithFallback('mfe-auth', './LoginComponent'),
  },
  {
    path: 'signup',
    loadComponent: loadRemoteWithFallback('mfe-auth', './SignupComponent'),
  },
  {
    path: 'otp-verify',
    loadComponent: loadRemoteWithFallback('mfe-auth', './OtpVerifyComponent'),
  },
```
- **NO `canActivate`** on any of the three (D37 — public, pre-auth).
- The `{ path: '**', redirectTo: 'login' }` wildcard at the bottom is **UNCHANGED** — it now resolves to the remote LoginComponent (verify in Phase B).
- The protected shell parent + its `canActivate: [authGuard]` is **UNTOUCHED**.

### 3.2 `frontend/public/federation.manifest.json` — add the SIXTH (final) entry

**From (5 entries):**
```json
{
  "mfe-pricing": "http://localhost:4201/remoteEntry.json",
  "mfe-export": "http://localhost:4202/remoteEntry.json",
  "mfe-onboarding": "http://localhost:4203/remoteEntry.json",
  "mfe-catalog": "http://localhost:4205/remoteEntry.json",
  "mfe-dashboard": "http://localhost:4204/remoteEntry.json"
}
```
**To (6 entries — the COMPLETE topology):**
```json
{
  "mfe-pricing": "http://localhost:4201/remoteEntry.json",
  "mfe-export": "http://localhost:4202/remoteEntry.json",
  "mfe-onboarding": "http://localhost:4203/remoteEntry.json",
  "mfe-catalog": "http://localhost:4205/remoteEntry.json",
  "mfe-dashboard": "http://localhost:4204/remoteEntry.json",
  "mfe-auth": "http://localhost:4206/remoteEntry.json"
}
```

### 3.3 `frontend/angular.json` — add `projects.mfe-auth` (port 4206 in BOTH port keys)

Add this block as a sibling project (copy the mfe-dashboard block verbatim, swap `mfe-dashboard`→`mfe-auth` everywhere, `4204`→`4206` in BOTH port slots, host element selector is implicit via the index.html). Verbatim:
```json
"mfe-auth": {
  "projectType": "application",
  "schematics": {},
  "root": "apps/mfe-auth",
  "sourceRoot": "apps/mfe-auth/src",
  "prefix": "app",
  "architect": {
    "build": {
      "builder": "@angular-architects/native-federation:build",
      "options": {},
      "configurations": {
        "production": { "target": "mfe-auth:esbuild:production" },
        "development": { "target": "mfe-auth:esbuild:development", "dev": true }
      },
      "defaultConfiguration": "production"
    },
    "serve": {
      "builder": "@angular-architects/native-federation:build",
      "options": {
        "target": "mfe-auth:serve-original:development",
        "rebuildDelay": 500,
        "dev": true,
        "cacheExternalArtifacts": false,
        "port": 4206
      }
    },
    "esbuild": {
      "builder": "@angular/build:application",
      "options": {
        "browser": "apps/mfe-auth/src/main.ts",
        "index": "apps/mfe-auth/src/index.html",
        "tsConfig": "apps/mfe-auth/tsconfig.app.json",
        "styles": ["src/styles.css"],
        "polyfills": ["es-module-shims"]
      },
      "configurations": {
        "production": {
          "budgets": [
            { "type": "initial", "maximumWarning": "500kB", "maximumError": "1MB" },
            { "type": "anyComponentStyle", "maximumWarning": "4kB", "maximumError": "8kB" }
          ],
          "outputHashing": "all"
        },
        "development": { "optimization": false, "extractLicenses": false, "sourceMap": true }
      },
      "defaultConfiguration": "production"
    },
    "serve-original": {
      "builder": "@angular/build:dev-server",
      "configurations": {
        "production": { "buildTarget": "mfe-auth:esbuild:production" },
        "development": { "buildTarget": "mfe-auth:esbuild:development" }
      },
      "defaultConfiguration": "development",
      "options": { "port": 4206 }
    }
  }
}
```
- **Shell project (`frontend`) UNCHANGED.** The test-discovery `include` (`../apps/**/*.spec.ts`) ALREADY covers `apps/mfe-auth/` — RE-CONFIRM, do NOT edit.
- `tsconfig.spec.json` `apps/**/*.spec.ts` ALREADY covers it — RE-CONFIRM, do NOT edit.
- `src/styles.css` `@source "../apps"` (L24) ALREADY present — RE-CONFIRM, do NOT edit.

### 3.4 `frontend/package.json` — add the start script (alphabetical-by-port grouping with the others)

Add this line in the scripts block alongside the other `start:mfe-*` lines:
```json
    "start:mfe-auth": "ng serve mfe-auth"
```
> Port-pin is via the script flag convention OR angular.json — here angular.json carries 4206, so `ng serve mfe-auth` picks it up. Matches the master constraint line verbatim.

---

## 4. THE D38/C4 WRITE-PATH PROOF + FULL VALIDATION CHECKLIST

### 4.A The C4 setSession WRITE-path smoke test (service-builder, Phase C) — the migration's auth WRITE go/no-go

This is the INVERSE of SP03's C5 READ/LOGOUT test (`apps/mfe-onboarding/src/app/auth-singleton.smoke.spec.ts`). Reuse its harness shape. Author at `apps/mfe-auth/src/app/auth-write.smoke.spec.ts` (or `auth-singleton-write.smoke.spec.ts`). The test asserts the REMOTE's setSession WRITE crosses the boundary into the SHELL's signal.

**Exact procedure (must produce visible assertion output):**
```
1. TestBed: provide AuthService (the @mesell/core singleton), provideRouter with STUB routes
   for '/login' AND '/dashboard' (per SP03 C5 gotcha: a router.navigate(['/dashboard']) with no
   matching route throws NG04002 and exits the suite 1 despite "passed"). Create OtpVerifyComponent.
2. START UNAUTHENTICATED: assert shellAuth.isAuthenticated() === false AND shellAuth.currentUser() === null.
   Assert the authGuard (runInInjectionContext(envInjector, () => authGuard(...))) returns a UrlTree
   redirect to /login (i.e. /dashboard is BLOCKED) — mirrors SP03 C5's guard assertion, pre-write.
3. Confirm the otp component's injected auth IS the same instance: comp['auth'] === TestBed.inject(AuthService)
   (C2 single-instance, the WRITE target must be the shell's instance).
4. Trigger the WRITE: set comp.otpValue to a 6-char string, call comp.onSubmit(); the onSubmit uses
   setTimeout(1500) before setSession — use fakeAsync + tick(1500) (or vi fake timers) to flush it.
5. ASSERT post-WRITE (the crux): shellAuth.isAuthenticated() === true
   AND shellAuth.currentUser()?.name === 'Seller'
   AND shellAuth.currentUser()?.id === 1
   AND shellAuth.getToken() === 'mock-token'
   — the REMOTE's setSession('mock-token', {id:1,name:'Seller',phone:'+91XXXXXXXXXX'}) mutated the
   SHELL's single signal across the boundary (C4 WRITE proven).
6. ASSERT the guard now PASSES: runInInjectionContext(envInjector, () => authGuard(...)) returns true
   (===true, not a UrlTree) — /dashboard is now reachable; the post-setSession router.navigate(['/dashboard'])
   would succeed (it was blocked in step 2).
```
> The `setSession('mock-token', ...)` simulation is PRESERVED EXACTLY (no real OTP/JWT API — Wave 6). The test proves the SIGNAL-SHARING mechanism, not the auth backend. The otp `setInterval` resend-timer must be flushable/cleanable in the test (the component's ngOnDestroy clears it; assert no orphaned timer after fixture.destroy()).

**C2 static proof (Phase C, alongside C4):** inspect the built `dist/mfe-auth/browser/` output:
```
- remoteEntry.json shared[] CONTAINS @mesell/core (it is consumed by otp + reachable from main.ts).
- EXACTLY ONE _mesell_core-*.js chunk; AuthService class impl in it, NOT inlined into the otp component chunk.
- grep the otp component chunk: NO standalone auth.service class body duplicated.
```
> Contrast: pricing/export/dashboard legitimately OMIT @mesell/core (never consume it). mfe-auth MUST INCLUDE it (otp consumes it). Its ABSENCE here = the P0 drift = HARD STOP.

### 4.B Full validation checklist (the merge-gate scorecard — §9.A + extras)

| # | Check | Expected | Phase |
|---|---|---|---|
| 1 | `ng build mfe-auth` GREEN → `dist/mfe-auth/browser/remoteEntry.json` | name `mfe-auth`, 3 exposes (Login/Signup/OtpVerify); record seconds | A |
| 2 | Shell `pnpm build` (or `./node_modules/.bin/ng build frontend`) GREEN | **≤ 90 s** (D12 stop condition); record seconds + bundle delta (auth chunks LEAVE shell → initial should shrink ~ from 60.80 kB) | B |
| 3 | Full test suite `pnpm test` | **44 files**, 0 failing, 0 skipped (43 pre-existing baseline w/ 3 auth specs relocated src→apps, +1 C4 smoke). Below 43 = HARD REJECT. After Phase B alone (pre-C4) = 43. | B / C |
| 4 | Moved-spec discovery | 3 auth specs discovered at `spec-apps-mfe-auth-src-app-{login,signup,otp-verify}.component`; C4 at `spec-apps-mfe-auth-src-app-auth-write.smoke` | B / C |
| 5 | Boundary grep | `grep -rn "from 'primeng" frontend/apps/mfe-auth/` = ZERO (no new PrimeNG leak) | B |
| 6 | All 3 PUBLIC routes resolve | `/login`→Login, `/signup`→Signup, `/otp-verify`→OtpVerify; render in shell outlet; NO guard (pre-auth reachable) | B |
| 7 | D39 AuthLayout-from-composites | all 3 import from `@mesell/composites`; `grep -rn "layouts/auth-layout" apps/mfe-auth/` = ZERO | A |
| 8 | D39/D18 resend-timer | `setInterval`/`clearInterval` byte-identical (blob-hash); clears on navigate-away (ngOnDestroy fires; no orphaned timer) | A / B |
| 9 | Wildcard redirect | `{ path:'**', redirectTo:'login' }` still resolves to the remote LoginComponent | B |
| 10 | **C4 WRITE-path smoke (D38)** | PASS — unauth shell (guard blocks /dashboard) → remote setSession → shell isAuthenticated TRUE + currentUser correct + getToken 'mock-token' → guard now passes. **FAIL = HARD STOP (P0 drift, halt cutover).** | C |
| 11 | C2 no-duplicate-chunk | `@mesell/core` in remoteEntry shared[]; single `_mesell_core-*.js`; NOT inlined in otp chunk | C |
| 12 | Singleton non-drift (C1) | `@mesell/core` confirmed `shared + singleton:true` in federation.config.js (shareAll), NOT skipped | A / C |
| 13 | Manifest | SIX entries (the complete MASTER_PLAN §2.2 topology) | B |
| 14 | `git diff libs/core/services/auth.service.ts` | EMPTY (D22 C2 — ZERO AuthService change) | C |
| 15 | Move integrity | `git diff -M --summary` shows 6× `rename ... (100%)`; blob-hash equality on all 6 moved files (byte-identical to develop) | A |
| 16 | D12 fallback (headless) | serve `dist/mfe-auth/browser/` on :4206; curl remoteEntry.json→200, an exposed chunk→200, broken-url→404; load-remote helper reused (NOT re-authored) | B |
| 17 | Screenshots | 360 px + 1280 px of /login + /signup + /otp-verify (no visual change — pure rename) | D (lead) |

> **REUSE, do NOT re-author:** `src/app/core/load-remote.ts` (`loadRemoteWithFallback`) + `src/app/core/remote-failure.component.ts` (D12 boundary) exist from SP01 — reuse verbatim.

---

## 5. BRANCH / PR PLAN

Feature slug `mfe-auth`. Per F1. Worktree under `/tmp/mesell-wt/sp06-*`.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-auth/integration` | `develop` @ 90e3f0e (all 5 remotes merged) | Integration branch | Frontend Lead |
| `feature/mfe-auth/frontend` | `feature/mfe-auth/integration` | ALL extraction + C4 proof | component-builder, then service-builder (SAME branch, sequential) |

**F1 setup (lead, EXECUTION stage) — do NOT branch-switch the master tree:**
```bash
git fetch origin develop
git branch feature/mfe-auth/integration origin/develop          # 90e3f0e, all 5 remotes present
git push -u origin feature/mfe-auth/integration
git branch feature/mfe-auth/frontend feature/mfe-auth/integration
git push -u origin feature/mfe-auth/frontend
git worktree add /tmp/mesell-wt/sp06-frontend feature/mfe-auth/frontend
# F3 protection on integration via `gh api PUT .../protection --input <json-file>` (NOT -f/-F mixing):
#   required_status_checks null, review-count 0, force-push off, deletions off (re-probe empirically).
```
> Worktree fresh-install: `pnpm install --config.dangerously-allow-all-builds=true` then (if esbuild darwin binary not extracted) `pnpm rebuild esbuild`; build via `./node_modules/.bin/ng build <proj>` DIRECTLY (not `pnpm build` — its deps-check re-fails). `**/tsconfig.federation.json` already in .gitignore (SP03) — NEVER commit it.

**Dispatch order (SERIAL — service-builder AFTER component-builder's Phase A+B is GREEN):**
- Session 1: `meesell-angular-component-builder` (Phase A extract + B wire). Session name `mesell-mfe-auth-frontend-session-1`.
- Session 2: `meesell-angular-service-builder` (Phase C C4 WRITE proof). Session name `mesell-mfe-auth-frontend-session-2`.

**PR flow:**
```
feature/mfe-auth/frontend
        │  PR — Frontend Lead reviews + SQUASH-merges            [D1 — lead's gate]
        ▼
feature/mfe-auth/integration
        │  (lead: reset --hard origin/integration; MERGE origin/develop FIRST — develop is busy,
        │   union-merge the 4 shared files if any remote landed; re-certify builds+tests)
        │  PR — FOUNDER reviews + merges  [D1 — LEFT OPEN, lead must NOT approve]
        ▼
develop
```
- **DEVELOP-IS-BUSY discipline:** before opening the founder-gate PR, `git reset --hard origin/feature/mfe-auth/integration` THEN `git merge origin/develop` (the SP02 stale-integration gotcha: reset BEFORE merging develop, else fast-forward silently drops the group-PR code). The 4 shared files (app.routes.ts / manifest / angular.json / package.json) are union-merge candidates if a sibling remote landed on develop meanwhile — keep-both, re-certify both builds + test count on the merged tip.
- Founder-gate PR title `[FOUNDER GATE — DO NOT MERGE]`, full §4.B scorecard in body, LEFT OPEN.
- `gh pr merge --squash --admin`; self-approval blocked → record LEAD GATE APPROVE as a PR comment first. `gh api -X DELETE .../git/refs/heads/feature/mfe-auth/frontend` for the branch delete (worktree-safe).

---

## 6. STOP CONDITIONS (specialist HALTS + escalates to lead — do NOT push through)

1. **ANY AuthService code change required** = **STOP**. ZERO changes to `libs/core/services/auth.service.ts` allowed (D39/D22 C2 — singleton is via import-map sharing, NOT a decorator/logic refactor). `git diff` on that file MUST be empty. If extraction seems to "need" an AuthService edit, the approach is wrong — halt.
2. **C4 WRITE-path test FAILS** (remote's setSession mutates a DUPLICATE instance; shell stays unauthenticated) = **HARD STOP**. This is the migration's auth WRITE go/no-go (P0 drift, MASTER_PLAN R1). Do NOT merge. Escalate to founder — a failed WRITE contract on the LAST remote blocks the SP07 cutover.
3. **`@mesell/core` missing/skipped from mfe-auth federation.config shared set** = STOP (would cause #2). It MUST be in shareAll + reachable from main.ts (route to otp-verify).
4. **Shell build > 90 s** = STOP (D12 stop condition).
5. **Test count drops below 43** (Phase B) / below 44 (Phase C) = HARD REJECT (silent spec non-discovery — the `apps/**/*.spec.ts` glob gotcha).
6. **A relative `../../layouts/auth-layout` import surfaces** in the moved pages = STOP/fix (the remote cannot reach `../../layouts/`). Expectation: NONE on develop@90e3f0e.
7. **otp resend-timer rewritten to RxJS** OR **deep `@mesell/ui-kit/*` imports barrel-rewritten** = REJECT (D39/D18 timer-preserve; bundle landmine).
8. **A guard added to any of the 3 public auth routes** = REJECT (D37 — pre-auth public).
9. **CSP authored / shell moved to apps/shell/** = REJECT (D14/D9 — SP07's job; R-SP6-6 CSP gap stays escalated to SP07).
10. **Any byte-level logic/template edit to login/signup/otp** beyond the (expected-zero) AuthLayout re-point = REJECT (blob hashes MUST equal develop).
11. **Iteration cap: 3** per specialist → founder escalation.

---

## 7. CROSS-LEAD / MEMORY DELIVERABLES (lead, Phase D)

- **Infra memo** `handoff_mf_auth_deploy.md` → infra: sixth/final-remote GCS prefix `gs://meesell-frontend/{env}/mfe-auth/{version}/` + matrix fan-out (C-CI-1) + **the public-auth-pages CSP escalation for SP07** (R-SP6-6 / C-CSP-1: `/login` first paint fetches `remotes.mesell.xyz` PRE-AUTH — alongside SP04's public landing, the two highest-stakes CSP surfaces). Board inter-lead row, 48h SLA.
- **Memory** `sub_plan_06_auth.md`: the C4 WRITE-path go/no-go result + the COMPLETE-6-remote-topology milestone + the SP07 handoff (all extractions DONE; cutover is the only remaining sub-plan).
- **Board** `feature_board_frontend.md`: `mfe-auth` row lifecycle (IN PROGRESS at dispatch → IN REVIEW on PR open by specialist → MERGED on lead merge) + infra inter-lead row.
- **STATUS** `STATUS_FRONTEND.md`: build/test numbers, the C4 WRITE-path verdict, the complete-topology milestone.
```

