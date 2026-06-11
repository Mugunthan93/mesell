# Sub-Plan 05 — `mfe-catalog` Extraction (F7 smart-picker + F8 catalog-form + F9 images + F10 preview)

**STATUS: DRAFT 2026-06-10 — authored under master-session night-run dispatch (S3, session `mesell-module-federation-frontend-session-3`). Awaits founder approval to EXECUTE.**

| Field | Value |
|---|---|
| Document type | Module-federation sub-plan (planning only — zero application-code changes in THIS authoring session) |
| Parent plan | `docs/plans/module_federation/MASTER_PLAN.md` (APPROVED 2026-06-10, FEDERATION FIRST) §4.2 ordering "5th" + §5 row 5 |
| Predecessors | SP00 (EXECUTED) + SP01 pilot (§9.A) + SP02 export (lifecycle) + SP03 onboarding (AuthService singleton D22 C1–C5; AuthLayout promoted) + SP04 dashboard (public/private routing; `@Injectable()` non-root provider-preservation D28a) |
| Canonical pattern | `docs/plans/features/_CANONICAL_PATTERN.md` v2.1 — 11 sections, locked order |
| Author | meesell-frontend-coordinator (Frontend Lead) |
| Feature slug | `mfe-catalog` |
| Remote ID | R4 (MASTER_PLAN §2.2) |
| Owned features | F7 smart-picker (catalog-new) · F8 catalog-form · F9 images · F10 preview |
| Owned routes | `/catalogs` · `/catalogs/new` · `/catalogs/:id/edit` · `/catalogs/:id/images` · `/catalogs/:id/preview` |
| Complexity | **L** (FIVE pages across a connected `:id`-threaded funnel; the FIRST `Routes`-array expose (`./CatalogRoutes`); promotes the shared Product/Catalog model to `libs/core`; route-scoped service preservation) |
| Scope | Extract the 5-page catalog creation funnel into a standalone remote exposing a `Routes` array (`./CatalogRoutes`); promote the cross-boundary Product/Catalog model to `@mesell/core/models` (§5 row 5 dependency); wire the shell `catalogs` sub-tree to `loadRemoteModule` of the routes. Frontend-only. |
| Out of scope | Other remotes; backend; AI; mobile/Ionic; real-API wiring (Wave 6); CSP cutover (Sub-plan 7) |
| Execution gates | SP01–SP04 merged to develop + founder approval of THIS sub-plan + infra C-CI-1 ready + GATE4 Option-C confirmed (`docs/plans/infra/GATE4_CONFIRMATION.md`) |

`mfe-catalog` is the **fifth and largest extraction** (MASTER_PLAN §4.2: "the biggest, most connected remote (5 pages, shared `:id`) — done after the toolchain has been battle-tested by 4 prior extractions"). It is the FIRST remote to expose a `Routes` array (`./CatalogRoutes`) rather than single components, because it owns a connected funnel: smart-picker (`catalogs/new`) → catalog-form (`catalogs/:id/edit`) → images (`catalogs/:id/images`) → preview (`catalogs/:id/preview`), plus the `catalogs` list. MASTER_PLAN §2.4 names this exact case: "R4 (`mfe-catalog`) gets a sub-routes export (`./CatalogRoutes`) because it owns 5 connected pages." The toolchain risk is at its lowest by now — every primitive (project shape, fallback helper, manifest, test-discovery, singleton, public/private) is proven — so SP05 spends its complexity budget on the TWO genuinely new surfaces: the **`Routes`-array expose** and the **shared-model promotion**.

Facts from the post-SP0 integration-branch reality (verified, `feature/mf-workspace-foundation/integration` @ `e51761b`):
- **5 distinct route targets** map to 4 page components + 1 placeholder + 1 route file: `catalogs` → `CatalogListComponent` (a trivial placeholder, `features/catalogs/catalog-list.component.ts` — template only, NO imports beyond `@angular/core`); `catalogs/new` → `CatalogNewComponent` (the smart-picker, `features/catalog-new/`); `catalogs/:id/edit` → `loadChildren` → `CATALOG_FORM_ROUTES` (`features/catalog-form/catalog-form.routes.ts`, which provides a **route-scoped `CatalogFormApiService`**); `catalogs/:id/images` → `ImageUploaderComponent`; `catalogs/:id/preview` → `PreviewComponent`.
- **`CatalogFormApiService` is `@Injectable()` non-root, registered via the ROUTE `providers` array** in `catalog-form.routes.ts` (verified) — this is the D28a route-scoped-provider case SP04 flagged, now real.
- **Each page reads `:id` from `ActivatedRoute`** (catalog-form, images, preview all `inject(ActivatedRoute)`); smart-picker injects only `Router` (it CREATES a catalog then navigates to `:id/edit`).
- **No page injects AuthService** — the whole funnel is auth-gated by the shell's `authGuard` on the protected parent (same as dashboard, D27). The catalog remote consumes `@mesell/core` ONLY for the shared model (after promotion) — NOT AuthService.
- **Local feature services + models per page:** `smart-picker-api.service.ts` + `smart-picker.model.ts` (catalog-new); `catalog-form-api.service.ts` + `catalog-form.model.ts` + `models/field-schema.model.ts` (catalog-form); `image-uploader.model.ts` (images); `preview.model.ts` (preview).

---

## Decisions

D-numbers append-only and monotonic, continuing from SUB_PLAN_04 (which ended at D29). FOUNDER-FLAG marks founder-level calls.

### Adaptations from the canonical V1-feature pattern

Same structural-extraction shape, but L-complexity: FIVE route targets + a `Routes`-array expose + a shared-model promotion to `libs/core` + a route-scoped service to preserve. Lineup is one lead + BOTH specialists (component-builder for the 4 pages + the routes-expose; service-builder for the `CatalogFormApiService`/`SmartPickerApiService` route-scoping + the shared-model promotion verification, per MASTER_PLAN §5 row 5 "+ meesell-angular-service-builder for catalog services"). §3 is the largest of any sub-plan: 4 page dirs + a route file + a placeholder + the model promotion. §9 carries the `Routes`-array-resolves gate + the shared-model-promotion gate as NEW first-class items.

### D30 — SP05 COPIES the proven recipe for project shape, fallback, manifest, test-discovery; it innovates ONLY on the routes-expose + the model promotion

**Decision.** The `apps/mfe-catalog/` project shape, `federation.config.js` base tokens, the `loadRemoteWithFallback` shell helper, the test-discovery `apps/**/*.spec.ts` include, and the Tailwind `content` glob are COPIED from `apps/mfe-pricing/` per `sub_plan_01_pricing.md` (SP02 D15 / SP04 D25 precedent). SP05's net-new surfaces are exactly TWO: (1) the `./CatalogRoutes` `Routes`-array expose (D31), and (2) the Product/Catalog shared-model promotion to `@mesell/core/models` (D33).

**Rationale.** By the 5th extraction the toolchain is fully battle-tested. Concentrating innovation on the two real new surfaces (and reusing everything else) is the strangler-fig payoff (MASTER_PLAN §4.1) — and keeps the L-complexity remote tractable.

**Consequence.** The shell route swap for the catalog sub-tree uses `loadRemoteModule` of a `Routes` array (NOT the single-component `loadRemoteWithFallback`-of-a-component helper) — see D31 for the helper variant. All other scaffolding is identical to SP04.

### D31 — The remote exposes a `Routes` ARRAY (`./CatalogRoutes`), NOT individual components; the shell mounts the sub-tree with a fallback-wrapped `loadChildren`

