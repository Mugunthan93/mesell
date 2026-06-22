"""CAT-BE-22 / CAT-BE-23 / CAT-BE-24 / CAT-BE-25 / CAT-BE-26
Gap-fill for ``app.modules.category.picker`` pure-function helpers.

What this file adds (does NOT duplicate test_picker_helpers.py):
- CAT-BE-22  compress_tree caps per-super at _MAX_LEAVES_PER_SUPER (50)
- CAT-BE-23  compress_tree description-trigram prioritisation: overlapping
             leaves rank first within their super
- CAT-BE-24  compress_tree deterministic on empty rows + identical input
             → identical JSON bytes (cache-key invariant)
- CAT-BE-25  calibrate_confidence clamp at both ends:
             0 retries = no-op, ≥2 retries ≤ 0.65, negative → clamped
- CAT-BE-26  select_top_k tie-break by category_id ASC (cache invariant)

No I/O, no DB, no Valkey.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from app.modules.category.picker import (
    _MAX_LEAVES_PER_SUPER,
    calibrate_confidence,
    compress_tree,
    select_top_k,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _Row:
    id: str
    super_id: str
    super_name: str
    path: str
    leaf_name: str


def _make_large_bucket(n: int, super_id: str = "s1") -> list[_Row]:
    """Return n leaves all in the same super-category."""
    return [
        _Row(
            id=f"aaaa{i:08d}-0000-0000-0000-aaaaaaaaaaaa",
            super_id=super_id,
            super_name="Women Fashion",
            path=f"Women Fashion > Leaf {i}",
            leaf_name=f"Leaf {i}",
        )
        for i in range(n)
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-22  compress_tree caps per super at _MAX_LEAVES_PER_SUPER
# ─────────────────────────────────────────────────────────────────────────────

def test_compress_tree_caps_per_super() -> None:
    """CAT-BE-22: >_MAX_LEAVES_PER_SUPER (50) leaves in one super → exactly 50 emitted."""
    rows = _make_large_bucket(_MAX_LEAVES_PER_SUPER + 20, super_id="s1")
    result = compress_tree(rows)

    super_cats = result["super_categories"]
    assert len(super_cats) == 1, "Expected exactly one super-category bucket"
    leaves = super_cats[0]["leaves"]
    assert len(leaves) == _MAX_LEAVES_PER_SUPER, (
        f"Expected {_MAX_LEAVES_PER_SUPER} leaves (cap), got {len(leaves)}"
    )


def test_compress_tree_does_not_cap_under_limit() -> None:
    """compress_tree does NOT drop leaves when count is below the cap."""
    rows = _make_large_bucket(_MAX_LEAVES_PER_SUPER - 5, super_id="s2")
    result = compress_tree(rows)
    leaves = result["super_categories"][0]["leaves"]
    assert len(leaves) == _MAX_LEAVES_PER_SUPER - 5, (
        f"Expected {_MAX_LEAVES_PER_SUPER - 5} leaves, got {len(leaves)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-23  description-trigram prioritisation within a super
# ─────────────────────────────────────────────────────────────────────────────

def test_compress_tree_description_prioritises_overlapping_leaves() -> None:
    """CAT-BE-23: leaves whose leaf_name/path overlaps the description rank first."""
    rows = [
        _Row(
            id="bbbb0001-0000-0000-0000-bbbbbbbbbbbb",
            super_id="s1",
            super_name="Women Fashion",
            path="Women Fashion > Sarees",
            leaf_name="Sarees",
        ),
        _Row(
            id="bbbb0002-0000-0000-0000-bbbbbbbbbbbb",
            super_id="s1",
            super_name="Women Fashion",
            path="Women Fashion > Kurtis",
            leaf_name="Kurtis",
        ),
        _Row(
            id="bbbb0003-0000-0000-0000-bbbbbbbbbbbb",
            super_id="s1",
            super_name="Women Fashion",
            path="Women Fashion > Bags",
            leaf_name="Bags",
        ),
    ]

    # Description has "kurti" — strong trigram overlap with "Kurtis".
    result = compress_tree(rows, description="cotton kurti printed")

    leaves = result["super_categories"][0]["leaves"]
    leaf_names = [leaf["leaf_name"] for leaf in leaves]

    # "Kurtis" must rank ahead of "Sarees" and "Bags" (0-overlap).
    kurti_index = leaf_names.index("Kurtis")
    sarees_index = leaf_names.index("Sarees")
    bags_index = leaf_names.index("Bags")

    assert kurti_index < sarees_index, (
        f"Kurtis (matching description) must rank before Sarees; order={leaf_names}"
    )
    assert kurti_index < bags_index, (
        f"Kurtis must rank before Bags; order={leaf_names}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-24  compress_tree deterministic + empty rows edge case
# ─────────────────────────────────────────────────────────────────────────────

def test_compress_tree_empty_rows_returns_empty_dict() -> None:
    """CAT-BE-24a: empty row iterable → {super_categories: []} deterministically."""
    result_a = compress_tree([])
    result_b = compress_tree([])

    assert result_a == {"super_categories": []}, (
        f"Expected empty super_categories list, got {result_a}"
    )
    # Identical JSON bytes.
    assert json.dumps(result_a, sort_keys=True) == json.dumps(result_b, sort_keys=True), (
        "Empty-input result is not deterministic"
    )


def test_compress_tree_identical_input_identical_json_bytes() -> None:
    """CAT-BE-24b: identical (rows, description) → bit-identical json.dumps output."""
    rows = _make_large_bucket(10, super_id="s1")
    desc = "cotton kurti for daily wear"

    out_a = compress_tree(rows, description=desc)
    out_b = compress_tree(rows, description=desc)

    json_a = json.dumps(out_a, sort_keys=True)
    json_b = json.dumps(out_b, sort_keys=True)
    assert json_a == json_b, (
        "compress_tree is not deterministic for identical (rows, description)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-25  calibrate_confidence clamp both ends
# ─────────────────────────────────────────────────────────────────────────────

def test_calibrate_confidence_zero_retries_no_change() -> None:
    """CAT-BE-25a: 0 retries → confidence unchanged (no penalty applied)."""
    assert calibrate_confidence(0.75, 0) == pytest.approx(0.75)
    assert calibrate_confidence(1.0, 0) == pytest.approx(1.0)
    assert calibrate_confidence(0.0, 0) == pytest.approx(0.0)


def test_calibrate_confidence_two_retries_at_most_065() -> None:
    """CAT-BE-25b: 2 retries → confidence ≤ 0.65 (2 × 0.1 penalty)."""
    # Start from 0.85 (common post-ranker value) → 0.85 - 0.20 = 0.65
    result = calibrate_confidence(0.85, 2)
    assert result <= 0.65, f"Expected ≤0.65 with 2 retries, got {result}"
    assert result == pytest.approx(0.65)


def test_calibrate_confidence_clamp_below_zero() -> None:
    """CAT-BE-25c: penalty that would push below 0.0 → clamped to 0.0."""
    assert calibrate_confidence(0.05, 3) == pytest.approx(0.0)
    assert calibrate_confidence(0.0, 2) == pytest.approx(0.0)


def test_calibrate_confidence_clamp_above_one() -> None:
    """CAT-BE-25d: raw confidence > 1.0 → clamped to 1.0."""
    assert calibrate_confidence(1.5, 0) == pytest.approx(1.0)
    assert calibrate_confidence(2.0, 0) == pytest.approx(1.0)


def test_calibrate_confidence_negative_retries_treated_as_zero() -> None:
    """CAT-BE-25e: negative retries → same as 0 retries (defensive)."""
    assert calibrate_confidence(0.8, -5) == pytest.approx(0.8)


# ─────────────────────────────────────────────────────────────────────────────
# CAT-BE-26  select_top_k tie-break determinism (cache-key invariant)
# ─────────────────────────────────────────────────────────────────────────────

def test_select_top_k_tie_break_by_category_id_asc() -> None:
    """CAT-BE-26: equal-confidence suggestions are sorted by category_id ASC."""
    # 5 suggestions all at exactly the same confidence.
    tied = [
        {"category_id": "zzz", "confidence": 0.7},
        {"category_id": "aaa", "confidence": 0.7},
        {"category_id": "mmm", "confidence": 0.7},
        {"category_id": "bbb", "confidence": 0.7},
        {"category_id": "ccc", "confidence": 0.7},
    ]
    top3 = select_top_k(tied, k=3)
    ids = [s["category_id"] for s in top3]
    assert ids == ["aaa", "bbb", "ccc"], (
        f"Tie-break must be category_id ASC; got {ids}"
    )


def test_select_top_k_is_stable_on_multiple_calls() -> None:
    """CAT-BE-26 cache invariant: same input → same output on repeated calls."""
    suggestions = [
        {"category_id": f"id-{i:02d}", "confidence": 0.5}
        for i in range(8)
    ]
    run1 = [s["category_id"] for s in select_top_k(suggestions, k=5)]
    run2 = [s["category_id"] for s in select_top_k(suggestions, k=5)]
    assert run1 == run2, (
        f"select_top_k must be deterministic across calls; run1={run1}, run2={run2}"
    )


def test_select_top_k_does_not_mutate_input() -> None:
    """select_top_k must not mutate its input list (sorted copy contract)."""
    suggestions = [
        {"category_id": "z", "confidence": 0.9},
        {"category_id": "a", "confidence": 0.5},
    ]
    original_order = [s["category_id"] for s in suggestions]
    select_top_k(suggestions, k=2)
    assert [s["category_id"] for s in suggestions] == original_order, (
        "select_top_k must not mutate the input list"
    )
