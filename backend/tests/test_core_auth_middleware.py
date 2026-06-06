"""Unit tests for ``app.core.middleware.auth_mw.AuthContextMiddleware`` per §4.G.

These tests build a minimal Starlette app with ``AuthContextMiddleware`` as
the only middleware + a tiny endpoint that introspects ``request.state.user``.
No DB / no Valkey needed — the middleware is fail-open by contract and never
hits the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.auth import issue_access_token
from app.core.middleware.auth_mw import AuthContextMiddleware
from app.shared.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Test-app factory
# ─────────────────────────────────────────────────────────────────────────────


def _build_app() -> Starlette:
    """Minimal Starlette app: ``GET /probe`` echoes ``request.state.user``."""

    async def probe(request: Request) -> JSONResponse:
        user = getattr(request.state, "user", None)
        if user is None:
            return JSONResponse({"user": None})
        return JSONResponse(
            {
                "user": {
                    "user_id": str(user.user_id),
                    "plan": user.plan,
                }
            }
        )

    app = Starlette(routes=[Route("/probe", probe)])
    app.add_middleware(AuthContextMiddleware)
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_app())


# ─────────────────────────────────────────────────────────────────────────────
# 10. fail-open: no Authorization header
# ─────────────────────────────────────────────────────────────────────────────


def test_auth_mw_fail_open_no_header(client: TestClient) -> None:
    """Request with no Authorization header → state.user is None, status 200.

    Per §4.G ``auth_mw`` fail-open posture: missing token traverses the
    middleware without 401 — public routes (``/health``, ``/auth/otp/send``)
    rely on this.
    """
    resp = client.get("/probe")
    assert resp.status_code == 200, f"middleware must not 401 on missing header, got {resp.status_code}"
    assert resp.json() == {"user": None}


# ─────────────────────────────────────────────────────────────────────────────
# 11. fail-open: malformed Authorization header
# ─────────────────────────────────────────────────────────────────────────────


def test_auth_mw_fail_open_malformed(client: TestClient) -> None:
    """``Authorization: Bearer garbage`` → state.user is None, status 200."""
    resp = client.get("/probe", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 200
    assert resp.json() == {"user": None}

    # Also assert that a missing-Bearer-prefix variant is also fail-open.
    resp = client.get("/probe", headers={"Authorization": "Basic ZGVtbzpkZW1v"})
    assert resp.status_code == 200
    assert resp.json() == {"user": None}

    # Empty bearer value also fail-open.
    resp = client.get("/probe", headers={"Authorization": "Bearer "})
    assert resp.status_code == 200
    assert resp.json() == {"user": None}


# ─────────────────────────────────────────────────────────────────────────────
# 12. fail-open: expired token
# ─────────────────────────────────────────────────────────────────────────────


def test_auth_mw_fail_open_expired(client: TestClient) -> None:
    """Expired token → state.user is None, status 200.

    The dep at §4.B turns expiry into a 401; the middleware deliberately
    swallows it so unauthenticated routes still work.
    """
    user_id = uuid.uuid4()
    past = datetime.now(timezone.utc) - timedelta(seconds=300)
    expired_token = jwt.encode(
        {"sub": str(user_id), "exp": past, "plan": "free"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    resp = client.get("/probe", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 200
    assert resp.json() == {"user": None}


# ─────────────────────────────────────────────────────────────────────────────
# 13. happy: valid token → CurrentUser attached
# ─────────────────────────────────────────────────────────────────────────────


def test_auth_mw_attaches_user_on_valid_token(client: TestClient) -> None:
    """Valid Bearer token → state.user.user_id matches the JWT ``sub``.

    The middleware does NOT hit the DB — it only decodes and constructs the
    CurrentUser from the claim.  This is by design (§4.G — DB lookup is the
    dep's job).
    """
    user_id = uuid.uuid4()
    token = issue_access_token(user_id, plan="free")

    resp = client.get("/probe", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"] is not None, "middleware failed to attach user on valid token"
    assert body["user"]["user_id"] == str(user_id)
    assert body["user"]["plan"] == "free"


# ─────────────────────────────────────────────────────────────────────────────
# Bonus coverage — wrong-signature token also fail-open
# ─────────────────────────────────────────────────────────────────────────────


def test_auth_mw_fail_open_wrong_signature(client: TestClient) -> None:
    """Token signed with a different secret → state.user is None, status 200."""
    user_id = uuid.uuid4()
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    foreign_token = jwt.encode(
        {"sub": str(user_id), "exp": future, "plan": "free"},
        "totally-different-secret-key-not-the-real-one",
        algorithm="HS256",
    )
    resp = client.get("/probe", headers={"Authorization": f"Bearer {foreign_token}"})
    assert resp.status_code == 200
    assert resp.json() == {"user": None}
