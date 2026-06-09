"""``export`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §14.H (LOCKED 2026-06-05).

Validation-message-id convention (§5A.H locked regex)::

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

Seven export-specific IDs ship in ``app/i18n/messages_en.py`` per §5A.I
+ §14.J (already shipped at §5A construction time, normalised to
3-segment per the §5A.H regex).

============================================  =======  ==========================================
Class                                         status   validation_message_id
============================================  =======  ==========================================
ExportError (base)                            —        — (inherits MeesellError defaults)
ExportNotFoundError                           404      export.lookup.not_found
ProductNotReadyForExportError                 422      export.product.not_ready
FrontImageMissingError                        422      export.front_image.missing
ExportEnumValidationError                     500      export.enum.validation_failed
ComplianceStrategyError                       500      export.compliance.strategy_failed
XlsxBuildError                                500      export.xlsx.build_failed
RoundTripValidationError                      500      export.round_trip.mismatch
============================================  =======  ==========================================

DECISION FLAG §14-EXPORT-D3 — error_code-in-error_message prefix
----------------------------------------------------------------
The ``exports`` DDL ships WITHOUT an ``error_code`` column (Wave 1 fixed
shape; sub-session may not migrate per protocol §5.0).  The 4
worker-internal 500-class exceptions carry an ``error_code`` class
attribute that the worker concatenates as a ``"[code] message"`` prefix
into the existing ``exports.error_message`` column.  The GET response
parses the bracketed prefix back into the API's ``error_code`` field.
This preserves the §14.B.2 wire contract while honoring the locked DDL.

DECISION FLAG §14-EXPORT-D11 — 3-segment normalisation
------------------------------------------------------
§14.H prose lists 2-segment shorthand IDs (``export.not_found``,
``export.product_not_ready``, etc.).  Wire to the canonical 3-segment
IDs already registered in ``messages_en.py`` per §5A.H — same precedent
as §7 iam (memory D2), §8 customer (D5), §9 category (D3), §10 catalog
(D3), §11 image (D2), §12 pricing (D3a).
"""

from __future__ import annotations

from app.core.errors import MeesellError


class ExportError(MeesellError):
    """Base class for ``export`` module failures.  Never raised directly."""

    code = "export.base"


# ─────────────────────────────────────────────────────────────────────────────
# 404 / 422 — router surface (raised before Celery enqueue)
# ─────────────────────────────────────────────────────────────────────────────
class ExportNotFoundError(ExportError):
    """GET /exports/{id} — no row matches the user-scoped query.

    Conflates non-existent + cross-tenant per §4.C privacy posture.
    """

    code = "export.not_found"
    status_code = 404
    validation_message_id = "export.lookup.not_found"

    def __init__(self, detail: str = "Export not found.") -> None:
        super().__init__(detail=detail)


class ProductNotReadyForExportError(ExportError):
    """POST /products/{id}/export-xlsx — product.status != 'ready'.

    Also fires when the product's front-image precheck is
    ``failed_precheck`` per §10 cascade (the product's status flips to
    non-ready when the front image fails precheck).
    """

    code = "export.product_not_ready"
    status_code = 422
    validation_message_id = "export.product.not_ready"

    def __init__(
        self,
        detail: str = (
            "Product is not ready for export.  Complete the product setup "
            "first."
        ),
    ) -> None:
        super().__init__(detail=detail)


class FrontImageMissingError(ExportError):
    """POST /products/{id}/export-xlsx with ``format='xlsx_with_images'``
    requires at least 1 image with ``idx=1`` AND ``status='ready'`` per
    `MVP_ARCH §0` premise #3 (the front image MUST be in slot 1).
    """

    code = "export.front_image_missing"
    status_code = 422
    validation_message_id = "export.front_image.missing"

    def __init__(
        self,
        detail: str = (
            "A front image is required to export with images.  Upload an "
            "image in slot 1."
        ),
    ) -> None:
        super().__init__(detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# 500 — worker-internal (status='failed' + error_message + error_code)
#
# Each class carries an ``error_code`` class attribute that the orchestrator
# concatenates as the ``"[code] message"`` prefix into the
# ``exports.error_message`` column per §14-EXPORT-D3.
# ─────────────────────────────────────────────────────────────────────────────
class ExportEnumValidationError(ExportError):
    """Step 5 — Layer 3 hallucination guardrail rejection per
    `MVP_ARCH §9.7`.

    A canonical enum value emitted by AI autofill (or typed by the seller)
    is not present in ``field_enum_values.enum_entries`` for the relevant
    ``(category_id, field_name)`` combo.  The deterministic safety net
    that holds the line even if Layer 1 (prompt prefix) and Layer 2
    (post-response re-validation in §6A.E) were bypassed by a future
    bug.
    """

    code = "export.enum_validation_failed"
    status_code = 500
    validation_message_id = "export.enum.validation_failed"
    error_code: str = "enum_validation_failed"

    def __init__(
        self,
        detail: str = (
            "Export failed: an invalid value was detected.  Please re-run "
            "the export."
        ),
    ) -> None:
        super().__init__(detail=detail)


class ComplianceStrategyError(ExportError):
    """Step 4 — ``strategy.apply(...)`` raised an unexpected exception OR
    ``schema.compliance_shape`` is neither ``'standard'`` nor
    ``'collapsed'``.
    """

    code = "export.compliance_strategy_failed"
    status_code = 500
    validation_message_id = "export.compliance.strategy_failed"
    error_code: str = "compliance_strategy_failed"

    def __init__(
        self,
        detail: str = (
            "Export failed: unable to process compliance information."
        ),
    ) -> None:
        super().__init__(detail=detail)


class XlsxBuildError(ExportError):
    """Step 8 — openpyxl write failed (out-of-memory, corrupt input
    cell, encoding error)."""

    code = "export.xlsx_build_failed"
    status_code = 500
    validation_message_id = "export.xlsx.build_failed"
    error_code: str = "xlsx_build_failed"

    def __init__(
        self,
        detail: str = "Export failed: unable to generate the XLSX file.",
    ) -> None:
        super().__init__(detail=detail)


class RoundTripValidationError(ExportError):
    """Step 9 — re-parse showed canonical mismatch with the input
    snapshot per `MVP_ARCH §5.7`.  The XLSX is logically incorrect; do
    not ship.
    """

    code = "export.round_trip_mismatch"
    status_code = 500
    validation_message_id = "export.round_trip.mismatch"
    error_code: str = "round_trip_mismatch"

    def __init__(
        self,
        detail: str = (
            "Export failed: data validation mismatch.  Please re-run the "
            "export."
        ),
    ) -> None:
        super().__init__(detail=detail)


__all__ = [
    "ComplianceStrategyError",
    "ExportEnumValidationError",
    "ExportError",
    "ExportNotFoundError",
    "FrontImageMissingError",
    "ProductNotReadyForExportError",
    "RoundTripValidationError",
    "XlsxBuildError",
]
