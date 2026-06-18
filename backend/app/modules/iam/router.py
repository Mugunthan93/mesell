"""``iam`` router — 6 endpoint handlers per §7.B (LOCKED 2026-06-05).

Endpoints
---------
1. ``POST /api/v1/auth/otp/send``      — Feature 1 phone OTP send
2. ``POST /api/v1/auth/otp/verify``    — Feature 1 phone OTP verify + JWT issue
3. ``POST /api/v1/auth/refresh``       — FE-D5 silent refresh
4. ``POST /api/v1/auth/logout``        — FE-D5 server-side revocation
5. ``GET  /api/v1/auth/me``            — JWT introspection
6. ``POST /api/v1/webhooks/razorpay``  — V1 capture-only webhook

Rate limits (per §7.I + deviation #2 doc'd to master)
------------------------------------------------------
§7.B prose specifies ``rate_limit(scope, limit="3/h", key="phone")`` etc.
The Wave 1 ``rate_limit`` decorator at
``app/core/middleware/rate_limit_mw.py`` exposes ``rate_limit(scope, limit:
int, window: int)`` — no ``key=`` parameter.  Effective semantics with the
existing decorator:

  * authenticated routes → keyed per ``user_id``;
  * anonymous routes (the four ``/auth/*`` ones below) → keyed per IP.

So ``otp_send`` 3/h and ``otp_verify`` 10/h here are per-IP, not per-phone.
Per-phone keying is a §V1.5 enhancement to the decorator API.

Cookie format (locked per §4.B FE-D5 amendment)
-----------------------------------------------
``Set-Cookie: refresh_token=<value>; Domain=.mesell.xyz; Path=/api/v1/auth;
HttpOnly; Secure; SameSite=Strict; Max-Age=<TTL>``
(production values; dev omits Domain and Secure — see settings.COOKIE_DOMAIN /
COOKIE_SECURE)
(or Max-Age=0 with empty value to clear on failure/logout).
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.rate_limit_mw import rate_limit
from app.modules.iam import service as iam_service
from app.modules.iam.schemas import (
    GoogleVerifyRequest,
    GoogleVerifyResponse,
    MeResponse,
    RefreshResponse,
    SendOtpRequest,
    SendOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
    WebhookCaptureResponse,
)
from app.shared.config import settings
from app.shared.database import get_db
from app.shared.valkey import get_valkey_otp

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Cookie constants (locked per §4.B FE-D5 amendment + §7.B.2 / §7.B.3 / §7.B.4)
# ─────────────────────────────────────────────────────────────────────────────
_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    """Attach the locked-format refresh cookie to ``response``.

    Domain + Secure are environment-dependent (``settings.COOKIE_DOMAIN`` /
    ``settings.COOKIE_SECURE``): prod = ``.mesell.xyz`` + Secure; local-http dev
    omits both.  HttpOnly + SameSite=Strict are FE-D5 security-critical and
    always on, never configurable.
    """
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        path=_REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Idempotent clear-cookie header per §7.B.3 / §7.B.4.

    Domain MUST match the set-cookie's Domain or the browser will not clear it,
    so this mirrors ``_set_refresh_cookie``'s env-dependent Domain/Secure.
    """
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        path=_REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1", tags=["iam"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /auth/otp/send  — §7.B.1
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/auth/otp/send",
    response_model=SendOtpResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a 6-digit OTP to a phone number",
)
@rate_limit(scope="otp_send", limit=3, window=3600)
async def otp_send(
    payload: SendOtpRequest,
    valkey: Annotated[Redis, Depends(get_valkey_otp)],
) -> SendOtpResponse:
    """§7.B.1 contract.  Per-IP rate limit 3/h (decorator key="phone" is a §V1.5 ask)."""
    result = await iam_service.send_otp_for_login(payload.phone, valkey)
    return SendOtpResponse(request_id=result.request_id)


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST /auth/otp/verify  — §7.B.2  (FE-D5 split-token)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/auth/otp/verify",
    response_model=VerifyOtpResponse,
    summary="Verify OTP, mint access JWT, set refresh cookie",
)
@rate_limit(scope="otp_verify", limit=10, window=3600)
async def otp_verify(
    payload: VerifyOtpRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    valkey: Annotated[Redis, Depends(get_valkey_otp)],
) -> VerifyOtpResponse:
    """§7.B.2 contract — issues access JWT (body) + refresh cookie (Set-Cookie)."""
    client_ip = request.client.host if request.client else "unknown"
    result = await iam_service.verify_otp_and_issue_tokens(
        payload.phone, payload.otp, client_ip, db, valkey
    )
    _set_refresh_cookie(response, result.refresh_token, result.refresh_expires_in)
    return VerifyOtpResponse(
        access_token=result.access_token,
        expires_in=result.access_expires_in,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. POST /auth/refresh  — §7.B.3  (Lua-atomic rotation)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/auth/refresh",
    response_model=RefreshResponse,
    summary="Atomically rotate refresh cookie and issue a new access JWT",
)
@rate_limit(scope="auth_refresh", limit=60, window=3600)
async def auth_refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    valkey: Annotated[Redis, Depends(get_valkey_otp)],
    refresh_token: Annotated[Optional[str], Cookie()] = None,
) -> RefreshResponse:
    """§7.B.3 contract.  On any 401 path the failure handler ALSO clears the cookie.

    The 401-path clear-cookie behaviour is implemented via a try/except so
    the §7.B.3 "clear cookie on 401" requirement is honoured without relying
    on the global error handler (which has no view of this route's
    ``response`` instance).
    """
    from app.modules.iam.exceptions import RefreshInvalidError

    client_ip = request.client.host if request.client else "unknown"
    try:
        result = await iam_service.rotate_refresh_token(
            refresh_token, client_ip, db, valkey
        )
    except RefreshInvalidError:
        # Per §7.B.3 failure path — clear the (possibly stale) cookie too.
        _clear_refresh_cookie(response)
        raise

    _set_refresh_cookie(response, result.new_refresh_token, result.refresh_expires_in)
    return RefreshResponse(
        access_token=result.access_token,
        expires_in=result.access_expires_in,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. POST /auth/logout  — §7.B.4  (idempotent)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the refresh cookie (idempotent)",
)
async def auth_logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    valkey: Annotated[Redis, Depends(get_valkey_otp)],
    refresh_token: Annotated[Optional[str], Cookie()] = None,
) -> Response:
    """§7.B.4 contract.  No rate limit (idempotent, no abuse vector).

    Always returns 204 + clear-cookie, regardless of whether a cookie was
    present.  The audit row is emitted by the service ONLY when a cookie
    was actually present (so calling logout twice does not double-log).
    """
    await iam_service.revoke_refresh_token(refresh_token, valkey, db=db)
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /auth/me  — §7.B.5  (introspection)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/auth/me",
    response_model=MeResponse,
    summary="Return the authenticated user's profile",
)
async def me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    """§7.B.5 contract.  No rate limit (per-IP DDoS guard is the floor).

    No audit event per documented absence — the JWT itself proves the user
    is active; logging every ``/me`` would flood the table.

    ``onboarding_complete`` is a CUSTOMER-domain fact, sourced cleanly through
    the customer module's public service surface
    (:func:`customer.service.get_onboarding_completeness` — the same seam
    ``dashboard.service`` uses).  No customer ORM model is imported into iam.
    For a brand-new seller with no profile row yet, that surface returns
    ``onboarding_complete=False`` without raising (per customer §8.F), so the
    pre-onboarding case is handled by the callee, not here.
    """
    # Function-level import: keeps the customer dependency off iam's
    # module-load path (no circular import — customer does not import iam).
    from app.modules.customer import service as customer_service

    profile = await iam_service.get_profile(user.user_id, db)
    completeness = await customer_service.get_onboarding_completeness(
        user.user_id, db
    )
    return MeResponse(
        user_id=profile.user_id,
        phone=profile.phone,
        plan="free",  # V1 narrow per §4.B CurrentUser
        created_at=profile.created_at,
        last_login_at=profile.last_login_at,
        onboarding_complete=completeness.onboarding_complete,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. POST /webhooks/razorpay  — §7.B.6  (V1 capture only)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/webhooks/razorpay",
    response_model=WebhookCaptureResponse,
    summary="Capture a Razorpay webhook (V1: signature-verify + log)",
)
async def razorpay_webhook(request: Request) -> WebhookCaptureResponse:
    """§7.B.6 contract.

    The body is read as RAW bytes (NOT JSON-parsed at the FastAPI dependency
    layer) — Pydantic parsing happens only AFTER HMAC signature verification
    succeeds, per the V1 capture-only posture.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get(
        "x-razorpay-signature", ""
    )
    # Service call drives signature verify + audit capture; the response is
    # always 200 ``captured=True`` on success.  Any failure raises a typed
    # ``MeesellError`` subclass which the §4.F handler translates into the
    # 401 / 400 envelope.
    await iam_service.capture_razorpay_webhook(raw_body, signature)
    return WebhookCaptureResponse(captured=True)


# ─────────────────────────────────────────────────────────────────────────────
# 7. POST /auth/google/verify  — google-auth feature (design §C)
# ─────────────────────────────────────────────────────────────────────────────
# Mounted on a SEPARATE router so main.py can gate its inclusion on
# FEATURE_GOOGLE_AUTH_ENABLED — when the flag is off the route is NOT mounted
# (404), keeping the OpenAPI surface + §17 count at 28 until enabled per env.
google_router = APIRouter(prefix="/api/v1", tags=["iam"])


@google_router.post(
    "/auth/google/verify",
    response_model=GoogleVerifyResponse,
    summary="Verify a Google ID-token, mint access JWT, set refresh cookie",
)
@rate_limit(scope="google_verify", limit=20, window=3600)
async def google_verify(
    payload: GoogleVerifyRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    valkey: Annotated[Redis, Depends(get_valkey_otp)],
) -> GoogleVerifyResponse:
    """google-auth §C contract — verify a Google ID-token, issue our own
    access JWT (body) + refresh cookie (Set-Cookie), byte-identical to the
    OTP-verify path.  Per-IP rate limit 20/h (no SMS cost; abuse floor only).
    """
    client_ip = request.client.host if request.client else "unknown"
    result = await iam_service.verify_google_and_issue_tokens(
        payload.credential, client_ip, db, valkey
    )
    _set_refresh_cookie(response, result.refresh_token, result.refresh_expires_in)
    return GoogleVerifyResponse(
        access_token=result.access_token,
        expires_in=result.access_expires_in,
    )


__all__ = ["router", "google_router"]
