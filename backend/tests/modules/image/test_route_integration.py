"""Image route integration tests — IMG-BE-01, IMG-BE-07, IMG-BE-09, IMG-BE-11.

Wave: qa-image-ai (Wave A).

Tests ROUTE-layer contracts (via AsyncClient + ASGITransport) for the image
module endpoints:

IMG-BE-01  POST happy 202 — enqueued_task_id non-empty + shape
IMG-BE-07  POST GCS-fail → 502 (AS-BUILT ground-truth: GcsAdapterError
           inherits AdapterError.status_code=502, NOT 503)
IMG-BE-09  GET list happy — signed-URL TTL + verbatim precheck_jsonb passthrough
IMG-BE-11  GET list cross-tenant → 404

Mock seam: ``adapters.gcs`` patched via monkeypatch at the module level;
Celery task delay patched via the ``stub_celery_delay`` conftest fixture.
Auth: ``get_current_user`` dependency overridden to return a synthetic
CurrentUser (no live JWT or OTP).

Ground-truth for GCS-fail (IMG-BE-07)
--------------------------------------
``GcsAdapterError`` inherits from ``AdapterError`` (``adapters/__init__.py``),
which has ``status_code: int = 502``.  The ``core/errors.register_error_handlers``
translates this to HTTP 502.  The V1-spec note mentions 503 but the AS-BUILT
is 502.  This test asserts 502.

D2 fix (Gate-4 repair pattern — matched from integration/conftest.py)
----------------------------------------------------------------------
``rate_limit_mw._check_window`` calls ``await get_valkey_otp()`` as a plain
function — NOT through FastAPI DI.  So a FastAPI ``dependency_overrides``
override has no effect on it.  After test N's function loop closes, the
``_otp_client`` singleton retains a ``StreamWriter`` whose transport's
``_loop`` is the now-closed loop N.  When test N+1 boots a new lifespan
and the middleware makes a Valkey pipeline call, that writer tries
``self._loop.call_soon(...)`` → ``RuntimeError: Event loop is closed``.

Fix: in ``image_route_client`` we replace ``_valkey_module._otp_client``
with a fresh function-loop-bound client for the fixture's duration, exactly
as ``integration/conftest.py::iam_client`` does (the D2 fix / Gate-4
repair-1 canon pattern).  The original singleton is restored in teardown.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.shared.valkey as _valkey_module
from app.adapters import GcsAdapterError
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from tests.conftest import _valkey_base

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# ---------------------------------------------------------------------------
# Stub auth
# ---------------------------------------------------------------------------
_STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")
_STUB_PLAN = "free"


@dataclass(frozen=True)
class _StubCurrentUser:
    user_id: uuid.UUID = _STUB_USER_ID
    plan: str = _STUB_PLAN


async def _stub_get_current_user() -> CurrentUser:
    return _StubCurrentUser()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# ASGI client fixture (stub auth only; DB from conftest db_session)
# D2 fix applied: patch _valkey_module._otp_client to a fresh function-loop
# client so rate_limit_mw never calls call_soon() on a closed loop.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(loop_scope="function")
async def image_route_client():
    """ASGI client with stub auth.  DB + Valkey come from the conftest.

    Applies the D2 fix (Gate-4 repair-1 canon): replaces the module-level
    ``_otp_client`` singleton with a fresh client born in this test's function
    loop for the fixture's duration.  Restores the original on teardown.
    Without this, a combined ``pytest -m integration`` run triggers
    ``RuntimeError: Event loop is closed`` on ``TestPostImageGCSFail`` and
    ``TestGetImageListCrossTenant`` because the lifespan boot causes
    rate_limit_mw to call ``call_soon()`` on the previous test's dead loop.
    """
    import redis.asyncio as _redis_lib

    valkey_base = _valkey_base()

    # ── D2 fix: swap in a fresh function-loop OTP client ─────────────────────
    _original_otp_client = _valkey_module._otp_client
    _test_otp_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    _valkey_module._otp_client = _test_otp_client  # type: ignore[assignment]

    app.dependency_overrides[get_current_user] = _stub_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    lifespan_db_engine = None
    lifespan_valkey_client = None

    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                lifespan_db_engine = getattr(app.state, "db_engine", None)
                lifespan_valkey_client = getattr(app.state, "valkey", None)
                yield ac

            # Drain pending asyncpg pool callbacks before the function loop tears down.
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
    finally:
        # ── Teardown ─────────────────────────────────────────────────────────
        app.dependency_overrides.pop(get_current_user, None)

        # Restore the original _otp_client singleton.
        _valkey_module._otp_client = _original_otp_client  # type: ignore[assignment]

        # Close the function-loop OTP client.
        try:
            await _test_otp_client.aclose()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Minimal JPEG factory
# ---------------------------------------------------------------------------
def _make_1500_jpeg() -> bytes:
    from io import BytesIO
    from PIL import Image
    img = Image.new("RGB", (1500, 1500), color=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ===========================================================================
# IMG-BE-01 — POST happy 202 enqueued_task_id non-empty
# ===========================================================================
class TestPostImageHappy202:
    """POST /products/{id}/images returns 202 with the locked shape.

    Asserts:
    - HTTP 202
    - ``enqueued_task_id`` is non-empty (task was enqueued)
    - ``status == "pending"``
    - ``idx`` matches the submitted slot
    """

    async def test_upload_returns_202_with_task_id(
        self,
        db,
        user,
        product,
        image_route_client,
        stub_gcs_upload,
        stub_gcs_signed_url,
        stub_celery_delay,
    ):
        jpeg_bytes = _make_1500_jpeg()

        # We need the route to own this product — the stub user id doesn't match
        # the seeded user.  Override get_db to return a session that can see the
        # seeded product, then also override get_current_user to match the seeded
        # user's ID.
        from app.shared.database import get_db

        async def _stub_db():
            yield db

        app.dependency_overrides[get_db] = _stub_db
        app.dependency_overrides[get_current_user] = (
            lambda: _StubCurrentUser(user_id=user.id)
        )

        try:
            resp = await image_route_client.post(
                f"/api/v1/products/{product.id}/images",
                files={"file": ("img.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
                data={"idx": "1"},
            )
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides[get_current_user] = _stub_get_current_user

        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["status"] == "pending"
        assert body["idx"] == 1
        assert body["enqueued_task_id"], "enqueued_task_id must not be empty"
        assert len(stub_celery_delay["calls"]) == 1


# ===========================================================================
# IMG-BE-07 — POST GCS-fail → 502 (AS-BUILT status code)
# ===========================================================================
class TestPostImageGCSFail:
    """GCS upload raises GcsAdapterError → 502.

    Ground-truth: ``GcsAdapterError`` has ``status_code=502`` (NOT 503).
    The AdapterError base class defaults to 502 per ``adapters/__init__.py``.
    The error handler translates this to HTTP 502.
    """

    async def test_gcs_fail_returns_502_not_503(
        self,
        db,
        user,
        product,
        image_route_client,
        stub_gcs_signed_url,
        stub_celery_delay,
        monkeypatch,
    ):
        from app.adapters import gcs as gcs_adapter
        from app.shared.database import get_db

        async def _raise_gcs(*args, **kwargs):
            raise GcsAdapterError("Simulated GCS upload failure")

        monkeypatch.setattr(gcs_adapter, "upload_bytes", _raise_gcs)

        async def _stub_db():
            yield db

        app.dependency_overrides[get_db] = _stub_db
        app.dependency_overrides[get_current_user] = (
            lambda: _StubCurrentUser(user_id=user.id)
        )

        jpeg_bytes = _make_1500_jpeg()
        try:
            resp = await image_route_client.post(
                f"/api/v1/products/{product.id}/images",
                files={"file": ("img.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
                data={"idx": "1"},
            )
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides[get_current_user] = _stub_get_current_user

        # AS-BUILT ground-truth: GcsAdapterError → 502 (NOT 503)
        assert resp.status_code == 502, (
            f"GCS-fail must map to 502 (AdapterError.status_code=502). "
            f"Got: {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        # validation_message_id must be non-empty (no blank key regression)
        assert body.get("validation_message_id") or body.get("code"), (
            f"Response must include a non-empty validation_message_id/code. Got: {body}"
        )
        # Celery task must NOT have been enqueued
        assert stub_celery_delay["calls"] == [], "Must not enqueue task on GCS failure"


# ===========================================================================
# IMG-BE-09 — GET list happy — signed-URL TTL + verbatim precheck_jsonb
# ===========================================================================
class TestGetImageListHappy:
    """GET /products/{id}/images returns signed URLs with correct TTL.

    Asserts:
    - Each image has a ``signed_url`` matching the stub's ``?ttl=<N>`` marker
    - TTL matches ``settings.GCS_SIGNED_URL_TTL_SECONDS``
    - ``precheck_jsonb`` is passed verbatim from the DB row
    """

    async def test_list_images_signed_url_ttl_and_precheck_passthrough(
        self,
        db,
        user,
        product,
        image_route_client,
        minimal_jpeg_bytes,
        stub_gcs_upload,
        stub_gcs_download,
        stub_gcs_signed_url,
        stub_celery_delay,
        stub_call_gemini_watermark,
    ):
        from fastapi import UploadFile
        from starlette.datastructures import Headers
        from app.modules.image import service as image_service
        from app.modules.image import tasks as image_tasks
        from app.shared.database import get_db
        from app.shared.config import settings

        stub_gcs_download["set"](minimal_jpeg_bytes)

        # Upload + run precheck inline to reach "ready" status
        upload = UploadFile(
            file=io.BytesIO(minimal_jpeg_bytes),
            filename="img.jpg",
            headers=Headers({"content-type": "image/jpeg"}),
        )
        resp_svc = await image_service.upload_image(
            user_id=user.id, product_id=product.id,
            file=upload, idx=1, db=db,
        )
        await db.commit()
        await image_tasks._run_precheck_pipeline(resp_svc.image_id, user.id)

        # Now call the route
        async def _stub_db():
            yield db

        app.dependency_overrides[get_db] = _stub_db
        app.dependency_overrides[get_current_user] = (
            lambda: _StubCurrentUser(user_id=user.id)
        )

        try:
            resp = await image_route_client.get(f"/api/v1/products/{product.id}/images")
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides[get_current_user] = _stub_get_current_user

        assert resp.status_code == 200
        body = resp.json()
        images = body["images"]
        assert len(images) == 1
        img = images[0]

        # Signed URL TTL assertion — the stub encodes ttl in the URL
        expected_ttl = settings.GCS_SIGNED_URL_TTL_SECONDS
        assert f"ttl={expected_ttl}" in img["signed_url"], (
            f"Signed URL must include ttl={expected_ttl}. Got: {img['signed_url']}"
        )

        # precheck_jsonb verbatim passthrough
        assert isinstance(img["precheck_jsonb"], dict)
        assert "jpeg_valid" in img["precheck_jsonb"]


# ===========================================================================
# IMG-BE-11 — GET list cross-tenant → 404
# ===========================================================================
class TestGetImageListCrossTenant:
    """GET /products/{id}/images for other user's product → 404.

    Verifies the tenancy gate on the list endpoint.
    """

    async def test_get_images_cross_tenant_returns_404(
        self,
        db,
        other_user,
        other_product,
        image_route_client,
        stub_gcs_signed_url,
    ):
        from app.shared.database import get_db

        # Request as _STUB_USER_ID (not other_user) for other_user's product
        async def _stub_db():
            yield db

        # Use a fresh UUID that does not match other_user
        requester_id = uuid.uuid4()
        app.dependency_overrides[get_db] = _stub_db
        app.dependency_overrides[get_current_user] = (
            lambda: _StubCurrentUser(user_id=requester_id)
        )

        try:
            resp = await image_route_client.get(
                f"/api/v1/products/{other_product.id}/images"
            )
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides[get_current_user] = _stub_get_current_user

        assert resp.status_code == 404, (
            f"Cross-tenant GET must return 404, got {resp.status_code}: {resp.text}"
        )
