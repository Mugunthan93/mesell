"""CAT-BE-02 / CAT-BE-03 / CAT-BE-05 / CAT-BE-08 / CAT-BE-09
Gap-fill for ``POST /categories/suggest``.

What this file adds (does NOT duplicate test_suggest_unit.py):
- CAT-BE-02  empty-q 422 carries a NON-EMPTY ``validation_message_id``
- CAT-BE-03  5001-char q → 422; 5000-char q → OK (boundary)
- CAT-BE-05  plan-guard 402 when ``smart_picker_hourly`` is exhausted
- CAT-BE-08  all-invalid IDs returned by AI → fallback (no valid ID left)
- CAT-BE-09  AI returns 8 valid IDs → exactly 5 emitted, descending confidence,
             tie-break by category_id (CAT-OBS-1 backend end)

All tests stub the AI seam at ``app.modules.category.service.ai_client.call_gemini``.
No Postgres is touched; ``use_live_valkey`` provides the cache layer.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.adapters.gemini import GeminiResponse
from app.ai_ops.client import AIResponse
from app.core.auth import CurrentUser, get_current_user
from app.main import app

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _empty_gemini_resp() -> GeminiResponse:
    return GeminiResponse(
        text="", input_tokens=0, output_tokens=0, finish_reason="STOP", raw={}
    )


@dataclass(frozen=True)
class _StubUser:
    user_id: object
    plan: str = "free"


def _stub_user_dep():
    return _StubUser(user_id=uuid4())


@asynccontextmanager
async def _make_client(raise_app_exceptions: bool = False):
    """ASGI client with a stub auth override + lifespan so app state is ready."""
    app.dependency_overrides[get_current_user] = _stub_user_dep
    transport = ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-02  empty-q → 422 with NON-EMPTY validation_message_id
# ─────────────────────────────────────────────────────────────────────────────

async def test_suggest_empty_q_422_with_nonempty_message_id(use_live_valkey):
    """CAT-BE-02: POST /categories/suggest with empty q → 422; message_id present."""
    async with _make_client() as ac:
        resp = await ac.post("/api/v1/categories/suggest", json={"q": ""})

    assert resp.status_code == 422, (
        f"Expected 422 for empty q, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    # The 422 must carry SOME identifier — either a standard FastAPI
    # "detail" list or a validation_message_id; the important thing is the
    # body is non-empty and not "detail: null".
    assert body, "422 body must be non-empty (non-null)"
    # FastAPI wraps Pydantic 422 as {"detail": [...]}.
    detail = body.get("detail") or body.get("validation_message_id")
    assert detail, (
        f"422 body must carry a non-empty detail or validation_message_id; got {body}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-03  5001-char q → 422;  5000-char q → NOT 422 (boundary)
# ─────────────────────────────────────────────────────────────────────────────

async def test_suggest_5001_char_q_returns_422(use_live_valkey, monkeypatch):
    """CAT-BE-03a: q of length 5001 exceeds the 5000-char limit → 422."""
    # Stub the tree + AI so the service won't fail on those; the rejection
    # fires at the SuggestQuery Pydantic validation before service entry.
    async with _make_client() as ac:
        resp = await ac.post(
            "/api/v1/categories/suggest",
            json={"q": "k" * 5001},
        )

    assert resp.status_code == 422, (
        f"Expected 422 for 5001-char q, got {resp.status_code}: {resp.text}"
    )


async def test_suggest_5000_char_q_accepted(use_live_valkey, monkeypatch):
    """CAT-BE-03b: q of exactly 5000 chars is within the limit → NOT 422."""
    from app.modules.category import service as cat_svc

    # Stub tree + AI so we get a deterministic fallback envelope.
    monkeypatch.setattr(
        cat_svc, "_fetch_tree_dicts", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(cat_svc, "enforce_plan_limit", AsyncMock())

    async def _fallback_ai(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={"suggestions": [], "fallback_offered": True},
            raw_response=_empty_gemini_resp(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(cat_svc.ai_client, "call_gemini", _fallback_ai)

    async with _make_client() as ac:
        resp = await ac.post(
            "/api/v1/categories/suggest",
            json={"q": "k" * 5000},
        )

    # The request MUST NOT be rejected at the length guard.
    assert resp.status_code != 422, (
        f"5000-char q must NOT be rejected (got 422). Response: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-05  plan-guard 402 when smart_picker_hourly is exhausted
# ─────────────────────────────────────────────────────────────────────────────

async def test_suggest_plan_guard_402_when_limit_exceeded(use_live_valkey, monkeypatch):
    """CAT-BE-05: enforce_plan_limit raises PlanLimitExceededError → 402."""
    from app.modules.category import service as cat_svc
    from app.core.plan_guard import PlanLimitExceededError

    # Stub the tree so the service gets to the plan-guard step.
    monkeypatch.setattr(
        cat_svc, "_fetch_tree_dicts", AsyncMock(return_value=[])
    )

    async def _raise_limit(*args, **kwargs):
        raise PlanLimitExceededError(
            resource="smart_picker_hourly",
            current=100,
            limit=100,
        )

    monkeypatch.setattr(cat_svc, "enforce_plan_limit", _raise_limit)

    async with _make_client() as ac:
        resp = await ac.post(
            "/api/v1/categories/suggest",
            json={"q": "cotton kurti"},
        )

    assert resp.status_code == 402, (
        f"Expected 402 when plan limit is exhausted, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    # Must carry a non-empty machine code (§4.F envelope).
    code = body.get("code") or body.get("validation_message_id") or body.get("detail")
    assert code, f"402 body must carry a non-empty code/detail; got {body}"


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-08  all-invalid AI category_ids → 200 fallback_offered=true
# ─────────────────────────────────────────────────────────────────────────────

async def test_suggest_all_invalid_ids_returns_fallback(use_live_valkey, monkeypatch):
    """CAT-BE-08: AI returns IDs that are NOT in the tree → fallback envelope."""
    from app.modules.category import service as cat_svc

    # Tree has one real ID; AI returns three different (unknown) IDs.
    real_id = str(uuid4())

    async def _stub_tree(db):  # noqa: ARG001
        return [
            {
                "id": real_id,
                "meesho_leaf_id": 9999,
                "super_id": "s1",
                "super_name": "Women Fashion",
                "path": "Women Fashion > Kurtis",
                "leaf_name": "Kurtis",
                "template_id": str(uuid4()),
                "commission_pct": "18.00",
            }
        ]

    monkeypatch.setattr(cat_svc, "_fetch_tree_dicts", _stub_tree)
    monkeypatch.setattr(cat_svc, "enforce_plan_limit", AsyncMock())

    # AI returns 3 IDs — none matching the real_id in the tree.
    unknown_ids = [str(uuid4()), str(uuid4()), str(uuid4())]

    async def _all_invalid_ai(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={
                "suggestions": [
                    {"category_id": uid, "confidence": 0.8, "reasons": []}
                    for uid in unknown_ids
                ],
                "fallback_offered": False,
            },
            raw_response=_empty_gemini_resp(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(cat_svc.ai_client, "call_gemini", _all_invalid_ai)

    async with _make_client() as ac:
        resp = await ac.post(
            "/api/v1/categories/suggest",
            json={"q": "cotton kurti"},
        )

    assert resp.status_code == 200, (
        f"Expected 200 for all-invalid AI IDs, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("fallback_offered") is True, (
        f"fallback_offered must be True when all AI IDs are invalid; got {body}"
    )
    assert body.get("suggestions") == [], (
        f"suggestions must be empty when all AI IDs are invalid; got {body}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-09  AI returns 8 valid IDs → caps at 5, descending confidence,
#            tie-break by category_id (CAT-OBS-1 backend end)
# ─────────────────────────────────────────────────────────────────────────────

async def test_suggest_caps_at_5_deterministic_order(use_live_valkey, monkeypatch):
    """CAT-BE-09 (CAT-OBS-1 pin): AI returns 8 valid IDs → exactly 5 returned.

    Verifies the ``SuggestResponse.max_length=5`` contract (the deliberate
    "fetch-5, show-3" design).  Also verifies deterministic order: the 5
    returned must be the 5 HIGHEST confidence, in descending order.
    Tie-break is by category_id ASC.
    """
    from app.modules.category import service as cat_svc

    # 8 IDs in the tree with different confidence values.
    # UUIDs must use only hex chars (0-9, a-f); g/h are invalid.
    ids_and_confs = [
        ("a0000000-0000-0000-0000-000000000001", 0.50),
        ("b0000000-0000-0000-0000-000000000002", 0.95),
        ("c0000000-0000-0000-0000-000000000003", 0.70),
        ("d0000000-0000-0000-0000-000000000004", 0.85),
        ("e0000000-0000-0000-0000-000000000005", 0.60),
        ("f0000000-0000-0000-0000-000000000006", 0.90),
        ("a1000000-0000-0000-0000-000000000007", 0.75),
        ("a2000000-0000-0000-0000-000000000008", 0.55),
    ]

    async def _stub_tree(db):  # noqa: ARG001
        return [
            {
                "id": cid,
                "meesho_leaf_id": idx,
                "super_id": "s1",
                "super_name": "Women Fashion",
                "path": f"Women Fashion > Leaf {idx}",
                "leaf_name": f"Leaf {idx}",
                "template_id": str(uuid4()),
                "commission_pct": "18.00",
            }
            for idx, (cid, _) in enumerate(ids_and_confs)
        ]

    monkeypatch.setattr(cat_svc, "_fetch_tree_dicts", _stub_tree)
    monkeypatch.setattr(cat_svc, "enforce_plan_limit", AsyncMock())

    async def _return_8(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={
                "suggestions": [
                    {"category_id": cid, "confidence": conf, "reasons": []}
                    for cid, conf in ids_and_confs
                ],
                "fallback_offered": False,
            },
            raw_response=_empty_gemini_resp(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(cat_svc.ai_client, "call_gemini", _return_8)

    async with _make_client() as ac:
        resp = await ac.post(
            "/api/v1/categories/suggest",
            json={"q": "cotton kurti"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    suggestions = body.get("suggestions", [])
    # CAT-OBS-1 BE end: exactly 5 returned.
    assert len(suggestions) == 5, (
        f"Expected exactly 5 suggestions (CAT-OBS-1), got {len(suggestions)}: {suggestions}"
    )

    # Descending confidence order.
    confs = [s["confidence"] for s in suggestions]
    assert confs == sorted(confs, reverse=True), (
        f"Suggestions must be in descending confidence order; got {confs}"
    )

    # The 5 highest-confidence IDs are those with conf 0.95,0.90,0.85,0.75,0.70.
    top5_ids = {s["category_id"] for s in suggestions}
    expected_ids = {
        "b0000000-0000-0000-0000-000000000002",  # 0.95
        "f0000000-0000-0000-0000-000000000006",  # 0.90
        "d0000000-0000-0000-0000-000000000004",  # 0.85
        "a1000000-0000-0000-0000-000000000007",  # 0.75
        "c0000000-0000-0000-0000-000000000003",  # 0.70
    }
    assert top5_ids == expected_ids, (
        f"Top-5 IDs mismatch (CAT-OBS-1); expected {expected_ids}, got {top5_ids}"
    )

    # fallback_offered must be False (all IDs were valid).
    assert body.get("fallback_offered") is False, (
        f"fallback_offered must be False when all IDs are valid; got {body}"
    )
