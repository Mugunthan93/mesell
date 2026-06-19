"""Unit tests for ``app.adapters.razorpay`` (§6.E + §6.G).

Verifies the two LOCKED EXCEPTIONS to §6.G:

#. ``verify_webhook_signature`` is SYNCHRONOUS (NOT ``async def``) because
   HMAC-SHA256 is CPU-bound — adding async wrapper is overhead with no
   I/O benefit.  See §6.E rationale.
#. ``verify_webhook_signature`` returns ``bool`` (NOT raises) — caller
   (``iam.router.razorpay_webhook``) responds 401 on False.
"""

from __future__ import annotations

import hashlib
import hmac
import inspect

import pytest

from app.adapters import RazorpayAdapterError
from app.adapters import razorpay as razorpay_mod
from app.core.errors import MeesellError
from app.shared.config import settings

pytestmark = pytest.mark.unit


# ── Helper to compute a real signature ─────────────────────────────────────
def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


# ── LOCKED EXCEPTION #1: SYNC, not async ──────────────────────────────────
def test_verify_webhook_signature_is_sync_not_async():
    """§6.E: HMAC verification is sync per locked exception to §6.G.

    Asserts via ``inspect.iscoroutinefunction`` — automated CI / linter
    can use this same check.
    """
    assert not inspect.iscoroutinefunction(
        razorpay_mod.verify_webhook_signature
    )


def test_verify_webhook_signature_signature_is_def_not_async_def():
    """Source-level assertion — defensive against accidental rewrite."""
    src = inspect.getsource(razorpay_mod.verify_webhook_signature)
    first_line = src.splitlines()[0]
    assert first_line.strip().startswith("def verify_webhook_signature")
    assert not first_line.strip().startswith("async def")


# ── Exception class defined for V1.5 ──────────────────────────────────────
def test_razorpay_adapter_error_defined_for_v15():
    """Class defined for V1.5 subscription surface; V1 NEVER raises."""
    assert issubclass(RazorpayAdapterError, MeesellError)
    assert RazorpayAdapterError().status_code == 502


# ── LOCKED EXCEPTION #2: returns bool, never raises ───────────────────────
def test_valid_signature_returns_true():
    """Valid HMAC + matching secret → True."""
    payload = b'{"event":"payment.captured","payload":{"x":1}}'
    secret = "test-webhook-secret"
    sig = _sign(payload, secret)

    assert razorpay_mod.verify_webhook_signature(
        payload, sig, secret=secret
    ) is True


def test_invalid_signature_returns_false_does_not_raise():
    """Bad signature → False (NOT raise).  Locked exception #2."""
    payload = b'{"event":"payment.captured"}'
    secret = "test-webhook-secret"

    result = razorpay_mod.verify_webhook_signature(
        payload, "deadbeef" * 8, secret=secret
    )
    assert result is False


def test_wrong_secret_returns_false():
    """Right HMAC for wrong secret → False."""
    payload = b'{"event":"x"}'
    sig_with_other = _sign(payload, "other-secret")
    result = razorpay_mod.verify_webhook_signature(
        payload, sig_with_other, secret="actual-secret"
    )
    assert result is False


def test_uses_settings_when_secret_arg_omitted():
    """Default ``secret`` reads from settings.RAZORPAY_WEBHOOK_SECRET."""
    payload = b'{"a":1}'
    sig = _sign(payload, settings.RAZORPAY_WEBHOOK_SECRET)
    assert razorpay_mod.verify_webhook_signature(payload, sig) is True


# ── Defensive — malformed input returns False, never raises ───────────────
def test_empty_signature_returns_false():
    assert razorpay_mod.verify_webhook_signature(b"payload", "") is False


def test_none_signature_returns_false():
    # Type-annotated as ``str``; runtime defensive check should still hold
    assert razorpay_mod.verify_webhook_signature(b"payload", None) is False  # type: ignore[arg-type]


