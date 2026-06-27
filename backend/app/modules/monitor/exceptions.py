"""``monitor`` module exceptions.

Two exceptions:

* :class:`CategoryNotFoundError` — Wave-2 gate: the category id cannot be
  resolved to its Meesho scrape inputs (no ``categories`` row).
* :class:`CategorySnapshotNotFoundError` — Wave-3 serving: the category has
  no ``category_snapshots`` row yet (never scraped), so there is nothing to
  serve from the read-through cache / DB fallback.
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


class CategorySnapshotNotFoundError(Exception):
    """Raised when a category has no ``category_snapshots`` row to serve.

    The Wave-3 serving read (``get_served_category_data``) falls back to the
    DB when the read-through cache misses. If there is also no snapshot row
    (the category has never been scraped), there is nothing to serve — the
    caller surfaces this as a not-found condition.
    """

    def __init__(self, category_id: str) -> None:
        self.category_id = category_id
        super().__init__(
            f"category {category_id} has no snapshot in category_snapshots table"
        )
