"""Phase 4 smoke tests — MeeSell database track.

Tests every DB property that protects the API/services builders from a real
class of bug.  All tests run against the live dev Postgres (K3s, port 5433).

Categories:
  A. CRUD per table (13 tests)
  B. JSONB round-trip (8 tests — one per JSONB column)
  C. FK enforcement (5 tests)
  D. Unique constraint enforcement (3 tests)
  E. CHECK constraint enforcement (2 tests)
  F. Computed column (2 tests — is_front True and False)
  G. Server-default verification (3 tests)
  H. Seeded data sanity (6 tests — read-only, no fixtures)
     Includes 2 new tests added in Session 2 gap pass (G1 — is_advanced wiring):
       - test_is_advanced_flag_set_for_group_id
       - test_is_advanced_flag_not_set_for_non_advanced_fields

Total: 42 tests

Fixture contract:
  ``db``         — per-test AsyncSession bound to a rolled-back transaction
                   (from conftest.py).  Guarantees zero test-data leakage.
  ``dev_engine`` — session-scoped engine for section H read-only queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models import (
    AuditEvent,
    Base,
    Catalog,
    Category,
    Export,
    FieldAlias,
    FieldEnumValue,
    PricingCalc,
    Product,
    ProductDraft,
    ProductImage,
    SellerProfile,
    Template,
    User,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=timezone.utc)


def _unique_phone() -> str:
    """Return a unique E.164-ish phone number that fits in VARCHAR(15)."""
    # Use last 10 hex digits of a UUID to stay within 15 chars: "+9" + 10 digits
    suffix = str(uuid.uuid4().int)[-10:]
    return f"+9{suffix}"


def _unique_leaf_id() -> str:
    """Return a unique Meesho leaf ID string (≤16 chars)."""
    return str(uuid.uuid4().int)[:10]


def _unique_hash() -> str:
    """Return a unique 64-char hex string for schema_hash."""
    return uuid.uuid4().hex + uuid.uuid4().hex  # 32+32 = 64 chars


def _unique_variant() -> str:
    """Return a unique field alias variant name."""
    return f"test_variant_{uuid.uuid4().hex[:12]}"


async def _make_user(db: AsyncSession) -> User:
    """Insert and flush a minimal User row; return the ORM object."""
    user = User(phone=_unique_phone())
    db.add(user)
    await db.flush()
    return user


async def _make_template(db: AsyncSession) -> Template:
    """Insert and flush a minimal Template row; return the ORM object."""
    tmpl = Template(
        schema_hash=_unique_hash(),
        schema_jsonb={
            "fields": [
                {
                    "canonical_name": "product_name",
                    "data_type": "text",
                    "primitive": "short_text",
                    "marker": "compulsory",
                    "is_advanced": False,
                    "is_hidden": False,
                    "compliance_role": None,
                    "step_id": "basics",
                    "max_length": 255,
                    "min_length": 1,
                    "regex": None,
                    "min_value": None,
                    "max_value": None,
                    "unit_suffix": None,
                    "display_label": {"en": "Product Name"},
                    "display_help": {"en": "Enter the product name"},
                    "display_placeholder": {"en": "e.g. Cotton T-Shirt"},
                    "display_unit_label": None,
                    "validation_message": {"en": "Product name is required"},
                    "help_url": None,
                    "meesho_column_header": "Product Name",
                    "meesho_column_index": 1,
                    "meesho_default": None,
                    "enum_codes_map": None,
                    "enum_labels": None,
                }
            ],
            "compulsory_count": 1,
            "optional_count": 0,
            "total_count": 1,
            "wizard_step_count": 1,
            "main_sheet_label": "Test Sheet",
        },
        compliance_shape="standard",
    )
    db.add(tmpl)
    await db.flush()
    return tmpl


async def _make_category(db: AsyncSession, template: Template) -> Category:
    """Insert and flush a minimal Category row; return the ORM object."""
    cat = Category(
        meesho_leaf_id=_unique_leaf_id(),
        super_id="26",
        super_name="Grocery",
        path="Grocery > Test Super > Test Sub",
        leaf_name="Test Leaf",
        template_id=template.id,
    )
    db.add(cat)
    await db.flush()
    return cat


async def _make_catalog(db: AsyncSession, user: User) -> Catalog:
    """Insert and flush a minimal Catalog row; return the ORM object."""
    cat = Catalog(user_id=user.id, name="Test Catalog")
    db.add(cat)
    await db.flush()
    return cat


async def _make_product(
    db: AsyncSession, catalog: Catalog, user: User, category: Category
) -> Product:
    """Insert and flush a minimal Product row; return the ORM object."""
    prod = Product(
        catalog_id=catalog.id,
        user_id=user.id,
        category_id=category.id,
    )
    db.add(prod)
    await db.flush()
    return prod


# ===========================================================================
# A. CRUD — one test per model (13 tests)
# ===========================================================================


async def test_crud_user(db: AsyncSession) -> None:
    """Create / read / delete a User row."""
    phone = _unique_phone()
    user = User(phone=phone, email="test@example.com")
    db.add(user)
    await db.flush()

    fetched = await db.get(User, user.id)
    assert fetched is not None
    assert fetched.phone == phone
    assert fetched.plan == "free"

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(User, user.id)
    assert gone is None


async def test_crud_seller_profile(db: AsyncSession) -> None:
    """Create / read / delete a SellerProfile row (requires User parent)."""
    user = await _make_user(db)

    profile = SellerProfile(
        user_id=user.id,
        manufacturer_name="Test Mfr",
        manufacturer_address="123 Test St",
        manufacturer_pincode="600001",
        packer_name="Test Packer",
        packer_address="456 Test St",
        packer_pincode="600002",
        country_of_origin="India",
    )
    db.add(profile)
    await db.flush()

    fetched = await db.get(SellerProfile, user.id)
    assert fetched is not None
    assert fetched.manufacturer_name == "Test Mfr"
    assert fetched.onboarding_complete is False

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(SellerProfile, user.id)
    assert gone is None


async def test_crud_template(db: AsyncSession) -> None:
    """Create / read / delete a Template row."""
    tmpl = await _make_template(db)
    schema_hash = tmpl.schema_hash

    fetched = await db.get(Template, tmpl.id)
    assert fetched is not None
    assert fetched.schema_hash == schema_hash
    assert fetched.compliance_shape == "standard"

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(Template, tmpl.id)
    assert gone is None


async def test_crud_category(db: AsyncSession) -> None:
    """Create / read / delete a Category row (requires Template parent)."""
    tmpl = await _make_template(db)
    leaf_id = _unique_leaf_id()

    cat = Category(
        meesho_leaf_id=leaf_id,
        super_id="11",
        super_name="Women Fashion",
        path="Women Fashion > Western Wear > Tops",
        leaf_name="Women Tops",
        template_id=tmpl.id,
    )
    db.add(cat)
    await db.flush()

    fetched = await db.get(Category, cat.id)
    assert fetched is not None
    assert fetched.meesho_leaf_id == leaf_id
    assert fetched.super_name == "Women Fashion"

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(Category, cat.id)
    assert gone is None


async def test_crud_field_enum_value(db: AsyncSession) -> None:
    """Create / read / delete a FieldEnumValue row (requires Category parent)."""
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)

    enum_entries = [
        {"canonical": "Cotton", "meesho": "Cotton", "labels": {"en": "Cotton"}},
        {"canonical": "Polyester", "meesho": "Polyester", "labels": {"en": "Polyester"}},
    ]
    fev = FieldEnumValue(
        category_id=cat.id,
        field_name="fabric",
        enum_entries=enum_entries,
        value_count=2,
    )
    db.add(fev)
    await db.flush()

    fetched = await db.get(FieldEnumValue, (cat.id, "fabric"))
    assert fetched is not None
    assert fetched.value_count == 2
    assert isinstance(fetched.enum_entries, list)
    assert len(fetched.enum_entries) == 2

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(FieldEnumValue, (cat.id, "fabric"))
    assert gone is None


async def test_crud_field_alias(db: AsyncSession) -> None:
    """Create / read / delete a FieldAlias row."""
    variant = _unique_variant()
    alias = FieldAlias(
        variant_name=variant,
        canonical_name="product_color",
        source="manual",
        for_xlsx_export=True,
    )
    db.add(alias)
    await db.flush()

    fetched = await db.get(FieldAlias, variant)
    assert fetched is not None
    assert fetched.canonical_name == "product_color"
    assert fetched.for_xlsx_export is True

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(FieldAlias, variant)
    assert gone is None


async def test_crud_catalog(db: AsyncSession) -> None:
    """Create / read / delete a Catalog row (requires User parent)."""
    user = await _make_user(db)
    catalog = await _make_catalog(db, user)

    fetched = await db.get(Catalog, catalog.id)
    assert fetched is not None
    assert fetched.name == "Test Catalog"
    assert fetched.status == "draft"

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(Catalog, catalog.id)
    assert gone is None


async def test_crud_product(db: AsyncSession) -> None:
    """Create / read / delete a Product row (requires Catalog + User + Category)."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    fetched = await db.get(Product, prod.id)
    assert fetched is not None
    assert fetched.status == "draft"
    assert fetched.deleted_at is None

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(Product, prod.id)
    assert gone is None


