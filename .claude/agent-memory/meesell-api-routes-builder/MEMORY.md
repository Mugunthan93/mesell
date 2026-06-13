# Memory — meesell-api-routes-builder

## Agent Identity
FastAPI route handler specialist for MeeSell. Owns the 16 V1 endpoints + Pydantic request/response schemas + OpenAPI metadata + route-level pytest tests. Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## MEMORY.md
(Index of memory files — populated as agent works)

---

## Session: 2026-06-05 — Router Purge (G2/G3/G5)

### Task summary
Executed 3-step purge: delete legacy routers/schemas/services, rewrite auth URLs, author boot integration test.

### Files deleted
Routers (9): catalogs.py, skus.py, images.py, pricing.py, exports.py, generation.py, quality.py, research.py
(auth.py kept — modified only)
Schemas (6): catalog.py, sku.py, image.py, pricing.py, quality.py, scrape.py
(auth.py kept)
Services (4): export_service.py, quality_engine.py, image_processor.py, meesho_scraper.py
(ai_engine.py, otp_service.py, pricing_engine.py, storage.py kept — no deleted model imports)
Tests (3): test_export_service.py, test_quality.py, test_smoke.py (dead code for deleted services)

### Files modified
- backend/app/main.py: removed 8 router imports + 8 include_router calls, kept auth_router only
- backend/app/routers/auth.py: /send-otp -> /otp/send, /verify-otp -> /otp/verify; added summary= on both endpoints
- backend/tests/test_auth.py: 4 URL string replacements (send-otp -> otp/send, verify-otp -> otp/verify)
- backend/tests/conftest.py: same URL replacements in auth_client fixture

### Files created
- backend/tests/test_app_boot_integration.py: 7 tests, all PASS

### Route types (important pattern)
FastAPI mounts its built-in OpenAPI routes (/openapi.json, /docs, /docs/oauth2-redirect, /redoc)
as `starlette.routing.Route` instances, NOT `fastapi.routing.APIRoute`.
Application endpoints are `fastapi.routing.APIRoute`.
Mount objects (e.g. StaticFiles) are `starlette.routing.Mount`.
When asserting route inventory in tests: use isinstance(r, (Route, APIRoute)) to include both.

### Auth URL pattern (locked)
prefix = "/api/v1/auth"
send:   @router.post("/otp/send")   -> POST /api/v1/auth/otp/send
verify: @router.post("/otp/verify") -> POST /api/v1/auth/otp/verify
me:     @router.get("/me")          -> GET  /api/v1/auth/me

### Blocker surfaced (hand-off to services-builder)
backend/app/workers/generation_tasks.py lines 18, 79:
  `from app.models.sku import SKU` (lazy imports inside function bodies)
The SKU model is deleted. Worker will fail at runtime.
Services-builder must rewrite generation_tasks.py to use new Product model.
This reference survived grep check 6 — coordinator is aware.

### Python version note
Project venv is Python 3.11 (not 3.12 as CLAUDE.md states).
Venv path: backend/.venv/bin/python
Always use PYTHONPATH=/Users/mugunthansrinivasan/Project/mesell/backend when running pytest
from outside the venv activate context.

### Total route count after purge
app.routes has 9 entries:
  - 4 starlette.routing.Route (FastAPI builtins: openapi, docs, oauth2-redirect, redoc)
  - 3 fastapi.routing.APIRoute (auth: otp/send, otp/verify, me)
  - 1 fastapi.routing.APIRoute (health)
  - 1 starlette.routing.Mount (/dev-static, dev-only StaticFiles)
= 8 routable (Route + APIRoute) + 1 Mount = 9 total app.routes

### Memory entry index
| Entry | Type | Summary |
|---|---|---|
| Router purge 2026-06-05 | project | G2/G3/G5 complete — 9 routers, 6 schemas, 4 services, 3 tests deleted |
| Route types pattern | reference | FastAPI builtins are Route not APIRoute; use isinstance(r, (Route, APIRoute)) |
| Auth URL pattern | reference | /otp/send, /otp/verify locked per §3.1 |
| Python venv path | reference | .venv/bin/python (3.11), PYTHONPATH needed for pytest |
| Worker blocker | reference | generation_tasks.py lazy-imports deleted SKU model — services-builder must fix |
| §8 customer routes 2026-06-07 | project | 5 endpoints + 19 tests PASS; fixture engineering patterns below |

---

## Session: 2026-06-07 — §8 customer router (step 2 of 2)

### Task summary
Authored `backend/app/modules/customer/router.py` (5 endpoint handlers per §8.B), exported `customer_router` from `__init__.py`, mounted it in `main.py`, bumped boot integration test from 11 → 15 paths, and authored 19 route-level tests in `test_customer_routes.py`.

### Route count math (critical gotcha)
FastAPI creates one `APIRoute` object per (path, method). `/api/v1/seller-profile` has both GET and PATCH → 2 raw `APIRoute` objects in `app.routes`, but `_route_map()` (dict keyed by path) has 1 entry. 4 new customer PATHS = +4 to route_map count (not +5). Boot test expected_count went 11 → 15.

### `rate_limit` decorator pattern
```python
@router.patch("/seller-profile", response_model=SellerProfileResponse, ...)
@rate_limit(scope="profile_update", limit=60, window=3600)
async def patch_seller_profile(payload: ..., user: ..., db: ...) -> ...:
```
Decorator signature: `rate_limit(scope: str, limit: int, window: int)` — NO `key=` param. Per-user keying is automatic for authenticated routes (TenancyContextMiddleware writes `request.state.user_id`).

### Compliance extension raw payload extraction pattern
```python
raw_payload: dict[str, Any] = {
    **payload.model_dump(),
    **(payload.model_extra or {}),
}
```
`PatchComplianceExtensionRequest` has `extra="allow"` → must combine both to capture forward-compat keys.

### Service method return types (critical for response)
- `get_required_fields()` returns `RequiredFieldsResponse` directly — do NOT `.model_validate()`
- All other service methods return `SellerProfile` domain object → `SellerProfileResponse.model_validate(profile)`

### Test fixture engineering: 3 bypassed-DI problems + solutions

**Problem 1: app.dependency_overrides works for `Depends()` but NOT module-level singletons**
`audit_mw.AsyncSessionLocal` is imported at module level and used directly — NOT via `Depends()`. Override via `dependency_overrides` has no effect on it. Fix: patch the attribute directly:
```python
import app.core.middleware.audit_mw as _audit_mw
_original = _audit_mw.AsyncSessionLocal
_audit_mw.AsyncSessionLocal = TestSession
# ... yield ...
_audit_mw.AsyncSessionLocal = _original  # restore in teardown
```

**Problem 2: core/cache.py uses `app.shared.valkey._cache_client` singleton**
`get_valkey_cache()` is NOT a FastAPI dependency — it's called directly by `core/cache.py get_or_set()`. The singleton is module-level in `app.shared.valkey`. Fix: patch `_cache_client` directly:
```python
import app.shared.valkey as _valkey_module
_original_cache = _valkey_module._cache_client
_valkey_module._cache_client = _redis_lib.from_url(f"{valkey_base}/3", decode_responses=True)
# ... yield ...
_valkey_module._cache_client = _original_cache  # restore in teardown
```

**Problem 3: asyncpg pool binds to event loop at first connection**
With `pool_pre_ping=True` (default pooled engine), asyncpg stores `Future` objects bound to the loop that established the connection. In test contexts where the loop context shifts (even slightly, e.g., within session-loop tests that straddle anyio TaskGroups), this causes `RuntimeError: Task got Future attached to a different loop`.
Fix: ALWAYS use `poolclass=NullPool` for test engines:
```python
from sqlalchemy.pool import NullPool
engine = create_async_engine(db_url, poolclass=NullPool)
```
NullPool opens a fresh TCP connection per request and closes it immediately — zero pool reuse, zero Future binding issues. Per-connection overhead (~2 ms) is negligible.

**When `audit_mw` cross-loop error becomes ExceptionGroup**
Starlette's `BaseHTTPMiddleware` wraps `call_next` in an anyio `TaskGroup`. If ANY task in that group raises a `RuntimeError` (even one caught inside `audit_mw`), anyio wraps it in an `ExceptionGroup` that propagates PAST the normal exception handler chain to pytest. This breaks tests that expect a 4xx HTTP response — pytest sees an ExceptionGroup, not a Response object. The ONLY fix is to prevent the RuntimeError at source (NullPool + patching `AsyncSessionLocal`).

