"""QA Wave 2 — BE-AUTH-12: Logout route idempotency.

Covers:
- BE-AUTH-12: Logout is idempotent at the route: double-call → 204 + clear-cookie both times.

Design:
  * Seed user via OTP verify; extract refresh cookie.
  * Call /auth/logout twice with the same cookie.
  * Both calls must return 204.
  * Both must carry the Max-Age=0 clear-cookie header.
  * The second call must NOT return 5xx.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from tests.integration._cookie_helpers import extract_refresh_cookie

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _otp_payload(otp: str) -> str:
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})


async def test_logout_double_call_both_204_with_clear_cookie(iam_client, use_live_valkey):
    """BE-AUTH-12: POST /auth/logout twice → both 204 + both clear-cookie; no 5xx.

    Arrange: verify to get a refresh cookie.
    Act: POST /auth/logout with the cookie — twice.
    Assert: first call 204; second call 204 (idempotent, no 5xx);
            both responses carry a Max-Age=0 clear-cookie header.
    """
    phone = "+9155500120"
    otp = "121212"

    # Arrange: seed OTP and verify to get a cookie.
    from app.shared import valkey as _vk_mod  # noqa: PLC0415
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(otp), ex=300)

    verify_resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    assert verify_resp.status_code == 200, f"verify failed: {verify_resp.text}"
    refresh_cookie = extract_refresh_cookie(verify_resp)
    assert refresh_cookie, "verify must emit a refresh_token cookie"

    # Act — first logout call.
    r1 = await iam_client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )

    # Assert — first call.
    assert r1.status_code == 204, (
        f"first logout must be 204, got {r1.status_code}: {r1.text}"
    )
    r1_cookie_headers = r1.headers.get_list("set-cookie")
    assert any(
        "max-age=0" in h.lower() and "refresh_token" in h.lower()
        for h in r1_cookie_headers
    ), f"first logout must carry Max-Age=0 clear-cookie; headers: {r1_cookie_headers}"

    # Act — second logout call (same cookie, now revoked).
    r2 = await iam_client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )

    # Assert — second call must ALSO be 204, not 5xx.
    assert r2.status_code == 204, (
        f"second (idempotent) logout must be 204, got {r2.status_code}: {r2.text}"
    )
    r2_cookie_headers = r2.headers.get_list("set-cookie")
    assert any(
        "max-age=0" in h.lower() and "refresh_token" in h.lower()
        for h in r2_cookie_headers
    ), f"second logout must carry Max-Age=0 clear-cookie; headers: {r2_cookie_headers}"
