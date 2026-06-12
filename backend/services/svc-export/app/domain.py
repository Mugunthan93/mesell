"""``export`` internal domain types per §14.F (LOCKED 2026-06-05).

Vendored from the monolith ``app.modules.export.domain``.  The ONLY import-line
change (spec §3.A / §0.4): the monolith's

    from app.modules.customer.domain import ComplianceBlock

becomes a VENDORED local :class:`ComplianceBlock` dataclass below (same field
shape, cited from ``customer/domain.py`` source — the §16 "domain exchange
currency" pattern).  The customer HTTP shim
(``app.core.extracted_clients.customer_client``) deserializes the customer-svc
JSON into THIS local dataclass.  Every other line below is byte-for-byte from
the monolith domain module.

Owns 5 frozen dataclasses + 1 ``ComplianceStrategy`` ABC + 2 concrete
``ComplianceStrategy`` subclasses + 1 ``MarketplaceExportAdapter`` ABC + 1 V1
concrete ``MeeshoExportAdapter`` subclass + the vendored ``ComplianceBlock``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID


# ─────────────────────────────────────────────────────────────────────────────
# VENDORED ComplianceBlock (spec §3.A / §0.4)
#
# Field shape cited verbatim from app/modules/customer/domain.py:76-94 (the
# monolith ``customer.domain.ComplianceBlock``).  The customer HTTP shim
# deserializes the customer-svc ``/internal/seller-profile/{user_id}/
# compliance-block`` JSON into this local dataclass; the export pipeline's
# strategy step reads ``getattr(compliance_block, <canonical>, None)`` against
# it exactly as it did against the monolith's cross-module import.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ComplianceBlock:
    """The 9 standard Legal Metrology fields + country_of_origin.

    Vendored copy of ``customer.domain.ComplianceBlock`` (the cross-module
    "domain exchange currency").  Field names + nullability match the source
    so the standard/collapsed strategies' ``getattr`` access is unchanged.
    """

    manufacturer_name: str
    manufacturer_address: str
    manufacturer_pincode: str
    packer_name: str
    packer_address: str
    packer_pincode: str
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    country_of_origin: str


# ─────────────────────────────────────────────────────────────────────────────
# Frozen dataclasses (§14.F)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Export:
    """Mirrors the ``exports`` row per MVP_ARCH §2.5.

    DDL-driven fields per §14-EXPORT-D1+D2+D4 — see :mod:`.repository`
    docstring for the column / API mapping.
    """

    id: UUID
    user_id: UUID
    product_id: UUID
    format: Literal["xlsx_only", "xlsx_with_images"]
    status: Literal["pending", "ready", "failed"]
    xlsx_gcs_path: str | None
    zip_gcs_path: str | None
    error_message: str | None
    error_code: str | None
    round_trip_validated: bool | None
    initiated_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class XlsxColumnSpec:
    """One column in the output XLSX.

    M10 boundary: this dataclass holds ``meesho_column_header`` and
    ``meesho_column_index`` — these symbols MUST NOT escape the export module
    per §14.J.
    """

    canonical_name: str
    meesho_column_header: str
    meesho_column_index: int
    value: Any


@dataclass(frozen=True)
class XlsxRowSpec:
    """One row in the output XLSX.

    V1 = one product per export = one row.  The ``compliance_block`` is carried
    alongside ``columns`` so the strategy step (4) can construct compliance
    columns then merge them at the schema-defined positions.
    """

    main_sheet_label: str
    columns: tuple[XlsxColumnSpec, ...]
    compliance_block: ComplianceBlock | None = None


@dataclass(frozen=True)
class RoundTripResult:
    """§5.7 round-trip validator output (step 9)."""

    passed: bool
    mismatches: tuple[str, ...]
    diagnostic: str | None


@dataclass(frozen=True)
class ExportStatusSummary:
    """Cross-module return type for ``service.summary()`` — OPTIONAL per §2.D."""

    product_id: UUID
    latest_export_id: UUID | None
    latest_export_status: Literal["pending", "ready", "failed"] | None
    latest_completed_at: datetime | None


# ─────────────────────────────────────────────────────────────────────────────
# ComplianceStrategy ABC + 2 concrete subclasses (§14.F)
# ─────────────────────────────────────────────────────────────────────────────
class ComplianceStrategy(ABC):
    """Per MVP_ARCH §5.5.5 — Strategy pattern for compliance-block transformation.

    V1 has exactly 2 concrete subclasses: :class:`StandardComplianceStrategy`
    and :class:`CollapsedComplianceStrategy`.
    """

    @abstractmethod
    def apply(
        self,
        compliance_block: ComplianceBlock,
        *,
        column_header_map: dict[str, str],
        column_index_map: dict[str, int],
    ) -> tuple[XlsxColumnSpec, ...]:
        """Transform the 9 standard compliance fields into output XLSX columns.

        Standard:  9 fields → 9 columns (pass-through).
        Collapsed: 9 fields → 3 columns (concatenate manufacturer / packer /
                   importer blocks).
        """


# ─────────────────────────────────────────────────────────────────────────────
# Standard strategy — 9 fields → 9 columns (pass-through)
# ─────────────────────────────────────────────────────────────────────────────
_STANDARD_CANONICAL_FIELDS: tuple[str, ...] = (
    "manufacturer_name",
    "manufacturer_address",
    "manufacturer_pincode",
    "packer_name",
    "packer_address",
    "packer_pincode",
    "importer_name",
    "importer_address",
    "importer_pincode",
)


class StandardComplianceStrategy(ComplianceStrategy):
    """3,771 templates (all except Eye-Serum).  9 fields → 9 columns pass-through."""

    def apply(
        self,
        compliance_block: ComplianceBlock,
        *,
        column_header_map: dict[str, str],
        column_index_map: dict[str, int],
    ) -> tuple[XlsxColumnSpec, ...]:
        out: list[XlsxColumnSpec] = []
        for canonical in _STANDARD_CANONICAL_FIELDS:
            value = getattr(compliance_block, canonical, None)
            header = column_header_map.get(canonical, canonical)
            idx = column_index_map.get(canonical, 0)
            out.append(
                XlsxColumnSpec(
                    canonical_name=canonical,
                    meesho_column_header=header,
                    meesho_column_index=idx,
                    value=value if value is not None else "",
                )
            )
        return tuple(out)


# ─────────────────────────────────────────────────────────────────────────────
# Collapsed strategy — 9 fields → 3 combined "Details" columns
# ─────────────────────────────────────────────────────────────────────────────
_COLLAPSED_CANONICAL_FIELDS: tuple[str, ...] = (
    "manufacturer_details",
    "packer_details",
    "importer_details",
)

_COLLAPSED_TRIPLES: dict[str, tuple[str, str, str]] = {
    "manufacturer_details": (
        "manufacturer_name",
        "manufacturer_address",
        "manufacturer_pincode",
    ),
    "packer_details": (
        "packer_name",
        "packer_address",
        "packer_pincode",
    ),
    "importer_details": (
        "importer_name",
        "importer_address",
        "importer_pincode",
    ),
}

_COLLAPSED_DEFAULT_HEADERS: dict[str, str] = {
    "manufacturer_details": "Manufacturer Details",
    "packer_details": "Packer Details",
    "importer_details": "Importer Details",
}


class CollapsedComplianceStrategy(ComplianceStrategy):
    """1 template (Eye-Serum, leaf 12378).  9 fields → 3 combined "Details" columns.

    Concatenation separator locked at ``', '`` (comma-space) per §0.G §12.6.
    Empty input fields are dropped from the concatenation.
    """

    _SEPARATOR: str = ", "

    def apply(
        self,
        compliance_block: ComplianceBlock,
        *,
        column_header_map: dict[str, str],
        column_index_map: dict[str, int],
    ) -> tuple[XlsxColumnSpec, ...]:
        out: list[XlsxColumnSpec] = []
        for canonical in _COLLAPSED_CANONICAL_FIELDS:
            triple = _COLLAPSED_TRIPLES[canonical]
            parts: list[str] = []
            for field_name in triple:
                raw = getattr(compliance_block, field_name, None)
                if raw is None:
                    continue
                str_val = str(raw).strip()
                if not str_val:
                    continue
                parts.append(str_val)
            value = self._SEPARATOR.join(parts)
            header = column_header_map.get(
                canonical, _COLLAPSED_DEFAULT_HEADERS[canonical]
            )
            idx = column_index_map.get(canonical, 0)
            out.append(
                XlsxColumnSpec(
                    canonical_name=canonical,
                    meesho_column_header=header,
                    meesho_column_index=idx,
                    value=value,
                )
            )
        return tuple(out)


# ─────────────────────────────────────────────────────────────────────────────
# MarketplaceExportAdapter ABC + V1 concrete MeeshoExportAdapter (§14.F)
# ─────────────────────────────────────────────────────────────────────────────
class MarketplaceExportAdapter(ABC):
    """Per MVP_ARCH §5.5.9 — V2 future-proofing for multi-marketplace.

    V1 has exactly ONE concrete subclass: :class:`MeeshoExportAdapter`.
    """

    @abstractmethod
    async def export(
        self,
        product_id: UUID,
        user_id: UUID,
        format: Literal["xlsx_only", "xlsx_with_images"],
    ) -> bytes:
        """Returns the marketplace-format file bytes."""


class MeeshoExportAdapter(MarketplaceExportAdapter):
    """V1 — the only concrete subclass.

    DECISION FLAG §14-EXPORT-D12 — V1 pipeline runs via
    ``service._run_export_pipeline`` directly.  This adapter's ``export`` method
    raises :class:`NotImplementedError`; it is a V2 seam.
    """

    async def export(
        self,
        product_id: UUID,
        user_id: UUID,
        format: Literal["xlsx_only", "xlsx_with_images"],
    ) -> bytes:
        raise NotImplementedError(
            "V1 export runs through export.service._run_export_pipeline "
            "directly (invoked by the Celery task).  The "
            "MeeshoExportAdapter.export seam is reserved for V2 "
            "multi-marketplace dispatch per §14.L."
        )


__all__ = [
    "CollapsedComplianceStrategy",
    "ComplianceBlock",
    "ComplianceStrategy",
    "Export",
    "ExportStatusSummary",
    "MarketplaceExportAdapter",
    "MeeshoExportAdapter",
    "RoundTripResult",
    "StandardComplianceStrategy",
    "XlsxColumnSpec",
    "XlsxRowSpec",
]
