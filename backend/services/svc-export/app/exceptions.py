"""``export`` module exceptions — subclasses of
:class:`app.core.errors.MeesellError`.

Vendored BYTE-FOR-BYTE from the monolith ``app.modules.export.exceptions``
(BACKEND_ARCHITECTURE.md §14.H).  The single import line
(``from app.core.errors import MeesellError``) is unchanged — ``core.errors``
exists at the same flat path in the svc-export tree.

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
    """GET /exports/{id} — no row matches the user-scoped query."""

    code = "export.not_found"
    status_code = 404
    validation_message_id = "export.lookup.not_found"

    def __init__(self, detail: str = "Export not found.") -> None:
        super().__init__(detail=detail)


class ProductNotReadyForExportError(ExportError):
    """POST /products/{id}/export-xlsx — product.status != 'ready'."""

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
    requires at least 1 image with ``idx=1`` AND ``status='ready'``.
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
# ─────────────────────────────────────────────────────────────────────────────
class ExportEnumValidationError(ExportError):
    """Step 5 — Layer 3 hallucination guardrail rejection per MVP_ARCH §9.7."""

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
    """Step 4 — ``strategy.apply(...)`` raised OR ``schema.compliance_shape``
    is neither ``'standard'`` nor ``'collapsed'``.
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
    """Step 8 — openpyxl write failed."""

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
    """Step 9 — re-parse showed canonical mismatch with the input snapshot."""

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
