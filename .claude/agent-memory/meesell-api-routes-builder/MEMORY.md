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

