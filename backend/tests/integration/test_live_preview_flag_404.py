"""Integration smoke test — FEATURE_LIVE_PREVIEW_ENABLED flag guard.

Session: mesell-flag-parity-sweep-session-1
Per FEATURE_PLAN.md §3 D3 + Master Plan §3.2 backend feature-flag protocol.

R1 + R4 RULINGS IN EFFECT (master-confirmed):
- R1 404-on-read: the preview GET route IS the feature; 404 when disabled is
  intentional (D3 kill-switch semantics).
- R4 default-False: FEATURE_LIVE_PREVIEW_ENABLED ships default False (the ONLY
  V1 flag with default False; all other V1 flags default True). This means the
  404 path is the DEFAULT behavior in all environments until the flag is
  explicitly set to True.

G3 coded-error body
-------------------
Per FEATURE_PLAN.md §3 D3, the disabled response carries BOTH a human-readable
``detail`` AND a machine-readable ``code``:
    {"detail": "Preview unavailable", "code": "feature.live_preview.disabled", ...}

The ``code`` field is emitted by the §4.F ``MeesellError`` handler (not by
``HTTPException``, which only emits ``code = "http.404"``).  The guard in the
handler raises ``MeesellError(code="feature.live_preview.disabled", ...)``
directly — consistent with the codebase's coded-error pattern and the
"do NOT invent a new error envelope" ruling (R3).

Two test paths covered
----------------------
1. **Default behavior (flag=False)**: with the default ``FEATURE_LIVE_PREVIEW_ENABLED=False``
   (config.py) the route returns 404 with the locked detail + code.
   This path is fully self-contained — no DB or Valkey required.

2. **Route-reachable when enabled** (``FEATURE_LIVE_PREVIEW_ENABLED=True``):
   GET /api/v1/products/{id}/preview is reachable (does NOT return the flag-guard
   404 detail) when the flag is explicitly set to True.  Full end-to-end response
   is infra-gated.  When infra is unavailable the test confirms a non-flag-guard
   response so the gate is meaningful in CI without a live DB.

Fixture strategy
----------------
- ``stub_preview_client`` creates an in-process ASGI client with a single
  dependency override:
    * ``get_current_user`` → a stub that returns a synthetic ``CurrentUser``
      so no valid JWT or DB user record is required.
- For the 404 path, ``get_db`` override is irrelevant — the flag guard fires
  before the service call, so the DB is never touched.
- ``settings.FEATURE_LIVE_PREVIEW_ENABLED`` is patched at the router import
  surface via ``unittest.mock.patch`` — specifically
  ``app.modules.catalog.router.settings`` (the module-level name in the
  catalog router) — per the smart-picker + export + pricing precedent.

Phone-prefix convention: ``+9155500XXXXX`` for teardown-compatible user writes
(none in this test — stub auth bypasses DB user lookup entirely).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app

# ── Stub user ─────────────────────────────────────────────────────────────────

_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-0000000000ff")
_STUB_PLAN: str = "free"

# A random product UUID used as the path param in all preview GET requests.
_STUB_PRODUCT_ID = uuid.UUID("00000000-0000-0000-0000-000000000044")

# Locked detail + code strings from FEATURE_PLAN.md §3 D3.
_FLAG_GUARD_DETAIL = "Preview unavailable"
_FLAG_GUARD_CODE = "feature.live_preview.disabled"


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
async def stub_preview_client():
    """ASGI client with stub auth override; NO DB/Valkey required.

    Only ``get_current_user`` is overridden — the DB override is left out
    intentionally.  The flag-guard tests fire BEFORE any DB call, so DB
    access is irrelevant for the flag-disabled assertions.
    """
    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ── Test 1: Default behavior (flag=False) → 404 ───────────────────────────────


@pytest.mark.asyncio
async def test_preview_returns_404_with_default_flag(stub_preview_client):
    """FEATURE_LIVE_PREVIEW_ENABLED defaults to False → 404 with locked body.

    R4 RULING: this flag ships default-False (the only V1 flag that does).
    No patching needed here — the config.py default IS False.

    Acceptance criteria (FEATURE_PLAN.md §3 D3 + Master Plan §3.2):
    - HTTP 404
    - body["detail"] == "Preview unavailable"
    - body["code"] == "feature.live_preview.disabled"
    """
    response = await stub_preview_client.get(
        f"/api/v1/products/{_STUB_PRODUCT_ID}/preview",
    )

    assert response.status_code == 404, (
        f"Expected 404 with default flag=False, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("detail") == _FLAG_GUARD_DETAIL, (
        f"Unexpected detail: {body.get('detail')!r}"
    )
    assert body.get("code") == _FLAG_GUARD_CODE, (
        f"Unexpected code: {body.get('code')!r}"
    )


@pytest.mark.asyncio
async def test_preview_flag_off_404_body_is_json(stub_preview_client):
    """Default flag=False 404 response carries a valid JSON body with code field.

    Ensures the MeesellError handler produces the standard §4.F envelope
    (not a plain string or HTML error page) and carries the ``code`` key.
    """
    response = await stub_preview_client.get(
        f"/api/v1/products/{_STUB_PRODUCT_ID}/preview",
    )

    assert response.status_code == 404
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body
    assert "code" in body, (
        "Expected 'code' key in §4.F MeesellError envelope; "
        f"got keys: {list(body.keys())}"
    )


# ── Test 2: Route reachable when flag explicitly True ─────────────────────────


@pytest.mark.asyncio
async def test_preview_route_reachable_when_flag_enabled(stub_preview_client):
    """FEATURE_LIVE_PREVIEW_ENABLED=True → GET does NOT return the flag-guard 404.

    Patches ``app.modules.catalog.router.settings`` at the module level to
    override the default-False flag to True.

    The response may be:
    - 200 if DB is seeded + product exists (full happy path)
    - 404 from the service (product not found — NOT from the flag guard;
      ``body["code"] != "feature.live_preview.disabled"`` confirms this)
    - 500 if DB connection is down (infra-gated — we accept this)

    ANY response where the flag-guard body strings are absent confirms the
    guard did NOT fire at the flag level.  This assertion is meaningful in CI
    without a live DB: the flag-guard 404 is the ONLY path that sets
    detail == ``_FLAG_GUARD_DETAIL`` AND code == ``_FLAG_GUARD_CODE``.

    If the service layer raises an exception due to missing DB infra, the test
    skips gracefully.
    """
    with patch("app.modules.catalog.router.settings") as mock_settings:
        mock_settings.FEATURE_LIVE_PREVIEW_ENABLED = True
        # Also enable catalog form so the catalog router itself doesn't get
        # excluded by the FEATURE_CATALOG_FORM_ENABLED main.py include guard.
        mock_settings.FEATURE_CATALOG_FORM_ENABLED = True

        response = await stub_preview_client.get(
            f"/api/v1/products/{_STUB_PRODUCT_ID}/preview",
        )

    # The flag-guard 404 must NOT appear when the flag is enabled.
    if response.status_code == 404:
        body = response.json()
        assert body.get("detail") != _FLAG_GUARD_DETAIL or body.get("code") != _FLAG_GUARD_CODE, (
            "Flag guard fired even though FEATURE_LIVE_PREVIEW_ENABLED=True (patched). "
            f"Full response: {body}"
        )
        # A real 404 from the service (product not found) is acceptable.
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

    # Successful reach: 200, 400, 404, 422, 500 are all acceptable
    # as long as the flag-guard strings are absent.
    assert response.status_code in {200, 400, 404, 422, 500}, (
        f"Unexpected status {response.status_code}: {response.text}"
    )
