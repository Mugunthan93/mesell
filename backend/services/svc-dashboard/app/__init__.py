"""svc-dashboard — standalone dashboard microservice (MS Sub-Plan B).

Extracted from the monolith ``app.modules.dashboard`` subtree per
``docs/plans/microservices_migration/SUB_PLAN_0B_dashboard_extraction.md`` +
backend-coordinator ``spec_msB_backend.md`` §3.A.

dashboard is a LEAF CONSUMER (§2.D matrix): it reads from ``catalog`` and
``customer`` and is read by no one.  It owns ZERO tables (§13.D), runs NO
Celery worker (it is a pure read — §13.I), and exposes NO ``/internal/*``
surface (zero inbound callers).

The composition logic (``service.py``) is preserved BYTE-FOR-BYTE from the
monolith per BACKEND_ARCHITECTURE.md §16.G (call-site preservation —
ABSOLUTE).  The ONLY changes to ``service.py`` are import lines: the 2
cross-module imports become HTTP-shim client imports re-exporting the same
``<callee>_service`` symbol names, and the schema/domain import paths are
mechanically rewritten to the new flat tree.  ``_compose_response`` remains a
PURE function (no I/O, no ``await``, no clock, no randomness — §13.C).
"""
