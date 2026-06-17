# TASK SPEC — SP04 `mfe-dashboard` Extraction (F1 landing + F6 dashboard)

**For:** `meesell-angular-component-builder` (sonnet) — execute VERBATIM. Zero judgment calls.
**Authored by:** meesell-frontend-coordinator (Frontend Lead) — Hybrid-rule step 1 of 3.
**Session:** `mesell-mfe-dashboard-frontend-session-1`
**Ground truth:** `docs/plans/module_federation/SUB_PLAN_04_dashboard_extraction.md` + develop tip **e64fa82** (SP01/SP02/SP03 ALL merged; 3 remotes live: mfe-pricing :4201, mfe-export :4202, mfe-onboarding :4203). Verified against the as-built source on develop, NOT the pre-split shape.
**Master-assigned constraints baked in:** port **4204**; R-SP3-1 P0 main.ts-reachability; `start:mfe-dashboard` script; recipe gotchas; SP05 parallel-wave additive-edit discipline.

> **VERIFIED GROUND-TRUTH CORRECTIONS to the SUB_PLAN narrative (the specialist must follow THIS spec where it differs):**
> 1. **`DashboardApiService` is a COMPONENT-LEVEL provider** — `dashboard.component.ts` has `providers: [DashboardApiService]` on its `@Component` decorator. It is NOT a route-level provider. So it moves with the component automatically; D28a "verify" reduces to "do not strip the `providers:` array." Zero NullInjectorError risk if the component is moved intact.
> 2. **`dashboard.component.spec.ts` is a PURE-FUNCTION spec — NO TestBed, NO DI.** It imports ONLY from `./dashboard.model`. It does NOT test the provider. Its only move-sensitivity is the relative import `./dashboard.model` staying valid (it does — the model moves alongside).
> 3. **`landing.component.ts` uses `RouterLink` only — no programmatic `router.navigate`.** R-SP4-6 (cross-boundary redirect) is declarative + shell-routed; no special handling.
> 4. **Test baseline on develop e64fa82 = 43 spec files / 408 tests, 0 fail / 0 skip.** SP04 moves 2 existing specs and adds ZERO new specs → baseline MUST stay **43 files / 408 tests**. (A drop = silent non-discovery = HARD REJECT. An increase = an unrequested new spec = flag, do not add.)
> 5. **The closest copy template is `apps/mfe-onboarding/` (TWO exposes), NOT `apps/mfe-pricing/` (one expose).** Dashboard = two exposes like onboarding/profile. Copy onboarding's `federation.config.js` / `main.ts` / `public-api.ts` shape, swap the component names. Use mfe-pricing only for the single-expose-agnostic files (`index.html`, `tsconfig.app.json` — identical across all 3).

---

## 0. Preconditions (the specialist confirms before touching anything)

- [ ] develop tip is **e64fa82** (or newer with SP01/02/03 still present). `git rev-parse --short origin/develop`.
- [ ] `frontend/src/app/features/landing/` (2 files) + `frontend/src/app/features/dashboard/` (4 files) exist on develop.
- [ ] `frontend/apps/mfe-pricing/`, `mfe-export/`, `mfe-onboarding/` all exist (the copy templates + the 3 live remotes).
- [ ] `frontend/src/app/core/load-remote.ts` + `remote-failure.component.ts` exist (REUSE — do NOT re-author).
- [ ] manifest has exactly THREE entries (pricing/export/onboarding).

If any precondition fails → STOP and report (do not improvise).

---

## 1. Exact file moves (source → destination)

All moves are `git mv` (100%-similarity, history-preserving, ZERO logic/template edits). Paths are repo-relative.

