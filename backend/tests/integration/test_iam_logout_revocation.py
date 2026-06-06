"""Integration §7.J #2 — logout revocation.

Per BACKEND_ARCHITECTURE.md §7.J integration 2:

    "Logout revocation — verify → logout → refresh → 401 `auth.refresh.invalid`
    (allowlist entry is gone; Lua returns nil)."
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.adapters.msg91 import Msg91Response


pytestmark = pytest.mark.asyncio


async def test_logout_revokes_then_refresh_returns_401(
    client, use_live_valkey, monkeypatch
):
    """End-to-end: verify → logout → refresh must 401."""
    # ── Arrange ────────────────────────────────────────────────────────────
    phone = "+919876500002"
    otp = "525252"

    from app.shared import valkey as _vk_mod
    valkey = await _vk_mod.get_valkey_otp()
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})
    await valkey.set(f"otp:{phone}", payload, ex=300)

    async def _fake_send_otp(*args, **kwargs):
        return Msg91Response(success=True, request_id="x", message="")

    monkeypatch.setattr("app.adapters.msg91.send_otp", _fake_send_otp)

    # ── Step 1: verify ─────────────────────────────────────────────────────
    r1 = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    assert r1.status_code == 200, r1.text
    assert "refresh_token" in r1.cookies

    # ── Step 2: logout — must return 204 ───────────────────────────────────
    r2 = await client.post("/api/v1/auth/logout")
    assert r2.status_code == 204, r2.text

    # ── Step 3: refresh on the now-revoked cookie must 401 ────────────────
    # The client's cookie jar still carries the (now-stale) refresh_token
    # cookie because httpx does not auto-clear on the server's Max-Age=0
    # in this test path; we re-send it explicitly via the cookie jar.
    r3 = await client.post("/api/v1/auth/refresh")
    assert r3.status_code == 401, r3.text
    envelope = r3.json()
    assert envelope.get("validation_message_id") == "auth.refresh.invalid"
