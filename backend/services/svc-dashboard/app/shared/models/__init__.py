"""svc-dashboard vendored ORM models.

dashboard owns ZERO tables (§13.D) — there is NO dashboard model here.  Only
the two ``public`` tables the vendored core layer touches are vendored:

* :class:`User` — bound to ``public``; ``core/auth.get_current_user`` does an
  existence check (``db.get(User, sub)``).
* :class:`AuditEvent` — bound to ``public`` (the monolith owns the audit
  table; ``audit_mw`` writes the request-level audit fact via a cross-schema
  INSERT — though dashboard's mounted route is a read-only GET, so the audit
  middleware NO-OPs on it; the model is vendored for chain-shape parity).
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.user import User

__all__ = ["AuditEvent", "User"]