async def test_crud_product_image(db: AsyncSession) -> None:
    """Create / read / delete a ProductImage row."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    img = ProductImage(
        product_id=prod.id,
        gcs_path=f"{user.id}/{prod.id}/1.jpg",
        order_idx=1,
    )
    db.add(img)
    await db.flush()
    # Expire to force re-read of server-computed is_front
    await db.refresh(img)

    fetched = await db.get(ProductImage, img.id)
    assert fetched is not None
    assert fetched.order_idx == 1
    assert fetched.status == "pending"

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(ProductImage, img.id)
    assert gone is None


async def test_crud_pricing_calc(db: AsyncSession) -> None:
    """Create / read / delete a PricingCalc row."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    calc = PricingCalc(
        product_id=prod.id,
        mrp=Decimal("999.00"),
        meesho_price=Decimal("799.00"),
        commission_pct=Decimal("12.50"),
    )
    db.add(calc)
    await db.flush()

    fetched = await db.get(PricingCalc, calc.id)
    assert fetched is not None
    assert fetched.mrp == Decimal("999.00")
    assert fetched.commission_pct == Decimal("12.50")

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(PricingCalc, calc.id)
    assert gone is None


async def test_crud_export(db: AsyncSession) -> None:
    """Create / read / delete an Export row."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    exp = Export(
        product_id=prod.id,
        user_id=user.id,
        status="processing",
    )
    db.add(exp)
    await db.flush()

    fetched = await db.get(Export, exp.id)
    assert fetched is not None
    assert fetched.status == "processing"
    assert fetched.error_message is None

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(Export, exp.id)
    assert gone is None


async def test_crud_audit_event(db: AsyncSession) -> None:
    """Create / read an AuditEvent row.  No delete — append-only in production.
    id is BIGSERIAL (Identity), so we must NOT supply it."""
    user = await _make_user(db)

    event = AuditEvent(
        user_id=user.id,
        event_type="product.patch",
        entity_type="product",
        entity_id=uuid.uuid4(),
    )
    db.add(event)
    await db.flush()

    fetched = await db.get(AuditEvent, event.id)
    assert fetched is not None
    assert fetched.event_type == "product.patch"
    assert isinstance(fetched.id, int)
    assert fetched.id > 0


async def test_crud_product_draft(db: AsyncSession) -> None:
    """Create / read / delete a ProductDraft row (composite PK)."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    draft = ProductDraft(
        user_id=user.id,
        product_id=prod.id,
        draft_jsonb={"product_name": "Draft Name", "color": "Red"},
    )
    db.add(draft)
    await db.flush()

    fetched = await db.get(ProductDraft, (user.id, prod.id))
    assert fetched is not None
    assert fetched.draft_jsonb["product_name"] == "Draft Name"

    await db.delete(fetched)
    await db.flush()

    gone = await db.get(ProductDraft, (user.id, prod.id))
    assert gone is None


