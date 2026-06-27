## §4 core/ services slice CONSTRUCTED (2026-06-06)

### Scope
Joint dispatch with `meesell-auth-builder` against `BACKEND_ARCHITECTURE.md` §4 (`core/`).
Owned: errors, tenancy, cache, plan_guard + 6 middleware (request_id, tenancy_mw,
rate_limit_mw, plan_guard_mw, audit_mw) + `app/main.py` wiring.
Auth-builder owns `core/auth.py` + `core/middleware/auth_mw.py` — both were shipped
in time for me to wire `app/main.py`.

### Files created
- `backend/app/core/__init__.py` — package doc only.
- `backend/app/core/errors.py` (255 LOC) — `MeesellError` root + `register_error_handlers`
  registering 5 handlers (MeesellError, RequestValidationError, PydanticValidationError,
  HTTPException, Exception). Locked envelope `{detail, code, validation_message_id, request_id}`.
  Deferred-wire i18n resolver: `_resolve_message_id` tries `app.i18n.resolver` then falls back
  to `fallback or mid`.
- `backend/app/core/tenancy.py` (130 LOC) — `TenantViolationError`, `assert_owned`,
  `scope_to_user` using SQLAlchemy `query.column_descriptions[0]['entity']` reflection.
- `backend/app/core/cache.py` (160 LOC) — `get_or_set` (versioned `meesell:v{cv}:{key}`,
  single-flight via SET NX EX with 10s lock + 50ms poll up to 5s), `etag_for` (quoted SHA-256
  per RFC 7232), `prewarm_top_categories` (V1 no-op stub).
- `backend/app/core/plan_guard.py` (200 LOC) — `PlanLimitExceededError` (status 402),
  `V1_LIMITS_FREE` table, `enforce_plan_limit` with sliding-window (Valkey DB 0 sorted-set)
  + total-cap (SELECT COUNT(*) FROM products) branches.
- `backend/app/core/middleware/__init__.py` — package doc only.
- `backend/app/core/middleware/request_id.py` (60 LOC) — UUID gen + `X-Request-ID` echo.
- `backend/app/core/middleware/tenancy_mw.py` (35 LOC) — pure-copy `user.user_id` → `state.user_id`.
- `backend/app/core/middleware/rate_limit_mw.py` (230 LOC) — per-IP DDoS + per-route via
  `@rate_limit(scope, limit, window)` decorator attaching `__rate_limit__` tuple to the
  handler. Manual route resolution via `app.router.routes[r].matches(scope)` because
  `BaseHTTPMiddleware` runs BEFORE Starlette populates `request.scope["route"]`. Returns
  JSONResponse 429 inline (does NOT raise — see decision below). Fail-open with WARNING
  on `RedisError`/`ConnectionError`/`OSError`.
- `backend/app/core/middleware/plan_guard_mw.py` (30 LOC) — V1 no-op pass-through.
- `backend/app/core/middleware/audit_mw.py` (290 LOC) — post-2xx commit `audit_events`
  write via `AsyncSessionLocal()`. `@audit_event(event_type)` decorator; coalesce regex
  `/api/v1/products/{uuid}/(draft|autosave)` with Valkey DB 0 `SET NX EX 300` marker.
  PII scrubber hashes `phone` (SHA-256 + AUDIT_PII_SALT), strips `fssai_no`/`FSSAI_no`/
  `gst_no`/`GST_no`. Drop-on-failure: every exception caught + WARNING-logged.
- `backend/app/main.py` — re-authored to register 7 middleware deepest-first (Audit →
  PlanGuard → RateLimit → TenancyContext → AuthContext → RequestId → CORS) +
  `register_error_handlers(app)` + `prewarm_top_categories()` inside `lifespan` startup
  (try/except so startup never blocks on prewarm failure). Health endpoint preserved.

### Tests added (39 new, all PASS)
- `tests/test_core_errors.py` — 6 tests: envelope shape, MeesellError handler returns
  locked envelope, RequestValidationError → 422 with `validation.<field>.<constraint>`,
  HTTPException → `http.<status>`, generic Exception → `server.internal_error` with NO
  traceback leakage, deferred-wire fallback returns `mid` or `fallback`.
- `tests/test_core_tenancy.py` — 4 tests: assert_owned OK, mismatch → 403, None → 403,
  scope_to_user adds WHERE clause + unknown column raises ValueError.
- `tests/test_core_cache.py` — 5 tests: versioned key format, miss-then-hit dedupes,
  single-flight (10 concurrent → fetch called exactly 1), ETag quoted SHA-256, prewarm stub.
- `tests/test_core_plan_guard.py` — 9 tests: parametrised sliding-window over the 3 hourly
  resources, batched `requested` arg, recovery after key purge, product_count under-limit OK,
  at-limit raise, missing-db kwarg raises ValueError, unknown resource raises.
- `tests/test_core_middleware_ordering.py` — 4 tests: count==7, runtime order matches §4.H,
  audit innermost, CORS outermost. Reads `app.user_middleware` from the real `app.main.app`.
