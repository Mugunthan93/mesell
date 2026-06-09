"""§14.K unit test 5 — standard strategy 9 → 9 pass-through.

9 input fields → 9 :class:`XlsxColumnSpec` with the canonical_name
unchanged and meesho_column_header sourced from
``column_header_map``.
"""

from __future__ import annotations

from app.modules.export.domain import (
    StandardComplianceStrategy,
    XlsxColumnSpec,
)


_CANONICAL_NAMES = (
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


def test_standard_strategy_emits_exactly_9_columns(compliance_block_full):
    strategy = StandardComplianceStrategy()
    header_map = {
        name: f"Header for {name}" for name in _CANONICAL_NAMES
    }
    index_map = {name: i for i, name in enumerate(_CANONICAL_NAMES)}

    columns = strategy.apply(
        compliance_block_full,
        column_header_map=header_map,
        column_index_map=index_map,
    )

    assert len(columns) == 9
    assert all(isinstance(c, XlsxColumnSpec) for c in columns)


def test_standard_strategy_preserves_canonical_names(compliance_block_full):
    strategy = StandardComplianceStrategy()
    header_map = {name: name.upper() for name in _CANONICAL_NAMES}
    index_map = {name: i for i, name in enumerate(_CANONICAL_NAMES)}

    columns = strategy.apply(
        compliance_block_full,
        column_header_map=header_map,
        column_index_map=index_map,
    )
    emitted_canonicals = [c.canonical_name for c in columns]
    assert emitted_canonicals == list(_CANONICAL_NAMES)


def test_standard_strategy_passes_header_map_into_meesho_header(
    compliance_block_full,
):
    strategy = StandardComplianceStrategy()
    header_map = {
        "manufacturer_name": "Mfr Name (verbatim)",
        "manufacturer_address": "Mfr Address (verbatim)",
        "manufacturer_pincode": "Mfr Pincode (verbatim)",
        "packer_name": "Pkr Name",
        "packer_address": "Pkr Address",
        "packer_pincode": "Pkr Pincode",
        "importer_name": "Imp Name",
        "importer_address": "Imp Address",
        "importer_pincode": "Imp Pincode",
    }
    index_map = {name: i for i, name in enumerate(_CANONICAL_NAMES)}

    columns = strategy.apply(
        compliance_block_full,
        column_header_map=header_map,
        column_index_map=index_map,
    )
    headers = {c.canonical_name: c.meesho_column_header for c in columns}
    assert headers["manufacturer_name"] == "Mfr Name (verbatim)"
    assert headers["packer_address"] == "Pkr Address"


def test_standard_strategy_carries_compliance_values(compliance_block_full):
    strategy = StandardComplianceStrategy()
    header_map = {name: name for name in _CANONICAL_NAMES}
    index_map = {name: i for i, name in enumerate(_CANONICAL_NAMES)}

    columns = strategy.apply(
        compliance_block_full,
        column_header_map=header_map,
        column_index_map=index_map,
    )
    values = {c.canonical_name: c.value for c in columns}
    assert values["manufacturer_name"] == compliance_block_full.manufacturer_name
    assert values["packer_pincode"] == compliance_block_full.packer_pincode
    assert values["importer_address"] == compliance_block_full.importer_address