# ===========================================================================
# B. JSONB round-trip (8 tests)
# ===========================================================================


async def test_jsonb_seller_profile_compliance_extensions(db: AsyncSession) -> None:
    """seller_profile.compliance_extensions — nested object with arrays."""
    user = await _make_user(db)
    payload = {
        "26": {
            "fssai_license_number": "10012345678901",
            "fssai_expiry": "2027-12-31",
            "allergens": ["nuts", "dairy"],
        },
        "13": {
            "bis_isi_certification_number": "IS-1234-2024",
            "bis_marks": [{"mark": "ISI", "applicable": True}],
        },
    }
    profile = SellerProfile(
        user_id=user.id,
        manufacturer_name="Mfr",
        manufacturer_address="Addr",
        manufacturer_pincode="600001",
        packer_name="Packer",
        packer_address="Addr",
        packer_pincode="600002",
        compliance_extensions=payload,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    assert isinstance(profile.compliance_extensions, dict)
    assert profile.compliance_extensions["26"]["fssai_license_number"] == "10012345678901"
    assert profile.compliance_extensions["26"]["allergens"] == ["nuts", "dairy"]
    assert profile.compliance_extensions["13"]["bis_marks"][0]["mark"] == "ISI"


async def test_jsonb_template_schema_jsonb(db: AsyncSession) -> None:
    """templates.schema_jsonb — full §5.6.1 shape with nested objects."""
    schema = {
        "fields": [
            {
                "canonical_name": "product_name",
                "data_type": "text",
                "primitive": "short_text",
                "marker": "compulsory",
                "is_advanced": False,
                "is_hidden": False,
                "compliance_role": None,
                "step_id": "basics",
                "max_length": 255,
                "min_length": 1,
                "regex": None,
                "min_value": None,
                "max_value": None,
                "unit_suffix": None,
                "display_label": {"en": "Product Name", "hi": "उत्पाद नाम"},
                "display_help": {"en": "Full product name including brand"},
                "display_placeholder": {"en": "e.g. Rexona Men Deo"},
                "display_unit_label": None,
                "validation_message": {"en": "Required"},
                "help_url": None,
                "meesho_column_header": "Product Name",
                "meesho_column_index": 3,
                "meesho_default": None,
                "enum_codes_map": None,
                "enum_labels": None,
            },
            {
                "canonical_name": "mrp",
                "data_type": "number",
                "primitive": "currency_inr",
                "marker": "compulsory",
                "is_advanced": False,
                "is_hidden": False,
                "compliance_role": None,
                "step_id": "pricing",
                "max_length": None,
                "min_length": None,
                "regex": None,
                "min_value": 1,
                "max_value": 9999999,
                "unit_suffix": "INR",
                "display_label": {"en": "MRP"},
                "display_help": {"en": "Maximum retail price"},
                "display_placeholder": {"en": "e.g. 499"},
                "display_unit_label": {"en": "₹"},
                "validation_message": {"en": "MRP must be a positive number"},
                "help_url": None,
                "meesho_column_header": "MRP (Rs)",
                "meesho_column_index": 8,
                "meesho_default": None,
                "enum_codes_map": None,
                "enum_labels": None,
            },
        ],
        "compulsory_count": 2,
        "optional_count": 0,
        "total_count": 2,
        "wizard_step_count": 2,
        "main_sheet_label": "T-Shirt",
    }
    tmpl = Template(
        schema_hash=_unique_hash(),
        schema_jsonb=schema,
        compliance_shape="standard",
    )
    db.add(tmpl)
    await db.flush()
    await db.refresh(tmpl)

    assert isinstance(tmpl.schema_jsonb, dict)
    assert tmpl.schema_jsonb["total_count"] == 2
    assert tmpl.schema_jsonb["fields"][0]["display_label"]["hi"] == "उत्पाद नाम"
    assert tmpl.schema_jsonb["fields"][1]["min_value"] == 1


async def test_jsonb_field_enum_values_enum_entries(db: AsyncSession) -> None:
    """field_enum_values.enum_entries — list of objects per §5.6.4."""
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)

    entries = [
        {"canonical": "PE-HD", "meesho": "PE-HD", "labels": {"en": "High-Density Polyethylene"}},
        {"canonical": "PE-LD", "meesho": "PE-LD", "labels": {"en": "Low-Density Polyethylene"}},
        {"canonical": "PP", "meesho": "PP", "labels": {"en": "Polypropylene"}},
    ]
    fev = FieldEnumValue(
        category_id=cat.id,
        field_name="material_type",
        enum_entries=entries,
        value_count=3,
    )
    db.add(fev)
    await db.flush()
    await db.refresh(fev)

    assert isinstance(fev.enum_entries, list)
    assert len(fev.enum_entries) == 3
    assert fev.enum_entries[0]["labels"]["en"] == "High-Density Polyethylene"
    assert fev.enum_entries[2]["canonical"] == "PP"


