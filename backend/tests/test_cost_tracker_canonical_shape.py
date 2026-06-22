"""AI-BE-13 — cost_tracker writes CANONICAL audit-row shape.

Wave: qa-image-ai · guard: IA-RED-1 contract lock.

This test asserts that :func:`ai_ops.cost_tracker.record` writes an
``audit_events`` row with EXACTLY the field names the perf-test
``test_ai_cost_average.py`` reads:

  - ``event_type = "ai.call"``
  - ``metadata_jsonb`` contains the ``"cost_inr"`` key (NOT ``"inr_cost"``)
  - ``metadata_jsonb`` also carries ``"workload"``, ``"input_tokens"``,
    ``"output_tokens"`` (informational; the perf test reads only cost_inr)

If this test breaks it means the PRODUCER has drifted and the CONSUMER
(perf test) will silently skip rather than catching regressions.

Mock seam: ``app.shared.database.AsyncSessionLocal`` is replaced with a
stub that captures the ORM row passed to ``session.add()``.  No live DB
or Valkey connection required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai_ops import cost_tracker

pytestmark = pytest.mark.unit


class TestCostTrackerCanonicalShape:
    """AI-BE-13 — ``cost_tracker.record`` writes the canonical audit shape."""

    async def test_record_writes_event_type_ai_call(self) -> None:
        """``event_type`` must be ``"ai.call"`` (not ``"ai_ops.cost"`` or any other)."""
        user_id = uuid.uuid4()
        captured: list[object] = []

        class _StubSession:
            async def __aenter__(self) -> "_StubSession":
                return self

            async def __aexit__(self, *a: object) -> None:
                return None

            def add(self, obj: object) -> None:
                captured.append(obj)

            async def commit(self) -> None:
                return None

        with (
            patch("app.ai_ops.cost_tracker.AsyncSessionLocal", return_value=_StubSession()),
            patch("app.ai_ops.cost_tracker.get_valkey_otp", new_callable=AsyncMock) as mv,
        ):
            mv.return_value.incrbyfloat = AsyncMock()
            mv.return_value.expire = AsyncMock()
            await cost_tracker.record(
                user_id=user_id,
                workload="autofill",
                input_tokens=500,
                output_tokens=200,
            )

        assert len(captured) == 1
        row = captured[0]
        # IA-RED-1 canonical column: event_type = "ai.call"
        assert row.event_type == "ai.call", (
            f"Expected event_type='ai.call', got {row.event_type!r}"
        )

    async def test_record_writes_cost_inr_in_metadata_jsonb(self) -> None:
        """``metadata_jsonb`` must contain key ``"cost_inr"`` (NOT ``"inr_cost"``)."""
        user_id = uuid.uuid4()
        captured: list[object] = []

        class _StubSession:
            async def __aenter__(self) -> "_StubSession":
                return self

            async def __aexit__(self, *a: object) -> None:
                return None

            def add(self, obj: object) -> None:
                captured.append(obj)

            async def commit(self) -> None:
                return None

        with (
            patch("app.ai_ops.cost_tracker.AsyncSessionLocal", return_value=_StubSession()),
            patch("app.ai_ops.cost_tracker.get_valkey_otp", new_callable=AsyncMock) as mv,
        ):
            mv.return_value.incrbyfloat = AsyncMock()
            mv.return_value.expire = AsyncMock()
            await cost_tracker.record(
                user_id=user_id,
                workload="autofill",
                input_tokens=500,
                output_tokens=200,
            )

        row = captured[0]
        metadata = row.metadata_jsonb
        assert isinstance(metadata, dict), (
            f"metadata_jsonb should be a dict, got {type(metadata).__name__}"
        )
        # IA-RED-1 canonical field: "cost_inr" (NOT "inr_cost")
        assert "cost_inr" in metadata, (
            f"Expected 'cost_inr' key in metadata_jsonb, got keys: {list(metadata)}"
        )
        assert "inr_cost" not in metadata, (
            "metadata_jsonb must NOT use the drifted 'inr_cost' key"
        )

    async def test_record_metadata_jsonb_cost_inr_matches_compute(self) -> None:
        """The ``cost_inr`` value in ``metadata_jsonb`` matches ``compute_cost_inr``."""
        user_id = uuid.uuid4()
        captured: list[object] = []

        class _StubSession:
            async def __aenter__(self) -> "_StubSession":
                return self

            async def __aexit__(self, *a: object) -> None:
                return None

            def add(self, obj: object) -> None:
                captured.append(obj)

            async def commit(self) -> None:
                return None

        with (
            patch("app.ai_ops.cost_tracker.AsyncSessionLocal", return_value=_StubSession()),
            patch("app.ai_ops.cost_tracker.get_valkey_otp", new_callable=AsyncMock) as mv,
        ):
            mv.return_value.incrbyfloat = AsyncMock()
            mv.return_value.expire = AsyncMock()
            await cost_tracker.record(
                user_id=user_id,
                workload="watermark",
                input_tokens=300,
                output_tokens=50,
            )

        row = captured[0]
        expected_cost = cost_tracker.compute_cost_inr(300, 50)
        assert row.metadata_jsonb["cost_inr"] == pytest.approx(expected_cost), (
            f"cost_inr mismatch: got {row.metadata_jsonb['cost_inr']}, "
            f"expected {expected_cost}"
        )

    async def test_record_metadata_jsonb_has_workload(self) -> None:
        """``metadata_jsonb`` must contain the ``"workload"`` key."""
        user_id = uuid.uuid4()
        captured: list[object] = []

        class _StubSession:
            async def __aenter__(self) -> "_StubSession":
                return self

            async def __aexit__(self, *a: object) -> None:
                return None

            def add(self, obj: object) -> None:
                captured.append(obj)

            async def commit(self) -> None:
                return None

        with (
            patch("app.ai_ops.cost_tracker.AsyncSessionLocal", return_value=_StubSession()),
            patch("app.ai_ops.cost_tracker.get_valkey_otp", new_callable=AsyncMock) as mv,
        ):
            mv.return_value.incrbyfloat = AsyncMock()
            mv.return_value.expire = AsyncMock()
            await cost_tracker.record(
                user_id=user_id,
                workload="smart_picker",
                input_tokens=800,
                output_tokens=100,
            )

        row = captured[0]
        assert row.metadata_jsonb.get("workload") == "smart_picker"
