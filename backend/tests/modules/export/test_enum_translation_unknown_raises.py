"""§14.K unit test 8 — unknown enum translation raises Layer 3
guardrail.

A canonical NOT in ``entries[].canonical`` → :class:`ExportEnumValidationError`
per ``MVP_ARCH §9.7``.  This is the Layer 3 hallucination guardrail.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.export.domain import XlsxColumnSpec, XlsxRowSpec
from app.modules.export.exceptions import ExportEnumValidationError
from app.modules.export.service import _translate_enums


@pytest.mark.asyncio
async def test_unknown_canonical_value_raises(monkeypatch):
    """``HALLUCINATED_PLASTIC`` not in the entries set → raises."""
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
                value="HALLUCINATED_PLASTIC",
            ),
        ),
    )
    db_mock = AsyncMock()
    with pytest.raises(ExportEnumValidationError) as exc_info:
        await _translate_enums(row, uuid4(), db=db_mock)
    # Verify Layer 3 envelope conforms to §14.H locks.
    assert exc_info.value.status_code == 500
    assert exc_info.value.error_code == "enum_validation_failed"
    assert exc_info.value.validation_message_id == "export.enum.validation_failed"


@pytest.mark.asyncio
async def test_non_enum_field_passes_through(monkeypatch):
    """When category.service.get_field_enum raises FieldEnumNotFoundError
    the value is treated as non-enum and passes through unchanged."""
    from app.modules.category.exceptions import FieldEnumNotFoundError
    from app.modules.export import service as svc

    async def fake_get_field_enum(category_id, field_name, db):
        raise FieldEnumNotFoundError()

    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)

    row = XlsxRowSpec(
        main_sheet_label="Sheet",
        columns=(
            XlsxColumnSpec(
                canonical_name="description",
                meesho_column_header="Description",
                meesho_column_index=0,
                value="A free-text description.",
            ),
        ),
    )
    db_mock = AsyncMock()
    translated = await _translate_enums(row, uuid4(), db=db_mock)
    assert translated.columns[0].value == "A free-text description."
