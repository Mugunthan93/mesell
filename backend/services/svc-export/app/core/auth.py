"""Authentication contract — JWT verification + ``get_current_user``.

Vendored from the monolith ``app.core.auth`` (BACKEND_ARCHITECTURE.md §4.B),
TRIMMED to the access-token VERIFICATION surface svc-export needs (A2 — each
service verifies the user JWT LOCALLY via the shared ``JWT_SECRET``).

The monolith's refresh-token machinery (opaque-token generation, HMAC-with-
pepper allowlist, the atomic rotation Lua script) is NOT vendored — svc-export
ISSUES no tokens (it has no ``/auth/*`` routes) and reads no
``REFRESH_TOKEN_PEPPER`` (absent from the trimmed Settings).  It only verifies
the access JWT presented on the 2 export routes and proves the ``sub`` resolves
to a live ``public.users`` row.

Kept surface:
* :class:`CurrentUser` — the immutable principal handed to route handlers.
* :class:`TokenMissingError` / :class:`TokenExpiredError` /
  :class:`UserNotFoundError` — the §4.B auth-exception hierarchy.
* :data:`oauth2_scheme` + :func:`get_current_user` — the canonical dep.

Locked rules (unchanged from monolith):
* HS256 only; verifier whitelist is ``[settings.JWT_ALGORITHM]`` (never "none").
* Access-token lifetime / claim shape is the monolith issuer's concern; this
  service only VERIFIES.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import MeesellError
from app.shared.config import settings
from app.shared.database import get_db
from app.shared.models.user import User

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CurrentUser — the shape every authenticated route receives.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CurrentUser:
    """Immutable principal handed to authenticated route handlers.

    V1 ships a single plan tier (``"free"``); the literal widens in V1.5.
    """

    user_id: UUID
    plan: Literal["free"]


# ─────────────────────────────────────────────────────────────────────────────
# Auth-exception hierarchy (subclasses of MeesellError per §4.F).
# ─────────────────────────────────────────────────────────────────────────────
class TokenMissingError(MeesellError):
    """Authorization header absent OR malformed → 401."""

    code = "auth.token_missing"
    status_code = 401
    validation_message_id = "auth.token_missing"

    def __init__(self, detail: str = "Authorization token missing or malformed") -> None:
        super().__init__(detail=detail)


class TokenExpiredError(MeesellError):
    """JWT decode returned ``jwt.ExpiredSignatureError`` → 401."""

    code = "auth.token_expired"
    status_code = 401
    validation_message_id = "auth.token_expired"

    def __init__(self, detail: str = "Access token has expired") -> None:
        super().__init__(detail=detail)


class UserNotFoundError(MeesellError):
    """Decoded ``sub`` does NOT resolve to a ``users`` row → 403."""

    code = "auth.user_not_found"
    status_code = 403
    validation_message_id = "auth.user_not_found"

    def __init__(self, detail: str = "Authenticated user no longer exists") -> None:
        super().__init__(detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# OAuth2 scheme — auto_error=False so we raise typed errors.
# ─────────────────────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/otp/verify",
    auto_error=False,
)
"""FastAPI security scheme.  ``tokenUrl`` points at the monolith's OTP-verify
endpoint (the route that mints the access token); ``auto_error=False`` lets
:func:`get_current_user` raise :class:`TokenMissingError` rather than FastAPI's
default plain 401.
"""


def _decode_access_token(token: str) -> dict:
    """Decode an access JWT or raise the appropriate auth-exception."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise TokenMissingError() from exc


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Canonical authenticated-user dependency per §4.B.

    1. ``token is None`` → :class:`TokenMissingError`.
    2. Decode the JWT.  Expired → :class:`TokenExpiredError`; malformed →
       :class:`TokenMissingError`.
    3. Look up the ``users`` row for the decoded ``sub`` UUID.  Missing →
       :class:`UserNotFoundError`.
    4. Return :class:`CurrentUser`.
    """
    if token is None:
        raise TokenMissingError()

    payload = _decode_access_token(token)

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise TokenMissingError("Token subject is not a valid UUID") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise UserNotFoundError()

    plan_claim: Literal["free"] = "free"  # V1 narrow per §4.B
    return CurrentUser(user_id=user_id, plan=plan_claim)


__all__ = [
    "CurrentUser",
    "TokenMissingError",
    "TokenExpiredError",
    "UserNotFoundError",
    "oauth2_scheme",
    "get_current_user",
]
