"""svc-export — standalone export microservice (MS Sub-Plan A).

Extracted from the monolith ``app.modules.export`` subtree per
``docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md`` +
backend-coordinator ``spec_msA_backend.md`` §3.A.

The export pipeline logic (``service.py`` / ``tasks.py`` / ``repository.py``
/ ``domain.py`` / ``exceptions.py``) is preserved BYTE-FOR-BYTE from the
monolith per BACKEND_ARCHITECTURE.md §16.G (call-site preservation —
ABSOLUTE).  The ONLY changes to ``service.py`` are import lines: the 4
cross-module imports become HTTP-shim client imports re-exporting the same
``<callee>_service`` symbol names, and intra-module import paths are
mechanically rewritten to the new flat tree.
"""
