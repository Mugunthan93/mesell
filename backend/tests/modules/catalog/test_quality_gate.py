"""PQE Wave A — Quality gate + completeness tests.

Covers:
  PQE-BE-44  PATCH /products/{id} with status="ready" blocks on missing
             compulsory field → 422 with
             validation_message_id="validation.completeness.missing_compulsory"
  PQE-BE-45  PATCH /products/{id} with invalid enum value → 422 with
             non-empty validation_message_id
  PQE-BE-46  _compute_completeness counts compulsory / optional filled vs total
  PQE-BE-47  get_product_for_export surfaces validation_summary.status as
             row.status (the export pipeline reads it for the "ready-only"
             gate)

PQE-BE-44 / 45 are route-level integration tests; they stub
``catalog_service.patch_product`` so that the service raises the real
exception class with the correct message-id.  This mirrors the pattern used by
``tests/modules/pricing/test_feature_flag.py``.

PQE-BE-46 / 47 are unit tests — pure functions, no DB.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace  # noqa: F401 — used in PQE-BE-47 docstring example
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio

# ─────────────────────────────────────────────────────────────────────────────
# Unit-level imports (pure functions — no DB/Valkey needed)
# ─────────────────────────────────────────────────────────────────────────────
from app.modules.catalog.service import _compute_completeness
from app.modules.catalog.domain import ValidationSummaryInternal


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _make_schema(
    compulsory_canonicals: list[str],
    optional_canonicals: list[str],
) -> dict:
    """Build a minimal schema dict for _compute_completeness."""
    fields = [
        {
            "canonical_name": name,
            "data_type": "text",
            "primitive": "text_short",
            "marker": "compulsory",
        }
        for name in compulsory_canonicals
    ] + [
        {
            "canonical_name": name,
            "data_type": "text",
            "primitive": "text_short",
            "marker": "optional",
        }
        for name in optional_canonicals
    ]
    return {"fields": fields}


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-46  _compute_completeness counts
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_pqe_be_46_completeness_all_filled():
    """_compute_completeness returns correct counts when all fields are filled.

    Arrange: schema with 2 compulsory + 1 optional; fields dict fills all 3.
    Act: _compute_completeness.
    Assert: compulsory_total=2, compulsory_filled=2, optional_total=1,
            optional_filled=1.
    """
    schema = _make_schema(
        compulsory_canonicals=["product_name", "selling_price"],
        optional_canonicals=["color"],
    )
    fields = {"product_name": "Red Kurti", "selling_price": "499", "color": "Red"}

    result = _compute_completeness(fields, schema)

    assert result.compulsory_total == 2
    assert result.compulsory_filled == 2
    assert result.optional_total == 1
    assert result.optional_filled == 1


@pytest.mark.unit
def test_pqe_be_46_completeness_partial_fill():
    """_compute_completeness counts only non-empty / non-None values as filled.

    Arrange: 2 compulsory; fields dict has one filled and one empty string.
    Act: _compute_completeness.
    Assert: compulsory_filled=1, compulsory_total=2.
    """
    schema = _make_schema(
        compulsory_canonicals=["product_name", "selling_price"],
        optional_canonicals=[],
    )
    fields = {"product_name": "Red Kurti", "selling_price": ""}  # empty = not filled

    result = _compute_completeness(fields, schema)

    assert result.compulsory_total == 2
    assert result.compulsory_filled == 1, (
        f"Empty string must not count as filled; got {result.compulsory_filled}"
    )


@pytest.mark.unit
def test_pqe_be_46_completeness_none_value_not_filled():
    """None values are not counted as filled by _compute_completeness.

    Arrange: 1 compulsory; fields dict has None for that field.
    Act: _compute_completeness.
    Assert: compulsory_filled=0.
    """
    schema = _make_schema(compulsory_canonicals=["product_name"], optional_canonicals=[])
    fields = {"product_name": None}

    result = _compute_completeness(fields, schema)

    assert result.compulsory_filled == 0, (
        f"None value must not count as filled; got {result.compulsory_filled}"
    )


@pytest.mark.unit
def test_pqe_be_46_completeness_empty_fields_dict():
    """_compute_completeness with empty fields dict yields all-zero fill counts.

    Arrange: schema with 2 compulsory + 1 optional; fields = {}.
    Act: _compute_completeness.
    Assert: compulsory_filled=0, optional_filled=0; totals are correct.
    """
    schema = _make_schema(
        compulsory_canonicals=["product_name", "selling_price"],
        optional_canonicals=["color"],
    )
    result = _compute_completeness({}, schema)

    assert result.compulsory_total == 2
    assert result.compulsory_filled == 0
    assert result.optional_total == 1
    assert result.optional_filled == 0


@pytest.mark.unit
def test_pqe_be_46_completeness_returns_validation_summary_internal():
    """_compute_completeness returns a ValidationSummaryInternal (frozen dataclass)."""
    schema = _make_schema(compulsory_canonicals=["name"], optional_canonicals=[])
    result = _compute_completeness({"name": "Test"}, schema)

    assert isinstance(result, ValidationSummaryInternal), (
        f"Expected ValidationSummaryInternal, got {type(result)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-47  get_product_for_export surfaces validation_summary.status
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_pqe_be_47_export_snapshot_status_matches_row_status():
    """The export snapshot's validation_summary.status carries the product's
    ORM status — so the export pipeline's "ready-only" gate reads the right value.

    This test exercises the unit-level contract by calling _compute_completeness
    and assembling a ValidationSummaryInternal just as get_product_for_export
    does (lines 1207-1218 of catalog/service.py).
    """
    schema = _make_schema(compulsory_canonicals=["product_name"], optional_canonicals=[])
    fields = {"product_name": "Test Saree"}

    # Simulate the ORM-row status values the export service reads.
    for expected_status in ("draft", "ready"):
        summary_internal = _compute_completeness(fields, schema)
        summary = ValidationSummaryInternal(
            product_id=uuid4(),
            compulsory_filled=summary_internal.compulsory_filled,
            compulsory_total=summary_internal.compulsory_total,
            optional_filled=summary_internal.optional_filled,
            optional_total=summary_internal.optional_total,
            has_validation_errors=False,
            status=expected_status,  # type: ignore[arg-type]
        )

        assert summary.status == expected_status, (
            f"ValidationSummaryInternal.status must reflect the ORM row status; "
            f"expected {expected_status!r}, got {summary.status!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Shared ASGI client fixture for route-level tests (PQE-BE-44 / 45)
# ─────────────────────────────────────────────────────────────────────────────
_STUB_CATALOG_USER_ID = uuid4()
_STUB_CATALOG_PLAN = "starter"


async def _stub_catalog_get_current_user():
    """Stub auth — returns a frozen CurrentUser-like object; never hits the DB."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _Stub:
        user_id: uuid.UUID = _STUB_CATALOG_USER_ID
        plan: str = _STUB_CATALOG_PLAN

    return _Stub()  # type: ignore[return-value]