def test_non_bytes_payload_returns_false():
    """Defensive — string payload returns False (avoids accidental bypass).

    The caller MUST pass raw request bytes per §6.E (NOT json-parsed).
    """
    result = razorpay_mod.verify_webhook_signature(
        "stringy payload",  # type: ignore[arg-type]
        "any-signature",
    )
    assert result is False


def test_bytearray_payload_works():
    """bytearray (also a bytes-like) is accepted."""
    payload = bytearray(b'{"event":"x"}')
    secret = "s"
    sig = _sign(bytes(payload), secret)
    assert razorpay_mod.verify_webhook_signature(
        payload, sig, secret=secret
    ) is True


def test_constant_time_compare_used():
    """Verify implementation uses ``hmac.compare_digest`` (constant-time)."""
    src = inspect.getsource(razorpay_mod.verify_webhook_signature)
    assert "hmac.compare_digest" in src


# ── Boundary discipline ───────────────────────────────────────────────────
def test_no_os_getenv_in_razorpay():
    """§6.G — credentials via settings only."""
    src = inspect.getsource(razorpay_mod)
    assert "os.getenv" not in src


def test_razorpay_sdk_imported_for_v15_surface():
    """V1.5 surface (RAZORPAY_SPEC §5, F9) imports the official Razorpay SDK.

    Updated from the V1-era ``test_razorpay_sdk_not_imported_in_v1``: Wave 2
    adds the async subscription/order/customer methods that wrap the sync
    official SDK via ``asyncio.to_thread`` (GCS pattern), so the SDK is now a
    direct import.  ``verify_webhook_signature`` itself remains pure-stdlib
    (hmac + hashlib) and unchanged — asserted separately above.
    """
    src = inspect.getsource(razorpay_mod)
    assert "import razorpay" in src
    assert "asyncio.to_thread" in src


# ═══════════════════════════════════════════════════════════════════════════
# V1.5 async surface unit tests (RAZORPAY_SPEC §5; task spec §7.11)
#
# The lazy singleton ``_client`` is patched with a MagicMock SDK client so the
# methods run without touching the network.  Each test asserts (a) success maps
# to the frozen dataclass with correct fields, (b) a raised vendor error is
# caught + re-raised as RazorpayAdapterError (never leaks the raw error).
# ═══════════════════════════════════════════════════════════════════════════

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

from razorpay.errors import BadRequestError, ServerError  # noqa: E402


@pytest.fixture
def patched_client(monkeypatch):
    """Install a MagicMock as the adapter's lazy singleton SDK client.

    ``_get_client`` is patched to an AsyncMock returning the MagicMock so no
    real ``razorpay.Client`` is constructed and no network/auth happens.
    """
    razorpay_mod._reset_for_testing()
    client = MagicMock()
    client.subscription = MagicMock()
    client.order = MagicMock()
    client.customer = MagicMock()
    monkeypatch.setattr(razorpay_mod, "_get_client", AsyncMock(return_value=client))
    yield client
    razorpay_mod._reset_for_testing()


@pytest.mark.asyncio
async def test_create_subscription_maps_dataclass(patched_client):
    patched_client.subscription.create.return_value = {
        "id": "sub_123",
        "status": "created",
        "plan_id": "plan_pro",
        "current_end": 1893456000,
        "short_url": "https://rzp.io/i/abc",
        "notes": {"user_id": "u1", "tier": "pro"},
    }
    out = await razorpay_mod.create_subscription(
        plan_id="plan_pro", notes={"user_id": "u1", "tier": "pro"}
    )
    assert isinstance(out, razorpay_mod.RazorpaySubscription)
    assert out.id == "sub_123"
    assert out.status == "created"
    assert out.plan_id == "plan_pro"
    assert out.current_end == 1893456000
    assert out.short_url == "https://rzp.io/i/abc"
    assert out.notes == {"user_id": "u1", "tier": "pro"}
    # Body shaping: customer_notify default True → 1; plan_id forwarded.
    sent = patched_client.subscription.create.call_args.args[0]
    assert sent["plan_id"] == "plan_pro"
    assert sent["customer_notify"] == 1


