"""Unit + integration tests for the cross-field dependency rule engine.

The engine lives in ``app.modules.catalog.service``
(``_predicate_met`` / ``_evaluate_dependency_rules`` / ``_applicable_rules``)
and the /schema FE projection lives in ``app.modules.category.service``
(``_project_dependency_rules``).  Both load the SAME single-source-of-truth
``app/data/field_dependency_rules.json``.

Unit tests need no DB.  The integration tests mock every DB-touching call on
the catalog service (ownership / schema / enums / repository) so they assert
the 422-vs-200 contract without a live database.
"""

from __future__ import annotations

import re
from uuid import uuid4

import pytest

from app.i18n.messages_en import VALIDATION_MESSAGES
from app.modules.catalog import service as catalog_service
from app.modules.catalog.exceptions import ValidationFailedError
from app.modules.category import service as category_service

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — _predicate_met: each operator (eq, in, contains, any)
# ─────────────────────────────────────────────────────────────────────────────
class TestPredicateOperators:
    def test_eq_true(self):
        rule = {"type": "value_conditional", "if_field": "gender",
                "if_operator": "eq", "if_value": "Kids"}
        assert catalog_service._predicate_met(rule, {"gender": "Kids"}) is True

    def test_eq_false(self):
        rule = {"type": "value_conditional", "if_field": "gender",
                "if_operator": "eq", "if_value": "Kids"}
        assert catalog_service._predicate_met(rule, {"gender": "Men"}) is False

    def test_in_true(self):
        rule = {"type": "value_conditional", "if_field": "product_type",
                "if_operator": "in", "if_value": ["food", "snack"]}
        assert catalog_service._predicate_met(rule, {"product_type": "snack"}) is True

    def test_in_false(self):
        rule = {"type": "value_conditional", "if_field": "product_type",
                "if_operator": "in", "if_value": ["food", "snack"]}
        assert catalog_service._predicate_met(rule, {"product_type": "shirt"}) is False

    def test_in_value_not_a_list_is_false(self):
        rule = {"type": "value_conditional", "if_field": "product_type",
                "if_operator": "in", "if_value": "food"}
        assert catalog_service._predicate_met(rule, {"product_type": "food"}) is False

    def test_contains_substring_in_string(self):
        rule = {"type": "value_conditional", "if_field": "product_type",
                "if_operator": "contains", "if_value": "food"}
        assert catalog_service._predicate_met(rule, {"product_type": "Dog Food Pack"}) is True

    def test_contains_membership_in_list(self):
        rule = {"type": "value_conditional", "if_field": "tags",
                "if_operator": "contains", "if_value": "food"}
        assert catalog_service._predicate_met(rule, {"tags": ["pet", "food"]}) is True

    def test_contains_false(self):
        rule = {"type": "value_conditional", "if_field": "product_type",
                "if_operator": "contains", "if_value": "food"}
        assert catalog_service._predicate_met(rule, {"product_type": "Shirt"}) is False

    def test_any_truthy_string(self):
        rule = {"type": "value_conditional", "if_field": "license_registration_number",
                "if_operator": "any", "if_value": None}
        assert catalog_service._predicate_met(rule, {"license_registration_number": "AB12"}) is True

    def test_any_empty_string_false(self):
        rule = {"type": "value_conditional", "if_field": "license_registration_number",
                "if_operator": "any", "if_value": None}
        assert catalog_service._predicate_met(rule, {"license_registration_number": "  "}) is False

    def test_any_none_false(self):
        rule = {"type": "value_conditional", "if_field": "license_registration_number",
                "if_operator": "any", "if_value": None}
        assert catalog_service._predicate_met(rule, {}) is False

    def test_unknown_operator_false(self):
        rule = {"type": "value_conditional", "if_field": "x",
                "if_operator": "nope", "if_value": "y"}
        assert catalog_service._predicate_met(rule, {"x": "y"}) is False

    def test_malformed_value_conditional_no_if_field_false(self):
        rule = {"type": "value_conditional", "if_field": None,
                "if_operator": "eq", "if_value": "y"}
        assert catalog_service._predicate_met(rule, {}) is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — category_required fires unconditionally
# ─────────────────────────────────────────────────────────────────────────────
def test_category_required_predicate_always_true():
    rule = {"type": "category_required", "if_field": None,
            "if_operator": None, "if_value": None}
    assert catalog_service._predicate_met(rule, {}) is True
    assert catalog_service._predicate_met(rule, {"anything": "value"}) is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — value_conditional fires only when predicate met
