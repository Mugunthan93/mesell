# SUB-PLAN H — `catalog` Service Extraction (THE SPINE — LAST + RISKIEST)

**STATUS: AUTHORED — EXECUTION GATED ON MS-5 WAVE OPEN (ALONE, after MS-4).**
Authored under session `mesell-ms-catalog-session-1` (PHASE 1, hybrid step 1,
docs-only — 2026-06-12). This is the **eighth and FINAL** extraction sub-plan of
the Microservices Migration MASTER_PLAN (LOCKED 2026-06-10, v1.3). It implements
MASTER_PLAN §4 row **H** (`catalog`, complexity **XL**) under the **MS-PAR-1
parallel wave program** (dispatch doc
`docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md`).

> **Execution gate — MS-5 WAVE, ALONE.** Per MS-PAR-1 (founder ruling "prepare a
> parallel plan for micro service", 2026-06-12), the LOCKED serial A→H order is
> upgraded to **pilot alone → parallel pairs → riskiest last**. `catalog`
> executes in **MS-5**, with **NO parallel partner** (the MS-5 wave is catalog
> only), and unblocks only when **MS-4 (`category` + `iam`) are BOTH
> founder-gate-merged**. By the time catalog extracts, **all 4 of its downstream
> callers (image, pricing, dashboard, export) are already running in HTTP-shim
> mode against the in-process monolithic catalog** — so catalog's cutover flips
> 4 networking surfaces at once (MASTER_PLAN §3.B order position 8, "the spine;
> 4 downstream consumers means 4 networking surfaces flip simultaneously").
> **Sub-plan AUTHORING (this document) is unblocked NOW; EXECUTION is
> MS-5-gated.**
>
> **MASTER_PLAN naming reconciliation (SOURCE WINS):** MASTER_PLAN §4 row H
> (line 308) names this file `SUB_PLAN_08_catalog_extraction.md` and lists the
> OLD serial dependency chain "A-G complete". The **MS-PAR-1 dispatch doc
> supersedes both**: the canonical filename for the parallel program is
> `SUB_PLAN_0H_catalog_extraction.md` (this file), and the dependency is "MS-4
> complete (category + iam), runs ALONE" — NOT the full A–G serial chain (though
> in practice MS-5-after-MS-4 means A–G ARE all merged, so the two formulations
> converge here). This is a plan-prose-vs-dispatch reconciliation recorded per
> the Wave-6 SOURCE-WINS discipline; the §4 row H annotation should be updated to
> point at this file when the founder next touches the master plan.
>
> **Execution posture — PLANNING ONLY.** This document is the executable
> specification a coding session (dispatched once MS-5 opens) will follow. NO
> extraction code is written by the authoring session. The two ai_ops /
> middleware decisions are already **LOCKED** via founder rulings D6 / D7
> (2026-06-10) — see §H1 / §H2.

> Authoritative inputs read for this sub-plan (file:line citations from SOURCE
> per Wave-6 law — never plan prose for enums/contracts):
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (LOCKED v1.3 — §1.C call
>   matrix, §2.E shared infra/Valkey namespacing line 209, §3.A/§3.A.1, §3.B
>   order line 273-275 (why catalog last), §3.C rollback lines 281-291, §4 row H
>   line 308, §5.A local-JWT line 328 + internal-endpoint-auth line 338, §5.B
>   shared audit, §5.G program-completion compliance audit line 397, §6 Risk #1
>   (autosave P95) line 405, D6/A1 line 221, D7/A2 line 330)
> - `docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md` (THE
>   FRESHEST canonical template — PR #183; section structure + ai_ops-vendoring +
>   budget-brake carve-out pattern mirrored here)
> - `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (the
>   original shape template; A1/A2 supersession banner)
> - `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md`
>   (MS-PAR-1 wave structure, common rules 1-9, the Session MS-H prompt block)
> - **MS-A FROZEN shim contract** (`spec_msA_backend.md` §5, master-tree
>   untracked) — the 6-endpoint `/internal/*` contract the export pilot froze.
>   catalog implements the **two** catalog-owned frozen shims
>   (`assert_product_ownership` + `get_product_for_export`), cited §H4.
> - As-built source (file:line): `backend/app/modules/catalog/` (7 files —
>   `service.py` 1070, `repository.py` 506, `router.py` 383, `schemas.py` 297,
>   `domain.py` 244, `exceptions.py` 193, `__init__.py` 30),
>   `backend/app/ai_ops/{client,budget_cap,cost_tracker}.py`,
>   `backend/app/main.py`, and the 4 inbound callers
>   `backend/app/modules/{image,pricing,dashboard,export}/service.py`

---

## As-built inventory (file:line — SOURCE, not plan prose)

### Mounted routes (verified in `backend/app/main.py`, NOT schema existence — the row-26 lesson)

`backend/app/main.py:40` imports `catalog_router`; `:126-127`
mounts it **FEATURE-FLAG-GUARDED**:

```
if settings.FEATURE_CATALOG_FORM_ENABLED:      # main.py:126
    app.include_router(catalog_router)         # main.py:127
```

> **MOUNT-CONDITIONALITY — load-bearing (row-26 discipline).** catalog is the
> ONLY domain router mounted behind a runtime flag (`FEATURE_CATALOG_FORM_ENABLED`).
> When the flag is False the entire `/api/v1/products/*` catalog surface falls
> through to FastAPI's default 404 (`main.py:122-125` comment). The extracted
> svc-catalog `main.py` MUST preserve this guard OR the Traefik route must be
> gated equivalently — the route count is **conditional**, not unconditional. The
> merge-gate counts MOUNTED `APIRoute` objects with the flag ON, not schema
> classes.

The router (`backend/app/modules/catalog/router.py:98`) carries `prefix="/api/v1"`,
`tags=["catalog"]`. **6 mounted public routes** (matches MASTER_PLAN §4 row H
"6 endpoints"; BACKEND_ARCHITECTURE.md §10.B LOCKED 2026-06-05):

| # | Method + path | Handler (router.py) | Service call | Decorators / guards |
|---|---|---|---|---|
| 1 | `POST /api/v1/products` | `create_product` `:141` | `catalog_service.create_product(user_id, plan, payload, db)` `:154` | `@rate_limit(scope="create_product", limit=20, window=3600)` `:139`; `@audit_event("catalog.product.created")` `:140`; **plan_guard `product_count` 100-cap enforced INSIDE service** `:148` |
| 2 | `PATCH /api/v1/products/{id}` | `patch_product` `:170` | `catalog_service.patch_product(user_id, id, payload, is_autosave, db)` `:186` | `@rate_limit(scope="product_patch", limit=600, window=3600)` `:168` (autosave-friendly per-IP); `@audit_event("catalog.product.updated")` `:169`; `X-Autosave` header `:175` → upserts `product_drafts` |
| 3 | `POST /api/v1/products/{id}/autofill` | `autofill_product` `:202` | `catalog_service.autofill_product(user_id, plan, id, payload, request_id, db)` `:243` | `@rate_limit(scope="ai_autofill", limit=50, window=3600)` `:200`; `@audit_event("catalog.autofill.invoked")` `:201`; **`FEATURE_AI_AUTOFILL_ENABLED` 404 guard** `:228`; **the ONLY AI-consuming route in catalog** |
| 4 | `GET /api/v1/products/{id}/preview` | `get_product_preview` `:275` | `catalog_service.get_preview(user_id, id, db)` `:299` | `@rate_limit(scope="product_preview", limit=600, window=3600)` `:274`; NO audit (read); **`FEATURE_LIVE_PREVIEW_ENABLED` 404 guard** (default-False — the only V1 flag defaulting False) `:293`; raises `MeesellError(code="feature.live_preview.disabled")` |
| 5 | `DELETE /api/v1/products/{id}` | `delete_product` `:329` | `catalog_service.soft_delete(user_id, id, db)` `:338` | `@rate_limit(scope="product_delete", limit=60, window=3600)` `:327`; `@audit_event("catalog.product.deleted")` `:328`; 204 |
| 6 | `GET /api/v1/products/{id}/draft` | `get_product_draft` `:352` | `catalog_service.get_draft(user_id, id, db)` `:366` | `@rate_limit(scope="product_draft_read", limit=600, window=3600)` `:351`; NO audit (read); returns 204 when no snapshot |

> **§3.4 endpoint-inventory disambiguation (SOURCE WINS).** The authoritative
> endpoint inventory (`reference_authoritative_endpoint_inventory.md` §3.4) lists
> "Catalog & product (11)" — but that grouping **mingles routes owned by OTHER
> modules** that share the `/products/*` path prefix: `POST /products/{id}/images`
> + `GET /products/{id}/images` (image-svc), `GET /products/{id}/price-calc`
> (pricing-svc), `POST /products/{id}/export-xlsx` + `GET /exports/{id}`
> (export-svc), `GET /products` (dashboard-svc). **catalog-svc owns exactly the 6
> routes above** (its own `catalog_router`). The shared-path-key collision
> (`POST /products` catalog vs `GET /products` dashboard — `main.py:138-140`) is
> two distinct `APIRoute` objects on one path key — at catalog's cutover, Traefik
> must route by METHOD on `/api/v1/products` (POST→catalog-svc, GET→dashboard-svc)
> OR by sub-path. This is an MS-5-specific routing nuance flagged in §H-infra. |

All 6 require `Depends(get_current_user)` (`router.py:14-16` invariant) — routes
never decode JWT. 4 write routes carry `@audit_event`; 2 read routes (preview,
draft) carry none (read-flood rule, `router.py:33-37`).

### Public service surface (`backend/app/modules/catalog/service.py`)

**Public methods** (`service.py:1058-1068` `__all__` — the 6 route-backing
methods + 3 cross-module-consumed methods):

| Method | Signature (service.py) | Consumer |
|---|---|---|
| `create_product` | `(user_id, plan, request, db) -> Product` `:375` | route 1 |
| `patch_product` | `(user_id, product_id, request, *, is_autosave, db) -> Product` `:476` | route 2 |
| `autofill_product` | `(user_id, plan, product_id, request, *, request_id, db) -> AutofillResponse` `:585` | route 3 **+ the AI seam (§H3)** |
| `get_preview` | `(user_id, product_id, db) -> ProductPreviewInternal` `:782` | route 4 |
| `soft_delete` | `(user_id, product_id, db) -> None` `:877` | route 5 |
| `get_draft` | `(user_id, product_id, db) -> ProductDraft \| None` `:898` | route 6 |
| `assert_product_ownership` | `(product_id, user_id, db) -> None` `:921` | **cross-module: image, pricing, export (frozen shim #1)** |
| `get_product_for_export` | `(product_id, user_id, db) -> ExportSnapshotInternal` `:945` | **cross-module: export (frozen shim #2)** |
| `list_products` | `(user_id, pagination, db) -> PaginatedProductsInternal` `:999` | **cross-module: dashboard** |
| `get_validation_summary` | `(...) -> ...` `:1020` | **DOCUMENTED dashboard-consumed (`__init__.py:11`, `:23`) — but NO live caller at develop tip (see contradiction below)** |

### ⚠️ CONTRADICTION — `get_validation_summary` documented-but-not-called (TRUE branch tip, reported not papered over)

The catalog `__init__.py:11-12` docstring + `service.py:23` + `schemas.py:245` +
`domain.py:135` all assert `get_validation_summary` is "used by dashboard.service
per §2.D". **As-built grep `get_validation_summary` across `backend/app/`
(excluding catalog's own subtree) returns ZERO callers** — `dashboard/service.py`
calls ONLY `list_products` (`dashboard/service.py:78`). `get_validation_summary`
is a **latent/defensive public surface, not a LIVE cross-module edge** at the
develop tip. **TRUE branch tip: catalog has 3 LIVE inbound methods
(`assert_product_ownership`, `get_product_for_export`, `list_products`) + 1 latent
documented method (`get_validation_summary`).** Per the SUB_PLAN_0F `latent shim`
precedent (its `list_super_categories` case), this sub-plan exposes a **defensive
`/internal/*` shim** for `get_validation_summary` (§H4) and raises it as an Open
Question — if dashboard never calls it over HTTP, the unused shim is harmless; if
a future dashboard slice needs it, the shim already exists. The docstring should
be corrected (founder-touch) to mark it latent.

### Cross-module edges — catalog as CALLEE (verified by grep across all 4 callers)

`catalog` is called by **4 modules** (grep `catalog_service.` in each caller's
`service.py`) — the MOST-called module in the architecture (`__init__.py:8-13`):

| Caller | Import site | Method(s) consumed (call site) |
|---|---|---|
| `image` | `image/service.py:53` | `assert_product_ownership` (`:162`, `:248`) |
| `pricing` | `pricing/service.py:65` | `assert_product_ownership` (`:134`, `:241`) |
| `export` | `export/service.py:57` | `assert_product_ownership` (`:174`) + `get_product_for_export` (`:177`, `:314`) — **the 2 MS-A frozen shims** |
| `dashboard` | `dashboard/service.py:36` | `list_products` (`:78`) |

**Inbound networking surfaces that flip at catalog's cutover: 4** (image,
pricing, export, dashboard). All 4 are ALREADY-EXTRACTED pods by MS-5 (image=MS-2,
pricing=MS-3, dashboard=MS-2, export=MS-1) — so each already runs a `catalog_client`
HTTP shim pointing at the monolith ClusterIP. At catalog's cutover the Traefik
route for `/api/v1/products/*` (POST/PATCH/DELETE/autofill/preview/draft) AND
`/internal/products/*` flips from monolith-svc to svc-catalog — **all 4 callers'
call sites stay byte-for-byte identical** (§16.G; the shim re-exports the same
symbol). This is the §3.B "4 networking surfaces flip simultaneously" risk
concentration — de-risked by MS-5 running ALONE so the operational pain lands once.

### Cross-module edges — catalog as CALLER (verified by grep — 2 LIVE + 1 latent)

catalog imports **2 domain modules** (`service.py:98-99`,
re-affirmed `service.py:27-28` docstring "imports `from app.modules.category
import service` and `from app.modules.customer import service` ONLY"):

| Callee | Import site | Method(s) called (call site) | Becomes |
|---|---|---|---|
| `category` | `service.py:98` | `assert_category_exists` (`:401`); `fetch_schema` (`:463`, `:506`, `:620`, `:800`, `:962`, `:1034`); `get_field_enum` (`:309`) | **3 outbound HTTP shims → category-svc `/internal/*`** |
| `customer` | `service.py:99` | `assert_eligible_for_super_id` (`:406`); `get_compliance_block` (`:839`) | **2 outbound HTTP shims → customer-svc `/internal/*`** |

> **LATENT image edge (defensive `getattr`, NEVER fires in V1 — TRUE branch tip).**
> `service.py:828` + `:980` do `from app.modules import image as _image_module`
> then `getattr(_image_module, "service", None)` and check
> `hasattr(image_service, "get_image_refs")`. **`get_image_refs` does NOT exist on
> `image/service.py`** (its public methods are `upload_image`, `list_images`,
> `get_image_urls`, `get_image_bytes`, `write_precheck_result`, `summary` —
> `image/service.py:426` `__all__`). So the `hasattr` check resolves False in V1
> and the image branch is **dead code** (defensive scaffolding for a §11 surface
> that was never built). **catalog authors NO outbound image shim** — the
> `image_refs` field in `ExportSnapshotInternal` stays the empty tuple
> (`service.py:984` `image_refs: tuple[str, ...] = ()`). The dead `getattr` block
> travels verbatim (§16.G) but never executes. Record in the runbook as a known
> dead branch; do NOT "fix" it during extraction (strangler discipline).

**Consequence:** catalog authors **5 outbound HTTP-shim clients** (category×3
methods + customer×2 methods, against 2 callee services) AND implements **3 (+1
defensive) inbound `/internal/*` shims** for its 4 callers. It is the ONLY service
in the program with BOTH a heavy inbound surface AND a multi-callee outbound
surface — the spine, confirmed. The outbound callees (category, customer) are
already extracted pods by MS-5 (category=MS-4, customer=MS-3), so catalog's
`category_client` + `customer_client` shims point at the **real extracted services'
ClusterIPs** at MS-5 — NOT the monolith (unlike the MS-A pilot where callees were
still in-process). This is the FIRST extraction whose outbound shims target real
sibling pods from day one.

> **The `get_product_for_export` nested-call subtlety (load-bearing for shim
> design).** catalog's `get_product_for_export` (`service.py:945`) is itself a
> COMPOSITE: it calls `assert_product_ownership` (in-process, `:961`),
> `category_service.fetch_schema` (`:962` — an OUTBOUND shim), and the dead image
> `getattr` block (`:980`). So when export-svc calls catalog-svc's
> `/internal/products/{id}/export-snapshot`, catalog-svc internally makes an
> OUTBOUND call to category-svc's `/internal/categories/{id}/schema`. **This is a
> 2-hop internal chain (export-svc → catalog-svc → category-svc).** The shim
> timeouts (§5.E: 5s read / 2s connect) must account for the nested hop — document
> the chain depth in the runbook; the catalog→category hop is cached
> (category full-tree + top-100 schema pre-warm, ≥99% hit) so the nested cost is
> ~10ms cached, not a cold DB read.

### DB tables owned (3 tenant-scoped tables)

`repository.py:59-61` ORM imports. `catalog` owns **3 tables** (MASTER_PLAN §4
row H "3 tables: catalogs/products/product_drafts"):

| Table | ORM | Where it lives today | Tenant-scoped? |
|---|---|---|---|
| `catalogs` | `app.shared.models.catalog.Catalog` (`repository.py:59`) | 13-table baseline `935e55b4852c` | YES — `scope_to_user` (`repository.py:143`) |
| `products` | `app.shared.models.product.Product` (`repository.py:60`) | baseline | YES — `scope_to_user` (`repository.py:87`, `:108`, `:126`) |
| `product_drafts` | `app.shared.models.product_draft.ProductDraft` (`repository.py:61`) | baseline (autosave snapshots) | YES |

> **Tenancy contrast with category (SOURCE).** Unlike category (GLOBAL, NO
> `scope_to_user`, §9.D structural exception), catalog is FULLY tenant-scoped —
> `scope_to_user(select(ProductORM), user_id)` is on every product read
> (`repository.py:87`, `:108`, `:126`). The extracted repository MUST keep
> `scope_to_user` everywhere (the §10 leak-protection rule — `find_by_id` collapses
> not-found / wrong-owner / soft-deleted to `None` uniformly, `service.py:938-940`).
> This is a merge-gate acceptance item.

**What migrates:** all 3 tables move to the `catalog` Postgres schema via
`ALTER TABLE ... SET SCHEMA catalog`. The `products.user_id` FK to `users` (an iam
table) becomes a **cross-schema reference** — Risk #5 (cross-schema FK integrity)
applies: the database-builder runs the integrity pre-scan (every `products.user_id`
resolves to a real `users` row) before any FK adjustment. Per MS-A precedent,
catalog drops NO FK itself, but the scan is the documented §6-Risk #5 pattern.

### Module-private internals (stay inside the service, no contract surface)

- `repository.py` — module-PRIVATE data access (`find_by_id`, `find_by_id_any_state`,
  `count_active`, catalog upsert, draft upsert, `list_paginated`). `scope_to_user`
  on every product/catalog read. Bound to schema `catalog` post-extraction.
- `domain.py` — frozen dataclasses (`Product` `:35`, `Catalog` `:58`,
  `ProductDraft` `:68`, `AutofillSuggestionInternal` `:93`, `AutofillResponse`
  `:114`, `ValidationSummaryInternal` `:134`, `ExportSnapshotInternal` `:152`,
  `PaginatedProductsInternal` `:170`, `PreviewField` `:180`,
  `ProductPreviewInternal` `:199`, `Pagination` `:219`). `ExportSnapshotInternal`,
  `ValidationSummaryInternal`, `PaginatedProductsInternal` are the cross-module
  exchange currency (§16.D) — consumed by export/dashboard verbatim.
- `exceptions.py` — `CatalogError` base + subclasses (`ProductNotFoundError`,
  `DraftNotFoundError`, `CatalogNotFoundError`, `ProfileIncompleteError`,
  `AutofillFailedError`, plan/cap errors).
- `schemas.py` — PRIVATE Pydantic wire-shapes (`CreateProductRequest`,
  `PatchProductRequest`, `AutofillRequest`/`AutofillResponse`/`AutofillSuggestion`,
  `ProductResponse`, `ProductPreviewResponse`/`ProductPreviewField`,
  `ProductDraftResponse`). PRIVATE wire-shape per §16.C.

### Celery / worker surface — NONE

Grep `shared_task | @task | Celery` in `backend/app/modules/catalog/` returns only
a doc COMMENT (`router.py:54` mentions the audit flush layer). **catalog has NO
Celery worker** (unlike export/image). No worker deployment, no broker/result-DB
wiring. The autosave `product_drafts` upsert is synchronous inside `patch_product`.
The audit-coalescing is handled by the shared `audit_mw` + the monolith's audit
flush (NOT a catalog-owned task). svc-catalog ships NO `celery_app.py`, NO
`tasks.py`.

---

## Decisions

> **H1 / H2 carry the LOCKED D6 / D7 rulings verbatim** (same as SUB_PLAN_0F §F1/F2).

### H1 — `ai_ops/` placement — VENDORED per AI-consuming service (LOCKED, founder ruling D6 / A1, 2026-06-10)

**Relevance to THIS sub-plan: DIRECT and HIGH.** `catalog` is the LAST of the 3
AI-consuming services (category/catalog/image) to extract. It runs the
**`autofill.v1`** workload (`service.py:638` `call_gemini(ctx, "autofill.v1", ...)`)
— a DIFFERENT prompt from category's `smart_picker.v1`. catalog-svc vendors its OWN
trimmed copy of ai_ops carrying the `autofill_v1` prompt.

**LOCKED ruling (MASTER_PLAN line 221, D6/A1):** `ai_ops/` is a **vendored
Python-package copy per AI-consuming service at V1.5**; promoted to a dedicated
`ai-ops-svc` at V2. **There is NO ai-ops-svc until V2.** catalog-svc carries its
own vendored copy. **The ₹500 daily BUDGET BRAKE stays SHARED via Valkey DB 0 / the
audit-DB counter across ALL services regardless of code placement** — so the spend
cap remains GLOBAL across category + catalog + image. The full vendoring plan +
shared-budget-brake wiring is §H3.

### H2 — Shared `core/middleware/` placement — VENDORED, LOCAL JWT (LOCKED, founder ruling D7 / A2, 2026-06-10)

**Relevance: DIRECT.** catalog-svc needs `auth_mw` (`get_current_user` on all 6
routes), `rate_limit_mw` (5 distinct scopes: `create_product` 20/h, `product_patch`
600/h, `ai_autofill` 50/h, `product_preview` 600/h, `product_delete` 60/h,
`product_draft_read` 600/h), `tenancy_mw`, `request_id_mw`, `audit_mw` (ACTIVE for
catalog — 4 write routes emit `catalog.product.created/updated/deleted` +
`catalog.autofill.invoked`), and `plan_guard_mw`. **plan_guard IS active for
catalog** — `product_count` (100 active cap) enforced inside `create_product`
(`service.py` step 1) and `ai_autofill_hourly` (50/h/user) inside `autofill_product`
(`service.py:613`).

**LOCKED ruling (MASTER_PLAN line 330, D7/A2):** the **6-middleware chain (CORS →
request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw) is
VENDORED per service**; **JWT VERIFICATION runs LOCALLY in every service** via the
vendored `core/auth.py` + shared `JWT_SECRET` from Secret Manager. iam-svc (MS-4,
already extracted by MS-5) owns OTP/login/refresh ONLY — NOT consulted per-request.
**Gateway-JWT validation is REJECTED.** catalog-svc validates its own JWTs.

> **Internal-endpoint auth (MASTER_PLAN §5.A line 338).** When catalog-svc's
> outbound `customer_client` calls customer-svc's
> `/internal/seller-profile/{user_id}/eligibility/{super_id}`, the caller forwards
> the user's JWT; the callee validates it the same way as a public JWT. **No
> separate service-to-service token in V1.5.** Symmetrically, when export-svc calls
> catalog-svc's `/internal/products/{id}/export-snapshot`, export-svc forwards the
> user JWT and catalog-svc validates locally. K3s NetworkPolicy blocks
> `/internal/*` from outside the cluster.

### H3 — `ai_ops/` vendoring plan + SHARED budget-brake wiring (the load-bearing decision)

Operationalizes H1 against the autofill workload — mirrors SUB_PLAN_0F §F3 but for
the `autofill.v1` prompt.

#### H3.a — What catalog-svc vendors

catalog-svc ships a **trimmed vendored copy of `ai_ops/`** carrying ONLY the
autofill code path:

| ai_ops file | Vendored? | Why |
|---|---|---|
| `client.py` | YES | sole AI import surface; `service.py:76` `from app.ai_ops import client as ai_client`; `:638 call_gemini(ctx, "autofill.v1", ...)` |
| `budget_cap.py` | YES | `service.py:77` imports `BudgetExceededError`; the brake reserve/release Lua runs in-process |
| `cost_tracker.py` | YES | `client.py` imports it; writes committed cost + audit_events |
| `guardrail.py` | YES | autofill's §6A.E Layer-2 enum guardrail (`allowed_enums` resolved at `service.py:623`, passed to `call_gemini` at `:646`) — the autofill hallucination guard |
| `prompt_registry.py` | YES | `resolve()` + `render()` for `autofill.v1` |
| `prompts/autofill_v1.py` | YES (this ONE prompt module) | the only workload catalog runs; `prompts/smart_picker_v1.py` + `prompts/watermark_v1.py` are NOT vendored (category/image carry those) |
| `eval.py` | OPTIONAL (vendor for CI golden-set parity) | the autofill golden eval (`backend/tests/eval/autofill/run_autofill_eval.py`) — vendor so catalog-svc CI can run its own eval gate |
| `metrics.py` | YES | the 7 Prometheus singletons with the per-service `service="catalog"` label (§5.F) |

#### H3.b — The SHARED budget brake — same Valkey keys + DB table as category (cited file:line)

The budget brake state is **NOT vendored** — it is SHARED infrastructure all
AI-consuming services point at. **IDENTICAL keyspace to SUB_PLAN_0F §F3.b** (the
brake is global across category + catalog + image):

**Valkey DB 0:**

| Key family | Constant (file:line) | Purpose |
|---|---|---|
| `ai:cost:daily:{YYYY-MM-DD}` | `cost_tracker.py:92 _DAILY_KEY_FMT` | **committed** daily spend (the ₹500 cap numerator) |
| `ai:cost:pending:{YYYY-MM-DD}` | `budget_cap.py:124 _PENDING_KEY_FMT` | reserved-but-not-committed headroom |
| `ai:budget:reservation:{reservation_id}` | `budget_cap.py:125 _RESERVATION_KEY_FMT` | per-call 5-min-TTL reservation (`budget_cap.py:130`) |
| `ai:cost:user:{user_id}:hourly:{YYYY-MM-DD-HH}` | `cost_tracker.py:93 _USER_HOURLY_KEY_FMT` | per-user hourly accumulator |

The cap check is **atomic** via two Lua scripts (`budget_cap.py:136 _RESERVE_LUA`,
`:153 _RELEASE_LUA`) in Valkey's single-threaded loop — concurrent
`check_and_reserve` from catalog-svc AND category-svc AND the monolith serialise
here against the SAME `ai:cost:daily:{date}` counter. Cap value
`settings.AI_DAILY_BUDGET_INR` (=500); day boundary Asia/Kolkata.

**Postgres `audit_events`** — the committed-cost ledger (`cost_tracker.py:55`
imports `AuditEvent`; `:250` direct ORM write, drops-on-failure with WARNING).
GLOBAL shared state.

#### H3.c — How the vendored copy points at SHARED state (the carve-out — same as F3.c)

1. **Valkey:** catalog-svc's vendored `shared/valkey.py` `get_valkey_otp()` points
   at the **SAME Valkey instance, SAME DB 0** as every AI service.
   **CRITICAL CARVE-OUT (identical to SUB_PLAN_0F R1):** the budget keys
   (`ai:cost:*`, `ai:budget:*`) MUST **NOT** be prefixed with `catalog:` — if they
   were, catalog would have its OWN ₹500 counter and the GLOBAL cap would split
   into N independent caps. **The `ai:*` budget keyspace is the documented
   EXCEPTION to the §2.E `{service_name}:` prefixing rule** — it stays
   un-prefixed/global. catalog's OWN cache keys (schema lookups, etc.) DO get the
   `catalog:` prefix. **This carve-out is a merge-gate acceptance item + a contract
   test (`budget-brake-shared assertion`).**

2. **Audit DB:** catalog-svc's vendored `cost_tracker.py` writes `audit_events`
   rows. catalog-svc's own Postgres schema is `catalog`, but `audit_events` lives in
   the SHARED ledger (§5.B). **catalog-svc's Postgres role needs `GRANT INSERT ON
   public.audit_events TO catalog_user`** (infra handoff §H-infra) — mirrors the
   MS-A `export_user` + MS-F `category_user` grants. NOTE: catalog ALSO writes
   audit_events for its 4 write-route `@audit_event` decorators (via `audit_mw`) —
   so catalog-svc needs the audit grant for BOTH the AI cost ledger AND its own
   write-route audit rows.

#### H3.d — Drift control (3 vendored copies of ai_ops — category, catalog, image)

By MS-5, all 3 AI services have vendored ai_ops. Same mitigation as SUB_PLAN_0F
§F3.d: single-source vendoring from `backend/app/ai_ops/` at the extraction commit
with a recorded source-commit SHA; per-service Prometheus `service="catalog"`
label; a `test_ai_ops_vendoring_parity` contract test asserting the vendored
`budget_cap.py` Lua + key formats are byte-identical to the monolith source; V2
collapses all 3 into `ai-ops-svc` (D6).

> **Cross-service budget-brake invariant at MS-5 (the LAST AI extraction).** After
> catalog extracts, ALL 3 AI workloads (smart_picker in category-svc, autofill in
> catalog-svc, watermark in image-svc) run from vendored copies, ALL decrementing
> the ONE shared `ai:cost:daily:{date}` counter. The MS-5 integration test MUST
> assert a 3-source budget reservation (category-svc + catalog-svc + monolith, or
> all 3 extracted services) all move the SAME counter — this is the final proof
> the GLOBAL ₹500 cap survived the full AI-service fan-out.

---

## H4 — The `/internal/*` shims catalog implements (3 LIVE + 1 defensive — frozen by MS-A)

`catalog` is the largest CALLEE. MS-A (the export pilot) **froze** the two
catalog-owned `/internal/*` shapes. catalog implements them EXACTLY as frozen —
NEVER renames or re-shapes. Plus the dashboard `list_products` shim and the
defensive `get_validation_summary` shim.

### Shim #1 — ownership check (MS-A FROZEN — 3 callers)

```
POST  /internal/products/{id}/ownership-check
  ← backs:  catalog/service.py:921  assert_product_ownership(product_id, user_id, db) -> None
  → returns: 204 No Content on success; 404 catalog.product.not_found on
    (not-exist OR wrong-owner OR soft-deleted) — collapsed uniformly (§10 leak rule)
  callers (post-extraction, over HTTP): image-svc, pricing-svc, export-svc
  (today, in-process): image/service.py:53, pricing/service.py:65, export/service.py:57
```
> **MS-A frozen path (spec_msA_backend.md §5):**
> `/internal/products/{id}/ownership-check` ← `assert_product_ownership(product_id, user_id) -> None`.
> The 3 callers' already-built `catalog_client` shims call THIS exact path. The id
> path-param is the product_id; the user_id is carried in the forwarded JWT
> (caller forwards JWT per §5.A; catalog-svc decodes `user_id` from `sub` claim).

### Shim #2 — export snapshot (MS-A FROZEN — 1 caller, 2-hop internal chain)

```
GET  /internal/products/{id}/export-snapshot
  ← backs:  catalog/service.py:945  get_product_for_export(product_id, user_id, db) -> ExportSnapshotInternal
  → returns: ExportSnapshotInternal verbatim — {product_id, category_id, fields,
    ai_suggestions, image_refs (empty tuple in V1 — dead image branch),
    validation_summary{compulsory_filled/total, optional_filled/total,
    has_validation_errors, status}}  (domain.py:152 + :134)
  callers (post-extraction, over HTTP): export-svc
  (today, in-process): export/service.py:177, :314
```
> **MS-A frozen path (spec_msA_backend.md §5):**
> `/internal/products/{id}/export-snapshot` ← `get_product_for_export(product_id, user_id) -> ExportSnapshotInternal`.
> **2-HOP CHAIN:** this shim internally calls category-svc's
> `/internal/categories/{id}/schema` (the nested outbound — `service.py:962`).
> export-svc's `catalog_client` deserializes catalog-svc's JSON into a vendored
> `ExportSnapshotInternal` dataclass (the §16.D domain-exchange-currency pattern —
> MS-A already authored the vendored copy on the export side). catalog-svc serves
> the shape; export-svc owns its vendored mirror. Zero call-site diff on
> export-svc (§16.G).

### Shim #3 — list products (dashboard — LIVE)

```
GET  /internal/products?page=&limit=
  ← backs:  catalog/service.py:999  list_products(user_id, pagination, db) -> PaginatedProductsInternal
  → returns: PaginatedProductsInternal {items:[Product...], total, page, limit}
    (domain.py:170); active products only, most-recently-updated first
  caller (post-extraction, over HTTP): dashboard-svc
  (today, in-process): dashboard/service.py:78
```
> dashboard-svc (MS-2, already extracted) authored its `catalog_client` shim
> against this method at MS-2 — pointing at the monolith ClusterIP. At catalog's
> MS-5 cutover the Traefik route flips to svc-catalog; dashboard's call site
> (`dashboard/service.py:78`) is byte-identical (§16.G). **VERIFY against
> SUB_PLAN_0B (dashboard)'s frozen contract that dashboard-svc calls
> `list_products` over the path `/internal/products` with `page`/`limit` query
> params — match its frozen shape exactly (Open Question).**

### Shim #4 — validation summary (DEFENSIVE — documented-but-not-called, §contradiction above)

```
GET  /internal/products/{id}/validation-summary   [DEFENSIVE — author only if Open Question confirms a live HTTP caller]
  ← backs:  catalog/service.py:1020  get_validation_summary(...)
  → returns: ValidationSummaryInternal (domain.py:134)
  caller: dashboard-svc IF it consumes validation summaries over HTTP (NO live
    caller at develop tip — see §contradiction)
```
> Author DEFENSIVELY per the SUB_PLAN_0F `list_super_categories` precedent. **Open
> Question: confirm with the master session / SUB_PLAN_0B whether dashboard-svc
> calls `get_validation_summary` over HTTP. If not, the unused shim is harmless;
> if a dashboard slice adds it, the shim exists.** Default: author it (cheap
> insurance for the spine).

**§16.G call-site preservation (all 4 inbound shims):** catalog-svc authors the
SERVER side. The 4 callers' `catalog_client` shims (already built at MS-1/2/3) call
these paths; at catalog's cutover the Traefik route for `/internal/products/*`
flips from monolith-svc to svc-catalog — every caller's `await
catalog_service.<method>(...)` call site stays byte-for-byte identical.

---

## H5 — The 5 OUTBOUND HTTP-shim clients catalog authors (the spine's caller side)

Unlike category (ZERO outbound), catalog has the heaviest outbound surface. It
authors **5 client shims across 2 callee services**, each pointing at the ALREADY-
EXTRACTED sibling pod's ClusterIP (NOT the monolith — category-svc + customer-svc
are real pods by MS-5):

### category_client (→ category-svc, 3 methods)

```
core/extracted_clients/category_client.py
  assert_category_exists(category_id, db)  → GET  /internal/categories/{id}/exists
     ← catalog/service.py:401  (create_product 404 gate)
  fetch_schema(category_id, db)            → GET  /internal/categories/{id}/schema   [MS-F FROZEN shim #1]
     ← catalog/service.py:463,:506,:620,:800,:962,:1034  (6 call sites — the hot path)
  get_field_enum(category_id, field, db)   → GET  /internal/categories/{id}/field-enum/{field}  [MS-F FROZEN shim #2]
     ← catalog/service.py:309  (autofill enum resolution)
```
> **`fetch_schema` is THE autosave hot path (Risk #1, MASTER_PLAN §6 line 405).**
> catalog calls `category_service.fetch_schema` on 6 call sites including
> `patch_product` validation (`:506`) and `autofill_product` (`:620`) — fired at
> autosave frequency (~every 5s during typing). In-process ~1ms; HTTP ~10ms.
> **MITIGATION:** category-svc serves `fetch_schema` from its full-tree + top-100-
> schema pre-warm cache (≥99% hit, SUB_PLAN_0F §F-acceptance) — so the hot-path hop
> is ~10ms cached, not a cold DB read. Pre-extraction load test (MASTER_PLAN §6
> Risk #1: 10× traffic against dockerized catalog-svc + category-svc; HALT if the
> autosave P95 exceeds the §15.E budget by >20%). **`assert_category_exists` →
> `/internal/categories/{id}/exists`: category's SUB_PLAN_0F §F4 flagged this shim
> as "added when catalog extracts (MS-5)" — so catalog's MS-5 work must coordinate
> with category-svc to ADD the `/internal/categories/{id}/exists` server shim if
> SUB_PLAN_0F did not pre-emptively author it. Open Question / cross-wave
> coordination item.**

### customer_client (→ customer-svc, 2 methods)

```
core/extracted_clients/customer_client.py
  assert_eligible_for_super_id(user_id, super_id, db)  → GET  /internal/seller-profile/{user_id}/eligibility/{super_id}
     ← catalog/service.py:406  (create_product PROFILE_INCOMPLETE_FOR_CATEGORY gate)
  get_compliance_block(user_id, db)                    → GET  /internal/seller-profile/{user_id}/compliance-block  [MS-A/MS-E FROZEN]
     ← catalog/service.py:839  (get_preview compliance block)
```
> `get_compliance_block` → `/internal/seller-profile/{user_id}/compliance-block` is
> the SAME shim MS-A froze for export (spec_msA_backend.md §5: customer-svc
> `/internal/seller-profile/{user_id}/compliance-block` ← `get_compliance_block`).
> customer-svc (MS-3) already serves it. catalog's `customer_client` reuses the
> SAME frozen path. The `ComplianceBlock` returned is deserialized into catalog-
> svc's vendored copy of the customer `ComplianceBlock` dataclass (§16.D — same
> pattern MS-A used on export's side). `assert_eligible_for_super_id` →
> `/internal/seller-profile/{user_id}/eligibility/{super_id}` is the path MASTER_PLAN
> §5.A line 338 names verbatim. **VERIFY against SUB_PLAN_0E (customer) that
> customer-svc serves BOTH these `/internal/*` paths (Open Question — the
> eligibility shim may need to be ADDED to customer-svc at MS-5).**

> **§16.G outbound discipline:** every outbound call site in catalog's service.py
> stays byte-identical. ONLY the import lines change from
> `from app.modules.category import service as category_service` (`:98`) /
> `from app.modules.customer import service as customer_service` (`:99`) to
> `from app.core.extracted_clients import category_client as category_service` /
> `customer_client as customer_service` — re-exporting the SAME symbol name so the
> 8 call sites (category ×6 fetch_schema + ×1 exists + ×1 field-enum; customer ×2)
> are UNCHANGED. The `get_product_for_export` diff vs monolith shows ONLY the
> import-line change.

---

## Code surfaces

File-level inventory. `backend/services/svc-catalog/` is the new home; the old
`backend/app/modules/catalog/` tree is DELETED only after hybrid-mode CI passes
≥7 days (MASTER_PLAN §3.C) — until then both coexist (strangler fig).

### Backend — new service tree (`backend/services/svc-catalog/`)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `app/main.py` | NEW | Standalone FastAPI; mounts 6 public routes (**preserve `FEATURE_CATALOG_FORM_ENABLED` guard**) + 3-4 `/internal/*` shim routes; 6-mw chain (H2); `/health` + `/metrics`. NO Celery (catalog has no worker). | services-builder |
| `app/router.py` | NEW (from `modules/catalog/router.py`) | 6 public routes verbatim (paths, 5 rate-limit scopes, 4 audit decorators, 3 feature-flag guards) | api-routes-builder |
| `app/internal_router.py` | NEW | 3 LIVE shims (ownership-check, export-snapshot, list_products) + 1 defensive (validation-summary); forwarded-JWT auth per §5.A line 338, NOT get_current_user UI flow | api-routes-builder |
| `app/service.py` | NEW (from `modules/catalog/service.py`) | 9 public methods verbatim; the 8 outbound call sites rewired to `core/extracted_clients` (§16.G byte-identical); ai_ops imports → vendored `app.ai_ops` (same path) | services-builder |
| `app/repository.py` | NEW (from `modules/catalog/repository.py`) | private data access; **`scope_to_user` preserved everywhere** (§10 leak rule); bound to schema `catalog` | services-builder |
| `app/domain.py` | NEW (from `modules/catalog/domain.py`) | 11 frozen dataclasses; `ExportSnapshotInternal`/`ValidationSummaryInternal`/`PaginatedProductsInternal` are the cross-module exchange currency | services-builder |
| `app/schemas.py` | NEW (from `modules/catalog/schemas.py`) | PRIVATE Pydantic wire-shapes | api-routes-builder |
| `app/exceptions.py` | NEW (from `modules/catalog/exceptions.py`) | `CatalogError` + subclasses | services-builder |
| `app/core/extracted_clients/category_client.py` | NEW | 3 shims (exists, schema, field-enum) → category-svc ClusterIP (real pod by MS-5) | services-builder |
| `app/core/extracted_clients/customer_client.py` | NEW | 2 shims (eligibility, compliance-block) → customer-svc ClusterIP | services-builder |
| `app/ai_ops/{client,budget_cap,cost_tracker,guardrail,prompt_registry,eval,metrics}.py` | NEW (VENDORED, byte-identical) | the autofill AI path (H3.a); budget brake → SHARED Valkey DB 0 + audit DB (H3.c) | services-builder |
| `app/ai_ops/prompts/autofill_v1.py` | NEW (VENDORED — this ONE prompt) | the only workload catalog runs; content owned by prompt-engineer | services-builder (carries verbatim) |
| `app/core/middleware/*` | NEW (VENDORED) | 6-mw chain (H2); audit_mw ACTIVE (4 write routes) | services-builder |
| `app/core/{auth,cache,plan_guard,errors,tenancy,metrics}.py` | NEW (VENDORED) | local JWT (H2); plan_guard `product_count` + `ai_autofill_hourly` | services-builder |
| `app/i18n/{messages_en,...}.py` | NEW (VENDORED read-only) | catalog's `validation_message_id` subset (schema-driven field validation) | services-builder |
| `app/shared/{database,config,valkey}.py` | NEW (vendored, trimmed) | `Settings`: `DATABASE_URL`@schema `catalog`, `VALKEY_URL`, `JWT_SECRET`, `GEMINI_*`, `LANGFUSE_*`, `AI_DAILY_BUDGET_INR`, `CACHE_VERSION`, `FEATURE_*` flags, `APP_ENV`; **largest pool** (autosave write-heavy, §2.E line 207 "catalog gets the largest pool") | services-builder |
| `requirements.txt` | NEW | fastapi, sqlalchemy, asyncpg, redis, httpx, **google-genai (gemini)**, langfuse; NO openpyxl/celery (no XLSX/worker) | services-builder |
| `Dockerfile` | NEW (placeholder) | FROM python:3.12-slim; infra lead authors the real one | infra-builder |
| `alembic/` | NEW | own chain rooted at schema `catalog`; `version_table_schema="catalog"`; 3 tables | database-builder |
| `tests/test_catalog_extraction.py` | NEW | hybrid-mode integration; ownership/export-snapshot/list shim shapes; budget-brake-shared (3-source); autosave P95 | backend-coordinator |

### Backend — monolith-side changes (during strangler window)

| File | Tag | Description | Owning specialist |
|---|---|---|---|
| `backend/app/modules/catalog/` (7 files) | KEEP-then-DELETE | stay live until hybrid-mode CI green ≥7 days, then deleted | backend-coordinator |
| `backend/app/main.py` | MODIFY (additive-minimal) | at cutover, remove the in-process mount — **delete the single `:127` `app.include_router(catalog_router)` inside the `if settings.FEATURE_CATALOG_FORM_ENABLED:` block + the `:40` import; touch NOTHING else.** Until cutover both modes run. | backend-coordinator |

### Infra (placeholders only — owned by infra lead, land on infra branch)

| File | Tag | Description |
|---|---|---|
| `k8s/svc-catalog/deployment.yaml` | NEW (placeholder) | API replicas; **largest pool** (autosave write-heavy); requests/limits per infra plan §6.3; NO worker deployment |
| `k8s/svc-catalog/service.yaml` | NEW (placeholder) | ClusterIP :8001 |
| Traefik IngressRoute | NEW (placeholder) | `/api/v1/products/*` (POST/PATCH/DELETE/autofill/preview/draft) + `/internal/products/*` → svc-catalog:8001. **METHOD-split on `/api/v1/products`** (POST→catalog, GET→dashboard) — the §3.4-disambiguation routing nuance |
| Postgres schema `catalog` + role + grants | NEW (placeholder) | `CREATE SCHEMA catalog; GRANT ... TO catalog_user; GRANT INSERT ON public.audit_events TO catalog_user` (BOTH the AI cost ledger AND the 4 write-route audit rows, H3.c) |
| Secret Manager bindings | NEW (placeholder) | `JWT_SECRET` (same secret iam-svc signs with — H2), `GEMINI_API_KEY`, `LANGFUSE_*` |

---

## Documentation deliverables

- **OpenAPI** — svc-catalog standalone OpenAPI; 6 public + 3-4 internal endpoints.
- **`BACKEND_ARCHITECTURE.md` §10 amendment** — "Extracted to svc-catalog (V1.5)"
  note: 4 inbound callers (image/pricing/dashboard/export) now HTTP shims; 2
  outbound (category/customer) now HTTP shims; §16.G call-site contract preserved;
  ai_ops VENDORED per D6; budget brake SHARED. **Founder approval required (§10 is
  LOCKED).**
- **`MASTER_PLAN.md` §4 row H** — update annotation: filename `SUB_PLAN_0H` (not
  `SUB_PLAN_08`); dependency "MS-4 complete, runs ALONE." **Founder touches the
  master plan; this sub-plan flags the reconciliation.**
- **HTTP-shim contract doc (callee side)** — the 3-4 `/internal/*` endpoints
  catalog exposes (§H4), frozen-shape-cited.
- **Runbook** — `docs/runbooks/svc-catalog-rollback.md` (§3.C specialized for
  catalog — incl. the 4-surface route-flip-back, the 2-hop chain note, the dead
  image branch note, the budget-brake-keyspace carve-out).
- **Hybrid-mode CI config note** — at MS-5, CI docker-composes ALL 7 already-
  extracted services (export, dashboard, image, pricing, customer, category, iam) +
  catalog-svc. catalog's HTTP-mode CI must stand up catalog-svc + assert the 4
  callers reach it via `/internal/*` AND assert catalog-svc reaches category-svc +
  customer-svc via ITS outbound shims (the FIRST extraction with both directions
  live).

---

## Branch setup

Model C (per common rule 6): `feature/microservices-catalog/integration` off
develop + group branches (`feature/microservices-catalog/backend`,
`feature/microservices-catalog/infra`); worktrees `/tmp/mesell-wt/msH-*`; F3
protection; founder-gate PR `[FOUNDER GATE — DO NOT MERGE]` LEFT OPEN; squash group
merges; lead-gate as PR comment; `--admin`; ref-delete via `gh api`. NEVER switch
the master tree's branch. Integration branch merges `origin/develop` BEFORE the
founder-gate PR opens (shared-file discipline, common rule 4). **This PHASE-1 docs
sub-plan is authored on `feature/microservices-catalog/docs-subplan0h` — a docs-only
branch distinct from the execution branches above.**

---

## Memory protocol

**Memories the coding-session leads MUST read at start:**
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (extraction
  contracts, §16.G, the MS-A recipe, this sub-plan's notes `spec_msH_backend.md`)
- `.claude/agent-memory/meesell-services-builder/MEMORY.md`
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md` (svc sizing, schema-per-
  service, Traefik method-split, largest-pool)
- `.claude/agent-memory/meesell-database-builder/MEMORY.md` (Alembic head chain;
  3-table schema-move; cross-schema FK pre-scan)

**Memos created during this extraction:**
- `.claude/agent-memory/meesell-backend-coordinator/spec_msH_backend.md` (the
  executable specialist task spec — companion to THIS sub-plan)
- `.claude/agent-memory/meesell-backend-coordinator/handoff_msH_infra.md`
  (K8s/Postgres/Traefik/Secret placeholders + the audit-DB grant + method-split route)

---

## Dispatch templates

See the companion spec `spec_msH_backend.md` for the full paste-able specialist
prompts (services-builder / api-routes-builder / database-builder), dispatch
sequence, and per-specialist acceptance criteria. **Not dispatched by this planning
session** (PHASE 1 is authoring only; the session cannot dispatch agents per
CLAUDE.md HYBRID rule 7 — the master session runs steps 2-3 at MS-5).

---

## Acceptance gate

Sub-Plan H execution (MS-5) is DONE when:

- [ ] `feature/microservices-catalog/backend` PR merged to `.../integration` (backend lead gate)
- [ ] `feature/microservices-catalog/infra` PR merged to `.../integration` (infra lead gate)
- [ ] Hybrid-mode CI green in BOTH modes (in-process monolith + svc-catalog-as-pod) per §3.A, for ≥7 days
- [ ] `cd backend && pytest services/svc-catalog/tests/test_catalog_extraction.py` green
- [ ] service.py diff vs monolith = ZERO call-site changes (only the 2 import-line rewires + vendoring) — §16.G absolute contract
- [ ] `scope_to_user` preserved on every product/catalog read (§10 leak rule) — repository bound to schema `catalog`
- [ ] **`FEATURE_CATALOG_FORM_ENABLED` mount guard preserved** (route count is conditional — row-26 lesson)
- [ ] The 6 public routes mount (flag ON); 5 rate-limit scopes + 4 audit decorators + 3 feature-flag guards preserved verbatim
- [ ] The 2 MS-A-frozen `/internal/*` shims (ownership-check, export-snapshot) respond with the FROZEN shapes; image/pricing/export reach them via Traefik route flip with ZERO call-site diff (§16.G)
- [ ] `list_products` shim (#3) matches SUB_PLAN_0B's frozen dashboard contract (Open Question resolution)
- [ ] **export-snapshot 2-hop chain works**: catalog-svc's `/internal/products/{id}/export-snapshot` internally reaches category-svc's `/internal/categories/{id}/schema` (the nested outbound) within the §5.E timeout budget
- [ ] **Budget-brake-shared (3-source) assertion green** — a `check_and_reserve` from catalog-svc + category-svc + monolith all decrement the SAME `ai:cost:daily:{date}` counter (carve-out: `ai:*` keys NOT `catalog:`-prefixed)
- [ ] **ai_ops vendoring parity test green** — vendored `budget_cap.py` Lua + key formats byte-identical to source (drift guard, H3.d)
- [ ] autofill `autofill.v1` workload runs from the vendored prompt; graceful fallback (`fallback_offered=True`) on BudgetExceededError preserved (`service.py:649`)
- [ ] **autosave P95 within §15.E budget** — `fetch_schema` hot path served from category-svc pre-warm cache (≥99% hit); pre-extraction 10× load test passed (Risk #1)
- [ ] CI gates 1 (unit), 2 (smoke), 3 (lint) green; gates 4/5 advisory
- [ ] Full backend suite `def test_` count MONOTONIC ≥ **698** baseline (live count at authoring 2026-06-12; quote the live count at PR time, do NOT hardcode) — extraction ADDS svc-catalog tests, removes none until the strangler window closes
- [ ] catalog's own tests green in BOTH monolith (pre-flip) AND extracted service (the 24 catalog-owned: 7 `test_catalog_routes` + 9 `test_catalog_unit` + 5 `test_ai_autofill_integration` + 3 `test_live_preview_flag_404`)
- [ ] NO tautological tests (pricing lesson) — the hybrid integration test asserts REAL behavior (an audit row lands; a shim forwards JWT + returns the real shape; the budget counter actually moves)
- [ ] Documentation deliverables landed (OpenAPI, §10 amendment w/ founder approval, runbook, shim contract doc)
- [ ] V1_FEATURE_SPEC features 3 (Fast Catalog Form), 4 (AI Auto-fill), 6 (Live Preview) acceptance still met against the extracted service
- [ ] `feature_board_backend.md` row reflects MERGED (F2 discipline)
- [ ] Founder approval on `feature/microservices-catalog/integration` → `develop` PR

### PHASE-2 TAIL — unique to MS-H (the FINAL extraction)

After catalog's founder gate merges, two PROGRAM-LEVEL steps close the migration:

- [ ] **STEP T1 — §5.G post-extraction repo-management compliance audit** (MASTER_PLAN
  line 397, founder-mandated 2026-06-10). **Owner: meesell-backend-coordinator with
  master-session review.** Acceptance: (a) re-verify the Model C convention against
  the realized 8-service topology (a backend "feature" = a service) — branch model,
  PR templates, boards, merge gates, session naming; (b) verify hybrid-mode CI
  behaved as specified across ALL 8 extractions; (c) audit agent obedience during
  migration (worktrees scoped, allowlists honored, boards kept, iteration caps
  respected, rollback contract adhered to); (d) **report to founder**; (e) amend
  `docs/plans/repo_management/MASTER_PLAN.md` if it drifted from realized practice.
- [ ] **STEP T2 — MASTER_PLAN completion stamp.** Only AFTER T1 passes: stamp the
  Microservices Migration MASTER_PLAN as COMPLETE (A–H all extracted + soaked +
  audited). Owner: meesell-backend-coordinator drafts the stamp + revision-history
  row; **master-session/founder ratifies** (the lead does not self-declare program
  completion). Per §4 row H line 308: "the program (A–H) is NOT declared complete
  until the post-extraction repo-management compliance audit at §5.G passes" — T2
  is gated on T1. Update §4 row H annotation, the Revision History, and the
  document-status banner.

> **D3 VM checkpoint (per MS-PAR-1):** at MS-5 the deploy is monolith (now nearly
> empty) + export + dashboard + image + pricing + customer + category + iam +
> catalog (8 services + the shrinking monolith) on the dev node. **MS-4 already
> likely triggered the e2-standard-4 ask; if not, MS-5 almost certainly does.** The
> upgrade (~₹2,600/mo) is plan-pre-approved (D3) BUT the SPEND gets a fresh founder
> ask at the moment the deploy doesn't fit. **STOP and ask the founder before
> provisioning** — never on the plan-level pre-approval alone (master-session
> standing rule).

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **The autosave hot path P95 blows** — catalog calls `fetch_schema` on 6 sites incl. `patch_product` validation (every ~5s autosave); in-process ~1ms → HTTP ~10ms (MASTER_PLAN §6 Risk #1) | **Medium** | **High** | category-svc serves `fetch_schema` from full-tree + top-100 pre-warm cache (≥99% hit, SUB_PLAN_0F) → ~10ms cached not cold DB; pre-extraction 10× load test against dockerized catalog-svc+category-svc; HALT if autosave P95 exceeds §15.E budget by >20%. catalog runs MS-5 ALONE so this pain lands once. |
| R2 | **4 networking surfaces flip at once** — image/pricing/export/dashboard all repoint at catalog-svc simultaneously at cutover | Medium | **High** | All 4 callers already run `catalog_client` HTTP shims against the monolith by MS-5 (built at MS-1/2/3); cutover is ONE Traefik route flip per surface; §16.G means zero caller call-site diff; rollback = flip all 4 back to monolith-svc in one IngressRoute revert. MS-5 ALONE de-risks. |
| R3 | **2-hop internal chain latency** (export-svc → catalog-svc → category-svc on export-snapshot) | Medium | Medium | category's `/internal/categories/{id}/schema` is cache-served (≥99% hit); document the chain depth + cumulative §5.E timeout budget in the runbook; the chain only fires on export (not autosave), so it is off the hot path. |
| R4 | **`ai:*` budget keyspace accidentally gets the `catalog:` prefix**, splitting the GLOBAL ₹500 cap | Medium | **High** | The carve-out (H3.c) is a named acceptance item + the 3-source `budget-brake-shared assertion`; vendored `budget_cap.py`/`cost_tracker.py` byte-identical to source (no prefix logic); prefix applied only in `shared/valkey.py` cache-DB-3 factory; infra excludes `ai:*` from any backfill re-prefixing. |
| R5 | **Vendored ai_ops drifts** from monolith / category / image (3 copies by MS-5) | Medium | Medium | Single-source vendoring + recorded source-commit SHA; `test_ai_ops_vendoring_parity` byte-compares the brake code; V2 collapses to `ai-ops-svc` (D6). |
| R6 | **Cross-schema FK integrity** — `products.user_id` → `users` (iam schema) becomes cross-schema (Risk #5) | Low | High | database-builder runs the §6-Risk#5 integrity pre-scan (every `products.user_id` resolves to a real `users` row) before any FK adjustment; `SET SCHEMA` preserves the table; round-tripped upgrade/downgrade; catalog drops NO FK. |
| R7 | **`scope_to_user` accidentally dropped** during extraction, leaking products across tenants (the §10 leak rule) | Low | **High** | merge-gate acceptance item; the extracted `repository.py` diff vs monolith shows `scope_to_user` on every product/catalog read (`:87`, `:108`, `:126`, `:143`); a contract test asserts a cross-tenant product fetch returns 404 (collapsed to `None`). |
| R8 | **Dead image `getattr` branch** (`service.py:828`,`:980`) mistaken for a live edge → an unneeded image_client shim authored | Low | Low | Documented as dead code (`get_image_refs` does not exist on image-svc); travels verbatim (§16.G) but never executes; `image_refs` stays empty tuple; NO image_client shim authored. |
| R9 | **`FEATURE_CATALOG_FORM_ENABLED` mount guard dropped** → catalog routes mount unconditionally, breaking flag-off environments | Low | Medium | merge-gate acceptance item (row-26 lesson); svc-catalog main.py preserves the guard OR Traefik gates equivalently; the mounted-route count is verified with the flag ON. |
| R10 | **`get_validation_summary` shim built/omitted wrongly** (documented-but-not-called contradiction) | Low | Low | Author DEFENSIVELY (cheap insurance); Open Question to master session / SUB_PLAN_0B; unused shim harmless; docstring correction flagged for founder-touch. |

---

## Open Questions (resolve with master session before MS-5 dispatch)

1. **`assert_category_exists` → `/internal/categories/{id}/exists` server shim:**
   SUB_PLAN_0F §F4 deferred this to "added when catalog extracts (MS-5)." Confirm
   category-svc must ADD this server shim at MS-5 (cross-wave coordination), OR
   whether SUB_PLAN_0F pre-emptively authored it.
2. **customer-svc `/internal/seller-profile/{user_id}/eligibility/{super_id}` shim:**
   verify SUB_PLAN_0E (customer) serves this path (MASTER_PLAN §5.A line 338 names
   it). If not, it must be ADDED to customer-svc at MS-5.
3. **dashboard `list_products` frozen contract:** verify SUB_PLAN_0B's
   `catalog_client` calls `/internal/products?page=&limit=` with the
   `PaginatedProductsInternal` shape — match exactly.
4. **`get_validation_summary` defensive shim:** confirm whether dashboard-svc
   consumes it over HTTP (NO live caller at develop tip). Default: author it.

---

## Rollback Log

*(Empty until execution. Per MASTER_PLAN §3.C, a rollback during MS-5 is the
4-surface Traefik route-flip back to monolith-svc + one `git revert -m 1
<merge-sha>` on the integration branch + the 3-table schema downgrade to `public`
+ `kubectl delete deployment svc-catalog` + re-run hybrid-mode CI in pure
in-process mode + root-cause recorded here. The budget-brake keyspace + the
category-svc/customer-svc outbound targets need no rollback step — they are
shared/sibling-owned and unaffected by a catalog-svc revert.)*

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-12 | mesell-ms-catalog-session-1 (PHASE 1, hybrid step 1) | Initial AUTHORED draft. Sub-Plan H (catalog — THE SPINE, last+riskiest) per MASTER_PLAN §4 row H + MS-PAR-1 + SUB_PLAN_0F template. As-built: 6 mounted routes (FLAG-GUARDED `FEATURE_CATALOG_FORM_ENABLED`); 4 inbound callers (image/pricing/export/dashboard, file:line cited); 2 outbound callees (category×3 + customer×2, file:line cited) + 1 DEAD image getattr branch; 3 tables (catalogs/products/product_drafts, tenant-scoped). H1 (ai_ops vendored, `autofill.v1`) + H2 (mw vendored, local JWT) LOCKED from D6/D7. H3 ai_ops vendoring + SHARED budget brake (same `ai:*` keyspace carve-out as F3). H4 the 3 LIVE + 1 defensive `/internal/*` shims (ownership-check + export-snapshot MS-A-FROZEN; list_products; validation-summary defensive). H5 the 5 outbound shims (the spine's caller side, targeting REAL sibling pods at MS-5). SOURCE-WINS corrections recorded: filename 0H-not-08; §3.4 "11 endpoints" disambiguated to catalog's own 6; `get_validation_summary` documented-but-NOT-called (TRUE branch tip — defensive shim + Open Question); dead image `getattr` branch (`get_image_refs` does not exist). PHASE-2 TAIL: §5.G compliance audit (T1) + MASTER_PLAN completion stamp (T2). STATUS: AUTHORED — EXECUTION GATED ON MS-5 WAVE OPEN (ALONE, after MS-4). |

---

**END OF SUB-PLAN H — AUTHORED, execution gated on MS-5 wave open (ALONE, after MS-4). THE FINAL EXTRACTION.**
