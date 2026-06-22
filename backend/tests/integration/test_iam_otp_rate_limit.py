"""QA Wave 1 (P0.2) + Wave 2 (BE-AUTH-08): OTP /send rate-limit tests.

``POST /api/v1/auth/otp/send`` carries ``@rate_limit(scope="otp_send",
limit=3, window=3600)``.

Wave-1: The 4th call in the window must return 429 with a non-empty
``validation_message_id`` (P0 item 14 blank-error guard).

Wave-2 hardening (BE-AUTH-08): after the window key expiry the next call
is ALLOWED (window-recovery half of the rate-limit assertion).

Design:
  * ``RL_PER_IP_PER_MINUTE`` patched to 9999 so only the per-route cap fires.
  * MSG91 stubbed — no real SMS.
  * Unique test IP per run — no cross-test counter bleed.
  * BE-AUTH-08 window-recovery: after the 429, manually DEL the Valkey
    sliding-window key (simulating window expiry) and assert the next call
    is 202 again.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.adapters.msg91 import Msg91Response

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_TEST_PHONE = "+915550009901"  # non-routable; cleaned by iam_client teardown
_TEST_PHONE_08 = "+915550009908"  # dedicated phone for BE-AUTH-08 window-recovery


async def _stub_msg91(monkeypatch) -> None:
    async def _fake(*args, **kwargs):
        return Msg91Response(success=True, request_id="qaw1-req", message="")
    monkeypatch.setattr("app.adapters.msg91.send_otp", _fake)


async def test_otp_send_rate_limit_429_on_4th_call(
    iam_client, use_live_valkey, monkeypatch
):
    """4th POST /otp/send within the window returns 429 with non-empty msg id.

    Arrange: stub MSG91; per-IP cap disabled; unique IP.
    Act: 4 successive OTP-send calls on the same phone.
    Assert: calls 1-3 succeed (200); call 4 → 429;
            validation_message_id is a non-empty string (P0 item 14).
    """
    await _stub_msg91(monkeypatch)
    test_ip = f"10.99.{uuid.uuid4().int % 255}.1"

    with patch("app.core.middleware.rate_limit_mw.settings") as mock_settings:
        mock_settings.RL_PER_IP_PER_MINUTE = 9999

        for call_n in range(3):
            r = await iam_client.post(
                "/api/v1/auth/otp/send",
                json={"phone": _TEST_PHONE},
                headers={"X-Forwarded-For": test_ip},
            )
            assert r.status_code == 202, (
                f"call #{call_n + 1}: expected 202, got {r.status_code}: {r.text}"
            )

        r4 = await iam_client.post(
            "/api/v1/auth/otp/send",
            json={"phone": _TEST_PHONE},
            headers={"X-Forwarded-For": test_ip},
        )

    assert r4.status_code == 429, (
        f"4th OTP send expected 429, got {r4.status_code}: {r4.text}"
    )
    body = r4.json()
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"429 must carry non-empty validation_message_id; got {body!r}"
    )


async def test_otp_send_rate_limit_recovers_after_window(
    iam_client, use_live_valkey, monkeypatch
):
    """BE-AUTH-08 (window-recovery half): after window expiry, a new call is allowed.

    This is the second half of BE-AUTH-08 — the existing test covers the 429 trip;
    this test covers the RECOVERY: after the window key expires (simulated by
    DELeting the sliding-window Valkey key), the next /otp/send returns 202 again.

    Arrange: stub MSG91; unique IP; exhaust the 3-call window → 429.
    Act step 1: DEL the rate-limit Valkey key (simulates window expiry).
    Act step 2: POST /otp/send again on the same phone + IP.
    Assert: step 2 returns 202 (no longer rate-limited).
    """
    await _stub_msg91(monkeypatch)
    test_ip = f"10.99.{uuid.uuid4().int % 255}.2"

    with patch("app.core.middleware.rate_limit_mw.settings") as mock_settings:
        mock_settings.RL_PER_IP_PER_MINUTE = 9999

        # Exhaust the 3-call window.
        for _n in range(3):
            r = await iam_client.post(
                "/api/v1/auth/otp/send",
                json={"phone": _TEST_PHONE_08},
                headers={"X-Forwarded-For": test_ip},
            )
            assert r.status_code == 202, f"setup call expected 202, got {r.status_code}: {r.text}"

        r4 = await iam_client.post(
            "/api/v1/auth/otp/send",
            json={"phone": _TEST_PHONE_08},
            headers={"X-Forwarded-For": test_ip},
        )
    assert r4.status_code == 429, (
        f"4th call must be 429 (rate-limit trip), got {r4.status_code}: {r4.text}"
    )

    # Simulate window expiry by deleting the Valkey sliding-window key.
    # CORRECTION (Wave-2 fix): the rate_limit_mw uses a NAMESPACED key format
    # per rate_limit_mw.py line 174: ``meesell:rl:route:{scope}:ip:{ip}:{window}``
    # (anonymous/per-IP path, since /otp/send is unauthenticated).
    # ``rl:otp_send:{test_ip}`` was wrong — the actual key is:
    #   meesell:rl:route:otp_send:ip:{ip}:3600
    from app.shared import valkey as _vk_mod  # noqa: PLC0415
    valkey = await _vk_mod.get_valkey_otp()
    rl_key = f"meesell:rl:route:otp_send:ip:{test_ip}:3600"
    await valkey.delete(rl_key)

    # After key deletion (window reset), the next call must be allowed.
    with patch("app.core.middleware.rate_limit_mw.settings") as mock_settings_recovery:
        mock_settings_recovery.RL_PER_IP_PER_MINUTE = 9999
        r_recovery = await iam_client.post(
            "/api/v1/auth/otp/send",
            json={"phone": _TEST_PHONE_08},
            headers={"X-Forwarded-For": test_ip},
        )

    assert r_recovery.status_code == 202, (
        f"After window reset, OTP send must be 202 again; "
        f"got {r_recovery.status_code}: {r_recovery.text}"
    )
