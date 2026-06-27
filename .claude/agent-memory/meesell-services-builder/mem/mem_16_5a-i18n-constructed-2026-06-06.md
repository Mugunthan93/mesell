## §5A i18n CONSTRUCTED (2026-06-06)

### Scope
Solo sub-session `meesell-backend-construction-5A-i18n-1`. Built the
Presentation Layer Contract + i18n package per `BACKEND_ARCHITECTURE.md`
§5A. Six files created/extended under `backend/app/i18n/` + 4 unit-test
modules + `core/errors.py` resolver wire.

### Files created (5)
- `backend/app/i18n/messages_en.py` (NEW) — `VALIDATION_MESSAGES: dict[str, str]`
  with **54 IDs** covering iam (8) + auth-dep (3) + customer (6) + category (4)
  + catalog (8) + image (5) + pricing (5) + dashboard (1) + export (7) + core
  cross-cutting (3: tenancy/plan_guard/server) + validation.body.malformed_json.
- `backend/app/i18n/resolver.py` (NEW) — `resolve(message_id, locale="en") -> str`
  per §5A.I. Locked fallback chain: locale → en → verbatim ID. Logs
  `i18n.resolver.missing_key` at WARNING when verbatim returned (§6A/§19
  observability hook).
- `backend/app/i18n/schema_contract.py` (NEW) — TypedDicts `SchemaEnvelope`
  (§5A.B 7-key) + `FieldSpec` (§5A.C 9-key). Locked enum sets:
  `DATA_TYPE_VALUES` (8) + `PRIMITIVE_VALUES` (11) + `COMPLIANCE_SHAPE_VALUES`
  (2) + `ENUM_RESOLVER_VALUES` (3). Frozensets `ENVELOPE_KEYS` + `FIELD_SHAPE_KEYS`
  drive the conformance tests.
- `backend/app/i18n/advanced_canonical.py` (NEW) — `ADVANCED_CANONICAL_NAMES =
  frozenset({"group_id"})` exactly 1 element per §5A.F + sub-session 2 G1.
- `backend/app/i18n/__init__.py` (REWRITTEN) — module docstring now
  documents the three concerns the package owns: seed-rule modules,
  presentation contract, locale-aware message resolution.

### Files modified (1)
- `backend/app/core/errors.py` — replaced deferred-wire `_resolve_message_id`
  with direct call to `app.i18n.resolver.resolve(mid, locale="en")`.
  Locale hard-coded to `"en"` per V1 (§5A.I item 4); V1.5 will plumb
  `request.state.locale` from an Accept-Language middleware. Existing
  fallback-to-prose semantic preserved when resolver returns verbatim ID.

### Tests added (4 modules, 140 tests)
- `tests/test_messages_en_id_regex.py` — 6 test classes including
  parametrised `pytest.mark.parametrize("message_id", sorted(VALIDATION_MESSAGES.keys()))`
  regex match per §5A.H `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$` + segment
  count + no-hyphen + no-uppercase + non-empty values.
- `tests/test_resolver_fallback.py` — 7 tests: en locale hit, default
  locale = en, non-en fallback to en, unknown id → verbatim, unknown id
  non-en locale → verbatim, missing-key WARNING log assertion, entirely
  unregistered locale code → en.
- `tests/test_schema_jsonb_envelope_keys.py` — 8 tests against reference
  envelope: exactly-7-keys, parametrised key presence, types
  (list/int/str), total_count invariant, compliance_shape ∈ locked set,
  wizard_step_count ∈ [3, 8].
- `tests/test_per_field_shape_keys.py` — 14 test classes mostly
  parametrised across 6 reference fields covering all 6 data_type
  primitives + advanced + non-advanced: 9-key subset coverage,
  data_type ∈ 8 locked, primitive ∈ 11 locked, enum_resolver invariant
  (REQUIRED for dropdown, null otherwise), marker binary, canonical_name
  regex, help_text non-empty, validation_message_ids list[str],
  is_advanced allowlist enforcement, cardinality locks for each enum
  set (8/11/2/3) plus ADVANCED_CANONICAL_NAMES cardinality=1.

### Decisions FLAGGED (not in locked architecture)

D1 — **`server.internal_error` and `http.{N}` IDs stay 2-segment** despite
the §5A.H regex requiring 3-segment registry keys. Resolution: these are
DYNAMIC envelope `validation_message_id` values built at runtime in
`core/errors.py` for fall-through handlers (generic Exception, HTTPException);
they are NOT registry keys. §5A.H line 1688 says the CI Contract 10 regex
scans the **registry** (`i18n/messages_en.py`), not dynamic envelope values.
Registry has `server.internal.error` (3-segment) as the canonical entry;
the envelope-emitted ID `server.internal_error` falls through the resolver
to verbatim, then errors.py uses the supplied fallback. Tests
`test_register_error_handlers_generic_exception` + `test_register_error_handlers_http_exception`
preserved as-is — they assert on the envelope's literal `validation_message_id`
field which is independent of the registry key spelling.

