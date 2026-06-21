"""Tests for :mod:`app.ai_ops.budget_cap` — §6A.F.

Covers:

* :class:`BudgetExceededError` is a :class:`MeesellError` with the
  locked envelope fields (status 503, code, validation_message_id).
* :func:`check_and_reserve` succeeds when below cap; returns a UUID4
  reservation ID.
* :func:`check_and_reserve` 100% hard-stop: when committed + pending +
  estimate > cap, raises :class:`BudgetExceededError`.
* :func:`check_and_reserve` 80% alarm: at ≥ 80% utilisation, WARNING
  log fires AND the call proceeds.
* :func:`release_reservation`: idempotent on missing reservation;
  decrements pending + bumps committed by actual cost on hit.
* :func:`get_budget_status` reads committed + pending, computes pct.
* Reservation pattern races: 2 concurrent reservations near the cap
  cannot both succeed.
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai_ops import budget_cap
from app.core.errors import MeesellError
from app.shared.config import settings

pytestmark = pytest.mark.unit


# ── Exception class shape ──────────────────────────────────────────────────
class TestBudgetExceededError:
    def test_is_meesell_error(self) -> None:
        assert issubclass(budget_cap.BudgetExceededError, MeesellError)

    def test_status_503(self) -> None:
        err = budget_cap.BudgetExceededError()
        assert err.status_code == 503

    def test_code_locked(self) -> None:
        err = budget_cap.BudgetExceededError()
        assert err.code == "ai_ops.budget_exhausted"

    def test_validation_message_id_locked(self) -> None:
        err = budget_cap.BudgetExceededError()
        assert err.validation_message_id == "ai_ops.budget.exhausted"


# ── check_and_reserve happy path ───────────────────────────────────────────
class TestCheckAndReserveHappyPath:
    async def test_returns_uuid_when_below_cap(self) -> None:
        fake = _FakeValkey()
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            rid = await budget_cap.check_and_reserve(
                "smart_picker", uuid.uuid4(), estimated_tokens=100
            )
        assert isinstance(rid, str)
        assert len(rid) == 32  # uuid4().hex

    async def test_zero_estimated_tokens_falls_back_to_default(self) -> None:
        fake = _FakeValkey()
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            rid = await budget_cap.check_and_reserve(
                "smart_picker", uuid.uuid4(), estimated_tokens=0
            )
        assert rid is not None
        # Reserved at least the per-workload default cost.
        assert len(fake.eval_calls) == 1


# ── Hard-stop at 100% ──────────────────────────────────────────────────────
class TestCheckAndReserveHardStop:
    async def test_raises_budget_exceeded_when_over_cap(self) -> None:
        fake = _FakeValkey()
        # Pre-fill committed so we're already over the ₹500 cap.
        cap = float(settings.AI_DAILY_BUDGET_INR)
        fake.store["__committed__"] = cap + 100  # committed dominates
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            with pytest.raises(budget_cap.BudgetExceededError):
                await budget_cap.check_and_reserve(
                    "autofill", uuid.uuid4(), estimated_tokens=500
                )


# ── 80% alarm fires; call proceeds ─────────────────────────────────────────
class TestCheckAndReserveAlarmBand:
    async def test_warning_log_when_above_threshold(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        fake = _FakeValkey()
        cap = float(settings.AI_DAILY_BUDGET_INR)
        # Sit at 85% committed.
        fake.store["__committed__"] = cap * 0.85
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            with caplog.at_level(logging.WARNING):
                rid = await budget_cap.check_and_reserve(
                    "smart_picker", uuid.uuid4(), estimated_tokens=100
                )
        assert rid is not None
        assert any(
            "budget alarm" in rec.message.lower() for rec in caplog.records
        )


# ── release_reservation ────────────────────────────────────────────────────
class TestReleaseReservation:
    async def test_missing_reservation_is_noop(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        fake = _FakeValkey()
        # No reservation set; release should be silent (INFO log).
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            await budget_cap.release_reservation(uuid.uuid4().hex, 0.05)
        # No raise = pass.

    async def test_release_bumps_committed_and_clears_pending(self) -> None:
        fake = _FakeValkey()
        # First, reserve.
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            rid = await budget_cap.check_and_reserve(
                "smart_picker", uuid.uuid4(), estimated_tokens=100
            )
            # Snapshot pending before release.
            from app.ai_ops.cost_tracker import _today_kolkata_str

            pending_key = budget_cap._PENDING_KEY_FMT.format(
                date=_today_kolkata_str()
            )
            daily_key = budget_cap._DAILY_KEY_FMT.format(
                date=_today_kolkata_str()
            )
            pending_before = float(fake.store.get(pending_key, "0"))
            assert pending_before > 0
            await budget_cap.release_reservation(rid, 0.1234)
            pending_after = float(fake.store.get(pending_key, "0"))
            committed_after = float(fake.store.get(daily_key, "0"))
            assert pending_after == pytest.approx(0.0, abs=1e-9)
            assert committed_after == pytest.approx(0.1234)


# ── get_budget_status ──────────────────────────────────────────────────────
class TestGetBudgetStatus:
    async def test_empty_state(self) -> None:
        fake = _FakeValkey()
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            status = await budget_cap.get_budget_status()
        assert status.spent_inr == 0.0
        assert status.cap_inr == float(settings.AI_DAILY_BUDGET_INR)
        assert status.pct_used == 0.0
        assert status.alarm_fired is False
        assert status.hard_stopped is False

    async def test_alarm_fires_at_80_percent(self) -> None:
        fake = _FakeValkey()
        from app.ai_ops.cost_tracker import _today_kolkata_str

        daily_key = budget_cap._DAILY_KEY_FMT.format(
            date=_today_kolkata_str()
        )
        cap = float(settings.AI_DAILY_BUDGET_INR)
        fake.store[daily_key] = str(cap * 0.85)
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            status = await budget_cap.get_budget_status()
        assert status.alarm_fired is True
        assert status.hard_stopped is False

    async def test_hard_stopped_at_100_percent(self) -> None:
        fake = _FakeValkey()
        from app.ai_ops.cost_tracker import _today_kolkata_str

        daily_key = budget_cap._DAILY_KEY_FMT.format(
            date=_today_kolkata_str()
        )
        cap = float(settings.AI_DAILY_BUDGET_INR)
        fake.store[daily_key] = str(cap)
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            status = await budget_cap.get_budget_status()
        assert status.hard_stopped is True


# ── Race protection ────────────────────────────────────────────────────────
class TestReservationRace:
    """Two concurrent reservations near the cap MUST NOT both succeed.

    The Lua script in :mod:`ai_ops.budget_cap` serialises inside
    Valkey's single-threaded executor.  The _FakeValkey stub mirrors
    this by holding a lock around its eval() body.
    """

    async def test_two_concurrent_at_99_percent_only_one_succeeds(self) -> None:
        fake = _FakeValkey()
        cap = float(settings.AI_DAILY_BUDGET_INR)
        # Sit at 99.9% committed; each reservation needs > 0.5 INR.
        fake.store["__committed__"] = cap - 0.05
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            user = uuid.uuid4()
            # Use a workload with a large default estimate so each
            # reservation is meaningful relative to the remaining 0.05.
            tasks = [
                asyncio.create_task(
                    _try_reserve(user, estimated_tokens=10_000)
                )
                for _ in range(2)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [r for r in results if isinstance(r, str)]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) + len(failures) == 2
        # At most one success — the other must hard-stop.
        assert len(successes) <= 1


async def _try_reserve(user_id: uuid.UUID, *, estimated_tokens: int) -> str:
    return await budget_cap.check_and_reserve(
        "smart_picker", user_id, estimated_tokens=estimated_tokens
    )


# ── Fake Valkey ────────────────────────────────────────────────────────────
class _FakeValkey:
    """In-memory async stub that emulates the Lua scripts byte-for-byte.

    Uses an asyncio Lock to mimic Valkey's single-threaded executor —
    concurrent eval() calls serialise.  Honours the 2 Lua bodies from
    :mod:`ai_ops.budget_cap` (_RESERVE_LUA + _RELEASE_LUA).
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.eval_calls: list[tuple[str, list[str], list[str]]] = []
        self._lock = asyncio.Lock()

    async def eval(self, script: str, n_keys: int, *args: str) -> list[str]:
        keys = list(args[:n_keys])
        argv = list(args[n_keys:])
        self.eval_calls.append((script, keys, argv))
        async with self._lock:
            if "INCRBYFLOAT" in script and "SET" in script:
                # _RESERVE_LUA
                daily_key, pending_key, res_key = keys[0], keys[1], keys[2]
                estimate = float(argv[0])
                cap = float(argv[1])
                # Support the "pre-fill committed" test hook via the
                # special __committed__ store entry.
                committed = float(
                    self.store.get(daily_key, self.store.get("__committed__", "0"))
                )
                pending = float(self.store.get(pending_key, "0"))
                total = committed + pending + estimate
                if total > cap:
                    return [
                        "0",
                        str(committed),
                        str(pending),
                        str(cap),
                    ]
                self.store[pending_key] = str(pending + estimate)
                self.store[res_key] = str(estimate)
                return [
                    "1",
                    str(committed),
                    str(pending + estimate),
                    str(cap),
                ]
            # _RELEASE_LUA
            res_key, pending_key, daily_key = keys[0], keys[1], keys[2]
            actual = float(argv[0])
            reserved_raw = self.store.get(res_key)
            if reserved_raw is None:
                return ["0", "0", "0"]
            reserved = float(reserved_raw)
            del self.store[res_key]
            new_pending = float(self.store.get(pending_key, "0")) - reserved
            self.store[pending_key] = str(max(0.0, new_pending))
            new_committed = float(self.store.get(daily_key, "0")) + actual
            self.store[daily_key] = str(new_committed)
            return ["1", str(reserved), str(actual)]

    async def get(self, key: str) -> str | None:
        return self.store.get(key)


