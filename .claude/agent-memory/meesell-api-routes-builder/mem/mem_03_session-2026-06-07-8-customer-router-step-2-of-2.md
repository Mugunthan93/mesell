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
