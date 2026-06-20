"""``iam`` Pydantic v2 request/response models.

Per BACKEND_ARCHITECTURE.md §7.E (LOCKED 2026-06-05).

Field constraints are normative — Pydantic regex rejection produces the 400
``validation.{field}.invalid_format`` envelopes via the §4.F + §5A.H
validation handler chain.

E.164 phone regex
-----------------
``^\\+[1-9]\\d{1,14}$`` is the §7.E LOCKED generic E.164 form (NOT the
narrower ``^\\+91[6-9]\\d{9}$`` from the deleted legacy ``schemas/auth.py``).
Generic E.164 keeps the door open for V1.5+ international expansion without
needing a model migration.

OTP regex
---------
``^\\d{6}$`` enforces the §7.B 6-digit lock.  The legacy 4-digit dev OTP is
no longer accepted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Billing tier vocabulary (Pricing v2 §5 locked set — "free" is not subscribable)
_BillingTier = Literal[
    "starter", "pro", "business", "pro_annual", "business_annual", "ltd"
]


class SendOtpRequest(BaseModel):
    """``POST /api/v1/auth/otp/send`` body."""

    phone: str = Field(pattern=r"^\+[1-9]\d{1,14}$", examples=["+919876543210"])


class SendOtpResponse(BaseModel):
    """``POST /api/v1/auth/otp/send`` 202 body."""

    request_id: str = Field(description="MSG91 correlation ID — opaque to the client")


class VerifyOtpRequest(BaseModel):
    """``POST /api/v1/auth/otp/verify`` body."""

    phone: str = Field(pattern=r"^\+[1-9]\d{1,14}$", examples=["+919876543210"])
    otp: str = Field(pattern=r"^\d{6}$", examples=["123456"])


class VerifyOtpResponse(BaseModel):
    """``POST /api/v1/auth/otp/verify`` 200 body.

    The refresh token is NOT in the body — it ships in the ``Set-Cookie``
    response header per §4.B FE-D5 amendment.
    """

    access_token: str
    expires_in: int = Field(description="Seconds — matches ACCESS_TOKEN_TTL_SECONDS")
    token_type: Literal["bearer"] = "bearer"


class RefreshResponse(BaseModel):
    """``POST /api/v1/auth/refresh`` 200 body.

    Identical SHAPE to :class:`VerifyOtpResponse` but locked as a distinct
    model so the OpenAPI surface differentiates them (per §7.E note).
    """

    access_token: str
    expires_in: int
    token_type: Literal["bearer"] = "bearer"


class GoogleVerifyRequest(BaseModel):
    """``POST /api/v1/auth/google/verify`` body (google-auth feature).

    The frontend sends ONLY the Google Identity Services ID-token.  The token
    is verified server-side and never stored.  ``max_length`` bounds the body
    against oversized-body abuse (Google ID-tokens are ~1KB; 4KB is headroom).
    """

    credential: str = Field(
        min_length=1,
        max_length=4096,
        description="Google Identity Services ID-token (JWT). Verified server-side; never stored.",
    )


class GoogleVerifyResponse(VerifyOtpResponse):
    """``POST /api/v1/auth/google/verify`` 200 body (google-auth feature).

    Identical SHAPE to :class:`VerifyOtpResponse` (access JWT in body; refresh
    token ships in the ``Set-Cookie`` header) — declared as a distinct subclass
    so the OpenAPI surface differentiates the Google path (mirrors how
    :class:`RefreshResponse` is distinct-but-identical, per §7.E note).
    """


class MeResponse(BaseModel):
    """``GET /api/v1/auth/me`` 200 body.

    Razorpay Wave 3 widened ``plan`` from ``Literal["free"]`` to the full
    Pricing v2 vocabulary and added ``trial_ends_at`` + ``entitlement`` so the
    FE (Wave 5) can render plan state from ``/auth/me``.  ``plan`` is sourced
    DB-FRESH from ``users.plan`` (founder ruling F7 — NOT the JWT claim);
    ``entitlement`` is the RESOLVED effective tier from
    ``core.plan_guard.resolve_entitlement`` (annual→base, ltd/trial→pro).

    This is an ADDITIVE contract change — existing fields are unchanged; the
    widened ``plan`` Literal and the two new optional fields are the only diff.
    FE-coordination memo owed (``handoff_contract_razorpay.md``).

    ``phone`` is nullable per #322 (google-auth): Google-only users have no
    phone (``users.phone`` is nullable), so the FE must tolerate ``null``.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    # google-auth (#322): NULL for Google-only users (matches users.phone nullable).
    phone: str | None = None
    # Widened to the full Pricing v2 plan set (sourced DB-fresh per F7).
    plan: Literal[
        "free", "starter", "pro", "pro_annual", "business", "business_annual", "ltd"
    ]
    created_at: datetime
    last_login_at: datetime | None = None
    # Cross-module fact sourced from the customer module's
    # ``get_onboarding_completeness`` surface (see router).  Resolves to
    # ``False`` for a brand-new seller with no profile row yet — never raises.
    onboarding_complete: bool = False
    # ── Razorpay Wave 3 additions ──────────────────────────────────────────
    # The 14-day Pro-trial expiry (Pricing v2 §5.1); ``None`` if no trial.
    trial_ends_at: datetime | None = None
    # The RESOLVED effective entitlement (the field the FE should gate UI on):
    # annual cadences collapse to their base tier; ltd + a live trial → "pro".
    entitlement: Literal["free", "starter", "pro", "business"] = "free"