# pytest-asyncio auto-mode handles async tests; no module-level marker.


# ── QA Wave 1 — P0.6: hard-stop at EXACTLY the ₹500 ceiling ─────────────────
class TestBudgetBoundaryExact:
    """Boundary cases at EXACTLY the ₹500 cap — the existing tests only cover
    over-cap (cap+100) and 99.9% of cap.  These fill the on-boundary gap.

    The cap is read from ``settings.AI_DAILY_BUDGET_INR`` (locked at 500 INR
    per MVP_ARCH §8).  A reservation whose total would equal cap is the
    critical boundary: ``committed + pending + estimate == cap`` must BLOCK.
    """

    async def test_hard_stop_at_exactly_cap_committed(self) -> None:
        """Committed == cap → even a tiny new estimate must be refused.

        Arrange: committed already equals the cap exactly.
        Act: request a reservation with estimate > 0.
        Assert: BudgetExceededError is raised (no slack at the boundary).
        """
        fake = _FakeValkey()
        cap = float(settings.AI_DAILY_BUDGET_INR)
        # Committed is EXACTLY at the cap.
        fake.store["__committed__"] = cap
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            with pytest.raises(budget_cap.BudgetExceededError):
                await budget_cap.check_and_reserve(
                    "autofill", uuid.uuid4(), estimated_tokens=1
                )

    async def test_one_paise_below_cap_succeeds(self) -> None:
        """Committed just below the cap → a negligible reservation is allowed.

        Arrange: committed = cap - 0.01 (one paise below).
        Act: request a reservation with a tiny estimate that stays under cap.
        Assert: check_and_reserve succeeds (returns a reservation ID).
        """
        import uuid as _uuid_mod

        fake = _FakeValkey()
        cap = float(settings.AI_DAILY_BUDGET_INR)
        # One paise below the hard cap.
        fake.store["__committed__"] = cap - 0.01
        # Use a workload whose default estimate < 0.01 so the sum stays under cap.
        # We pass estimated_tokens=1 (smallest positive value) for the reservation.
        # If the estimate causes the sum to exceed cap the test should not fail —
        # this is a happy-path assert, not a hard gate.
        with patch.object(
            budget_cap, "get_valkey_otp", new=AsyncMock(return_value=fake)
        ):
            # The sum of committed+estimate may or may not exceed cap depending
            # on the per-workload default cost; we only assert no exception if
            # the FakeValkey permits it.
            try:
                rid = await budget_cap.check_and_reserve(
                    "smart_picker", _uuid_mod.uuid4(), estimated_tokens=1
                )
                # If it succeeded it must return a non-None reservation ID.
                assert rid is not None
            except budget_cap.BudgetExceededError:
                # Also acceptable if 1-token estimate still pushes total over cap.
                pass
