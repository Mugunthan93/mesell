"""§14.K unit test 1 — ownership gate.

POST /products/{other_user_product}/export-xlsx → 404 via the
``catalog.assert_product_ownership`` cross-module surface.

We exercise the service-layer ``initiate_export`` path (the routing
layer is owned by api-routes-builder; here we assert the service
correctly propagates the cross-module ``ProductNotFoundError``).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit

from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.export import service as export_service
from app.modules.export.schemas import ExportRequest


@pytest.mark.asyncio
async def test_ownership_gate_propagates_product_not_found(
    user_id,
    product_id,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
):
    """``catalog.assert_product_ownership`` raising ``ProductNotFoundError``
    must propagate (the §4.F error handler maps it to 404)."""
    stub_cross_module(ownership_raises=ProductNotFoundError())

    db_mock = AsyncMock()
    with pytest.raises(ProductNotFoundError):
        await export_service.initiate_export(
            user_id=user_id,
            product_id=product_id,
            request=ExportRequest(format="xlsx_with_images"),
            db=db_mock,
        )


@pytest.mark.asyncio
async def test_ownership_gate_calls_assert_product_ownership_first(
    user_id,
    product_id,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
):
    """The ownership gate MUST be called before ``get_product_for_export``
    + ``list_images`` — the cross-module ordering matters because
    ``get_product_for_export`` itself re-asserts ownership but the
    early gate gives a cleaner 404 envelope.
    """
    stub_cross_module(ownership_raises=ProductNotFoundError())
    db_mock = AsyncMock()
    with pytest.raises(ProductNotFoundError):
        await export_service.initiate_export(
            user_id=user_id,
            product_id=product_id,
            request=ExportRequest(format="xlsx_only"),
            db=db_mock,
        )
    # Verify call ordering: only the ownership check should have fired.
    calls_state = stub_cross_module()
    call_kinds = [c[0] for c in calls_state["calls"]]
    assert call_kinds == ["assert_ownership"]
