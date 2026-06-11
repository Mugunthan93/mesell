"""Unit test §8.J #1 — profile upsert idempotency.

Per BACKEND_ARCHITECTURE.md §8.J unit 1:

    "Profile upsert idempotency — first PATCH creates the row, subsequent
    PATCH updates the same row, returns the same ``user_id``."

The repository.upsert function is the locked first-PATCH-creates-row
contract per §8.B.2.  We exercise it through the service layer so the
recompute + cache invalidation paths also run.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.modules.customer import service as customer_service
from app.modules.customer.schemas import PatchProfileRequest
from app.shared.models.seller_profile import SellerProfile as SellerProfileORM
from app.shared.models.user import User


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _seed_user(db, phone: str = "+915550000801") -> User:
    """Insert a User row so the seller_profile.user_id FK resolves."""
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    return user


async def test_first_patch_creates_row_then_subsequent_patches_update(
    db, use_live_valkey
):
    """Idempotency: 3 PATCHs → exactly 1 row, last value wins per field."""
    user = await _seed_user(db, phone="+915550000801")

    # ── First PATCH — provides all NOT NULL fields so the row INSERTs ────────
    patch1 = PatchProfileRequest(
        manufacturer_name="Acme Pvt Ltd",
        manufacturer_address="1 Acme Road, Bengaluru",
        manufacturer_pincode="560001",
        packer_name="Acme Pvt Ltd",
        packer_address="1 Acme Road, Bengaluru",
        packer_pincode="560001",
        country_of_origin="India",
    )
    profile1 = await customer_service.upsert_profile(user.id, patch1, db)
    assert profile1.user_id == user.id
    assert profile1.manufacturer_name == "Acme Pvt Ltd"
    assert profile1.country_of_origin == "India"

    # ── Second PATCH — updates only one field; others untouched ──────────────
    patch2 = PatchProfileRequest(manufacturer_address="2 New Acme Road, Bengaluru")
    profile2 = await customer_service.upsert_profile(user.id, patch2, db)
    assert profile2.user_id == user.id, "user_id must stabilise across upserts"
    assert profile2.manufacturer_address == "2 New Acme Road, Bengaluru"
    # Untouched field preserved.
    assert profile2.manufacturer_name == "Acme Pvt Ltd"

    # ── Third PATCH — country_of_origin update ───────────────────────────────
    patch3 = PatchProfileRequest(country_of_origin="India")
    profile3 = await customer_service.upsert_profile(user.id, patch3, db)
    assert profile3.user_id == user.id
    assert profile3.country_of_origin == "India"

    # ── Exactly ONE row in the DB for this user_id ──────────────────────────
    result = await db.execute(
        select(SellerProfileORM).where(SellerProfileORM.user_id == user.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1, "Upsert must produce exactly one row per user_id"


async def test_upsert_returns_same_user_id_as_input(db, use_live_valkey):
    """user_id round-trips unchanged across the service ↔ ORM boundary."""
    user = await _seed_user(db, phone="+915550000802")

    patch = PatchProfileRequest(
        manufacturer_name="Round Trip Pvt",
        manufacturer_address="1 RT Rd",
        manufacturer_pincode="110001",
        packer_name="Round Trip Pvt",
        packer_address="1 RT Rd",
        packer_pincode="110001",
        country_of_origin="India",
    )
    profile = await customer_service.upsert_profile(user.id, patch, db)
    assert isinstance(profile.user_id, uuid.UUID)
    assert profile.user_id == user.id
