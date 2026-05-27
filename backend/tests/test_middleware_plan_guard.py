"""Plan-based access guard."""

import pytest
from fastapi import HTTPException

from app.middleware.plan_guard import PLAN_LIMITS, ensure_can_generate, limits_for
from app.models.user import User


def _user(plan: str, used: int) -> User:
    return User(phone="+919876543210", plan=plan, catalogs_used=used)


def test_limits_for_known_plans():
    assert limits_for(_user("free", 0)).catalogs_per_month == 5
    assert limits_for(_user("starter", 0)).catalogs_per_month == 50
    assert limits_for(_user("pro", 0)).catalogs_per_month == 200
    assert limits_for(_user("growth", 0)).catalogs_per_month == 1000


def test_limits_for_unknown_plan_falls_back_to_free():
    assert limits_for(_user("enterprise", 0)) == PLAN_LIMITS["free"]


def test_ensure_can_generate_passes_below_quota():
    ensure_can_generate(_user("free", 0))
    ensure_can_generate(_user("free", PLAN_LIMITS["free"].catalogs_per_month - 1))


def test_ensure_can_generate_raises_403_at_quota():
    with pytest.raises(HTTPException) as exc:
        ensure_can_generate(_user("free", PLAN_LIMITS["free"].catalogs_per_month))
    assert exc.value.status_code == 403
    assert "Upgrade" in exc.value.detail


def test_ensure_can_generate_uses_correct_limit_for_pro():
    ensure_can_generate(_user("pro", PLAN_LIMITS["pro"].catalogs_per_month - 1))
    with pytest.raises(HTTPException):
        ensure_can_generate(_user("pro", PLAN_LIMITS["pro"].catalogs_per_month))
