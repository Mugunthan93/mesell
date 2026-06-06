"""Tests for ``app.core.middleware.audit_mw``.

Verifies §11.3 (post-2xx commit) + §11.4 (autosave coalescing) + §11.9
(PII scrubbing) + §1.E drop-on-failure posture.

Strategy: mock the ``AuditEvent``-insert path so we observe row builds
without requiring a Postgres connection.  PII scrubbing is verified by
inspecting the constructed row directly.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import register_error_handlers
from app.core.middleware.audit_mw import (
    AuditMiddleware,
    _scrub_pii,
    audit_event,
)
from app.core.middleware.request_id import RequestIdMiddleware
from app.core.middleware.tenancy_mw import TenancyContextMiddleware


# ── Helper: app builder ───────────────────────────────────────────────────
def _make_app(user_id: uuid.UUID | None) -> FastAPI:
    """Build a tiny app with audit + tenancy + request_id middleware.

    A pseudo-auth middleware injects ``request.state.user`` so the
    downstream ``tenancy_mw`` populates ``request.state.user_id``.  This
    avoids depending on the real auth_mw inside this test file.
    """
    from starlette.middleware.base import BaseHTTPMiddleware

    app = FastAPI()
    register_error_handlers(app)

    class _StubUser:
        def __init__(self, uid: uuid.UUID | None) -> None:
            self.user_id = uid

    class _StubAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.user = _StubUser(user_id) if user_id is not None else None
            return await call_next(request)

    @app.post("/api/v1/products/{product_id}/draft")
    @audit_event("product.autosave")
    async def autosave(product_id: str) -> dict:
        return {"product_id": product_id, "saved": True}

    @app.post("/api/v1/products/{product_id}/export")
    @audit_event("product.export")
    async def export_product(product_id: str) -> dict:
        return {"product_id": product_id, "exported": True}

    @app.get("/api/v1/products/{product_id}")
    async def get_product(product_id: str) -> dict:
        return {"product_id": product_id}

    @app.get("/api/v1/error4xx")
    async def err4() -> dict:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="nope")

    @app.get("/api/v1/error5xx")
    async def err5() -> dict:
        raise RuntimeError("kaboom")

    # Deepest-first registration; see app.main rationale.
    app.add_middleware(AuditMiddleware)
    app.add_middleware(TenancyContextMiddleware)
    app.add_middleware(_StubAuthMiddleware)
    app.add_middleware(RequestIdMiddleware)
    return app


# ── PII scrubbing unit test ───────────────────────────────────────────────
def test_pii_scrubbing_phone_hashed_and_secrets_stripped():
    payload = {
        "phone": "+919876543210",
        "FSSAI_no": "10012345678901",
        "gst_no": "07AAA1234B1ZA",
        "ok": "keep me",
    }
    out = _scrub_pii(payload)
    assert "FSSAI_no" not in out
    assert "gst_no" not in out
    assert out["ok"] == "keep me"
    # phone hashed — 64-hex SHA-256
    assert len(out["phone"]) == 64
    assert all(c in "0123456789abcdef" for c in out["phone"])


# ── Helper: capture all AuditEvent constructions ──────────────────────────
def _patch_session_capture(rows: list):
    """Patch ``AsyncSessionLocal`` to capture rows added inside the middleware.

    Returns a context-manager patch object suitable for ``with``.
    """

    class _CaptureSession:
        def __init__(self) -> None:
            self.added = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        def add(self, row):
            self.added.append(row)
            rows.append(row)

        async def commit(self):
            return None

    return patch(
        "app.core.middleware.audit_mw.AsyncSessionLocal",
        side_effect=lambda: _CaptureSession(),
    )


# ── Coverage tests ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_2xx_authenticated_writes_one_row(use_live_valkey):
    uid = uuid.uuid4()
    app = _make_app(uid)
    rows: list = []
    transport = ASGITransport(app=app)
    with _patch_session_capture(rows):
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            pid = uuid.uuid4()
            r = await ac.post(f"/api/v1/products/{pid}/export")
            assert r.status_code == 200
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == uid
    assert row.event_type == "product.export"
    assert row.entity_type == "product"
    # phone scrubbed in metadata (the user_agent header has no phone, but
    # the scrubber must have processed metadata).  Confirm the key set.
    assert "method" in row.metadata_jsonb
    assert row.metadata_jsonb["status"] == 200


@pytest.mark.asyncio
async def test_4xx_response_writes_no_row(use_live_valkey):
    uid = uuid.uuid4()
    app = _make_app(uid)
    rows: list = []
    transport = ASGITransport(app=app)
    with _patch_session_capture(rows):
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/api/v1/error4xx")
            assert r.status_code == 400
    assert rows == []


@pytest.mark.asyncio
async def test_5xx_response_writes_no_row(use_live_valkey):
    uid = uuid.uuid4()
    app = _make_app(uid)
    rows: list = []
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    with _patch_session_capture(rows):
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/api/v1/error5xx")
            assert r.status_code == 500
    assert rows == []


@pytest.mark.asyncio
async def test_anonymous_writes_no_row(use_live_valkey):
    """Without a user_id, no row is written."""
    app = _make_app(None)
    rows: list = []
    transport = ASGITransport(app=app)
    with _patch_session_capture(rows):
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            pid = uuid.uuid4()
            r = await ac.post(f"/api/v1/products/{pid}/export")
            assert r.status_code == 200
    assert rows == []


@pytest.mark.asyncio
async def test_autosave_coalesce_two_hits_one_row(use_live_valkey):
    """Two autosave hits for same (user, product) within 5 min → 1 row."""
    uid = uuid.uuid4()
    pid = uuid.uuid4()
    app = _make_app(uid)
    rows: list = []
    transport = ASGITransport(app=app)
    with _patch_session_capture(rows):
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r1 = await ac.post(f"/api/v1/products/{pid}/draft")
            r2 = await ac.post(f"/api/v1/products/{pid}/draft")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_non_autosave_two_hits_two_rows(use_live_valkey):
    """Two ``product.export`` calls → 2 rows (no coalescing)."""
    uid = uuid.uuid4()
    pid = uuid.uuid4()
    app = _make_app(uid)
    rows: list = []
    transport = ASGITransport(app=app)
    with _patch_session_capture(rows):
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            await ac.post(f"/api/v1/products/{pid}/export")
            await ac.post(f"/api/v1/products/{pid}/export")
    assert len(rows) == 2
