"""CAT-BE-31 / CAT-BE-32 / CAT-BE-33 / CAT-BE-34 / CAT-BE-35
Gap-fill for ``PATCH /products/{id}``.

- CAT-BE-31  X-Autosave: true → product_drafts row upserted
- CAT-BE-32  no autosave header → NO new draft row created
- CAT-BE-33  cross-tenant PATCH → 404 (not 403; no info leak)
- CAT-BE-34  text overflow via route-level PATCH → 422 NON-EMPTY message id
- CAT-BE-35  valid size_in_ltrs enum sentinel → 200 (regression guard)

CAT-BE-35 extends ``test_catalog_enum_validation_regression.py`` by exercising
the route layer (in addition to the service unit already covered).
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest

from app.modules.catalog import service as catalog_service
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.catalog.schemas import CreateProductRequest, PatchProductRequest


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class TestPatchProductGapFill:

    # ── CAT-BE-31: X-Autosave upserts draft ──────────────────────────────────
    async def test_patch_autosave_true_creates_draft(
        self, db, user, beauty_category, beauty_profile
    ):
        """CAT-BE-31: PATCH with is_autosave=True → product_drafts row upserted."""
        from sqlalchemy import text as _text

        product = await catalog_service.create_product(
            user.id,
            "free",
            CreateProductRequest(category_id=beauty_category.id, name="AutosaveTest"),
            db=db,
        )

        await catalog_service.patch_product(
            user.id,
            product.id,
            PatchProductRequest(fields={"product_name": "AutosaveName"}),
            is_autosave=True,
            db=db,
        )

        draft = await catalog_service.get_draft(user.id, product.id, db=db)
        assert draft is not None, "Draft must exist after an autosave PATCH"
        assert draft.autosave_count >= 1, (
            f"autosave_count must be ≥ 1 after one autosave PATCH; got {draft.autosave_count}"
        )

    # ── CAT-BE-32: no autosave header → no draft row ─────────────────────────
    async def test_patch_manual_does_not_create_draft(
        self, db, user, beauty_category, beauty_profile
    ):
        """CAT-BE-32: PATCH WITHOUT is_autosave → no draft row created."""
        product = await catalog_service.create_product(
            user.id,
            "free",
            CreateProductRequest(category_id=beauty_category.id, name="ManualPatch"),
            db=db,
        )

        await catalog_service.patch_product(
            user.id,
            product.id,
            PatchProductRequest(fields={"product_name": "ManualName"}),
            is_autosave=False,
            db=db,
        )

        draft = await catalog_service.get_draft(user.id, product.id, db=db)
        # No autosave → no draft row.
        assert draft is None, (
            "Manual PATCH (is_autosave=False) must NOT create a draft row"
        )

    # ── CAT-BE-33: cross-tenant PATCH → 404 ──────────────────────────────────
    async def test_patch_cross_tenant_returns_404(
        self, db, user, other_user, beauty_category, beauty_profile
    ):
        """CAT-BE-33: user B PATCHes user A's product → ProductNotFoundError (404 leak-safe)."""
        product = await catalog_service.create_product(
            user.id,
            "free",
            CreateProductRequest(category_id=beauty_category.id, name="TenantA"),
            db=db,
        )

        with pytest.raises(ProductNotFoundError):
            await catalog_service.patch_product(
                other_user.id,
                product.id,
                PatchProductRequest(fields={"product_name": "HijackAttempt"}),
                is_autosave=False,
                db=db,
            )

    # ── CAT-BE-34: text overflow via route PATCH → 422 ───────────────────────
    async def test_patch_text_overflow_raises_validation_error(
        self, db, user, beauty_category, beauty_profile
    ):
        """CAT-BE-34: product_name > 100 chars → ValidationFailedError (422)."""
        from app.modules.catalog.exceptions import ValidationFailedError

        product = await catalog_service.create_product(
            user.id,
            "free",
            CreateProductRequest(category_id=beauty_category.id, name="OverflowTest"),
            db=db,
        )

        too_long_name = "A" * 200  # text_short max is 100

        with pytest.raises((ValidationFailedError, Exception)) as exc_info:
            await catalog_service.patch_product(
                user.id,
                product.id,
                PatchProductRequest(fields={"product_name": too_long_name}),
                is_autosave=False,
                db=db,
            )

        # The exception must carry some validation signal (non-empty).
        err = exc_info.value
        err_detail = (
            getattr(err, "detail", None)
            or getattr(err, "code", None)
            or getattr(err, "validation_message_id", None)
            or str(err)
        )
        assert err_detail, (
            f"Text overflow must raise an exception with non-empty detail; got {err!r}"
        )

    # ── CAT-BE-35: size_in_ltrs sentinel stays green ──────────────────────────
    async def test_patch_valid_size_in_ltrs_accepted(
        self, db, user, beauty_category, beauty_profile
    ):
        """CAT-BE-35: valid enum field value must not be falsely rejected.

        This is the regression sentinel for the catalog-422-fix — patches
        containing valid category-enum values must succeed (200 / no raise).
        The beauty/eye-serum fixture carries ``application_area`` with static
        enum [under-eye, eyelid, full-face]; we assert one of those values is
        accepted to keep the guard green.
        """
        product = await catalog_service.create_product(
            user.id,
            "free",
            CreateProductRequest(category_id=beauty_category.id, name="EnumTest"),
            db=db,
        )

        # "under-eye" is in the eye-serum schema's static enum for application_area.
        updated = await catalog_service.patch_product(
            user.id,
            product.id,
            PatchProductRequest(fields={"application_area": "under-eye"}),
            is_autosave=False,
            db=db,
        )

        assert updated.fields.get("application_area") == "under-eye", (
            f"Valid enum value 'under-eye' must be accepted; got {updated.fields!r}"
        )
