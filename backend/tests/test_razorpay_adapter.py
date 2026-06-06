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

from app.adapters import RazorpayAdapterError
from app.adapters import razorpay as razorpay_mod
from app.core.errors import MeesellError
from app.shared.config import settings


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


def test_razorpay_sdk_not_imported_in_v1():
    """V1 surface uses only stdlib hmac + hashlib.  Razorpay SDK is V1.5."""
    src = inspect.getsource(razorpay_mod)
    assert "import razorpay" not in src
    assert "from razorpay" not in src
