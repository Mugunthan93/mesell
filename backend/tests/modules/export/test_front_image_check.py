"""§14.K unit test 3 — front image check.

Router-surface ``initiate_export`` was reworked from fail-fast to
collect-all (per export-validation-aggregation, 2026-06-18): a
``xlsx_with_images`` export on a product with no ``idx=1, status='ready'``
image now contributes a ``front_image_missing`` entry to the aggregated
:class:`ExportValidationFailedError` (422 + ``export.validation.failed``)
rather than raising the standalone :class:`FrontImageMissingError` (which
the worker pipeline ``_run_export_pipeline`` still raises).

The snapshot here is ``status='ready'`` so ``front_image_missing`` is the
SOLE failure in each aggregate below.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit

from app.modules.export import service as export_service
from app.modules.export.exceptions import ExportValidationFailedError
from app.modules.export.schemas import ExportRequest

_FRONT_IMAGE_CHECK = {
    "check_id": "front_image_missing",
    "message_key": "export.check.front_image_missing",
}


@pytest.mark.asyncio
async def test_no_front_image_raises_missing(
    user_id,
    product_id,
    export_snapshot,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
):
    """Empty image list → aggregated ``front_image_missing`` check."""
    stub_cross_module(snapshot=export_snapshot, images=[])

    db_mock = AsyncMock()
    with pytest.raises(ExportValidationFailedError) as exc_info:
        await export_service.initiate_export(
            user_id=user_id,
            product_id=product_id,
            request=ExportRequest(format="xlsx_with_images"),
            db=db_mock,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.validation_message_id == "export.validation.failed"
    assert exc_info.value.failed_checks == [_FRONT_IMAGE_CHECK]


@pytest.mark.asyncio
async def test_only_slot_2_image_raises_missing(
    user_id,
    product_id,
    export_snapshot,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
):
    """A product with an image at idx=2 but NONE at idx=1 → aggregated
    ``front_image_missing`` check."""
    images = [SimpleNamespace(idx=2, status="ready")]
    stub_cross_module(snapshot=export_snapshot, images=images)

    db_mock = AsyncMock()
    with pytest.raises(ExportValidationFailedError) as exc_info:
        await export_service.initiate_export(
            user_id=user_id,
            product_id=product_id,
            request=ExportRequest(format="xlsx_with_images"),
            db=db_mock,
        )
    assert exc_info.value.failed_checks == [_FRONT_IMAGE_CHECK]


@pytest.mark.asyncio
async def test_slot_1_pending_image_raises_missing(
    user_id,
    product_id,
    export_snapshot,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
):
    """A front image at idx=1 but ``status='pending'`` → aggregated
    ``front_image_missing`` check (precheck must have completed)."""
    images = [SimpleNamespace(idx=1, status="pending")]
    stub_cross_module(snapshot=export_snapshot, images=images)

    db_mock = AsyncMock()
    with pytest.raises(ExportValidationFailedError) as exc_info:
        await export_service.initiate_export(
            user_id=user_id,
            product_id=product_id,
            request=ExportRequest(format="xlsx_with_images"),
            db=db_mock,
        )
    assert exc_info.value.failed_checks == [_FRONT_IMAGE_CHECK]


@pytest.mark.asyncio
async def test_xlsx_only_format_skips_front_image_check(
    user_id,
    product_id,
    export_snapshot,
    stub_cross_module,
    stub_valkey_hint,
    stub_celery,
    monkeypatch,
):
    """``format='xlsx_only'`` does NOT trigger the image gate — the
    image fixture is empty but no exception is raised."""
    from app.modules.export import service as svc
    from app.modules.export.domain import Export
    from datetime import datetime, timezone
    from uuid import uuid4

    stub_cross_module(snapshot=export_snapshot, images=[])

    fake_export = Export(
        id=uuid4(),
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

    async def fake_insert(*, db, user_id, product_id, format, initiated_at):
        return fake_export

    monkeypatch.setattr(svc.export_repo, "insert", fake_insert)

    db_mock = AsyncMock()
    response = await export_service.initiate_export(
        user_id=user_id,
        product_id=product_id,
        request=ExportRequest(format="xlsx_only"),
        db=db_mock,
    )
    assert response.status == "pending"

    # Verify list_images was NOT called for xlsx_only.
    state = stub_cross_module()
    image_calls = [c for c in state["calls"] if c[0] == "list_images"]
    assert image_calls == []
