"""Service-layer unit tests for the catalog-form backend slice.

Covers (all pure-unit — external systems mocked, no DB/Valkey/Gemini):

* G7 regression — ``autofill_product`` writes ONLY to ``ai_suggestions_jsonb``
  and NEVER auto-applies, even at confidence 1.0 (FOUNDER RULING 2026-06-11,
  ai-autofill D1).
* G1/G2 — ``FEATURE_CATALOG_FORM_ENABLED`` + ``FEATURE_AI_AUTOFILL_ENABLED``
  defaults exist on the ``Settings`` model.
* ``assert_product_ownership`` 404 semantics (§10.C verbatim contract).

These tests stub the catalog service's collaborators directly via monkeypatch
so the autofill flow exercises ONLY the suggestion-construction + persistence
branch under test — no Postgres, no Valkey, no Gemini SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest

from app.modules.catalog import service as catalog_service
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.catalog.schemas import AutofillRequest

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# Lightweight stand-ins (the service only reads ``.parsed`` off the AI result
# and a handful of attributes off the product row).
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class _FakeAIResponse:
    parsed: dict[str, Any]


@dataclass
class _FakeProductRow:
    category_id: Any
    fields_jsonb: dict[str, Any]


class _Sentinel:
    """Marker DB object — never touched (all DB calls are stubbed)."""


def _install_autofill_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ai_fields: dict[str, Any],
    captured: dict[str, Any],
) -> None:
    """Wire every collaborator ``autofill_product`` calls so the flow runs
    end-to-end in-memory and records what it would have persisted.

    ``captured`` accumulates the calls to the two write surfaces so the test
    can assert that ONLY ``update_ai_suggestions_jsonb`` fires.
    """
    captured.setdefault("ai_suggestions_writes", [])
    captured.setdefault("fields_jsonb_writes", [])

    async def _assert_owned(product_id, user_id, db):  # noqa: ANN001
        return None

    async def _enforce(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _find_by_id(db, user_id, product_id):  # noqa: ANN001
        return _FakeProductRow(category_id=uuid4(), fields_jsonb={})

    async def _fetch_schema(category_id, db):  # noqa: ANN001
        return {"fields": []}

    async def _resolve_enums(schema, category_id, db):  # noqa: ANN001
        return {}

    async def _call_gemini(ctx, prompt_id, *, prompt_vars, allowed_enums):  # noqa: ANN001
        return _FakeAIResponse(parsed={"fields": ai_fields, "fallback_offered": False})

    async def _update_ai_suggestions(db, user_id, product_id, payload):  # noqa: ANN001
        captured["ai_suggestions_writes"].append(payload)
        return None

    async def _update_fields(db, user_id, product_id, patch):  # noqa: ANN001
        captured["fields_jsonb_writes"].append(patch)
        return None

    monkeypatch.setattr(catalog_service, "assert_product_ownership", _assert_owned)
    monkeypatch.setattr(catalog_service, "enforce_plan_limit", _enforce)
    monkeypatch.setattr(catalog_service.catalog_repo, "find_by_id", _find_by_id)
    monkeypatch.setattr(catalog_service.category_service, "fetch_schema", _fetch_schema)
    monkeypatch.setattr(catalog_service, "_resolve_allowed_enums", _resolve_enums)
    monkeypatch.setattr(catalog_service.ai_client, "call_gemini", _call_gemini)
    monkeypatch.setattr(
        catalog_service.catalog_repo, "update_ai_suggestions_jsonb", _update_ai_suggestions
    )
    monkeypatch.setattr(
        catalog_service.catalog_repo, "update_fields_jsonb", _update_fields
    )


# ─────────────────────────────────────────────────────────────────────────────
# G7 — NO auto-apply (the regression guard)
# ─────────────────────────────────────────────────────────────────────────────
class TestAutofillNeverAutoApplies:
    async def test_suggestions_persisted_but_fields_never_mutated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}
        _install_autofill_stubs(
            monkeypatch,
            ai_fields={"fabric": "Cotton", "neck_type": "Round"},
            captured=captured,
        )

        resp = await catalog_service.autofill_product(
            user_id=uuid4(),
            plan="free",
            product_id=uuid4(),
            request=AutofillRequest(description="A red cotton kurti"),
            request_id="req-1",
            db=_Sentinel(),
        )

        # Suggestions returned + persisted to ai_suggestions_jsonb.
        assert set(resp.suggestions.keys()) == {"fabric", "neck_type"}
        assert len(captured["ai_suggestions_writes"]) == 1
        persisted = captured["ai_suggestions_writes"][0]
        assert set(persisted.keys()) == {"fabric", "neck_type"}

        # CRITICAL: fields_jsonb (accepted attributes) is NEVER written.
        assert captured["fields_jsonb_writes"] == []

        # Every applied flag is False — nothing auto-applied.
        assert resp.applied == {"fabric": False, "neck_type": False}
        # And the persisted provenance marks accepted=False for each.
        assert all(entry["accepted"] is False for entry in persisted.values())
        assert resp.fallback_offered is False

    async def test_no_auto_apply_even_at_confidence_floor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Force the default confidence to 1.0 — the old code would have
        auto-applied above the 0.85 floor.  Post-ruling it must NOT."""
        monkeypatch.setattr(catalog_service, "_DEFAULT_AUTOFILL_CONFIDENCE", 1.0)
        captured: dict[str, Any] = {}
        _install_autofill_stubs(
            monkeypatch,
            ai_fields={"fabric": "Silk"},
            captured=captured,
        )

        resp = await catalog_service.autofill_product(
            user_id=uuid4(),
            plan="free",
            product_id=uuid4(),
            request=AutofillRequest(description="A silk saree"),
            request_id="req-2",
            db=_Sentinel(),
        )

        # Even at confidence 1.0: no fields_jsonb write, applied stays False.
        assert captured["fields_jsonb_writes"] == []
        assert resp.applied == {"fabric": False}
        # Confidence signal is STILL emitted into provenance (1.0 here).
        persisted = captured["ai_suggestions_writes"][0]
        assert persisted["fabric"]["confidence"] == 1.0
        assert persisted["fabric"]["accepted"] is False

    async def test_auto_apply_constant_removed(self) -> None:
        """The dead ``_AUTO_APPLY_CONFIDENCE_FLOOR`` constant is gone."""
        assert not hasattr(catalog_service, "_AUTO_APPLY_CONFIDENCE_FLOOR")

    async def test_empty_ai_fields_offers_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}
        _install_autofill_stubs(monkeypatch, ai_fields={}, captured=captured)

        resp = await catalog_service.autofill_product(
            user_id=uuid4(),
            plan="free",
            product_id=uuid4(),
            request=AutofillRequest(description="vague text"),
            request_id="req-3",
            db=_Sentinel(),
        )

        assert resp.fallback_offered is True
        assert resp.suggestions == {}
        assert captured["fields_jsonb_writes"] == []
        assert captured["ai_suggestions_writes"] == []


