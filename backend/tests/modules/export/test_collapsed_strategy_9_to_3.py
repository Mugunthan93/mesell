"""§14.K unit test 6 — collapsed strategy 9 → 3.

9 input fields → 3 combined "Details" columns concatenating
manufacturer / packer / importer with ', ' separator per §14.F.
Empty input fields are dropped from the concatenation.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from app.modules.export.domain import (
    CollapsedComplianceStrategy,
    XlsxColumnSpec,
)


_COLLAPSED_NAMES = ("manufacturer_details", "packer_details", "importer_details")


def test_collapsed_strategy_emits_exactly_3_columns(compliance_block_full):
    strategy = CollapsedComplianceStrategy()
    columns = strategy.apply(
        compliance_block_full,
        column_header_map={},
        column_index_map={},
    )
    assert len(columns) == 3
    assert all(isinstance(c, XlsxColumnSpec) for c in columns)


def test_collapsed_strategy_default_header_labels(compliance_block_full):
    strategy = CollapsedComplianceStrategy()
    columns = strategy.apply(
        compliance_block_full,
        column_header_map={},
        column_index_map={},
    )
    headers = {c.canonical_name: c.meesho_column_header for c in columns}
    assert headers["manufacturer_details"] == "Manufacturer Details"
    assert headers["packer_details"] == "Packer Details"
    assert headers["importer_details"] == "Importer Details"


def test_collapsed_strategy_concatenates_with_comma_space(
    compliance_block_full,
):
    strategy = CollapsedComplianceStrategy()
    columns = strategy.apply(
        compliance_block_full,
        column_header_map={},
        column_index_map={},
    )
    values = {c.canonical_name: c.value for c in columns}
    # Manufacturer triple: (name, address, pincode) joined by ", "
    assert values["manufacturer_details"] == (
        f"{compliance_block_full.manufacturer_name}, "
        f"{compliance_block_full.manufacturer_address}, "
        f"{compliance_block_full.manufacturer_pincode}"
    )


def test_collapsed_strategy_drops_empty_fields(compliance_block_with_empties):
    """The packer triple has an empty address — it must NOT appear as
    a stray ", " in the concatenation.  The importer triple is fully
    None — the result must be an empty string."""
    strategy = CollapsedComplianceStrategy()
    columns = strategy.apply(
        compliance_block_with_empties,
        column_header_map={},
        column_index_map={},
    )
    values = {c.canonical_name: c.value for c in columns}
    # Manufacturer trio fully populated.
    assert values["manufacturer_details"] == (
        f"{compliance_block_with_empties.manufacturer_name}, "
        f"{compliance_block_with_empties.manufacturer_address}, "
        f"{compliance_block_with_empties.manufacturer_pincode}"
    )
    # Packer trio — address is empty → dropped.
    assert values["packer_details"] == (
        f"{compliance_block_with_empties.packer_name}, "
        f"{compliance_block_with_empties.packer_pincode}"
    )
    # Importer trio — all None → empty string (no "None, None, None").
    assert values["importer_details"] == ""


def test_collapsed_strategy_honors_schema_header_override(
    compliance_block_full,
):
    """Schema-supplied headers (via column_header_map) override the
    default labels.
    """
    strategy = CollapsedComplianceStrategy()
    custom_headers = {
        "manufacturer_details": "Mfr Combined",
        "packer_details": "Pkr Combined",
        "importer_details": "Imp Combined",
    }
    columns = strategy.apply(
        compliance_block_full,
        column_header_map=custom_headers,
        column_index_map={},
    )
    headers = {c.canonical_name: c.meesho_column_header for c in columns}
    assert headers == custom_headers
