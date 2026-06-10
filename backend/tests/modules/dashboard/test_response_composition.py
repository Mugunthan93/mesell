"""Unit test #2 per §13.J.

Verifies the pure-function :func:`_compose_response` is correct in
isolation. Per §13.C the helper exists specifically so the composition
logic can be unit-tested without any DB / I/O / awaiting.

Scenarios:

* Mocked catalog returns 3 products + ``total=42`` (3 of 42 page).
* Mocked customer returns specific completeness counts.
* Verify :class:`DashboardResponse.products` has 3 items, ``total=42``,
  ``page`` and ``limit`` echo the request shape, ``onboarding_completeness``
  mirrors the mocked completeness shape.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.catalog.domain import (
    PaginatedProductsInternal,
    Pagination,
)
from app.modules.dashboard.schemas import DashboardQuery, DashboardResponse
from app.modules.dashboard.service import (
    _compose_response,
    list_products_for_dashboard,
)


class TestComposeResponsePure:
    """The composition helper is a pure function — no DB, no I/O, no await."""

    def test_compose_with_3_products_and_total_42(self, sample_products, sample_completeness):
        paginated = PaginatedProductsInternal(
            items=tuple(sample_products),
            total=42,
            page=1,
            limit=20,
        )

        response = _compose_response(
            paginated=paginated,
            completeness=sample_completeness,
        )

        assert isinstance(response, DashboardResponse)
        assert len(response.products) == 3
        assert response.total == 42
        assert response.page == 1
        assert response.limit == 20

    def test_compose_product_id_field_renamed_from_domain_id(self, sample_products, sample_completeness):
        """``Product.id`` (domain) → ``ProductListItem.product_id`` (wire)."""
        paginated = PaginatedProductsInternal(
            items=tuple(sample_products),
            total=3,
            page=1,
            limit=20,
        )

        response = _compose_response(
            paginated=paginated,
            completeness=sample_completeness,
        )

        for idx, item in enumerate(response.products):
            assert item.product_id == sample_products[idx].id, (
                "product_id at wire must equal Product.id at domain"
            )

    def test_compose_product_status_passthrough(self, sample_products, sample_completeness):
        """Each ``Product.status`` lands on ``ProductListItem.status`` as-is."""
        paginated = PaginatedProductsInternal(
            items=tuple(sample_products),
            total=3,
            page=1,
            limit=20,
        )

        response = _compose_response(
            paginated=paginated,
            completeness=sample_completeness,
        )

        # sample_products fixture builds: [ready, draft, draft]
        assert response.products[0].status == "ready"
        assert response.products[1].status == "draft"
        assert response.products[2].status == "draft"

    def test_compose_product_name_null_passthrough(self, sample_products, sample_completeness):
        """A ``None`` name (seller hasn't filled it) flows through to wire."""
        paginated = PaginatedProductsInternal(
            items=tuple(sample_products),
            total=3,
            page=1,
            limit=20,
        )

        response = _compose_response(
            paginated=paginated,
            completeness=sample_completeness,
        )

        # sample_products[2] has name=None
        assert response.products[2].name is None

    def test_compose_completeness_mirrors_mock(self, sample_products, sample_completeness):
        """:class:`ProfileCompleteness` → :class:`ProfileCompletenessSummary` 1:1."""
        paginated = PaginatedProductsInternal(
            items=tuple(sample_products),
            total=3,
            page=1,
            limit=20,
        )

        response = _compose_response(
            paginated=paginated,
            completeness=sample_completeness,
        )

        oc = response.onboarding_completeness
        assert oc.base_complete_count == sample_completeness.base_complete_count
        assert oc.base_total_count == sample_completeness.base_total_count
        assert oc.extension_complete_count == sample_completeness.extension_complete_count
        assert oc.extension_total_count == sample_completeness.extension_total_count
        assert oc.onboarding_complete == sample_completeness.onboarding_complete

    def test_compose_is_deterministic(self, sample_products, sample_completeness):
        """Same inputs → same outputs. No randomness, no clock reads."""
        paginated = PaginatedProductsInternal(
            items=tuple(sample_products),
            total=42,
            page=2,
            limit=10,
        )

        first = _compose_response(paginated=paginated, completeness=sample_completeness)
        second = _compose_response(paginated=paginated, completeness=sample_completeness)

        # Pydantic model_dump comparison — guarantees deep equality.
        assert first.model_dump() == second.model_dump()


class TestListProductsForDashboardOrchestration:
    """The public service method wires both ``await`` points through to the
    stubs and returns the composed shape. Verifies the §13.C orchestration
    contract (no I/O of its own; pure delegation + composition).
    """

    @pytest.mark.asyncio
    async def test_full_flow_with_3_products_and_total_42(
        self,
        stub_consumed_services,
        sample_products,
        sample_completeness,
    ):
        stub_consumed_services(
            items=sample_products,
            total=42,
            completeness=sample_completeness,
        )

        user_id = uuid4()
        query = DashboardQuery(page=1, limit=20)

        response = await list_products_for_dashboard(
            user_id=user_id,
            query=query,
            db=None,  # stub does not touch db
        )

        assert isinstance(response, DashboardResponse)
        assert len(response.products) == 3
        assert response.total == 42
        assert response.page == 1
        assert response.limit == 20
        assert response.onboarding_completeness.base_complete_count == 8

    @pytest.mark.asyncio
    async def test_query_pagination_forwarded_to_catalog_service(
        self,
        stub_consumed_services,
        sample_products,
        sample_completeness,
    ):
        """``DashboardQuery`` page/limit must reach catalog as :class:`Pagination`."""
        state = stub_consumed_services(
            items=sample_products,
            total=42,
            completeness=sample_completeness,
        )

        user_id = uuid4()
        query = DashboardQuery(page=3, limit=25)

        await list_products_for_dashboard(user_id=user_id, query=query, db=None)

        calls = state["calls"]["list_products"]
        assert len(calls) == 1
        assert calls[0]["page"] == 3
        assert calls[0]["limit"] == 25
        assert calls[0]["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_user_id_forwarded_to_customer_service(
        self,
        stub_consumed_services,
        sample_products,
        sample_completeness,
    ):
        state = stub_consumed_services(
            items=sample_products,
            total=42,
            completeness=sample_completeness,
        )

        user_id = uuid4()
        query = DashboardQuery(page=1, limit=20)

        await list_products_for_dashboard(user_id=user_id, query=query, db=None)

        calls = state["calls"]["get_onboarding_completeness"]
        assert len(calls) == 1
        assert calls[0]["user_id"] == user_id


# Silence unused-import noise — Pagination is imported for documentation purposes;
# the actual instance is constructed inside dashboard.service.
_ = Pagination
