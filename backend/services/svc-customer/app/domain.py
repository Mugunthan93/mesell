"""``customer`` internal domain types — frozen dataclasses + the
``COMPLIANCE_EXTENSION_MAP`` constant.

Per BACKEND_ARCHITECTURE.md §8.F (LOCKED 2026-06-05) + the §8 sub-session
master rulings (2026-06-07):

- ``COMPLIANCE_EXTENSION_MAP`` is a frozen ``dict[str, ComplianceExtensionSpec]``
  with **11 keys** — 6 source rules covering 11 ``super_id``s.  Beauty's 6
  ``super_id``s (19/36/37/14/88/34) each map to the **same shared**
  ``ComplianceExtensionSpec`` instance for O(1) lookup; the 5 single-super
  rules map 1:1.
- Beauty ``compulsory=True`` (block on missing) per master ruling 4 — same
  posture as Grocery FSSAI; the lenient "if licensed" gating is deferred
  to V1.5.
- ``onboarding_complete`` flag (NOT ``profile_complete``) per master
  ruling 2 — the live DB column is ``onboarding_complete`` per
  migration ``935e55b4852c``; the DB is authoritative.

These types never cross the HTTP boundary directly — the schemas in
``.schemas`` are the wire shapes.  Using plain frozen dataclasses (not
Pydantic) keeps them lightweight and immutable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Final, Mapping
from uuid import UUID


# ─────────────────────────────────────────────────────────────────────────────
# Frozen dataclasses (§8.F)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SellerProfile:
    """Mirrors a ``seller_profile`` row; never crosses HTTP.

    Field order mirrors the ORM model at
    :mod:`app.shared.models.seller_profile` for readability — the dataclass
    is hand-converted from the ORM instance by the repository.
    """

    user_id: UUID
    # 9 Legal Metrology fields.  Nullable in the dataclass even though the
    # ORM model marks the 6 mandatory ones as NOT NULL — the dataclass shape
    # is what's returned to callers (and to schemas).  A row only EXISTS in
    # the DB once all 6 mandatory fields have been provided (first-PATCH-
    # creates-row pattern, §8.B.2).  Returning a dataclass with None values
    # to a caller before the row exists is by design — the caller maps
    # absence to 404 ``customer.profile.not_found`` per §8.B.1.
    manufacturer_name: str | None
    manufacturer_address: str | None
    manufacturer_pincode: str | None
    packer_name: str | None
    packer_address: str | None
    packer_pincode: str | None
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    # Universal
    country_of_origin: str
    # Sell-in scope (ordered list — JSONB array stored as text[])
    active_super_categories: list[str] = field(default_factory=list)
    # Conditional compliance, JSONB shape per MVP_ARCH §2.2:
    #   {super_id: {key: value, ...}}
    compliance_extensions: dict[str, dict] = field(default_factory=dict)
    # Bookkeeping
    onboarding_complete: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class ComplianceBlock:
    """The 9 standard Legal Metrology fields + country_of_origin.

    Consumed by ``export.service`` cross-module (per §16) — never crosses
    the HTTP boundary as a request/response body, but its Pydantic mirror
    (:class:`schemas.ComplianceBlockResponse`) is used by the export
    Adapter when serialising compliance rows into XLSX cells.
    """

    manufacturer_name: str
    manufacturer_address: str
    manufacturer_pincode: str
    packer_name: str
    packer_address: str
    packer_pincode: str
    importer_name: str | None
    importer_address: str | None
    importer_pincode: str | None
    country_of_origin: str


@dataclass(frozen=True)
class ProfileCompleteness:
    """Consumed by ``dashboard.service`` for the completeness badge.

    All four counts are computed by ``customer.service``:

    - ``base_total_count`` is always 10 (9 LM fields + country_of_origin).
    - ``extension_total_count`` is the sum of ``len(Spec.required_keys)``
      across each ``super_id`` in ``active_super_categories`` whose
      ``Spec.compulsory`` is True.
    - ``onboarding_complete`` mirrors the ``seller_profile.onboarding_complete``
      DB column, recomputed on every service write per §8.C.
    """

    base_complete_count: int
    base_total_count: int  # always 10 (9 LM fields + country_of_origin)
    extension_complete_count: int
    extension_total_count: int  # depends on active_super_categories
    onboarding_complete: bool  # mirrors seller_profile.onboarding_complete


@dataclass(frozen=True)
class ComplianceExtensionSpec:
    """Static spec per ``super_id`` family.

    Per MVP_ARCH §2.2 table + §8.F lock + master rulings 3 & 4 (2026-06-07):

    - Grocery (``super_id`` 26)        — ``compulsory=True``, FSSAI.
    - Kids (13)                          — ``compulsory=False``.
    - Electronics (16)                   — ``compulsory=False``.
    - Beauty (19/36/37/14/88/34)         — ``compulsory=True``; license.
    - Books (80)                         — ``compulsory=False``.
    - Home & Kitchen appliance subset (30) — ``compulsory=False``.

    The ``compulsory=True`` spec causes the recompute logic to require all
    ``required_keys`` to be populated for the gate to flip
    ``onboarding_complete`` to True; ``compulsory=False`` specs do not
    block onboarding even when ``required_keys`` are empty (the keys
    behave as documentation hints for V1.5 conditional gating).
    """

    super_id: str
    super_name: str
    required_keys: tuple[str, ...]
    optional_keys: tuple[str, ...]
    compulsory: bool


# ─────────────────────────────────────────────────────────────────────────────
# COMPLIANCE_EXTENSION_MAP — locked at 11 keys (6 source rules)
# ─────────────────────────────────────────────────────────────────────────────
# Master ruling 3 (2026-06-07): the dict has exactly 11 KEYS because
# Beauty's 6 super_ids all map to the SAME shared ``ComplianceExtensionSpec``
# instance.  The "6 entries" phrasing in older drafts refers to the 6 source
# rules — the constructed dict has 11 keys for O(1) lookup by super_id.
#
# §19 CI Contract: the test ``test_compliance_extension_validation_per_super_id``
# asserts both the cardinality (11) and the shared-instance identity for the
# Beauty family.

_GROCERY_SPEC: Final[ComplianceExtensionSpec] = ComplianceExtensionSpec(
    super_id="26",
    super_name="Grocery",
    required_keys=("fssai_license_number",),
    optional_keys=("fssai_expiry",),
    compulsory=True,
)

_KIDS_SPEC: Final[ComplianceExtensionSpec] = ComplianceExtensionSpec(
    super_id="13",
    super_name="Kids",
    required_keys=(),
    optional_keys=("bis_isi_certification_number",),
    compulsory=False,
)

_ELECTRONICS_SPEC: Final[ComplianceExtensionSpec] = ComplianceExtensionSpec(
    super_id="16",
    super_name="Electronics",
    required_keys=(),
    optional_keys=(
        "bis_isi_certification_number",
        "r_number",
        "is_number",
        "cm_l_number",
    ),
    compulsory=False,
)

# Beauty: 6 super_ids, ONE shared spec instance (O(1) lookup by super_id).
# The super_name on this shared spec is "Beauty" — it is the family label,
# not a per-super disambiguator (Meesho's own catalogue reuses several
# names across Beauty sub-trees).
_BEAUTY_SPEC: Final[ComplianceExtensionSpec] = ComplianceExtensionSpec(
    super_id="19",  # canonical anchor; the dict registers it under 6 keys
    super_name="Beauty",
    required_keys=(
        "license_registration_number",
        "license_registration_type",
        "license_expiry_date",
    ),
    optional_keys=(),
    compulsory=True,
)

_BOOKS_SPEC: Final[ComplianceExtensionSpec] = ComplianceExtensionSpec(
    super_id="80",
    super_name="Books",
    required_keys=(),
    optional_keys=("isbn_publisher_id",),
    compulsory=False,
)

_HOME_KITCHEN_SPEC: Final[ComplianceExtensionSpec] = ComplianceExtensionSpec(
    super_id="30",
    super_name="Home & Kitchen",
    required_keys=(),
    optional_keys=("license_number", "license_expiry_date"),
    compulsory=False,
)


# 11 keys — the locked cardinality per master ruling 3.
_COMPLIANCE_EXTENSION_MAP_RAW: dict[str, ComplianceExtensionSpec] = {
    # Grocery — 1 key, compulsory.
    "26": _GROCERY_SPEC,
    # Kids — 1 key, optional.
    "13": _KIDS_SPEC,
    # Electronics — 1 key, optional.
    "16": _ELECTRONICS_SPEC,
    # Beauty — 6 keys, ALL pointing at the SAME shared spec instance.
    # Tests assert identity (``is``) on this shared spec, not just equality.
    "19": _BEAUTY_SPEC,
    "36": _BEAUTY_SPEC,
    "37": _BEAUTY_SPEC,
    "14": _BEAUTY_SPEC,
    "88": _BEAUTY_SPEC,
    "34": _BEAUTY_SPEC,
    # Books — 1 key, optional.
    "80": _BOOKS_SPEC,
    # Home & Kitchen — 1 key, optional.
    "30": _HOME_KITCHEN_SPEC,
}

#: The locked mapping from ``super_id`` → :class:`ComplianceExtensionSpec`.
#: Exactly **11 keys** (6 source rules; Beauty's 6 share one Spec instance).
#: Wrapped in :class:`types.MappingProxyType` so callers cannot mutate it
#: at runtime — a defensive complement to the frozen-dataclass values.
COMPLIANCE_EXTENSION_MAP: Final[Mapping[str, ComplianceExtensionSpec]] = (
    MappingProxyType(_COMPLIANCE_EXTENSION_MAP_RAW)
)


# ─────────────────────────────────────────────────────────────────────────────
# Base-field inventory — the 10 always-required fields.
# ─────────────────────────────────────────────────────────────────────────────
#: The 10 base fields the seller must populate before ``onboarding_complete``
#: can flip True (9 Legal Metrology + ``country_of_origin``).  Importer
#: fields are EXCLUDED from this list per §8.F + the ORM (they remain
#: nullable in V1 since many domestic sellers do not import).
#:
#: Used by:
#:   - :func:`service.get_required_fields` — drives the wizard's `base_fields`.
#:   - :func:`service._recompute_onboarding_complete` — counts present-vs-required.
#:   - :class:`schemas.ComplianceBlockResponse` — same 10 names, cross-module.
BASE_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "manufacturer_name",
    "manufacturer_address",
    "manufacturer_pincode",
    "packer_name",
    "packer_address",
    "packer_pincode",
    # importer_* are documented as OPTIONAL — they are tracked for
    # display/completeness UX but do not block onboarding.
    "country_of_origin",
)

#: The full list of base fields the wizard renders (including the optional
#: importer trio).  ``base_total_count`` in :class:`ProfileCompleteness` is
#: ``len(BASE_FIELD_NAMES) == 10`` per §8.F.
BASE_FIELD_NAMES: Final[tuple[str, ...]] = (
    "manufacturer_name",
    "manufacturer_address",
    "manufacturer_pincode",
    "packer_name",
    "packer_address",
    "packer_pincode",
    "importer_name",
    "importer_address",
    "importer_pincode",
    "country_of_origin",
)


__all__ = [
    "BASE_FIELD_NAMES",
    "BASE_REQUIRED_FIELDS",
    "COMPLIANCE_EXTENSION_MAP",
    "ComplianceBlock",
    "ComplianceExtensionSpec",
    "ProfileCompleteness",
    "SellerProfile",
]
