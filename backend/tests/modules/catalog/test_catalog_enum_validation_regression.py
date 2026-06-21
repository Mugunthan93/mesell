"""Regression — product-field validation reads the FLAT §5A.C wire DTO.

Root cause (catalog-422-fix): ``patch_product`` / ``autofill_product`` fed the
RICH ``fetch_schema`` envelope (export-only — does NOT carry the derived
``enum_resolver`` key) to ``_resolve_allowed_enums``. With no ``enum_resolver``
every dropdown defaulted to ``"static"`` + ``[]``, ``get_field_enum`` was never
called, and a VALID category-enum value (e.g. ``"3.5"``) was rejected 422.

Fix: validation now reads ``fetch_schema_dto`` (the FLAT shape that derives
``enum_resolver`` / ``enum_values`` and is what the public ``/field-enum``
agrees with), and the ``category`` branch of ``_validate_single_field``
fails open when no allowed set was resolved.

These tests run against the ephemeral test DB (top-level ``db`` fixture; reset
per test) and use the catalog conftest's Beauty / Eye-Serum fixtures.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.modules.catalog import service as catalog_service
from app.modules.catalog.exceptions import ValidationFailedError
from app.modules.catalog.schemas import PatchProductRequest
from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.product import Product as ProductORM


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ── schema with a category-resolved dropdown (``size_in_ltrs``) ─────────────
def _schema_with_size_dropdown() -> dict:
    """RICH §5A.B envelope with one category-resolved dropdown.

    ``size_in_ltrs`` is a ``dropdown`` with NO inline ``enum_codes_map`` → the
    DTO mapper derives ``enum_resolver="category"`` so the validator must hit
    ``get_field_enum`` (the bug skipped that call entirely).
    """
    return {
        "fields": [
            {
                "name": "Product Name",
                "canonical_name": "product_name",
                "marker": "compulsory",
                "data_type": "text",
                "primitive": "text_short",
                "help_text": "Title.",
                "is_advanced": False,
                "enum_resolver": None,
                "validation_message_ids": [],
            },
            {
                "name": "Size (litres)",
                "canonical_name": "size_in_ltrs",
                "marker": "compulsory",
                "data_type": "dropdown",
                "primitive": "dropdown_category",
                "help_text": "Pick a size.",
                "is_advanced": False,
                # NOTE: rich at-rest field with NO enum_codes_map → the DTO
                # mapper derives enum_resolver="category".
            },
        ],
        "compulsory_count": 2,
        "optional_count": 0,
        "total_count": 2,
        "wizard_step_count": 1,
        "main_sheet_label": "Size Test",
        "compliance_shape": "collapsed",
        "super_id": "19",
        "path": "Beauty > Skin Care > Eye-Serum",
    }


def _field_enum_with_three_point_five() -> dict:
    """``get_field_enum`` payload whose canonical set includes ``"3.5"``."""
    return {
        "enum_entries": [
            {"canonical": "1.0", "meesho": "1.0", "labels": {"en": "1 L"}},
            {"canonical": "3.5", "meesho": "3.5", "labels": {"en": "3.5 L"}},
            {"canonical": "5.0", "meesho": "5.0", "labels": {"en": "5 L"}},
        ],
        "total": 3,
        "truncated": False,
    }


async def _seed_catalog(db, user_id):
    catalog = CatalogORM(user_id=user_id, name="Test Catalog", status="draft")
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _seed_product(db, user_id, catalog_id, category_id):
    product = ProductORM(
        user_id=user_id,
        catalog_id=catalog_id,
        category_id=category_id,
        name="Test Product",
        status="draft",
        fields_jsonb={},
        ai_suggestions_jsonb={},
        deleted_at=None,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


def _patch_schema_and_enum(monkeypatch, *, enum_payload: dict) -> None:
    """Monkeypatch the category service so ``patch_product`` sees our schema.

    Patches BOTH ``fetch_schema`` (the source ``fetch_schema_dto`` wraps) and
    ``get_field_enum``. ``fetch_schema_dto`` itself is left REAL so the test
    exercises the genuine read-time DTO projection.
    """
    from app.modules.category import service as category_service_mod

    schema = _schema_with_size_dropdown()

    async def _fake_fetch_schema(category_id, db=None, **_kw):
        return schema

    async def _fake_get_field_enum(category_id, field_name, db=None, **_kw):
        return enum_payload

    monkeypatch.setattr(category_service_mod, "fetch_schema", _fake_fetch_schema)
    monkeypatch.setattr(category_service_mod, "get_field_enum", _fake_get_field_enum)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD-BEARING regression — valid category-enum value is accepted (was 422).
# ─────────────────────────────────────────────────────────────────────────────
class TestCategoryEnumValueAccepted:
    async def test_valid_category_enum_value_persists_200(
        self, db, user, beauty_category, beauty_profile, monkeypatch, use_live_valkey
    ):
        """PATCH ``size_in_ltrs="3.5"`` → success + persisted (NOT 422)."""
        _patch_schema_and_enum(
            monkeypatch, enum_payload=_field_enum_with_three_point_five()
        )
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)

        req = PatchProductRequest(fields={"size_in_ltrs": "3.5"})
        # Must NOT raise — the bug raised ValidationFailedError here.
        result = await catalog_service.patch_product(
            user.id, product.id, req, is_autosave=False, db=db
        )
        assert result is not None

        row = (
            await db.execute(select(ProductORM).where(ProductORM.id == product.id))
        ).scalar_one()
        assert row.fields_jsonb["size_in_ltrs"] == "3.5"

    async def test_out_of_set_value_still_rejected_422(
        self, db, user, beauty_category, beauty_profile, monkeypatch, use_live_valkey
    ):
        """A value outside a RESOLVED non-empty set still raises 422."""
        _patch_schema_and_enum(
            monkeypatch, enum_payload=_field_enum_with_three_point_five()
        )
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)

        req = PatchProductRequest(fields={"size_in_ltrs": "9.9"})
        with pytest.raises(ValidationFailedError) as exc:
            await catalog_service.patch_product(
                user.id, product.id, req, is_autosave=False, db=db
            )
        assert exc.value.validation_message_id == (
            "validation.size_in_ltrs.invalid_enum_value"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fail-open — an EMPTY resolved set must never falsely reject.
# ─────────────────────────────────────────────────────────────────────────────
class TestCategoryEnumFailOpen:
    async def test_empty_enum_entries_fails_open(
        self, db, user, beauty_category, beauty_profile, monkeypatch, use_live_valkey
    ):
        """``get_field_enum`` returns no entries → any value passes (no 422).

        This guards the cold-cache / unseeded-field_enum_values path that the
        original bug turned into a false reject.
        """
        empty_payload = {"enum_entries": [], "total": 0, "truncated": False}
        _patch_schema_and_enum(monkeypatch, enum_payload=empty_payload)
        catalog = await _seed_catalog(db, user.id)
        product = await _seed_product(db, user.id, catalog.id, beauty_category.id)

        req = PatchProductRequest(fields={"size_in_ltrs": "any-value-at-all"})
        result = await catalog_service.patch_product(
            user.id, product.id, req, is_autosave=False, db=db
        )
        assert result is not None
        row = (
            await db.execute(select(ProductORM).where(ProductORM.id == product.id))
        ).scalar_one()
        assert row.fields_jsonb["size_in_ltrs"] == "any-value-at-all"


# ─────────────────────────────────────────────────────────────────────────────
# DTO-source guard — validation enums match ``fetch_schema_dto``, not the rich
# envelope (guards against a revert that re-reads the rich shape).
# ─────────────────────────────────────────────────────────────────────────────
class TestValidationReadsFlatDto:
    async def test_resolved_enums_equivalent_to_fetch_schema_dto(
        self, db, user, beauty_category, beauty_profile, monkeypatch, use_live_valkey
    ):
        """``_resolve_allowed_enums`` over the DTO surfaces ``size_in_ltrs``.

        The rich envelope omits ``enum_resolver`` → ``_resolve_allowed_enums``
        would yield ``{}`` (the bug). Over the FLAT DTO it derives
        ``enum_resolver="category"`` and resolves the canonical set. Asserting
        equivalence to ``fetch_schema_dto`` pins the fix to the flat source.
        """
        from app.modules.category import service as category_service_mod

        _patch_schema_and_enum(
            monkeypatch, enum_payload=_field_enum_with_three_point_five()
        )

        dto = await category_service_mod.fetch_schema_dto(
            beauty_category.id, db=db
        )
        # The DTO derives the category resolver for size_in_ltrs.
        size_field = next(
            f for f in dto["fields"] if f["canonical_name"] == "size_in_ltrs"
        )
        assert size_field["enum_resolver"] == "category"

        resolved = await catalog_service._resolve_allowed_enums(
            dto, beauty_category.id, db
        )
        assert resolved.get("size_in_ltrs") == ["1.0", "3.5", "5.0"]

        # Sanity: the RICH envelope omits ``enum_resolver`` so
        # ``_resolve_allowed_enums`` defaults the dropdown to "static" and reads
        # the absent ``enum_values`` → an EMPTY allowed set. That empty set is
        # exactly what made the OLD fail-shut validator reject the valid "3.5"
        # (and is why the fix both switches to the DTO source AND fails open).
        rich = await category_service_mod.fetch_schema(beauty_category.id, db=db)
        rich_resolved = await catalog_service._resolve_allowed_enums(
            rich, beauty_category.id, db
        )
        assert rich_resolved.get("size_in_ltrs") == []


# ── QA Wave 1 — P1.10: size_in_ltrs canonical enum must not produce 422 ───────
class TestSizeInLtrsEnumRegression:
    """Regression guard for the 2026-06-17 finding: PATCH autosave with
    ``size_in_ltrs:"3.5"`` (a valid canonical value in cat 46677c24) was
    incorrectly rejected with 422 validation.size_in_ltrs.invalid_enum_value.

    The root cause was a cache divergence / key-casing mismatch in
    ``_resolve_allowed_enums``.  This test pins the fix at the service layer.
    """

    async def test_3_5_is_in_canonical_enum_list(self, monkeypatch):
        """``"3.5"`` must pass ``_validate_single_field`` when it is a valid canonical.

        Signature: _validate_single_field(canonical_name, value, spec, category_enums)
        Returns None on pass, (validation_message_id, suffix) on failure.

        We call the validator with a dropdown/category spec and a
        ``category_enums`` dict that includes "3.5" in the size_in_ltrs set.
        This mirrors what ``patch_product`` builds from ``_resolve_allowed_enums``.
        """
        from app.modules.catalog import service as catalog_service

        field_name = "size_in_ltrs"
        value = "3.5"

        # Minimal field spec for a dropdown with enum_resolver="category"
        spec = {
            "data_type": "dropdown",
            "primitive": "dropdown",
            "enum_resolver": "category",
            "enum_values": None,
        }

        # category_enums: what _resolve_allowed_enums returns for this category.
        # "3.5" must be present — it IS a valid canonical per the DB fixture.
        category_enums = {
            field_name: ["1.5", "2.0", "3.5", "5.0", "7.5"]
        }

        error = catalog_service._validate_single_field(
            field_name, value, spec, category_enums
        )
        assert error is None, (
            f"_validate_single_field rejected valid enum '3.5' for "
            f"size_in_ltrs; returned: {error!r}"
        )
