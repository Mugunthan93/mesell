"""svc-export English message registry — vendored SUBSET.

Carries ONLY:

* the 7 export module-specific IDs (raised by ``app.exceptions``);
  NOTE the not-found exception uses ``export.lookup.not_found`` per the
  monolith ``ExportNotFoundError.validation_message_id``;
* the cross-cutting IDs the vendored core layer raises:
  ``tenancy.cross_user_access`` (core/tenancy), ``rate_limit.exceeded``
  (core/middleware/rate_limit_mw), the 3 auth IDs (core/auth), and
  ``server.internal_error`` (the generic-exception fallback).

Every key matches the §5A.H locked regex
``^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$`` EXCEPT ``server.internal_error``
which is a 2-segment dynamic envelope value (not a true registry key — same
§5A D1 precedent as the monolith; it falls through to the supplied fallback
prose in ``core/errors``).
"""

from __future__ import annotations

VALIDATION_MESSAGES: dict[str, str] = {
    # ── §14 export (module-specific) ─────────────────────────────────────
    "export.lookup.not_found": "Export not found.",
    "export.product.not_ready": (
        "Product is not ready for export. Complete the product setup first."
    ),
    "export.front_image.missing": (
        "A front image is required to export with images. Upload an image in slot 1."
    ),
    "export.enum.validation_failed": (
        "Export failed: an invalid value was detected. Please re-run the export."
    ),
    "export.compliance.strategy_failed": (
        "Export failed: unable to process compliance information."
    ),
    "export.xlsx.build_failed": "Export failed: unable to generate the XLSX file.",
    "export.round_trip.mismatch": (
        "Export failed: data validation mismatch. Please re-run the export."
    ),
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
