"""svc-export vendored ORM models.

Three trimmed models, mirroring the monolith DDL shapes but WITHOUT the
cross-schema relationships (svc-export queries scalar columns only, so the
ORM relationships are unnecessary and would require importing models the
service does not own):

* :class:`Export` — bound to the ``export`` Postgres schema (Sub-Plan A
  schema-split).  The repository's only ORM entity.
* :class:`AuditEvent` — bound to ``public`` (the monolith owns the audit
  table; ``tasks.py`` writes ``export.completed`` / ``export.failed`` rows
  via a fully-qualified cross-schema INSERT).
* :class:`User` — bound to ``public``; ``core/auth.get_current_user`` does
  an existence check (``db.get(User, sub)``).
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.export import Export
from app.shared.models.user import User

__all__ = ["AuditEvent", "Export", "User"]