**Decision.** `mfe-catalog`'s `federation.config.js` `exposes` exactly one entry — a routes file:
```
'./CatalogRoutes': './apps/mfe-catalog/src/app/catalog.routes.ts'
```
`catalog.routes.ts` is a NEW remote-owned `Routes` array that internalises ALL 5 route targets:
```ts
export const CATALOG_ROUTES: Routes = [
  { path: '',          loadComponent: () => import('./catalog-list.component')... },     // /catalogs
  { path: 'new',       loadComponent: () => import('./catalog-new.component')... },      // /catalogs/new
  { path: ':id/edit',  loadComponent: () => import('./catalog-form.component')...,
                       providers: [CatalogFormApiService] },                              // :id/edit (route-scoped svc, D32)
  { path: ':id/images',  loadComponent: () => import('./image-uploader.component')... }, // :id/images
  { path: ':id/preview', loadComponent: () => import('./preview.component')... },        // :id/preview
];
```
The shell collapses its FIVE separate `catalogs*` child routes into ONE `loadChildren` that mounts the remote's `Routes`:
```ts
{ path: 'catalogs', loadChildren: loadRemoteRoutesWithFallback('mfe-catalog', './CatalogRoutes') }
```

**Rationale.** MASTER_PLAN §2.4: "shell owns top-level path, remote owns deep sub-routes when the remote contains a flow." The catalog funnel IS a flow — the 5 pages share the `:id` param and a navigation sequence. Exposing a `Routes` array (vs 5 single components) lets the remote own its internal navigation (the smart-picker can `router.navigate(['../', id, 'edit'])` relative to the catalog base) WITHOUT the shell knowing the funnel's internal shape. This is the §2.4 `./CatalogRoutes` case named in the master plan — and SP03's two-expose (D20) proved a remote can expose more than one symbol, but a `Routes` array is the first NON-component expose.

**Consequence.** A NEW shell helper variant `loadRemoteRoutesWithFallback(remoteName, exposedModule)` is needed: it returns a `loadChildren` function that resolves the remote's `Routes` array (`m.CATALOG_ROUTES`) and, on failure, returns a single-route array `[{ path: '**', component: RemoteFailureComponent }]` so a remote-load failure degrades the WHOLE sub-tree gracefully (MASTER_PLAN §6.4). This helper lives beside the SP01 `loadRemoteWithFallback` in `src/app/core/load-remote.ts` and is authored ONCE in SP05 (no later remote needs a routes-expose in V1 — catalog is the only flow-owning remote). The shell route table SHRINKS: 5 `catalogs*` children → 1 `catalogs` `loadChildren`. **Critical:** the catalog base path is `catalogs` in the shell, so the remote's internal `path: ''` = `/catalogs`, `path: 'new'` = `/catalogs/new`, `path: ':id/edit'` = `/catalogs/:id/edit` — the deep links are preserved EXACTLY. Verify every deep link (`/catalogs`, `/catalogs/new`, `/catalogs/<id>/edit`, `/catalogs/<id>/images`, `/catalogs/<id>/preview`) still resolves after the collapse.

### D32 — The route-scoped `CatalogFormApiService` (`@Injectable()` non-root, route `providers`) is preserved EXACTLY on the remote's `:id/edit` route — the D28a case made real

**Decision.** `catalog-form.routes.ts` today registers `CatalogFormApiService` via the route's `providers: [CatalogFormApiService]` (verified). When the catalog-form route moves INTO the remote's `catalog.routes.ts`, the `:id/edit` route entry MUST carry the SAME `providers: [CatalogFormApiService]`. The service stays `@Injectable()` non-root (route-scoped, NOT `providedIn:'root'`) — promoting it to root would change its lifecycle (one instance for the whole app vs one per route activation) and is a behaviour change. Same treatment for any other route-scoped page service (e.g. `SmartPickerApiService` — verify whether it is component-level or route-level and preserve whichever it is).

**Rationale.** D28a (SP04) flagged exactly this: an `@Injectable()` non-root service registered at the route level must travel with its route. Because SP05 exposes a `Routes` ARRAY (not a bare component), the route's `providers` array travels NATURALLY with the route definition — this is actually CLEANER than SP04's single-component case (where a route-level provider would have been orphaned). The `Routes`-array expose is the natural home for route-scoped providers.

**Consequence.** Zero lifecycle change: `CatalogFormApiService` is instantiated when `:id/edit` activates and destroyed when it deactivates, exactly as today. Verify no NullInjectorError on `/catalogs/:id/edit`. This validates the route-scoped-provider pattern that the D28a SP04 note anticipated.

### D33 — Promote the cross-boundary Product/Catalog model to `@mesell/core/models` (the §5-row-5 deliverable); page-private models stay remote-local — **FOUNDER-FLAG (shared-model surface)**

