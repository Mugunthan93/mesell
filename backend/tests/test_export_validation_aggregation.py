"""Unit tests for the export pre-enqueue validation aggregation.

``export.service.initiate_export`` was reworked from fail-fast to collect-all:
all router-surface validation checks are gathered into a single
:class:`ExportValidationFailedError` carrying ``failed_checks[]`` (per
export-validation-aggregation, 2026-06-18).  The ownership gate stays
fail-fast (404) and is NOT aggregated.

All external collaborators (``catalog_service``, ``image_service``,
``export_repo``, the lazily-imported ``export_xlsx_task``) are mocked at the
``app.modules.export.service`` module level via ``monkeypatch.setattr``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.export import service as export_service
from app.modules.export.exceptions import ExportValidationFailedError
from app.modules.export.schemas import ExportInitiatedResponse

pytestmark = pytest.mark.unit


# ── Helpers ──────────────────────────────────────────────────────────────────
def _snapshot(status: str) -> SimpleNamespace:
    """Minimal export snapshot — only ``validation_summary.status`` is read."""
    return SimpleNamespace(validation_summary=SimpleNamespace(status=status))


def _images_payload(images: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(images=images)


def _ready_front_image() -> SimpleNamespace:
    return SimpleNamespace(idx=1, status="ready")


def _request(fmt: str) -> SimpleNamespace:
    return SimpleNamespace(format=fmt)


def _patch_catalog(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ownership: AsyncMock | None = None,
    snapshot_status: str = "ready",
) -> SimpleNamespace:
    """Patch ``catalog_service.assert_product_ownership`` +
    ``get_product_for_export`` on the service module."""
    fake = SimpleNamespace(
        assert_product_ownership=ownership or AsyncMock(return_value=None),
        get_product_for_export=AsyncMock(return_value=_snapshot(snapshot_status)),
    )
    monkeypatch.setattr(export_service, "catalog_service", fake)
    return fake


def _patch_images(
    monkeypatch: pytest.MonkeyPatch, images: list[SimpleNamespace]
) -> SimpleNamespace:
    fake = SimpleNamespace(
        list_images=AsyncMock(return_value=_images_payload(images))
    )
    monkeypatch.setattr(export_service, "image_service", fake)
    return fake


# ── 1. quality_status only ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_quality_status_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """status='draft' + xlsx_only → only the quality_status check fails."""
    _patch_catalog(monkeypatch, snapshot_status="draft")
    # image_service must not even be consulted for xlsx_only — patch it so an
    # accidental call would blow up loudly.
    monkeypatch.setattr(
        export_service,
        "image_service",
        SimpleNamespace(list_images=AsyncMock(side_effect=AssertionError("called"))),
    )

    with pytest.raises(ExportValidationFailedError) as ei:
        await export_service.initiate_export(
            user_id=uuid4(),
            product_id=uuid4(),
            request=_request("xlsx_only"),
            db=AsyncMock(),
        )

    assert ei.value.failed_checks == [
        {"check_id": "quality_status", "message_key": "export.check.quality_status"}
    ]


# ── 2. front_image_missing only ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_front_image_missing_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """status='ready' + xlsx_with_images + no ready idx==1 image →
    only the front_image_missing check fails."""
    _patch_catalog(monkeypatch, snapshot_status="ready")
    # Wrong-slot + wrong-status images — neither satisfies idx==1 AND ready.
    _patch_images(
        monkeypatch,
        [
            SimpleNamespace(idx=2, status="ready"),
            SimpleNamespace(idx=1, status="processing"),
        ],
    )

    with pytest.raises(ExportValidationFailedError) as ei:
        await export_service.initiate_export(
            user_id=uuid4(),
            product_id=uuid4(),
            request=_request("xlsx_with_images"),
            db=AsyncMock(),
        )

    assert ei.value.failed_checks == [
        {
            "check_id": "front_image_missing",
            "message_key": "export.check.front_image_missing",
        }
    ]


# ── 3. multiple checks aggregate ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_multiple_checks_aggregate(monkeypatch: pytest.MonkeyPatch) -> None:
    """status='draft' + xlsx_with_images + no front image →
    both checks fail, in order [quality_status, front_image_missing]."""
    _patch_catalog(monkeypatch, snapshot_status="draft")
    _patch_images(monkeypatch, [])  # no images at all

    with pytest.raises(ExportValidationFailedError) as ei:
        await export_service.initiate_export(
            user_id=uuid4(),
            product_id=uuid4(),
            request=_request("xlsx_with_images"),
            db=AsyncMock(),
        )

    checks = ei.value.failed_checks
    assert len(checks) == 2
    assert checks == [
        {"check_id": "quality_status", "message_key": "export.check.quality_status"},
        {
            "check_id": "front_image_missing",
            "message_key": "export.check.front_image_missing",
        },
    ]


# ── 4. no failures → proceeds to enqueue ────────────────────────────────────────
@pytest.mark.asyncio
async def test_no_failures_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """status='ready' + a ready front image → no exception; insert + delay
    called; ExportInitiatedResponse(status='pending') returned."""
    _patch_catalog(monkeypatch, snapshot_status="ready")
    _patch_images(monkeypatch, [_ready_front_image()])

    export_id = uuid4()
    initiated_at = datetime.now(timezone.utc)
    insert_mock = AsyncMock(
        return_value=SimpleNamespace(id=export_id, initiated_at=initiated_at)
    )
    monkeypatch.setattr(
        export_service,
        "export_repo",
        SimpleNamespace(insert=insert_mock),
    )

    # Best-effort Valkey format hint — no-op it.
    monkeypatch.setattr(export_service, "_set_format_hint", AsyncMock(return_value=None))

    # Patch the lazily-imported Celery task (`from app.modules.export.tasks
    # import export_xlsx_task` inside the function body).
    delay_mock = MagicMock(return_value=SimpleNamespace(id="task-123"))
    import app.modules.export.tasks as export_tasks

    monkeypatch.setattr(
        export_tasks,
        "export_xlsx_task",
        SimpleNamespace(delay=delay_mock),
    )

    result = await export_service.initiate_export(
        user_id=uuid4(),
        product_id=uuid4(),
        request=_request("xlsx_with_images"),
        db=AsyncMock(),
    )

    insert_mock.assert_awaited_once()
    delay_mock.assert_called_once()
    assert isinstance(result, ExportInitiatedResponse)
    assert result.status == "pending"
    assert result.export_id == export_id
    assert result.enqueued_task_id == "task-123"


# ── 5. ownership 404 propagates unwrapped ───────────────────────────────────────
@pytest.mark.asyncio
async def test_ownership_404_not_aggregated(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fail-fast ownership gate raises ProductNotFoundError, which
    propagates UNCHANGED (never wrapped into ExportValidationFailedError),
    and get_product_for_export is never called."""
    get_snapshot_mock = AsyncMock()
    fake_catalog = SimpleNamespace(
        assert_product_ownership=AsyncMock(side_effect=ProductNotFoundError()),
        get_product_for_export=get_snapshot_mock,
    )
    monkeypatch.setattr(export_service, "catalog_service", fake_catalog)

    with pytest.raises(ProductNotFoundError):
        await export_service.initiate_export(
            user_id=uuid4(),
            product_id=uuid4(),
            request=_request("xlsx_with_images"),
            db=AsyncMock(),
        )

    get_snapshot_mock.assert_not_awaited()
