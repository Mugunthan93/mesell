"""Catalog-module unit tests — §10.J units 1-5.

Per BACKEND_ARCHITECTURE.md §10.J:

  TestOwnershipEnforcement      — 3 methods (non-existent / cross-tenant / soft-deleted)
  TestSchemaDrivenValidation    — 5 methods (unknown key / text overflow /
                                  static-enum miss / category-enum miss / multi-violation)
  TestAutofillGracefulFallback  — 1 method (BudgetExceededError → 200 + fallback_offered)
  TestAutosaveDraftUpsert       — 3 methods (autosave writes draft / no-autosave skips /
                                  second autosave increments)
  TestPlanGuardEnforcement      — 1 method (count=100 raises PlanLimitExceededError → 402)

Tests run against the ephemeral test DB (top-level conftest's
``db_session``; reset per test).  They DO use the actual
:func:`category.service.fetch_schema` (via the autouse Valkey-cache
bypass in the catalog conftest) so the schema envelope is exercised
end-to-end up to the §5A.B contract.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.modules.catalog import repository as catalog_repo
from app.modules.catalog import service as catalog_service
from app.modules.catalog.exceptions import (
    ProductNotFoundError,
    ValidationFailedError,
)
from app.modules.catalog.schemas import (
    AutofillRequest,
    CreateProductRequest,
    PatchProductRequest,
)
from app.core.plan_guard import PlanLimitExceededError
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.product_draft import ProductDraft as ProductDraftORM


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_product(
    db, user_id, catalog_id, category_id, *, deleted: bool = False,
    fields_jsonb=None
):
    """Insert a product row directly via ORM — bypasses service for fixtures.

    Used where the test wants a specific ORM state (soft-deleted,
    pre-populated fields) without re-running the full create flow.
    """
    product = ProductORM(
        user_id=user_id,
        catalog_id=catalog_id,
        category_id=category_id,
        name="Test Product",
        status="draft",
        fields_jsonb=fields_jsonb or {},
        ai_suggestions_jsonb={},
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def _seed_catalog(db, user_id):
    catalog = CatalogORM(user_id=user_id, name="Test Catalog", status="draft")
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Unit 1 — Ownership enforcement
# ─────────────────────────────────────────────────────────────────────────────
class TestOwnershipEnforcement:
    """``assert_product_ownership`` MUST raise ProductNotFoundError for:

    (a) non-existent product,
    (b) product owned by another user,
    (c) soft-deleted product.

    All three cases collapse to the same exception per §10 leak-protection.
    """

    async def test_raises_for_non_existent_product(
        self, db, user, beauty_category, use_live_valkey
    ):
        """No row → ProductNotFoundError (404 / catalog.product.not_found)."""
        bogus_id = uuid.uuid4()
        with pytest.raises(ProductNotFoundError):
            await catalog_service.assert_product_ownership(
                bogus_id, user.id, db=db
            )

    async def test_raises_for_cross_tenant_product(
        self, db, user, other_user, beauty_category, use_live_valkey
    ):
        """Product owned by user A → ProductNotFoundError when user B asks.

        Verifies structural M6 enforcement — image/pricing/dashboard/export
        will see the same exception bubble up.
        """
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(
            db, user.id, catalog.id, beauty_category.id
        )
        with pytest.raises(ProductNotFoundError):
            await catalog_service.assert_product_ownership(
                product.id, other_user.id, db=db
            )

    async def test_raises_for_soft_deleted_product(
        self, db, user, beauty_category, use_live_valkey
    ):
        """``deleted_at IS NOT NULL`` → ProductNotFoundError.

        Verifies the §10.B.5 + §10 leak-protection rule: deleting a
        product makes it invisible to its OWNER too (the seller sees
        404 if they re-visit the URL).
        """
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(
            db, user.id, catalog.id, beauty_category.id, deleted=True
        )
        with pytest.raises(ProductNotFoundError):
            await catalog_service.assert_product_ownership(
                product.id, user.id, db=db
            )


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Unit 2 — Schema-driven validation
# ─────────────────────────────────────────────────────────────────────────────
class TestSchemaDrivenValidation:
    """``patch_product`` MUST raise ValidationFailedError with the correct
    validation_message_id for the 5 documented violation classes.
    """

    async def test_unknown_canonical_name_raises_unknown_key(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        req = PatchProductRequest(fields={"definitely_not_a_field": "x"})
        with pytest.raises(ValidationFailedError) as exc:
            await catalog_service.patch_product(
                user.id, product.id, req, is_autosave=False, db=db
            )
        assert exc.value.validation_message_id == "validation.fields.unknown_key"

    async def test_text_overflow_raises_too_long(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        # product_name is text_short (≤100 chars).
        too_long = "x" * 101
        req = PatchProductRequest(fields={"product_name": too_long})
        with pytest.raises(ValidationFailedError) as exc:
            await catalog_service.patch_product(
                user.id, product.id, req, is_autosave=False, db=db
            )
        assert exc.value.validation_message_id == "validation.product_name.too_long"

    async def test_static_enum_miss_raises_invalid_enum_value(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        # application_area is static enum: ["under-eye", "eyelid", "full-face"].
        req = PatchProductRequest(fields={"application_area": "tentacles"})
        with pytest.raises(ValidationFailedError) as exc:
            await catalog_service.patch_product(
                user.id, product.id, req, is_autosave=False, db=db
            )
        assert exc.value.validation_message_id == (
            "validation.application_area.invalid_enum_value"
        )

    async def test_category_enum_miss_raises_invalid_enum_value(
        self, db, user, beauty_category, beauty_profile, monkeypatch, use_live_valkey
    ):
        """Per §5A.E ``enum_resolver=category`` — service resolves the
        allowed list via :func:`category.service.get_field_enum`; values
        outside that list raise the same enum-violation id.

        The Eye-Serum schema does not carry a category-resolved enum,
        so this test injects a schema with one via monkeypatching
        :func:`category.service.fetch_schema`.
        """
        from app.modules.category import service as category_service_mod

        async def _fake_fetch_schema(category_id, db=None, **_kw):
            return {
                "fields": [
                    {
                        "name": "Brand",
                        "canonical_name": "brand",
                        "marker": "compulsory",
                        "data_type": "dropdown",
                        "primitive": "dropdown_category",
                        "is_advanced": False,
                        "enum_resolver": "category",
                    }
                ],
                "compulsory_count": 1,
                "optional_count": 0,
                "total_count": 1,
                "wizard_step_count": 1,
                "main_sheet_label": "Brand Test",
                "compliance_shape": "standard",
                "super_id": "19",
            }

        async def _fake_get_field_enum(category_id, field_name, db=None, **_kw):
            return {
                "enum_entries": [
                    {"canonical": "Nivea", "meesho": "nivea", "labels": {"en": "Nivea"}},
                    {"canonical": "Loreal", "meesho": "loreal", "labels": {"en": "Loreal"}},
                ],
                "total": 2,
                "truncated": False,
            }

        monkeypatch.setattr(category_service_mod, "fetch_schema", _fake_fetch_schema)
        monkeypatch.setattr(category_service_mod, "get_field_enum", _fake_get_field_enum)

        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        req = PatchProductRequest(fields={"brand": "NotARealBrand"})
        with pytest.raises(ValidationFailedError) as exc:
            await catalog_service.patch_product(
                user.id, product.id, req, is_autosave=False, db=db
            )
        assert exc.value.validation_message_id == (
            "validation.brand.invalid_enum_value"
        )

    async def test_multi_violation_first_drives_envelope_rest_in_details(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        """When multiple fields fail, envelope's validation_message_id
        carries the FIRST violation and ``details`` carries the rest.
        """
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        req = PatchProductRequest(
            fields={
                "product_name": "x" * 101,                 # text overflow
                "application_area": "tentacles",            # enum miss
                "totally_unknown_field": "y",               # unknown key
            }
        )
        with pytest.raises(ValidationFailedError) as exc:
            await catalog_service.patch_product(
                user.id, product.id, req, is_autosave=False, db=db
            )
        # Insertion order is preserved in Python 3.7+ dicts, so
        # product_name should be first.
        assert exc.value.validation_message_id == "validation.product_name.too_long"
        # The trailing 2 violations must show up in details.
        assert len(exc.value.details) == 3, exc.value.details
        joined = " | ".join(exc.value.details)
        assert "application_area" in joined
        assert "totally_unknown_field" in joined


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Unit 3 — Auto-fill graceful fallback
# ─────────────────────────────────────────────────────────────────────────────
class TestAutofillGracefulFallback:
    """``autofill_product`` returns ``AutofillResponse(suggestions={},
    applied={}, fallback_offered=True)`` with HTTP 200 when
    :func:`ai_ops.client.call_gemini` raises ``BudgetExceededError``.

    Verifies the §9.B.1 + §6A.F precedent applies symmetrically to §10.
    """

    async def test_budget_exceeded_returns_fallback_response(
        self,
        db,
        user,
        beauty_category,
        beauty_profile,
        stub_call_gemini_budget_exceeded,
        use_live_valkey,
    ):
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        req = AutofillRequest(description="A peptide-based eye serum.")
        result = await catalog_service.autofill_product(
            user.id,
            "free",
            product.id,
            req,
            request_id="test-req-id",
            db=db,
        )
        assert result.fallback_offered is True
        assert result.suggestions == {}
        assert result.applied == {}


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Unit 4 — Autosave draft upsert
# ─────────────────────────────────────────────────────────────────────────────
class TestAutosaveDraftUpsert:
    """``patch_product`` MUST upsert ``product_drafts`` when
    ``is_autosave=True`` and MUST NOT touch the table when
    ``is_autosave=False``.  Second autosave on the same product MUST
    increment ``autosave_count``.

    Per master ruling D1, ``autosave_count`` lives inside the
    ``draft_jsonb`` wrapper envelope.
    """

    async def test_autosave_writes_through_to_product_drafts(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        req = PatchProductRequest(fields={"product_name": "Saved Title"})
        await catalog_service.patch_product(
            user.id, product.id, req, is_autosave=True, db=db
        )
        # Read the draft row directly via the ORM.
        from sqlalchemy import select
        row = (await db.execute(
            select(ProductDraftORM).where(
                ProductDraftORM.user_id == user.id,
                ProductDraftORM.product_id == product.id,
            )
        )).scalar_one_or_none()
        assert row is not None, "Expected a product_drafts row after autosave PATCH"
        fields, count = catalog_repo._unwrap_draft_payload(row.draft_jsonb)
        assert fields.get("product_name") == "Saved Title"
        assert count == 1

    async def test_non_autosave_does_not_write_draft(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)
        req = PatchProductRequest(fields={"product_name": "Manual Save Title"})
        await catalog_service.patch_product(
            user.id, product.id, req, is_autosave=False, db=db
        )
        from sqlalchemy import select
        row = (await db.execute(
            select(ProductDraftORM).where(
                ProductDraftORM.user_id == user.id,
                ProductDraftORM.product_id == product.id,
            )
        )).scalar_one_or_none()
        assert row is None, (
            "Manual save (is_autosave=False) must NOT touch product_drafts."
        )

    async def test_second_autosave_increments_count_and_replaces_fields(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)

        await catalog_service.patch_product(
            user.id,
            product.id,
            PatchProductRequest(fields={"product_name": "v1"}),
            is_autosave=True,
            db=db,
        )
        await catalog_service.patch_product(
            user.id,
            product.id,
            PatchProductRequest(fields={"product_name": "v2"}),
            is_autosave=True,
            db=db,
        )

        from sqlalchemy import select
        row = (await db.execute(
            select(ProductDraftORM).where(
                ProductDraftORM.user_id == user.id,
                ProductDraftORM.product_id == product.id,
            )
        )).scalar_one_or_none()
        assert row is not None
        fields, count = catalog_repo._unwrap_draft_payload(row.draft_jsonb)
        # Second autosave snapshot is taken AFTER the JSONB merge — so
        # the snapshot reflects the MERGED state, which retains the v2
        # value (the merge replaced v1 with v2 at the products row).
        assert fields.get("product_name") == "v2"
        assert count == 2, (
            f"Expected autosave_count to increment to 2, got {count}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Unit 5 — Plan-guard enforcement (product_count)
# ─────────────────────────────────────────────────────────────────────────────
class TestPlanGuardEnforcement:
    """``create_product`` MUST raise PlanLimitExceededError (402) when the
    plan_guard product_count gate fires — BEFORE any DB write.

    We exercise the gate by inserting 100 active products via direct ORM
    bypass, then attempting the 101st via the service.
    """

    async def test_plan_limit_raised_when_at_100_active_products(
        self, db, user, beauty_category, beauty_profile, use_live_valkey
    ):
        catalog = await _seed_catalog(db, user.id)
        # Seed 100 active products owned by this user.
        for i in range(100):
            await _seed_product(
                db,
                user.id,
                catalog.id,
                beauty_category.id,
                fields_jsonb={"index": i},
            )
        # Sanity check repository count.
        count = await catalog_repo.count_active_products(db, user.id)
        assert count == 100, f"Expected 100 active products, got {count}"

        req = CreateProductRequest(category_id=beauty_category.id, name="overflow")
        with pytest.raises(PlanLimitExceededError) as exc:
            await catalog_service.create_product(
                user.id, "free", req, db=db
            )
        assert exc.value.status_code == 402
        # No new row was written — count still 100.
        count_after = await catalog_repo.count_active_products(db, user.id)
        assert count_after == 100, (
            f"plan_guard must fail BEFORE any DB write; got {count_after}"
        )
