"""svc-image English message registry — vendored SUBSET.

Carries ONLY:

* the 5 image module-specific IDs (raised by ``app.exceptions``):
  ``validation.image.invalid_format``, ``validation.image.too_large``,
  ``validation.image.invalid_idx``, ``image.slot.occupied``,
  ``image.not.found``;
* ``catalog.product.not_found`` — raised by the catalog-ownership HTTP shim
  (``app.core.extracted_clients.catalog_client.ProductNotFoundError``);
* ``ai_ops.budget.exhausted`` / ``gemini.unavailable`` — the VENDORED ai_ops
  watermark.v1 path may surface these (both are normally intercepted +
  mapped to a graceful fallback inside ``ai_ops.client``, but the IDs are
  registered for the rare escape path);
* the cross-cutting IDs the vendored core layer raises:
  ``tenancy.cross_user_access`` (core/tenancy), ``rate_limit.exceeded``
  (core/middleware/rate_limit_mw), the 3 auth IDs (core/auth),
  ``adapter.unavailable`` / ``gcs.unavailable`` (adapter transport failure),
  and ``server.internal_error`` (the generic-exception fallback).

Every key matches the §5A.H locked regex
``^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$`` EXCEPT ``server.internal_error``
which is a 2-segment dynamic envelope value (not a true registry key — same
§5A D1 precedent as the monolith; it falls through to the supplied fallback
prose in ``core/errors``).
"""

from __future__ import annotations

VALIDATION_MESSAGES: dict[str, str] = {
    # ── §11 image (module-specific) ──────────────────────────────────────
    "validation.image.invalid_format": "Only JPEG images are accepted.",
    "validation.image.too_large": "Image exceeds the 10 MB upload limit.",
    "validation.image.invalid_idx": "Image slot must be between 1 and 4.",
    "image.slot.occupied": (
        "This image slot already has an image. Please remove it first or pick another slot."
    ),
    "image.not.found": "We couldn't find that image. It may have been deleted.",
    # ── catalog ownership shim (raised by catalog_client) ────────────────
    "catalog.product.not_found": "Product not found.",
    # ── ai_ops watermark.v1 vendored path (rare escape; normally fallback) ─
    "ai_ops.budget.exhausted": (
        "AI features are temporarily unavailable for today. Please try again later."
    ),
    "gemini.unavailable": "The AI service is temporarily unavailable. Please try again.",
    # ── cross-cutting (raised by the vendored core layer) ────────────────
    "tenancy.cross_user_access": "You do not have access to this resource.",
    "rate_limit.exceeded": "Too many requests. Please slow down and try again.",
    "auth.token_missing": "Authorization token missing or malformed.",
    "auth.token_expired": "Your session has expired. Please sign in again.",
    "auth.user_not_found": "Authenticated user no longer exists.",
    # ── §6.G adapter (GCS transport failure raised inside the pipeline) ──
    "adapter.unavailable": "A required service is temporarily unavailable. Please try again.",
    "gcs.unavailable": "File storage is temporarily unavailable. Please try again.",
}


__all__ = ["VALIDATION_MESSAGES"]
