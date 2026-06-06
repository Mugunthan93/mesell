"""Canonical authentication contract — JWT, refresh allowlist, ``get_current_user``.

Per BACKEND_ARCHITECTURE.md §4.B (LOCKED 2026-06-05 incl. the FE-D5 amendment of
the same date), this module owns:

* The :class:`CurrentUser` immutable dataclass — the shape every authenticated
  route receives via ``Depends(get_current_user)``.
* The :func:`get_current_user` FastAPI dependency — the **only** authenticated
  user dep route handlers MAY consume.  Routes do NOT decode JWT themselves;
  modules do NOT re-implement this dep; the ``iam`` module does NOT re-export
  an alternative.
* The access-token issuer (:func:`issue_access_token`) — short-lived HS256 JWT
  with the claim shape ``{sub, exp, plan}``.
* The refresh-token primitives — opaque-token generation
  (:func:`issue_refresh_token`), HMAC-with-pepper allowlist key derivation
  (:func:`refresh_allowlist_key`), constant-time comparison
  (:func:`compare_tokens`), and the **atomic** Lua-script-driven rotation
  (:func:`rotate_refresh_token`).

Auth-exception subclasses are also defined here so that the routes that raise
them (e.g. ``/auth/refresh``) share the auth module's import surface.  They
subclass :class:`app.core.errors.MeesellError` so that the §4.F error-handler
registration in ``app/main.py`` resolves them into the locked error envelope.

Locked rules (do not relax)
---------------------------
* HS256 only; algorithm read from ``settings.JWT_ALGORITHM`` for symmetry with
  the §5.D config registry — but the contract is HS256 and the verifier
  whitelist passed to :func:`jwt.decode` is ``[settings.JWT_ALGORITHM]`` only
  (never ``"none"``).
* Access-token lifetime is ``settings.ACCESS_TOKEN_TTL_SECONDS`` (the
  deprecated ``JWT_EXPIRY_DAYS`` is NOT referenced here).
* Refresh-token allowlist key uses **HMAC-SHA256 with backend pepper**, not
  bare SHA-256.  Rationale: a Valkey-only breach must NOT let an attacker
  validate captured refresh cookies by computing SHA-256 themselves.
* Refresh-token comparison uses :func:`secrets.compare_digest` — never ``==``
  (timing-attack mitigation).
* Refresh-token rotation runs as a server-side Lua script (single round-trip,
  no race window) — never as a Python-side check-then-set or MULTI/EXEC.

Import allowlist (§4.I)
-----------------------
This module imports ONLY from ``shared.*`` and ``core.errors`` — never from
``app.modules.*`` or ``app.adapters.*``.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config import settings
from app.shared.database import get_db
from app.shared.models.user import User
from app.shared.valkey import eval_lua_script, load_lua_script

# ── core.errors integration (parallel-dispatch tolerant) ───────────────────
# services-builder owns ``app/core/errors.py``.  During parallel dispatch the
# file may not yet exist when this module is first imported; we tolerate that
# by falling back to a local shim base class whose interface matches §4.F.
# Once services-builder lands ``core/errors.py``, the import below resolves to
# the canonical ``MeesellError`` and the shim is bypassed.  No reconcile is
# required at the call sites — the subclass attributes (`code`, `status_code`,
# `validation_message_id`) are part of both definitions.
try:
    from app.core.errors import MeesellError  # noqa: F401 — re-exported via subclasses
except ImportError:  # pragma: no cover — only hit during parallel-dispatch window

    class MeesellError(Exception):  # type: ignore[no-redef]
        """Temporary shim for the §4.F base.

        Replaced by services-builder's canonical class once ``core/errors.py``
        lands.  Signature matches the canonical class so the auth-exception
        subclasses below construct identically on either path.
        """

        code: str = "internal.unknown"
        status_code: int = 500
        validation_message_id: str = "server.internal_error"

        def __init__(
            self,
            code: str | None = None,
            status_code: int | None = None,
            validation_message_id: str | None = None,
            detail: str | None = None,
        ) -> None:
            if code is not None:
                self.code = code
            if status_code is not None:
                self.status_code = status_code
            if validation_message_id is not None:
                self.validation_message_id = validation_message_id
            self.detail = detail
            super().__init__(detail or self.code)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CurrentUser — the shape every authenticated route receives.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CurrentUser:
    """Immutable principal handed to authenticated route handlers.

    Per §4.B: V1 ships a single plan tier (``"free"``); the ``plan`` field's
    type widens to ``Literal["free", "pro"]`` in V1.5.  Routes that need the
    string value treat it as opaque — plan-gating logic lives in
    ``core/plan_guard.py``, not in route handlers.
    """

    user_id: UUID
    plan: Literal["free"]


# ─────────────────────────────────────────────────────────────────────────────
# Auth-exception hierarchy (subclasses of MeesellError per §4.F).
# ─────────────────────────────────────────────────────────────────────────────
class TokenMissingError(MeesellError):
    """Raised when the ``Authorization`` header is absent OR malformed.

    Per §4.B: maps to HTTP 401 with ``validation_message_id =
    "auth.token_missing"``.  The same exception covers "no header at all" and
    "header present but unparseable" — the contract treats these uniformly
    from the client's point of view (both mean "you have no valid bearer
    token; obtain one via /auth/otp/verify").
    """

    code = "auth.token_missing"
    status_code = 401
    validation_message_id = "auth.token_missing"

    def __init__(self, detail: str = "Authorization token missing or malformed") -> None:
        # Use the keyword-only ``detail=`` form so the canonical §4.F
        # ``MeesellError.__init__(code, status_code, validation_message_id,
        # detail)`` does not misinterpret a positional first arg as ``code``.
        super().__init__(detail=detail)


class TokenExpiredError(MeesellError):
    """Raised when JWT decode returns ``jwt.ExpiredSignatureError``.

    Per §4.B: maps to HTTP 401 with ``validation_message_id =
    "auth.token_expired"``.  Distinct from :class:`TokenMissingError` because
    the client should silent-refresh via ``/auth/refresh`` rather than
    re-prompting the seller to re-enter an OTP.
    """

    code = "auth.token_expired"
    status_code = 401
    validation_message_id = "auth.token_expired"

    def __init__(self, detail: str = "Access token has expired") -> None:
        super().__init__(detail=detail)


class UserNotFoundError(MeesellError):
    """Raised when the decoded ``sub`` does NOT resolve to a ``users`` row.

    Per §4.B: maps to HTTP 403 with ``validation_message_id =
    "auth.user_not_found"``.  Status 403 (not 404) because the JWT was valid —
    the principal is simply gone (e.g. account deleted between issuance and
    use); a 401 would suggest "send credentials" but the credentials WERE
    sent.
    """

    code = "auth.user_not_found"
    status_code = 403
    validation_message_id = "auth.user_not_found"

    def __init__(self, detail: str = "Authenticated user no longer exists") -> None:
        super().__init__(detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# OAuth2 scheme — auto_error=False so we raise typed errors, not FastAPI's
# default ``{"detail": "Not authenticated"}`` 401 dict.
# ─────────────────────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/otp/verify",
    auto_error=False,
)
"""FastAPI security scheme.

