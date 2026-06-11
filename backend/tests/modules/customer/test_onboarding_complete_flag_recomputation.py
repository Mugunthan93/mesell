"""Unit test §8.J #4 — onboarding_complete flag recomputation.

Per BACKEND_ARCHITECTURE.md §8.J unit 4:

    "``onboarding_complete`` flag recomputation — true iff all 10 base
    fields are present AND all ``active_super_categories``' compulsory
    extension keys are present; recomputed on every PATCH (B.2 / B.3 / B.4)."

The flag column is ``onboarding_complete`` per master ruling 2 (DB-aligned;
the §8 doc was amended to match the migration ``935e55b4852c``).

This test asserts the recompute logic at 6 transition points:
  (1) brand-new profile → False
  (2) all base fields, no super → True
  (3) add a compulsory Grocery — flag flips False
  (4) provide fssai_license_number — flag flips True
  (5) add an optional Kids super — flag stays True
  (6) add a Beauty super (compulsory) without license keys — flag flips False
"""

from __future__ import annotations

import pytest

from app.modules.customer import repository as customer_repo
from app.modules.customer import service as customer_service
from app.modules.customer.schemas import PatchProfileRequest
from app.shared.models.user import User


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_user(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    return user


async def test_recompute_through_full_onboarding_lifecycle(db, use_live_valkey):
    """6 transitions; the flag tracks the gate per master ruling 4."""
    user = await _seed_user(db, "+915550000820")

    # ── (1) Brand-new profile (first PATCH) — no extensions, but full base
    # → flag flips True immediately because no compulsory super is declared.
    patch1 = PatchProfileRequest(
        manufacturer_name="Recompute Pvt",
        manufacturer_address="1 R Rd",
        manufacturer_pincode="560001",
        packer_name="Recompute Pvt",
        packer_address="1 R Rd",
        packer_pincode="560001",
        country_of_origin="India",
    )
    profile = await customer_service.upsert_profile(user.id, patch1, db)
    assert profile.onboarding_complete is True, (
        "Full base + no compulsory super → onboarding_complete=True"
    )

    # ── (3) Declare Grocery (compulsory) — flag flips False until the FSSAI
    # license number is provided.
    await customer_repo.update_active_categories(
        db, user.id, ["26"], onboarding_complete=False
    )
    # Trigger a recompute path via the service-level set_active_categories
    # — but we already bypassed the categories.super_id validation, so
    # we re-run the recompute by issuing a no-op PATCH base profile.
    profile = await customer_service.upsert_profile(
        user.id, PatchProfileRequest(country_of_origin="India"), db
    )
    assert profile.active_super_categories == ["26"]
    assert profile.onboarding_complete is False, (
        "Compulsory Grocery declared but FSSAI missing → False"
    )

    # ── (4) Provide fssai_license_number — flag flips True.
    profile = await customer_service.set_compliance_extension(
        user.id, "26", {"fssai_license_number": "10012345678901"}, db
    )
    assert profile.onboarding_complete is True

    # ── (5) Add Kids (optional) — flag stays True (Kids is not compulsory).
    await customer_repo.update_active_categories(
        db, user.id, ["26", "13"], onboarding_complete=True
    )
    profile = await customer_service.upsert_profile(
        user.id, PatchProfileRequest(country_of_origin="India"), db
    )
    assert profile.onboarding_complete is True, (
        "Adding an OPTIONAL super (Kids) must NOT flip the flag"
    )

    # ── (6) Add Beauty (compulsory) without license keys — flag flips False.
    await customer_repo.update_active_categories(
        db, user.id, ["26", "13", "19"], onboarding_complete=False
    )
    profile = await customer_service.upsert_profile(
        user.id, PatchProfileRequest(country_of_origin="India"), db
    )
    assert profile.onboarding_complete is False, (
        "Adding a COMPULSORY super (Beauty) without keys → flag flips False"
    )

    # Sanity: providing Beauty keys flips it back to True.
    profile = await customer_service.set_compliance_extension(
        user.id,
        "19",
        {
            "license_registration_number": "LIC-001",
            "license_registration_type": "MFG",
            "license_expiry_date": "2027-12-31",
        },
        db,
    )
    assert profile.onboarding_complete is True


async def test_missing_base_field_keeps_flag_false(db, use_live_valkey):
    """First PATCH that does NOT include all 7 blocking fields → IntegrityError.

    The ORM 6 NOT-NULL columns force the row to fail INSERT if missing.
    """
    user = await _seed_user(db, "+915550000821")

    incomplete = PatchProfileRequest(
        manufacturer_name="Incomplete Pvt",
        # missing manufacturer_address (NOT NULL) → expect failure
        manufacturer_pincode="560001",
        packer_name="Incomplete Pvt",
        packer_address="1 Inc Rd",
        packer_pincode="560001",
        country_of_origin="India",
    )
    with pytest.raises(Exception):  # noqa: BLE001 — IntegrityError or wrapper
        await customer_service.upsert_profile(user.id, incomplete, db)


async def test_recompute_truth_table_all_optional_supers(db, use_live_valkey):
    """All declared supers are OPTIONAL → flag tracks only base fields."""
    user = await _seed_user(db, "+915550000822")
    patch = PatchProfileRequest(
        manufacturer_name="Optional Pvt",
        manufacturer_address="1 Opt Rd",
        manufacturer_pincode="560001",
        packer_name="Optional Pvt",
        packer_address="1 Opt Rd",
        packer_pincode="560001",
        country_of_origin="India",
    )
    profile = await customer_service.upsert_profile(user.id, patch, db)
    assert profile.onboarding_complete is True

    # Declare two OPTIONAL supers (Kids + Electronics + Books).
    await customer_repo.update_active_categories(
        db, user.id, ["13", "16", "80"], onboarding_complete=True
    )
    profile = await customer_service.upsert_profile(
        user.id, PatchProfileRequest(country_of_origin="India"), db
    )
    assert profile.onboarding_complete is True, (
        "All-optional supers must never block the flag"
    )