### conftest.py VALKEY_URL default
`tests/conftest.py` sets `os.environ.setdefault("VALKEY_URL", "redis://localhost:6381/15")`. The test fixture CORE_TEST_VALKEY_URL defaults to `redis://localhost:6379`. These are different ports. Always verify which port is actually running in the test environment (use `CORE_TEST_VALKEY_URL` env var, not `VALKEY_URL` settings).

### monkeypatch for _get_super_id_set
When the ephemeral DB has ZERO category rows, `set_active_categories` always raises `InvalidSuperCategoryError`. For tests that need a valid super_id path:
```python
import app.modules.customer.service as _customer_service
async def _mock_get_super_id_set(db): return {"26", "19", "13", "16", "80"}
monkeypatch.setattr(_customer_service, "_get_super_id_set", _mock_get_super_id_set)
```
This also applies to `set_compliance_extension` indirectly (requires super_id in active_super_categories, which requires set_active_categories to have been called with a valid super_id first).

### ruff note
`from fastapi import APIRouter, Depends, status` — `status` is commonly imported from FastAPI but customer routes use no `status.HTTP_xxx` constants (all responses default to 200). Ruff F401 will flag it. Remove unused `status` import.

### Files touched
- `backend/app/modules/customer/router.py` (CREATED + ruff-fixed)
- `backend/app/modules/customer/__init__.py` (MODIFIED)
- `backend/app/main.py` (MODIFIED)
- `backend/tests/test_app_boot_integration.py` (MODIFIED)
- `backend/tests/test_customer_routes.py` (CREATED)

---

## Session: 2026-06-07 — §9 category router (step 2 of 2)

### Task summary
Authored `backend/app/modules/category/schemas.py` (10 Pydantic v2 models per §9.E),
`backend/app/modules/category/router.py` (5 endpoint handlers per §9.B), exported
`category_router` from `__init__.py`, mounted it in `main.py`, bumped boot integration
test from 15 → 20 distinct paths. Ruff clean on all files.

### Route count math
Boot integration: 20 distinct paths. Breakdown:
  4 FastAPI builtins + 6 iam + 4 customer paths (GET+PATCH on /seller-profile count as 1 path)
  + 5 category paths + 1 health = 20.