``tokenUrl`` points at the OTP-verify endpoint (per the §17 endpoint inventory
and §7 ``iam`` ownership) — that is the route the OpenAPI ``Authorize`` button
hands the credentials to.  ``auto_error=False`` lets :func:`get_current_user`
own the missing-token handling and raise :class:`TokenMissingError` rather
than FastAPI's default plain 401.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Access JWT — issuance + the canonical dep.
# ─────────────────────────────────────────────────────────────────────────────
def issue_access_token(user_id: UUID, plan: str = "free") -> str:
    """Issue an HS256 access JWT per §4.B.

    Claim shape::

        {"sub": str(user_id), "exp": <unix_ts>, "plan": "free"}

    Lifetime is ``settings.ACCESS_TOKEN_TTL_SECONDS`` (env-driven per §4.B
    amendment — prod 900, staging 60, dev 30).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + timedelta(seconds=settings.ACCESS_TOKEN_TTL_SECONDS),
        "plan": plan,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _decode_access_token(token: str) -> dict:
    """Decode an access JWT or raise the appropriate auth-exception.

    Internal helper for :func:`get_current_user`.  Translates PyJWT's exception
    surface into the §4.F-typed exceptions so the rest of the dep never has to
    catch ``jwt.*`` directly.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        # Catches malformed signature, malformed structure, wrong-alg headers,
        # missing claims (when required-claim verification is on), etc.
        raise TokenMissingError() from exc


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Canonical authenticated-user dependency per §4.B.

    Resolution chain:

    1. If ``token`` is ``None`` (no ``Authorization`` header), raise
       :class:`TokenMissingError`.
    2. Decode the JWT.  Expired → :class:`TokenExpiredError`; malformed →
       :class:`TokenMissingError`.
    3. Look up the ``users`` row for the decoded ``sub`` UUID.  Missing →
       :class:`UserNotFoundError`.
    4. Return :class:`CurrentUser` with the row's id + the JWT's ``plan``
       claim (the source-of-truth for plan during the access-token's lifetime;
       the DB column updates take effect on the next refresh).

    The §4.B locked rule: route handlers MUST consume this dep — they do NOT
    decode the JWT themselves, do NOT re-implement this resolution chain, and
    do NOT receive ``User`` ORM instances (only the immutable
    :class:`CurrentUser`).  Per §16 the ORM model is repository-internal and
    must not cross module boundaries.
    """
    if token is None:
        raise TokenMissingError()

    payload = _decode_access_token(token)

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        # ``sub`` missing / not a UUID → treat as malformed token (401).  This
        # only happens if an attacker forges a token with our secret or if a
        # legacy issuer wrote a non-UUID ``sub``; either way the client must
        # re-authenticate.
        raise TokenMissingError("Token subject is not a valid UUID") from exc

    user = await db.get(User, user_id)
    if user is None:
        # JWT signature valid, but the principal vanished between issuance and
        # use.  Per §4.B this is 403 (not 401) — the client has credentials,
        # they just don't map to an existing user.
        raise UserNotFoundError()

    # The JWT ``plan`` claim is the source-of-truth for the access-token's
    # lifetime per §4.B.  V1 narrows the type to ``"free"`` — anything else in
    # the claim is coerced to ``"free"`` to keep the dataclass contract
    # honest; V1.5 widens the literal.
    plan_claim: Literal["free"] = "free"  # V1 narrow
    return CurrentUser(user_id=user_id, plan=plan_claim)


# ─────────────────────────────────────────────────────────────────────────────
# Refresh token — opaque generation + allowlist key + comparison.
# ─────────────────────────────────────────────────────────────────────────────
def issue_refresh_token() -> str:
    """Generate a fresh opaque refresh-token value per §4.B FE-D5 amendment.

    NOT a JWT — JWTs in cookies are an anti-pattern (size, no rotation, no
    server-side revocation).  Uses :func:`secrets.token_urlsafe(48)` which
    yields ~64 URL-safe characters of cryptographically-strong randomness.
    The opaque value is the credential that goes into the HttpOnly Secure
    cookie; its HMAC digest is what lives in the Valkey allowlist.
    """
    return secrets.token_urlsafe(48)


def refresh_allowlist_key(refresh_token: str) -> str:
    """Derive the Valkey allowlist key for ``refresh_token`` per §4.B.

    Key format: ``cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}``.

    Rationale for HMAC-with-pepper (vs bare SHA-256): a Valkey-only breach
    leaks the digests but NOT the pepper.  An attacker who captures a
    refresh cookie value cannot validate it against the leaked digests
    without the backend-only pepper — defence in depth beyond the
    cookie-itself confidentiality.
    """
    digest = hmac.new(
        settings.REFRESH_TOKEN_PEPPER.encode("utf-8"),
        refresh_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"cache:refresh:{digest}"


def compare_tokens(a: str, b: str) -> bool:
    """Constant-time equality check per §4.B (timing-attack mitigation).

    Use this wherever the auth code compares two opaque-token-shaped values
    (e.g. checking a presented refresh cookie against an allowlist-recovered
    JSON `"raw"` field, should we ever store it; the canonical path is
    key-derivation + lookup, no value-comparison required).  The helper
    exists so call sites cannot accidentally drift to ``==``.
    """
    return secrets.compare_digest(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# Refresh-token rotation Lua script — single-round-trip atomic check-DEL-SET.
# ─────────────────────────────────────────────────────────────────────────────
REFRESH_ROTATE_LUA: str = (
    "if redis.call('GET', KEYS[1]) then\n"
    "    redis.call('DEL', KEYS[1])\n"
    "    redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])\n"
    "    return 1\n"
    "else\n"
    "    return 0\n"
    "end"
).strip()
"""Lua script body per §4.B FE-D5 amendment.