| # | Source (develop e64fa82) | Destination | Tag |
|---|---|---|---|
| 1 | `frontend/src/app/features/landing/landing.component.ts` | `frontend/apps/mfe-dashboard/src/app/landing.component.ts` | MOVE (rename-only) |
| 2 | `frontend/src/app/features/landing/landing.component.spec.ts` | `frontend/apps/mfe-dashboard/src/app/landing.component.spec.ts` | MOVE (rename-only) |
| 3 | `frontend/src/app/features/dashboard/dashboard.component.ts` | `frontend/apps/mfe-dashboard/src/app/dashboard.component.ts` | MOVE (rename-only) |
| 4 | `frontend/src/app/features/dashboard/dashboard.component.spec.ts` | `frontend/apps/mfe-dashboard/src/app/dashboard.component.spec.ts` | MOVE (rename-only) |
| 5 | `frontend/src/app/features/dashboard/dashboard.model.ts` | `frontend/apps/mfe-dashboard/src/app/dashboard.model.ts` | MOVE (rename-only) |
| 6 | `frontend/src/app/features/dashboard/services/dashboard-api.service.ts` | `frontend/apps/mfe-dashboard/src/app/services/dashboard-api.service.ts` | MOVE (rename-only) — **keep the `services/` subdir** so `./services/dashboard-api.service` stays valid |

**Relative import paths inside the moved files MUST stay byte-identical:**
- `dashboard.component.ts` imports `./dashboard.model` and `./services/dashboard-api.service` → both targets move alongside in the same relative layout → imports unchanged.
- `dashboard.component.spec.ts` imports `./dashboard.model` → moves alongside → unchanged.
- `@mesell/*` imports (ui-kit, composites) are workspace aliases → unchanged regardless of physical location.

**After the move:** `frontend/src/app/features/landing/` and `frontend/src/app/features/dashboard/` directories are EMPTY and removed (git mv handles this; confirm no orphan files remain — e.g. an `index.ts` barrel; there is none on develop).

**Forbidden during the move:** any edit to logic, templates, `styles:[...]`, selectors, decorators (incl. the `providers: [DashboardApiService]` array — KEEP it), or imports beyond path context. `git log --follow` on each file must show preserved history. `git diff -M` on the move must show R100 (pure rename) with no `-`/`+` content lines except none.

---

## 2. Exact new files (full deterministic content)

### 2.1 `frontend/apps/mfe-dashboard/federation.config.js` (NEW)

```js
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 04 — remote `mfe-dashboard` (F1 landing + F6 dashboard,
// routes / [public] + /dashboard [authenticated]). The FOURTH extraction and the
// FIRST remote to federate a PUBLIC pre-auth route. Exposes TWO components living on
// OPPOSITE sides of the shell's authGuard (D26): LandingComponent (public) and
// DashboardComponent (shell-guarded).
//
// R-SP3-1 (P0): neither page injects AuthService, so @mesell/core is not strictly
// required by the import graph. It is kept in the shared/singleton set for contract
// uniformity (D22 C1) via shareAll. ignoreUnusedDeps may still prune it from this
// remote's remoteEntry shared[] (correct — same as mfe-pricing/mfe-export, which also
// omit @mesell/core). That is NOT drift: drift only matters for a lib a remote DOES
// consume. @mesell/ui-kit, @mesell/composites, @angular/*, rxjs resolve to the shell's
// instances (MASTER_PLAN §6.1).
module.exports = withNativeFederation({
  name: 'mfe-dashboard',

  exposes: {
    './LandingComponent': './apps/mfe-dashboard/src/app/landing.component.ts',
    './DashboardComponent': './apps/mfe-dashboard/src/app/dashboard.component.ts',
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

> **`exposes` path format is repo-root-relative** (`./apps/mfe-dashboard/src/app/...`) — verified against the as-built mfe-onboarding config. Do NOT use `./src/app/...` or absolute paths.

### 2.2 `frontend/apps/mfe-dashboard/src/main.ts` (NEW) — **R-SP3-1 P0: routes BOTH exposes**

```ts
// mfe-dashboard — dev-serve / standalone bootstrap entry ONLY.
// In federation each component is mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 (P0): main.ts MUST reference BOTH exposed components. Native Federation's
// `ignoreUnusedDeps` analyzer (Sheriff) prunes shared-mappings from the import graph
// rooted at THIS main.ts. Routing to BOTH LandingComponent and DashboardComponent keeps
// every shared lib either page consumes (@mesell/ui-kit, @mesell/composites) in the
// analysis graph so they stay shared+singleton and resolve to the shell's import-map
// instances. Referencing only one expose would let a lib used solely by the OTHER expose
// get inlined into that component's chunk → silent singleton drift. (Mirrors mfe-onboarding.)
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, type Routes } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { LandingComponent } from './app/landing.component';
import { DashboardComponent } from './app/dashboard.component';