**Decision.** MASTER_PLAN §5 row 5 names this sub-plan's blocking deliverable: "shared Product/Catalog model promoted to `libs/core/models`." The catalog funnel's pages currently keep per-page model files (`smart-picker.model.ts`, `catalog-form.model.ts`, `field-schema.model.ts`, `image-uploader.model.ts`, `preview.model.ts` — all verified). SP05 must determine WHICH types are genuinely cross-boundary (shared between the catalog remote AND another remote — e.g. dashboard's product-list types, or a future Wave-6 backend contract) vs page-private.

**Decision detail.** The promotion is SURGICAL, not wholesale:
1. **Identify the cross-boundary core types** — the canonical `Product` and `Catalog` shapes (the `:id` entity threaded through the funnel AND surfaced in `mfe-dashboard`'s list). These go to `libs/core/models/` (`product.model.ts`, `catalog.model.ts`) + the `@mesell/core` barrel re-exports them.
2. **Page-private types stay remote-local** — `field-schema.model.ts` (catalog-form's dynamic form schema), the smart-picker tree-node shapes, image-uploader's upload-state types, preview's render-DTO. These are NOT shared (grep confirms single-remote use) → they move INTO `apps/mfe-catalog/src/app/` with their pages, NOT to `libs/core` (D11/D17/D23/D28 precedent).
3. **`mfe-dashboard` reconciliation (forward):** SP04 D28 kept `dashboard.model.ts` remote-local with a forward note that its product/catalog list types MAY converge here. SP05's promotion is the convergence point — BUT SP04 is already merged. So SP05 promotes the canonical `Product`/`Catalog` to `@mesell/core/models` and the catalog remote imports them; whether `mfe-dashboard` is RE-POINTED to consume the promoted types is a SEPARATE minor follow-up (a `mfe-dashboard` re-import PR) — NOT in SP05's scope (SP05 must not touch a merged remote's internals beyond what its own extraction needs). Recorded as a forward note for a post-SP05 cleanup or SP07.

**Rationale.** §5 row 5 makes the shared-model promotion a hard dependency of the catalog extraction because catalog is the largest model owner and the natural place to establish the `@mesell/core/models` contract (MASTER_PLAN §2.3: `@mesell/core` holds "shared models (User, Product, Catalog)"; §6.5: only cross-boundary types are promoted; R5 P0: cross-remote contract drift on `libs/core/models`). Promoting the canonical entity here means SP06 (auth) and any Wave-6 wiring inherit a single source of truth for `Product`/`Catalog`.

**FOUNDER-FLAG.** This adds new files to `@mesell/core` (the federation singleton lib) — `libs/core/models/{product,catalog}.model.ts` + barrel re-exports. It expands the shared-singleton surface (every remote now resolves these types from the one `@mesell/core`). The founder confirms: **promote ONLY the canonical `Product`/`Catalog` entity types to `@mesell/core/models` (recommended — surgical, matches §2.3/§6.5), keeping all page-private schema/DTO types remote-local — OR scope the promotion differently.** Recommendation: surgical promotion (the §2.3 model contract names exactly `User, Product, Catalog`). NOTE: this is a `libs/core` CONTENT change (new model files, no logic) — it is NOT a FRONTEND_ARCHITECTURE.md LOCKED-doc amendment (the SP0 FD1 amendment already documented `libs/core` as the shared-models home), but the promotion + the dashboard-convergence forward note must be recorded in the lead memory + the §11 history. **R5 mitigation (MASTER_PLAN):** because these are now cross-remote contract types, a change to them must rebuild the WHOLE workspace (the C-CI-1 `shared/**`-triggers-all rule) — note this to infra in the deploy memo.

> **RULED 2026-06-11 (founder, morning session): APPROVED as recommended.** Product/Catalog model promotion to `@mesell/core` approved — surgical promotion of ONLY the canonical `Product`/`Catalog` entity types to `@mesell/core/models`, page-private schema/DTO types stay remote-local. Executes at SP05 as planned. No LOCKED-doc amendment required. The cross-remote contract status triggers the C-CI-1 `shared/**`-rebuilds-all rule (R5 mitigation) — noted to infra in the deploy memo.

### D34 — `catalog.routes.ts` is a NEW remote-owned file; the shell's `catalog-form.routes.ts` (loadChildren target) is SUBSUMED, not moved

**Decision.** The shell's existing `features/catalog-form/catalog-form.routes.ts` (`CATALOG_FORM_ROUTES`, currently a `loadChildren` target for `:id/edit`) is NOT moved verbatim — its single route entry (the catalog-form component + its `providers: [CatalogFormApiService]`) is FOLDED INTO the new remote-owned `apps/mfe-catalog/src/app/catalog.routes.ts` as the `:id/edit` entry (D31/D32). The old `catalog-form.routes.ts` file is removed once subsumed.

**Rationale.** The catalog remote owns ONE routes file (`./CatalogRoutes`) that internalises all 5 targets including `:id/edit`. Keeping a separate `catalog-form.routes.ts` would mean a nested `loadChildren` inside the remote's routes — unnecessary indirection. Folding it in keeps the remote's routing flat and the route-scoped provider (D32) sits directly on the `:id/edit` entry.

**Consequence.** The shell `app.routes.ts` loses BOTH the 5 separate `catalogs*` children AND the `loadChildren` to `catalog-form.routes`. They collapse into one `{ path: 'catalogs', loadChildren: loadRemoteRoutesWithFallback('mfe-catalog','./CatalogRoutes') }`. The remote-internal `catalog.routes.ts` carries the `:id/edit` `providers` array. Net: the shell route table is materially SIMPLER after SP05 (a strangler-fig win — the shell increasingly only knows remote names + base paths).

### D35 — Option-C deploy mirrors SP01–04; `mfe-catalog` is the fifth (and largest) remote at `remotes.mesell.xyz`

**Decision.** Per `GATE4_CONFIRMATION.md` C-RES-2 / C-ROUTE-1: built `mfe-catalog` → `gs://meesell-frontend/{env}/mfe-catalog/{version}/`, shell manifest gains a fifth entry. Same infra surface. Dev-validation uses localhost-served remotes. **Build-budget watch:** catalog is the largest remote (5 pages + the heaviest model); §9 measures its build seconds against the R4 stop-condition (any remote >15 s after SP05 → halt + re-evaluate per MASTER_PLAN §7 R4). The shell build must still be ≤90 s.

**Rationale + Consequence.** Identical to D13/D19/D24/D29. The new (minor) surface is the five-remote manifest + the FIRST `Routes`-array remote in the manifest. The real new surface is the `loadChildren`-of-a-remote-routes resolution (does the shell correctly mount a remote's entire `Routes` sub-tree at `catalogs`?). The promoted `@mesell/core/models` types being a cross-remote contract triggers the C-CI-1 `shared/**`-rebuilds-all rule (D33) — noted to infra.

### Founder decisions required

1. **FOUNDER-FLAG D33** — promote ONLY the canonical `Product`/`Catalog` entity types to `@mesell/core/models`, keeping page-private schema/DTO types remote-local (recommended, surgical, matches §2.3/§6.5) — OR scope the promotion differently. This is the §5-row-5 deliverable. — **RULED 2026-06-11 (founder, morning session): APPROVED as recommended (surgical promotion; executes at SP05).**
2. **Inherited:** SP01 D9 (shell stays at `src/`) + D14 (dev without CSP, deferred to Sub-plan 7); SP03 D21 (AuthLayout promoted — already merged). Apply unchanged.

D31 (the `Routes`-array expose), D32 (route-scoped provider preservation), and D34 (route-file subsumption) are LEAD-level technical decisions, not founder calls — they do not change any LOCKED decision. No LOCKED-doc amendment (D33's promotion is a `libs/core` content change, recorded in memory + history).

---

## Agent lineup

| Lead | Specialist dispatched | What the specialist builds |
|---|---|---|
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-component-builder` (sonnet) | Creates `apps/mfe-catalog/` (copy pilot recipe); `git mv`s the 4 page dirs (catalog-new, catalog-form, images, preview) + the `catalogs` list placeholder into it; authors the NEW `catalog.routes.ts` (`Routes` array, 5 entries, D31) folding in the subsumed `catalog-form.routes.ts` `:id/edit` entry (D34); authors the NEW shell `loadRemoteRoutesWithFallback` helper (D31); collapses the shell's 5 `catalogs*` children + the `catalog-form` loadChildren into ONE `catalogs` loadChildren; patches the manifest with a fifth entry; verifies builds, all 5 deep links resolve, the `Routes`-array mounts, both page tests green. |
| `meesell-frontend-coordinator` (Frontend Lead) | `meesell-angular-service-builder` (sonnet) | Handles the catalog SERVICES + the shared-model promotion: (1) verifies `CatalogFormApiService` route-scoped `providers` preserved on `:id/edit` (D32, no NullInjectorError, lifecycle unchanged); (2) verifies `SmartPickerApiService` provider scope preserved; (3) executes the SURGICAL Product/Catalog model promotion to `@mesell/core/models` + barrel re-export (D33), re-pointing the catalog pages' imports to `@mesell/core`; (4) confirms page-private models stayed remote-local; (5) records the dashboard-convergence forward note. Does NOT change service logic. |

Per MASTER_PLAN §5 row 5 the responsible agents are `meesell-angular-component-builder + meesell-angular-service-builder (for catalog services)`. Dispatch order: component-builder does the extraction + routes-expose; service-builder does the route-scoped-service preservation + the model promotion AFTER the component-builder's build is green. Infra is a cross-lead dependency (D35 memo), not a dispatched specialist.

### Dispatch order

```
PHASE A — extract the 5 pages + author the routes-expose (component-builder)
   A1. Copy apps/mfe-pricing/ shape -> apps/mfe-catalog/ (angular.json native-federation:build remote)
   A2. git mv features/catalog-new/** + features/catalog-form/** + features/images/** + features/preview/**
       + features/catalogs/catalog-list.component.{ts,spec.ts?} -> apps/mfe-catalog/src/app/ (preserve subdirs/relative imports)
   A3. NEW apps/mfe-catalog/src/app/catalog.routes.ts: a Routes array with 5 entries (D31) —
       '' (list), 'new' (smart-picker), ':id/edit' (catalog-form, providers:[CatalogFormApiService] D32),
       ':id/images', ':id/preview'. FOLD IN the subsumed catalog-form.routes.ts :id/edit entry (D34); remove the old file.
   A4. NEW apps/mfe-catalog/src/app/public-api.ts re-exporting CATALOG_ROUTES (+ the page components if needed)
   A5. NEW apps/mfe-catalog/federation.config.js name 'mfe-catalog' exposing { './CatalogRoutes': './apps/mfe-catalog/src/app/catalog.routes.ts' } + shareAll singletons (@mesell/core in shared set)
   A6. NEW shell src/app/core/load-remote.ts addition: loadRemoteRoutesWithFallback(remoteName, exposedModule) returning a loadChildren that resolves the remote Routes array + degrades to [{path:'**',component:RemoteFailureComponent}] on failure (D31)
   A7. BUILD CHECKPOINT — `ng build mfe-catalog`. HARD GATE.

PHASE B — wire the shell (component-builder)
   B1. app.routes.ts: REMOVE the 5 separate catalogs* children + the catalog-form loadChildren; ADD ONE
       { path: 'catalogs', loadChildren: loadRemoteRoutesWithFallback('mfe-catalog','./CatalogRoutes') } under the protected parent (authGuard UNCHANGED, D27/D32)
   B2. public/federation.manifest.json: add "mfe-catalog" (now FIVE entries)
   B3. VERIFY — shell build ≤90 s; catalog build seconds recorded (R4 watch); tests green/count preserved;
       boundary clean; ALL 5 deep links resolve (/catalogs, /catalogs/new, /catalogs/:id/edit, /catalogs/:id/images, /catalogs/:id/preview)
       + the remote Routes sub-tree mounts under the shell 'catalogs' base + relative navigation within the funnel works

PHASE C — services + model promotion (service-builder, AFTER B green)
   C1. Verify CatalogFormApiService route-scoped providers on :id/edit (D32 — no NullInjectorError, lifecycle unchanged)
   C2. Verify SmartPickerApiService provider scope preserved
   C3. SURGICAL promotion: Product/Catalog canonical types -> libs/core/models/{product,catalog}.model.ts + @mesell/core barrel; re-point catalog pages' imports to @mesell/core (D33)
   C4. Confirm page-private models (field-schema, smart-picker tree, image-state, preview-DTO) stayed remote-local
   C5. Record the dashboard-convergence forward note (SP04 D28 reconciliation — NOT touched here)

PHASE D — lead, no specialist
   D1. 360/1280 screenshots of all 5 pages (no visual change)
   D2. Verify the shell route table SHRANK (5 children + loadChildren -> 1 loadChildren) — the strangler-fig win
   D3. Infra deploy memo (D35 fifth-remote GCS prefix + matrix fan-out + the shared/**-rebuilds-all note for the promoted models) + merge-gate review + PR
```

---

## Code surfaces

Exhaustive inventory. Tags: `MOVE` / `MODIFY` / `NEW`. Source paths verified on `feature/mf-workspace-foundation/integration`.

### Relocation — the 5 catalog pages → `apps/mfe-catalog/src/app/`

| # | Source (post-SP0) | Target | Tag | Notes |
|---|---|---|---|---|
| 1 | `frontend/src/app/features/catalog-new/catalog-new.component.{ts,spec.ts}` | `apps/mfe-catalog/src/app/catalog-new/` | MOVE | Smart-picker (`CatalogNewComponent`). `@mesell/ui-kit` (MeeTreeNode etc.) + `@mesell/composites` (PageHeader, LoadingSkeleton) UNCHANGED; local `smart-picker.model.ts` + `services/smart-picker-api.service.ts` move alongside. Injects `Router` + `FormBuilder` + `SmartPickerApiService`. |
| 2 | `frontend/src/app/features/catalog-new/smart-picker.model.ts` | `apps/mfe-catalog/src/app/catalog-new/smart-picker.model.ts` | MOVE | Page-private (D33) — tree-node shapes stay remote-local. |
| 3 | `frontend/src/app/features/catalog-new/services/smart-picker-api.service.ts` | `apps/mfe-catalog/src/app/catalog-new/services/` | MOVE | Remote-private service. Preserve its provider scope (D32). |
| 4 | `frontend/src/app/features/catalog-form/catalog-form/catalog-form.component.{ts,spec.ts}` | `apps/mfe-catalog/src/app/catalog-form/` | MOVE | `CatalogFormComponent`. `@mesell/ui-kit` + `@mesell/composites` + `MeeToastService` UNCHANGED; reads `:id` via `ActivatedRoute`; local `field-schema.model.ts` moves alongside; the canonical Product/Catalog types re-pointed to `@mesell/core` (D33). |
| 5 | `frontend/src/app/features/catalog-form/catalog-form.model.ts` | `apps/mfe-catalog/src/app/catalog-form/catalog-form.model.ts` | MOVE | Split: page-private form-state stays; canonical Product/Catalog types extracted to `@mesell/core/models` (D33). |
| 6 | `frontend/src/app/features/catalog-form/models/field-schema.model.ts` | `apps/mfe-catalog/src/app/catalog-form/models/field-schema.model.ts` | MOVE | Page-private dynamic-form schema — remote-local (D33). |
| 7 | `frontend/src/app/features/catalog-form/services/catalog-form-api.service.ts` | `apps/mfe-catalog/src/app/catalog-form/services/catalog-form-api.service.ts` | MOVE | `CatalogFormApiService` `@Injectable()` non-root — route-scoped (D32). Provider stays on the `:id/edit` route in `catalog.routes.ts`. |
| 8 | `frontend/src/app/features/images/image-uploader/image-uploader.component.{ts,spec.ts}` | `apps/mfe-catalog/src/app/images/` | MOVE | `ImageUploaderComponent`. `@mesell/ui-kit` (MeeFileUpload + MeeFileUploadEvent type) + `@mesell/composites` UNCHANGED; reads `:id`; local `image-uploader.model.ts` moves alongside. |
| 9 | `frontend/src/app/features/images/image-uploader/image-uploader.model.ts` | `apps/mfe-catalog/src/app/images/image-uploader.model.ts` | MOVE | Page-private upload-state — remote-local (D33). |
| 10 | `frontend/src/app/features/preview/preview/preview.component.{ts,spec.ts}` | `apps/mfe-catalog/src/app/preview/` | MOVE | `PreviewComponent`. `@mesell/ui-kit` + `@mesell/composites` (PageHeader) UNCHANGED; reads `:id`; local `preview.model.ts` moves alongside; canonical types re-pointed to `@mesell/core` (D33). |
| 11 | `frontend/src/app/features/preview/preview/preview.model.ts` | `apps/mfe-catalog/src/app/preview/preview.model.ts` | MOVE | Split: page-private render-DTO stays; any canonical Product/Catalog type re-pointed to `@mesell/core` (D33). |
| 12 | `frontend/src/app/features/catalogs/catalog-list.component.{ts,spec.ts?}` | `apps/mfe-catalog/src/app/catalog-list.component.ts` | MOVE | `CatalogListComponent` — trivial placeholder (template only, no imports beyond `@angular/core`). The `''` route of the remote. |

After the moves, `features/catalog-new/`, `features/catalog-form/`, `features/images/`, `features/preview/`, `features/catalogs/` are all removed.

### Shared-model promotion (D33) — Product/Catalog → `@mesell/core/models` (NEW + MODIFY)

| # | Path | Tag | Description |
|---|---|---|---|
| 13 | `frontend/libs/core/models/product.model.ts` | NEW | The canonical `Product` entity type, extracted from the catalog pages' local models (the cross-boundary shape — also surfaced in `mfe-dashboard`'s list). |
| 14 | `frontend/libs/core/models/catalog.model.ts` | NEW | The canonical `Catalog` entity type (the `:id` entity threaded through the funnel). |
| 15 | `frontend/libs/core/index.ts` | MODIFY | Re-export `Product` + `Catalog` from the `@mesell/core` barrel (deep alias `@mesell/core/models` also resolves via the SP0 `@mesell/core/*` wildcard). |

> The split is SURGICAL (D33): only the canonical entity types move; page-private schema/DTO/state types stay in the remote. The service-builder enumerates which local-model symbols are cross-boundary BEFORE moving (`grep` for cross-remote importers).

### Federation scaffolding — `apps/mfe-catalog/` (NEW, copies the pilot + the routes-expose)

| # | Path | Tag | Description |
|---|---|---|---|
| 16 | `frontend/apps/mfe-catalog/src/app/catalog.routes.ts` | NEW | The `Routes` array (5 entries, D31) — the `./CatalogRoutes` expose. `:id/edit` carries `providers: [CatalogFormApiService]` (D32). Subsumes the old `catalog-form.routes.ts` (D34). |
| 17 | `frontend/apps/mfe-catalog/src/app/public-api.ts` | NEW | Re-exports `CATALOG_ROUTES` (the typed boundary, §6.5). |
| 18 | `frontend/apps/mfe-catalog/federation.config.js` | NEW | `name: 'mfe-catalog'`, ONE `exposes` entry (`'./CatalogRoutes'`), `shareAll` singletons — `@mesell/core` in the shared set (now carries the promoted Product/Catalog, D33). |
| 19 | `frontend/apps/mfe-catalog/src/main.ts` | NEW | Dev-serve bootstrap — `bootstrapApplication` with `provideRouter(CATALOG_ROUTES)` for standalone dev. |
| 20 | `frontend/apps/mfe-catalog/tsconfig.app.json` | NEW | Extends base; `@mesell/*` paths incl. `@mesell/core`. |

### Shell wiring (MODIFY + NEW helper)

| # | Path | Tag | Description |
|---|---|---|---|
| 21 | `frontend/src/app/core/load-remote.ts` | MODIFY | Add `loadRemoteRoutesWithFallback(remoteName, exposedModule)` — returns a `loadChildren` resolving the remote `Routes` array, degrading to `[{path:'**',component:RemoteFailureComponent}]` on failure (D31). Beside the SP01 `loadRemoteWithFallback`. |
| 22 | `frontend/src/app/app.routes.ts` | MODIFY | REMOVE the 5 `catalogs*` children + the `catalog-form` `loadChildren`; ADD ONE `{ path: 'catalogs', loadChildren: loadRemoteRoutesWithFallback('mfe-catalog','./CatalogRoutes') }` under the protected parent (authGuard UNCHANGED). |
| 23 | `frontend/public/federation.manifest.json` | MODIFY | Add `"mfe-catalog"` (now FIVE entries). |
| 24 | `frontend/angular.json` | MODIFY | Add `projects.mfe-catalog`. |
| 25 | test-discovery `include` + Tailwind `content` | RE-CONFIRM | `apps/**` globs from SP01 cover the new project. No edit expected. |

### Old file removal (D34)

| # | Path | Tag | Description |
|---|---|---|---|
| 26 | `frontend/src/app/features/catalog-form/catalog-form.routes.ts` | REMOVE | Subsumed into the remote's `catalog.routes.ts` `:id/edit` entry (D34). |

### Documentation / status / memory

| # | Path | Tag | Description |
|---|---|---|---|
| 27 | `docs/status/feature_board_frontend.md` | MODIFY | `mfe-catalog` row lifecycle + infra inter-lead row (D35). |
| 28 | `docs/status/STATUS_FRONTEND.md` | MODIFY | Updates Log — build/test numbers, catalog build seconds (R4 watch), the `Routes`-array-resolves result, the model-promotion record. |
| 29 | `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_05_catalog.md` | NEW | The `Routes`-array-expose recipe + `loadRemoteRoutesWithFallback` + the route-scoped-provider preservation + the Product/Catalog promotion record + the dashboard-convergence forward note. |

No backend/AI/data surface (until Wave 6 wires the catalog API — a future frontend↔backend contract on the now-promoted `@mesell/core` models). No LOCKED-doc amendment.

### Illustrative `catalog.routes.ts` (remote-owned `Routes` array)

```ts
// frontend/apps/mfe-catalog/src/app/catalog.routes.ts
import { Routes } from '@angular/router';
import { CatalogFormApiService } from './catalog-form/services/catalog-form-api.service';

export const CATALOG_ROUTES: Routes = [
  { path: '',           loadComponent: () => import('./catalog-list.component').then(m => m.CatalogListComponent) },
  { path: 'new',        loadComponent: () => import('./catalog-new/catalog-new.component').then(m => m.CatalogNewComponent) },
  { path: ':id/edit',   loadComponent: () => import('./catalog-form/catalog-form.component').then(m => m.CatalogFormComponent),
                        providers: [CatalogFormApiService] },                       // D32 route-scoped service
  { path: ':id/images', loadComponent: () => import('./images/image-uploader.component').then(m => m.ImageUploaderComponent) },
  { path: ':id/preview',loadComponent: () => import('./preview/preview.component').then(m => m.PreviewComponent) },
];
```

### Illustrative shell `loadRemoteRoutesWithFallback` helper

```ts
// frontend/src/app/core/load-remote.ts (addition)
import { loadRemoteModule } from '@angular-architects/native-federation';
import { Routes } from '@angular/router';
import { RemoteFailureComponent } from './remote-failure.component';

export function loadRemoteRoutesWithFallback(remoteName: string, exposedModule: string) {
  return () =>
    loadRemoteModule({ remoteName, exposedModule })
      .then(m => (Object.values(m).find(Array.isArray) ?? m['CATALOG_ROUTES']) as Routes)
      .catch(() => [{ path: '**', component: RemoteFailureComponent }] as Routes);  // §6.4 — whole sub-tree degrades
}
```

---

## Documentation deliverables

Gate conditions in §9. The PR cannot merge to integration without:

1. **`SUB_PLAN_05_catalog_extraction.md`** (this document) — referenced from MASTER_PLAN §5 row 5.
2. **`sub_plan_05_catalog.md` memo** — the `Routes`-array-expose recipe (`./CatalogRoutes` + `loadRemoteRoutesWithFallback`), the route-scoped-provider preservation (D32), and the FINALISED Product/Catalog model promotion (D33) + the dashboard-convergence forward note. Consumed by SP06 (auth, which exposes single components again — but reads the model contract) + SP07 (cutover) + any Wave-6 catalog API wiring.
3. **The §5-row-5 deliverable:** the Product/Catalog model promoted to `@mesell/core/models`, recorded.
4. **Infra deploy memo** (`handoff_mf_catalog_deploy.md`) — fifth-remote GCS prefix + matrix fan-out (C-CI-1) + the `shared/**`-rebuilds-all note for the promoted `@mesell/core` models (R5).
5. **`feature_board_frontend.md` + `STATUS_FRONTEND.md`** current through the lifecycle.

---

## Branch setup

Feature slug `mfe-catalog`. Per F1.

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/mfe-catalog/integration` | `develop` (AFTER SP04 merged) | Integration branch | Frontend Lead |
| `feature/mfe-catalog/frontend` | `feature/mfe-catalog/integration` | ALL extraction + routes-expose + model promotion | `meesell-angular-component-builder`, `meesell-angular-service-builder` |

Both specialists work the SAME `feature/mfe-catalog/frontend` branch sequentially (component-builder extraction + routes-expose first, then service-builder services + model promotion) — one frontend group branch per feature (repo-management §1.2). No infra group branch (parallel C-CI-1 effort).

### F1 branch-setup commands (EXECUTION stage)

```bash
git fetch origin develop
git checkout develop && git pull --ff-only          # must include SP04's merge

git checkout -b feature/mfe-catalog/integration develop
git push -u origin feature/mfe-catalog/integration

git checkout -b feature/mfe-catalog/frontend feature/mfe-catalog/integration
git push -u origin feature/mfe-catalog/frontend

git worktree add /tmp/mesell-wt/mfe-catalog feature/mfe-catalog/frontend
```

### PR flow

```
feature/mfe-catalog/frontend
        │  PR — Frontend Lead reviews+merges (squash)   [D1]
        ▼
feature/mfe-catalog/integration
        │  PR — FOUNDER reviews+merges (merge-commit)    [D1]
        ▼
develop
```

Group → integration: Frontend Lead. Integration → develop: Founder (lead must NOT approve). F3 protection; re-probe empirically.

---

## Memory protocol

### Memories the coding-session leads MUST read at start

- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` (own memory — deep-import bundle landmine; `@mesell/ui-kit/*` wildcard alias; the `apps/**/*.spec.ts` test-discovery gotcha; pnpm-worktree native-build fix)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md` (THE recipe) + `sub_plan_03_onboarding.md` (multi-expose + the AuthService singleton — for the uniform `@mesell/core` shared-set rule) + `sub_plan_04_dashboard.md` (the `@Injectable()` non-root provider-preservation note — D28a, made real here as D32)
- `.claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md` (alias map — `@mesell/core` + the `@mesell/core/*` wildcard)
- `docs/plans/module_federation/MASTER_PLAN.md` §2.3 (shared libs — `@mesell/core` holds User/Product/Catalog), §2.4 (routing — the `./CatalogRoutes` flow case), §6.5 (type sharing — promote only cross-boundary), §7 R5 (cross-remote contract drift P0)
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (GATE4 Option-C; C-CI-1 `shared/**`-rebuilds-all)

### Cross-feature memos

- **Outgoing → infra:** `handoff_mf_catalog_deploy.md` — fifth-remote GCS prefix + matrix fan-out (C-CI-1) + the `shared/**`-rebuilds-all note (the promoted `@mesell/core` models are now a cross-remote contract — a change rebuilds the WHOLE workspace, R5). 48h SLA. Board row added.
- **Forward-reference:** `sub_plan_05_catalog.md` — the `Routes`-array-expose recipe + the model-promotion contract (SP05's gift to SP06/SP07 + Wave 6).

### Session-close memory entries

Session header (`## Session mesell-mfe-catalog-frontend-session-{N}`), D30–D35 outcomes (esp. the D33 FOUNDER-FLAG resolution + the model-promotion record + the dashboard-convergence forward note), files-touched count, the shell-route-table-shrank confirmation, remote + shell build seconds (catalog vs the R4 15 s watch), test pass count, boundary result, the all-5-deep-links-resolve + Routes-array-mounts proof, the route-scoped-provider-preserved proof, blockers, next-step (Sub-plan 6 auth — the last, riskiest extraction).

---

## Dispatch templates

### meesell-angular-component-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-catalog-frontend-session-1

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_05_catalog_extraction.md (this plan — D30-D35, esp. D31 Routes-array expose + D32 route-scoped provider + D34 route-file subsumption, §3, §9)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_01_pricing.md (THE recipe) + sub_plan_04_dashboard.md (provider-preservation D28a, made real here)
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (apps/**/*.spec.ts test-discovery; deep-import bundle landmine; @mesell/ui-kit/* wildcard)
- docs/plans/module_federation/MASTER_PLAN.md §2.4 (routing — ./CatalogRoutes flow case), §6.4 (error boundary)

## Your mission
PHASE A: Copy apps/mfe-pricing/ shape -> apps/mfe-catalog/. `git mv` features/catalog-new/** + features/catalog-form/** + features/images/** + features/preview/** + features/catalogs/catalog-list.component.* -> apps/mfe-catalog/src/app/ (preserve subdirs + relative imports; @mesell/* imports UNCHANGED). NEW catalog.routes.ts: a Routes array with 5 entries (''=list, 'new'=smart-picker, ':id/edit'=catalog-form with providers:[CatalogFormApiService] D32, ':id/images', ':id/preview'); FOLD IN the old catalog-form.routes.ts :id/edit entry then REMOVE that file (D34). NEW public-api.ts re-exporting CATALOG_ROUTES. NEW federation.config.js name 'mfe-catalog' exposing { './CatalogRoutes': './apps/mfe-catalog/src/app/catalog.routes.ts' } + shareAll singletons (@mesell/core in shared set). NEW shell helper loadRemoteRoutesWithFallback in src/app/core/load-remote.ts (resolves the remote Routes array; degrades to [{path:'**',component:RemoteFailureComponent}] on failure). BUILD CHECKPOINT: `ng build mfe-catalog`. HARD GATE.
PHASE B: app.routes.ts -> REMOVE the 5 catalogs* children + the catalog-form loadChildren; ADD ONE { path:'catalogs', loadChildren: loadRemoteRoutesWithFallback('mfe-catalog','./CatalogRoutes') } under the protected parent (authGuard UNCHANGED). manifest: add "mfe-catalog" (FIVE entries). VERIFY: shell build ≤90 s; catalog build seconds recorded; tests green/count preserved; boundary clean; ALL 5 deep links resolve + the remote Routes sub-tree mounts under 'catalogs' + relative navigation in the funnel works.

## Acceptance criteria
- [ ] apps/mfe-catalog/ holds the 5 pages (+ specs + per-page models/services) + catalog.routes.ts + public-api + federation.config + main.ts; old features removed; old catalog-form.routes.ts removed
- [ ] catalog.routes.ts has 5 entries; :id/edit carries providers:[CatalogFormApiService] (D32)
- [ ] federation.config exposes './CatalogRoutes'; @mesell/core shared+singleton
- [ ] `ng build mfe-catalog` GREEN -> remoteEntry.json (record seconds — watch the R4 15s budget)
- [ ] shell `pnpm build` GREEN ≤ 90 s (seconds + bundle delta)
- [ ] `pnpm test` total == prior baseline, 0 failing/skipped (drop = HARD REJECT)
- [ ] boundary clean; ALL 5 deep links resolve (/catalogs, /catalogs/new, /catalogs/:id/edit, /catalogs/:id/images, /catalogs/:id/preview); the remote Routes mount under 'catalogs'; CatalogFormApiService resolves on :id/edit (no NullInjectorError)
- [ ] manifest has FIVE entries; the shell route table SHRANK (5 children + loadChildren -> 1 loadChildren)

## Hard constraints
- ZERO logic/template edits to the 5 pages — relocation + route-array authoring only
- Do NOT promote CatalogFormApiService/SmartPickerApiService to providedIn:'root' (D32 — preserve route/component scope + lifecycle)
- Do NOT promote page-private models (field-schema, smart-picker tree, image-state, preview-DTO) to libs/core (D33 — that is the service-builder's SURGICAL Product/Catalog-only promotion, runs after you)
- Do NOT author CSP (D14); do NOT move the shell into apps/shell/ (D9); do NOT add a guard/AuthService into the remote (D27)
- Do NOT touch backend/, k8s/, infra/, OR other remotes/features

## Files you MAY touch
- frontend/apps/mfe-catalog/** (new), frontend/angular.json (add project), frontend/public/federation.manifest.json
- frontend/src/app/app.routes.ts (catalog sub-tree collapse), frontend/src/app/core/load-remote.ts (add the routes helper)
- REMOVE frontend/src/app/features/catalog-form/catalog-form.routes.ts (subsumed)

## Files you must NOT touch
- libs/core/** (the model promotion is the service-builder's job, after you); other remotes; src/app/core/remote-failure.component.ts (reuse); backend/k8s/infra

## Final report format
Files moved (count), files new (count), the catalog.routes.ts 5-entry confirmation, remote build seconds, shell build seconds + bundle delta, test count, boundary output, all-5-deep-links-resolve proof, CatalogFormApiService-resolves proof, the shell-route-table-shrank confirmation. Then STOP for lead review (service-builder does the model promotion next).
```

### meesell-angular-service-builder

```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/. Worktrees under /tmp/mesell-wt/ are part of the project.
SESSION: mesell-mfe-catalog-frontend-session-2

## Mandatory reads (in this order)
- docs/plans/module_federation/SUB_PLAN_05_catalog_extraction.md (this plan — D32 route-scoped provider, D33 SURGICAL Product/Catalog model promotion, §9 model-promotion gate)
- docs/plans/module_federation/MASTER_PLAN.md §2.3 (@mesell/core holds User/Product/Catalog), §6.5 (promote only cross-boundary), §7 R5 (contract drift P0)
- .claude/agent-memory/meesell-frontend-coordinator/sub_plan_00_workspace.md (@mesell/core barrel + the @mesell/core/* wildcard alias)

## Your mission
AFTER component-builder's Phase A+B is green. (1) Verify CatalogFormApiService route-scoped providers:[...] on the :id/edit route in catalog.routes.ts (D32) — confirm it resolves at runtime (no NullInjectorError) with UNCHANGED lifecycle (instantiated on :id/edit activation, destroyed on deactivation); do NOT change it to providedIn:'root'. (2) Verify SmartPickerApiService provider scope preserved. (3) SURGICAL model promotion (D33): grep the catalog pages' local model files for the CANONICAL Product/Catalog entity types that are CROSS-BOUNDARY (shared with mfe-dashboard's list or a future backend contract); extract ONLY those to libs/core/models/{product,catalog}.model.ts + re-export from the @mesell/core barrel; re-point the catalog pages' imports of those types to @mesell/core. (4) Confirm page-private types (field-schema, smart-picker tree-node, image-upload-state, preview-render-DTO) stayed remote-local — do NOT promote them. (5) Record the dashboard-convergence forward note (SP04's dashboard.model.ts MAY later re-point to the promoted types — NOT touched here).

## Acceptance criteria
- [ ] CatalogFormApiService resolves on :id/edit (no NullInjectorError), lifecycle unchanged, NOT providedIn:'root' (D32)
- [ ] SmartPickerApiService provider scope preserved
- [ ] ONLY canonical Product/Catalog types in libs/core/models + @mesell/core barrel; catalog pages import them from @mesell/core
- [ ] page-private models stayed remote-local (verified by grep — no over-promotion)
- [ ] shell + catalog build still GREEN; tests green/count preserved; the dashboard-convergence forward note recorded

## Hard constraints
- Do NOT change service LOGIC (only verify provider scope) ; do NOT change service injectability scope (D32)
- Do NOT over-promote: page-private schema/DTO/state types stay in the remote (D33 / §6.5)
- Do NOT touch a merged remote (mfe-dashboard) — the dashboard re-import is a SEPARATE follow-up (forward note only)
- Do NOT add NgRx/any state lib (CLAUDE.md D10); do NOT touch backend/k8s/infra

## Files you MAY touch
- frontend/libs/core/models/** (new product/catalog), frontend/libs/core/index.ts (barrel re-export)
- the catalog pages' import lines that reference the promoted canonical types (re-point to @mesell/core)
- read-only verification of CatalogFormApiService/SmartPickerApiService provider scope

## Final report format
The route-scoped-provider verification (CatalogFormApiService resolves, lifecycle unchanged), the promoted Product/Catalog type list, the confirmation that page-private models stayed local, the build/test status, and the dashboard-convergence forward note. Then STOP for lead review + PR.
```

---

## Review + iteration protocol

### meesell-angular-component-builder (extraction + routes-expose)

- **Pre-approval checklist:** (a) history preserved on all 12 moved files; (b) the 5 pages' diffs empty except path/import context — NO logic change; (c) `catalog.routes.ts` has exactly 5 entries with `:id/edit` carrying `providers:[CatalogFormApiService]` (D32); (d) the old `catalog-form.routes.ts` removed (D34); (e) `federation.config.js` exposes exactly `'./CatalogRoutes'`; (f) shell `federation.config.js` UNCHANGED; (g) manifest has FIVE entries; (h) the shell route table SHRANK (5 children + loadChildren → 1 loadChildren); (i) ALL 5 deep links resolve + the Routes sub-tree mounts; (j) `CatalogFormApiService` resolves on `:id/edit`; (k) test count == prior baseline; (l) shell build ≤90 s; catalog build < the R4 15 s watch.
- **PR-template gate:** complete, no `<>`; build evidence (catalog + shell seconds), bundle delta, 360/1280 screenshots of ALL 5 pages (no visual change), a11y, boundary output, the all-5-deep-links + Routes-array-mounts proof.
- **Re-dispatch triggers:** "edited a page's logic/template" → quote the no-logic rule; "promoted a service to providedIn:'root'" → quote D32; "lost CatalogFormApiService (NullInjectorError on :id/edit)" → quote D32 (provider on the route); "a deep link broke after the collapse" → quote D31 (base-path math); "didn't author loadRemoteRoutesWithFallback / used the single-component helper for the routes" → quote D31; "promoted page-private models" → quote D33 (that's the service-builder's surgical job); "test count dropped" → the `apps/**/*.spec.ts` note.
- **Iteration cap: 3** → founder escalation.

### meesell-angular-service-builder (services + model promotion)

- **Pre-approval checklist:** (a) `CatalogFormApiService` resolves on `:id/edit`, lifecycle unchanged, still `@Injectable()` non-root (D32); (b) ONLY canonical `Product`/`Catalog` in `libs/core/models` + the barrel; (c) page-private schema/DTO/state types verifiably stayed remote-local (grep proof — no over-promotion, §6.5); (d) the catalog pages import the canonical types from `@mesell/core`; (e) build + tests still green; (f) the dashboard-convergence forward note recorded.
- **Re-dispatch triggers:** "changed a service to providedIn:'root'" → quote D32; "over-promoted page-private models" → quote D33/§6.5 with the offending file; "touched mfe-dashboard internals" → quote the merged-remote no-touch rule; "promoted-type drift broke a remote build" → re-dispatch with the build error + the R5 whole-workspace-rebuild note; "added NgRx" → quote CLAUDE.md D10.
- **Iteration cap: 3** → founder escalation.

---

## Acceptance gate

When every box is `[x]`, `feature/mfe-catalog/integration` is ready for the founder's develop PR.

- [ ] PR (`feature/mfe-catalog/frontend` → integration) merged by Frontend Lead (squash)
- [ ] `ng build mfe-catalog` GREEN — produces `remoteEntry.json` exposing `./CatalogRoutes` (record seconds; catalog < R4 15 s watch)
- [ ] Shell `pnpm build` GREEN and **≤ 90 s** (CLAUDE.md Decision 12 / Stop Condition) — seconds + initial bundle delta recorded
- [ ] `pnpm test` total == **prior baseline, 0 failing, 0 skipped** — any new failure OR a count DROP blocks merge (R-SP5-3)
- [ ] **Boundary grep clean:** no new PrimeNG leak from `apps/mfe-catalog/`
- [ ] **All 5 deep links resolve:** `/catalogs`, `/catalogs/new`, `/catalogs/:id/edit`, `/catalogs/:id/images`, `/catalogs/:id/preview` — the remote `Routes` sub-tree mounts under the shell `catalogs` base; the `:id` param reaches every page; relative navigation within the funnel works
- [ ] **`Routes`-array expose works (D31):** the shell `loadChildren` resolves the remote's `CATALOG_ROUTES`; a deliberately-broken `mfe-catalog` manifest URL degrades the WHOLE sub-tree to `RemoteFailureComponent` (not a white screen) via `loadRemoteRoutesWithFallback`
- [ ] **Route-scoped service preserved (D32):** `CatalogFormApiService` resolves on `:id/edit` (no NullInjectorError), lifecycle unchanged, still `@Injectable()` non-root
- [ ] **Shared-model promotion done (D33, the §5-row-5 deliverable):** ONLY canonical `Product`/`Catalog` in `@mesell/core/models` + barrel; page-private types stayed remote-local; the catalog pages import canonical types from `@mesell/core`; the dashboard-convergence forward note recorded
- [ ] **FIVE remotes coexist** in the manifest (`mfe-pricing`, `mfe-export`, `mfe-onboarding`, `mfe-dashboard`, `mfe-catalog`)
- [ ] **Shell route table SHRANK:** the 5 separate `catalogs*` children + the `catalog-form` `loadChildren` collapsed into ONE `catalogs` `loadChildren` (the strangler-fig win)
- [ ] FOUNDER-FLAGs: D33 (Product/Catalog promotion) resolved; D9 + D14 inherited from SP01; D21 inherited from SP03 — *(D33 founder RULED APPROVED-as-recommended 2026-06-11; D21 RULED same day at SP03; D9/D14 resolved at SP07 via D43/D42, also RULED 2026-06-11)*
- [ ] Infra deploy memo filed (D35 — GCS prefix/matrix + the `shared/**`-rebuilds-all note for the promoted models); board inter-lead row added
- [ ] `feature_board_frontend.md` row = MERGED; STATUS_FRONTEND.md appended; `sub_plan_05_catalog.md` recipe memo written
- [ ] **Founder approval** on `feature/mfe-catalog/integration` → `develop` (founder's gate, NOT the lead's)

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SP5-1 | **`Routes`-array expose resolution bug** — the shell's `loadChildren` can't resolve the remote's `CATALOG_ROUTES` symbol (Native Federation hands a routes file differently than a component; the `Object.values(m).find(Array.isArray)` heuristic picks the wrong export). | Medium | High | D31: `public-api.ts` re-exports ONLY `CATALOG_ROUTES`; prefer the explicit `m.CATALOG_ROUTES` once the export name is build-confirmed. §9 verifies all 5 deep links mount. This is the genuinely new surface vs SP01–04 (all single-component/multi-component); SP03 R-SP3-4 (two-expose) is the closest precedent. If it fails, HALT — it blocks any future flow-owning remote. |
| R-SP5-2 | **Deep-link base-path drift** — collapsing 5 shell children into one `catalogs` `loadChildren` mis-computes a sub-path, so e.g. `/catalogs/:id/edit` 404s or `/catalogs/new` collides with `/catalogs/:id`. | Medium | High | D31: the remote's `path: ''`/`'new'`/`':id/edit'`/`':id/images'`/`':id/preview'` map exactly onto the shell `catalogs` base. ROUTE ORDER matters: `'new'` must precede `':id/edit'` so `new` isn't captured as an `:id`. §9 verifies every one of the 5 deep links + the `new`-vs-`:id` disambiguation. |
| R-SP5-3 | **Spec-discovery regression** — moving ~8 spec files (4 pages + placeholder) into `apps/mfe-catalog/`; relies on SP01's `apps/**/*.spec.ts` glob. | Medium | High | RE-CONFIRM the glob; assert exact total count preserved; drop = hard reject. (Same recipe as SP01 §9.A item 6.) The largest spec-move so far — count carefully. |
| R-SP5-4 | **Route-scoped service lost or re-scoped** — `CatalogFormApiService` (route `providers`) is dropped or promoted to root during the move, changing its lifecycle or causing a NullInjectorError on `:id/edit`. | Medium | High | D32: the `providers` array travels with the `:id/edit` route in `catalog.routes.ts` (cleaner than SP04's single-component case). Service-builder verifies resolution + lifecycle. §9 gate item. The D28a SP04 note anticipated exactly this. |
| R-SP5-5 | **Model over-promotion** — the service-builder promotes page-private schema/DTO types (field-schema, preview-DTO) to `@mesell/core`, bloating the federation singleton and creating false cross-remote contracts (MASTER_PLAN R5). | Medium | Medium | D33: SURGICAL promotion — ONLY canonical `Product`/`Catalog`; grep-verify single-remote use before keeping a type local; pre-approval checklist (c). Over-promotion bloats every remote's shared bundle. |
| R-SP5-6 | **Build-budget regression** — the largest remote (5 pages + heaviest model + the promoted `@mesell/core` types) pushes the catalog remote build past the R4 15 s watch or the shell build past 90 s. | Low | High | D35 + §9 measure both. Stop Condition: shell >90 s OR catalog remote >15 s → HALT, escalate (CLAUDE.md D12 / MASTER_PLAN §7 R4). Each page is a separate lazy chunk inside the remote (the `catalog.routes.ts` uses `loadComponent`), so the remote's INITIAL entry stays small — only the touched page loads. |
| R-SP5-7 | **`@mesell/core` model change becomes a cross-remote contract bomb (MASTER_PLAN R5 P0)** — once `Product`/`Catalog` live in the shared singleton, a future change ships in the shell but a remote built against the old shape is still in the manifest → runtime type mismatch. | Low (now) / Medium (Wave 6) | **P0** | D33 + D35: the C-CI-1 `shared/**`-rebuilds-all rule (noted to infra) means a `@mesell/core/models` change rebuilds the WHOLE workspace; manifest version-pinning (per-env) prevents a stale remote. This is the R5 mitigation made concrete by the first real shared model. SP07 cutover enforces the version-pin. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1.1 | 2026-06-11 | `meesell-frontend-coordinator` (founder-ruling landing session) | Landed the founder's 2026-06-11 morning ruling on D33: **Product/Catalog model promotion to `@mesell/core` APPROVED as recommended** — surgical promotion of ONLY the canonical `Product`/`Catalog` entity types to `@mesell/core/models`, page-private schema/DTO types stay remote-local; executes at SP05 as planned; no LOCKED-doc amendment; the C-CI-1 `shared/**`-rebuilds-all rule (R5) noted to infra. Additive RULED annotation on the D33 FOUNDER-FLAG block + the Founder-decisions-required summary + the §9 FOUNDER-FLAGs acceptance line (also noting D21 RULED at SP03 and D9/D14 resolved at SP07 via the same-day D43/D42 rulings). No structural change. |
| v1 (DRAFT) | 2026-06-10 | `mesell-module-federation-frontend-session-3` (night-run master-session dispatch) | Initial authoring of Sub-Plan 05 — `mfe-catalog` (F7 smart-picker + F8 catalog-form + F9 images + F10 preview), the L-complexity extraction. Grounded in the POST-SP0 integration-branch reality (`e51761b`): 5 route targets = 4 page components + 1 placeholder + 1 route file; `CatalogFormApiService` is `@Injectable()` non-root via route `providers` (the D28a case made real); no page injects AuthService (shell-guard gated, D27); per-page local models + services. D30–D35 (copy-the-recipe; the FIRST `Routes`-array expose `./CatalogRoutes` + the new `loadRemoteRoutesWithFallback` helper D31; route-scoped `CatalogFormApiService` preservation D32; the SURGICAL Product/Catalog promotion to `@mesell/core/models` = the §5-row-5 deliverable D33 FOUNDER-FLAG; route-file subsumption D34; Option-C fifth/largest remote D35). The TWO genuinely new surfaces = the `Routes`-array expose + the shared-model promotion; everything else reuses the proven recipe. The shell route table SHRINKS (5 children + loadChildren → 1 loadChildren) — a strangler-fig win. 7 risks incl. the `Routes`-array resolution (R-SP5-1), deep-link base-path drift incl. the `new`-vs-`:id` order (R-SP5-2), and the cross-remote contract bomb on the first real shared model (R-SP5-7 P0, R5 mitigation). One new FOUNDER-FLAG (D33); D9/D14/D21 inherited. No LOCKED-doc amendment. Awaits founder approval to EXECUTE; gated on SP01–SP04 merged + infra C-CI-1. |
