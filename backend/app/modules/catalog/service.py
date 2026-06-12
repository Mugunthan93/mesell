"""``catalog`` service layer — 10 PUBLIC async methods per §10.C
(LOCKED 2026-06-05).

Public surface
--------------

Route-internal (driven by §10.B.1 through §10.B.6):

* :func:`create_product`
* :func:`patch_product`
* :func:`autofill_product`
* :func:`get_preview`
* :func:`soft_delete`
* :func:`get_draft`

Cross-module surfaces (consumed via ``from app.modules.catalog import
service as catalog_service`` per §16):

* :func:`assert_product_ownership` — used by image / pricing /
  dashboard / export per §2.D + philosophy M6.
* :func:`get_product_for_export`   — used by export.service per §2.D.
* :func:`list_products`            — used by dashboard.service per §2.D.
* :func:`get_validation_summary`   — used by dashboard.service per §2.D.

Cross-module imports (strict allowlist per §3.G + §16)
------------------------------------------------------
This module imports ``from app.modules.category import service`` and
``from app.modules.customer import service`` ONLY.  It NEVER imports
``app.modules.category.repository`` or ``app.modules.customer.repository``.
It NEVER imports ``app.adapters.gemini`` — Auto-fill goes through
:func:`app.ai_ops.client.call_gemini` per §6A.C.

AI graceful-fallback contract (§6A.F + §10.B.3 step 6)
------------------------------------------------------
:func:`autofill_product` returns ``AutofillResponse(suggestions={},
applied={}, fallback_offered=True)`` with HTTP 200 — never 503 — when
any of the following occurs:

* :class:`BudgetExceededError` is raised through ``call_gemini``
  (V1.5 surface; V1 ``call_gemini`` catches internally + emits a
  fallback envelope).
* ``AIResponse.parsed.get("fallback_offered") is True`` — Layer-2
  retry exhaustion path inside ``call_gemini``.
* ``AIResponse.parsed.get("fields")`` is empty or malformed (defensive
  final safety net after the Layer-2 enum guardrail already ran).

DECISION FLAGS
--------------
§10-CATALOG-D1 — ``product_drafts`` wrapper applied (repository layer).
§10-CATALOG-D2 — Audit-mw 5-min coalescing now matches the real
    autosave surface ``PATCH /products/{id}`` (widened in
    ``core/middleware/audit_mw._is_autosave`` for the catalog-form slice;
    the §4.G doc amendment is the coordinator's follow-up).
§10-CATALOG-D3 — Canonical 3-segment ``validation_message_id`` IDs
    (already-shipped i18n entries) replace the §10.G 2-segment shorthand.
§10-CATALOG-D4 — Auto-fill ``confidence`` defaults to 0.9 for every
    field emitted by the ``autofill.v1`` prompt.  Rationale: the prompt
    instructs the model to OMIT fields it is not confident about —
    emission is the confidence signal; the constant is service-owned so
    prompt-engineer can refine the prompt independently.  NOTE: per the
    FOUNDER RULING 2026-06-11 (ai-autofill D1) there is NO auto-apply —
    confidence is a display/provenance signal only and never gates a
    write to ``products.fields_jsonb``.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_ops import client as ai_client
from app.ai_ops.budget_cap import BudgetExceededError
from app.ai_ops.client import AICallContext
from app.core.plan_guard import enforce_plan_limit
from app.modules.catalog import repository as catalog_repo
from app.modules.catalog.domain import (
    AutofillResponse,
    AutofillSuggestionInternal,
    ExportSnapshotInternal,
    PaginatedProductsInternal,
    Pagination,
    PreviewField,
    Product,
    ProductDraft,
    ProductPreviewInternal,
    ValidationSummaryInternal,
)
from app.modules.catalog.exceptions import (
    CatalogNotFoundError,
    ProductNotFoundError,
    ValidationFailedError,
)
from app.modules.category import service as category_service
from app.modules.customer import service as customer_service

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
_PLAN_FREE = "free"

# Confidence value stamped onto each AI-emitted autofill suggestion for
# provenance in ``ai_suggestions_jsonb``.  The auto-APPLY path was REMOVED
# per the FOUNDER RULING 2026-06-11 (ai-autofill D1) — this is now purely a
# display/provenance signal, never a gate for mutating accepted fields.
_DEFAULT_AUTOFILL_CONFIDENCE = 0.9

# Per §10.E AutofillRequest constraints — mirrored here for defensive
# service-level re-checks (the Pydantic layer already enforces).
_DESCRIPTION_MIN = 1
_DESCRIPTION_MAX = 2000


# ─────────────────────────────────────────────────────────────────────────────
# ORM → domain
# ─────────────────────────────────────────────────────────────────────────────
def _orm_to_domain(row) -> Product:
    """Convert a hydrated ``ProductORM`` to the frozen :class:`Product`."""
    return Product(
        id=row.id,
        user_id=row.user_id,
        catalog_id=row.catalog_id,
        category_id=row.category_id,
        name=row.name,
        status=row.status,
        fields=dict(row.fields_jsonb or {}),
        ai_suggestions=dict(row.ai_suggestions_jsonb or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Schema-driven validation (§5A.C + §5A.D)
# ─────────────────────────────────────────────────────────────────────────────
def _index_schema_fields(schema: dict) -> dict[str, dict]:
    """Return ``{canonical_name: field_spec}`` for O(1) lookup.

    The schema envelope (§5A.B) carries ``fields: list[field_spec]`` —
    fold to a dict so per-field validation does not re-scan the list per
    canonical name.
    """
    out: dict[str, dict] = {}
    for spec in schema.get("fields") or []:
        if not isinstance(spec, dict):
            continue
        canonical = spec.get("canonical_name") or spec.get("name")
        if not canonical:
            continue
        out[str(canonical)] = spec
    return out


def _validate_single_field(
    canonical_name: str,
    value: Any,
    spec: dict,
    category_enums: dict[str, list[str]] | None,
) -> tuple[str, str] | None:
    """Validate ``value`` against ``spec``.

    Returns ``(validation_message_id, suffix)`` on FAILURE, ``None`` on
    pass.  ``suffix`` is appended to the details list for multi-violation
    surfaces; it carries the canonical name + constraint for the caller.

    Dispatches by ``data_type`` + ``primitive`` (§5A.D):

    * ``text`` + ``text_short`` ≤ 100 chars; ``text_long`` ≤ 2000.
    * ``dropdown`` + ``enum_resolver="static"`` → inline ``enum_values``.
    * ``dropdown`` + ``enum_resolver="category"`` → ``category_enums[name]``.
    * ``number`` / ``integer`` / ``boolean`` / ``date`` / ``url`` —
        primitive coercion via Python's built-ins.

    Empty values (``None``, empty string) pass schema validation here —
    completeness is handled by :func:`_compute_completeness` when the
    request asks for ``status="ready"``.
    """
    if value is None or value == "":
        return None

    data_type = str(spec.get("data_type") or "text")
    primitive = str(spec.get("primitive") or "text_short")

    # ── text bounds ────────────────────────────────────────────────────────
    if data_type == "text" or primitive.startswith("text_"):
        if not isinstance(value, str):
            return (
                f"validation.{canonical_name}.invalid_type",
                f"{canonical_name}: expected string",
            )
        if primitive == "text_short" and len(value) > 100:
            return (
                f"validation.{canonical_name}.too_long",
                f"{canonical_name}: max 100 chars",
            )
        if primitive == "text_long" and len(value) > 2000:
            return (
                f"validation.{canonical_name}.too_long",
                f"{canonical_name}: max 2000 chars",
            )
        return None

    # ── dropdown / enum ────────────────────────────────────────────────────
    if data_type == "dropdown":
        resolver = str(spec.get("enum_resolver") or "static")
        if resolver == "static":
            allowed = spec.get("enum_values") or []
            if isinstance(allowed, list) and value not in allowed:
                return (
                    f"validation.{canonical_name}.invalid_enum_value",
                    f"{canonical_name}: not in static enum",
                )
            return None
        if resolver == "category":
            allowed = (category_enums or {}).get(canonical_name) or []
            if isinstance(allowed, list) and value not in allowed:
                return (
                    f"validation.{canonical_name}.invalid_enum_value",
                    f"{canonical_name}: not in category enum",
                )
            return None
        return None

    # ── number / integer / boolean / date / url ────────────────────────────
    if data_type == "number":
        try:
            float(value)
        except (TypeError, ValueError):
            return (
                f"validation.{canonical_name}.invalid_type",
                f"{canonical_name}: not a number",
            )
        return None
    if data_type == "integer":
        try:
            int(value)
        except (TypeError, ValueError):
            return (
                f"validation.{canonical_name}.invalid_type",
                f"{canonical_name}: not an integer",
            )
        return None
    if data_type == "boolean":
        if not isinstance(value, bool):
            return (
                f"validation.{canonical_name}.invalid_type",
                f"{canonical_name}: not a boolean",
            )
        return None
    if data_type == "date":
        if not isinstance(value, str):
            return (
                f"validation.{canonical_name}.invalid_type",
                f"{canonical_name}: expected ISO date string",
            )
        return None
    if data_type == "url":
        if not isinstance(value, str) or not (
            value.startswith("http://") or value.startswith("https://")
        ):
            return (
                f"validation.{canonical_name}.invalid_url",
                f"{canonical_name}: must start with http(s)://",
            )
        return None

    # Unknown data_type — accept defensively (the schema author owns the
    # data_type vocabulary; an unknown type means catalog hasn't been
    # updated for a new primitive).
    return None


async def _resolve_allowed_enums(
    schema: dict,
    category_id: UUID,
    db: AsyncSession,
) -> dict[str, list[str]]:
    """Build the per-field allowed-enum dict for §10.B.3 step 4.

    Static-enum fields are read inline from ``fields[*].enum_values`` per
    §5A.E; ``enum_resolver="category"`` fields are resolved through
    :func:`category.service.get_field_enum` per §9.C (cached read).
    """
    out: dict[str, list[str]] = {}
    for spec in schema.get("fields") or []:
        if not isinstance(spec, dict):
            continue
        if spec.get("data_type") != "dropdown":
            continue
        canonical = spec.get("canonical_name") or spec.get("name")
        if not canonical:
            continue
        resolver = str(spec.get("enum_resolver") or "static")
        if resolver == "static":
            values = spec.get("enum_values") or []
            if isinstance(values, list):
                out[str(canonical)] = [str(v) for v in values]
            continue
        if resolver == "category":
            try:
                payload = await category_service.get_field_enum(
                    category_id, str(canonical), db
                )
            except Exception as exc:  # noqa: BLE001 — Layer 1 input is best-effort
                logger.warning(
                    "catalog.service._resolve_allowed_enums: "
                    "get_field_enum(%s, %s) failed: %r",
                    category_id, canonical, exc,
                )
                continue
            entries = payload.get("enum_entries") or [] if isinstance(payload, dict) else []
            values = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                v = entry.get("canonical")
                if v is not None:
                    values.append(str(v))
            if values:
                out[str(canonical)] = values
    return out


def _compute_completeness(
    fields: dict[str, Any], schema: dict
) -> ValidationSummaryInternal:
    """Sum compulsory/optional filled vs total per the schema spec list.

    A field is "filled" if its value is not ``None`` and not empty
    string.  Marker convention per §5A.C is ``compulsory`` / ``optional``.
    """
    compulsory_total = 0
    compulsory_filled = 0
    optional_total = 0
    optional_filled = 0
    for spec in schema.get("fields") or []:
        if not isinstance(spec, dict):
            continue
        canonical = spec.get("canonical_name") or spec.get("name")
        if not canonical:
            continue
        marker = str(spec.get("marker") or "optional")
        value = fields.get(str(canonical))
        is_filled = value is not None and value != ""
        if marker == "compulsory":
            compulsory_total += 1
            if is_filled:
                compulsory_filled += 1
        else:
            optional_total += 1
            if is_filled:
                optional_filled += 1
    return ValidationSummaryInternal(
        product_id=UUID(int=0),  # placeholder — caller fills
        compulsory_filled=compulsory_filled,
        compulsory_total=compulsory_total,
        optional_filled=optional_filled,
        optional_total=optional_total,
        has_validation_errors=False,
        status="draft",
    )


# ─────────────────────────────────────────────────────────────────────────────
# §10.B.1 — create_product
# ─────────────────────────────────────────────────────────────────────────────
async def create_product(
    user_id: UUID,
    plan: str,
    request,  # CreateProductRequest — type-hint omitted to keep test mocks simple
    db: AsyncSession,
) -> Product:
    """Implement the §10.B.1 6-step flow.

    Locked sequence:
        1. plan_guard.enforce_plan_limit(product_count, +1) — fails fast 402.
        2. category.service.assert_category_exists — 404 on miss.
        3. customer.service.assert_eligible_for_super_id — 422 on miss.
        4. Catalog selection: existing-or-create.
        5. Repository.insert_product — defaults per §10.B.1.
        6. Commit owned by route's ``Depends(get_db)``.
        7. Return :class:`Product`.

    Per §10.B.1 audit posture, audit_mw emits ``catalog.product.created``
    on 2xx.
    """
    # Step 1 — plan_guard product_count cap (100 active per V1 free tier).
    await enforce_plan_limit(
        user_id, plan or _PLAN_FREE, "product_count", requested=1, db=db
    )

    # Step 2 — category existence gate (raises CategoryNotFoundError → 404).
    await category_service.assert_category_exists(request.category_id, db=db)

    # Step 3 — eligibility gate (raises ProfileIncompleteForCategoryError → 422).
    super_id = await _resolve_super_id_for_category(request.category_id, db)
    if super_id is not None:
        await customer_service.assert_eligible_for_super_id(
            user_id, super_id, db=db
        )

    # Step 4 — catalog selection.
    if request.catalog_id is None:
        default_name = _default_catalog_name(user_id)
        catalog = await catalog_repo.create_catalog(db, user_id, default_name)
    else:
        catalog = await catalog_repo.find_catalog_by_id(
            db, user_id, request.catalog_id
        )
        if catalog is None:
            raise CatalogNotFoundError()

    # Step 5 — insert product (draft, empty jsonbs).
    row = await catalog_repo.insert_product(
        db,
        user_id,
        catalog.id,
        request.category_id,
        request.name,
    )
    return _orm_to_domain(row)


def _default_catalog_name(user_id: UUID) -> str:
    """Return the locked default-catalog name per §10.B.1.

    Per spec: ``"{seller_phone_last4}-Drafts-{YYYYMMDD-HHMM}"``.  V1 has
    no convenient way to read the seller's phone from inside this
    function (it would force a DB read on the hot path) — substitute the
    user_id's last 4 hex chars so the name remains unique-per-session
    without an extra round-trip.  The display layer (frontend) may
    rewrite the prefix to the seller's phone after the fact; the backend
    stores what it can compute in O(1).

    DECISION FLAG §10-CATALOG-D5 — uses user_id-last-4 (not phone-last-4)
    to avoid a hot-path DB read; rename safe-defaults to "{prefix}-Drafts-{ts}"
    if master prefers a different shape.
    """
    short_id = str(user_id).replace("-", "")[-4:]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return f"{short_id}-Drafts-{ts}"


async def _resolve_super_id_for_category(
    category_id: UUID, db: AsyncSession
) -> str | None:
    """Look up ``super_id`` for a category by reading the schema cache.

    The §9 schema envelope is the cached source — ``schema["super_id"]``
    carries the parent grouping per §5A.B.  Returns ``None`` if absent
    (defensive — newly-seeded categories may not yet carry the field, in
    which case the eligibility check is skipped per §10 forward-compat).
    """
    try:
        schema = await category_service.fetch_schema(category_id, db=db)
    except Exception as exc:  # noqa: BLE001 — fetch_schema raises CategoryNotFoundError when missing
        raise exc
    if isinstance(schema, dict):
        super_id = schema.get("super_id")
        if super_id is not None:
            return str(super_id)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# §10.B.2 — patch_product
# ─────────────────────────────────────────────────────────────────────────────
async def patch_product(
    user_id: UUID,
    product_id: UUID,
    request,  # PatchProductRequest
    is_autosave: bool,
    db: AsyncSession,
) -> Product:
    """Implement the §10.B.2 9-step flow.

    1. assert_product_ownership.
    2. category.service.fetch_schema (cached).
    3. Per-field validation (§5A.C) — raises ValidationFailedError on miss.
    4. (V1: no special is_advanced handling beyond honour-the-wizard.)
    5. Repository.update_fields_jsonb — JSONB merge.
    6. If status="ready": completeness check + status transition.
    7. If is_autosave: repository.upsert_draft (wrapper applied).
    8. Commit owned by route's get_db.
    9. Return Product.
    """
    # Step 1 — ownership gate.
    await assert_product_ownership(product_id, user_id, db=db)

    # Step 2 — fetch the schema for the product's category.
    # We need the product row to read its category_id.  ``find_by_id`` was
    # already called inside ``assert_product_ownership``; re-call here to
    # keep the function side-effect-free.
    product_row = await catalog_repo.find_by_id(db, user_id, product_id)
    if product_row is None:
        raise ProductNotFoundError()

    schema = await category_service.fetch_schema(product_row.category_id, db=db)

    # Step 3 — per-field validation.
    patch_fields = request.fields or {}
    if patch_fields:
        schema_index = _index_schema_fields(schema)
        # Resolve allowed enums up front so the dropdown checks have data.
        allowed_enums = await _resolve_allowed_enums(
            schema, product_row.category_id, db
        )
        violations: list[tuple[str, str]] = []
        for canonical_name, value in patch_fields.items():
            spec = schema_index.get(str(canonical_name))
            if spec is None:
                violations.append(
                    (
                        "validation.fields.unknown_key",
                        f"{canonical_name}: not in schema",
                    )
                )
                continue
            violation = _validate_single_field(
                str(canonical_name), value, spec, allowed_enums
            )
            if violation is not None:
                violations.append(violation)
        if violations:
            first_id, _ = violations[0]
            details = [suffix for _id, suffix in violations]
            raise ValidationFailedError(
                validation_message_id=first_id,
                detail=f"Field validation failed: {details[0]}",
                details=details,
            )

    # Step 5 — JSONB merge.
    if patch_fields:
        product_row = await catalog_repo.update_fields_jsonb(
            db, user_id, product_id, patch_fields
        )

    # Step 6 — optional status transition.
    target_status = request.status
    if target_status == "ready":
        merged_fields = dict(product_row.fields_jsonb or {})
        completeness = _compute_completeness(merged_fields, schema)
        # Any compulsory missing → 422.
        if completeness.compulsory_filled < completeness.compulsory_total:
            raise ValidationFailedError(
                validation_message_id="validation.completeness.missing_compulsory",
                detail=(
                    f"{completeness.compulsory_total - completeness.compulsory_filled} "
                    "required field(s) still empty."
                ),
                details=[
                    f"missing_compulsory: "
                    f"{completeness.compulsory_total - completeness.compulsory_filled}"
                ],
            )
        product_row = await catalog_repo.update_status(
            db, user_id, product_id, "ready"
        )
    elif target_status == "draft" and product_row.status != "draft":
        product_row = await catalog_repo.update_status(
            db, user_id, product_id, "draft"
        )

    # Step 7 — autosave snapshot.
    if is_autosave:
        merged_fields = dict(product_row.fields_jsonb or {})
        await catalog_repo.upsert_draft(db, user_id, product_id, merged_fields)

    # Step 8 — commit owned by route.
    return _orm_to_domain(product_row)


# ─────────────────────────────────────────────────────────────────────────────
# §10.B.3 — autofill_product
# ─────────────────────────────────────────────────────────────────────────────
async def autofill_product(
    user_id: UUID,
    plan: str,
    product_id: UUID,
    request,  # AutofillRequest
    request_id: str,
    db: AsyncSession,
) -> AutofillResponse:
    """Implement the §10.B.3 11-step flow.

    Returns :class:`AutofillResponse` — ALWAYS HTTP 200 at the router.
    Budget exhaustion → fallback_offered=True (NOT 503), per §6A.F.
    """
    # Step 1 — ownership gate.
    await assert_product_ownership(product_id, user_id, db=db)

    # Defensive re-check of description bounds (router has the Pydantic
    # gate; service does NOT trust callers blindly).
    description = request.description or ""
    if not (_DESCRIPTION_MIN <= len(description) <= _DESCRIPTION_MAX):
        raise ValidationFailedError(
            validation_message_id="validation.description.too_short_or_long",
            detail="Description length out of range.",
            details=[f"description: len={len(description)}"],
        )

    # Step 2 — plan_guard ai_autofill_hourly (50/h/user).
    await enforce_plan_limit(
        user_id, plan or _PLAN_FREE, "ai_autofill_hourly", requested=1
    )

    # Step 3 — fetch the schema for the product's category.
    product_row = await catalog_repo.find_by_id(db, user_id, product_id)
    if product_row is None:
        raise ProductNotFoundError()
    schema = await category_service.fetch_schema(product_row.category_id, db=db)

    # Step 4 — build allowed_enums for §6A.E Layer-2 guardrail.
    allowed_enums = await _resolve_allowed_enums(
        schema, product_row.category_id, db
    )

    # Step 5 — call_gemini with workload=autofill.
    ctx = AICallContext(workload="autofill", user_id=user_id, trace_id=request_id)
    product_spec = _render_product_spec(
        description=description,
        existing_fields=dict(product_row.fields_jsonb or {}),
        fields_to_fill=request.fields_to_fill,
    )
    schema_summary = _render_schema_summary(
        schema, fields_to_fill=request.fields_to_fill
    )
    try:
        ai_response = await ai_client.call_gemini(
            ctx,
            "autofill.v1",
            prompt_vars={
                "product_spec": product_spec,
                "schema": schema_summary,
            },
            allowed_enums=allowed_enums,
        )
    except BudgetExceededError:
        # Step 6 — graceful fallback path A: V1.5 surface; today
        # call_gemini catches internally and returns AIResponse with
        # parsed.fallback_offered=True.  Mirrors §9 category precedent.
        logger.info(
            "catalog.autofill: BudgetExceededError surfaced — "
            "returning graceful fallback"
        )
        return AutofillResponse(suggestions={}, applied={}, fallback_offered=True)

    # Step 6 — graceful fallback path B: AIResponse.parsed signals fallback.
    parsed = ai_response.parsed if isinstance(ai_response.parsed, dict) else {}
    if parsed.get("fallback_offered") is True:
        return AutofillResponse(suggestions={}, applied={}, fallback_offered=True)

    # Step 7 — parse + threshold.
    raw_fields = parsed.get("fields")
    if not isinstance(raw_fields, dict) or not raw_fields:
        # Defensive final safety net — Layer 2 already retried; if we
        # still have nothing, offer fallback.
        return AutofillResponse(suggestions={}, applied={}, fallback_offered=True)

    # FOUNDER RULING 2026-06-11 (ai-autofill D1): NO auto-apply.  Autofill
    # writes ONLY to ``ai_suggestions_jsonb``; the user explicitly accepts
    # each value per §F4 yellow-highlight UX.  ``autofill_product`` MUST NEVER
    # mutate the product's accepted attribute fields directly — so every
    # ``applied`` flag is False and ``fields_jsonb`` is left untouched.  The
    # ``confidence`` signal is still emitted into the suggestion provenance.
    suggestions: dict[str, AutofillSuggestionInternal] = {}
    applied: dict[str, bool] = {}
    for canonical_name, value in raw_fields.items():
        if value is None or value == "":
            continue
        # If caller constrained fields_to_fill, reject keys outside the set.
        if request.fields_to_fill and canonical_name not in request.fields_to_fill:
            continue
        suggestion = AutofillSuggestionInternal(
            canonical_name=str(canonical_name),
            value=value,
            confidence=_DEFAULT_AUTOFILL_CONFIDENCE,
            source="ai",
        )
        suggestions[str(canonical_name)] = suggestion
        # Never auto-applied — the seller accepts each value in the UI.
        applied[str(canonical_name)] = False

    if not suggestions:
        return AutofillResponse(suggestions={}, applied={}, fallback_offered=True)

    # Step 8 — persist the FULL suggestions payload for provenance into
    # ``ai_suggestions_jsonb`` ONLY.  No write to ``fields_jsonb`` (no
    # auto-apply per the founder ruling above).  ``accepted`` is always
    # False here; the per-field accept transition is a separate user action.
    suggestions_persisted = {
        canonical: {
            "value": suggestion.value,
            "confidence": suggestion.confidence,
            "source": suggestion.source,
            "accepted": False,
        }
        for canonical, suggestion in suggestions.items()
    }
    await catalog_repo.update_ai_suggestions_jsonb(
        db, user_id, product_id, suggestions_persisted
    )

    # Step 10 — audit_mw emits catalog.autofill.invoked on route 2xx.
    # Step 11 — return.
    return AutofillResponse(
        suggestions=suggestions, applied=applied, fallback_offered=False
    )


def _render_product_spec(
    *,
    description: str,
    existing_fields: dict[str, Any],
    fields_to_fill: list[str] | None,
) -> str:
    """Render the ``{{product_spec}}`` template variable.

    The prompt expects free-text description PLUS the already-filled
    fields as key: value pairs so the model knows what NOT to overwrite.
    """
    lines: list[str] = [description.strip()]
    if existing_fields:
        lines.append("")
        lines.append("Already filled:")
        for k, v in sorted(existing_fields.items()):
            if v is None or v == "":
                continue
            lines.append(f"  {k}: {v}")
    if fields_to_fill:
        lines.append("")
        lines.append("Fill only these fields:")
        for k in fields_to_fill:
            lines.append(f"  - {k}")
    return "\n".join(lines)


def _render_schema_summary(
    schema: dict, fields_to_fill: list[str] | None
) -> str:
    """Render the ``{{schema}}`` template variable.

    Compact JSON-ish list of canonical fields with their type +
    constraints so the model can fill values that match.  Per
    `MVP_ARCH §5.2` the token budget for autofill assumes ~3,000 tokens
    of compressed schema — for V1 we emit a flat ``canonical: type``
    list which is well under that budget.
    """
    lines: list[str] = []
    for spec in schema.get("fields") or []:
        if not isinstance(spec, dict):
            continue
        canonical = spec.get("canonical_name") or spec.get("name")
        if not canonical:
            continue
        if fields_to_fill and str(canonical) not in fields_to_fill:
            continue
        dtype = spec.get("data_type") or "text"
        marker = spec.get("marker") or "optional"
        enum_values = spec.get("enum_values")
        line = f"- {canonical} ({dtype}, {marker})"
        if isinstance(enum_values, list) and enum_values:
            shown = ", ".join(str(v) for v in enum_values[:10])
            tail = "..." if len(enum_values) > 10 else ""
            line += f" allowed=[{shown}{tail}]"
        lines.append(line)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# §10.B.4 — get_preview
# ─────────────────────────────────────────────────────────────────────────────
async def get_preview(
    user_id: UUID,
    product_id: UUID,
    db: AsyncSession,
) -> ProductPreviewInternal:
    """Implement the §10.B.4 6-step flow.

    Compose the live preview from:
        * product fields + schema labels,
        * image URLs (via image.service.get_image_urls — V1 absent module
          returns empty list defensively),
        * compliance block from customer.service.get_compliance_block.
    """
    await assert_product_ownership(product_id, user_id, db=db)
    product_row = await catalog_repo.find_by_id(db, user_id, product_id)
    if product_row is None:
        raise ProductNotFoundError()

    schema = await category_service.fetch_schema(product_row.category_id, db=db)

    # Compose ordered preview fields with display labels per §5A.C.
    fields: list[PreviewField] = []
    for spec in schema.get("fields") or []:
        if not isinstance(spec, dict):
            continue
        canonical = spec.get("canonical_name") or spec.get("name")
        if not canonical:
            continue
        label = str(
            spec.get("name") or spec.get("display_label") or canonical
        )
        value = (product_row.fields_jsonb or {}).get(str(canonical))
        is_advanced = bool(spec.get("is_advanced", False))
        fields.append(
            PreviewField(
                canonical_name=str(canonical),
                display_label=label,
                value=value,
                is_advanced=is_advanced,
            )
        )

    # Image URLs — §11 image module may not yet be constructed; defensive
    # call via getattr keeps the catalog construction independent of §11.
    image_urls: tuple[str, ...] = ()
    try:
        from app.modules import image as _image_module  # noqa: F401 — defensive
        image_service = getattr(_image_module, "service", None)
        if image_service is not None and hasattr(image_service, "get_image_urls"):
            urls = await image_service.get_image_urls(product_id, user_id, db=db)
            if isinstance(urls, (list, tuple)):
                image_urls = tuple(str(u) for u in urls)
    except ImportError:
        pass  # §11 not yet constructed — return empty list.

    # Compliance block via customer.service.
    try:
        compliance_block = await customer_service.get_compliance_block(
            user_id, db=db
        )
        compliance = {
            "manufacturer_name": compliance_block.manufacturer_name,
            "manufacturer_address": compliance_block.manufacturer_address,
            "manufacturer_pincode": compliance_block.manufacturer_pincode,
            "packer_name": compliance_block.packer_name,
            "packer_address": compliance_block.packer_address,
            "packer_pincode": compliance_block.packer_pincode,
            "importer_name": compliance_block.importer_name,
            "importer_address": compliance_block.importer_address,
            "importer_pincode": compliance_block.importer_pincode,
            "country_of_origin": compliance_block.country_of_origin,
        }
    except Exception as exc:  # noqa: BLE001 — preview tolerates missing profile
        logger.info(
            "catalog.preview: get_compliance_block fallback (missing profile): %r",
            exc,
        )
        compliance = {}

    category_path = str(schema.get("category_path") or schema.get("path") or "")

    return ProductPreviewInternal(
        id=product_row.id,
        name=product_row.name,
        category_path=category_path,
        fields=tuple(fields),
        image_urls=image_urls,
        compliance=compliance,
        status=product_row.status,
    )


# ─────────────────────────────────────────────────────────────────────────────
# §10.B.5 — soft_delete
# ─────────────────────────────────────────────────────────────────────────────
async def soft_delete(
    user_id: UUID,
    product_id: UUID,
    db: AsyncSession,
) -> None:
    """Soft-delete the product if owned + active.

    Idempotent on re-deletes of an already-deleted product (204; the
    soft-delete repo method's WHERE clause is a no-op for those).
    """
    # Look up including soft-deletes so a re-DELETE on an already-deleted
    # product 204s rather than 404s.  The ownership check still applies.
    row = await catalog_repo.find_by_id_including_deleted(db, user_id, product_id)
    if row is None:
        raise ProductNotFoundError()
    await catalog_repo.soft_delete_product(db, user_id, product_id)


# ─────────────────────────────────────────────────────────────────────────────
# §10.B.6 — get_draft
# ─────────────────────────────────────────────────────────────────────────────
async def get_draft(
    user_id: UUID,
    product_id: UUID,
    db: AsyncSession,
) -> ProductDraft | None:
    """Return the autosave snapshot or ``None`` (router maps None → 204)."""
    await assert_product_ownership(product_id, user_id, db=db)
    row = await catalog_repo.get_draft(db, user_id, product_id)
    if row is None:
        return None
    fields, count = catalog_repo._unwrap_draft_payload(row.draft_jsonb)
    return ProductDraft(
        user_id=row.user_id,
        product_id=row.product_id,
        fields=fields,
        last_updated=row.saved_at,
        autosave_count=count,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cross-module surfaces (§10.C)
# ─────────────────────────────────────────────────────────────────────────────
async def assert_product_ownership(
    product_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> None:
    """Structural enforcement of philosophy M6 — used by image / pricing /
    dashboard / export per §2.D + §16.

    Raises :class:`ProductNotFoundError` (404 / ``catalog.product.not_found``)
    for any of:

    * product does not exist,
    * product owned by another user,
    * product is soft-deleted (``deleted_at IS NOT NULL``).

    The repository's ``find_by_id`` collapses all three to ``None`` so
    callers cannot distinguish the cases — this is the §10 leak-protection
    rule.
    """
    row = await catalog_repo.find_by_id(db, user_id, product_id)
    if row is None:
        raise ProductNotFoundError()


async def get_product_for_export(
    product_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> ExportSnapshotInternal:
    """Cross-module call from ``export.service`` per §2.D.

    Returns a frozen snapshot — product row + ai_suggestions + image
    refs + last validation summary.  The export pipeline builds the
    XLSX from this fixed view; subsequent edits to the product do NOT
    leak into the in-flight export.
    """
    await assert_product_ownership(product_id, user_id, db=db)
    row = await catalog_repo.find_by_id(db, user_id, product_id)
    if row is None:
        raise ProductNotFoundError()

    schema = await category_service.fetch_schema(row.category_id, db=db)

    summary_internal = _compute_completeness(
        dict(row.fields_jsonb or {}), schema
    )
    summary = ValidationSummaryInternal(
        product_id=row.id,
        compulsory_filled=summary_internal.compulsory_filled,
        compulsory_total=summary_internal.compulsory_total,
        optional_filled=summary_internal.optional_filled,
        optional_total=summary_internal.optional_total,
        has_validation_errors=False,
        status=row.status,
    )

    # Image refs — §11 may not yet be constructed; defensive empty tuple.
    image_refs: tuple[str, ...] = ()
    try:
        from app.modules import image as _image_module  # noqa: F401 — defensive
        image_service = getattr(_image_module, "service", None)
        if image_service is not None and hasattr(image_service, "get_image_refs"):
            refs = await image_service.get_image_refs(product_id, user_id, db=db)
            if isinstance(refs, (list, tuple)):
                image_refs = tuple(str(r) for r in refs)
    except ImportError:
        pass

    return ExportSnapshotInternal(
        product_id=row.id,
        category_id=row.category_id,
        fields=dict(row.fields_jsonb or {}),
        ai_suggestions=dict(row.ai_suggestions_jsonb or {}),
        image_refs=image_refs,
        validation_summary=summary,
    )


async def list_products(
    user_id: UUID,
    pagination: Pagination,
    db: AsyncSession,
) -> PaginatedProductsInternal:
    """Cross-module call from ``dashboard.service`` per §2.D.

    Returns active products only; ordered most-recently-updated first.
    """
    rows, total = await catalog_repo.list_paginated(
        db, user_id, page=pagination.page, limit=pagination.limit
    )
    items = tuple(_orm_to_domain(r) for r in rows)
    return PaginatedProductsInternal(
        items=items,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )


async def get_validation_summary(
    user_id: UUID,
    product_id: UUID,
    db: AsyncSession,
) -> ValidationSummaryInternal:
    """Cross-module call from ``dashboard.service`` per §2.D.

    Recomputed against the schema each call — small N (the dashboard
    page-size is bounded).
    """
    await assert_product_ownership(product_id, user_id, db=db)
    row = await catalog_repo.find_by_id(db, user_id, product_id)
    if row is None:
        raise ProductNotFoundError()
    schema = await category_service.fetch_schema(row.category_id, db=db)
    summary = _compute_completeness(dict(row.fields_jsonb or {}), schema)
    return ValidationSummaryInternal(
        product_id=row.id,
        compulsory_filled=summary.compulsory_filled,
        compulsory_total=summary.compulsory_total,
        optional_filled=summary.optional_filled,
        optional_total=summary.optional_total,
        has_validation_errors=False,
        status=row.status,
    )


# Hash export — used by router to compute audit_event payload
# description_sha256 per §10.B.3 audit posture (PII compromise).
def description_sha256(description: str) -> str:
    """SHA-256(description) hex digest — for audit payload only.

    Per §10.B.3 audit posture: payload carries SHA-256 + 200-char
    preview, NEVER the full description (PII per `MVP_ARCH §11.9`).
    """
    return hashlib.sha256(description.encode("utf-8")).hexdigest()


__all__ = [
    "assert_product_ownership",
    "autofill_product",
    "create_product",
    "description_sha256",
    "get_draft",
    "get_preview",
    "get_product_for_export",
    "get_validation_summary",
    "list_products",
    "patch_product",
    "soft_delete",
]
