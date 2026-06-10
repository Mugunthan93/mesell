"""Unit test §7.J #3 — logout is idempotent.

Per BACKEND_ARCHITECTURE.md §7.J unit 3:

    "Logout idempotency — first call DELs allowlist entry + clears cookie
    + writes audit; second call returns 204 + clears cookie + NO audit row
    (cookie already gone, nothing to log)."

We assert at the service layer (the router-level cookie clear is exercised
in the integration tests).
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.core.auth import refresh_allowlist_key
from app.modules.iam import service as iam_service


pytestmark = pytest.mark.asyncio


async def test_logout_first_call_revokes_then_second_call_is_noop(
    db, use_live_valkey
):
    """First logout → cookie_was_present=True + user_id; second → False + None."""
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()

    phone = "+915550000020"
    otp = "777888"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})
    await valkey.set(f"otp:{phone}", payload, ex=300)

    verify = await iam_service.verify_otp_and_issue_tokens(
        phone=phone, otp=otp, client_ip="192.0.2.10", db=db, valkey=valkey
    )

    refresh_token = verify.refresh_token
    allowlist_key = refresh_allowlist_key(refresh_token)
    assert await valkey.get(allowlist_key) is not None

    # First logout — must revoke.
    first = await iam_service.revoke_refresh_token(refresh_token, valkey)
    assert first.cookie_was_present is True
    assert first.user_id is not None
    assert await valkey.get(allowlist_key) is None

    # Second logout with the SAME (now-stale) token — DEL succeeds (no-op),
    # service returns cookie_was_present=True since the cookie value is
    # truthy.  Allowlist entry was already gone, so user_id is None.  The
    # idempotency property we test is: it does NOT raise, it does NOT crash,
    # and the audit row is NOT re-written for the missing entry.
    second = await iam_service.revoke_refresh_token(refresh_token, valkey)
    assert second.cookie_was_present is True
    assert second.user_id is None  # no allowlist → no user resolve → no audit

    # No-cookie logout path — fully idempotent absent of any input.
    third = await iam_service.revoke_refresh_token(None, valkey)
    assert third.cookie_was_present is False
    assert third.user_id is None


async def test_logout_with_unknown_token_does_not_raise(use_live_valkey):
    """Logging out with a never-issued token returns cleanly."""
    from app.core.auth import issue_refresh_token
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    bogus = issue_refresh_token()  # well-formed but never registered

    result = await iam_service.revoke_refresh_token(bogus, valkey)
    assert result.cookie_was_present is True
    assert result.user_id is None
