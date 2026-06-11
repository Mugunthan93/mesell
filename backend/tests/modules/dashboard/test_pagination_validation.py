"""Unit test #1 per §13.J + §13.A.1 amendment (2026-06-07).

Covers Pydantic :class:`schemas.DashboardQuery` rejection paths:

* ``page=0``  → ``ValidationError`` (Pydantic ``ge=1`` constraint).
* ``limit=0``  → ``ValidationError`` (Pydantic ``ge=1`` constraint).
* ``limit=101`` → ``ValidationError`` (Pydantic ``le=100`` constraint).

All happy-path defaults verified (``page=1``, ``limit=20``).

**Amendment scope (§13.A.1):** the original 5-case form covered
``status_filter="invalid"`` and ``search`` > 100 chars — both DROPPED in V1
because the two fields are deferred to V1.5 alongside a §10 catalog
``Pagination`` extension.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from app.modules.dashboard.exceptions import InvalidPaginationError
from app.modules.dashboard.schemas import DashboardQuery


class TestDashboardQueryDefaults:
    """Happy-path defaults per §13.B amended."""

    def test_default_page_is_1(self):
        q = DashboardQuery()
        assert q.page == 1

    def test_default_limit_is_20(self):
        q = DashboardQuery()
        assert q.limit == 20

    def test_explicit_page_and_limit_accepted(self):
        q = DashboardQuery(page=3, limit=50)
        assert q.page == 3
        assert q.limit == 50

    def test_page_1_and_limit_100_max_boundary_accepted(self):
        """Upper boundary of the ``limit`` Field constraint."""
        q = DashboardQuery(page=1, limit=100)
        assert q.limit == 100


class TestDashboardQueryRejections:
    """Pydantic ``Field`` constraints — out-of-range inputs."""

    def test_page_zero_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DashboardQuery(page=0, limit=20)
        # Must mention the page field.
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("page",) for e in errors), (
            f"Expected ValidationError on 'page', got {errors}"
        )

    def test_page_negative_rejected(self):
        with pytest.raises(ValidationError):
            DashboardQuery(page=-1, limit=20)

    def test_limit_zero_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DashboardQuery(page=1, limit=0)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors), (
            f"Expected ValidationError on 'limit', got {errors}"
        )

    def test_limit_101_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DashboardQuery(page=1, limit=101)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("limit",) for e in errors), (
            f"Expected ValidationError on 'limit', got {errors}"
        )

    def test_limit_high_value_rejected(self):
        with pytest.raises(ValidationError):
            DashboardQuery(page=1, limit=1_000_000)


class TestDashboardQueryAmendmentScope:
    """§13.A.1 — extra fields rejected (status_filter, search deferred to V1.5)."""

    def test_unknown_status_filter_field_rejected(self):
        """``status_filter`` is deferred to V1.5 — ``extra='forbid'`` rejects it."""
        with pytest.raises(ValidationError) as exc_info:
            DashboardQuery(
                page=1,
                limit=20,
                status_filter="draft",  # type: ignore[call-arg]
            )
        # The error must mention the unknown key.
        msg = str(exc_info.value)
        assert "status_filter" in msg or "extra" in msg.lower(), (
            f"Expected ValidationError mentioning the deferred 'status_filter' field, got {msg}"
        )

    def test_unknown_search_field_rejected(self):
        """``search`` is deferred to V1.5 — ``extra='forbid'`` rejects it."""
        with pytest.raises(ValidationError) as exc_info:
            DashboardQuery(
                page=1,
                limit=20,
                search="kurti",  # type: ignore[call-arg]
            )
        msg = str(exc_info.value)
        assert "search" in msg or "extra" in msg.lower(), (
            f"Expected ValidationError mentioning the deferred 'search' field, got {msg}"
        )


class TestInvalidPaginationErrorContract:
    """:class:`InvalidPaginationError` exists for the rare service-layer raise
    path. Verifies the §13.G locked contract (status + validation_message_id).
    """

    def test_invalid_pagination_error_status_code_400(self):
        err = InvalidPaginationError()
        assert err.status_code == 400

    def test_invalid_pagination_error_validation_message_id(self):
        err = InvalidPaginationError()
        assert err.validation_message_id == "validation.dashboard.invalid_pagination"

    def test_invalid_pagination_error_message_id_registered_in_en_registry(self):
        """The validation_message_id MUST exist in messages_en VALIDATION_MESSAGES."""
        from app.i18n.messages_en import VALIDATION_MESSAGES

        assert "validation.dashboard.invalid_pagination" in VALIDATION_MESSAGES, (
            "InvalidPaginationError's validation_message_id is not registered in "
            "i18n/messages_en.VALIDATION_MESSAGES — the §4.F resolver would fall "
            "back to err.detail and the i18n contract would be silently broken."
        )
        assert VALIDATION_MESSAGES["validation.dashboard.invalid_pagination"]
