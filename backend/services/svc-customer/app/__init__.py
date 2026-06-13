"""svc-customer — standalone seller-profile / onboarding microservice (MS Sub-Plan E).

Extracted from the monolith ``app.modules.customer`` subtree per
``docs/plans/microservices_migration/SUB_PLAN_0E_customer_extraction.md`` +
backend-coordinator ``spec_msE_backend.md`` §3.A.

customer owns ONE table — ``customer.seller_profile`` (schema-split from
``public`` by migration ``a9f3b2c5e1d8``).  It runs NO Celery worker (it has no
background jobs), exposes 3 INBOUND ``/internal/*`` surfaces (the frozen
compliance-block / onboarding-completeness / eligibility contracts), and is the
CALLER of ONE outbound shim (``GET /internal/super-categories`` — FROZEN-0E).

Extraction fidelity (BACKEND_ARCHITECTURE.md §16.G — call-site preservation):
``service.py`` is preserved BYTE-FOR-BYTE from the monolith EXCEPT the 2
sanctioned edits: (a) the ``_load_super_id_set`` loader body swaps the
``SELECT DISTINCT super_id FROM categories`` ORM read for
``await category_client.get_super_category_set()``; (b) the ``CategoryORM``
import is dropped.  No other logic change.  ``domain.py`` /  ``exceptions.py``
are VERBATIM.  ``repository.py`` keeps ``scope_to_user`` on all 4 methods.
"""
