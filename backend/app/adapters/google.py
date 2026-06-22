"""adapters/google.py — Google ID-token verification transport (§6, google-auth).

The 6th adapter (alongside msg91, razorpay, gcs, gemini, langfuse).  Pure
transport/verification boundary: it verifies a Google Identity Services
ID-token and returns typed claims.  It contains NO business logic — no user
upsert, no token issuance, no linking (those live in the iam ``service.py``).

MONOLITH NOTE: this is the byte-parity twin of
``backend/services/svc-iam/app/adapters/google.py``.  The ONLY difference is
the exceptions import path (the monolith nests iam exceptions under
``app.modules.iam.exceptions``; svc-iam uses the flat ``app.exceptions``).

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
        → :class:`app.modules.iam.exceptions.GoogleTokenInvalidError` (401).
  * network error reaching Google's certs endpoint
        → :class:`app.modules.iam.exceptions.GoogleUnavailableError` (503).
  * ``email_verified`` false/absent
        → :class:`app.modules.iam.exceptions.GoogleEmailUnverifiedError` (401).

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
import secrets
from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.auth.exceptions import GoogleAuthError, TransportError
from google.oauth2 import id_token

from app.modules.iam.exceptions import (
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


def _resolve_dev_bypass_claims(credential: str) -> GoogleClaims | None:
    """Return synthetic verified claims iff the dev-google bypass is active AND
    ``credential`` exactly equals the configured sentinel; otherwise ``None``.

    THREE independent guards — ALL must hold or the bypass is inert and the
    real Google verify path runs unchanged:

      1. ``settings.APP_ENV != "production"``  — force-disabled in prod
         regardless of config (mirrors the OTP-bypass ``test_prod_force_disable``
         contract).  This is checked FIRST so a leaked prod sentinel never
         even reaches the comparison.
      2. ``settings.DEV_GOOGLE_BYPASS_TOKEN`` is NON-EMPTY.
      3. ``settings.FEATURE_GOOGLE_AUTH_ENABLED`` is True (the route is not
         mounted otherwise, but we gate defensively).

    Sentinel format (``dev-google:{sub}:{email}``) encodes the test identity so
    e2e/integration lanes can drive different dual-identity users.  The
    comparison is constant-time and the raw credential is never logged.
    """
    # Guard 1 — hard prod kill-switch, checked before anything else.
    if settings.APP_ENV == "production":
        return None
    # Guards 2 + 3 — bypass must be configured AND the feature must be on.
    configured = settings.DEV_GOOGLE_BYPASS_TOKEN
    if not configured or not settings.FEATURE_GOOGLE_AUTH_ENABLED:
        return None
    # Exact-match the sentinel (constant-time); a non-match → real verify.
    if not secrets.compare_digest(credential, configured):
        return None

    # Parse the identity out of the sentinel: dev-google:{sub}:{email}
    parts = configured.split(":", 2)
    if len(parts) != 3 or parts[0] != "dev-google" or not parts[1] or not parts[2]:
        # Malformed sentinel — refuse to synthesise (do NOT silently fall
        # through to real verify either; a misconfigured dev sentinel is a
        # config error the developer must fix).
        logger.warning(
            "google.verify_id_token dev-bypass sentinel malformed "
            "(expected 'dev-google:{sub}:{email}') — rejecting."
        )
        raise GoogleTokenInvalidError()

    _, sub, email = parts
    logger.warning(
        "google.verify_id_token DEV BYPASS ACTIVE (APP_ENV=%s) — synthetic "
        "claims, NO real Google verify. sub_present=%s email_present=%s.",
        settings.APP_ENV,
        bool(sub),
        bool(email),
    )
    return GoogleClaims(
        sub=sub,
        email=email,
        email_verified=True,
        name=email.split("@", 1)[0],
        picture=None,
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
    # ── Dev/test bypass (PROD-HARD-DISABLED) ───────────────────────────────
    # When the sentinel matches AND APP_ENV != "production" AND the feature is
    # on, resolve synthetic verified claims without calling Google.  In prod,
    # OR when the sentinel does not match, this returns None and the REAL
    # verify path below runs byte-identically to before this seam existed.
    bypass_claims = _resolve_dev_bypass_claims(credential)
    if bypass_claims is not None:
        return bypass_claims

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
