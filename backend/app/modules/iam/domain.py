"""``iam`` internal domain types — frozen dataclasses, never crossing HTTP.

Per BACKEND_ARCHITECTURE.md §7.F (LOCKED 2026-06-05).

These are **internal value objects** passed between service ↔ repository ↔
Valkey-serializer.  They do NOT cross the HTTP boundary — that responsibility
belongs to the Pydantic models in :mod:`.schemas`.  Using plain frozen
dataclasses (not Pydantic) keeps them lightweight and immutable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.shared.models.user import User


@dataclass(frozen=True)
class OtpRecord:
    """JSON-serialised in Valkey under ``otp:{phone}``.

    Attributes:
        otp_hash: SHA-256 hex digest of the 6-digit OTP. The plaintext OTP
            is NEVER stored or logged per §7.B.2 constant-time-compare lock.
        attempts: 0, 1, or 2. The 3rd mismatch triggers ``OtpAttemptsExceededError``.
        expires_at: Unix timestamp (seconds). Driven by Valkey ``EX 300`` TTL.
    """

    otp_hash: str
    attempts: int
    expires_at: int


@dataclass(frozen=True)
class RefreshAllowlistEntry:
    """JSON-serialised in Valkey under ``cache:refresh:{hmac}``.

    Attributes:
        user_id: The principal the cookie authenticates as.
        issued_at: Unix timestamp at issuance.
        ip: Client IP captured at issuance — surfaced in the audit row, not
            enforced for validation (per §7.B.3 the cookie alone is the
            credential; IP change is logged not blocked).
    """

    user_id: UUID
    issued_at: int
    ip: str


@dataclass(frozen=True)
class SendOtpResult:
    """Returned by ``iam.service.send_otp_for_login``.

    Attributes:
        request_id: MSG91 correlation ID. Opaque to the client; logged.
    """

    request_id: str


@dataclass(frozen=True)
class VerifyOtpResult:
    """Returned by ``iam.service.verify_otp_and_issue_tokens``.

    Attributes:
        access_token: Short-lived HS256 JWT per §4.B.
        refresh_token: Opaque ``secrets.token_urlsafe(48)``. The router
            serialises this into the ``refresh_token`` HttpOnly cookie.
        access_expires_in: Seconds until the access token expires.
        refresh_expires_in: Seconds until the refresh cookie expires.
    """

    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int


@dataclass(frozen=True)
class RotateRefreshResult:
    """Returned by ``iam.service.rotate_refresh_token``.

    Attributes:
        access_token: Freshly minted HS256 access JWT.
        new_refresh_token: New opaque cookie value (the router sets it via
            ``Set-Cookie``; the OLD cookie's Valkey entry was DELed atomically
            by the Lua rotation script).
        access_expires_in: Seconds until the new access token expires.
        refresh_expires_in: Seconds until the new refresh cookie expires.
    """

    access_token: str
    new_refresh_token: str
    access_expires_in: int
    refresh_expires_in: int


@dataclass(frozen=True)
class RevokeResult:
    """Returned by ``iam.service.revoke_refresh_token``.

    Attributes:
        cookie_was_present: True if the request carried a refresh cookie.
            False on the idempotent "logout twice" path. Drives whether the
            service writes an ``auth.logout`` audit row.
        user_id: The resolved user_id when ``cookie_was_present`` AND the
            allowlist entry decoded cleanly. ``None`` on the no-cookie path.
    """

    cookie_was_present: bool
    user_id: UUID | None


@dataclass(frozen=True)
class UserProfile:
    """Returned by ``iam.service.get_profile`` — backs the ``/me`` response.

    Attributes:
        user_id: Primary key.
        phone: E.164 string. Surfaced to the seller; NOT scrubbed.
        plan: V1 always ``"free"``.
        created_at: Account creation timestamp.
        last_login_at: Last successful OTP verify timestamp; ``None`` on the
            (very rare) just-created edge case before any verify completes.
    """

    user_id: UUID
    phone: str
    plan: str
    created_at: datetime
    last_login_at: datetime | None


@dataclass(frozen=True)
class BillingStatus:
    """Returned by ``iam.service.get_billing_status`` — backs ``/auth/me`` and
    ``GET /billing/subscription`` (Razorpay Wave 3).

    Carries the DB-fresh plan facts plus the RESOLVED effective entitlement so
    the two read surfaces agree (F7 — entitlement read DB-fresh, not the JWT).

    Attributes:
        plan: ``users.plan`` (DB-fresh — the full Pricing v2 vocabulary).
        entitlement: The resolved effective tier from
            ``core.plan_guard.resolve_entitlement`` (``free``/``starter``/
            ``pro``/``business``; annual→base, ltd/trial→pro).
        status: The latest ``subscriptions.status``, or ``None`` for a
            free/trial user with no sub row.
        current_period_end: End of the current paid period; ``None`` =
            perpetual (LTD) or no sub.
        cancel_scheduled: True when the latest sub has ``cancel_scheduled_at``
            set (a cancel-at-cycle-end is pending).
        tier_label: Human label for the FE (e.g. ``"Pro"``, ``"Pro (Annual)"``,
            ``"Lifetime"``, ``"Free"``).
        trial_ends_at: The §3.7 14-day trial expiry; ``None`` if no trial.
    """

    plan: str
    entitlement: str
    status: str | None
    current_period_end: datetime | None
    cancel_scheduled: bool
    tier_label: str
    trial_ends_at: datetime | None


@dataclass(frozen=True)
class StartTrialResult:
    """Returned by ``iam.service.start_trial`` (Razorpay Wave 3, §3.7).

    Attributes:
        trial_ends_at: The freshly set ``users.trial_ends_at`` (now + 14 days).
        entitlement: Always ``"pro"`` — the trial grants Pro-level entitlement.
    """

    trial_ends_at: datetime
    entitlement: str


@dataclass(frozen=True)
class WebhookCaptureResult:
    """Returned by ``iam.service.capture_razorpay_webhook``.

    Attributes:
        event_type: The Razorpay event type processed (e.g.
            ``subscription.activated``, ``payment.captured``).  For a
            deduplicated replay this is the event type of the duplicate;
            for an unknown/unmodelled event it is that event's type.
        event_subtype: Back-compat alias carrying the same Razorpay event
            string (preserved so existing callers/tests reading
            ``event_subtype`` keep working after the V1.5 router rework).
        audit_event_id: PK of the business ``audit_events`` row when a
            grant/downgrade/cancel effect was written; ``None`` for
            transport-only events (renewal heartbeat, unknown, dedupe replay).
            Widened from ``int`` to ``int | None`` in Wave 2 (the V1
            sentinel ``0`` is retired in favour of ``None``).
    """

    event_type: str
    event_subtype: str
    audit_event_id: int | None


@dataclass(frozen=True)
class GoogleUpsertOutcome:
    """Returned by ``repository.upsert_user_on_google_login`` (google-auth).

    Carries the resolved ``User`` plus discriminator flags so the service can
    emit the right audit events (design §E.2 / §F.3) and decide whether to
    raise ``GoogleIdentityConflictError`` (the iam exceptions module).

    Attributes:
        user: The (new, linked, or returning) ``User`` ORM instance, flushed.
            On ``conflict=True`` this is the existing email-owner row (the
            service raises 409 and does NOT issue tokens for it).
        linked: True when an existing phone user gained a Google identity
            (rule 2) — triggers an ``auth.google.linked`` audit row.
        created: True when a brand-new Google-only user was created (rule 3).
        email_changed: True when a returning Google user's token email differs
            from the stored email (rule 1 edge case 3) — info-logged, not
            overwritten in V1.
        conflict: True when the verified email belongs to a DIFFERENT
            ``google_sub`` (edge case 4) — the service raises 409.
    """

    user: "User"
    linked: bool
    created: bool
    email_changed: bool
    conflict: bool


__all__ = [
    "OtpRecord",
    "RefreshAllowlistEntry",
    "SendOtpResult",
    "VerifyOtpResult",
    "RotateRefreshResult",
    "RevokeResult",
    "UserProfile",
    "WebhookCaptureResult",
    "GoogleUpsertOutcome",
]
