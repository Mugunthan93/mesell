"""``is_advanced`` allowlist per §5A.F + founder ruling D2 (``§0.F``).

The locked V1 allowlist for fields rendered behind the wizard's
"Advanced fields" expandable section. Widening this set requires a §5A
amendment block (append-only audit trail) before any seed script or
template builder may emit ``is_advanced=True`` for a new ``canonical_name``.

Source-of-truth cross-references:
  - ``BACKEND_ARCHITECTURE.md`` §5A.F (V1 allowlist: ``{"group_id"}``).
  - ``meesell-database-builder`` memory line 395 (locked at line 84 of
    ``scripts/build_template_schemas.py``).
  - 3,566 templates carry ``group_id`` with ``is_advanced=True``;
    0 templates have any other ``is_advanced=True`` field per
    database-builder memory line 396.

Tests assert the cardinality is exactly 1 (sub-session 2 G1 lock).
"""

from __future__ import annotations

from typing import Final

#: The V1 ``is_advanced`` allowlist — exactly one element. Widening
#: requires §5A amendment per §5A.F locked rule.
ADVANCED_CANONICAL_NAMES: Final[frozenset[str]] = frozenset({"group_id"})


__all__ = ["ADVANCED_CANONICAL_NAMES"]
