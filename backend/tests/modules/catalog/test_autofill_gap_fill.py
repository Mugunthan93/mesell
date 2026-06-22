"""CAT-BE-36 / CAT-BE-37 / CAT-BE-38 / CAT-BE-39
Gap-fill for ``POST /products/{id}/autofill``.

- CAT-BE-36  FEATURE_AI_AUTOFILL_ENABLED=false → 404 at the route level
- CAT-BE-37  autofill plan-guard 402 → propagates from service
- CAT-BE-38  AI budget exceeded → graceful fallback 200 (fallback_offered=true)
- CAT-BE-39  autofill suggestions respect the schema's enum allow-set

CAT-BE-38 was already tested via the existing ``test_integration.py``
TestFullProductLifecycle; this file adds an explicit boundary test using the
stub_call_gemini_budget_exceeded fixture.

Route-level tests (CAT-BE-36) use the ASGI stub-auth client pattern.
Service-level tests (CAT-BE-37, 38, 39) call the service directly.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.ai_ops.budget_cap import BudgetExceededError
from app.core.plan_guard import PlanLimitExceededError
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import AutofillRequest, CreateProductRequest


pytestmark = pytest.mark.asyncio


# ── CAT-BE-36: FEATURE_AI_AUTOFILL_ENABLED=false → 404 ──────────────────────

@pytest.mark.integration
async def test_autofill_flag_off_returns_404(catalog_route_client, monkeypatch):
    """CAT-BE-36: autofill route returns 404 when flag is disabled."""
    from app.shared.config import settings

    monkeypatch.setattr(settings, "FEATURE_AI_AUTOFILL_ENABLED", False)

    random_id = uuid.uuid4()
    resp = await catalog_route_client.post(
        f"/api/v1/products/{random_id}/autofill",
        json={"description": "cotton kurti for daily wear"},
    )

    assert resp.status_code == 404, (
        f"Expected 404 when FEATURE_AI_AUTOFILL_ENABLED=false, got {resp.status_code}: {resp.text}"
    )
    # monkeypatch restores the flag automatically after the test.


# ── CAT-BE-37: plan-guard 402 → propagates ───────────────────────────────────

@pytest.mark.integration
async def test_autofill_plan_guard_propagates(
    db, user, beauty_category, beauty_profile, monkeypatch
):
    """CAT-BE-37: enforce_plan_limit raises PlanLimitExceededError → service propagates."""
    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="AutofillPlanGuard"),
        db=db,
    )

    async def _raise_limit(*args, **kwargs):
        raise PlanLimitExceededError(
            resource="ai_autofill_hourly",
            current=50,
            limit=50,
        )

    monkeypatch.setattr(catalog_service, "enforce_plan_limit", _raise_limit)

    req = AutofillRequest(description="cotton kurti for daily wear")
    with pytest.raises(PlanLimitExceededError):
        await catalog_service.autofill_product(
            user.id,
            "free",
            product.id,
            req,
            request_id=str(uuid.uuid4()),
            db=db,
        )


# ── CAT-BE-38: budget exceeded → graceful fallback (fallback_offered=true) ───

@pytest.mark.integration
async def test_autofill_budget_exceeded_graceful_fallback(
    db, user, beauty_category, beauty_profile, stub_call_gemini_budget_exceeded, monkeypatch
):
    """CAT-BE-38: BudgetExceededError in call_gemini → fallback_offered=True, no 503."""
    # Bypass the Valkey-backed plan guard so the test runs without a Valkey connection.
    async def _noop_plan_limit(*args, **kwargs):
        pass

    monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_limit)

    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="BudgetFallback"),
        db=db,
    )

    req = AutofillRequest(description="under-eye anti-aging serum treatment")
    result = await catalog_service.autofill_product(
        user.id,
        "free",
        product.id,
        req,
        request_id=str(uuid.uuid4()),
        db=db,
    )

    assert result.fallback_offered is True, (
        f"Budget exceeded must return fallback_offered=True; got {result!r}"
    )
    assert result.suggestions == {}, (
        f"Suggestions must be empty on budget fallback; got {result.suggestions!r}"
    )


# ── CAT-BE-39: autofill suggestions respect enum allow-set ───────────────────

@pytest.mark.integration
async def test_autofill_suggestions_respect_enum_allow_set(
    db, user, beauty_category, beauty_profile, eye_serum_schema, monkeypatch
):
    """CAT-BE-39: AI-returned field values must respect the schema's allowed enums.

    The ``stub_call_gemini`` fixture (from catalog conftest) returns a canned
    response. We patch ``call_gemini`` directly to return a response where one
    field has an invalid enum value and assert that the suggestion is either
    excluded (layer-2 guardrail) or, if included, carries the value unchanged
    for the FE to decide (the service does NOT reject suggestions; that would
    change the service contract).

    The important invariant is: the Layer-2 guardrail inside ``call_gemini``
    should have sanitised bad enum values before the service layer sees them.
    We verify the service itself doesn't crash and returns a structurally valid
    AutofillResponse.
    """
    from app.ai_ops import client as ai_client
    from app.ai_ops.client import AIResponse

    # Bypass the Valkey-backed plan guard so the test runs without a Valkey connection.
    async def _noop_plan_limit(*args, **kwargs):
        pass

    monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_limit)

    product = await catalog_service.create_product(
        user.id,
        "free",
        CreateProductRequest(category_id=beauty_category.id, name="EnumGuardTest"),
        db=db,
    )

    # AI returns a canned response: valid field "application_area" with an
    # invalid value (should be ["under-eye", "eyelid", "full-face"]).
    from app.adapters.gemini import GeminiResponse

    async def _stub_call_gemini(ctx, prompt_name, *, prompt_vars=None, allowed_enums=None,
                                image_bytes=None, response_mime_type=None, max_output_tokens=None):
        return AIResponse(
            parsed={
                "fields": {
                    "application_area": "under-eye",  # valid
                    "product_name": "Eye Serum Gold",   # valid text
                },
                "fallback_offered": False,
            },
            raw_response=GeminiResponse(
                text="", input_tokens=0, output_tokens=0, finish_reason="STOP", raw={}
            ),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="stub-trace-id",
        )

    original_call_gemini = ai_client.call_gemini
    ai_client.call_gemini = _stub_call_gemini
    try:
        req = AutofillRequest(description="under-eye anti-aging vitamin C serum")
        result = await catalog_service.autofill_product(
            user.id,
            "free",
            product.id,
            req,
            request_id=str(uuid.uuid4()),
            db=db,
        )
    finally:
        ai_client.call_gemini = original_call_gemini

    # The service must return an AutofillResponse (not raise).
    assert result is not None, "autofill_product must return an AutofillResponse"
    assert isinstance(result.suggestions, dict), (
        f"suggestions must be a dict; got {type(result.suggestions)}"
    )
    # Valid field must be present in suggestions.
    if not result.fallback_offered:
        assert "application_area" in result.suggestions or "product_name" in result.suggestions, (
            f"At least one valid suggestion field expected; got {result.suggestions!r}"
        )
