"""Integration — DEV-only OTP bypass (dev-otp-bypass feature).

The bypass lets a developer log in with any phone + a fixed code
(``DEV_OTP_BYPASS_CODE``) AFTER a normal ``/otp/send`` has seeded the Valkey
OTP record.  Two independent guards gate it (in ``service.py``):

  1. ``DEV_OTP_BYPASS_CODE`` must be NON-EMPTY, and
  2. ``APP_ENV`` must NOT be ``"production"``.

These tests assert the live contract:

  (a) dev success      — APP_ENV=development, code seeded real, verify with the
                         bypass code → 200 + access_token + refresh cookie.
  (b) prod force-disable — APP_ENV=production, same config → REJECTED (the
                         bypass code is NOT the real OTP, so the normal mismatch
                         path raises ``OtpInvalidError``).
  (c) regression       — under an active bypass the REAL OTP still verifies and a
                         WRONG (non-bypass) code still fails.

Mirrors ``test_iam_silent_refresh_flow.py``: ``iam_client`` + ``use_live_valkey``
fixtures, ``_seed_otp_in_valkey`` to seed a real OTP record, ``extract_refresh_cookie``
to read the Set-Cookie.  The bypass is toggled per-test via ``monkeypatch.setattr``
on ``settings`` (NEVER mutating the process env).
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.adapters.msg91 import Msg91Response
from app.shared.config import settings

from tests.integration._cookie_helpers import extract_refresh_cookie


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_otp_in_valkey(phone: str, otp: str) -> None:
    """Bypass /otp/send: drop a known OTP record into Valkey directly.

    Stores the real sha256 of ``otp`` (attempts=0, 300 s TTL) so the
    record-exists gate is satisfied exactly as a real send would.
    """
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})
    await valkey.set(f"otp:{phone}", payload, ex=300)


async def _stub_msg91(monkeypatch) -> None:
    """Never reach the real vendor even if a stray /otp/send leaks."""

    async def _fake_send_otp(*args, **kwargs):
        return Msg91Response(success=True, request_id="test-req-id", message="")

    monkeypatch.setattr("app.adapters.msg91.send_otp", _fake_send_otp)


async def test_dev_bypass_success(iam_client, use_live_valkey, monkeypatch):
    """(a) APP_ENV=development + bypass code → verify with bypass code → 200."""
    await _stub_msg91(monkeypatch)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEV_OTP_BYPASS_CODE", "000000")

    phone = "+915550000201"
    real_otp = "424242"  # seeded, but we DO NOT present it — we present the bypass
    await _seed_otp_in_valkey(phone, real_otp)

    r = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "000000"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"], "bypass success must mint an access token"
    assert body["token_type"] == "bearer"

    refresh = extract_refresh_cookie(r)
    assert refresh, "bypass success must emit a refresh_token Set-Cookie"


async def test_prod_force_disable(iam_client, use_live_valkey, monkeypatch):
    """(b) APP_ENV=production → the bypass is inert; the bypass code is rejected."""
    await _stub_msg91(monkeypatch)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DEV_OTP_BYPASS_CODE", "000000")

    phone = "+915550000202"
    real_otp = "424242"
    await _seed_otp_in_valkey(phone, real_otp)

    r = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "000000"},
    )
    # The bypass guard requires APP_ENV != "production"; in prod the bypass code
    # is just a wrong OTP → normal mismatch path → OtpInvalidError (401).
    assert r.status_code == 401, r.text
    envelope = r.json()
    assert envelope.get("validation_message_id") == "auth.otp.invalid"
    assert envelope.get("code") == "iam.otp_invalid"


async def test_dev_bypass_regression(iam_client, use_live_valkey, monkeypatch):
    """(c) Under an active bypass: wrong code still fails; real OTP still works."""
    await _stub_msg91(monkeypatch)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEV_OTP_BYPASS_CODE", "000000")

    # ── A wrong, non-bypass code still fails (attempts/mismatch path) ──────
    phone_wrong = "+915550000203"
    await _seed_otp_in_valkey(phone_wrong, "424242")
    r_wrong = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone_wrong, "otp": "111111"},
    )
    assert r_wrong.status_code == 401, r_wrong.text
    assert r_wrong.json().get("validation_message_id") == "auth.otp.invalid"

    # ── The REAL OTP still verifies (the real hash-compare is intact) ──────
    phone_real = "+915550000204"
    await _seed_otp_in_valkey(phone_real, "424242")
    r_real = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone_real, "otp": "424242"},
    )
    assert r_real.status_code == 200, r_real.text
    body = r_real.json()
    assert body["access_token"]
    assert extract_refresh_cookie(r_real), "real-OTP verify must emit a refresh cookie"
