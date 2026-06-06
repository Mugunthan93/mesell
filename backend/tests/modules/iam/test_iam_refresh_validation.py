"""Unit test §7.J #2 — refresh validation under the 4 locked cases.

Per BACKEND_ARCHITECTURE.md §7.J unit 2:

    "Refresh validation under 4 cases — valid (rotation succeeds),
    expired (Lua returns nil, 401), revoked (post-logout, Lua returns
    nil, 401), already-rotated (replay attack: old cookie after refresh,
    Lua returns nil, 401)."

Each case exercises the Lua-atomic rotation primitive through the service.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.core.auth import (
    issue_refresh_token,
    refresh_allowlist_key,
)
from app.modules.iam import service as iam_service
from app.modules.iam.exceptions import RefreshInvalidError
from app.shared.config import settings


pytestmark = pytest.mark.asyncio


async def _seed_verified_user(db_engine, valkey, phone: str = "+919876543210"):
    """Helper — drive a single verify_otp_and_issue_tokens to seed state.

    Returns ``(refresh_token, user_id)``.  Skips the MSG91 dispatch by
    pre-populating the OTP record directly.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    otp = "111222"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})
    await valkey.set(f"otp:{phone}", payload, ex=300)

    async with Session() as db:
        result = await iam_service.verify_otp_and_issue_tokens(
            phone=phone, otp=otp, client_ip="198.51.100.1", db=db, valkey=valkey
        )
    return result.refresh_token


async def test_refresh_case_a_valid_rotation_succeeds(db_engine, use_live_valkey):
    """Case A — present a fresh valid cookie → rotation succeeds."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.shared import valkey as _vk_mod

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    valkey = await _vk_mod.get_valkey_otp()

    refresh_token = await _seed_verified_user(db_engine, valkey)

    async with Session() as db:
        result = await iam_service.rotate_refresh_token(
            refresh_token, "198.51.100.2", db, valkey
        )

    assert result.access_token
    assert result.new_refresh_token
    assert result.new_refresh_token != refresh_token
    # Old key gone; new key present.
    assert await valkey.get(refresh_allowlist_key(refresh_token)) is None
    assert await valkey.get(refresh_allowlist_key(result.new_refresh_token)) is not None


async def test_refresh_case_b_expired_returns_401(db_engine, use_live_valkey):
    """Case B — Lua sees no key (expired) → RefreshInvalidError."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.shared import valkey as _vk_mod

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    valkey = await _vk_mod.get_valkey_otp()

    # Issue a token but DO NOT populate the allowlist — simulates expiry.
    orphan_token = issue_refresh_token()

    async with Session() as db:
        with pytest.raises(RefreshInvalidError):
            await iam_service.rotate_refresh_token(orphan_token, "198.51.100.3", db, valkey)


async def test_refresh_case_c_revoked_returns_401(db_engine, use_live_valkey):
    """Case C — logout DELs the entry; subsequent refresh is invalid."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.shared import valkey as _vk_mod

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    valkey = await _vk_mod.get_valkey_otp()

    refresh_token = await _seed_verified_user(db_engine, valkey)

    # Revoke (server-side logout).
    revoke_result = await iam_service.revoke_refresh_token(refresh_token, valkey)
    assert revoke_result.cookie_was_present
    assert revoke_result.user_id is not None

    # Subsequent refresh must 401.
    async with Session() as db:
        with pytest.raises(RefreshInvalidError):
            await iam_service.rotate_refresh_token(
                refresh_token, "198.51.100.4", db, valkey
            )


async def test_refresh_case_d_replay_after_rotation_returns_401(
    db_engine, use_live_valkey
):
    """Case D — rotate once; replay the OLD cookie → RefreshInvalidError."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.shared import valkey as _vk_mod

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    valkey = await _vk_mod.get_valkey_otp()

    old_token = await _seed_verified_user(db_engine, valkey)

    # First rotation — succeeds.
    async with Session() as db:
        first = await iam_service.rotate_refresh_token(old_token, "198.51.100.5", db, valkey)
    assert first.new_refresh_token

    # Replay the OLD token — should now 401.
    async with Session() as db:
        with pytest.raises(RefreshInvalidError):
            await iam_service.rotate_refresh_token(old_token, "198.51.100.6", db, valkey)