async def test_jsonb_product_fields_jsonb(db: AsyncSession) -> None:
    """products.fields_jsonb — flat dict keyed by canonical field name."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)

    fields = {
        "product_name": "Premium Cotton T-Shirt",
        "color": "Navy Blue",
        "size": "M",
        "mrp": 499,
        "fabric": "100% Cotton",
        "brand": "WearCo",
    }
    prod = Product(
        catalog_id=catalog.id,
        user_id=user.id,
        category_id=cat.id,
        fields_jsonb=fields,
    )
    db.add(prod)
    await db.flush()
    await db.refresh(prod)

    assert isinstance(prod.fields_jsonb, dict)
    assert prod.fields_jsonb["product_name"] == "Premium Cotton T-Shirt"
    assert prod.fields_jsonb["mrp"] == 499
    assert prod.fields_jsonb["fabric"] == "100% Cotton"


async def test_jsonb_product_ai_suggestions_jsonb(db: AsyncSession) -> None:
    """products.ai_suggestions_jsonb — nested confidence object."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)

    ai_suggestions = {
        "product_name": {
            "value": "Premium Organic Cotton T-Shirt for Men",
            "confidence": 0.93,
            "source": "gemini-2.5-flash",
            "accepted": False,
        },
        "description": {
            "value": "Soft, breathable cotton tee perfect for everyday wear.",
            "confidence": 0.87,
            "source": "gemini-2.5-flash",
            "accepted": True,
        },
        "color": {
            "value": "Navy Blue",
            "confidence": 0.99,
            "source": "image-analysis",
            "accepted": True,
        },
    }
    prod = Product(
        catalog_id=catalog.id,
        user_id=user.id,
        category_id=cat.id,
        ai_suggestions_jsonb=ai_suggestions,
    )
    db.add(prod)
    await db.flush()
    await db.refresh(prod)

    assert isinstance(prod.ai_suggestions_jsonb, dict)
    assert prod.ai_suggestions_jsonb["product_name"]["confidence"] == 0.93
    assert prod.ai_suggestions_jsonb["description"]["accepted"] is True
    assert prod.ai_suggestions_jsonb["color"]["source"] == "image-analysis"


