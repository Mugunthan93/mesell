"""Integration test §8.J integration 2 — cross-module eligibility gate.

Per BACKEND_ARCHITECTURE.md §8.J integration 2:

    "Cross-module call — ``catalog.service.create_product`` calls
    ``customer.service.assert_eligible_for_super_id(user_id, super_id)``;
    on a profile lacking the required extension → 422
    ``customer.profile.incomplete_for_category`` (the §10
    PROFILE_INCOMPLETE_FOR_CATEGORY gate per ``MVP_ARCH §3.3``)."

Since the ``catalog`` module does not exist yet (it lands in a future
dispatch), we MOCK the catalog-side caller — the test directly asserts
that the customer SURFACE raises the right exception for the right
combination of profile state + super_id.  When ``catalog`` lands, an
integration test in ``tests/integration/test_catalog_*.py`` will exercise
the same surface through the real ``catalog.service.create_product``
path.

Loop pinning per :mod:`tests.integration.test_customer_full_onboarding_flow`.
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

from app.modules.customer import repository as customer_repo
from app.modules.customer import service as customer_service
from app.modules.customer.exceptions import ProfileIncompleteForCategoryError
from app.modules.customer.schemas import PatchProfileRequest


async def _make_session_factory():
    """Per-test NullPool engine in the current event loop."""
    engine = create_async_engine(
        os.environ["DATABASE_URL"], poolclass=NullPool, echo=False
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _create_user_via_otp_verify(iam_client, phone: str, otp: str) -> str:
    """Drive a real OTP verify so the user_id is created via §7 iam."""
    from app.shared import valkey as _vk_mod

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
    return resp.json()["access_token"]


async def _resolve_user_id(iam_client, access_token: str):
    resp = await iam_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200
    return UUID(resp.json()["user_id"])


async def test_assert_eligibility_raises_when_profile_does_not_exist(
    iam_client, use_live_valkey
):
    """No profile row → ProfileIncompleteForCategoryError (422)."""
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000850", "454545"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        async with Session() as session:
            with pytest.raises(ProfileIncompleteForCategoryError) as excinfo:
                await customer_service.assert_eligible_for_super_id(
                    user_id, "26", session
                )
        assert excinfo.value.status_code == 422
        assert (
            excinfo.value.validation_message_id
            == "customer.profile.incomplete_for_category"
        )
    finally:
        await engine.dispose()


async def test_assert_eligibility_raises_when_super_not_declared(
    iam_client, use_live_valkey
):
    """Profile exists; super_id not in active list → 422 envelope."""
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000851", "545454"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        async with Session() as session:
            await customer_service.upsert_profile(
                user_id,
                PatchProfileRequest(
                    manufacturer_name="Elig Test Pvt",
                    manufacturer_address="1 ET Rd",
                    manufacturer_pincode="560001",
                    packer_name="Elig Test Pvt",
                    packer_address="1 ET Rd",
                    packer_pincode="560001",
                    country_of_origin="India",
                ),
                session,
            )
            await session.commit()

        async with Session() as session:
            with pytest.raises(ProfileIncompleteForCategoryError) as excinfo:
                await customer_service.assert_eligible_for_super_id(
                    user_id, "26", session
                )
        assert excinfo.value.super_id == "26"
    finally:
        await engine.dispose()


async def test_assert_eligibility_raises_when_compliance_keys_missing(
    iam_client, use_live_valkey
):
    """Profile + Grocery declared + FSSAI missing → 422 with missing list."""
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000852", "353535"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        async with Session() as session:
            await customer_service.upsert_profile(
                user_id,
                PatchProfileRequest(
                    manufacturer_name="Compliance Gate Pvt",
                    manufacturer_address="1 CG Rd",
                    manufacturer_pincode="560001",
                    packer_name="Compliance Gate Pvt",
                    packer_address="1 CG Rd",
                    packer_pincode="560001",
                    country_of_origin="India",
                ),
                session,
            )
            await customer_repo.update_active_categories(
                session, user_id, ["26"], onboarding_complete=False
            )
            await session.commit()

        async with Session() as session:
            with pytest.raises(ProfileIncompleteForCategoryError) as excinfo:
                await customer_service.assert_eligible_for_super_id(
                    user_id, "26", session
                )
        assert "fssai_license_number" in excinfo.value.missing_keys
    finally:
        await engine.dispose()


async def test_assert_eligibility_succeeds_when_all_gates_pass(
    iam_client, use_live_valkey
):
    """All gates pass → no raise."""
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000853", "252525"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        async with Session() as session:
            await customer_service.upsert_profile(
                user_id,
                PatchProfileRequest(
                    manufacturer_name="Eligible Pvt",
                    manufacturer_address="1 E Rd",
                    manufacturer_pincode="560001",
                    packer_name="Eligible Pvt",
                    packer_address="1 E Rd",
                    packer_pincode="560001",
                    country_of_origin="India",
                ),
                session,
            )
            await customer_repo.update_active_categories(
                session, user_id, ["26"], onboarding_complete=False
            )
            await customer_service.set_compliance_extension(
                user_id,
                "26",
                {"fssai_license_number": "10012345678901"},
                session,
            )
            await session.commit()

        async with Session() as session:
            result = await customer_service.assert_eligible_for_super_id(
                user_id, "26", session
            )
            assert result is None
    finally:
        await engine.dispose()


async def test_assert_eligibility_passes_for_optional_super(
    iam_client, use_live_valkey
):
    """Declared OPTIONAL super (Kids) without extension → no raise."""
    access_token = await _create_user_via_otp_verify(
        iam_client, "+915550000854", "151515"
    )
    user_id = await _resolve_user_id(iam_client, access_token)

    engine, Session = await _make_session_factory()
    try:
        async with Session() as session:
            await customer_service.upsert_profile(
                user_id,
                PatchProfileRequest(
                    manufacturer_name="Optional Pvt",
                    manufacturer_address="1 O Rd",
                    manufacturer_pincode="560001",
                    packer_name="Optional Pvt",
                    packer_address="1 O Rd",
                    packer_pincode="560001",
                    country_of_origin="India",
                ),
                session,
            )
            await customer_repo.update_active_categories(
                session, user_id, ["13"], onboarding_complete=True
            )
            await session.commit()

        async with Session() as session:
            result = await customer_service.assert_eligible_for_super_id(
                user_id, "13", session
            )
            assert result is None
    finally:
        await engine.dispose()
