"""svc-pricing vendored ORM models.

pricing OWNS ONE table — ``pricing_calcs`` — bound to the ``pricing`` schema
(moved ``public`` → ``pricing`` in MS-D Phase A).  The two ``public`` tables
the vendored core layer touches are also vendored:

* :class:`PricingCalc` — bound to ``pricing``; the pricing ``repository``
  reads/writes this (insert_calc + find_latest_by_product).  NO ``Product``
  relationship / ForeignKey (§0.6 — catalog-owned, not vendored).
* :class:`User` — bound to ``public``; ``core/auth.get_current_user`` does an
  existence check (``db.get(User, sub)``).
* :class:`AuditEvent` — bound to ``public`` (the monolith owns the audit
  table; ``audit_mw`` writes the request-level audit fact via a cross-schema
  INSERT — for pricing's write POST this ACTUALLY FIRES on the 2xx path).
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.pricing_calc import PricingCalc
from app.shared.models.user import User

__all__ = ["AuditEvent", "PricingCalc", "User"]