class WebhookCaptureResponse(BaseModel):
    """``POST /api/v1/webhooks/razorpay`` 200 body."""

    captured: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay Wave 3 — Billing API schemas (api-routes-builder, step 2b).
#
# These 6 Pydantic models are the wire shapes for the four ``/api/v1/billing/*``
# endpoints.  See RAZORPAY_INTEGRATION_SPEC §6 + WAVE3_ROUTES_TASKSPEC.md §3.3.
# All are in ``iam/schemas.py`` per §16.C private-surface rule.
# ─────────────────────────────────────────────────────────────────────────────


class BillingSubscribeRequest(BaseModel):
    """``POST /api/v1/billing/subscribe`` request body.

    ``tier`` drives which Razorpay surface is called:
      - recurring tiers (starter/pro/pro_annual/business/business_annual) →
        Razorpay Subscriptions API (``create_subscription``).
      - ``ltd`` → Razorpay Orders API (``create_order``), one-time payment.
    ``"free"`` is NOT a subscribable tier — it is the default and can only be
    left by subscribing or starting a trial.
    """

    tier: _BillingTier = Field(
        description=(
            "Target billing tier.  Recurring: starter|pro|pro_annual|business|"
            "business_annual.  One-time LTD: ltd."
        ),
        examples=["pro"],
    )


class BillingCheckout(BaseModel):
    """Razorpay Checkout handle returned to the FE widget.

    The FE mounts the Razorpay Checkout JS with either ``subscription_id`` (for
    recurring) or ``order_id`` (for LTD).  ``key_id`` is the public Razorpay key
    (safe to expose — it is the same key used in the FE environment config).
    ``short_url`` is a Razorpay-hosted checkout fallback that the FE may open
    in a WebView / external browser if the JS widget is unavailable.
    """

    key_id: str = Field(description="Razorpay public key (safe to expose to FE)")
    razorpay_subscription_id: str | None = Field(
        default=None,
        description="Set for recurring tiers; used by the FE Checkout widget",
    )
    razorpay_order_id: str | None = Field(
        default=None,
        description="Set for the LTD one-time purchase",
    )
    short_url: str | None = Field(
        default=None,
        description="Razorpay-hosted checkout fallback URL",
    )
    amount_paise: int | None = Field(
        default=None,
        description="Amount in paise — set only for the LTD order (display only)",
    )
    currency: str = Field(default="INR", description="ISO-4217 currency code")
    tier: str = Field(description="The tier being subscribed to — echoes the request")
    mock: bool = Field(
        default=False,
        description="DEV-ONLY. True when the dev mock granted entitlement synchronously "
        "(no real Razorpay object). The FE skips checkout.js and polls directly.",
    )


