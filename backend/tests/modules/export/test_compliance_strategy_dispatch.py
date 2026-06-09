"""§14.K unit test 4 — compliance strategy dispatch.

Verifies :func:`export.service._select_strategy` dispatch behaviour:

* ``"standard"`` → :class:`StandardComplianceStrategy`
* ``"collapsed"`` → :class:`CollapsedComplianceStrategy`
* anything else → :class:`ComplianceStrategyError` (500)
"""

from __future__ import annotations

import pytest

from app.modules.export.domain import (
    CollapsedComplianceStrategy,
    StandardComplianceStrategy,
)
from app.modules.export.exceptions import ComplianceStrategyError
from app.modules.export.service import _select_strategy


def test_standard_shape_returns_standard_strategy():
    strategy = _select_strategy("standard")
    assert isinstance(strategy, StandardComplianceStrategy)


def test_collapsed_shape_returns_collapsed_strategy():
    strategy = _select_strategy("collapsed")
    assert isinstance(strategy, CollapsedComplianceStrategy)


@pytest.mark.parametrize(
    "bad_shape",
    [
        "",
        "STANDARD",  # case-sensitive lock
        "Collapsed",
        "unknown",
        "v2_extended",
    ],
)
def test_unknown_shape_raises_compliance_strategy_error(bad_shape):
    with pytest.raises(ComplianceStrategyError) as exc_info:
        _select_strategy(bad_shape)
    assert exc_info.value.status_code == 500
    assert exc_info.value.error_code == "compliance_strategy_failed"
    assert exc_info.value.validation_message_id == "export.compliance.strategy_failed"
