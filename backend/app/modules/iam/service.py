"""``iam`` service layer — 6 async PUBLIC methods per §7.C.

Per BACKEND_ARCHITECTURE.md §7 (LOCKED 2026-06-05) +
§4.B (FE-D5 split-token amendment) +
§7.I documented exception for direct-ORM audit writes.

Locked invariants (do not relax)
--------------------------------
* OTP plaintext is NEVER logged or persisted; only its SHA-256 hex digest.
* OTP comparison uses :func:`secrets.compare_digest` — never ``==``.
* Refresh allowlist key uses ``cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}``
  (HMAC-with-pepper per §4.B FE-D5 amendment, NOT bare SHA-256).
* Refresh rotation runs inside a server-side Lua script via EVALSHA / EVAL
  (single round-trip, no race window) — never MULTI/EXEC.
* Audit rows for ``verify_otp``, ``refresh``, and ``logout`` are written
  inside this service via direct ORM, NOT via ``audit_mw`` — the §7.I
  documented exception (the cookie-resolved ``user_id`` is known only here,
  BEFORE the Valkey ``DEL``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import google as google_adapter
from app.adapters import msg91 as msg91_adapter
from app.adapters import razorpay as razorpay_adapter
from app.core.auth import (
    issue_access_token,
    issue_refresh_token,
    refresh_allowlist_key,
    rotate_refresh_token as rotate_refresh_token_in_valkey,
    validate_refresh_allowlist,
)
from app.core.metrics import AUTH_TOKEN_REFRESH_FAILED
from app.modules.iam import repository as iam_repo
from app.modules.iam.domain import (
    BillingStatus,
    CancelSubscriptionResult,
    OtpRecord,
    RefreshAllowlistEntry,
    RevokeResult,
    RotateRefreshResult,
    SendOtpResult,
    StartTrialResult,
    SubscribeResult,
    UserProfile,
    VerifyOtpResult,
    WebhookCaptureResult,
)
from app.modules.iam.exceptions import (
    AlreadySubscribedError,
    GoogleIdentityConflictError,
    MalformedWebhookPayloadError,
    Msg91UnavailableError,
    NoActiveSubscriptionError,
    OtpAttemptsExceededError,
    OtpInvalidError,
    RefreshInvalidError,
    TrialAlreadyUsedError,
    WebhookSignatureInvalidError,
)
from app.shared.config import settings
from app.shared.database import AsyncSessionLocal
from app.shared.models.audit_event import AuditEvent
from app.shared.models.payment import Payment
from app.shared.models.subscription import Subscription
from app.shared.models.user import User
from app.shared.models.webhook_event import WebhookEvent

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
_OTP_TTL_SECONDS = 300
"""5 minutes per §7.B.1 + CLAUDE.md OTP TTL lock."""

_OTP_MAX_ATTEMPTS = 3
"""3rd wrong attempt triggers ``OtpAttemptsExceededError`` per §7.B.2."""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (module-private)
# ─────────────────────────────────────────────────────────────────────────────
def _otp_key(phone: str) -> str:
    """Valkey DB 0 keyspace for the OTP record per §7.B.1 + CLAUDE.md."""
    return f"otp:{phone}"


def _hash_otp(otp: str) -> str:
    """SHA-256 hex digest of the OTP — what we persist + constant-time compare."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    """Crypto-strong 6-digit OTP via :func:`secrets.choice` per §7.B.1 step 3."""
    return "".join(secrets.choice("0123456789") for _ in range(6))


def _serialize_otp_record(record: OtpRecord) -> str:
    return json.dumps(
        {
            "otp_hash": record.otp_hash,
            "attempts": record.attempts,
            "expires_at": record.expires_at,
        }
    )


def _deserialize_otp_record(raw: str | bytes | None) -> OtpRecord | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        data = json.loads(raw)
        return OtpRecord(
            otp_hash=str(data["otp_hash"]),
            attempts=int(data["attempts"]),
            expires_at=int(data["expires_at"]),
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        logger.warning("iam.otp_record.malformed — treating as missing")
        return None


def _serialize_allowlist_entry(entry: RefreshAllowlistEntry) -> str:
    return json.dumps(
        {
            "user_id": str(entry.user_id),
            "issued_at": entry.issued_at,
            "ip": entry.ip,
        }
    )


def _deserialize_allowlist_entry(raw: str | bytes | None) -> RefreshAllowlistEntry | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        data = json.loads(raw)
        return RefreshAllowlistEntry(
            user_id=UUID(str(data["user_id"])),
            issued_at=int(data["issued_at"]),
            ip=str(data["ip"]),
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        logger.warning("iam.allowlist_entry.malformed — treating as missing")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Audit writes — DIRECT ORM (§7.I documented exception to audit_mw rule).
# ─────────────────────────────────────────────────────────────────────────────
async def _write_audit_direct(
    user_id: UUID | None,
    event_type: str,
    *,
    db: AsyncSession | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    metadata: dict | None = None,
    diff: dict | None = None,
) -> int | None:
    """Write an ``audit_events`` row per §7.I documented exception.

    Two dispatch paths:

    * **In-request path** (``db`` provided) — the audit row is inserted
      inside a SAVEPOINT on the caller's session.  This is REQUIRED for
      events whose ``user_id`` references a row that the caller has
      ``flush``ed but not yet committed (e.g. ``auth.login.success``
      on the verify path — the user upsert is in-flight within the
      route's ``get_db`` transaction; a separate session would see the
      pre-commit snapshot and FK-fail).  The SAVEPOINT preserves the
      drop-on-failure invariant: an audit error rolls back only the
      nested transaction, never the outer business write.

    * **Out-of-request path** (``db`` is None) — opens its own
      :data:`AsyncSessionLocal` session.  Used for events that fire
      from a context with no active request session (none currently in
      iam; reserved for future Celery callbacks).

    Returns the row ID on success, ``None`` on any failure or when
    ``user_id`` is None (the ``audit_events`` table requires NOT NULL
    ``user_id`` per §11.2 DDL; we elide the write rather than violate it).
    """
    if user_id is None:
        return None

    def _build_row() -> AuditEvent:
        return AuditEvent(
            user_id=user_id,
            event_type=event_type[:40],  # column is String(40)
            entity_type=entity_type,
            entity_id=entity_id,
            diff_jsonb=diff,
            metadata_jsonb=metadata,
        )

    if db is not None:
        # In-request: SAVEPOINT so audit failure does not poison the txn.
        try:
            async with db.begin_nested():
                row = _build_row()
                db.add(row)
                await db.flush()
            return int(row.id) if row.id is not None else None
        except Exception as exc:  # noqa: BLE001 — drop-on-failure
            logger.warning(
                "audit_events direct-write failed inside savepoint "
                "(event=%s, user=%s): %s",
                event_type,
                user_id,
                exc,
            )
            return None

    # Out-of-request: independent session.
    try:
        async with AsyncSessionLocal() as session:
            row = _build_row()
            session.add(row)
            await session.commit()
            return int(row.id) if row.id is not None else None
    except Exception as exc:  # noqa: BLE001 — drop-on-failure
        logger.warning(
            "audit_events direct-write failed (event=%s, user=%s): %s",
            event_type,
            user_id,
            exc,
        )
        return None


def _hash_phone_for_audit(phone: str) -> str:
    """SHA-256(phone + AUDIT_PII_SALT) per MVP_ARCH §11.9 PII scrubbing rule.

    Identical to ``app/core/middleware/audit_mw.py:_hash_phone``; duplicated
    here because the direct-ORM audit path bypasses the middleware.
    """
    salt = settings.AUDIT_PII_SALT
    return hashlib.sha256((phone + salt).encode("utf-8")).hexdigest()


def _hash_email_for_audit(email: str) -> str:
    """SHA-256(email + AUDIT_PII_SALT) — email is PII (google-auth §F.3).

    Mirrors :func:`_hash_phone_for_audit`; the Google login audit row stores
    the hashed email, never the plaintext.
    """
    salt = settings.AUDIT_PII_SALT
    return hashlib.sha256((email + salt).encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Public service surface — §7.C six methods.
# ─────────────────────────────────────────────────────────────────────────────
async def send_otp_for_login(phone: str, valkey: Redis) -> SendOtpResult:
    """``POST /api/v1/auth/otp/send`` business path per §7.B.1.

    Steps:

    1. Generate 6-digit OTP via :func:`_generate_otp`.
    2. Persist :class:`OtpRecord` (hash only) to Valkey DB 0 under
       ``otp:{phone}`` with TTL 300 s.
    3. Dispatch via MSG91 adapter — raise :class:`Msg91UnavailableError`
       on adapter ``success=False`` (per §6.C the adapter never raises).
    """
    otp = _generate_otp()
    record = OtpRecord(
        otp_hash=_hash_otp(otp),
        attempts=0,
        expires_at=int(time.time()) + _OTP_TTL_SECONDS,
    )
    await valkey.set(_otp_key(phone), _serialize_otp_record(record), ex=_OTP_TTL_SECONDS)

    response = await msg91_adapter.send_otp(phone, otp)
    if not response.success:
        # The OTP record stays in Valkey — the seller can retry without
        # being rate-limited by us (vendor outage shouldn't burn their 3/h).
        # Per §7.B.1 mapping: 503 / auth.msg91.unavailable.
        raise Msg91UnavailableError()

    # NOTE: `auth.otp.sent` audit row is emitted by `audit_mw` on 2xx response
    # per §7.B.1 audit-event row — direct write NOT used here (no exception
    # path needs the cookie-resolved user_id).
    return SendOtpResult(request_id=response.request_id or "")


async def verify_otp_and_issue_tokens(
    phone: str,
    otp: str,
    client_ip: str,
    db: AsyncSession,
    valkey: Redis,
) -> VerifyOtpResult:
    """``POST /api/v1/auth/otp/verify`` business path per §7.B.2.

    Atomicity note: the user upsert uses the caller's ``db`` session
    (committed by ``get_db``'s commit-on-yield).  The Valkey writes (OTP
    DEL, allowlist SET) are NOT in a Valkey transaction — Valkey ops on
    DB 0 are individually atomic and the rare partial-success path
    (allowlist set but OTP DEL fails) yields a single-use OTP that will
    naturally expire at the 300 s TTL.

    Audit writes are direct-ORM per §7.I documented exception (the failed
    paths have no ``user_id`` for the middleware to extract from
    ``request.state.user``).
    """
    key = _otp_key(phone)
    raw = await valkey.get(key)
    record = _deserialize_otp_record(raw)

    if record is None:
        # Missing or expired OTP.  No user_id known — audit row CANNOT be
        # written (the audit_events.user_id is NOT NULL).  We log via the
        # service logger; ops dashboards still see the failure.
        logger.info("iam.verify_otp.miss phone_present=%s reason=missing_or_expired", bool(phone))
        raise OtpInvalidError()

    presented_hash = _hash_otp(otp)

    # ── Dev-only OTP bypass (dev-otp-bypass feature) ───────────────────────
    # Two independent guards: a NON-EMPTY configured code AND a non-production
    # APP_ENV.  In production the bypass is force-disabled here regardless of
    # the config value (so a misconfigured prod env var is inert).  The
    # record-exists gate above is unchanged: a real /otp/send must still have
    # seeded the Valkey record.  Only the code comparison is relaxed; a wrong
    # code under an active bypass still falls through to the mismatch /
    # attempts / lockout path below.
    bypass_active = bool(settings.DEV_OTP_BYPASS_CODE) and settings.APP_ENV != "production"
    bypass_match = bypass_active and secrets.compare_digest(otp, settings.DEV_OTP_BYPASS_CODE)

    if not bypass_match and not secrets.compare_digest(presented_hash, record.otp_hash):
        new_attempts = record.attempts + 1
        if new_attempts >= _OTP_MAX_ATTEMPTS:
            await valkey.delete(key)
            logger.info(
                "iam.verify_otp.lockout phone_present=%s attempts=%d",
                bool(phone),
                new_attempts,
            )
            raise OtpAttemptsExceededError()

        ttl_remaining = await valkey.ttl(key)
        updated = OtpRecord(
            otp_hash=record.otp_hash,
            attempts=new_attempts,
            expires_at=record.expires_at,
        )
        await valkey.set(
            key,
            _serialize_otp_record(updated),
            ex=max(int(ttl_remaining), 1),
        )
        logger.info(
            "iam.verify_otp.mismatch phone_present=%s attempts=%d",
            bool(phone),
            new_attempts,
        )
        raise OtpInvalidError()

    # ── SUCCESS PATH ─────────────────────────────────────────────────────
    user = await iam_repo.upsert_user_on_login(db, phone, client_ip, capture_dpdp=True)
    # ``get_db`` commits on yield — the user upsert lands when the route returns.

    # Mint access JWT — uses settings.ACCESS_TOKEN_TTL_SECONDS per §4.B amendment.
    access_token = issue_access_token(user.id, user.plan)

    # Mint refresh token (opaque) + persist allowlist entry.
    refresh_token = issue_refresh_token()
    allowlist_entry = RefreshAllowlistEntry(
        user_id=user.id,
        issued_at=int(time.time()),
        ip=client_ip,
    )
    await valkey.set(
        refresh_allowlist_key(refresh_token),
        _serialize_allowlist_entry(allowlist_entry),
        ex=settings.REFRESH_TOKEN_TTL_SECONDS,
    )

    # Single-use OTP — DEL after successful verify per §7.B.2 step 2.
    await valkey.delete(key)

    # Audit row — direct write per §7.I exception, in-request via SAVEPOINT
    # so the user_id FK resolves against the user we just upserted in the
    # same transaction.
    await _write_audit_direct(
        user_id=user.id,
        event_type="auth.login.success",
        db=db,
        metadata={
            "ip": client_ip,
            "hashed_phone": _hash_phone_for_audit(phone),
        },
    )

    return VerifyOtpResult(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
        refresh_expires_in=settings.REFRESH_TOKEN_TTL_SECONDS,
    )


async def verify_google_and_issue_tokens(
    credential: str,
    client_ip: str,
    db: AsyncSession,
    valkey: Redis,
) -> VerifyOtpResult:
    """``POST /api/v1/auth/google/verify`` business path (google-auth §F.2).

    Pipeline:

    1. Verify the Google ID-token via the adapter (raises typed errors;
       enforces signature / aud / iss / exp / ``email_verified``).
    2. Upsert/link the user per the deterministic linking rules (design §E).
       A 409 conflict (email owned by a different google_sub) raises
       :class:`GoogleIdentityConflictError`.
    3. Mint the access JWT + opaque refresh token and write the Valkey
       allowlist entry — the EXACT same issuance code as the OTP path
       (no new token shape / TTL / allowlist key format).
    4. Write the ``auth.login.success`` audit row (provider=google) via the
       §7.I direct-ORM SAVEPOINT path so the user_id FK resolves against the
       just-upserted row.  Emit ``auth.google.linked`` when a phone user
       gained a Google identity, and an info ``auth.google.email_changed``
       note when the token email differs from the stored email.

    Concurrency: a unique-violation on the create path (two concurrent first
    logins for the same new email/sub) is caught once, the session rolled back,
    and the upsert retried (now finds the row → links/logs in) per §E.4.

    Returns the SAME :class:`VerifyOtpResult` the OTP path returns — the router
    serialises it identically (access JWT in body, refresh token → cookie).
    """
    # ── Step 1 — verify the Google ID-token (typed raises) ─────────────────
    claims = await google_adapter.verify_id_token(credential)

    # ── Step 2 — upsert / link, with a single retry on a unique-violation ──
    try:
        outcome = await iam_repo.upsert_user_on_google_login(
            db,
            google_sub=claims.sub,
            email=claims.email,
            ip=client_ip,
            capture_dpdp=True,
        )
    except IntegrityError:
        # Race (§E.4 / edge case 7): a concurrent request created the same
        # new email/sub between our lookups and the INSERT.  Roll back the
        # poisoned transaction and retry once — the row now exists, so the
        # upsert resolves via rule 1/2 (login/link).
        logger.info("iam.google_login.integrity_race — retrying upsert once.")
        await db.rollback()
        outcome = await iam_repo.upsert_user_on_google_login(
            db,
            google_sub=claims.sub,
            email=claims.email,
            ip=client_ip,
            capture_dpdp=True,
        )

    if outcome.conflict:
        # Edge case 4 — verified email owned by a DIFFERENT google_sub.
        # Fail closed; no tokens issued.  No user_id audit row (we did not
        # authenticate anyone); the service logger records the event.
        logger.warning(
            "iam.google_login.identity_conflict existing_user=%s — failing closed (409).",
            outcome.user.id,
        )
        raise GoogleIdentityConflictError()

    user = outcome.user

    # ── Step 3 — mint tokens + allowlist entry (IDENTICAL to the OTP path) ─
    access_token = issue_access_token(user.id, user.plan)
    refresh_token = issue_refresh_token()
    allowlist_entry = RefreshAllowlistEntry(
        user_id=user.id,
        issued_at=int(time.time()),
        ip=client_ip,
    )
    await valkey.set(
        refresh_allowlist_key(refresh_token),
        _serialize_allowlist_entry(allowlist_entry),
        ex=settings.REFRESH_TOKEN_TTL_SECONDS,
    )

    # ── Step 4 — audit (direct-ORM SAVEPOINT, in-request) ──────────────────
    await _write_audit_direct(
        user_id=user.id,
        event_type="auth.login.success",
        db=db,
        metadata={
            "provider": "google",
            "ip": client_ip,
            "hashed_email": _hash_email_for_audit(claims.email),
        },
    )
    if outcome.linked:
        await _write_audit_direct(
            user_id=user.id,
            event_type="auth.google.linked",
            db=db,
            metadata={"ip": client_ip, "hashed_email": _hash_email_for_audit(claims.email)},
        )
    if outcome.email_changed:
        await _write_audit_direct(
            user_id=user.id,
            event_type="auth.google.email_changed",
            db=db,
            metadata={"ip": client_ip},
        )

    return VerifyOtpResult(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
        refresh_expires_in=settings.REFRESH_TOKEN_TTL_SECONDS,
    )


async def rotate_refresh_token(
    old_refresh_token: str | None,
    client_ip: str,
    db: AsyncSession,
    valkey: Redis,
) -> RotateRefreshResult:
    """``POST /api/v1/auth/refresh`` business path per §7.B.3.

    The Lua script (``app.core.auth.rotate_refresh_token_in_valkey``)
    atomically performs ``GET old_key → DEL old_key + SET new_key`` and
    returns 1/0.

    Failure paths (missing cookie, allowlist miss, race lost) all surface
    :class:`RefreshInvalidError`; the audit row distinguishes ``reason``.
    """
    if not old_refresh_token:
        # No user_id known on this failure path — _write_audit_direct
        # short-circuits when user_id is None (see DDL NOT NULL constraint).
        AUTH_TOKEN_REFRESH_FAILED.labels(reason="cookie_missing").inc()
        await _write_audit_direct(
            user_id=None,
            event_type="auth.token.refresh_failed",
            db=db,
            metadata={"reason": "missing", "ip": client_ip},
        )
        raise RefreshInvalidError()

    # Read the entry BEFORE rotation so we know the user_id for both the new
    # JWT (plan claim re-read) and the audit row.  This GET is not part of
    # the atomic rotation — the Lua script re-reads + DELs atomically.  The
    # window between this GET and EVAL is bounded by single-event-loop
    # serialisation (no other task in this request handles the same cookie).
    #
    # Dual-pepper (R5): validate_refresh_allowlist tries the CURRENT pepper/
    # version first, then falls back to PREVIOUS during a grace window. It
    # returns the MATCHED key so the Lua DEL below (KEYS[1]=old_key) targets
    # the exact key found — a cookie issued under vN-1 is rotated by DELeting
    # its vN-1 key and SETting the fresh vN key. The new key is ALWAYS current.
    matched = await validate_refresh_allowlist(valkey, old_refresh_token)
    old_key = matched[0] if matched is not None else refresh_allowlist_key(old_refresh_token)
    existing_raw = matched[1] if matched is not None else None
    existing_entry = _deserialize_allowlist_entry(existing_raw)

    new_refresh_token = issue_refresh_token()
    new_key = refresh_allowlist_key(new_refresh_token)

    if existing_entry is None:
        # Either expired, never existed, or malformed JSON.  The Lua call
        # below would also return 0; we short-circuit so the audit row has
        # the right reason without needing to ask the script.
        AUTH_TOKEN_REFRESH_FAILED.labels(reason="expired").inc()
        await _write_audit_direct(
            user_id=None,
            event_type="auth.token.refresh_failed",
            db=db,
            metadata={"reason": "expired", "ip": client_ip},
        )
        raise RefreshInvalidError()

    # Build the new payload.  Re-use the original ``issued_at`` semantics?
    # Per §7.B.3 step 3 the new entry is a fresh issuance — new issued_at.
    new_entry = RefreshAllowlistEntry(
        user_id=existing_entry.user_id,
        issued_at=int(time.time()),
        ip=client_ip,
    )

    rotated = await rotate_refresh_token_in_valkey(
        valkey,
        old_key=old_key,
        new_key=new_key,
        new_value=_serialize_allowlist_entry(new_entry),
        ttl_seconds=settings.REFRESH_TOKEN_TTL_SECONDS,
    )
    if not rotated:
        # Race lost — another concurrent /refresh already rotated.
        AUTH_TOKEN_REFRESH_FAILED.labels(reason="replay").inc()
        await _write_audit_direct(
            user_id=existing_entry.user_id,
            event_type="auth.token.refresh_failed",
            db=db,
            metadata={"reason": "race_lost", "ip": client_ip},
        )
        raise RefreshInvalidError()

    # Re-read the user to get the freshest ``plan`` claim (V1 always "free";
    # V1.5 may have changed plan since the prior refresh).
    user = await iam_repo.get_user_by_id(db, existing_entry.user_id)
    if user is None:
        # Edge case: user deleted while their refresh cookie was still live.
        # Treat as refresh_invalid; the new allowlist entry we just wrote
        # has TTL — it will expire naturally.  We could DEL it, but the user
        # being gone means no attacker can use it without the cookie value
        # (which we are NOT returning).
        AUTH_TOKEN_REFRESH_FAILED.labels(reason="allowlist_miss").inc()
        await _write_audit_direct(
            user_id=None,
            event_type="auth.token.refresh_failed",
            db=db,
            metadata={"reason": "user_deleted", "ip": client_ip},
        )
        raise RefreshInvalidError()

    access_token = issue_access_token(user.id, user.plan)
    await _write_audit_direct(
        user_id=user.id,
        event_type="auth.token.refreshed",
        db=db,
        metadata={"ip": client_ip},
    )

    return RotateRefreshResult(
        access_token=access_token,
        new_refresh_token=new_refresh_token,
        access_expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
        refresh_expires_in=settings.REFRESH_TOKEN_TTL_SECONDS,
    )


async def revoke_refresh_token(
    refresh_token: str | None,
    valkey: Redis,
    db: AsyncSession | None = None,
) -> RevokeResult:
    """``POST /api/v1/auth/logout`` business path per §7.B.4.

    Always idempotent — returns ``RevokeResult(cookie_was_present, user_id)``.
    The router uses ``cookie_was_present`` to decide whether to emit the
    ``auth.logout`` audit row; this service writes the row directly so the
    ``user_id`` resolution happens BEFORE the Valkey DEL.

    The optional ``db`` parameter routes the audit write through the
    caller's session via SAVEPOINT.  When ``None`` (e.g. unit-test paths
    that don't need an audit row), the audit falls back to its own
    :data:`AsyncSessionLocal` — drop-on-failure still applies.
    """
    if not refresh_token:
        return RevokeResult(cookie_was_present=False, user_id=None)

    # Dual-pepper (R5): validate_refresh_allowlist returns the MATCHED key so
    # logout DELs the exact key that holds the session — including a vN-1 key
    # for a cookie issued under the PREVIOUS pepper during a grace window. A
    # current-pepper-only DEL would leave that vN-1 entry live until TTL.
    matched = await validate_refresh_allowlist(valkey, refresh_token)
    if matched is not None:
        key, raw = matched
    else:
        # Not present under either pepper — DEL the current-pepper key anyway
        # so logout stays idempotent (no-op if it was never there).
        key, raw = refresh_allowlist_key(refresh_token), None
    entry = _deserialize_allowlist_entry(raw)
    # DEL is idempotent — succeeds whether or not the key existed.
    await valkey.delete(key)

    if entry is not None:
        await _write_audit_direct(
            user_id=entry.user_id,
            event_type="auth.logout",
            db=db,
            metadata={"ip": entry.ip},
        )

    return RevokeResult(
        cookie_was_present=True,
        user_id=entry.user_id if entry is not None else None,
    )


async def get_profile(user_id: UUID, db: AsyncSession) -> UserProfile:
    """``GET /api/v1/auth/me`` business path per §7.B.5.

    Read-only.  Emits NO audit event per the documented absence (§7.B.5).
    Raises :class:`app.core.auth.UserNotFoundError` if the row is gone
    between JWT issuance and this read (very rare — account deletion).
    """
    user = await iam_repo.get_user_by_id(db, user_id)
    if user is None:
        # Forward to the §4.B canonical exception so the envelope shape is
        # consistent with what ``get_current_user`` would have raised had
        # the row been gone at JWT-decode time.
        from app.core.auth import UserNotFoundError

        raise UserNotFoundError()

    return UserProfile(
        user_id=user.id,
        phone=user.phone,
        plan=user.plan,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay Wave 3 — billing-status read + app-side trial (entitlement-shaped).
#
# Authored by the auth-builder (step 2a).  ``get_billing_status`` is the single
# DB-fresh read both ``/auth/me`` and ``GET /billing/subscription`` consume so
# the resolved entitlement is computed in ONE place (F7).  ``start_trial`` is
# the §3.7 app-side trial grant — NO Razorpay call, idempotent one-per-phone.
# ─────────────────────────────────────────────────────────────────────────────

_TRIAL_DAYS = 14
"""14-day Pro trial window per Pricing v2 §5 / Razorpay spec §3.7."""

#: ``users.plan`` → human label for the FE (Pricing v2 §5).
_PLAN_LABELS: dict[str, str] = {
    "free": "Free",
    "starter": "Starter",
    "pro": "Pro",
    "pro_annual": "Pro (Annual)",
    "business": "Business",
    "business_annual": "Business (Annual)",
    "ltd": "Lifetime",
}


async def get_billing_status(user_id: UUID, db: AsyncSession) -> BillingStatus:
    """DB-FRESH billing/entitlement read backing ``/auth/me`` + ``GET
    /billing/subscription`` (Razorpay Wave 3, F7).

    Reads ``users.plan`` + ``users.trial_ends_at`` + the user's latest
    ``subscriptions`` row, computes the resolved effective entitlement via
    :func:`app.core.plan_guard.resolve_entitlement`, and returns a
    :class:`BillingStatus`.  Read-only; emits no audit event.

    A trialist (``plan='free'`` + a live ``trial_ends_at``) returns
    ``plan='free'`` but ``entitlement='pro'`` — the F7 DB-fresh proof.
    """
    # Local import — keeps the plan_guard dependency off the module-load path
    # and mirrors the core/auth lazy-import pattern already used in get_profile.
    from app.core.plan_guard import resolve_entitlement

    user = await iam_repo.get_user_by_id(db, user_id)
    if user is None:
        from app.core.auth import UserNotFoundError

        raise UserNotFoundError()

    entitlement = await resolve_entitlement(user_id=user_id, db=db)

    # Latest subscription row (most-recent by created_at) for status surfacing.
    stmt = (
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = (await db.execute(stmt)).scalar_one_or_none()

    sub_status = sub.status if sub is not None else None
    current_period_end = sub.current_period_end if sub is not None else None
    cancel_scheduled = bool(sub is not None and sub.cancel_scheduled_at is not None)

    return BillingStatus(
        plan=user.plan,
        entitlement=entitlement,
        status=sub_status,
        current_period_end=current_period_end,
        cancel_scheduled=cancel_scheduled,
        tier_label=_PLAN_LABELS.get(user.plan, user.plan),
        trial_ends_at=user.trial_ends_at,
    )


async def start_trial(user_id: UUID, db: AsyncSession) -> StartTrialResult:
    """Grant the 14-day app-side Pro trial (Razorpay spec §3.7, Pricing v2 §5).

    App-side ONLY — NO Razorpay call, NO ``subscriptions``/``payments``/
    ``webhook_events`` row.  Sets ``users.trial_ends_at = now() + 14 days`` and
    writes a business ``audit_events`` row (``billing.trial.started``).

    Idempotent one-per-phone (Q3 ruling): rejects with
    :class:`TrialAlreadyUsedError` (409) if the user has ALREADY consumed a
    trial (``trial_ends_at`` already set — past OR future) OR already holds a
    non-free plan OR any subscription row (a trial would be redundant).  The
    one-per-PHONE bound is enforced transitively: the user_id IS the verified
    phone identity (a phone maps to exactly one users row via the OTP gate), so
    "one trial per user row" == "one trial per phone".

    Raises:
        TrialAlreadyUsedError: when a trial was already used / is redundant.
        UserNotFoundError: when the principal row is gone (very rare).
    """
    user = await iam_repo.get_user_by_id(db, user_id)
    if user is None:
        from app.core.auth import UserNotFoundError

        raise UserNotFoundError()

    # Idempotency / redundancy guard.
    if user.trial_ends_at is not None:
        logger.info("start_trial: rejected (trial already used) user=%s", user_id)
        raise TrialAlreadyUsedError()
    if user.plan != "free":
        logger.info(
            "start_trial: rejected (non-free plan=%s — trial redundant) user=%s",
            user.plan,
            user_id,
        )
        raise TrialAlreadyUsedError(
            detail="You already have a paid plan; no trial needed."
        )

    # Defensive: a free user with an existing sub row (created-but-unpaid) — a
    # trial would muddy the entitlement; reject as redundant.
    existing_sub = (
        await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.user_id == user_id
            )
        )
    ).scalar_one()
    if int(existing_sub or 0) > 0:
        logger.info(
            "start_trial: rejected (existing subscription row) user=%s", user_id
        )
        raise TrialAlreadyUsedError(
            detail="A subscription already exists on this account."
        )

    trial_ends_at = datetime.now(timezone.utc) + timedelta(days=_TRIAL_DAYS)
    user.trial_ends_at = trial_ends_at
    await db.flush()

    # Business audit row — SAVEPOINT path (drop-on-failure; never poisons the
    # trial grant).  user_id FK is visible (the user row pre-exists).
    await _write_audit_direct(
        user_id=user_id,
        event_type="billing.trial.started",
        db=db,
        metadata={"trial_days": _TRIAL_DAYS},
    )

    logger.info(
        "start_trial: granted 14-day Pro trial user=%s ends_at=%s",
        user_id,
        trial_ends_at.isoformat(),
    )
    return StartTrialResult(trial_ends_at=trial_ends_at, entitlement="pro")


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay Wave 3 — subscribe + cancel service helpers (routes-builder, step 2b).
#
# ``subscribe`` — initiates a Razorpay Subscription (recurring) or Order (LTD).
# ``cancel``    — schedules a cancel-at-cycle-end via the adapter.
#
# Both are route-shaped helpers: they call the Wave-2 adapter and write the
# appropriate ``subscriptions`` row.  The plan grant itself is webhook-driven
# (D-D, §3.4 handler) — these helpers do NOT touch ``users.plan``.
#
# Tier → RAZORPAY_PLAN_ID mapping (D-B from spec §2/§5):
# The adapter is plan-agnostic; the map lives here so PRICING_LOCKED v2 §5
# is the single source of truth and config carries only opaque Razorpay IDs.
# ─────────────────────────────────────────────────────────────────────────────

#: Tier → ``settings.RAZORPAY_PLAN_ID_*`` attribute name.
#: Resolved lazily at call time from ``settings`` so a restart picks up
#: new env vars without needing a code change.
_TIER_TO_PLAN_ID_ATTR: dict[str, str] = {
    "starter": "RAZORPAY_PLAN_ID_STARTER_MONTHLY",
    "pro": "RAZORPAY_PLAN_ID_PRO_MONTHLY",
    "pro_annual": "RAZORPAY_PLAN_ID_PRO_ANNUAL",
    "business": "RAZORPAY_PLAN_ID_BUSINESS_MONTHLY",
    "business_annual": "RAZORPAY_PLAN_ID_BUSINESS_ANNUAL",
}
#: Recurring tiers that use the Subscriptions API.
_RECURRING_TIERS = frozenset(_TIER_TO_PLAN_ID_ATTR)
#: Tiers where an active sub blocks a new subscribe (all non-ltd active-ish statuses).
_BLOCKING_SUB_STATUSES = frozenset({"created", "authenticated", "active", "past_due"})


def _get_plan_id_for_tier(tier: str) -> str:
    """Resolve the Razorpay plan_id for a recurring tier from ``settings``.

    Returns the configured plan_id string (may be empty in dev — an empty plan_id
    causes the Razorpay SDK to reject the call with a ``BadRequestError`` which
    surfaces as a clean 502 ``RazorpayAdapterError``; this is the intended behaviour
    for a feature-flagged route not yet wired to real Razorpay plans).
    """
    attr = _TIER_TO_PLAN_ID_ATTR[tier]
    return str(getattr(settings, attr, ""))


async def subscribe(
    user_id: UUID,
    tier: str,
    db: AsyncSession,
) -> SubscribeResult:
    """Initiate a Razorpay Subscription (recurring) or Order (LTD one-time purchase).

    Pipeline (§3.4):
    1. Guard: if the user already holds an active/authenticated/created/past_due
       subscription row → raise :class:`AlreadySubscribedError` (409).
    2. For LTD (``tier == 'ltd'``):
       a. Call ``adapter.create_order(amount=settings.RAZORPAY_LTD_PRICE_PAISE,
          receipt=..., notes={user_id, tier})``.
       b. Write a ``subscriptions`` row ``{tier:'ltd', status:'created',
          razorpay_order_id:..., current_period_end:NULL}``.
       c. Return :class:`SubscribeResult` with ``razorpay_order_id`` + ``amount_paise``.
    3. For recurring tiers:
       a. Resolve ``plan_id = _get_plan_id_for_tier(tier)`` (from settings).
       b. Call ``adapter.create_subscription(plan_id=..., notes={user_id, tier})``.
       c. Write a ``subscriptions`` row ``{tier, status:'created',
          razorpay_subscription_id:...}``.
       d. Return :class:`SubscribeResult` with ``razorpay_subscription_id`` + ``short_url``.

    The plan grant (``users.plan`` change) is NOT applied here — it happens on
    the ``subscription.activated`` / ``payment.captured`` webhook (D-D, Wave 2).

    Raises:
        AlreadySubscribedError: When the user already holds an active subscription.
        RazorpayAdapterError: When the Razorpay API call fails (502 to the FE).
    """
    # ── Step 1: guard ─────────────────────────────────────────────────────────
    existing_stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_(_BLOCKING_SUB_STATUSES),
        )
        .limit(1)
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        logger.info(
            "subscribe: rejected (existing sub status=%s) user=%s",
            existing.status,
            user_id,
        )
        raise AlreadySubscribedError()

    if tier == "ltd":
        # ── Step 2: LTD Orders path ───────────────────────────────────────────
        receipt = f"ltd-{user_id!s}"
        order = await razorpay_adapter.create_order(
            amount=settings.RAZORPAY_LTD_PRICE_PAISE,
            receipt=receipt,
            notes={"user_id": str(user_id), "tier": "ltd"},
        )
        sub = Subscription(
            user_id=user_id,
            tier="ltd",
            status="created",
            razorpay_order_id=order.id,
            current_period_end=None,  # perpetual sentinel
        )
        db.add(sub)
        await db.flush()
        logger.info(
            "subscribe: LTD order created user=%s order=%s sub=%s",
            user_id,
            order.id,
            sub.id,
        )
        return SubscribeResult(
            tier="ltd",
            razorpay_order_id=order.id,
            amount_paise=order.amount,
        )

    # ── Step 3: recurring Subscriptions path ──────────────────────────────────
    plan_id = _get_plan_id_for_tier(tier)
    rzp_sub = await razorpay_adapter.create_subscription(
        plan_id=plan_id,
        notes={"user_id": str(user_id), "tier": tier},
    )
    sub = Subscription(
        user_id=user_id,
        tier=tier,
        status="created",
        razorpay_subscription_id=rzp_sub.id,
    )
    db.add(sub)
    await db.flush()
    logger.info(
        "subscribe: recurring sub created user=%s rzp_sub=%s tier=%s sub=%s",
        user_id,
        rzp_sub.id,
        tier,
        sub.id,
    )
    return SubscribeResult(
        tier=tier,
        razorpay_subscription_id=rzp_sub.id,
        short_url=rzp_sub.short_url,
    )


async def cancel(user_id: UUID, db: AsyncSession) -> CancelSubscriptionResult:
    """Schedule a cancel-at-cycle-end for the user's active subscription (§3.3.3).

    Pipeline:
    1. Find the user's latest subscription row in a cancellable state
       (``active`` / ``authenticated`` / ``created`` / ``past_due``).
       If none → raise :class:`NoActiveSubscriptionError` (404).
    2. Call ``adapter.cancel_subscription(sub_id, cancel_at_cycle_end=True)``.
    3. Set ``subscriptions.cancel_scheduled_at = now()`` on the local row.
    4. Return :class:`CancelSubscriptionResult` with ``entitled_until =
       current_period_end``.

    The ``status → 'cancelled'`` transition on ``subscriptions`` + any plan
    downgrade are driven by the ``subscription.cancelled`` webhook (Wave 2).
    The plan remains active until ``current_period_end``.

    Raises:
        NoActiveSubscriptionError: When no cancellable subscription is found.
        RazorpayAdapterError: When the Razorpay cancel API call fails (502).
    """
    # ── Step 1: look up a cancellable sub ─────────────────────────────────────
    cancellable_stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_({"active", "authenticated", "created", "past_due"}),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = (await db.execute(cancellable_stmt)).scalar_one_or_none()
    if sub is None:
        logger.info("cancel: no cancellable sub user=%s", user_id)
        raise NoActiveSubscriptionError()

    # LTD subscriptions are perpetual — cancellation is not meaningful (no cycle
    # end to cancel at).  Block cleanly rather than forwarding to Razorpay (which
    # would reject it anyway since LTD is an Order, not a Subscription).
    if sub.tier == "ltd":
        logger.info("cancel: LTD is perpetual — cancellation rejected user=%s", user_id)
        raise NoActiveSubscriptionError(
            detail="Lifetime (LTD) purchases cannot be cancelled this way. "
            "Please contact support."
        )

    # ── Step 2: call the adapter ──────────────────────────────────────────────
    if sub.razorpay_subscription_id:
        await razorpay_adapter.cancel_subscription(
            sub.razorpay_subscription_id, cancel_at_cycle_end=True
        )

    # ── Step 3: record cancel_scheduled_at ───────────────────────────────────
    sub.cancel_scheduled_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        "cancel: scheduled cancel user=%s sub=%s entitled_until=%s",
        user_id,
        sub.id,
        sub.current_period_end,
    )
    return CancelSubscriptionResult(entitled_until=sub.current_period_end)


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay webhook event router (V1.5 — RAZORPAY_INTEGRATION_SPEC §4).
#
# Evolved from the V1 log-only capture into a signature-verified, idempotent,
# out-of-order-tolerant event router.  The dedupe INSERT and the state mutation
# commit in a SINGLE transaction (§4.2) — a handler raise rolls back BOTH so
# Razorpay's retry reprocesses cleanly.
# ─────────────────────────────────────────────────────────────────────────────

#: Razorpay subscription ``tier`` → ``users.plan`` mapping.  The tier comes from
#: the subscription row we created (``notes.tier`` echoed by Razorpay, or the
#: ``subscriptions.tier`` column).  Both vocabularies overlap exactly for the
#: paid tiers (Pricing v2), so this is an identity map — kept explicit so an
#: unknown tier resolves to ``None`` (no grant) rather than silently leaking.
_TIER_TO_PLAN: dict[str, str] = {
    "starter": "starter",
    "pro": "pro",
    "pro_annual": "pro_annual",
    "business": "business",
    "business_annual": "business_annual",
    "ltd": "ltd",
}


def _epoch_to_utc(value: object) -> datetime | None:
    """Convert a Razorpay epoch-seconds field to a UTC ``datetime`` (or None)."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _entity(payload: dict, key: str) -> dict:
    """Extract ``payload['payload'][key]['entity']`` defensively → dict."""
    try:
        node = payload["payload"][key]["entity"]
        return node if isinstance(node, dict) else {}
    except (KeyError, TypeError):
        return {}