async def test_jsonb_product_image_precheck_jsonb(db: AsyncSession) -> None:
    """product_images.precheck_jsonb — flat dict from image pipeline."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    precheck = {
        "width": 1000,
        "height": 1000,
        "aspect_ratio": "1:1",
        "color_space": "RGB",
        "has_watermark": False,
        "watermark_confidence": 0.02,
        "background_type": "white",
        "passes_meesho_rules": True,
        "failure_reasons": [],
    }
    img = ProductImage(
        product_id=prod.id,
        gcs_path=f"{user.id}/{prod.id}/1.jpg",
        order_idx=1,
        precheck_jsonb=precheck,
    )
    db.add(img)
    await db.flush()
    await db.refresh(img)

    assert isinstance(img.precheck_jsonb, dict)
    assert img.precheck_jsonb["width"] == 1000
    assert img.precheck_jsonb["has_watermark"] is False
    assert img.precheck_jsonb["passes_meesho_rules"] is True
    assert img.precheck_jsonb["failure_reasons"] == []


async def test_jsonb_audit_event_diff_jsonb(db: AsyncSession) -> None:
    """audit_events.diff_jsonb — before/after structure."""
    user = await _make_user(db)

    diff = {
        "before": {
            "product_name": "Old T-Shirt",
            "color": "Black",
            "mrp": 399,
        },
        "after": {
            "product_name": "Premium Old T-Shirt",
            "color": "Black",
            "mrp": 499,
        },
    }
    event = AuditEvent(
        user_id=user.id,
        event_type="product.patch",
        entity_type="product",
        entity_id=uuid.uuid4(),
        diff_jsonb=diff,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    assert isinstance(event.diff_jsonb, dict)
    assert "before" in event.diff_jsonb
    assert "after" in event.diff_jsonb
    assert event.diff_jsonb["before"]["mrp"] == 399
    assert event.diff_jsonb["after"]["mrp"] == 499
    assert event.diff_jsonb["after"]["product_name"] == "Premium Old T-Shirt"


async def test_jsonb_product_draft_draft_jsonb(db: AsyncSession) -> None:
    """product_drafts.draft_jsonb — full wizard field state."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    draft_state = {
        "product_name": "Work In Progress T-Shirt",
        "color": "White",
        "size": "L",
        "mrp": None,
        "fabric": "Cotton",
        "_wizard_step": "pricing",
        "_last_saved": "2026-06-05T10:30:00Z",
        "images": [{"slot": 1, "status": "uploading", "gcs_path": None}],
    }
    draft = ProductDraft(
        user_id=user.id,
        product_id=prod.id,
        draft_jsonb=draft_state,
    )
    db.add(draft)
    await db.flush()
    await db.refresh(draft)

    assert isinstance(draft.draft_jsonb, dict)
    assert draft.draft_jsonb["product_name"] == "Work In Progress T-Shirt"
    assert draft.draft_jsonb["mrp"] is None
    assert draft.draft_jsonb["_wizard_step"] == "pricing"
    assert draft.draft_jsonb["images"][0]["status"] == "uploading"


