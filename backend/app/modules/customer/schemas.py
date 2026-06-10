"""``customer`` Pydantic v2 request/response models — SCAFFOLD.

Per BACKEND_ARCHITECTURE.md §8.E (LOCKED 2026-06-05).

**SCAFFOLD STATUS** — this module is authored by ``meesell-services-builder``
in step 1 of 2 so that ``service.py`` can import the request/response
classes by name and type-hint its public surface.  ``meesell-api-routes-
builder`` in step 2 of 2 may refine field examples, add OpenAPI
descriptions, and wire validators that depend on framework state — but
the **field SHAPES are locked here** per §8.E.

Field-level pincode regex is enforced at the schema layer (Pydantic v2
``Field(pattern=...)``) per §4.F errors envelope contract.  Service-layer
defensive re-checks live in :mod:`.service` and raise
:class:`.exceptions.InvalidPincodeError` if reached.

Master ruling 2 (2026-06-07): the bookkeeping flag is ``onboarding_complete``
(NOT ``profile_complete``) — DB-aligned per the migration ``935e55b4852c``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# NOTE: ``app.i18n.schema_contract.FieldSpec`` is a ``typing.TypedDict``;
# Pydantic v2 on Python < 3.12 requires ``typing_extensions.TypedDict`` for
# nested-TypedDict schema generation, so we represent FieldSpec entries as
# ``dict[str, Any]`` at the schema layer — service-layer builders construct
# the dict with the §5A.C-shaped keys + ``test_per_field_shape_keys.py`` is
# the schema-conformance gate.  When the runtime moves to 3.12 (or the
# i18n module switches to typing_extensions) this can be replaced with
# ``list[FieldSpec]``.


# ─────────────────────────────────────────────────────────────────────────────
# Response — the full profile shape, used by 4 of the 5 endpoints + cross-module
# ─────────────────────────────────────────────────────────────────────────────
class SellerProfileResponse(BaseModel):
    """Returned by GET /seller-profile + PATCH /seller-profile +
    PATCH /seller-profile/active-categories + PATCH /seller-profile/compliance/{super_id}.

    Per §8.E — the 9 Legal Metrology fields are nullable in the wire shape
    even though 6 of them are NOT NULL in the ORM (the row only EXISTS
    once those 6 are populated, so a response with all-null only happens
    in the cross-module ``get_profile_or_none`` path which the route maps
    to 404 anyway).
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    # 9 Legal Metrology fields
    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    manufacturer_pincode: str | None = None
    packer_name: str | None = None
    packer_address: str | None = None
    packer_pincode: str | None = None
    importer_name: str | None = None
    importer_address: str | None = None
    importer_pincode: str | None = None
    # Universal
    country_of_origin: str = "India"
    # Sell-in scope
    active_super_categories: list[str] = Field(default_factory=list)
    # Conditional compliance, JSONB shape per MVP_ARCH §2.2
    compliance_extensions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Bookkeeping — onboarding_complete is the locked DB-aligned name
    onboarding_complete: bool = False
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Request — partial update of base fields
# ─────────────────────────────────────────────────────────────────────────────
class PatchProfileRequest(BaseModel):
    """PATCH /seller-profile body — every field OPTIONAL (subset semantics).

    Pincode regex ``^\\d{6}$`` per §8.E + master ruling on Indian 6-digit
    PIN.  Pydantic emits 422 ``validation.<field>.<constraint>`` envelopes
    via :class:`app.core.errors._pydantic_validation_handler`; the
    constraint segment maps to ``validation.pincode.invalid_format``
    through the i18n registry.
    """

    model_config = ConfigDict(extra="forbid")

    manufacturer_name: str | None = None
    manufacturer_address: str | None = None
    manufacturer_pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    packer_name: str | None = None
    packer_address: str | None = None
    packer_pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    importer_name: str | None = None
    importer_address: str | None = None
    importer_pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    country_of_origin: str | None = None
    # active_super_categories has its own endpoint (B.3); compliance_extensions has its own (B.4).


# ─────────────────────────────────────────────────────────────────────────────
# Request — replace active super-categories entirely
# ─────────────────────────────────────────────────────────────────────────────
class PatchActiveCategoriesRequest(BaseModel):
    """PATCH /seller-profile/active-categories body.

    Replaces the array entirely (NOT additive) per §8.B.3 — declares the
    seller's current sell-in scope.  ``min_length=1`` rejects empty arrays
    at schema time so the service never has to handle the "scope reset"
    edge case (frontend uses a separate delete-account flow for that).
    """

    model_config = ConfigDict(extra="forbid")

    active_super_categories: list[str] = Field(min_length=1)


# ─────────────────────────────────────────────────────────────────────────────
# Request — set compliance extension for one super_id
# ─────────────────────────────────────────────────────────────────────────────
class PatchComplianceExtensionRequest(BaseModel):
    """PATCH /seller-profile/compliance/{super_id} body.

    Pydantic schema accepts any dict shape; service-layer validates against
    :data:`.domain.COMPLIANCE_EXTENSION_MAP[super_id]` and raises
    :class:`.exceptions.ComplianceExtensionMissingFieldsError` (422
    ``customer.compliance.missing_fields``) when required keys are absent.

    ``extra="allow"`` is intentional — the spec layer accepts forward-compat
    optional keys (e.g. metadata fields the frontend adds in V1.5) without
    rejecting the request; the service ignores keys not in the Spec's
    required + optional union.
    """

    model_config = ConfigDict(extra="allow")


# ─────────────────────────────────────────────────────────────────────────────
# Response — required fields, drives the onboarding wizard
# ─────────────────────────────────────────────────────────────────────────────
class RequiredFieldsResponse(BaseModel):
    """GET /seller-profile/required-fields response.

    ``base_fields`` uses the §5A.C ``FieldSpec`` contract verbatim so the
    frontend renderer dispatches with the same convention it uses for the
    catalog wizard (single rendering convention).

    ``extension_fields`` is a dict keyed by ``super_id`` carrying the
    extension fields PER declared super.  Empty dict when the seller has
    not yet declared any active super-categories.

    ``completed`` maps each rendered field's path to a boolean — paths use
    dot notation::

        - "manufacturer_name"                         (base field)
        - "country_of_origin"                         (base field)
        - "ext.26.fssai_license_number"               (Grocery extension)
        - "ext.19.license_registration_number"        (Beauty extension)
    """

    base_fields: list[dict[str, Any]]
    extension_fields: dict[str, list[dict[str, Any]]]
    completed: dict[str, bool]


# ─────────────────────────────────────────────────────────────────────────────
# Response — compliance block (cross-module consumer: export.service)
# ─────────────────────────────────────────────────────────────────────────────
class ComplianceBlockResponse(BaseModel):
    """Consumed cross-module by ``export.service`` per §16 — service-layer
    call, NEVER a route.

    Field names mirror :class:`.domain.ComplianceBlock`.  Mandatory
    manufacturer + packer fields are non-null because the row only exists
    once those 6 fields have been provided (first-PATCH-creates-row);
    importer fields remain nullable.
    """

    model_config = ConfigDict(from_attributes=True)

    manufacturer_name: str
    manufacturer_address: str
    manufacturer_pincode: str
    packer_name: str
    packer_address: str
    packer_pincode: str
    importer_name: str | None = None
    importer_address: str | None = None
    importer_pincode: str | None = None
    country_of_origin: str


__all__ = [
    "ComplianceBlockResponse",
    "PatchActiveCategoriesRequest",
    "PatchComplianceExtensionRequest",
    "PatchProfileRequest",
    "RequiredFieldsResponse",
    "SellerProfileResponse",
]
