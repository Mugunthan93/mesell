"""Meesho-data helper functions."""

import pytest

from app.data import (
    all_banned_words,
    get_category_config,
    is_valid_category,
    load_attributes,
    load_categories,
    load_shipping_slabs,
)

pytestmark = pytest.mark.unit


def test_taxonomy_has_at_least_50_leaves():
    cats = load_categories()
    leaves = sum(len(leafs) for groups in cats.values() for leafs in groups.values())
    assert leaves >= 50, f"expected ≥50 leaf categories, got {leaves}"


def test_banned_words_has_at_least_100_entries():
    assert len(all_banned_words()) >= 100


def test_known_category_returns_required_attributes():
    cfg = get_category_config("Kurtis")
    assert "fabric" in cfg["required"]
    assert "fit" in cfg["required"]


def test_unknown_category_falls_back_to_default():
    cfg = get_category_config("This Category Does Not Exist")
    assert cfg == get_category_config("_default")


def test_is_valid_category_truth_table():
    assert is_valid_category("Kurtis") is True
    assert is_valid_category("Sarees") is True
    assert is_valid_category("Earphones") is True
    assert is_valid_category("Quantum Foam") is False
    assert is_valid_category("") is False


def test_shipping_slabs_monotonic():
    slabs = load_shipping_slabs()["slabs"]
    weights = [s["max_grams"] for s in slabs]
    assert weights == sorted(weights), "slabs must be sorted by ascending weight"
    # All zones present per slab.
    for s in slabs:
        for zone in ("local", "regional", "national", "special"):
            assert zone in s


def test_attributes_each_category_lists_required_keys():
    attrs = load_attributes()
    assert "_default" in attrs
    for name, cfg in attrs.items():
        assert "required" in cfg and isinstance(cfg["required"], list)
        assert "default_return_rate" in cfg
        assert 0.0 <= cfg["default_return_rate"] <= 1.0
