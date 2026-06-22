"""QA Wave 1 (P0.2) + qa-auth-contract (BE-AUTH-08): OTP /send rate-limit tests.

``POST /api/v1/auth/otp/send`` carries ``@rate_limit(scope="otp_send",
limit=3, window=3600)``.

Wave-1 P0.2: The 4th call in the window must return 429 with a non-empty
``validation_message_id`` (P0 item 14 blank-error guard).

BE-AUTH-08 (window-recovery): after the window key expires the next call is
ALLOWED again (the recovery half of the rate-limit assertion — absent on develop
before this salvage lane).

Design:
  * ``RL_PER_IP_PER_MINUTE`` patched to 9999 so only the per-route cap fires.
  * MSG91 stubbed — no real SMS.
  * Unique test IP per run — no cross-test counter bleed.
  * BE-AUTH-08: DEL the Valkey sliding-window key after the 429 trip (simulates
    window expiry) then assert the next call is 202 again.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.adapters.msg91 import Msg91Response

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_TEST_PHONE = "+915550009901"     # non-routable; cleaned by iam_client teardown
_TEST_PHONE_08 = "+915550009908"  # dedicated phone for BE-AUTH-08 window-recovery


async def _stub_msg91(monkeypatch) -> None:
    async def _fake(*args, **kwargs):
        return Msg91Response(success=True, request_id="qaw1-req", message="")
    monkeypatch.setattr("app.adapters.msg91.send_otp", _fake)
    # Also patch the name captured in iam.service at import time.
    try:
        import app.modules.iam.service as _svc
        monkeypatch.setattr(_svc.msg91_adapter, "send_otp", _fake)
    except (ImportError, AttributeError):
        pass


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


# ─────────────────────────────────────────────────────────────────────────────
# BE-AUTH-08 (window-recovery half) — absent on develop before this lane
# ─────────────────────────────────────────────────────────────────────────────

async def test_otp_send_rate_limit_recovers_after_window(
    iam_client, use_live_valkey, monkeypatch
):
    """BE-AUTH-08 (recovery half): after window expiry the next /otp/send is 202.

    The existing test (above) covers the 429 TRIP.  This test covers the
    RECOVERY half: after the sliding-window Valkey key is deleted (simulating
    TTL expiry), the same phone + IP is allowed again (202).

    Arrange: stub MSG91; disable per-IP cap; unique IP; exhaust the 3-call
             window → 429.
    Act step 1: DEL the Valkey sliding-window key (simulates window expiry).
    Act step 2: POST /otp/send again on the same phone + IP.
    Assert: step 2 returns 202 — window has reset, caller is no longer blocked.
    """
    await _stub_msg91(monkeypatch)
    test_ip = f"10.99.{uuid.uuid4().int % 255}.2"

    # Exhaust the 3-call window (all must be 202).
    with patch("app.core.middleware.rate_limit_mw.settings") as mock_settings:
        mock_settings.RL_PER_IP_PER_MINUTE = 9999

        for call_n in range(3):
            r = await iam_client.post(
                "/api/v1/auth/otp/send",
                json={"phone": _TEST_PHONE_08},
                headers={"X-Forwarded-For": test_ip},
            )
            assert r.status_code == 202, (
                f"setup call #{call_n + 1}: expected 202, got {r.status_code}: {r.text}"
            )

        r4 = await iam_client.post(
            "/api/v1/auth/otp/send",
            json={"phone": _TEST_PHONE_08},
            headers={"X-Forwarded-For": test_ip},
        )
    assert r4.status_code == 429, (
        f"4th call must be 429 (rate-limit trip); got {r4.status_code}: {r4.text}"
    )

    # Simulate window expiry: delete the sliding-window Valkey key.
    # Key format per rate_limit_mw.py (anonymous/per-IP path, unauthenticated):
    #   meesell:rl:route:{scope}:ip:{ip}:{window}
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    rl_key = f"meesell:rl:route:otp_send:ip:{test_ip}:3600"
    deleted = await valkey.delete(rl_key)
    # Key may or may not exist depending on implementation detail; the point is
    # the window is now cleared.  ``delete`` is idempotent.

    # After window reset: next call must be allowed (202).
    with patch("app.core.middleware.rate_limit_mw.settings") as mock_settings_r:
        mock_settings_r.RL_PER_IP_PER_MINUTE = 9999
        r_recovery = await iam_client.post(
            "/api/v1/auth/otp/send",
            json={"phone": _TEST_PHONE_08},
            headers={"X-Forwarded-For": test_ip},
        )

    assert r_recovery.status_code == 202, (
        f"After window reset, /otp/send must be 202 again; "
        f"got {r_recovery.status_code}: {r_recovery.text}"
    )
