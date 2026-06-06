"""Unit tests for ``app.core.auth`` per the §4.B locked contract.

These tests do NOT touch the database or Valkey directly — ``db`` is mocked
via ``MagicMock(spec=AsyncSession)`` with an awaitable ``db.get(...)``.  The
JWT secret + algorithm are read from ``settings`` (loaded from the test
``.env`` defaults in ``conftest.py``).
"""

from __future__ import annotations

import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    CurrentUser,
    TokenExpiredError,
    TokenMissingError,
    UserNotFoundError,
    compare_tokens,
    get_current_user,
    issue_access_token,
    issue_refresh_token,
    refresh_allowlist_key,
)
from app.shared.config import settings
from app.shared.models.user import User


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_user(user_id: uuid.UUID, plan: str = "free") -> User:
    """Build a User ORM instance without committing to a DB.

    We only need attribute access for the unit-test assertions, not the
    SQLAlchemy session mapping — ``User()`` initialises columns from
    server-defaults to None which is fine here.
    """
    u = User()
    u.id = user_id
    u.phone = "+919999999999"
    u.plan = plan
    return u


def _mock_db_returning(user: User | None) -> AsyncSession:
    """Build a MagicMock AsyncSession whose ``get(User, ...)`` returns ``user``."""
    db = MagicMock(spec=AsyncSession)
    db.get = AsyncMock(return_value=user)
    return db


# ─────────────────────────────────────────────────────────────────────────────
# 1. issue_access_token — claim shape verification (§4.B)
# ─────────────────────────────────────────────────────────────────────────────


def test_issue_access_token_claim_shape() -> None:
    """Token must carry ``sub`` (str(uuid)), ``plan``, ``exp`` in the future, HS256.

    Per §4.B the access JWT payload is ``{sub: str(user_id), exp: int,
    plan: str}`` with algorithm HS256 and lifetime
    ``settings.ACCESS_TOKEN_TTL_SECONDS``.
    """
    user_id = uuid.uuid4()
    before = datetime.now(timezone.utc)
    token = issue_access_token(user_id, plan="free")

    # Inspect the unverified header to confirm the algorithm.
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "HS256", "JWT alg must be HS256 per §4.B"

    # Decode with verification — proves the secret is correct AND the
    # signature is valid.
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == str(user_id), "sub must be the str-form of the UUID"
    assert payload["plan"] == "free", "plan claim missing or wrong"
    assert "exp" in payload, "exp claim is mandatory per §4.B"

    # exp must be in the future and within (now, now + TTL + slack).
    exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert exp_dt > before, "exp must be in the future at issuance"
    expected_ttl = timedelta(seconds=settings.ACCESS_TOKEN_TTL_SECONDS)
    assert exp_dt <= before + expected_ttl + timedelta(seconds=5)


# ─────────────────────────────────────────────────────────────────────────────
# 2. issue_refresh_token — opaque, URL-safe, unique (§4.B FE-D5)
# ─────────────────────────────────────────────────────────────────────────────


def test_issue_refresh_token_is_opaque_urlsafe() -> None:
    """``secrets.token_urlsafe(48)`` yields a >=60-char URL-safe string.

    Per §4.B FE-D5 amendment, the refresh token is opaque (NOT a JWT) and
    generated via ``secrets.token_urlsafe(48)``.  This test verifies length,
    charset, and uniqueness.
    """
    allowed = set(string.ascii_letters + string.digits + "-_")

    tokens = {issue_refresh_token() for _ in range(20)}
    assert len(tokens) == 20, "20 calls must yield 20 distinct tokens"

    for tok in tokens:
        # ``secrets.token_urlsafe(48)`` -> base64-urlsafe of 48 bytes -> ~64 chars
        # without padding.  We assert >= 60 to allow for the small rstrip
        # padding variations on the boundary.
        assert len(tok) >= 60, f"refresh token too short: {len(tok)}"
        assert set(tok) <= allowed, f"non-URL-safe chars in token: {tok}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. refresh_allowlist_key — HMAC-SHA256 with pepper (§4.B FE-D5)
# ─────────────────────────────────────────────────────────────────────────────


