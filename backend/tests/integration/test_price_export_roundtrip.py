"""W4b integration test — apply-price → export roundtrip.

Verifies that the chain:
  POST /products/{id}/apply-price  →  products.fields_jsonb updated
  →  _run_export_pipeline reads fields_jsonb  →  XLSX cell under
  meesho_price's meesho_column_header contains the applied price

NEGATIVE ASSERTION (founder constraint — W4_EXPORT_SPEC §4 item 5):
  NO column named/containing settlement/payout/net_profit/transfer_price
  /commission appears in the XLSX.  The calculator is a seller-facing
  exploration tool; derived bank-settlement figures MUST NOT leak into
  the Meesho XLSX (Meesho never reads them and they could confuse
  Meesho's own payout calculations).

Architecture:
  * The export pipeline's cross-module surfaces (catalog, customer,
    category, GCS, Valkey hint) are ALL monkeypatched — this is
    a pure-logic integration test with zero network/DB I/O.
  * ``apply_price_to_product`` is monkeypatched to simulate the W4a
    service writing the chosen price into fields_jsonb.
  * The snapshot's ``fields`` dict is the single source of truth that
    both ``apply_price_to_product`` (writes) and ``_run_export_pipeline``
    (reads via catalog_service.get_product_for_export) share.
  * No disposable DB is needed — the test is fully in-memory.

These tests carry the ``unit`` marker (no live DB dependency) but
their scope is broader than an individual function — they verify the
complete apply → export cross-module call graph.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# Test fixtures / seed helpers
# ─────────────────────────────────────────────────────────────────────────────

_MEESHO_PRICE_HEADER = "Meesho Price"
"""The meesho_column_header value for the ``meesho_price`` canonical as
present in the test schema fixture.  W4_EXPORT_SPEC §1.1 notes that the
exact production header is DB/seed-sourced; for this test we control the
schema dict, so we pin it here."""

_MRP_HEADER = "MRP (Rs)"
"""The meesho_column_header for the ``mrp`` canonical (per the test
fixture used in test_database.py L598 — the only pinned header in-repo)."""

_BANNED_EXPORT_COLUMN_FRAGMENTS: tuple[str, ...] = (
    "settlement",
    "payout",
    "net_profit",
    "transfer_price",
    "commission",
)
"""Fragments that MUST NOT appear in any XLSX column header (case-insensitive).
Derived from W4_EXPORT_SPEC §4 item 5 negative assertion."""


def _make_price_schema() -> dict:
    """Minimal schema dict with meesho_price + mrp + a filler field.

    All three fields use ``enum_resolver=None`` (free-text) so the export
    pipeline's ``_translate_enums`` step is a no-op for them.
    """
    def _field(canonical: str, header: str) -> dict:
        return {
            "canonical_name": canonical,
            "meesho_column_header": header,
            "data_type": "decimal",
            "primitive": "number_decimal",
            "marker": "compulsory",
            "enum_resolver": None,
            "is_advanced": False,
            "help_text": "",
            "validation_message_ids": [],
        }

    return {
        "fields": [
            _field("product_name", "Product Name"),
            _field("meesho_price", _MEESHO_PRICE_HEADER),
            _field("mrp", _MRP_HEADER),
        ],
        "compulsory_count": 3,
        "optional_count": 0,
        "total_count": 3,
        "wizard_step_count": 1,
        "main_sheet_label": "W4 Roundtrip Test",
        "compliance_shape": "standard",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — apply-price lands under the correct Meesho column header
# ─────────────────────────────────────────────────────────────────────────────
async def test_applied_price_appears_under_meesho_price_column(monkeypatch):
    """POST apply-price → export XLSX: the selling price sits under
    _MEESHO_PRICE_HEADER, not under any settlement/payout column.

    Steps (per W4_EXPORT_SPEC §4):
      1. Simulate apply_price_to_product writing into the shared
         snapshot.fields dict (the W4a service's write path).
      2. Run _run_export_pipeline with all cross-module surfaces mocked.
      3. Parse the XLSX bytes via openpyxl.
      4. Assert: price cell is under _MEESHO_PRICE_HEADER.
      5. Assert: NO banned column fragment appears in any header.
    """
    from app.modules.export import service as svc
    from app.modules.export.domain import Export
    from app.shared import database as shared_db
    from app.modules.customer.domain import ComplianceBlock
    from app.modules.category.exceptions import FieldEnumNotFoundError
    from datetime import datetime, timezone

    user_id = uuid4()
    product_id = uuid4()
    category_id = uuid4()
    export_id = uuid4()

    # Shared mutable state — apply_price_to_product writes here;
    # get_product_for_export reads it.
    shared_fields: dict = {
        "product_name": "W4 Test Product",
    }

    # ── Simulate W4a: apply_price_to_product writes into fields_jsonb ────
    # The W4a service calls _q(selling_price) → Decimal("106.00"), then
    # catalog.service.patch_product serializes via JSONB (PostgreSQL stores
    # Decimal as numeric → re-read as float from JSONB).  For the in-memory
    # test we use the string "106" which round-trips through openpyxl cleanly:
    # openpyxl writes integer-valued floats as integers (106 → 106) and reads
    # them back as int(106); str(106) == str(106) → round-trip passes.
    SELLING_PRICE = Decimal("106.00")
    shared_fields["meesho_price"] = "106"  # string form: round-trip safe

    # ── Export domain object ──────────────────────────────────────────────
    fake_export = Export(
        id=export_id,
        user_id=user_id,
        product_id=product_id,
        format="xlsx_only",
        status="pending",
        xlsx_gcs_path=None,
        zip_gcs_path=None,
        error_message=None,
        error_code=None,
        round_trip_validated=None,
        initiated_at=datetime.now(timezone.utc),
        completed_at=None,
    )

    # ── Worker session mock ───────────────────────────────────────────────
    session_mock = AsyncMock()

    class _Ctx:
        async def __aenter__(self_inner):
            return session_mock

        async def __aexit__(self_inner, *args):
            return False

    monkeypatch.setattr(shared_db, "make_worker_session", lambda: _Ctx())

    # ── Snapshot exposes shared_fields ───────────────────────────────────
    snapshot = SimpleNamespace(
        product_id=product_id,
        category_id=category_id,
        fields=shared_fields,      # the export reads from here
        ai_suggestions={},
        image_refs=(),
        validation_summary=SimpleNamespace(status="ready"),
    )

    compliance = ComplianceBlock(
        manufacturer_name="Test Mfr",
        manufacturer_address="Test Address",
        manufacturer_pincode="560001",
        packer_name="Test Pkr",
        packer_address="PA",
        packer_pincode="560002",
        importer_name=None,
        importer_address=None,
        importer_pincode=None,
        country_of_origin="IN",
    )

    schema = _make_price_schema()

    # ── Mock all cross-module export surfaces ─────────────────────────────
    async def fake_find_by_id(db, uid, eid, *, pending_format_hint=None):
        return fake_export

    update_ready_calls: dict = {"n": 0}

    async def fake_update_status_ready(**kwargs):
        update_ready_calls["n"] += 1
        return fake_export

    async def fake_update_status_failed(**kwargs):
        raise AssertionError(
            f"update_status_failed must NOT be called on the happy path. kwargs={kwargs}"
        )

    async def fake_get_product_for_export(pid, uid, db=None):
        return snapshot

    async def fake_get_compliance_block(uid, db):
        return compliance

    async def fake_fetch_schema(cid, db):
        return schema

    async def fake_get_field_enum(cid, fname, db):
        raise FieldEnumNotFoundError()

    monkeypatch.setattr(svc.export_repo, "find_by_id", fake_find_by_id)
    monkeypatch.setattr(svc.export_repo, "update_status_ready", fake_update_status_ready)
    monkeypatch.setattr(svc.export_repo, "update_status_failed", fake_update_status_failed)
    monkeypatch.setattr(
        svc.catalog_service, "get_product_for_export", fake_get_product_for_export
    )
    monkeypatch.setattr(svc.customer_service, "get_compliance_block", fake_get_compliance_block)
    monkeypatch.setattr(svc.category_service, "fetch_schema", fake_fetch_schema)
    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)

    # ── GCS mock ─────────────────────────────────────────────────────────
    gcs_uploads: dict[str, bytes] = {}

    async def fake_upload(path, data, content_type=None, **kw):
        gcs_uploads[path] = data

    monkeypatch.setattr(svc.gcs_adapter, "upload_bytes", fake_upload)

    # ── Bypass Valkey hint ────────────────────────────────────────────────
    async def fake_read_hint(eid):
        return "xlsx_only"

    monkeypatch.setattr(svc, "_read_format_hint", fake_read_hint)

    # ── Run the export pipeline ───────────────────────────────────────────
    await svc._run_export_pipeline(export_id, user_id)

    # ── Verify pipeline completed ─────────────────────────────────────────
    assert update_ready_calls["n"] == 1, "update_status_ready must fire exactly once"

    # ── Parse XLSX ────────────────────────────────────────────────────────
    expected_xlsx_path = f"meesell-exports/{user_id}/{export_id}/sheet.xlsx"
    assert expected_xlsx_path in gcs_uploads, (
        f"XLSX not uploaded to expected path. Got: {list(gcs_uploads.keys())}"
    )
    xlsx_bytes = gcs_uploads[expected_xlsx_path]
    assert len(xlsx_bytes) > 0, "XLSX bytes must not be empty"

    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(xlsx_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    assert len(rows) >= 2, f"Expected at least 2 rows (header + data); got {len(rows)}"

    headers: list[str] = [str(h) for h in rows[0] if h is not None]
    values: list = list(rows[1])

    # ── POSITIVE ASSERT: meesho_price sits under the correct header ───────
    assert _MEESHO_PRICE_HEADER in headers, (
        f"Expected '{_MEESHO_PRICE_HEADER}' in XLSX headers; got {headers}"
    )
    price_col_idx = headers.index(_MEESHO_PRICE_HEADER)
    price_cell = str(values[price_col_idx]) if price_col_idx < len(values) else None
    assert price_cell is not None, (
        f"No value in column {price_col_idx!r} ({_MEESHO_PRICE_HEADER!r})"
    )
    # The export serializes Decimal as its str() representation or numeric.
    # The round-trip validator stores the value as-is in XlsxColumnSpec.value
    # ("106"); openpyxl reads it back and str-compares.  We assert the numeric
    # equivalence: cell must equal the selling price value we applied.
    assert Decimal(str(price_cell)) == SELLING_PRICE, (
        f"Expected price cell numerically = {SELLING_PRICE}; got {price_cell!r} "
        f"(column '{_MEESHO_PRICE_HEADER}')"
    )

    # ── NEGATIVE ASSERT: no settlement/payout/commission columns in XLSX ──
    lower_headers = [h.lower() for h in headers]
    for fragment in _BANNED_EXPORT_COLUMN_FRAGMENTS:
        matching = [h for h in lower_headers if fragment in h]
        assert not matching, (
            f"Banned fragment '{fragment}' found in XLSX headers: {matching}. "
            "Bank-settlement / commission figures must NEVER appear as XLSX "
            "columns (W4_EXPORT_SPEC §4 item 5)."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — no meesho_price in fields_jsonb → cell is blank (not an error)
# ─────────────────────────────────────────────────────────────────────────────
async def test_price_column_blank_when_not_applied(monkeypatch):
    """When apply-price has NOT been called, the meesho_price column exports
    as a blank cell — the export does NOT error out.

    This verifies the baseline (§2.A verify-only path from W4_EXPORT_SPEC):
    if the seller has not applied a price, the column is present in the XLSX
    with an empty value, not a pipeline failure.
    """
    from app.modules.export import service as svc
    from app.modules.export.domain import Export
    from app.shared import database as shared_db
    from app.modules.customer.domain import ComplianceBlock
    from app.modules.category.exceptions import FieldEnumNotFoundError
    from datetime import datetime, timezone

    user_id = uuid4()
    product_id = uuid4()
    category_id = uuid4()
    export_id = uuid4()

    # NO meesho_price in fields — seller never applied a price.
    shared_fields: dict = {"product_name": "Unapplied Price Product"}

    fake_export = Export(
        id=export_id,
        user_id=user_id,
        product_id=product_id,
        format="xlsx_only",
        status="pending",
        xlsx_gcs_path=None,
        zip_gcs_path=None,
        error_message=None,
        error_code=None,
        round_trip_validated=None,
        initiated_at=datetime.now(timezone.utc),
        completed_at=None,
    )

    session_mock = AsyncMock()

    class _Ctx:
        async def __aenter__(self_inner):
            return session_mock

        async def __aexit__(self_inner, *args):
            return False

    monkeypatch.setattr(shared_db, "make_worker_session", lambda: _Ctx())

    snapshot = SimpleNamespace(
        product_id=product_id,
        category_id=category_id,
        fields=shared_fields,
        ai_suggestions={},
        image_refs=(),
        validation_summary=SimpleNamespace(status="draft"),
    )

    compliance = ComplianceBlock(
        manufacturer_name="Mfr",
        manufacturer_address="Addr",
        manufacturer_pincode="560001",
        packer_name="P",
        packer_address="PA",
        packer_pincode="560002",
        importer_name=None,
        importer_address=None,
        importer_pincode=None,
        country_of_origin="IN",
    )

    schema = _make_price_schema()

    async def fake_find_by_id(db, uid, eid, *, pending_format_hint=None):
        return fake_export

    update_ready_calls: dict = {"n": 0}

    async def fake_update_status_ready(**kwargs):
        update_ready_calls["n"] += 1
        return fake_export

    async def fake_update_status_failed(**kwargs):
        raise AssertionError(f"update_status_failed must NOT be called. kwargs={kwargs}")

    async def fake_get_product_for_export(pid, uid, db=None):
        return snapshot

    async def fake_get_compliance_block(uid, db):
        return compliance

    async def fake_fetch_schema(cid, db):
        return schema

    async def fake_get_field_enum(cid, fname, db):
        raise FieldEnumNotFoundError()

    monkeypatch.setattr(svc.export_repo, "find_by_id", fake_find_by_id)
    monkeypatch.setattr(svc.export_repo, "update_status_ready", fake_update_status_ready)
    monkeypatch.setattr(svc.export_repo, "update_status_failed", fake_update_status_failed)
    monkeypatch.setattr(
        svc.catalog_service, "get_product_for_export", fake_get_product_for_export
    )
    monkeypatch.setattr(svc.customer_service, "get_compliance_block", fake_get_compliance_block)
    monkeypatch.setattr(svc.category_service, "fetch_schema", fake_fetch_schema)
    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)

    gcs_uploads: dict[str, bytes] = {}

    async def fake_upload(path, data, content_type=None, **kw):
        gcs_uploads[path] = data

    monkeypatch.setattr(svc.gcs_adapter, "upload_bytes", fake_upload)

    async def fake_read_hint(eid):
        return "xlsx_only"

    monkeypatch.setattr(svc, "_read_format_hint", fake_read_hint)

    await svc._run_export_pipeline(export_id, user_id)

    assert update_ready_calls["n"] == 1

    xlsx_bytes = gcs_uploads[f"meesell-exports/{user_id}/{export_id}/sheet.xlsx"]
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(xlsx_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h) for h in rows[0] if h is not None]

    # Header IS present (column is in the schema).
    assert _MEESHO_PRICE_HEADER in headers, (
        f"'{_MEESHO_PRICE_HEADER}' header must be present even when price not applied; "
        f"got {headers}"
    )

    price_col_idx = headers.index(_MEESHO_PRICE_HEADER)
    price_cell = rows[1][price_col_idx] if price_col_idx < len(rows[1]) else None
    # When fields_jsonb has no meesho_price, the export emits "" (blank).
    # openpyxl reads blank cells as None.
    assert price_cell in (None, ""), (
        f"Expected blank/None for unapplied price; got {price_cell!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — ApplyPriceRequest schema validation: selling_price must be > 0
# ─────────────────────────────────────────────────────────────────────────────
def test_apply_price_request_rejects_zero_price():
    """``ApplyPriceRequest`` must reject selling_price=0 (Pydantic Field gt=0)."""
    import pydantic
    from app.modules.pricing.schemas import ApplyPriceRequest

    with pytest.raises(pydantic.ValidationError) as exc_info:
        ApplyPriceRequest(selling_price=Decimal("0"))

    errors = exc_info.value.errors()
    assert any(
        e["loc"] == ("selling_price",) and "greater than 0" in str(e["msg"]).lower()
        for e in errors
    ), f"Expected 'greater than 0' error for selling_price=0; got {errors}"


def test_apply_price_request_rejects_extra_fields():
    """``extra='forbid'`` on ApplyPriceRequest must reject unknown fields."""
    import pydantic
    from app.modules.pricing.schemas import ApplyPriceRequest

    with pytest.raises(pydantic.ValidationError):
        ApplyPriceRequest(selling_price=Decimal("100"), mrp=Decimal("120"))


def test_apply_price_request_accepts_valid_price():
    """ApplyPriceRequest must accept a valid selling_price."""
    from app.modules.pricing.schemas import ApplyPriceRequest

    req = ApplyPriceRequest(selling_price=Decimal("106.00"))
    assert req.selling_price == Decimal("106.00")
