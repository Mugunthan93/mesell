"""Shared foundation layer.

Per BACKEND_ARCHITECTURE.md §3.E + §5, this package contains the stateless
foundation that every module + ``core/`` + ``ai_ops/`` + ``i18n/`` consumes:

  * ``shared.database`` — SQLAlchemy 2.0 async engine + ``AsyncSession`` factory
    + the ``get_db`` FastAPI dependency + ``make_worker_session`` Celery helper.
  * ``shared.valkey`` — four DB-scoped Valkey 8 client factories (OTP / Celery
    broker / Celery results / app cache).
  * ``shared.config`` — Pydantic Settings singleton with fail-fast required-
    field validation at process start.
  * ``shared.models`` — the 13-table ORM registry; the single canonical
    import path for any model class in the codebase.

Locked rule: NO module redefines a model, an engine, a session, or a Settings
class.  Cross-DB Valkey access is structurally impossible — there is no
``get_valkey(db: int)`` factory by design.
"""
