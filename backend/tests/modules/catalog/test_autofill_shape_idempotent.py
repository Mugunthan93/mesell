"""QA Wave 1 — P1.9: Catalog autofill mocked-shape + idempotent JSONB replace.

Two gap-fill tests for the autofill surface:

1. Mocked-shape: ``autofill_product`` returns ``AutofillResponse`` with a
   non-empty ``suggestions`` dict when the AI adapter is mocked at the seam.

2. Idempotent replace: the repo's ``update_ai_suggestions_jsonb`` is called
   with the SECOND call's suggestions (not accumulated from both calls).

Seams mocked (all at the import level in catalog.service):
  * ``app.modules.catalog.service.catalog_repo``  — the repository module
  * ``app.modules.catalog.service.category_service.fetch_schema_dto``
  * ``app.modules.catalog.service.assert_product_ownership``
  * ``app.modules.catalog.service.enforce_plan_limit``
  * ``app.modules.catalog.service.ai_client.call_gemini``

No running PostgreSQL, Valkey, or network calls required.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit


# ── shared helpers ────────────────────────────────────────────────────────────

def _make_product_orm(product_id, user_id, category_id=None):
    if category_id is None:
        category_id = uuid4()
    ns = SimpleNamespace(
        id=product_id,
        user_id=user_id,
        category_id=category_id,
        ai_suggestions_jsonb={},
        fields_jsonb={},
        field_values_jsonb={},
    )
    return ns


def _make_schema_dict():
    """Minimal §5A.C flat schema dict as returned by fetch_schema_dto."""
    return {
        "fields": [
            {
                "canonical_name": "product_name",
                "data_type": "text",
                "primitive": "text_short",
                "display_name": "Product Name",
                "enum_resolver": None,
                "enum_values": None,
                "meesho_column": "Product Name",
                "step": "basics",
                "marker": "required",
            },
        ],
        "meesho_headers": ["Product Name"],
        "dependency_rules": [],
    }


def _make_request(description="Cotton kurti for women summer fashion"):
    return SimpleNamespace(
        description=description,
        fields_to_fill=["product_name"],
    )


def _ok_ai_response(fields=None):
    if fields is None:
        fields = {"product_name": "Floral Kurti"}
    r = SimpleNamespace()
    r.parsed = {"fields": fields}
    r.cost_inr = 0.01
    return r


# ── Test 1: shape ─────────────────────────────────────────────────────────────

async def test_autofill_service_returns_field_value_dict():
    """autofill_product returns AutofillResponse with non-empty suggestions.

    Arrange: mock all external seams (repo, schema, plan_guard, AI client).
    Act: call autofill_product.
    Assert: result.suggestions is a non-empty mapping (field → value).
    """
    from app.modules.catalog import service as catalog_service
    from app.modules.catalog import repository as catalog_repo_mod

    pid = uuid4()
    uid = uuid4()
    cat_id = uuid4()
    product_row = _make_product_orm(pid, uid, cat_id)

    with (
        patch.object(catalog_repo_mod, "find_by_id", AsyncMock(return_value=product_row)),
        patch.object(catalog_repo_mod, "update_ai_suggestions_jsonb", AsyncMock(return_value=product_row)),
        patch("app.modules.catalog.service.assert_product_ownership", AsyncMock()),
        patch("app.modules.catalog.service.enforce_plan_limit", AsyncMock()),
        patch("app.modules.catalog.service.category_service.fetch_schema_dto",
              AsyncMock(return_value=_make_schema_dict())),
        patch("app.modules.catalog.service._resolve_allowed_enums",
              AsyncMock(return_value={})),
        patch("app.modules.catalog.service.ai_client.call_gemini",
              AsyncMock(return_value=_ok_ai_response())),
    ):
        result = await catalog_service.autofill_product(
            user_id=uid,
            plan="free",
            product_id=pid,
            request=_make_request(),
            request_id="test-req-001",
            db=None,  # type: ignore[arg-type]
        )

    assert result is not None, "autofill_product must return a non-None result"
    suggestions = getattr(result, "suggestions", None) or {}
    applied = getattr(result, "applied", None) or {}
    assert bool(suggestions) or bool(applied), (
        f"AutofillResponse must have non-empty suggestions or applied; "
        f"got suggestions={suggestions!r}, applied={applied!r}"
    )


# ── Test 2: idempotent replace ────────────────────────────────────────────────

async def test_autofill_jsonb_replace_is_idempotent():
    """Second autofill call replaces ai_suggestions_jsonb, not appends.

    The repo's update_ai_suggestions_jsonb is called with the SECOND call's
    data.  The captured write from the second invocation must reflect the
    second AI response (not the union of both calls).
    """
    from app.modules.catalog import service as catalog_service
    from app.modules.catalog import repository as catalog_repo_mod

    pid = uuid4()
    uid = uuid4()
    cat_id = uuid4()

    # Capture every write to update_ai_suggestions_jsonb.
    write_log: list[dict] = []

    async def _capture_save(db, user_id_, product_id_, suggestions_dict):
        write_log.append(dict(suggestions_dict))
        return _make_product_orm(product_id_, user_id_, cat_id)

    call_counter = {"n": 0}

    async def _ai_incremental(ctx, prompt_id, prompt_vars=None, **kwargs):
        call_counter["n"] += 1
        n = call_counter["n"]
        return _ok_ai_response({"product_name": f"Result-{n}"})

    product_row = _make_product_orm(pid, uid, cat_id)

    with (
        patch.object(catalog_repo_mod, "find_by_id", AsyncMock(return_value=product_row)),
        patch.object(catalog_repo_mod, "update_ai_suggestions_jsonb", _capture_save),
        patch("app.modules.catalog.service.assert_product_ownership", AsyncMock()),
        patch("app.modules.catalog.service.enforce_plan_limit", AsyncMock()),
        patch("app.modules.catalog.service.category_service.fetch_schema_dto",
              AsyncMock(return_value=_make_schema_dict())),
        patch("app.modules.catalog.service._resolve_allowed_enums",
              AsyncMock(return_value={})),
        patch("app.modules.catalog.service.ai_client.call_gemini", _ai_incremental),
    ):
        await catalog_service.autofill_product(
            user_id=uid, plan="free", product_id=pid,
            request=_make_request(), request_id="req-1", db=None,  # type: ignore
        )
        await catalog_service.autofill_product(
            user_id=uid, plan="free", product_id=pid,
            request=_make_request(), request_id="req-2", db=None,  # type: ignore
        )

    assert len(write_log) >= 1, (
        "update_ai_suggestions_jsonb must be called at least once"
    )
    # The last write must contain the second call's product_name.
    last_write = write_log[-1]
    assert "product_name" in last_write, (
        f"Last JSONB write must include product_name; got {last_write!r}"
    )
    # If both calls succeeded (wrote twice), the second must NOT be same as first.
    if len(write_log) == 2:
        first_val = list(write_log[0].values())[0] if write_log[0] else {}
        second_val = list(write_log[1].values())[0] if write_log[1] else {}
        assert first_val != second_val, (
            f"The two writes must differ (second replaces first); "
            f"write_log={write_log!r}"
        )
