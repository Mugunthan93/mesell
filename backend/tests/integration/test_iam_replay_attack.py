"""Integration §7.J #3 — replay-attack mitigation.

Per BACKEND_ARCHITECTURE.md §7.J integration 3:

    "Replay-attack mitigation — verify → refresh → save old refresh cookie
    locally in test → attempt to reuse old cookie → 401 (rotation
    invalidated it during refresh step)."
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.adapters.msg91 import Msg91Response

from tests.integration._cookie_helpers import extract_refresh_cookie


pytestmark = pytest.mark.asyncio


async def test_replay_of_old_refresh_cookie_after_rotation_returns_401(
    iam_client, use_live_valkey, monkeypatch
):
    """End-to-end: verify → refresh → replay old cookie → 401."""
    phone = "+915550000103"
    otp = "636363"

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
    old_refresh = extract_refresh_cookie(r1)
    assert old_refresh, "verify response must set refresh_token cookie"

    # ── Step 2: refresh — issues a new cookie, invalidates the old ────────
    # Forward the OLD cookie explicitly (httpx drops .mesell.xyz cookies).
    r2 = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={old_refresh}"},
    )
    assert r2.status_code == 200, r2.text
    new_refresh = extract_refresh_cookie(r2)
    assert new_refresh and new_refresh != old_refresh

    # ── Step 3: replay the OLD cookie ─────────────────────────────────────
    r3 = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={old_refresh}"},
    )
    assert r3.status_code == 401, r3.text
    envelope = r3.json()
    assert envelope.get("validation_message_id") == "auth.refresh.invalid"
