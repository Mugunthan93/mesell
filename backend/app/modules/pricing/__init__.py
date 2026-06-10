"""``pricing`` — Feature 7 Price Calculator module.

Owner specialists: ``meesell-api-routes-builder`` (routes + Pydantic
schemas) + ``meesell-services-builder`` (business logic, P&L calculator,
alert generation) per BACKEND_ARCHITECTURE.md §12 (LOCKED 2026-06-05).

A leaf-with-2-calls module on the cross-module graph (per §2.D matrix:
``pricing → catalog`` for ownership + ``pricing → category`` for
commission; both ✓).  Writes the ``pricing_calcs`` table exclusively
(append-only audit trail per §12.B.1 step 8 + D4).

Per BACKEND_ARCHITECTURE.md §12 the module surfaces 1 endpoint:

1. ``POST /api/v1/products/{id}/price-calc`` — Price Calculator (Feature 7).

NO AI track collaboration — pricing is deterministic math per §6A + §12.H
(no ``ai_ops.client`` import, no Gemini call, no vendor adapter).

§0.E latent bug resolved: the legacy
``backend/app/services/pricing_engine.py`` was DELETED at this
construction time; the new ``service.py`` here is the replacement per
§12.A.  The new ``PricingAlert`` frozen dataclass in ``domain.py``
replaces the deleted legacy ``backend/app/schemas/pricing.PricingAlert``.

The public router is exposed via ``pricing_router`` so ``app/main.py``
can mount it with ``app.include_router(pricing_router)``.
"""

from app.modules.pricing.router import router as pricing_router

__all__: list[str] = ["pricing_router"]
