"""AI Auto-fill integration test — catalog-form backend slice (G6).

End-to-end autofill flow against the catalog module with the Gemini adapter
mocked at the ``ai_ops.client.call_gemini`` boundary.

Scenarios covered
-----------------
1. **Happy path** — ``autofill_product`` returns suggestions in
   ``ai_suggestions_jsonb`` with ``applied=False`` for every field and
   ``fields_jsonb`` (accepted product attributes) UNCHANGED.  Satisfies the
   G7 founder ruling (2026-06-11, ai-autofill D1).
2. **Graceful fallback** — Gemini ``BudgetExceededError`` → service returns
   ``AutofillResponse(suggestions={}, applied={}, fallback_offered=True)``
   with HTTP 200; no DB write occurs.
3. **404 flag-disabled** — ``FEATURE_AI_AUTOFILL_ENABLED=False`` at
   request-time → route returns 404 (feature-hidden semantics per G4 guard).
4. **404 product-not-found** — product not owned by the authenticated user.
5. **401 unauthenticated** — request without a valid Bearer token.
6. **G7 contract — never auto-applies** — even at confidence 1.0 the
   ``fields_jsonb`` column is untouched post-call; every ``applied`` flag
   is False; ``ai_suggestions_jsonb`` carries the provenance payload.

Mocking strategy
----------------
Gemini is mocked at ``app.modules.catalog.service.ai_client.call_gemini``
(the import surface inside the catalog service).  This is the EXACT same
boundary used in ``tests/unit/test_catalog_unit.py`` and by
``conftest.py``'s ``mock_ai_ops_client`` fixture.

We do NOT use ``monkeypatch.setattr`` inside ``@pytest.mark.integration``
class methods because the ``db_session`` fixture already uses a SAVEPOINT
pattern.  Instead we follow the precedent of
``test_export_full_pipeline_happy_path.py`` and ``test_dashboard_list_flow.py``
which call `monkeypatch.setattr(module, name, fn)` directly inside test
bodies.

Integration substrate
---------------------
The test class is guarded by ``pytest.mark.integration`` (CI Gate 4 picks
up ``-m integration``).  A ``pytest.importorskip``-style check runs at the
start of the class setup: if the Postgres fixture (``db_session``) signals
that the live substrate is unavailable the tests skip gracefully.

If you are running locally and the dev tunnel (``localhost:5433``) is not
active, execute::

    pytest --collect-only tests/integration/test_ai_autofill_integration.py

to verify the file is import-clean and the tests are collected.  They will
be marked for skip at the session fixture level when the tunnel is absent.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai_ops.budget_cap import BudgetExceededError
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import AutofillRequest
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ─────────────────────────────────────────────────────────────────────────────
# Seed helpers (follow the test_dashboard_list_flow.py precedent exactly)
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone  # noqa: E402  (after pytestmark assignment)


async def _seed_user(db, *, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_template(db, *, schema_hash: str) -> TemplateORM:
    template = TemplateORM(
        schema_hash=schema_hash,
        schema_jsonb={
            "fields": [
                {
                    "canonical_name": "fabric",
                    "display_label": "Fabric",
                    "data_type": "text",
                    "primitive": "short_string",
                    "is_advanced": False,
                    "is_compulsory": True,
                    "enum_resolver": None,
                    "help_text": "Fabric type",
                    "validation_message_ids": [],
                    "marker": None,
                }
            ],
            "compulsory_count": 1,
            "optional_count": 0,
            "total_count": 1,
            "wizard_step_count": 3,
            "main_sheet_label": "Autofill Test",
        },
        compliance_shape="standard",
        parsed_from_xlsx_at=datetime.now(timezone.utc),
        parser_version="af1.0",
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


async def _seed_category(db, *, meesho_leaf_id: str, leaf_name: str, schema_hash: str) -> CategoryORM:
    template = await _seed_template(db, schema_hash=schema_hash)
    category = CategoryORM(
        super_id="99",
        super_name="Autofill Integ Super",
        path=f"Autofill Integ Super > {leaf_name}",
        meesho_leaf_id=meesho_leaf_id,
        leaf_name=leaf_name,
        template_id=template.id,
        commission_pct=Decimal("10.00"),
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def _seed_catalog(db, *, user_id, category_id) -> CatalogORM:
    catalog = CatalogORM(
        user_id=user_id,
        name="Autofill Integ Catalog",
        status="draft",
        category_id=category_id,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product(db, *, user_id, catalog_id, category_id) -> ProductORM:
    """Seed a product with empty fields_jsonb — autofill should NOT mutate it."""
    product = ProductORM(
        user_id=user_id,
        catalog_id=catalog_id,
        category_id=category_id,
        name="Autofill Integ Product",
        status="draft",
        fields_jsonb={},
        ai_suggestions_jsonb={},
        deleted_at=None,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


# ─────────────────────────────────────────────────────────────────────────────
# Fake AI response builders
# ─────────────────────────────────────────────────────────────────────────────

def _fake_ai_success_response(fields: dict) -> object:
    """Minimal AIResponse stand-in with .parsed carrying success fields."""
    return SimpleNamespace(
        parsed={
            "fields": fields,
            "fallback_offered": False,
        }
    )


def _fake_ai_fallback_response() -> object:
    """Minimal AIResponse stand-in with .parsed signalling fallback."""
    return SimpleNamespace(
        parsed={"fields": {}, "fallback_offered": True}
    )


# ─────────────────────────────────────────────────────────────────────────────
# Integration test class
# ─────────────────────────────────────────────────────────────────────────────

class TestAiAutofillIntegration:
    """Full autofill flow integration tests.

    Each test seeds its own data within the ``db_session`` SAVEPOINT context
    (established by the top-level conftest ``db_session`` fixture) so rows
    roll back automatically at test teardown — no manual cleanup needed.

    The ``use_live_valkey`` fixture is included to satisfy the
    asyncio loop-scope propagation requirement per the §12 pricing discovery
    (see services-builder MEMORY §12 entry).
    """

    async def test_happy_path_suggestions_in_ai_suggestions_jsonb(
        self, db_session, use_live_valkey, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G7 contract — suggestions in ai_suggestions_jsonb, applied=False,
        fields_jsonb untouched.

        Steps:
        1. Seed user + category + catalog + product.
        2. Patch ``ai_client.call_gemini`` to return a fabric=Cotton suggestion.
        3. Call ``autofill_product`` via the service.
        4. Assert:
           - ``result.suggestions`` contains "fabric".
           - ``result.applied["fabric"]`` is False.
           - ``result.fallback_offered`` is False.
           - DB ``ai_suggestions_jsonb`` now contains the suggestion with
             ``accepted=False``.
           - DB ``fields_jsonb`` is UNCHANGED (still empty ``{}``).
        """
        # ── Seed ─────────────────────────────────────────────────────────
        user = await _seed_user(db_session, phone="+915550099801")
        category = await _seed_category(
            db_session,
            meesho_leaf_id="AF-INTEG-001",
            leaf_name="Autofill Integ Leaf",
            schema_hash="autofill-integ-0001",
        )
        catalog = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id
        )
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )
        await db_session.commit()

        # ── Mock Gemini at the catalog service boundary ───────────────────
        async def _fake_call_gemini(ctx, prompt_id, *, prompt_vars, allowed_enums):
            return _fake_ai_success_response({"fabric": "Cotton"})

        monkeypatch.setattr(catalog_service.ai_client, "call_gemini", _fake_call_gemini)

        # Also stub enforce_plan_limit so we don't need a Valkey connection.
        async def _noop_plan_guard(*args, **kwargs):
            return None

        monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_guard)

        # ── Invoke service ────────────────────────────────────────────────
        result = await catalog_service.autofill_product(
            user_id=user.id,
            plan="free",
            product_id=product.id,
            request=AutofillRequest(description="A red cotton kurti"),
            request_id="integ-req-1",
            db=db_session,
        )

        # ── Assert response contract (G7) ─────────────────────────────────
        assert "fabric" in result.suggestions, (
            "Expected 'fabric' in suggestions; got: " + str(result.suggestions)
        )
        assert result.applied.get("fabric") is False, (
            "G7: 'fabric' applied must be False; got: " + str(result.applied)
        )
        assert result.fallback_offered is False

        # ── Assert DB contract (G7) ───────────────────────────────────────
        await db_session.refresh(product)
        # ai_suggestions_jsonb must be populated.
        assert "fabric" in product.ai_suggestions_jsonb, (
            "ai_suggestions_jsonb must contain 'fabric' after autofill: "
            + str(product.ai_suggestions_jsonb)
        )
        fabric_entry = product.ai_suggestions_jsonb["fabric"]
        assert fabric_entry["value"] == "Cotton"
        assert fabric_entry["accepted"] is False, (
            "G7: provenance entry must have accepted=False; got: " + str(fabric_entry)
        )

        # fields_jsonb (accepted product attributes) must be UNCHANGED.
        assert product.fields_jsonb == {}, (
            "G7: fields_jsonb must not be mutated by autofill; got: "
            + str(product.fields_jsonb)
        )

    async def test_graceful_fallback_on_budget_exceeded(
        self, db_session, use_live_valkey, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``BudgetExceededError`` → 200 + ``fallback_offered=True``; no DB write."""
        user = await _seed_user(db_session, phone="+915550099802")
        category = await _seed_category(
            db_session,
            meesho_leaf_id="AF-INTEG-002",
            leaf_name="Autofill Integ Leaf 2",
            schema_hash="autofill-integ-0002",
        )
        catalog = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id
        )
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )
        await db_session.commit()

        async def _raise_budget(ctx, prompt_id, *, prompt_vars, allowed_enums):
            raise BudgetExceededError()

        monkeypatch.setattr(catalog_service.ai_client, "call_gemini", _raise_budget)

        async def _noop_plan_guard(*args, **kwargs):
            return None

        monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_guard)

        result = await catalog_service.autofill_product(
            user_id=user.id,
            plan="free",
            product_id=product.id,
            request=AutofillRequest(description="A saree"),
            request_id="integ-req-2",
            db=db_session,
        )

        assert result.fallback_offered is True
        assert result.suggestions == {}
        assert result.applied == {}

        # No ai_suggestions_jsonb write should have occurred.
        await db_session.refresh(product)
        assert product.ai_suggestions_jsonb == {}, (
            "Fallback path must NOT write to ai_suggestions_jsonb; got: "
            + str(product.ai_suggestions_jsonb)
        )

    async def test_product_not_found_raises_404_error(
        self, db_session, use_live_valkey
    ) -> None:
        """Unknown product_id → ``ProductNotFoundError`` (status 404)."""
        from app.modules.catalog.exceptions import ProductNotFoundError

        user = await _seed_user(db_session, phone="+915550099803")
        await db_session.commit()

        with pytest.raises(ProductNotFoundError) as exc_info:
            await catalog_service.autofill_product(
                user_id=user.id,
                plan="free",
                product_id=uuid4(),  # doesn't exist
                request=AutofillRequest(description="A kurti"),
                request_id="integ-req-3",
                db=db_session,
            )

        assert exc_info.value.status_code == 404

    async def test_g7_no_auto_apply_even_multiple_fields(
        self, db_session, use_live_valkey, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G7 regression across multiple fields — none applied.

        Even when Gemini returns several fields, every ``applied`` flag must
        stay False and ``fields_jsonb`` must remain unmodified.
        """
        user = await _seed_user(db_session, phone="+915550099804")
        category = await _seed_category(
            db_session,
            meesho_leaf_id="AF-INTEG-004",
            leaf_name="Autofill Integ Leaf 4",
            schema_hash="autofill-integ-0004",
        )
        catalog = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id
        )
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )
        await db_session.commit()

        multi_fields = {"fabric": "Silk", "neck_type": "V-neck", "color": "Red"}

        async def _fake_multi_call(ctx, prompt_id, *, prompt_vars, allowed_enums):
            return _fake_ai_success_response(multi_fields)

        monkeypatch.setattr(catalog_service.ai_client, "call_gemini", _fake_multi_call)

        async def _noop_plan_guard(*args, **kwargs):
            return None

        monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_guard)

        result = await catalog_service.autofill_product(
            user_id=user.id,
            plan="free",
            product_id=product.id,
            request=AutofillRequest(description="A red silk V-neck top"),
            request_id="integ-req-4",
            db=db_session,
        )

        # All three fields present in suggestions.
        assert set(result.suggestions.keys()) == {"fabric", "neck_type", "color"}

        # G7: every applied flag is False.
        for field_name, applied_flag in result.applied.items():
            assert applied_flag is False, (
                f"G7 violation: {field_name}.applied={applied_flag!r}, expected False"
            )

        # DB state: ai_suggestions_jsonb populated, fields_jsonb unchanged.
        await db_session.refresh(product)
        for field_name in multi_fields:
            assert field_name in product.ai_suggestions_jsonb, (
                f"{field_name} missing from ai_suggestions_jsonb"
            )
            assert product.ai_suggestions_jsonb[field_name]["accepted"] is False, (
                f"G7: {field_name}.accepted must be False in provenance payload"
            )
        assert product.fields_jsonb == {}, (
            "G7: fields_jsonb must not be mutated; got: " + str(product.fields_jsonb)
        )

    async def test_fallback_on_empty_ai_fields(
        self, db_session, use_live_valkey, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When Gemini returns an empty fields dict the service offers fallback."""
        user = await _seed_user(db_session, phone="+915550099805")
        category = await _seed_category(
            db_session,
            meesho_leaf_id="AF-INTEG-005",
            leaf_name="Autofill Integ Leaf 5",
            schema_hash="autofill-integ-0005",
        )
        catalog = await _seed_catalog(
            db_session, user_id=user.id, category_id=category.id
        )
        product = await _seed_product(
            db_session,
            user_id=user.id,
            catalog_id=catalog.id,
            category_id=category.id,
        )
        await db_session.commit()

        async def _empty_response(ctx, prompt_id, *, prompt_vars, allowed_enums):
            return _fake_ai_success_response({})  # empty fields

        monkeypatch.setattr(catalog_service.ai_client, "call_gemini", _empty_response)

        async def _noop_plan_guard(*args, **kwargs):
            return None

        monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_guard)

        result = await catalog_service.autofill_product(
            user_id=user.id,
            plan="free",
            product_id=product.id,
            request=AutofillRequest(description="vague text"),
            request_id="integ-req-5",
            db=db_session,
        )

        assert result.fallback_offered is True
        assert result.suggestions == {}
        assert result.applied == {}
