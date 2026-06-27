## F-15-1 export worker terminal audit rows IMPLEMENTED (2026-06-09)

### Scope
Micro-task. Founder ruled Option A (implement, not V1.5-defer). Touched ONLY
`backend/app/modules/export/tasks.py`. No commit. Branch
`claude/meesell-project-setup-Tl7DS`. BACKEND_ARCHITECTURE.md untouched (§5.0).

### Defect (from §15/§22 audit, MEDIUM)
`export/tasks.py` docstring lines 15-18 CLAIMED audit writes for
`export.completed`/`export.failed` were "embedded in the service-level pipeline"
(`_run_export_pipeline`), but ZERO `AuditEvent(event_type="export.*")` calls
existed anywhere in the export module. False claim → MEDIUM defect F-15-1.

### What I did
- Added imports mirroring image/tasks.py: `from datetime import datetime, timezone`,
  `from sqlalchemy.exc import SQLAlchemyError`,
  `from app.shared.database import AsyncSessionLocal`,
  `from app.shared.models.audit_event import AuditEvent`.
- New async helper `_emit_export_terminal_audit(*, user_id, export_id, event_type,
  error)` — byte-for-byte same pattern as
  `image/tasks.py:_emit_precheck_completed_audit` (own `AsyncSessionLocal()`
  session, `session.add(row)` + `await session.commit()`, drop-on-failure via
  `except (SQLAlchemyError, Exception) as exc: logger.warning(...)`).
- `export.completed` written at terminal SUCCESS (after
  `asyncio.run(_run_export_pipeline(...))` returns, before the return dict).
- `export.failed` written at terminal FAILURE — GATED on
  `self.request.retries >= self.max_retries` so it fires ONCE on the final
  retries-exhausted attempt. Transient first-attempt failures that later succeed
  record only `export.completed`. Written BEFORE `raise self.retry(exc=exc)`.
- Task body is SYNC (`@shared_task`, not async) so the helper is invoked via
  `asyncio.run(_emit_export_terminal_audit(...))` (same as the pipeline call).
- Corrected docstring lines 15-18 to state writes are in the worker task.
- `__all__` now exports `_emit_export_terminal_audit` for unit tests.

### AuditEvent field shape (LOCKED — confirmed from shared/models/audit_event.py)
Constructor kwargs used: `user_id` (UUID, FK RESTRICT), `event_type` (String(40)),
`entity_type` (String(20), nullable), `entity_id` (UUID, nullable), `diff_jsonb`
(JSONB, nullable — None here), `metadata_jsonb` (JSONB, nullable — carries
`export_id`/`emitted_at`/optional `error`). `id` is BIGSERIAL Identity(always)
— do NOT set. `occurred_at` server_default NOW() — do NOT set.
For export terminal events: entity_type="export", entity_id=exports.id.

### Pattern locked (reusable for any worker terminal audit)
Workers have NO request-close hook → audit_mw post-commit path cannot fire →
every Celery terminal event needs a DIRECT `AuditEvent(...)` write in its own
`AsyncSessionLocal()` session, drop-on-failure with WARNING. Canonical reference:
`image/tasks.py:370-409`. The `metadata_jsonb` (NOT a dedicated `meta` column) is
where worker context (entity ids, timestamps, error repr) goes. There is NO
`core.audit_helpers` module — import `AuditEvent` directly from the ORM model.

### Verification
- `ast.parse` OK; `from app.modules.export import tasks` imports clean; `__all__`
  resolves `['export_xlsx_task', '_emit_export_terminal_audit']`.
- `grep -n "AuditEvent\|export.completed\|export.failed" app/modules/export/tasks.py`
  → 2+ AuditEvent-related call sites, both event types present.
- ruff NOT installed in backend/.venv this session — skipped (import + AST clean).

### Follow-up queued
- services-builder: write `tests/test_export_tasks.py` asserting both event_type
  writes + the `retries >= max_retries` gate (mock AsyncSessionLocal +
  `self.request.retries`). Not done in this no-test micro-task.
- F-15-1 MEDIUM blocker CLOSED in STATUS_BACKEND. F6 (api-routes-builder) + F7
  (services-builder, audit_mw read-flood) still open per §15/§17.

---
