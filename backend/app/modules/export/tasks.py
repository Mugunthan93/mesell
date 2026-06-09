"""``export`` Celery tasks — 9-step Export Adapter pipeline per §14.E.

Per BACKEND_ARCHITECTURE.md §14.E (LOCKED 2026-06-05).

Task name + retry semantics per §14.E + §14-EXPORT-D8:
    name="export.xlsx"
    max_retries=1
    retry_backoff=True
    bind=True

The pipeline runs through :func:`export.service._run_export_pipeline`
which orchestrates the 9 steps + persists ready/failed status via
:mod:`.repository`.

Direct audit writes for ``export.completed`` / ``export.failed`` are
emitted from this worker task at its terminal SUCCESS / FAILURE points
(F-15-1, same documented exception pattern as §6A.D ``cost_tracker``,
§7.B ``verify_otp``, §11.E precheck task — workers have no request-close
hook for audit_mw).  ``export.completed`` fires after the orchestrator
returns; ``export.failed`` fires once on the final (retries-exhausted)
attempt.  Both drop-on-failure with a warning so audit observability
never blocks the export task.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from app.shared.database import AsyncSessionLocal
from app.shared.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


@shared_task(
    name="export.xlsx",
    bind=True,
    max_retries=1,
    retry_backoff=True,
)
def export_xlsx_task(
    self,  # noqa: ANN001 — Celery task bound self
    export_id: str | UUID,
    user_id: str | UUID,
) -> dict:
    """§14.E — Celery task wrapper for the 9-step Export Adapter
    pipeline.

    Synchronous Celery task; the async orchestrator runs via
    :func:`asyncio.run`.  Returns a small dict reflecting the post-run
    state for callers reading from the Celery result backend (Valkey
    DB 2).

    Args:
        export_id: ``exports.id`` UUID (or its string form).
        user_id:   Owning user's UUID (or its string form).

    Retry policy:

    * ``max_retries=1`` — single retry on transient/unexpected failure.
    * ``retry_backoff=True`` — exponential backoff between attempts.
    * Typed pipeline exceptions (``RoundTripValidationError``,
      ``ExportEnumValidationError``, ``ComplianceStrategyError``,
      ``XlsxBuildError``, ``ProductNotReadyForExportError``,
      ``FrontImageMissingError``) are caught INSIDE
      ``_run_export_pipeline`` and persist as ``status='failed'`` — they
      do NOT propagate here.  Only adapter/transport failures from the
      orchestrator's commit path (rare) would surface and trigger the
      retry.
    """
    # Coerce string-form UUIDs (Celery JSON serialiser strips UUID type).
    export_uuid = export_id if isinstance(export_id, UUID) else UUID(str(export_id))
    user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))

    # Lazy import to avoid loading the service module at task-discovery
    # time (heavy chain: openpyxl, sqlalchemy, cross-module).
    from app.modules.export.service import _run_export_pipeline

    try:
        asyncio.run(_run_export_pipeline(export_uuid, user_uuid))
    except Exception as exc:  # noqa: BLE001 — defensive Celery retry
        logger.warning(
            "export.xlsx retry (export=%s): unexpected failure: %r",
            export_uuid,
            exc,
        )
        # Terminal FAILURE — only on the final attempt (retries exhausted).
        # Earlier attempts re-raise via self.retry without writing the
        # terminal audit row, so a transient failure that later succeeds
        # records only ``export.completed``.
        if self.request.retries >= self.max_retries:
            asyncio.run(
                _emit_export_terminal_audit(
                    user_id=user_uuid,
                    export_id=export_uuid,
                    event_type="export.failed",
                    error=repr(exc),
                )
            )
        raise self.retry(exc=exc) from exc

    # Terminal SUCCESS.
    asyncio.run(
        _emit_export_terminal_audit(
            user_id=user_uuid,
            export_id=export_uuid,
            event_type="export.completed",
            error=None,
        )
    )

    return {
        "export_id": str(export_uuid),
        "user_id": str(user_uuid),
        "status": "completed",
    }


async def _emit_export_terminal_audit(
    *,
    user_id: UUID,
    export_id: UUID,
    event_type: str,
    error: str | None,
) -> None:
    """Direct ORM write to ``audit_events`` for ``export.completed`` /
    ``export.failed`` (F-15-1).

    Same documented-exception pattern as §6A.D ``cost_tracker._write_audit_row``,
    §7 ``verify_otp``, and §11.E ``image.tasks._emit_precheck_completed_audit``
    — the worker has no request-close hook, so the standard ``audit_mw``
    post-commit path cannot fire.

    Drops on failure with a warning log — audit observability MUST NOT block
    (or fail) the export task per the §1.E lock.
    """
    metadata: dict[str, str] = {
        "export_id": str(export_id),
        "emitted_at": datetime.now(timezone.utc).isoformat(),
    }
    if error is not None:
        metadata["error"] = error
    try:
        async with AsyncSessionLocal() as session:
            row = AuditEvent(
                user_id=user_id,
                event_type=event_type,
                entity_type="export",
                entity_id=export_id,
                diff_jsonb=None,
                metadata_jsonb=metadata,
            )
            session.add(row)
            await session.commit()
    except (SQLAlchemyError, Exception) as exc:  # noqa: BLE001 — informational
        logger.warning(
            "%s audit_events write failed (user=%s export=%s): %r",
            event_type,
            user_id,
            export_id,
            exc,
        )


__all__ = [
    "export_xlsx_task",
    "_emit_export_terminal_audit",
]
