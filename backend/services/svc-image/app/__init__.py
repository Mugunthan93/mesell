"""svc-image — standalone image upload + precheck microservice (MS Sub-Plan C).

Extracted from the monolith ``app.modules.image`` subtree per
``docs/plans/microservices_migration/SUB_PLAN_0C_image_extraction.md`` +
backend-coordinator ``spec_msC_backend_EXECUTION.md`` §1 B1.

The pipeline logic (``service.py`` / ``tasks.py`` / ``domain.py`` /
``exceptions.py``) is preserved BYTE-FOR-BYTE from the monolith per
BACKEND_ARCHITECTURE.md §16.G (call-site preservation — ABSOLUTE).  The ONLY
changes to ``service.py`` + ``tasks.py`` are import lines: the catalog
cross-module import becomes the HTTP-shim ``catalog_client`` re-exporting the
same ``catalog_service`` symbol name, and intra-module import paths are
mechanically rewritten to the flat tree.

``repository.py`` is the FOUNDER-RULED Option-B EXCEPTION to §16.G (spec §0.3
/ develop ``d4aa572`` / PR #197): its method bodies are rewritten to drop the
cross-schema ``products`` join and scope by ``product_id`` / ``image_id``
direct — tenancy is proved by the upstream ``catalog.assert_product_ownership``
HTTP shim, NOT a local join.
"""
