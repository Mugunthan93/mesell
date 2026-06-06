"""adapters/ — Third-party vendor clients (§6).

Pure transport boundary — vendor SDK quirks NEVER leak past file boundary
per Philosophy M10 and §2.9.  Each adapter exposes a stable async interface
(the single locked exception is :func:`razorpay.verify_webhook_signature`
which is sync per §6.E) consumed by domain modules and ``ai_ops/``.

Locked invariants (§6.G)
------------------------
* Async interfaces — except ``razorpay.verify_webhook_signature`` (sync HMAC).
* Credentials via ``app.shared.config.settings`` — NO ``os.getenv`` anywhere
  in this package (CI-enforced per §19 import-linter).
* No business logic — pure transport.  Domain decisions (retry with softer
  prompt, quarantine seller, mark export partial) live above the adapter.
* Transport-level retry only — business-level retry decisions live above
  the adapter (in ``ai_ops/`` for AI, in the calling module's
  ``service.py`` for non-AI).
* Typed exception hierarchy rooted at :class:`AdapterError`, which inherits
  from :class:`app.core.errors.MeesellError` per §4.F.  Default status 502.
* Lazy singleton SDK clients — module-level singleton instances are
  initialised on first call; same client reused for the life of the process.

Locked exceptions to the typed-exception pattern (§6.G + §6.C + §6.F)
--------------------------------------------------------------------
1. :func:`msg91.send_otp` returns ``Msg91Response(success=False, ...)`` on
   transport failure — does NOT raise.  Caller surfaces 503 to the seller
   per §1.E.
2. :func:`langfuse.trace` and :func:`langfuse.score` NEVER raise —
   drop-on-failure with ``logger.warning(...)``.

Boundary rule (§3.G + §16.D)
----------------------------
``adapters.gemini`` is consumed ONLY by ``app.ai_ops.client``.  Domain
modules call ``ai_ops.client.call_gemini(...)`` — never the adapter
directly.  The §19 import-linter rejects ``from app.adapters.gemini``
anywhere under ``app/modules/``.
"""

from __future__ import annotations

from app.core.errors import MeesellError


class AdapterError(MeesellError):
    """Root of the 5 vendor adapter exception classes (§6.G).

    Default HTTP 502 Bad Gateway.  Seller sees the i18n message
    ``<vendor>.unavailable`` (e.g. ``gemini.unavailable``) via the
    ``core/errors.py`` envelope resolution per §5A.H.
    """

    code: str = "adapter.unavailable"
    status_code: int = 502
    validation_message_id: str = "adapter.unavailable"


class GeminiAdapterError(AdapterError):
    """Raised by ``adapters.gemini`` on transport failure or retry exhaustion."""

    code: str = "gemini.unavailable"
    validation_message_id: str = "gemini.unavailable"


class Msg91AdapterError(AdapterError):
    """Defined for V1.5 surface; V1 does NOT raise this — :func:`msg91.send_otp`
    returns ``Msg91Response(success=False, ...)`` on failure per §6.C.
    """

    code: str = "msg91.unavailable"
    validation_message_id: str = "msg91.unavailable"


class GcsAdapterError(AdapterError):
    """Raised by ``adapters.gcs`` on auth / not-found / forbidden / SDK error."""

    code: str = "gcs.unavailable"
    validation_message_id: str = "gcs.unavailable"


class RazorpayAdapterError(AdapterError):
    """Defined for V1.5 surface (subscription business logic).

    V1 ``verify_webhook_signature`` returns ``bool`` and never raises per §6.E.
    """

    code: str = "razorpay.unavailable"
    validation_message_id: str = "razorpay.unavailable"


class LangfuseAdapterError(AdapterError):
    """Defined for V1.5 surface; V1 NEVER raises (drop-on-failure per §6.F)."""

    code: str = "langfuse.unavailable"
    validation_message_id: str = "langfuse.unavailable"


__all__ = [
    "AdapterError",
    "GeminiAdapterError",
    "Msg91AdapterError",
    "GcsAdapterError",
    "RazorpayAdapterError",
    "LangfuseAdapterError",
]