- `tests/test_core_audit_mw.py` — 7 tests: PII scrubber unit (phone hashed, FSSAI/GST stripped),
  2xx authenticated writes 1 row, 4xx writes 0 rows, 5xx writes 0 rows, anonymous writes 0
  rows, autosave coalesce (2 hits → 1 row), non-autosave (2 hits → 2 rows). Mocks
  `AsyncSessionLocal` to capture row inserts without Postgres.
- `tests/test_core_rate_limit_mw.py` — 3 tests: per-IP triggers 429 with locked envelope,
  per-route decorator triggers 429, Valkey unreachable fails OPEN + WARNING logged.

Plus `tests/conftest.py` extended with `use_live_valkey` fixture (loop_scope="function")
that re-points `shared.valkey._otp_client`/`_cache_client` at the locally-running Redis on
6379 — the conftest default 6381 is a tunnel that's not normally running on the laptop.

### Decisions FLAGGED (not in locked architecture)

1. **`RateLimitMiddleware` returns `JSONResponse` inline, not `raise RateLimitExceededError`.**
   Reason: `BaseHTTPMiddleware.dispatch` raises pass OUTSIDE Starlette's exception handler
   middleware in the dispatch stack, so registered handlers for `MeesellError` are bypassed.
   The inline JSONResponse builds the same locked envelope `{detail, code, validation_message_id, request_id}`
   manually. The `RateLimitExceededError` class is still exposed for service-layer use.
   Trade-off acknowledged; documented in module docstring.

2. **`plan_guard.enforce_plan_limit(product_count, ...)` REQUIRES `db: AsyncSession` kwarg.**
   Picked SELECT COUNT(*) over a Valkey-counter sync-up because the latter is a second
   source-of-truth with extra failure modes. `core/` takes the AsyncSession DB import via a
   LOCAL import (inside the function body) to avoid top-level `app.shared.models` import in
   `core/`. Documented in module docstring + tests cover the missing-kwarg ValueError path.

3. **Per-route rate-limit metadata lookup uses manual `app.router.routes[r].matches(scope)`.**
   `BaseHTTPMiddleware` runs BEFORE Starlette's router populates `request.scope["route"]`,
   so the documented `request.scope.get("route")` approach in §4.H is incomplete for this
   middleware position. Walks `app.routes` and picks the FULL match. Uses
   `starlette.routing.Match.FULL` enum. The fallback path also checks `request.scope["route"]`
   first so an inner middleware re-dispatch still works.

4. **`errors.py` registers BOTH `RequestValidationError` AND `PydanticValidationError`.**
   FastAPI body-validation raises the former; service-layer `Model.model_validate(...)`
   raises the latter. The §4.F spec mentions "pydantic.ValidationError" only — handler
   added for both to cover both call sites with the same envelope. Documented in module.

5. **`use_live_valkey` fixture added to `tests/conftest.py`** — pivots the singletons at
   localhost:6379 because conftest default port 6381 expects an SSH tunnel that is not
   running. Override via env `CORE_TEST_VALKEY_URL`. Loop-scope=function to dodge the
   asyncpg/asyncio cross-loop Future attachment that pytest-asyncio 0.24 induces under
   `asyncio_default_fixture_loop_scope=session`.

### Acceptance gate result
- `python -c "from app.main import app"` → imports clean; 9 routes; 7 user middleware in
  exactly the §4.H runtime order.
- `ruff check app/core/ app/main.py tests/test_core_*.py` → ALL CHECKS PASSED.
- Core test suite: 39/39 PASS.
- Baseline regression (`test_app_boot_integration.py` + `test_database.py`): 49/49 PASS.
- Shared infra (`test_shared_*`): 46/46 PASS.
- Grand total this dispatch: 134/134 PASS.

### Auth-builder coordination
`core/auth.py` (19.6 KB) and `core/middleware/auth_mw.py` (5.5 KB) were both already on
disk when I wired `app/main.py`. The import `from app.core.middleware.auth_mw import AuthContextMiddleware`
resolved cleanly — class name confirmed by inspecting auth_mw `__all__`. No blocker raised.

### Hand-offs queued
- §5A `i18n/resolver.py` — `_resolve_message_id` in `core/errors.py` is already wired with
  a lazy import. When resolver lands, no code change is required in `errors.py`.
- §7 `iam` — consumes `RateLimitMiddleware`'s `@rate_limit` decorator + `audit_event`
  decorator on auth endpoints; consumes `PlanLimitExceededError` for the upcoming
  subscription gates; consumes `enforce_plan_limit` from service layer at every
  create-product call site.
- §9 `category` — replaces `prewarm_top_categories` stub with the real seed-list +
  fetch fn. Signature `prewarm_top_categories(n: int = 100) -> None` is locked.
- `meesell-api-routes-builder` — every authenticated route can now use
  `@rate_limit(...)`, `@audit_event(...)`, and rely on `request.state.{user_id, request_id}`
  being populated by the chain. Error responses follow the locked envelope automatically.

---
