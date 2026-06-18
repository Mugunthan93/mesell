"""svc-iam i18n message registry — vendored SUBSET (SUB_PLAN_0G §"Code surfaces").

Carries the iam-relevant ``validation_message_id`` strings VERBATIM from the
monolith ``app.i18n.messages_en``:

* the 3 ``core/auth.py`` auth-dependency IDs (``auth.token.missing`` /
  ``auth.token.expired`` / ``auth.user.not_found``) — these resolve the
  envelopes raised by the vendored ``core/auth.py`` (auth-builder's file);
* the 8 iam module IDs raised by ``exceptions.py`` (the 9-class IamError
  hierarchy; ``IamError`` base carries no own ID — it inherits MeesellError
  defaults), and
* the 3 cross-cutting registry IDs the vendored core layer
  (tenancy / plan_guard / server-fallback) may resolve.

The full monolith registry (55 IDs across 8 domains) is NOT vendored — only
the IDs an iam request can actually surface.

NOTE on the §5A.H 3-segment regex (the L_iam_1 latent — carried, NOT fixed):
``core/auth.py`` raises 2-segment runtime IDs (``auth.token_missing`` etc.);
the registry keys here are the 3-segment forms (``auth.token.missing`` etc.).
The resolver falls through 2-segment IDs to verbatim (same posture as the
monolith — services-builder D1).  svc-iam preserves this behaviour exactly;
migrating the runtime IDs to 3-segment is a V1.5 latent, out of extraction
scope (SUB_PLAN_0G "extraction preserves behavior").
"""

from __future__ import annotations

VALIDATION_MESSAGES: dict[str, str] = {
    # ── core/auth.py (§4.B + §7.G — auth-dependency surface) ──────────────
    "auth.token.missing": "You're not signed in. Please sign in to continue.",
    "auth.token.expired": "Your session has expired. Please sign in again.",
    "auth.user.not_found": "We couldn't find your account. Please sign in again.",
    # ── §7 iam (8 module-specific IDs — verbatim from monolith) ──────────
    "validation.phone.invalid_format": (
        "Please enter a valid 10-digit Indian mobile number."
    ),
    "validation.otp.invalid_format": (
        "Please enter the 6-digit OTP we sent to your phone."
    ),
    "validation.webhook.malformed_payload": (
        "We received an unreadable webhook payload."
    ),
    "auth.otp.invalid": (
        "That OTP didn't match. Please check the code and try again."
    ),
    "auth.otp.attempts_exceeded": (
        "Too many wrong attempts. Please request a new OTP after a few minutes."
    ),
    "auth.msg91.unavailable": (
        "Our OTP service is temporarily unavailable. Please try again in a moment."
    ),
    "auth.refresh.invalid": (
        "Your session can't be refreshed. Please sign in again."
    ),
    "auth.webhook.signature_invalid": (
        "Webhook signature could not be verified."
    ),
    # ── §7 iam — google-auth (5 IDs, 2026-06-18) ─────────────────────────
    "validation.credential.invalid_format": (
        "We couldn't read your Google sign-in. Please try again."
    ),
    "auth.google.token_invalid": (
        "Your Google sign-in could not be verified. Please try again."
    ),
    "auth.google.email_unverified": (
        "Your Google email isn't verified. Please verify it with Google and try again."
    ),
    "auth.google.unavailable": (
        "Google sign-in is temporarily unavailable. Please try again in a moment."
    ),
    "auth.google.identity_conflict": (
        "This email is already linked to a different Google account. Please contact support."
    ),
    # ── §4.C tenancy (1 cross-cutting ID) ────────────────────────────────
    "tenancy.cross_user.access": (
        "You do not have access to this resource."
    ),
    # ── §4.E plan_guard (1 cross-cutting ID) ─────────────────────────────
    "plan.limit.exceeded": (
        "You've reached your plan's limit. Upgrade to continue."
    ),
    # ── §4.F server fallback (1 cross-cutting ID) ────────────────────────
    "server.internal.error": (
        "Something went wrong on our end. Please try again."
    ),
}

__all__ = ["VALIDATION_MESSAGES"]
