"""``customer`` — Seller Profile & Onboarding module.

Owner specialists: ``meesell-api-routes-builder`` (routes + Pydantic schemas) +
``meesell-services-builder`` (business logic, compliance-extension resolver,
onboarding state machine) per BACKEND_ARCHITECTURE.md §2.2.

Per BACKEND_ARCHITECTURE.md §8 (LOCKED 2026-06-05), this module exposes
5 endpoint surfaces:

1. ``GET    /api/v1/seller-profile``                       — read current profile
2. ``PATCH  /api/v1/seller-profile``                       — partial update of base fields
3. ``PATCH  /api/v1/seller-profile/active-categories``     — declare/update active super-categories
4. ``PATCH  /api/v1/seller-profile/compliance/{super_id}`` — set compliance extension for one super
5. ``GET    /api/v1/seller-profile/required-fields``       — drives the onboarding wizard

Leaf module on the cross-module call graph (per §2.D) — ``customer`` itself
calls no other module's ``service.py``.  But ``customer`` IS called BY
``catalog`` (PROFILE_INCOMPLETE_FOR_CATEGORY gate), ``export`` (compliance
block for XLSX emission), and ``dashboard`` (profile-completeness badge) —
those callers consume the public service methods locked in §8.C.

The public router lives in :mod:`.router` (authored by api-routes-builder
in step 2 of 2); the service surface lives in :mod:`.service`; the
repository (module-private per §16) lives in :mod:`.repository`.

The public router is exposed via ``customer_router`` so ``app/main.py`` can
mount it with ``app.include_router(customer_router)``.
"""

from app.modules.customer.router import router as customer_router

__all__: list[str] = ["customer_router"]
