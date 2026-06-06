"""adapters/razorpay.py — Razorpay webhook signature verifier (§6.E).

V1 ONLY surface.  Subscription / payment business logic is deferred to
V1.5 per §1.E + ``MVP_ARCH §14``.  This adapter exposes exactly one
synchronous helper for HMAC signature verification.

LOCKED EXCEPTION #1 (§6.G "all adapters async")
-----------------------------------------------
This function is **synchronous** because HMAC-SHA256 verification is
CPU-bound and microsecond-scale; an ``async def`` wrapper would add
event-loop overhead with no I/O benefit.  See §6.E rationale.

LOCKED EXCEPTION #2 (§6.G "raise typed errors")
-----------------------------------------------
This function returns ``bool``.  Invalid signature returns ``False``;
malformed input returns ``False``.  It NEVER raises in V1.  The caller
(``iam.router.razorpay_webhook``) responds 401 on a ``False`` return.

(The V1.5 surface that adds ``create_subscription`` / ``cancel_subscription`` /
``get_customer`` will follow the §6.G typed-exception pattern via
:class:`RazorpayAdapterError`, which is already defined in
``adapters/__init__.py`` for forward compatibility.)
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from app.shared.config import settings

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    *,
    secret: str | None = None,
) -> bool:
    """Verify Razorpay webhook signature.

    HMAC-SHA256 of ``payload`` with ``secret`` is compared constant-time
    against ``signature`` (the value of the ``X-Razorpay-Signature``
    request header).

    Args:
        payload: Raw request body — bytes, NOT json-parsed.  Parsing
            mutates whitespace and breaks the HMAC.
        signature: Hex-encoded signature from the request header.
        secret: Override the configured ``RAZORPAY_WEBHOOK_SECRET``.

    Returns:
        True if the signature matches; False otherwise.

    NEVER raises (locked exception #2).  Returns ``False`` on:
      * non-bytes payload (defensive)
      * empty / non-string signature (defensive)
      * actual signature mismatch
      * any HMAC compare exception (defensive)
    """
    if not isinstance(payload, (bytes, bytearray)):
        logger.warning(
            "razorpay.verify_webhook_signature: non-bytes payload type=%s",
            type(payload).__name__,
        )
        return False
    if not isinstance(signature, str) or not signature:
        return False

    key = (secret or settings.RAZORPAY_WEBHOOK_SECRET).encode("utf-8")
    expected = hmac.new(key, bytes(payload), hashlib.sha256).hexdigest()

    try:
        return hmac.compare_digest(expected, signature)
    except Exception as exc:
        # Defensive — ``hmac.compare_digest`` accepts str-vs-str or bytes-vs-bytes
        # only; any TypeError here is signal we have malformed input upstream.
        logger.warning(
            "razorpay.verify_webhook_signature compare error: %r", exc
        )
        return False
