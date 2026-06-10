"""``export`` module pytest fixtures.

Mostly mock-driven — the §14.K unit tests stand alone from the live
Postgres/Valkey infra by mocking the 6 cross-module service surfaces +
the GCS adapter.  Integration tests use the standard ``db_session`` +
``use_live_valkey`` fixtures from ``tests/conftest.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.modules.customer.domain import ComplianceBlock


# ─────────────────────────────────────────────────────────────────────────────
# Identity fixtures (deterministic UUIDs simplify mock assertions)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def product_id() -> UUID:
    return uuid4()


@pytest.fixture
def export_id() -> UUID:
    return uuid4()


@pytest.fixture
def category_id() -> UUID:
    return uuid4()


# ─────────────────────────────────────────────────────────────────────────────
# Reference data fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def compliance_block_full() -> ComplianceBlock:
    """A fully-populated 9-field standard compliance block."""
    return ComplianceBlock(
        manufacturer_name="ACME Manufacturing",
        manufacturer_address="123 Industrial Estate, Bangalore",
        manufacturer_pincode="560001",
        packer_name="ACME Packers",
        packer_address="456 Warehouse Road, Bangalore",
        packer_pincode="560002",
        importer_name="ACME Imports",
        importer_address="789 Port Road, Mumbai",
        importer_pincode="400001",
        country_of_origin="IN",
    )


@pytest.fixture
def compliance_block_with_empties() -> ComplianceBlock:
    """A compliance block with some empty importer fields (tested in
    collapsed strategy)."""
    return ComplianceBlock(
        manufacturer_name="ACME Manufacturing",
        manufacturer_address="123 Industrial Estate",
        manufacturer_pincode="560001",
        packer_name="ACME Packers",
        packer_address="",
        packer_pincode="560002",
        importer_name=None,
        importer_address=None,
        importer_pincode=None,
        country_of_origin="IN",
    )


def _make_field_spec(canonical: str, header: str) -> dict:
    """Minimal schema field entry per §5A.C."""
    return {
        "canonical_name": canonical,
        "meesho_column_header": header,
        "data_type": "text",
        "primitive": "text_short",
        "marker": "optional",
        "enum_resolver": None,
        "is_advanced": False,
        "help_text": "Test help.",
        "validation_message_ids": [],
    }


@pytest.fixture
def standard_schema() -> dict:
    """A standard 7-key §5A.B envelope with the 9 LM canonical fields
    plus a few product fields."""
    fields = [
        _make_field_spec("name", "Product Name"),
        _make_field_spec("description", "Description"),
        _make_field_spec("manufacturer_name", "Manufacturer Name"),
        _make_field_spec("manufacturer_address", "Manufacturer Address"),
        _make_field_spec("manufacturer_pincode", "Manufacturer Pincode"),
        _make_field_spec("packer_name", "Packer Name"),
        _make_field_spec("packer_address", "Packer Address"),
        _make_field_spec("packer_pincode", "Packer Pincode"),
        _make_field_spec("importer_name", "Importer Name"),
        _make_field_spec("importer_address", "Importer Address"),
        _make_field_spec("importer_pincode", "Importer Pincode"),
    ]
    return {
        "fields": fields,
        "compulsory_count": 0,
        "optional_count": len(fields),
        "total_count": len(fields),
        "wizard_step_count": 3,
        "main_sheet_label": "Test Standard Sheet",
        "compliance_shape": "standard",
    }


@pytest.fixture
def collapsed_schema() -> dict:
    """An Eye-Serum-style 7-key envelope with the 3 collapsed
    compliance canonical fields."""
    fields = [
        _make_field_spec("name", "Product Name"),
        _make_field_spec("manufacturer_details", "Manufacturer Details"),
        _make_field_spec("packer_details", "Packer Details"),
        _make_field_spec("importer_details", "Importer Details"),
    ]
    return {
        "fields": fields,
        "compulsory_count": 0,
        "optional_count": len(fields),
        "total_count": len(fields),
        "wizard_step_count": 3,
        "main_sheet_label": "Eye Serum Sheet",
        "compliance_shape": "collapsed",
    }


@pytest.fixture
def export_snapshot(category_id, product_id):  # noqa: PT004
    """A minimal :class:`ExportSnapshotInternal`-shaped object — uses
    SimpleNamespace so the test doesn't need to wire the catalog
    domain.
    """
    summary = SimpleNamespace(
        product_id=product_id,
        compulsory_filled=0,
        compulsory_total=0,
        optional_filled=2,
        optional_total=10,
        has_validation_errors=False,
        status="ready",
    )
    return SimpleNamespace(
        product_id=product_id,
        category_id=category_id,
        fields={
            "name": "Test Product",
            "description": "A friendly test product.",
        },
        ai_suggestions={},
        image_refs=(),
        validation_summary=summary,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mock helper — patch cross-module service surfaces
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def stub_cross_module(monkeypatch):
    """Patch the bound cross-module imports inside ``export.service``.

    Returns a ``configure(*, snapshot, compliance, schema, enum_payloads,
    images)`` callable.  Tests call ``configure(...)`` to shape the
    stubs before invoking the export service.
    """
    from app.modules.export import service as svc

    state: dict[str, Any] = {
        "snapshot": None,
        "compliance": None,
        "schema": {},
        "enum_payloads": {},
        "enum_raises": None,
        "images": [],
        "ownership_raises": None,
        "calls": [],
    }

    async def fake_assert_ownership(product_id, user_id, db=None):
        state["calls"].append(("assert_ownership", product_id, user_id))
        if state["ownership_raises"] is not None:
            raise state["ownership_raises"]

    async def fake_get_product_for_export(product_id, user_id, db=None):
        state["calls"].append(("get_product_for_export", product_id, user_id))
        return state["snapshot"]

    async def fake_get_compliance_block(user_id, db):
        state["calls"].append(("get_compliance_block", user_id))
        return state["compliance"]

    async def fake_fetch_schema(category_id, db):
        state["calls"].append(("fetch_schema", category_id))
        return state["schema"]

    async def fake_get_field_enum(category_id, field_name, db):
        state["calls"].append(("get_field_enum", category_id, field_name))
        if state["enum_raises"] is not None:
            exc = state["enum_raises"](field_name)
            if exc is not None:
                raise exc
        return state["enum_payloads"].get(field_name, {"enum_entries": [], "total": 0, "truncated": False})

    async def fake_list_images(user_id, product_id, db):
        state["calls"].append(("list_images", user_id, product_id))
        return SimpleNamespace(images=list(state["images"]))

    monkeypatch.setattr(svc.catalog_service, "assert_product_ownership", fake_assert_ownership)
    monkeypatch.setattr(svc.catalog_service, "get_product_for_export", fake_get_product_for_export)
    monkeypatch.setattr(svc.customer_service, "get_compliance_block", fake_get_compliance_block)
    monkeypatch.setattr(svc.category_service, "fetch_schema", fake_fetch_schema)
    monkeypatch.setattr(svc.category_service, "get_field_enum", fake_get_field_enum)
    monkeypatch.setattr(svc.image_service, "list_images", fake_list_images)

    def configure(
        *,
        snapshot=None,
        compliance=None,
        schema=None,
        enum_payloads=None,
        enum_raises=None,
        images=None,
        ownership_raises=None,
    ):
        if snapshot is not None:
            state["snapshot"] = snapshot
        if compliance is not None:
            state["compliance"] = compliance
        if schema is not None:
            state["schema"] = schema
        if enum_payloads is not None:
            state["enum_payloads"] = enum_payloads
        if enum_raises is not None:
            state["enum_raises"] = enum_raises
        if images is not None:
            state["images"] = images
        if ownership_raises is not None:
            state["ownership_raises"] = ownership_raises
        return state

    return configure


@pytest.fixture
def stub_gcs(monkeypatch):
    """Patch the GCS adapter's upload/download/signed-url calls inside
    ``export.service``.

    Returns a state dict recording calls + a sink dict of uploaded
    bytes keyed by path.
    """
    from app.modules.export import service as svc

    state: dict[str, Any] = {
        "uploads": {},
        "downloads": {},  # path → bytes
        "signed_urls": {},  # path → URL
        "upload_calls": [],
        "download_calls": [],
        "signed_calls": [],
    }

    async def fake_upload_bytes(path, data, content_type=None, **kwargs):
        state["uploads"][path] = data
        state["upload_calls"].append((path, content_type))

    async def fake_download_bytes(path, **kwargs):
        state["download_calls"].append(path)
        return state["downloads"].get(path, b"\x00\x01\x02")

    async def fake_generate_signed_url(path, ttl_seconds=3600, method="GET", **kwargs):
        state["signed_calls"].append((path, ttl_seconds, method))
        return state["signed_urls"].get(path, f"https://signed.example/{path}?ttl={ttl_seconds}")

    monkeypatch.setattr(svc.gcs_adapter, "upload_bytes", fake_upload_bytes)
    monkeypatch.setattr(svc.gcs_adapter, "download_bytes", fake_download_bytes)
    monkeypatch.setattr(svc.gcs_adapter, "generate_signed_url", fake_generate_signed_url)

    return state


@pytest.fixture
def stub_valkey_hint(monkeypatch):
    """No-op the Valkey format hint reads/writes inside
    ``export.service`` to avoid touching live Valkey in unit tests.
    """
    from app.modules.export import service as svc

    state: dict[str, str] = {}

    async def fake_set(export_id, fmt):
        state[str(export_id)] = fmt

    async def fake_read(export_id):
        return state.get(str(export_id))

    monkeypatch.setattr(svc, "_set_format_hint", fake_set)
    monkeypatch.setattr(svc, "_read_format_hint", fake_read)
    return state


@pytest.fixture
def stub_celery(monkeypatch):
    """Stub the Celery ``.delay()`` call inside ``initiate_export``.

    Patches ``export_xlsx_task.delay`` to avoid the live Celery broker
    + the pre-existing ``settings.CELERY_BROKER_URL`` config gap
    (settings field absent; env var supplies the value to celery_app
    but the Settings model doesn't expose it).
    """
    from app.modules.export import tasks as export_tasks

    state: dict[str, Any] = {"sent": []}

    class _Task:
        def __init__(self, task_id: str) -> None:
            self.id = task_id

    def fake_delay(export_id, user_id):
        state["sent"].append((export_id, user_id))
        return _Task(f"celery-task-{len(state['sent'])}")

    monkeypatch.setattr(export_tasks.export_xlsx_task, "delay", fake_delay)
    return state


__all__ = [
    "category_id",
    "compliance_block_full",
    "compliance_block_with_empties",
    "export_id",
    "export_snapshot",
    "other_user_id",
    "product_id",
    "standard_schema",
    "collapsed_schema",
    "stub_celery",
    "stub_cross_module",
    "stub_gcs",
    "stub_valkey_hint",
    "user_id",
]


# Avoid "imported but unused" complaints — the fixtures above are
# imported by pytest discovery, not by tests directly.
_ = datetime
_ = timezone