const devRoutes: Routes = [
  { path: '', component: LandingComponent },
  { path: 'dashboard', component: DashboardComponent },
];

bootstrapApplication(LandingComponent, {
  providers: [
    provideRouter(devRoutes),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));
```

> Both `LandingComponent` and `DashboardComponent` are imported AND referenced in `devRoutes`. This is the load-bearing R-SP3-1 guard. Do not remove either import even though dev-serve only bootstraps `LandingComponent`.

### 2.3 `frontend/apps/mfe-dashboard/src/app/public-api.ts` (NEW)

```ts
// mfe-dashboard — public surface (the federation typed boundary, MASTER_PLAN §6.5).
// Multi-expose remote: re-exports BOTH exposed components. The shell's
// loadRemoteWithFallback helper resolves each exposed symbol from one remoteEntry.json.
export { LandingComponent } from './landing.component';
export { DashboardComponent } from './dashboard.component';
```

### 2.4 `frontend/apps/mfe-dashboard/src/index.html` (NEW)

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>mfe-dashboard</title>
  <base href="/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/primeicons/primeicons.css">
</head>
<body>
  <!-- Standalone dev-serve host only. In federation the Landing/Dashboard components
       are mounted INTO the shell's router outlet via loadRemoteModule; this index is
       not used there. main.ts bootstraps LandingComponent for the dev server. -->
  <app-landing></app-landing>
</body>
</html>
```

> **GOTCHA (SP01, costs a build cycle):** `@angular/build:application` REQUIRES `index.html` or the remote build fails "Failed to read index HTML file." The host element is the LANDING selector `<app-landing>` (verified: `selector: 'app-landing'`), matching the component main.ts bootstraps. (Dashboard selector is `app-dashboard` — not used here.)

### 2.5 `frontend/apps/mfe-dashboard/tsconfig.app.json` (NEW)

```jsonc
/* mfe-dashboard remote — app build tsconfig. Extends the workspace base
   (inherits strict mode + the @mesell/* path aliases). */
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "../../out-tsc/mfe-dashboard",
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

## 3. Exact shared-file diffs (additive / minimal — SP05 runs in parallel)

> **SP05 (mfe-catalog) parallel-wave discipline:** `app.routes.ts`, `federation.manifest.json`, `angular.json`, `package.json`, `tsconfig.spec.json` are shared with the concurrent SP05 session. ALL edits below are ADDITIVE (add lines, never reformat/reorder existing entries). Before the founder-gate PR, the integration branch MUST `git merge origin/develop` and keep-both any SP05 overlap (see §4).

### 3.1 `frontend/src/app/app.routes.ts` — TWO swaps (additive in spirit; the two `import()` loaders become helper calls)

**Swap A — PUBLIC top-level `''` route.** Find this block (the FIRST `path: ''`, the public landing, NOT the protected shell parent):

```ts
  // Root — public landing page
  {
    path: '',
    loadComponent: () =>
      import('./features/landing/landing.component').then(m => m.LandingComponent),
    pathMatch: 'full',
  },
```

Replace with:

```ts
  // MF Sub-Plan 04 — mfe-dashboard remote (apps/mfe-dashboard/). The PUBLIC landing
  // page now lives in the `mfe-dashboard` Native-Federation remote, loaded at runtime
  // via the manifest. NO authGuard (public, pre-auth); pathMatch:'full' preserved so it
  // matches ONLY the empty path. D12 fallback on load failure. The remoteEntry is a
  // static public asset — fetched with no Authorization header (D27/D29).
  {
    path: '',
    loadComponent: loadRemoteWithFallback('mfe-dashboard', './LandingComponent'),
    pathMatch: 'full',
  },
```

> `pathMatch: 'full'` MUST be preserved. NO `canActivate`. This route MUST stay a TOP-LEVEL route (a sibling of the protected shell parent), not become a shell child.

**Swap B — PRIVATE shell-child `dashboard` route.** Find this block (inside the `children:` array of the protected empty-path parent that has `canActivate: [authGuard]`):

```ts
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
      },