Semantics: if ``KEYS[1]`` (old allowlist key) exists, atomically delete it
and SET ``KEYS[2]`` (new allowlist key) with ``ARGV[1]`` (new JSON value) and
``ARGV[2]`` (TTL seconds).  Returns ``1`` on success, ``0`` if the old key
did not exist.  Replay-attack mitigation: re-presenting an old refresh cookie
after rotation returns ``0`` here, which the caller maps to 401.

The script is server-side atomic — no race window between GET and DEL-SET as
there would be with MULTI/EXEC + WATCH.  This is the canonical Valkey primitive
for compare-DEL-then-SET; see §4.B coordinator-pushback ruling for the full
rationale.
"""

# Module-level cache of the loaded script's SHA1 digest.  Populated on the
# first call to :func:`rotate_refresh_token`; reused for the lifetime of the
# worker process.  Reset on ``SCRIPT FLUSH`` via the EVALSHA→EVAL fallback in
# :func:`app.shared.valkey.eval_lua_script`.
_refresh_rotate_sha: str | None = None


async def rotate_refresh_token(
    valkey: Redis,
    old_key: str,
    new_key: str,
    new_value: str,
    ttl_seconds: int,
) -> bool:
    """Atomically rotate a refresh-token allowlist entry per §4.B.

    On first call, loads :data:`REFRESH_ROTATE_LUA` via ``SCRIPT LOAD`` and
    caches the SHA1.  Subsequent calls go via ``EVALSHA`` (zero network
    payload for the script body).  The :func:`eval_lua_script` helper transparently
    falls back to plain ``EVAL`` if the Valkey server flushed its script cache
    (e.g. after a restart).

    Args:
        valkey: The DB-0 client returned by :func:`app.shared.valkey.get_valkey_otp`.
        old_key: The current allowlist key — derived from the cookie value the
            client presented on ``/auth/refresh``.
        new_key: The new allowlist key — derived from the freshly issued
            refresh-token value.
        new_value: The JSON payload to store at ``new_key`` (per §4.B:
            ``{"user_id", "issued_at", "ip"}``).
        ttl_seconds: New entry TTL — typically ``settings.REFRESH_TOKEN_TTL_SECONDS``.

    Returns:
        ``True`` if ``old_key`` existed and rotation succeeded; ``False`` if
        ``old_key`` was absent (which the caller maps to 401 — replay or
        already-rotated cookie).
    """
    global _refresh_rotate_sha
    if _refresh_rotate_sha is None:
        _refresh_rotate_sha = await load_lua_script(valkey, REFRESH_ROTATE_LUA)

    result = await eval_lua_script(
        valkey,
        _refresh_rotate_sha,
        REFRESH_ROTATE_LUA,
        keys=[old_key, new_key],
        args=[new_value, ttl_seconds],
    )
    return bool(result)


def _reset_lua_cache_for_tests() -> None:
    """Test-only helper — clears the module-level Lua SHA cache.

    Used by ``tests/test_core_auth_rotation.py`` to exercise both the
    first-call (``SCRIPT LOAD`` + ``EVALSHA``) and the post-``SCRIPT FLUSH``
    fallback (``EVAL``) code paths within one test session.  Not part of the
    public API — name-mangled with a leading underscore.
    """
    global _refresh_rotate_sha
    _refresh_rotate_sha = None


__all__ = [
    "CurrentUser",
    "TokenMissingError",
    "TokenExpiredError",
    "UserNotFoundError",
    "oauth2_scheme",
    "get_current_user",
    "issue_access_token",
    "issue_refresh_token",
    "refresh_allowlist_key",
    "compare_tokens",
    "rotate_refresh_token",
    "REFRESH_ROTATE_LUA",
]