D2 — **The 8 §7.G iam message IDs spec'd as 2-segment** (`auth.otp_invalid`,
`auth.refresh_invalid`, etc.) were normalised to 3-segment in the
registry (`auth.otp.invalid`, `auth.refresh.invalid`, etc.) to conform
to §5A.H. Same pattern for customer/catalog/image/export domain IDs that
the spec lists in 2-segment shorthand (e.g. `customer.profile_not_found`
→ `customer.profile.not_found`; `export.not_found` → `export.not.found`).
Spec text at §7.G/§8/§14.J uses 2-segment shorthand inline; §5A.H regex
is the authoritative lock. ESCALATION NEEDED if master prefers updating
§5A.H to permit 2-segment instead.

D3 — **Spec mentions 6-key envelope; spec example shows 7 keys.** The
construction prompt summary said "6-key envelope" but §5A.B example
envelope (lines 1533-1542) shows 7: fields, compulsory_count,
optional_count, total_count, wizard_step_count, main_sheet_label,
compliance_shape. Honoured the spec example (7). The prompt was a
summary, not a lock amendment.

D4 — **Spec key name is `validation_message_ids` (plural)**, not
`validation_message_id` (singular) the prompt summary used. Spec §5A.C
line 1587 locks `list[str]` plural. Honoured spec.

### Hand-offs queued
- §6 adapters + §6A ai_ops — NO direct consumption; resolver only fires
  on error envelope path.
- §7 iam (`meesell-auth-builder`) — every `IamError` subclass raises with
  `validation_message_id` set to one of the 8+3 IDs registered:
  `validation.phone.invalid_format`, `validation.otp.invalid_format`,
  `validation.webhook.malformed_payload`, `auth.otp.invalid`,
  `auth.otp.attempts_exceeded`, `auth.msg91.unavailable`,
  `auth.refresh.invalid`, `auth.webhook.signature_invalid`,
  `auth.token.missing`, `auth.token.expired`, `auth.user.not_found`.
  `core/errors.py` resolves to English via `resolve()`.
- §8/§9/§10/§11/§12/§13/§14 module construction — exceptions.py file
  per module raises with the IDs registered here. ID set is forward-compat:
  modules MAY add per-field dynamic IDs at services-builder dispatch time;
  the registry growth pattern is documented in §5A.J.
- §19 CI Contract 10 — `test_messages_en_id_regex.py` IS the CI gate.
- `schema_contract.py` — consumed by §9 (`category.service.fetch_schema`
  return-type hint should be `SchemaEnvelope`), §10 (`catalog.service.patch_product`
  validator dispatches on `data_type`/`enum_resolver`/`is_advanced`),
  §14 (`export.tasks._select_strategy` dispatches on `compliance_shape`).
- `ADVANCED_CANONICAL_NAMES` — consumed at seed time by
  `scripts/build_template_schemas.py` (already locked at line 84 per
  database-builder memory) and at validation time by §10 catalog
  schema-driven validator (rejects new is_advanced=True canonical_name
  not in the allowlist).

### Test counts
- New tests this dispatch: **140 PASS** (90 messages_en_id_regex
  parametrised + 7 resolver_fallback + 8 schema_envelope + 35 per_field_shape).
- Updated tests: `test_core_errors.py::test_i18n_resolver_wired` (was
  `test_i18n_resolver_deferred_wire`) — 6/6 PASS.
- Full Wave 1 regression suite: **268/268 PASS** (boot 7 + database 42 +
  shared 46 + core 39 + 4 new modules 140 + assorted = 268).
- Ruff: clean on all 7 touched files.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §5A i18n landed | project | 5 i18n package files + 1 errors wire + 4 test modules; 140 new tests; 268 regression PASS |
| i18n.resolver fallback chain locked | reference | locale → en → verbatim with WARNING log on verbatim tier; observability key = i18n.resolver.missing_key |
| 3-segment regex normalisation | reference | spec §7.G/§8/§14.J 2-segment IDs renormalised to 3-segment registry keys; §5A.H regex is the authoritative lock |
| ADVANCED_CANONICAL_NAMES locked at 1 element | reference | frozenset({"group_id"}) exactly per §5A.F + sub-session 2 G1; widening requires §5A amendment |
| SchemaEnvelope + FieldSpec TypedDicts | reference | doc-in-code §5A.B (7 keys) + §5A.C (9 keys); imported by tests, optional import for downstream module type hints |
| DATA_TYPE_VALUES (8) / PRIMITIVE_VALUES (11) / COMPLIANCE_SHAPE_VALUES (2) / ENUM_RESOLVER_VALUES (3) | reference | locked frozensets at app.i18n.schema_contract module level |

---
