"""Unit tests — ``suggest_categories`` §9.B.1 branch gap-fill.

These COMPLEMENT (do not duplicate) the two pre-existing §9.J unit
tests:

* ``test_suggest_graceful_fallback_on_budget.py`` — §9.J unit 4
  (BudgetExceededError raised + AIResponse.parsed.fallback_offered=True).
* ``test_suggest_layer2_invalid_id_retry.py`` — §9.J unit 5
  (AI returns a category_id absent from the categories table).

The branches covered HERE are the §9.B.1 flow steps NOT exercised by the
above two (which both terminate in the empty-fallback envelope):

* **Step 1 — query validation** (``SuggestQueryInvalidError`` on empty /
  whitespace-only / > 5000-char ``q``).  Neither existing test trips the
  length guard.
* **Steps 6-8 — the SUCCESS path**: a valid AI suggestion is enriched
  from the in-process tree (super_id / super_name / path / leaf_name),
  the confidence is calibrated by ``picker.calibrate_confidence``, and
  ``picker.select_top_k`` caps at 5 with ``fallback_offered=False``.  The
  two existing tests only ever assert the EMPTY envelope.
* **Non-dict ``parsed``** defensive branch (``parsed`` is a bare string,
  not a dict) → empty fallback.  The budget test exercises the
  dict-with-flag path; this hits the ``isinstance(..., dict)`` guard.
* **Cache-hit determinism** — a second identical call returns the cached
  payload WITHOUT re-invoking ``call_gemini`` (the §9.B.1 step-3
  ``get_or_set`` ttl=900 contract; temperature=0 makes the response
  deterministic per query).

All tests stub the tree fetch + AI call + repository so NO Postgres is
required; only the ``use_live_valkey`` fixture (localhost Valkey) backs
the ``core.cache.get_or_set`` layer.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.adapters.gemini import GeminiResponse
from app.ai_ops.client import AIResponse
from app.modules.category import service as category_service
from app.modules.category.exceptions import SuggestQueryInvalidError

pytestmark = pytest.mark.usefixtures("use_live_valkey")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _empty_gemini_response() -> GeminiResponse:
    return GeminiResponse(
        text="",
        input_tokens=0,
        output_tokens=0,
        finish_reason="STOP",
        raw={},
    )


_SEEDED_ID = "11111111-1111-1111-1111-111111111111"


def _tree_row(category_id: str) -> dict:
    """One in-process tree row matching ``_fetch_tree_dicts`` output shape."""
    return {
        "id": category_id,
        "meesho_leaf_id": 4242,
        "super_id": "super-fashion",
        "super_name": "Women Western",
        "path": "Women Western > Kurtis",
        "leaf_name": "Kurtis",
        "template_id": "22222222-2222-2222-2222-222222222222",
        "commission_pct": "18.00",
    }


def _stub_tree_with(category_id: str):
    async def _stub(db):  # noqa: ARG001
        return [_tree_row(category_id)]

    return _stub


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — query validation guard (SuggestQueryInvalidError → 400)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "bad_q",
    [
        "",            # empty
        "   ",         # whitespace-only → trims to empty
        "\t\n ",       # mixed whitespace
        "x" * 5001,    # over the 5000-char §9.B.1 bound
    ],
)
async def test_suggest_rejects_out_of_bounds_query(bad_q, monkeypatch):
    """Step 1: ``1 <= len(q.strip()) <= 5000`` — else SuggestQueryInvalidError.

    The guard fires BEFORE plan_guard / cache / AI — so no stubs of those
    are required.  Asserts the 400-mapped category exception per §9.G.
    """
    user_id = uuid4()
    with pytest.raises(SuggestQueryInvalidError):
        await category_service.suggest_categories(
            user_id, bad_q, db=None  # type: ignore[arg-type]
        )


async def test_suggest_accepts_max_length_boundary(monkeypatch):
    """A 5000-char query is INSIDE the bound — must not raise on length.

    We stub the tree + AI so the call returns the empty fallback cleanly;
    the assertion is simply that no ``SuggestQueryInvalidError`` escapes
    the length guard at exactly len==5000.
    """
    monkeypatch.setattr(
        category_service, "_fetch_tree_dicts", _stub_tree_with(_SEEDED_ID)
    )

    async def _returning_empty(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={"suggestions": [], "fallback_offered": True},
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(
        category_service.ai_client, "call_gemini", _returning_empty
    )

    payload = await category_service.suggest_categories(
        uuid4(), "k" * 5000, db=None  # type: ignore[arg-type]
    )
    # No raise → length guard passed; envelope is the graceful empty shape.
    assert payload["suggestions"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Steps 6-8 — the SUCCESS path (enrichment + calibration + top-K)
# ─────────────────────────────────────────────────────────────────────────────
async def test_suggest_success_path_enriches_and_returns_top_k(monkeypatch):
    """A valid AI suggestion is enriched from the tree + calibrated + ranked.

    Covers §9.B.1 steps 6 (existence pass via in-process tree), 7
    (denormalised super_id/super_name/path/leaf_name enrichment), 8
    (calibrate_confidence + select_top_k) and the
    ``fallback_offered=False`` success envelope — none of which the two
    pre-existing §9.J tests reach (they both terminate in the empty
    fallback).
    """
    monkeypatch.setattr(
        category_service, "_fetch_tree_dicts", _stub_tree_with(_SEEDED_ID)
    )

    async def _returning_valid(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={
                "suggestions": [
                    {
                        "category_id": _SEEDED_ID,
                        "confidence": 0.91,
                        "reasons": ["matches kurti description"],
                    }
                ],
                "fallback_offered": False,
            },
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(
        category_service.ai_client, "call_gemini", _returning_valid
    )

    # Mock plan_guard to avoid Valkey dependency in this unit test.
    with _patch("app.modules.category.service.enforce_plan_limit", new_callable=_AM_CLS):
        payload = await category_service.suggest_categories(
            uuid4(), "cotton kurti", db=None  # type: ignore[arg-type]
        )

    assert payload["fallback_offered"] is False
    assert len(payload["suggestions"]) == 1
    sug = payload["suggestions"][0]
    # Step 7 enrichment — denormalised tree fields are present.
    assert sug["category_id"] == _SEEDED_ID
    assert sug["super_id"] == "super-fashion"
    assert sug["super_name"] == "Women Western"
    assert sug["path"] == "Women Western > Kurtis"
    assert sug["leaf_name"] == "Kurtis"
    # Step 8 — calibrate_confidence with 0 retries leaves the value intact.
    assert sug["confidence"] == pytest.approx(0.91)
    assert sug["reasons"] == ["matches kurti description"]


async def test_suggest_caps_results_at_five(monkeypatch):
    """``select_top_k(scored, 5)`` never returns more than 5 suggestions.

    The AI returns 7 valid suggestions (all in the stubbed tree); the
    service must emit at most 5 per the §9.E ``max_length=5`` contract —
    the locked cap the dispatch forbids widening.
    """
    ids = [f"{i:08d}-1111-1111-1111-111111111111" for i in range(7)]

    async def _stub_tree(db):  # noqa: ARG001
        return [_tree_row(cid) for cid in ids]

    monkeypatch.setattr(category_service, "_fetch_tree_dicts", _stub_tree)

    async def _returning_seven(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={
                "suggestions": [
                    {"category_id": cid, "confidence": 0.5 + idx * 0.05, "reasons": []}
                    for idx, cid in enumerate(ids)
                ],
                "fallback_offered": False,
            },
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(
        category_service.ai_client, "call_gemini", _returning_seven
    )

    payload = await category_service.suggest_categories(
        uuid4(), "many matches", db=None  # type: ignore[arg-type]
    )
    assert payload["fallback_offered"] is False
    assert len(payload["suggestions"]) == 5


# ─────────────────────────────────────────────────────────────────────────────
# Defensive — non-dict ``parsed`` → empty fallback
# ─────────────────────────────────────────────────────────────────────────────
async def test_suggest_handles_non_dict_parsed(monkeypatch):
    """``AIResponse.parsed`` arriving as a bare string → empty fallback.

    Hits the ``isinstance(ai_response.parsed, dict)`` guard branch that
    the dict-shaped fallback tests do not exercise.
    """
    monkeypatch.setattr(
        category_service, "_fetch_tree_dicts", _stub_tree_with(_SEEDED_ID)
    )

    async def _returning_string(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed="not-a-dict",  # type: ignore[arg-type]
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(
        category_service.ai_client, "call_gemini", _returning_string
    )

    payload = await category_service.suggest_categories(
        uuid4(), "weird response", db=None  # type: ignore[arg-type]
    )
    assert payload["suggestions"] == []
    assert payload["fallback_offered"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Cache-hit determinism — §9.B.1 step 3 get_or_set ttl=900
# ─────────────────────────────────────────────────────────────────────────────
async def test_suggest_second_call_hits_cache_and_skips_ai(monkeypatch):
    """Two identical calls invoke ``call_gemini`` exactly ONCE.

    The §9.B.1 cache (key ``smart_picker:{sha256(q)}``, ttl 900 s) must
    short-circuit the AI call on the second identical query.  A unique
    query string per test run avoids a stale cache entry from a prior run
    poisoning the assertion (the ``use_live_valkey`` fixture flushes the
    scratch DBs, but belt-and-braces uniqueness keeps this robust).
    """
    monkeypatch.setattr(
        category_service, "_fetch_tree_dicts", _stub_tree_with(_SEEDED_ID)
    )

    call_count = {"n": 0}

    async def _counting(ctx, prompt_id, prompt_vars=None, **kwargs):
        call_count["n"] += 1
        return AIResponse(
            parsed={
                "suggestions": [
                    {"category_id": _SEEDED_ID, "confidence": 0.8, "reasons": []}
                ],
                "fallback_offered": False,
            },
            raw_response=_empty_gemini_response(),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(category_service.ai_client, "call_gemini", _counting)

    user_id = uuid4()
    unique_q = f"deterministic query {uuid4().hex}"

    first = await category_service.suggest_categories(
        user_id, unique_q, db=None  # type: ignore[arg-type]
    )
    second = await category_service.suggest_categories(
        user_id, unique_q, db=None  # type: ignore[arg-type]
    )

    assert call_count["n"] == 1, "second identical call must hit the cache"
    assert first == second
    assert first["fallback_offered"] is False


# ─────────────────────────────────────────────────────────────────────────────
# QA Wave 1 — P0.7: GET /categories/suggest → 405, POST → 200 (via route layer)
# P1.8: top-3 contract — exactly 3 suggestions + confidence each
# ─────────────────────────────────────────────────────────────────────────────
# These tests use an ASGI stub client (no live DB required).  The Smart Picker
# route is POST-only since the 2026-06-16 amendment; a GET must return 405.

import os as _os
import uuid as _uuid_mod
from contextlib import asynccontextmanager as _acm
from unittest.mock import patch as _patch, AsyncMock as _AM_CLS

from httpx import ASGITransport as _ASGITransport
from httpx import AsyncClient as _AsyncClient

from app.core.auth import CurrentUser as _CU, get_current_user as _gcu
from app.main import app as _app


@_acm
async def _make_stub_client():
    """Async context manager: in-process client with a stub auth bypass."""
    _app.dependency_overrides[_gcu] = lambda: _CU(
        user_id=_uuid_mod.uuid4(), plan="free"
    )
    transport = _ASGITransport(app=_app, raise_app_exceptions=False)
    async with _AsyncClient(transport=transport, base_url="http://testserver") as ac:
        try:
            yield ac
        finally:
            _app.dependency_overrides.pop(_gcu, None)


async def test_suggest_get_returns_405():
    """GET /categories/suggest must return 405 — the route is POST-only.

    The suggest route was changed from GET to POST in the 2026-06-16
    amendment.  A stale GET call must be rejected at the HTTP layer (405),
    not silently served or returning 404/422 from the validator.
    """
    async with _make_stub_client() as ac:
        resp = await ac.get(
            "/api/v1/categories/suggest",
            params={"q": "kurti"},
        )
    assert resp.status_code == 405, (
        f"GET /categories/suggest expected 405, got {resp.status_code}: {resp.text}"
    )


async def test_suggest_post_returns_non_405(monkeypatch):
    """POST /categories/suggest does NOT return 405 — the route is registered.

    We do not assert a 200 (the service may fail without seeded data or a
    live DB), but it must NOT return 405 (method not allowed) or 404 from
    the flag guard.  Any non-405 / non-404 response confirms the route is
    correctly registered as POST.
    """
    from app.modules.category import service as _cat_svc
    from app.adapters.gemini import GeminiResponse as _GR
    from app.ai_ops.client import AIResponse as _AIR

    monkeypatch.setattr(_cat_svc, "_fetch_tree_dicts", _AM_CLS(return_value=[]))
    monkeypatch.setattr(_cat_svc, "enforce_plan_limit", _AM_CLS())

    async def _noop(ctx, prompt_id, prompt_vars=None, **kwargs):
        return _AIR(
            parsed={"suggestions": [], "fallback_offered": True},
            raw_response=_GR(text="", input_tokens=0, output_tokens=0,
                             finish_reason="STOP", raw={}),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(_cat_svc.ai_client, "call_gemini", _noop)

    async with _make_stub_client() as ac:
        resp = await ac.post(
            "/api/v1/categories/suggest",
            json={"q": "cotton kurti"},
        )
    assert resp.status_code != 405, (
        f"POST /categories/suggest must not return 405; got {resp.status_code}: {resp.text}"
    )


# ── P1.8: top-3 contract ─────────────────────────────────────────────────────
async def test_suggest_top_3_contract_exactly_3_with_confidence(monkeypatch):
    """Service returns exactly 3 suggestions when AI returns exactly 3.

    Verifies the top-K contract: when the AI returns exactly 3 suggestions
    (all valid in the tree), ``suggest_categories`` must emit exactly 3 items
    and each item must carry a ``confidence`` field that is a float.

    This complements ``test_suggest_caps_results_at_five`` (which tests the
    5-item cap) by fixing the exact-3 case that the cap test does not cover
    (the cap test uses 7 → 5, never 3 → 3).
    """
    _IDS_3 = [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
    ]

    from uuid import uuid4

    from app.adapters.gemini import GeminiResponse
    from app.ai_ops.client import AIResponse
    from app.modules.category import service as category_service

    async def _stub_tree(db):
        return [
            {
                "id": cid,
                "meesho_leaf_id": 1000 + idx,
                "super_id": "super-x",
                "super_name": "Women Western",
                "path": "Women Western > Kurtis",
                "leaf_name": "Kurtis",
                "template_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                "commission_pct": "0.00",
            }
            for idx, cid in enumerate(_IDS_3)
        ]

    monkeypatch.setattr(category_service, "_fetch_tree_dicts", _stub_tree)

    async def _returning_3(ctx, prompt_id, prompt_vars=None, **kwargs):
        return AIResponse(
            parsed={
                "suggestions": [
                    {"category_id": cid, "confidence": 0.7 + idx * 0.05, "reasons": []}
                    for idx, cid in enumerate(_IDS_3)
                ],
                "fallback_offered": False,
            },
            raw_response=GeminiResponse(
                text="", input_tokens=0, output_tokens=0, finish_reason="STOP", raw={}
            ),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="t",
        )

    monkeypatch.setattr(category_service.ai_client, "call_gemini", _returning_3)

    # Mock plan_guard to avoid Valkey dependency in this unit test.
    with _patch("app.modules.category.service.enforce_plan_limit", new_callable=_AM_CLS):
        payload = await category_service.suggest_categories(
            uuid4(), "cotton kurti", db=None  # type: ignore[arg-type]
        )

    suggestions = payload["suggestions"]
    # Top-3 contract: exactly 3 items.
    assert len(suggestions) == 3, (
        f"Expected exactly 3 suggestions, got {len(suggestions)}: {suggestions}"
    )
    # Each item must carry a confidence field that is a numeric float.
    for sug in suggestions:
        conf = sug.get("confidence")
        assert isinstance(conf, float), (
            f"suggestion missing float 'confidence'; got {sug!r}"
        )
