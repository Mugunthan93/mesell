"""svc-image vendored adapters — GCS + Gemini + LangFuse transport.

Trimmed from the monolith ``app.adapters`` (§6.G).  svc-image consumes:

* the GCS adapter — image upload + download + signed-URL issuance (service.py
  + tasks.py);
* the Gemini adapter — the VENDORED ai_ops watermark.v1 vision step
  (consumed ONLY by ``app.ai_ops.client`` per the §3.G boundary, never the
  domain code directly);
* the LangFuse adapter — fire-and-forget trace egress for ai_ops (drop-on-
  failure, never raises — §6.F).

The msg91 / razorpay adapters are NOT vendored — image has no SMS/payment
surface.

Locked invariants (§6.G): async interfaces; credentials via
``app.shared.config.settings``; pure transport, no business logic; typed
exception hierarchy rooted at :class:`AdapterError` (default HTTP 502).
"""

from __future__ import annotations

from app.core.errors import MeesellError


class AdapterError(MeesellError):
    """Root of the vendor adapter exception classes (§6.G).  Default HTTP 502."""

    code: str = "adapter.unavailable"
    status_code: int = 502
    validation_message_id: str = "adapter.unavailable"


class GcsAdapterError(AdapterError):
    """Raised by ``adapters.gcs`` on auth / not-found / forbidden / SDK error."""

    code: str = "gcs.unavailable"
    validation_message_id: str = "gcs.unavailable"


class GeminiAdapterError(AdapterError):
    """Raised by ``adapters.gemini`` on transport failure or retry exhaustion."""

    code: str = "gemini.unavailable"
    validation_message_id: str = "gemini.unavailable"


class LangfuseAdapterError(AdapterError):
    """Defined for V1.5 surface; V1 NEVER raises (drop-on-failure per §6.F)."""

    code: str = "langfuse.unavailable"
    validation_message_id: str = "langfuse.unavailable"


__all__ = [
    "AdapterError",
    "GcsAdapterError",
    "GeminiAdapterError",
    "LangfuseAdapterError",
]
