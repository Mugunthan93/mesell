"""svc-image vendored ORM models.

Three trimmed models, mirroring the monolith DDL shapes but WITHOUT the
cross-schema relationships (svc-image queries scalar columns only, so the
ORM relationships are unnecessary and would require importing models the
service does not own):

* :class:`ProductImage` — bound to the ``image`` Postgres schema (Sub-Plan C
  schema-split).  The repository's only ORM entity.  Its former ``products``
  ForeignKey + relationship are DROPPED per OPTION B (spec §0.3) — svc-image
  issues no ``products`` read; tenancy is the upstream ownership shim.
* :class:`AuditEvent` — bound to ``public`` (the monolith owns the audit
  table; ``tasks.py`` writes ``image.precheck.completed`` rows via a
  fully-qualified cross-schema INSERT per §15.E).
* :class:`User` — bound to ``public``; ``core/auth.get_current_user`` +
  the ``task_prerun`` worker JWT re-validation do an existence check.
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.product_image import ProductImage
from app.shared.models.user import User

__all__ = ["AuditEvent", "ProductImage", "User"]
