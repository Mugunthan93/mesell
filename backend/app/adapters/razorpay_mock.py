"""adapters/razorpay_mock.py — DEV-ONLY Razorpay mock (razorpay-dev-mock feature).

A drop-in fake for :mod:`app.adapters.razorpay`'s V1.5 async surface, used ONLY
when ``settings.razorpay_mock_active`` is True (dev/staging, never production —
see :pyattr:`app.shared.config.Settings.razorpay_mock_active`).  It lets the
founder exercise the full billing flow locally with NO Razorpay account and NO
network call, mirroring the ``DEV_OTP_BYPASS_CODE`` pattern.

Design (DEV_MOCK_MODE_SPEC §2):

* Exposes the SAME 6 coroutine signatures as the real adapter and returns the
  SAME frozen dataclasses (:class:`~app.adapters.razorpay.RazorpaySubscription`,
  :class:`~app.adapters.razorpay.RazorpayOrder`,
  :class:`~app.adapters.razorpay.RazorpayCustomer`) — so the service code path
  downstream of the call site is byte-identical between real and mock.
* ZERO network I/O: no ``import razorpay``, no ``httpx``, no
  ``asyncio.to_thread``.  Pure in-process object construction.
* Every method opens with ``assert settings.razorpay_mock_active`` so the mock
  is structurally unreachable in production even if a call site forgot to gate.
* All ids are prefixed ``sub_mock_`` / ``order_mock_`` and the ``short_url`` host
  is ``mock.razorpay.local`` so synthetic data is trivially identifiable.

The LOCKED synchronous ``verify_webhook_signature`` is **NOT** re-implemented
here — the mock service tail routes synthetic webhooks through
``_route_webhook_in_session`` directly (post-HMAC), so signature verification is
never invoked on the mock path (spec §3.4).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.adapters.razorpay import (
    RazorpayCustomer,
    RazorpayOrder,
    RazorpaySubscription,
)
from app.shared.config import settings

logger = logging.getLogger(__name__)


def _mock_period_end_epoch() -> int:
    """Epoch SECONDS for ``now + 30 days`` — the fake recurring period end."""
    return int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())


async def create_subscription(
    *,
    plan_id: str,
    customer_notify: bool = True,
    total_count: int | None = None,
    notes: dict | None = None,
) -> RazorpaySubscription:
    """Fake a recurring subscription create (no network).

    Returns a ``created``-status sub with a ``sub_mock_*`` id and a fake hosted
    ``short_url``.  ``current_end`` is ``None`` (matches the real adapter — the
    period end is set later by the synthetic ``subscription.activated`` replay).
    """
    assert settings.razorpay_mock_active  # never reachable in prod
    sub_id = f"sub_mock_{uuid4().hex[:14]}"
    logger.info("razorpay_mock.create_subscription sub=%s plan=%s", sub_id, plan_id)
    return RazorpaySubscription(
        id=sub_id,
        status="created",
        plan_id=plan_id or "plan_mock",
        current_end=None,
        short_url=f"https://mock.razorpay.local/sub/{sub_id}",
        notes=notes or {},
    )


async def create_order(
    *,
    amount: int,
    currency: str = "INR",
    receipt: str,
    notes: dict | None = None,
) -> RazorpayOrder:
    """Fake a one-time Order create (LTD path; no network)."""
    assert settings.razorpay_mock_active
    order_id = f"order_mock_{uuid4().hex[:14]}"
    logger.info("razorpay_mock.create_order order=%s receipt=%s", order_id, receipt)
    return RazorpayOrder(
        id=order_id,
        amount=amount,
        currency=currency,
        status="created",
        receipt=receipt,
    )


async def fetch_subscription(sub_id: str) -> RazorpaySubscription:
    """Fake a reconcile fetch — returns an already-active sub (Wave-4 use)."""
    assert settings.razorpay_mock_active
    return RazorpaySubscription(
        id=sub_id,
        status="active",
        plan_id="plan_mock",
        current_end=_mock_period_end_epoch(),
        short_url=None,
        notes={},
    )


async def cancel_subscription(
    sub_id: str,
    *,
    cancel_at_cycle_end: bool = True,
) -> RazorpaySubscription:
    """Fake a cancel — cycle-end keeps ``active``; immediate flips ``cancelled``."""
    assert settings.razorpay_mock_active
    logger.info(
        "razorpay_mock.cancel_subscription sub=%s cycle_end=%s",
        sub_id,
        cancel_at_cycle_end,
    )
    return RazorpaySubscription(
        id=sub_id,
        status="active" if cancel_at_cycle_end else "cancelled",
        plan_id="plan_mock",
        current_end=_mock_period_end_epoch(),
        short_url=None,
        notes={},
    )


async def update_subscription(
    sub_id: str,
    *,
    plan_id: str,
    schedule_change_at: str = "cycle_end",
) -> RazorpaySubscription:
    """Fake a plan change (no synthetic webhook tail — spec Q3 scope)."""
    assert settings.razorpay_mock_active
    return RazorpaySubscription(
        id=sub_id,
        status="active",
        plan_id=plan_id,
        current_end=_mock_period_end_epoch(),
        short_url=None,
        notes={},
    )


async def get_customer(customer_id: str) -> RazorpayCustomer:
    """Fake a customer fetch — no PII, no network."""
    assert settings.razorpay_mock_active
    return RazorpayCustomer(id=customer_id, email=None, contact=None)
