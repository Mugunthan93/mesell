"""``iam`` billing router — 4 contract endpoints per Razorpay spec §6.

Endpoints
---------
1. ``POST /api/v1/billing/subscribe``     — Start a subscription / LTD purchase
2. ``POST /api/v1/billing/start-trial``   — Start the 14-day app-side Pro trial
3. ``POST /api/v1/billing/cancel``        — Cancel subscription at cycle end
4. ``GET  /api/v1/billing/subscription``  — Current billing/plan/trial status

Design decisions (per WAVE3_ROUTES_TASKSPEC.md §3.1)
------------------------------------------------------
* Mounted on a **SEPARATE** ``APIRouter`` (``prefix="/api/v1", tags=["billing"]``)
  from the auth router — keeps the OpenAPI tag clean (billing vs iam) and
  mirrors the ``iam_google_router`` pattern established for the google-auth
  feature.  Both the auth router and the billing router originate in the
  ``iam`` module.
* Feature-flag gated: ``FEATURE_BILLING_ENABLED`` gates the ``include_router``
  call in ``main.py`` so billing stays dark until Wave 0 (Razorpay plan-ids +
  KYC) clears on staging/prod.  In dev, the flag defaults True.
* **None of the four endpoints is plan-gated** (``enforce_plan_limit`` is NOT
  called here) — a free user MUST be able to subscribe or start a trial.
  The rate-limit decorators are the only throttle.
* ``subscribe`` and ``start-trial`` write a ``subscriptions`` row but do NOT
  grant the plan (``users.plan`` stays unchanged) — the plan grant is
  webhook-driven (D-D, Wave 2 ``subscription.activated`` / ``payment.captured``).

Rate limits (per spec §3.2)
---------------------------
* ``billing_subscribe``   — 10/h per user (spam-subscription prevention)
* ``billing_start_trial`` — 5/h per user (trial-abuse prevention)
* ``billing_cancel``      — 10/h per user (accidental-cancel prevention)
* GET subscription        — no rate-limit decorator (read; per-IP DDoS floor only)

No secrets/PII in logs — log tier/event/user_id only (§9).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.rate_limit_mw import rate_limit
from app.modules.iam import service as iam_service
from app.modules.iam.schemas import (
    BillingCancelResponse,
    BillingCheckout,
    BillingStartTrialResponse,
    BillingSubscribeRequest,
    BillingSubscribeResponse,
    BillingSubscriptionResponse,
)
from app.shared.config import settings
from app.shared.database import get_db

logger = logging.getLogger(__name__)

billing_router = APIRouter(prefix="/api/v1", tags=["billing"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /billing/subscribe  — §6 + §3.4
# ─────────────────────────────────────────────────────────────────────────────
@billing_router.post(
    "/billing/subscribe",
    response_model=BillingSubscribeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a Razorpay subscription or LTD purchase",
)
@rate_limit(scope="billing_subscribe", limit=10, window=3600)
async def billing_subscribe(
    payload: BillingSubscribeRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingSubscribeResponse:
    """Initiate a Razorpay Subscription (recurring) or Order (LTD).

    Returns the Razorpay Checkout handle the FE widget needs.  The plan is NOT
    granted immediately — it lands via the ``subscription.activated`` /
    ``payment.captured`` webhook (D-D, Wave 2).

    Raises:
        409 ``billing.already_subscribed`` — user already has an active sub.
        502 — Razorpay API unavailable (``RazorpayAdapterError``).
    """
    result = await iam_service.subscribe(
        user_id=user.user_id,
        tier=payload.tier,
        db=db,
    )
    checkout = BillingCheckout(
        key_id=settings.RAZORPAY_KEY_ID,
        razorpay_subscription_id=result.razorpay_subscription_id,
        razorpay_order_id=result.razorpay_order_id,
        short_url=result.short_url,
        amount_paise=result.amount_paise,
        tier=result.tier,
    )
    return BillingSubscribeResponse(checkout=checkout)


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST /billing/start-trial  — §6 + §3.7
# ─────────────────────────────────────────────────────────────────────────────
@billing_router.post(
    "/billing/start-trial",
    response_model=BillingStartTrialResponse,
    summary="Start the 14-day app-side Pro trial (one per phone, no Razorpay call)",
)
@rate_limit(scope="billing_start_trial", limit=5, window=3600)
async def billing_start_trial(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingStartTrialResponse:
    """Grant the 14-day app-side Pro trial (§3.7).

    App-side only — NO Razorpay call.  Sets ``users.trial_ends_at = now() + 14
    days`` and writes a business ``audit_events`` row.

    Raises:
        409 ``billing.trial.already_used`` — trial already used / non-free plan /
            existing subscription (all three are handled as "redundant trial").
    """
    result = await iam_service.start_trial(user_id=user.user_id, db=db)
    return BillingStartTrialResponse(
        trial_ends_at=result.trial_ends_at,
        entitlement="pro",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. POST /billing/cancel  — §6 + §3.3.3
# ─────────────────────────────────────────────────────────────────────────────
@billing_router.post(
    "/billing/cancel",
    response_model=BillingCancelResponse,
    summary="Cancel the current subscription at end of billing cycle",
)
@rate_limit(scope="billing_cancel", limit=10, window=3600)
async def billing_cancel(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingCancelResponse:
    """Schedule a cancel-at-cycle-end for the active subscription.

    The subscription stays active until ``entitled_until`` (the current
    ``subscriptions.current_period_end``).  The final ``status → 'cancelled'``
    transition is webhook-driven via ``subscription.cancelled`` (Wave 2).

    Raises:
        404 ``billing.no_active_subscription`` — no cancellable subscription found.
        502 — Razorpay cancel API unavailable (``RazorpayAdapterError``).
    """
    result = await iam_service.cancel(user_id=user.user_id, db=db)
    return BillingCancelResponse(
        status="cancel_scheduled",
        entitled_until=result.entitled_until,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /billing/subscription  — §6 + §3.4 (read-only status)
# ─────────────────────────────────────────────────────────────────────────────
@billing_router.get(
    "/billing/subscription",
    response_model=BillingSubscriptionResponse,
    summary="Get the current billing / plan / trial status (DB-fresh, F7)",
)
async def billing_subscription(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingSubscriptionResponse:
    """Return the DB-fresh billing status for the authenticated seller.

    ``entitlement`` is the RESOLVED effective tier the FE should gate UI on —
    annual→base, ltd→pro, trial→pro while live.  Per founder ruling F7 the plan
    is read DB-fresh, not from the JWT claim.

    No rate-limit decorator (read-only; per-IP DDoS floor via the middleware).
    """
    billing = await iam_service.get_billing_status(user_id=user.user_id, db=db)
    return BillingSubscriptionResponse(
        plan=billing.plan,  # type: ignore[arg-type]  # narrowed at runtime
        status=billing.status,
        current_period_end=billing.current_period_end,
        cancel_scheduled=billing.cancel_scheduled,
        tier_label=billing.tier_label,
        trial_ends_at=billing.trial_ends_at,
        entitlement=billing.entitlement,  # type: ignore[arg-type]  # narrowed at runtime
    )
