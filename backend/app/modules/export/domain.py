"""``export`` internal domain types per §14.F (LOCKED 2026-06-05).

Owns 5 frozen dataclasses + 1 ``ComplianceStrategy`` ABC + 2 concrete
``ComplianceStrategy`` subclasses + 1 ``MarketplaceExportAdapter`` ABC +
1 V1 concrete ``MeeshoExportAdapter`` subclass.

Philosophy M10 boundary (§14.J)
-------------------------------
The :class:`XlsxColumnSpec` dataclass holds ``meesho_column_header`` and
``meesho_column_index`` — these symbols MUST NOT escape the export
subtree per §19 import-linter contract 9 (AST scanner).  Allowed call
sites:

* ``app/modules/export/domain.py`` (this file)
* ``app/modules/export/service.py``
* ``app/modules/export/tasks.py``
* ``app/adapters/gcs.py`` (write paths — byte-stream upload, no semantic
  awareness of the header strings)

DECISION FLAG §14-EXPORT-D12 — ``MeeshoExportAdapter.export`` is a seam
----------------------------------------------------------------------
The V1 pipeline runs directly through ``service._run_export_pipeline``
(invoked by the Celery task).  The :class:`MeeshoExportAdapter` is
retained as a future-proofing seam for V2 multi-marketplace expansion
per ``MVP_ARCH §5.5.9`` + §14.L.  Its ``export`` method raises
:class:`NotImplementedError` in V1 — the ABC + V1-concrete structure is
locked here so V2 lands as additional sibling subclasses with NO
refactor of the public service surface.

DECISION FLAG §14-EXPORT-D6/D7 (annotated in service.py — not domain)
---------------------------------------------------------------------
The :class:`XlsxColumnSpec.meesho_column_header` is sourced from the
schema envelope's ``fields[*].meesho_column_header`` at service-layer
construction time (D7 — runtime no-op for the §14.C step 7 "restore
aliases" helper because the schema's typo-preserved headers are already
embedded in the seeded template per ``MVP_ARCH §3``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

# The single cross-module domain import (justified by the strategy
# contract demanding a typed input).  Per §14.F.
from app.modules.customer.domain import ComplianceBlock


# ─────────────────────────────────────────────────────────────────────────────
# Frozen dataclasses (§14.F)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Export:
    """Mirrors the ``exports`` row per `MVP_ARCH §2.5`.

    DDL-driven fields per §14-EXPORT-D1+D2+D4 — see :mod:`.repository`
    docstring for the column / API mapping.  Some fields below are
    derived at the API layer rather than persisted directly.
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
    ``meesho_column_index`` — these symbols MUST NOT escape the export
    module per §14.J.

    Attributes:
        canonical_name: Internal canonical field name (the key used in
            ``products.fields_jsonb`` and ``ai_suggestions_jsonb`` per
            §5A.C).
        meesho_column_header: Exact Meesho XLSX header string per
            ``MVP_ARCH §12.2`` typo restore (e.g.
            ``"No. of Primiary Cameras"`` with the intentional typo
            preserved).
        meesho_column_index: Column position per
            ``templates.schema_jsonb.fields[]`` ordering (0-based).
        value: The seller's value, possibly translated via
            ``enum_codes_map`` at step 5 of the pipeline.
    """

    canonical_name: str
    meesho_column_header: str
    meesho_column_index: int
    value: Any


@dataclass(frozen=True)
class XlsxRowSpec:
    """One row in the output XLSX.

    V1 = one product per export = one row.  V1.5 bulk-export will accept
    a ``list[XlsxRowSpec]`` in ``_write_xlsx``.

    The ``compliance_block`` is carried alongside ``columns`` so the
    strategy step (4) can construct compliance columns from the typed
    block, then merge them into ``columns`` at the schema-defined
    positions per §14.C step 4 + step 6.
    """

    main_sheet_label: str
    columns: tuple[XlsxColumnSpec, ...]
    compliance_block: ComplianceBlock | None = None


@dataclass(frozen=True)
class RoundTripResult:
    """§5.7 round-trip validator output (step 9).

    ``mismatches`` lists the canonical field names whose value differs
    between the input snapshot and the re-parsed XLSX.  Empty when
    ``passed=True``.  ``diagnostic`` is the human-readable summary used
    for the surfaced ``error_message`` on validation failure.
    """

    passed: bool
    mismatches: tuple[str, ...]
    diagnostic: str | None


@dataclass(frozen=True)
class ExportStatusSummary:
    """Cross-module return type for ``service.summary()`` — OPTIONAL per
    §2.D matrix (dashboard does NOT consume in V1; surface exists for
    V1.5 elevation).
    """

    product_id: UUID
    latest_export_id: UUID | None
    latest_export_status: Literal["pending", "ready", "failed"] | None
    latest_completed_at: datetime | None


# ─────────────────────────────────────────────────────────────────────────────
# ComplianceStrategy ABC + 2 concrete subclasses (§14.F)
# ─────────────────────────────────────────────────────────────────────────────
class ComplianceStrategy(ABC):
    """Per `MVP_ARCH §5.5.5` — Strategy pattern for compliance-block
    transformation.

    V1 has exactly 2 concrete subclasses:

    * :class:`StandardComplianceStrategy` for the 3,771 templates with
      9-field standard compliance.
    * :class:`CollapsedComplianceStrategy` for the 1 Eye-Serum template
      at leaf 12378 per §0.G §12.6 founder ruling.

    M10 boundary: subclasses MUST produce :class:`XlsxColumnSpec` entries
    whose ``meesho_column_header`` values come from the locked
    ``schema_jsonb.fields[]`` contract per §5A.B — they may NOT invent
    header strings.  The ``column_header_map`` kwarg threads the
    schema-supplied headers into the strategy without coupling the
    strategy to the schema repository.
    """

    @abstractmethod
    def apply(
        self,
        compliance_block: ComplianceBlock,
        *,
        column_header_map: dict[str, str],
        column_index_map: dict[str, int],
    ) -> tuple[XlsxColumnSpec, ...]:
        """Transform the 9 standard compliance fields into output XLSX
        columns.

        Standard:  9 fields → 9 columns (pass-through).
        Collapsed: 9 fields → 3 columns (concatenate manufacturer /
                   packer / importer blocks).

        Args:
            compliance_block: The customer's 9 LM compliance fields per
                ``customer.service.get_compliance_block``.
            column_header_map: Per-canonical-name Meesho column header
                from ``schema_jsonb.fields[*].meesho_column_header``.
                Standard strategy uses 9 keys; collapsed strategy uses
                3 keys (``"manufacturer_details"`` /
                ``"packer_details"`` / ``"importer_details"``).
            column_index_map: Per-canonical-name 0-based column position
                from the schema's ``fields[]`` ordering.

        Returns:
            Frozen tuple of :class:`XlsxColumnSpec`.
        """


# ─────────────────────────────────────────────────────────────────────────────
# Standard strategy — 9 fields → 9 columns (pass-through)
# ─────────────────────────────────────────────────────────────────────────────
# The 9 canonical compliance field names per §8.F + §5A.F (standard shape).
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
    """3,771 templates (all except Eye-Serum).  9 fields → 9 columns
    pass-through.

    Each input field becomes one :class:`XlsxColumnSpec` with its
    ``canonical_name`` unchanged and its ``meesho_column_header``
    sourced from ``column_header_map`` (which itself was sourced from
    ``schema_jsonb.fields[*].meesho_column_header`` per §5A.B at the
    service layer).
    """

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
# The 3 collapsed canonical names + their constituent triples per §0.G §12.6
# founder ruling + §14.F separator-and-empty-drop rules.
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

# Default headers per §14.F prose ("Manufacturer Details" / "Packer Details"
# / "Importer Details").  Schema overrides via column_header_map.
_COLLAPSED_DEFAULT_HEADERS: dict[str, str] = {
    "manufacturer_details": "Manufacturer Details",
    "packer_details": "Packer Details",
    "importer_details": "Importer Details",
}


class CollapsedComplianceStrategy(ComplianceStrategy):
    """1 template (Eye-Serum, leaf 12378).  9 fields → 3 combined
    "Details" columns per §0.G §12.6 founder ruling: 9 stored, 3 derived
    at emit time only.

    Implements Philosophy F4 (no derived data stored — the 3 collapsed
    columns exist ONLY in the XLSX, never in any database column).
    The collapse rule:

        meesho 'Manufacturer Details'  ← concat(name, address, pincode)
        meesho 'Packer Details'        ← concat(name, address, pincode)
        meesho 'Importer Details'      ← concat(name, address, pincode)

    Concatenation separator is locked at ``', '`` (comma-space) per the
    §0.G §12.6 reference XLSX inspection.  Empty input fields are
    dropped from the concatenation (not represented as ``'None'`` or
    empty separators).
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
                # Drop empty + whitespace-only entries from the concat.
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
    """Per `MVP_ARCH §5.5.9` — V2 future-proofing for multi-marketplace.

    V1 has exactly ONE concrete subclass: :class:`MeeshoExportAdapter`.
    V2 will add ``AmazonExportAdapter``, ``FlipkartExportAdapter``,
    ``EtsyExportAdapter`` (scope per ``MVP_ARCH §14``).

    Each subclass owns its marketplace-specific column ordering, alias
    map, and compliance shape — all marketplace knowledge stays inside
    this adapter ABC hierarchy per philosophy M10.

    The ABC is locked here in V1 so the V2 expansion lands as additional
    concrete subclasses with NO refactor of the export module's public
    surface.
    """

    @abstractmethod
    async def export(
        self,
        product_id: UUID,
        user_id: UUID,
        format: Literal["xlsx_only", "xlsx_with_images"],
    ) -> bytes:
        """Returns the marketplace-format file bytes (XLSX or whatever
        the target marketplace expects).
        """


class MeeshoExportAdapter(MarketplaceExportAdapter):
    """V1 — the only concrete subclass.

    DECISION FLAG §14-EXPORT-D12 — V1 pipeline runs via
    ``service._run_export_pipeline`` directly (invoked by the Celery
    task).  This adapter class is a future-proofing seam — its
    ``export`` method raises :class:`NotImplementedError`.  V2
    multi-marketplace expansion will populate the body and shift the
    Celery worker to dispatch through the adapter; V1 leaves the
    pipeline as service-layer helpers for simpler unit testing per
    §14.K.
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
