"""``export`` Celery tasks — 9-step Export Adapter pipeline per §14.E.

Vendored from the monolith ``app.modules.export.tasks``.  The ONLY import-line
change is the intra-tree rewrite of the lazy service import
(``from app.modules.export.service import _run_export_pipeline`` →
``from app.service import _run_export_pipeline``).  ``app.shared.database`` and
``app.shared.models.audit_event`` are at the same flat paths.  Every executable
line is byte-for-byte from the monolith task module.

Task name + retry semantics per §14.E + §14-EXPORT-D8:
    name="export.xlsx"
    max_retries=1
    retry_backoff=True
    bind=True

CROSS-SCHEMA AUDIT WRITE (spec §3.A)
------------------------------------
The terminal ``export.completed`` / ``export.failed`` audit rows are written
directly to ``public.audit_events`` via the vendored ``AuditEvent`` model
(bound to ``public`` — see ``app.shared.models.audit_event``).  svc-export's
own ``exports`` table lives in the ``export`` schema, so this is a cross-schema
INSERT.  Drop-on-failure with a warning so audit observability never blocks the
export task (F-15-1; same pattern as §6A.D cost_tracker / §7 verify_otp /
§11.E precheck task — workers have no request-close hook for audit_mw).
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
    """§14.E — Celery task wrapper for the 9-step Export Adapter pipeline.

    Synchronous Celery task; the async orchestrator runs via
    :func:`asyncio.run`.  Returns a small dict reflecting the post-run
    state for callers reading from the Celery result backend (Valkey DB 2).
    """
    # Coerce string-form UUIDs (Celery JSON serialiser strips UUID type).
    export_uuid = export_id if isinstance(export_id, UUID) else UUID(str(export_id))
    user_uuid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))

    # Lazy import to avoid loading the service module at task-discovery
    # time (heavy chain: openpyxl, sqlalchemy, cross-module).
    from app.service import _run_export_pipeline

    try:
        asyncio.run(_run_export_pipeline(export_uuid, user_uuid))
    except Exception as exc:  # noqa: BLE001 — defensive Celery retry
        logger.warning(
            "export.xlsx retry (export=%s): unexpected failure: %r",
            export_uuid,
            exc,
        )
        # Terminal FAILURE — only on the final attempt (retries exhausted).
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
    """Direct ORM write to ``public.audit_events`` for ``export.completed`` /
    ``export.failed`` (F-15-1).

    Cross-schema INSERT — svc-export's own table is in the ``export`` schema;
    the ``AuditEvent`` model is bound to ``public``.  Drops on failure with a
    warning — audit observability MUST NOT block (or fail) the export task.
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
