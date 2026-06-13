"""svc-customer vendored ORM models.

customer OWNS ONE table — :class:`SellerProfile`, bound to the ``customer``
schema (moved from ``public`` by migration ``a9f3b2c5e1d8``).

Two ``public`` tables are vendored for the cross-cutting core layer:

* :class:`User` — bound to ``public``; ``core/auth.get_current_user`` does an
  existence check (``db.get(User, sub)``).  The FK from ``seller_profile`` was
  SEVERED on extraction (Risk #5) — there is NO relationship between them here.
* :class:`AuditEvent` — bound to ``public`` (the monolith owns the audit
  table; ``audit_mw`` writes the audit fact on customer's 3 PATCH endpoints via
  a cross-schema INSERT into ``public.audit_events``).
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.seller_profile import SellerProfile
from app.shared.models.user import User

__all__ = ["AuditEvent", "SellerProfile", "User"]
