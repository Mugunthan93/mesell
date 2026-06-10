"""Unit test §9.J #4 — ``/suggest`` graceful fallback on BudgetExceededError.

Per BACKEND_ARCHITECTURE.md §9.J unit 4:

    "``/suggest`` graceful fallback on ``BudgetExceededError`` — when
    the mocked ``ai_ops.client.call_gemini`` raises
    ``BudgetExceededError``, the response is 200 with
    ``SuggestResponse(suggestions=[], fallback_offered=True)`` (NOT
    503)."

This test covers BOTH paths the service handles per the dispatch
criterion #7:

a. ``call_gemini`` RAISES :class:`BudgetExceededError` directly
   (V1.5 surface — today's ``call_gemini`` catches the error
   internally, but the service code defensively handles both).
b. ``call_gemini`` RETURNS an ``AIResponse`` with
   ``parsed.fallback_offered=True`` (the V1 in-place behaviour).

No DB seeding required — we mock the tree fetch, the AI call, and the
plan-guard hourly counter (via use_live_valkey + flushed Valkey).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.ai_ops.budget_cap import BudgetExceededError
from app.ai_ops.client import AIResponse
from app.adapters.gemini import GeminiResponse
from app.modules.category import service as category_service


def _empty_gemini_response() -> GeminiResponse:
    return GeminiResponse(
        text="",
        input_tokens=0,
        output_tokens=0,
        finish_reason="FALLBACK",
        raw={"fallback": True},
    )


async def test_suggest_returns_fallback_when_call_gemini_raises_budget_error(
    use_live_valkey, monkeypatch
):
    """Path (a): BudgetExceededError raised → 200 empty + fallback_offered."""
    # Bypass tree load (would otherwise hit the dev DB).  Stub it to an
    # empty list — the picker is a no-op on empty input and the AI mock
    # raises before any tree consumer runs.
    async def _stub_tree(db):  # noqa: ARG001
        return []

    monkeypatch.setattr(category_service, "_fetch_tree_dicts", _stub_tree)

    async def _raising_call_gemini(ctx, prompt_id, prompt_vars=None, **kwargs):
        raise BudgetExceededError(
            detail="day budget hit",
        )

    monkeypatch.setattr(
        category_service.ai_client, "call_gemini", _raising_call_gemini
    )

    user_id = uuid4()
    payload = await category_service.suggest_categories(
        user_id, "test kurti", db=None  # type: ignore[arg-type]
    )

    assert payload["suggestions"] == []
    assert payload["fallback_offered"] is True


async def test_suggest_returns_fallback_when_call_gemini_returns_fallback_offered(
    use_live_valkey, monkeypatch
):
    """Path (b): AIResponse(parsed.fallback_offered=True) → same."""
    async def _stub_tree(db):  # noqa: ARG001
        return []

    monkeypatch.setattr(category_service, "_fetch_tree_dicts", _stub_tree)

    async def _returning_fallback(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={
                "suggestions": [],
                "fallback_offered": True,
                "reason": "budget",
            },
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="test-trace",
        )

    monkeypatch.setattr(
        category_service.ai_client, "call_gemini", _returning_fallback
    )

    user_id = uuid4()
    payload = await category_service.suggest_categories(
        user_id, "test kurti", db=None  # type: ignore[arg-type]
    )

    assert payload["suggestions"] == []
    assert payload["fallback_offered"] is True


pytestmark = pytest.mark.usefixtures("use_live_valkey")
