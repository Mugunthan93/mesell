"""``customer`` service layer — 9 PUBLIC async methods per §8.C.

Per BACKEND_ARCHITECTURE.md §8.C (LOCKED 2026-06-05) + the §8 sub-session
master rulings (2026-06-07):

- Flag column is ``onboarding_complete`` (NOT ``profile_complete``) —
  DB-aligned per migration ``935e55b4852c``.
- Cross-module entry points: :func:`get_profile`,
  :func:`get_compliance_block`, :func:`get_onboarding_completeness`,
  :func:`assert_eligible_for_super_id`.
- :func:`get_required_fields` is the wizard driver — cached 60 s in
  Valkey DB 3 per §4.D; invalidated by :func:`_invalidate_required_fields_cache`
  on every PATCH path.

Public surface (9 methods)::

    # 5 endpoint-mirror
    get_profile_or_none(user_id) -> SellerProfile | None
    upsert_profile(user_id, patch) -> SellerProfile
    set_active_categories(user_id, super_ids) -> SellerProfile
    set_compliance_extension(user_id, super_id, payload) -> SellerProfile
    get_required_fields(user_id) -> RequiredFieldsResponse

    # 3 cross-module
    get_profile(user_id) -> SellerProfile          # raises ProfileNotFoundError
    get_compliance_block(user_id) -> ComplianceBlock
    get_onboarding_completeness(user_id) -> ProfileCompleteness

    # 1 cross-module assertion (catalog gate)
    assert_eligible_for_super_id(user_id, super_id) -> None

Domain types come from :mod:`.domain` (frozen dataclasses) — the schemas
in :mod:`.schemas` are the WIRE shapes the router consumes.

MS-E extraction note (spec §3.A — 2 sanctioned edits ONLY)
----------------------------------------------------------
This module is byte-for-byte identical to the monolith
``app.modules.customer.service`` EXCEPT:
  (a) the ``CategoryORM`` import + the ``sqlalchemy.select`` import (used ONLY
      by the loader) are DROPPED;
  (b) the ``_load_super_id_set`` loader BODY swaps the
      ``SELECT DISTINCT super_id FROM categories`` ORM read for
      ``await category_client.get_super_category_set()`` (FROZEN-0E).
The cached accessor ``_get_super_id_set`` signature + cache contract
(``customer.super_category_set``, TTL 3600 s, single_flight) are UNCHANGED.
Plus mechanical import-path flattening (``app.modules.customer.X`` → ``app.X``).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app import repository as customer_repo
from app.core.cache import get_or_set
from app.core.extracted_clients import category_client
from app.domain import (
    BASE_FIELD_NAMES,
    COMPLIANCE_EXTENSION_MAP,
    ComplianceBlock,
    ComplianceExtensionSpec,
    ProfileCompleteness,
    SellerProfile,
)
from app.exceptions import (
    ComplianceExtensionMissingFieldsError,
    InvalidSuperCategoryError,
    ProfileIncompleteForCategoryError,
    ProfileNotFoundError,
    SuperCategoryNotDeclaredError,
)
from app.schemas import (
    PatchProfileRequest,
    RequiredFieldsResponse,
)
from app.shared.models.seller_profile import SellerProfile as SellerProfileORM

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Cache constants
# ─────────────────────────────────────────────────────────────────────────────
_REQUIRED_FIELDS_TTL_SECONDS = 60
"""Per §8.B.5: response cache TTL is 60 s — low because the profile
changes during onboarding and the wizard polls per step.  Invalidated
on every PATCH."""

_SUPER_CATEGORY_SET_TTL_SECONDS = 3600
"""Per §4.D + §8.I: the global ``categories.super_id`` distinct set is
reference data — refreshed hourly.  CACHE_VERSION bumps on quarterly
Meesho corpus refresh handles invalidation."""

_SUPER_CATEGORY_SET_KEY = "customer.super_category_set"
"""Logical key under which the distinct super_id set is cached.  The
``meesell:v{cv}:`` prefix is added by :func:`core.cache.get_or_set`."""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — module-private
# ─────────────────────────────────────────────────────────────────────────────
def _orm_to_domain(row: SellerProfileORM) -> SellerProfile:
    """Convert a hydrated ORM instance to the frozen :class:`SellerProfile`."""
    return SellerProfile(
        user_id=row.user_id,
        manufacturer_name=row.manufacturer_name,
        manufacturer_address=row.manufacturer_address,
        manufacturer_pincode=row.manufacturer_pincode,
        packer_name=row.packer_name,
        packer_address=row.packer_address,
        packer_pincode=row.packer_pincode,
        importer_name=row.importer_name,
        importer_address=row.importer_address,
        importer_pincode=row.importer_pincode,
        country_of_origin=row.country_of_origin,
        active_super_categories=list(row.active_super_categories or []),
        compliance_extensions=dict(row.compliance_extensions or {}),
        onboarding_complete=bool(row.onboarding_complete),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _is_field_present(value: Any) -> bool:
    """Truth-test for "this field has been provided".

    None and empty-string both count as absent.  Whitespace-only strings
    are also absent (defensive — the schema layer trims, but service
    callers should not depend on that).
    """
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _recompute_onboarding_complete(
    base_state: dict[str, Any],
    active_super_categories: list[str],
    compliance_extensions: dict[str, dict[str, Any]],
) -> bool:
    """Return True iff the profile satisfies the §8.F + master ruling 4
    onboarding contract.

    Rule (per master ruling 4 + §8.F + §8.J test 4)::

        all 10 base fields present                                 -- AND --
        for every super_id in active_super_categories whose
            Spec.compulsory == True,
            all Spec.required_keys present in compliance_extensions[super_id]

    Importer fields are tracked in ``base_state`` but are NOT required —
    only the 7 LM+country_of_origin fields actually block.  However per
    the §8.J test 4 phrasing the recompute treats the 10 fields as the
    completeness denominator (importer trio counts toward the
    ``base_complete_count`` UX badge but does NOT gate the flag).

    Args:
        base_state: dict[name → value] for each name in BASE_FIELD_NAMES.
        active_super_categories: ordered list of declared super_ids.
        compliance_extensions: ``{super_id: {key: value}}`` JSONB shape.

    Returns:
        True only when every gate evaluates True.
    """
    # ── Base-field gate ──────────────────────────────────────────────────────
    # The 6 mandatory LM fields + country_of_origin must be present.
    # (Importer trio is optional — does not block the flag.)
    blocking_names = (
        "manufacturer_name",
        "manufacturer_address",
        "manufacturer_pincode",
        "packer_name",
        "packer_address",
        "packer_pincode",
        "country_of_origin",
    )
    for name in blocking_names:
        if not _is_field_present(base_state.get(name)):
            return False

    # ── Compliance-extension gate ────────────────────────────────────────────
    for super_id in active_super_categories:
        spec = COMPLIANCE_EXTENSION_MAP.get(super_id)
        if spec is None or not spec.compulsory:
            # Either the super_id has no compliance rule, or the rule is
            # optional — does not block.
            continue
        ext = compliance_extensions.get(super_id) or {}
        for required_key in spec.required_keys:
            if not _is_field_present(ext.get(required_key)):
                return False
    return True


def _missing_required_keys(
    spec: ComplianceExtensionSpec,
    payload: dict[str, Any],
) -> list[str]:
    """Return the list of ``spec.required_keys`` absent or empty in ``payload``."""
    return [k for k in spec.required_keys if not _is_field_present(payload.get(k))]


def _build_field_spec(
    *,
    name: str,
    canonical_name: str,
    marker: str,
    data_type: str,
    primitive: str,
    help_text: str,
    enum_resolver: str | None,
    validation_message_ids: list[str],
    is_advanced: bool = False,
) -> dict[str, Any]:
    """Build a :class:`app.i18n.schema_contract.FieldSpec`-shaped dict."""
    return {
        "name": name,
        "canonical_name": canonical_name,
        "marker": marker,
        "data_type": data_type,
        "primitive": primitive,
        "help_text": help_text,
        "is_advanced": is_advanced,
        "enum_resolver": enum_resolver,
        "validation_message_ids": validation_message_ids,
    }


# Static per-field metadata for the 10 base fields the wizard renders.
# Field metadata is a tuple of (name, marker, data_type, primitive,
# help_text, validation_message_ids).
_BASE_FIELD_DEFINITIONS: tuple[tuple[str, str, str, str, str, tuple[str, ...]], ...] = (
    ("manufacturer_name", "compulsory", "text", "text_short",
     "Legal name of the entity that manufactures the product.",
     ("validation.body.malformed_json",)),
    ("manufacturer_address", "compulsory", "address", "address_group",
     "Full registered address of the manufacturer.",
     ("validation.body.malformed_json",)),
    ("manufacturer_pincode", "compulsory", "text", "text_short",
     "6-digit Indian PIN code of the manufacturer's address.",
     ("validation.pincode.invalid_format",)),
    ("packer_name", "compulsory", "text", "text_short",
     "Legal name of the packer (often the same as the manufacturer).",
     ("validation.body.malformed_json",)),
    ("packer_address", "compulsory", "address", "address_group",
     "Full registered address of the packer.",
     ("validation.body.malformed_json",)),
    ("packer_pincode", "compulsory", "text", "text_short",
     "6-digit Indian PIN code of the packer's address.",
     ("validation.pincode.invalid_format",)),
    ("importer_name", "optional", "text", "text_short",
     "Legal name of the importer. Leave blank if you do not import.",
     ()),
    ("importer_address", "optional", "address", "address_group",
     "Full registered address of the importer.",
     ()),
    ("importer_pincode", "optional", "text", "text_short",
     "6-digit Indian PIN code of the importer's address.",
     ("validation.pincode.invalid_format",)),
    ("country_of_origin", "compulsory", "text", "text_short",
     "Country where the product was manufactured.",
     ("validation.body.malformed_json",)),
)


def _build_base_fields_spec() -> list[dict[str, Any]]:
    """Build the §5A.C-shaped list for the 10 base fields."""
    return [
        _build_field_spec(
            name=name,
            canonical_name=name,
            marker=marker,
            data_type=dtype,
            primitive=primitive,
            help_text=help_text,
            enum_resolver=None,
            validation_message_ids=list(vmids),
        )
        for (name, marker, dtype, primitive, help_text, vmids) in _BASE_FIELD_DEFINITIONS
    ]


def _build_extension_fields_spec(super_id: str) -> list[dict[str, Any]]:
    """Build the §5A.C-shaped list for one super_id's extension fields.

    Returns an empty list when ``super_id`` has no Spec registered (the
    seller declared a super-category that does not require extension
    fields — e.g. Apparel).
    """
    spec = COMPLIANCE_EXTENSION_MAP.get(super_id)
    if spec is None:
        return []
    result: list[dict[str, Any]] = []
    for key in spec.required_keys:
        result.append(_build_field_spec(
            name=key,
            canonical_name=key,
            marker="compulsory" if spec.compulsory else "optional",
            data_type="text",
            primitive="text_short",
            help_text=f"Required for {spec.super_name} sellers.",
            enum_resolver=None,
            validation_message_ids=["customer.compliance.missing_fields"],
        ))
    for key in spec.optional_keys:
        result.append(_build_field_spec(
            name=key,
            canonical_name=key,
            marker="optional",
            data_type="text",
            primitive="text_short",
            help_text=f"Optional for {spec.super_name} sellers.",
            enum_resolver=None,
            validation_message_ids=[],
        ))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Cache — required-fields response
# ─────────────────────────────────────────────────────────────────────────────
def _required_fields_cache_key(user_id: UUID) -> str:
    """Logical cache key per §8.B.5."""
    return f"customer.required_fields.{user_id}"


async def _invalidate_required_fields_cache(user_id: UUID) -> None:
    """Drop the cached ``/required-fields`` response on every PATCH path."""
    try:
        from app.shared.config import settings
        from app.shared.valkey import get_valkey_cache

        client = await get_valkey_cache()
        full_key = f"meesell:{settings.CACHE_VERSION}:{_required_fields_cache_key(user_id)}"
        await client.delete(full_key)
    except Exception as exc:  # noqa: BLE001 — cache invalidation must not break writes
        logger.warning(
            "customer.cache.invalidate_required_fields failed for user_id=%s: %s",
            user_id,
            exc,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — super_id validation against the global categories set
# ─────────────────────────────────────────────────────────────────────────────
async def _load_super_id_set(db: AsyncSession) -> list[str]:
    """The distinct ``super_id`` set — JSON-serialisable list form for the cache.

    MS-E (FROZEN-0E): the original monolith body
    (``SELECT DISTINCT super_id FROM categories`` via ``CategoryORM``) is
    REPLACED by the OUTBOUND HTTP shim ``category_client.get_super_category_set``
    — the cross-schema ORM read is forbidden post-extraction (§2.D / §16.G).
    The shim returns ``list[str]`` of distinct super_ids; the cache contract
    (``customer.super_category_set``, TTL 3600 s, single_flight) is UNCHANGED.

    ``db`` is retained in the signature so the cached accessor
    ``_get_super_id_set``'s ``lambda: _load_super_id_set(db)`` call site is
    byte-for-byte unchanged.  The HTTP shim forwards the caller's JWT from the
    request context; ``db`` is unused by the shim path.
    """
    return await category_client.get_super_category_set()


async def _get_super_id_set(db: AsyncSession) -> set[str]:
    """Return the global ``categories.super_id`` distinct set, cached.

    Uses :func:`app.core.cache.get_or_set` with TTL 3600 s and the
    versioned ``meesell:v{cv}:customer.super_category_set`` key per §4.D.

    Single-flight is enabled — the SELECT is global reference data with
    no per-user fan-out, and a cold-cache stampede on app boot would
    otherwise serialise many DISTINCTs against ``categories``.
    """
    value = await get_or_set(
        _SUPER_CATEGORY_SET_KEY,
        lambda: _load_super_id_set(db),
        ttl=_SUPER_CATEGORY_SET_TTL_SECONDS,
        single_flight=True,
    )
    return set(value)


# ─────────────────────────────────────────────────────────────────────────────
# Public surface — §8.C nine methods
# ─────────────────────────────────────────────────────────────────────────────
async def get_profile_or_none(
    user_id: UUID, db: AsyncSession
) -> SellerProfile | None:
    """``GET /api/v1/seller-profile`` business path per §8.B.1.

    Returns ``None`` when no row exists (first-time seller).  The router
    maps ``None`` to the 404 ``customer.profile.not_found`` envelope.
    """
    row = await customer_repo.find_by_user_id(db, user_id)
    if row is None:
        return None
    return _orm_to_domain(row)


async def get_profile(user_id: UUID, db: AsyncSession) -> SellerProfile:
    """Cross-module read — raises :class:`ProfileNotFoundError` if no row.

    Consumed by ``catalog`` (PROFILE_INCOMPLETE_FOR_CATEGORY upstream
    check), ``export`` (compliance block sourcing), ``dashboard``
    (completeness badge).
    """
    row = await customer_repo.find_by_user_id(db, user_id)
    if row is None:
        raise ProfileNotFoundError()
    return _orm_to_domain(row)


async def upsert_profile(
    user_id: UUID,
    patch: PatchProfileRequest,
    db: AsyncSession,
) -> SellerProfile:
    """``PATCH /api/v1/seller-profile`` business path per §8.B.2.

    First PATCH creates the row; subsequent PATCH updates.  Recomputes
    ``onboarding_complete`` on every call.  Invalidates the
    ``/required-fields`` cache.

    Subset semantics: only fields present in ``patch`` are written; absent
    fields are untouched on the existing row.  On first PATCH the
    ORM-required NOT NULL columns (6 base fields) MUST be present in the
    payload or asyncpg raises an IntegrityError, which the route surfaces
    as 422 via the §4.F handler.
    """
    # Build the dict of provided fields — exclude None values + unset fields
    # so we never overwrite an existing value with ``None``.
    provided = patch.model_dump(exclude_unset=True, exclude_none=True)

    # Load existing (if any) to merge for the recompute.
    existing = await customer_repo.find_by_user_id(db, user_id)
    merged_base: dict[str, Any] = {}
    if existing is not None:
        for name in BASE_FIELD_NAMES:
            merged_base[name] = getattr(existing, name)
    merged_base.update(provided)

    if existing is not None:
        active = list(existing.active_super_categories or [])
        ext = dict(existing.compliance_extensions or {})
    else:
        active = []
        ext = {}

    onboarding_complete = _recompute_onboarding_complete(merged_base, active, ext)

    row = await customer_repo.upsert(
        db,
        user_id,
        provided,
        onboarding_complete=onboarding_complete,
    )

    await _invalidate_required_fields_cache(user_id)

    return _orm_to_domain(row)


async def set_active_categories(
    user_id: UUID,
    super_ids: list[str],
    db: AsyncSession,
) -> SellerProfile:
    """``PATCH /api/v1/seller-profile/active-categories`` per §8.B.3.

    1. Validate each ``super_id`` against the cached distinct set from
       ``categories.super_id``.  Unknown → :class:`InvalidSuperCategoryError`.
    2. Repository replaces ``active_super_categories`` entirely.
    3. Recompute ``onboarding_complete``.
    4. Invalidate the ``/required-fields`` cache.

    Pre-conditions:
    - The profile row MUST exist (the wizard flow guarantees PATCH base
      profile precedes this call).  If absent → :class:`ProfileNotFoundError`.
    """
    valid_set = await _get_super_id_set(db)
    unknown = [sid for sid in super_ids if sid not in valid_set]
    if unknown:
        raise InvalidSuperCategoryError(
            detail=f"Unknown super_id(s): {sorted(set(unknown))}",
            unknown_super_ids=sorted(set(unknown)),
        )

    existing = await customer_repo.find_by_user_id(db, user_id)
    if existing is None:
        raise ProfileNotFoundError()

    base_state = {name: getattr(existing, name) for name in BASE_FIELD_NAMES}
    ext = dict(existing.compliance_extensions or {})
    onboarding_complete = _recompute_onboarding_complete(
        base_state, list(super_ids), ext
    )

    row = await customer_repo.update_active_categories(
        db,
        user_id,
        list(super_ids),
        onboarding_complete=onboarding_complete,
    )

    await _invalidate_required_fields_cache(user_id)
    return _orm_to_domain(row)


async def set_compliance_extension(
    user_id: UUID,
    super_id: str,
    payload: dict[str, Any],
    db: AsyncSession,
) -> SellerProfile:
    """``PATCH /api/v1/seller-profile/compliance/{super_id}`` per §8.B.4.

    1. Read current profile (404 if absent).
    2. Verify ``super_id IN active_super_categories``; if not →
       :class:`SuperCategoryNotDeclaredError`.
    3. Validate ``payload`` against ``COMPLIANCE_EXTENSION_MAP[super_id]``:
       missing required keys → :class:`ComplianceExtensionMissingFieldsError`.
    4. Repository JSONB-merges the payload at ``{super_id}`` (other
       super_id entries untouched).
    5. Recompute ``onboarding_complete``.
    6. Invalidate the ``/required-fields`` cache.
    """
    existing = await customer_repo.find_by_user_id(db, user_id)
    if existing is None:
        raise ProfileNotFoundError()

    if super_id not in (existing.active_super_categories or []):
        raise SuperCategoryNotDeclaredError(
            detail=(
                f"Super category {super_id!r} is not in your declared "
                "active categories."
            ),
            super_id=super_id,
        )

    spec = COMPLIANCE_EXTENSION_MAP.get(super_id)
    if spec is None:
        # Defensive — should be unreachable because the super_id IS in
        # active_super_categories which was validated against the global
        # set, and a super_id without a Spec is by definition not
        # compliance-gated.  But if a future spec is added without a Map
        # entry, the seller's payload is meaningless — surface it cleanly.
        logger.info(
            "customer.compliance.no_spec super_id=%s — accepting payload as-is",
            super_id,
        )
        # No required keys to check; just merge whatever payload was provided.
        row = await customer_repo.update_compliance_extension(
            db,
            user_id,
            super_id,
            payload,
            onboarding_complete=existing.onboarding_complete,
        )
        await _invalidate_required_fields_cache(user_id)
        return _orm_to_domain(row)

    # Service-layer validation: if the spec requires keys and any are
    # missing → 422.
    missing = _missing_required_keys(spec, payload)
    if missing:
        raise ComplianceExtensionMissingFieldsError(
            detail=(
                f"Compliance fields missing for super_id {super_id!r}: "
                f"{missing}"
            ),
            super_id=super_id,
            missing_keys=missing,
        )

    # Project the merged compliance extensions for the recompute.
    merged_ext = dict(existing.compliance_extensions or {})
    merged_super = dict(merged_ext.get(super_id, {}))
    merged_super.update(payload)
    merged_ext[super_id] = merged_super

    base_state = {name: getattr(existing, name) for name in BASE_FIELD_NAMES}
    onboarding_complete = _recompute_onboarding_complete(
        base_state,
        list(existing.active_super_categories or []),
        merged_ext,
    )

    row = await customer_repo.update_compliance_extension(
        db,
        user_id,
        super_id,
        payload,
        onboarding_complete=onboarding_complete,
    )
    await _invalidate_required_fields_cache(user_id)
    return _orm_to_domain(row)


async def get_required_fields(
    user_id: UUID, db: AsyncSession
) -> RequiredFieldsResponse:
    """``GET /api/v1/seller-profile/required-fields`` per §8.B.5.

    Cached 60 s per §4.D; invalidated on any PATCH path.  The frontend
    polls this on every wizard step.

    Behaviour when no profile row exists (first-time seller):

    - ``base_fields`` lists all 10 base fields with ``completed`` False.
    - ``extension_fields`` is an empty dict (no active super_categories yet).
    """
    cached = await get_or_set(
        _required_fields_cache_key(user_id),
        lambda: _build_required_fields_payload(user_id, db),
        ttl=_REQUIRED_FIELDS_TTL_SECONDS,
        single_flight=False,
    )
    return RequiredFieldsResponse.model_validate(cached)


async def _build_required_fields_payload(
    user_id: UUID, db: AsyncSession
) -> dict[str, Any]:
    """Build the JSON-serialisable payload for the required-fields cache."""
    row = await customer_repo.find_by_user_id(db, user_id)

    base_fields = _build_base_fields_spec()
    completed: dict[str, bool] = {}

    # Base fields completed map.
    for name in BASE_FIELD_NAMES:
        completed[name] = _is_field_present(getattr(row, name, None)) if row else False

    # Extension fields per declared super_id.
    extension_fields: dict[str, list[dict[str, Any]]] = {}
    active_super_categories: list[str] = (
        list(row.active_super_categories or []) if row else []
    )
    ext_state: dict[str, dict[str, Any]] = (
        dict(row.compliance_extensions or {}) if row else {}
    )

    for super_id in active_super_categories:
        fields_for_super = _build_extension_fields_spec(super_id)
        if not fields_for_super:
            continue
        extension_fields[super_id] = fields_for_super
        for fs in fields_for_super:
            completed[f"ext.{super_id}.{fs['name']}"] = _is_field_present(
                ext_state.get(super_id, {}).get(fs["name"])
            )

    return {
        "base_fields": base_fields,
        "extension_fields": extension_fields,
        "completed": completed,
    }


async def get_compliance_block(
    user_id: UUID, db: AsyncSession
) -> ComplianceBlock:
    """Cross-module call from ``export.service``.  Returns the 9 standard
    LM fields + ``country_of_origin``.

    Raises :class:`ProfileNotFoundError` when no row exists.
    """
    profile = await get_profile(user_id, db)
    # Mandatory fields cannot be None at this point (the row exists, so the
    # NOT NULL constraints have already been satisfied).  Defensive cast:
    if profile.manufacturer_name is None or profile.manufacturer_address is None \
            or profile.manufacturer_pincode is None \
            or profile.packer_name is None or profile.packer_address is None \
            or profile.packer_pincode is None:
        # Should never happen — the row only exists once these 6 NOT NULL
        # fields are populated.  Surface defensively as not-found.
        raise ProfileNotFoundError(
            detail="Seller profile is missing mandatory compliance fields."
        )
    return ComplianceBlock(
        manufacturer_name=profile.manufacturer_name,
        manufacturer_address=profile.manufacturer_address,
        manufacturer_pincode=profile.manufacturer_pincode,
        packer_name=profile.packer_name,
        packer_address=profile.packer_address,
        packer_pincode=profile.packer_pincode,
        importer_name=profile.importer_name,
        importer_address=profile.importer_address,
        importer_pincode=profile.importer_pincode,
        country_of_origin=profile.country_of_origin,
    )


async def get_onboarding_completeness(
    user_id: UUID, db: AsyncSession
) -> ProfileCompleteness:
    """Cross-module call from ``dashboard.service``.

    Returns counts + the ``onboarding_complete`` flag mirror.  When no
    profile row exists yet (first-time seller), returns
    ``ProfileCompleteness(0, 10, 0, 0, onboarding_complete=False)`` —
    the dashboard renders this as 0% so the seller knows to start the
    wizard.  This branch deliberately does NOT raise — the dashboard
    home page is the seller's first stop after sign-up.
    """
    row = await customer_repo.find_by_user_id(db, user_id)

    base_total = len(BASE_FIELD_NAMES)  # always 10 per §8.F

    if row is None:
        return ProfileCompleteness(
            base_complete_count=0,
            base_total_count=base_total,
            extension_complete_count=0,
            extension_total_count=0,
            onboarding_complete=False,
        )

    base_complete = sum(
        1 for name in BASE_FIELD_NAMES if _is_field_present(getattr(row, name))
    )

    # Extension totals: sum of required_keys across each declared super's
    # COMPULSORY Spec.  Non-compulsory specs contribute 0 to the total
    # (they don't gate completeness; they don't appear in the badge math).
    extension_total = 0
    extension_complete = 0
    ext_state: dict[str, dict[str, Any]] = dict(row.compliance_extensions or {})
    for super_id in (row.active_super_categories or []):
        spec = COMPLIANCE_EXTENSION_MAP.get(super_id)
        if spec is None or not spec.compulsory:
            continue
        extension_total += len(spec.required_keys)
        for required_key in spec.required_keys:
            if _is_field_present(ext_state.get(super_id, {}).get(required_key)):
                extension_complete += 1

    return ProfileCompleteness(
        base_complete_count=base_complete,
        base_total_count=base_total,
        extension_complete_count=extension_complete,
        extension_total_count=extension_total,
        onboarding_complete=bool(row.onboarding_complete),
    )


async def assert_eligible_for_super_id(
    user_id: UUID,
    super_id: str,
    db: AsyncSession,
) -> None:
    """Cross-module call from ``catalog.service.create_product``.

    Per §8.C + the §10 PROFILE_INCOMPLETE_FOR_CATEGORY gate.

    Eligibility =
      1. Profile row exists, AND
      2. ``super_id`` is in ``active_super_categories``, AND
      3. For every required key in ``COMPLIANCE_EXTENSION_MAP[super_id]``
         (when the spec is compulsory), the key is present in
         ``compliance_extensions[super_id]``.

    Raises:
        ProfileIncompleteForCategoryError: 422 envelope
            ``customer.profile.incomplete_for_category``.
    """
    row = await customer_repo.find_by_user_id(db, user_id)
    if row is None:
        raise ProfileIncompleteForCategoryError(
            detail="Your seller profile is not yet created.",
            super_id=super_id,
            missing_keys=[],
        )

    if super_id not in (row.active_super_categories or []):
        raise ProfileIncompleteForCategoryError(
            detail=(
                f"You have not declared super_id {super_id!r} as an "
                "active category."
            ),
            super_id=super_id,
            missing_keys=[],
        )

    spec = COMPLIANCE_EXTENSION_MAP.get(super_id)
    if spec is None or not spec.compulsory:
        # No compliance gate for this super.  Eligible.
        return

    ext = (row.compliance_extensions or {}).get(super_id, {}) or {}
    missing = _missing_required_keys(spec, ext)
    if missing:
        raise ProfileIncompleteForCategoryError(
            detail=(
                f"Compliance fields missing for super_id {super_id!r}: {missing}"
            ),
            super_id=super_id,
            missing_keys=missing,
        )
    # All gates passed.
    return


__all__ = [
    "assert_eligible_for_super_id",
    "get_compliance_block",
    "get_onboarding_completeness",
    "get_profile",
    "get_profile_or_none",
    "get_required_fields",
    "set_active_categories",
    "set_compliance_extension",
    "upsert_profile",
]
