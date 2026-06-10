"""Unit test #3 per §13.J.

Boundary case for first-time sellers: empty inventory must return 200 with
``products=[]`` + ``total=0`` (NOT 404 — empty seller inventory is a valid
state per §13.B status-code lock).

Profile completeness still surfaces (the seller still has a profile shape
even with zero products — possibly a brand-new account with
``base_complete_count=0`` per :func:`customer.service.get_onboarding_completeness`
first-time-seller no-profile branch).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.catalog.domain import PaginatedProductsInternal
from app.modules.customer.domain import ProfileCompleteness
from app.modules.dashboard.schemas import DashboardQuery, DashboardResponse
from app.modules.dashboard.service import (
    _compose_response,
    list_products_for_dashboard,
)


class TestEmptyStateCompose:
    """Pure-function variant — verifies :func:`_compose_response` shape on empty."""

    def test_empty_paginated_yields_empty_products_list(self):
        paginated = PaginatedProductsInternal(
            items=(),
            total=0,
            page=1,
            limit=20,
        )
        completeness = ProfileCompleteness(
            base_complete_count=0,
            base_total_count=10,
            extension_complete_count=0,
            extension_total_count=0,
            onboarding_complete=False,
        )

        response = _compose_response(
            paginated=paginated,
            completeness=completeness,
        )

        assert isinstance(response, DashboardResponse)
        assert response.products == []
        assert response.total == 0
        assert response.page == 1
        assert response.limit == 20

    def test_empty_completeness_still_surfaces(self):
        """First-time seller with no profile rows yet — still emits the summary."""
        paginated = PaginatedProductsInternal(
            items=(),
            total=0,
            page=1,
            limit=20,
        )
        completeness = ProfileCompleteness(
            base_complete_count=0,
            base_total_count=10,
            extension_complete_count=0,
            extension_total_count=0,
            onboarding_complete=False,
        )

        response = _compose_response(
            paginated=paginated,
            completeness=completeness,
        )

        oc = response.onboarding_completeness
        assert oc.base_complete_count == 0
        assert oc.base_total_count == 10  # the "10" denominator always surfaces
        assert oc.extension_complete_count == 0
        assert oc.extension_total_count == 0
        assert oc.onboarding_complete is False


class TestEmptyStateFullFlow:
    """Orchestration variant — verifies the full
    :func:`list_products_for_dashboard` path with empty stubs.
    """

    @pytest.mark.asyncio
    async def test_empty_inventory_returns_200_shape_with_empty_products(
        self,
        stub_consumed_services,
    ):
        """The §13.B locked rule: empty inventory is 200, NOT 404."""
        stub_consumed_services(
            items=(),
            total=0,
            completeness=ProfileCompleteness(
                base_complete_count=0,
                base_total_count=10,
                extension_complete_count=0,
                extension_total_count=0,
                onboarding_complete=False,
            ),
        )

        user_id = uuid4()
        query = DashboardQuery(page=1, limit=20)

        response = await list_products_for_dashboard(
            user_id=user_id,
            query=query,
            db=None,
        )

        # The endpoint returns the composed shape — the absence of an
        # exception IS the "200" assertion at the service-layer test level.
        # The router test (test_dashboard_get_products_route_mounted in
        # boot_integration) confirms the wire-level 200 path.
        assert response.products == []
        assert response.total == 0
        assert response.onboarding_completeness.base_complete_count == 0
        # base_total_count is always 10 — denominator surfaces even on empty.
        assert response.onboarding_completeness.base_total_count == 10

    @pytest.mark.asyncio
    async def test_empty_completeness_still_surfaces_in_full_flow(
        self,
        stub_consumed_services,
    ):
        """Profile shape stays visible to the wizard CTA even at zero products."""
        stub_consumed_services(
            items=(),
            total=0,
            completeness=ProfileCompleteness(
                base_complete_count=2,
                base_total_count=10,
                extension_complete_count=0,
                extension_total_count=0,
                onboarding_complete=False,
            ),
        )

        user_id = uuid4()
        query = DashboardQuery(page=1, limit=20)

        response = await list_products_for_dashboard(
            user_id=user_id,
            query=query,
            db=None,
        )

        assert response.onboarding_completeness.base_complete_count == 2
        assert response.onboarding_completeness.onboarding_complete is False

    @pytest.mark.asyncio
    async def test_empty_state_with_high_page_number_does_not_404(
        self,
        stub_consumed_services,
    ):
        """``GET /api/v1/products?page=100&limit=20`` on a 0-product seller
        returns 200 with empty list — the page being past the end is NOT 404.
        """
        stub_consumed_services(
            items=(),
            total=0,
            completeness=ProfileCompleteness(
                base_complete_count=0,
                base_total_count=10,
                extension_complete_count=0,
                extension_total_count=0,
                onboarding_complete=False,
            ),
        )

        user_id = uuid4()
        query = DashboardQuery(page=100, limit=20)

        response = await list_products_for_dashboard(
            user_id=user_id,
            query=query,
            db=None,
        )

        assert response.products == []
        assert response.total == 0
        assert response.page == 100  # echoes the request
        assert response.limit == 20