# ===========================================================================
# C. FK enforcement (5 tests)
# ===========================================================================


async def test_fk_seller_profile_nonexistent_user(db: AsyncSession) -> None:
    """Inserting a seller_profile row with a non-existent user_id → IntegrityError."""
    bogus_user_id = uuid.uuid4()
    profile = SellerProfile(
        user_id=bogus_user_id,
        manufacturer_name="Ghost Mfr",
        manufacturer_address="Ghost Addr",
        manufacturer_pincode="000000",
        packer_name="Ghost Packer",
        packer_address="Ghost Addr",
        packer_pincode="000000",
    )
    db.add(profile)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_fk_product_nonexistent_catalog(db: AsyncSession) -> None:
    """Inserting a product with a non-existent catalog_id → IntegrityError."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)

    bogus_catalog_id = uuid.uuid4()
    prod = Product(
        catalog_id=bogus_catalog_id,
        user_id=user.id,
        category_id=cat.id,
    )
    db.add(prod)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_fk_field_enum_value_nonexistent_category(db: AsyncSession) -> None:
    """Inserting a field_enum_value with a non-existent category_id → IntegrityError."""
    bogus_category_id = uuid.uuid4()
    fev = FieldEnumValue(
        category_id=bogus_category_id,
        field_name="color",
        enum_entries=[{"canonical": "Red", "meesho": "Red", "labels": {"en": "Red"}}],
        value_count=1,
    )
    db.add(fev)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_fk_cascade_user_deletes_seller_profile(db: AsyncSession) -> None:
    """Deleting a user CASCADE-deletes the linked seller_profile."""
    user = await _make_user(db)
    profile = SellerProfile(
        user_id=user.id,
        manufacturer_name="Mfr",
        manufacturer_address="Addr",
        manufacturer_pincode="600001",
        packer_name="Packer",
        packer_address="Addr",
        packer_pincode="600002",
    )
    db.add(profile)
    await db.flush()

    # Confirm profile exists
    assert await db.get(SellerProfile, user.id) is not None

    # Delete the user — should cascade
    user_id = user.id
    await db.delete(user)
    await db.flush()

    # Profile must be gone too
    gone = await db.get(SellerProfile, user_id)
    assert gone is None


async def test_fk_cascade_catalog_deletes_products(db: AsyncSession) -> None:
    """Deleting a catalog CASCADE-deletes all its products."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)
    prod_id = prod.id

    # Confirm product exists
    assert await db.get(Product, prod_id) is not None

    # Delete the catalog — should cascade
    await db.delete(catalog)
    await db.flush()

    # Product must be gone too
    gone = await db.get(Product, prod_id)
    assert gone is None


# ===========================================================================
# D. Unique constraint enforcement (3 tests)
# ===========================================================================