class BillingSubscribeResponse(BaseModel):
    """``POST /api/v1/billing/subscribe`` 201 body.

    The actual entitlement grant happens via the Razorpay webhook
    (``subscription.activated`` / ``payment.captured``) — this response is
    ADVISORY: it only confirms that a checkout session was created.  The FE
    MUST wait for the webhook-driven plan update (observable via
    ``GET /auth/me`` or ``GET /billing/subscription`` polling).
    """

    checkout: BillingCheckout


class BillingStartTrialResponse(BaseModel):
    """``POST /api/v1/billing/start-trial`` 200 body.

    The trial grants Pro-level entitlement immediately (app-side — no Razorpay
    call).  ``trial_ends_at`` is the absolute UTC expiry; the FE should display
    a countdown.  ``entitlement`` is always ``"pro"`` for a live trial.
    """

    trial_ends_at: datetime = Field(
        description="UTC expiry of the 14-day Pro trial"
    )
    entitlement: Literal["pro"] = Field(
        default="pro",
        description="Effective entitlement granted by the trial (always 'pro')",
    )


class BillingCancelResponse(BaseModel):
    """``POST /api/v1/billing/cancel`` 200 body.

    The subscription is scheduled to cancel at the end of the current billing
    cycle (Razorpay ``cancel_at_cycle_end=True``).  The entitlement remains
    active until ``entitled_until``; the actual ``status → 'cancelled'``
    transition on ``subscriptions`` is driven by the
    ``subscription.cancelled`` webhook (Wave 2).
    """

    status: Literal["cancel_scheduled"] = Field(
        default="cancel_scheduled",
        description=(
            "Immediate confirmation that a cancel-at-cycle-end was scheduled. "
            "The subscription stays active until entitled_until."
        ),
    )
    entitled_until: datetime | None = Field(
        default=None,
        description=(
            "Current ``subscriptions.current_period_end`` — the seller retains "
            "access until this date.  None in edge states (e.g. LTD cancel attempt "
            "which is currently blocked)."
        ),
    )


class BillingSubscriptionResponse(BaseModel):
    """``GET /api/v1/billing/subscription`` 200 body.

    The DB-fresh subscription/plan/trial status for the authenticated seller.
    ``entitlement`` is the field the FE should gate UI features on (it is the
    RESOLVED effective tier — annual→base, ltd/trial→pro).
    """

    model_config = ConfigDict(from_attributes=True)

    plan: Literal[
        "free", "starter", "pro", "pro_annual", "business", "business_annual", "ltd"
    ] = Field(
        description="users.plan — the raw plan (DB-fresh per F7); may differ from entitlement"
    )
    status: str | None = Field(
        default=None,
        description="subscriptions.status (active/cancelled/past_due/…); None if no sub row",
    )
    current_period_end: datetime | None = Field(
        default=None,
        description=(
            "End of the current paid period; None = perpetual (LTD) or no sub"
        ),
    )
    cancel_scheduled: bool = Field(
        default=False,
        description="True when a cancel-at-cycle-end is pending on the sub row",
    )
    tier_label: str = Field(
        description="Human-readable label for the plan (e.g. 'Pro', 'Pro (Annual)', 'Lifetime')"
    )
    trial_ends_at: datetime | None = Field(
        default=None,
        description="The §3.7 14-day trial expiry; None if no trial was started",
    )
    entitlement: Literal["free", "starter", "pro", "business"] = Field(
        description=(
            "The RESOLVED effective entitlement (the field the FE should gate UI on). "
            "Resolves annual→base, ltd→pro, trial→pro while live."
        )
    )


__all__ = [
    "SendOtpRequest",
    "SendOtpResponse",
    "VerifyOtpRequest",
    "VerifyOtpResponse",
    "RefreshResponse",
    "GoogleVerifyRequest",
    "GoogleVerifyResponse",
    "MeResponse",
    "WebhookCaptureResponse",
    # Wave 3 billing schemas:
    "BillingSubscribeRequest",
    "BillingCheckout",
    "BillingSubscribeResponse",
    "BillingStartTrialResponse",
    "BillingCancelResponse",
    "BillingSubscriptionResponse",
]
