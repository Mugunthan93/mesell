"""QA Wave 2 — BE-AUTH-02, BE-AUTH-05, BE-AUTH-06, BE-AUTH-07: OTP /verify contract tests.

Covers:
- BE-AUTH-02: Verify happy path — 200 + access_token + Set-Cookie refresh_token (HttpOnly, SameSite=Strict).
- BE-AUTH-05: Non-6-digit OTP shape → 422 with non-empty detail.
- BE-AUTH-06: Wrong code (valid shape but incorrect) → 401 with non-empty auth-namespaced detail.
- BE-AUTH-07: No stored record (expired/absent) → 401 with non-empty detail; no cookie set.

Design:
  * OTP seeded directly into Valkey DB 0 (sha256 hash) — no live /otp/send.
  * BE-AUTH-06 seeds a record but sends a wrong OTP.
  * BE-AUTH-07 sends to a phone with no Valkey record at all.
  * Each test uses a unique phone to prevent cross-test Valkey key collisions.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from tests.integration._cookie_helpers import extract_refresh_cookie

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_BASE_PHONE = "+9155500991"


def _make_phone(suffix: str) -> str:
    return f"{_BASE_PHONE}{suffix}"


def _otp_payload(otp: str) -> str:
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})


async def test_otp_verify_200_access_token_and_refresh_cookie(
    iam_client, use_live_valkey, monkeypatch
):
    """BE-AUTH-02: OTP verify happy path — 200 + access_token + HttpOnly SameSite=Strict cookie.

    Arrange: seed OTP hash into Valkey DB 0.
    Act: POST /api/v1/auth/otp/verify with the matching OTP.
    Assert: 200; body has non-empty ``access_token`` and ``expires_in`` > 0;
            Set-Cookie refresh_token is present, HttpOnly, SameSite=Strict.
    """
    phone = _make_phone("02")
    otp = "112233"

    # Arrange: seed the OTP record into Valkey DB 0.
    from app.shared import valkey as _vk_mod  # noqa: PLC0415
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(otp), ex=300)

    # Act
    resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )

    # Assert
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    access_token = body.get("access_token", "")
    assert isinstance(access_token, str) and access_token, (
        f"body must have non-empty access_token; got {body!r}"
    )
    expires_in = body.get("expires_in", 0)
    assert isinstance(expires_in, int) and expires_in > 0, (
        f"expires_in must be a positive int; got {expires_in!r}"
    )

    # Cookie attrs — must be HttpOnly and SameSite=Strict.
    refresh_cookie = extract_refresh_cookie(resp)
    assert refresh_cookie, "verify must emit a Set-Cookie refresh_token"
    raw_cookie_headers = resp.headers.get_list("set-cookie")
    refresh_header = next(
        (h for h in raw_cookie_headers if "refresh_token" in h.lower()), ""
    )
    assert "httponly" in refresh_header.lower(), (
        f"refresh_token cookie must be HttpOnly; header: {refresh_header!r}"
    )
    assert "samesite=strict" in refresh_header.lower(), (
        f"refresh_token cookie must be SameSite=Strict; header: {refresh_header!r}"
    )


@pytest.mark.parametrize("bad_otp", ["12345", "1234567", "abcdef", "12 345", ""])
async def test_otp_verify_rejects_non_6digit_otp_shape(iam_client, use_live_valkey, bad_otp):
    """BE-AUTH-05: Non-6-digit OTP → 422 with non-empty detail (Pydantic shape constraint).

    Arrange: OTP that fails ``^\\d{6}$`` pattern.
    Act: POST /api/v1/auth/otp/verify.
    Assert: 422; non-empty detail.
    """
    resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": "+919876540005", "otp": bad_otp}
    )

    assert resp.status_code == 422, (
        f"bad OTP shape {bad_otp!r} should be 422, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    detail = body.get("detail") or body.get("validation_message_id") or ""
    assert detail, f"422 must have non-empty detail; got {body!r}"


async def test_otp_verify_wrong_code_returns_401(iam_client, use_live_valkey, monkeypatch):
    """BE-AUTH-06: OTP verify with wrong code (valid shape, wrong value) → 401.

    Arrange: seed real OTP hash; present wrong code with same shape.
    Act: POST /api/v1/auth/otp/verify.
    Assert: 401; auth-namespaced validation_message_id non-empty; no Set-Cookie.
    """
    phone = _make_phone("06")
    real_otp = "999111"
    wrong_otp = "000999"

    from app.shared import valkey as _vk_mod  # noqa: PLC0415
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(real_otp), ex=300)

    resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": wrong_otp}
    )

    assert resp.status_code == 401, f"wrong OTP must be 401, got {resp.status_code}: {resp.text}"
    body = resp.json()
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"401 must have non-empty validation_message_id; got {body!r}"
    )
    # Must be an auth-namespaced i18n key (auth.*)
    assert msg_id.startswith("auth."), f"msg_id must be auth.*; got {msg_id!r}"
    # No Set-Cookie on failure.
    assert extract_refresh_cookie(resp) is None, "401 must not set a refresh cookie"


async def test_otp_verify_no_stored_record_returns_401(iam_client, use_live_valkey):
    """BE-AUTH-07: OTP verify with no stored record (Valkey key absent) → 401.

    Arrange: present a valid-shaped OTP for a phone that has no Valkey key.
    Act: POST /api/v1/auth/otp/verify.
    Assert: 401; non-empty detail; no Set-Cookie.
    """
    phone = "+919555000007"  # unique phone with NO seeded Valkey record

    resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": "654321"}
    )

    assert resp.status_code == 401, (
        f"no stored record must be 401, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    detail = body.get("detail") or body.get("validation_message_id") or ""
    assert detail, f"401 must have non-empty detail; got {body!r}"
    # No cookie on failure.
    assert extract_refresh_cookie(resp) is None, "401 must not set a refresh cookie"
