"""Integration smoke test — FEATURE_SMART_PICKER_ENABLED flag guard.

Session: mesell-smart-picker-backend-session-1
Per FEATURE_PLAN.md D2 + Master Plan §3.2 backend feature-flag protocol.

AMENDMENT 2026-06-16 (founder ruling, finding #4):
``/api/v1/categories/suggest`` changed from GET (query param) → POST (JSON body).
``q`` max_length raised 500 → 5000.  All tests updated accordingly.
Field name ``q`` is preserved.

Two test paths covered
----------------------
1. **404-when-disabled** (``FEATURE_SMART_PICKER_ENABLED=False``):
   The route returns ``{"detail": "Smart Picker is disabled in this
   environment"}`` with HTTP 404 regardless of request content.
   This path is fully self-contained — no DB or Valkey required.

2. **Route-reachable when enabled** (``FEATURE_SMART_PICKER_ENABLED=True``,
   the default):
   The route is reachable (does NOT return 404 from the flag guard) when
   the flag is on.  Full end-to-end response is infra-gated (dev-tunnel
   DB + categories seed required).  When infra is unavailable the test
   confirms a non-flag-guard response (200 or 400/422 or 402 — anything
   except the 404 the flag guard emits) so the gate is meaningful even
   in CI without a live DB.

3. **Max-length boundary** (q exactly 5000 chars → 200/non-422, q 5001 chars → 422).
   Added per finding #4 requirement.

Fixture strategy
----------------
- ``stub_category_client`` creates an in-process ASGI client with stub auth
  override:
    * ``get_current_user`` → a stub that returns a synthetic ``CurrentUser``
      so no valid JWT or DB user record is required.
- For the 404 path, ``get_db`` override is irrelevant — the flag guard fires
  before the service call, so the DB is never touched.
- ``settings.FEATURE_SMART_PICKER_ENABLED`` is patched at the router import
  level via ``unittest.mock.patch`` (matching the
  ``test_core_rate_limit_mw.py`` precedent for patching module-level
  ``settings``).
- The ``iam_client`` fixture (from ``integration/conftest.py``) is NOT used
  here — that fixture requires an active dev tunnel for DB + Valkey.  The
  stub fixture is lighter and self-contained for the flag-guard purpose.

Phone-prefix convention: ``+9155500XXXXX`` for any teardown-compatible
user writes (none in this test — stub auth bypasses DB user lookup entirely).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.shared.valkey as _valkey_module
from app.core.auth import CurrentUser, get_current_user
from app.main import app


def _valkey_base_url() -> str:
    """Derive the Valkey base URL (no db suffix) from environment, matching
    the precedence chain in tests/conftest.py ``_valkey_base()``.
    """
    raw = (
        os.environ.get("TEST_VALKEY_URL")
        or os.environ.get("VALKEY_URL")
        or os.environ.get("CORE_TEST_VALKEY_URL")
        or "redis://localhost:6379"
    )
    # Strip trailing /<db> suffix to avoid double-suffix later.
    if raw.rsplit("/", 1)[-1].isdigit():
        raw = raw.rsplit("/", 1)[0]
    return raw

# ── Stub user injected into every request instead of a real JWT resolve ──────

_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
_STUB_PLAN: str = "free"


def _make_stub_user() -> CurrentUser:
    """Synthetic CurrentUser — satisfies the Depends(get_current_user) type."""

    @dataclass(frozen=True)
    class _StubCurrentUser:
        user_id: uuid.UUID = _STUB_USER_ID
        plan: str = _STUB_PLAN

    return _StubCurrentUser()  # type: ignore[return-value]


async def _stub_get_current_user() -> CurrentUser:
    return _make_stub_user()  # type: ignore[return-value]


# ── Fixture — lightweight ASGI client with stub auth ─────────────────────────


@pytest_asyncio.fixture(loop_scope="function")
async def stub_category_client():
    """ASGI client with stub auth override; NO DB/Valkey required.

    Only ``get_current_user`` is overridden — the DB override is left out
    intentionally so that tests needing DB access can hit the real dev-tunnel
    URL (infra-gated tests skip on connection failure at the service layer).
    The flag-guard tests fire BEFORE any DB call, so DB access is irrelevant
    for those assertions.

    Per the Gate-4 repair (meesell-api-routes-builder memory D2, 2026-06-12):
    ``RateLimitMiddleware`` calls ``_check_window`` which calls
    ``get_valkey_otp()`` directly (NOT via FastAPI DI).
    ``dependency_overrides[get_valkey_otp]`` has no effect on middleware.
    With ``loop_scope="function"`` each fixture gets its own event loop; if
    the ``_otp_client`` singleton was bound to a prior loop it causes
    ``RuntimeError: Event loop is closed`` inside the rate-limit pipeline.
    Fix: patch ``_valkey_module._otp_client`` with a fresh per-test
    connection so every test's middleware uses the current function loop.
    """
    import redis.asyncio as _redis_lib

    valkey_base = _valkey_base_url()
    _original_otp_client = _valkey_module._otp_client

    # Fresh connection bound to THIS function's event loop.
    _valkey_module._otp_client = _redis_lib.from_url(
        f"{valkey_base}/0", decode_responses=True
    )

    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            lifespan_db_engine = getattr(app.state, "db_engine", None)
            lifespan_valkey_client = getattr(app.state, "valkey", None)
            yield ac
        # Drain lifespan-created engine + Valkey BEFORE the function loop tears down
        # to prevent "Event loop is closed" teardown errors (per double-dispose pattern).
        if lifespan_db_engine is not None:
            try:
                await lifespan_db_engine.dispose()
            except Exception:
                pass
        if lifespan_valkey_client is not None:
            try:
                await lifespan_valkey_client.aclose()
            except Exception:
                pass

    app.dependency_overrides.pop(get_current_user, None)

    # Restore original singleton.
    try:
        await _valkey_module._otp_client.aclose()
    except Exception:
        pass
    _valkey_module._otp_client = _original_otp_client


# ── Test 1: 404 when flag disabled ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_returns_404_when_flag_disabled(stub_category_client):
    """FEATURE_SMART_PICKER_ENABLED=False → 404 with the locked detail string.

    Patches ``app.modules.category.router.settings`` at the module level so
    the guard expression ``if not settings.FEATURE_SMART_PICKER_ENABLED``
    evaluates True.  Auth is stubbed so the dependency chain resolves without
    a real JWT.

    AMENDMENT 2026-06-16: uses POST + JSON body ``{"q": "..."}`` instead of
    GET + query param.

    Acceptance criteria (FEATURE_PLAN.md D2 + Master Plan §3.2):
    - HTTP 404
    - body["detail"] == "Smart Picker is disabled in this environment"
    """
    with patch("app.modules.category.router.settings") as mock_settings:
        # Mirror real settings except for the flag.
        mock_settings.FEATURE_SMART_PICKER_ENABLED = False

        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": "cotton saree for wedding"},
        )

    assert response.status_code == 404, (
        f"Expected 404 when flag is disabled, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("detail") == "Smart Picker is disabled in this environment", (
        f"Unexpected detail: {body.get('detail')!r}"
    )


@pytest.mark.asyncio
async def test_suggest_404_body_is_json(stub_category_client):
    """Flag-disabled 404 response carries a valid JSON body.

    Ensures the error handler produces the standard FastAPI HTTPException
    envelope (not a plain string or HTML error page).

    AMENDMENT 2026-06-16: uses POST + JSON body.
    """
    with patch("app.modules.category.router.settings") as mock_settings:
        mock_settings.FEATURE_SMART_PICKER_ENABLED = False

        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": "test product"},
        )

    assert response.status_code == 404
    # Must be parseable JSON.
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


@pytest.mark.asyncio
async def test_suggest_flag_off_ignores_q_length(stub_category_client):
    """Flag guard fires before Pydantic validation; any q value yields 404.

    Verifies the guard is at function entry, not gated by body-param validity.
    Even a maximally long q (5000 chars) returns 404 from the guard rather
    than 422 from Pydantic.

    AMENDMENT 2026-06-16: uses POST + JSON body; q max raised to 5000.
    """
    long_q = "x" * 5000  # max-length valid q
    with patch("app.modules.category.router.settings") as mock_settings:
        mock_settings.FEATURE_SMART_PICKER_ENABLED = False
        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": long_q},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Smart Picker is disabled in this environment"


# ── Test 2: Route reachable when flag enabled ─────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_route_reachable_when_flag_enabled(stub_category_client, monkeypatch):
    """FEATURE_SMART_PICKER_ENABLED=True → route does NOT return the flag-guard 404.

    The default value of ``settings.FEATURE_SMART_PICKER_ENABLED`` is True
    (per config.py); no patching needed for the flag.

    AMENDMENT 2026-06-16: uses POST + JSON body ``{"q": "cotton kurti for women"}``.

    The response may be:
    - 200 if DB is seeded + AI is mocked (full happy path)
    - 402 if plan_guard fires (stub user has no plan rows in DB)
    - 422 if Pydantic rejects q (unlikely — we send a valid q)
    - 500 if DB connection is down (infra-gated — we accept this silently)

    ANY response other than 404 confirms the flag guard did NOT fire.
    This assertion is meaningful in CI without a live DB: the 404 guard
    is the ONLY path that returns exactly 404 for a syntactically valid q.
    Other failures (DB down → 500; plan_guard → 402) are all non-404.

    If the service layer raises an exception that results in 500 due to
    missing DB infra, the test skips gracefully.
    """
    # Mock the AI call to avoid real Gemini spend; the service may not reach
    # it if plan_guard fires first, but the mock keeps the test hermetic.
    mock_ai_response = AsyncMock(
        return_value=type(
            "_AIResp",
            (),
            {
                "parsed": {"suggestions": [], "fallback_offered": True},
                "raw_response": None,
                "cost_inr": 0.0,
                "layer2_retries": 0,
                "trace_id": "stub",
            },
        )()
    )
    with patch("app.modules.category.service.ai_client.call_gemini", mock_ai_response):
        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": "cotton kurti for women"},
        )

    # The flag guard 404 must NOT appear when the flag is enabled.
    if response.status_code == 404:
        body = response.json()
        assert body.get("detail") != "Smart Picker is disabled in this environment", (
            "Flag guard fired even though FEATURE_SMART_PICKER_ENABLED=True (default). "
            f"Full response: {body}"
        )
        # A real 404 from the route (e.g. category not found) is acceptable.
        return

    # If the service blows up due to missing DB infra, skip rather than fail.
    if response.status_code == 500:
        body_text = response.text
        if any(
            keyword in body_text
            for keyword in ("Connection refused", "could not connect", "asyncpg")
        ):
            pytest.skip(
                "DB infra not available — flag-enabled path is infra-gated; "
                "flag-guard 404 path (test 1) is the authoritative smoke test"
            )

    # Successful reach: 200, 400, 402, 422 are all acceptable (not the flag-guard 404).
    assert response.status_code in {200, 400, 402, 422, 500}, (
        f"Unexpected status {response.status_code}: {response.text}"
    )


# ── Test 3: OpenAPI emits POST for the route ──────────────────────────────────


@pytest.mark.asyncio
async def test_openapi_includes_suggest_route(stub_category_client):
    """OpenAPI JSON includes /api/v1/categories/suggest as a POST operation.

    AMENDMENT 2026-06-16: verifies the route is now a POST (not GET) with a
    JSON request body (not a query param).  The ``q`` field appears in the
    requestBody schema with minLength=1 and maxLength=5000.

    Verifies the route is visible to API clients and tooling regardless of
    the feature flag state.  OpenAPI is generated from route metadata, not
    from runtime flag evaluation, so this test does NOT patch the flag.
    """
    response = await stub_category_client.get("/openapi.json")
    assert response.status_code == 200, f"/openapi.json failed: {response.status_code}"
    spec = response.json()

    paths = spec.get("paths", {})
    suggest_path = "/api/v1/categories/suggest"
    assert suggest_path in paths, (
        f"OpenAPI paths missing {suggest_path!r}. Present paths: {list(paths.keys())}"
    )

    # AMENDMENT 2026-06-16: must be a POST, not a GET.
    post_op = paths[suggest_path].get("post", {})
    assert post_op, (
        f"No POST operation under {suggest_path!r} in OpenAPI "
        f"(operations present: {list(paths[suggest_path].keys())})"
    )

    # Must NOT have a GET operation (method was changed).
    assert "get" not in paths[suggest_path], (
        f"Stale GET operation still present under {suggest_path!r} — "
        "router was not updated from GET to POST"
    )

    # Verify the request body carries q.
    request_body = post_op.get("requestBody", {})
    assert request_body, f"POST {suggest_path!r} is missing a requestBody"
    content = request_body.get("content", {})
    assert "application/json" in content, (
        f"requestBody.content missing 'application/json' for {suggest_path!r}"
    )

    # Walk the JSON schema for the body to find q's constraints.
    body_schema = content["application/json"].get("schema", {})
    # Schema may be a $ref — resolve via components/schemas if needed.
    if "$ref" in body_schema:
        ref_name = body_schema["$ref"].split("/")[-1]
        body_schema = spec.get("components", {}).get("schemas", {}).get(ref_name, {})

    props = body_schema.get("properties", {})
    assert "q" in props, (
        f"Field 'q' missing from requestBody schema for {suggest_path!r}. "
        f"Properties found: {list(props.keys())}"
    )
    q_schema = props["q"]
    assert q_schema.get("minLength") == 1, (
        f"q minLength expected 1, got {q_schema.get('minLength')}"
    )
    assert q_schema.get("maxLength") == 5000, (
        f"q maxLength expected 5000, got {q_schema.get('maxLength')} "
        "(was 500 before 2026-06-16 amendment)"
    )


# ── Test 4: 5000-char body is accepted (finding #4 boundary gate) ─────────────


@pytest.mark.asyncio
async def test_suggest_accepts_5000_char_description(stub_category_client):
    """A 5000-character description MUST NOT yield a 422 Pydantic validation error.

    Finding #4 requirement: max_length was raised from 500 to 5000.  The
    Pydantic ``SuggestQuery`` schema enforces this.  With the flag enabled,
    the body passes Pydantic validation and reaches the service.
    The service may fail (DB down → 500, plan_guard → 402) but it MUST NOT
    produce a 422 for exactly 5000 chars.

    AMENDMENT 2026-06-16: primary acceptance gate for the max_length=5000 change.
    """
    long_q = "A" * 5000  # exactly at the new max length

    with patch("app.modules.category.router.settings") as mock_settings:
        # Keep the flag enabled so we actually reach body validation.
        mock_settings.FEATURE_SMART_PICKER_ENABLED = True

        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": long_q},
        )

    # 422 means Pydantic rejected the body — that would be a regression.
    assert response.status_code != 422, (
        f"5000-char q was rejected with 422 — max_length not raised correctly. "
        f"Body: {response.text}"
    )
    # 200, 402, 404 (flag off), 500 (no DB) are all acceptable non-422 outcomes.
    assert response.status_code in {200, 402, 404, 500}, (
        f"Unexpected status {response.status_code} for 5000-char q: {response.text}"
    )


# ── Test 5: 5001-char body is rejected (>max_length) ─────────────────────────


@pytest.mark.asyncio
async def test_suggest_rejects_5001_char_description(stub_category_client):
    """A description exceeding 5000 chars MUST yield HTTP 422.

    Finding #4 requirement: verifies the upper boundary is enforced at exactly
    5000 chars (i.e., 5001 → 422).  This guards against accidentally removing
    the max_length constraint.

    AMENDMENT 2026-06-16: new boundary test.
    """
    too_long_q = "A" * 5001  # one over the max length

    with patch("app.modules.category.router.settings") as mock_settings:
        mock_settings.FEATURE_SMART_PICKER_ENABLED = True

        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": too_long_q},
        )

    assert response.status_code == 422, (
        f"5001-char q should be rejected with 422 (max_length=5000), "
        f"got {response.status_code}: {response.text}"
    )


# ── Test 6: empty q (min_length=1) is rejected ───────────────────────────────


@pytest.mark.asyncio
async def test_suggest_rejects_empty_q(stub_category_client):
    """An empty string ``q`` must yield HTTP 422 (min_length=1 enforced).

    Unchanged from pre-amendment behaviour — min_length=1 is preserved.
    Uses POST + JSON body.
    """
    with patch("app.modules.category.router.settings") as mock_settings:
        mock_settings.FEATURE_SMART_PICKER_ENABLED = True

        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": ""},
        )

    assert response.status_code == 422, (
        f"Empty q should be rejected with 422, got {response.status_code}: {response.text}"
    )


# ── Test 7: missing body field returns 422 ───────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_missing_body_returns_422(stub_category_client):
    """POST with empty JSON object yields 422 (q is required).

    AMENDMENT 2026-06-16: since the endpoint is now POST, an empty body
    object must be rejected by Pydantic's required-field validation.
    """
    with patch("app.modules.category.router.settings") as mock_settings:
        mock_settings.FEATURE_SMART_PICKER_ENABLED = True

        # Send empty JSON object — q is required, so this is missing.
        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={},
        )

    assert response.status_code == 422, (
        f"Missing q in body should yield 422, got {response.status_code}: {response.text}"
    )


# ── Test 8: extra body fields are rejected (extra='forbid') ──────────────────


@pytest.mark.asyncio
async def test_suggest_extra_body_fields_rejected(stub_category_client):
    """Body with extra fields must be rejected with 422.

    AMENDMENT 2026-06-16: SuggestQuery now has ``model_config = ConfigDict(extra='forbid')``.
    """
    with patch("app.modules.category.router.settings") as mock_settings:
        mock_settings.FEATURE_SMART_PICKER_ENABLED = True

        response = await stub_category_client.post(
            "/api/v1/categories/suggest",
            json={"q": "valid description", "unexpected_field": "should fail"},
        )

    assert response.status_code == 422, (
        f"Extra body fields should yield 422 (extra='forbid'), "
        f"got {response.status_code}: {response.text}"
    )


# ── Test 9: 401 on unauthenticated request ───────────────────────────────────


@pytest.mark.asyncio
async def test_suggest_returns_401_without_auth():
    """POST /categories/suggest without a Bearer token → 401.

    No auth dependency override — verifies the route remains auth-protected.
    Uses a bare ASGI client (no dependency_overrides).
    """
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            response = await ac.post(
                "/api/v1/categories/suggest",
                json={"q": "cotton saree"},
            )

    assert response.status_code == 401, (
        f"Expected 401 without auth, got {response.status_code}: {response.text}"
    )