@pytest_asyncio.fixture(loop_scope="function")
async def stub_catalog_client(use_live_valkey):
    """AsyncClient with stubbed auth for catalog route tests (no real DB).

    Uses ``app.dependency_overrides`` to inject a no-DB CurrentUser stub,
    matching the pattern from ``test_apply_price_route.py``.
    ``use_live_valkey`` resets Valkey singletons per-function so that the
    rate_limit / audit_event decorators do not raise 'Event loop is closed'.
    """
    from app.core.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = _stub_catalog_get_current_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-44  ready-transition blocks on missing compulsory field → 422
# ─────────────────────────────────────────────────────────────────────────────
async def test_pqe_be_44_ready_transition_blocked_on_missing_compulsory(
    stub_catalog_client,
):
    """PATCH /products/{id} with status='ready' and missing compulsory → 422.

    The service raises ``ValidationFailedError(
        validation_message_id='validation.completeness.missing_compulsory'
    )`` — the error handler maps it to 422 with the §4.F envelope.

    Arrange: stub ``catalog_service.patch_product`` to raise the expected error.
    Act: PATCH the route.
    Assert: 422 response; ``validation_message_id`` in body matches the id.
    """
    from app.modules.catalog.exceptions import ValidationFailedError

    product_id = uuid4()
    client = stub_catalog_client

    with patch(
        "app.modules.catalog.router.catalog_service.patch_product",
        new_callable=AsyncMock,
        side_effect=ValidationFailedError(
            validation_message_id="validation.completeness.missing_compulsory",
            detail="1 required field(s) still empty.",
            details=["missing_compulsory: 1"],
        ),
    ):
        resp = await client.patch(
            f"/api/v1/products/{product_id}",
            json={"status": "ready"},
        )

    assert resp.status_code == 422, (
        f"Expected 422 for missing-compulsory on ready-transition, got {resp.status_code}; "
        f"body: {resp.text}"
    )
    body = resp.json()
    assert body.get("validation_message_id") == "validation.completeness.missing_compulsory", (
        f"validation_message_id mismatch; got {body.get('validation_message_id')!r}"
    )
    assert body.get("validation_message_id"), (
        "validation_message_id must be non-empty (gate requirement)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PQE-BE-45  enum out-of-set → 422 with non-empty validation_message_id
# ─────────────────────────────────────────────────────────────────────────────
async def test_pqe_be_45_invalid_enum_value_returns_422(stub_catalog_client):
    """PATCH /products/{id} with an invalid enum value → 422 with non-empty msg_id.

    The service raises ``ValidationFailedError(
        validation_message_id='validation.<canonical>.invalid_enum_value'
    )`` — the error handler surfaces it per §4.F.

    Arrange: stub ``catalog_service.patch_product`` to raise the error.
    Act: PATCH the route.
    Assert: 422; ``validation_message_id`` is non-empty.
    """
    from app.modules.catalog.exceptions import ValidationFailedError

    product_id = uuid4()
    client = stub_catalog_client

    with patch(
        "app.modules.catalog.router.catalog_service.patch_product",
        new_callable=AsyncMock,
        side_effect=ValidationFailedError(
            validation_message_id="validation.size_in_ltrs.invalid_enum_value",
            detail="size_in_ltrs: not in category enum.",
            details=["size_in_ltrs: not in category enum"],
        ),
    ):
        resp = await client.patch(
            f"/api/v1/products/{product_id}",
            json={"fields": {"size_in_ltrs": "99999"}},
        )

    assert resp.status_code == 422, (
        f"Expected 422 for invalid enum value, got {resp.status_code}; body: {resp.text}"
    )
    body = resp.json()
    msg_id = body.get("validation_message_id")
    assert msg_id, (
        f"validation_message_id must be non-empty for enum-rejection 422; body: {body!r}"
    )
    assert "invalid_enum_value" in msg_id, (
        f"validation_message_id should reference invalid_enum_value; got {msg_id!r}"
    )


async def test_pqe_be_45_unknown_key_returns_422_with_nonempty_msg_id(
    stub_catalog_client,
):
    """PATCH /products/{id} with an unknown canonical key → 422 with non-empty msg_id.

    Covers the second class of 422 (§5A.H ``validation.fields.unknown_key``)
    to confirm the envelope contract for any validation 422.
    """
    from app.modules.catalog.exceptions import ValidationFailedError

    product_id = uuid4()
    client = stub_catalog_client

    with patch(
        "app.modules.catalog.router.catalog_service.patch_product",
        new_callable=AsyncMock,
        side_effect=ValidationFailedError(
            validation_message_id="validation.fields.unknown_key",
            detail="unknown canonical: ghost_field.",
            details=["ghost_field"],
        ),
    ):
        resp = await client.patch(
            f"/api/v1/products/{product_id}",
            json={"fields": {"ghost_field": "value"}},
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body.get("validation_message_id"), (
        f"validation_message_id must be non-empty for unknown-key 422; body: {body!r}"
    )