### ETag implementation pattern (locked for §9 + future modules)
```python
# In router handler for GET /categories and GET /categories/{id}/schema:
payload = await category_service.get_category_tree(db=db)
etag_value = etag_for(json.dumps(payload, default=str).encode())

if if_none_match and if_none_match == etag_value:
    return Response(status_code=304)

return Response(
    content=json.dumps(
        CategoryTreeResponse.model_validate(payload).model_dump(mode="json"),
        default=str,
    ),
    media_type="application/json",
    headers={"ETag": etag_value},
)
```
Key decisions:
- `If-None-Match` is received via `Header(alias="if-none-match")` (lowercase — HTTP headers
  are case-insensitive; FastAPI's Header normalises). NOT via `Query`.
- Must return raw `Response` (not Pydantic model directly) to set the ETag header.
- `json.dumps(payload, default=str)` handles UUID / Decimal in the dict before encoding.

### FastAPI `Query` default-in-Annotated pitfall
Placing `Query(default=None, ...)` INSIDE `Annotated[..., Query(...)]` AND `= None` OUTSIDE
causes `AssertionError: Query default value cannot be set in Annotated`. Fix: put `default`
only in the `= None` assignment, not in `Query(...)`:
```python
# WRONG:
q: Annotated[str | None, Query(default=None, max_length=100)] = None
# CORRECT:
q: Annotated[str | None, Query(max_length=100, description="...")] = None
```

### service.py parameter shape confirmed (D1)
Services-builder returns plain `dict` payloads. All 5 endpoint-mirror service methods
accept `db: AsyncSession` as a **positional kwarg**:
  `suggest_categories(user_id, q, db)` — not `db=db` but we pass as keyword
  `browse_categories(q, super_id, limit, offset, db)`
  `get_category_tree(db)`
  `fetch_schema(category_id, db)`
  `get_field_enum(category_id, field_name, db)`
Router always calls with `db=db` keyword to be safe.

### SchemaResponse.fields — dict[str, Any] not list[FieldSpec]
Follows customer schemas precedent: `FieldSpec` is `typing.TypedDict`; Pydantic v2 on
Python 3.11 can't generate proper JSON schema from nested TypedDict. Use `list[dict[str, Any]]`
at the Pydantic layer. `test_per_field_shape_keys.py` is the conformance gate.

### 3 integration tests re: skip condition
`test_category_smart_picker_to_schema_flow`, `test_category_browse_to_schema_flow`,
`test_category_etag_roundtrip` — these skip on:
  1. categories table having no rows (needs seeded DB + dev tunnel)
  2. Previously: also skipped on router 404
Now the router is live, so condition 2 is cleared. They will fully pass once
the dev tunnel + seeded categories DB is available.

### Endpoint inventory (§9 — 5 endpoints, all GET, all auth-required)
| Method | Path | Rate limit | ETag |
|---|---|---|---|
| GET | /api/v1/categories/suggest | @rate_limit(smart_picker, 100, 3600) | no |
| GET | /api/v1/categories/browse | none (per-IP floor) | no |
| GET | /api/v1/categories | none (per-IP floor) | YES |
| GET | /api/v1/categories/{id}/schema | none (per-IP floor) | YES |
| GET | /api/v1/categories/{id}/field-enum/{name} | none (per-IP floor) | no |

### Files touched
- `backend/app/modules/category/schemas.py` (CREATED)
- `backend/app/modules/category/router.py` (CREATED + ruff-fixed)
- `backend/app/modules/category/__init__.py` (MODIFIED — preserves picker docstring)
- `backend/app/main.py` (MODIFIED)
- `backend/tests/test_app_boot_integration.py` (MODIFIED — 15→20)

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| §9 category routes 2026-06-07 | project | 5 endpoints + 7 boot tests PASS |
| ETag Header pattern | reference | Use Header(alias="if-none-match") + raw Response with headers= |
| Query default-in-Annotated pitfall | reference | Don't set default in Query() when = default outside Annotated |
| SchemaResponse.fields dict pattern | reference | TypedDict compat → dict[str, Any] for Python 3.11 |

## §10 catalog — CONSTRUCTED 2026-06-07 (sub-session 1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §10 catalog 6 endpoints | reference | POST /products (201); PATCH /products/{id}; POST /products/{id}/autofill; GET /products/{id}/preview; DELETE /products/{id} (204); GET /products/{id}/draft (200 OR 204) |
| §10 X-Autosave header pattern | reference | `Header(alias="x-autosave")` → `_is_autosave(header)` accepts {"true","1","yes"} (case-insensitive); absent OR any other → False |
| §10 autofill audit | reference | router-level `@audit_event("catalog.autofill.invoked")`; PII compromise = SHA-256(description) + 200-char preview lives in service.description_sha256 helper |
| §10 5 distinct path keys (boot integration) | reference | PATCH+DELETE share /products/{id} → 1 path key in _route_map; integration test expects 25 total now (was 20) |
| §10 audit decorators (4 writes, 2 reads) | reference | writes: product.created/updated/deleted + autofill.invoked; reads (preview + draft): NO @audit_event per MVP_ARCH §11.3 read-flood rule |
| §10 rate_limit shapes | reference | create_product 20/h user; product_patch 600/h IP (autosave-friendly); ai_autofill 50/h user; product_preview 600/h IP; product_delete 60/h user; product_draft_read 600/h IP |
| §10 catalog.draft 204 path | reference | router branches on `service.get_draft` returning None → `Response(status_code=204)`; no envelope (per RFC 7231 §6.3.5) |
| §10 PatchProductRequest model_validator | reference | rejects empty body (both `fields` and `status` None) via @model_validator(mode="after") raising ValueError → 422 envelope through §4.F handler |

## §11 image router — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-11-image-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §11 image router (2 endpoints) | reference | POST /api/v1/products/{id}/images — 202 ACCEPTED, multipart/form-data (UploadFile + Form idx), @rate_limit(scope="image_upload", limit=10, window=60), @audit_event("image.upload.received"); GET /api/v1/products/{id}/images — 200 OK, @rate_limit(scope="image_list", limit=600, window=3600), NO audit (read-only polling) |
| §11 image schemas (3 models) | reference | ImageUploadResponse {image_id, gcs_path, status="pending", idx 1-4, enqueued_task_id}; ImageSummary {image_id, idx, status, signed_url, precheck_jsonb, is_front, width, height, color_space, created_at}; ImagesListResponse {images: list[ImageSummary]} — extra="forbid" on all |
| §11 idx Form() coercion (route-layer fail-fast) | reference | FastAPI Form() default cannot enforce [1,4] range; router fails fast with InvalidImageIdxError BEFORE catalog.assert_product_ownership round-trip — saves DB query on malformed clients; service ALSO re-validates as defence-in-depth |
| §11 multipart upload pattern | reference | file: Annotated[UploadFile, File(description=...)], idx: Annotated[int, Form(description=...)] = 0 — V1 direct multipart through FastAPI; V1.5 may move to direct-to-GCS PUT per §11.M + MVP_ARCH §10.8 |
| §11 boot test route count: 27 → 31 actual | reference | test_app_boot_integration expects 27 distinct path keys (1 image path shared POST + GET); actual app.routes is 31 because each (path, method) is its own APIRoute object — _route_map() helper deduplicates by path key |

## §12 pricing — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-12-pricing-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §12 pricing router (1 endpoint) | reference | POST /api/v1/products/{id}/price-calc — 200 OK; @rate_limit(scope="price_calc", limit=600, window=3600) per-IP only (typing-rapid-iteration UX); @audit_event("pricing.calculated"); NO plan_guard per §12.I (pricing is one of 3 V1 modules excluded with customer + dashboard) |
| §12 pricing schemas (3 Pydantic v2) | reference | PriceCalcRequest{input_cost gt=0, target_margin_pct ge=0 le=500 default=30, override_commission_pct V1.5+ ignored, override_gst_pct V1.5+ ignored}; PriceCalcAlert{code Literal LOW_MARGIN/HIGH_MRP_MULTIPLIER/THIN_PROFIT, message_id, severity warning/info}; PriceCalcResponse{mrp/meesho_price/seller_price/commission_pct/commission_amount/gst_pct/gst_amount/profit/profit_pct + alerts list + calculated_at} — all Decimal, all 2 dp, ConfigDict(extra="forbid") on request |
| §12 boot test route count: 25 → 27 | reference | folded in §11 image cleanup (image dispatch had not updated boot test); added /api/v1/products/{id}/images + /api/v1/products/{id}/price-calc to allowed_paths; expected_count 25 → 27 (+1 image +1 pricing) |
| §12 use_live_valkey fixture chain pattern | reference | pricing module tests + integration tests must include `use_live_valkey` fixture arg even though pricing does NOT use Valkey directly — required for pytest-asyncio loop_scope="function" propagation. Without it, fixtures default to session loop scope per asyncio_default_fixture_loop_scope=session in pytest.ini, but test runs in function loop → asyncpg cross-loop Future binding error. Same fix as §8 customer cross-loop discovery. |

## §14 export — routes CONSTRUCTED 2026-06-08 (sub-session: meesell-backend-construction-14-export-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §14 export 2 endpoints | reference | POST /api/v1/products/{product_id}/export-xlsx (202 ACCEPTED); GET /api/v1/exports/{export_id} (200 OK). Path templates use {product_id} and {export_id} (NOT {id} — distinct param names to avoid FastAPI path collision with §10 catalog's {id}) |
| §14 schemas (4 Pydantic v2) | reference | ExportRequest{format Literal, extra="forbid", default="xlsx_with_images"}; ExportInitiatedResponse{export_id, status="pending", enqueued_task_id, initiated_at}; ExportResponse{export_id, product_id, status, format, xlsx_signed_url, zip_signed_url, error_message, error_code, initiated_at, completed_at, round_trip_validated — all Optional with None defaults}; ExportStatusSummaryResponse (V1.5 dashboard surface) |
| §14 rate_limit (1 endpoint only) | reference | POST export-xlsx: @rate_limit(scope="export_initiate", limit=10, window=3600); GET exports/{id}: NO decorator (per-IP fallback only — polling endpoint per §14.J) |
| §14 audit_mw posture | reference | POST export-xlsx: NO @audit_event decorator — audit_mw emits "export.initiated" automatically on 2xx POST per §4.G. GET exports/{id}: NO audit event (read-only polling, documented absence) |
| §14 plan_guard | reference | NOT participating in V1 per §14.A/§14.J — exports are core seller value |
| §14 M10 enforcement | reference | meesho_column_header / meesho_column_index / enum_codes_map confirmed ABSENT from schemas.py and test_router.py. These 3 symbols belong ONLY to domain.py/service.py/tasks.py |
| §14 boot test route count | reference | 29 distinct paths (was 27 after §13). +2 new path keys: /api/v1/products/{product_id}/export-xlsx AND /api/v1/exports/{export_id}. The {product_id} template does NOT collide with §10/{id} because FastAPI treats them as separate path segments after the /export-xlsx suffix |
| §14 services-builder parallel dispatch | reference | services-builder ran in parallel and overwrote the stub service.py with full implementation during this session. The router imports `from app.modules.export import service as export_service` and calls `export_service.initiate_export(user_id, product_id, request, db)` + `export_service.get_export(user_id, export_id, db)` |
| §14 self-contained fixture pattern | reference | export_client fixture follows test_customer_routes.py precedent: creates ephemeral DB schema (NullPool), overrides get_db + get_valkey_otp via dependency_overrides, patches audit_mw.AsyncSessionLocal + shared.valkey._cache_client at module level, seeds OTP at CORE_TEST_VALKEY_URL/0, obtains Bearer token via /otp/verify. Unauth tests use bare unauth_client (no Valkey needed — auth middleware rejects before any service call) |
| §14 test_router.py 9 tests | reference | 1 unauth POST 401, 2 wrong-user 404, 3 invalid-format 422, 4 happy 202 — for POST; 5 unauth GET 401, 6 not-found 404, 7 pending 200, 8 ready 200 (signed URLs), 9 failed 200 (error fields) — for GET. All 9 PASS |

## §13 dashboard — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-13-dashboard-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §13 dashboard router (1 endpoint) | reference | GET /api/v1/products — 200 OK; @rate_limit(scope="dashboard_list", limit=600, window=3600); NO @audit_event (read-only per §13.B + §4.G); NO plan_guard (§13.I lock — dashboard is one of 3 plan_guard-excluded modules alongside customer + pricing); Depends(get_current_user) + Depends(get_db); page/limit as Annotated[int, Query(...)] inline |
| §13 dashboard schemas (4 Pydantic v2) | reference | DashboardQuery {page ge=1 default=1, limit ge=1 le=100 default=20} extra="forbid"; ProductListItem {product_id, name nullable, category_id, status Literal["draft","ready"], created_at, updated_at} extra="ignore"; ProfileCompletenessSummary {base_complete_count, base_total_count, extension_complete_count, extension_total_count, onboarding_complete} extra="ignore"; DashboardResponse {products, total, page, limit, onboarding_completeness} extra="ignore" |
| §13 path co-location with §10 catalog | reference | GET /api/v1/products (dashboard) shares path key /api/v1/products with POST /api/v1/products (§10 catalog). FastAPI registers as 2 distinct APIRoute objects under 1 path key. The _route_map helper deduplicates by path → distinct path count stays at 27. Added new test_dashboard_get_products_route_mounted that inspects app.routes directly (not via _route_map) to confirm both GET and POST coexist |
| §13-DASHBOARD-D1 rate_limit keying | feedback | rate_limit decorator has no key="ip" param; per-route keying is automatic via request.state.user_id for authenticated routes (TenancyContextMiddleware). §13.I locked spec calls for per-IP fallback only, but V1 decorator only supports per-user keying for authed routes. Matches §7 D2, §8 D5, §10 D2 precedent. **Why**: V1 decorator limitation; **How to apply**: per-user keying is the safer default — one IP carrying multiple sellers shares a higher limit. V1.5 decorator enhancement for true per-IP keying on per-route bucket |
| §13-DASHBOARD-D2 GET /products path co-location | feedback | GET /api/v1/products is owned by §13 dashboard, NOT §10 catalog (per §2.7 ownership lock). Boot integration test docstring rewritten to make this clear. **Why**: §2.7 lock explicit — "catalog owns CREATE/PATCH/AUTOFILL/PREVIEW/DELETE/DRAFT-RECOVER but not the LIST"; **How to apply**: when reading the route map, /api/v1/products carries 2 method sets — POST is catalog (create), GET is dashboard (list) |
| §13 boot test route count: 27 (unchanged) | reference | distinct path count stays at 27 because GET /api/v1/products shares the path with the already-mounted POST. Raw APIRoute count rises from 26 to 27 (+1 new APIRoute object for the GET endpoint). expected_count assertion unchanged |
| §13 path NO repository pattern | reference | dashboard subtree has 5 source files: __init__, router, service, schemas, domain (empty), exceptions. NO repository.py — structural §13.D + §3.C deviation locked since 2026-06-05. §19 CI linter must allowlist dashboard as documented exception to per-module subtree completeness check |
| §13 i18n key already registered (Wave 1 §5A) | reference | "validation.dashboard.invalid_pagination" already in app/i18n/messages_en.py from §5A.I pre-commitment; no new key added by §13 construction. InvalidPaginationError defined in dashboard/exceptions.py for parity with §13.G surface even though Pydantic Field constraints catch all V1 cases before raising |


## Per-feature memory > smart-picker

- [feature_smart_picker_route-flag-guard.md](feature_smart_picker_route-flag-guard.md) — 2026-06-11: FEATURE_SMART_PICKER_ENABLED flag added to config.py; guard in router.py suggest_categories; §9.E/§9.G conformance verified (no drift); 5 smoke tests PASS; commit 6a107ca on feature/smart-picker/backend

---

## Session: 2026-06-11 — CI Gate-1 pytest-collection fix

### Task summary
Executed spec_ci_gate1_fix.md STEP 2 of 3. Added `pythonpath = .` to `backend/pytest.ini` to fix `ModuleNotFoundError: No module named 'app'` at pytest collection in CI Gate 1.

### Root cause (precise)
CI runs `pytest -m "unit" -v` (not `python -m pytest`). The direct `pytest` invocation does NOT add CWD to sys.path. `python -m pytest` would add CWD via the `-m` module mechanism. Since there is no `tests/__init__.py` and no `tests/modules/__init__.py`, importmode=prepend inserts `tests/` or `tests/modules/` (not `backend/`), and `app/` is unreachable. Fix: `pythonpath = .` in pytest>=7.0 prepends rootdir (= backend/) before any collection.

### Key distinction to remember
- `pytest` script directly: CWD NOT on sys.path
- `python -m pytest`: CWD IS on sys.path (Python -m adds it)
- CI uses the former; local venv users often run the latter — explains why CI failed but local seemed ok

### BEFORE/AFTER reproducibility
BEFORE: Use a throwaway venv (no .pth for the project), install deps, run `pytest` directly from backend/. Gets exit code 4 + `ModuleNotFoundError: No module named 'app'` at conftest.py:37.
AFTER: Same command → `FATAL: required env var(s) empty or unset` (app config validation, not collection error). Exit code 1 (app's own guard). `No module named 'app'` gone.

### Worktree pattern
Branch: `fix/ci-gate1-pytest-collection` at `/tmp/mesell-wt/ci-gate1-fix`
PR: #74, base: develop. Not merged — STEP 3 is coordinator.

### Files touched
- `backend/pytest.ini` (MODIFIED — 7 lines added after addopts: comment + `pythonpath = .`)
- `docs/status/STATUS_BACKEND.md` (MODIFIED — UPDATE block appended)

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| CI Gate-1 fix 2026-06-11 | project | pythonpath=. in pytest.ini; PR #74 open for coordinator STEP 3 |
| pytest direct vs python -m | reference | Direct pytest does NOT add CWD to sys.path; python -m pytest does. CI uses direct. |
| pythonpath ini key | reference | pytest>=7.0 feature; additive to §19.D-locked config; no founder flag needed per coordinator ruling |

---

## Session: 2026-06-11 — catalog-form backend slice G4 + G6 (HYBRID STEP 2b)

### Task summary
Authored the `/autofill` 404 flag guard (G4) and two test files (G6 routes-builder half):
`backend/tests/unit/test_catalog_routes.py` (7 tests) + `backend/tests/integration/test_ai_autofill_integration.py` (5 tests).

### G4 guard implementation (locked pattern)

File: `backend/app/modules/catalog/router.py`

New imports added:
```python
from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.shared.config import settings
```

Guard inside `autofill_product` handler (first statement, after FastAPI resolves auth dep):
```python
if not settings.FEATURE_AI_AUTOFILL_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="AI Auto-fill is disabled in this environment",
    )
```

This EXACTLY matches the smart-picker pattern in `category/router.py:117` (canonical guard for all feature-flagged routes in MeeSell V1).

### Guard pattern rule (locked)
- Import `settings` at module level (`from app.shared.config import settings`).
- Read `settings.FEATURE_XXX` inside the handler body (not as a default argument or module-level constant).
- This makes the guard monkeypatch-friendly: `monkeypatch.setattr(_config_module.settings, "FEATURE_XXX", False)` works per-request because the attribute read happens at call time, not at import time.
- Pattern reference: `app/modules/category/router.py:68` (import) + `:117` (guard).

### Unit route test pattern (G6 novelty)

The `/autofill 404 when disabled` test requires auth to succeed (otherwise auth rejects first and you get 401 instead of 404). Pattern:
```python
from app.core.auth import CurrentUser, get_current_user
fake_user = CurrentUser(user_id=uuid4(), plan="free")  # CurrentUser has ONLY user_id + plan (not phone)

async def _fake_auth():
    return fake_user

_production_app.dependency_overrides[get_current_user] = _fake_auth
# ... test ...
_production_app.dependency_overrides.pop(get_current_user, None)  # ALWAYS restore in finally
```

For the "flag=True → service enters → assert not 404" test, also override `get_db` to prevent DB hit, and monkeypatch the first service method (e.g. `assert_product_ownership`) to raise a known non-404 exception (e.g. 403) so you can distinguish "flag guard 404" from "service 404":
```python
from app.shared.database import get_db

async def _fake_db():
    yield AsyncMock()

_production_app.dependency_overrides[get_db] = _fake_db
```

### CurrentUser shape (CRITICAL)
`CurrentUser` is a frozen dataclass with ONLY 2 fields:
```python
@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    plan: Literal["free"]
```
NO `phone` field. Discovered during test run — TypeError otherwise.

### Integration test seed gotchas (CRITICAL — VARCHAR limits)
When seeding `templates` + `categories` in integration tests:
- `templates.parser_version`: `VARCHAR(8)` — use <= 8 chars (e.g. `"af1.0"`, NOT `"autofill-integ-1.0"`)
- `categories.meesho_leaf_id`: `VARCHAR(16)` — use <= 16 chars (e.g. `"AF-INTEG-001"`, NOT `"AUTOFILL-INTEG-001"`)
- `categories.super_id`: `VARCHAR(8)` — use <= 8 chars (e.g. `"99"`)
- `categories.super_name`: `VARCHAR(64)` — fine for typical test names
- `templates.schema_hash`: `String(64)` — fine for typical test hashes
- `categories.path`: `Text` — no limit
- `categories.leaf_name`: `String(255)` — fine

Ref: see dashboard integration test `test_dashboard_list_flow.py` pattern (uses `parser_version="dash1.0"`).

### Integration test mock boundary (ai-autofill)
Mock at `catalog_service.ai_client.call_gemini` (the module-qualified reference inside the catalog service). Also stub `catalog_service.enforce_plan_limit` if running without a live Valkey:
```python
async def _fake_call_gemini(ctx, prompt_id, *, prompt_vars, allowed_enums):
    return SimpleNamespace(parsed={"fields": {"fabric": "Cotton"}, "fallback_offered": False})

monkeypatch.setattr(catalog_service.ai_client, "call_gemini", _fake_call_gemini)

async def _noop_plan_guard(*args, **kwargs):
    return None

monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_guard)
```

### Test results
- Unit tests/unit: 37/37 PASS (30 pre-existing from services-builder + 7 new route tests)
- Integration test_ai_autofill_integration.py: 5/5 PASS (substrate available on laptop)
- Ruff: all clean, line-length 100

### Files touched
- `backend/app/modules/catalog/router.py` (MODIFIED — G4 flag guard + 2 imports)
- `backend/tests/unit/test_catalog_routes.py` (CREATED — 7 unit tests)
- `backend/tests/integration/test_ai_autofill_integration.py` (CREATED — 5 integration tests)
- `docs/status/STATUS_BACKEND.md` (MODIFIED — UPDATE block appended)

### Git commits (on feature/catalog-form/backend)
- 2678040 feat(catalog): /autofill 404 flag guard — catalog-form backend slice G4
- 79ae93d test(catalog): route + autofill integration tests — catalog-form backend slice G6
- Pushed to origin/feature/catalog-form/backend

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| catalog-form G4 flag guard 2026-06-11 | project | /autofill 404 guard added; router.py:~218; matches smart-picker pattern; settings read at request-time |
| Feature flag guard pattern (locked) | reference | `if not settings.FEATURE_XXX: raise HTTPException(404)`; import settings at module level; read inside handler body — NOT as default arg |
| CurrentUser shape (locked) | reference | Frozen dataclass: ONLY user_id + plan — no phone field |
| Route test auth-bypass pattern | reference | dependency_overrides[get_current_user] = lambda: fake_user; always pop in finally |
| Integration seed VARCHAR limits | reference | parser_version VARCHAR(8); meesho_leaf_id VARCHAR(16); super_id VARCHAR(8) — use short strings |
| Integration mock boundary (ai) | reference | monkeypatch catalog_service.ai_client.call_gemini + catalog_service.enforce_plan_limit |

---

## Session: 2026-06-11 — image-precheck backend slice G1/G2

### Task summary
Added FEATURE_IMAGE_PRECHECK_ENABLED flag (G1) and router gates (G2) for the
image precheck feature. The image module was already fully built on develop;
this session adds the 2 missing feature-flag surfaces only.

### G1 config addition (config.py)
Added to `backend/app/shared/config.py` adjacent to FEATURE_SMART_PICKER_ENABLED:
```python
FEATURE_IMAGE_PRECHECK_ENABLED: bool = True
```
Same dev-true/staging-false comment posture; references FEATURE_PLAN.md D2 + 3 staging gates.

### G2 POST guard (router.py upload_image handler)
```python
if not settings.FEATURE_IMAGE_PRECHECK_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Image upload is disabled in this environment",
    )
```
Placed at TOP of handler, BEFORE idx validation and BEFORE service call.

### G2 GET guard (router.py list_images handler)
```python
if not settings.FEATURE_IMAGE_PRECHECK_ENABLED:
    return ImagesListResponse(images=[])
```
Placed at TOP of handler, BEFORE service call. Returns 200 + empty list (NOT 404) —
read-only endpoint; sellers may have legacy images. Per D2: do NOT 404 the GET.

### ImageSummary required fields gotcha
`signed_url: str` and `created_at: datetime` are NON-OPTIONAL in the as-built schema.
When constructing sentinel ImageSummary in tests: must provide a real string URL and
a real datetime (timezone-aware). Cannot pass None.

### Flag gate test pattern (image-specific)
- stub auth via `dependency_overrides[get_current_user] = _stub_get_current_user`
- patch at `app.modules.image.router.settings` (module-qualified, not `app.shared.config.settings`)
- POST uses multipart: `files={"file": ...}, data={"idx": "1"}`
- GET uses stub service return to distinguish "flag guard empty" from "service empty"
- Env vars required for FATAL check: all 13 REQUIRED_FIELDS must be set (use test-sentinel values)

### Files touched
- `backend/app/shared/config.py` (MODIFIED — G1 flag)
- `backend/app/modules/image/router.py` (MODIFIED — G2 POST + GET guards + imports)
- `backend/tests/modules/image/test_flag_gate.py` (NEW — 4 tests)

### Test results
- 4/4 new flag-gate tests PASS
- 11/11 tests/modules/image/ standalone (4 new + 7 pre-existing) PASS
- Ruff: clean
- Commits: 4444dce (feat) + de96aca (test) on feature/image-precheck/backend, pushed

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| image-precheck G1/G2 2026-06-11 | project | flag + router gates + 4 tests PASS; 2 commits pushed |
| ImageSummary non-optional fields | reference | signed_url:str and created_at:datetime are required (no None) |
| Flag gate test env setup | reference | All 13 REQUIRED_FIELDS must be set (even test-sentinel) for config to pass |
| GET-when-flag-OFF = 200+empty NOT 404 | reference | D2 contract: list endpoint is read-only; sellers may have legacy images |

---

## Features in flight

| Feature slug | Status | Last entry | Files |
|---|---|---|---|
| image-precheck | COMPLETE (HYBRID STEP 2) | 2026-06-11 | feature_image_precheck_session_1_handoff.md |
| catalog-form | COMPLETE (MERGED) | 2026-06-11 | (merged to develop) |
| smart-picker | COMPLETE (MERGED) | 2026-06-11 | feature_smart_picker_route-flag-guard.md |

---

## Session: 2026-06-12 — xlsx-export backend slice G1/G2/G3

### Task summary
Added FEATURE_XLSX_EXPORT_ENABLED flag (G1), POST gate in export router (G2), and
flag-404 integration test (G3) for V1 Feature 9 (XLSX Export).

### G1 config addition (config.py:184+)
Added to `backend/app/shared/config.py` after FEATURE_SMART_PICKER_ENABLED:
```python
FEATURE_XLSX_EXPORT_ENABLED: bool = True
```
D2 staging-gate note: dev True / staging False until 15 golden fixtures x3 consecutive
runs + manual Meesho supplier-panel upload accepted.

### G2 POST gate (export/router.py initiate_export handler)
```python
if not settings.FEATURE_XLSX_EXPORT_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="XLSX export is disabled in this environment",
    )
```
Placed at TOP of handler, BEFORE export_service call.
R1 RULING: GET /exports/{id} is NOT gated — in-flight export polls must keep working.
Imports added: `HTTPException` from fastapi + `settings` from app.shared.config.

### G3 flag-404 test pattern (export-specific)
- Fixture: `stub_export_client` — overrides get_current_user only; no DB/Valkey.
- Patch surface: `app.modules.export.router.settings` (NOT `app.shared.config.settings`).
- Test 4 (R1 verification): asserts GET /exports/{id} body.detail != guard string even
  when flag=False — confirms guard is absent from GET handler.
- 4/4 PASS standalone; 1 harmless ResourceWarning (unawaited coroutine in teardown
  path for `get_valkey_otp` — same class as other flag-gate tests; not our code).

### R1 ruling pattern (POST-only flag gate)
When FEATURE_PLAN D2 says "POST 404 when disabled; GET stays UNGATED":
- Add guard ONLY to the POST handler.
- Do NOT add guard to the GET handler.
- Add a test (test 4) that explicitly verifies the GET is NOT blocked.
This pattern is now locked for any future export-class feature with inflight-poll GET.

### Existing export test status (pre-existing infra-gated)
39/46 collected tests PASS standalone. 7 errors in test_router.py are ALL
OSError port 5433 (dev-tunnel absent) — pre-existing infra-gated condition,
not regressions from G1/G2. Gate-5 golden runner collects 18 tests cleanly.

### Files touched
- `backend/app/shared/config.py` (MODIFIED — G1 flag)
- `backend/app/modules/export/router.py` (MODIFIED — G2 imports + POST guard)
- `backend/tests/integration/test_export_flag_404.py` (NEW — G3, 4 tests)
- `docs/status/STATUS_BACKEND.md` (MODIFIED — UPDATE block appended)

### Git commits (on feature/xlsx-export/backend)
- 9a10a25 feat(export): FEATURE_XLSX_EXPORT_ENABLED flag + POST gate — xlsx-export backend slice G1/G2
- afdcaff test(export): flag-404 test — G3
- Pushed to origin/feature/xlsx-export/backend

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| xlsx-export G1/G2/G3 2026-06-12 | project | flag + POST gate + 4 tests PASS; 2 commits pushed |
| R1 POST-only gate pattern | reference | GET poll endpoint NOT gated; test 4 verifies absence |
| Export flag-404 test 4 (R1) | reference | assert body.detail != guard-string on GET when flag=False |

### Gate outcome (coordinator STEP 3 — 2026-06-12)
- Coordinator merge-gate: PASS. PR #139 OPEN (feature/xlsx-export → develop, founder gate).
- Squash SHA: d885daf on feature/xlsx-export. Sub-ref feature/xlsx-export/backend DELETED (204).
- All 3 gaps adjudicated PASS: G1 config, G2 POST guard, G3 4/4 test.
- Infra inter-lead request OPEN: meesell-infra-builder to wire FEATURE_XLSX_EXPORT_ENABLED into ConfigMaps.
- Founder queue: merge PR #139; R2 FYI (runner name drift, no action); PR #115 still pending.

---

## Session: 2026-06-12 — flag-parity sweep G1/G2/G3 (chore/flag-parity)

### Task summary
Wired 3 missing V1 feature flags + in-handler route guards + flag-404 tests.
Branch: chore/flag-parity (worktree /tmp/mesell-wt/flag-parity).
9 tests across 3 files — all PASS. 2 commits pushed.

### G1 price-calculator (pricing/router.py)
Added `FEATURE_PRICE_CALCULATOR_ENABLED: bool = True` to config.py §3.2 after FEATURE_AI_AUTOFILL_ENABLED.
Added `HTTPException, status` + `settings` imports to pricing/router.py (were absent).
In-handler guard BEFORE service call:
```python
if not settings.FEATURE_PRICE_CALCULATOR_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Price Calculator is disabled in this environment",
    )
```
Test file: tests/modules/pricing/test_feature_flag.py (3 tests, @unit marker).
Patch surface: `app.modules.pricing.router.settings`.

### G2 dashboard (dashboard/router.py)
Added `FEATURE_TRACKING_DASHBOARD_ENABLED: bool = True` to config.py §3.2.
Added `HTTPException, status` + `settings` imports to dashboard/router.py.
In-handler guard BEFORE service call. R1 RULING: GET/read endpoint gets 404 — the read IS the feature
(D3 kill-switch). Guard comment explains this divergence from "writes only get 404" convention.
Test file: tests/modules/dashboard/test_feature_flag.py (3 tests, @unit marker).
Patch surface: `app.modules.dashboard.router.settings`.

### G3 live-preview (catalog/router.py)
Added `FEATURE_LIVE_PREVIEW_ENABLED: bool = False` to config.py §3.2.
DEFAULT FALSE — the ONLY V1 flag that ships default-False; all others default True.

CRITICAL JUDGMENT CALL: HTTPException does NOT carry a custom `code` field.
The _http_exception_handler in core/errors.py always sets `code = f"http.{exc.status_code}"`.
To emit the spec-required `{"code": "feature.live_preview.disabled"}`, must use MeesellError directly.
MeesellError.__init__ accepts `code: str | None` as a per-instance override.
Pattern used:
```python
from app.core.errors import MeesellError
# ...
if not settings.FEATURE_LIVE_PREVIEW_ENABLED:
    raise MeesellError(
        code="feature.live_preview.disabled",
        status_code=404,
        detail="Preview unavailable",
    )
```
This goes through _meesell_error_handler which emits the §4.F envelope with `code = "feature.live_preview.disabled"`.
R3 RULING HONORED: no new core/feature_flags.py; MeesellError is the codebase's existing coded-error mechanism.

Test file: tests/integration/test_live_preview_flag_404.py (3 tests; no @unit marker — placed in integration/).
R4: test_preview_returns_404_with_default_flag does NOT patch the flag — default IS False, so 404 is the default.
The `code` field is verified explicitly: `assert body.get("code") == "feature.live_preview.disabled"`.

### HTTPException vs MeesellError for coded errors — decision table (LOCKED PATTERN)
| Need | Use |
|---|---|
| Simple 404 flag guard (no custom code) | HTTPException(status_code=404, detail="...") |
| Coded 404 flag guard (custom code field) | MeesellError(code="...", status_code=404, detail="...") |
The _http_exception_handler hardcodes `code = "http.{status_code}"`. Only MeesellError escapes this.

### Config comment style (locked for §3.2 flag block)
```
# FEATURE_XYZ_ENABLED: dev default True/False; staging default False
# (staging gate conditions from FEATURE_PLAN.md Decision D2 or D3).
# Route path returns 404 when False per Master Plan §3.2 backend protocol.
# Note if default False: DEFAULT FALSE — the only / one of few V1 flags that ships default-False.
FEATURE_XYZ_ENABLED: bool = True/False
```

### Pre-existing reds observed
None encountered in isolation runs. (Gate-1 unit RED on develop tip is pre-existing per D-2 note
in audit memo — not caused by this sweep.)

### Commits
- a61c864 feat(flags): price-calc + dashboard + live-preview flags + guards — flag-parity G1/G2/G3
- 41b654d test(flags): flag-404 tests x3 — flag-parity G1/G2/G3
- Pushed to origin/chore/flag-parity

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| flag-parity sweep 2026-06-12 | project | G1/G2/G3: 3 flags + 3 guards + 9 tests; 2 commits pushed on chore/flag-parity |
| HTTPException vs MeesellError for coded errors | reference | Use MeesellError when spec requires custom `code` field; HTTPException always emits `code="http.N"` |
| FEATURE_LIVE_PREVIEW_ENABLED default-False | reference | ONLY V1 flag that ships default-False; test 1 verifies default WITHOUT patching the flag |
| R1 GET-route 404 (dashboard kill-switch) | reference | dashboard list_products IS the feature — R1 mandates 404 on GET, not just writes |

---

## Session: 2026-06-12 — Gate-4 cross-loop contamination fix (fix/gate4-loop-contamination)

### Task summary
Fixed 6 FAILED + 13 ERROR integration tests unmasked by PR #150 (Gate-1 event-loop fix).
Root cause: `iam_client` fixture had `loop_scope="function"` but NO `get_db` override —
routes resolved `Depends(get_db)` against the app-global `AsyncSessionLocal`, whose asyncpg
pool was bound to the session loop. Function-scoped tests get their own loop → `RuntimeError:
got Future attached to a different loop`. Starlette's `BaseHTTPMiddleware` + anyio TaskGroup
wrapped this as an ExceptionGroup that bypassed test assertions.

Secondary root cause (13 ERRORs): `app.state.db_engine` (pooled, `pool_pre_ping=True`) created
by lifespan schedules asyncpg pool callbacks via `loop.call_soon()`. These fire AFTER the
function loop teardown → `Event loop is closed` teardown errors.

### Authoritative spec
`.claude/agent-memory/meesell-backend-coordinator/spec_ci_gate4_loop_contamination.md`
on branch `origin/docs/gate1-resolved-gate4-spec` (locked before this session).

### Files modified (test harness only — app/ untouched)

**1. `backend/tests/integration/conftest.py` — PRIMARY FIX (complete rewrite)**
- Old: 118 lines, iam_client had NO `get_db` override
- New: ~264 lines, mirrors `customer_client` / `export_client` twin pattern
- Key additions:
  - `_cleanup_users_by_phone_prefix(db_url)` — accepts explicit `db_url` param; uses NullPool
  - `iam_client` fixture: full NullPool engine + SAVEPOINT isolation + DI overrides
  - Patches: `audit_mw.AsyncSessionLocal`, `shared.valkey._cache_client`
  - Explicit lifespan-state disposal (see pattern below)
  - Provision-aware schema setup: skip drop_all/create_all when `TEST_DATABASE_URL` set
  - Phone prefix `+9155500` — non-routable Indian test numbers

**2. `backend/tests/test_shared_database.py` — MODIFIED**
- `test_get_db_yields_async_session`: patched `AsyncSessionLocal` with per-test NullPool
  session-maker instead of using app-global session-loop-bound engine.
- Added `create_async_engine` to SQLAlchemy import line.

**3. `backend/tests/test_customer_routes.py` — MODIFIED**
- Added lifespan-state tracking + explicit disposal after lifespan exits (inside async body).

**4. `backend/tests/modules/export/test_router.py` — MODIFIED**
- Same lifespan teardown hygiene applied to both `export_client` and `unauth_client` fixtures.

### Canonical iam_client fixture pattern (LOCKED)

```python
@pytest_asyncio.fixture(loop_scope="function")
async def iam_client():
    import redis.asyncio as _redis_lib
    db_url = _DEV_DATABASE_URL
    valkey_base = _valkey_base()

    # 1. NullPool engine (no Future binding)
    engine = create_async_engine(db_url, poolclass=NullPool, echo=False)
    _provisioned = bool(os.environ.get("TEST_DATABASE_URL"))
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    # 2. SAVEPOINT per-test isolation
    shared_conn = await engine.connect()
    outer_txn = await shared_conn.begin()
    TestSession = async_sessionmaker(
        bind=shared_conn, expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    # 3. FastAPI DI overrides
    app.dependency_overrides[get_valkey_otp] = _otp_override
    app.dependency_overrides[get_db] = _db_override

    # 4. Module-level singleton patches
    _audit_mw.AsyncSessionLocal = TestSession
    _valkey_module._cache_client = _redis_lib.from_url(f"{valkey_base}/3", ...)

    # 5. Pre-test cleanup (NullPool engine)
    await _cleanup_users_by_phone_prefix(db_url)

    # 6. Boot lifespan + yield + teardown
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            lifespan_db_engine = getattr(app.state, "db_engine", None)
            lifespan_valkey_client = getattr(app.state, "valkey", None)
            yield ac
        # CRITICAL: explicit disposal AFTER lifespan exits, WITHIN async body
        if lifespan_db_engine is not None:
            try: await lifespan_db_engine.dispose()
            except Exception: pass
        if lifespan_valkey_client is not None:
            try: await lifespan_valkey_client.aclose()
            except Exception: pass

    # finally: restore singletons, rollback outer_txn, dispose engine, pop overrides
```

### Double-dispose pattern (LOCKED for lifespan teardown hygiene)
When a fixture boots a FastAPI lifespan that creates a pooled engine (`app.state.db_engine`
with `pool_pre_ping=True`), you MUST explicitly dispose that engine AFTER the lifespan
exits but while still inside the fixture's async body (function loop active). This drains
pending asyncpg pool callbacks BEFORE the function loop is torn down. Without this,
`Event loop is closed` teardown errors fire on every test.

The same applies to `app.state.valkey` (async Redis client) — explicit `aclose()` needed.

Pattern:
```python
async with app.router.lifespan_context(app):
    lifespan_db_engine = getattr(app.state, "db_engine", None)
    lifespan_valkey_client = getattr(app.state, "valkey", None)
    yield ac
# Here: lifespan has exited its own dispose calls, but callbacks still pending
if lifespan_db_engine is not None:
    try: await lifespan_db_engine.dispose()  # drain asyncpg pool callbacks
    except Exception: pass
if lifespan_valkey_client is not None:
    try: await lifespan_valkey_client.aclose()
    except Exception: pass
```

### Gate-1 unmasks Gate-4 lesson
Removing a session-scope `event_loop` fixture (PR #150) correctly shifts all session-scoped
fixtures to the session event loop. This unmasks latent cross-loop contamination in any
fixture that did NOT override `get_db`. Lesson: every fixture that boots a FastAPI lifespan
MUST override `get_db` with a NullPool session-maker bound to the fixture's own loop, regardless
of whether it looks like it "works" with the session-scope fixture present.

### `_valkey_base()` helper — precedence chain
Strips trailing `/<db>` from Valkey URLs to prevent `/0/0` double-suffix.
Precedence: `TEST_VALKEY_URL > VALKEY_URL > CORE_TEST_VALKEY_URL > redis://localhost:6379`
Defined in `tests/conftest.py`. Import: `from tests.conftest import _DEV_DATABASE_URL, _valkey_base`

### `_DEV_DATABASE_URL` — precedence chain (LOCKED)
`TEST_DATABASE_URL > DEV_DATABASE_URL > baked K3s-dev DSN`
Defined in `tests/conftest.py`. Required by any test module that needs a per-fixture NullPool engine.

### Phone prefix convention
Every integration test uses `+9155500XXXXX` range — non-routable Indian SIM numbers.
Safe to DELETE-by-prefix at teardown. Hard-coded in `_INTEGRATION_PHONE_PREFIX`.

### Local env note (Gate-4 session)
Dev tunnel to postgres (port 5433) NOT available locally during this session.
Only Valkey on port 6379 available. Integration tests require live DB → CI is the
formal acceptance confirmation. Unit tests (634 passing) verified no regressions.
4 pre-existing unit failures on `origin/develop` baseline CONFIRMED pre-existing
(verified via git stash + baseline run before our changes).

### Worktree + PR
- Worktree: `/tmp/mesell-wt/gate4-fix/`
- Branch: `fix/gate4-loop-contamination`
- Commit SHA: `6c5941f`
- PR: #159 → develop (OPEN, awaiting coordinator STEP 3)

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| Gate-4 cross-loop fix 2026-06-12 | project | 4 test harness files fixed; PR #159 open for coordinator STEP 3 |
| NullPool + get_db override rule | reference | Every fixture that boots FastAPI lifespan MUST override get_db with NullPool session |
| Double-dispose lifespan teardown | reference | Explicit dispose()/aclose() after lifespan exits, while still in async body |
| Gate-1 unmasks Gate-4 lesson | reference | Removing session event_loop fixture reveals latent cross-loop contamination |
| _valkey_base() / _DEV_DATABASE_URL | reference | Imported from tests/conftest.py; precedence chains locked |
| Integration phone prefix | reference | +9155500XXXXX range; non-routable; safe for DELETE-by-prefix teardown |

---

## Session: 2026-06-12 — Gate-4 repair loop 1 (fix/gate4-loop-contamination, PR #159)

### Task summary
Repaired 3 defects (D1/D2/D3) rejected by coordinator's STEP 3 merge-gate.
PR #159 Gate-4 went from `5f/13e` to `180p/17s/0f/0e` (PASS). CI run 27394517680 GREEN.
Commits: 0059272 + b9d1557 on fix/gate4-loop-contamination.

### D1: SAVEPOINT on iam_client was a net regression
Root cause: split-engine tests (`test_customer_cross_module_eligibility`,
`test_customer_full_onboarding_flow`) create user via `iam_client` then read it back
via a SEPARATE NullPool engine on `os.environ["DATABASE_URL"]`. With SAVEPOINT isolation
the user row is inside an uncommitted outer transaction → invisible to the second engine
→ ForeignKeyViolationError.
Fix: remove SAVEPOINT from `iam_client`. Use plain commit-for-real `async_sessionmaker(engine)`.
The function-loop NullPool engine ALONE kills the cross-loop error; SAVEPOINT not needed for
iam_client because `_cleanup_users_by_phone_prefix` handles teardown.
Key distinction: `customer_client` / `export_client` CAN use SAVEPOINT because they are
self-contained (no split-engine pattern). `iam_client` MUST NOT use SAVEPOINT.

### D2: _otp_client module singleton bypasses DI — must patch explicitly
Root cause: `rate_limit_mw._check_window` calls `await get_valkey_otp()` as a plain
function (not through FastAPI DI). `dependency_overrides[get_valkey_otp]` has ZERO effect
on middleware. When test N's function loop closes, `_otp_client.connection._writer._transport._loop`
is the closed loop. Test N+1 fixture setup boots a new lifespan and the rate_limit_mw pipeline
call invokes `loop.call_soon(self._call_connection_lost, None)` on the closed loop →
`RuntimeError: Event loop is closed`.
Fix: patch `_valkey_module._otp_client` at module level in ALL fixtures that boot a lifespan
and make requests (including `unauth_client`!). Same pattern as `_cache_client` patching.
The `unauth_client` erroneously documents "does NOT require Valkey" — FALSE: rate_limit_mw
always runs before auth rejection in the middleware chain.
Affected fixtures: iam_client (integration/conftest.py), customer_client (test_customer_routes.py),
export_client (modules/export/test_router.py), unauth_client (modules/export/test_router.py).

### D3: G7 auto-apply test was stale at 2 assertion points
Root cause: G7 FOUNDER RULING 2026-06-11 (ai-autofill D1) removed auto-apply from
`autofill_product`. Service is correct (applied always False, writes only ai_suggestions_jsonb).
Two test assertions were stale:
1. `autofill_result.applied.get("product_name") is True` → `is False` (direct assertion)
2. `patch_product(status="ready")` fails with ValidationFailedError (3 compulsory fields empty)
   because G7 means autofill no longer writes to `fields_jsonb`.
Fix: (1) change `is True` → `is False`. (2) add a PATCH step that manually accepts the
suggested field values (simulates seller accepting autofill suggestions in UI), THEN transitions
to `status=ready`. Both fixes cite `BE-CATALOG-G7-AUTOAPPLY-1` in comments.
Lesson: when G7 (or any ruling) changes behavior, ALL downstream test steps that depended on
the OLD behavior must also be updated — not just the direct assertion.

### Key insight: always interrogate ALL assertions in a lifecycle test
When a ruling removes behavior (e.g. auto-apply), a multi-step test will cascade failures:
- Step N: assertion against the removed behavior → fixed
- Step N+2: downstream step that was predicated on step N's OLD behavior → also broken
Both must be fixed. Do not stop after fixing the first visible assertion.

### Rate limit middleware always runs before auth rejection
`AuthContextMiddleware` sets `request.state.user = None` — it does NOT short-circuit the
request. The 401 is raised inside the route handler's `get_current_user` dependency, which
runs AFTER all middleware. So `RateLimitMiddleware` always runs for every request, including
unauthenticated ones. Any fixture that boots the lifespan and makes ANY request must patch
`_otp_client`.

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| Gate-4 repair-1 COMPLETE 2026-06-12 | project | 5 files fixed; 2 commits; CI 27394517680 GREEN 180p/17s/0f/0e |
| SAVEPOINT vs commit-for-real | reference | iam_client MUST NOT use SAVEPOINT (split-engine); customer/export CAN. |
| _otp_client singleton patch | reference | ALL lifespan-booting fixtures must patch _otp_client; DI override alone insufficient |
| unauth_client also needs _otp_client patch | reference | rate_limit_mw runs before auth rejection; unauth requests hit _check_window |
| G7 cascade lesson | reference | Ruling that removes behavior breaks ALL downstream steps predicated on it; fix all |

## MS Sub-Plan A Phase B — svc-export router extraction (2026-06-12)

| Memory key | type | content |
| ---------- | ---- | ------- |
| svc-export router.py import path | reference | In extracted svc-export, service import is `from app import service as export_service` (NOT `from app.modules.export import service`) — the svc-export tree root IS the module |
| svc-export schemas.py import path | reference | `from app.schemas import ExportInitiatedResponse, ExportRequest, ExportResponse` (flat `app.schemas`, not `app.modules.export.schemas`) |
| FastAPI route.status_code = None for default 200 | reference | FastAPI only sets `route.status_code` when explicitly passed to the decorator. GET routes with implicit 200 have `route.status_code = None`. Assert `(route.status_code is None or route.status_code == 200)` for default-200 routes. |
| FastAPI dependant.dependencies ARE Dependant objects | reference | In FastAPI 0.115, items in `route.dependant.dependencies` are `Dependant` objects directly (NOT wrappers with `.dependant`). They have `.call` and `.dependencies`. Recurse on the child directly. |
| route.dependencies vs route.dependant.dependencies | reference | `route.dependencies` = decorator-level `dependencies=[Depends(...)]` only. `route.dependant.dependencies` = ALL parameter-level `Depends()`. To find `get_current_user`, walk `route.dependant.dependencies` recursively. |
| E402 in main.py mid-module imports | reference | Mid-module `from app.router import ...` after app construction (middleware must register first) raises E402 — fix with `# noqa: E402`, do NOT move to top. |
| svc-export test run command | reference | `PYTHONPATH=<worktree>/backend/services/svc-export <repo>/backend/.venv/bin/pytest tests/ -v` (monolith .venv has all deps incl. fastapi 0.115) |
| svc-export isolation guard | reference | STATUS_BACKEND.md + agent MEMORY.md writes blocked by worktree isolation guard in this session. Include full content in final report for session relay. |

**MS Sub-Plan A Phase B summary (2026-06-12):** delivered `backend/services/svc-export/app/router.py` (2 routes verbatim: POST /api/v1/products/{product_id}/export-xlsx 202 + @rate_limit export_initiate 10/3600; GET /api/v1/exports/{export_id} 200 no rate_limit) + authoritative `schemas.py` (wire shapes byte-equivalent) + `openapi.json` (2 endpoints, 3 business schemas) + `tests/test_export_routes.py` (7 non-tautological mounted-route tests). Zero /internal/* (leaf consumer). 26/26 svc-export tests PASS, ruff clean. Commit `a3a8e71`.

---

## MS Sub-Plan B Phase B — svc-dashboard router extraction (2026-06-13)

| Memory key | type | content |
| ---------- | ---- | ------- |
| svc-dashboard router.py import path | reference | `from app import service as dashboard_service` (NOT `from app.modules.dashboard import service`) — the svc-dashboard tree root IS the module. Exact same convention as svc-export. |
| svc-dashboard schemas.py import path | reference | `from app.schemas import DashboardQuery, DashboardResponse` — flat `app.schemas` (not `app.modules.dashboard.schemas`) |
| DashboardQuery is query-param model | reference | DashboardQuery is composed from individual FastAPI Query() params (page + limit), NOT a JSON body model. FastAPI does NOT generate a JSON schema component for it in the OpenAPI output. The 4 Python classes in schemas.py are DashboardQuery/ProductListItem/ProfileCompletenessSummary/DashboardResponse, but only 3 appear in `components/schemas` in the OpenAPI JSON (body models only). |
| svc-dashboard 1 business route | reference | Exactly 1 business /api/v1 APIRoute: GET /api/v1/products. FastAPI builtins (Route: /openapi.json, /docs, /docs/oauth2-redirect, /redoc) + /health APIRoute + /metrics Mount complete the app.routes inventory. |
| Feature flag guard reads settings at request-time | reference | `if not settings.FEATURE_TRACKING_DASHBOARD_ENABLED` inside handler body (NOT module-level or default arg). Preserves monkeypatch-friendly behavior: patching `app.shared.config.settings.FEATURE_TRACKING_DASHBOARD_ENABLED` works per-request because the attribute read happens at call time. Same pattern as category smart-picker guard and dashboard guard in monolith. |
| Guard fires BEFORE service call | reference | Spec §3.B says BEFORE service call. In router.py the guard is the FIRST statement in the handler body, before `query = DashboardQuery(...)` and before `await dashboard_service.list_products_for_dashboard(...)`. |
| NO /internal/* for leaf consumer | reference | svc-dashboard has zero inbound callers. The spec explicitly requires NO /internal/* routes. Only svc-export added /internal/* (as a callee of the image service); svc-dashboard does NOT add any. |
| svc-dashboard test_dashboard_extraction.py | reference | NO pytest suite from api-routes-builder slice. Per spec §3 Phase-C, test_dashboard_extraction.py is the backend-coordinator's Phase C deliverable (lead-owned, not specialist). |
| svc-dashboard openapi.json location | reference | backend/services/svc-dashboard/openapi.json — generated by booting the app in-process and calling app.openapi(). Contains 2 paths: /api/v1/products + /health; 5 schema components (DashboardResponse, ProductListItem, ProfileCompletenessSummary, HTTPValidationError, ValidationError). |
| ruff clean from first pass | reference | No ruff issues on either schemas.py or router.py. Extract-without-change (modulo import paths only) pattern delivers clean code automatically. |

**MS Sub-Plan B Phase B summary (2026-06-13):** delivered `backend/services/svc-dashboard/app/router.py` (1 route: GET /api/v1/products 200 + @rate_limit dashboard_list 600/3600 + FEATURE_TRACKING_DASHBOARD_ENABLED 404 guard BEFORE service call) + `app/schemas.py` (4 Pydantic v2 models byte-for-byte from monolith) + `openapi.json` regenerated (1 business endpoint, 3 OpenAPI schema components). Zero /internal/* (leaf consumer). App boots clean: `svc-dashboard: dashboard router mounted` logged. ruff clean. No pytest suite (Phase C deliverable). STATUS_BACKEND.md updated with UPDATE block + hand-off to backend-coordinator.
