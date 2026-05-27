"""JWT issuance and FastAPI auth dependencies."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

JWT_ALG = "HS256"
_bearer_required = HTTPBearer(auto_error=False)


def create_token(user_id: uuid.UUID, plan: str) -> str:
    """Issue an HS256 JWT with a 7-day expiry."""
    expiry = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRY_DAYS)
    payload = {"user_id": str(user_id), "plan": plan, "exp": expiry}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALG)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALG])


async def _load_user(token: str, db: AsyncSession) -> User | None:
    try:
        payload = _decode_token(token)
        user_id = uuid.UUID(payload["user_id"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        logger.debug(f"Token rejected: {exc}")
        return None
    return await db.get(User, user_id)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_required)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve the bearer token to a User row; raise 401 on any failure."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await _load_user(creds.credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Like `get_current_user` but returns None instead of raising."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    return await _load_user(auth.split(" ", 1)[1], db)
