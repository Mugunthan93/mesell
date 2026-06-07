"""Unit test §8.J #5 — Eye-Serum case.

Per BACKEND_ARCHITECTURE.md §8.J unit 5:

    "Eye-Serum case — ``customer`` stores ONLY the 9 standard fields
    regardless of the seller's active categories (the
    ``compliance_shape='collapsed'`` lookup is ``export``'s concern per
    §5A.F + §12.6)."

This test asserts the customer module's boundary contract: it MUST NOT
collapse, MUST NOT join, MUST NOT prematurely render the Eye-Serum
specific 3-column form.  The export Adapter consumes
``get_compliance_block`` and performs the collapse to 3 columns at
XLSX-write time only.
"""

from __future__ import annotations

from app.modules.customer import service as customer_service
from app.modules.customer.domain import COMPLIANCE_EXTENSION_MAP, ComplianceBlock
from app.modules.customer.schemas import PatchProfileRequest
from app.shared.models.user import User


async def _seed_user_and_profile(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    patch = PatchProfileRequest(
        manufacturer_name="Eye Serum Mfg Pvt",
        manufacturer_address="1 ES Rd, Mumbai",
        manufacturer_pincode="400001",
        packer_name="Eye Serum Pkr Pvt",
        packer_address="2 ES Rd, Mumbai",
        packer_pincode="400002",
        importer_name="Eye Serum Imp Pvt",
        importer_address="3 ES Rd, Mumbai",
        importer_pincode="400003",
        country_of_origin="India",
    )
    await customer_service.upsert_profile(user.id, patch, db)
    return user


async def test_compliance_block_contains_exactly_nine_lm_fields_plus_country(
    db, use_live_valkey
):
    """ComplianceBlock contains the 9 LM fields + country_of_origin — no Beauty
    collapse, no Eye-Serum-specific 3-column shape."""
    user = await _seed_user_and_profile(db, "+915550000830")

    block = await customer_service.get_compliance_block(user.id, db)
    assert isinstance(block, ComplianceBlock)

    # The block carries each of the 9 standard LM fields under its own attr.
    # No "manufacturer_details" / "packer_details" / "importer_details"
    # collapsed columns.
    assert block.manufacturer_name == "Eye Serum Mfg Pvt"
    assert block.manufacturer_address == "1 ES Rd, Mumbai"
    assert block.manufacturer_pincode == "400001"
    assert block.packer_name == "Eye Serum Pkr Pvt"
    assert block.packer_address == "2 ES Rd, Mumbai"
    assert block.packer_pincode == "400002"
    assert block.importer_name == "Eye Serum Imp Pvt"
    assert block.importer_address == "3 ES Rd, Mumbai"
    assert block.importer_pincode == "400003"
    assert block.country_of_origin == "India"

    # The dataclass MUST NOT carry a collapsed-shape attribute.
    forbidden_names = (
        "manufacturer_details",
        "packer_details",
        "importer_details",
        "compliance_shape",
    )
    for n in forbidden_names:
        assert not hasattr(block, n), (
            f"ComplianceBlock leaked collapsed-shape attr {n!r} — that lives in "
            "export, not customer"
        )


async def test_eye_serum_seller_with_beauty_super_still_stores_only_9_fields(
    db, use_live_valkey
):
    """A seller selling Eye Serum (Beauty super_id) still has 9 base + Beauty
    extension stored.  The extension does NOT collapse the base 9 fields.
    """
    user = await _seed_user_and_profile(db, "+915550000831")

    # Declare Beauty (compulsory) + provide license keys.
    from app.modules.customer import repository as customer_repo

    await customer_repo.update_active_categories(
        db, user.id, ["19"], onboarding_complete=False
    )
    profile = await customer_service.set_compliance_extension(
        user.id,
        "19",
        {
            "license_registration_number": "BEAUTY-001",
            "license_registration_type": "MFG",
            "license_expiry_date": "2027-12-31",
        },
        db,
    )

    # The 9 base fields are STILL stored individually.
    assert profile.manufacturer_name == "Eye Serum Mfg Pvt"
    assert profile.packer_name == "Eye Serum Pkr Pvt"
    assert profile.importer_name == "Eye Serum Imp Pvt"

    # Beauty extension is stored alongside, NOT collapsed into the base 9.
    assert "19" in profile.compliance_extensions
    assert profile.compliance_extensions["19"]["license_registration_number"] == (
        "BEAUTY-001"
    )

    # The active super categories list is correctly the single Beauty super.
    assert profile.active_super_categories == ["19"]


def test_beauty_spec_does_not_carry_collapsed_marker():
    """Per §5A.F + §12.6 the compliance_shape selector lives on the export
    side, NOT on the Spec.  Customer's Spec must NOT carry a shape marker.
    """
    beauty_spec = COMPLIANCE_EXTENSION_MAP["19"]
    forbidden_attrs = ("compliance_shape", "collapse", "shape")
    for attr in forbidden_attrs:
        assert not hasattr(beauty_spec, attr), (
            f"ComplianceExtensionSpec leaked export-shape attr {attr!r}"
        )
