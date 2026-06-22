"""qa-auth-contract backend lane — BE-AUTH-03: /auth/me entitlement + trial_ends_at.

Covers:
- BE-AUTH-03: GET /auth/me returns DB-fresh ``entitlement`` and ``trial_ends_at``
              keys (not present in develop's OB-BE-16 assertion set).

Develop's gap:
  * ``test_iam_onboarding_coverage.py::test_me_authed_200_shape`` (OB-BE-16) asserts
    user_id, phone, plan, and onboarding_complete — but does NOT assert
    ``entitlement`` or ``trial_ends_at`` which were added by the Razorpay Wave 3
    ``MeResponse`` widening.
  * This test pins those two keys so a future regression (missing field or type
    mismatch) fails the merge gate.

NOT duplicating (already covered by OB-BE-16):
  * 200 status, non-empty phone, non-empty plan, onboarding_complete presence.

Design:
  * Seed user via OTP verify (Valkey seed + route call); extract access_token.
  * GET /auth/me with the token.
  * Assert ``entitlement`` key is present and a non-empty string.
  * Assert ``trial_ends_at`` key is present (value may be null for a fresh user).
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _otp_payload(otp: str) -> str:
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )


async def test_me_returns_entitlement_and_trial_ends_at(iam_client, use_live_valkey):
    """BE-AUTH-03: GET /auth/me carries ``entitlement`` + ``trial_ends_at`` keys.

    These fields were added by the Razorpay Wave 3 MeResponse widening and are
    absent from develop's OB-BE-16 assertion set.

    Arrange: seed OTP; POST /otp/verify → access_token.
    Act: GET /api/v1/auth/me with the access_token.
    Assert:
      1. 200 status.
      2. ``entitlement`` key is present and a non-empty string
         (free for a fresh user; type-checked not value-checked).
      3. ``trial_ends_at`` key is present in the body
         (null for a fresh user without an active trial).
    """
    phone = "+9155500030"
    otp = "030030"

    # Arrange: seed OTP record and obtain an access token via /otp/verify.
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(otp), ex=300)

    verify_resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    assert verify_resp.status_code == 200, (
        f"verify must succeed; got {verify_resp.status_code}: {verify_resp.text}"
    )
    access_token = verify_resp.json()["access_token"]

    # Act
    resp = await iam_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # Assert 1 — 200 status
    assert resp.status_code == 200, (
        f"GET /auth/me must be 200; got {resp.status_code}: {resp.text}"
    )
    body = resp.json()

    # Assert 2 — ``entitlement`` key present + non-empty string
    assert "entitlement" in body, (
        f"``entitlement`` key must be in /auth/me response; got keys: {list(body.keys())}"
    )
    entitlement = body["entitlement"]
    assert isinstance(entitlement, str) and entitlement, (
        f"``entitlement`` must be a non-empty string; got {entitlement!r}"
    )

    # Assert 3 — ``trial_ends_at`` key present (value may be null)
    assert "trial_ends_at" in body, (
        f"``trial_ends_at`` key must be in /auth/me response; got keys: {list(body.keys())}"
    )
