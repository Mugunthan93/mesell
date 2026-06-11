"""Unit test §9.J #5 — ``/suggest`` Layer 2 invalid-category-id retry.

Per BACKEND_ARCHITECTURE.md §9.J unit 5:

    "``/suggest`` Layer 2 invalid-category-id retry — when the mocked AI
    returns an invalid ``category_id`` (not in ``categories``), §6A
    retries with stricter prompt; after 2 retries the response is 200
    with empty suggestions + ``fallback_offered=true`` per §9.B.1 flow."

The service-layer guardrail is the final defensive layer.  ``call_gemini``
already retries up to 2 times for invalid IDs (per §6A.E); when those
retries are exhausted ``call_gemini`` returns ``parsed.fallback_offered=True``
and the service emits the empty fallback envelope.  BUT — if the AI
"convinces" itself a UUID is valid that is NOT actually present in our
``categories`` table (the AI track's Layer 2 only verifies SHAPE, not
table membership), the service-level guardrail is the only thing that
catches it.

The mocked ``call_gemini`` here returns a single suggestion whose
``category_id`` is a UUID we KNOW is not in the table.  The service
must reject it via ``assert_category_exists_uncached`` and return the
empty fallback envelope.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.ai_ops.client import AIResponse
from app.adapters.gemini import GeminiResponse
from app.modules.category import service as category_service


_INVALID_UUID = UUID("00000000-0000-0000-0000-000000000000")


def _empty_gemini_response() -> GeminiResponse:
    return GeminiResponse(
        text="",
        input_tokens=0,
        output_tokens=0,
        finish_reason="STOP",
        raw={},
    )


async def test_suggest_drops_unknown_category_id_returned_by_ai(
    use_live_valkey, monkeypatch
):
    """AI returns a single suggestion for a UUID not in the categories table.

    Service's final-pass guardrail must reject the suggestion and emit
    the empty fallback envelope.
    """
    # Stub the tree so the in-process by_id lookup is empty — forces the
    # service into the assert_category_exists_uncached DB path.
    async def _stub_tree(db):  # noqa: ARG001
        return []

    monkeypatch.setattr(category_service, "_fetch_tree_dicts", _stub_tree)

    # Stub the existence check to FALSE — the chosen all-zeros UUID won't
    # be in any seeded categories table, but we also stub the DB query so
    # the test does not require the dev tunnel.
    async def _no_row(db, category_id):  # noqa: ARG001
        return False

    monkeypatch.setattr(
        category_service.category_repo,
        "assert_category_exists_uncached",
        _no_row,
    )

    async def _returning_one_invalid(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={
                "suggestions": [
                    {
                        "category_id": str(_INVALID_UUID),
                        "confidence": 0.9,
                        "reasons": ["test"],
                    }
                ],
                "fallback_offered": False,
            },
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=2,
            trace_id="test-trace",
        )

    monkeypatch.setattr(
        category_service.ai_client, "call_gemini", _returning_one_invalid
    )

    user_id = uuid4()
    payload = await category_service.suggest_categories(
        user_id, "valid query", db=None  # type: ignore[arg-type]
    )

    assert payload["suggestions"] == []
    assert payload["fallback_offered"] is True


pytestmark = [pytest.mark.usefixtures("use_live_valkey"), pytest.mark.integration]