# ─────────────────────────────────────────────────────────────────────────────
def test_value_conditional_fires_only_when_predicate_met():
    schema_index = {"fssai_license_number": {"canonical_name": "fssai_license_number"},
                    "product_type": {"canonical_name": "product_type"}}
    # predicate met (product_type=food) + target empty → hard violation
    hard, _soft = catalog_service._evaluate_dependency_rules(
        super_id=None,
        schema_index=schema_index,
        merged_fields={"product_type": "food"},
        enforce_required=True,
    )
    assert any(mid == "validation.cross_field.fssai_foodtype" for mid, _ in hard)

    # predicate NOT met (product_type=shirt) → no fssai_foodtype violation
    hard2, _soft2 = catalog_service._evaluate_dependency_rules(
        super_id=None,
        schema_index=schema_index,
        merged_fields={"product_type": "shirt"},
        enforce_required=True,
    )
    assert not any(mid == "validation.cross_field.fssai_foodtype" for mid, _ in hard2)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — target_field not in schema → rule is inert (skipped)
# ─────────────────────────────────────────────────────────────────────────────
def test_rule_inert_when_target_field_not_in_schema():
    # Universal hard rule country_origin targets country_of_origin; if that
    # field is not in the schema the rule is skipped entirely.
    hard, soft = catalog_service._evaluate_dependency_rules(
        super_id=None,
        schema_index={"product_type": {"canonical_name": "product_type"}},
        merged_fields={},
        enforce_required=True,
    )
    assert not any(mid == "validation.cross_field.country_origin" for mid, _ in hard)
    assert all(r["id"] != "country_origin" for r in soft)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — enforce_required=False → hard violation becomes soft advisory
# ─────────────────────────────────────────────────────────────────────────────
def test_enforce_required_false_demotes_hard_to_soft():
    schema_index = {"country_of_origin": {"canonical_name": "country_of_origin"}}
    hard, soft = catalog_service._evaluate_dependency_rules(
        super_id=None,
        schema_index=schema_index,
        merged_fields={},  # country_of_origin empty
        enforce_required=False,  # autosave
    )
    assert hard == []  # never blocks autosave
    assert any(r["id"] == "country_origin" for r in soft)


def test_enforce_required_true_yields_hard():
    schema_index = {"country_of_origin": {"canonical_name": "country_of_origin"}}
    hard, _soft = catalog_service._evaluate_dependency_rules(
        super_id=None,
        schema_index=schema_index,
        merged_fields={},
        enforce_required=True,
    )
    assert any(mid == "validation.cross_field.country_origin" for mid, _ in hard)


def test_soft_severity_rule_never_blocks_even_when_required():
    # nonreturn_reason is a soft rule: is_returnable=No → target empty.
    schema_index = {"non_returnable_reason": {"canonical_name": "non_returnable_reason"},
                    "is_returnable": {"canonical_name": "is_returnable"}}
    hard, soft = catalog_service._evaluate_dependency_rules(
        super_id=None,
        schema_index=schema_index,
        merged_fields={"is_returnable": "No"},
        enforce_required=True,
    )
    assert not any(mid == "validation.cross_field.nonreturn_reason" for mid, _ in hard)
    assert any(r["id"] == "nonreturn_reason" for r in soft)


def test_filled_target_produces_no_violation():
    schema_index = {"country_of_origin": {"canonical_name": "country_of_origin"}}
    hard, soft = catalog_service._evaluate_dependency_rules(
        super_id=None,
        schema_index=schema_index,
        merged_fields={"country_of_origin": "India"},
        enforce_required=True,
    )
    assert hard == []
    assert soft == []


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — all rule ids dot-free and unique
# ─────────────────────────────────────────────────────────────────────────────
def test_rule_ids_unique_and_dot_free():
    rules = catalog_service._ALL_DEPENDENCY_RULES
    ids = [r["id"] for r in rules]
    assert len(ids) == 20
    assert len(ids) == len(set(ids)), "rule ids must be unique"
    assert all("." not in rid for rid in ids), "rule ids must be dot-free"
    # Each id is ONE i18n segment (snake_case, no dots) so the composed key
    # ``validation.cross_field.<id>`` is a valid §5A.H 3-segment id.
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", rid) for rid in ids)
    three_segment = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$")
    assert all(three_segment.match(f"validation.cross_field.{rid}") for rid in ids)


