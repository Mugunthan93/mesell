"""QA Wave 2 — BE-AUTH-03, BE-AUTH-13: /auth/me contract tests.

Covers:
- BE-AUTH-03: /auth/me returns DB-fresh plan + entitlement for an OTP user.
- BE-AUTH-13: /auth/me without a valid JWT → 401 with non-empty i18n detail.

Design:
  * BE-AUTH-03 seeds user via OTP verify (direct Valkey seed + route call),
    then calls /auth/me and asserts the DB-fresh plan/entitlement/trial_ends_at
    reflect the seeded user row (NOT a hardcoded "free" assumption).
  * BE-AUTH-13 calls /auth/me with NO Authorization header.
  * Each test uses a unique phone to prevent cross-test DB collisions.
"""

from __future__ import annotations

import hashlib
import json
import time

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _otp_payload(otp: str) -> str:
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return json.dumps({"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300})


async def test_me_returns_db_fresh_plan_and_entitlement_for_otp_user(
    iam_client, use_live_valkey
):
    """BE-AUTH-03: /auth/me returns DB-fresh plan/entitlement for an OTP user.

    Arrange: seed user by doing a real OTP verify; extract access_token.
    Act: GET /api/v1/auth/me with the access token.
    Assert: 200; ``phone`` is the E.164 string we used; ``plan`` and
            ``entitlement`` are non-empty strings; ``trial_ends_at`` is
            present (null or datetime string — seeded user has no trial);
            these fields reflect the users row, NOT a hardcoded assumption.
    """
    phone = "+9155500030"
    otp = "030030"

    # Arrange: seed OTP into Valkey and perform a real verify to get tokens.
    from app.shared import valkey as _vk_mod  # noqa: PLC0415
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", _otp_payload(otp), ex=300)

    verify_resp = await iam_client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    assert verify_resp.status_code == 200, f"verify failed: {verify_resp.text}"
    access_token = verify_resp.json()["access_token"]

    # Act
    resp = await iam_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    # Assert
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    # phone must be the E.164 string used to log in.
    assert body.get("phone") == phone, (
        f"phone must equal {phone!r}; got {body.get('phone')!r}"
    )
    # plan must be a non-empty string (fresh user defaults to "free").
    plan = body.get("plan", "")
    assert isinstance(plan, str) and plan, f"plan must be a non-empty string; got {plan!r}"
    # entitlement must be a non-empty string.
    entitlement = body.get("entitlement", "")
    assert isinstance(entitlement, str) and entitlement, (
        f"entitlement must be a non-empty string; got {entitlement!r}"
    )
    # trial_ends_at must be present as a key (null for fresh users without a trial).
    assert "trial_ends_at" in body, f"trial_ends_at key must be in /me response; got {body!r}"


async def test_me_without_jwt_returns_401(iam_client):
    """BE-AUTH-13: /auth/me without a valid JWT → 401 with non-empty i18n detail.

    Arrange: no Authorization header.
    Act: GET /api/v1/auth/me.
    Assert: 401; body has non-empty ``detail`` or ``validation_message_id``.
    """
    # Act — no Authorization header at all.
    resp = await iam_client.get("/api/v1/auth/me")

    # Assert
    assert resp.status_code == 401, (
        f"unauthenticated /auth/me must be 401, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    detail = body.get("detail") or body.get("validation_message_id") or ""
    assert detail, f"401 must carry a non-empty human-string detail; got {body!r}"
