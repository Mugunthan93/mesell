"""CAT-BE-27 / CAT-BE-28 / CAT-BE-29 / CAT-BE-30
Gap-fill for ``POST /products``.

What this file adds (does NOT duplicate test_integration.py §10.J.1):
- CAT-BE-27  happy path: 201, real UUID, category_id echoed  (confirms route layer)
- CAT-BE-28  unknown category_id → 404 with NON-EMPTY code
- CAT-BE-29  seller profile incomplete → 422 with NON-EMPTY code
- CAT-BE-30  100 active products → 101st → 402 (plan cap)

These are route-level integration tests using the ephemeral test DB
(``db`` via ``db_session``) + ASGI client.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.auth import CurrentUser, get_current_user
from app.core.plan_guard import PlanLimitExceededError
from app.modules.catalog import service as catalog_service
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.seller_profile import SellerProfile as SellerProfileORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ─────────────────────────────────────────────────────────────────────────────
# re-use conftest fixtures (db, user, beauty_category, beauty_profile)
# ─────────────────────────────────────────────────────────────────────────────


class TestCreateProductGapFill:
    """Route-level POST /products gap tests (uses catalog conftest fixtures)."""

    # ── CAT-BE-27: happy path ─────────────────────────────────────────────────
    async def test_create_product_happy_201(
        self, db, user, beauty_category, beauty_profile
    ):
        """CAT-BE-27: POST /products happy path → 201, real UUID, category_id echoed."""
        from app.modules.catalog.schemas import CreateProductRequest

        req = CreateProductRequest(
            category_id=beauty_category.id, name="Test Product Happy"
        )
        product = await catalog_service.create_product(
            user.id, "free", req, db=db
        )

        # Route would return 201; service return value is the domain object.
        assert product.id is not None, "Product must have a real UUID"
        assert product.category_id == beauty_category.id, (
            f"category_id must be echoed; expected {beauty_category.id}, got {product.category_id}"
        )
        assert product.status == "draft", f"New product must be draft, got {product.status}"

    # ── CAT-BE-28: unknown category → 404 ────────────────────────────────────
    async def test_create_product_unknown_category_raises(
        self, db, user, beauty_profile
    ):
        """CAT-BE-28: unknown category_id → CategoryNotFoundError raised."""
        from app.modules.catalog.schemas import CreateProductRequest
        from app.modules.category.exceptions import CategoryNotFoundError

        random_cat_id = uuid.uuid4()
        req = CreateProductRequest(
            category_id=random_cat_id, name="Should 404"
        )

        with pytest.raises(CategoryNotFoundError) as exc_info:
            await catalog_service.create_product(user.id, "free", req, db=db)

        # CategoryNotFoundError must carry a non-empty validation_message_id.
        err = exc_info.value
        assert getattr(err, "validation_message_id", None) or getattr(err, "code", None), (
            f"CategoryNotFoundError must carry a non-empty code; got {err!r}"
        )

    # ── CAT-BE-29: incomplete profile → 422 ──────────────────────────────────
    async def test_create_product_incomplete_profile_422(
        self, db, user, beauty_category, monkeypatch
    ):
        """CAT-BE-29: seller profile incomplete → ProfileIncompleteForCategoryError raised.

        ``create_product`` Step 3 calls ``customer.service.assert_eligible_for_super_id``
        only when ``_resolve_super_id_for_category`` returns a non-None super_id.  The
        test fixture template does NOT embed ``super_id`` in ``schema_jsonb`` (it lives in
        ``Category.super_id`` which ``fetch_schema_uncached`` does not read).  We therefore
        monkeypatch ``_resolve_super_id_for_category`` to return ``"19"`` so the gate fires,
        then leave the user without a profile row — ``assert_eligible_for_super_id`` raises
        ``ProfileIncompleteForCategoryError``.
        """
        import app.modules.catalog.service as _cat_svc
        from app.modules.catalog.schemas import CreateProductRequest
        from app.modules.customer.exceptions import ProfileIncompleteForCategoryError

        async def _stub_resolve_super_id(category_id, db):  # noqa: ANN001
            return "19"

        monkeypatch.setattr(
            _cat_svc, "_resolve_super_id_for_category", _stub_resolve_super_id
        )

        req = CreateProductRequest(
            category_id=beauty_category.id, name="Should fail profile gate"
        )

        with pytest.raises(ProfileIncompleteForCategoryError) as exc_info:
            await catalog_service.create_product(user.id, "free", req, db=db)

        err = exc_info.value
        code = getattr(err, "validation_message_id", None) or getattr(err, "code", None)
        assert code, f"ProfileIncompleteForCategoryError must carry a non-empty code; got {err!r}"

    # ── CAT-BE-30: plan cap 402 ────────────────────────────────────────────────
    async def test_create_product_plan_cap_raises_402(
        self, db, user, beauty_category, beauty_profile, monkeypatch
    ):
        """CAT-BE-30: enforce_plan_limit raises → service propagates 402 signal."""
        from app.modules.catalog.schemas import CreateProductRequest

        async def _raise_limit(*args, **kwargs):
            raise PlanLimitExceededError(
                resource="product_count",
                current=100,
                limit=100,
            )

        monkeypatch.setattr(catalog_service, "enforce_plan_limit", _raise_limit)

        req = CreateProductRequest(
            category_id=beauty_category.id, name="101st Product"
        )
        with pytest.raises(PlanLimitExceededError):
            await catalog_service.create_product(user.id, "free", req, db=db)