# ─────────────────────────────────────────────────────────────────────────────
# Test 7 — all validation.cross_field.{id} keys exist in VALIDATION_MESSAGES
# ─────────────────────────────────────────────────────────────────────────────
def test_all_cross_field_keys_registered():
    three_segment = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$")
    for rule in catalog_service._ALL_DEPENDENCY_RULES:
        key = f"validation.cross_field.{rule['id']}"
        assert key in VALIDATION_MESSAGES, f"missing i18n key {key}"
        assert VALIDATION_MESSAGES[key].strip(), f"blank message for {key}"
        assert three_segment.match(key), f"{key} not a valid 3-segment id"


def test_category_projection_loads_same_rule_set():
    # Both modules load the same JSON → same rule ids under "*".
    cat_universal = {r["id"] for r in category_service._RULES_BY_SUPER.get("*", [])}
    eng_universal = {r["id"] for r in catalog_service._RULES_BY_SUPER.get("*", [])}
    assert cat_universal == eng_universal


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests — mock the catalog service DB call sites
# ─────────────────────────────────────────────────────────────────────────────
class _FakeProductRow:
    def __init__(self, category_id, fields_jsonb=None, status="draft"):
        self.id = uuid4()
        self.user_id = uuid4()
        self.catalog_id = uuid4()
        self.category_id = category_id
        self.name = "Test Product"
        self.fields_jsonb = fields_jsonb or {}
        self.ai_suggestions_jsonb = {}
        self.status = status
        self.created_at = None
        self.updated_at = None
        self.deleted_at = None


class _PatchReq:
    def __init__(self, fields=None, status=None):
        self.fields = fields
        self.status = status


def _grocery_schema_dto():
    """Flat §5A.C wire schema for a Grocery-like category."""
    return {
        "fields": [
            {"canonical_name": "fssai_license_number", "name": "FSSAI License",
             "marker": "optional", "data_type": "text", "primitive": "text_short"},
            {"canonical_name": "product_name", "name": "Product Name",
             "marker": "compulsory", "data_type": "text", "primitive": "text_short"},
        ],
        "compulsory_count": 1,
        "optional_count": 1,
        "total_count": 2,
        "wizard_step_count": 3,
        "main_sheet_label": "Grocery",
        "compliance_shape": "standard",
    }


@pytest.fixture
def patch_mocks(monkeypatch):
    """Patch every DB-touching call on catalog.patch_product."""
    async def _own(*a, **k):
        return None

    async def _schema(*a, **k):
        return _grocery_schema_dto()

    async def _enums(*a, **k):
        return {}

    async def _super(*a, **k):
        return "26"  # Grocery super_id

    captured = {}

    async def _update_fields(db, user_id, product_id, fields):
        captured.setdefault("product").fields_jsonb.update(fields)
        return captured["product"]

    async def _update_status(db, user_id, product_id, status):
        captured["product"].status = status
        return captured["product"]

    async def _upsert_draft(*a, **k):
        return None

    monkeypatch.setattr(catalog_service, "assert_product_ownership", _own)
    monkeypatch.setattr(catalog_service.category_service, "fetch_schema_dto", _schema)
    monkeypatch.setattr(catalog_service, "_resolve_allowed_enums", _enums)
    monkeypatch.setattr(catalog_service.category_service, "get_super_id", _super)
    monkeypatch.setattr(catalog_service.catalog_repo, "update_fields_jsonb", _update_fields)
    monkeypatch.setattr(catalog_service.catalog_repo, "update_status", _update_status)
    monkeypatch.setattr(catalog_service.catalog_repo, "upsert_draft", _upsert_draft)
    return captured


@pytest.mark.asyncio
async def test_ready_grocery_missing_fssai_raises_422(patch_mocks, monkeypatch):
    cat_id = uuid4()
    row = _FakeProductRow(cat_id, fields_jsonb={"product_name": "Rice 5kg"})
    patch_mocks["product"] = row

    async def _find(*a, **k):
        return row

    monkeypatch.setattr(catalog_service.catalog_repo, "find_by_id", _find)

    req = _PatchReq(fields=None, status="ready")
    with pytest.raises(ValidationFailedError) as exc:
        await catalog_service.patch_product(
            user_id=uuid4(), product_id=row.id, request=req,
            is_autosave=False, db=object(),
        )
    assert exc.value.validation_message_id == "validation.cross_field.fssai_grocery"


