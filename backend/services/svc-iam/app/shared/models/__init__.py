"""svc-iam vendored ORM models.

iam OWNS ONE table — ``users`` — bound to the ``iam`` schema (moved
``public`` → ``iam`` in MS-4 Phase A, migration ``b1c2d3e4f5a6``).  The
``public`` audit table the vendored core layer writes to is also vendored:

* :class:`User` — bound to ``iam``; the iam ``repository`` reads/writes this
  (find_user_by_phone + upsert_user_on_login + get_user_by_id) and
  ``core/auth.get_current_user`` does the existence check (``db.get(User, sub)``).
  All SQLAlchemy relationships are DROPPED — the cross-schema FKs to ``users.id``
  were dropped by migration ``b1c2d3e4f5a6`` and the sibling tables
  (SellerProfile / Catalog / Product / Export / ProductDraft) live in their own
  extracted services, not in iam-svc (SUB_PLAN_0G §0.7).
* :class:`AuditEvent` — bound to ``public`` (the monolith owns the audit
  table; ``audit_mw`` + the §7.I service-layer direct-ORM path write the audit
  fact via a cross-schema INSERT — iam's auth routes are write POSTs so the
  audit path FIRES).
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.user import User

__all__ = ["AuditEvent", "User"]
