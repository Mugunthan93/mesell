"""QA Wave 2 — BE-AUTH-09, BE-AUTH-10: Refresh single-use + allowlist-miss tests.

Covers:
- BE-AUTH-09: Refresh rotation is single-use: 2nd use of the OLD rotated cookie → 401 +
              cookie cleared (Max-Age=0).
- BE-AUTH-10: Refresh with a cookie absent from the allowlist → 401 (pairs the existing
              allowlist-write test with a MISS assertion).

Design:
  * OTP seeded directly into Valkey; real verify call issues the refresh cookie.
  * BE-AUTH-09: rotate once (200, new cookie); replay the OLD cookie → 401; assert Max-Age=0.
  * BE-AUTH-10: delete the allowlist key out-of-band; then call /refresh → 401.
  * Unique phones per test.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.core.auth import refresh_allowlist_key
from tests.integration._cookie_helpers import extract_refresh_cookie

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _otp_payload(otp: str) -> str:
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})


async def _verify_and_get_refresh_cookie(client, phone: str, otp: str) -> str:
    """Seed OTP into Valkey and perform a real verify; return the raw refresh cookie value."""
    from app.shared import valkey as _vk_mod  # noqa: PLC0415
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(otp), ex=300)

    resp = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp})
    assert resp.status_code == 200, f"verify failed: {resp.status_code}: {resp.text}"
    cookie = extract_refresh_cookie(resp)
    assert cookie, "verify must emit a refresh_token cookie"
    return cookie


async def test_refresh_rotation_single_use_second_call_401(iam_client, use_live_valkey):
    """BE-AUTH-09: 2nd use of the OLD rotated cookie → 401 + cookie cleared.

    Arrange: verify to get refresh cookie.
    Act step 1: POST /auth/refresh with that cookie → 200, new cookie issued.
    Act step 2: POST /auth/refresh with the OLD (pre-rotation) cookie → 401.
    Assert: step 2 returns 401; Set-Cookie carries Max-Age=0 (clear-cookie on failure path).
    """
    phone = "+9155500090"
    otp = "090909"

    # Arrange
    old_cookie = await _verify_and_get_refresh_cookie(iam_client, phone, otp)

    # Act step 1: first rotation — must succeed.
    r1 = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={old_cookie}"},
    )
    assert r1.status_code == 200, f"first refresh expected 200, got {r1.status_code}: {r1.text}"
    new_cookie = extract_refresh_cookie(r1)
    assert new_cookie, "first refresh must issue a new cookie"
    assert new_cookie != old_cookie, "rotation must produce a different cookie value"

    # Act step 2: replay the OLD cookie (should be single-use).
    r2 = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={old_cookie}"},
    )

    # Assert
    assert r2.status_code == 401, (
        f"2nd use of old cookie must be 401, got {r2.status_code}: {r2.text}"
    )
    # On the 401 path the router must clear the cookie (Max-Age=0).
    raw_cookie_headers = r2.headers.get_list("set-cookie")
    has_clear = any(
        "max-age=0" in h.lower() and "refresh_token" in h.lower()
        for h in raw_cookie_headers
    )
    assert has_clear, (
        f"401 refresh response must carry a Max-Age=0 clear-cookie; headers: {raw_cookie_headers}"
    )


async def test_refresh_allowlist_miss_returns_401(iam_client, use_live_valkey):
    """BE-AUTH-10: Refresh with a cookie absent from the allowlist → 401.

    Arrange: verify to get refresh cookie; delete the allowlist key out-of-band.
    Act: POST /auth/refresh with the now-orphaned cookie.
    Assert: 401 with non-empty validation_message_id.
    """
    phone = "+9155500100"
    otp = "101010"

    # Arrange: get a valid cookie.
    cookie = await _verify_and_get_refresh_cookie(iam_client, phone, otp)

    # Delete the allowlist entry out-of-band so the cookie is now orphaned.
    from app.shared import valkey as _vk_mod  # noqa: PLC0415
    valkey = await _vk_mod.get_valkey_otp()
    allowlist_k = refresh_allowlist_key(cookie)
    await valkey.delete(allowlist_k)
    # Also try the alternate pepper key (dual-pepper) if it differs.
    # The test simply deletes the key that exists; delete is idempotent.

    # Act
    resp = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={cookie}"},
    )

    # Assert
    assert resp.status_code == 401, (
        f"allowlist-miss must be 401, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"401 must have non-empty validation_message_id; got {body!r}"
    )
