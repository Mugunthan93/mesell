"""Tests for :mod:`app.ai_ops.cost_tracker` — §6A.D.

Covers:

* ``RATE_INPUT_PER_1K`` / ``RATE_OUTPUT_PER_1K`` module-level constants
  match MVP_ARCH §8.2 lock.
* :func:`compute_cost_inr` produces correct INR amounts.
* :func:`record` writes one ``audit_events`` row per call with the
  locked ``event_type='ai.call'`` + workload/tokens/cost in
  ``metadata_jsonb``.
* :func:`record` bumps the per-user-per-hour Valkey counter.
* :func:`record` calls ``budget_cap.release_reservation`` when a
  ``reservation_id`` is supplied.
* :func:`record` does NOT call ``release_reservation`` when
  ``reservation_id`` is ``None``.
* :func:`record` does NOT raise when the audit write fails (informational).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai_ops import cost_tracker

pytestmark = pytest.mark.unit


# ── Constants ──────────────────────────────────────────────────────────────
class TestRateConstants:
    """Locked at module level per §6A.D (MVP_ARCH §8.2)."""

    def test_input_rate_is_0_0078(self) -> None:
        assert cost_tracker.RATE_INPUT_PER_1K == 0.0078

    def test_output_rate_is_0_031(self) -> None:
        assert cost_tracker.RATE_OUTPUT_PER_1K == 0.031


# ── compute_cost_inr ───────────────────────────────────────────────────────
class TestComputeCostInr:
    def test_simple_case(self) -> None:
        # 1000 in, 1000 out → 0.0078 + 0.031 = 0.0388
        assert cost_tracker.compute_cost_inr(1000, 1000) == pytest.approx(0.0388)

    def test_zero_inputs(self) -> None:
        assert cost_tracker.compute_cost_inr(0, 0) == 0.0

    def test_negative_inputs_treated_as_zero(self) -> None:
        assert cost_tracker.compute_cost_inr(-100, -200) == 0.0

    def test_target_per_call_under_5_paise(self) -> None:
        # MVP_ARCH §8.2: ₹0.05 average per call.  500 in + 200 out is the
        # rough V1 envelope.
        cost = cost_tracker.compute_cost_inr(500, 200)
        assert cost < 0.05


# ── record() ───────────────────────────────────────────────────────────────
class TestRecord:
    """All async — pytest-asyncio auto-mode handles `async def`."""

    async def test_writes_one_audit_event_row(self) -> None:
        """``record`` writes exactly one ``audit_events`` row with locked shape."""
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
                pass

        with patch.object(
            cost_tracker,
            "AsyncSessionLocal",
            return_value=_StubSession(),
        ), patch.object(
            cost_tracker,
            "get_valkey_otp",
            new=AsyncMock(return_value=_FakeValkey()),
        ):
            cost = await cost_tracker.record(
                user_id=user_id,
                workload="autofill",
                input_tokens=1000,
                output_tokens=500,
            )

        assert cost == pytest.approx(0.0078 + 0.0155)
        assert len(captured) == 1
        row = captured[0]
        assert row.user_id == user_id
        assert row.event_type == "ai.call"
        assert row.entity_type is None
        assert row.entity_id is None
        assert row.diff_jsonb is None
        meta = row.metadata_jsonb
        assert meta["workload"] == "autofill"
        assert meta["input_tokens"] == 1000
        assert meta["output_tokens"] == 500
        assert meta["cost_inr"] == pytest.approx(0.0078 + 0.0155)

    async def test_calls_release_reservation_when_id_supplied(self) -> None:
        user_id = uuid.uuid4()
        release_mock = AsyncMock()
        with patch.object(
            cost_tracker,
            "AsyncSessionLocal",
            return_value=_NoopSession(),
        ), patch.object(
            cost_tracker,
            "get_valkey_otp",
            new=AsyncMock(return_value=_FakeValkey()),
        ), patch(
            "app.ai_ops.budget_cap.release_reservation",
            new=release_mock,
        ):
            await cost_tracker.record(
                user_id=user_id,
                workload="smart_picker",
                input_tokens=100,
                output_tokens=200,
                reservation_id="resv-xyz",
            )
        release_mock.assert_awaited_once()
        # Args: (reservation_id, actual_cost)
        args = release_mock.call_args
        assert args[0][0] == "resv-xyz"
        assert args[0][1] == pytest.approx(
            cost_tracker.compute_cost_inr(100, 200)
        )

    async def test_no_release_when_reservation_id_is_none(self) -> None:
        user_id = uuid.uuid4()
        release_mock = AsyncMock()
        with patch.object(
            cost_tracker,
            "AsyncSessionLocal",
            return_value=_NoopSession(),
        ), patch.object(
            cost_tracker,
            "get_valkey_otp",
            new=AsyncMock(return_value=_FakeValkey()),
        ), patch(
            "app.ai_ops.budget_cap.release_reservation",
            new=release_mock,
        ):
            await cost_tracker.record(
                user_id=user_id,
                workload="smart_picker",
                input_tokens=100,
                output_tokens=200,
                reservation_id=None,
            )
        release_mock.assert_not_called()

    async def test_audit_failure_does_not_raise(self) -> None:
        """Per §6A.D: audit write is informational; failure must be logged
        and swallowed so the AI call path itself does not regress."""
        user_id = uuid.uuid4()

        class _BrokenSession:
            async def __aenter__(self) -> "_BrokenSession":
                return self

            async def __aexit__(self, *a: object) -> None:
                return None

            def add(self, obj: object) -> None:
                pass

            async def commit(self) -> None:
                raise RuntimeError("DB down")

        with patch.object(
            cost_tracker,
            "AsyncSessionLocal",
            return_value=_BrokenSession(),
        ), patch.object(
            cost_tracker,
            "get_valkey_otp",
            new=AsyncMock(return_value=_FakeValkey()),
        ):
            cost = await cost_tracker.record(
                user_id=user_id,
                workload="smart_picker",
                input_tokens=100,
                output_tokens=200,
            )
        assert cost > 0  # cost still returned

    async def test_bumps_user_hourly_counter(self) -> None:
        user_id = uuid.uuid4()
        fake_valkey = _FakeValkey()
        with patch.object(
            cost_tracker,
            "AsyncSessionLocal",
            return_value=_NoopSession(),
        ), patch.object(
            cost_tracker,
            "get_valkey_otp",
            new=AsyncMock(return_value=fake_valkey),
        ):
            await cost_tracker.record(
                user_id=user_id,
                workload="watermark",
                input_tokens=2000,
                output_tokens=10,
            )
        # incrbyfloat should have been called once with the user-hourly key.
        assert len(fake_valkey.incrbyfloat_calls) == 1
        key, amount = fake_valkey.incrbyfloat_calls[0]
        assert str(user_id) in key
        assert amount > 0


# ── get_daily_spend / get_user_hourly_spend ───────────────────────────────
class TestSpendGetters:
    async def test_get_daily_spend_returns_zero_when_unset(self) -> None:
        fake = _FakeValkey()
        with patch.object(
            cost_tracker, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            assert await cost_tracker.get_daily_spend() == 0.0

    async def test_get_user_hourly_spend_returns_zero_when_unset(self) -> None:
        fake = _FakeValkey()
        with patch.object(
            cost_tracker, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            assert (
                await cost_tracker.get_user_hourly_spend(uuid.uuid4()) == 0.0
            )

    async def test_get_daily_spend_reads_stored_value(self) -> None:
        fake = _FakeValkey()
        # Pre-populate today's key.
        key = cost_tracker._DAILY_KEY_FMT.format(
            date=cost_tracker._today_kolkata_str()
        )
        fake.store[key] = "12.345"
        with patch.object(
            cost_tracker, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            assert await cost_tracker.get_daily_spend() == pytest.approx(12.345)


# ── Fixtures ───────────────────────────────────────────────────────────────
class _FakeValkey:
    """Minimal async stub of the redis.asyncio interface we use."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.incrbyfloat_calls: list[tuple[str, float]] = []
        self.expire_calls: list[tuple[str, int]] = []

    async def incrbyfloat(self, key: str, amount: float) -> float:
        self.incrbyfloat_calls.append((key, float(amount)))
        new = float(self.store.get(key, "0")) + float(amount)
        self.store[key] = str(new)
        return new

    async def expire(self, key: str, ttl: int) -> bool:
        self.expire_calls.append((key, int(ttl)))
        return True

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: object, ex: int | None = None) -> bool:
        self.store[key] = str(value)
        return True

    async def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                n += 1
        return n


class _NoopSession:
    async def __aenter__(self) -> "_NoopSession":
        return self

    async def __aexit__(self, *a: object) -> None:
        return None

    def add(self, obj: object) -> None:
        pass

    async def commit(self) -> None:
        pass


# pytest-asyncio auto-mode (configured in pytest.ini) handles async tests
# without an explicit marker.  No module-level marker needed.