async def _audit_business_effect(
    db: AsyncSession,
    *,
    user_id: UUID,
    event_type: str,
    metadata: dict | None = None,
) -> int | None:
    """Write a business ``audit_events`` row inside the webhook transaction.

    Uses the SAVEPOINT in-request path of :func:`_write_audit_direct` so an
    audit failure never poisons the webhook state mutation, while the row still
    commits atomically with it when both succeed.
    """
    return await _write_audit_direct(
        user_id=user_id,
        event_type=event_type,
        db=db,
        metadata=metadata,
    )


async def _get_subscription_by_rzp_id(
    db: AsyncSession, rzp_sub_id: str | None
) -> Subscription | None:
    if not rzp_sub_id:
        return None
    res = await db.execute(
        select(Subscription).where(
            Subscription.razorpay_subscription_id == rzp_sub_id
        )
    )
    return res.scalar_one_or_none()


async def _upsert_payment(
    db: AsyncSession,
    *,
    user_id: UUID,
    subscription_id: UUID | None,
    razorpay_payment_id: str | None,
    amount_paise: int,
    currency: str,
    status: str,
    event_type: str,
    occurred_at: datetime | None,
    raw: dict | None,
) -> None:
    """Insert a ``payments`` row, deduped on ``razorpay_payment_id`` (§4.2).

    A re-delivered ``subscription.charged`` cannot create a duplicate payment
    even if the event-id gate were bypassed — the UNIQUE ``razorpay_payment_id``
    ON CONFLICT DO NOTHING is the second line of defence.
    """
    values: dict = {
        "user_id": user_id,
        "subscription_id": subscription_id,
        "razorpay_payment_id": razorpay_payment_id,
        "amount_paise": amount_paise,
        "currency": currency or "INR",
        "status": status,
        "event_type": event_type[:40],
        "occurred_at": occurred_at,
        "raw_jsonb": raw,
    }
    stmt = pg_insert(Payment).values(**values)
    if razorpay_payment_id is not None:
        stmt = stmt.on_conflict_do_nothing(index_elements=["razorpay_payment_id"])
    await db.execute(stmt)


