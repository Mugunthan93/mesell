"""QualityGate report schemas."""

from typing import Literal

from pydantic import BaseModel

CheckSeverity = Literal["fail", "warn"]
CheckStatus = Literal["pass", "warn", "fail"]


class QualityCheckResult(BaseModel):
    name: str
    status: CheckStatus
    severity: CheckSeverity
    weight: int
    score: int  # awarded weight (== weight on pass, 0 on fail/warn)
    detail: str
    fix: str | None = None


class QualityReport(BaseModel):
    catalog_id: str
    score: int  # 0-100
    passed: bool
    checks: list[QualityCheckResult]
    summary: dict
