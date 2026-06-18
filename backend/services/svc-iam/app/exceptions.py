"""``iam`` module exceptions — subclasses of :class:`app.core.errors.MeesellError`.

Per BACKEND_ARCHITECTURE.md §7.G (LOCKED 2026-06-05) + §5A.H validation-
message-id naming convention.

Validation-message-id segment count
-----------------------------------
§5A.H locks the convention as **3 dot-separated snake_case segments**:

    ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*){2}$

§19 CI Contract 10 (`test_messages_en_id_regex.py`) enforces the regex.
§7.G prose uses 2-segment IDs (``auth.otp_invalid``); the registry at
``app/i18n/messages_en.py`` uses 3-segment IDs (``auth.otp.invalid``).
This module uses the **3-segment registry form** to match what the resolver
actually finds. The auth-builder dispatch flagged the §7.G prose ↔ §5A.H
mismatch to the master; the registry won.

Exception inventory (8 classes per §7.G + the auth-builder's
``MalformedWebhookPayloadError`` to fill the 8th slot for §7.B.6 step 4):

================================  =======  ==============================
Class                             status   validation_message_id
================================  =======  ==============================
IamError (base)                   —        — (inherits MeesellError defaults)
InvalidPhoneFormatError           400      validation.phone.invalid_format
InvalidOtpFormatError             400      validation.otp.invalid_format
MalformedWebhookPayloadError      400      validation.webhook.malformed_payload
OtpInvalidError                   401      auth.otp.invalid
OtpAttemptsExceededError          401      auth.otp.attempts_exceeded
RefreshInvalidError               401      auth.refresh.invalid
WebhookSignatureInvalidError      401      auth.webhook.signature_invalid
Msg91UnavailableError             503      auth.msg91.unavailable
================================  =======  ==============================

The three ``auth.token.*`` IDs (``missing``, ``expired``, ``user.not_found``)
are owned by ``core/auth.py`` per §4.B + §7.G note; NOT raised by this module.
"""

from __future__ import annotations

from app.core.errors import MeesellError


class IamError(MeesellError):
    """Base class for ``iam`` module failures. Never raised directly."""

    code = "iam.base"


class InvalidPhoneFormatError(IamError):
    """Raised when the request body's ``phone`` fails E.164 regex.

    Per §7.B.1 / §7.B.2 prose this is normally caught by Pydantic's regex
    validator (which fires the 422 ``validation.phone.invalid_format``
    envelope via :class:`app.core.errors._pydantic_validation_handler`).
    This subclass exists for service-layer raises (e.g. defensive re-checks)
    and to keep the 8-message-ID inventory complete.
    """

    code = "iam.invalid_phone_format"
    status_code = 400
    validation_message_id = "validation.phone.invalid_format"

    def __init__(self, detail: str = "Phone number is not a valid E.164 value") -> None:
        super().__init__(detail=detail)


class InvalidOtpFormatError(IamError):
    """Raised when the OTP body field fails the 6-digit regex.

    Same role as :class:`InvalidPhoneFormatError` — Pydantic normally fires.
    """

    code = "iam.invalid_otp_format"
    status_code = 400
    validation_message_id = "validation.otp.invalid_format"

    def __init__(self, detail: str = "OTP must be 6 digits") -> None:
        super().__init__(detail=detail)


class MalformedWebhookPayloadError(IamError):
    """Raised when a Razorpay webhook body parses past HMAC but fails JSON load.

    Per §7.B.6 step 4: signature valid but JSON parse fails → 400 with
    ``validation.webhook.malformed_payload``. Distinct from
    :class:`WebhookSignatureInvalidError` so client + ops dashboards can
    tell "signed but malformed" apart from "unsigned attacker".
    """

    code = "iam.webhook_malformed_payload"
    status_code = 400
    validation_message_id = "validation.webhook.malformed_payload"

    def __init__(self, detail: str = "Webhook payload could not be parsed as JSON") -> None:
        super().__init__(detail=detail)


class OtpInvalidError(IamError):
    """Raised when the stored OTP is missing/expired or the presented OTP mismatches.

    Per §7.B.2 mapping: 401 / ``auth.otp.invalid``. The "attempt < 3"
    mismatch path raises this; the "3rd attempt" path raises
    :class:`OtpAttemptsExceededError` instead.
    """

    code = "iam.otp_invalid"
    status_code = 401
    validation_message_id = "auth.otp.invalid"

    def __init__(self, detail: str = "OTP is invalid or has expired") -> None:
        super().__init__(detail=detail)


class OtpAttemptsExceededError(IamError):
    """Raised when the seller has burned their 3rd wrong OTP attempt.

    Per §7.B.2 flow step 2: after the 3rd mismatch the OTP record is
    ``DEL``ed in Valkey; a fresh ``/otp/send`` is required.  Maps to
    401 / ``auth.otp.attempts_exceeded`` so the frontend can render a
    differentiating "wait + request new OTP" CTA.
    """

    code = "iam.otp_attempts_exceeded"
    status_code = 401
    validation_message_id = "auth.otp.attempts_exceeded"

    def __init__(self, detail: str = "Too many OTP attempts. Request a new OTP.") -> None:
        super().__init__(detail=detail)


