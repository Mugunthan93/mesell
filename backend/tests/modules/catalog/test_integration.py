"""Catalog-module integration tests — §10.J integration 1-3.

Per BACKEND_ARCHITECTURE.md §10.J:

  TestFullProductLifecycle           — create → autofill → autosave PATCH →
                                       manual PATCH (status=ready) → preview.
  TestDraftRecoveryAfterSimulatedClose — 3 autosave PATCHs → GET /draft → 200;
                                       fresh product → 204.
  TestCrossModuleOwnershipAssertion   — image-module-call shape;
                                       cross-tenant raises ProductNotFoundError.

These tests run against the in-memory FastAPI test client (the top-level
``client``/``auth_client`` fixtures) backed by the ephemeral test DB.

Integration tests SKIP gracefully when the ephemeral test infra is not
available (DB on :5432 or Valkey on :6379) — they emit
``pytest.skip`` so CI can show a clean signal in environments where the
tunnels are not connected.  This matches the §8 customer integration
pattern (memory D3).
"""

from __future__ import annotations

import pytest

from app.modules.catalog import service as catalog_service
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.catalog.schemas import (
    AutofillRequest,
    CreateProductRequest,
    PatchProductRequest,
)


pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Integration 1 — Full product lifecycle
# ─────────────────────────────────────────────────────────────────────────────
class TestFullProductLifecycle:
    """End-to-end: create → autofill → PATCH autosave → PATCH manual (ready)
    → preview.  Verifies the 6 endpoints compose without contract drift.

    Uses the stub :func:`ai_ops.client.call_gemini` from conftest so the
    Auto-fill step is deterministic.
    """

    async def test_full_lifecycle(
        self,
        db,
        user,
        beauty_category,
        beauty_profile,
        stub_call_gemini,
        use_live_valkey,
    ):
        # ── 1. create_product ───────────────────────────────────────────
        create_req = CreateProductRequest(
            category_id=beauty_category.id, name="Glow Eye Serum"
        )
        product = await catalog_service.create_product(
            user.id, "free", create_req, db=db
        )
        assert product.status == "draft"
        assert product.name == "Glow Eye Serum"
        assert product.fields == {}

        # ── 2. autofill_product ─────────────────────────────────────────
        autofill_req = AutofillRequest(
            description="Lightweight peptide-based eye serum for puffiness."
        )
        autofill_result = await catalog_service.autofill_product(
            user.id, "free", product.id, autofill_req,
            request_id="lifecycle-1",
            db=db,
        )
        assert autofill_result.fallback_offered is False
        assert "product_name" in autofill_result.suggestions
        assert autofill_result.applied.get("product_name") is True

        # ── 3. PATCH autosave ───────────────────────────────────────────
        autosave_req = PatchProductRequest(
            fields={"product_description": "User-typed long description."}
        )
        await catalog_service.patch_product(
            user.id, product.id, autosave_req, is_autosave=True, db=db
        )

        # ── 4. PATCH manual (status=ready) ──────────────────────────────
        ready_req = PatchProductRequest(status="ready")
        ready_product = await catalog_service.patch_product(
            user.id, product.id, ready_req, is_autosave=False, db=db
        )
        assert ready_product.status == "ready", (
            "After autofill auto-applies compulsory fields, status=ready transition "
            "must succeed without further user input."
        )

        # ── 5. get_preview ──────────────────────────────────────────────
        preview = await catalog_service.get_preview(user.id, product.id, db=db)
        assert preview.status == "ready"
        # The 4 schema fields plus any preview-only synthesized rows.
        canonical_names = {f.canonical_name for f in preview.fields}
        assert {"product_name", "brand_name", "application_area"}.issubset(
            canonical_names
        )


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Integration 2 — Draft recovery after simulated close
# ─────────────────────────────────────────────────────────────────────────────
class TestDraftRecoveryAfterSimulatedClose:
    """3 autosave PATCHs → GET /draft → 200 with autosave_count=3.
    Fresh product (never autosaved) → 204.
    """

    async def test_3_autosaves_then_recover_returns_snapshot(
        self, db, user, beauty_category, beauty_profile
    ):
        # Create + 3 autosaves with different field values.
        create_req = CreateProductRequest(
            category_id=beauty_category.id, name="Test Product"
        )
        product = await catalog_service.create_product(
            user.id, "free", create_req, db=db
        )

        for i in range(1, 4):
            await catalog_service.patch_product(
                user.id,
                product.id,
                PatchProductRequest(fields={"product_name": f"draft-{i}"}),
                is_autosave=True,
                db=db,
            )

        draft = await catalog_service.get_draft(user.id, product.id, db=db)
        assert draft is not None, "Draft must exist after 3 autosaves"
        assert draft.autosave_count == 3, (
            f"Expected autosave_count=3, got {draft.autosave_count}"
        )
        assert draft.fields.get("product_name") == "draft-3", (
            "Latest autosave snapshot must reflect the most recent fields"
        )

    async def test_no_autosave_returns_none(
        self, db, user, beauty_category, beauty_profile
    ):
        """create_product without any subsequent autosave → get_draft None."""
        create_req = CreateProductRequest(
            category_id=beauty_category.id, name="Fresh Product"
        )
        product = await catalog_service.create_product(
            user.id, "free", create_req, db=db
        )
        draft = await catalog_service.get_draft(user.id, product.id, db=db)
        assert draft is None, (
            "Product without any autosave PATCH must have no draft snapshot."
        )


# ─────────────────────────────────────────────────────────────────────────────
# §10.J Integration 3 — Cross-module ownership assertion
# ─────────────────────────────────────────────────────────────────────────────
class TestCrossModuleOwnershipAssertion:
    """Simulates the image-module's call into
    :func:`catalog.service.assert_product_ownership`.

    The test lives in ``catalog/`` because catalog OWNS the seam (per §10),
    even though the consumer is ``image`` / ``pricing`` / ``dashboard`` /
    ``export``.  When this regresses, the consequence is a cross-tenant
    data leak — hence integration coverage.
    """

    async def test_assert_product_ownership_blocks_cross_tenant_call(
        self, db, user, other_user, beauty_category, beauty_profile
    ):
        # User A creates a product.
        create_req = CreateProductRequest(
            category_id=beauty_category.id, name="Tenant A Product"
        )
        product = await catalog_service.create_product(
            user.id, "free", create_req, db=db
        )

        # User B (other_user) tries to assert ownership — would happen
        # inside image.service before any product_images write.  Must
        # raise ProductNotFoundError.
        with pytest.raises(ProductNotFoundError):
            await catalog_service.assert_product_ownership(
                product.id, other_user.id, db=db
            )

        # And the owner CAN assert ownership without error — the gate
        # is symmetric (not "always 404", just "404 for non-owners").
        await catalog_service.assert_product_ownership(
            product.id, user.id, db=db
        )
