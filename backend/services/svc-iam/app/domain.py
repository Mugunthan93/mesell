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
from uuid import UUID


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
class WebhookCaptureResult:
    """Returned by ``iam.service.capture_razorpay_webhook``.

    Attributes:
        event_type: Always ``"razorpay.webhook.captured"`` in V1.
        event_subtype: The parsed-event name from the payload (e.g.
            ``subscription.created``, ``subscription.charged``).
        audit_event_id: PK of the row written to ``audit_events``.
    """

    event_type: str
    event_subtype: str
    audit_event_id: int


__all__ = [
    "OtpRecord",
    "RefreshAllowlistEntry",
    "SendOtpResult",
    "VerifyOtpResult",
    "RotateRefreshResult",
    "RevokeResult",
    "UserProfile",
    "WebhookCaptureResult",
]
