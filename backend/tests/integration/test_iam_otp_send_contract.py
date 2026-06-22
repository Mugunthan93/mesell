"""qa-auth-contract backend lane — BE-AUTH-04, BE-AUTH-14: OTP /send contract.

Covers:
- BE-AUTH-04 (upgrade): Non-E.164 phone → 422/400.  Develop tests ONE bad phone
  (``"not-a-phone"`` in test_iam_onboarding_coverage.py::test_otp_send_invalid_phone_422).
  This file parametrizes 6 distinct boundary shapes per the E.164 regex
  ``^\\+[1-9]\\d{1,14}$`` — each must be rejected.

  NOTE: "+91" is VALID per ``^\\+[1-9]\\d{1,14}$`` (9→[1-9], 1→\\d{1},
  total payload = 2 digits which is ≥1) — do NOT include it as a bad phone.
  The bad phones here are genuinely-invalid boundary cases.

- BE-AUTH-14 (net-new): MSG91 adapter returns success=False → service raises
  Msg91UnavailableError → route returns 503 + ``auth.msg91.unavailable``
  + non-empty detail + NO leaked traceback.
  Develop has the MSG91 adapter unit suite (test_msg91_adapter.py) but NO
  route-level 503 envelope test on /otp/send.

DROPPED (already on develop):
- BE-AUTH-01: happy-path 202 + request_id (OB-BE-01 in test_iam_onboarding_coverage.py)

Design:
  * MSG91 stubbed at the adapter boundary: ``app.adapters.msg91.send_otp``
    AND the consumer-captured ``app.modules.iam.service.msg91_adapter.send_otp``
    (iam.service imports the module, not the function — must patch the attribute
    on the imported adapter object).
  * BE-AUTH-14: mock RETURNS success=False (iam.service checks the return value
    and raises Msg91UnavailableError internally; do NOT mock the exception itself).
  * No real SMS, no real Valkey OTP seeding needed for shape/failure tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.adapters.msg91 import Msg91Response

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# BE-AUTH-04: boundary shapes that must fail E.164 validation.
# Rule: ``^\\+[1-9]\\d{1,14}$``
# "+91" PASSES (valid short number) — never list it here.
_BAD_PHONES = [
    "9876543210",             # missing + prefix entirely
    "919876543210",           # digits only, missing +
    "+0876543210",            # leading zero after + (E.164 requires +[1-9])
    "+9",                     # only one digit after + (needs ≥2 total to meet \d{1,14})
    "+919876543210123456",    # 17 digits total after + — exceeds E.164 max of 15
    "not-a-phone",            # plaintext, no digits
]

_BAD_PHONE_IDS = [
    "no-plus",
    "plus-missing",
    "leading-zero",
    "too-short",
    "too-long",
    "plaintext",
]


# ─────────────────────────────────────────────────────────────────────────────
# BE-AUTH-04 upgrade — 6-shape parametrized phone validation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_phone", _BAD_PHONES, ids=_BAD_PHONE_IDS)
async def test_otp_send_rejects_non_e164_phone_422(
    iam_client, use_live_valkey, bad_phone: str
):
    """BE-AUTH-04: POST /otp/send with a non-E.164 phone → 422/400 + non-empty detail.

    The ``phone`` field in SendOtpRequest carries ``pattern=r'^\\+[1-9]\\d{1,14}$'``.
    Pydantic fires the validation error BEFORE the service is reached, so no
    MSG91 stub is needed (no send_otp call will be made).

    Arrange: send a phone string that violates the E.164 constraint.
    Act: POST /api/v1/auth/otp/send.
    Assert: 422 or 400 (Pydantic/service rejection); detail is non-empty (i18n guard).
    """
    resp = await iam_client.post(
        "/api/v1/auth/otp/send", json={"phone": bad_phone}
    )

    assert resp.status_code in (400, 422), (
        f"Non-E.164 phone {bad_phone!r} should be 400/422; "
        f"got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    detail = body.get("detail") or body.get("validation_message_id") or ""
    assert detail, (
        f"Error response must have non-empty detail or validation_message_id; got {body!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# BE-AUTH-14 — MSG91 adapter failure → 503 envelope
# ─────────────────────────────────────────────────────────────────────────────

async def test_otp_send_msg91_failure_surfaces_503(
    iam_client, use_live_valkey, monkeypatch
):
    """BE-AUTH-14: MSG91 returns success=False → 503 + auth.msg91.unavailable.

    The iam.service checks the Msg91Response.success flag and raises
    Msg91UnavailableError when it is False — the route/error-handler translates
    that to a 503 envelope with ``auth.msg91.unavailable``.

    Arrange: patch the MSG91 adapter to return success=False (adapter does NOT
             raise; the SERVICE raises Msg91UnavailableError internally).
    Act: POST /api/v1/auth/otp/send with a valid E.164 phone.
    Assert:
      1. Status 503.
      2. validation_message_id == "auth.msg91.unavailable".
      3. detail is non-empty (no blank i18n key).
      4. No raw "Traceback" in the response body (no stack leak).
    """
    # Arrange: stub the adapter to return failure (success=False).
    # iam.service captures ``msg91`` at import time as a MODULE reference
    # (``from app.adapters import msg91 as msg91_adapter``), so we must patch
    # the ``send_otp`` attribute on the already-imported adapter object.
    fail_mock = AsyncMock(
        return_value=Msg91Response(success=False, request_id=None, message="vendor down")
    )
    monkeypatch.setattr("app.adapters.msg91.send_otp", fail_mock)
    try:
        import app.modules.iam.service as _svc
        monkeypatch.setattr(_svc.msg91_adapter, "send_otp", fail_mock)
    except (ImportError, AttributeError):
        pass  # If the attribute path differs, the source-module patch above covers it.

    # Act
    resp = await iam_client.post(
        "/api/v1/auth/otp/send",
        json={"phone": "+919876540014"},
    )

    # Assert 1 — status 503
    assert resp.status_code == 503, (
        f"MSG91 failure must surface as 503; got {resp.status_code}: {resp.text}"
    )
    body = resp.json()

    # Assert 2 — validation_message_id == "auth.msg91.unavailable"
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"503 must carry a non-empty validation_message_id; got {body!r}"
    )
    assert msg_id == "auth.msg91.unavailable", (
        f"validation_message_id must be 'auth.msg91.unavailable'; got {msg_id!r}"
    )

    # Assert 3 — detail non-empty (no blank i18n key)
    detail = body.get("detail", "")
    assert detail, f"503 must have non-empty detail; got {body!r}"

    # Assert 4 — no raw traceback leaked
    assert "Traceback" not in resp.text, (
        "503 must NOT leak a raw Python traceback in the response body"
    )
