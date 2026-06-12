"""svc-export vendored adapters — GCS transport only.

Trimmed from the monolith ``app.adapters`` (§6.G).  Export consumes ONLY the
GCS adapter (XLSX + image-ZIP upload + signed-URL issuance + per-image ZIP
download).  The gemini / msg91 / razorpay / langfuse adapters are NOT vendored
— export uses none of them.
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


__all__ = [
    "AdapterError",
    "GcsAdapterError",
]
