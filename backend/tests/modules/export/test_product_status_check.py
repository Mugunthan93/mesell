"""§14.K unit test 2 — product status check.

Product with ``status='draft'`` must raise
:class:`ProductNotReadyForExportError` (422 +
``export.product.not_ready``).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit

from app.modules.export import service as export_service
from app.modules.export.exceptions import ProductNotReadyForExportError
from app.modules.export.schemas import ExportRequest


@pytest.mark.asyncio
async def test_product_status_draft_raises_not_ready(
    user_id,
    product_id,
    category_id,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
):
    """``snapshot.validation_summary.status == 'draft'`` → 422."""
    draft_snapshot = SimpleNamespace(
        product_id=product_id,
        category_id=category_id,
        fields={},
        ai_suggestions={},
        image_refs=(),
        validation_summary=SimpleNamespace(
            product_id=product_id,
            compulsory_filled=0,
            compulsory_total=5,
            optional_filled=0,
            optional_total=10,
            has_validation_errors=False,
            status="draft",
        ),
    )
    stub_cross_module(snapshot=draft_snapshot)

    db_mock = AsyncMock()
    with pytest.raises(ProductNotReadyForExportError) as exc_info:
        await export_service.initiate_export(
            user_id=user_id,
            product_id=product_id,
            request=ExportRequest(format="xlsx_with_images"),
            db=db_mock,
        )

    # Verify exception envelope conforms to §14.H locks.
    assert exc_info.value.status_code == 422
    assert exc_info.value.validation_message_id == "export.product.not_ready"


@pytest.mark.asyncio
async def test_product_status_ready_does_NOT_raise(
    user_id,
    product_id,
    export_snapshot,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
    monkeypatch,
):
    """``snapshot.validation_summary.status == 'ready'`` proceeds past
    step 2 to the image gate (which we stub with a single ready front
    image so the test path completes through to the insert).
    """
    from app.modules.export import service as svc

    # Front image present.
    image_obj = SimpleNamespace(idx=1, status="ready")
    stub_cross_module(snapshot=export_snapshot, images=[image_obj])

    # Stub the repository.insert + composition through to the response.
    from app.modules.export.domain import Export
    from datetime import datetime, timezone
    from uuid import uuid4
    fake_export = Export(
        id=uuid4(),
        user_id=user_id,
        product_id=product_id,
        format="xlsx_with_images",
        status="pending",
        xlsx_gcs_path=None,
        zip_gcs_path=None,
        error_message=None,
        error_code=None,
        round_trip_validated=None,
        initiated_at=datetime.now(timezone.utc),
        completed_at=None,
    )

    async def fake_insert(*, db, user_id, product_id, format, initiated_at):
        return fake_export

    monkeypatch.setattr(svc.export_repo, "insert", fake_insert)

    db_mock = AsyncMock()
    response = await export_service.initiate_export(
        user_id=user_id,
        product_id=product_id,
        request=ExportRequest(format="xlsx_with_images"),
        db=db_mock,
    )
    assert response.status == "pending"
    assert response.export_id == fake_export.id