# ─────────────────────────────────────────────────────────────────────────────
# G1 / G2 — feature flag defaults on Settings
# ─────────────────────────────────────────────────────────────────────────────
class TestFeatureFlagDefaults:
    def test_catalog_form_flag_default_true(self) -> None:
        from app.shared.config import settings

        assert hasattr(settings, "FEATURE_CATALOG_FORM_ENABLED")
        assert settings.FEATURE_CATALOG_FORM_ENABLED is True

    def test_ai_autofill_flag_default_true(self) -> None:
        from app.shared.config import settings

        assert hasattr(settings, "FEATURE_AI_AUTOFILL_ENABLED")
        assert settings.FEATURE_AI_AUTOFILL_ENABLED is True

    def test_flags_are_bool_typed(self) -> None:
        from app.shared.config import Settings

        fields = Settings.model_fields
        assert fields["FEATURE_CATALOG_FORM_ENABLED"].annotation is bool
        assert fields["FEATURE_AI_AUTOFILL_ENABLED"].annotation is bool


# ─────────────────────────────────────────────────────────────────────────────
# assert_product_ownership — 404 semantics (§10.C verbatim contract)
# ─────────────────────────────────────────────────────────────────────────────
class TestAssertProductOwnership:
    async def test_missing_row_raises_product_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _find_none(db, user_id, product_id):  # noqa: ANN001
            return None

        monkeypatch.setattr(catalog_service.catalog_repo, "find_by_id", _find_none)

        with pytest.raises(ProductNotFoundError) as exc_info:
            await catalog_service.assert_product_ownership(
                product_id=uuid4(), user_id=uuid4(), db=_Sentinel()
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "catalog.product_not_found"

    async def test_owned_row_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _find_row(db, user_id, product_id):  # noqa: ANN001
            return _FakeProductRow(category_id=uuid4(), fields_jsonb={})

        monkeypatch.setattr(catalog_service.catalog_repo, "find_by_id", _find_row)

        result = await catalog_service.assert_product_ownership(
            product_id=uuid4(), user_id=uuid4(), db=_Sentinel()
        )
        assert result is None
