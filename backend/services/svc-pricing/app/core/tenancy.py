"""Tenant isolation helpers — app-level ``user_id`` scoping.

Vendored from the monolith ``app.core.tenancy`` (BACKEND_ARCHITECTURE.md §4.C).

pricing's ``pricing_calcs`` table carries NO ``user_id`` column (§12-PRICING-D4);
tenant isolation is enforced UPSTREAM at the catalog ``assert_product_ownership``
HTTP shim (§0.6) BEFORE any pricing_calcs read or write.  These helpers are
vendored for chain-shape parity + the ``TenantViolationError`` the vendored core
layer may raise; pricing's repository does NOT call ``scope_to_user`` (the
``products`` JOIN was rewritten out per §0.6 — the ownership shim provides
user-scoping).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.sql import Select

from app.core.errors import MeesellError

logger = logging.getLogger(__name__)


class TenantViolationError(MeesellError):
    """Raised when a record's ``user_id`` does not match the caller (403)."""

    code = "tenancy.cross_user_access"
    status_code = 403
    validation_message_id = "tenancy.cross_user_access"


def assert_owned(record: Any, user_id: UUID) -> None:
    """Raise :class:`TenantViolationError` unless ``record.user_id == user_id``."""
    if record is None:
        logger.warning("assert_owned called with None record (user_id=%s)", user_id)
        raise TenantViolationError()
    record_owner = getattr(record, "user_id", None)
    if record_owner != user_id:
        logger.warning(
            "tenancy violation: record.user_id=%s, caller=%s",
            record_owner,
            user_id,
        )
        raise TenantViolationError()


def scope_to_user(
    query: Select,
    user_id: UUID,
    column: str = "user_id",
) -> Select:
    """Add ``WHERE <column> = :user_id`` to a SQLAlchemy ``Select``.

    Raises ``ValueError`` if the query's primary entity does not expose the
    requested ``column`` (surfaced at construction time, before the query
    reaches the database).
    """
    descriptors = query.column_descriptions
    if not descriptors:
        raise ValueError("scope_to_user: query has no column descriptions")
    entity = descriptors[0].get("entity") or descriptors[0].get("type")
    if entity is None:
        raise ValueError("scope_to_user: cannot resolve primary entity from query")
    try:
        col = getattr(entity, column)
    except AttributeError as exc:
        raise ValueError(
            f"scope_to_user: entity {entity!r} has no column {column!r}"
        ) from exc
    return query.where(col == user_id)


__all__ = [
    "TenantViolationError",
    "assert_owned",
    "scope_to_user",
]
