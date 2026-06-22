"""``monitor`` module exceptions.

Kept deliberately minimal for Wave-2 Unit C — only the one exception the
gate orchestrator raises when a category id cannot be resolved to its
Meesho scrape inputs.
"""

from __future__ import annotations


class CategoryNotFoundError(Exception):
    """Raised when ``category_id`` has no matching row in ``categories``.

    The gate resolves a category's Meesho scrape inputs
    (``meesho_leaf_id`` → ``sscat_id``, ``leaf_name`` → ``category_name``)
    before calling the live scrape. A missing row is an operator-level
    error (the monitor was handed a stale / unknown id) — the gate clears
    its in-flight Valkey claim and lets this propagate.
    """

    def __init__(self, category_id: str) -> None:
        self.category_id = category_id
        super().__init__(f"category {category_id} not found in categories table")
