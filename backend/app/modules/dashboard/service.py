"""``dashboard`` service layer per §13.C.

ONE public async method (:func:`list_products_for_dashboard`) — a thin
orchestration wrapper around two ``await`` points + one pure compose call.
ONE module-private helper (:func:`_compose_response`) — pure function with
NO I/O, NO DB, NO ``await`` — unit-tested in isolation per §13.J.

The simplicity is the point: dashboard is a leaf consumer on the §2.D
matrix and a producer of nothing. No other module reads from dashboard.

**Cross-module calls (per §16.B rows 6 + 7):**

* :func:`catalog.service.list_products` — paginated active products.
  ``scope_to_user(user_id)`` enforced at catalog's repository per §10.D.
* :func:`customer.service.get_onboarding_completeness` — profile
  completeness summary. ``scope_to_user(user_id)`` enforced at customer's
  repository per §8.D.

**Adapters touched:** NONE per §13.H (P95 ≤ 200 ms budget per §1.E).

**AI Ops touched:** NONE per §13.I (this is a pure read).

**i18n key:** ``validation.dashboard.invalid_pagination`` — registered at
:data:`app.i18n.messages_en.VALIDATION_MESSAGES`. The Pydantic validator
in :class:`schemas.DashboardQuery` raises ``ValidationError`` for invalid
``page`` / ``limit``; the §4.F handler resolves the message ID.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.catalog.domain import (
    PaginatedProductsInternal,
    Pagination,
)
from app.modules.customer import service as customer_service
from app.modules.customer.domain import ProfileCompleteness
from app.modules.dashboard.schemas import (
    DashboardQuery,
    DashboardResponse,
    ProductListItem,
    ProfileCompletenessSummary,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public surface — single method per §13.C
# ─────────────────────────────────────────────────────────────────────────────
async def list_products_for_dashboard(
    user_id: UUID,
    query: DashboardQuery,
    db: AsyncSession,
) -> DashboardResponse:
    """Compose the dashboard view per §13.B.4 flow.

    1. Build :class:`catalog.domain.Pagination` from the validated
       ``DashboardQuery``.
    2. ``await`` :func:`catalog.service.list_products` — returns a
       :class:`PaginatedProductsInternal` with ``scope_to_user`` already
       enforced at catalog's repository layer.
    3. ``await`` :func:`customer.service.get_onboarding_completeness` —
       returns a :class:`ProfileCompleteness` with ``scope_to_user``
       already enforced at customer's repository layer.
    4. :func:`_compose_response` (pure, no I/O) maps both into the wire
       shape :class:`DashboardResponse`.

    Owns no data access; pure delegation + composition.
    """
    pagination = Pagination(page=query.page, limit=query.limit)

    paginated: PaginatedProductsInternal = await catalog_service.list_products(
        user_id=user_id,
        pagination=pagination,
        db=db,
    )

    completeness: ProfileCompleteness = (
        await customer_service.get_onboarding_completeness(
            user_id=user_id,
            db=db,
        )
    )

    return _compose_response(paginated=paginated, completeness=completeness)


# ─────────────────────────────────────────────────────────────────────────────
# Internal — pure function, unit-tested in isolation per §13.J test #2
# ─────────────────────────────────────────────────────────────────────────────
def _compose_response(
    *,
    paginated: PaginatedProductsInternal,
    completeness: ProfileCompleteness,
) -> DashboardResponse:
    """Pure composition: catalog + customer domain → wire shape.

    No I/O. No DB. No ``await``. No clock reads. No randomness. Deterministic
    one-shot mapping — the function can be invoked in unit tests with mocked
    inputs and the output is fully predictable per §13.J test #2.

    Field mappings:

    * ``Product.id`` → ``ProductListItem.product_id`` (rename at boundary).
    * ``Product.name``, ``Product.category_id``, ``Product.status``,
      ``Product.created_at``, ``Product.updated_at`` → 1:1 copy.
    * ``ProfileCompleteness`` → :class:`ProfileCompletenessSummary` 1:1.

    Per §13.A.1: ``Product.status`` is ``Literal["draft", "ready"]`` in V1
    (per §10.F) — matches the amended :class:`ProductListItem.status` Literal.
    """
    products = [
        ProductListItem(
            product_id=product.id,
            name=product.name,
            category_id=product.category_id,
            status=product.status,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
        for product in paginated.items
    ]

    summary = ProfileCompletenessSummary(
        base_complete_count=completeness.base_complete_count,
        base_total_count=completeness.base_total_count,
        extension_complete_count=completeness.extension_complete_count,
        extension_total_count=completeness.extension_total_count,
        onboarding_complete=completeness.onboarding_complete,
    )

    return DashboardResponse(
        products=products,
        total=paginated.total,
        page=paginated.page,
        limit=paginated.limit,
        onboarding_completeness=summary,
    )


__all__ = [
    "list_products_for_dashboard",
    # `_compose_response` is intentionally NOT exported — module-private per §13.C.
]
