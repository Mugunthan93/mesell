---
name: spec-w6b-dashboard
description: HYBRID step-1 TASK SPEC for Wave 6 Wave B lane 1 (wave6-dashboard) — wire mfe-dashboard from mock to real GET /products (#26) paginated + DELETE /products/{id} (#21). Consumes the Wave-A-frozen shared surface (interceptors/ApiClient/ErrorService/NetworkService/MeeAlertBanner/MeeOfflineBanner/AuthService.bootstrap, all frozen at fcb9ceb). SPEC ONLY — no code, no dispatch, no git executed by the spec author.
metadata:
  type: project
  session: mesell-wave6-b-specs-session-1
  status: SPEC — awaiting #135 founder merge, then master step-2 dispatch
  base: feature/wave6-dashboard/integration cut from POST-#135 develop (NOT develop tip today b622847)
  parallel_lane_peer: spec_w6b_onboarding.md (mfe-onboarding) — FILE-DISJOINT
---

# Wave 6 · Wave B — lane 1 — `wave6-dashboard` — TASK SPEC

> HYBRID step-1 deliverable. The session window dispatches the named specialists (step 2) with this spec; I am re-dispatched for the merge gate (step 3). I wrote NO feature code, called NO Task, ran NO git this session.

## 0. Governing context — Wave A is the FROZEN floor

This slice branches from **post-#135 develop** (Wave A `wave6-auth-core` integration tip `fcb9ceb` merged by the founder). Wave A delivered and FROZE the entire shared surface this slice depends on. **This slice MUST NOT modify any of it** (§7 parallel-lane discipline):

| Wave-A frozen surface (do NOT edit) | What this slice consumes |
|---|---|
| `libs/core/interceptors/{jwt,refresh,error}.interceptor.ts` | The global `Authorization: Bearer` attach (jwt), 401→refresh→retry (refresh), error-envelope normalisation (error) — registered in `apps/mfe-dashboard/src/main.ts` by Wave A. This slice does NOT add manual auth headers. |
| `libs/core/services/api-client.service.ts` (`ApiClient`) | The typed HttpClient wrapper (`get<T>`, `delete<T>`, `retryOn503` opt-in). The new `DashboardApiService` SHOULD use `ApiClient` (consistent with the Wave-6 convention); raw `HttpClient` is the fallback if ApiClient's surface is insufficient — confirm the as-merged `ApiClient` API at dispatch. |
| `libs/core/services/error.service.ts` (`ErrorService`) | Global error surface written by `errorInterceptor`. Do NOT write to it directly; it is fed by the interceptor. |
| `libs/core/services/network.service.ts` (`NetworkService`) | `online` signal — gates the offline banner (§6 degradation matrix row "offline"). |
| `libs/core/services/auth.service.ts` (`AuthService`, `AuthUser` additive-optional) | `currentUser()` for the (optional) greeting; `logout()` is wired via interceptor on terminal 401. `AuthUser` now has optional `user_id?/plan?/created_at?/last_login_at?` + `phone` required (`id?/name?` legacy-optional). |
| `libs/core/models/product.model.ts` (`Product`, `ProductStatus`) | The D33-promoted canonical `Product` (`ProductResponse` shape). **See §2.5 — the dashboard LIST endpoint does NOT return `Product`; it returns `ProductListItem` (a narrower row). Use `Product` only if a row needs the full shape, which it does NOT.** |
| `@mesell/composites` `MeeAlertBanner` + `MeeOfflineBanner` (NEW in Wave A) | The error-state banner + offline banner the degradation matrix (§6) renders. CONFIRM their exact selectors/inputs from the as-merged `frontend/libs/composites/index.ts` at dispatch (they do NOT exist on develop today — Wave A creates them). |
| `apps/mfe-dashboard/src/main.ts` | Wave A ADDED `provideHttpClient(withFetch(), withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]))` to this remote's dev-serve providers. **This slice must NOT touch main.ts** (it is the Wave-A-frozen registration AND a parallel-lane shared-surface tripwire — see §7). If a Wave-B change to main.ts seems necessary, STOP and escalate. |

**If ANY of the above frozen surface needs a change → STOP and escalate to the founder/master (§10).** Wave B lanes are forbidden from touching `@mesell/core`, the interceptors, or any remote `main.ts`.

## 1. Slice identity & scope

- **Slice:** `wave6-dashboard` (Wave 6, Wave B, lane 1 — parallel with `wave6-onboarding`).
- **Remote:** `apps/mfe-dashboard` ONLY (port 4204). FILE-DISJOINT from lane 2 (`apps/mfe-onboarding`).
- **V1 routes exercised:** `/` (landing — PUBLIC, no auth call, no wiring) + `/dashboard` (authenticated — the wiring target).
- **Endpoints wired:** **#26** `GET /api/v1/products?page=&limit=` (paginated list) + **#21** `DELETE /api/v1/products/{id}` (soft-delete, 204).
- **Specialists:** `meesell-angular-service-builder` (PRIMARY — swap the mock `DashboardApiService` → real HTTP; reconcile the model to the backend wire shape; build the degradation matrix + specs) → `meesell-angular-component-builder` (wire `DashboardComponent` state to the new service shape; render loading/error/empty/offline states; reconcile the status-counts + filter logic to the V1 2-value status) → `meesell-angular-ui-styler` (error/offline banner styling, 360/1280 screenshots). Serial order MANDATORY (§8).

### Scope IN (this slice only — all under `apps/mfe-dashboard/`)
- `apps/mfe-dashboard/src/app/services/dashboard-api.service.ts` (EDIT — mock → real HTTP; add `catchError` matrix)
- `apps/mfe-dashboard/src/app/dashboard.model.ts` (EDIT — reconcile `ProductListItem`/`ProductListResponse` to the backend wire shape §2.1/§2.5)
- `apps/mfe-dashboard/src/app/dashboard.component.ts` (EDIT — wire to new shape; loading/error/empty/offline states; status-count reconciliation)
- `apps/mfe-dashboard/src/app/dashboard.component.spec.ts` (EDIT — assert new shape + error/empty/offline states)
- `apps/mfe-dashboard/src/app/services/dashboard-api.service.spec.ts` (NEW — `HttpTestingController` for #26 + #21 + error matrix)
- `apps/mfe-dashboard/src/app/landing.component.ts` / `.spec.ts` — **NO CHANGE** (landing is public, no data; touch only if a degradation-matrix import leaks — it should not).

### Scope OUT (defer / STOP)
- Any `backend/` change → **STOP** (§10).
- `@mesell/core` (interceptors, ApiClient, ErrorService, NetworkService, AuthService, models) → Wave-A FROZEN. Touch = STOP.
- `apps/mfe-dashboard/src/main.ts` → Wave-A FROZEN registration + parallel-lane tripwire. Touch = STOP.
- `apps/mfe-onboarding/**` (lane 2) → DISJOINT, never touch.
- `@mesell/composites` source — CONSUME `MeeAlertBanner`/`MeeOfflineBanner`/existing composites; do NOT edit composites source (if a composite needs a new input, STOP — that is a shared-surface change).
- `app.routes.ts` route tables → frozen by cutover.
- `status_filter`/`search` server params → **V1.5 deferred** (backend `DashboardQuery` is `page`+`limit` ONLY per dashboard/schemas.py + §13.A.1 amendment). See §2.4 + AMBIGUITY A3.

---

## 2. Ground-truth contract (cited file:line — NO invented shapes)

All paths under `/api/v1`. Verified on `origin/develop` @ `b622847` (the backend surface is stable; #135 is a FRONTEND-only merge so the backend contract is unchanged from today).

### 2.1 #26 — `GET /api/v1/products` — the LIST endpoint (CRITICAL CORRECTION)

> **GROUND-TRUTH OVERRIDE of the MASTER PLAN §1.2 row-26 "CORRECTION".** The prompt instructed me to transcribe row 26 as `PaginatedProductsResponse{items[], total, page, limit}` (key `items`). **This is WRONG and I am resolving it from source, not transcribing the error.** The mounted route returns `DashboardResponse`, NOT `PaginatedProductsResponse`. See A1 (§11) for the full resolution. Builders MUST use the shapes below, NOT the master-plan row.

**Route:** `backend/app/modules/dashboard/router.py` L80-82 — `@router.get("/products", response_model=DashboardResponse)`, mounted `backend/app/main.py` L137 (`app.include_router(dashboard_router)`, prefix `/api/v1` at dashboard/router.py L74). Query params (router.py L88-89): `page: int Query(ge=1)=1`, `limit: int Query(ge=1, le=100)=20`. Auth: JWT (`Depends(get_current_user)`). Rate-limit `dashboard_list` 600/h.

**`PaginatedProductsResponse` (catalog/schemas.py L230-238) is DEAD CODE** — declared, exported in `__all__`, but referenced by ZERO routes (`grep -rn PaginatedProductsResponse backend/app` → only the schemas.py decl + catalog `__init__` import, never a `response_model=`). Do NOT transcribe it.

**The REAL response — `DashboardResponse`** (`backend/app/modules/dashboard/schemas.py`, class `DashboardResponse`):

```
DashboardResponse:
  products: list[ProductListItem]               -> ProductListItem[]   (KEY = "products", NOT "items")
  total: int                                    -> number
  page: int                                     -> number
  limit: int                                    -> number
  onboarding_completeness: ProfileCompletenessSummary  -> see §2.2   (NOT in the master plan at all)
```

**`ProductListItem`** (dashboard/schemas.py, class `ProductListItem`) — the LIST ROW shape (NARROWER than catalog `ProductResponse`):

```
ProductListItem:
  product_id: UUID    -> string   (NOTE: "product_id", NOT "id" — renamed at the dashboard boundary per §13.B.4)
  name: str | None    -> string | null   (nullable until the seller fills it)
  category_id: UUID   -> string   (NOTE: "category_id" — there is NO "category_name" on the wire)
  status: Literal['draft','ready']  -> 'draft' | 'ready'   (§13.A.1 narrows to 2 values; NO 'exported'/'live'/'deleted')
  created_at: datetime -> string  (ISO-8601 TZ)
  updated_at: datetime -> string
```

### 2.2 `ProfileCompletenessSummary` (the header strip — currently UN-rendered by the dashboard)

`DashboardResponse.onboarding_completeness` (dashboard/schemas.py, class `ProfileCompletenessSummary`):

```
ProfileCompletenessSummary:
  base_complete_count: int          -> number
  base_total_count: int             -> number   (always 10 per §8.F, sent so FE renders "8 of 10")
  extension_complete_count: int     -> number
  extension_total_count: int        -> number
  onboarding_complete: bool         -> boolean
```

**V1 SCOPE CALL (lead):** the as-built dashboard does NOT render onboarding completeness anywhere (it renders 4 stat cards = status counts). `onboarding_completeness` arrives on the wire but the page has no slot for it. **This slice DECODES the field into the TS interface (field-for-field, §1.1 contract chain — never drop a wire key silently) but does NOT add a new UI element to render it** — adding a completeness strip is a NEW feature, not API-wiring, and would expand scope. Type it; leave it unrendered; note the unused-but-decoded field in the PR. (A future polish slice can surface it.) This keeps the slice = pure wiring.

### 2.3 #21 — `DELETE /api/v1/products/{id}` (soft-delete)

`backend/app/modules/catalog/router.py` L295-312 — `@router.delete("/products/{id}", status_code=204)`. Path param `id: UUID`. Auth JWT. Returns `Response(status_code=204)` (NO body). Status codes (L311 docstring): **204, 401, 404**. Rate-limit `product_delete` 60/h. Audit `catalog.product.deleted`.

> **NOTE the path key collision (informational, no FE action):** `GET /api/v1/products` (dashboard module) and `POST/DELETE /api/v1/products[/{id}]` (catalog module) share the `/api/v1/products` path prefix across TWO backend modules. This is intentional (dashboard/router.py DECISION-FLAG §13-DASHBOARD-D2). The FE just calls the literal URLs; no FE concern.

### 2.4 Query params — V1 is `page`+`limit` ONLY

`DashboardQuery` (dashboard/schemas.py) = `page` + `limit` (`extra="forbid"`). **`status_filter` and `search` are V1.5-deferred** (§13.A.1 amendment, explicit in the schema docstring). The current frontend sends `status_filter`/`search` to its MOCK (`LoadProductsParams` carries them; the mock filters client-side). **The real endpoint will 400 (`extra="forbid"` would reject them IF sent as body — but they are query params, and FastAPI `Query` validators simply ignore unknown query params unless declared; the risk is they are silently dropped, NOT a 400).** Resolution: see A3 (§11) — the wiring sends ONLY `page`+`limit`; client-side search/filter is RETAINED as a local-only convenience over the current page's rows (no behaviour regression, no server param). This is a documented scope-narrow, not a contract drift.

### 2.5 As-built frontend ground truth (what must change)

`apps/mfe-dashboard/src/app/dashboard.model.ts`:
- `ProductListItem{ id: string, name: string, category_name: string, status: 'draft'|'ready'|'exported'|'live'|'deleted', updated_at: string }` (L14-20) — **MISMATCHES the backend on 3 axes:** (a) `id` vs backend `product_id`; (b) `category_name` vs backend `category_id` (the backend gives NO name, only the UUID); (c) 5-value status vs backend 2-value `'draft'|'ready'`.
- `ProductListResponse{ products, total, page }` (L22-26) — backend ALSO has `limit` + `onboarding_completeness`. `products` key is CORRECT (matches `DashboardResponse.products`).
- `StatusCounts{ draft, ready, exported, live }` (L28-33) + `deriveStatusCounts` (L50-61) + `filterProducts` (L67-87) + `formatRelativeTime` (L93-101) — pure functions.

`apps/mfe-dashboard/src/app/services/dashboard-api.service.ts`:
- `@Injectable()` (NON-root, provided in `DashboardComponent.providers[]` — keep this; it travels with the route per D28a/D32).
- `loadProducts(params)` returns `of({products, total, page}).pipe(delay(800))` (L63-71) — MOCK.
- `deleteProduct(_id)` returns `of(null).pipe(delay(500))` (L73-75) — MOCK.
- `deriveStatusCounts` delegates to the pure fn (L77-79).
- SEED data with `category_name` + `live`/`exported` statuses (L17-53).

`apps/mfe-dashboard/src/app/dashboard.component.ts`:
- injects `DashboardApiService`, `Router`, `MeeConfirmService`, `DestroyRef` (L234-237).
- `fetchProducts()` (L318-341): calls `loadProducts`, maps `res.products`/`res.total`, derives status counts, sets `loading`. **Error handler is `error: () => this.loading.set(false)` (L337-339) — silently swallows; NO error/empty distinction, NO offline.** This is the R-W6-1 gap to fix.
- `deleteProduct(row)` (L343-352): optimistic local filter on success.
- table renders `row.category_name` (L167-169) + `track row.id` (L146) + `row.name` + status badge + `formatRelativeTime(row.updated_at)`.
- 4 stat cards: Draft/Ready/Exported/Live (L65-88). Search input + status `<select>` with draft/ready/exported/live options (L92-122). Client-side pagination math via `pageSize`/`totalCount`.

---

## 3. The build — service layer (§3.x, dependency order)

### 3.1 Reconcile `dashboard.model.ts` to the backend wire shape
Rewrite the TS interfaces to match §2.1/§2.2 EXACTLY (field-for-field, §1.1 contract chain):

```ts
// the LIST row — transcribed from dashboard/schemas.py ProductListItem
export interface ProductListItem {
  product_id: string;
  name: string | null;
  category_id: string;
  status: 'draft' | 'ready';
  created_at: string;
  updated_at: string;
}

// transcribed from dashboard/schemas.py ProfileCompletenessSummary
export interface ProfileCompletenessSummary {
  base_complete_count: number;
  base_total_count: number;
  extension_complete_count: number;
  extension_total_count: number;
  onboarding_complete: boolean;
}

// transcribed from dashboard/schemas.py DashboardResponse — KEY is "products" not "items"
export interface DashboardResponse {
  products: ProductListItem[];
  total: number;
  page: number;
  limit: number;
  onboarding_completeness: ProfileCompletenessSummary;
}
```

**Status-count reconciliation (the load-bearing model decision):** the V1 wire status is 2-value (`'draft'|'ready'`). The 4 stat cards (Draft/Ready/Exported/Live) + the 4-key `StatusCounts` reference `exported`/`live`, which the backend NEVER returns. RESOLUTION (A2, §11): narrow `StatusCounts` to `{ draft: number; ready: number }` and the stat-card UI to 2 cards (Draft, Ready) — OR keep 4 cards with Exported/Live always 0 (visually misleading). **RECOMMEND: 2 cards (Draft, Ready)** — render only what V1 produces; do not show always-zero cards. `deriveStatusCounts` narrows to 2 keys. The component-builder reconciles the template (§3.4). **STOP-flag:** if narrowing to 2 cards is judged a UX regression by the styler, surface it in the PR — but do NOT invent server data to fill 4 cards.

**`LoadProductsParams`:** narrow to `{ page: number; limit?: number }` for the SERVER call (drop `status_filter`/`search` from the server-bound params per §2.4). If the component retains a local search box, the search/filter stays a CLIENT-side function over the current page (A3) — keep `filterProducts` as a pure local helper, do NOT pass its params to the service.

### 3.2 `DashboardApiService` — mock → real HTTP (#26 + #21)
EDIT `services/dashboard-api.service.ts`. Keep `@Injectable()` (NON-root, route-scoped via component `providers[]`).

- **`loadProducts({ page, limit })`:** `ApiClient.get<DashboardResponse>('/api/v1/products', { params: { page, limit } })` (or raw `HttpClient.get<DashboardResponse>` with `HttpParams` if ApiClient's params surface is thin — confirm at dispatch). The `jwtInterceptor` attaches Bearer automatically — **NO manual `Authorization` header** (this is the #101 → Wave-A migration; the dashboard mock never had one, so just do not add one). Returns `Observable<DashboardResponse>`.
- **`deleteProduct(id: string)`:** `ApiClient.delete<void>('/api/v1/products/' + id)` (204, no body). Returns `Observable<void>`.
- **`deriveStatusCounts`:** delegate to the narrowed pure fn (§3.1).
- **Remove** the `SEED_PRODUCTS` const, the `of(...).pipe(delay(...))`, and the `delay`/`of` imports (grep-verify `of(.*).pipe(.*delay` = 0 in the file post-edit).

### 3.3 Graceful-degradation matrix (§6 — MANDATORY, copied from Wave A §6 VERBATIM-pattern)
Both service methods carry a `catchError` matrix per §6. The merge gate REJECTS a wired service with no matrix (R-W6-1).

### 3.4 (component-builder) Wire `DashboardComponent`
- Map `res.products`→`products` signal, `res.total`→`totalCount`, decode `res.limit` + `res.onboarding_completeness` (store the latter in a signal even if unrendered — §2.2). `track row.product_id` (was `row.id`). `onRowClick` navigates `['/catalogs', row.product_id, 'edit']`. `onDeleteClick`/`deleteProduct` use `row.product_id`.
- **Category column:** the wire gives `category_id` (a UUID), NOT a display name. RESOLUTION (A4, §11): the V1 dashboard has no category-name lookup endpoint mounted for the list. RECOMMEND: drop the "Category" column for V1 (or show a truncated id — ugly). **Cleaner: remove the Category column** (the list is "My Catalogs" by product name + status + updated; category is editable inside the catalog). Flag the column removal in the PR as a wire-driven scope-narrow, not a regression. Do NOT invent a category-name field.
- **Degradation states (§6):** `loading` skeleton (exists); on `error` outcome → render `MeeAlertBanner` with a retry affordance (re-call `fetchProducts`); on `empty` (200 + `products:[]`) → keep the existing `MeeEmptyState`; on offline (`NetworkService.online()===false`) → render `MeeOfflineBanner` instead of the error banner. The component subscribes `{ next, error }` and sets an `error` signal in `error` (defence-in-depth even though the service catchErrors).
- Status filter `<select>`: narrow options to All/Draft/Ready (drop Exported/Live). Search box: client-side over current page (A3) or remove if the styler prefers — keep it minimal.

### 3.5 (ui-styler) error/offline banner styling + screenshots
Tailwind + `mee-*` primitives only; boundary 0 (no PrimeNG outside ui-kit). 360px + 1280px screenshots of the dashboard in **loading + error + empty + data** states for the PR.

---

## 4. Model promotion — none

This slice promotes NOTHING to `@mesell/core`. `Product` (the full `ProductResponse`) was promoted by Wave A (D33). The dashboard LIST row is `ProductListItem` (a NARROWER, dashboard-private shape) — it is consumed by mfe-dashboard ONLY → stays remote-private (SP05 D32 2+-remote criterion not met). Do NOT import `Product` from `@mesell/core` for the list rows (wrong shape). `ProfileCompletenessSummary` is also dashboard-private.

---

## 5. (reserved — no auth-flow wiring in this lane)

This lane has no OTP/login wiring (that was Wave A). The only auth touch is implicit: the `jwtInterceptor` attaches Bearer to `GET /products` + `DELETE`, and a terminal 401 (refresh also failed) triggers `AuthService.logout()` via the `refreshInterceptor` → the matrix returns a fallback. The landing page (`/`) is PUBLIC and does NO data call (no change).

---

## 6. Graceful-degradation matrix (VERBATIM from Wave A §6 — the canonical pattern)

> **R-W6-1 (P0). The merge gate REJECTS any wired service that removes its mock without this pattern.**

1. **Every wired `dashboard-api.service.ts` method has a `catchError` error matrix** mapping `HttpErrorResponse.status` → typed outcome:
   - **401** → handled by `refreshInterceptor` (retry); only reaches the service if refresh ALSO failed → matrix lets the interceptor's `logout()` stand and returns a contract-shaped fallback (`{ products: [], total: 0, page, limit, onboarding_completeness: <zeroed> }` for `loadProducts`; `EMPTY`/no-op for `deleteProduct`). NEVER throw to a white screen.
   - **402** (plan-guard quota) → contract-shaped fallback (empty list). NEVER throw. (Dashboard is plan_guard-EXCLUDED per dashboard/router.py docstring, so 402 is unlikely here — but the matrix handles it uniformly.)
   - **400** (bad pagination) → caller-validated; the FE only ever sends valid `page>=1`/`limit 1..100`, so 400 should not occur; if it does → empty fallback + log.
   - **404** (delete: product not found / already deleted) → for `deleteProduct`, treat as success-equivalent (the row is gone) — remove the row locally; do NOT error-banner. For `loadProducts`, 404 is not expected (empty inventory is 200 + `[]`).
   - **5xx** (server unavailable) → contract-shaped fallback (empty) + the component renders the `MeeAlertBanner` error state with a retry, NOT a crash.
2. **The component renders an EXPLICIT state for every outcome** — `loading`/`error`/`empty`/`data` signals + the `MeeAlertBanner` (error) / `MeeEmptyState` (empty) / `MeeOfflineBanner` (offline) / data table. NEVER let an unhandled throw white-screen.
3. **`NetworkService.online` gates the offline banner** — when offline, render `MeeOfflineBanner` ("You are offline") instead of a confusing 0-status error.
4. **`ErrorService`** receives the typed envelope from `errorInterceptor` for any global surface — non-blocking, does not replace the per-service matrix.

**This lane's application:** `loadProducts` failure → error signal → `MeeAlertBanner` + retry (NOT the old silent `loading.set(false)`); `deleteProduct` failure → leave the row, surface a transient error (toast or inline) — do NOT optimistically remove a row that failed to delete.

---

## 7. Branch plan (Model C — documented, NOT executed by the spec author) + PARALLEL-LANE discipline

Per MASTER PLAN §4.1 + proven SP01-07 Model C. The LEAD executes at step-2 dispatch time (not the spec author, not now):

- **Integration branch:** `feature/wave6-dashboard/integration` cut from **POST-#135 develop** (re-fetch after the founder merges #135 — do NOT branch from today's `b622847`, which predates Wave A). **F3-protected** via `gh api PUT .../protection` with a JSON-file body (the `-f/-F` mix produces malformed payload — memory): `required_status_checks: null`, review-count 0, force-push off, deletions off.
- **Group branch:** `feature/wave6-dashboard/frontend` cut from the integration branch.
- **Worktree:** `/tmp/mesell-wt/w6b-dash`. `pnpm install --config.dangerously-allow-all-builds=true` (or `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract` if the flag is env-blocked — memory); run `./node_modules/.bin/ng build mfe-dashboard` / `ng build frontend` directly (not `pnpm build`).
- **Master tree:** NEVER branch-switch it; create branches via `git branch <name> <start>` + push, never `checkout`.
- **Founder-gate PR:** `feature/wave6-dashboard/integration` → `develop`, title `[FOUNDER GATE — DO NOT MERGE]`, **LEFT OPEN** — the lead does NOT approve it (D1). The lead DOES gate + squash-merge the `frontend` → `integration` group PR (`gh pr merge --squash --admin`; branch delete via `gh api -X DELETE .../git/refs/heads/<branch>`).
- **5-calendar-day cap** on the open group branch (STOP / escalate per repo-mgmt §1.2).

### PARALLEL-LANE discipline (lane 1 ‖ lane 2 — FILE-DISJOINT, enforced)
- **This lane touches ONLY `apps/mfe-dashboard/**`.** Lane 2 (`wave6-onboarding`) touches ONLY `apps/mfe-onboarding/**`. ZERO file overlap (different remotes). The two integration branches both cut from the SAME post-#135 develop tip → when both founder-gate PRs land, the union is conflict-free (disjoint file sets — the SP02‖SP03 precedent).
- **Shared surfaces are FROZEN (Wave A).** `@mesell/core` (any file), `@mesell/composites` source, ANY remote `main.ts`, `apps/shell/**` → if THIS lane needs to change any of them, **STOP and escalate** (§10). A Wave-B lane changing a shared surface breaks the disjointness guarantee and the singleton.
- **`@mesell/composites` consumption (not edit):** importing `MeeAlertBanner`/`MeeOfflineBanner`/existing composites is fine (read-only consumption). Lane 2 also imports composites — that is NOT a conflict (both import; neither edits the barrel/source). If a banner needs a NEW input that does not exist as-merged → STOP (composites source change = shared surface).

---

## 8. Builder sequence (SERIAL — mandatory) + dispatch headers

The three specialists run SERIAL on the SAME `feature/wave6-dashboard/frontend` branch (they touch overlapping files: the service shape the component consumes; the template the styler restyles).

1. **`meesell-angular-service-builder` (session-1)** — reconcile `dashboard.model.ts` to the backend wire shape (§3.1); rewrite `DashboardApiService` mock→real HTTP for #26 + #21 with the §6 `catchError` matrix (§3.2/§3.3); author `dashboard-api.service.spec.ts` (`HttpTestingController`: #26 asserts `GET /api/v1/products?page=&limit=`, maps `DashboardResponse.products`/`total`/`limit`/`onboarding_completeness`; #21 asserts `DELETE /api/v1/products/{id}` 204; error-matrix tests for 401/402/404/5xx). Re-confirm the `apps/mfe-dashboard/**/*.spec.ts` test-discovery glob still matches (SP0 cwd-glob gotcha).
2. **`meesell-angular-component-builder` (session-2)** — wire `DashboardComponent` to the new shape (§3.4): `product_id` rename, drop Category column (A4), narrow status to draft/ready (A2), decode-but-don't-render `onboarding_completeness` (§2.2), render the §6 degradation states (`MeeAlertBanner`/`MeeOfflineBanner`/`MeeEmptyState`), client-side-only search/filter (A3). Update `dashboard.component.spec.ts` to assert the new shape + error/empty/offline states.
3. **`meesell-angular-ui-styler` (session-3)** — error/offline banner styling, narrowed stat cards, 360px+1280px screenshots (loading/error/empty/data). Tailwind + mee-* only; boundary 0.

### Dispatch header template (each specialist)
```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/apps/mfe-dashboard/. NO backend/ changes. NO @mesell/core / composites-source / main.ts / shell / mfe-onboarding changes (Wave-A FROZEN + parallel-lane disjoint).
SESSION: mesell-wave6-dashboard-frontend-session-{N}
TASK: <the §-slice above for this specialist>
CONTEXT: Wave 6 Wave B lane 1. Ground truth = spec_w6b_dashboard.md §2 (cited backend file:line). GET /products returns DashboardResponse{products[],total,page,limit,onboarding_completeness} — products NOT items, product_id NOT id, category_id NOT category_name, status 2-value draft|ready. Branch feature/wave6-dashboard/frontend, worktree /tmp/mesell-wt/w6b-dash, cut from POST-#135 develop. Degradation matrix = §6 (MANDATORY). Consume Wave-A-frozen interceptors/ApiClient/ErrorService/NetworkService/MeeAlertBanner/MeeOfflineBanner — confirm their as-merged surfaces, do NOT modify them.
OUTPUT: <files + the §9 validation checklist evidence the PR template needs>
```

---

## 9. Validation checklist (the step-3 merge gate runs ALL of these, skeptical-lead, in a review worktree)

- **Builds GREEN ≤ 90 s (D12):** `ng build mfe-dashboard` AND `ng build frontend` (shell). Record each time. >90 s = STOP.
- **Full suite, NO drop:** baseline = the post-#135 develop spec-file count (47 on develop today + Wave A's new specs — **re-establish the exact baseline at dispatch via `git ls-tree -r --name-only origin/develop -- frontend/ | grep -c '\.spec\.ts$'`** once #135 lands). New `dashboard-api.service.spec.ts` makes the count MONOTONICALLY RISE; the edited `dashboard.component.spec.ts` does NOT drop. A DROP = silent test-discovery failure (SP0 cwd-glob gotcha) = HARD REJECT. `CI=true ng test frontend`, 0 fail / 0 skip, exit 0. Re-confirm `apps/mfe-dashboard/**/*.spec.ts` discovery (3 dashboard specs: dashboard.component, landing.component, dashboard-api.service[NEW]).
- **Boundary grep = 0:** `grep -rn "from 'primeng" frontend/apps/mfe-dashboard --include=*.ts | grep -v libs/ui-kit/` → 0.
- **Singleton non-drift (P0, §6.G):** mfe-dashboard already shares `@mesell/ui-kit`+`@mesell/composites` and (post-Wave-A) imports interceptors from `@mesell/core` via main.ts. Prove EXACTLY ONE `_mesell_core.js` chunk in the mfe-dashboard dist; AuthService class DEFINITION lives ONLY there (not inlined). The interceptor import (Wave-A main.ts) keeps core in the graph — VERIFY no second core chunk introduced by this slice's service.
- **Mock-removal grep:** `grep -rn "of(.*).pipe(.*delay" frontend/apps/mfe-dashboard --include=*.ts` → 0; `SEED_PRODUCTS` removed; no `import { delay }` / `import { of }` left unused in the service.
- **Contract greps:** (a) wired URLs match §2.1/§2.3 EXACTLY — `grep -rn "/api/v1/products" frontend/apps/mfe-dashboard` shows the GET (list) + DELETE literal; (b) NO manual `Authorization`/`Bearer`/`authHeaders` in the dashboard service (`grep -rn "Authorization\|authHeaders\|Bearer" frontend/apps/mfe-dashboard` = 0 — the interceptor owns it); (c) `localStorage`/`sessionStorage` = 0 (FE-D5); (d) NO `withCredentials` (this slice is not auth-cookie traffic).
- **Shape-fidelity grep:** the TS interface uses `products`/`product_id`/`category_id`/2-value `status` — `grep -rn "items\b\|category_name\|'exported'\|'live'\|'deleted'" frontend/apps/mfe-dashboard/src/app/dashboard.model.ts` → 0 (the stale mock keys are GONE). `onboarding_completeness` decoded in the interface.
- **Degradation coverage (R-W6-1):** the service has a `catchError` matrix (grep `catchError` present); the component renders `MeeAlertBanner`(error) + `MeeOfflineBanner`(offline) + `MeeEmptyState`(empty); a spec asserts the error/empty/offline render paths. NO `catchError` = automatic REJECT.
- **Parallel-lane disjointness:** `git diff --name-only <base>..HEAD` touches ONLY `apps/mfe-dashboard/**` (ZERO `@mesell/core`, composites-source, `main.ts`, shell, or `apps/mfe-onboarding/**` paths). Any out-of-lane file = REJECT.
- **TS strict + strictTemplates ON:** `tsc` app + spec EXIT 0.
- **a11y + screenshots:** keyboard nav on the table rows + delete button + pagination; aria on the table/rows/buttons; 360px + 1280px screenshots of loading/error/empty/data states.
- **PR template fully filled** (no `<>` placeholders), bundle delta noted (expect near-zero shell-initial delta — this is remote-local; the HttpClient infra chunk was paid by Wave A).
- **Gate-4 note:** record whether `GET /products` (dashboard) + `DELETE /products/{id}` (catalog) have Gate-4 real-Postgres CI coverage at dispatch (the two-sided proof). Do NOT block on Gate-4 (§5.2 MASTER PLAN).

---

## 10. STOP conditions (escalate — do NOT paper over)

1. **ANY `backend/` change needed = STOP and report** (cross-lead memo to backend, not an edit). The 28-endpoint surface is LOCKED.
2. **ANY shared-surface change needed** (`@mesell/core`, interceptors, `@mesell/composites` source, any remote `main.ts`, `apps/shell/**`) = STOP and escalate (breaks Wave-A freeze + parallel-lane disjointness + singleton).
3. **Contract drift BEYOND the documented set** (A1 `items`→`products`, A2 status narrowing, A3 query params, A4 category-name, §2.2 unrendered completeness) — a NEW runtime 4xx/shape surprise → STOP, raise a backend memo, do NOT add a client-side shim (R-W6-2 / §5.3).
4. **Build > 90 s (D12).**
5. **TS strict accidentally disabled.**
6. **Singleton §6.G grep shows a duplicated `@mesell/core` chunk** in mfe-dashboard dist = P0 reject (R-W6-3).
7. **Any wired service shipped without a `catchError` matrix** = automatic reject (R-W6-1).
8. **The diff touches a file outside `apps/mfe-dashboard/**`** = parallel-lane violation = reject (fix the lane boundary before re-review).
9. **`feature/wave6-dashboard/frontend` open > 5 calendar days** unmerged.
10. **A 400 from `GET /products` because `status_filter`/`search` were sent as server params** (A3 not honored) = design defect, fix before merge (send `page`+`limit` only).

---

## 11. Open ambiguities + ground-truth resolutions (resolved here, NOT punted)

| # | Ambiguity | Resolution (ground-truth) |
|---|---|---|
| A1 | MASTER PLAN §1.2 row-26 CORRECTION says `GET /products` returns `PaginatedProductsResponse{items[],total,page,limit}` (key `items`); the prompt told me to transcribe this verbatim. | **OVERRIDDEN from source.** The mounted route returns **`DashboardResponse`** (dashboard/router.py L82, mounted main.py L137), NOT `PaginatedProductsResponse`. The array key is **`products`** (dashboard/schemas.py `DashboardResponse.products`), NOT `items`. `PaginatedProductsResponse` (catalog/schemas.py L230) is DEAD CODE — referenced by ZERO routes. The wire ALSO carries `onboarding_completeness` (a `ProfileCompletenessSummary`) the master plan never mentions. **The master-plan row-26 "correction" is itself a transcription error — flagged for a docs-chore fix; builders use §2.1, NOT the master plan.** This is a P0 spec-level catch (a builder transcribing the master plan would have produced `items` and 4xx'd / silently-undefined on `res.items`). |
| A2 | Stat cards show Draft/Ready/Exported/Live; backend status is 2-value `'draft'|'ready'`. | RESOLVED: narrow to 2 cards (Draft, Ready) + `StatusCounts{draft,ready}`. `'exported'/'live'/'deleted'` do NOT exist in the V1 wire (§13.A.1 narrows; `exported` lives on the `exports` table, not products). Render only what V1 produces. Styler flags if 2 cards reads as a regression — but do NOT invent server data. |
| A3 | Mock sends `status_filter`/`search`; backend `DashboardQuery` is `page`+`limit` only (`extra="forbid"`, V1.5-deferred). | RESOLVED: send ONLY `page`+`limit` to the server. Retain search/filter as a CLIENT-side convenience over the current page's rows (`filterProducts` pure fn stays, local-only) OR drop them (styler's call). NOT a contract drift — a documented scope-narrow. Sending them as server params risks silent-drop (query) and is wrong intent. |
| A4 | Table renders `category_name`; backend `ProductListItem` gives `category_id` (UUID), no name. | RESOLVED: there is NO category-name on the list wire and no mounted name-lookup for the list. RECOMMEND drop the Category column for V1 (category is editable inside the catalog flow). Do NOT invent a name field or call a per-row lookup (N+1). Flag the column drop in the PR. |
| A5 | Does the dashboard render `onboarding_completeness`? | RESOLVED: decode it into the TS interface (never silently drop a wire key) but do NOT add a new UI element — that is a NEW feature, not wiring. Type it, leave it unrendered, note it in the PR (§2.2). |
| A6 | Does `DashboardApiService` use `ApiClient` or raw `HttpClient`? | RESOLVED: PREFER `ApiClient` (Wave-6 convention) IF its `get`/`delete` + `params` surface (as merged in Wave A) is sufficient; else raw `HttpClient` with `HttpParams`. Confirm the as-merged `ApiClient` signature at dispatch. Either way, NO manual auth header (interceptor owns it). |
| A7 | `id` vs `product_id` everywhere (track, navigate, delete). | RESOLVED: backend key is `product_id`. Rename all 4 component sites (`track`, `onRowClick` nav, `onDeleteClick`, `deleteProduct` local filter) from `row.id` → `row.product_id`. The `/catalogs/:id/edit` ROUTE param name is unchanged (it is a route token, not the wire key) — pass `row.product_id` as the value. |
| A8 | Baseline spec count for the no-drop gate. | 47 on `origin/develop` today; the REAL baseline = post-#135 develop (47 + Wave A's new specs). Re-establish at dispatch (`git ls-tree ... | grep -c spec`). Do NOT hardcode 47 — Wave A raised it. |
| A9 | Do `MeeAlertBanner`/`MeeOfflineBanner` exist? | RESOLVED: NOT on develop today; Wave A creates them in `@mesell/composites` (frozen at fcb9ceb). Confirm exact selectors/inputs from the as-merged `frontend/libs/composites/index.ts` at dispatch. Consume, do NOT edit the composites source. |

---

## 12. Cross-lead memos to open (lead, at dispatch — recorded, not yet filed)

- **→ founder / docs-chore (lead, fast-mode):** MASTER PLAN §1.2 row-26 CORRECTION is itself WRONG — `GET /products` returns `DashboardResponse{products[],...,onboarding_completeness}`, NOT `PaginatedProductsResponse{items[]}`. Fix the row + add a revision note. (A1.) Do BEFORE the Wave B dashboard build dispatch so no builder transcribes the wrong shape.
- **→ backend (`meesell-backend-coordinator`):** confirm `GET /api/v1/products` + `DELETE /api/v1/products/{id}` have Gate-4 real-Postgres CI coverage (the two-sided proof note for the PR). No contract question — the schemas are verified §2. INFORMATIONAL.
- **→ ai (`meesell-ai-coordinator`):** NONE for the dashboard lane (no AI affordance on the list/landing).
