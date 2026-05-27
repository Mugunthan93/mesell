"""Static data files + helpers for Meesho catalog metadata."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=8)
def _load(filename: str) -> Any:
    return json.loads((DATA_DIR / filename).read_text())


def load_categories() -> dict:
    return _load("meesho_categories.json")


def load_attributes() -> dict:
    return _load("category_attributes.json")


def load_banned_words() -> dict:
    return _load("banned_words.json")


def load_shipping_slabs() -> dict:
    return _load("meesho_shipping_slabs.json")


def all_banned_words() -> list[str]:
    data = load_banned_words()
    flat: list[str] = []
    for words in data.values():
        flat.extend(w.lower() for w in words)
    return flat


def get_category_config(category_name: str) -> dict:
    """Return required/optional attributes + default return rate for a category."""
    attrs = load_attributes()
    return attrs.get(category_name) or attrs["_default"]


def is_valid_category(category_name: str) -> bool:
    """True if ``category_name`` appears anywhere in the Meesho taxonomy."""
    for groups in load_categories().values():
        for leaves in groups.values():
            if category_name in leaves:
                return True
    return False
