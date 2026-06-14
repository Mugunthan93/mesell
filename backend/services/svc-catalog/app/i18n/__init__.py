"""i18n — Versioned rule modules + presentation contract + message registry.

This package owns three concerns per ``BACKEND_ARCHITECTURE.md`` §3.H and
§5A:

1. **Versioned seed-rule modules** that drive the shape of
   ``templates.schema_jsonb`` at seed time:
     - :mod:`app.i18n.step_assignment` — wizard step-id dispatch
       (``STEP_ASSIGNMENT``, ``STEP_ORDER``, ``assign_step``).
     - :mod:`app.i18n.primitive_classifier` — ``primitive`` inference
       (``classify_primitive`` + constants).
   Any edit to a rule module MUST: (a) bump the module's ``*_VERSION``
   constant, (b) trigger a re-run of ``scripts/seed_all.py`` against the
   relevant environment, (c) ensure the regression tests still pass.

2. **Presentation Layer Contract** — locked shape declarations
   consumed by ``category`` / ``catalog`` / ``export`` modules:
     - :mod:`app.i18n.schema_contract` — ``SchemaEnvelope`` TypedDict
       (§5A.B 7-key envelope) + ``FieldSpec`` TypedDict (§5A.C 9-key
       per-field shape) + locked enums (``DATA_TYPE`` 8 / ``PRIMITIVE``
       11 / ``COMPLIANCE_SHAPE`` 2 / ``ENUM_RESOLVER`` 3).
     - :mod:`app.i18n.advanced_canonical` — ``ADVANCED_CANONICAL_NAMES``
       allowlist (V1 locked at ``{"group_id"}`` per §5A.F + D2).

3. **Locale-aware message resolution** — the single import surface every
   error/exception path uses (per §5A.I):
     - :mod:`app.i18n.messages_en` — ``VALIDATION_MESSAGES`` registry
       (English; V1 ships English only).
     - :mod:`app.i18n.resolver` — :func:`app.i18n.resolver.resolve`
       (``message_id``, ``locale``) → resolved string with the locked
       fallback chain (locale → en → verbatim ID).
     - V1.5 will add ``messages_ta.py`` / ``messages_hi.py`` (§3.H +
       §5A.J — placeholders only; specialists do NOT create them in V1).

Modules a consumer might import:
    from app.i18n.resolver import resolve
    from app.i18n.schema_contract import (
        SchemaEnvelope, FieldSpec, ENVELOPE_KEYS, FIELD_SHAPE_KEYS,
        DATA_TYPE_VALUES, PRIMITIVE_VALUES,
        COMPLIANCE_SHAPE_VALUES, ENUM_RESOLVER_VALUES,
    )
    from app.i18n.advanced_canonical import ADVANCED_CANONICAL_NAMES
"""
