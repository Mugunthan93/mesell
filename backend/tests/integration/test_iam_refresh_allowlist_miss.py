"""qa-auth-contract backend lane — BE-AUTH-10: refresh allowlist-MISS → 401.

Covers:
- BE-AUTH-10: POST /auth/refresh with a cookie whose allowlist key has been
              deleted out-of-band → 401 + non-empty validation_message_id.

This is distinct from the existing develop coverage:
  * ``test_iam_refresh_allowlist_write.py`` (modules/iam) — asserts the WRITE
    (allowlist key exists after verify).
  * ``test_iam_replay_attack.py`` — the key is removed via the rotate Lua script
    on first use (rotation revocation).
  * This test — the key is removed OUT-OF-BAND (simulates TTL expiry or admin
    revocation); tests the route-level MISS path that the write-only test never
    exercises.

Design:
  * Verify via /otp/verify to issue a real refresh cookie.
  * Delete the allowlist Valkey key directly (simulates key expiry / revocation).
  * POST /auth/refresh with the now-orphaned cookie.
  * Assert 401 + non-empty validation_message_id.
  * No cookie-clear assertion (that is BE-AUTH-09/11 territory, hard-covered by
    PR #427's test_refresh_401_clears_stale_cookie — do NOT duplicate).
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
    return json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )


async def test_refresh_allowlist_miss_returns_401(iam_client, use_live_valkey):
    """BE-AUTH-10: Refresh with a cookie absent from the allowlist → 401.

    Arrange: verify to get a valid refresh cookie; delete its allowlist key
             out-of-band (simulates key TTL expiry or admin revocation).
    Act: POST /api/v1/auth/refresh with the now-orphaned cookie.
    Assert: 401 + non-empty validation_message_id (token is no longer in the
            allowlist so the Lua rotation script returns nil/reject).
    """
    phone = "+9155500100"
    otp = "100100"

    # Arrange step 1: seed OTP and call /otp/verify to get a real refresh cookie.
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

    # Arrange step 2: delete the allowlist entry out-of-band.
    allowlist_k = refresh_allowlist_key(refresh_cookie)
    await valkey.delete(allowlist_k)

    # Act: POST /auth/refresh with the now-orphaned cookie.
    resp = await iam_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )

    # Assert: allowlist miss must surface as 401.
    assert resp.status_code == 401, (
        f"allowlist-miss must be 401; got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"401 must carry a non-empty validation_message_id; got {body!r}"
    )