# ── Per-event handlers — each returns an audit_event_id (or None) ───────────
async def _handle_subscription_authenticated(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    entity = _entity(payload, "subscription")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        logger.info("iam.webhook.%s no_local_sub id=%s", event_type, entity.get("id"))
        return None
    # Guard: only from created/authenticated (§4.3 matrix).
    if sub.status in ("created", "authenticated"):
        sub.status = "authenticated"
    else:
        logger.info(
            "iam.webhook.%s illegal_transition from=%s (no-op)", event_type, sub.status
        )
    return None


async def _handle_subscription_activated(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    entity = _entity(payload, "subscription")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        logger.info("iam.webhook.%s no_local_sub id=%s", event_type, entity.get("id"))
        return None
    sub.status = "active"
    new_end = _epoch_to_utc(entity.get("current_end"))
    if new_end is not None:
        sub.current_period_end = new_end
    plan = _TIER_TO_PLAN.get(sub.tier)
    audit_id: int | None = None
    if plan is not None:
        user = await db.get(User, sub.user_id)
        if user is not None:
            user.plan = plan
            audit_id = await _audit_business_effect(
                db,
                user_id=user.id,
                event_type="billing.plan.granted",
                metadata={"tier": sub.tier, "event": event_type},
            )
    return audit_id


async def _handle_subscription_charged(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    entity = _entity(payload, "subscription")
    payment = _entity(payload, "payment")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        logger.info("iam.webhook.%s no_local_sub id=%s", event_type, entity.get("id"))
        return None

    # Monotonic period guard (§4.3): GREATEST(current_period_end, new_end).
    new_end = _epoch_to_utc(entity.get("current_end"))
    if new_end is not None:
        if sub.current_period_end is None or new_end > sub.current_period_end:
            sub.current_period_end = new_end

    # Renewal heartbeat: a late charge does NOT re-activate a cancelled sub.
    if sub.status in ("active", "past_due"):
        sub.status = "active"
    else:
        logger.info(
            "iam.webhook.%s status=%s not re-activated by charge", event_type, sub.status
        )

    await _upsert_payment(
        db,
        user_id=sub.user_id,
        subscription_id=sub.id,
        razorpay_payment_id=payment.get("id"),
        amount_paise=int(payment.get("amount") or entity.get("plan_amount") or 0),
        currency=str(payment.get("currency") or "INR"),
        status="captured",
        event_type=event_type,
        occurred_at=_epoch_to_utc(payment.get("created_at")),
        raw=payment or None,
    )
    return None


async def _handle_subscription_pending(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    entity = _entity(payload, "subscription")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        return None
    if sub.status == "active":
        sub.status = "past_due"  # grace = trust Razorpay retry window (F8)
        logger.info("iam.webhook.%s sub=%s → past_due (dunning trigger)", event_type, sub.id)
    else:
        logger.info("iam.webhook.%s illegal_transition from=%s (no-op)", event_type, sub.status)
    return None


async def _handle_subscription_halted(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    entity = _entity(payload, "subscription")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        return None
    if sub.status not in ("past_due", "active"):
        logger.info("iam.webhook.%s illegal_transition from=%s (no-op)", event_type, sub.status)
        return None
    sub.status = "halted"
    user = await db.get(User, sub.user_id)
    audit_id: int | None = None
    if user is not None:
        user.plan = "free"  # F8 — downgrade only on halted, no fixed grace timer
        audit_id = await _audit_business_effect(
            db,
            user_id=user.id,
            event_type="billing.plan.downgraded",
            metadata={"reason": "halted", "event": event_type},
        )
    return audit_id


async def _handle_subscription_cancelled(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    entity = _entity(payload, "subscription")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        return None
    # A cancelled sub STAYS cancelled even if a late charged arrives.
    sub.status = "cancelled"
    sub.cancel_scheduled_at = sub.cancel_scheduled_at or datetime.now(tz=timezone.utc)
    # users.plan stays at tier until current_period_end — the Wave-4
    # reconciliation sweep does the eventual downgrade.
    audit_id = await _audit_business_effect(
        db,
        user_id=sub.user_id,
        event_type="billing.subscription.cancelled",
        metadata={"tier": sub.tier, "event": event_type},
    )
    return audit_id


async def _handle_subscription_completed(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    entity = _entity(payload, "subscription")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        return None
    sub.status = "completed"  # terminal; not expected for open-ended plans
    user = await db.get(User, sub.user_id)
    audit_id: int | None = None
    if user is not None:
        user.plan = "free"
        audit_id = await _audit_business_effect(
            db,
            user_id=user.id,
            event_type="billing.plan.downgraded",
            metadata={"reason": "completed", "event": event_type},
        )
    return audit_id


async def _handle_subscription_updated(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    """Apply a landed plan change (upgrade-immediate; downgrade lands at next
    cycle ``charged`` per F4)."""
    entity = _entity(payload, "subscription")
    sub = await _get_subscription_by_rzp_id(db, entity.get("id"))
    if sub is None:
        return None
    # Razorpay echoes the new plan_id; the tier→plan resolution is Wave-3 config
    # (plan_id → tier).  Here we only react if the payload carries a notes.tier
    # the subscribe flow set — upgrade-immediate sets both sub.tier + users.plan.
    notes = entity.get("notes") or {}
    new_tier = notes.get("tier") if isinstance(notes, dict) else None
    if not new_tier or new_tier not in _TIER_TO_PLAN:
        logger.info("iam.webhook.%s no resolvable tier in notes (no-op)", event_type)
        return None
    sub.tier = new_tier
    user = await db.get(User, sub.user_id)
    audit_id: int | None = None
    if user is not None and sub.status == "active":
        user.plan = _TIER_TO_PLAN[new_tier]
        audit_id = await _audit_business_effect(
            db,
            user_id=user.id,
            event_type="billing.plan.updated",
            metadata={"tier": new_tier, "event": event_type},
        )
    return audit_id


async def _handle_payment_captured(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    """LTD path: a captured Order → permanent ``users.plan='ltd'``.

    Matches the LTD ``subscriptions`` row by ``razorpay_order_id`` (or the
    order ``notes.tier == 'ltd'``).  Non-LTD ``payment.captured`` (the payment
    leg of a subscription charge) is handled via ``subscription.charged`` — here
    we only act when we can resolve an LTD order, else record + no-op.
    """
    payment = _entity(payload, "payment")
    order = _entity(payload, "order")
    order_id = payment.get("order_id") or order.get("id")
    notes = (order.get("notes") or payment.get("notes") or {})
    is_ltd_note = isinstance(notes, dict) and notes.get("tier") == "ltd"

    sub: Subscription | None = None
    if order_id:
        res = await db.execute(
            select(Subscription).where(Subscription.razorpay_order_id == order_id)
        )
        sub = res.scalar_one_or_none()
    if sub is None and not is_ltd_note:
        logger.info("iam.webhook.%s not an LTD order (no-op) order=%s", event_type, order_id)
        return None
    if sub is None:
        logger.info("iam.webhook.%s LTD note but no local sub order=%s", event_type, order_id)
        return None

    sub.status = "active"
    sub.current_period_end = None  # perpetual sentinel (LTD)
    await _upsert_payment(
        db,
        user_id=sub.user_id,
        subscription_id=sub.id,
        razorpay_payment_id=payment.get("id"),
        amount_paise=int(payment.get("amount") or 0),
        currency=str(payment.get("currency") or "INR"),
        status="captured",
        event_type=event_type,
        occurred_at=_epoch_to_utc(payment.get("created_at")),
        raw=payment or None,
    )
    user = await db.get(User, sub.user_id)
    audit_id: int | None = None
    if user is not None:
        user.plan = "ltd"
        audit_id = await _audit_business_effect(
            db,
            user_id=user.id,
            event_type="billing.plan.granted",
            metadata={"tier": "ltd", "event": event_type},
        )
    return audit_id


async def _handle_payment_failed(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    """Record a failed payment (informs dunning).  NO state downgrade here —
    downgrade is halted-driven (F8)."""
    payment = _entity(payload, "payment")
    # Best-effort tenant resolution: link via the order's subscription if present.
    order_id = payment.get("order_id")
    sub: Subscription | None = None
    if order_id:
        res = await db.execute(
            select(Subscription).where(Subscription.razorpay_order_id == order_id)
        )
        sub = res.scalar_one_or_none()
    if sub is None:
        logger.info("iam.webhook.%s unlinked failed payment (logged, no row)", event_type)
        return None
    await _upsert_payment(
        db,
        user_id=sub.user_id,
        subscription_id=sub.id,
        razorpay_payment_id=payment.get("id"),
        amount_paise=int(payment.get("amount") or 0),
        currency=str(payment.get("currency") or "INR"),
        status="failed",
        event_type=event_type,
        occurred_at=_epoch_to_utc(payment.get("created_at")),
        raw=payment or None,
    )
    return None


async def _handle_refund_processed(
    db: AsyncSession, event_type: str, payload: dict
) -> int | None:
    """Record a refund row.  Issuing refunds is out of scope (Razorpay
    dashboard); we react only.  Full-refund downgrade policy (F3) is applied
    by the Wave-4 reconciliation sweep — here we record the refund."""
    refund = _entity(payload, "refund")
    payment = _entity(payload, "payment")
    payment_id = refund.get("payment_id") or payment.get("id")
    if payment_id:
        res = await db.execute(
            select(Payment).where(Payment.razorpay_payment_id == payment_id)
        )
        orig = res.scalar_one_or_none()
        if orig is not None:
            sub_id = orig.subscription_id
            await _upsert_payment(
                db,
                user_id=orig.user_id,
                subscription_id=sub_id,
                razorpay_payment_id=refund.get("id"),
                amount_paise=int(refund.get("amount") or 0),
                currency=str(refund.get("currency") or "INR"),
                status="refunded",
                event_type=event_type,
                occurred_at=_epoch_to_utc(refund.get("created_at")),
                raw=refund or None,
            )
            return None
    logger.info("iam.webhook.%s unlinked refund (logged, no row)", event_type)
    return None


#: Event-type → handler dispatch table (§4.3).  Unknown types are NOT in this
#: map → recorded + 200 + no dispatch (§4.1 step 5).
_EVENT_HANDLERS = {
    "subscription.authenticated": _handle_subscription_authenticated,
    "subscription.activated": _handle_subscription_activated,
    "subscription.charged": _handle_subscription_charged,
    "subscription.pending": _handle_subscription_pending,
    "subscription.halted": _handle_subscription_halted,
    "subscription.cancelled": _handle_subscription_cancelled,
    "subscription.completed": _handle_subscription_completed,
    "subscription.updated": _handle_subscription_updated,
    "payment.captured": _handle_payment_captured,
    "payment.failed": _handle_payment_failed,
    "refund.processed": _handle_refund_processed,
}


async def capture_razorpay_webhook(
    raw_payload: bytes,
    signature: str,
    *,
    event_id: str | None = None,
    db: AsyncSession | None = None,
) -> WebhookCaptureResult:
    """``POST /api/v1/webhooks/razorpay`` — idempotent event router (§4).

    Pipeline (the exact order — §4.1, correctness-critical):

    1. Verify HMAC signature on RAW bytes (:func:`verify_webhook_signature`,
       sync per §6.E).  ``False`` → :class:`WebhookSignatureInvalidError` (401).
    2. JSON-parse.  Non-dict / decode error → :class:`MalformedWebhookPayloadError`
       (400).
    3. Resolve ``event_id`` (from the ``x-razorpay-event-id`` header passed by
       the route as ``event_id=...``; fallback to the body ``id``) and
       ``event_type`` (``payload['event']``).  Absent ``event_id`` → malformed
       (the dedupe key is mandatory).
    4. ONE transaction: ``INSERT ... ON CONFLICT (event_id) DO NOTHING`` into
       ``webhook_events``; if 0 rows (conflict) → already processed → commit
       no-op + return.  Else dispatch to the per-event handler in the SAME
       transaction, set ``processed_at = NOW()``, commit.  A handler raise rolls
       back BOTH the dedupe row and the mutation → Razorpay retries → clean
       reprocess.
    5. Unknown / unmodelled event type → record the ``webhook_events`` row, do
       NOT dispatch, return 200 (so Razorpay does not retry).

    Args:
        raw_payload: RAW request bytes (NOT json-parsed) — required for HMAC.
        signature: ``X-Razorpay-Signature`` header value.
        event_id: ``x-razorpay-event-id`` header value (route-supplied).  When
            ``None`` the body ``id`` is used as the dedupe key.
        db: Optional request-scoped session.  When ``None`` (the current route
            still calls with 2 positional args), a session is acquired from
            :data:`AsyncSessionLocal` so the route stays untouched this wave
            (Wave 3 wires ``db=Depends(get_db)`` + the header).

    No secrets / PII are logged — only ``event_type`` + ``event_id`` + payload
    key names (§9).
    """
    if not razorpay_adapter.verify_webhook_signature(raw_payload, signature):
        raise WebhookSignatureInvalidError()

    try:
        payload = json.loads(raw_payload.decode("utf-8"))
        if not isinstance(payload, dict):
            raise MalformedWebhookPayloadError()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.info("iam.webhook.malformed_json: %r", exc)
        raise MalformedWebhookPayloadError() from exc

    event_type = str(payload.get("event") or "unknown")
    resolved_event_id = event_id or payload.get("id")
    if not resolved_event_id:
        # The dedupe key is mandatory — without it we cannot guarantee
        # idempotency, so treat as malformed (400) rather than risk a double
        # grant on a Razorpay retry.
        logger.info("iam.webhook.missing_event_id event_type=%s", event_type)
        raise MalformedWebhookPayloadError(
            detail="Webhook payload is missing the event id (dedupe key)"
        )
    resolved_event_id = str(resolved_event_id)

    if db is not None:
        return await _route_webhook_in_session(
            db, resolved_event_id, event_type, payload, owns_transaction=False
        )
    async with AsyncSessionLocal() as session:
        return await _route_webhook_in_session(
            session, resolved_event_id, event_type, payload, owns_transaction=True
        )


async def _route_webhook_in_session(
    db: AsyncSession,
    event_id: str,
    event_type: str,
    payload: dict,
    *,
    owns_transaction: bool,
) -> WebhookCaptureResult:
    """The single-transaction dedupe-INSERT + dispatch core (§4.1 step 4-6).

    ``owns_transaction`` is True when this function acquired its own session
    (route-compat path) and is responsible for the COMMIT; False when a
    request-scoped session was passed (Wave 3 / tests) and the caller's
    transaction boundary owns the commit.
    """
    is_known = event_type in _EVENT_HANDLERS

    # ── Dedupe gate: INSERT ... ON CONFLICT (event_id) DO NOTHING ────────────
    insert_stmt = (
        pg_insert(WebhookEvent)
        .values(
            event_id=event_id,
            event_type=event_type[:60],
            payload_jsonb=payload,
            signature_valid=True,
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(WebhookEvent.event_id)
    )
    result = await db.execute(insert_stmt)
    inserted = result.scalar_one_or_none()

    if inserted is None:
        # Conflict → this event was already processed → no-op, return 200.
        if owns_transaction:
            await db.commit()
        logger.info(
            "iam.webhook.duplicate event_type=%s event_id=%s (no-op)",
            event_type,
            event_id,
        )
        return WebhookCaptureResult(
            event_type=event_type,
            event_subtype=event_type,
            audit_event_id=None,
        )

    audit_event_id: int | None = None
    if is_known:
        handler = _EVENT_HANDLERS[event_type]
        # Dispatch in the SAME transaction as the dedupe insert.  Any raise
        # propagates → the outer transaction rolls back BOTH → Razorpay retries.
        audit_event_id = await handler(db, event_type, payload)
        await db.execute(
            WebhookEvent.__table__.update()
            .where(WebhookEvent.event_id == event_id)
            .values(processed_at=func.now())
        )
        logger.info(
            "iam.webhook.processed event_type=%s event_id=%s audit=%s",
            event_type,
            event_id,
            audit_event_id,
        )
    else:
        # Unknown/unmodelled — recorded (above) but NOT dispatched.  Mark
        # processed so the unprocessed-sweep index does not flag it forever.
        await db.execute(
            WebhookEvent.__table__.update()
            .where(WebhookEvent.event_id == event_id)
            .values(processed_at=func.now())
        )
        logger.info(
            "iam.webhook.unknown_event event_type=%s event_id=%s payload_keys=%s",
            event_type,
            event_id,
            sorted(payload.keys()),
        )

    if owns_transaction:
        await db.commit()

    return WebhookCaptureResult(
        event_type=event_type,
        event_subtype=event_type,
        audit_event_id=audit_event_id,
    )


__all__ = [
    "send_otp_for_login",
    "verify_otp_and_issue_tokens",
    "verify_google_and_issue_tokens",
    "rotate_refresh_token",
    "revoke_refresh_token",
    "get_profile",
    "capture_razorpay_webhook",
    # Wave 3 billing (auth-builder step 2a):
    "get_billing_status",
    "start_trial",
    # Wave 3 billing (api-routes-builder step 2b):
    "subscribe",
    "cancel",
]