```

Replace with:

```ts
      {
        // MF Sub-Plan 04 — mfe-dashboard remote (apps/mfe-dashboard/). The dashboard
        // page now lives in the `mfe-dashboard` Native-Federation remote, loaded at
        // runtime via the manifest. The parent's authGuard (canActivate on the shell
        // empty-path parent) UNCHANGED — the guard runs in the SHELL before the remote
        // is fetched (D27): an unauthenticated visitor is redirected to /login WITHOUT
        // downloading the dashboard remoteEntry. The remote does NOT self-guard and does
        // NOT inject AuthService. D12 fallback on load failure.
        path: 'dashboard',
        loadComponent: loadRemoteWithFallback('mfe-dashboard', './DashboardComponent'),
      },
```

> The parent `canActivate: [authGuard]` is UNCHANGED (D27). Do NOT add a guard to this child. Do NOT remove the parent guard.

**Import header:** `loadRemoteWithFallback` is ALREADY imported at the top of `app.routes.ts` (`import { loadRemoteWithFallback } from './core/load-remote';`) — verified. Do NOT re-import it. After the two swaps, the file should have ZERO remaining `import('./features/landing/...')` and ZERO `import('./features/dashboard/...')` dynamic imports.

### 3.2 `frontend/public/federation.manifest.json` — add fourth entry (additive)

Current:
```json
{
  "mfe-pricing": "http://localhost:4201/remoteEntry.json",
  "mfe-export": "http://localhost:4202/remoteEntry.json",
  "mfe-onboarding": "http://localhost:4203/remoteEntry.json"
}
```

Add ONE line (keep the existing three byte-identical):
```json
{
  "mfe-pricing": "http://localhost:4201/remoteEntry.json",
  "mfe-export": "http://localhost:4202/remoteEntry.json",
  "mfe-onboarding": "http://localhost:4203/remoteEntry.json",
  "mfe-dashboard": "http://localhost:4204/remoteEntry.json"
}
```

> Port **4204** (master-assigned registry: 4201 pricing / 4202 export / 4203 onboarding / **4204 dashboard** / 4205 catalog-reserved / 4206 auth-reserved). This dev localhost URL; prod `https://remotes.mesell.xyz/{env}/mfe-dashboard/{version}/remoteEntry.json` is infra-owned (D29 memo).

### 3.3 `frontend/angular.json` — add `projects.mfe-dashboard` block (additive — port 4204 in TWO places)

Add this complete project block alongside the existing `mfe-pricing`/`mfe-export`/`mfe-onboarding` keys (do NOT touch the `frontend` shell project or the other remote projects). It is the mfe-onboarding block with every `mfe-onboarding` token replaced by `mfe-dashboard` and **both port occurrences set to 4204**:

```jsonc
"mfe-dashboard": {
  "projectType": "application",
  "schematics": {},
  "root": "apps/mfe-dashboard",
  "sourceRoot": "apps/mfe-dashboard/src",
  "prefix": "app",
  "architect": {
    "build": {
      "builder": "@angular-architects/native-federation:build",
      "options": {},
      "configurations": {
        "production": { "target": "mfe-dashboard:esbuild:production" },
        "development": { "target": "mfe-dashboard:esbuild:development", "dev": true }
      },
      "defaultConfiguration": "production"
    },
    "serve": {
      "builder": "@angular-architects/native-federation:build",
      "options": {
        "target": "mfe-dashboard:serve-original:development",
        "rebuildDelay": 500,
        "dev": true,
        "cacheExternalArtifacts": false,
        "port": 4204
      }
    },
    "esbuild": {
      "builder": "@angular/build:application",
      "options": {
        "browser": "apps/mfe-dashboard/src/main.ts",
        "index": "apps/mfe-dashboard/src/index.html",
        "tsConfig": "apps/mfe-dashboard/tsconfig.app.json",
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
        "production": { "buildTarget": "mfe-dashboard:esbuild:production" },
        "development": { "buildTarget": "mfe-dashboard:esbuild:development" }
      },
      "defaultConfiguration": "development",
      "options": { "port": 4204 }
    }
  }
}
```

