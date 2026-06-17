# TASK SPEC — SP05 `mfe-catalog` extraction (HYBRID-RULE step 1 of 3)

**Author:** meesell-frontend-coordinator (Frontend Lead) · **Date:** 2026-06-11
**For execution by:** `meesell-angular-component-builder` (Phase A+B) then `meesell-angular-service-builder` (Phase C) — verbatim, zero judgment calls.
**Ground truth:** `docs/plans/module_federation/SUB_PLAN_05_catalog_extraction.md` (D33 RULED 2026-06-11) + `sub_plan_01_pricing.md` recipe + R-SP3-1 forward rule.
**Develop tip at spec time:** `e64fa82` (PR#68 merged). 3 remotes live: mfe-pricing :4201, mfe-export :4202, mfe-onboarding :4203.
**Port assignment (master):** **mfe-catalog = 4205** (4204 dashboard-reserved, 4206 auth-reserved).

> ROUTES TOUCHED: `/catalogs`, `/catalogs/new`, `/catalogs/:id/edit`, `/catalogs/:id/images`, `/catalogs/:id/preview` (5 — the funnel). NOT touched: `/catalogs/:id/pricing` (mfe-pricing, already remote), `/catalogs/:id/export` (mfe-export, already remote).
> SPECIALISTS: component-builder (extraction + Routes-array expose + shell wiring) → service-builder (provider-scope verify + D33 model promotion). Dispatch order is strict-sequential; service-builder starts only after component-builder Phase B is green.

---

## 0. Verified-reality preface (read before anything — these correct/refine SUB_PLAN_05 illustrative claims)

1. **`SmartPickerApiService` is COMPONENT-scoped, NOT route-scoped.** Verified `frontend/src/app/features/catalog-new/catalog-new.component.ts` line 111 = `providers: [SmartPickerApiService]` on the `@Component`. It is `@Injectable()` no-providedIn. → It travels with the COMPONENT automatically on relocation (no route-providers needed). SUB_PLAN_05 §3-row-3 said "preserve its provider scope" — concretely: leave the `providers:[SmartPickerApiService]` on the component decorator untouched. Do NOT move it to the route.
2. **`CatalogFormApiService` IS route-scoped** via `catalog-form.routes.ts` → `providers:[CatalogFormApiService]` (verified). This is the D32 case. It must move to the `:id/edit` entry of the new `catalog.routes.ts`.
3. **D33 AMBIGUITY (flag — bake into service-builder spec):** there is NO existing canonical `Product` or `Catalog` entity type in any catalog page model today. The model files hold ONLY page-private DTOs/state: `catalog-form.model.ts` (SaveStatus, AiSuggestionsMap, FieldValuesMap + pure fns), `models/field-schema.model.ts` (FieldGroup/FieldSchema), `smart-picker.model.ts` (CategorySuggestionModel, CreateProductRequest/ResponseModel, PickerState), `image-uploader.model.ts` (PrecheckResult, ProductImage, PrecheckItem), `preview.model.ts` (PreviewData, MobileTile, PreviewTab). NONE is named `Product`/`Catalog`; NONE is imported cross-remote (grep proof required). → See §4 for the exact D33 handling: the service-builder does a SURGICAL promotion of ONLY genuinely-cross-boundary canonical types; if none exists as a named entity, it MUST NOT synthesize/over-promote — it records the finding and reports to the Lead (do-nothing on `libs/core` is a valid, expected outcome). This is a Lead-review decision point, not a specialist judgment call.
4. **`SmartPickerApiService` and `CatalogFormApiService` each have a duplicate inline interface** (e.g. `CategorySuggestion`/`CreateProductRequest` in the service file AND `*Model` variants in the model file). These are page-private — leave as-is, do NOT consolidate (out of scope; relocation only).
5. **Catalog routes on develop are NOT collapsed** — `app.routes.ts` (verbatim §3) has 5 SEPARATE protected children for the funnel (`catalogs`, `catalogs/new`, `catalogs/:id/edit` via loadChildren, `catalogs/:id/images`, `catalogs/:id/preview`) PLUS the two already-remote `catalogs/:id/pricing` + `catalogs/:id/export`. SP05 collapses ONLY the 5 funnel children into one `catalogs` loadChildren; it must NOT touch the pricing/export remote routes.

---

## 1. EXACT FILE MOVES (source → destination)

All moves via `git mv` to preserve history. `@mesell/*` imports stay UNCHANGED. Relative imports within a moved subtree stay valid because subtree shape is preserved. ZERO logic/template edits.

| # | Source (on develop `e64fa82`) | Destination | Mode |
|---|---|---|---|
| 1 | `frontend/src/app/features/catalog-new/catalog-new.component.ts` | `frontend/apps/mfe-catalog/src/app/catalog-new/catalog-new.component.ts` | rename-only |
| 2 | `frontend/src/app/features/catalog-new/catalog-new.component.spec.ts` | `frontend/apps/mfe-catalog/src/app/catalog-new/catalog-new.component.spec.ts` | rename-only |
| 3 | `frontend/src/app/features/catalog-new/smart-picker.model.ts` | `frontend/apps/mfe-catalog/src/app/catalog-new/smart-picker.model.ts` | rename-only |
| 4 | `frontend/src/app/features/catalog-new/services/smart-picker-api.service.ts` | `frontend/apps/mfe-catalog/src/app/catalog-new/services/smart-picker-api.service.ts` | rename-only |
| 5 | `frontend/src/app/features/catalog-form/catalog-form/catalog-form.component.ts` | `frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form/catalog-form.component.ts` | rename-only* |
| 6 | `frontend/src/app/features/catalog-form/catalog-form/catalog-form.component.spec.ts` | `frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form/catalog-form.component.spec.ts` | rename-only |
| 7 | `frontend/src/app/features/catalog-form/catalog-form.model.ts` | `frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form.model.ts` | rename-only* |
| 8 | `frontend/src/app/features/catalog-form/models/field-schema.model.ts` | `frontend/apps/mfe-catalog/src/app/catalog-form/models/field-schema.model.ts` | rename-only |
| 9 | `frontend/src/app/features/catalog-form/services/catalog-form-api.service.ts` | `frontend/apps/mfe-catalog/src/app/catalog-form/services/catalog-form-api.service.ts` | rename-only |
| 10 | `frontend/src/app/features/images/image-uploader/image-uploader.component.ts` | `frontend/apps/mfe-catalog/src/app/images/image-uploader/image-uploader.component.ts` | rename-only |
| 11 | `frontend/src/app/features/images/image-uploader/image-uploader.component.spec.ts` | `frontend/apps/mfe-catalog/src/app/images/image-uploader/image-uploader.component.spec.ts` | rename-only |
| 12 | `frontend/src/app/features/images/image-uploader/image-uploader.model.ts` | `frontend/apps/mfe-catalog/src/app/images/image-uploader/image-uploader.model.ts` | rename-only |
| 13 | `frontend/src/app/features/preview/preview/preview.component.ts` | `frontend/apps/mfe-catalog/src/app/preview/preview/preview.component.ts` | rename-only* |
| 14 | `frontend/src/app/features/preview/preview/preview.component.spec.ts` | `frontend/apps/mfe-catalog/src/app/preview/preview/preview.component.spec.ts` | rename-only |
| 15 | `frontend/src/app/features/preview/preview/preview.model.ts` | `frontend/apps/mfe-catalog/src/app/preview/preview/preview.model.ts` | rename-only* |
| 16 | `frontend/src/app/features/catalogs/catalog-list.component.ts` | `frontend/apps/mfe-catalog/src/app/catalog-list.component.ts` | rename-only |

\* Files marked `*` are rename-only in PHASE A (component-builder), and MAY receive a single import-line re-point in PHASE C (service-builder) IF and ONLY IF the D33 promotion finds a genuinely-cross-boundary type in them (see §4). The component-builder does NOT edit any file content.

**Preserve subtree shape.** Note rows 5/6 keep the nested `catalog-form/catalog-form/` doubled dir and rows 13/14/15 keep `preview/preview/` — these are the as-built shapes; preserving them keeps every relative import (`./catalog-form.model`, `../models/field-schema.model`, `./services/...`, `./preview.model`) valid with zero edits. Do NOT flatten.

**`git mv` verification:** after all moves, `git status` shows each as `renamed:`. If any shows `deleted:`+`added:` (history break), redo as `git mv`.

**Empty-dir cleanup:** after moves, `frontend/src/app/features/{catalog-new,catalog-form,images,preview,catalogs}/` must be GONE (git removes emptied tracked dirs automatically; verify no stray files remain via `git ls-tree`).

---

## 2. EXACT NEW FILES (full deterministic content)

### 2.1 `frontend/apps/mfe-catalog/src/app/catalog.routes.ts` (NEW — the `./CatalogRoutes` expose; D31/D32/D34)

```ts
// mfe-catalog — the remote-owned Routes array. The ONLY federation expose
// (./CatalogRoutes). Internalises all 5 funnel route targets so the shell mounts
// the whole catalog sub-tree with ONE loadChildren (D31). Route order: 'new' MUST
// precede ':id/edit' so the literal 'new' is not captured as an :id (R-SP5-2).
// The :id/edit route carries providers:[CatalogFormApiService] — the route-scoped
// service preserved EXACTLY from the subsumed catalog-form.routes.ts (D32/D34).
import { Routes } from '@angular/router';
import { CatalogFormApiService } from './catalog-form/services/catalog-form-api.service';

export const CATALOG_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./catalog-list.component').then(m => m.CatalogListComponent),
  },
  {
    path: 'new',
    loadComponent: () =>
      import('./catalog-new/catalog-new.component').then(m => m.CatalogNewComponent),
  },
  {
    path: ':id/edit',
    loadComponent: () =>
      import('./catalog-form/catalog-form/catalog-form.component').then(m => m.CatalogFormComponent),
    providers: [CatalogFormApiService],
  },
  {
    path: ':id/images',
    loadComponent: () =>
      import('./images/image-uploader/image-uploader.component').then(m => m.ImageUploaderComponent),
  },
  {
    path: ':id/preview',
    loadComponent: () =>
      import('./preview/preview/preview.component').then(m => m.PreviewComponent),
  },
];
```

(The `loadComponent` import paths exactly match the preserved subtree shape from §1: note the doubled `catalog-form/catalog-form/` and `preview/preview/` dirs.)

### 2.2 `frontend/apps/mfe-catalog/src/app/public-api.ts` (NEW — typed boundary, §6.5)

```ts
// mfe-catalog — public federation boundary. Re-exports ONLY the Routes array
// consumed by the shell via loadRemoteModule('mfe-catalog','./CatalogRoutes').
export { CATALOG_ROUTES } from './catalog.routes';
```

### 2.3 `frontend/apps/mfe-catalog/federation.config.js` (NEW — clone of mfe-pricing with catalog tokens)

```js
const { withNativeFederation, shareAll } = require('@angular-architects/native-federation/config');

// MF Sub-Plan 05 — remote `mfe-catalog` (R4): the 5-page catalog funnel
// (F7 smart-picker, F8 catalog-form, F9 images, F10 preview, + catalogs list).
// kind: 'remote' — produces remoteEntry.json + ESM chunks, mounted by the shell host.
// Exposes a Routes ARRAY (D31) — the FIRST non-component expose — because catalog
// owns a connected :id-threaded flow (MASTER_PLAN §2.4).
// @mesell/core (auth singleton — carries the promoted Product/Catalog after D33),
// @mesell/ui-kit, @mesell/composites, @angular/*, rxjs resolve to the SHELL's single
// instances via shareAll singleton:true (MASTER_PLAN §6.1).
module.exports = withNativeFederation({
  name: 'mfe-catalog',

  exposes: {
    './CatalogRoutes': './apps/mfe-catalog/src/app/catalog.routes.ts',
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

### 2.4 `frontend/apps/mfe-catalog/src/main.ts` (NEW — R-SP3-1 P0 CRITICAL: references ALL 5 route targets)

```ts
// mfe-catalog — dev-serve / standalone bootstrap entry ONLY.
// In federation the routes are mounted INTO the shell host via loadRemoteModule;
// this entry exists so the remote can be served independently for local validation.
//
// R-SP3-1 (P0 — SP05 is the HIGH-attention case): Native Federation's
// `ignoreUnusedDeps` analyzer (Sheriff) prunes shared-mappings from the import graph
// rooted at THIS main.ts. A shared lib (e.g. @mesell/core, which after D33 carries the
// promoted Product/Catalog types) consumed by an UNREACHED expose gets dropped from
// `shared[]` and INLINED into a component chunk → the remote gets its OWN copy →
// singleton drift (the SP03 bug). For a Routes-array expose, "all exposes reachable"
// means provideRouter(CATALOG_ROUTES) here — CATALOG_ROUTES references all 5 lazy
// loadComponent targets, so every page (and thus every shared lib any page consumes)
// stays in the analysis graph. Do NOT trim CATALOG_ROUTES here or short-circuit to a
// subset — the FULL route set must be reachable from main.ts (forward rule from SP03).
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { CatalogListComponent } from './app/catalog-list.component';
import { CATALOG_ROUTES } from './app/catalog.routes';

bootstrapApplication(CatalogListComponent, {
  providers: [
    provideRouter(CATALOG_ROUTES),
    provideAnimationsAsync(),
  ],
}).catch((err) => console.error(err));
```

> **R-SP3-1 enforcement note for component-builder:** after `ng build mfe-catalog`, the validation step (§6) MUST confirm `@mesell/core` and every other consumed `@mesell/*` lib appears in the remote's `shared[]` as its OWN chunk (`_mesell_core-*.js`, `_mesell_ui-kit-*.js`, etc.) and is NOT inlined into any page chunk. If `@mesell/core` is absent from `shared[]` AND no page consumes it, that is acceptable ONLY if the D33 promotion (Phase C) did not put a consumed type there yet — re-run this static check AGAIN after Phase C, because D33 may add a `@mesell/core` import to catalog-form/preview, which then MUST be shared. (This is the singleton non-drift proof in §6.)

### 2.5 `frontend/apps/mfe-catalog/src/index.html` (NEW — clone of mfe-pricing, host element = `app-catalog-list` per the `''`-route component selector)

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>mfe-catalog</title>
  <base href="/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/primeicons/primeicons.css">
</head>
<body>
  <!-- Standalone dev-serve host only. In federation the CATALOG_ROUTES are mounted
       INTO the shell's router outlet via loadRemoteModule; this index is not used there.
       main.ts bootstraps CatalogListComponent (the '' route component) as the dev host. -->
  <app-catalog-list></app-catalog-list>
</body>
</html>
```

> **HOST-ELEMENT GOTCHA (verify):** the body host tag must equal the `selector` of the component `main.ts` bootstraps (`CatalogListComponent`). Open `catalog-list.component.ts` and read its `selector:` — if it is NOT `app-catalog-list`, set the body tag to the actual selector. (mfe-pricing used `<app-pricing>` matching `app-pricing`.) The index is dev-serve-only; the federated mount ignores it.

### 2.6 `frontend/apps/mfe-catalog/src/bootstrap.ts`

NOT NEEDED. A remote (unlike the shell host) bootstraps directly in `main.ts` — mfe-pricing/mfe-onboarding have NO `bootstrap.ts`. Do not create one. (The `initFederation→import('./bootstrap')` split is a HOST-only pattern.)

### 2.7 `frontend/apps/mfe-catalog/tsconfig.app.json` (NEW — clone of mfe-pricing, retarget outDir)

```jsonc
/* mfe-catalog remote — app build tsconfig. Extends the workspace base
   (inherits strict mode + the @mesell/* path aliases). */
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "../../out-tsc/mfe-catalog",
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

## 3. EXACT SHARED-FILE DIFFS (additive/minimal — SP04 dashboard runs in parallel; keep disjoint)

> **PARALLEL-WAVE DISCIPLINE (SP04 sibling):** SP04 (dashboard, another specialist) edits the SAME four shared files (`app.routes.ts`, `federation.manifest.json`, `angular.json`, `package.json`). Make EVERY edit ADDITIVE and confined to the catalog lines only. Do NOT reorder or reformat unrelated entries. The integration branch must `git merge origin/develop` (picking up SP04 if it landed first) BEFORE the founder-gate PR opens (§5). If a merge conflict arises it will be in these 4 files only and is line-additive — resolve keep-both.

### 3.1 `frontend/src/app/core/load-remote.ts` (MODIFY — ADD the routes helper beside the existing component helper; D31)

ADD this function (do NOT remove/alter `loadRemoteWithFallback`):

```ts
import { Routes } from '@angular/router';

/**
 * SP05 (D31) — Routes-array variant of loadRemoteWithFallback. Returns a `loadChildren`
 * function that resolves a remote's exposed Routes array. On load failure the WHOLE
 * sub-tree degrades to a single catch-all route rendering RemoteFailureComponent
 * (MASTER_PLAN §6.4) — not a white screen. Authored ONCE here; catalog is the only
 * flow-owning (Routes-expose) remote in V1.
 */
export function loadRemoteRoutesWithFallback(remoteName: string, exposedModule: string) {
  return () =>
    loadRemoteModule({ remoteName, exposedModule })
      .then(m => (m['CATALOG_ROUTES'] ?? Object.values(m).find(Array.isArray)) as Routes)
      .catch(() => [{ path: '**', component: RemoteFailureComponent }] as Routes);
}
```

> Imports `loadRemoteModule`, `RemoteFailureComponent` already exist in the file (used by `loadRemoteWithFallback`). ADD the `Routes` import from `@angular/router` if not present. Prefer the explicit `m['CATALOG_ROUTES']` lookup first (the export name is known), falling back to the array-finder heuristic (R-SP5-1 mitigation).

### 3.2 `frontend/src/app/app.routes.ts` (MODIFY — collapse 5 funnel children → 1; D31/D34)

Within the protected Shell-layout parent's `children: [...]`:
- **REMOVE** these 5 child entries (verbatim on develop): `{ path: 'catalogs', loadComponent ... CatalogListComponent }`, `{ path: 'catalogs/new', ... CatalogNewComponent }`, `{ path: 'catalogs/:id/edit', loadChildren ... CATALOG_FORM_ROUTES }`, `{ path: 'catalogs/:id/images', ... ImageUploaderComponent }`, `{ path: 'catalogs/:id/preview', ... PreviewComponent }`.
- **DO NOT TOUCH** `{ path: 'catalogs/:id/pricing', loadComponent: loadRemoteWithFallback('mfe-pricing','./PricingComponent') }` or `{ path: 'catalogs/:id/export', loadComponent: loadRemoteWithFallback('mfe-export','./ExportComponent') }` — these remain as-is.
- **DO NOT TOUCH** the `profile`/`onboarding`/`dashboard` children.
- **ADD** exactly one child (place it where the old `catalogs` child was, so the diff reads cleanly):

```ts
      {
        // MF Sub-Plan 05 — mfe-catalog remote (apps/mfe-catalog/). The 5-page catalog
        // funnel (list, new/smart-picker, :id/edit, :id/images, :id/preview) now lives in
        // one Native-Federation remote exposing a Routes ARRAY (./CatalogRoutes) — the
        // FIRST routes-expose (D31). The shell collapses its 5 separate catalogs* children
        // into this ONE loadChildren (the strangler-fig win). The :id param flows through
        // the shell outlet into the remote routes unchanged. CatalogFormApiService stays
        // route-scoped inside the remote's catalog.routes.ts (D32). D12 fallback degrades
        // the whole sub-tree to RemoteFailureComponent on remote-load failure.
        path: 'catalogs',
        loadChildren: loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes'),
      },
```

- **UPDATE the import** at the top of `app.routes.ts`: change `import { loadRemoteWithFallback } from './core/load-remote';` to `import { loadRemoteWithFallback, loadRemoteRoutesWithFallback } from './core/load-remote';`.

> **BASE-PATH MATH (R-SP5-2 — verify):** shell base `catalogs` + remote `path:''` = `/catalogs`; + `'new'` = `/catalogs/new`; + `':id/edit'` = `/catalogs/:id/edit`; + `':id/images'` = `/catalogs/:id/images`; + `':id/preview'` = `/catalogs/:id/preview`. The pricing/export remotes stay as SIBLING children `catalogs/:id/pricing` + `catalogs/:id/export` (Angular matches the most specific literal first; the `catalogs` loadChildren parent does NOT shadow them because they are distinct sibling paths at the SAME level — VERIFY both still resolve after the change; if Angular routing precedence breaks them, that is a STOP condition — escalate, do not hack).

### 3.3 `frontend/public/federation.manifest.json` (MODIFY — add 5th entry; dev URL :4205)

From (develop):
```json
{
  "mfe-pricing": "http://localhost:4201/remoteEntry.json",
  "mfe-export": "http://localhost:4202/remoteEntry.json",
  "mfe-onboarding": "http://localhost:4203/remoteEntry.json"
}
```
To:
```json
{
  "mfe-pricing": "http://localhost:4201/remoteEntry.json",
  "mfe-export": "http://localhost:4202/remoteEntry.json",
  "mfe-onboarding": "http://localhost:4203/remoteEntry.json",
  "mfe-catalog": "http://localhost:4205/remoteEntry.json"
}
```
> Port 4205 (master assignment; 4204 dashboard-reserved). The Wave-1 4202 collision was an export/onboarding clash — confirm 4205 is unused (it is: 4201/4202/4203 taken). Prod URL `https://remotes.mesell.xyz/{env}/mfe-catalog/{version}/remoteEntry.json` is infra's (D35 memo); manifest stays localhost for dev.

### 3.4 `frontend/angular.json` (MODIFY — add `mfe-catalog` project block, port 4205)

ADD a new project key `"mfe-catalog"` as a sibling of `"mfe-onboarding"` (after it, before the closing of `projects`). Clone the verified `mfe-pricing` block VERBATIM, replacing every `mfe-pricing` token with `mfe-catalog` and the TWO port `4201` values with `4205`:

```jsonc
    "mfe-catalog": {
      "projectType": "application",
      "schematics": {},
      "root": "apps/mfe-catalog",
      "sourceRoot": "apps/mfe-catalog/src",
      "prefix": "app",
      "architect": {
        "build": {
          "builder": "@angular-architects/native-federation:build",
          "options": {},
          "configurations": {
            "production": { "target": "mfe-catalog:esbuild:production" },
            "development": { "target": "mfe-catalog:esbuild:development", "dev": true }
          },
          "defaultConfiguration": "production"
        },
        "serve": {
          "builder": "@angular-architects/native-federation:build",
          "options": {
            "target": "mfe-catalog:serve-original:development",
            "rebuildDelay": 500,
            "dev": true,
            "cacheExternalArtifacts": false,
            "port": 4205
          }
        },
        "esbuild": {
          "builder": "@angular/build:application",
          "options": {
            "browser": "apps/mfe-catalog/src/main.ts",
            "index": "apps/mfe-catalog/src/index.html",
            "tsConfig": "apps/mfe-catalog/tsconfig.app.json",
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
            "production": { "buildTarget": "mfe-catalog:esbuild:production" },
            "development": { "buildTarget": "mfe-catalog:esbuild:development" }
          },
          "defaultConfiguration": "development",
          "options": { "port": 4205 }
        }
      }
    }
```

> **TEST-DISCOVERY (R-SP5-3 — RE-CONFIRM, do NOT re-add):** the shell `frontend` project's `architect.test.options.include` already has `'../apps/**/*.spec.ts'` and `tsconfig.spec.json` already has `'apps/**/*.spec.ts'` (added at SP01, in place on develop). The new `apps/mfe-catalog/**/*.spec.ts` files are covered by the existing glob — NO edit expected. VERIFY by asserting the post-move test total (§6). A drop = silent non-discovery = HARD REJECT.
> **TAILWIND (re-confirm):** `src/styles.css` already has `@source "../apps"` (SP01) — covers `apps/mfe-catalog/`. No edit.

### 3.5 `frontend/package.json` (MODIFY — add ONE script line)

ADD to `"scripts"` (after `"start:mfe-onboarding"`):
```json
    "start:mfe-catalog": "ng serve mfe-catalog"
```
> Convention `start:mfe-<name>`. Port is pinned in angular.json serve target (4205) — the script does NOT pass `--port` (matches the as-built `start:mfe-export`/`start:mfe-onboarding` lines which omit it; only `start:shell` carries `--port 4200`). Manifest-safe.

### 3.6 Old file removal (D34)

`git rm frontend/src/app/features/catalog-form/catalog-form.routes.ts` — its single `:id/edit` route entry + `providers:[CatalogFormApiService]` is SUBSUMED into `catalog.routes.ts` (§2.1). Confirm no other file imports `CATALOG_FORM_ROUTES` after removal (grep — should be zero; the shell `app.routes.ts` loadChildren to it is removed in §3.2).

---

## 4. D33 MODEL-PROMOTION STEPS (service-builder, Phase C — SURGICAL; RULED 2026-06-11 APPROVED-as-recommended)

> **CRITICAL CONTEXT (from §0.3 verified reality):** NO file currently declares a canonical `Product` or `Catalog` ENTITY type. The catalog models hold page-private DTOs only. D33 promotes ONLY genuinely-cross-boundary canonical entity types. The service-builder MUST follow this decision tree and MUST NOT improvise:

**Step C-D33-1 — enumerate candidate cross-boundary types.** Grep every catalog model file for type/interface declarations. For each, grep the WHOLE `frontend/` tree (shell + all `apps/*` remotes + `libs/`) for cross-remote importers:
```bash
grep -rn "interface \|export type " frontend/apps/mfe-catalog/src/app --include=*.model.ts
# for each candidate type T, check cross-remote use:
grep -rn "\bT\b" frontend/src frontend/apps frontend/libs --include=*.ts | grep -v apps/mfe-catalog
```
**Step C-D33-2 — apply the surgical rule.**
- A type is PROMOTED to `libs/core/models/` ONLY IF it is (a) a canonical entity matching the §2.3 contract name (`Product` or `Catalog`) AND (b) imported by ≥1 file OUTSIDE `apps/mfe-catalog/` (another remote — e.g. a dashboard product-list type — or a future-Wave-6 contract that ALREADY exists in the tree).
- ALL page-private DTO/state/schema types (`PreviewData`, `MobileTile`, `CategorySuggestionModel`, `CreateProduct*Model`, `PickerState`, `ProductImage`, `PrecheckResult`, `PrecheckItem`, `FieldGroup`, `FieldSchema`, `SaveStatus`, `AiSuggestionsMap`, `FieldValuesMap`, etc.) STAY remote-local. Do NOT promote them.
**Step C-D33-3 — EXPECTED OUTCOME given verified reality:** because no named `Product`/`Catalog` entity exists today and none is cross-remote-imported (mfe-dashboard is not yet extracted — SP04 in flight, and even its `dashboard.model.ts` is remote-local per SP04 D28), the surgical rule likely yields **ZERO promotions**. THIS IS A VALID, EXPECTED RESULT. The service-builder MUST:
  - If zero qualify → create NO files in `libs/core/models/`; re-point NOTHING; record in the report + the memo: "D33: no canonical cross-boundary Product/Catalog entity exists as-built; promotion deferred to the Wave-6 backend-contract session that introduces the entity. Page-private DTOs verified single-remote (grep proof attached). `@mesell/core` barrel unchanged." STOP — this is a Lead-review decision, NOT a failure.
  - If a type genuinely qualifies → proceed to C-D33-4.
**Step C-D33-4 — IF (and only if) a type qualifies:** create `frontend/libs/core/models/<name>.model.ts` (e.g. `product.model.ts`, `catalog.model.ts`), move ONLY the canonical type there, ADD to the `@mesell/core` barrel (`frontend/libs/core/index.ts`): `export type { Product } from './models/product.model';` etc. Re-point the catalog pages' imports of that type to `from '@mesell/core'`. Verify the deep alias `@mesell/core/models/*` resolves via the SP0 `@mesell/core/*` wildcard (it maps to `libs/core/*`).
**Step C-D33-5 — record the dashboard-convergence forward note** in the memo regardless: "When mfe-dashboard (SP04) is extracted/reconciled, its product/catalog list types MAY re-point to any promoted `@mesell/core` canonical types — a SEPARATE post-SP05 follow-up PR, NOT touched here (SP05 must not edit a merged/sibling remote's internals)."

> **R5 mitigation (if any promotion happens):** the promoted types become a cross-remote contract → a change must rebuild the WHOLE workspace (C-CI-1 `shared/**`-rebuilds-all). Note in the infra memo (§5).
> **Lead pre-review on D33:** the Lead (step 3 of the hybrid rule) decides whether a zero-promotion outcome is correct or whether a canonical type should be authored — the specialist reports findings; it does NOT author a brand-new entity type speculatively.

---

## 5. BRANCH / PR PLAN (Model C — F1/F3)

Slug `mfe-catalog`. Worktree, never switch the master tree's branch.

### 5.1 Branch setup (Lead, EXECUTION stage — after founder approves THIS sub-plan to execute)
```bash
git fetch origin develop
# must include SP04 if it landed; develop tip at spec time = e64fa82
git branch feature/mfe-catalog/integration origin/develop
git push -u origin feature/mfe-catalog/integration
git branch feature/mfe-catalog/frontend feature/mfe-catalog/integration
git push -u origin feature/mfe-catalog/frontend
git worktree add /tmp/mesell-wt/sp05-catalog feature/mfe-catalog/frontend
```
(Use `git branch <name> <start>` + `git push`, NOT `checkout` — keeps the master tree untouched, per recurring memory.)

### 5.2 F3 protection on the integration branch (JSON-file body, NOT -f/-F flags)
```bash
cat > /tmp/sp05-protection.json <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
gh api -X PUT repos/Mugunthan93/mesell/branches/feature/mfe-catalog/integration/protection --input /tmp/sp05-protection.json
```
(Per memory: the `-f/-F` flag-mixing produces a malformed payload — use `--input <file>`. review-count 0 lets the lead squash-merge without a second approver; single-account self-approval is blocked so record the APPROVE as a PR comment.)

### 5.3 Worktree build prep (pnpm native-build gotcha)
```bash
cd /tmp/mesell-wt/sp05-catalog/frontend
pnpm install --config.dangerously-allow-all-builds=true   # ~4s, no .npmrc, no workspace.yaml drift
pnpm rebuild esbuild                                       # if the flag alone didn't extract darwin-arm64 esbuild (SP03 needed this)
./node_modules/.bin/ng build mfe-catalog                  # build remote DIRECTLY (NOT `pnpm build` — its deps-check re-fails)
git checkout pnpm-workspace.yaml 2>/dev/null || true      # revert any placeholder drift before staging
```
Add `**/tsconfig.federation.json` to `frontend/.gitignore` if not already present (SP03 added it; verify) — it is a per-build artefact, NEVER commit.

### 5.4 PR flow (Model C)
```
feature/mfe-catalog/frontend  --(PR, squash)-->  feature/mfe-catalog/integration   [Frontend Lead reviews+merges — D1]
feature/mfe-catalog/integration  --(PR, merge-commit)-->  develop                   [FOUNDER reviews+merges — lead must NOT approve — D1]
```
- Group PR: fill `.github/PULL_REQUEST_TEMPLATE/frontend.md` completely (no `<>` placeholders). Lead records APPROVE as a comment (self-approval block), then `gh pr merge --squash --admin --delete-branch`. If the worktree holds the branch, the GitHub merge still lands; recover the local branch-delete via `gh api -X DELETE repos/Mugunthan93/mesell/git/refs/heads/feature/mfe-catalog/frontend` + `git worktree remove --force /tmp/mesell-wt/sp05-catalog`.
- **Before the founder gate:** `git reset --hard origin/feature/mfe-catalog/integration` (sync local to the squashed state — avoids the SP02 stale-integration fast-forward bug that silently drops group-PR code), THEN `git merge origin/develop` (picks up SP04 if merged; resolve any keep-both conflict in the 4 shared files), push, REBUILD shell+remote on the merged branch to re-certify green, THEN open the founder-gate PR.
- Founder-gate PR: title `[FOUNDER GATE — DO NOT MERGE] mfe-catalog (SP05) integration → develop`, body = the full §6 acceptance scorecard. **LEAVE IT OPEN. The lead does NOT approve or merge it (D1 — founder's gate).**

---

## 6. VALIDATION CHECKLIST + EVIDENCE (the merge-gate; every box must be evidenced in the PR body)

### 6.A Builds
- [ ] `ng build mfe-catalog` GREEN → `dist/mfe-catalog/browser/remoteEntry.json` exists, `name:"mfe-catalog"`, `exposes` includes `./CatalogRoutes`. **Record seconds** (R4 watch: catalog remote > 15 s → HALT/escalate).
- [ ] Shell `ng build` (`frontend`) GREEN and **≤ 90 s** (CLAUDE.md D12). **Record seconds + initial bundle delta** vs develop baseline (no silent regression).

### 6.B Tests (R-SP5-3)
- [ ] `pnpm test` total == prior baseline (develop tip count; SP03 ended 43 files / 408 tests — confirm the exact develop count first, then assert preserved). **0 failing, 0 skipped.** A DROP in count = silent spec non-discovery = HARD REJECT.
- [ ] The ~7 moved spec files (catalog-new, catalog-form, image-uploader, preview + any) discovered under `spec-apps-mfe-catalog-*` ids. Paste the discovery list.

### 6.C Boundary
- [ ] `grep -rn "from 'primeng" frontend/apps/mfe-catalog --include=*.ts` = ZERO (no new PrimeNG leak; all PrimeNG stays behind `@mesell/ui-kit`).

### 6.D Routes-array expose + deep links (D31 / R-SP5-1 / R-SP5-2)
- [ ] All 5 deep links resolve under the collapsed `catalogs` loadChildren: `/catalogs`, `/catalogs/new`, `/catalogs/:id/edit`, `/catalogs/:id/images`, `/catalogs/:id/preview`. The `:id` param reaches each page; `new` is NOT captured as `:id`.
- [ ] `/catalogs/:id/pricing` and `/catalogs/:id/export` (sibling remotes) STILL resolve unchanged.
- [ ] Relative navigation within the funnel works (smart-picker → `:id/edit`, form → `:id/images`, etc. — the existing `buildEditRoute`/`buildImagesRoute` helpers use absolute `/catalogs/...` paths so they resolve to the same shell base).
- [ ] D12 fallback: a deliberately-broken `mfe-catalog` manifest URL degrades the WHOLE sub-tree to `RemoteFailureComponent` (not a white screen) via `loadRemoteRoutesWithFallback`. Evidence: a `load-remote-routes.spec.ts` that `vi.mock`s `loadRemoteModule` asserting (a) resolves `CATALOG_ROUTES` on success, (b) returns `[{path:'**',component:RemoteFailureComponent}]` on reject. Plus headless: serve `dist/mfe-catalog/browser/` on :4205, `curl remoteEntry.json` → 200, curl the `./CatalogRoutes` chunk → 200, curl broken-url → 404.

### 6.E Route-scoped + component-scoped services (D32)
- [ ] `CatalogFormApiService` resolves on `/catalogs/:id/edit` (NO NullInjectorError); still `@Injectable()` non-root (NOT `providedIn:'root'`); lifecycle unchanged (instantiated on `:id/edit` activation, destroyed on deactivation) — `providers:[CatalogFormApiService]` sits on the `:id/edit` route entry.
- [ ] `SmartPickerApiService` provider scope preserved as COMPONENT-level (`providers:[SmartPickerApiService]` on `catalog-new.component.ts` decorator, unchanged). Resolves on `/catalogs/new`, no NullInjectorError.

### 6.F D33 model promotion (the §5-row-5 deliverable)
- [ ] Surgical-promotion decision tree (§4) executed: grep proof of cross-boundary use attached. EITHER (a) zero promotions + recorded deferral note (expected, valid), OR (b) ONLY canonical `Product`/`Catalog` in `libs/core/models` + barrel, page-private types verifiably stayed local, catalog pages import canonical types from `@mesell/core`.
- [ ] Dashboard-convergence forward note recorded in the memo (regardless of outcome).
- [ ] mfe-dashboard internals NOT touched.

### 6.G Singleton non-drift proof (R-SP3-1 — P0 — RUN TWICE: after Phase A build AND after Phase C)
- [ ] Inspect the remote build output: every `@mesell/*` lib that ANY of the 5 pages consumes (`@mesell/ui-kit`, `@mesell/composites`, and `@mesell/core` IF Phase C re-pointed any type there) appears in the remote's `shared[]` / as its OWN chunk (`_mesell_ui-kit-*.js`, `_mesell_composites-*.js`, `_mesell_core-*.js`) and is **NOT inlined** into any page component chunk. Evidence: `grep`/list the `dist/mfe-catalog/browser/_mesell_*.js` chunks + confirm no `AuthService`/promoted-type class definition is duplicated inside a page chunk.
- [ ] Confirm `main.ts` references the FULL `CATALOG_ROUTES` (all 5 lazy targets) so Sheriff's `ignoreUnusedDeps` graph reaches every page (the SP03 fix). If `@mesell/core` is correctly ABSENT (no page consumes it post-Phase-C), that is acceptable and explicitly noted; if a page DOES consume it and it is absent → drift bug → HARD REJECT + re-route main.ts.

### 6.H Strangler-fig + manifest
- [ ] Shell route table SHRANK: 5 separate `catalogs*` funnel children + the `catalog-form` loadChildren → 1 `catalogs` loadChildren. (pricing/export siblings unchanged.)
- [ ] Manifest has FIVE entries (pricing, export, onboarding, catalog) — wait: that is FOUR named here; if SP04 dashboard merged first the manifest may have dashboard too. Assert AT LEAST {pricing, export, onboarding, catalog}; catalog = the 4205 entry.
- [ ] `git status` shows all 16 moved files as `renamed:` (history preserved); old `catalog-form.routes.ts` removed; old feature dirs gone.

### 6.I PR-template + screenshots + a11y (Lead merge-gate)
- [ ] `.github/PULL_REQUEST_TEMPLATE/frontend.md` complete, NO `<>` placeholders.
- [ ] 360 px + 1280 px screenshots of all 5 pages (pure-rename = zero visual delta by construction; capture or note the by-construction argument if no browser in env per SP01 headless pattern).
- [ ] a11y unchanged (keyboard nav, contrast, aria-* — relocation does not alter markup).
- [ ] CI gates 1 (unit) + 3 (lint) green.

### 6.J Docs/memory/memo
- [ ] `feature_board_frontend.md`: `mfe-catalog` row driven through IN PROGRESS → IN REVIEW (specialist on PR open, D2) → MERGED (lead, D2) + infra inter-lead row (D35).
- [ ] `STATUS_FRONTEND.md` Updates Log appended (build/test numbers, catalog build seconds, Routes-array-resolves result, D33 outcome).
- [ ] `sub_plan_05_catalog.md` memo written (Routes-array recipe + `loadRemoteRoutesWithFallback` + provider-preservation + D33 outcome + dashboard-convergence note).
- [ ] `handoff_mf_catalog_deploy.md` → infra (5th-remote GCS prefix `gs://meesell-frontend/{env}/mfe-catalog/{version}/` + matrix fan-out C-CI-1 + `shared/**`-rebuilds-all note IF any D33 promotion). 48h SLA; board inter-lead row.

---

## 7. STOP CONDITIONS (halt + escalate to founder; do NOT improvise a workaround)

1. Shell `ng build` > 90 s (CLAUDE.md D12) OR `mfe-catalog` remote build > 15 s (MASTER_PLAN §7 R4).
2. `pnpm test` count DROPS below the develop baseline (silent spec non-discovery) OR any test fails/skips that was green on develop.
3. The Routes-array expose does not resolve — shell `loadChildren` cannot get `CATALOG_ROUTES` from the remote (R-SP5-1). This blocks every future flow-owning remote → HALT, do not hack the resolver.
4. Any of the 5 deep links 404s after the collapse, OR `new` is captured as `:id`, OR the pricing/export sibling routes break (R-SP5-2 / routing-precedence regression).
5. `CatalogFormApiService` throws NullInjectorError on `:id/edit`, OR a specialist promotes it/`SmartPickerApiService` to `providedIn:'root'` (D32 violation — lifecycle change).
6. R-SP3-1 singleton drift: a `@mesell/*` lib a page consumes is INLINED into a page chunk instead of shared (after Phase C re-points a type to `@mesell/core`, this becomes the auth-singleton-drift class of bug).
7. D33 over-promotion: a page-private DTO/schema/state type lands in `libs/core` (R-SP5-5), OR the specialist authors a speculative brand-new `Product`/`Catalog` entity without a real cross-boundary consumer (that is a Lead decision, not a specialist call).
8. TypeScript strict mode disabled, an NgModule introduced, NgRx/state-lib added, Ionic added, or CSP authored / shell moved to `apps/shell/` (D9/D14 deferred to SP07) — any LOCKED-decision violation.
9. PrimeNG imported outside `@mesell/ui-kit` (boundary leak).
10. PR template left with a `<placeholder>` — refuse to merge.
11. A specialist edits a page's logic/template (relocation must be byte-identical except path/import context).
12. The `feature/mfe-catalog/frontend` branch exceeds 5 calendar days unmerged (repo-mgmt §1.2) — escalate.

---

## 8. Dispatch order (Lead executes after founder exec-approval)
```
A (component-builder, session mesell-mfe-catalog-frontend-session-1):
   §1 moves + §2 new files + §3.1 helper + §3.2 routes collapse + §3.3 manifest + §3.4 angular.json + §3.5 package.json + §3.6 remove old routes file.
   BUILD CHECKPOINT ng build mfe-catalog (HARD GATE) → shell build → tests → boundary → 5 deep links → 6.G run #1. STOP for lead review.
B (lead): review Phase A/B against 6.A–6.E,6.G,6.H. If green, dispatch C.
C (service-builder, session mesell-mfe-catalog-frontend-session-2):
   §4 D33 decision tree + §6.E provider verification. Re-run 6.G #2. STOP for lead review.
D (lead): 6.F review, 360/1280 screenshots/by-construction, 6.I/6.J docs, group PR squash-merge, integration sync+merge-develop, founder-gate PR OPEN.
```
```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
```
Use the SUB_PLAN_05 §"Dispatch templates" mandatory-reads list verbatim in each specialist prompt; append this spec file path as the authoritative execution contract.