def test_refresh_allowlist_key_uses_hmac_pepper(monkeypatch) -> None:
    """Key format is ``cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}``.

    We monkey-patch the pepper to a known value, compute the expected HMAC by
    hand, and verify the helper returns the exact same hex digest in the
    locked key namespace.
    """
    import hashlib
    import hmac as hmac_mod

    known_pepper = "unit-test-pepper-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    monkeypatch.setattr(settings, "REFRESH_TOKEN_PEPPER", known_pepper)

    token = "test-refresh-token-value-abc123"
    expected_digest = hmac_mod.new(
        known_pepper.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expected_key = f"cache:refresh:{expected_digest}"

    actual = refresh_allowlist_key(token)
    assert actual == expected_key, f"key mismatch: got {actual!r}, want {expected_key!r}"

    # Also assert the key namespace is exactly ``cache:refresh:`` (no drift).
    assert actual.startswith("cache:refresh:"), "wrong allowlist key namespace"


# ─────────────────────────────────────────────────────────────────────────────
# 4. compare_tokens — constant-time equality (§4.B FE-D5)
# ─────────────────────────────────────────────────────────────────────────────


def test_compare_tokens_constant_time() -> None:
    """``compare_tokens`` delegates to :func:`secrets.compare_digest`.

    We can't directly observe timing behaviour in a unit test, but we CAN
    verify the helper returns True only for full equality (prefix matches
    must return False — a property of ``compare_digest`` that ``==`` also
    has, but this guards against an accidental ``startswith`` regression).
    """
    a = "abc-123-xyz"
    assert compare_tokens(a, a) is True

    # Prefix mismatch
    assert compare_tokens(a, "abc-123-xy") is False
    # Suffix mismatch
    assert compare_tokens(a, "abc-123-xyZ") is False
    # Empty pair (both empty -> True; compare_digest convention)
    assert compare_tokens("", "") is True
    # One-empty
    assert compare_tokens("", "a") is False

    # Sanity: the implementation must actually call ``secrets.compare_digest``
    # — patch it and verify our helper goes through.
    from unittest.mock import patch

    sentinel_arg_a = "ZZZ"
    sentinel_arg_b = "YYY"
    with patch.object(secrets, "compare_digest", return_value=True) as mock_cd:
        result = compare_tokens(sentinel_arg_a, sentinel_arg_b)
    assert result is True
    mock_cd.assert_called_once_with(sentinel_arg_a, sentinel_arg_b)


# ─────────────────────────────────────────────────────────────────────────────
# 5. get_current_user — happy path
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_happy_path() -> None:
    """Valid token + DB returns user → CurrentUser with matching id + plan='free'."""
    user_id = uuid.uuid4()
    token = issue_access_token(user_id, plan="free")
    db = _mock_db_returning(_make_user(user_id, plan="free"))

    result = await get_current_user(token=token, db=db)

    assert isinstance(result, CurrentUser)
    assert result.user_id == user_id
    assert result.plan == "free"
    db.get.assert_awaited_once_with(User, user_id)


# ─────────────────────────────────────────────────────────────────────────────
# 6. get_current_user — missing token (no Authorization header)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_missing_token() -> None:
    """``token=None`` (no Authorization header) raises ``TokenMissingError``.

    Per §4.B: status 401, ``validation_message_id="auth.token_missing"``.
    """
    db = _mock_db_returning(None)

    with pytest.raises(TokenMissingError) as excinfo:
        await get_current_user(token=None, db=db)

    err = excinfo.value
    assert err.status_code == 401
    assert err.validation_message_id == "auth.token_missing"
    # DB must NOT have been hit — the early bail-out at the dep entrance.
    db.get.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 7. get_current_user — expired token
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_expired_token() -> None:
    """Token whose ``exp`` is in the past raises ``TokenExpiredError`` → 401 expired."""
    user_id = uuid.uuid4()
    past = datetime.now(timezone.utc) - timedelta(seconds=120)
    token = jwt.encode(
        {"sub": str(user_id), "exp": past, "plan": "free"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    db = _mock_db_returning(_make_user(user_id))

    with pytest.raises(TokenExpiredError) as excinfo:
        await get_current_user(token=token, db=db)

    err = excinfo.value
    assert err.status_code == 401
    assert err.validation_message_id == "auth.token_expired"
    db.get.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 8. get_current_user — malformed token
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_malformed_token() -> None:
    """Garbage string → ``TokenMissingError`` (§4.B mapping: malformed → token_missing).

    The contract says missing/malformed → 401 ``auth.token_missing``.  Both
    paths raise the same exception class so the client sees one consistent
    "obtain a new token via OTP-verify" signal.
    """
    db = _mock_db_returning(None)

    with pytest.raises(TokenMissingError) as excinfo:
        await get_current_user(token="this-is-not-a-jwt", db=db)

    err = excinfo.value
    assert err.status_code == 401
    assert err.validation_message_id == "auth.token_missing"
    db.get.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 9. get_current_user — unknown user (decoded sub not in DB)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_unknown_user() -> None:
    """Valid token but ``db.get`` returns None raises ``UserNotFoundError`` → 403."""
    user_id = uuid.uuid4()
    token = issue_access_token(user_id, plan="free")
    db = _mock_db_returning(None)  # row vanished between issuance and use

    with pytest.raises(UserNotFoundError) as excinfo:
        await get_current_user(token=token, db=db)

    err = excinfo.value
    assert err.status_code == 403
    assert err.validation_message_id == "auth.user_not_found"
    db.get.assert_awaited_once_with(User, user_id)
