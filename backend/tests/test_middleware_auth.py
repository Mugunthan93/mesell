"""JWT issuance + Depends-based user resolution."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import settings
from app.middleware.auth import (
    JWT_ALG,
    _decode_token,
    create_token,
    get_current_user,
    get_optional_user,
)
from app.models.user import User


def test_create_token_round_trip():
    uid = uuid.uuid4()
    token = create_token(uid, "pro")
    payload = _decode_token(token)
    assert payload["user_id"] == str(uid)
    assert payload["plan"] == "pro"
    assert "exp" in payload


def test_token_expiry_is_in_the_future():
    token = create_token(uuid.uuid4(), "free")
    payload = _decode_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    delta = exp - datetime.now(timezone.utc)
    assert delta > timedelta(days=settings.JWT_EXPIRY_DAYS - 1)
    assert delta <= timedelta(days=settings.JWT_EXPIRY_DAYS + 1)


def test_expired_token_rejected():
    payload = {
        "user_id": str(uuid.uuid4()),
        "plan": "free",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=60),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALG)
    with pytest.raises(jwt.ExpiredSignatureError):
        _decode_token(token)


def test_wrong_secret_rejected():
    token = jwt.encode(
        {
            "user_id": str(uuid.uuid4()),
            "plan": "free",
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
        },
        "different-secret",
        algorithm=JWT_ALG,
    )
    with pytest.raises(jwt.InvalidSignatureError):
        _decode_token(token)


@pytest.mark.asyncio
async def test_get_current_user_no_credentials_401():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None, db)
    assert exc.value.status_code == 401
    assert exc.value.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_get_current_user_bad_token_401():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="garbage.jwt.value")
    db = MagicMock()
    db.get = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds, db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_loads_user_from_db():
    uid = uuid.uuid4()
    token = create_token(uid, "pro")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = User(id=uid, phone="+919876543210", plan="pro")
    db = MagicMock()
    db.get = AsyncMock(return_value=user)
    out = await get_current_user(creds, db)
    assert out is user
    db.get.assert_awaited_once_with(User, uid)


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_without_header():
    request = MagicMock()
    request.headers = {}
    db = MagicMock()
    assert await get_optional_user(request, db) is None


@pytest.mark.asyncio
async def test_get_optional_user_returns_user_with_valid_header():
    uid = uuid.uuid4()
    token = create_token(uid, "free")
    request = MagicMock()
    request.headers = {"Authorization": f"Bearer {token}"}
    user = User(id=uid, phone="+919876543210", plan="free")
    db = MagicMock()
    db.get = AsyncMock(return_value=user)
    out = await get_optional_user(request, db)
    assert out is user
