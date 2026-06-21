"""/verify gate (api-endpoint) for the auth i18n 3-segment fix.

Closes L_iam_1.  Asserts that an HTTP 401/403 raised by ``get_current_user``
renders an error envelope whose ``detail`` is the HUMAN, resolved i18n string
(e.g. "You're not signed in. Please sign in to continue.") — NOT the verbatim
message id (``auth.token.missing`` / the legacy ``auth.token_missing``).

This exercises the FULL chain end-to-end over ASGI:

    get_current_user → TokenMissing/Expired/UserNotFound (3-segment id)
        → core.errors._meesell_error_handler → i18n.resolver.resolve
        → locked §4.F envelope

No real database or Valkey is touched: ``get_db`` is dependency-overridden with
a stub AsyncSession whose ``get(...)`` returns ``None`` (the unknown-user case)
or is never called (the missing/malformed/expired cases bail before the DB).
Per the standing constraint, NO live dev DB is used.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import register_error_handlers
from app.i18n.messages_en import VALIDATION_MESSAGES
from app.shared.config import settings
from app.shared.database import get_db

pytestmark = pytest.mark.unit


# ── Resolved human strings the envelope MUST carry (from the en catalog) ─────
_HUMAN_TOKEN_MISSING = VALIDATION_MESSAGES["auth.token.missing"]
_HUMAN_TOKEN_EXPIRED = VALIDATION_MESSAGES["auth.token.expired"]
_HUMAN_USER_NOT_FOUND = VALIDATION_MESSAGES["auth.user.not_found"]


def _stub_db(user_row: object | None) -> AsyncSession:
    """A stub AsyncSession whose ``get(User, ...)`` resolves to ``user_row``.

    Used only for the unknown-user path (where the dep reaches the DB lookup).
    The missing / malformed / expired paths bail before ``db.get`` is awaited.
    """
    db = MagicMock(spec=AsyncSession)
    db.get = AsyncMock(return_value=user_row)
    return db


def _make_app(user_row: object | None = None) -> FastAPI:
    """Minimal app: real §4.F handlers + one protected route + stubbed get_db."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/protected")
    async def _protected(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> dict:
        return {"user_id": str(user.user_id)}

    app.dependency_overrides[get_db] = lambda: _stub_db(user_row)
    return app


def _expired_token() -> str:
    past = datetime.now(timezone.utc) - timedelta(seconds=120)
    return jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": past, "plan": "free"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def _valid_token() -> str:
    future = datetime.now(timezone.utc) + timedelta(seconds=120)
    return jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": future, "plan": "free"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


@pytest.mark.asyncio
async def test_missing_token_detail_is_human_string() -> None:
    """No Authorization header → 401, envelope detail = human copy (not the id)."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/protected")

    assert resp.status_code == 401
    body = resp.json()
    # The locked id is correct AND 3-segment...
    assert body["validation_message_id"] == "auth.token.missing"
    # ...and the human-facing detail is the RESOLVED string, never a verbatim id.
    assert body["detail"] == _HUMAN_TOKEN_MISSING
    assert body["detail"] not in ("auth.token.missing", "auth.token_missing")


@pytest.mark.asyncio
async def test_malformed_token_detail_is_human_string() -> None:
    """Garbage bearer token → 401 token.missing, human detail."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get(
            "/protected", headers={"Authorization": "Bearer not-a-jwt"}
        )

    assert resp.status_code == 401
    body = resp.json()
    assert body["validation_message_id"] == "auth.token.missing"
    assert body["detail"] == _HUMAN_TOKEN_MISSING
    assert body["detail"] not in ("auth.token.missing", "auth.token_missing")


@pytest.mark.asyncio
async def test_expired_token_detail_is_human_string() -> None:
    """Expired JWT → 401 token.expired, human detail."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get(
            "/protected", headers={"Authorization": f"Bearer {_expired_token()}"}
        )

    assert resp.status_code == 401
    body = resp.json()
    assert body["validation_message_id"] == "auth.token.expired"
    assert body["detail"] == _HUMAN_TOKEN_EXPIRED
    assert body["detail"] not in ("auth.token.expired", "auth.token_expired")


@pytest.mark.asyncio
async def test_unknown_user_detail_is_human_string() -> None:
    """Valid JWT but the user row is gone → 403 user.not_found, human detail."""
    app = _make_app(user_row=None)  # db.get(...) -> None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get(
            "/protected", headers={"Authorization": f"Bearer {_valid_token()}"}
        )

    assert resp.status_code == 403
    body = resp.json()
    assert body["validation_message_id"] == "auth.user.not_found"
    assert body["detail"] == _HUMAN_USER_NOT_FOUND
    assert body["detail"] not in ("auth.user.not_found", "auth.user_not_found")
