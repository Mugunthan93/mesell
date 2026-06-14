"""svc-category vendored ORM models.

Five trimmed models mirroring the monolith DDL shapes:

* :class:`Category` / :class:`Template` / :class:`FieldEnumValue` — bound to
  the ``category`` Postgres schema (Sub-Plan F schema-split, migration
  ``c4f1e7a9d302``).  The 3 tables svc-category OWNS + reads.  Their former
  cross-schema ``products`` / ``catalogs`` relationships are DROPPED (those
  tables are catalog-owned and not vendored); the intra-schema
  Category↔Template↔FieldEnumValue relationships are KEPT.
* :class:`AuditEvent` — bound to ``public`` (the monolith owns the audit
  ledger).  The vendored ``ai_ops.cost_tracker`` writes AI-cost rows here via
  a cross-schema INSERT (the SHARED ₹500/day budget ledger, F3.c) enabled by
  ``GRANT INSERT ON public.audit_events TO category_user``.
* :class:`User` — bound to ``public``; ``core/auth.get_current_user`` does an
  existence check (``db.get(User, sub)``).

NOTE: ``Product`` is intentionally NOT vendored.  The vendored
``core/plan_guard.enforce_plan_limit`` lazy-imports ``Product`` ONLY inside
its ``product_count`` branch — svc-category never calls that resource (its
sole plan-guard resource is ``smart_picker_hourly``, a Valkey sliding-window
that needs no ORM), so the import stays dormant.
"""

from app.shared.models.audit_event import AuditEvent
from app.shared.models.category import Category
from app.shared.models.field_enum_value import FieldEnumValue
from app.shared.models.template import Template
from app.shared.models.user import User

__all__ = [
    "AuditEvent",
    "Category",
    "FieldEnumValue",
    "Template",
    "User",
]
