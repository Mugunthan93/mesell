"""qa-auth-contract backend lane — BE-AUTH-12: logout route idempotency.

Covers:
- BE-AUTH-12: POST /auth/logout twice with the same refresh cookie → both 204
              + both carry a Max-Age=0 clear-cookie header; no 5xx on the 2nd call.

This fills the route-level gap:
  * ``test_iam_logout_idempotency.py`` (modules/iam) — covers the SERVICE layer
    (first call DELs + audit, second call is noop/no-raise).
  * This test — covers the ROUTE surface: two sequential HTTP calls, both 204,
    both clear-cookie.  The service-layer idempotency test does not drive the
    router, so the clear-cookie header from auth_logout → _clear_refresh_cookie
    is never exercised there.

Design:
  * Verify via /otp/verify to issue a real refresh cookie.
  * POST /auth/logout with the cookie twice (same cookie value).
  * Assert: call 1 → 204 + Max-Age=0 clear-cookie; call 2 → 204 + Max-Age=0.
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
    return json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )


def _has_clear_cookie(response) -> bool:
    """Return True when the response carries a Max-Age=0 clear-cookie for refresh_token."""
    return any(
        "max-age=0" in h.lower() and "refresh_token" in h.lower()
        for h in response.headers.get_list("set-cookie")
    )


async def test_logout_double_call_both_204_with_clear_cookie(iam_client, use_live_valkey):
    """BE-AUTH-12: POST /auth/logout × 2 → both 204 + both Max-Age=0; no 5xx.

    Arrange: seed OTP + verify to obtain a real refresh cookie.
    Act: POST /api/v1/auth/logout with that cookie — twice in a row.
    Assert:
      1. First call → 204.
      2. First call response carries a Max-Age=0 clear-cookie for refresh_token.
      3. Second call → 204 (idempotent; cookie is already revoked).
      4. Second call response also carries a Max-Age=0 clear-cookie (§7.B.4 always clears).
    """
    phone = "+9155500120"
    otp = "120120"

    # Arrange: seed OTP record and call /otp/verify to get a refresh cookie.
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(otp), ex=300)

    verify_resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    assert verify_resp.status_code == 200, (
        f"verify must succeed; got {verify_resp.status_code}: {verify_resp.text}"
    )
    refresh_cookie = extract_refresh_cookie(verify_resp)
    assert refresh_cookie, "verify must emit a refresh_token Set-Cookie"

    # Act — first logout call.
    r1 = await iam_client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )

    # Assert first call.
    assert r1.status_code == 204, (
        f"first logout must be 204; got {r1.status_code}: {r1.text}"
    )
    assert _has_clear_cookie(r1), (
        f"first logout must carry Max-Age=0 clear-cookie; "
        f"set-cookie headers: {r1.headers.get_list('set-cookie')!r}"
    )

    # Act — second logout call with the same (now-revoked) cookie.
    r2 = await iam_client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )

    # Assert second call — must be 204, not 5xx.
    assert r2.status_code == 204, (
        f"second (idempotent) logout must be 204; got {r2.status_code}: {r2.text}"
    )
    assert _has_clear_cookie(r2), (
        f"second logout must also carry Max-Age=0 clear-cookie (§7.B.4 always clears); "
        f"set-cookie headers: {r2.headers.get_list('set-cookie')!r}"
    )
