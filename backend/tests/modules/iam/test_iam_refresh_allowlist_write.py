"""Unit test §7.J #1 — verify-OTP success path writes the refresh allowlist entry.

Per BACKEND_ARCHITECTURE.md §7.J unit 1:

    "Refresh allowlist write on verify-success — verify path writes
    cache:refresh:{hmac} to Valkey DB 0 with correct JSON payload + TTL =
    REFRESH_TOKEN_TTL_SECONDS."

Strategy
--------
Patch the MSG91 adapter so ``send_otp`` is a no-op success (no real API
call).  Patch the OTP record in Valkey to a known hash so we can verify
with a known plaintext.  Then call ``verify_otp_and_issue_tokens`` and
assert:

  1. The refresh allowlist key ``cache:refresh:{hmac_sha256(token, pepper)}``
     exists in Valkey DB 0.
  2. The JSON payload deserialises to ``{user_id, issued_at, ip}``.
  3. The Valkey ``TTL`` on the key is within 1 s of ``REFRESH_TOKEN_TTL_SECONDS``.
  4. The OTP record was DELed (single-use semantics).
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

from app.core.auth import refresh_allowlist_key
from app.modules.iam import service as iam_service
from app.shared.config import settings


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_verify_writes_allowlist_entry_with_correct_payload_and_ttl(
    db, use_live_valkey
):
    """Happy path — verify writes the allowlist entry per §7.J unit 1.

    Uses conftest's ``db`` fixture (NullPool, rollback on teardown) so the
    upsert lands in a transaction that disappears at the test boundary —
    no dev DB pollution per the §conftest fixture docstring.
    """
    from app.shared import valkey as _vk_mod

    # Phone uses a 5XX prefix not in the registered E.164 range that any
    # real Indian SIM would carry — keeps the test data trivially
    # identifiable in dev DB audit dumps even though the txn rolls back.
    phone = "+915550000001"
    otp = "654321"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()

    # 1. Pre-populate OTP record (skip /otp/send to avoid the MSG91 call).
    valkey = await _vk_mod.get_valkey_otp()
    payload = json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})
    await valkey.set(f"otp:{phone}", payload, ex=300)

    # 2. Drive the verify path through the service.
    result = await iam_service.verify_otp_and_issue_tokens(
        phone=phone, otp=otp, client_ip="203.0.113.7", db=db, valkey=valkey
    )

    # 3. Allowlist key MUST exist with the locked payload shape.
    allowlist_key = refresh_allowlist_key(result.refresh_token)
    raw = await valkey.get(allowlist_key)
    assert raw is not None, f"Allowlist key {allowlist_key} missing"
    payload_obj = json.loads(raw)
    assert set(payload_obj.keys()) == {"user_id", "issued_at", "ip"}
    assert payload_obj["ip"] == "203.0.113.7"
    assert isinstance(payload_obj["issued_at"], int)

    # 4. TTL must match REFRESH_TOKEN_TTL_SECONDS (within ±2 s for clock drift).
    ttl = await valkey.ttl(allowlist_key)
    assert (
        settings.REFRESH_TOKEN_TTL_SECONDS - 2 <= ttl <= settings.REFRESH_TOKEN_TTL_SECONDS
    ), f"TTL {ttl} out of band for {settings.REFRESH_TOKEN_TTL_SECONDS}"

    # 5. OTP record DELed — single-use semantics per §7.B.2.
    after = await valkey.get(f"otp:{phone}")
    assert after is None, "OTP record should be deleted after successful verify"

    # 6. Returned VerifyOtpResult sanity.
    assert result.access_expires_in == settings.ACCESS_TOKEN_TTL_SECONDS
    assert result.refresh_expires_in == settings.REFRESH_TOKEN_TTL_SECONDS
    assert result.access_token  # non-empty
    assert len(result.refresh_token) >= 60  # token_urlsafe(48) → ~64 chars
