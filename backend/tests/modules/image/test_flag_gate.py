"""Feature-flag gate tests — FEATURE_IMAGE_PRECHECK_ENABLED.

Session: mesell-image-precheck-backend-session-1
Per FEATURE_PLAN.md D2 + Master Plan §3.2 backend feature-flag protocol.

Four test cases
---------------
1. **POST → 404 when flag OFF** — upload endpoint returns HTTP 404 with the
   locked detail string when ``FEATURE_IMAGE_PRECHECK_ENABLED=False``.
2. **GET → 200 + empty list when flag OFF** — list endpoint returns HTTP 200
   with ``{"images": []}`` when the flag is OFF (read-only; sellers may have
   legacy images — must NOT 404).
3. **POST behaves normally when flag ON** — upload endpoint does NOT return
   the flag-guard 404 when the flag is its default True value.
4. **GET behaves normally when flag ON** — list endpoint does NOT return an
   empty list from the flag guard when the flag is True (it calls the service
   instead).

Fixture strategy
----------------
- ``stub_image_client`` creates an in-process ASGI client with ONE dependency
  override: ``get_current_user`` → a stub that returns a synthetic
  ``CurrentUser`` so no valid JWT or DB user record is required.
- ``get_db`` is NOT overridden — the flag-guard tests for cases 1 and 2 fire
  BEFORE any DB call, so the DB is never touched.
- For cases 3 and 4 the DB *would* be called after the flag guard passes.
  We patch the first service call so no DB round-trip happens; the test only
  needs to confirm the guard did NOT fire (i.e. a non-flag-guard response).
- ``settings.FEATURE_IMAGE_PRECHECK_ENABLED`` is patched via
  ``unittest.mock.patch`` at the router import level
  (``app.modules.image.router.settings``), matching the smart-picker precedent
  in ``tests/integration/test_suggest_flag_404.py``.

Phone-prefix convention: ``+9155500XXXXX`` for any teardown-compatible user
writes (none here — stub auth bypasses DB user lookup entirely).
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app

# ── Synthetic user injected instead of a real JWT resolve ────────────────────

_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000088")
_STUB_PLAN: str = "free"


def _make_stub_user() -> CurrentUser:
    """Synthetic CurrentUser — satisfies Depends(get_current_user)."""

    @dataclass(frozen=True)
    class _StubCurrentUser:
        user_id: uuid.UUID = _STUB_USER_ID
        plan: str = _STUB_PLAN

    return _StubCurrentUser()  # type: ignore[return-value]


async def _stub_get_current_user() -> CurrentUser:
    return _make_stub_user()  # type: ignore[return-value]


# ── Fixture — lightweight ASGI client with stub auth ─────────────────────────


@pytest_asyncio.fixture(loop_scope="function")
async def stub_image_client():
    """ASGI client with stub auth override; NO DB/Valkey required.

    Only ``get_current_user`` is overridden — the flag-guard tests fire
    before any DB call, so DB access is irrelevant for assertions 1 and 2.
    """
    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ── Minimal synthetic product id ─────────────────────────────────────────────

_FAKE_PRODUCT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Minimal JPEG bytes for multipart upload (flag-gate only; Pillow not used) ─

def _make_minimal_jpeg() -> bytes:
    """Return 10-byte placeholder simulating a JPEG Content-Type payload.

    The flag guard fires BEFORE the file is inspected, so the bytes do not
    need to be a valid JPEG for the 404-when-OFF tests.
    """
    # Minimal 2-byte JPEG SOI marker + 1 byte placeholder.
    return b"\xff\xd8\xff"


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — POST → 404 when flag OFF
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_images_returns_404_when_flag_disabled(stub_image_client):
    """FEATURE_IMAGE_PRECHECK_ENABLED=False → POST returns 404.

    The flag guard fires at the TOP of the handler, before idx validation
    and before any service call.  Auth is stubbed so the dependency chain
    resolves without a real JWT.

    Acceptance criteria (FEATURE_PLAN.md D2 + Master Plan §3.2):
    - HTTP 404
    - body["detail"] == "Image upload is disabled in this environment"
    """
    jpeg_bytes = _make_minimal_jpeg()
    with patch("app.modules.image.router.settings") as mock_settings:
        mock_settings.FEATURE_IMAGE_PRECHECK_ENABLED = False

        response = await stub_image_client.post(
            f"/api/v1/products/{_FAKE_PRODUCT_ID}/images",
            files={"file": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
            data={"idx": "1"},
        )

    assert response.status_code == 404, (
        f"Expected 404 when flag is disabled, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("detail") == "Image upload is disabled in this environment", (
        f"Unexpected detail: {body.get('detail')!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — GET → 200 + empty list when flag OFF
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_images_returns_empty_list_when_flag_disabled(stub_image_client):
    """FEATURE_IMAGE_PRECHECK_ENABLED=False → GET returns 200 + empty list.

    The GET endpoint must NOT return 404 when the flag is OFF — the list
    endpoint is read-only and sellers may have legacy images.  Per
    FEATURE_PLAN.md D2: ``GET /products/{id}/images`` returns
    ``{images: []}`` (200) when the flag is OFF.

    Acceptance criteria:
    - HTTP 200
    - body == {"images": []}
    """
    with patch("app.modules.image.router.settings") as mock_settings:
        mock_settings.FEATURE_IMAGE_PRECHECK_ENABLED = False

        response = await stub_image_client.get(
            f"/api/v1/products/{_FAKE_PRODUCT_ID}/images",
        )

    assert response.status_code == 200, (
        f"Expected 200 when flag is disabled for GET, got {response.status_code}: "
        f"{response.text}"
    )
    body = response.json()
    assert body == {"images": []}, (
        f"Expected {{\"images\": []}} when flag is disabled, got: {body!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — POST behaves normally when flag ON
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_images_flag_on_does_not_return_flag_guard_404(stub_image_client):
    """FEATURE_IMAGE_PRECHECK_ENABLED=True → POST does NOT return the flag-guard 404.

    When the flag is ON (default), the upload endpoint passes the guard and
    proceeds to the service layer.  We patch the first service call
    (``image_service.upload_image``) to raise a known non-404 exception so
    the test is hermetic (no live DB or GCS needed) and can distinguish
    "flag guard fired" from "service rejected for business reason".

    The patched service raises a generic Exception → FastAPI returns 500.
    Any non-flag-guard response confirms the guard did NOT block the request.
    """
    jpeg_bytes = _make_minimal_jpeg()

    # Patch the service to raise a predictable exception the moment the guard
    # passes.  We use a sentinel RuntimeError so the test is unambiguous.
    with patch(
        "app.modules.image.router.image_service.upload_image",
        side_effect=RuntimeError("stub: service entered — flag guard passed"),
    ):
        response = await stub_image_client.post(
            f"/api/v1/products/{_FAKE_PRODUCT_ID}/images",
            files={"file": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
            data={"idx": "1"},
        )

    # The flag-guard 404 must NOT appear when the flag is enabled.
    if response.status_code == 404:
        body = response.json()
        assert body.get("detail") != "Image upload is disabled in this environment", (
            "Flag guard fired even though FEATURE_IMAGE_PRECHECK_ENABLED=True (default). "
            f"Full response: {body}"
        )

    # 500 from our RuntimeError stub = service was reached = guard passed.
    # Accept any non-flag-guard response.
    assert response.status_code != 404 or response.json().get("detail") != (
        "Image upload is disabled in this environment"
    ), f"Flag guard must not fire when flag is ON. Response: {response.text}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — GET behaves normally when flag ON
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_images_flag_on_does_not_return_empty_list_from_guard(stub_image_client):
    """FEATURE_IMAGE_PRECHECK_ENABLED=True → GET does NOT short-circuit to empty list.

    When the flag is ON, the list endpoint must call the service (not
    return an empty list from the guard).  We patch the service to return a
    sentinel response with one image entry so the test can confirm the
    service was actually called (i.e. the guard did NOT intercept).
    """
    from datetime import timezone

    from app.modules.image.schemas import ImageSummary, ImagesListResponse

    sentinel_image = ImageSummary(
        image_id=_FAKE_PRODUCT_ID,
        idx=1,
        status="pending",
        signed_url="https://storage.googleapis.com/test/sentinel.jpg?signed=1",
        precheck_jsonb={},
        is_front=True,
        width=None,
        height=None,
        color_space=None,
        created_at=__import__("datetime").datetime(2026, 6, 11, 0, 0, 0, tzinfo=timezone.utc),
    )
    sentinel_response = ImagesListResponse(images=[sentinel_image])

    with patch(
        "app.modules.image.router.image_service.list_images",
        return_value=sentinel_response,
    ):
        response = await stub_image_client.get(
            f"/api/v1/products/{_FAKE_PRODUCT_ID}/images",
        )

    # Must not be the guard's empty-list short-circuit.
    assert response.status_code == 200, (
        f"Expected 200 from service, got {response.status_code}: {response.text}"
    )
    body = response.json()
    # Guard returns {"images": []}; service returns 1-item list.
    assert body != {"images": []}, (
        "GET returned the flag-guard empty list even though the flag is ON. "
        "The guard is firing when it should not be."
    )
    assert len(body.get("images", [])) == 1, (
        f"Expected 1 image from sentinel service stub, got: {body!r}"
    )
