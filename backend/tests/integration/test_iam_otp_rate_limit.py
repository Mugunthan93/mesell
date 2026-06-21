"""QA Wave 1 — P0.2: OTP /send rate-limit triggers 429 on the 4th call.

``POST /api/v1/auth/otp/send`` carries ``@rate_limit(scope="otp_send",
limit=3, window=3600)``.  The 4th call in the window must return 429 with
a non-empty ``validation_message_id`` (P0 item 14 blank-error guard).

Design:
  * ``RL_PER_IP_PER_MINUTE`` patched to 9999 so only the per-route cap fires.
  * MSG91 stubbed — no real SMS.
  * Unique test IP per run — no cross-test counter bleed.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.adapters.msg91 import Msg91Response

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_TEST_PHONE = "+915550009901"  # non-routable; cleaned by iam_client teardown


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
