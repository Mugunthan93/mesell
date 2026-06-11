"""Integration §7.J #1 — full silent-refresh flow.

Per BACKEND_ARCHITECTURE.md §7.J integration 1:

    "Full silent-refresh flow — verify → short wait (well under
    ACCESS_TOKEN_TTL_SECONDS staging=60s) → refresh → old access still
    valid until its `exp` (the new access has fresh `exp`; the old one
    isn't revoked — the access token has no allowlist, only refresh does)."

Drives the routes via the FastAPI test client (httpx).  Requires:
  * Postgres at the conftest TEST_DATABASE_URL.
  * Valkey at CORE_TEST_VALKEY_URL (default redis://localhost:6379) for
    the use_live_valkey factory.
  * MSG91 mocked at module level so no real OTP is dispatched.
"""

from __future__ import annotations

import hashlib
import json
import time

import jwt
import pytest

from app.adapters.msg91 import Msg91Response
from app.shared.config import settings

from tests.integration._cookie_helpers import extract_refresh_cookie


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_otp_in_valkey(phone: str, otp: str) -> None:
    """Bypass /otp/send: drop a known OTP record into Valkey directly."""
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})
    await valkey.set(f"otp:{phone}", payload, ex=300)


async def test_full_silent_refresh_flow(iam_client, use_live_valkey, monkeypatch):
    """End-to-end: verify → refresh → old access still decodes."""
    # ── Arrange ────────────────────────────────────────────────────────────
    phone = "+915550000101"
    otp = "424242"
    await _seed_otp_in_valkey(phone, otp)

    # MSG91 is not on the verify path, but if a stray /otp/send call ever
    # leaks, swap the dispatch for a stub so CI never reaches the vendor.
    async def _fake_send_otp(*args, **kwargs):
        return Msg91Response(success=True, request_id="test-req-id", message="")

    monkeypatch.setattr("app.adapters.msg91.send_otp", _fake_send_otp)

    # ── Step 1: verify (issues access JWT + refresh cookie) ────────────────
    r1 = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp},
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    old_access = body1["access_token"]
    assert body1["token_type"] == "bearer"
    refresh_v1 = extract_refresh_cookie(r1)
    assert refresh_v1, "verify must emit a refresh_token Set-Cookie"

    # ── Step 2: small in-loop wait, well under any TTL ─────────────────────
    # No real sleep needed — the access token's `exp` is `now + TTL`, so we
    # just verify decode succeeds immediately AND after refresh.
    decoded_old = jwt.decode(
        old_access,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert "sub" in decoded_old
    assert decoded_old["plan"] == "free"

    # ── Step 3: refresh (cookie carries the credential) ────────────────────
    # httpx's cookie jar drops the `.mesell.xyz`-domain cookie on a
    # `testserver` request — see ``_cookie_helpers``.  Forward the value
    # explicitly via the Cookie header.
    r2 = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_v1}"},
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    new_access = body2["access_token"]
    # NOTE: we do NOT assert ``new_access != old_access`` — when verify +
    # refresh land in the same wall-clock second the JWT payload is
    # bit-identical because §4.B does not include an ``iat`` claim
    # (CurrentUser shape is ``{sub, exp, plan}``).  What matters for the
    # silent-refresh contract is (a) the new token decodes, (b) the
    # claims still resolve to the same principal, (c) the new refresh
    # cookie is fresh (already exercised by the rotation Lua replay test).

    # ── Step 4: old access is still valid until its own exp ────────────────
    # The access token has NO allowlist — only refresh does.  Decoding it
    # again must still succeed.
    decoded_old_again = jwt.decode(
        old_access,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert decoded_old_again["sub"] == decoded_old["sub"]

    # ── Step 5: new access decodes with the same sub ───────────────────────
    decoded_new = jwt.decode(
        new_access,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert decoded_new["sub"] == decoded_old["sub"]
    assert decoded_new["exp"] >= decoded_old["exp"]
    # New refresh cookie MUST be present and fresh (locked at §7.B.3).
    refresh_v2 = extract_refresh_cookie(r2)
    assert refresh_v2 and refresh_v2 != refresh_v1
