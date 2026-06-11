"""Integration test §8.J integration 1 — full onboarding flow.

Per BACKEND_ARCHITECTURE.md §8.J integration 1:

    "Full onboarding flow — sign up via §7 OTP-verify → first PATCH base
    profile → first PATCH active-categories ['26'] (Grocery) → first
    PATCH compliance/26 → ``/required-fields`` shows
    ``onboarding_complete=true``."

This test drives the customer service directly (the router has not yet
been mounted by the api-routes-builder dispatch).  When the router lands
in step 2 of 2 the test will be amended to drive the HTTP surface
directly.  This step-1 variant asserts the SERVICE contract end-to-end
so the api-routes-builder dispatch has a known-good baseline.

Phone-prefix convention: every test uses ``+9155500XXXXX`` per the
integration conftest cleanup rule.

Loop pinning
------------
The customer service is called against a **fresh NullPool engine** built
inside the test's function-scoped loop, NOT the module-level
``app.shared.database.engine`` whose pool was first bound to the loop
that ran the iam_client lifespan.  This avoids the
``Task ... got Future ... attached to a different loop`` runtime error
that bites integration tests sharing an asyncpg pool across pytest-asyncio
loops.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.modules.customer import service as customer_service
from app.modules.customer.schemas import (
    PatchActiveCategoriesRequest,
    PatchProfileRequest,
)

pytestmark = pytest.mark.integration


async def _make_session_factory():
    """Per-test NullPool engine in the current event loop."""
    engine = create_async_engine(
        os.environ["DATABASE_URL"], poolclass=NullPool, echo=False
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _create_user_via_otp_verify(iam_client) -> tuple[str, str]:
    """Drive a real OTP verify so the user_id is created via §7 iam.

    Bypasses MSG91 by pre-seeding the OTP record into Valkey directly.
    Returns ``(access_token, phone)``.
    """
    from app.shared import valkey as _vk_mod

    phone = "+915550000840"
    otp = "555444"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", payload, ex=300)

    resp = await iam_client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return body["access_token"], phone


async def test_full_onboarding_flow_drives_flag_true(iam_client, use_live_valkey):
    """Sign up → PATCH base → PATCH active → PATCH compliance → flag is True."""
    access_token, _phone = await _create_user_via_otp_verify(iam_client)

    # Resolve user_id via /me so we can drive the service layer directly.
    me_resp = await iam_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_resp.status_code == 200
    user_id = UUID(me_resp.json()["user_id"])

    engine, Session = await _make_session_factory()
    try:
        # ── Seed-check: the Grocery super_id must be in the categories table.
        async with Session() as session:
            from sqlalchemy import select
            from app.shared.models.category import Category as CategoryORM

            existing = (
                await session.execute(
                    select(CategoryORM).where(CategoryORM.super_id == "26").limit(1)
                )
            ).scalar_one_or_none()
            if existing is None:
                pytest.skip("categories.super_id='26' not seeded — skipping flow")

        # ── Step 1: PATCH base profile via the service ───────────────────────
        async with Session() as session:
            patch_base = PatchProfileRequest(
                manufacturer_name="Full Onboard Pvt",
                manufacturer_address="1 Onboard Rd",
                manufacturer_pincode="560001",
                packer_name="Full Onboard Pvt",
                packer_address="1 Onboard Rd",
                packer_pincode="560001",
                country_of_origin="India",
            )
            profile_after_base = await customer_service.upsert_profile(
                user_id, patch_base, session
            )
            await session.commit()
        # Grocery not yet declared — flag is True because base is complete and
        # no compulsory super has been declared.
        assert profile_after_base.onboarding_complete is True

        # ── Step 2: PATCH active-categories ['26'] (Grocery) ────────────────
        async with Session() as session:
            req = PatchActiveCategoriesRequest(active_super_categories=["26"])
            profile_after_categories = await customer_service.set_active_categories(
                user_id, list(req.active_super_categories), session
            )
            await session.commit()
        assert profile_after_categories.onboarding_complete is False
        assert profile_after_categories.active_super_categories == ["26"]

        # ── Step 3: PATCH compliance/26 ─────────────────────────────────────
        async with Session() as session:
            profile_after_compliance = await customer_service.set_compliance_extension(
                user_id,
                "26",
                {"fssai_license_number": "10012345678901"},
                session,
            )
            await session.commit()
        assert profile_after_compliance.onboarding_complete is True

        # ── Step 4: /required-fields shows completed map fully True ─────────
        async with Session() as session:
            rf = await customer_service.get_required_fields(user_id, session)
        assert rf.completed["manufacturer_name"] is True
        assert rf.completed["country_of_origin"] is True
        assert rf.completed["ext.26.fssai_license_number"] is True

    finally:
        await engine.dispose()
