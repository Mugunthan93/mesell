"""Tests for diff_category_rules.py — Unit B of the category change monitor.

All tests are stdlib-only (no DB, no network, no Playwright).
Three main verdict cases:
    1. hash_equal_pass       — identical hashes → PASS, empty diff, no dimension traversal
    2. compliance_add        — compliance_fields has a new required field → REVIEW_REQUIRED
                               with correct per-dimension added set
    3. truncated_block       — one snapshot is a partial/truncated projection → BLOCK

Additional cases:
    4. identical_dims_pass   — no hash provided, but dims are identical → PASS
    5. shipping_change       — shipping_charges changed → REVIEW_REQUIRED
    6. banned_words_add      — a new banned word added → REVIEW_REQUIRED
    7. block_flag_precedence — BLOCK trumps REVIEW_REQUIRED when both conditions apply
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Add backend/ to sys.path so imports resolve correctly inside the worktree
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from scripts.diff_category_rules import (  # type: ignore[import]
    VERDICT_BLOCK,
    VERDICT_PASS,
    VERDICT_REVIEW,
    diff_category_snapshot,
    render_diff_report,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

# Fixtures live at tests/fixtures/category_monitor/ (one level above tests/scripts/)
_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "category_monitor"


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _full_dims(
    required: list[str] | None = None,
    optional: list[str] | None = None,
    shipping_charges: int = 55,
    gst_percentage: int = 5,
    branded: list[str] | None = None,
    trademark: list[str] | None = None,
    transfer_price: float = 68.0,
    platform_fee: float = 0.0,
    sscat_id: str = "46677c24",
) -> dict[str, Any]:
    """Build a fully-populated dimensions dict for use in parameterised tests."""
    return {
        "compliance_fields": {
            "required": required if required is not None else ["fabric", "fit"],
            "optional": optional if optional is not None else ["wash_care"],
        },
        "shipping_slab": {
            "shipping_charges": shipping_charges,
            "gst_percentage": gst_percentage,
        },
        "banned_words": {
            "branded": branded if branded is not None else ["nike", "adidas"],
            "trademark": trademark if trademark is not None else ["patented"],
        },
        "cost_fields": {
            "transfer_price": transfer_price,
            "platform_fee": platform_fee,
            "sscat_id": sscat_id,
        },
    }


# ---------------------------------------------------------------------------
# Test 1: hash-equal short-circuit → PASS
# ---------------------------------------------------------------------------


def test_hash_equal_pass() -> None:
    """When prev_hash == new_hash, diff returns PASS immediately with empty sets."""
    same_hash = "a" * 64
    new_dims = _full_dims()
    prev_dims = _full_dims(required=["totally", "different"])  # content differs but hash is same

    result = diff_category_snapshot(
        new_dims,
        prev_dims,
        prev_hash=same_hash,
        new_hash=same_hash,
    )

    assert result["verdict"] == VERDICT_PASS, "hash-equal must yield PASS"
    assert result["hash_equal"] is True, "hash_equal flag must be set"
    assert result["block_reasons"] == [], "no block reasons on hash-equal PASS"
    assert result["review_reasons"] == [], "no review reasons on hash-equal PASS"
    # Dimension diffs must be empty (short-circuit before any dimension traversal)
    assert result["compliance_diff"] == {}
    assert result["shipping_diff"] == {}
    assert result["banned_words_diff"] == {}
    assert result["cost_fields_diff"] == {}


# ---------------------------------------------------------------------------
# Test 2: compliance_fields add → REVIEW_REQUIRED
# ---------------------------------------------------------------------------


def test_compliance_add_review_required() -> None:
    """New required field 'color' in new_dims → REVIEW_REQUIRED with correct added set."""
    prev = _full_dims(required=["fabric", "fit", "sleeve_length"])
    new = _full_dims(required=["fabric", "fit", "sleeve_length", "color"])  # 'color' is new

    result = diff_category_snapshot(new, prev)

    assert result["verdict"] == VERDICT_REVIEW, (
        f"Expected REVIEW_REQUIRED for compliance add, got {result['verdict']}"
    )
    assert result["hash_equal"] is False
    assert "compliance_fields changed" in result["review_reasons"]

    cd = result["compliance_diff"]
    assert "color" in cd["required_added"], "'color' must appear in required_added"
    assert cd["required_removed"] == [], "nothing was removed"


def test_compliance_add_from_fixture() -> None:
    """v2 fixture has 'color' added to required vs v1 → REVIEW_REQUIRED."""
    v1 = _load_fixture("cat_46677c24_v1.json")
    v2 = _load_fixture("cat_46677c24_v2.json")

    result = diff_category_snapshot(v2, v1)

    assert result["verdict"] == VERDICT_REVIEW, (
        f"Expected REVIEW_REQUIRED from v1→v2 fixture diff, got {result['verdict']}"
    )
    cd = result["compliance_diff"]
    assert "color" in cd["required_added"], "'color' field must show as required_added"


# ---------------------------------------------------------------------------
# Test 3: truncated fixture → BLOCK
# ---------------------------------------------------------------------------


def test_truncated_dims_block() -> None:
    """A truncated/partial new_dims missing required dimension keys → BLOCK."""
    truncated = _load_fixture("cat_46677c24_truncated.json")
    prev = _full_dims()

    result = diff_category_snapshot(truncated, prev)

    assert result["verdict"] == VERDICT_BLOCK, (
        f"Expected BLOCK for truncated new_dims, got {result['verdict']}"
    )
    assert result["block_reasons"], "block_reasons must be non-empty for truncated projection"
    # Must flag the new_dims as partial
    assert any("new_dims" in r for r in result["block_reasons"]), (
        "block reason must mention new_dims as partial"
    )


def test_truncated_prev_dims_block() -> None:
    """A truncated prev_dims → BLOCK (prev snapshot corruption is also anomalous)."""
    truncated = _load_fixture("cat_46677c24_truncated.json")
    new = _full_dims()

    result = diff_category_snapshot(new, truncated)

    assert result["verdict"] == VERDICT_BLOCK, (
        f"Expected BLOCK for truncated prev_dims, got {result['verdict']}"
    )
    assert any("prev_dims" in r for r in result["block_reasons"]), (
        "block reason must mention prev_dims as partial"
    )


# ---------------------------------------------------------------------------
# Test 4: identical full dims → PASS (no hash provided)
# ---------------------------------------------------------------------------


def test_identical_dims_pass() -> None:
    """Same dims without hash shortcircuit → diff still yields PASS."""
    dims = _full_dims()

    result = diff_category_snapshot(dims, dims)

    assert result["verdict"] == VERDICT_PASS
    assert result["hash_equal"] is False  # no hash was provided
    assert result["block_reasons"] == []
    assert result["review_reasons"] == []
    assert result["compliance_diff"]["changed"] is False
    assert result["shipping_diff"]["changed"] is False
    assert result["banned_words_diff"]["changed"] is False
    assert result["cost_fields_diff"]["changed"] is False


# ---------------------------------------------------------------------------
# Test 5: shipping change → REVIEW_REQUIRED
# ---------------------------------------------------------------------------


def test_shipping_change_review_required() -> None:
    """shipping_charges changes from 55 to 80 → REVIEW_REQUIRED."""
    prev = _full_dims(shipping_charges=55)
    new = _full_dims(shipping_charges=80)

    result = diff_category_snapshot(new, prev)

    assert result["verdict"] == VERDICT_REVIEW
    assert "shipping_slab changed" in result["review_reasons"]

    sd = result["shipping_diff"]
    assert sd["shipping_charges_old"] == 55
    assert sd["shipping_charges_new"] == 80
    assert sd["shipping_delta"] == 25


# ---------------------------------------------------------------------------
# Test 6: banned_words add → REVIEW_REQUIRED
# ---------------------------------------------------------------------------


def test_banned_words_add_review_required() -> None:
    """New banned word 'lv' added in v2 → REVIEW_REQUIRED with correct added set."""
    v1 = _load_fixture("cat_46677c24_v1.json")
    v2 = _load_fixture("cat_46677c24_v2.json")

    result = diff_category_snapshot(v2, v1)

    bd = result["banned_words_diff"]
    assert bd["changed"] is True, "banned_words_diff.changed must be True"
    branded_diff = bd["per_key"].get("branded", {})
    assert "lv" in branded_diff.get("added", []), "'lv' must appear in branded.added"


# ---------------------------------------------------------------------------
# Test 7: BLOCK verdict overrides REVIEW_REQUIRED
# (hard threshold set to 0 for compliance_added to force BLOCK)
# ---------------------------------------------------------------------------


def test_block_trumps_review(monkeypatch: pytest.MonkeyPatch) -> None:
    """BLOCK condition (threshold=0) overrides REVIEW_REQUIRED for the same run."""
    # Force the compliance threshold to 0 so any addition is a BLOCK
    import scripts.diff_category_rules as _mod  # type: ignore[import]

    monkeypatch.setattr(_mod, "BLOCK_THRESHOLD_COMPLIANCE_ADDED", 0)

    prev = _full_dims(required=["fabric"])
    new = _full_dims(required=["fabric", "color"])  # 'color' added; also shipping changed

    # Also change shipping to confirm REVIEW would have fired
    new["shipping_slab"]["shipping_charges"] = 80

    result = diff_category_snapshot(new, prev)

    assert result["verdict"] == VERDICT_BLOCK, (
        "BLOCK must trump REVIEW_REQUIRED when a BLOCK threshold is crossed"
    )
    assert result["block_reasons"], "block_reasons must be populated"


# ---------------------------------------------------------------------------
# Test 8: render_diff_report produces non-empty markdown
# ---------------------------------------------------------------------------


def test_render_diff_report_review() -> None:
    """render_diff_report produces a non-empty markdown string for REVIEW_REQUIRED."""
    prev = _full_dims(required=["fabric"])
    new = _full_dims(required=["fabric", "color"])

    result = diff_category_snapshot(new, prev)
    report = render_diff_report(result, run_date="2026-06-22")

    assert isinstance(report, str), "render_diff_report must return a string"
    assert "2026-06-22" in report, "report must contain the run_date"
    assert "REVIEW_REQUIRED" in report, "report must contain the verdict"
    assert "color" in report, "report must mention the added field"


def test_render_diff_report_pass() -> None:
    """render_diff_report for PASS verdict mentions zero drift."""
    dims = _full_dims()
    result = diff_category_snapshot(dims, dims)
    report = render_diff_report(result)

    assert "PASS" in report
    assert "Zero drift" in report
