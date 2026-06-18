"""adapters/google.py — Google ID-token verification transport (§6, google-auth).

The 6th adapter (alongside msg91, razorpay).  Pure transport/verification
boundary: it verifies a Google Identity Services ID-token and returns typed
claims.  It contains NO business logic — no user upsert, no token issuance,
no linking (those live in ``service.py``).

Verification (design §D.3) — ``google.oauth2.id_token.verify_oauth2_token``
enforces in ONE call:
  * signature against Google's published JWKs,
  * ``exp`` not in the past (small clock-skew tolerance built in),
  * ``aud`` ∈ ``settings.GOOGLE_OAUTH_CLIENT_ID`` (audience-confusion defence),
  * ``iss`` ∈ {accounts.google.com, https://accounts.google.com}.
This adapter additionally enforces ``email_verified == true`` — THE
anti-spoofing gate for email-based account linking.

Failure modes (design §D.5) — this adapter RAISES typed errors (it does NOT
follow the msg91/razorpay non-raise pattern; it follows the §6.G default
raise-on-failure pattern):
  * ``ValueError`` from the library (bad sig / aud / exp / malformed)
        → :class:`app.exceptions.GoogleTokenInvalidError` (401).
  * network error reaching Google's certs endpoint
        → :class:`app.exceptions.GoogleUnavailableError` (503).
  * ``email_verified`` false/absent
        → :class:`app.exceptions.GoogleEmailUnverifiedError` (401).

Security invariants (do not relax):
  * The raw ``credential`` (the ID-token) is NEVER logged.  Only presence
    booleans (``email_verified``, ``sub`` present) are logged.
  * ``settings.GOOGLE_OAUTH_CLIENT_ID`` is read from config — NEVER os.getenv
    (§6.G CI-enforced).
  * The cert-fetching ``Request`` transport is a module-level singleton so
    Google's JWKs are cached across calls within the worker process (design
    §D.4) — do NOT construct a new ``Request()`` per call.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.auth.exceptions import GoogleAuthError, TransportError
from google.oauth2 import id_token

from app.exceptions import (
    GoogleEmailUnverifiedError,
    GoogleTokenInvalidError,
    GoogleUnavailableError,
)
from app.shared.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleClaims:
    """Typed, immutable subset of a verified Google ID-token's claims.

    Google SDK quirks never leak past this boundary (design §D.1 / §2.9 M10).

    Attributes:
        sub: Google's stable subject identifier — the durable identity key.
        email: The verified email address (linking key).
        email_verified: Always True for a returned ``GoogleClaims`` (the
            adapter raises if it is not true).
        name: Display name from the token, may be empty.
        picture: Avatar URL, or None when absent.
    """

    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str | None


# ── Module-level singleton cert transport (caches Google JWKs) ──────────────
_request_transport: google_requests.Request | None = None


def _get_request_transport() -> google_requests.Request:
    """Lazy singleton ``Request`` — caches Google's JWKs across calls."""
    global _request_transport
    if _request_transport is None:
        _request_transport = google_requests.Request()
    return _request_transport


def _verify_sync(credential: str) -> dict:
    """Synchronous, CPU/network-bound verify — wrapped by the async surface.

    Returns the raw claims dict on success.  Raises the library's
    ``ValueError`` (bad sig/aud/exp) or transport errors — translated by the
    async caller.
    """
    return id_token.verify_oauth2_token(
        credential,
        _get_request_transport(),
        # audience accepts a list of valid client IDs (Web + future native);
        # the library checks membership.  Empty would be rejected by config.
        audience=list(settings.GOOGLE_OAUTH_CLIENT_ID),
    )


async def verify_id_token(credential: str) -> GoogleClaims:
    """Verify a Google ID-token and return typed claims.

    Args:
        credential: The raw Google Identity Services ID-token (a JWT).  NEVER
            logged.  Consumed once; never stored.

    Returns:
        :class:`GoogleClaims` with ``email_verified is True``.

    Raises:
        GoogleTokenInvalidError: signature / aud / iss / exp / malformed.
        GoogleEmailUnverifiedError: token valid but ``email_verified`` not true.
        GoogleUnavailableError: Google's certs endpoint unreachable.
    """
    try:
        # The library call is sync (signature math + a cached cert fetch); run
        # it off the event loop so we never block other requests.
        claims = await asyncio.to_thread(_verify_sync, credential)
    except TransportError as exc:
        # Network error reaching Google's JWKs endpoint → 503.
        logger.warning("google.verify_id_token transport error: %r", exc)
        raise GoogleUnavailableError() from exc
    except ValueError as exc:
        # Bad signature / wrong aud / wrong iss / expired / malformed → 401.
        # ValueError message may embed token-derived detail; do NOT log it raw.
        logger.info("google.verify_id_token rejected token (invalid).")
        raise GoogleTokenInvalidError() from exc
    except GoogleAuthError as exc:
        # Any other google-auth failure that is not a transport error → 401.
        logger.info("google.verify_id_token google-auth error: %s", type(exc).__name__)
        raise GoogleTokenInvalidError() from exc

    email_verified = bool(claims.get("email_verified", False))
    sub = str(claims.get("sub") or "")
    email = str(claims.get("email") or "")

    if not email_verified:
        logger.info(
            "google.verify_id_token email_verified=false sub_present=%s — rejecting.",
            bool(sub),
        )
        raise GoogleEmailUnverifiedError()

    if not sub or not email:
        # A verified Google token always carries sub + email; defend anyway.
        logger.info(
            "google.verify_id_token missing sub/email (sub_present=%s email_present=%s).",
            bool(sub),
            bool(email),
        )
        raise GoogleTokenInvalidError()

    return GoogleClaims(
        sub=sub,
        email=email,
        email_verified=True,
        name=str(claims.get("name") or ""),
        picture=(str(claims["picture"]) if claims.get("picture") else None),
    )


# ── Test helper ─────────────────────────────────────────────────────────────
def _reset_for_testing() -> None:
    """Reset the module singleton.  Called from test fixtures only."""
    global _request_transport
    _request_transport = None
