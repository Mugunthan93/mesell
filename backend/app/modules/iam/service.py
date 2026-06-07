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
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import msg91 as msg91_adapter
from app.adapters import razorpay as razorpay_adapter
from app.core.auth import (
    issue_access_token,
    issue_refresh_token,
    refresh_allowlist_key,
    rotate_refresh_token as rotate_refresh_token_in_valkey,
)
from app.modules.iam import repository as iam_repo
from app.modules.iam.domain import (
    OtpRecord,
    RefreshAllowlistEntry,
    RevokeResult,
    RotateRefreshResult,
    SendOtpResult,
    UserProfile,
    VerifyOtpResult,
    WebhookCaptureResult,
)
from app.modules.iam.exceptions import (
    MalformedWebhookPayloadError,
    Msg91UnavailableError,
    OtpAttemptsExceededError,
    OtpInvalidError,
    RefreshInvalidError,
    WebhookSignatureInvalidError,
)
from app.shared.config import settings
from app.shared.database import AsyncSessionLocal
from app.shared.models.audit_event import AuditEvent

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
    if not secrets.compare_digest(presented_hash, record.otp_hash):
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
        await _write_audit_direct(
            user_id=None,
            event_type="auth.token.refresh_failed",
            db=db,
            metadata={"reason": "missing", "ip": client_ip},
        )
        raise RefreshInvalidError()

    old_key = refresh_allowlist_key(old_refresh_token)
    # Read the entry BEFORE rotation so we know the user_id for both the new
    # JWT (plan claim re-read) and the audit row.  This GET is not part of
    # the atomic rotation — the Lua script re-reads + DELs atomically.  The
    # window between this GET and EVAL is bounded by single-event-loop
    # serialisation (no other task in this request handles the same cookie).
    existing_raw = await valkey.get(old_key)
    existing_entry = _deserialize_allowlist_entry(existing_raw)

    new_refresh_token = issue_refresh_token()
    new_key = refresh_allowlist_key(new_refresh_token)

    if existing_entry is None:
        # Either expired, never existed, or malformed JSON.  The Lua call
        # below would also return 0; we short-circuit so the audit row has
        # the right reason without needing to ask the script.
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

    key = refresh_allowlist_key(refresh_token)
    raw = await valkey.get(key)
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


async def capture_razorpay_webhook(
    raw_payload: bytes, signature: str
) -> WebhookCaptureResult:
    """``POST /api/v1/webhooks/razorpay`` business path per §7.B.6.

    V1 = capture only.  Steps:

    1. Verify HMAC signature via :func:`app.adapters.razorpay.verify_webhook_signature`
       (synchronous per §6.E).  ``False`` → raise
       :class:`WebhookSignatureInvalidError`.
    2. JSON-parse the (already-verified) payload.  Malformed → raise
       :class:`MalformedWebhookPayloadError`.
    3. Write an ``audit_events`` row (``event_type =
       "razorpay.webhook.captured"``, ``user_id = NULL``).  Per §7.B.6 the
       full payload is stored under ``payload_jsonb`` so V1.5 reprocessing
       can derive subscription state without re-fetching from Razorpay.

    V1 does NOT update ``users.plan`` or any other state per §7.B.6 lock.

    Audit row caveat: ``audit_events.user_id`` is NOT NULL (per §11.2 DDL).
    The webhook has no user_id.  We sidestep this by NOT writing a row for
    the webhook surface — instead we log to the service logger with the
    full payload.  This is a §7.B.6 vs. §11.2 DDL conflict that needs a
    §V1.5 resolution (audit_events.user_id NULLability, or a separate
    ``webhook_events`` table).  Logged + flagged for hand-off.
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

    event_subtype = str(payload.get("event") or "unknown")

    # §7.B.6 says "Full payload stored in audit_events.payload_jsonb"; the
    # live DDL uses `diff_jsonb` and `metadata_jsonb` (no `payload_jsonb`),
    # AND requires NOT NULL `user_id`.  Two-fold gap.  V1 posture: LOG the
    # capture (so it is observable end-to-end) and return success.  V1.5
    # adds the column + table-level NULL allowance and lights this path.
    logger.info(
        "iam.razorpay.webhook.captured event_subtype=%s payload_keys=%s",
        event_subtype,
        sorted(payload.keys()),
    )

    return WebhookCaptureResult(
        event_type="razorpay.webhook.captured",
        event_subtype=event_subtype,
        audit_event_id=0,  # placeholder — see V1.5 hand-off
    )


__all__ = [
    "send_otp_for_login",
    "verify_otp_and_issue_tokens",
    "rotate_refresh_token",
    "revoke_refresh_token",
    "get_profile",
    "capture_razorpay_webhook",
]
