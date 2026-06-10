"""Dashboard-module pytest fixtures.

Per BACKEND_ARCHITECTURE.md §13.J + §13.A.1 amendment (2026-06-07):

* Dashboard has **no vendor egress** per §13.H — NO stubs needed for
  Gemini / MSG91 / GCS / Razorpay / LangFuse.
* Dashboard has **no DB writes** — only reads via consumed services. The
  unit tests can mock the two consumed services without touching Postgres.
* Dashboard has **no AI Ops integration** per §13.I — no ``call_gemini``
  stubbing.

The ``mocked_catalog_list_products`` and ``mocked_customer_completeness``
fixtures provide the deterministic stand-ins the §13.J unit tests
require — they replace ``catalog.service.list_products`` and
``customer.service.get_onboarding_completeness`` via ``monkeypatch`` at
the *service module's* import binding (since
``app.modules.dashboard.service`` binds ``catalog_service`` and
``customer_service`` as module-level aliases at import time).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.modules.catalog.domain import (
    PaginatedProductsInternal,
    Pagination,
    Product,
)
from app.modules.customer.domain import ProfileCompleteness


# ─────────────────────────────────────────────────────────────────────────────
# Domain-object factories (pure — no I/O)
# ─────────────────────────────────────────────────────────────────────────────
def _make_product(
    *,
    id: UUID | None = None,
    user_id: UUID | None = None,
    name: str | None = "Sample Product",
    status: str = "draft",
) -> Product:
    """Build a frozen :class:`catalog.domain.Product` for unit tests.

    Deterministic timestamps for reproducible assertions.
    """
    now = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)
    return Product(
        id=id or uuid4(),
        user_id=user_id or uuid4(),
        catalog_id=uuid4(),
        category_id=uuid4(),
        name=name,
        status=status,  # type: ignore[arg-type]
        fields={},
        ai_suggestions={},
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


@pytest.fixture
def make_product():
    """Return the :func:`_make_product` factory for parameterised use."""
    return _make_product


@pytest.fixture
def sample_products() -> list[Product]:
    """3 frozen :class:`Product` instances for ``test_response_composition``."""
    return [
        _make_product(name="Glow Eye Serum", status="ready"),
        _make_product(name="Daily Face Wash", status="draft"),
        _make_product(name=None, status="draft"),  # name not yet filled
    ]


@pytest.fixture
def sample_completeness() -> ProfileCompleteness:
    """Concrete :class:`ProfileCompleteness` for composition unit tests."""
    return ProfileCompleteness(
        base_complete_count=8,
        base_total_count=10,
        extension_complete_count=2,
        extension_total_count=3,
        onboarding_complete=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Service stubs — replace catalog + customer at the dashboard service's
# import binding so ``await catalog_service.list_products(...)`` and
# ``await customer_service.get_onboarding_completeness(...)`` reach the stubs.
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def stub_consumed_services(monkeypatch):
    """Replace :func:`catalog.service.list_products` and
    :func:`customer.service.get_onboarding_completeness` with deterministic
    stubs at the dashboard service module's import binding.

    Returns a ``configure(items, total, completeness)`` callable so each
    test can shape the stand-ins independently:

        async def test_x(stub_consumed_services, sample_completeness):
            stub_consumed_services(
                items=[],
                total=0,
                completeness=sample_completeness,
            )
            # ... invoke dashboard.service.list_products_for_dashboard ...
    """
    from app.modules.dashboard import service as dashboard_service_module

    state: dict[str, Any] = {
        "items": (),
        "total": 0,
        "completeness": ProfileCompleteness(
            base_complete_count=0,
            base_total_count=10,
            extension_complete_count=0,
            extension_total_count=0,
            onboarding_complete=False,
        ),
        "calls": {"list_products": [], "get_onboarding_completeness": []},
    }

    async def _stub_list_products(
        *,
        user_id: UUID,
        pagination: Pagination,
        db: Any,
    ) -> PaginatedProductsInternal:
        state["calls"]["list_products"].append(
            {
                "user_id": user_id,
                "page": pagination.page,
                "limit": pagination.limit,
            }
        )
        return PaginatedProductsInternal(
            items=tuple(state["items"]),
            total=int(state["total"]),
            page=pagination.page,
            limit=pagination.limit,
        )

    async def _stub_get_completeness(
        *,
        user_id: UUID,
        db: Any,
    ) -> ProfileCompleteness:
        state["calls"]["get_onboarding_completeness"].append(
            {"user_id": user_id}
        )
        return state["completeness"]

    # Patch the BOUND module aliases the dashboard service uses at runtime.
    monkeypatch.setattr(
        dashboard_service_module.catalog_service,
        "list_products",
        _stub_list_products,
    )
    monkeypatch.setattr(
        dashboard_service_module.customer_service,
        "get_onboarding_completeness",
        _stub_get_completeness,
    )

    def configure(
        *,
        items: list[Product] | tuple[Product, ...] = (),
        total: int = 0,
        completeness: ProfileCompleteness | None = None,
    ) -> dict[str, Any]:
        state["items"] = tuple(items)
        state["total"] = total
        if completeness is not None:
            state["completeness"] = completeness
        return state

    return configure


__all__ = [
    "make_product",
    "sample_completeness",
    "sample_products",
    "stub_consumed_services",
]


# Silence unused-import noise — ``replace`` is reserved for future
# parametrisation that swaps individual fields on the frozen Product.
_ = replace
