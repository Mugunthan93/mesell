"""§14.K unit test 7 — known enum translation.

A canonical enum value present in ``field_enum_values.enum_entries``
must be preserved (V1 identity transform; V1.5 may add friendly-label
substitution per `MVP_ARCH §14`).
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.export.domain import XlsxColumnSpec, XlsxRowSpec
from app.modules.export.service import _translate_enums


@pytest.mark.asyncio
async def test_canonical_enum_known_value_preserved(monkeypatch):
    """``PE-HD`` in the canonical set → emitted as-is in V1."""
    from app.modules.export import service as svc

    async def fake_get_field_enum(category_id, field_name, db):
        return {
            "enum_entries": [
                {"canonical": "PE-HD", "meesho": "PE-HD", "labels": {"en": "HDPE"}},
                {"canonical": "PP", "meesho": "PP", "labels": {"en": "Polypropylene"}},
            ],
            "total": 2,
            "truncated": False,
        }

    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)

    row = XlsxRowSpec(
        main_sheet_label="Sheet",
        columns=(
            XlsxColumnSpec(
                canonical_name="material",
                meesho_column_header="Material",
                meesho_column_index=0,
                value="PE-HD",
            ),
        ),
    )
    db_mock = AsyncMock()
    translated = await _translate_enums(row, uuid4(), db=db_mock)
    assert len(translated.columns) == 1
    assert translated.columns[0].value == "PE-HD"


@pytest.mark.asyncio
async def test_empty_value_skips_enum_lookup(monkeypatch):
    """Empty / None values bypass the lookup (no false enum rejection
    on optional empty fields).
    """
    from app.modules.export import service as svc

    call_counter = {"n": 0}

    async def fake_get_field_enum(category_id, field_name, db):
        call_counter["n"] += 1
        return {"enum_entries": [], "total": 0, "truncated": False}

    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)

    row = XlsxRowSpec(
        main_sheet_label="Sheet",
        columns=(
            XlsxColumnSpec(
                canonical_name="optional_field",
                meesho_column_header="Optional",
                meesho_column_index=0,
                value="",
            ),
            XlsxColumnSpec(
                canonical_name="none_field",
                meesho_column_header="None",
                meesho_column_index=1,
                value=None,
            ),
        ),
    )
    db_mock = AsyncMock()
    translated = await _translate_enums(row, uuid4(), db=db_mock)
    # No enum lookup made because both values are empty/None.
    assert call_counter["n"] == 0
    assert len(translated.columns) == 2
