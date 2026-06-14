"""svc-catalog vendored ORM models.

catalog OWNS THREE tenant-scoped tables — ``catalogs`` / ``products`` /
``product_drafts`` — all bound to the ``catalog`` schema (moved ``public`` →
``catalog`` in MS-H Phase A, migration ``a8f3b2e9c1d5``).  The two ``public``
tables the vendored core layer touches are also vendored:

* :class:`Catalog` / :class:`Product` / :class:`ProductDraft` — bound to
  ``catalog``; the catalog ``repository`` reads/writes these.  INTRA-schema
  relationships are KEPT (Catalog ↔ Product ↔ ProductDraft); the cross-schema
  ``user`` / ``category`` / ``images`` / ``pricing_calcs`` / ``exports``
  relationships are DROPPED (§2.D — those ORM models are sibling-owned and not
  vendored).
* :class:`User` — bound to ``public``; ``core/auth.get_current_user`` does an
  existence check (``db.get(User, sub)``), AND ``core/plan_guard.enforce_plan_limit``
  imports ``Product`` lazily for the ``product_count`` total-cap COUNT (catalog
  DOES hit ``product_count`` in ``create_product`` — unlike category, which
  never did; so the ``Product`` export below is LOAD-BEARING for plan_guard).
* :class:`AuditEvent` — bound to ``public`` (the shared audit ledger).
  ``audit_mw`` writes the 4 write-route audit facts (created/updated/deleted/
  autofill.invoked) via a cross-schema INSERT, AND the vendored ai_ops
  ``cost_tracker`` writes the AI committed-cost ledger to the SAME table — both
  covered by ``GRANT INSERT ON public.audit_events TO catalog_user`` (H3.c).
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.catalog import Catalog
from app.shared.models.product import Product
from app.shared.models.product_draft import ProductDraft
from app.shared.models.user import User

__all__ = ["AuditEvent", "Catalog", "Product", "ProductDraft", "User"]
