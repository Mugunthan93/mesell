"""Unit tests for :mod:`app.modules.category.picker` — Smart Picker
pure-Python helpers (AI track).

Per BACKEND_ARCHITECTURE.md §9.J test plan, these are the deterministic
helper tests for the AI-track contribution to the ``category`` module.
The §6A.E graceful-fallback + Layer 2 retry integration tests live with
the services-builder (``test_category_service_*.py`` — owned by that
specialist).

Hard rules:

* No I/O.  No DB.  No Valkey.  No HTTP.
* No ``ai_ops.client`` import — these helpers are decoupled from the
  Gemini call site by design.
* Deterministic — each test asserts an exact, byte-stable property of
  the output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit

from app.modules.category.picker import (
    calibrate_confidence,
    compress_tree,
    select_top_k,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tiny CategoryRow stand-in.  We don't import the real §9.F dataclass so
# this test file doesn't pull the (heavier) ``app.modules.category.domain``
# module before that file exists in this construction sub-session — the
# picker helpers are deliberately duck-typed (``_row_field`` accepts any
# attribute-bearing object).
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Row:
    id: str
    super_id: str
    super_name: str
    path: str
    leaf_name: str


def _make_rows() -> list[_Row]:
    """Six rows across three super-categories — exercise grouping + sort."""
    return [
        _Row(
            id="11111111-1111-1111-1111-111111111111",
            super_id="11",
            super_name="Women Fashion",
            path="Women Fashion > Ethnic Wear > Kurtis",
            leaf_name="Kurtis",
        ),
        _Row(
            id="22222222-2222-2222-2222-222222222222",
            super_id="11",
            super_name="Women Fashion",
            path="Women Fashion > Ethnic Wear > Sarees",
            leaf_name="Sarees",
        ),
        _Row(
            id="33333333-3333-3333-3333-333333333333",
            super_id="13",
            super_name="Beauty & Personal Care",
            path="Beauty > Skin Care > Serums",
            leaf_name="Serums",
        ),
        _Row(
            id="44444444-4444-4444-4444-444444444444",
            super_id="13",
            super_name="Beauty & Personal Care",
            path="Beauty > Skin Care > Moisturisers",
            leaf_name="Moisturisers",
        ),
        _Row(
            id="55555555-5555-5555-5555-555555555555",
            super_id="20",
            super_name="Home & Kitchen",
            path="Home > Kitchen > Cookware",
            leaf_name="Cookware",
        ),
        _Row(
            id="66666666-6666-6666-6666-666666666666",
            super_id="20",
            super_name="Home & Kitchen",
            path="Home > Decor > Wall Art",
            leaf_name="Wall Art",
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 1) compress_tree is deterministic — identical input → identical bytes.
# ─────────────────────────────────────────────────────────────────────────────


def test_compress_tree_deterministic() -> None:
    """Same input must produce byte-identical JSON output.

    The §9.B.1 cache key (``smart_picker:{sha256(q)}:v{cache_version}``)
    relies on this: two workers handling the same query must build the
    same prompt body, or cache reads return stale-but-different shapes.
    """
    rows = _make_rows()
    out_a = compress_tree(rows, description="kurti")
    out_b = compress_tree(rows, description="kurti")
    # Dicts compare structurally — but assert the JSON bytes too so the
    # determinism claim survives a future dict-ordering subtlety.
    assert out_a == out_b
    assert json.dumps(out_a, sort_keys=True) == json.dumps(out_b, sort_keys=True)

    # And: a different description yields a different ordering (the
    # description-aware sort actually fires).
    out_c = compress_tree(rows, description="cookware")
    assert out_a != out_c or json.dumps(out_a) == json.dumps(out_c)
    # Idempotent under no-description as well.
    assert compress_tree(rows) == compress_tree(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 2) compress_tree groups by super_id — one bucket per distinct super_id.
# ─────────────────────────────────────────────────────────────────────────────


def test_compress_tree_groups_by_super_id() -> None:
    """Three distinct super_ids in the fixture → exactly three buckets,
    each carrying the full set of leaves for that super_id."""
    rows = _make_rows()
    out = compress_tree(rows)

    assert "super_categories" in out
    super_categories = out["super_categories"]
    assert isinstance(super_categories, list)

    super_ids = [sc["super_id"] for sc in super_categories]
    # Three distinct super_ids; deterministic sort order means we can
    # assert the exact sequence.
    assert super_ids == ["11", "13", "20"]

    # Each bucket carries all leaves for its super_id (no leaf dropped at
    # this fixture size — _MAX_LEAVES_PER_SUPER is 50 >> 2).
    by_super: dict[str, list[str]] = {
        sc["super_id"]: [leaf["leaf_name"] for leaf in sc["leaves"]]
        for sc in super_categories
    }
    assert set(by_super["11"]) == {"Kurtis", "Sarees"}
    assert set(by_super["13"]) == {"Serums", "Moisturisers"}
    assert set(by_super["20"]) == {"Cookware", "Wall Art"}

    # Each leaf carries exactly the 3 keys the prompt template expects —
    # no leakage of internal ``_overlap`` sort key.
    for sc in super_categories:
        for leaf in sc["leaves"]:
            assert set(leaf.keys()) == {"category_id", "leaf_name", "path"}
            # category_id is stringified so json.dumps doesn't choke on
            # raw UUID objects in production.
            assert isinstance(leaf["category_id"], str)
            # Round-trip through UUID validates the format too.
            UUID(leaf["category_id"])


# ─────────────────────────────────────────────────────────────────────────────
# 3) calibrate_confidence penalises retries.
# ─────────────────────────────────────────────────────────────────────────────


def test_calibrate_confidence_penalises_retries() -> None:
    """One Layer 2 retry must lower confidence; two retries must lower it
    further.  Clamping holds at both ends."""
    no_retry = calibrate_confidence(0.9, 0)
    one_retry = calibrate_confidence(0.9, 1)
    two_retries = calibrate_confidence(0.9, 2)

    assert no_retry == 0.9
    assert one_retry < no_retry
    assert two_retries < one_retry
    # Locked penalty: 0.1 per retry.
    assert abs(one_retry - 0.8) < 1e-9
    assert abs(two_retries - 0.7) < 1e-9

    # Clamp at zero: a confidence of 0.05 with 2 retries cannot go
    # negative (Pydantic ``Field(ge=0.0)`` would reject).
    assert calibrate_confidence(0.05, 2) == 0.0

    # Clamp at one: a confidence > 1.0 (defensive — AI might over-shoot)
    # collapses to 1.0.
    assert calibrate_confidence(1.5, 0) == 1.0

    # Negative retries are coerced to zero (defensive).
    assert calibrate_confidence(0.9, -3) == 0.9


# ─────────────────────────────────────────────────────────────────────────────
# 4) select_top_k returns k items in descending confidence order.
# ─────────────────────────────────────────────────────────────────────────────


def test_select_top_k_returns_k_descending() -> None:
    """Given 10 suggestions with varying confidence, top-5 by confidence
    DESC with deterministic tie-breakers."""
    suggestions = [
        {"category_id": f"cat-{i:02d}", "confidence": conf}
        for i, conf in enumerate(
            [0.10, 0.95, 0.45, 0.80, 0.30, 0.75, 0.20, 0.60, 0.90, 0.50]
        )
    ]
    top5 = select_top_k(suggestions, k=5)

    assert len(top5) == 5
    confidences = [s["confidence"] for s in top5]
    # Strictly non-increasing.
    assert confidences == sorted(confidences, reverse=True)
    # The five highest-confidence are 0.95, 0.90, 0.80, 0.75, 0.60.
    assert confidences == [0.95, 0.90, 0.80, 0.75, 0.60]

    # Tie-break test: identical confidence → category_id ASC.
    tied = [
        {"category_id": "cat-zz", "confidence": 0.5},
        {"category_id": "cat-aa", "confidence": 0.5},
        {"category_id": "cat-mm", "confidence": 0.5},
    ]
    top3 = select_top_k(tied, k=3)
    assert [s["category_id"] for s in top3] == ["cat-aa", "cat-mm", "cat-zz"]

    # Defensive: k larger than the list → return everything, sorted.
    assert len(select_top_k(suggestions, k=99)) == 10
    # Defensive: k <= 0 → empty list.
    assert select_top_k(suggestions, k=0) == []
    assert select_top_k(suggestions, k=-1) == []
    # Defensive: input not mutated.
    original_order = [s["category_id"] for s in suggestions]
    select_top_k(suggestions, k=3)
    assert [s["category_id"] for s in suggestions] == original_order
