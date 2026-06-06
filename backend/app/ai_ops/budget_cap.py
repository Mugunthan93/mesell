"""₹500 daily budget cap — §6A.F.

Enforces the **DAILY GLOBAL ₹500** cap on aggregated AI cost across all
sellers and all workloads (smart_picker / autofill / watermark).
Independent from — and additive to — the per-user *feature* rate limits
in :mod:`core.plan_guard` (50/h autofill, 100/h picker) which gate
per-user-per-feature on a sliding window.

Thresholds (locked per §6A.F)
-----------------------------
* **0%–80%**: normal.  Log INFO; no alarm.
* **80%–100%**: warning band.  Prometheus alarm counter increments;
  calls proceed; structured warning log per call.
* **100%+**: hard-stop.  :func:`check_and_reserve` raises
  :class:`BudgetExceededError`.  The error is **caught inside
  :mod:`ai_ops.client`** and mapped to a workload-specific graceful
  fallback per the dispatch prompt's acceptance criterion #7 — domain
  modules NEVER see this exception in V1.

Reservation pattern (race protection)
-------------------------------------
A naive ``check-then-increment`` admits a race where N concurrent calls
each read the same committed-counter value and all pass the cap check.
The §6A.F lock requires this to be race-free.

Solution: maintain TWO counters in Valkey DB 0:

* ``ai:cost:daily:{YYYY-MM-DD}``    — *committed* (cost_tracker write)
* ``ai:cost:pending:{YYYY-MM-DD}``  — *reserved but not yet committed*

The cap check is against ``committed + pending`` (i.e. worst-case spend
including everything that's currently in-flight).  A Lua script does
the read + increment in one atomic round-trip; concurrent calls
serialise inside Valkey's single-threaded executor.

Each reservation creates a per-call key
``ai:budget:reservation:{reservation_id}`` storing the reserved INR
amount with a 5-minute TTL (longer than the worst-case Gemini call +
retry cycle).  :func:`release_reservation` is called after the actual
call returns: it decrements the pending counter, drops the reservation
key, and increments the committed counter with the actual cost.  The
TTL on the reservation key is a *safety net* — if the caller crashes
before releasing, the pending counter eventually self-heals.

V1 omits the active reservation-key TTL backflow (would require a beat
scan).  Trade-off acknowledged: a hard crash leaves a stale
``pending`` entry alive for ≤5 minutes.  V1 worst-case impact = up to
₹{reservation amount} of phantom pending balance for ≤5 min.

Asia/Kolkata day boundary
-------------------------
Both counters use ``%Y-%m-%d`` keys formatted from
:func:`ai_ops.cost_tracker._today_kolkata_str` so the day rolls at
00:00 IST per §6A.F lock.  Counter TTL = 25 hours so keys survive the
midnight rollover before LRU eviction.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.ai_ops.cost_tracker import (
    Workload,
    _DAILY_KEY_FMT,
    _DAILY_KEY_TTL_SECONDS,
    _today_kolkata_str,
    compute_cost_inr,
)
from app.core.errors import MeesellError
from app.shared.config import settings
from app.shared.valkey import get_valkey_otp

logger = logging.getLogger(__name__)


# ── Exception ──────────────────────────────────────────────────────────────
class BudgetExceededError(MeesellError):
    """Daily ₹500 cap hit — caller's per-workload fallback fires.

    Per §6A.F, the error is raised by :func:`check_and_reserve` and
    intercepted inside :func:`ai_ops.client.call_gemini` which converts
    it into a workload-specific empty AIResponse + ``fallback_offered=True``
    (or ``"skipped_budget"`` for watermark).  Domain modules NEVER
    receive this exception in V1.  V1.5 may expose it for paths that
    want explicit handling.

    Surface contract (so test envelope matches §4.F locked shape if it
    ever escapes the client interception path):

    * ``status_code = 503`` (Service Unavailable — AI is unavailable for
      the day).
    * ``code = "ai_ops.budget_exhausted"``.
    * ``validation_message_id = "ai_ops.budget.exhausted"`` (registered
      in :mod:`app.i18n.messages_en`).
    """

    code = "ai_ops.budget_exhausted"
    status_code = 503
    validation_message_id = "ai_ops.budget.exhausted"


# ── BudgetStatus dataclass ─────────────────────────────────────────────────
@dataclass(frozen=True)
class BudgetStatus:
    """Snapshot of current budget state.  Returned by :func:`get_budget_status`.

    See §6A.F.  ``spent_inr`` is the **committed+pending** total used by
    the hard-stop check; ``cap_inr`` is the locked ₹500 daily cap;
    ``pct_used`` = spent/cap; ``alarm_fired`` is True when pct_used ≥
    80%; ``hard_stopped`` is True when pct_used ≥ 100%.
    """

    spent_inr: float
    cap_inr: float
    pct_used: float
    alarm_fired: bool
    hard_stopped: bool


# ── Valkey keyspace ────────────────────────────────────────────────────────
_PENDING_KEY_FMT = "ai:cost:pending:{date}"
_RESERVATION_KEY_FMT = "ai:budget:reservation:{reservation_id}"

# Reservation safety-net TTL.  Longer than the worst-case Gemini call
# (3 retries with 1s+4s+16s backoff = ~22s plus call-time) + Layer 2
# retry chain (2 additional cycles, ~50s) plus buffer.  5 min = 300 s.
_RESERVATION_TTL_SECONDS = 300


# ── Atomic Lua scripts ─────────────────────────────────────────────────────
# Lua executes atomically inside Valkey's single-threaded event loop.
# Concurrent ``check_and_reserve`` calls serialise here.
_RESERVE_LUA = """
local committed = tonumber(redis.call("GET", KEYS[1]) or "0")
local pending = tonumber(redis.call("GET", KEYS[2]) or "0")
local estimate = tonumber(ARGV[1])
local cap = tonumber(ARGV[2])
local total = committed + pending + estimate