class RefreshInvalidError(IamError):
    """Raised when the refresh cookie is missing / unknown / already-rotated.

    Per §7.B.3 mapping: 401 / ``auth.refresh.invalid``.  The three
    underlying failure causes ("missing cookie", "expired allowlist
    entry", "rotation race lost") all surface the same client-visible
    error; the ``reason`` is captured only in the direct-ORM audit row
    that the service writes alongside the raise.
    """

    code = "iam.refresh_invalid"
    status_code = 401
    validation_message_id = "auth.refresh.invalid"

    def __init__(self, detail: str = "Refresh token is invalid or already used") -> None:
        super().__init__(detail=detail)


class WebhookSignatureInvalidError(IamError):
    """Raised when ``adapters.razorpay.verify_webhook_signature`` returns False.

    Per §7.B.6 mapping: 401 / ``auth.webhook.signature_invalid``.  Razorpay
    expects 401 on bad signatures; per §6.E the adapter returns ``bool``
    (does not raise), and this exception is the service-layer translation.
    """

    code = "iam.webhook_signature_invalid"
    status_code = 401
    validation_message_id = "auth.webhook.signature_invalid"

    def __init__(self, detail: str = "Webhook signature is invalid") -> None:
        super().__init__(detail=detail)


class Msg91UnavailableError(IamError):
    """Raised when ``adapters.msg91.send_otp`` returns ``success=False``.

    Per §7.B.1 mapping: 503 / ``auth.msg91.unavailable``.  Per §6.C the
    MSG91 adapter NEVER raises on transport failure — it returns
    :class:`Msg91Response(success=False, ...)`.  The service translates
    that into this exception so :class:`app.core.errors.MeesellError`
    error-handling can build the standard envelope.
    """

    code = "iam.msg91_unavailable"
    status_code = 503
    validation_message_id = "auth.msg91.unavailable"

    def __init__(self, detail: str = "OTP service temporarily unavailable") -> None:
        super().__init__(detail=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Google Sign-In errors (google-auth feature, 2026-06-18 — design §C.4)
# ─────────────────────────────────────────────────────────────────────────────
class GoogleTokenInvalidError(IamError):
    """Raised when a Google ID-token fails verification.

    Covers bad signature, wrong ``aud``, wrong ``iss``, expired, or malformed
    (the library's ``ValueError``).  Maps to 401 / ``auth.google.token_invalid``.
    The raw token is NEVER surfaced or logged.
    """

    code = "iam.google_token_invalid"
    status_code = 401
    validation_message_id = "auth.google.token_invalid"

    def __init__(self, detail: str = "Google sign-in token is invalid or expired") -> None:
        super().__init__(detail=detail)


class GoogleEmailUnverifiedError(IamError):
    """Raised when a Google ID-token's ``email_verified`` is not true.

    The anti-spoofing gate for email-based account linking — we only link or
    create on a Google-verified email.  Maps to 401 /
    ``auth.google.email_unverified``.
    """

    code = "iam.google_email_unverified"
    status_code = 401
    validation_message_id = "auth.google.email_unverified"

    def __init__(self, detail: str = "Your Google email is not verified") -> None:
        super().__init__(detail=detail)


class GoogleUnavailableError(IamError):
    """Raised when Google's certificate endpoint is unreachable.

    Analogous to :class:`Msg91UnavailableError` (a vendor outage), but here the
    adapter RAISES (the §6.G default) rather than returning a bool.  Maps to
    503 / ``auth.google.unavailable``.
    """

    code = "iam.google_unavailable"
    status_code = 503
    validation_message_id = "auth.google.unavailable"

    def __init__(self, detail: str = "Google sign-in is temporarily unavailable") -> None:
        super().__init__(detail=detail)


class GoogleIdentityConflictError(IamError):
    """Raised when a verified email belongs to a *different* ``google_sub``.

    Design §E.3 edge case 4: two distinct Google accounts claim the same
    verified email (should be impossible — Google enforces email uniqueness per
    account).  We fail closed rather than hijack.  Maps to 409 /
    ``auth.google.identity_conflict``.
    """

    code = "iam.google_identity_conflict"
    status_code = 409
    validation_message_id = "auth.google.identity_conflict"

    def __init__(
        self, detail: str = "This email is already linked to a different Google account"
    ) -> None:
        super().__init__(detail=detail)


__all__ = [
    "IamError",
    "InvalidPhoneFormatError",
    "InvalidOtpFormatError",
    "MalformedWebhookPayloadError",
    "OtpInvalidError",
    "OtpAttemptsExceededError",
    "RefreshInvalidError",
    "WebhookSignatureInvalidError",
    "Msg91UnavailableError",
    "GoogleTokenInvalidError",
    "GoogleEmailUnverifiedError",
    "GoogleUnavailableError",
    "GoogleIdentityConflictError",
]
