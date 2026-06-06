"""Presentation Layer Contract — ``templates.schema_jsonb`` shape lock.

Per ``BACKEND_ARCHITECTURE.md`` §5A.B/§5A.C/§5A.D/§5A.E/§5A.F, this module
documents — IN CODE — the locked shapes that three consumer modules read
from at runtime: ``category`` (serves the schema), ``catalog`` (validates
PATCH payloads), and ``export`` (round-trips canonical → meesho).

**This module is documentation-in-code.** No runtime business logic
imports the TypedDicts here for validation; they exist so that
(a) tests can assert envelope conformance against a fixture template
(``test_schema_jsonb_envelope_keys.py`` + ``test_per_field_shape_keys.py``)
and (b) IDE intellisense surfaces the contract to specialists writing
new schema-aware code in §9/§10/§14. The seed-time builder
(``scripts/build_template_schemas.py``) IS the source-of-truth writer
and validator per §5A.J — readers trust the envelope verbatim.

The shapes here are LOCKED per §5A:
  - 7 top-level envelope keys per §5A.B (the prompt's "6-key" wording is
    a summary; the spec example at §5A.B lines 1534-1542 shows 7).
  - 9 per-field keys per §5A.C.
  - 8 ``data_type`` values per §5A.C.
  - 11 ``primitive`` values per §5A.D.
  - 3 ``enum_resolver`` values per §5A.E (``"category"`` / ``"static"`` /
    ``null``).
  - 2 ``compliance_shape`` values per §5A.F (``"standard"`` /
    ``"collapsed"``).
"""

from __future__ import annotations

from typing import Final, Literal, TypedDict

# ----------------------------------------------------------------------------
# Locked enums per §5A
# ----------------------------------------------------------------------------

# §5A.C — 8 data_type values, parser-time classification.
DATA_TYPE = Literal[
    "text",
    "long_text",
    "number",
    "number_with_unit",
    "currency",
    "dropdown",
    "image",
    "address",
]

# §5A.D — 11 input primitive components (renderer-time identifier).
PRIMITIVE = Literal[
    "text_short",
    "text_long",
    "number",
    "number_with_unit",
    "currency",
    "dropdown_small",
    "dropdown_medium",
    "dropdown_large",
    "dropdown_api_search",
    "image_upload",
    "address_group",
]

# §5A.B — 2 compliance_shape values.
COMPLIANCE_SHAPE = Literal["standard", "collapsed"]

# §5A.E — 3 enum_resolver values (``None`` is the JSON null form).
ENUM_RESOLVER = Literal["category", "static", None]

# §5A.C — 2 marker values (binary tiering per MVP_ARCH §0 premise #2).
FIELD_MARKER = Literal["compulsory", "optional"]


# ----------------------------------------------------------------------------
# Per-field shape (§5A.C — 9 keys)
# ----------------------------------------------------------------------------
class FieldSpec(TypedDict, total=False):
    """One element of ``templates.schema_jsonb.fields[]`` per §5A.C.

    Required keys (every entry has them): ``name``, ``canonical_name``,
    ``marker``, ``data_type``, ``primitive``, ``help_text``,
    ``enum_resolver``, ``validation_message_ids``.

    Optional key: ``is_advanced`` (defaults ``False`` when absent — §5A.C).

    Additional keys MAY appear (forward-compat note §5A.C) — e.g.
    ``unit_suffix`` for ``number_with_unit``, or ``enum_values`` for
    ``enum_resolver == "static"`` per §5A.E. ``total=False`` lets the
    TypedDict accept those keys without complaint; the conformance test
    asserts on the 9 LOCKED keys only.
    """

    # Required keys per §5A.C (8 required + 1 optional).
    name: str
    canonical_name: str
    marker: FIELD_MARKER
    data_type: DATA_TYPE
    primitive: PRIMITIVE
    help_text: str
    is_advanced: bool  # OPTIONAL — defaults False when absent
    enum_resolver: ENUM_RESOLVER
    validation_message_ids: list[str]


#: The 9 locked per-field keys per §5A.C. Used by
#: ``test_per_field_shape_keys.py`` to assert every entry of ``fields[]``
#: carries all 9.
FIELD_SHAPE_KEYS: Final[frozenset[str]] = frozenset({
    "name",
    "canonical_name",
    "marker",
    "data_type",
    "primitive",
    "help_text",
    "is_advanced",
    "enum_resolver",
    "validation_message_ids",
})


# ----------------------------------------------------------------------------
# Top-level envelope (§5A.B — 7 keys)
# ----------------------------------------------------------------------------
class SchemaEnvelope(TypedDict):
    """Top-level ``templates.schema_jsonb`` envelope per §5A.B.

    All 7 keys are REQUIRED. The seed-time builder writes the envelope;
    readers (``category``, ``catalog``, ``export``) trust the values
    verbatim — readers MUST NOT recompute count fields (§5A.B note on
    ``compulsory_count``).

    Invariant (seed-time validated):
        ``total_count == compulsory_count + optional_count``
    """

    fields: list[FieldSpec]
    compulsory_count: int
    optional_count: int
    total_count: int
    wizard_step_count: int
    main_sheet_label: str
    compliance_shape: COMPLIANCE_SHAPE


#: The 7 locked top-level envelope keys per §5A.B. Used by
#: ``test_schema_jsonb_envelope_keys.py``.
ENVELOPE_KEYS: Final[frozenset[str]] = frozenset({
    "fields",
    "compulsory_count",
    "optional_count",
    "total_count",
    "wizard_step_count",
    "main_sheet_label",
    "compliance_shape",
})


# ----------------------------------------------------------------------------
# Locked sets — for runtime + test consumption.
# ----------------------------------------------------------------------------

#: The 8 locked ``data_type`` values per §5A.C.
DATA_TYPE_VALUES: Final[frozenset[str]] = frozenset({
    "text",
    "long_text",
    "number",
    "number_with_unit",
    "currency",
    "dropdown",
    "image",
    "address",
})

#: The 11 locked ``primitive`` values per §5A.D.
PRIMITIVE_VALUES: Final[frozenset[str]] = frozenset({
    "text_short",
    "text_long",
    "number",
    "number_with_unit",
    "currency",
    "dropdown_small",
    "dropdown_medium",
    "dropdown_large",
    "dropdown_api_search",
    "image_upload",
    "address_group",
})

#: The 2 locked ``compliance_shape`` values per §5A.B / §5A.F.
COMPLIANCE_SHAPE_VALUES: Final[frozenset[str]] = frozenset({
    "standard",
    "collapsed",
})

#: The 3 locked ``enum_resolver`` values per §5A.E. ``None`` is the JSON
#: ``null`` (Python ``None``) — included as a literal in the frozenset
#: typed against ``object`` to allow the runtime check.
ENUM_RESOLVER_VALUES: Final[frozenset[object]] = frozenset({
    "category",
    "static",
    None,
})


__all__ = [
    "COMPLIANCE_SHAPE",
    "COMPLIANCE_SHAPE_VALUES",
    "DATA_TYPE",
    "DATA_TYPE_VALUES",
    "ENUM_RESOLVER",
    "ENUM_RESOLVER_VALUES",
    "ENVELOPE_KEYS",
    "FIELD_MARKER",
    "FIELD_SHAPE_KEYS",
    "FieldSpec",
    "PRIMITIVE",
    "PRIMITIVE_VALUES",
    "SchemaEnvelope",
]
