"""§14.K integration test 3 — round-trip validation failure.

Monkeypatch :func:`_write_xlsx` to produce an XLSX that drops a column.
The :func:`_round_trip_validate` step rejects, the pipeline transitions
to ``status='failed'`` with ``error_code='round_trip_mismatch'``, and
the persisted ``error_message`` carries the ``[round_trip_mismatch]``
prefix per §14-EXPORT-D3.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from app.modules.customer.domain import ComplianceBlock
from app.modules.export.domain import Export


@pytest.mark.asyncio
async def test_round_trip_failure_persists_failed_status(monkeypatch):
    """Force a column-drop in :func:`_write_xlsx` → round-trip fails →
    update_status_failed fires with error_code='round_trip_mismatch'.
    """
    from app.modules.export import service as svc
    from app.shared import database as shared_db

    user_id = uuid4()
    product_id = uuid4()
    category_id = uuid4()
    export_id = uuid4()

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

    # Worker session stub.
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
        fields={"name": "P", "color": "Red"},
        ai_suggestions={},
        image_refs=(),
        validation_summary=SimpleNamespace(status="ready"),
    )
    compliance = ComplianceBlock(
        manufacturer_name="m", manufacturer_address="a", manufacturer_pincode="560001",
        packer_name="p", packer_address="b", packer_pincode="560002",
        importer_name=None, importer_address=None, importer_pincode=None,
        country_of_origin="IN",
    )
    schema = {
        "fields": [
            {
                "canonical_name": "name", "meesho_column_header": "Name",
                "data_type": "text", "primitive": "text_short", "marker": "compulsory",
                "enum_resolver": None, "is_advanced": False, "help_text": "h",
                "validation_message_ids": [],
            },
            {
                "canonical_name": "color", "meesho_column_header": "Color",
                "data_type": "text", "primitive": "text_short", "marker": "optional",
                "enum_resolver": None, "is_advanced": False, "help_text": "h",
                "validation_message_ids": [],
            },
        ],
        "compulsory_count": 1, "optional_count": 1, "total_count": 2,
        "wizard_step_count": 1, "main_sheet_label": "S",
        "compliance_shape": "standard",
    }

    async def fake_find_by_id(db, uid, eid, *, pending_format_hint=None):
        return fake_export

    async def fake_get_product_for_export(pid, uid, db=None):
        return snapshot

    async def fake_get_compliance_block(uid, db):
        return compliance

    async def fake_fetch_schema(cid, db):
        return schema

    from app.modules.category.exceptions import FieldEnumNotFoundError

    async def fake_get_field_enum(cid, fname, db):
        raise FieldEnumNotFoundError()

    monkeypatch.setattr(svc.export_repo, "find_by_id", fake_find_by_id)
    monkeypatch.setattr(svc.catalog_service, "get_product_for_export", fake_get_product_for_export)
    monkeypatch.setattr(svc.customer_service, "get_compliance_block", fake_get_compliance_block)
    monkeypatch.setattr(svc.category_service, "fetch_schema", fake_fetch_schema)
    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)

    # Patch _write_xlsx to drop the last column from the XLSX before
    # writing — this guarantees a round-trip mismatch.
    from openpyxl import Workbook

    def broken_write_xlsx(row):
        wb = Workbook()
        ws = wb.active
        ws.title = row.main_sheet_label[:31]
        # DROP the last column on header AND data rows.
        truncated_headers = [c.meesho_column_header for c in row.columns[:-1]]
        truncated_values = [c.value for c in row.columns[:-1]]
        ws.append(truncated_headers)
        ws.append(truncated_values)
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    monkeypatch.setattr(svc, "_write_xlsx", broken_write_xlsx)

    # Ensure GCS upload won't run (round-trip rejects before upload).
    upload_calls = {"n": 0}

    async def fake_upload(path, data, content_type=None, **kw):
        upload_calls["n"] += 1

    monkeypatch.setattr(svc.gcs_adapter, "upload_bytes", fake_upload)

    # Hint stub.
    async def fake_read_hint(eid):
        return "xlsx_only"

    monkeypatch.setattr(svc, "_read_format_hint", fake_read_hint)

    # Capture the failure persist.
    fail_calls = {"args": None, "n": 0}

    async def fake_update_status_failed(**kwargs):
        fail_calls["args"] = kwargs
        fail_calls["n"] += 1
        return fake_export

    monkeypatch.setattr(svc.export_repo, "update_status_failed", fake_update_status_failed)

    # ── Run ───────────────────────────────────────────────────────────
    await svc._run_export_pipeline(export_id, user_id)

    # ── Assertions ────────────────────────────────────────────────────
    assert fail_calls["n"] == 1
    args = fail_calls["args"]
    assert args["error_code"] == "round_trip_mismatch"
    # update_status_ready must NOT fire on failure path.
    assert upload_calls["n"] == 0


def test_repository_prefix_round_trip_via_parse():
    """Independent unit-style assertion: the repository's
    ``_parse_error_code`` helper round-trips the
    ``[round_trip_mismatch]`` prefix per §14-EXPORT-D3.
    """
    from app.modules.export.repository import _parse_error_code

    composed = "[round_trip_mismatch] Value mismatch on fields: ['color']"
    code, msg = _parse_error_code(composed)
    assert code == "round_trip_mismatch"
    assert msg == "Value mismatch on fields: ['color']"
