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
    """``GET /api/v1/auth/me`` 200 body."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    phone: str | None = None  # google-auth: NULL for Google-only users (matches users.phone nullable)
    plan: Literal["free"]
    created_at: datetime
    last_login_at: datetime | None = None
    # Cross-module fact sourced from the customer module's
    # ``get_onboarding_completeness`` surface (see router).  Resolves to
    # ``False`` for a brand-new seller with no profile row yet — never raises.
    onboarding_complete: bool = False


class WebhookCaptureResponse(BaseModel):
    """``POST /api/v1/webhooks/razorpay`` 200 body."""

    captured: bool = True


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
]
