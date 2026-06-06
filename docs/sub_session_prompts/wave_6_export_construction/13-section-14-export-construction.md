# Sub-Session Prompt: §14 Module `export`
# Wave 6 of 10 — CONSTRUCTION
# Specialist agents: meesell-services-builder (heavy) + meesell-api-routes-builder
# Renames session to: meesell-backend-construction-14-export-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §14 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-services-builder (heavy lift) + meesell-api-routes-builder agents operating in a dedicated construction sub-session for MeeSell §14 (Module `export`).

§14 is the **most cross-module module** (consumes customer/category/catalog/image) AND the **EASIEST V1.5 extraction target** per §2.8. M10 Philosophy (Meesho-format knowledge locked inside this module) lives here.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §14 Module `export` — 2 endpoints + 9-step Export Adapter + 15 golden round-trip fixtures
- Specialist agents: meesell-services-builder (HEAVY — 9-step Export Adapter pipeline + ComplianceStrategy + alias reverse map + Layer 3 guardrail + Celery task + 15 fixtures) + meesell-api-routes-builder (2 endpoints + schemas)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-14-export-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §14 — A through M (esp. §14.B 2 endpoints: POST initiate xlsx + GET poll/download; §14.C 9-step pipeline service layer; §14.D repository; §14.E Celery task `@shared_task(name="export.generate")` with 9-step pipeline; §14.F internal domain types incl. MarketplaceExportAdapter ABC + MeeshoExportAdapter concrete + ComplianceStrategy ABC + StandardComplianceStrategy 9→9 + CollapsedComplianceStrategy 9→3 + XlsxColumnSpec + XlsxRowSpec frozen dataclasses + ExportSnapshot; §14.G schemas; §14.H 7+ exception classes incl. ExportEnumValidationError (Layer 3); §14.I 4 adapter usages incl. GCS export bucket; §14.J cross-cutting incl. M10 forbidden symbols ONLY here + ai_ops Layer 3 enum re-validation; §14.K test plan + 15 golden round-trip fixtures coverage matrix).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0.G §12.2 (typo restore via field_aliases), §0.G §12.6 (CollapsedComplianceStrategy 9→3), §0.H M10 (Meesho leak rules), §4 (core/), §5 (shared/), §6.D (gcs adapter), §6A.E (Layer 3 guardrail — enum re-validation at XLSX emission), §8 customer (CONSTRUCTED; consumes `get_compliance_block`), §9 category (CONSTRUCTED; consumes `fetch_schema` + `get_field_enum`), §10 catalog (CONSTRUCTED; consumes `get_product_for_export`), §11 image (CONSTRUCTED; consumes `get_image_bytes`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §5.5 (Export Adapter entire), §5.7 (round-trip + 15 fixtures), §11.7 (`user_id` FK on exports), §12.2 (typo restore via field_aliases.for_xlsx_export), §12.6 (CollapsedComplianceStrategy).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md`.

5. `.claude/agents/meesell-services-builder.md`, `meesell-api-routes-builder.md`. Optionally consult `meesell-xlsx-parser` memory (DATA track) for XLSX format gotchas; do NOT dispatch them (DATA track).

6. Memory files.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1-5 CONSTRUCTED — esp. §8, §9, §10, §11).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.C:

```
backend/app/modules/export/
├── __init__.py
├── router.py            # 2 endpoints
├── service.py           # 9-step Export Adapter pipeline
├── repository.py        # PRIVATE; scope_to_user; exports table append-only
├── schemas.py           # ExportInitiateRequest, ExportInitiateResponse, ExportStatusResponse
├── domain.py            # MarketplaceExportAdapter ABC + MeeshoExportAdapter + ComplianceStrategy ABC + StandardComplianceStrategy + CollapsedComplianceStrategy + XlsxColumnSpec + XlsxRowSpec + ExportSnapshot
├── exceptions.py        # 7+ exception classes per §14.H incl. ExportEnumValidationError (Layer 3), ProductNotReadyError, FrontImageMissingError, ComplianceStrategyError, RoundTripMismatchError
└── tasks.py             # @shared_task(name="export.generate") Celery task; 9-step pipeline orchestration
```

NOTE: `tasks.py` is one of only 2 modules with a `tasks.py` per §3.C (the other is `image`).

Plus: register `export_router` in `backend/app/main.py`. `workers/celery_app.py` `include` list extended with `"app.modules.export.tasks"` (final population in §18 Celery construction).

Plus: 15 golden round-trip fixtures land at `backend/tests/integration/golden_round_trip/fixture_NN_<name>.json` per `MVP_ARCH §5.7.4` shape.

Locked invariants:
- 2 endpoints: `POST /api/v1/products/{id}/export-xlsx` (initiate), `GET /api/v1/exports/{id}` (poll status + download URLs).
- 9-step pipeline per §14.C:
  1. Load ExportSnapshot from `catalog.get_product_for_export(product_id, user_id)`.
  2. Load ComplianceBlock from `customer.get_compliance_block(user_id)`.
  3. Load schema from `category.fetch_schema(category_id)`.
  4. Compliance strategy dispatch via `compliance_shape` → Standard 9→9 OR Collapsed 9→3.
  5. Enum translation (canonical → meesho) per `category.fetch_xlsx_aliases`.
  6. Column reordering to match `schema_jsonb.fields[]` position.
  7. Alias restoration (typo restore per `field_aliases.for_xlsx_export=TRUE`).
  8. XLSX write via openpyxl; ZIP pack with images if `xlsx_with_images` format.
  9. `_round_trip_validate` — re-parse the XLSX and assert byte-equal canonical match.
- M10 forbidden symbols (`meesho_column_header`, `meesho_column_index`, `enum_codes_map`) MUST appear ONLY in `modules/export/*` and `adapters/gcs.py`. The §19 custom AST scanner (Contract 9) enforces this.
- Layer 3 guardrail: at step 5, unknown canonical-to-meesho enum → raise `ExportEnumValidationError` per §6A.E + `MVP_ARCH §9.7`.
- ABC + concrete pattern: `MarketplaceExportAdapter` ABC + V1 `MeeshoExportAdapter` concrete (V2 marketplaces are sibling concretes — V1.5 prep).
- `CollapsedComplianceStrategy` 9→3 — combines manufacturer/packer/importer into 3 "Details" columns per `MVP_ARCH §12.6` separator-and-empty-drop rules.
- GCS path: `meesell-exports/{user_id}/{export_id}.xlsx` and `.zip`.
- Celery task name: `"export.generate"`; max retries 2; sync task with `asyncio.run` for internals.
- Audit events emitted via direct ORM write inside Celery worker (no request-close hook).

Construction protocol:

1. **Tests first** per §14.K (10 unit + 3 integration + 15 golden fixtures):

   **Unit** (`backend/tests/modules/export/`):
   - `test_ownership_gate` — POST `/products/{other_user_product}/export-xlsx` → 404.
   - `test_product_status_check` — product `status="draft"` → 422.
   - `test_front_image_check` — `xlsx_with_images` with no idx=1 image → 422.
   - `test_compliance_strategy_dispatch` — standard → StandardComplianceStrategy; collapsed → CollapsedComplianceStrategy; other → raises.
   - `test_standard_strategy_9_to_9` — pass-through.
   - `test_collapsed_strategy_9_to_3` — 9 fields → 3 combined columns per §14.F.
   - `test_enum_translation_known` — canonical "PE-HD" → meesho "PE-HD" (V1 identity).
   - `test_enum_translation_unknown_raises` — Layer 3 raises `ExportEnumValidationError`.
   - `test_alias_restoration_typo` — `no_of_primary_cameras` → "No. of Primiary Cameras" (typo restored).
   - `test_column_reordering` — canonical [a,b,c] reordered to [b,a,c] per schema_jsonb position.

   **Integration** (`backend/tests/integration/test_export_*.py`):
   - `test_export_full_pipeline_happy_path` — create → upload front image → POST export → poll until ready → download XLSX → openpyxl re-parse + non-empty + header row matches.
   - `test_export_blocked_by_failed_precheck` — image precheck `status="failed_precheck"` → 422.
   - `test_export_round_trip_validation_failure` — corrupt XLSX in test → `_round_trip_validate` rejects → exports row `status="failed"` + `error_code="round_trip_mismatch"`.

   **Golden fixtures** at `backend/tests/integration/golden_round_trip/`:
   - 15 fixtures per §14.K matrix: Sarees, Mobiles (typo restore), Eye-Serum (Collapsed 9→3), FSSAI Grocery, Kids Toys BIS, Books ISBN, Beauty License trio, Home & Kitchen, Compatible Models 4481-enum, Brand 2-category, is_advanced group_id, Empty optional, Weight+unit, Multi-line, Special chars.

   Fixtures: real Postgres + Valkey + GCS test bucket via dev tunnel; `ai_ops.client.call_gemini` mocked (none of 15 fixtures require AI).

2. **Implementation** per §14.B-§14.J with locked signatures. Heavy lift on `meesell-services-builder` for the Strategy classes + 9-step pipeline + alias reverse map. `meesell-api-routes-builder` for the 2 endpoint signatures.

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT use M10 forbidden symbols (`meesho_column_header`, `meesho_column_index`, `enum_codes_map`) outside `modules/export/*` or `adapters/gcs.py`.
- DO NOT skip `_round_trip_validate` (step 9) — the byte-equal canonical match is the §5.7 contract.
- DO NOT skip Layer 3 guardrail (step 5) — unknown canonical-to-meesho enum MUST raise `ExportEnumValidationError`.
- DO NOT skip `scope_to_user(user_id)` on any repository method.
- DO NOT import `customer.repository`, `category.repository`, `catalog.repository`, `image.repository` — cross-module only via service.
- DO NOT call `ai_ops.client` (export has no AI workload in V1).
- DO NOT add V2 marketplace concretes (Amazon, Flipkart, Etsy) — V1 is `MeeshoExportAdapter` only.
- DO NOT make Celery task async — sync with `asyncio.run`.
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-services-builder` — heavy lift on the 9-step pipeline + Strategy classes + alias reverse map + Celery task + 15 fixtures.
- `meesell-api-routes-builder` — 2 endpoint signatures + Pydantic schemas.

You ARE NOT permitted: any other dispatch. NOTE: you MAY read `meesell-xlsx-parser` memory for XLSX format gotchas but do NOT dispatch them — XLSX parser is DATA track.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §14)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 2 endpoints mounted per §14.B.
2. 9-step pipeline implemented; each step idempotent within `_run_export_pipeline` call.
3. `MarketplaceExportAdapter` ABC + `MeeshoExportAdapter` concrete.
4. `ComplianceStrategy` ABC + `StandardComplianceStrategy` (9→9) + `CollapsedComplianceStrategy` (9→3) concretes.
5. Layer 3 guardrail at step 5 raises `ExportEnumValidationError` on unknown enum.
6. `_round_trip_validate` at step 9 asserts byte-equal canonical match.
7. M10 forbidden symbols only in `modules/export/*` and `adapters/gcs.py` (grep-verifiable; §19 Contract 9 enforces).
8. GCS path `meesell-exports/{user_id}/{export_id}.xlsx` (grep-verifiable).
9. `tasks.py` task name `"export.generate"`; `max_retries=2`.
10. 15 golden fixtures land at `backend/tests/integration/golden_round_trip/fixture_NN_*.json`.
11. 10 unit + 3 integration + 15 fixture tests PASS per §14.K.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update both specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §14 export CONSTRUCTED ===
   Files created: modules/export/{8 files incl. tasks.py}; main.py mount; 15 golden fixtures JSON
   Tests added: 10 unit + 3 integration + 15 golden fixtures
   Decisions made: <list>
   Hand-offs: §18 celery_app.py include list update (image+export both registered); §19 CI linter Contract 9 (M10 forbidden symbols scanner) construction
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- 15-fixture round-trip validator finds a corner case the locked contract doesn't cover (e.g. special character preservation through openpyxl encoding).
- CollapsedComplianceStrategy 9→3 column header naming ambiguity.
- field_aliases.for_xlsx_export seed missing a typo-restore entry for a fixture.
- 30s P95 budget breached by ZIP packing step (escalate — may need streaming optimization).

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-14-export-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-5 CONSTRUCTED (esp. §8, §9, §10, §11).
4. Report "Context loaded. Ready to begin §14 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 6 of 10
- **Sequential dependency:** Wave 1-5 CONSTRUCTED (esp. §8 customer, §9 category, §10 catalog, §11 image).
- **Parallel-safe?:** No — Wave 6 is single-section.
- **Expected duration estimate:** ~16-22 hours (heaviest module; 15 golden fixtures + 9-step pipeline + 2 Strategy classes + Layer 3).
- **Acceptance verification by master:** (1) `grep -rn "meesho_column_header\|meesho_column_index\|enum_codes_map" backend/app/` shows hits ONLY in `modules/export/` + `adapters/gcs.py`; (2) `ls backend/tests/integration/golden_round_trip/ | wc -l` >= 15; (3) `_round_trip_validate` test PASS; (4) Layer 3 ExportEnumValidationError test PASS; (5) STATUS_BACKEND.md UPDATE block present.