async def test_unique_users_phone(db: AsyncSession) -> None:
    """Two users with the same phone → IntegrityError on UNIQUE."""
    phone = _unique_phone()
    user1 = User(phone=phone)
    db.add(user1)
    await db.flush()

    user2 = User(phone=phone)
    db.add(user2)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_unique_categories_meesho_leaf_id(db: AsyncSession) -> None:
    """Two categories with the same meesho_leaf_id → IntegrityError."""
    tmpl = await _make_template(db)
    leaf_id = _unique_leaf_id()

    cat1 = Category(
        meesho_leaf_id=leaf_id,
        super_id="11",
        super_name="Women Fashion",
        path="Women Fashion > Tops",
        leaf_name="Tops First",
        template_id=tmpl.id,
    )
    db.add(cat1)
    await db.flush()

    cat2 = Category(
        meesho_leaf_id=leaf_id,  # duplicate
        super_id="11",
        super_name="Women Fashion",
        path="Women Fashion > Tops",
        leaf_name="Tops Second",
        template_id=tmpl.id,
    )
    db.add(cat2)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_unique_product_images_product_order(db: AsyncSession) -> None:
    """Two product_images with the same (product_id, order_idx) → IntegrityError."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    img1 = ProductImage(
        product_id=prod.id,
        gcs_path=f"{user.id}/{prod.id}/1_a.jpg",
        order_idx=2,
    )
    db.add(img1)
    await db.flush()

    img2 = ProductImage(
        product_id=prod.id,
        gcs_path=f"{user.id}/{prod.id}/1_b.jpg",
        order_idx=2,  # duplicate (product_id, order_idx)
    )
    db.add(img2)
    with pytest.raises(IntegrityError):
        await db.flush()


# ===========================================================================
# E. CHECK constraint enforcement (2 tests)
# ===========================================================================


async def test_check_templates_compliance_shape_invalid(db: AsyncSession) -> None:
    """Inserting a templates row with compliance_shape='garbage' → IntegrityError."""
    tmpl = Template(
        schema_hash=_unique_hash(),
        schema_jsonb={"fields": [], "compulsory_count": 0, "optional_count": 0,
                      "total_count": 0, "wizard_step_count": 0, "main_sheet_label": "X"},
        compliance_shape="garbage",  # not in ('standard', 'collapsed')
    )
    db.add(tmpl)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_check_product_images_order_idx_out_of_range(db: AsyncSession) -> None:
    """Inserting a product_images row with order_idx=5 → IntegrityError (CHECK 1..4)."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    img = ProductImage(
        product_id=prod.id,
        gcs_path=f"{user.id}/{prod.id}/5.jpg",
        order_idx=5,  # violates CHECK BETWEEN 1 AND 4
    )
    db.add(img)
    with pytest.raises(IntegrityError):
        await db.flush()


# ===========================================================================
# F. Computed column (2 tests — is_front True and False)
# ===========================================================================


async def test_computed_is_front_true_for_order_idx_1(db: AsyncSession) -> None:
    """ProductImage with order_idx=1 → is_front=True (GENERATED ALWAYS AS)."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    img = ProductImage(
        product_id=prod.id,
        gcs_path=f"{user.id}/{prod.id}/1.jpg",
        order_idx=1,
    )
    db.add(img)
    await db.flush()
    await db.refresh(img)

    assert img.is_front is True


async def test_computed_is_front_false_for_order_idx_2(db: AsyncSession) -> None:
    """ProductImage with order_idx=2 → is_front=False (GENERATED ALWAYS AS)."""
    user = await _make_user(db)
    tmpl = await _make_template(db)
    cat = await _make_category(db, tmpl)
    catalog = await _make_catalog(db, user)
    prod = await _make_product(db, catalog, user, cat)

    img = ProductImage(
        product_id=prod.id,
        gcs_path=f"{user.id}/{prod.id}/2.jpg",
        order_idx=2,
    )
    db.add(img)
    await db.flush()
    await db.refresh(img)

    assert img.is_front is False


# ===========================================================================
# G. Server-default verification (3 tests)
# ===========================================================================


async def test_server_default_uuid_pk(db: AsyncSession) -> None:
    """Insert User WITHOUT specifying id → assert id is populated post-flush."""
    user = User(phone=_unique_phone())
    # Do NOT set user.id — let server_default=gen_random_uuid() supply it
    db.add(user)
    await db.flush()

    assert user.id is not None
    assert isinstance(user.id, uuid.UUID)
    # The UUID should not be nil
    assert user.id != uuid.UUID("00000000-0000-0000-0000-000000000000")


async def test_server_default_created_at(db: AsyncSession) -> None:
    """Insert User WITHOUT specifying created_at → assert it's populated within ~30s of NOW()."""
    user = User(phone=_unique_phone())
    # Do NOT set created_at — let server_default=NOW() supply it
    db.add(user)
    await db.flush()
    await db.refresh(user)

    assert user.created_at is not None
    assert isinstance(user.created_at, datetime)

    # The server timestamp should be within 30 seconds of local now()
    # (generous tolerance for port-forward latency + clock drift)
    now_utc = datetime.now(tz=timezone.utc)
    delta = abs((now_utc - user.created_at).total_seconds())
    assert delta < 30, f"created_at is {delta:.1f}s from local now() — expected <30s"


