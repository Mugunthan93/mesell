"""Unit tests for ``app.adapters.msg91`` (§6.C + §6.G).

Verifies the LOCKED EXCEPTION to §6.G: msg91.send_otp returns
``Msg91Response(success=False, ...)`` on failure — it NEVER raises.
"""

from __future__ import annotations

import inspect

import httpx
import pytest

from app.adapters import Msg91AdapterError
from app.adapters import msg91 as msg91_mod
from app.core.errors import MeesellError

pytestmark = pytest.mark.unit


# ── Fixtures ───────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _reset_module():
    msg91_mod._reset_for_testing()
    yield
    msg91_mod._reset_for_testing()


def _install_mock_client(handler) -> None:
    """Replace the module-level httpx client with one backed by MockTransport.

    ``handler`` is a callable ``(httpx.Request) -> httpx.Response`` invoked
    on every request.  Use a closure-state list to count calls.
    """
    transport = httpx.MockTransport(handler)
    msg91_mod._client = httpx.AsyncClient(transport=transport, timeout=2.0)


# ── Exception hierarchy ────────────────────────────────────────────────────
def test_msg91_adapter_error_defined_for_v15():
    """Class is defined for V1.5 surface even though V1 never raises it."""
    assert issubclass(Msg91AdapterError, MeesellError)
    assert Msg91AdapterError().status_code == 502


# ── Happy path ─────────────────────────────────────────────────────────────
async def test_send_otp_returns_success_true_on_2xx(monkeypatch):
    """200 + vendor 'success' body → Msg91Response(success=True, request_id=...)."""
    seen: list[httpx.Request] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={"type": "success", "message": "OTP sent", "request_id": "abc123"},
        )

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")

    assert result.success is True
    assert result.request_id == "abc123"
    assert result.message == ""

    # Verify request shape: phone stripped of +, otp passed through, authkey present
    assert len(seen) == 1
    qs = dict(seen[0].url.params)
    assert qs["mobile"] == "919876543210"
    assert qs["otp"] == "123456"
    assert "authkey" in qs
    assert "template_id" in qs


# ── LOCKED EXCEPTION: failure modes DO NOT raise ──────────────────────────
async def test_send_otp_returns_success_false_on_4xx_does_not_raise():
    """400 Bad Request → success=False (NOT raise) per §6.C locked exception."""
    def _handler(_req):
        return httpx.Response(
            400, json={"type": "error", "message": "invalid mobile"}
        )

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")

    assert result.success is False
    assert result.request_id is None
    assert "invalid mobile" in result.message


async def test_send_otp_retries_5xx_then_returns_false_does_not_raise():
    """5xx triggers 1 retry per §6.C; persistent 5xx → success=False, NO raise."""
    counter = {"n": 0}

    def _handler(_req):
        counter["n"] += 1
        return httpx.Response(503, text="upstream unavailable")

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")

    # 1 initial + 1 retry = 2 calls per §6.C
    assert counter["n"] == 2
    assert result.success is False
    assert "503" in result.message


async def test_send_otp_retries_429_then_returns_false():
    """429 TooManyRequests is retryable transient (§6.C); persistent → False."""
    counter = {"n": 0}

    def _handler(_req):
        counter["n"] += 1
        return httpx.Response(429, json={"message": "rate limited"})

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")

    assert counter["n"] == 2
    assert result.success is False


async def test_send_otp_succeeds_after_one_transient_5xx():
    """If retry succeeds, success=True."""
    counter = {"n": 0}

    def _handler(_req):
        counter["n"] += 1
        if counter["n"] == 1:
            return httpx.Response(502, text="bad gateway")
        return httpx.Response(
            200, json={"type": "success", "request_id": "retry-ok"}
        )

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")

    assert counter["n"] == 2
    assert result.success is True
    assert result.request_id == "retry-ok"


async def test_send_otp_returns_false_on_connection_error(monkeypatch):
    """ConnectError → success=False, message has 'transport:' prefix.  NO raise."""
    def _handler(_req):
        raise httpx.ConnectError("connection refused")

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")

    assert result.success is False
    assert result.message.startswith("transport:")


async def test_send_otp_returns_false_on_timeout():
    """TimeoutException → success=False.  NO raise."""
    def _handler(_req):
        raise httpx.TimeoutException("timed out")

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")
    assert result.success is False


# ── Phone format handling ──────────────────────────────────────────────────
async def test_send_otp_strips_leading_plus_from_phone():
    """MSG91 requires phone without '+' prefix — adapter strips it."""
    seen_phones: list[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen_phones.append(request.url.params["mobile"])
        return httpx.Response(200, json={"type": "success", "request_id": "ok"})

    _install_mock_client(_handler)
    await msg91_mod.send_otp("+919876543210", "111111")
    await msg91_mod.send_otp("919876543210", "222222")  # no plus

    assert seen_phones == ["919876543210", "919876543210"]


async def test_send_otp_accepts_custom_template_id():
    """template_id arg overrides settings.MSG91_TEMPLATE_ID."""
    seen_templates: list[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen_templates.append(request.url.params["template_id"])
        return httpx.Response(200, json={"type": "success", "request_id": "ok"})

    _install_mock_client(_handler)
    await msg91_mod.send_otp("+919876543210", "111111", template_id="custom-tmpl")
    assert seen_templates[0] == "custom-tmpl"


# ── No-raise contract — structural enforcement ────────────────────────────
async def test_send_otp_never_raises_on_unexpected_exception():
    """Defensive: even an unexpected exception → success=False, no raise."""
    def _handler(_req):
        raise RuntimeError("unexpected boom")

    _install_mock_client(_handler)
    result = await msg91_mod.send_otp("+919876543210", "123456")
    assert result.success is False
    assert "unexpected" in result.message


# ── Boundary discipline ───────────────────────────────────────────────────
def test_no_os_getenv_in_msg91():
    """§6.G — credentials via settings only, never os.getenv."""
    src = inspect.getsource(msg91_mod)
    assert "os.getenv" not in src


def test_otp_not_logged_in_source(monkeypatch):
    """Defensive — adapter source should not include format strings that log
    the OTP code in plaintext (the OTP must NEVER leak to logs).
    """
    src = inspect.getsource(msg91_mod)
    # We log phone (for correlation) but not the OTP value.
    assert "code=%s" not in src
    assert "otp=%s" not in src.lower().replace("template_id", "")  # exclude param name