@pytest.mark.asyncio
async def test_create_order_maps_dataclass(patched_client):
    patched_client.order.create.return_value = {
        "id": "order_abc",
        "amount": 499900,
        "currency": "INR",
        "status": "created",
        "receipt": "ltd-u1",
    }
    out = await razorpay_mod.create_order(amount=499900, receipt="ltd-u1")
    assert isinstance(out, razorpay_mod.RazorpayOrder)
    assert out.id == "order_abc"
    assert out.amount == 499900  # paise (F9)
    assert out.currency == "INR"
    assert out.receipt == "ltd-u1"


@pytest.mark.asyncio
async def test_fetch_subscription_maps_dataclass(patched_client):
    patched_client.subscription.fetch.return_value = {
        "id": "sub_9",
        "status": "active",
        "plan_id": "plan_pro",
        "current_end": 1700000000,
    }
    out = await razorpay_mod.fetch_subscription("sub_9")
    assert out.status == "active"
    assert out.current_end == 1700000000
    patched_client.subscription.fetch.assert_called_once_with("sub_9")


@pytest.mark.asyncio
async def test_cancel_subscription_passes_cycle_end_flag(patched_client):
    patched_client.subscription.cancel.return_value = {
        "id": "sub_9",
        "status": "active",
        "plan_id": "plan_pro",
    }
    await razorpay_mod.cancel_subscription("sub_9", cancel_at_cycle_end=True)
    args = patched_client.subscription.cancel.call_args.args
    assert args[0] == "sub_9"
    assert args[1] == {"cancel_at_cycle_end": 1}


@pytest.mark.asyncio
async def test_update_subscription_uses_edit(patched_client):
    patched_client.subscription.edit.return_value = {
        "id": "sub_9",
        "status": "active",
        "plan_id": "plan_business",
    }
    out = await razorpay_mod.update_subscription("sub_9", plan_id="plan_business")
    assert out.plan_id == "plan_business"
    sent = patched_client.subscription.edit.call_args.args[1]
    assert sent["plan_id"] == "plan_business"
    assert sent["schedule_change_at"] == "cycle_end"


@pytest.mark.asyncio
async def test_get_customer_maps_dataclass(patched_client):
    patched_client.customer.fetch.return_value = {
        "id": "cust_1",
        "email": "a@b.com",
        "contact": "+919999999999",
    }
    out = await razorpay_mod.get_customer("cust_1")
    assert isinstance(out, razorpay_mod.RazorpayCustomer)
    assert out.id == "cust_1"
    assert out.email == "a@b.com"
    assert out.contact == "+919999999999"


@pytest.mark.asyncio
async def test_create_subscription_wraps_bad_request_error(patched_client):
    patched_client.subscription.create.side_effect = BadRequestError("bad plan_id")
    with pytest.raises(RazorpayAdapterError):
        await razorpay_mod.create_subscription(plan_id="plan_bad")


@pytest.mark.asyncio
async def test_create_order_wraps_server_error(patched_client):
    patched_client.order.create.side_effect = ServerError("rzp down")
    with pytest.raises(RazorpayAdapterError):
        await razorpay_mod.create_order(amount=100, receipt="r1")


@pytest.mark.asyncio
async def test_adapter_never_leaks_raw_vendor_error(patched_client):
    """A raised ``razorpay.errors.*`` is re-raised as RazorpayAdapterError."""
    patched_client.subscription.fetch.side_effect = BadRequestError("nope")
    try:
        await razorpay_mod.fetch_subscription("sub_x")
    except RazorpayAdapterError as exc:
        # The original vendor error is chained, not leaked as the raised type.
        assert isinstance(exc.__cause__, BadRequestError)
    else:
        pytest.fail("expected RazorpayAdapterError")


def test_six_async_methods_are_coroutines():
    """All six V1.5 surface methods are async (§3.2)."""
    for name in (
        "create_subscription",
        "create_order",
        "fetch_subscription",
        "cancel_subscription",
        "update_subscription",
        "get_customer",
    ):
        assert inspect.iscoroutinefunction(getattr(razorpay_mod, name)), name
