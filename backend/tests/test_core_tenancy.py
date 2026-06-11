"""Tests for ``app.core.tenancy`` — assert_owned + scope_to_user."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import select

from app.core.tenancy import TenantViolationError, assert_owned, scope_to_user
from app.shared.models import Product

pytestmark = pytest.mark.unit


# ── 1. assert_owned happy path ────────────────────────────────────────────
def test_assert_owned_ok() -> None:
    @dataclass
    class Stub:
        user_id: uuid.UUID

    uid = uuid.uuid4()
    rec = Stub(user_id=uid)
    # No raise.
    assert_owned(rec, uid)


# ── 2. assert_owned mismatch raises ───────────────────────────────────────
def test_assert_owned_violation() -> None:
    @dataclass
    class Stub:
        user_id: uuid.UUID

    rec = Stub(user_id=uuid.uuid4())
    other = uuid.uuid4()
    with pytest.raises(TenantViolationError) as exc_info:
        assert_owned(rec, other)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "tenancy.cross_user_access"
    assert exc_info.value.validation_message_id == "tenancy.cross_user_access"


# ── 2b. assert_owned with None record raises ──────────────────────────────
def test_assert_owned_none_record_violation() -> None:
    with pytest.raises(TenantViolationError):
        assert_owned(None, uuid.uuid4())


# ── 3. scope_to_user adds WHERE clause ────────────────────────────────────
def test_scope_to_user_adds_where() -> None:
    uid = uuid.uuid4()
    stmt = scope_to_user(select(Product), uid)
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    # Expect a WHERE clause referencing user_id on the products table.
    assert "products.user_id" in compiled
    assert "WHERE" in compiled


def test_scope_to_user_unknown_column_raises() -> None:
    with pytest.raises(ValueError):
        scope_to_user(select(Product), uuid.uuid4(), column="nonexistent_col")
