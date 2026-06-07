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

from tests.integration._cookie_helpers import extract_refresh_cookie


pytestmark = pytest.mark.asyncio


async def test_logout_revokes_then_refresh_returns_401(
    iam_client, use_live_valkey, monkeypatch
):
    """End-to-end: verify → logout → refresh must 401."""
    # ── Arrange ────────────────────────────────────────────────────────────
    phone = "+915550000102"
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
    r1 = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    assert r1.status_code == 200, r1.text
    saved_refresh = extract_refresh_cookie(r1)
    assert saved_refresh, "verify must emit a refresh_token Set-Cookie"

    # ── Step 2: logout — must return 204 (forward the cookie explicitly) ──
    r2 = await iam_client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": f"refresh_token={saved_refresh}"},
    )
    assert r2.status_code == 204, r2.text

    # ── Step 3: refresh on the now-revoked cookie must 401 ────────────────
    r3 = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={saved_refresh}"},
    )
    assert r3.status_code == 401, r3.text
    envelope = r3.json()
    assert envelope.get("validation_message_id") == "auth.refresh.invalid"
