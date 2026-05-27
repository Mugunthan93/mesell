"""Plan-based access guards.

Limits per plan (mirrors landing-page pricing)::
    free     — 5 catalogs/month, 3 QC checks/day
    starter  — 50 catalogs/month
    pro      — 200 catalogs/month
    growth   — 1000 catalogs/month
"""

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.models.user import User


@dataclass
class PlanLimits:
    catalogs_per_month: int
    qc_checks_per_day: int


PLAN_LIMITS: dict[str, PlanLimits] = {
    "free":    PlanLimits(catalogs_per_month=5,   qc_checks_per_day=3),
    "starter": PlanLimits(catalogs_per_month=50,  qc_checks_per_day=50),
    "pro":     PlanLimits(catalogs_per_month=200, qc_checks_per_day=200),
    "growth":  PlanLimits(catalogs_per_month=1000, qc_checks_per_day=1000),
}


def limits_for(user: User) -> PlanLimits:
    return PLAN_LIMITS.get((user.plan or "free").lower(), PLAN_LIMITS["free"])


def ensure_can_generate(user: User) -> None:
    limits = limits_for(user)
    used = user.catalogs_used or 0
    if used >= limits.catalogs_per_month:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Your '{user.plan}' plan allows {limits.catalogs_per_month} catalogs/month "
                f"(used {used}). Upgrade to Pro for more."
            ),
        )
