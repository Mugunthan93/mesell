"""§14.K integration test 2 — export blocked by failed precheck.

When the image precheck status is ``failed_precheck`` the product's
status cascades to non-``ready`` per §10 catalog rules.  The export
POST then returns 422 ``export.product.not_ready``.

We drive this through the service-layer ``initiate_export`` (the
catalog snapshot's validation_summary.status reflects the cascade).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.modules.export import service as export_service
from app.modules.export.exceptions import ProductNotReadyForExportError
from app.modules.export.schemas import ExportRequest


@pytest.mark.asyncio
async def test_failed_precheck_blocks_export(monkeypatch):
    """Product status cascaded to 'draft' (from a failed image precheck)
    → 422 :class:`ProductNotReadyForExportError`.
    """
    from app.modules.export import service as svc

    user_id = uuid4()
    product_id = uuid4()
    category_id = uuid4()

    # Snapshot reflects the §10 cascade: status='draft' even though the
    # seller may have set all fields — the failed precheck on the front
    # image flipped the product back to draft.
    cascaded_snapshot = SimpleNamespace(
        product_id=product_id,
        category_id=category_id,
        fields={"name": "Test"},
        ai_suggestions={},
        image_refs=(),
        validation_summary=SimpleNamespace(
            product_id=product_id,
            compulsory_filled=5,
            compulsory_total=5,
            optional_filled=3,
            optional_total=10,
            has_validation_errors=False,
            status="draft",  # The cascade.
        ),
    )

    async def fake_assert_ownership(pid, uid, db=None):
        return None

    async def fake_get_product_for_export(pid, uid, db=None):
        return cascaded_snapshot

    monkeypatch.setattr(svc.catalog_service, "assert_product_ownership", fake_assert_ownership)
    monkeypatch.setattr(svc.catalog_service, "get_product_for_export", fake_get_product_for_export)

    db_mock = AsyncMock()
    with pytest.raises(ProductNotReadyForExportError) as exc_info:
        await export_service.initiate_export(
            user_id=user_id,
            product_id=product_id,
            request=ExportRequest(format="xlsx_with_images"),
            db=db_mock,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.validation_message_id == "export.product.not_ready"