@pytest.mark.asyncio
async def test_autosave_grocery_missing_fssai_passes_200(patch_mocks, monkeypatch):
    cat_id = uuid4()
    row = _FakeProductRow(cat_id, fields_jsonb={})
    patch_mocks["product"] = row

    async def _find(*a, **k):
        return row

    monkeypatch.setattr(catalog_service.catalog_repo, "find_by_id", _find)

    # Autosave: no status, sends a partial field — must NOT 422 on the
    # missing fssai cross-field rule.
    req = _PatchReq(fields={"product_name": "Rice 5kg"}, status=None)
    result = await catalog_service.patch_product(
        user_id=uuid4(), product_id=row.id, request=req,
        is_autosave=True, db=object(),
    )
    assert result is not None  # 200 — no raise


@pytest.mark.asyncio
async def test_ready_all_hard_filled_soft_empty_passes(patch_mocks, monkeypatch):
    cat_id = uuid4()
    # fssai filled (the only applicable hard cross-field rule for this schema),
    # all compulsory filled → ready transition succeeds.
    row = _FakeProductRow(
        cat_id,
        fields_jsonb={"product_name": "Rice 5kg", "fssai_license_number": "10012345"},
    )
    patch_mocks["product"] = row

    async def _find(*a, **k):
        return row

    monkeypatch.setattr(catalog_service.catalog_repo, "find_by_id", _find)

    req = _PatchReq(fields=None, status="ready")
    result = await catalog_service.patch_product(
        user_id=uuid4(), product_id=row.id, request=req,
        is_autosave=False, db=object(),
    )
    assert result is not None
    assert row.status == "ready"


# ─────────────────────────────────────────────────────────────────────────────
# Integration — /schema dependency_rules projection
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_schema_grocery_includes_fssai_rule(monkeypatch):
    cat_id = uuid4()

    async def _rich(*a, **k):
        # rich envelope mapped by _map_envelope_to_dto
        return {
            "fields": [
                {"canonical_name": "fssai_license_number",
                 "display_label": {"en": "FSSAI License"},
                 "marker": "optional", "data_type": "text", "primitive": "text_short"},
                {"canonical_name": "product_name",
                 "display_label": {"en": "Product Name"},
                 "marker": "compulsory", "data_type": "text", "primitive": "text_short"},
            ],
            "compulsory_count": 1, "optional_count": 1, "total_count": 2,
            "wizard_step_count": 3, "main_sheet_label": "Grocery",
            "compliance_shape": "standard",
        }

    async def _super(*a, **k):
        return "26"  # Grocery

    monkeypatch.setattr(category_service, "fetch_schema", _rich)
    monkeypatch.setattr(category_service, "get_super_id", _super)

    dto = await category_service.fetch_schema_dto(cat_id, db=object())
    rule_ids = {r["id"] for r in dto["dependency_rules"]}
    assert "fssai_grocery" in rule_ids
    fssai = next(r for r in dto["dependency_rules"] if r["id"] == "fssai_grocery")
    assert fssai["message_id"] == "validation.cross_field.fssai_grocery"
    assert fssai["target_field"] == "fssai_license_number"
    # FE projection must NOT leak the internal-only keys.
    assert "error_message" not in fssai
    assert "description" not in fssai
    assert "category_match" not in fssai
    # country_origin is universal but country_of_origin field is absent → not projected
    assert "country_origin" not in rule_ids


@pytest.mark.asyncio
async def test_schema_no_applicable_rules_yields_empty_list(monkeypatch):
    cat_id = uuid4()

    async def _rich(*a, **k):
        # A schema whose fields match NO rule target_field.
        return {
            "fields": [
                {"canonical_name": "product_name",
                 "display_label": {"en": "Product Name"},
                 "marker": "compulsory", "data_type": "text", "primitive": "text_short"},
            ],
            "compulsory_count": 1, "optional_count": 0, "total_count": 1,
            "wizard_step_count": 3, "main_sheet_label": "Misc",
            "compliance_shape": "standard",
        }

    async def _super(*a, **k):
        return "999"  # a super with no specific rules

    monkeypatch.setattr(category_service, "fetch_schema", _rich)
    monkeypatch.setattr(category_service, "get_super_id", _super)

    dto = await category_service.fetch_schema_dto(cat_id, db=object())
    assert dto["dependency_rules"] == []
