"""QA Wave 2 — BE-AUTH-01, BE-AUTH-04, BE-AUTH-14: OTP /send contract tests.

Covers:
- BE-AUTH-01: Happy path — 202 + non-empty request_id; MSG91 adapter called once.
- BE-AUTH-04: Non-E.164 phone → 422/400 with non-empty human-string detail.
- BE-AUTH-14: MSG91 adapter failure surfaces as 503 auth.msg91.unavailable envelope.

Design:
  * MSG91 stubbed at the adapter boundary — no real SMS sent.
  * BE-AUTH-14: mock raises Msg91UnavailableError (per spec correction: the adapter
    RETURNS success=False, the SERVICE RAISES Msg91UnavailableError → 503).
  * Unique phones per test to prevent cross-test Valkey key collisions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.adapters.msg91 import Msg91Response
from app.modules.iam.exceptions import Msg91UnavailableError

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_VALID_PHONE = "+919876540001"
_BAD_PHONES = [
    "9876543210",       # missing + prefix
    "919876543210",     # missing +
    "+0876543210",      # leading zero after + (E.164 requires +[1-9])
    "+91",              # too short
    "not-a-phone",
]


async def _stub_msg91_success(monkeypatch) -> AsyncMock:
    """Patch msg91.send_otp to succeed; return the mock for call assertions."""
    mock = AsyncMock(return_value=Msg91Response(success=True, request_id="req-001", message="ok"))
    monkeypatch.setattr("app.adapters.msg91.send_otp", mock)
    # Patch the name captured by the iam service at import time.
    try:
        import app.modules.iam.service as _svc
        monkeypatch.setattr(_svc, "msg91_adapter", type("_M", (), {"send_otp": mock})())
    except Exception:
        pass
    return mock


async def test_otp_send_202_with_request_id(iam_client, use_live_valkey, monkeypatch):
    """BE-AUTH-01: POST /otp/send happy path returns 202 + non-empty request_id.

    Arrange: stub MSG91 success; valid E.164 phone.
    Act: POST /api/v1/auth/otp/send.
    Assert: status 202; body has non-empty ``request_id``; MSG91 send_otp called once.
    """
    # Arrange
    mock = AsyncMock(return_value=Msg91Response(success=True, request_id="req-be01", message="ok"))
    monkeypatch.setattr("app.adapters.msg91.send_otp", mock)
    import app.modules.iam.service as _svc  # noqa: PLC0415
    monkeypatch.setattr(_svc.msg91_adapter, "send_otp", mock)

    # Act
    resp = await iam_client.post("/api/v1/auth/otp/send", json={"phone": _VALID_PHONE})

    # Assert
    assert resp.status_code == 202, f"expected 202, got {resp.status_code}: {resp.text}"
    body = resp.json()
    request_id = body.get("request_id", "")
    assert isinstance(request_id, str) and request_id, (
        f"response must have non-empty request_id; got {body!r}"
    )
    mock.assert_awaited_once()


@pytest.mark.parametrize("bad_phone", _BAD_PHONES)
async def test_otp_send_rejects_non_e164_phone(iam_client, use_live_valkey, bad_phone):
    """BE-AUTH-04: Non-E.164 phone shape → 422/400 with non-empty detail.

    Arrange: send a phone that fails the ``^\\+[1-9]\\d{1,14}$`` constraint.
    Act: POST /api/v1/auth/otp/send.
    Assert: 422 or 400 (Pydantic validation fires); detail is non-empty string.
    """
    # Act
    resp = await iam_client.post("/api/v1/auth/otp/send", json={"phone": bad_phone})

    # Assert
    assert resp.status_code in (400, 422), (
        f"non-E.164 phone {bad_phone!r} should fail with 400/422, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    # The error envelope may use 'detail' (Pydantic) or 'validation_message_id' (MeesellError).
    detail = body.get("detail") or body.get("validation_message_id") or ""
    assert detail, f"error response must have non-empty detail; got {body!r}"


async def test_otp_send_msg91_failure_surfaces_503(iam_client, use_live_valkey, monkeypatch):
    """BE-AUTH-14: MSG91 adapter returns success=False → route returns 503.

    The iam service raises Msg91UnavailableError when the adapter returns
    success=False — the spec correction: the adapter does NOT raise, the
    SERVICE raises.  The error handler must translate to 503 with the
    ``auth.msg91.unavailable`` i18n envelope and non-empty detail.

    Arrange: stub MSG91 to return success=False.
    Act: POST /api/v1/auth/otp/send.
    Assert: 503; body has non-empty ``validation_message_id`` == auth.msg91.unavailable
            AND non-empty ``detail``; no stack trace leaked.
    """
    # Arrange — adapter returns failure (non-raise per §6.C)
    fail_mock = AsyncMock(
        return_value=Msg91Response(success=False, request_id=None, message="vendor down")
    )
    monkeypatch.setattr("app.adapters.msg91.send_otp", fail_mock)
    import app.modules.iam.service as _svc  # noqa: PLC0415
    monkeypatch.setattr(_svc.msg91_adapter, "send_otp", fail_mock)

    # Act
    resp = await iam_client.post(
        "/api/v1/auth/otp/send",
        json={"phone": "+919876540014"},
    )

    # Assert
    assert resp.status_code == 503, (
        f"MSG91 failure must surface as 503, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"503 must carry non-empty validation_message_id; got {body!r}"
    )
    assert msg_id == "auth.msg91.unavailable", (
        f"validation_message_id must be 'auth.msg91.unavailable'; got {msg_id!r}"
    )
    detail = body.get("detail", "")
    assert detail, f"503 must have non-empty detail; got {body!r}"
    # No raw traceback — stack should not appear in the response body.
    assert "Traceback" not in resp.text, "503 must not leak a raw traceback"
