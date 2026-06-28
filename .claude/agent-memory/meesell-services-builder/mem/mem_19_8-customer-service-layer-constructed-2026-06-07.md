## §8 customer service layer CONSTRUCTED (2026-06-07)

### Scope
Solo sub-session `meesell-backend-construction-8-customer-1` — step 1 of 2 (router lands in api-routes-builder step 2). Built the seller-profile service layer + 5 unit tests + 2 integration tests per §8 (LOCKED 2026-06-05) + master rulings (2026-06-07).

### Files created (8)

Source (6):
- `backend/app/modules/customer/__init__.py` — package shell; router NOT mounted in step 1.
- `backend/app/modules/customer/domain.py` — 4 frozen dataclasses (`SellerProfile`, `ComplianceBlock`, `ProfileCompleteness`, `ComplianceExtensionSpec`) + `COMPLIANCE_EXTENSION_MAP` (11 keys, MappingProxyType wrapped, Beauty's 6 super_ids share ONE Spec instance). Also `BASE_FIELD_NAMES` (10) + `BASE_REQUIRED_FIELDS` (7 blocking).
- `backend/app/modules/customer/exceptions.py` — 6 CustomerError subclasses: `ProfileNotFoundError` (404), `InvalidPincodeError` (422), `InvalidSuperCategoryError` (422), `SuperCategoryNotDeclaredError` (404), `ComplianceExtensionMissingFieldsError` (422), `ProfileIncompleteForCategoryError` (422). 3-segment validation_message_ids per §5A.H.
- `backend/app/modules/customer/schemas.py` — SCAFFOLD: 6 Pydantic v2 models (`SellerProfileResponse`, `PatchProfileRequest`, `PatchActiveCategoriesRequest`, `PatchComplianceExtensionRequest`, `RequiredFieldsResponse`, `ComplianceBlockResponse`). `Field(pattern=r"^\d{6}$")` on all 3 pincode fields.
- `backend/app/modules/customer/repository.py` — 4 module-private async methods (`find_by_user_id`, `upsert`, `update_active_categories`, `update_compliance_extension`). Every method body has a direct `scope_to_user(` call (inlined in `upsert` to be a §19 grep anchor).
- `backend/app/modules/customer/service.py` — 9 PUBLIC async methods per §8.C: `get_profile_or_none`, `get_profile`, `upsert_profile`, `set_active_categories`, `set_compliance_extension`, `get_required_fields`, `get_compliance_block`, `get_onboarding_completeness`, `assert_eligible_for_super_id`.

Tests (2 files in modules/customer + 2 files in integration + 1 conftest):
- `backend/tests/modules/customer/conftest.py` — `db` fixture aliases `db_session` (ephemeral 5432 DB) so unit tests don't need the 5433 tunnel.
- 5 unit tests (29 sub-tests pass).
- 2 integration tests (6 sub-tests pass, both use per-test NullPool engine to dodge cross-loop Future issues).

### Tests added
| File | Sub-tests | Notes |
|---|---|---|
| test_profile_upsert_idempotency.py | 2 | First-PATCH-creates-row + user_id stable across upserts. |
| test_pincode_regex_enforcement.py | 13 | Parametrised over 8 invalid + 3 fields + valid + None. |
| test_compliance_extension_validation_per_super_id.py | 8 | 4 sync MAP shape (11 keys, Beauty shared identity, Grocery/Beauty compulsory, optional supers) + 4 async DB. |
| test_onboarding_complete_flag_recomputation.py | 3 | 6-transition lifecycle + missing-base-field + all-optional-supers. |
| test_eye_serum_case.py | 3 | ComplianceBlock has only 9 LM fields; Beauty seller still stores 9 base; Beauty Spec has no compliance_shape attr. |
| test_customer_full_onboarding_flow.py | 1 | Sign up via OTP → PATCH base → PATCH active['26'] → PATCH compliance/26 → required-fields shows completed=True. |
| test_customer_cross_module_eligibility.py | 5 | assert_eligible_for_super_id under all 5 gate combinations. |

Total: **35 customer tests PASS / 35**.
Regression sweep (227 baseline core+iam+i18n+shared): 227/227 PASS, no regressions.

### Decisions FLAGGED

D1 — **`schemas.RequiredFieldsResponse` uses `list[dict[str, Any]]` not `list[FieldSpec]`.** Pydantic v2 on Python 3.11 rejects `typing.TypedDict` (which `app/i18n/schema_contract.FieldSpec` uses); requires `typing_extensions.TypedDict`. Service-layer `_build_field_spec` constructs each dict with the §5A.C 9-key shape; `tests/test_per_field_shape_keys.py` is the schema-conformance gate. Forward-compat: when Python 3.12 is runtime OR i18n switches to `typing_extensions.TypedDict`, the type can be tightened.

D2 — **`db` fixture in tests/modules/customer/conftest.py aliases `db_session` (5432 ephemeral) NOT the iam-style `db` (5433 tunnel).** Customer unit tests don't need seeded categories (repository helpers bypass the categories.super_id validation). Dev tunnel at 5433 is operator-dependent (SSH session required). iam unit tests keep the 5433 dependency because they exercise tunnel-only paths.

D3 — **Unit + integration tests CANNOT run in the same pytest invocation** against the local 5432 DB because `db_engine` teardown calls `Base.metadata.drop_all`, wiping `audit_events` before integration's `iam_client` teardown tries to DELETE. Run them in separate pytest invocations (the standard CI pattern). Both pass on their own.

D4 — **`repository.upsert` inlines its SELECT** (instead of delegating to `find_by_user_id`) so the §19 grep anchor `scope_to_user(` appears at the call site of every repository mutator method body. Same query plan; explicit grep visibility.

D5 — **6 customer-specific validation_message_ids were ALREADY in messages_en.py** from the §5A construction dispatch. The brief said to "append 6 entries" assuming they weren't there; they were. Verified all 6 keys present, conform to §5A.H regex, and have natural English text.

### Key implementation patterns locked

#### COMPLIANCE_EXTENSION_MAP structure
- `dict[str, ComplianceExtensionSpec]` wrapped in `MappingProxyType` (defensive immutability).
- 11 keys: `26` (Grocery, compulsory=True), `13` (Kids, optional), `16` (Electronics, optional), `19/36/37/14/88/34` (Beauty, compulsory=True, **shared instance** for O(1) lookup), `80` (Books, optional), `30` (Home & Kitchen, optional).
- Beauty `super_id` `"19"` is the canonical anchor; 6 keys all map to the SAME Spec instance (`is` identity verified in tests).
- `required_keys` + `optional_keys` are `tuple[str, ...]` (immutable). `compulsory: bool` drives the gate.

#### `onboarding_complete` recompute algorithm
```python
all(_is_field_present(base_state[name]) for name in BLOCKING_BASE_FIELDS)
AND
for super_id in active_super_categories:
    spec = COMPLIANCE_EXTENSION_MAP.get(super_id)
    if spec and spec.compulsory:
        all(_is_field_present(ext.get(super_id, {}).get(k)) for k in spec.required_keys)
```
- `BLOCKING_BASE_FIELDS` = 6 mandatory LM fields + `country_of_origin` (importer trio is OPTIONAL — does not block).
- Recomputed on every PATCH path (B.2 / B.3 / B.4); written into `seller_profile.onboarding_complete`.
- `ProfileCompleteness.base_total_count` is always 10 (`len(BASE_FIELD_NAMES)`) for UI badge math; blocking gate uses 7.

#### Cache pattern (§8.B.5 /required-fields)
- Logical key: `customer.required_fields.{user_id}`; full key: `meesell:v{cv}:customer.required_fields.{user_id}`.
- TTL: 60s (`_REQUIRED_FIELDS_TTL_SECONDS`).
- Invalidated by `_invalidate_required_fields_cache(user_id)` after every PATCH (B.2/B.3/B.4).
- Drop-on-failure: cache delete failures logged at WARNING, never raise.

#### Cache pattern (categories.super_id distinct set)
- Logical key: `customer.super_category_set` (global; not per-user).
- TTL: 3600s, `single_flight=True` to prevent cold-cache stampede.
- Service-side cache via `core.cache.get_or_set` — `_load_super_id_set` is `SELECT DISTINCT super_id FROM categories ORDER BY super_id`.

#### Cross-loop Future avoidance (integration tests)
- DO NOT use `app.shared.database.AsyncSessionLocal` directly in integration tests that span multiple iam_client requests — the module-level engine's pool attaches to whatever loop first awaits it.
- DO use a per-test NullPool engine: `create_async_engine(DATABASE_URL, poolclass=NullPool)` inside the test body, dispose in `finally`.

#### Test ordering (local dev with 5432 only)
- Unit tests use `db_session` (drops + creates tables fresh).
- Integration tests use `iam_client` against `settings.DATABASE_URL` (5432); assume schema already present.
- Run them in SEPARATE pytest invocations to avoid `db_engine` teardown wiping the integration schema.
- For the integration suite, before the first run: `Base.metadata.create_all` + seed a `Grocery` (super_id='26') Category row.

### Hand-offs queued

- **meesell-api-routes-builder (step 2 of 2)** — `backend/app/modules/customer/router.py` with 5 endpoint handlers per §8.B; main.py `include_router(customer_router)`; update `test_app_boot_integration.py` allowed paths + route count from 11 → 16; refine schemas examples/descriptions for OpenAPI. Service signatures use 3rd-positional `db: AsyncSession`; router handlers should `Depends(get_db)` and forward.
- **§9 category** — replaces my `_get_super_id_set` cached read with a richer category-set service if needed; existing key `customer.super_category_set` is the canonical name.
- **§10 catalog** — `catalog.service.create_product` calls `customer.service.assert_eligible_for_super_id(user_id, super_id, db)` BEFORE creating any row. Raises `ProfileIncompleteForCategoryError` (422 `customer.profile.incomplete_for_category`).
- **§13 dashboard** — `dashboard.service` consumes `customer.service.get_onboarding_completeness(user_id, db)` for the completeness badge.
- **§14 export** — `export.service` consumes `customer.service.get_compliance_block(user_id, db)`; the Eye-Serum collapsed-3-column transformation happens at XLSX-write time only (NOT in customer).
- **§19 import-linter** — register the customer module's repository surface as a §16 boundary: `from app.modules.customer.repository import` MUST NOT appear under any other `app/modules/<other>/`.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §8 customer landed | project | 6 source + 5 unit + 2 integration tests; 35 customer tests + 227 regression PASS |
| COMPLIANCE_EXTENSION_MAP 11 keys | reference | Beauty's 6 super_ids share ONE Spec instance (`is` identity); 6 source rules; MappingProxyType wrapped |
| Beauty Spec compulsory=True | reference | Master ruling 4 — license_registration_number/type/expiry_date block onboarding |
| onboarding_complete recompute | reference | 6+1 base fields blocking AND every compulsory super's required_keys present |
| customer cache keys | reference | `customer.required_fields.{user_id}` TTL 60s; `customer.super_category_set` TTL 3600s single_flight |
| repository scope_to_user invariant | reference | every method body has a direct `scope_to_user(` call (upsert inlines its SELECT) |
| customer test split rule | reference | unit + integration cannot share pytest invocation against 5432 (db_engine drops tables); run separately |
| per-test NullPool engine for integration | reference | DO NOT reuse `app.shared.database.AsyncSessionLocal` across `iam_client` requests — cross-loop Future error |
| customer has no adapter egress | reference | Pure CRUD-against-Postgres + cache reads; no Gemini, MSG91, GCS, Razorpay, LangFuse per §8.H |
| FieldSpec TypedDict workaround | reference | Pydantic v2 + py3.11 rejects typing.TypedDict; use list[dict[str, Any]] until py3.12 or typing_extensions migration |


---