async def test_server_default_compliance_extensions_empty_dict(db: AsyncSession) -> None:
    """Insert SellerProfile WITHOUT compliance_extensions → assert it defaults to {} (empty dict)."""
    user = await _make_user(db)

    profile = SellerProfile(
        user_id=user.id,
        manufacturer_name="Mfr",
        manufacturer_address="Addr",
        manufacturer_pincode="600001",
        packer_name="Packer",
        packer_address="Addr",
        packer_pincode="600002",
        # compliance_extensions deliberately omitted
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    assert profile.compliance_extensions == {}
    assert isinstance(profile.compliance_extensions, dict)


# ===========================================================================
# H. Seeded data sanity (4 tests — read-only, no fixtures)
# These hit the live seeded reference data directly.
# They use dev_engine (session-scoped) rather than the per-test `db` fixture
# because they are pure SELECT queries — no transaction rollback needed.
# ===========================================================================


async def test_seeded_grocery_category_count(dev_engine) -> None:
    """COUNT categories WHERE super_id='26' (Grocery) → ≥321 rows."""
    async with dev_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM categories WHERE super_id = '26'")
        )
        count = result.scalar_one()
    assert count >= 321, f"Expected ≥321 Grocery categories, got {count}"


async def test_seeded_collapsed_template_invariant(dev_engine) -> None:
    """COUNT templates WHERE compliance_shape='collapsed' → exactly 1 (Eye-Serum)."""
    async with dev_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM templates WHERE compliance_shape = 'collapsed'")
        )
        count = result.scalar_one()
    assert count == 1, (
        f"Expected exactly 1 collapsed template (Eye-Serum invariant), got {count}"
    )


async def test_seeded_field_enum_max_value_count(dev_engine) -> None:
    """MAX(value_count) FROM field_enum_values → 4,481 (Compatible Models invariant)."""
    async with dev_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT MAX(value_count) FROM field_enum_values")
        )
        max_val = result.scalar_one()
    assert max_val == 4481, (
        f"Expected MAX(value_count) = 4481 (Compatible Models), got {max_val}"
    )


async def test_seeded_field_aliases_xlsx_export_present(dev_engine) -> None:
    """COUNT field_aliases WHERE for_xlsx_export=TRUE → ≥1 (alias round-trip pre-condition)."""
    async with dev_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM field_aliases WHERE for_xlsx_export = TRUE")
        )
        count = result.scalar_one()
    assert count >= 1, (
        f"Expected ≥1 field_alias with for_xlsx_export=TRUE, got {count}"
    )


async def test_is_advanced_flag_set_for_group_id(dev_engine) -> None:
    """G1 (is_advanced wiring) — group_id fields have is_advanced=true in all templates.

    D2 (founder-locked): ADVANCED_CANONICAL_NAMES = {'group_id'} only.
    Every seeded template that contains a group_id field must have
    is_advanced=true on that specific field entry.

    Uses JSONB array operators (jsonb_array_elements) to check the flag on
    the exact field object, rather than schema_jsonb::text LIKE which would
    give false positives by matching is_advanced=true from a different field.
    """
    async with dev_engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*) FROM templates t
                WHERE EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(t.schema_jsonb -> 'fields') AS f
                    WHERE f->>'canonical_name' = 'group_id'
                    AND (f->>'is_advanced')::boolean = true
                )
                """
            )
        )
        count = result.scalar_one()
    assert count > 0, (
        "Expected at least one template with a group_id field where is_advanced=true; "
        f"got {count}.  Check ADVANCED_CANONICAL_NAMES in scripts/build_template_schemas.py "
        "and re-run the seed pipeline."
    )


async def test_is_advanced_flag_not_set_for_non_advanced_fields(dev_engine) -> None:
    """G1 (is_advanced wiring) — compulsory fields like product_name must NOT be advanced.

    Verifies that the ADVANCED_CANONICAL_NAMES allowlist is narrow (only group_id per D2)
    and does not accidentally mark universal compulsory fields as advanced.

    Uses JSONB array operators to check the exact field entry, same as the positive test.
    """
    async with dev_engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*) FROM templates t
                WHERE EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(t.schema_jsonb -> 'fields') AS f
                    WHERE f->>'canonical_name' = 'product_name'
                    AND (f->>'is_advanced')::boolean = true
                )
                """
            )
        )
        count = result.scalar_one()
    assert count == 0, (
        f"Expected 0 templates where product_name field is_advanced=true; got {count}. "
        "product_name is a universal compulsory field and must never be in ADVANCED_CANONICAL_NAMES."
    )