> **Port 4204 appears TWICE** in this block (the `serve.options.port` AND the `serve-original.options.port`) — Wave 1 had a 4202 collision from missing one. Set BOTH to 4204. `styles` is `["src/styles.css"]` (the SHELL's single Tailwind build — verified identical across all remotes).

### 3.4 `frontend/package.json` — add ONE script line (additive)

In `scripts`, add (after `start:mfe-onboarding`):
```json
"start:mfe-dashboard": "ng serve mfe-dashboard"
```
> Port is pinned in angular.json serve options (4204), NOT in the script flag — consistent with `start:mfe-export` / `start:mfe-onboarding` which carry no `--port`. (Only `start:shell` and `start:mfe-pricing` carry explicit flags; the convention for SP02+ is the bare `ng serve <name>` form. Match the SP02/SP03 form.)

### 3.5 Test-discovery + Tailwind — RE-CONFIRM ONLY (no edit)

- `frontend/angular.json` → `projects.frontend.architect.test.options.include` ALREADY = `["**/*.spec.ts", "../libs/**/*.spec.ts", "../apps/**/*.spec.ts"]` — the `../apps/**` glob covers `apps/mfe-dashboard/`. **Do NOT add a duplicate.**
- `frontend/tsconfig.spec.json` `include` ALREADY has `apps/**/*.spec.ts` + `apps/**/*.d.ts`. **No edit.**
- `frontend/src/styles.css` ALREADY has `@source "../apps";`. **No edit.**
- Confirm these three are present (read them); if ANY is missing the apps glob, STOP and report (do not edit — that would mean develop drifted from the recipe).

---

## 4. Branch / PR plan (Model C — repo-mgmt §1.2 F1; D1 gates)

Feature slug: `mfe-dashboard`. Worktree under `/tmp/mesell-wt/`.

### 4.1 Branch setup (run at EXECUTION start; never branch-switch the master tree)

```bash
git fetch origin develop
# Create integration off develop WITHOUT checking out in the master tree:
git branch feature/mfe-dashboard/integration origin/develop
git push -u origin feature/mfe-dashboard/integration
# Create the frontend group branch off integration:
git branch feature/mfe-dashboard/frontend feature/mfe-dashboard/integration
git push -u origin feature/mfe-dashboard/frontend
# Worktree for all work:
git worktree add /tmp/mesell-wt/sp04-mfe-dashboard feature/mfe-dashboard/frontend
```

### 4.2 F3 branch protection on the integration branch (apply via JSON body file — flag-mixing produces malformed payload)

```bash
cat > /tmp/sp04-protection.json <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
gh api -X PUT repos/Mugunthan93/<repo>/branches/feature/mfe-dashboard/integration/protection \
  --input /tmp/sp04-protection.json
```
> required_status_checks null + review-count 0 (lets the lead squash-merge the group PR without a second approver — single-account self-approval is blocked, so the lead records an APPROVE comment instead). Force-push off, deletions off (F3 profile, matches SP01-03).

### 4.3 PR flow

```
feature/mfe-dashboard/frontend
        │  PR #A — FRONTEND LEAD reviews + SQUASH-merges   [D1 — lead's gate]
        ▼
feature/mfe-dashboard/integration
        │  (BEFORE opening #B: git merge origin/develop into integration; resolve any
        │   SP05 overlap keep-both; re-run build+test to confirm conflict-free)
        │  PR #B — FOUNDER reviews + merges (merge-commit)  [D1 — founder's gate]
        ▼
develop
```

- **PR #A (group → integration):** opened by the specialist; specialist sets board row to `IN REVIEW` on open (D2). Lead reviews against the §5 checklist + the PR template, then `gh pr merge --squash --admin --delete-branch` (the lead's gate). Lead sets board `MERGED` on merge (D2).
- **PR #B (integration → develop):** opened + LEFT OPEN, titled `[FOUNDER GATE — DO NOT MERGE]`, with the full §5 scorecard in the body. **The lead does NOT approve or merge #B — it is the founder's gate (D1).**
- **Stale-integration guard (SP02 learning):** before merging develop into integration, `git reset --hard origin/feature/mfe-dashboard/integration` if the local integration ref is behind, ELSE a fast-forward can silently drop the group-PR code. Merge develop AFTER the group PR has landed on integration.

### 4.4 PR template
Fill `.github/PULL_REQUEST_TEMPLATE/frontend.md` COMPLETELY — no `<>` placeholders (a leftover placeholder = HARD REJECT at the lead gate). Session block = `mesell-mfe-dashboard-frontend-session-1`.

---

## 5. Validation checklist (the specialist runs ALL of these and pastes evidence)

Build/test run in the worktree. **pnpm worktree fix (SP01 clean form):** `pnpm install --config.dangerously-allow-all-builds=true` (then if esbuild binary still missing on darwin, `pnpm rebuild esbuild`), then run `./node_modules/.bin/ng build <proj>` DIRECTLY (NOT `pnpm build` — its implicit deps-check re-fails on IGNORED_BUILDS). Revert any `pnpm-workspace.yaml` drift with `git checkout pnpm-workspace.yaml` before staging.

### 5.A Acceptance criteria (SUB_PLAN §9.A reused — paste evidence per line)

- [ ] **PR #A merged** by Frontend Lead (squash) — N/A at specialist run; lead does this.
- [ ] `./node_modules/.bin/ng build mfe-dashboard` GREEN → produces `dist/mfe-dashboard/browser/remoteEntry.json` exposing BOTH `./LandingComponent` + `./DashboardComponent` (paste seconds + `curl`/`cat` of remoteEntry.json `exposes`).
- [ ] Shell `./node_modules/.bin/ng build frontend` (or `ng build`) GREEN and **≤ 90 s** (D12 stop condition) — paste seconds + the initial bundle line (note delta vs prior; expect landing + dashboard chunks to LEAVE the shell, so initial should be flat or smaller).
- [ ] `ng test` (`@angular/build:unit-test`) total == **43 spec files / 408 tests, 0 failing, 0 skipped** — paste the summary line. A DROP (spec not discovered) OR an unrequested increase = HARD REJECT.
  - Confirm `landing.component.spec.ts` + `dashboard.component.spec.ts` are discovered at their NEW `apps/mfe-dashboard/` path (grep the test reporter for the relocated spec identifiers).
- [ ] **Boundary grep zero:** `grep -rn "from 'primeng" frontend/apps/mfe-dashboard frontend/src --include=*.ts | grep -v "libs/ui-kit/"` returns ZERO lines. (No new PrimeNG leak from the moved files; landing/dashboard import only `@mesell/*`.) Paste the (empty) output.
- [ ] **PUBLIC route:** unauth visitor at `/` renders the remote `LandingComponent` — no guard, no redirect, `pathMatch:'full'` preserved. (Headless: the route resolves to the helper; in-browser screenshot handed forward — pure rename = zero visual delta.)
- [ ] **PRIVATE-blocked (D27):** unauth visitor at `/dashboard` is redirected to `/login` by the SHELL `authGuard` WITHOUT fetching the dashboard `remoteEntry` (the guard runs before the remote loads). Demonstrate via the guard-runs-in-shell routing config (the child has no guard; the parent does) + a smoke assertion if feasible.
- [ ] **PRIVATE-allowed:** authenticated visitor at `/dashboard` renders the remote `DashboardComponent`.
- [ ] **`DashboardApiService` resolves** — the component-level `providers: [DashboardApiService]` survived the move (no NullInjectorError). Paste the `providers:` line from the moved `dashboard.component.ts` as evidence it was preserved.
- [ ] **FOUR remotes coexist** in `public/federation.manifest.json` (pricing, export, onboarding, dashboard) — paste the manifest.
- [ ] **D12 fallback proof:** a deliberately-broken `mfe-dashboard` manifest URL degrades to `RemoteFailureComponent`, not a white screen. Headless form (SP01 recipe): serve `dist/mfe-dashboard/browser/` static on :4204, `curl remoteEntry.json` → 200, `curl <broken-url>` → 404 (proves loadRemoteModule rejects → `.catch` → fallback). The existing `load-remote.spec.ts` already asserts the fallback path — confirm it still passes.

### 5.B Move integrity

- [ ] `git log --follow apps/mfe-dashboard/src/app/landing.component.ts` (and the other 5) shows preserved history.
- [ ] `git diff -M --stat` on the 6 moves shows R100 renames (no content `+`/`-`).
- [ ] `frontend/src/app/features/landing/` + `frontend/src/app/features/dashboard/` are GONE.
- [ ] The shell `federation.config.js` is UNCHANGED (`name: 'shell'`).

### 5.C Headless validation recipe (no browser in build env — SP01 §9.A pattern)
- Build remote → `python3 -m http.server 4204 -d dist/mfe-dashboard/browser` → curl remoteEntry.json (200) + each exposed chunk (200) + a broken URL (404 → fallback path). Full in-browser mount + 360/1280 screenshots of `/` and `/dashboard` handed forward to the screenshot capture (pure rename = zero visual delta by construction).

---

## 6. STOP conditions (HALT and report to the Lead — do NOT improvise)

The specialist MUST stop and report (not work around) if ANY occurs:

1. **Shell build > 90 s** (D12 stop condition) — even though MF is the mitigation, escalate.
2. **Test count != 43 files / 408 tests** (drop OR unrequested increase) — silent non-discovery or an unsanctioned new spec.
3. **Boundary grep returns ANY new PrimeNG import** under `apps/mfe-dashboard/`.
4. **`DashboardApiService` NullInjectorError at runtime** — means the `providers:` array was dropped on the move (should be impossible if the component moved intact; if it happens, the component was edited — revert and report).
5. **The public `''` route swap requires touching `pathMatch` or adding a guard** to make it work — that means the routing model differs from this spec; STOP (do not invent a guard or drop pathMatch).
6. **Unauth `/dashboard` fetches the dashboard remoteEntry before redirecting** — the guard is not running in the shell before the load; report (do not move the guard into the remote).
7. **A required relative import (`./dashboard.model` / `./services/dashboard-api.service`) breaks** after the move — means the `services/` subdir or model was not moved alongside; fix the move (do not rewrite the import to an alias).
8. **`develop` lacks the SP01/02/03 remotes** or the test/Tailwind globs are MISSING the `apps/**` pattern — means develop drifted from the recipe; STOP (do not re-add the globs blindly).
9. **A merge conflict with SP05** on a shared file that is NOT a clean keep-both (e.g. SP05 reformatted a shared block) — STOP and report for lead-mediated resolution.
10. **Any temptation to edit landing/dashboard/model/service logic, templates, or selectors** — relocation is rename-only; STOP if a logic change seems "needed."
11. **Iteration cap = 3** re-dispatches; the third auto-escalates to the founder.

---

## 7. Forbidden (NEVER)

- Add a guard or AuthService into `DashboardComponent` or `LandingComponent` (D27).
- Promote `dashboard.model.ts` / `DashboardApiService` to `libs/core` (D28).
- Re-author `load-remote.ts` / `remote-failure.component.ts` (REUSE — SP02 D15).
- Move the shell into `apps/shell/` (D9 — deferred to SP07).
- Author CSP (D14 — deferred to SP07).
- Touch `backend/`, `k8s/`, `infra/`, or other remotes (`apps/mfe-pricing|export|onboarding/`) or other features.
- Touch the shell `frontend` angular.json project, the shell `federation.config.js`, or `libs/**`.
- Approve PR #B (founder's gate, D1).
- Reformat/reorder existing entries in any shared file (SP05 parallel-wave — additive only).

---

## 8. Final report format (specialist returns this, then STOPS for lead review + PR)

```
Files moved (count, all R100): 6
Files new (count): 5  (federation.config.js, main.ts, public-api.ts, index.html, tsconfig.app.json)
Shared files edited (additive): app.routes.ts (2 swaps), federation.manifest.json (+1), angular.json (+mfe-dashboard, port 4204 x2), package.json (+start:mfe-dashboard)
Remote build (ng build mfe-dashboard): <seconds> GREEN → remoteEntry.json exposes ./LandingComponent + ./DashboardComponent
Shell build: <seconds> GREEN ≤90s; initial bundle <kB> (delta vs baseline)
Tests: <files>/<tests> (MUST be 43/408), 0 fail / 0 skip; relocated specs discovered at apps/mfe-dashboard/
Boundary grep: <empty output>
PUBLIC '/' : renders LandingComponent, no guard, pathMatch:full
PRIVATE-blocked /dashboard (unauth): shell authGuard → /login, remoteEntry NOT fetched
PRIVATE-allowed /dashboard (auth): renders DashboardComponent
DashboardApiService: providers:[DashboardApiService] preserved (paste line) — resolves, no NullInjectorError
Manifest: FOUR entries (paste)
D12 fallback: broken URL → 404 → RemoteFailureComponent (load-remote.spec.ts green)
```

Then STOP. Do NOT open PR #B (founder gate). Set board `IN REVIEW` on PR #A open.
