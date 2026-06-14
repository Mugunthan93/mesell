"""``category`` internal domain types — frozen dataclasses per §9.F (LOCKED 2026-06-05).

These are MODULE-INTERNAL types.  The wire shapes consumed by the router
live in :mod:`app.modules.category.schemas` (owned by api-routes-builder).
The picker helpers in :mod:`app.modules.category.picker` consume the same
``CategoryRow`` shape duck-typed.

Per §9.F, these dataclasses are intentionally NOT Pydantic — they are
internal repository return types, not request/response shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class CategoryRow:
    """Mirrors a single ``categories`` table row.

    Returned by :mod:`app.modules.category.repository`.  Consumed by
    :func:`app.modules.category.picker.compress_tree` (via duck-typed
    attribute access) and by the service layer in-process tree assembly.
    """

    id: UUID
    meesho_leaf_id: str
    super_id: str
    super_name: str
    path: str
    leaf_name: str
    template_id: UUID
    commission_pct: Decimal | None


@dataclass(frozen=True)
class SuperCategoryInfo:
    """Distinct ``super_id`` aggregate row.

    Cross-module return type for ``customer.service.set_active_categories``
    (per §2.D + §8.C).  ``leaf_count`` is diagnostic (UI hints + telemetry)
    — NOT used to filter super_categories out per §12.3 long-tail
    inclusion.
    """

    super_id: str
    super_name: str
    leaf_count: int


__all__ = ["CategoryRow", "SuperCategoryInfo"]
