"""§14.K unit test 9 — alias restoration / typo preservation.

Per §0.G §12.2 + §14-EXPORT-D7: the schema field's
``meesho_column_header`` is sourced verbatim from
``templates.schema_jsonb.fields[*].meesho_column_header`` (seed-time
embedded).  Typo-preserved headers like "No. of Primiary Cameras" must
appear unchanged in the XlsxColumnSpec.

Step 7 (``_restore_aliases``) is a runtime no-op because the seed
pipeline already pre-embeds the typo-preserved headers — this test
verifies the no-op preserves the header from step 3.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit

from app.modules.export.service import _build_row, _restore_aliases


@pytest.mark.asyncio
async def test_typo_preserved_in_meesho_column_header(
    compliance_block_full,
    monkeypatch,
):
    """Seed schema field carries typo-preserved header → :func:`_build_row`
    emits it verbatim → :func:`_restore_aliases` no-ops."""
    from app.modules.export import service as svc

    async def fake_get_compliance_block(user_id, db):
        return compliance_block_full

    monkeypatch.setattr(svc.customer_service, "get_compliance_block", fake_get_compliance_block)

    schema = {
        "fields": [
            {
                "canonical_name": "no_of_primary_cameras",
                "meesho_column_header": "No. of Primiary Cameras",  # intentional typo
                "data_type": "number",
                "primitive": "integer",
                "marker": "optional",
                "enum_resolver": None,
                "is_advanced": False,
                "help_text": "h",
                "validation_message_ids": [],
            }
        ],
        "compulsory_count": 0,
        "optional_count": 1,
        "total_count": 1,
        "wizard_step_count": 1,
        "main_sheet_label": "Sheet",
        "compliance_shape": "standard",
    }

    snapshot = SimpleNamespace(
        product_id=None,
        category_id=None,
        fields={"no_of_primary_cameras": 4},
        ai_suggestions={},
        image_refs=(),
        validation_summary=SimpleNamespace(status="ready"),
    )

    row = await _build_row(
        product_id=None,
        user_id=None,
        schema=schema,
        snapshot=snapshot,
        db=AsyncMock(),
    )
    # Verify the typo is preserved verbatim in the header.
    assert row.columns[0].meesho_column_header == "No. of Primiary Cameras"
    assert row.columns[0].canonical_name == "no_of_primary_cameras"

    # Step 7 — restore_aliases is a no-op at runtime per D7.
    restored = _restore_aliases(row, schema)
    assert restored.columns[0].meesho_column_header == "No. of Primiary Cameras"
    # The restored row IS the same row identity-wise (no-op).
    assert restored is row


@pytest.mark.asyncio
async def test_second_typo_seconadry_preserved(
    compliance_block_full,
    monkeypatch,
):
    """The second canonical typo per §0.G §12.2 — "Seconadry" — also
    passes through verbatim."""
    from app.modules.export import service as svc

    async def fake_get_compliance_block(user_id, db):
        return compliance_block_full

    monkeypatch.setattr(svc.customer_service, "get_compliance_block", fake_get_compliance_block)

    schema = {
        "fields": [
            {
                "canonical_name": "no_of_secondary_cameras",
                "meesho_column_header": "No. of Seconadry Cameras",  # intentional typo
                "data_type": "number",
                "primitive": "integer",
                "marker": "optional",
                "enum_resolver": None,
                "is_advanced": False,
                "help_text": "h",
                "validation_message_ids": [],
            }
        ],
        "compulsory_count": 0,
        "optional_count": 1,
        "total_count": 1,
        "wizard_step_count": 1,
        "main_sheet_label": "Sheet",
        "compliance_shape": "standard",
    }
    snapshot = SimpleNamespace(
        product_id=None,
        category_id=None,
        fields={"no_of_secondary_cameras": 2},
        ai_suggestions={},
        image_refs=(),
        validation_summary=SimpleNamespace(status="ready"),
    )
    row = await _build_row(
        product_id=None,
        user_id=None,
        schema=schema,
        snapshot=snapshot,
        db=AsyncMock(),
    )
    assert row.columns[0].meesho_column_header == "No. of Seconadry Cameras"
