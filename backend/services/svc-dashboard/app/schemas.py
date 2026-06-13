"""``dashboard`` Pydantic v2 request/response models per §13.E.

Wire shapes for the **1 endpoint** (``GET /api/v1/products``) per §13.B.

**§13.A.1 amendment (2026-06-07) operative scope:**

* :class:`DashboardQuery` carries 2 fields (``page``, ``limit``) —
  ``status_filter`` and ``search`` deferred to V1.5.
* :class:`ProductListItem.status` is narrowed to ``Literal["draft", "ready"]``
  — ``"exported"`` value deferred to V1.5 (the catalog's V1 ``Product.status``
  domain Literal is ``Literal["draft", "ready"]`` per §10.F; ``"exported"``
  state lives on the ``exports`` table per §14).

All other §13.E shape locks stand verbatim. The §4.F handler chain renders
Pydantic ``ValidationError`` as 400 with ``validation.dashboard.invalid_pagination``
per §5A.D + §13.G.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardQuery(BaseModel):
    """Query parameters for ``GET /api/v1/products``.

    Per §13.B amended (§13.A.1, 2026-06-07): 2 fields only. ``status_filter``
    and ``search`` deferred to V1.5 alongside a §10 catalog ``Pagination``
    extension.
    """

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class ProductListItem(BaseModel):
    """One row in the dashboard product listing.

    Maps from :class:`app.modules.catalog.domain.Product` per §13.B.4
    flow step 4 (composition). The ``id`` -> ``product_id`` rename happens
    at this boundary so the wire shape is dashboard-flavoured (sellers
    think in "products", not "catalog rows").
    """

    model_config = ConfigDict(extra="ignore")

    product_id: UUID
    name: str | None  # nullable until seller fills it during catalog flow
    category_id: UUID
    status: Literal["draft", "ready"]  # §13.A.1 narrows from 3-value to 2-value
    created_at: datetime
    updated_at: datetime


class ProfileCompletenessSummary(BaseModel):
    """Customer profile completeness summary for the dashboard header strip.

    Maps 1:1 from :class:`app.modules.customer.domain.ProfileCompleteness`
    per §8.F. ``base_total_count`` is always 10 (the 10 base seller-profile
    fields per §8.F + ``MVP_ARCH §3.2``); the field is sent over the wire
    anyway so the frontend can render "8 of 10" without re-hardcoding the
    denominator. ``extension_total_count`` varies by the seller's
    ``active_super_categories`` per §8.B ``COMPLIANCE_EXTENSION_MAP``.
    """

    model_config = ConfigDict(extra="ignore")

    base_complete_count: int
    base_total_count: int
    extension_complete_count: int
    extension_total_count: int
    onboarding_complete: bool


class DashboardResponse(BaseModel):
    """Wire shape for ``GET /api/v1/products`` (200 OK)."""

    model_config = ConfigDict(extra="ignore")

    products: list[ProductListItem]
    total: int
    page: int
    limit: int
    onboarding_completeness: ProfileCompletenessSummary


__all__ = [
    "DashboardQuery",
    "DashboardResponse",
    "ProductListItem",
    "ProfileCompletenessSummary",
]
