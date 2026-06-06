"""Tenant isolation helpers — app-level ``user_id`` scoping.

Per BACKEND_ARCHITECTURE.md §4.C, this module owns the two helpers that
every owned-table query path consumes:

* :func:`assert_owned` — instance-level ownership check (called after a
  ``db.get`` or single-row fetch).  Raises :class:`TenantViolationError`
  (status 403) on mismatch.
* :func:`scope_to_user` — adds ``WHERE <column> = :user_id`` to a
  SQLAlchemy ``Select``.  Replaces ad-hoc ``.where(Model.user_id == ...)``
  calls so that grep-for-``scope_to_user`` is the §19 CI anchor.

V1 enforcement is at the application layer; RLS is deferred to V1.5
per §0.F and ``MVP_ARCH §9``.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.sql import Select

from app.core.errors import MeesellError

logger = logging.getLogger(__name__)


class TenantViolationError(MeesellError):
    """Raised when a record's ``user_id`` does not match the caller.

    Status 403 — the resource exists but the caller is not allowed to
    touch it.  ``validation_message_id`` = ``"tenancy.cross_user_access"``.
    """

    code = "tenancy.cross_user_access"
    status_code = 403
    validation_message_id = "tenancy.cross_user_access"


def assert_owned(record: Any, user_id: UUID) -> None:
    """Raise :class:`TenantViolationError` unless ``record.user_id == user_id``.

    Used at every cross-module ownership-gate call site — for example
    ``catalog.service.assert_product_ownership(product_id, user_id)`` and
    ``image.service`` before any write to ``product_images``.

    Args:
        record: An ORM instance carrying a ``user_id`` attribute.  ``None``
            is treated as a mismatch (defensive — callers should have raised
            ``NotFoundError`` upstream rather than reaching here with None).
        user_id: The caller's authenticated ``user_id`` (from
            ``CurrentUser.user_id``).

    Raises:
        TenantViolationError: if the record's ``user_id`` differs from
            ``user_id`` or the record is None.
    """
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

    Usage::

        from sqlalchemy import select
        from app.shared.models import Product
        from app.core.tenancy import scope_to_user

        stmt = scope_to_user(select(Product), current_user.user_id)
        result = await db.execute(stmt)

    Args:
        query: A SQLAlchemy ``Select`` against an owned table.  The query's
            primary entity must expose the named ``column`` (default
            ``"user_id"``).
        user_id: The caller's authenticated ``user_id``.
        column: Override for tables that name the ownership column
            differently (defensive — V1 owned tables all use ``user_id``).

    Returns:
        A new ``Select`` with the additional WHERE clause.

    Raises:
        ValueError: if the query's primary entity does not expose the
            requested ``column``.  Surfaced at construction time, before
            the query reaches the database, so the developer sees the
            problem in tests.
    """
    # SQLAlchemy 2.0 — ``column_descriptions`` is the canonical way to
    # discover the primary entity of a Select.  Each descriptor is
    # ``{"name": ..., "type": <class>, "aliased": bool, "expr": <element>, "entity": <mapper>}``.
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
