## catalog-form schema DTO mapper (2026-06-16, branch feature/catalog-form-fix, worktree /tmp/mesell-wt/catalog-form-fix)

### Scope / root cause
Catalog-form UI bugs (#1/#3 blank labels + "undefined", #2 dead dropdowns). `category.service.fetch_schema`
shipped the RICH at-rest §5.6.1 field shape (25 keys: canonical/display/export layers) VERBATIM. That shape
has NO `name`/`help_text`/`enum_resolver`/`validation_message_ids` — but the §5A.C WIRE contract (9 keys) and the
FE adapter both expect them. Two broken consumers: FE field-schema adapter (reads dto.name/dto.enum_resolver) AND
`catalog.service.validate_product` (reads spec["enum_resolver"]/spec.get("enum_values"), defaulted "static"+[]).

### The fix (Option C — read-time projection, NOT a storage change, NOT a §5A.C amendment)
NEW `category.service.fetch_schema_dto(category_id, db)` wraps `fetch_schema` (reuses the `schema:{category_id}`
cache) and applies a pure field-level projection. Storage stays RICH; the wire shape is materialized at read time.
- `_map_field_to_dto(rich)`: name←display_label["en"] (fallback `canonical_name.replace("_"," ").title()` — NEVER
  empty); help_text←display_help["en"] (fallback `f"Enter {name}."` — display_help is None when seed had no help);
  enum_resolver derived (see below); validation_message_ids←[] (rich validation_message is display text, not IDs);
  canonical_name/marker/data_type/primitive/is_advanced pass-through with defaults. Emits EXACTLY 9 keys + conditional
  enum_values; ALL other rich keys dropped.
- enum_resolver derivation: data_type!="dropdown"→None; dropdown+truthy enum_codes_map→"static" (+enum_values=list of
  map keys); dropdown+no inline map→"category" (V1 always — enum_codes_map is None at template level; per-category
  enums live in field_enum_values, FE lazy-loads, validator hits get_field_enum). enum_values surfaced ONLY when "static".
- `_map_envelope_to_dto(env)`: maps fields[] element-wise; 6 other envelope keys (compulsory_count/optional_count/
  total_count/wizard_step_count/main_sheet_label/compliance_shape) pass through UNCHANGED. Counts NEVER recomputed.

### Consumer routing (LOCKED after fix)
- GET /categories/{id}/schema (category/router.py:263) → fetch_schema_dto. SchemaResponse model UNCHANGED.
- catalog/service.py ALL 6 fetch_schema sites (464/507/621/801/987/1059) → fetch_schema_dto.
- export/service.py:452 → UNCHANGED rich fetch_schema (needs meesho_column_header/index/main_sheet_label).
- core/cache.py:232 prewarm → UNCHANGED rich fetch_schema (warms the underlying schema:{id} cache that
  fetch_schema_dto also reads; discards return value, does NOT read flat keys). This is the THIRD caller the
  task spec didn't enumerate — leaving it rich is correct.

### Test harness gotcha (IMPORTANT for future worktree sessions)
This worktree has NO .venv. System python3 is 3.9 → fails on `Mapped[str | None]` ORM annotations.
Use the MASTER tree's 3.11 venv as a TOOLCHAIN against worktree code:
`VENV=/Users/mugunthansrinivasan/Project/mesell/backend/.venv/bin/python3.11`
`cd <worktree>/backend && PYTHONPATH=$PWD <dummy env> $VENV -m pytest ...`
conftest sets APP_ENV/DATABASE_URL/VALKEY_URL/JWT_SECRET only; the other ~13 REQUIRED_FIELDS (REFRESH_TOKEN_PEPPER,
MSG91_*, RAZORPAY_*, GEMINI_API_KEY, GCS_*, LANGFUSE_*, AUDIT_PII_SALT, CORS_ALLOWED_ORIGINS) must be passed as dummy
env or config.py SystemExits at import. ruff lives at /opt/homebrew/bin/ruff (NOT in the venv).
Test file used the MIRROR-FIXTURE approach (not importing scripts.build_template_schemas) because the script imports
app.shared.config.settings + mutates sys.path at module load — spec explicitly permits mirror fixtures with a docstring
saying so. 104 passed (mapper + per-field shape); 162 across related §5A unit suite.

### Docs amended (append-only)
BACKEND_ARCHITECTURE §5A end (after §5A.J): amendment 2026-06-16 documenting read-time materialization.
DATABASE_ARCHITECTURE §4.2 (after templates.schema_jsonb who-reads-it): wizard reads flat DTO, not rich shape.

---