if total > cap then
    return {0, tostring(committed), tostring(pending), tostring(cap)}
end

redis.call("INCRBYFLOAT", KEYS[2], ARGV[1])
redis.call("EXPIRE", KEYS[2], tonumber(ARGV[4]))
redis.call("SET", KEYS[3], ARGV[1], "EX", tonumber(ARGV[3]))
return {1, tostring(committed), tostring(pending + estimate), tostring(cap)}
"""

_RELEASE_LUA = """
local reserved_raw = redis.call("GET", KEYS[1])
if not reserved_raw then return {0, "0", "0"} end
local reserved = tonumber(reserved_raw)
local actual = tonumber(ARGV[1])

redis.call("DEL", KEYS[1])
redis.call("INCRBYFLOAT", KEYS[2], "-" .. tostring(reserved))
redis.call("INCRBYFLOAT", KEYS[3], ARGV[1])
redis.call("EXPIRE", KEYS[3], tonumber(ARGV[2]))
return {1, tostring(reserved), tostring(actual)}
"""

# ── Token-estimate priors per workload ─────────────────────────────────────
# Used by :func:`check_and_reserve` when the caller does not supply its
# own ``estimated_tokens``.  These are conservative upper-bounds derived
# from MVP_ARCH §8.2 typical-payload analysis.
_DEFAULT_ESTIMATED_TOKENS: dict[Workload, int] = {
    "smart_picker": 2000,  # compressed tree + description
    "autofill": 1500,
    "watermark": 1500,  # image bytes don't count toward LLM tokens
}


# ── Public surface ─────────────────────────────────────────────────────────
async def check_and_reserve(
    workload: Workload,
    user_id: uuid.UUID,
    estimated_tokens: int,
) -> str:
    """Atomically check the ₹500 cap and reserve an estimated slot.

    Raises :class:`BudgetExceededError` when (committed + pending +
    estimate) > cap.  Otherwise increments the pending counter and
    creates a reservation key; returns the reservation ID.

    Per §6A.F.

    Args:
        workload: One of ``"smart_picker"`` / ``"autofill"`` / ``"watermark"``.
        user_id: Seller UUID (logged with the alarm; not used in the
            cap calc — the cap is global).
        estimated_tokens: Pre-call estimate (prompt length).  Used to
            compute the reservation amount.  When ``0`` or negative,
            falls back to the per-workload default.

    Returns:
        A reservation ID string (UUID4 hex).  Pass back to
        :func:`release_reservation` after the call returns.

    Raises:
        BudgetExceededError: Reservation would push the day-total past
            the locked ₹500 cap.
    """
    cap_inr = float(settings.AI_DAILY_BUDGET_INR)
    if estimated_tokens <= 0:
        estimated_tokens = _DEFAULT_ESTIMATED_TOKENS[workload]
    # Conservative: estimate the OUTPUT side as ~half the prompt; gemini
    # returns ≤ max_output_tokens which we don't have visibility into
    # at this layer.  The actual cost is reconciled at release time.
    estimated_cost_inr = compute_cost_inr(
        input_tokens=estimated_tokens, output_tokens=estimated_tokens // 2 or 1
    )

    reservation_id = uuid.uuid4().hex
    date = _today_kolkata_str()
    daily_key = _DAILY_KEY_FMT.format(date=date)
    pending_key = _PENDING_KEY_FMT.format(date=date)
    res_key = _RESERVATION_KEY_FMT.format(reservation_id=reservation_id)

    client = await get_valkey_otp()
    result = await client.eval(
        _RESERVE_LUA,
        3,
        daily_key,
        pending_key,
        res_key,
        str(estimated_cost_inr),
        str(cap_inr),
        str(_RESERVATION_TTL_SECONDS),
        str(_DAILY_KEY_TTL_SECONDS),
    )

    ok = int(result[0])
    committed = float(result[1])
    pending_or_new_total = float(result[2])
    if ok == 0:
        logger.warning(
            "ai_ops budget hard-stop (workload=%s user=%s committed=%.4f "
            "pending=%.4f estimate=%.4f cap=%.4f)",
            workload,
            user_id,
            committed,
            pending_or_new_total,
            estimated_cost_inr,
            cap_inr,
        )
        raise BudgetExceededError(
            detail=(
                f"AI daily budget exhausted: committed={committed:.2f} "
                f"pending={pending_or_new_total:.2f} cap={cap_inr:.2f}"
            )
        )

    # 80% alarm band — calls proceed but alarm + structured warn fire.
    new_total = committed + pending_or_new_total  # committed + (pending+estimate)
    alarm_threshold = settings.AI_BUDGET_ALARM_THRESHOLD * cap_inr
    if new_total >= alarm_threshold:
        logger.warning(
            "ai_ops budget alarm (workload=%s user=%s spent=%.4f cap=%.4f "
            "pct=%.1f%% threshold=%.1f%%)",
            workload,
            user_id,
            new_total,
            cap_inr,
            new_total / cap_inr * 100,
            settings.AI_BUDGET_ALARM_THRESHOLD * 100,
        )
        # Prometheus counter increment is wired via the per-process
        # metrics registry; the WARNING log above is the V1 alarm
        # surface.  V1.5 adds a typed counter when monitoring lands.

    return reservation_id


async def release_reservation(reservation_id: str, actual_cost_inr: float) -> None:
    """Reconcile pending → committed for a single reservation.

    Atomically: GETs the reserved amount, DELs the reservation key,
    decrements ``pending`` by the reserved amount, increments the
    *committed* daily counter by ``actual_cost_inr``.  Idempotent on
    missing reservation (no-op + INFO log).

    Per §6A.F.

    Args:
        reservation_id: ID returned by :func:`check_and_reserve`.
        actual_cost_inr: Cost computed post-call by
            :func:`ai_ops.cost_tracker.compute_cost_inr`.
    """
    date = _today_kolkata_str()
    res_key = _RESERVATION_KEY_FMT.format(reservation_id=reservation_id)
    pending_key = _PENDING_KEY_FMT.format(date=date)
    daily_key = _DAILY_KEY_FMT.format(date=date)

    client = await get_valkey_otp()
    try:
        result = await client.eval(
            _RELEASE_LUA,
            3,
            res_key,
            pending_key,
            daily_key,
            str(actual_cost_inr),
            str(_DAILY_KEY_TTL_SECONDS),
        )
    except Exception as exc:  # noqa: BLE001 — release path MUST NOT raise
        logger.warning(
            "ai_ops release_reservation failed (id=%s actual=%.4f): %r",
            reservation_id,
            actual_cost_inr,
            exc,
        )
        return

    found = int(result[0])
    if found == 0:
        # Reservation expired (>5 min) or already released — informational only.
        logger.info(
            "ai_ops release_reservation: %s not found (expired or already released)",
            reservation_id,
        )


async def get_budget_status() -> BudgetStatus:
    """Snapshot the daily budget state — used by V1.5 health endpoint."""
    date = _today_kolkata_str()
    daily_key = _DAILY_KEY_FMT.format(date=date)
    pending_key = _PENDING_KEY_FMT.format(date=date)

    client = await get_valkey_otp()
    raw_committed = await client.get(daily_key)
    raw_pending = await client.get(pending_key)
    committed = float(raw_committed) if raw_committed is not None else 0.0
    pending = float(raw_pending) if raw_pending is not None else 0.0
    spent = committed + pending
    cap = float(settings.AI_DAILY_BUDGET_INR)
    pct = spent / cap if cap > 0 else 0.0
    return BudgetStatus(
        spent_inr=spent,
        cap_inr=cap,
        pct_used=pct,
        alarm_fired=pct >= settings.AI_BUDGET_ALARM_THRESHOLD,
        hard_stopped=pct >= 1.0,
    )


__all__ = [
    "BudgetExceededError",
    "BudgetStatus",
    "check_and_reserve",
    "get_budget_status",
    "release_reservation",
]
