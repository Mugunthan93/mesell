"""qa-auth-contract backend lane — BE-AUTH-02, BE-AUTH-05: OTP /verify contract.

Covers:
- BE-AUTH-02: Tight bundle — verify 200 + non-empty access_token + expires_in>0
              + HttpOnly + SameSite=Strict refresh cookie (all in one test).
              Develop asserts these PIECEMEAL across three files; this bundles them.
- BE-AUTH-05: Non-6-digit OTP shape → 422 + non-empty detail.
              Absent on develop (no OTP-shape rejection test).

DROPPED (already on develop):
- BE-AUTH-06: wrong code → 401     (OB-BE-05 in test_iam_onboarding_coverage.py)
- BE-AUTH-07: expired key → 401    (OB-BE-06 in test_iam_onboarding_coverage.py)

Design:
  * OTP seeded directly into Valkey DB 0 — no live /otp/send → no MSG91 call.
  * Unique phone per test to prevent Valkey key collisions.
  * Uses ``iam_client`` + ``use_live_valkey`` from tests/integration/conftest.py
    (NullPool engine, function-loop safe, lifespan-bound).
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from tests.integration._cookie_helpers import extract_refresh_cookie

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _otp_payload(otp: str) -> str:
    """Build the Valkey OTP record payload (sha256 hash + metadata)."""
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )


# ─────────────────────────────────────────────────────────────────────────────
# BE-AUTH-02 — Tight verify contract bundle
# ─────────────────────────────────────────────────────────────────────────────

async def test_otp_verify_full_contract_bundle(iam_client, use_live_valkey):
    """BE-AUTH-02: verify 200 + access_token + expires_in>0 + HttpOnly SameSite=Strict cookie.

    Arrange: seed a valid OTP hash into Valkey DB 0 directly (no /otp/send call).
    Act: POST /api/v1/auth/otp/verify with the matching OTP.
    Assert (all four bundled):
      1. status 200
      2. access_token is a non-empty string
      3. expires_in is a positive integer
      4. Set-Cookie refresh_token is HttpOnly and SameSite=Strict
    """
    phone = "+9155500920"
    otp = "920920"

    # Arrange: seed the OTP record into Valkey DB 0.
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(otp), ex=300)

    # Act
    resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )

    # Assert 1 — status
    assert resp.status_code == 200, (
        f"verify must be 200; got {resp.status_code}: {resp.text}"
    )
    body = resp.json()

    # Assert 2 — access_token non-empty
    access_token = body.get("access_token", "")
    assert isinstance(access_token, str) and access_token, (
        f"access_token must be a non-empty string; got {body!r}"
    )

    # Assert 3 — expires_in positive integer
    expires_in = body.get("expires_in", 0)
    assert isinstance(expires_in, int) and expires_in > 0, (
        f"expires_in must be a positive int; got {expires_in!r}"
    )

    # Assert 4 — refresh cookie attrs: HttpOnly AND SameSite=Strict
    refresh_cookie = extract_refresh_cookie(resp)
    assert refresh_cookie, "verify must emit a Set-Cookie refresh_token"
    raw_headers = resp.headers.get_list("set-cookie")
    refresh_header = next(
        (h for h in raw_headers if "refresh_token" in h.lower()), ""
    )
    assert "httponly" in refresh_header.lower(), (
        f"refresh_token cookie must be HttpOnly; raw header: {refresh_header!r}"
    )
    assert "samesite=strict" in refresh_header.lower(), (
        f"refresh_token cookie must be SameSite=Strict; raw header: {refresh_header!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# BE-AUTH-05 — Non-6-digit OTP shape → 422
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "bad_otp",
    [
        "12345",      # 5 digits — too short
        "1234567",    # 7 digits — too long
        "abcdef",     # alpha — not digits
        "12 345",     # space — not digits
        "",           # empty
        "1234 6",     # embedded space
    ],
    ids=[
        "5-digits",
        "7-digits",
        "alpha",
        "space-between",
        "empty",
        "embedded-space",
    ],
)
async def test_otp_verify_rejects_non_6digit_otp_shape_422(
    iam_client, use_live_valkey, bad_otp: str
):
    """BE-AUTH-05: POST /otp/verify with a non-6-digit OTP → 422 + non-empty detail.

    The ``otp`` field carries ``pattern=r'^\\d{6}$'`` in VerifyOtpRequest —
    Pydantic fires the 422 BEFORE the service layer is reached, so no Valkey
    seed is needed (the record is never looked up).

    Arrange: OTP string that fails the ``^\\d{6}$`` pattern (various shapes).
    Act: POST /api/v1/auth/otp/verify with a valid phone + bad OTP.
    Assert: 422; response body has a non-empty ``detail`` or
            ``validation_message_id`` (i18n-blank-key guard).
    """
    resp = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "+919876540005", "otp": bad_otp},
    )

    assert resp.status_code == 422, (
        f"OTP {bad_otp!r} should be 422, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    # Error envelope may use 'detail' (Pydantic path) or 'validation_message_id'
    # (MeesellError path) — either must be non-empty (i18n-blank-key guard).
    detail = body.get("detail") or body.get("validation_message_id") or ""
    assert detail, f"422 must have non-empty detail or validation_message_id; got {body!r}"
