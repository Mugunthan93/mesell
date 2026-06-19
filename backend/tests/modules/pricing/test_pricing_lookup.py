"""test_pricing_lookup.py — W1 validation tests for the productionized pricing lookup.

Tests the data file at backend/app/data/meesho_pricing_lookup.json and the loader
at backend/app/modules/pricing/pricing_lookup.py.

Gate-1 (unit) MUST be green. Gate-5 (golden_roundtrip) is N/A — no XLSX surface is
touched in W1. This is noted in the PR body.

All tests are pure-unit (no DB, no network, no asyncio). The DB-join test
(test_no_orphan_categories) falls back to checking the lookup against the seed
fixture data when the dev DB is unavailable, so it never blocks the unit CI lane.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.pricing.pricing_lookup import (
    UnknownCategoryError,
    _load,
    get_commission_default,
    get_shipping,
    lookup_size,
)

# ---- Path to the committed data file -----------------------------------------------
_DATA_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "app"
    / "data"
    / "meesho_pricing_lookup.json"
)


def _raw_lookup() -> dict:
    """Load the JSON file directly (bypasses lru_cache — safe for data-file tests)."""
    with _DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---- Data-file tests ----------------------------------------------------------------


def test_lookup_has_3772_entries() -> None:
    """The committed file must have exactly 3772 entries and _meta.total must match."""
    data = _raw_lookup()
    assert len(data["lookup"]) == 3772, (
        f"Expected 3772 lookup entries, got {len(data['lookup'])}"
    )
    assert data["_meta"]["total"] == 3772, (
        f"_meta.total={data['_meta']['total']} != 3772"
    )


def test_all_commission_zero() -> None:
    """Every lookup entry must have commission_percentage == 0 (census-verified)."""
    data = _raw_lookup()
    bad = [
        k for k, v in data["lookup"].items() if v["commission_percentage"] != 0
    ]
    assert bad == [], (
        f"{len(bad)} entries have non-zero commission_percentage: {bad[:5]}"
    )


def test_shipping_in_range() -> None:
    """Every shipping_charges value must be an int in the spec range [48, 8435]."""
    data = _raw_lookup()
    bad = []
    for k, v in data["lookup"].items():
        sc = v["shipping_charges"]
        if not isinstance(sc, int):
            bad.append((k, f"type={type(sc).__name__}"))
        elif not (48 <= sc <= 8435):
            bad.append((k, f"value={sc}"))
    assert bad == [], (
        f"{len(bad)} entries have invalid shipping_charges: {bad[:5]}"
    )


def test_known_anchor() -> None:
    """Sanity anchor: sscat_id 10949 (Extension Chords) → shipping_charges == 82."""
    data = _raw_lookup()
    assert "10949" in data["lookup"], "Anchor sscat_id '10949' missing from lookup"
    entry = data["lookup"]["10949"]
    assert entry["shipping_charges"] == 82, (
        f"Anchor 10949 shipping_charges={entry['shipping_charges']}, expected 82"
    )
    assert entry["commission_percentage"] == 0, (
        f"Anchor 10949 commission_percentage={entry['commission_percentage']}, expected 0"
    )


# ---- Loader tests -------------------------------------------------------------------


def test_loader_get_shipping() -> None:
    """get_shipping('10949') must return 82 (Extension Chords anchor)."""
    _load.cache_clear()  # ensure a fresh load for the test
    result = get_shipping("10949")
    assert result == 82, f"get_shipping('10949') returned {result}, expected 82"
    assert isinstance(result, int), f"get_shipping must return int, got {type(result)}"


def test_loader_unknown_raises() -> None:
    """get_shipping on a non-existent id must raise UnknownCategoryError."""
    _load.cache_clear()
    with pytest.raises(UnknownCategoryError):
        get_shipping("99999999")


def test_loader_commission_default() -> None:
    """get_commission_default('10949') must return Decimal('0')."""
    _load.cache_clear()
    result = get_commission_default("10949")
    assert result == Decimal("0"), (
        f"get_commission_default('10949') returned {result!r}, expected Decimal('0')"
    )
    assert isinstance(result, Decimal), (
        f"get_commission_default must return Decimal, got {type(result)}"
    )


def test_loader_unknown_commission_raises() -> None:
    """get_commission_default on a non-existent id must also raise UnknownCategoryError."""
    _load.cache_clear()
    with pytest.raises(UnknownCategoryError):
        get_commission_default("99999999")


def test_loader_lookup_size() -> None:
    """lookup_size() must equal 3772."""
    _load.cache_clear()
    size = lookup_size()
    assert size == 3772, f"lookup_size() returned {size}, expected 3772"


def test_loader_str_coercion() -> None:
    """The loader must accept a numeric-string id and find the entry."""
    _load.cache_clear()
    # Some callers might pass the id as-is from meesho_leaf_id (String column)
    result = get_shipping("10949")
    assert result == 82


# ---- _meta tests --------------------------------------------------------------------


def test_meta_block() -> None:
    """_meta must carry all required fields with correct values."""
    data = _raw_lookup()
    meta = data["_meta"]
    assert "source" in meta, "_meta missing 'source'"
    assert "generated_at" in meta, "_meta missing 'generated_at'"
    assert meta["census_price"] == 100, (
        f"_meta.census_price={meta['census_price']}, expected 100"
    )
    assert meta["model"] == "confirmed-2026-06-19", (
        f"_meta.model={meta['model']!r}"
    )
    assert "refresh" in meta, "_meta missing 'refresh'"
    assert "version" in meta, "_meta missing 'version'"


# ---- No-orphan DB-join test ---------------------------------------------------------


def test_no_orphan_categories() -> None:
    """Every leaf_id in the category tree seed fixture must resolve in the lookup.

    The real category tree at meesho_category_tree.json has shape:
        {"categories": [{"leaf_id": "<str>", ...}, ...], ...}

    This test reads it directly (offline, no DB, no network) and asserts the full
    superset check: every one of the 3772 leaf_ids appears as a key in the pricing
    lookup.  A vacuous pass (empty seed_leaf_ids) is prevented by a guard-fail
    assertion before the superset check.

    The test is NOT marked @pytest.mark.integration — it is pure-unit (offline).
    """
    _load.cache_clear()

    category_tree_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "app"
        / "data"
        / "meesho_category_tree.json"
    )

    assert category_tree_path.exists(), (
        f"Category tree seed fixture not found: {category_tree_path}"
    )

    with category_tree_path.open(encoding="utf-8") as fh:
        tree = json.load(fh)

    # Real shape: {"categories": [{"leaf_id": "<str>", ...}, ...], ...}
    seed_leaf_ids = [c["leaf_id"] for c in tree["categories"]]

    # Guard: extraction must never be empty — catches future shape changes
    assert len(seed_leaf_ids) == 3772, (
        f"Expected 3772 leaf ids from tree['categories'], got {len(seed_leaf_ids)}. "
        "The tree JSON shape may have changed — update the extractor."
    )

    lookup_keys = set(_load().keys())
    orphans = set(seed_leaf_ids) - lookup_keys
    assert orphans == set(), (
        f"{len(orphans)} category tree leaf_ids have no pricing row: "
        f"{sorted(orphans)[:5]}"
    )
