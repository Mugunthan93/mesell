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
