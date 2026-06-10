"""Unit test §8.J #3 — compliance extension validation per super_id.

Per BACKEND_ARCHITECTURE.md §8.J unit 3:

    "Compliance extension validation per super_id — Grocery
    (``super_id=26``) requires ``fssai_license_number``; missing → 422
    ``customer.compliance.missing_fields`` with envelope payload listing
    the missing keys."

Also asserts the master-ruling 3 invariant — COMPLIANCE_EXTENSION_MAP
has exactly 11 keys; Beauty's 6 super_ids share ONE Spec instance.
"""

from __future__ import annotations

import pytest

from app.modules.customer import service as customer_service
from app.modules.customer.domain import COMPLIANCE_EXTENSION_MAP
from app.modules.customer.exceptions import (
    ComplianceExtensionMissingFieldsError,
    SuperCategoryNotDeclaredError,
)
from app.modules.customer.schemas import (
    PatchActiveCategoriesRequest,  # noqa: F401 — schema sanity for the suite
    PatchProfileRequest,
)
from app.shared.models.user import User


async def _seed_user_with_profile(db, phone: str, super_ids: list[str]):
    """Helper: create a User + minimal seller_profile + declared super_ids."""
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()

    patch = PatchProfileRequest(
        manufacturer_name="Ext Test Pvt",
        manufacturer_address="1 Test Rd",
        manufacturer_pincode="560001",
        packer_name="Ext Test Pvt",
        packer_address="1 Test Rd",
        packer_pincode="560001",
        country_of_origin="India",
    )
    await customer_service.upsert_profile(user.id, patch, db)

    # Bypass the categories-set validation by writing the array directly via
    # the repository.  We do this because seeding the categories table for a
    # unit test is heavyweight; the cross-module set-validation path is
    # already covered by the integration test.
    from app.modules.customer import repository as customer_repo

    await customer_repo.update_active_categories(
        db, user.id, super_ids, onboarding_complete=False
    )
    return user


def test_compliance_extension_map_has_exactly_eleven_keys():
    """Master ruling 3 lock: 11 keys, no 7th source rule."""
    assert len(COMPLIANCE_EXTENSION_MAP) == 11, (
        f"COMPLIANCE_EXTENSION_MAP must have 11 keys; got {len(COMPLIANCE_EXTENSION_MAP)}"
    )
    expected_keys = frozenset(
        {"26", "13", "16", "19", "36", "37", "14", "88", "34", "80", "30"}
    )
    assert frozenset(COMPLIANCE_EXTENSION_MAP.keys()) == expected_keys


def test_beauty_super_ids_share_one_spec_instance():
    """Beauty's 6 super_ids each map to the SAME Spec instance (O(1) lookup)."""
    beauty_super_ids = ("19", "36", "37", "14", "88", "34")
    first = COMPLIANCE_EXTENSION_MAP[beauty_super_ids[0]]
    for sid in beauty_super_ids[1:]:
        assert COMPLIANCE_EXTENSION_MAP[sid] is first, (
            f"super_id={sid} must share Beauty Spec instance with super_id=19"
        )
    assert first.compulsory is True, "Beauty spec must be compulsory per ruling 4"
    assert "license_registration_number" in first.required_keys


def test_grocery_compulsory_and_fssai_required():
    """Grocery (26) is compulsory and requires fssai_license_number."""
    spec = COMPLIANCE_EXTENSION_MAP["26"]
    assert spec.compulsory is True
    assert "fssai_license_number" in spec.required_keys


def test_optional_super_specs_are_non_compulsory():
    """Kids, Electronics, Books, Home & Kitchen are all compulsory=False."""
    for sid in ("13", "16", "80", "30"):
        spec = COMPLIANCE_EXTENSION_MAP[sid]
        assert spec.compulsory is False, (
            f"super_id={sid} ({spec.super_name}) must be compulsory=False"
        )


async def test_grocery_missing_fssai_raises_422(db, use_live_valkey):
    """Grocery extension missing fssai_license_number → 422 envelope ID."""
    user = await _seed_user_with_profile(db, "+915550000810", ["26"])

    with pytest.raises(ComplianceExtensionMissingFieldsError) as excinfo:
        await customer_service.set_compliance_extension(
            user.id,
            super_id="26",
            payload={},  # empty — missing required key
            db=db,
        )
    err = excinfo.value
    assert err.validation_message_id == "customer.compliance.missing_fields"
    assert err.status_code == 422
    assert "fssai_license_number" in err.missing_keys
    assert err.super_id == "26"


async def test_grocery_with_fssai_succeeds(db, use_live_valkey):
    """Grocery extension WITH fssai_license_number → success + recompute."""
    user = await _seed_user_with_profile(db, "+915550000811", ["26"])

    profile = await customer_service.set_compliance_extension(
        user.id,
        super_id="26",
        payload={"fssai_license_number": "10012345678901"},
        db=db,
    )
    assert profile.compliance_extensions["26"]["fssai_license_number"] == (
        "10012345678901"
    )
    # onboarding_complete flips True because all base fields are present AND
    # the one compulsory Grocery key is now populated.
    assert profile.onboarding_complete is True


async def test_beauty_missing_keys_raises_422(db, use_live_valkey):
    """Beauty extension missing all 3 required keys → 422 with all 3 listed."""
    user = await _seed_user_with_profile(db, "+915550000812", ["19"])

    with pytest.raises(ComplianceExtensionMissingFieldsError) as excinfo:
        await customer_service.set_compliance_extension(
            user.id,
            super_id="19",
            payload={},
            db=db,
        )
    assert set(excinfo.value.missing_keys) == {
        "license_registration_number",
        "license_registration_type",
        "license_expiry_date",
    }


async def test_super_id_not_declared_raises_404(db, use_live_valkey):
    """Setting compliance for a super_id NOT in active list → 404."""
    user = await _seed_user_with_profile(db, "+915550000813", ["26"])

    # Try to write Beauty extension while only Grocery is declared.
    with pytest.raises(SuperCategoryNotDeclaredError) as excinfo:
        await customer_service.set_compliance_extension(
            user.id,
            super_id="19",
            payload={"license_registration_number": "X"},
            db=db,
        )
    assert excinfo.value.status_code == 404
    assert excinfo.value.validation_message_id == "customer.super_category.not_declared"
    assert excinfo.value.super_id == "19"
