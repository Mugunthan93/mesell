# Wave 6 — API Wiring · MASTER PLAN

**Owner:** MeeSell Frontend Lead (`meesell-frontend-coordinator`)
**Status:** ACTIVE — all §7 decisions RULED by founder 2026-06-11 (night); Wave A executing
**Authored:** 2026-06-11 · session `mesell-wave6-planning-session-1`
**Base:** `origin/develop` @ `5cd6e32` (federation program COMPLETE — 7 apps + 4 libs + #101 smart-picker-wiring + #105 cutover all on develop)
**Pattern:** canonical v2.1, fence-aware audit. Grounded in the AS-BUILT federated topology, NOT the pre-split shell.

---

## 0. Premise & one-paragraph summary

The federation program is done. Every V1 page now lives in its final home — a Native Federation remote (`apps/mfe-*`) or the shell (`apps/shell`). But **the data layer is still mock**: of the 10 V1 routes across 6 remotes, exactly ONE service is HTTP-wired today (smart-picker `CategoryService`, landed by #101). Everything else returns `of(SEED).pipe(delay(N))` from a feature service or an inline `setTimeout` mock inside the component. Wave 6 wires every page to the real backend (28 mounted endpoints, 8 modules) WITHOUT inventing shapes — the contract chain is **Pydantic schema (source of truth) → typed api-client interface → page wiring**. The keystone is the FE-D5 auth loop (in-memory access JWT + HttpOnly refresh cookie + 401→refresh→retry interceptor) which does NOT exist yet and gates every authenticated page.

**Scope boundary:** Wave 6 is frontend HTTP wiring only. It does NOT touch backend endpoints (live on develop), AI prompts (AI lane owns those — §6), or infra hosting (carried to cutover week per SP07). It does NOT change `app.routes.ts` route tables — routes are frozen by the federation cutover; the shared surfaces now are `api-client` + `@mesell/core` models + interceptors.

---

## 1. Contract inventory (pages × endpoints)

### 1.1 The contract chain (NON-NEGOTIABLE)

```
backend/app/modules/<m>/schemas.py   ← SOURCE OF TRUTH (Pydantic, locked)
        │  (manual transcription, field-for-field; NO invented keys)
        ▼
frontend/libs/core/models/*.ts  +  per-remote *.model.ts   ← typed TS interfaces
        │  (consumed by the api-client method signature)
        ▼
<remote>/.../services/*-api.service.ts   ← HttpClient call, typed <T>
        │
        ▼
<page>.component.ts   ← subscribes, maps to signal, renders loading/error/data
```

A specialist MUST read the backend `schemas.py` for the endpoint before authoring the TS interface. If a field's type is ambiguous (e.g. `Decimal` → `string` vs `number`), the specialist STOPS and the lead raises a cross-lead memo to backend — no guessing.

### 1.2 Backend endpoint surface (28 mounted — verified from `backend/app/modules/*/router.py` on develop)

All under `/api/v1`. JWT-protected unless noted.

| # | Module | Method · Path | Response schema (source of truth) | Auth |
|---|---|---|---|---|
| 1 | iam | `POST /auth/otp/send` | `SendOtpResponse{request_id}` | public |
| 2 | iam | `POST /auth/otp/verify` | `VerifyOtpResponse{access_token, expires_in, token_type}` + `Set-Cookie: refresh_token` | public |
| 3 | iam | `POST /auth/refresh` | `RefreshResponse{access_token, expires_in}` + rotated `Set-Cookie` | cookie-auth |
| 4 | iam | `POST /auth/logout` | `204` + cookie clear | cookie-auth |
| 5 | iam | `GET /auth/me` | `MeResponse{user_id, phone, plan:'free', created_at, last_login_at}` | JWT |
| 6 | iam | `POST /webhooks/razorpay` | `WebhookCaptureResponse` | backend-only (NOT a FE consumer) |
| 7 | customer | `GET /seller-profile` | `SellerProfileResponse` | JWT |
| 8 | customer | `PATCH /seller-profile` | `SellerProfileResponse` | JWT |
| 9 | customer | `PATCH /seller-profile/active-categories` | `SellerProfileResponse` | JWT |
| 10 | customer | `PATCH /seller-profile/compliance/{super_id}` | `SellerProfileResponse` | JWT |
| 11 | customer | `GET /seller-profile/required-fields` | `RequiredFieldsResponse` | JWT |
| 12 | category | `GET /categories/suggest?q=` | `SuggestResponse{suggestions[0..5], fallback_offered}` | JWT | **WIRED (#101)** |
| 13 | category | `GET /categories/browse` | `BrowseResponse` | JWT |
| 14 | category | `GET /categories` | `CategoryTreeResponse` (+ETag) | JWT |
| 15 | category | `GET /categories/{id}/schema` | `SchemaResponse` (+ETag) | JWT |
| 16 | category | `GET /categories/{id}/field-enum/{name}?q=` | `FieldEnumResponse` | JWT |
| 17 | catalog | `POST /products` | `ProductResponse{id, catalog_id, category_id, name, status, fields, ai_suggestions, …}` | JWT | **partial (#101 posts here, see DISCREPANCY-1)** |
| 18 | catalog | `PATCH /products/{id}` | `ProductResponse` (autosave) | JWT |
| 19 | catalog | `POST /products/{id}/autofill` | `AutofillResponse{suggestions[], fallback_offered}` | JWT | **AI-lane boundary — §6** |
| 20 | catalog | `GET /products/{id}/preview` | `ProductPreviewResponse{fields[], …}` | JWT |
| 21 | catalog | `DELETE /products/{id}` | `204` (soft-delete) | JWT |
| 22 | catalog | `GET /products/{id}/draft` | `ProductDraftResponse` (draft-recovery) | JWT |
| 23 | image | `POST /products/{id}/images` | `ImageUploadResponse` (202 ACCEPTED) | JWT |
| 24 | image | `GET /products/{id}/images` | `ImagesListResponse` (poll for precheck) | JWT | **AI-lane boundary — §6** |
| 25 | pricing | `POST /products/{id}/price-calc` | `PriceCalcResponse{mrp, meesho_price, …, alerts[]}` | JWT | **DECISION-1 (client vs server calc)** |
| 26 | dashboard | `GET /products?page=&limit=` | `DashboardResponse{products: ProductListItem[], total, page, limit, onboarding_completeness}` | JWT |

> **AUTHORITATIVE CONTRACT (row 26) — set 2026-06-12 from the MOUNTED source by the Wave B spec session. DO NOT FLIP BACK.**
>
> The real, **mounted** dashboard response is **`DashboardResponse`**, NOT `PaginatedProductsResponse`. Source of truth, verified field-for-field:
> - `backend/app/modules/dashboard/schemas.py` **L81-90** — `class DashboardResponse{ products: list[ProductListItem], total: int, page: int, limit: int, onboarding_completeness: ProfileCompletenessSummary }`. The array key is **`products`** (the empty-inventory contract returns `products=[]` + `total=0`, router L101).
> - `backend/app/modules/dashboard/schemas.py` **L53-58** — `class ProductListItem{ product_id: UUID, name: str | None, category_id: UUID, status: Literal['draft','ready'], created_at: datetime, updated_at: datetime }`. Note `product_id` (the `id`→`product_id` rename happens at the dashboard boundary, schema L46), `name` is **nullable**, `status` is the 2-value narrow (`'exported'` deferred to V1.5).
> - `backend/app/modules/dashboard/router.py` **L80-82** — `@router.get("/products", response_model=DashboardResponse)`; **`backend/app/main.py` L137** — `app.include_router(dashboard_router)`. This is the route the `GET /api/v1/products` dashboard list actually resolves to.
>
> **Why `PaginatedProductsResponse{items[]}` is WRONG:** that schema lives in `backend/app/modules/catalog/schemas.py` and is referenced by **ZERO mounted routes** — it is dead code. The Wave B spec session proved this from source. Do not wire against it.
>
> The TS interface and the `mfe-dashboard` wiring (Wave B lane 1) MUST transcribe **`products`/`total`/`page`/`limit`/`onboarding_completeness`** (and the `ProductListItem` shape above) field-for-field per the §1.1 contract chain. The authoritative wiring spec is **`.claude/agent-memory/meesell-frontend-coordinator/spec_w6b_dashboard.md`** — cross-reference it; it transcribes the mounted shape. The §2.2 promotion analysis row "`DashboardResponse` → mfe-dashboard only → remote-private" was always correct and stands (keep the remote-private type named `DashboardResponse`).
>
> **Double-correction history (so nobody flips it back a THIRD time):**
> - **2026-06-11 (original):** row 26 recorded as `DashboardResponse{products[], total, page}` — **right schema name + right array key (`products`)**, but with undocumented/incomplete fields (missing `limit` + `onboarding_completeness`, no `ProductListItem` detail).
> - **2026-06-11 (PR #111 "correction"):** flipped to `PaginatedProductsResponse{items[], total, page, limit}` citing `catalog/schemas.py` L230-238. **This was the wrong fix** — it swapped in a dead-code catalog schema (`items[]`) that no mounted route returns, replacing the originally-correct `products[]` key.
> - **2026-06-12 (this revision, AUTHORITATIVE):** restored to the **mounted** `DashboardResponse{products: ProductListItem[], …}` with full field detail + source-line citations + the `ProductListItem` shape, cross-referenced to `spec_w6b_dashboard.md`. The first correction was directionally right (the schema was always `DashboardResponse`); the second over-corrected into dead code. This row is now anchored to the mounted source — verify against `dashboard/schemas.py` L81-90 before ANY future change.
| 27 | export | `POST /products/{product_id}/export-xlsx` | `ExportInitiatedResponse{export_id, status:'pending', enqueued_task_id}` | JWT |
| 28 | export | `GET /exports/{export_id}` | `ExportResponse{export_id, status, xlsx_signed_url?, zip_signed_url?, error_*?}` | JWT |

**FE consumes 26 of 28** (webhook #6 is backend-only; otp/me/refresh/logout are auth-infra not page data → 22 page-data endpoints + 4 auth-infra + 2 not-consumed).

> **⛔ ONBOARDING DOMAIN-MISMATCH (P0, founder ruling pending) — flagged 2026-06-12.** Rows #7–#11 (customer module) are **entirely Legal-Metrology compliance fields**; the as-built onboarding/profile UI collects fields (`businessName`, `city`, `gstNumber`, display `name`) that **do not exist on the wire**. Wave B lane 2 (`wave6-onboarding`) is therefore NOT a pure mock→real wiring slice and is BLOCKED on a founder Option-A/B/C ruling before build dispatch — see `.claude/agent-memory/meesell-frontend-coordinator/spec_w6b_onboarding.md` §2.6.

### 1.3 Page × endpoint × current state (the Wave-6 worklist)

| Remote | Route(s) | Page | Endpoints it needs | Current state | Wired? |
|---|---|---|---|---|---|
| `mfe-auth` (4206) | `/login`, `/signup`, `/otp-verify` | login / signup / otp-verify | #1 send, #2 verify, (#5 me on bootstrap) | inline `setTimeout` mock; `otp-verify` calls `AuthService.setSession('mock-token',…)` (C4 write proven, mock token) | **NO** |
| `mfe-onboarding` (4202) | `/onboarding`, `/profile` | onboarding / profile | #7 get-profile, #8/#9/#10 patch, #11 required-fields | inline mock | **NO** |
| `mfe-dashboard` (4204) | `/`, `/dashboard` | landing (public) / dashboard | #26 list, #21 delete | `DashboardApiService` `of(SEED).delay()` | **NO** (mock service exists) |
| `mfe-catalog` (4205) | `/catalogs/new` | smart-picker | #12 suggest, #17 create | `CategoryService` HTTP | **YES (#101)** |
| `mfe-catalog` (4205) | `/catalogs/:id/edit` | catalog-form | #15 schema, #18 autosave, #19 autofill, #22 draft, #16 field-enum | `CatalogFormApiService` `of(SEED).delay()` + inline mock | **NO** (mock service exists) |
| `mfe-catalog` (4205) | `/catalogs/:id/images` | image-uploader | #23 upload, #24 poll | inline mock | **NO** |
| `mfe-catalog` (4205) | `/catalogs/:id/preview` | preview | #20 preview | inline mock | **NO** |
| `mfe-pricing` (4201) | `/catalogs/:id/pricing` | pricing | #25 price-calc | self-contained client-side P&L math, NO service | **NO** (DECISION-1) |
| `mfe-export` (4200) | `/catalogs/:id/export` | export | #27 initiate, #28 poll | inline `setInterval` job-poll mock | **NO** |

**Summary count: 9 pages × 26 page-data endpoints. 1 page wired (smart-picker). 8 pages to wire. 3 mock services to swap (dashboard, catalog-form, smart-picker[done]); 5 pages have inline mocks needing service extraction first.**

### 1.4 Known contract discrepancies to resolve (carried from #101 + audit)

- **DISCREPANCY-1 (smart-picker `selectCategory`):** #101's `CategoryService.selectCategory()` posts to `POST /api/v1/catalogs` and navigates to `/catalogs/:id/edit`. Backend endpoint #17 is `POST /api/v1/products` returning `ProductResponse{id,…}`. The route alias `/catalogs` does not exist on the backend router. **This is a live latent bug** — the wired smart-picker create-path will 404 against the real backend. Wave 6 wave-C MUST reconcile: either FE re-points to `POST /products` (recommended — backend is source of truth) or backend adds a `/catalogs` alias (cross-lead memo). Flagged to founder as DECISION-2.
- **`POST /products` body shape:** smart-picker sends `{category_id}`. Backend `create_product` expects the `ProductCreate` request schema — must verify the create body matches (catalog_id derivation, name optionality). Verify at wave-C dispatch.
- **`Decimal` typing (pricing):** `PriceCalcResponse` uses `Decimal` for mrp/price/profit. FastAPI serialises `Decimal` to JSON string by default unless configured to float. The TS interface MUST match the wire format — verify the actual serialised shape (string vs number) before authoring `PriceCalc` TS interface. Likely a backend memo.

---

## 2. D33 execution — Product/Catalog model promotion to `@mesell/core`

D33 (founder-flagged at SP05, APPROVED-as-recommended, deferred to "Wave-6 backend-contract") fires HERE. SP05 recorded **ZERO promotions** because no page imported a cross-remote canonical entity — the real API shapes had not arrived. Now they have.

### 2.1 Promotion criterion (unchanged from SP05 D32/D33)

A type is promoted to `@mesell/core/models` ONLY if it is consumed by **2+ remotes**. A type used by one remote stays remote-private (D11/D17/D23). Promotion is surgical, transcribed from the backend Pydantic schema.

### 2.2 Cross-remote consumption analysis (from §1.3)

| Backend schema | Remotes that consume it | Promote? | Target |
|---|---|---|---|
| `ProductResponse` (catalog) | mfe-catalog (create/patch/preview), mfe-dashboard (list rows), mfe-export (initiate), mfe-pricing (price-calc context) | **YES — 4 remotes** | `@mesell/core/models/product.model.ts` |
| `MeResponse` → `AuthUser` enrichment | mfe-auth (verify→me), mfe-onboarding (profile), shell (bootstrap), mfe-dashboard (greeting) | **YES — already partly in core** (`AuthUser`); ADD `plan:'free'`, `phone`, `created_at` | extend `@mesell/core/services/auth.service.ts AuthUser` |
| `SellerProfileResponse` (customer) | mfe-onboarding only | NO — remote-private | `mfe-onboarding/.../seller-profile.model.ts` |
| `SchemaResponse` / field-group | mfe-catalog only | NO — remote-private | `mfe-catalog/.../catalog-form.model.ts` |
| `SuggestResponse` / `CategorySuggestion` | mfe-catalog only (smart-picker) | NO — already remote-private (#101) | stays |
| `PriceCalcResponse` | mfe-pricing only | NO — remote-private | `mfe-pricing/.../pricing.model.ts` |
| `ExportResponse` | mfe-export only | NO — remote-private | stays remote-private |
| `ImagesListResponse` | mfe-catalog only | NO — remote-private | stays |
| `DashboardResponse` | mfe-dashboard only | NO — remote-private | stays |

### 2.3 D33 PROMOTION LIST (the deliverable)

1. **`Product`** → `@mesell/core/models/product.model.ts`. Promoted from `catalog/schemas.py::ProductResponse`. Fields: `id, catalog_id, category_id, name (nullable), status ('draft'|'ready'), fields (Record<string,unknown>), ai_suggestions (nullable), created_at, updated_at`. Consumed by mfe-catalog + mfe-dashboard + mfe-export + mfe-pricing.
2. **`AuthUser` extension** → enrich the EXISTING `@mesell/core` `AuthUser` interface with `plan: 'free'`, `phone: string`, `created_at: string` (from `MeResponse`). This is an ADDITIVE field change to a shared singleton-adjacent type — verify no remote breaks on the new required fields (make them optional if any remote constructs `AuthUser` inline). Consumed by shell bootstrap + mfe-auth + mfe-onboarding + mfe-dashboard.

**Everything else stays remote-private.** Promotion happens in the FIRST wave that needs the shared type (the foundation wave, §4) so downstream waves consume it — never re-derive.

### 2.4 D33 singleton discipline (carried from SP05 §6.G / D22)

`@mesell/core/models/*` rides the SAME `@mesell/core` shared+singleton federation chunk as `AuthService`. Adding model files to the core barrel must NOT drag a second `_mesell_core.js` chunk or break the singleton. Build assertion (per SP06 C2): `dist` defines each promoted interface's consumers without inlining — models are `export type` (erased at runtime, zero chunk cost), so this is low-risk, but the foundation-wave PR MUST re-run the §6.G singleton grep.

---

## 3. Auth wiring — the FE-D5 keystone

### 3.1 What's wired vs mock TODAY

| FE-D5 element | Designed (FRONTEND_ARCH §4 LOCKED) | Built on develop? |
|---|---|---|
| `provideHttpClient(withFetch())` | yes | **YES** (shell app.config + mfe-catalog main.ts, #101) |
| In-memory access JWT (signal) | yes | **YES** (`AuthService._token` signal) |
| `setSession` / `logout` / `getToken` | yes | **YES** (AuthService) |
| Manual `Authorization: Bearer` per request | interim (Wave 7 → interceptor) | **YES** (smart-picker authHeaders() helper) |
| `jwtInterceptor` (global Bearer attach) | yes | **NO** |
| `RefreshInterceptor` (401→refresh→retry) | yes | **NO** |
| `errorInterceptor` (error envelope → ErrorService) | yes | **NO** |
| `AuthService.bootstrap()` (on-reload `GET /me`) | yes | **NO** |
| `AuthService.scheduleRefresh()` (proactive refresh) | yes | **NO** |
| Real OTP login (`POST /otp/send` + `/verify`) | yes | **NO** (otp-verify uses `setSession('mock-token')`) |
| `withCredentials: true` on `/auth/*` (refresh cookie) | yes | **NO** |
| `ApiClient` typed wrapper / `ErrorService` / `NetworkService` | yes (§4 LOCKED) | **NO** |

### 3.2 Auth wiring plan (foundation wave — §4 Wave A)

The proven patterns come from #101 (manual Bearer, in-memory token, error matrix, `withFetch()`) and SP06 C4 (the `setSession` write path in otp-verify). Wave 6 builds the missing interceptor chain ONCE in the shared core layer so every remote inherits it.

1. **`jwtInterceptor`** (`libs/core/interceptors/jwt.interceptor.ts`, NEW): functional `HttpInterceptorFn`, reads `AuthService.getToken()`, attaches `Authorization: Bearer` when present, skips when absent. **Replaces** the per-service `authHeaders()` helpers (smart-picker's helper gets removed in the same wave — the #101 migration note explicitly anticipated this).
2. **`refreshInterceptor`** (`libs/core/interceptors/refresh.interceptor.ts`, NEW): on `401`, call `POST /auth/refresh` (with `withCredentials: true`), on success re-issue the failed request with the new token; on refresh-failure call `AuthService.logout()` + redirect `/login`. Single-flight: concurrent 401s share ONE in-flight refresh (BehaviorSubject gate) to avoid a refresh storm. This is the §4-LOCKED RefreshInterceptor.
3. **`errorInterceptor`** (`libs/core/interceptors/error.interceptor.ts`, NEW): normalises the backend error envelope `{detail}` → typed `ErrorService` surface; non-blocking (does not swallow). Lowest priority in the chain.
4. **`AuthService.bootstrap()`** (extend existing service): on app init (shell `main.ts` / APP_INITIALIZER), attempt `POST /auth/refresh` (cookie auto-sent); on success set the in-memory token + call `GET /auth/me` to hydrate `AuthUser`. This is the page-reload survival path (FE-D5: no token in storage → must re-derive from the HttpOnly cookie).
5. **Real OTP login** (mfe-auth wave): `AuthApiService` wrapping `POST /auth/otp/send` + `POST /auth/otp/verify`; on verify-success call the EXISTING `setSession(access_token, user)` (C4 path, now with a REAL token, not `'mock-token'`); the `Set-Cookie` refresh is handled by the browser (requires `withCredentials: true`). Logout calls `POST /auth/logout` + `AuthService.logout()`.
6. **Interceptor registration:** `provideHttpClient(withFetch(), withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor]))` in the shell `app.config.ts` AND in EVERY remote `main.ts` (each remote dev-serves standalone). Order matters: jwt → refresh → error.

### 3.3 Auth wiring gotchas (recorded for the specialist)

- **`withCredentials` is per-request, not global** — only `/auth/*` calls need the refresh cookie; attaching it everywhere is a CORS-credentials surface. Scope it in the AuthApiService and the refreshInterceptor only.
- **CORS + cookie:** backend must respond `Access-Control-Allow-Credentials: true` and set `Set-Cookie: …; Domain=.mesell.xyz; Path=/api/v1/auth` (NOTE: the cross-track memo says `Path=/auth`; the backend coordinator corrected this to `Path=/api/v1/auth` — verify the live header before wiring). This is a backend+infra dependency → cross-lead memo (§7).
- **Singleton:** interceptors live in `@mesell/core` so they ride the singleton chunk; the AuthService they inject MUST be the same singleton instance (proven C2/C4/C5 across SP03/SP06). Re-run the §6.G grep in the foundation-wave PR.
- **Dev environment:** the live 401→refresh→retry smoke is a CARRIED item from SP07 (needs a reachable dev env). Wave 6 unit/integration-tests the interceptor chain with `HttpTestingController`; the live federated smoke piggybacks on the SP07 cutover-week CSP smoke (R-SP7-1, joint backend+infra).

---

## 4. Wave grouping for parallel execution

### 4.1 Constraints

- **Proven velocity: 2 parallel lanes** (Wave 1 SP02‖SP03, etc.).
- **Shared surface = serialise.** The shared files now are: `@mesell/core` (models + interceptors + AuthService), the shell `app.config.ts`, and each remote `main.ts` (interceptor registration). Routes are NOT shared (frozen by cutover). The foundation wave touches all the shared surfaces → it runs ALONE first; downstream waves touch only their own remote.
- **Hybrid rule:** per wave → (1) coordinator SPEC, (2) sonnet specialists (service-builder → component-builder → ui-styler), (3) coordinator MERGE-GATE review.
- **Branch model (Model C, as proven SP01-07):** `feature/wave6-{slice}/frontend` → `feature/wave6-{slice}/integration` → develop (founder gate). Per-remote slices are disjoint file sets → low conflict.

### 4.2 RECOMMENDED wave composition + sequencing

**WAVE A — FOUNDATION (serial, alone). Slice `wave6-auth-core`.**
The shared-surface wave. Builds: D33 `Product` + `AuthUser` promotion (§2.3); the 3 interceptors + `ApiClient` + `ErrorService` + `NetworkService` (§3.2 items 1-4 + §4-LOCKED service layer); `AuthService.bootstrap()`/`scheduleRefresh()`; interceptor registration in shell + all 6 remote `main.ts`; **real OTP login** in mfe-auth (§3.2 item 5). Removes smart-picker's `authHeaders()` helper (migrates to global jwtInterceptor). **RULED 2026-06-11 (DECISION-2): the DISCREPANCY-1 re-point (`POST /catalogs`→`POST /products`, #17) lands HERE in Wave A** (moved from the original-DRAFT Wave C) — it rides the same smart-picker-service edit as the `authHeaders()`→`jwtInterceptor` migration. This wave UNBLOCKS every other wave. Specialists: service-builder (interceptors + ApiClient + auth wiring + smart-picker re-point) → component-builder (mfe-auth login/signup/otp-verify wiring) → ui-styler (auth error states). **Must merge to develop before Wave B/C dispatch.**

**WAVE B — lane 1: `wave6-dashboard` ‖ lane 2: `wave6-onboarding`** (parallel; both consume the now-wired auth + `Product` model).
- Lane 1 `wave6-dashboard` (mfe-dashboard): swap `DashboardApiService` mock → `GET /products` (#26) paginated + `DELETE /products/{id}` (#21). Consume promoted `Product`. Landing (`/`) is public — no auth call.
- Lane 2 `wave6-onboarding` (mfe-onboarding): `SellerProfileService` (NEW) → #7/#8/#9/#10/#11. Reactive Forms already exist; wire submit → PATCH; load profile on init.

**WAVE C — lane 1: `wave6-catalog-form` ‖ lane 2: `wave6-export`** (parallel; disjoint remotes).
- Lane 1 `wave6-catalog-form` (mfe-catalog): swap `CatalogFormApiService` mock → schema (#15, ETag), autosave (#18), draft-recovery (#22), field-enum (#16). **DISCREPANCY-1 is now reconciled in Wave A (RULED DECISION-2) — no longer this slice's job.** **Does NOT wire autofill (#19) — AI-lane boundary, §6.**
- Lane 2 `wave6-export` (mfe-export): extract `ExportApiService` from the inline `setInterval` mock → initiate (#27) + poll (#28). PRESERVE the D18 timer pattern (proven SP02) — do not RxJS-rewrite the poll loop, just point it at the real endpoint; clear on `ngOnDestroy`.

**WAVE D — lane 1: `wave6-images` ‖ lane 2: `wave6-pricing`** (parallel).
- Lane 1 `wave6-images` (mfe-catalog images page): `ImageApiService` → upload (#23, multipart, 202) + poll (#24). **Does NOT wire the precheck DISPLAY logic if AI-lane owns it — §6 boundary check FIRST.** Owns the upload + poll plumbing only; the precheck-result rendering is the AI-lane question.
- Lane 2 `wave6-pricing` (mfe-pricing): resolve DECISION-1 (client vs server calc). If server: `PricingApiService` → #25 (verify `Decimal` wire-type first).

> **mfe-catalog appears in Wave C AND Wave D** (catalog-form + images are both in that remote). These are DIFFERENT pages/files in the same remote → can run in adjacent waves but NOT the same parallel lane-pair (avoid two slices branching the same remote concurrently → integration-branch collision). Sequence: catalog-form (Wave C) lands, THEN images (Wave D) branches off the updated remote. This is the one ordering constraint inside a remote.

### 4.3 Sequencing summary

```
Wave A (alone, shared surface)  ──merge──▶  Wave B (dashboard ‖ onboarding)  ──▶  Wave C (catalog-form ‖ export)  ──▶  Wave D (images ‖ pricing)
```

4 waves, 7 slices, max 2 lanes at a time. Wave A is the long pole (auth core). mfe-catalog ordering: catalog-form (C) before images (D).

---

## 5. Validation strategy per wave

Every `feature/wave6-{slice}/frontend` → integration PR is gated against the frontend PR template + these wave-specific checks:

### 5.1 Standing gates (every slice)
- **Build < 90 s** (D12) — record shell + affected-remote build times.
- **Bundle delta noted** — the foundation wave will ADD the interceptor chunk to `@mesell/core` (one-time cost, like #101's +10.49 kB provideHttpClient infra chunk); downstream waves should be near-zero shell-initial delta (remote-local).
- **Full suite green, no drop** — baseline = **47 spec files on develop @ `5cd6e32`**. Any NET-NEW failure attributable to the slice blocks it. New wiring tests use `HttpTestingController` (mock the HTTP backend, assert request URL/method/headers/body + map response). Count must MONOTONICALLY rise (new service specs) or hold — never drop (the SP0 test-discovery glob gotcha recurs per remote; re-confirm `apps/<remote>/**` discovery).
- **Contract greps:** (a) `grep "of(.*).pipe(.*delay"` in the wired service = 0 (mock removed); (b) the wired URL string matches the §1.2 path EXACTLY (`grep "/api/v1/<path>"`); (c) boundary 0 (`grep "from 'primeng"` outside ui-kit); (d) `localStorage` 0 (FE-D5); (e) singleton §6.G grep on any slice touching `@mesell/core`.
- **TS strict + strictTemplates ON** — `tsc` app + spec EXIT 0.
- **a11y + screenshots** 360px + 1280px per the template (loading + error + data states).

### 5.2 CI integration-DB reality (reference, do NOT block on it)
Gate-4 (integration tests against real Postgres) is in flight in another lane (pass-3, `fix/ci-gate4-integration-pass3` worktree observed; pass-2 #107 merged `df93208`). When Gate-4 lands, the wired endpoints get **real-Postgres CI coverage** — the FE wiring tests stay mock-HTTP (frontend CI gates 1+3), but the backend contract they target is independently verified by Gate-4. **Wave 6 does NOT block on Gate-4.** Reference it: a slice's contract is "FE-verified against schema + backend-verified by Gate-4" = the two-sided proof. Note in each PR which endpoints have Gate-4 coverage.

### 5.3 The contract-drift stop condition
If a wired call returns a runtime 4xx/shape-mismatch that the schema did not predict (DISCREPANCY-1 class), STOP the slice, raise a backend cross-lead memo (§7), do NOT paper over it with a client-side shim. This is the "contract surprise" stop condition from the merge gate.

---

## 6. AI-lane coordination (boundary — avoid double-wiring)

**Finding (verified from `feature_board_ai.md` on develop):** the AI lane's three features — `smart-picker` (#54), `catalog-form` (#56 autofill), `image-precheck` (#58) — are **backend AI prompt/eval work** (prompt registry version bumps, golden-set evals, guardrail compliance, cost ≤₹0.05). They deliver the AI *behaviour behind* endpoints #19 (autofill) and #24 (image precheck result). They do NOT deliver frontend HTTP wiring. The AI PR template gates on eval evidence, not screenshots.

**Boundary ruling (lead, to be confirmed by founder if AI lane disputes):**
- **smart-picker (#12 suggest):** FE wiring DONE by #101 (frontend lane). AI lane owns the prompt behind it. No double-wire. ✓
- **catalog-form autofill (#19):** the AI lane owns the `autofill.v1` prompt + the backend `POST /products/{id}/autofill` behaviour. **Frontend Wave C does NOT wire the autofill button-to-endpoint call IF the AI lane has a frontend slice for it.** Check `feature_board_ai.md` for an `autofill` FE row before Wave C dispatch — as of develop tip there is NONE (AI rows are all backend). **Therefore Wave 6 Wave-C OWNS the autofill UI wiring** (button → `POST /autofill` → overlay the `AutofillResponse.suggestions` onto the form), consuming the AI-lane-delivered endpoint. Memo the AI lead to confirm they are NOT also wiring the overlay.
- **image-precheck (#24 poll result):** same shape. Wave 6 Wave-D owns the upload + poll plumbing. The **precheck-result rendering** (the scorecard showing watermark/quality booleans from `precheck_jsonb`) — confirm with AI lead whether that display is AI-lane or frontend. Default assumption: frontend renders it (it is UI), AI lane owns only the backend precheck pipeline. Memo to confirm before Wave D.

**Action:** before Wave C and Wave D dispatch, the lead re-reads `feature_board_ai.md` + opens a confirm-memo to `meesell-ai-coordinator`. The boundary is: **AI lane = prompt + endpoint behaviour + eval; Frontend Wave 6 = the HTTP call + the UI rendering of the response.** No frontend slice touches `ai_ops/` or prompt registry.

---

## 7. Founder rulings — RULED 2026-06-11 (night)

All four decisions were RULED by the founder on 2026-06-11 (night), **each as recommended**. The rulings are quoted verbatim below; they are now binding on Wave 6 execution. (Original analysis + recommendation preserved under each ruling for traceability.)

- **DECISION-1 — pricing client-calc vs server-calc. RULED: SERVER-calc.**
  > Pricing is SERVER-calc. Wire mfe-pricing to `POST /products/{id}/price-calc` (#25); the client-side P&L math is retired at Wave D.

  *Recommendation (accepted):* wire to the server endpoint (#25) — single source of truth, server owns commission/GST/shipping-slab tables (which drift), alerts are server-computed, and the client-calc would silently diverge when Meesho rates change. Risk: P95 latency of an extra round-trip on every input change (mitigate with debounce, same as smart-picker). **Wave D lane 2 retires the local P&L utils and wires #25; verify the `Decimal` wire-type first (R-W6-6).**

- **DECISION-2 — smart-picker create-path (DISCREPANCY-1). RULED: FE re-points to `POST /products`.**
  > DISCREPANCY-1 resolves FE-side: re-point the smart-picker create-path from `POST /catalogs` to `POST /products` (#17). Fix lands in Wave A.

  *Recommendation (accepted):* FE re-points to `POST /products` (backend = source of truth; cleaner than adding a backend alias). **Sequencing change from the original DRAFT:** the founder placed the re-point in **Wave A** (not Wave C) — it rides the foundation wave's smart-picker `authHeaders()`→`jwtInterceptor` migration since both touch the same smart-picker service. §4.2 Wave A scope is amended accordingly (see §4.2 note below).

- **DECISION-3 — `AuthUser` shape extension (D33). RULED: ADDITIVE-OPTIONAL.**
  > The `AuthUser` extension (`plan`/`phone`/`created_at`) is ADDITIVE-OPTIONAL — new fields are optional so no remote that constructs `AuthUser` inline breaks.

  *Recommendation (accepted):* make the new fields optional so no remote that constructs `AuthUser` inline breaks, then tighten later. **§2.3 promotion item 2 stands: enrich the existing `@mesell/core` `AuthUser` with `plan?: 'free'`, `phone?: string`, `created_at?: string` (all optional).**

- **DECISION-4 — wave count. RULED: layout CONFIRMED (4 waves / 2 lanes / Wave A serial).**
  > The wave layout is CONFIRMED: 4 waves, 7 slices, max 2 parallel lanes, Wave A runs alone (serial) before B/C/D.

  *Recommendation (accepted):* keep Wave A monolithic — the interceptors + bootstrap + login are interdependent (login can't be smoke-tested without the refresh path) and all touch the shared core surface, so splitting them just adds integration-branch churn. **§4.2/§4.3 sequencing stands as authored, with the DECISION-2 re-point now folded into Wave A's scope.**

---

## 8. STOP / risk register

| ID | Risk | Mitigation | Severity |
|---|---|---|---|
| R-W6-1 | **Mock-removal trap** — a page wired to a real endpoint hard-crashes (white screen) when the backend is unreachable, where the mock always succeeded. | **Graceful-degradation pattern (MANDATORY, from #101):** every wired service has a `catchError` error matrix (401→logout, 402/404/5xx→fallback shape or empty-state, 400→caller-validated). The component renders an explicit error/empty state (MeeEmptyState / retry affordance), NEVER an unhandled throw. NetworkService surfaces offline. NO page may remove its mock without a paired error-state UI. The merge gate REJECTS a wired service with no `catchError`. | P0 |
| R-W6-2 | Contract drift (DISCREPANCY-1 class) surfaces at runtime as 4xx. | §5.3 stop condition + §1.4 known-discrepancy list reconciled up-front; schema-first transcription; Gate-4 two-sided proof. | P0 |
| R-W6-3 | Auth singleton breaks when interceptors are added to `@mesell/core` (a second core chunk, AuthService duplicated). | §6.G singleton grep on the foundation-wave PR; interceptors are functional (no class), models are `export type` (erased). | P0 |
| R-W6-4 | Refresh storm — N concurrent 401s each fire `/auth/refresh`. | Single-flight refresh gate (one in-flight refresh, others queue) in refreshInterceptor (§3.2 item 2). | High |
| R-W6-5 | `withCredentials` over-applied → CORS-credentials leak / preflight failures. | Scope `withCredentials:true` to `/auth/*` only (AuthApiService + refreshInterceptor). | High |
| R-W6-6 | `Decimal` wire-type ambiguity (pricing) → TS `number` vs `string` mismatch → NaN in P&L display. | Verify serialised shape against the live endpoint before authoring the TS interface; backend memo if ambiguous. | Med |
| R-W6-7 | Cookie `Path` mismatch (`/auth` vs `/api/v1/auth`) → browser never attaches refresh cookie → silent-refresh always 401. | Verify the live `Set-Cookie` header (backend corrected to `Path=/api/v1/auth`); backend+infra memo. | High |
| R-W6-8 | Test-discovery silently drops new specs (SP0 cwd-glob gotcha) → false-green. | Re-confirm `apps/<remote>/**/*.spec.ts` discovery per slice; assert spec-file count rises. | Med |
| R-W6-9 | mfe-catalog double-branch collision (catalog-form ‖ images same remote). | Serialise within the remote: catalog-form (Wave C) before images (Wave D). §4.2 ordering constraint. | Med |
| R-W6-10 | AI-lane double-wires autofill/precheck-display. | §6 confirm-memo to ai-coordinator before Wave C/D; board re-read. | Med |
| R-W6-11 | No reachable dev env → live 401→refresh→retry smoke can't run. | Unit-test the chain with HttpTestingController; piggyback live smoke on SP07 cutover-week CSP smoke (R-SP7-1, carried). Don't block Wave 6 merges on it. | Med |

### STOP conditions (escalate to founder)
- Build > 90 s (D12).
- TS strict accidentally disabled.
- Contract drift not in §1.4 (new 4xx surprise).
- Any wired service shipped without a `catchError` error matrix (R-W6-1 = automatic reject).
- A `feature/wave6-{slice}/frontend` branch open > 5 calendar days unmerged (§1.2 repo-mgmt).
- Singleton §6.G grep shows a duplicated `@mesell/core` chunk.

---

## 9. Acceptance criteria (Wave 6 COMPLETE)

1. All 8 unwired pages (§1.3) wired to their real endpoints; ZERO `of(SEED).pipe(delay)` or inline `setTimeout`/`setInterval` mocks remain in any `*-api.service.ts` or page component (grep-verified).
2. FE-D5 auth loop fully live: real OTP login, jwt+refresh+error interceptors registered in shell + all 6 remote `main.ts`, `bootstrap()` survives reload, `setSession` carries a REAL token (not `'mock-token'`).
3. D33 `Product` + `AuthUser` promoted to `@mesell/core`; singleton intact.
4. DISCREPANCY-1 reconciled (smart-picker → `POST /products`).
5. Every wired service has a `catchError` error matrix + paired error/empty-state UI (R-W6-1).
6. Build ≤90 s; full suite green, no drop (baseline 47 spec files, monotonic rise); boundary 0; localStorage 0; contract greps pass.
7. Founder-gate PRs (integration→develop) opened per slice; lead does NOT approve (D1).
8. Carried to cutover week (NOT Wave-6 blockers): live federated 401→refresh→retry smoke (joins SP07 R-SP7-1); Gate-4 endpoint coverage confirmation; FEATURE_*_ENABLED ConfigMaps + GEMINI_API_KEY live evals (AI-lane/infra).

---

## 10. Revision history

| Date | Rev | Change |
|---|---|---|
| 2026-06-11 | DRAFT | Initial authoring. Session `mesell-wave6-planning-session-1`. Base develop `5cd6e32`. Awaiting founder approval. |
| 2026-06-11 | ACTIVE | Founder RULED all 4 §7 decisions (night), each as recommended: D1 pricing=SERVER-calc (#25, client P&L retired at Wave D); D2 DISCREPANCY-1=FE re-point `POST /catalogs`→`POST /products`, moved to Wave A; D3 `AuthUser` extension=ADDITIVE-OPTIONAL; D4 wave layout CONFIRMED (4 waves/2 lanes/Wave A serial). §7 flipped DRAFT→RULED (verbatim rulings); header DRAFT→ACTIVE; §4.2 Wave A scope amended for the D2 re-point; §4.2 Wave C de-scoped DISCREPANCY-1. §1.2 row 26 corrected: response is `PaginatedProductsResponse{items[],total,page,limit}` (`catalog/schemas.py` L230-238) — `items` not `products`. Chore session (frontend lead, fast-mode docs class). |
| 2026-06-12 | ACTIVE | **§1.2 row 26 RE-corrected (2nd time) to the AUTHORITATIVE MOUNTED contract — reverses the 2026-06-11 PR #111 over-correction.** The mounted response is `DashboardResponse{products: ProductListItem[], total, page, limit, onboarding_completeness}` (`dashboard/schemas.py` L81-90; `ProductListItem{product_id,name?,category_id,status:'draft'\|'ready',created_at,updated_at}` L53-58; router L80-82; `main.py` L137). `PaginatedProductsResponse{items[]}` (`catalog/schemas.py`) is DEAD CODE — ZERO mounted routes reference it (proven from source by the Wave B spec session). Row 26 now cites source lines, carries a double-correction history note (so it is not flipped a third time), and cross-references `spec_w6b_dashboard.md` as the authoritative wiring spec. Also added a §1.2 ⛔ note flagging the onboarding domain-mismatch P0 (customer module = Legal-Metrology fields; UI form fields don't exist on the wire; founder Option-A/B/C ruling pending → `spec_w6b_onboarding.md` §2.6). Chore session `mesell-w6-row26-fix-session-1` (frontend lead, fast-mode docs class). |
