"""§14.K integration runner — exercises the 15 golden round-trip fixtures.

Per `MVP_ARCH §5.7.4` + §14.K coverage matrix.  For each fixture in
``tests/integration/golden_round_trip/fixture_NN_<name>.json``:

1. Reconstruct the :class:`XlsxRowSpec` from
   ``expected_xlsx_canonical`` + the schema's ``meesho_column_header``s.
2. Run :func:`export.service._write_xlsx` → bytes.
3. Run :func:`export.service._round_trip_validate` → must pass.

The fixture-level enum translation step (fixtures 9 + 10) is exercised
by an additional parametrised call to :func:`_translate_enums` for the
2 enum-bearing fixtures — the unit tests
``test_enum_translation_*.py`` cover the translator's edge cases, this
runner just confirms the fixtures' canonical → meesho mappings round-
trip cleanly.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.golden_roundtrip

from app.modules.export.domain import XlsxColumnSpec, XlsxRowSpec
from app.modules.export.service import _round_trip_validate, _write_xlsx

FIXTURES_DIR = Path(__file__).parent / "golden_round_trip"


def _load_all_fixtures() -> list[tuple[str, dict]]:
    """Load every ``fixture_*.json`` from the directory."""
    out: list[tuple[str, dict]] = []
    for path in sorted(FIXTURES_DIR.glob("fixture_*.json")):
        with path.open("r", encoding="utf-8") as fh:
            out.append((path.name, json.load(fh)))
    return out


def _row_from_fixture(fixture: dict) -> XlsxRowSpec:
    """Reconstruct an :class:`XlsxRowSpec` from a fixture envelope.

    Maps each expected column → ``XlsxColumnSpec`` whose
    ``meesho_column_header`` is sourced from the schema (preserves
    typos per §0.G §12.2 + §14-EXPORT-D7).
    """
    schema = fixture["schema"]
    header_map = {
        str(f["canonical_name"]): str(f["meesho_column_header"])
        for f in schema["fields"]
    }
    index_map = {
        str(f["canonical_name"]): i
        for i, f in enumerate(schema["fields"])
    }
    expected = fixture["expected_xlsx_canonical"]
    columns: list[XlsxColumnSpec] = []
    for col in expected["columns"]:
        canonical = str(col["canonical_name"])
        # Use the explicit `meesho_header_expected` override when the
        # fixture asserts a specific Meesho header (e.g. fixture 2 typo).
        header = col.get("meesho_header_expected") or header_map.get(
            canonical, canonical
        )
        columns.append(
            XlsxColumnSpec(
                canonical_name=canonical,
                meesho_column_header=str(header),
                meesho_column_index=index_map.get(canonical, len(columns)),
                value=col["value"],
            )
        )
    return XlsxRowSpec(
        main_sheet_label=str(expected["main_sheet_label"]),
        columns=tuple(columns),
        compliance_block=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Round-trip runner — parametrised over all 15 fixtures.
# ─────────────────────────────────────────────────────────────────────────────
_FIXTURES = _load_all_fixtures()


def test_fixture_count_is_exactly_15():
    """The §14.K coverage matrix locks 15 fixtures."""
    assert len(_FIXTURES) == 15, (
        f"Expected 15 fixtures per §14.K; got {len(_FIXTURES)}: "
        f"{[name for name, _ in _FIXTURES]}"
    )


@pytest.mark.parametrize(
    "fixture_name, fixture",
    _FIXTURES,
    ids=[name for name, _ in _FIXTURES],
)
def test_golden_fixture_round_trip(fixture_name, fixture):
    """For each fixture: reconstruct the row, write the XLSX, re-parse,
    and assert round-trip equivalence.
    """
    row = _row_from_fixture(fixture)
    xlsx_bytes = _write_xlsx(row)
    assert len(xlsx_bytes) > 0, f"{fixture_name}: empty XLSX bytes"

    result = _round_trip_validate(xlsx_bytes, row)
    assert result.passed, (
        f"{fixture_name}: round-trip failed.  "
        f"Mismatches={result.mismatches}.  Diagnostic={result.diagnostic}"
    )
    assert result.mismatches == ()


# ─────────────────────────────────────────────────────────────────────────────
# Enum-translation exercise for the 2 fixtures with `enum_payloads`.
# ─────────────────────────────────────────────────────────────────────────────
_ENUM_FIXTURES = [
    (name, fixture)
    for name, fixture in _FIXTURES
    if "enum_payloads" in fixture
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_name, fixture",
    _ENUM_FIXTURES,
    ids=[name for name, _ in _ENUM_FIXTURES],
)
async def test_golden_fixture_enum_translation(
    fixture_name,
    fixture,
    monkeypatch,
):
    """For each enum-bearing fixture: run the column values through
    :func:`_translate_enums` with the fixture's enum_payloads as the
    mocked category lookup; assert each translation produces the
    expected meesho value.
    """
    from app.modules.export import service as svc

    enum_payloads = fixture["enum_payloads"]

    async def fake_get_field_enum(category_id, field_name, db):
        from app.modules.category.exceptions import FieldEnumNotFoundError

        if field_name not in enum_payloads:
            raise FieldEnumNotFoundError()
        return enum_payloads[field_name]

    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)

    # Build a row from the INPUT snapshot (pre-translation values).
    schema = fixture["schema"]
    header_map = {
        str(f["canonical_name"]): str(f["meesho_column_header"])
        for f in schema["fields"]
    }
    input_fields = fixture["input_snapshot"]["product"]["fields_jsonb"]
    columns = []
    for i, f in enumerate(schema["fields"]):
        canonical = str(f["canonical_name"])
        columns.append(
            XlsxColumnSpec(
                canonical_name=canonical,
                meesho_column_header=header_map.get(canonical, canonical),
                meesho_column_index=i,
                value=input_fields.get(canonical, ""),
            )
        )
    row = XlsxRowSpec(
        main_sheet_label=schema["main_sheet_label"],
        columns=tuple(columns),
        compliance_block=None,
    )
    db_mock = AsyncMock()
    translated = await svc._translate_enums(row, uuid4(), db=db_mock)

    # Build expected map from fixture's expected_xlsx_canonical.
    expected_map = {
        str(col["canonical_name"]): col["value"]
        for col in fixture["expected_xlsx_canonical"]["columns"]
    }
    translated_map = {col.canonical_name: col.value for col in translated.columns}
    for canonical, expected_value in expected_map.items():
        assert translated_map.get(canonical) == expected_value, (
            f"{fixture_name}: enum translation mismatch on '{canonical}'. "
            f"Expected={expected_value!r}, got={translated_map.get(canonical)!r}"
        )
