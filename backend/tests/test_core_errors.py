"""Tests for ``app.core.errors`` — envelope shape + 4 handler priorities."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.errors import MeesellError, _resolve_message_id, register_error_handlers

pytestmark = pytest.mark.unit


# ── Subclass used across tests ────────────────────────────────────────────
class _DummyError(MeesellError):
    code = "dummy.something_broke"
    status_code = 418
    validation_message_id = "dummy.something_broke"


class _Body(BaseModel):
    n: int = Field(ge=1, le=10)


def _make_app() -> FastAPI:
    """Minimal FastAPI app with the 4 error handlers + 4 trigger routes."""
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/dummy")
    async def _route_dummy() -> dict:
        raise _DummyError()

    @app.post("/validate")
    async def _route_validate(body: _Body) -> dict:
        return {"ok": True, "n": body.n}

    @app.get("/http")
    async def _route_http() -> dict:
        raise HTTPException(status_code=418, detail="teapot")

    @app.get("/boom")
    async def _route_boom() -> dict:
        raise ValueError("kaboom inside route")

    return app


# ── 1. Envelope shape ─────────────────────────────────────────────────────
def test_meesell_error_envelope_shape() -> None:
    """Subclasses expose class-level defaults — instance pickup is automatic."""
    err = _DummyError()
    assert err.code == "dummy.something_broke"
    assert err.status_code == 418
    assert err.validation_message_id == "dummy.something_broke"

    # Override on instance.
    err2 = _DummyError(code="override", status_code=400, validation_message_id="x")
    assert err2.code == "override"
    assert err2.status_code == 400
    assert err2.validation_message_id == "x"


# ── 2. MeesellError handler returns the locked envelope ───────────────────
@pytest.mark.asyncio
async def test_register_error_handlers_meesell_error() -> None:
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        resp = await ac.post("/dummy")
    assert resp.status_code == 418
    body = resp.json()
    assert set(body.keys()) >= {"detail", "code", "validation_message_id", "request_id"}
    assert body["code"] == "dummy.something_broke"
    assert body["validation_message_id"] == "dummy.something_broke"
    # request_id defaults to "unknown" because request_id_mw is not on this app.
    assert body["request_id"] == "unknown"


# ── 3. Pydantic ValidationError → 422 ─────────────────────────────────────
@pytest.mark.asyncio
async def test_register_error_handlers_validation_error() -> None:
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        resp = await ac.post("/validate", json={"n": 0})  # below ge=1
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "validation.error"
    # validation_message_id follows the locked convention:
    #   validation.<field>.<constraint>
    assert body["validation_message_id"].startswith("validation.n.")
    assert "errors" in body and isinstance(body["errors"], list) and body["errors"]


# ── 4. HTTPException handler ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_error_handlers_http_exception() -> None:
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        resp = await ac.get("/http")
    assert resp.status_code == 418
    body = resp.json()
    assert body["validation_message_id"] == "http.418"
    assert body["code"] == "http.418"


# ── 5. Generic Exception handler ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_error_handlers_generic_exception() -> None:
    app = _make_app()
    # raise_app_exceptions=False — let Starlette's exception middleware turn
    # the route's ValueError into the 500 envelope rather than re-raising it
    # out of the ASGI transport for the test client to see.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        resp = await ac.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["validation_message_id"] == "server.internal_error"
    assert body["code"] == "server.internal_error"
    # Traceback MUST NOT be in the response body.
    assert "kaboom" not in body["detail"]
    assert "Traceback" not in str(body)


# ── 6. i18n resolver wire (§5A.I) ─────────────────────────────────────────
def test_i18n_resolver_wired() -> None:
    """``app.i18n.resolver.resolve`` is wired; locked fallback contract holds.

    - Registered ID (in ``messages_en.VALIDATION_MESSAGES``) → resolved string.
    - Unregistered ID with no fallback → returns ID verbatim (debug-hint tier).
    - Unregistered ID WITH fallback → returns fallback (prose-recovery tier
      per ``core/errors.py`` semantics — preserves the exception's draft
      prose when the registry lookup gaps).
    """
    # Registered ID — resolver returns the English string.
    en = _resolve_message_id("server.internal.error")
    assert en == "Something went wrong on our end. Please try again."
    # Unregistered ID with no fallback → verbatim mid (last-resort tier).
    assert _resolve_message_id("nope.totally.unknown") == "nope.totally.unknown"
    # Unregistered ID with fallback → fallback string (caller's draft prose).
    assert (
        _resolve_message_id("nope.totally.unknown", fallback="Human readable")
        == "Human readable"
    )
