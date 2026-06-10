# XLSX Export — Feature Plan

| Field | Value |
|---|---|
| Document type | Feature-level plan (planning only — zero code changes) |
| Feature slug | `xlsx-export` |
| V1 spec | `docs/V1_FEATURE_SPEC.md` §F9 (Feature 9 — XLSX Export) |
| Architecture lock | `docs/BACKEND_ARCHITECTURE.md` §14 (export module — LOCKED 2026-06-05) |
| Pipeline lock | `docs/MVP_ARCHITECTURE.md` §5.5 (Export Adapter — 9-step pipeline + round-trip contract) |
| Status | **PLAN READY** — awaiting founder review on PR |
| Authored by | master Director session (`mesell-xlsx-export-planning-session-1`) |
| Authored on | 2026-06-10 |
| Path | `docs/plans/features/xlsx-export/FEATURE_PLAN.md` |
| Related plans | `docs/plans/repo_management/MASTER_PLAN.md` · `docs/plans/microservices_migration/MASTER_PLAN.md` · `docs/plans/module_federation/MASTER_PLAN.md` · `docs/plans/features/xlsx-export/PLANNING_DISPATCH.md` |
| Out of scope | Production code (backend module, frontend feature, k8s/terraform, golden fixtures), PR template files themselves, the §14 LOCK status of `BACKEND_ARCHITECTURE.md` (already LOCKED), the V1.5 bulk-export feature, the V2 multi-marketplace adapter subclasses |

---

This document is the executable plan for the **XLSX Export** feature (V1 Feature 9). It locks every operational and scope decision needed by the four involved leads (backend, frontend, data, infra) to dispatch their specialists against. **No production code is written by this session.**

The plan is the merge gate input for the eventual eight per-group PRs that ship the feature. The `## Dispatch templates` section is the canonical copy-paste-ready Agent() prompt body that each lead pastes (with `{N}` session number filled) when dispatching their specialist.

**Pre-flight reality check (deltas vs. the dispatch prompt).** The dispatch prompt at `docs/plans/features/xlsx-export/PLANNING_DISPATCH.md` was authored **before** several architecture sections were locked. The plan below has been reconciled against the LOCKED corpus. The following deltas have been applied; each is recorded here so the founder can audit them:

| # | Dispatch prompt said | LOCKED reality | Resolution applied |
|---|---|---|---|
| 1 | `§14 export module — currently SKELETON; planning notes the §14 LOCK as a pre-code gate` | `§14 LOCKED 2026-06-05` (verified at line 5153 of `BACKEND_ARCHITECTURE.md`) | §14 LOCK is no longer a gate. Code dispatch may begin as soon as upstream prereqs (catalog-form + image-precheck) merge to `develop`. |
| 2 | `5 ComplianceStrategy variants per super-category (Fashion / Home / Beauty / Kitchen / Kids)` | `§14.F LOCKED — 2 strategy classes: StandardComplianceStrategy (3,771 templates) + CollapsedComplianceStrategy (1 Eye-Serum leaf 12378)` | Founder D1 selected "Lock §F9 + §14 LOCKED scope". The 5-variant framing is REJECTED. The 15-fixture golden coverage matrix per §14.K is the operationally correct way to cover Fashion/Home/Beauty/Kitchen/Kids/Books and edge cases. |
| 3 | `5 golden fixtures co-authored with backend (Fashion, Home, Beauty, Kitchen, Kids)` | `§14.K — 15 golden fixtures matrix: Sarees, Mobiles, Eye-Serum, FSSAI Grocery, Kids Toys, Books, Beauty License, Home Kitchen, large dropdown (4,481 values), brand-pattern, is_advanced, empty optional, weight w/ unit, multi-line, special chars` | All 15 fixtures land. xlsx-parser authors fixture JSONs; services-builder authors the pytest runner. |
| 4 | `Separate GCS bucket meesell-exports (separate from meesell-images)` | `§14.I LOCKED path `meesell-exports/{user_id}/{export_id}/sheet.xlsx`; live infra is single bucket meesell-prod-assets` | Founder D3 selected single bucket + `meesell-exports/` prefix. Full path: `gs://meesell-prod-assets/meesell-exports/{user_id}/{export_id}/sheet.xlsx`. |
| 5 | `frontend/src/app/pages/export/` (Angular 18 / Material) | `frontend/src/app/features/export/` (Angular 21 / PrimeNG 21 / Tailwind 4) per `FRONTEND_ARCHITECTURE.md` Layer 4 | All frontend file paths in §3 use the new Layer 4 location. Old Material/pages references are stripped. |
| 6 | `catalog.service.get_compliance_block_for_product cross-module call` | `§14.C LOCKED — _build_row calls catalog.get_product_for_export + customer.get_compliance_block(user_id)` (compliance lives under customer, not catalog) | Cross-module calls listed correctly in §3 and the services-builder dispatch template. |
| 7 | `image.service.get_image_bytes signature` | `§11.C LOCKED — get_image_bytes(image_id: UUID, user_id: UUID) -> bytes` (not `(product_id, user_id)` — by image_id) | services-builder dispatch template documents the exact signature. |
| 8 | `mesell-xlsx-export-{group}-session-{N}` naming convention | Confirmed against `MASTER_PLAN.md §4.1` + each lead's spec §"Session naming" | Every dispatch template carries this convention. |
| 9 | `Read docs/plans/features/feature_planning_master.md (master tracker)` (Steps 0.5 + 8.1 + 8.5) | File is **absent** as of 2026-06-10 (deleted between sessions) | Master tracker steps are SKIPPED. The plan PR is the single forward signal. If the master tracker is re-created in a parallel session, this feature's row should be backfilled to `PLAN READY`. |
| 10 | `Branch from develop; commit FEATURE_PLAN.md` (Step 8.2-8.3) | Director restriction + MeeSell rule (no nexus agents) | Master session runs git directly (the only path — no `meesell-git-manager` exists and MeeSell rule prohibits `nexus:cross-cutting:git-manager`). Branch `feature/xlsx-export/planning` is created off `develop`. |

If any of these deltas conflict with a founder mental model, raise on PR review and the plan will be amended in `## Revision history` rather than mid-flight.

---

## Decisions

### Operational decisions

#### D-A — Agent lineup

**Question:** Lock which leads and specialists work on xlsx-export.

**Locked answer:** **Confirm proposed lineup** — 4 leads + 7 to 8 specialists (scraper-maintainer conditional on Meesho template drift). AI track explicitly omitted per §14.A "NO AI track collaboration — export is deterministic transformation".

The full mapping is enumerated in §4 (Agent lineup).

#### D-B — Branch creation timing

**Question:** When are `feature/xlsx-export` (parent) and `feature/xlsx-export/{group}` branches created?

**Locked answer:** **Defer per master plan §1.2.** Only `feature/xlsx-export/planning` is created in this session (off `develop`, holds this FEATURE_PLAN.md). The parent integration branch `feature/xlsx-export` and the four per-group branches are created at **code-dispatch time** by each group's lead. This avoids the 14-day stale-branch flag per master plan §1.4 and matches the strangler-fig branch lifecycle invariants.

**Branch creation order (when code dispatch begins):**

```
Step 1 (founder OR backend lead — whoever dispatches first):
  git checkout develop && git pull
  git checkout -b feature/xlsx-export       # parent — created ONCE

Step 2 (each lead at specialist-dispatch time):
  git checkout feature/xlsx-export && git pull
  git checkout -b feature/xlsx-export/backend     # ← backend lead
  # OR
  git checkout -b feature/xlsx-export/frontend    # ← frontend lead
  # OR
  git checkout -b feature/xlsx-export/data        # ← data lead
  # OR
  git checkout -b feature/xlsx-export/infra       # ← infra lead (self-dispatch — standalone)
```

#### D-C — Cross-agent memory broadcast protocol

**Question:** Specialists work on multiple features. Without proactive broadcast, a specialist dispatched on xlsx-export months from now walks in blind. CLAUDE.md NON-NEGOTIABLE rule #4 prohibits cross-writes to other agent memories. How do we propagate awareness?

**Locked answer:** **Self-broadcast at plan merge.** The plan PR (this document) lists the four involved leads as reviewers — reading the PR IS the first awareness pass. After merge, each lead self-dispatches a short memory-update session (no specialist needed) to:

1. Append a one-line entry to their own `MEMORY.md`:
   `[xlsx-export queued](../../docs/plans/features/xlsx-export/FEATURE_PLAN.md) — V1 Feature 9; awaits catalog-form + image-precheck merge; my role per FEATURE_PLAN.md §4`
2. Add a row to `docs/status/feature_board_{domain}.md`:
   `| xlsx-export | — | PENDING | — | YYYY-MM-DD | depends on catalog-form + image-precheck | See docs/plans/features/xlsx-export/FEATURE_PLAN.md |`

Specialists are NOT pre-notified. Awareness reaches each specialist at first dispatch — every dispatch template in §7 below embeds the path to this plan in its "Mandatory reads" section. This is the **single broadcast surface** — specialists discover xlsx-export by being dispatched on it, and the dispatch template self-describes the feature.

The protocol is operationalised in §9 (Cross-agent broadcast protocol).

### Scope decisions

#### D1 — Scope confirmation

**Question:** Lock V1 §F9 + §14 LOCKED scope (single-product; 2 strategies; 15 golden fixtures; dual-suite Excel + LibreOffice; ≤15s budget; multi-error validation; 422 for missing category; block on image precheck not-yet-pass; retry on failure; 1h signed URL).

**Locked answer:** **Lock §F9 + §14 LOCKED scope** — verbatim. Every clause below is binding:

- **Single product per export.** V1 ships `POST /api/v1/products/{id}/export-xlsx` — one product per call. V1.5 bulk-export is explicitly deferred per V1 spec §1 + `BACKEND_ARCHITECTURE.md §14.A`. Backend's `_write_xlsx` step (§14.C step 8) writes header + 1 data row in V1; V1.5 expands to `list[XlsxRowSpec]`.
- **2 ComplianceStrategy classes per §14.F LOCKED:**
  - `StandardComplianceStrategy` — 3,771 templates (pass-through 9 compliance fields → 9 XLSX columns).
  - `CollapsedComplianceStrategy` — 1 template (Eye-Serum leaf 12378 per §0.G §12.6 founder ruling). 9 compliance fields → 3 combined "Details" columns concatenated with `, ` (comma-space) separator; empty input fields dropped from the concatenation per §14.F.
- **15 golden roundtrip fixtures per §14.K** — covers Sarees, Mobiles (typo restore), Eye-Serum (Collapsed strategy), FSSAI Grocery (super_id=26), Kids Toys (super_id=13), Books (super_id=80, optional ISBN), Beauty License (super_id subset), Home Kitchen (super_id=30 conditional license), Large dropdown (4,481 Compatible Models values), Brand-pattern (same canonical name across 2 categories), is_advanced field (`group_id`), empty optional field, number-with-unit (`weight: 500 g` split-column), multi-line text (`description` with newlines), special characters (ampersand + em-dash + escaped double-quote).
- **XLSX opens cleanly in BOTH Excel and LibreOffice.** Non-negotiable. Tests pass on both. Manual smoke pre-staging-flip covers both.
- **Image ZIP filenames match XLSX image-reference column.** Filename convention from `MEESHO_CATEGORY_INTELLIGENCE.md` + each variant's image_filename_template. Verified inside `_round_trip_validate` (step 9) per §14.K test 12 + test 15.
- **Generation ≤15s for 1 product with 6 images.** Per V1 §F9. Hard ceiling 30s per `MVP_ARCH §5.5.10`. Performance budget table (`MVP_ARCH §5.5.10`): pipeline steps 1-7 ~500ms; XLSX gen step 8 ~200ms; round-trip step 9 ~500ms; image ZIP ~3-5s; GCS upload ~1-2s; **total ~5-9s** with headroom for cold-cache schema fetch + Brand-pattern enum lookup on first call.
- **Multi-error validation blocks export.** Initiate endpoint runs all four prereq checks (ownership + product.status=='ready' + front image present + ComplianceStrategy dispatchable) and returns a SINGLE 422 response listing every failure — not the first one. Per `V1_FEATURE_SPEC.md §F9` "validation blocks export with clear error list (Title missing, 2 images missing)".
- **422 for missing category template.** When `category.fetch_schema(category_id)` returns no entry OR `templates.compliance_shape` is unrecognised, return 422 `export.product_not_ready` per §14.B.1 (NOT a new `export.category_not_supported` code — the existing taxonomy is sufficient; the founder may revisit this if a separate code is needed).
- **Block on image precheck not-yet-pass.** Per §14.B.1 step 3: `xlsx_with_images` format requires at least 1 image with `idx=1` AND `status='ready'` — verified via `image.service.list_images`. If precheck is still pending OR failed, return 422 `export.front_image_missing`.
- **Failed generation → mark failed, allow retry, idempotent.** A second POST on the same `product_id` opens a NEW `exports` row with a fresh UUID. The previous failed row stays in the table for audit. Idempotency is at the seller-experience level (re-clicking "Generate XLSX" works), NOT at the row level (no UPSERT). Partial GCS uploads from failed runs are NOT cleaned up in V1 per §14.E + §14.L (V1.5 cleanup pass).
- **Signed URL TTL = 1h.** Per `BACKEND_ARCHITECTURE.md §6.D + §14.B.2`. Frontend re-polls to refresh expired URLs (the upstream GCS objects are stable; only signatures rotate).

The dispatch prompt's "5-per-super-category strategies" framing is **REJECTED** — it contradicts §14.F LOCKED and would force a §14 amendment for no engineering gain (the 15-fixture matrix already covers cross-category coverage with higher precision).

#### D2 — Feature flag posture

**Question:** When does FEATURE_XLSX_EXPORT_ENABLED flip to `true` in staging?

**Locked answer:** **All fixtures green + manual Meesho upload.** Specifically:

- **Flag name:** `FEATURE_XLSX_EXPORT_ENABLED` (per master plan §3.2 backend feature-flag convention).
- **Dev environment:** `true` always. The route handler is unguarded in dev so specialists can test integration end-to-end.
- **Staging environment:** `false` UNTIL **both** conditions hold simultaneously:
  1. **Golden roundtrip CI gate (gate-5) is green on ALL 15 fixtures** for at least 3 consecutive runs on `develop` HEAD.
  2. **Manual Meesho supplier-panel upload verified.** Founder (or designated tester) downloads a generated XLSX from a `dev`-namespace export, uploads to a real Meesho supplier-panel test account, and Meesho QC accepts the listing. Founder records this in `STATUS_BACKEND.md` Updates Log with the test product_id + listing_id.
- **When disabled (`false`):** `POST /api/v1/products/{id}/export-xlsx` returns 404 (the route handler short-circuits before any validation). The `/catalogs/:id/export` route on the frontend renders an "Export temporarily disabled" placeholder via `featureFlagGuard` (per master plan §3.2 frontend convention).
- **Production:** V1.5 scope per master plan §3.4 — flag will be removed when the feature ships to `main`.

Carrying the flag past one release into V1.5 generates a debt-item entry in `STATUS_BACKEND.md` blockers section per master plan §3.2.

#### D3 — Priority ordering + GCS bucket alignment

**Question:** xlsx-export ships LAST among V1 features (depends on catalog-form + image-precheck). What is the GCS bucket scheme?

**Locked answer:** **Single bucket `meesell-prod-assets` + `meesell-exports/` prefix.**

**Priority ordering (locked):**

- xlsx-export is the **last V1 feature to begin code dispatch**. It depends on:
  - `catalog-form` merging — supplies `catalog.service.assert_product_ownership` + `catalog.service.get_product_for_export` + `products.fields_jsonb` + `products.status='ready'` state machine.
  - `image-precheck` merging — supplies `image.service.get_image_bytes(image_id, user_id) -> bytes` + `image.service.list_images` + `product_images.status='ready'` precondition.
- Until both upstream features have merged to `develop`, this plan stays in `PLAN READY` status. The leads can pre-load context (read this plan, append the §2.1 D-C memory entry) but specialist dispatch is gated.
- The §14 LOCK is satisfied (2026-06-05). It is NO LONGER a pre-code blocker — the dispatch prompt's framing of this is OUTDATED.

**GCS bucket scheme (locked):**

| Object | Full GCS path |
|---|---|
| XLSX | `gs://meesell-prod-assets/meesell-exports/{user_id}/{export_id}/sheet.xlsx` |
| Image ZIP | `gs://meesell-prod-assets/meesell-exports/{user_id}/{export_id}/images.zip` |
| Source images (read-only by export) | `gs://meesell-prod-assets/{user_id}/{product_id}/{idx}.jpg` (existing convention per infra D1) |

- Single bucket `meesell-prod-assets` (live SSOT per infra-builder D1 + Phase A migration).
- Path prefix `meesell-exports/` carries the §14.I path semantics inside the bucket.
- **Lifecycle policy:** 30-day delete rule applied to `meesell-exports/*` prefix (objects auto-deleted after 30 days from creation; sellers are expected to download their export within minutes — 30 days is the cleanup window for orphaned objects).
- **IAM bindings:** existing backend SA + worker SA already have `roles/storage.objectAdmin` on the bucket — NO new IAM bindings required. (This is the cost-saver vs. the "separate bucket" option.)
- **Tenancy:** path-prefix `{user_id}` is the structural enforcement at the object-store layer per §14.J — defence-in-depth alongside `core/tenancy.scope_to_user` at the repository layer + `catalog.service.assert_product_ownership` at the service layer.

The **§14.I literal reading of "separate bucket meesell-exports"** is amended to "single bucket meesell-prod-assets, prefix meesell-exports/" — this delta gets a one-line note in the §14 sentinel block at code-dispatch time (services-builder writes the note in their PR body).

---

## Agent lineup

Per D-A. Four leads + 7 to 8 specialists. AI track explicitly omitted.

| Lead | Specialists dispatched | What each specialist codes |
|---|---|---|
| `meesell-backend-coordinator` | `meesell-services-builder`, `meesell-api-routes-builder`, `meesell-database-builder` | **services-builder (HEAVY):** entire Export Adapter — 9-step pipeline orchestrator + 11 worker-internal helpers per §14.C; 2 ComplianceStrategy concrete classes + `MeeshoExportAdapter` per §14.F; 7 exception classes per §14.H; Layer 3 hallucination guardrail wired at step 5; openpyxl XLSX writer + `_round_trip_validate`; image ZIP packager via `image.service.get_image_bytes`; GCS upload via `adapters.gcs.upload_bytes`; Celery task wiring per §14.E; the 7 i18n keys in `messages_en.py`; the pytest runner for the 15 golden fixtures; the troubleshooting runbook. **api-routes-builder:** 2 route handlers (POST + GET) per §14.B; the 4 Pydantic wire schemas per §14.G; FEATURE flag gate at the POST entry; rate-limit decorator `@rate_limit(scope="export_initiate", limit="10/h", key="user_id")` per §14.J; router test suite. **database-builder:** `exports` table SQLAlchemy ORM model per `MVP_ARCH §2.5`; the Alembic migration with up + down per master plan §3.3; `scope_to_user(user_id)` enforced on the `exports.user_id` tenancy column per §15.B. |
| `meesell-frontend-coordinator` | `meesell-angular-component-builder`, `meesell-angular-service-builder` | **angular-component-builder:** `ExportPageComponent` (page-level) + `ExportProgressComponent` (polling-status sub-component); under `frontend/src/app/features/export/` per FRONTEND_ARCH Layer 4; uses `mee-*` primitives from `@mee/ui` (button, card, page-header, progress-bar, status-badge) — zero direct PrimeNG imports; multi-error validation render on 422 (`mee-toast` + an inline error list); download CTA when status flips to `ready`; component tests. **angular-service-builder:** `ExportService.initiate(productId)` + `ExportService.pollStatus(exportId)` with exponential backoff polling (1s → 2s → 4s, capped at 60s wall time matching the §F9 30s hard budget + headroom); TypeScript model file mirroring backend Pydantic schemas; error handling for 422 (validation blocked → render error list), 503 (transient GCS failure → retry once then surface), 404 (flag-disabled → render placeholder). |
| `meesell-data-engineer` | `meesell-xlsx-parser`, `meesell-scraper-maintainer` (conditional) | **xlsx-parser:** 15 golden fixture JSON files per Code surfaces §Backend + §14.K (each fixture is `{input_snapshot, expected_xlsx_canonical}` per §14.K format); fixture README; verification that `templates.schema_jsonb` is comprehensively seeded for the 15 coverage points (each fixture's category_id resolves to a non-empty schema with `meesho_column_header`, `meesho_column_index`, `enum_codes_map`, `compliance_role`, `compliance_shape`); verification that `field_aliases.for_xlsx_export = TRUE` covers the typo restore cases (`no_of_primary_cameras` → `No. of Primiary Cameras`); verification that `field_enum_values.enum_entries` covers all 291 Brand-pattern categories. **scraper-maintainer (CONDITIONAL):** dispatched ONLY if the quarterly Meesho refresh (post `2026-06-04` snapshot) shows template drift on any of the 15 fixture categories — re-scrape, update affected `templates.schema_jsonb` rows, regenerate the affected fixture's `expected_xlsx_canonical`. Default: NOT DISPATCHED for V1. |
| `meesell-infra-builder` (standalone) | — (no specialists; lead self-dispatches) | Add `export` Celery queue to worker deployment manifest (dev + staging mirror); add GCS lifecycle rule on `meesell-prod-assets` bucket for `meesell-exports/*` prefix (30-day delete); append xlsx-export runbook paragraph to `INFRASTRUCTURE_PLAYBOOK.md`. NO new bucket. NO new IAM binding. NO new K3s Service. |
| `meesell-ai-coordinator` | (no work — explicitly omitted) | Per §14.A LOCKED. The Layer 3 guardrail is deterministic dictionary lookup, not an AI workload. AI lead is NOT a reviewer on this plan PR. |

**Total: 4 active leads + 6 firm specialists + 1 conditional specialist = 7 firm dispatches + 1 conditional.**

---

## Code surfaces

The full enumeration of files this feature creates (NEW) or modifies (MODIFY). Grouped by group; this becomes the diff scope when leads brief their specialists.

### 3.1 Backend (group: `backend`, lead: `meesell-backend-coordinator`)

| File | NEW / MODIFY | Owned by specialist | Purpose |
|---|---|---|---|
| `backend/app/modules/export/__init__.py` | NEW | services-builder | Module init |
| `backend/app/modules/export/router.py` | NEW | api-routes-builder | 2 route handlers per §14.B (POST + GET) |
| `backend/app/modules/export/schemas.py` | NEW | api-routes-builder | Pydantic v2 wire models: `ExportRequest`, `ExportInitiatedResponse`, `ExportResponse`, `ExportStatusSummaryResponse` per §14.G |
| `backend/app/modules/export/service.py` | NEW | services-builder | Public surface (`initiate_export`, `get_export`, `summary`) + 11 worker-internal helpers (the 9-step pipeline + `_run_export_pipeline` + `_package_images_zip`) per §14.C |
| `backend/app/modules/export/repository.py` | NEW | services-builder | 5 module-private methods (`insert`, `find_by_id`, `update_status_ready`, `update_status_failed`, `summarize_by_products`) per §14.D |
| `backend/app/modules/export/tasks.py` | NEW | services-builder | One Celery task `export.xlsx` (bind=True, max_retries=1, retry_backoff=True) per §14.E |
| `backend/app/modules/export/domain.py` | NEW | services-builder | 5 frozen dataclasses (`Export`, `XlsxColumnSpec`, `XlsxRowSpec`, `RoundTripResult`, `ExportStatusSummary`) + 2 ABCs (`ComplianceStrategy`, `MarketplaceExportAdapter`) + 3 concrete subclasses (`StandardComplianceStrategy`, `CollapsedComplianceStrategy`, `MeeshoExportAdapter`) per §14.F |
| `backend/app/modules/export/exceptions.py` | NEW | services-builder | 7 exception classes per §14.H (`ExportNotFoundError`, `ProductNotReadyForExportError`, `FrontImageMissingError`, `ExportEnumValidationError`, `ComplianceStrategyError`, `XlsxBuildError`, `RoundTripValidationError`) |
| `backend/app/shared/models/export.py` | NEW | database-builder | SQLAlchemy ORM model for `exports` table per `MVP_ARCH §2.5` |
| `backend/app/alembic/versions/<rev>_add_exports_table.py` | NEW | database-builder | Alembic migration creating `exports` table |
| `backend/app/workers/celery_app.py` | MODIFY | services-builder | Add `"app.modules.export.tasks"` to `include=[...]` per §3.I |
| `backend/app/i18n/messages_en.py` | MODIFY | services-builder | Add 7 new `validation_message_id` strings per §14.J table (`export.not_found`, `export.product_not_ready`, `export.front_image_missing`, `export.enum_validation_failed`, `export.compliance_strategy_failed`, `export.xlsx_build_failed`, `export.round_trip_mismatch`) |
| `backend/app/main.py` | MODIFY | api-routes-builder | Register export router; add `FEATURE_XLSX_EXPORT_ENABLED` flag gate that returns 404 on POST when disabled |
| `backend/app/config.py` | MODIFY | api-routes-builder | Add `FEATURE_XLSX_EXPORT_ENABLED: bool = True` (Pydantic Settings) |
| `backend/tests/modules/export/__init__.py` | NEW | services-builder | Test module init |
| `backend/tests/modules/export/test_router.py` | NEW | api-routes-builder | Router tests — auth, rate limit, 4 prereq gates, 404 when flag disabled |
| `backend/tests/modules/export/test_service.py` | NEW | services-builder | Service tests — 10 unit tests per §14.K (ownership_gate, product_status_check, front_image_check, compliance_strategy_dispatch, standard_strategy_9_to_9, collapsed_strategy_9_to_3, enum_translation_known, enum_translation_unknown_raises, alias_restoration_typo, column_reordering) |
| `backend/tests/modules/export/test_repository.py` | NEW | services-builder | Repository tests — all 5 methods with `scope_to_user` enforcement |
| `backend/tests/modules/export/test_tasks.py` | NEW | services-builder | Celery task tests — happy path + 3 failure paths + retry logic |
| `backend/tests/modules/export/test_round_trip.py` | NEW | services-builder | Pytest runner for the 15 golden fixtures per §14.K. Loads JSON fixtures from `tests/integration/golden_round_trip/`. Powers CI gate-5. |
| `backend/tests/integration/test_export_full_pipeline.py` | NEW | services-builder | Integration test per §14.K (3 tests: happy_path, blocked_by_failed_precheck, round_trip_validation_failure) |
| `backend/tests/integration/golden_round_trip/fixture_01_sarees.json` | NEW | xlsx-parser (data) | Sarees fixture (Standard compliance baseline) |
| `backend/tests/integration/golden_round_trip/fixture_02_mobiles.json` | NEW | xlsx-parser (data) | Mobiles fixture (typo restore for `no_of_primiary_cameras`) |
| `backend/tests/integration/golden_round_trip/fixture_03_eye_serum.json` | NEW | xlsx-parser (data) | Eye-Serum fixture (Collapsed strategy 9→3) |
| `backend/tests/integration/golden_round_trip/fixture_04_fssai_grocery.json` | NEW | xlsx-parser (data) | FSSAI Grocery fixture (super_id=26 compliance extension) |
| `backend/tests/integration/golden_round_trip/fixture_05_kids_toys.json` | NEW | xlsx-parser (data) | Kids Toys fixture (optional BIS license) |
| `backend/tests/integration/golden_round_trip/fixture_06_books.json` | NEW | xlsx-parser (data) | Books fixture (optional ISBN) |
| `backend/tests/integration/golden_round_trip/fixture_07_beauty_license.json` | NEW | xlsx-parser (data) | Beauty License fixture (required license trio) |
| `backend/tests/integration/golden_round_trip/fixture_08_home_kitchen.json` | NEW | xlsx-parser (data) | Home & Kitchen appliance fixture (conditional license) |
| `backend/tests/integration/golden_round_trip/fixture_09_large_dropdown.json` | NEW | xlsx-parser (data) | Large dropdown fixture (4,481 Compatible Models values) |
| `backend/tests/integration/golden_round_trip/fixture_10_brand_pattern.json` | NEW | xlsx-parser (data) | Brand-pattern fixture (same canonical name, 2 categories) |
| `backend/tests/integration/golden_round_trip/fixture_11_is_advanced.json` | NEW | xlsx-parser (data) | is_advanced fixture (`group_id` populated) |
| `backend/tests/integration/golden_round_trip/fixture_12_empty_optional.json` | NEW | xlsx-parser (data) | Empty-optional fixture (blank cell verification) |
| `backend/tests/integration/golden_round_trip/fixture_13_weight_unit.json` | NEW | xlsx-parser (data) | Number-with-unit fixture (`weight: 500 g`) |
| `backend/tests/integration/golden_round_trip/fixture_14_multiline.json` | NEW | xlsx-parser (data) | Multi-line text fixture (`description` with `\n`) |
| `backend/tests/integration/golden_round_trip/fixture_15_special_chars.json` | NEW | xlsx-parser (data) | Special characters fixture (ampersand, em-dash, escaped double-quote) |
| `backend/tests/integration/golden_round_trip/README.md` | NEW | xlsx-parser (data) | Fixture format spec — how to author a new fixture |

### 3.2 Frontend (group: `frontend`, lead: `meesell-frontend-coordinator`)

| File | NEW / MODIFY | Owned by specialist | Purpose |
|---|---|---|---|
| `frontend/src/app/features/export/export-page.component.ts` | NEW | angular-component-builder | Page component (route `/catalogs/:id/export`); "Generate XLSX" CTA; multi-error validation render on 422 |
| `frontend/src/app/features/export/export-page.component.html` | NEW | angular-component-builder | Page template (Sakai-ng layout reference; mee-button + mee-card + mee-page-header from `@mee/ui`) |
| `frontend/src/app/features/export/export-page.component.scss` | NEW | angular-component-builder | Page-level style (Tailwind utility classes only; zero PrimeNG SCSS imports) |
| `frontend/src/app/features/export/export-page.component.spec.ts` | NEW | angular-component-builder | Component test |
| `frontend/src/app/features/export/export-progress.component.ts` | NEW | angular-component-builder | Polling-status sub-component (mee-progress-bar + mee-status-badge + download CTA) |
| `frontend/src/app/features/export/export-progress.component.html` | NEW | angular-component-builder | Sub-component template |
| `frontend/src/app/features/export/export-progress.component.spec.ts` | NEW | angular-component-builder | Sub-component test |
| `frontend/src/app/features/export/services/export.service.ts` | NEW | angular-service-builder | `initiate(productId): Observable<ExportInitiatedResponse>` + `pollStatus(exportId): Observable<ExportResponse>` (exponential backoff 1s → 2s → 4s, max 60s) |
| `frontend/src/app/features/export/services/export.service.spec.ts` | NEW | angular-service-builder | Service test |
| `frontend/src/app/features/export/models/export.model.ts` | NEW | angular-service-builder | TypeScript types mirroring backend Pydantic schemas (`ExportRequest`, `ExportInitiatedResponse`, `ExportResponse`, `ExportStatus`, `ExportFormat`) |
| `frontend/src/app/features/export/index.ts` | NEW | angular-component-builder | Barrel export |
| `frontend/src/app/app.routes.ts` | MODIFY | angular-component-builder | Register `/catalogs/:id/export` route (lazy `loadComponent` from `features/export/export-page.component`) |
| `frontend/src/app/core/services/feature-flags.service.ts` | MODIFY (if exists) OR NEW | angular-service-builder | Add `FEATURE_XLSX_EXPORT_ENABLED` flag read from build-time env per master plan §3.2 |

### 3.3 Data (group: `data`, lead: `meesell-data-engineer`)

The data track's deliverable for xlsx-export is **the 15 golden fixture JSONs** (above in §3.1 backend table — they live under `backend/tests/integration/golden_round_trip/` because pytest discovers them there) PLUS verification that the global tables (`templates.schema_jsonb`, `field_enum_values.enum_entries`, `field_aliases.for_xlsx_export`) are comprehensively seeded for all 15 coverage points.

| File | NEW / MODIFY | Owned by specialist | Purpose |
|---|---|---|---|
| (15 fixture JSONs + README) | NEW | xlsx-parser | Listed in §3.1 above — co-owned but pytest-discovered under `backend/tests/` |
| `docs/MEESHO_CATEGORY_INTELLIGENCE.md` | MODIFY (lightly) | data-engineer (lead authors) | Cross-link to xlsx-export feature — add a new §10 "Compliance shape per template" paragraph that points at `BACKEND_ARCHITECTURE.md §14.F` for the strategy contract |
| `backend/app/data/category_attributes.json` | MODIFY (if any seed gap detected) | xlsx-parser | Only modify IF the fixture authoring surfaces a gap in seed data; otherwise read-only |
| `backend/app/data/meesho_category_tree.json` | MODIFY (if any seed gap detected) | xlsx-parser | Same posture |

No new top-level data files in V1. The dispatch's `backend/app/data/meesho_templates/{fashion,home,beauty,kitchen,kids}.json` framing is **REJECTED** — the per-template data already lives in `templates.schema_jsonb` (DB column) per §14.F + §5.5.6, not in JSON files under `app/data/`. The data track's role is to ensure the DB seed is comprehensive, not to add a parallel JSON store.

### 3.4 Infra (group: `infra`, lead: `meesell-infra-builder`, self-dispatched)

| File | NEW / MODIFY | Owned by | Purpose |
|---|---|---|---|
| `k8s/dev/worker-deployment.yaml` | MODIFY | infra-builder | Add `export` Celery queue to the worker's `args:` (the worker pod handles both `image_precheck` and `export` queues per §3.I task discovery) |
| `k8s/staging/worker-deployment.yaml` | MODIFY (mirror dev) | infra-builder | Same change in staging manifest |
| `terraform/gcs/lifecycle.tf` (if exists) OR new resource block in `terraform/gcs/buckets.tf` | MODIFY | infra-builder | Add lifecycle rule on `meesell-prod-assets` bucket — `condition.matchesPrefix = ["meesell-exports/"]; condition.age = 30; action.type = "Delete"` |
| `docs/INFRASTRUCTURE_PLAYBOOK.md` | MODIFY (lightly) | infra-builder | Add a one-paragraph entry to the runbook section describing how to inspect a stuck export Celery task (`kubectl logs deploy/worker -n dev | grep export.xlsx`) + how to verify GCS lifecycle policy applied |

No new GCS bucket. No new IAM binding. No new K3s Service. Lifecycle is the only Terraform-managed addition.

### 3.5 AI (group: `ai`)

**NONE.** Per §14.A LOCKED: "NO AI track collaboration — export is deterministic transformation; the Layer 3 hallucination guardrail per `MVP_ARCH §9.7` re-validates AI-emitted enum values at emit time, but the re-validation logic itself is deterministic dictionary lookup against `field_enum_values.enum_entries`, not AI."

The Layer 3 guardrail lives at step 5 of the pipeline (`_translate_enums` in §14.C). It is owned by services-builder, not the AI track. The AI lead (`meesell-ai-coordinator`) is NOT a reviewer on the xlsx-export plan PR.

### 3.6 Cross-cutting docs

| File | NEW / MODIFY | Owned by | Purpose |
|---|---|---|---|
| `docs/V1_FEATURE_SPEC.md` §F9 | MODIFY (post-merge) | backend lead | Append "**Implemented:** YYYY-MM-DD — PR `feature/xlsx-export` #NN" line when feature ships to `develop` |
| `docs/runbooks/xlsx-export-troubleshooting.md` | NEW | services-builder (in backend PR) | Stuck-task inspection, XLSX local-validity check (`unzip -l sheet.xlsx`), Meesho upload manual smoke procedure |
| `docs/runbooks/README.md` | MODIFY | services-builder (same PR) | Link the new runbook |
| `.github/workflows/ci.yml` | MODIFY (if gate-5 not yet wired) | services-builder (in backend PR) | Add gate-5 step: `pytest backend/tests/modules/export/test_round_trip.py --tb=short` — invoked on every backend PR touching `app/modules/export/` OR the golden fixture directory |

## Documentation deliverables

"Documented" for xlsx-export means **all** of the following exist alongside the merged code. These items are checked in the §10 acceptance gate.

### 5.1 Backend documentation

- **OpenAPI entries** auto-generated by FastAPI for:
  - `POST /api/v1/products/{id}/export-xlsx` — 202 ACCEPTED with `ExportInitiatedResponse` schema; 401 / 404 / 422 error envelopes documented with `validation_message_id` keys
  - `GET /api/v1/exports/{id}` — 200 with `ExportResponse` schema; 401 / 404 documented
- **Service-method docstrings** on every public surface in `service.py`:
  - `initiate_export` docstring documents the 4 prereqs (ownership + product.status='ready' + front image present + ComplianceStrategy dispatchable) AND the multi-error response contract
  - `get_export` docstring documents the signed-URL freshness contract (fresh URL per response, 1h TTL)
  - `summary` docstring marks it OPTIONAL / V1.5-elevation
- **Worker-internal helper docstrings** on each of the 11 helpers in `service.py` — pipeline step number, inputs, outputs, exceptions raised, the §14.C citation
- **Inline `# Layer 3 guardrail` comment** at the top of `_translate_enums` flagging the security-critical nature of the dictionary lookup
- **Runbook** at `docs/runbooks/xlsx-export-troubleshooting.md` covering: stuck Celery task inspection, XLSX local-validity check, manual Meesho upload smoke procedure, error_code interpretation cheatsheet (the 7 codes per §14.H)

### 5.2 Frontend documentation

- **Route comment** in `app.routes.ts` next to the export route: `// xlsx-export feature — feature flag FEATURE_XLSX_EXPORT_ENABLED gates the backend POST`
- **Component docstring** on `ExportPageComponent` describing the multi-error render contract (one toast + inline error list)
- **Service docstring** on `ExportService` describing the exponential backoff schedule (1s → 2s → 4s, max 60s) and the rationale (matches §F9 ≤15s target + §5.5.10 30s hard ceiling + 2× headroom)

### 5.3 Data documentation

- **Golden fixture README** at `backend/tests/integration/golden_round_trip/README.md`:
  - Fixture file format (JSON schema)
  - How to author a new fixture when a new category is added
  - Coverage matrix mapping fixture-name to the §14.K test characteristic it covers
  - How to regenerate `expected_xlsx_canonical` from a hand-crafted product
- **Light cross-link** in `MEESHO_CATEGORY_INTELLIGENCE.md` §10 (new paragraph) pointing at `BACKEND_ARCHITECTURE.md §14.F` for the 2-strategy contract

### 5.4 Infra documentation

- **Runbook paragraph** in `docs/INFRASTRUCTURE_PLAYBOOK.md` covering:
  - Worker pod scaling for the export queue (2 replicas in staging baseline; HPA on CPU per existing pattern)
  - GCS cost monitoring at projected scale (1 seller × 10 exports/month × ~5MB XLSX+ZIP = ~50MB/seller/month; 1,000 sellers ≈ 50GB/month before 30-day lifecycle kicks in)
  - How to verify lifecycle policy applied: `gsutil lifecycle get gs://meesell-prod-assets | jq '.rule[] | select(.condition.matchesPrefix[]? == "meesell-exports/")'`

### 5.5 Cross-cutting documentation

- **V1_FEATURE_SPEC.md §F9** — post-merge `**Implemented:** YYYY-MM-DD — PR #NN` stamp added by backend lead at sprint PR merge to `develop`
- **CI gate-5 (golden_roundtrip)** wired in `.github/workflows/ci.yml`:
  - Triggered on every PR touching `backend/app/modules/export/**` OR `backend/tests/integration/golden_round_trip/**`
  - Step: `pytest backend/tests/modules/export/test_round_trip.py -v --tb=short`
  - Must pass for the PR to merge
- **Troubleshooting runbook** linked from `docs/runbooks/README.md`

### Glossary

Terminology referenced by the dispatch templates and the review protocol. Authoritative source where ambiguity arises.

| Term | Meaning |
|---|---|
| 9-step pipeline | The Export Adapter's ordered transformation chain per `MVP_ARCH §5.5.4`: schema resolve → strategy select → row build → strategy apply → enum translate (Layer 3 guardrail) → column reorder → alias restore → XLSX write → round-trip validate. |
| ComplianceStrategy | The §14.F Strategy pattern — V1 has 2 concrete classes: `StandardComplianceStrategy` (3,771 templates, 9 fields pass-through) + `CollapsedComplianceStrategy` (Eye-Serum leaf 12378, 9 fields → 3 Details columns). |
| Layer 3 guardrail | The deterministic safety net at step 5 of the pipeline; dictionary lookup against `field_enum_values.enum_entries` rejects any canonical enum value not registered. Independent of AI. |
| Round-trip validation | Step 9 — re-parse the just-written XLSX with openpyxl + canonical re-map; assert equivalence with the input snapshot. Holds the line on correctness even if upstream steps drift. |
| 15-fixture matrix | The §14.K golden coverage matrix — 15 JSON fixtures testing per-category compliance + edge cases (typo restore, large dropdowns, brand patterns, is_advanced, empty optional, weight w/ unit, multi-line, special chars). |
| M10 boundary | Philosophy M10 — `meesho_column_header`, `meesho_column_index`, `enum_codes_map` exist ONLY inside `app/modules/export/`. The §19 CI linter enforces. |
| FEATURE_XLSX_EXPORT_ENABLED | The feature flag per master plan §3.2. Dev=true; Staging=false until all 15 fixtures green + manual Meesho upload accepted. |
| Self-broadcast | The D-C protocol — each lead self-updates their MEMORY.md + feature_board after the plan PR merges. No cross-writes to other agent memories (CLAUDE.md rule #4). |

---

## Branch setup

Per D-B (defer per master plan §1.2). Only `feature/xlsx-export/planning` exists today (created off `develop` for this plan doc). The parent integration branch and per-group branches are created at code-dispatch time. AI does NOT get a branch (no AI work per D-A + §14.A).

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/xlsx-export` | `develop` | Integration branch; only merge commits | Backend lead (merge approval only) |
| `feature/xlsx-export/backend` | `feature/xlsx-export` | Backend specialist work (services + api-routes + database) | Backend specialists |
| `feature/xlsx-export/frontend` | `feature/xlsx-export` | Frontend specialist work (component + service) | Frontend specialists |
| `feature/xlsx-export/data` | `feature/xlsx-export` | Data work (15 golden fixtures + seed verification) | `meesell-xlsx-parser` |
| `feature/xlsx-export/infra` | `feature/xlsx-export` | Infra work (Celery queue + GCS lifecycle + INFRASTRUCTURE_PLAYBOOK paragraph) | `meesell-infra-builder` (self-dispatch) |

### Creation commands

When the first group is ready to dispatch (gated on `catalog-form` + `image-precheck` merging to `develop` per D3), the founder OR the backend lead runs:

```bash
cd /Users/mugunthansrinivasan/Project/mesell
git checkout develop && git pull --ff-only
git checkout -b feature/xlsx-export
git push -u origin feature/xlsx-export
```

Each per-group branch is then cut at its own lead's specialist-dispatch time:

```bash
git checkout feature/xlsx-export && git pull --ff-only
git checkout -b feature/xlsx-export/backend     # backend lead's first dispatch
# OR
git checkout -b feature/xlsx-export/frontend    # frontend lead's first dispatch
# OR
git checkout -b feature/xlsx-export/data        # data lead's first dispatch
# OR
git checkout -b feature/xlsx-export/infra       # infra lead self-dispatch
```

### PR flow (coding stage)

```
┌────────────────────────────────────┐
│ feature/xlsx-export/backend        │──┐
└────────────────────────────────────┘  │
┌────────────────────────────────────┐  │  4 group PRs (lead reviews each)
│ feature/xlsx-export/frontend       │──┤  per master plan §6 — each lead
└────────────────────────────────────┘  │  approves their own group's PR to
┌────────────────────────────────────┐  │  the integration branch
│ feature/xlsx-export/data           │──┤
└────────────────────────────────────┘  │
┌────────────────────────────────────┐  │
│ feature/xlsx-export/infra          │──┘
└────────────────────────────────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │ feature/xlsx-export  │
        └──────────────────────┘
                  │
                  │  1 integration PR (founder reviews per master plan §6 V1 rule)
                  ▼
              ┌─────────┐
              │ develop │
              └─────────┘
```

### PR templates

| Group PR | Template path |
|---|---|
| `feature/xlsx-export/backend` → `feature/xlsx-export` | `.github/PULL_REQUEST_TEMPLATE/backend.md` |
| `feature/xlsx-export/frontend` → `feature/xlsx-export` | `.github/PULL_REQUEST_TEMPLATE/frontend.md` |
| `feature/xlsx-export/data` → `feature/xlsx-export` | `.github/PULL_REQUEST_TEMPLATE/data.md` |
| `feature/xlsx-export/infra` → `feature/xlsx-export` | `.github/PULL_REQUEST_TEMPLATE/infra.md` |
| `feature/xlsx-export` → `develop` (integration) | Compose summary citing all 4 group PR numbers + acceptance gate checklist (see `## Acceptance gate` below) |

### Rebase strategy

When a sibling group PR lands first on `feature/xlsx-export`, the in-flight group rebases its branch on the moved integration tip:

```bash
git checkout feature/xlsx-export/backend
git fetch origin
git rebase origin/feature/xlsx-export
# resolve conflicts (if any); typical conflict surface is i18n/messages_en.py if
# multiple groups add keys in the same file
git push --force-with-lease
```

The migration order (services-builder PR depends on database-builder PR merge, services-builder PR depends on xlsx-parser PR merge) is documented in `## Review + iteration protocol` → "Cross-lead dependencies during review".

---

## Memory protocol

Per D-C (self-broadcast at plan merge). Coding-session leads + specialists read the agent memories below at session start; the cross-agent broadcast protocol is the operational mechanism that keeps memories fresh.

### Memories the coding-session leads MUST read at start

When any coding-session sub-session opens, the lead reads:

- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` (heaviest lead)
- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md`
- `.claude/agent-memory/meesell-data-engineer/MEMORY.md`
- `.claude/agent-memory/meesell-infra-builder/MEMORY.md`

When a specialist sub-session opens, the specialist reads:

- Their own `.claude/agent-memory/meesell-{specialist-slug}/MEMORY.md`
- Their dispatching lead's `MEMORY.md` (above)
- `.claude/agent-memory/meesell-backend-coordinator/feature_xlsx-export.md` (if it exists — see §Cross-feature memos below)

### Cross-feature memos this feature consumes

`xlsx-export` is a downstream feature — it consumes contracts produced by upstream merges:

| Upstream feature | Contract consumed | Where to find it |
|---|---|---|
| `catalog-form` | `catalog.service.assert_product_ownership(product_id, user_id)`, `catalog.service.get_product_for_export(product_id, user_id)`, `products.fields_jsonb` shape, `products.status='ready'` state machine | `.claude/agent-memory/meesell-backend-coordinator/feature_catalog-form.md` (already exists per `mesell-repo-management-session-1` Step 13 broadcast) |
| `image-precheck` | `image.service.get_image_bytes(image_id, user_id) -> bytes`, `image.service.list_images(product_id, user_id)`, `product_images.status='ready'` precondition | `.claude/agent-memory/meesell-backend-coordinator/feature_image-precheck.md` (authored at image-precheck plan merge) |
| `auth-otp` | `get_current_user` dependency injection contract; JWT in-memory access pattern (FE-D5) | `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` Sessions on auth-otp |

If any of the upstream memos are absent when the xlsx-export code dispatch begins, that's a broadcast failure — the lead pauses dispatch and escalates to the founder per the §9.2 broadcast protocol below.

### Naming convention for new memos created during this feature

Use `feature_xlsx-export.md` per the convention established by `feature_catalog-form.md` in `meesell-backend-coordinator/`. NEVER `xlsx-export_feature.md` — pick one convention per feature; the `feature_*` prefix sorts grouped in the directory and matches the convention seeded in this session by the backend coordinator.

Memo lives at:

- `.claude/agent-memory/meesell-backend-coordinator/feature_xlsx-export.md` — authored by backend lead at plan merge per D-C self-broadcast; updated at each coding-session close

Other leads may author their own per-feature memos (e.g., `.claude/agent-memory/meesell-frontend-coordinator/feature_xlsx-export.md`) at their discretion — not required by D-C.

### Session-close memory entries

At each coding-session close, the active agent appends to their own `MEMORY.md`:

```markdown
## Session mesell-xlsx-export-{group}-session-{N} — YYYY-MM-DD — {one-line outcome}

- Files touched count: {N}
- Tests added: {N}; tests passing: {N}/{N}
- Decisions ratified during session: {list of D-numbers or "none"}
- Blockers carried into next session: {list or "none"}
- Next-step recommendation: {one sentence}
```

The session header MUST use this exact format so the next session's resume protocol can locate it by session name.

### Cross-agent broadcast protocol

This sub-section is the **executable plan** for the self-broadcast committed in D-C. Each step is mandatory.

#### Plan PR reviewer list

The PR for this plan (open against `develop`) lists exactly the following GitLab/GitHub reviewers:

- Founder (Mugunthan) — primary approver
- `meesell-backend-coordinator` (named reviewer / lead reviewer per master plan §5.5; the data PR template is used because data is the most-involved lead, but backend is the heaviest implementation slice)
- `meesell-frontend-coordinator` (named reviewer)
- `meesell-data-engineer` (named reviewer + lead reviewer for the data PR template; the most-involved lead per master plan §5.5 reasoning)
- `meesell-infra-builder` (named reviewer)

The AI lead (`meesell-ai-coordinator`) is NOT a reviewer per the `## Code surfaces` "AI (group: ai)" subsection.

#### Per-lead self-broadcast on plan merge

When this PR merges to `develop`, each named lead reviewer runs the broadcast sequence in their next session. The trigger is "I read the plan PR is merged" — a one-line manual signal (no automation in V1).

**Backend lead broadcast steps:**

1. Open a fresh master-session window and dispatch `meesell-backend-coordinator` with:
   ```
   SESSION: mesell-xlsx-export-backend-session-0  (the "session-0" ordinal marks
            a broadcast-only session, not a specialist dispatch)
   PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell

   ## Mission
   Plan broadcast — xlsx-export FEATURE_PLAN.md merged to develop.

   1. Read docs/plans/features/xlsx-export/FEATURE_PLAN.md (entire doc).
   2. Append to your MEMORY.md (`.claude/agent-memory/meesell-backend-coordinator/MEMORY.md`):
      [xlsx-export queued](../../docs/plans/features/xlsx-export/FEATURE_PLAN.md) — V1 Feature 9; awaits catalog-form + image-precheck merge to develop; my role per FEATURE_PLAN.md `## Agent lineup` (backend lead — dispatch services-builder + api-routes-builder + database-builder); 3 specialist dispatches expected.
   3. Add to docs/status/feature_board_backend.md "Active features" table:
      | xlsx-export | — | PENDING | — | YYYY-MM-DD | depends on catalog-form + image-precheck | See docs/plans/features/xlsx-export/FEATURE_PLAN.md (FEATURE_PLAN ready; code dispatch gated on upstream features) |
   4. Commit both files in a single commit:
      `docs(memory): backend lead broadcast — xlsx-export queued`
   5. Push (no PR needed — the broadcast commits to develop directly per the master plan §6.5 update protocol, as feature_board updates are not feature work).
   ```
2. Confirm in the founder's STATUS_MASTER.md that the broadcast is done.

**Frontend / Data / Infra leads** run the same sequence with their own MEMORY.md + feature_board paths.

**Specialists are NOT dispatched in the broadcast.** Their awareness is deferred to first dispatch — the dispatch templates in `## Dispatch templates` embed the plan path in their mandatory reads.

#### What happens when an upstream feature merges (catalog-form, image-precheck)

When `catalog-form` merges to `develop`, the backend lead's next session can dispatch database-builder (the migration has no upstream code dependency). Services-builder and api-routes-builder still wait for image-precheck to merge.

When `image-precheck` merges to `develop`, the backend lead can dispatch services-builder (which exercises `image.service.get_image_bytes`). At this point all backend dispatches can proceed.

Frontend, data, infra dispatches are NOT blocked by these upstream merges — they can dispatch as soon as the broadcast is done.

#### Plan amendment protocol

If the plan needs to change after it merges (a §14 amendment, a fixture matrix change, a cost-driven scope cut), the protocol is:

1. The change-requesting lead opens a new branch `feature/xlsx-export/plan-amendment-<topic>` off `develop`
2. They author the amendment as a diff to this FEATURE_PLAN.md
3. They PR to `develop` with the founder + 3 other leads as reviewers
4. On merge, each lead re-runs their broadcast (re-reading the plan) and updates the relevant MEMORY.md entry to point at the new revision
5. The plan's `## Revision history` table gains a row

---

## Dispatch templates

### Common preamble

Every dispatch template below uses this preamble. The lead fills `{N}` with the session ordinal (1 on first dispatch; 2 on context-break resume; etc.) and dispatches via the Agent() tool with `subagent_type` set to the specialist's name.

```
SESSION: mesell-xlsx-export-{group}-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Feature context
You are implementing a slice of the XLSX Export feature (V1 Feature 9). The full
feature plan is at:

    docs/plans/features/xlsx-export/FEATURE_PLAN.md

Read it first. Your slice is described in `## Dispatch templates` of that document
under the "{specialist-name}" subsection. Acceptance criteria, hard constraints,
files-you-may-touch, and files-you-must-NOT-touch are all there.

## First action
1. Read your own agent memory: .claude/agent-memory/{specialist-name}/MEMORY.md
2. Read the feature plan: docs/plans/features/xlsx-export/FEATURE_PLAN.md
3. Read the mandatory architecture sections enumerated below.
4. Confirm to yourself which acceptance-criteria items are in scope for this
   session. If any criterion is unclear, STOP and ask the lead.

## Session naming
This session is `mesell-xlsx-export-{group}-session-{N}`. Record it in the first
commit message footer per MASTER_PLAN §4.2 and in your memory file's session-
start entry.
```

The per-specialist mandatory reads + acceptance + constraints + files list + report format are below.

### 7.1 `meesell-services-builder` (dispatched by `meesell-backend-coordinator`)

`{group} = backend`. This is the heaviest dispatch in the feature — plan for 2-3 sessions.

```
## Mandatory reads
1. docs/BACKEND_ARCHITECTURE.md §14 (LOCKED 2026-06-05) — the entire export
   module spec: §14.A premise, §14.B endpoint flows, §14.C service-layer
   public + worker-internal helper signatures, §14.D repository, §14.E Celery
   task with the 9-step delegation, §14.F domain types (5 frozen dataclasses +
   2 ABCs + 3 concretes), §14.G schemas, §14.H 7 exception classes, §14.I
   adapter usage + GCS path convention, §14.J cross-cutting (rate limit, audit,
   tenancy, Layer 3, M10), §14.K test plan + 15-fixture matrix
2. docs/MVP_ARCHITECTURE.md §5.5 (Export Adapter — 9-step pipeline detail per
   step) + §5.5.10 (performance budget) + §5.5.7 (round-trip contract)
3. docs/BACKEND_ARCHITECTURE.md §6A.C (ai_ops.client.call_gemini signature —
   though you DO NOT call this; you implement the Layer 3 guardrail at step 5
   which is the deterministic safety net independent of AI)
4. docs/BACKEND_ARCHITECTURE.md §11.C (image.service.get_image_bytes signature:
   `get_image_bytes(image_id: UUID, user_id: UUID) -> bytes`. NOTE the
   signature is by image_id NOT product_id.)
5. docs/BACKEND_ARCHITECTURE.md §10.C (catalog.service.get_product_for_export
   + assert_product_ownership signatures)
6. docs/BACKEND_ARCHITECTURE.md §8.C (customer.service.get_compliance_block
   signature — returns the 9-field ComplianceBlock typed object you import into
   domain.py for the strategy contract)
7. docs/BACKEND_ARCHITECTURE.md §15.E (audit log direct-write canonical pattern
   — your tasks.py uses this for `export.completed` + `export.failed`)
8. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan)
9. docs/plans/repo_management/MASTER_PLAN.md §2.1 (STEP 1 PR criteria) +
   §5.2 (backend PR template)
10. .claude/agents/meesell-services-builder.md (your spec)

## Mission
Build the entire Export Adapter:
- service.py (public + 11 worker-internal helpers; the 9-step pipeline)
- repository.py (5 module-private methods)
- tasks.py (1 Celery task `export.xlsx`)
- domain.py (5 frozen dataclasses + 2 ABCs + 3 concretes)
- exceptions.py (7 classes)
- The 7 i18n strings in app/i18n/messages_en.py
- workers/celery_app.py — add `"app.modules.export.tasks"` to `include=[...]`
- The pytest runner at backend/tests/modules/export/test_round_trip.py that
  loads the 15 golden fixtures from backend/tests/integration/golden_round_trip/
- backend/tests/modules/export/test_service.py with the 10 unit tests per §14.K
- backend/tests/modules/export/test_repository.py with `scope_to_user` proof
- backend/tests/modules/export/test_tasks.py with happy path + 3 failure paths
- backend/tests/integration/test_export_full_pipeline.py with 3 integration tests
- docs/runbooks/xlsx-export-troubleshooting.md (NEW) — stuck-task inspection +
  XLSX local-validity + Meesho upload smoke procedure + 7-error-code cheatsheet
- Link the runbook from docs/runbooks/README.md

## Acceptance criteria
[ ] 9-step pipeline matches MVP_ARCH §5.5 verbatim — step order, step names,
    step responsibilities. Diff your service.py against the §5.5 contract
    before opening PR.
[ ] Each of the 11 worker-internal helpers is a separately-callable function
    (so the 10 unit tests per §14.K can target them in isolation). Do NOT
    inline step bodies inside _run_export_pipeline.
[ ] StandardComplianceStrategy: 9 input fields → 9 output XlsxColumnSpec
    (pass-through). 100% of the 3,771 non-Eye-Serum templates.
[ ] CollapsedComplianceStrategy: 9 input fields → 3 output XlsxColumnSpec
    (Manufacturer / Packer / Importer Details columns). Concatenation
    separator = ', ' (comma-space). Empty input fields DROPPED from the
    concatenation per §14.F. Applies only to Eye-Serum leaf 12378.
[ ] Layer 3 hallucination guardrail wired at step 5 (`_translate_enums`).
    Lookup against field_enum_values.enum_entries via
    category.service.get_field_enum. Unknown canonical value → raises
    ExportEnumValidationError → tasks.py captures as exports.status='failed'
    with error_code='enum_validation_failed'. Add an inline comment at the
    top of _translate_enums flagging the security-critical nature.
[ ] Round-trip validation step 9 (`_round_trip_validate`) re-parses the just-
    written XLSX with openpyxl + canonical re-map, then asserts every field
    in original_snapshot matches the re-parsed value. On mismatch returns
    RoundTripResult(passed=False, mismatches=[...]); caller raises
    RoundTripValidationError.
[ ] Generation budget verified: 1 product + 6 images = ≤15s wall time on the
    dev VM. Measure in the integration test. Acceptable: ≤30s per
    MVP_ARCH §5.5.10 hard ceiling but flag any >15s result in PR body as a
    follow-up perf task.
[ ] XLSX opens cleanly in BOTH Microsoft Excel AND LibreOffice. Verify with
    a manual smoke (open the test-generated XLSX in both apps) + a
    `python -c "import openpyxl; openpyxl.load_workbook(...)"` automated
    re-parse in test_round_trip.py.
[ ] Image ZIP filenames match XLSX image-reference column EXACTLY. The
    image-reference column carries the convention from the ComplianceStrategy
    + the schema_jsonb.fields[] image-field entries. Test 15 (special chars)
    + Test 12 (empty optional) exercise the boundary cases.
[ ] All 15 golden fixtures pass the round-trip test
    (`pytest backend/tests/modules/export/test_round_trip.py`). CI gate-5
    wired to this command in `.github/workflows/ci.yml`.
[ ] GCS paths: gs://meesell-prod-assets/meesell-exports/{user_id}/{export_id}/sheet.xlsx
    + .../images.zip. Use adapters.gcs.upload_bytes — never raw GCS SDK calls
    in service.py or tasks.py.
[ ] 1h signed URL TTL: adapters.gcs.generate_signed_url(path, ttl_seconds=3600)
    in service.get_export. Fresh URL per response.
[ ] Audit writes: direct ORM write of `export.completed` AND `export.failed`
    from inside tasks.py using the canonical per-site pattern (§15.E). Do
    NOT create a shared audit_helpers module — per-site is V1 standard.
[ ] worker_session: use `make_worker_session()` per §5.B for the worker DB
    handle inside tasks.py — do NOT reuse the FastAPI request-scoped session.
[ ] FEATURE_XLSX_EXPORT_ENABLED flag respected at the POST entry (api-routes-
    builder owns this gate; your service.initiate_export is called only when
    enabled; do not duplicate the gate).
[ ] All 10 unit tests + 3 integration tests + 15 round-trip fixtures + CI
    gate-5 wired green.
[ ] backend/tests/integration/golden_round_trip/ directory contains the 15
    JSON fixtures co-authored with xlsx-parser (data lead's dispatch produces
    these — coordinate with backend-coordinator memo).
[ ] Runbook authored at docs/runbooks/xlsx-export-troubleshooting.md +
    linked from docs/runbooks/README.md.
[ ] PR uses .github/PULL_REQUEST_TEMPLATE/backend.md, fills every section
    including migration evidence (database-builder's PR may merge before
    yours; reference its Alembic revision in your PR body) + integration
    test results + 15-fixture roundtrip pass count.

## Hard constraints
1. DO NOT touch backend/app/modules/image/ — image is consumed only via
   image.service.list_images + image.service.get_image_bytes. Any need to
   modify image.service is a cross-lead coordination memo (escalate to
   backend-coordinator).
2. DO NOT touch backend/app/modules/catalog/ — catalog is consumed only via
   catalog.service.assert_product_ownership + catalog.service.get_product_for_export.
3. DO NOT touch backend/app/modules/customer/ — customer is consumed only via
   customer.service.get_compliance_block(user_id) returning the typed
   ComplianceBlock object.
4. DO NOT touch backend/app/modules/category/ — category is consumed only via
   category.service.fetch_schema + category.service.get_field_enum +
   category.service.fetch_xlsx_aliases.
5. DO NOT bypass the Layer 3 guardrail at step 5. The Celery task MUST call
   `_translate_enums` BEFORE step 6 (column reorder). Skipping it for "perf"
   reasons is a P0 bug.
6. DO NOT write to products.fields_jsonb during export — the export pipeline
   is READ-ONLY against product state.
7. DO NOT skip round-trip validation (step 9). If the round-trip costs too
   much wall time, the resolution is to optimise step 9, NOT to disable it.
8. DO NOT write meesho_column_header / meesho_column_index / enum_codes_map
   into any API response, AI prompt, cache payload, or any module outside
   app/modules/export/ per philosophy M10 (§14.J). The §19 CI linter
   enforces this — your tests should not even import these symbols outside
   modules/export/tests/.
9. DO NOT use openpyxl write_only mode for V1 (the round-trip read step
   requires a normal-mode write so the re-parse can index by column).
   Document this choice in a comment at the top of `_write_xlsx`.
10. Signed URL TTL is 3600 seconds (1h). NOT 24h, NOT 5min — exactly 3600.
11. GCS bucket is `meesell-prod-assets` with `meesell-exports/` prefix.
    DO NOT provision a separate bucket. DO NOT use the path
    `meesell-exports/{user_id}/...` directly without the bucket prefix.
12. NO partial-GCS-upload cleanup in V1 — that is V1.5 scope per §14.L.
    Failed export rows stay in `exports` table with status='failed'; the
    GCS bytes from any partial step are NOT deleted by service.py or
    tasks.py.

## Files you may touch
- backend/app/modules/export/* (all files in §3.1 backend table marked
  services-builder owned)
- backend/app/i18n/messages_en.py (add 7 keys)
- backend/app/workers/celery_app.py (modify `include=[]` only)
- backend/tests/modules/export/* (all files in §3.1 marked services-builder
  owned)
- backend/tests/integration/test_export_full_pipeline.py (NEW)
- docs/runbooks/xlsx-export-troubleshooting.md (NEW)
- docs/runbooks/README.md (1-line link addition)
- .github/workflows/ci.yml (add gate-5 step ONLY if not already present)

## Files you must NOT touch
- backend/app/modules/{iam,customer,category,catalog,image,pricing,dashboard}/**
- backend/app/shared/** (database-builder's territory for export.py; everything
  else is foundation-layer and out of scope)
- backend/app/alembic/** (database-builder owns the migration)
- backend/app/main.py (api-routes-builder owns the router registration)
- backend/app/config.py (api-routes-builder owns the flag setting)
- backend/app/modules/export/router.py + schemas.py (api-routes-builder owns)
- frontend/** (zero touches)
- k8s/** + terraform/** (infra-builder owns)
- docs/V1_FEATURE_SPEC.md (backend-coordinator stamps at sprint PR merge)
- docs/BACKEND_ARCHITECTURE.md (LOCKED — no amendments without founder
  approval via backend-coordinator)
- docs/MVP_ARCHITECTURE.md (LOCKED — no amendments)
- Any other feature's planning directory under docs/plans/features/

## Final report format
Report back to backend-coordinator with:
1. Acceptance-criteria checklist with each box ticked or annotated WHY-NOT
2. `pytest backend/tests/modules/export/ -v` output (all green)
3. `pytest backend/tests/modules/export/test_round_trip.py -v` output —
   15 fixtures pass count
4. Integration test wall-time measurement: 1-product + 6-image export in
   X.X seconds (against the 15s target; 30s hard ceiling)
5. Manual smoke confirmation: "Generated XLSX opens in Excel ✅" +
   "Generated XLSX opens in LibreOffice ✅"
6. Image ZIP filename match confirmation: "All 15 fixtures: image-reference
   column ↔ ZIP filenames match ✅"
7. CI gate-5 step PR-link (the modified ci.yml line range)
8. List of i18n keys added (the 7 export.* keys)
9. Runbook PR link
10. PR opened to feature/xlsx-export with .github/PULL_REQUEST_TEMPLATE/backend.md
    filled
11. feature_board_backend.md row updated to IN REVIEW with the PR link
12. Session-end entry appended to your MEMORY.md
```

### 7.2 `meesell-api-routes-builder` (dispatched by `meesell-backend-coordinator`)

`{group} = backend`. May dispatch in parallel with services-builder once the schemas/contract are agreed.

```
## Mandatory reads
1. docs/BACKEND_ARCHITECTURE.md §14.B (LOCKED) — the 2 endpoint signatures,
   status codes, rate limit, plan guard, audit, the 6-step initiate flow,
   the 4-step poll flow
2. docs/BACKEND_ARCHITECTURE.md §14.G — the 4 Pydantic wire schemas verbatim
3. docs/BACKEND_ARCHITECTURE.md §14.H — the 7 exception classes (the
   validation_message_id surfaces here are the error envelope payloads)
4. docs/BACKEND_ARCHITECTURE.md §4.B (core/auth.py JWT contract for
   `user: User = Depends(get_current_user)`)
5. docs/BACKEND_ARCHITECTURE.md §4.E (core/rate_limit.py decorator
   contract)
6. docs/BACKEND_ARCHITECTURE.md §4.F (core/errors.py — MeesellError base)
7. docs/BACKEND_ARCHITECTURE.md §0.C (the 27-endpoint locked contract —
   verify your 2 new endpoints align with the 25→27 expansion)
8. docs/BACKEND_ARCHITECTURE.md §17 (mounted endpoint inventory — your
   PR brings the count to 30; document this in PR body)
9. docs/plans/repo_management/MASTER_PLAN.md §3.2 (feature flag posture)
10. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan; especially
    §2.2 D2 flag posture for the 404-when-disabled semantics)

## Mission
Build the 2 route handlers + the 4 Pydantic wire schemas + the feature flag
gate at the POST entry.

- backend/app/modules/export/router.py (NEW)
- backend/app/modules/export/schemas.py (NEW)
- backend/app/main.py — register the export router (MODIFY, 1-2 lines)
- backend/app/config.py — add FEATURE_XLSX_EXPORT_ENABLED: bool = True
  (MODIFY, 1 line)
- backend/tests/modules/export/test_router.py — auth tests + rate-limit
  test + 4 prereq-gate tests + flag-disabled-404 test

## Acceptance criteria
[ ] POST /api/v1/products/{id}/export-xlsx returns 202 ACCEPTED with
    ExportInitiatedResponse on success. Status codes per §14.B.1: 202, 400
    invalid_format, 401 no JWT, 404 product_not_found, 422
    product_not_ready, 422 front_image_missing.
[ ] When FEATURE_XLSX_EXPORT_ENABLED=False, POST returns 404 with
    `{"detail": "Not Found"}` BEFORE any prereq check fires. Verify in
    test_router.py with monkeypatched config.
[ ] GET /api/v1/exports/{id} returns 200 with ExportResponse. Status codes
    per §14.B.2: 200, 401, 404 export.not_found.
[ ] @rate_limit(scope="export_initiate", limit="10/h", key="user_id") on
    POST. GET has no decorator (per-IP backbone only).
[ ] No plan-guard decorator on either endpoint (§14.J — exports are core
    seller value, NOT plan-gated in V1).
[ ] OpenAPI metadata complete on both routes: tag, summary, response_model,
    responses dict for each status code with the validation_message_id key.
[ ] The 4 Pydantic schemas in schemas.py match §14.G verbatim. NO extra
    fields. NO meesho_column_header / meesho_column_index / enum_codes_map
    appear in any schema per philosophy M10.
[ ] router test suite green; tests cover the 4 prereq gates by mocking
    service.initiate_export to verify the handler delegates AFTER the
    JWT + flag checks but BEFORE the prereq error mapping (the prereq
    errors come from service layer, not the route layer).

## Hard constraints
1. DO NOT inline business logic in route handlers — delegate to
   service.initiate_export and service.get_export.
2. DO NOT introduce a new HTTP method or path; the 2 routes are LOCKED at
   §0.C. Adding GET /api/v1/products/{id}/exports (list-exports-per-product)
   is V1.5 scope.
3. DO NOT add a request body to GET — it is path-param-only.
4. DO NOT add Content-Type=application/zip handling — XLSX + ZIP are
   served via signed GCS URLs, not via the API surface.
5. DO NOT touch service.py, tasks.py, domain.py, exceptions.py,
   repository.py — those are services-builder territory.
6. Feature flag MUST be read from app.config.Settings (Pydantic Settings) —
   do NOT read os.getenv() directly inside the handler.
7. The flag check returns 404 (not 503, not 503-with-body) per master plan
   §3.2 backend convention.

## Files you may touch
- backend/app/modules/export/router.py (NEW)
- backend/app/modules/export/schemas.py (NEW)
- backend/app/main.py (MODIFY — 1-2 lines to register router)
- backend/app/config.py (MODIFY — 1 line for the flag setting)
- backend/tests/modules/export/test_router.py (NEW)

## Files you must NOT touch
- backend/app/modules/export/* (other than router.py + schemas.py)
- backend/app/modules/{iam,customer,category,catalog,image,pricing,dashboard}/**
- backend/app/shared/** + backend/app/alembic/** + backend/app/i18n/**
- backend/app/workers/** + backend/app/core/**
- frontend/** + k8s/** + terraform/**
- docs/V1_FEATURE_SPEC.md + docs/BACKEND_ARCHITECTURE.md + docs/MVP_ARCHITECTURE.md
- Any other feature's planning directory

## Final report format
1. Acceptance-criteria checklist
2. `pytest backend/tests/modules/export/test_router.py -v` output
3. Manual curl smoke against dev: POST returns 202; GET returns 200; POST
   with flag disabled returns 404
4. Endpoint inventory delta (BACKEND_ARCHITECTURE.md §17): 28 → 30
5. PR opened to feature/xlsx-export with backend PR template filled
6. feature_board_backend.md row updated to IN REVIEW
```

### 7.3 `meesell-database-builder` (dispatched by `meesell-backend-coordinator`)

`{group} = backend`. Can dispatch in parallel with the other two backend specialists, but the migration must merge BEFORE services-builder's PR can run integration tests against `dev`.

```
## Mandatory reads
1. docs/MVP_ARCHITECTURE.md §2.5 (Product images, pricing, exports — the
   authoritative DDL for the `exports` table)
2. docs/BACKEND_ARCHITECTURE.md §14.D (repository layer signatures —
   informs which indexes you need)
3. docs/BACKEND_ARCHITECTURE.md §5.B (shared/database.py + ORM model
   conventions: UUID PKs, TIMESTAMPTZ, JSONB-where-appropriate)
4. docs/BACKEND_ARCHITECTURE.md §15.B (multi-tenancy — `exports.user_id` is
   the tenancy column, scope_to_user enforced on every query)
5. docs/plans/repo_management/MASTER_PLAN.md §3.3 (migration strategy —
   one migration per feature, downgrade path mandatory, no hand-edits
   after dev apply)
6. backend/app/alembic/versions/ — read the most recent migration to
   confirm the parent revision SHA you set as `down_revision`
7. .claude/agent-memory/meesell-database-builder/MEMORY.md (your spec)
8. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan)

## Mission
Add the `exports` table per `MVP_ARCH §2.5` + the matching SQLAlchemy ORM
model.

- backend/app/shared/models/export.py (NEW ORM model)
- backend/app/alembic/versions/<rev>_add_exports_table.py (NEW migration)
- backend/app/shared/models/__init__.py (MODIFY — register the export model
  for Alembic auto-discovery if not already done via `__all__`)
- backend/tests/test_database.py (MODIFY — append schema-smoke assertion
  that `exports` table exists with the expected columns)

## Acceptance criteria
[ ] `exports` table DDL matches MVP_ARCH §2.5 + V1_FEATURE_SPEC §F9 data
    model exactly:
    - id UUID PK (gen_random_uuid())
    - user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
    - product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE
    - format VARCHAR(20) NOT NULL CHECK (format IN ('xlsx_only','xlsx_with_images'))
    - status VARCHAR(16) NOT NULL CHECK (status IN ('pending','ready','failed'))
    - xlsx_gcs_path TEXT (nullable; populated on status=ready)
    - zip_gcs_path TEXT (nullable; populated only when format=xlsx_with_images AND status=ready)
    - error_message TEXT (nullable; populated on status=failed)
    - error_code VARCHAR(50) (nullable; populated on status=failed — one of
      the 7 §14.H codes)
    - round_trip_validated BOOLEAN (nullable; TRUE when status=ready per §14.K)
    - initiated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    - completed_at TIMESTAMPTZ (nullable; populated on status=ready OR failed)
[ ] Indexes:
    - idx_exports_user_id (btree on user_id) for `scope_to_user` performance
    - idx_exports_user_id_initiated_at_desc (btree on (user_id,
      initiated_at DESC)) for the dashboard.summary V1.5-elevation surface
      per §14.C
[ ] No JSONB columns — `exports` has no flexible-payload column.
[ ] downgrade path implemented (drop indexes + drop table).
[ ] Migration parent revision is the current head per the alembic chain.
[ ] `alembic upgrade head` runs cleanly on the dev DB (verify via the
    schema-smoke test).
[ ] ORM model in shared/models/export.py with proper relationships
    (user, product as backref-less foreign keys; no eager loading by
    default — the dashboard.summary surface is the only consumer that
    might benefit from eager).
[ ] backend/tests/test_database.py extended with the schema-smoke
    assertion (table exists, 11 columns present, 2 indexes present, 2
    CHECK constraints present).

## Hard constraints
1. DO NOT add new columns beyond the 11 in §2.5. The seller-facing
   download URL is generated FRESH per response per §14.B.2 — it is NOT
   a column.
2. DO NOT add a uniqueness constraint on (user_id, product_id) — D1
   confirms idempotency at the seller-experience level, NOT at the row
   level. Each retry inserts a new row.
3. DO NOT use Postgres ENUMs for status / format / error_code — use
   VARCHAR + CHECK constraint per MeeSell convention (founder ruling per
   coordinator memory).
4. DO NOT touch any other module's table or migration. The exports table
   is the ONLY new table in this feature.
5. ORM model lives at backend/app/shared/models/export.py — NOT under
   backend/app/modules/export/. ORM models are foundation-layer per §3.E.

## Files you may touch
- backend/app/shared/models/export.py (NEW)
- backend/app/shared/models/__init__.py (MODIFY — `__all__` only)
- backend/app/alembic/versions/<rev>_add_exports_table.py (NEW)
- backend/tests/test_database.py (MODIFY — schema-smoke addition only)

## Files you must NOT touch
- Any other shared/models/* file
- Any other module's alembic migration
- backend/app/modules/export/* (services-builder + api-routes-builder
  territory)
- frontend/** + k8s/** + terraform/**
- docs/*

## Final report format
1. Migration revision SHA (the new `revision` field)
2. Down-revision SHA (the parent)
3. `alembic upgrade head` output on dev DB (paste)
4. `alembic downgrade -1` output on dev DB (paste — verify down path)
5. `alembic upgrade head` output (re-apply after downgrade verification)
6. Schema-smoke test output: `pytest backend/tests/test_database.py -v -k exports`
7. Alembic head divergence check between dev + staging: paste both heads,
   confirm match (or note staging not yet applied)
8. PR opened to feature/xlsx-export/backend with backend PR template
   filled; specifically the "Database migration" section
9. feature_board_backend.md row updated to IN REVIEW (your row is its own
   sub-task within the xlsx-export feature)
```

### 7.4 `meesell-angular-component-builder` (dispatched by `meesell-frontend-coordinator`)

`{group} = frontend`.

```
## Mandatory reads
1. docs/FRONTEND_ARCHITECTURE.md (APPROVED 2026-06-08) — entire doc;
   especially the 4-Layer architecture rules, Layer 4 features placement,
   the @mee/ui barrel import rule, no-PrimeNG-imports-outside-ui rule
2. docs/V1_FEATURE_SPEC.md §F9 (the feature you're rendering) +
   §6 the route `/catalogs/:id/export`
3. docs/BACKEND_ARCHITECTURE.md §14.B (LOCKED) — the endpoint contracts
   so your component knows what JSON shapes to expect (the service-builder
   binds these via the model file at features/export/models/export.model.ts)
4. docs/plans/module_federation/MASTER_PLAN.md §4.2 (mfe-export is remote
   #2 in extraction order — but for V1 you build pre-federation; your file
   layout under src/app/features/export/ must be federation-friendly so
   later extraction is a copy-not-rewrite)
5. themes/sakai-ng/ — read the Sakai page closest to "single-action
   download CTA + progress polling" as a layout reference (probably
   `apps/showcase/sakai-sample-pages/file-export` or similar; if no exact
   match, adapt from the file-upload sample)
6. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan)
7. .claude/agents/meesell-angular-component-builder.md (your spec)

## Mission
Build the 2 page components under src/app/features/export/.

- export-page.component.ts + .html + .scss + .spec.ts
- export-progress.component.ts + .html + .spec.ts (no separate scss;
  Tailwind utilities inline)
- index.ts barrel
- src/app/app.routes.ts — register the lazy route

## Acceptance criteria
[ ] Route `/catalogs/:id/export` lazy-loads ExportPageComponent
[ ] Auth guard applied (the route lives under the authenticated shell)
[ ] Component uses standalone: true + ChangeDetectionStrategy.OnPush
[ ] Zero direct PrimeNG imports (`import { ... } from 'primeng/...'`).
    All UI primitives come from `@mee/ui`: mee-button, mee-card,
    mee-page-header, mee-progress-bar, mee-status-badge, mee-toast (via
    MeeToastService injection)
[ ] "Generate XLSX" CTA on the page; when clicked, calls
    inject(ExportService).initiate(productId) and switches to the
    polling progress sub-component
[ ] Multi-error validation render on 422: when initiate() errors with 422,
    parse the `error_message` envelope + render BOTH a mee-toast (top-level
    notification) AND an inline error list inside a mee-card (so the seller
    sees all failures at once, not just the toast)
[ ] Polling sub-component (ExportProgressComponent) renders a mee-progress-bar
    + status badge ("Pending..." / "Ready" / "Failed") + a download CTA
    (mee-button with icon) when status="ready"; clicking the CTA opens the
    signed URL in a new tab (window.open(xlsx_signed_url, '_blank'))
[ ] When status="failed", render the error_message in a mee-card with a
    "Retry" mee-button that re-calls initiate()
[ ] When status="ready" with format="xlsx_with_images", render 2 download
    CTAs (XLSX + Images ZIP)
[ ] Screenshots at 360px + 1280px attached to the PR (per master plan
    §5.3 frontend PR template)
[ ] Build < 90s (per CLAUDE.md Decision 12)
[ ] Component test green; covers: CTA click → initiate called; 422 →
    multi-error render; 200 polling → progress + download CTA visible

## Hard constraints
1. NO `import { ... } from 'primeng/...'` in feature files. PrimeNG imports
   live ONLY in src/app/ui/ per FRONTEND_ARCH non-negotiable rule #1.
2. NO `import { ... } from '@angular/material/...'` anywhere (Material was
   replaced by PrimeNG per FRONTEND_ARCH technology decisions LOCKED).
3. NO NgModules anywhere. All components standalone: true.
4. NO `BehaviorSubject` for component-local state — use signals
   (signal(), computed(), effect()).
5. Use `inject(ExportService)` — not constructor injection — for the
   service handle.
6. NO inline styles in the .ts file template; all styling is Tailwind
   utility classes in the .html (and rare additions in the .scss).
7. NO writes to ExportService.initiate() with a hard-coded productId;
   pull from route param via @Input from withComponentInputBinding or
   from inject(ActivatedRoute).
8. DO NOT touch frontend/src/app/ui/, layouts/, shared/, core/,
   design-system/ — those are out of scope (Layer 2/3/1 territory).
9. DO NOT touch any backend file, k8s, terraform, docs.
10. The export-page route comment in app.routes.ts MUST cite the feature
    flag: `// xlsx-export feature — backend POST returns 404 when
    FEATURE_XLSX_EXPORT_ENABLED=false (master plan §3.2)`

## Files you may touch
- frontend/src/app/features/export/* (all files in §3.2 marked
  angular-component-builder)
- frontend/src/app/app.routes.ts (MODIFY — register lazy route only)

## Files you must NOT touch
- frontend/src/app/{ui,layouts,shared,core,design-system}/**
- frontend/src/app/features/{landing,account,dashboard,smart-picker,
  catalog-form,images,preview,pricing,profile}/**
- frontend/src/app/features/export/services/* (angular-service-builder
  territory)
- frontend/angular.json + package.json + tsconfig.* (lead-level changes)
- All backend, k8s, terraform, docs paths

## Final report format
1. Acceptance-criteria checklist
2. `pnpm test` output — your spec files green
3. `pnpm build` output — under 90s (paste timing)
4. Bundle size delta vs the previous main.js bundle (paste relevant
   stats.json excerpt)
5. Screenshot at 360px (attach to PR description)
6. Screenshot at 1280px (attach to PR description)
7. Accessibility check confirmation: keyboard nav works on CTAs;
   contrast checked on the new status badge colors; aria-* attrs added
8. PR opened to feature/xlsx-export/frontend with
   .github/PULL_REQUEST_TEMPLATE/frontend.md filled
9. feature_board_frontend.md row updated to IN REVIEW
```

### 7.5 `meesell-angular-service-builder` (dispatched by `meesell-frontend-coordinator`)

`{group} = frontend`.

```
## Mandatory reads
1. docs/BACKEND_ARCHITECTURE.md §14.B (LOCKED) + §14.G — the wire schemas
   you mirror in TypeScript
2. docs/FRONTEND_ARCHITECTURE.md — non-negotiable rules, especially #4
   (signals for local state, RxJS for async)
3. frontend/src/app/core/services/auth.service.ts — the AuthService
   pattern + JWT interceptor (you do NOT write a new interceptor;
   the existing one handles Bearer attach)
4. docs/V1_FEATURE_SPEC.md §F9 — the polling UX target
5. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan, especially
   §2.2 D1 budget: ≤15s target, ≤30s hard ceiling)
6. .claude/agents/meesell-angular-service-builder.md (your spec)

## Mission
Build the ExportService + TypeScript model file.

- frontend/src/app/features/export/services/export.service.ts
- frontend/src/app/features/export/services/export.service.spec.ts
- frontend/src/app/features/export/models/export.model.ts
- (Conditionally) frontend/src/app/core/services/feature-flags.service.ts
  — MODIFY if it exists, NEW if it doesn't, to read
  FEATURE_XLSX_EXPORT_ENABLED from build-time env (per master plan §3.2)

## Acceptance criteria
[ ] ExportService.initiate(productId: string): Observable<ExportInitiatedResponse>
    — POSTs to /api/v1/products/{productId}/export-xlsx with body
    `{ format: 'xlsx_with_images' }` (the default)
[ ] ExportService.pollStatus(exportId: string): Observable<ExportResponse>
    — GETs /api/v1/exports/{exportId} every poll tick
[ ] Polling backoff: initial 1000ms → doubling (1s → 2s → 4s, cap at 4s),
    polling stops on status='ready' OR status='failed' OR wall-time > 60s
    (matches §F9 30s hard ceiling + 2× headroom + 1 retry)
[ ] When poll exceeds 60s wall time without reaching terminal state,
    surface a "Slow export — try again or contact support" error to the
    component
[ ] Error handling:
    - 401 → AuthService logout flow
    - 404 (flag disabled OR export not found) → distinguish via the path:
      POST 404 → render "Export temporarily disabled" placeholder;
      GET 404 → render "Export not found" error
    - 422 → propagate the error envelope (component renders the multi-error
      list)
    - 503 (transient GCS) → retry ONCE with 2-second delay, then surface
      "Storage temporarily unavailable. Try again."
    - 5xx other → MeeToastService.error('Something went wrong. Please retry.')
[ ] TypeScript models in export.model.ts mirror backend Pydantic schemas
    exactly:
    - type ExportFormat = 'xlsx_only' | 'xlsx_with_images'
    - type ExportStatus = 'pending' | 'ready' | 'failed'
    - interface ExportRequest { format: ExportFormat }
    - interface ExportInitiatedResponse { export_id, status: 'pending',
      enqueued_task_id, initiated_at }
    - interface ExportResponse { export_id, product_id, status, format,
      xlsx_signed_url?, zip_signed_url?, error_message?, error_code?,
      initiated_at, completed_at?, round_trip_validated? }
[ ] No `any` types. No `as unknown` casts. Strict TypeScript per
    FRONTEND_ARCH rule #6.
[ ] Service test green: covers initiate happy path, poll → ready
    transition, poll → failed transition, 422 propagation, 503 retry,
    60s timeout

## Hard constraints
1. NO localStorage / sessionStorage writes for export state — polling
   state is in-memory only (the seller refreshing the page restarts the
   poll from the URL param if applicable, or restarts the flow).
2. NO direct fetch() — use HttpClient via `inject(HttpClient)`.
3. NO unsubscribe leaks — use takeUntil(this.destroy$) or DestroyRef +
   takeUntilDestroyed() pattern.
4. NO duplicate poll on the same exportId — if pollStatus is called
   twice with the same exportId, return the cached Observable (use
   shareReplay(1)).
5. NO retries on 422 — validation errors are seller-actionable, not
   transient.
6. NO retries on 401 — auth failure is logout-trigger, not retry.
7. The 60s wall-time cap is NOT extendable per-call — it's the contract.
8. DO NOT touch frontend/src/app/features/export/{export-page,export-progress}.component.* — component-builder territory.
9. DO NOT touch any other feature's service file.
10. DO NOT modify auth.service.ts or the JWT interceptor — they pre-exist.

## Files you may touch
- frontend/src/app/features/export/services/export.service.ts (NEW)
- frontend/src/app/features/export/services/export.service.spec.ts (NEW)
- frontend/src/app/features/export/models/export.model.ts (NEW)
- frontend/src/app/core/services/feature-flags.service.ts (NEW or MODIFY)

## Files you must NOT touch
- frontend/src/app/features/export/export-{page,progress}.component.*
  (component-builder territory)
- frontend/src/app/features/{landing,account,dashboard,smart-picker,
  catalog-form,images,preview,pricing,profile}/**
- frontend/src/app/{ui,layouts,shared,design-system}/**
- frontend/src/app/core/services/auth.service.ts +
  frontend/src/app/core/interceptors/**
- frontend/src/app/app.routes.ts (component-builder owns this MODIFY)
- All backend, k8s, terraform, docs paths

## Final report format
1. Acceptance-criteria checklist
2. `pnpm test --filter export.service` output — green
3. TypeScript model file path + a copy of the 5 type declarations
4. Polling backoff timing trace from the spec file (1000ms → 2000ms →
   4000ms → 4000ms → ...)
5. PR opened to feature/xlsx-export/frontend with frontend PR template
   filled
6. feature_board_frontend.md row updated to IN REVIEW
```

### 7.6 `meesell-xlsx-parser` (dispatched by `meesell-data-engineer`)

`{group} = data`. The 15-fixture deliverable is the differentiating value of the data track for this feature.

```
## Mandatory reads
1. docs/BACKEND_ARCHITECTURE.md §14.K (LOCKED) — the 15-fixture coverage
   matrix; each fixture's specific characteristic; the fixture JSON format
2. docs/BACKEND_ARCHITECTURE.md §14.F — the 2 ComplianceStrategy classes
   you write fixtures AGAINST (StandardComplianceStrategy for fixtures
   1-2 + 4-15; CollapsedComplianceStrategy for fixture 3 Eye-Serum only)
3. docs/MVP_ARCHITECTURE.md §5.5.7 — round-trip validation contract
4. docs/MVP_ARCHITECTURE.md §5.5.6 — the data shape the adapter relies on
   (the per-field schema_jsonb structure: canonical_name, display_label,
   meesho_column_header, meesho_column_index, primitive, marker,
   is_advanced, enum_codes_map, compliance_role)
5. docs/MEESHO_CATEGORY_INTELLIGENCE.md (LOCKED 2026-06-04) — §2 the 28
   practical universals, §3-9 super-category-specific compliance shapes
6. backend/app/data/category_attributes.json — the seeded source data;
   confirm each of the 15 fixture categories resolves
7. backend/app/data/meesho_category_tree.json — for super_id mapping
8. docs/plans/repo_management/MASTER_PLAN.md §5.5 (data PR template) +
   §2.1 (CI gate-5 golden_roundtrip requirement)
9. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan)
10. .claude/agents/meesell-xlsx-parser.md (your spec)

## Mission
Produce the 15 golden fixture JSON files + the fixture README. Verify
that the global tables (`templates.schema_jsonb`, `field_enum_values`,
`field_aliases.for_xlsx_export`) are comprehensively seeded for all 15
coverage points.

- backend/tests/integration/golden_round_trip/fixture_NN_<name>.json
  (15 files — see §3.1 backend table for the full list)
- backend/tests/integration/golden_round_trip/README.md (NEW)
- backend/app/data/category_attributes.json (MODIFY only if you find a
  seed gap during fixture authoring; otherwise read-only)
- backend/app/data/meesho_category_tree.json (MODIFY only if you find
  a seed gap; otherwise read-only)

## Acceptance criteria
[ ] All 15 fixture JSONs land at the path
    backend/tests/integration/golden_round_trip/ per §14.K naming
    fixture_NN_<name>.json
[ ] Each fixture has shape:
    {
      "input_snapshot": {
        "product": {"category_id": "...", "fields_jsonb": {...},
                    "ai_suggestions": {...}},
        "compliance_block": {...},
        "format": "xlsx_with_images"
      },
      "expected_xlsx_canonical": {
        "main_sheet_label": "...",
        "columns": [{"canonical_name": "...", "value": "..."}, ...]
      }
    }
[ ] Fixture 1 (Sarees) — Standard compliance baseline (super_id=11);
    `compliance_block` populated with the 9 standard fields; output
    columns count = input fields + 9 compliance pass-through
[ ] Fixture 2 (Mobiles) — Includes the typo restore: a column with
    `canonical_name = "no_of_primary_cameras"` in input maps to
    `expected_xlsx_canonical` value with the typo-restored
    `meesho_column_header = "No. of Primiary Cameras"` (verified via
    field_aliases.for_xlsx_export=TRUE seeding)
[ ] Fixture 3 (Eye-Serum, leaf=12378) — Collapsed compliance: input has
    9 compliance fields; `expected_xlsx_canonical` has 3 "Details"
    columns; concatenation separator `, ` (comma-space); empty input
    fields dropped from the concatenation
[ ] Fixture 4 (FSSAI Grocery, super_id=26) — `compliance_block` includes
    `fssai_license_number`; verifies the customer.get_compliance_block
    super_id branch
[ ] Fixture 5 (Kids Toys, super_id=13) — Optional BIS license; tests
    the optional-license path
[ ] Fixture 6 (Books, super_id=80) — Optional ISBN; tests the optional-
    extension shape
[ ] Fixture 7 (Beauty License) — Required license trio; tests the
    compulsory-extension branch
[ ] Fixture 8 (Home & Kitchen appliance, super_id=30) — Conditional
    license; tests the conditional-extension branch
[ ] Fixture 9 (Large dropdown — Compatible Models, 4,481 values) —
    Tests dropdown_api_search primitive
[ ] Fixture 10 (Brand-pattern, `brand` across 2 categories) — Same
    canonical_name with 2 different enum sources per category; tests
    the per-category enum-resolution branch
[ ] Fixture 11 (is_advanced field — `group_id` populated) — Verifies
    `group_id` writes verbatim to XLSX even though it's behind the
    Advanced toggle
[ ] Fixture 12 (Empty optional field) — Verifies the XLSX writes a
    blank cell, NOT literal "None" / "null" / "" with quotes
[ ] Fixture 13 (Number with unit — `weight: 500 g`) — 2 output columns
    (value + unit) per MVP_ARCH §5.6.1
[ ] Fixture 14 (Multi-line text — `description` with `\n`) — Newlines
    preserved through XLSX encoding
[ ] Fixture 15 (Special chars — `name: "Kurti & Top — 5""`) — Ampersand,
    em-dash, escaped double-quote preserved through XLSX encoding
[ ] README at backend/tests/integration/golden_round_trip/README.md
    documents: fixture JSON shape, how to author a new fixture, coverage
    matrix mapping fixture-NN to the §14.K characteristic
[ ] Verification report on seed comprehensiveness: for each of the 15
    fixture category_ids, confirm `templates.schema_jsonb` is non-empty
    AND `compliance_shape` is set AND all per-field
    `meesho_column_header` / `meesho_column_index` / `enum_codes_map` /
    `compliance_role` are populated. For Fixture 9, confirm the full
    4,481 enum values are seeded into `field_enum_values`. For Fixture 10,
    confirm both `brand` enum sets are seeded. For Fixture 2, confirm
    `field_aliases.for_xlsx_export=TRUE` with the typo-restored
    `meesho_column_header`.
[ ] CI gate-5 (golden_roundtrip) green when the services-builder runs
    `pytest backend/tests/modules/export/test_round_trip.py`. Confirm
    via cross-team smoke (data + backend pair on a dev box) BEFORE
    opening the data PR.

## Hard constraints
1. NO new top-level JSON file under backend/app/data/. Per-template data
   lives in templates.schema_jsonb (DB column), NOT in JSON files. The
   dispatch prompt's "backend/app/data/meesho_templates/{super_category}.json"
   framing is REJECTED.
2. NO authoring of ComplianceStrategy Python classes — those are
   services-builder territory per §14.F. Your output is the fixture
   JSONs that EXERCISE the strategies, not the strategies themselves.
3. NO modifications to backend/tests/modules/export/test_round_trip.py —
   that test runner is services-builder territory; you produce the
   fixtures it consumes.
4. NO direct GCS access in your fixtures — fixtures are static JSON
   data; no real GCS calls happen during fixture authoring.
5. NO modifications to MEESHO_CATEGORY_INTELLIGENCE.md — data lead
   authors the cross-link paragraph; your dispatch produces fixtures only.
6. If a seed gap is detected while authoring a fixture, the resolution
   is to MODIFY backend/app/data/category_attributes.json or
   meesho_category_tree.json with the missing rows AND flag the change
   in your PR body. DO NOT silently work around the gap with
   hand-crafted fixture data that doesn't reflect the seed.
7. The fixture's `expected_xlsx_canonical` value MUST be the canonical
   names — NOT meesho_column_header. The round-trip validator
   (services-builder owns) compares canonical-to-canonical.

## Files you may touch
- backend/tests/integration/golden_round_trip/fixture_*.json (15 NEW
  files)
- backend/tests/integration/golden_round_trip/README.md (NEW)
- backend/app/data/category_attributes.json (MODIFY — gap fills only,
  if any)
- backend/app/data/meesho_category_tree.json (MODIFY — gap fills only,
  if any)

## Files you must NOT touch
- backend/app/modules/export/** (services-builder + api-routes-builder
  territory)
- backend/app/shared/** + backend/app/alembic/**
- backend/tests/modules/export/test_*.py (services-builder owns the
  test runner)
- backend/tests/integration/test_export_full_pipeline.py
  (services-builder territory)
- frontend/** + k8s/** + terraform/**
- docs/V1_FEATURE_SPEC.md + docs/BACKEND_ARCHITECTURE.md +
  docs/MVP_ARCHITECTURE.md (LOCKED)
- docs/MEESHO_CATEGORY_INTELLIGENCE.md (data lead authors the cross-link)
- Any other feature's planning directory

## Final report format
1. Acceptance-criteria checklist
2. List of 15 fixture file paths + a 1-line description per fixture
3. Seed comprehensiveness verification: a 15-row table showing
   category_id, has_schema_jsonb (Y/N), has_compliance_shape (Y/N),
   compulsory_fields_count, enum_completeness (e.g., 4481/4481 for
   Compatible Models), typo_restore_present (Y/N for Fixture 2)
4. List of seed gaps detected + the modify-summary if any
   `category_attributes.json` / `meesho_category_tree.json` changes
   landed
5. Cross-team smoke result: `pytest backend/tests/modules/export/test_round_trip.py -v`
   run output (15 fixtures passing)
6. PR opened to feature/xlsx-export/data with
   .github/PULL_REQUEST_TEMPLATE/data.md filled — golden roundtrip
   evidence + parser-stat-equivalent summary (no parser run since this
   is fixture authoring; cite the smoke output instead)
7. feature_board_data.md row updated to IN REVIEW
```

### 7.7 `meesell-scraper-maintainer` (CONDITIONAL — dispatched by `meesell-data-engineer` only if template drift detected)

`{group} = data`. **Default: NOT DISPATCHED for V1.** Listed here for completeness.

```
## Trigger
This dispatch only fires if the quarterly Meesho refresh (post
`2026-06-04` snapshot date) shows template drift on any of the 15
fixture categories per §7.6 xlsx-parser dispatch. Default trigger
state: NOT TRIGGERED.

If triggered, the conditions are:
- data-engineer ran the scraper diff (`python scripts/scraper_diff.py
  --since 2026-06-04`) and the report flags ≥1 of the 15 fixture
  category_ids as DRIFTED (template column-set changed, new compulsory
  field added, enum-set changed for a Brand-pattern category, etc.)
- The drift is on a category the 15 fixtures cover

## Mandatory reads
1. docs/PLAYWRIGHT_MCP_REFERENCE.md (the scraper toolchain)
2. docs/MEESHO_CATEGORY_INTELLIGENCE.md (the baseline 2026-06-04
   snapshot)
3. data/snapshots/2026-06-04.json (the gitignored raw snapshot — the
   diff baseline)
4. The drift report produced by data-engineer
5. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan,
   especially the 15-fixture matrix)
6. .claude/agents/meesell-scraper-maintainer.md (your spec)

## Mission
Re-scrape ONLY the categories flagged as drifted. Produce a new
snapshot under data/snapshots/<today>.json. Hand the diff back to
xlsx-parser so they can update the affected fixture JSONs.

## Acceptance criteria
[ ] Re-scrape ONLY the drifted category leaves; do NOT re-scrape the
    full 3,772 corpus
[ ] Rate limit: ≥1 second between requests to the Meesho catalog page;
    respect robots.txt; never authenticate beyond the public catalog
[ ] New snapshot lands at data/snapshots/YYYY-MM-DD.json (gitignored)
[ ] Diff report at data/parsed/drift_YYYY-MM-DD_summary.md (gitignored)
    documenting per-category: was_vs_is (column-set delta, compulsory
    delta, enum delta), recommended fixture update, recommended seed
    update
[ ] data-engineer + founder review the drift report BEFORE xlsx-parser
    is re-dispatched on the affected fixtures

## Hard constraints
1. DO NOT scrape the full corpus (re-doing the 2026-06-04 work)
2. DO NOT commit raw XLSX files; only derived JSON ends up in git
3. DO NOT modify backend/app/data/* directly — produce the report;
   xlsx-parser modifies the data files
4. DO NOT modify any fixture JSON — xlsx-parser owns fixture updates

## Files you may touch
- data/snapshots/YYYY-MM-DD.json (NEW, gitignored)
- data/parsed/drift_YYYY-MM-DD_summary.md (NEW, gitignored)

## Files you must NOT touch
- backend/** (everything)
- frontend/** + k8s/** + terraform/**
- docs/* + .claude/* + any committed file

## Final report format
1. Trigger justification: "Drift detected on N of 15 fixture categories
   per <report path>"
2. Re-scrape stats: N pages re-fetched, N successes, N failures, wall time
3. Drift report path
4. Recommended next action: re-dispatch xlsx-parser on fixtures
   {fixture_NN, fixture_NN, ...} with the drift report as input
5. NO PR opened (the snapshot + drift report are gitignored)
```

### 7.8 `meesell-infra-builder` (standalone — founder dispatches or lead self-dispatches)

`{group} = infra`. This is the lightest dispatch in the feature.

```
## Mandatory reads
1. docs/INFRASTRUCTURE_PLAYBOOK.md — entire doc; especially the GCS
   bucket section + the worker deployment section
2. docs/INFRASTRUCTURE_ARCHITECTURE.md — namespace + manifest patterns
3. docs/BACKEND_ARCHITECTURE.md §14.I (LOCKED) — the GCS path convention
   the worker writes; the lifecycle rule that's expected
4. docs/BACKEND_ARCHITECTURE.md §3.I — Celery worker queue discovery
   (`include=["app.modules.image.tasks", "app.modules.export.tasks"]`)
5. .claude/agent-memory/meesell-infra-builder/MEMORY.md — entry D1
   (single bucket `meesell-prod-assets` decision) + the namespace
   migration entries
6. docs/plans/features/xlsx-export/FEATURE_PLAN.md (this plan,
   especially §2.2 D3 GCS bucket alignment)
7. docs/plans/repo_management/MASTER_PLAN.md §5.6 (infra PR template) +
   §3.1 environment strategy

## Mission
Three small infra deltas:

1. Add the `export` Celery queue to the worker pod's args (dev manifest
   + staging mirror)
2. Add a 30-day GCS lifecycle rule on the `meesell-prod-assets` bucket
   for the `meesell-exports/` prefix
3. Append an xlsx-export runbook paragraph to INFRASTRUCTURE_PLAYBOOK.md

## Acceptance criteria
[ ] k8s/dev/worker-deployment.yaml: the worker pod's args reference the
    `export` queue alongside the existing `image_precheck` queue. The
    actual celery worker command becomes
    `celery -A app.workers.celery_app worker -Q image_precheck,export
     --concurrency=2 --loglevel=info`
[ ] k8s/staging/worker-deployment.yaml mirrors the dev change
[ ] Lifecycle rule applied to gs://meesell-prod-assets:
    - rule.condition.matchesPrefix = ["meesell-exports/"]
    - rule.condition.age = 30 (days)
    - rule.action.type = "Delete"
    Land via Terraform (preferred) at terraform/gcs/lifecycle.tf OR
    inline in terraform/gcs/buckets.tf. Verify with
    `gsutil lifecycle get gs://meesell-prod-assets | jq '.rule[]
     | select(.condition.matchesPrefix[]? == "meesell-exports/")'`
[ ] No new bucket. No new IAM binding. No new K3s Service.
[ ] `terraform plan` clean against the live state (paste the Plan: X
    to add, Y to change, Z to destroy summary in PR body — expectation
    is Plan: 0 to add (or 1 to add if lifecycle.tf is NEW), 1 to change,
    0 to destroy)
[ ] `kubectl apply --dry-run=server -f k8s/dev/worker-deployment.yaml`
    clean; same for staging
[ ] Smoke deploy to dev: `kubectl rollout status deploy/worker -n dev`
    Ready; `kubectl logs deploy/worker -n dev | grep -E "image_precheck|export"`
    shows both queues subscribed
[ ] INFRASTRUCTURE_PLAYBOOK.md gets a one-paragraph entry under the
    runbooks section describing: how to inspect a stuck export Celery
    task, how to verify the lifecycle policy, the projected GCS cost
    at scale (1K sellers × ~50MB/seller/month = 50GB/month before 30d
    cleanup)
[ ] Cost impact statement: lifecycle adds < ₹1/month (lifecycle action
    free in GCS pricing); export queue adds 0 new pods (reuses existing
    worker capacity). No founder cost approval needed.

## Hard constraints
1. DO NOT provision a separate GCS bucket. The dispatch's "meesell-exports
   bucket separate from meesell-images" framing is REJECTED per founder
   D3. Single bucket meesell-prod-assets stays.
2. DO NOT add new IAM bindings. The existing backend SA + worker SA
   already have roles/storage.objectAdmin on meesell-prod-assets.
3. DO NOT spin up a second worker deployment for export — reuse the
   existing worker pod. The Celery worker can subscribe to multiple
   queues via -Q image_precheck,export.
4. DO NOT change worker pod CPU/memory resources without founder
   approval (the existing 250m/500MiB is sized for image_precheck +
   export combined per infra-builder memory cost budget).
5. DO NOT amend §14.I in BACKEND_ARCHITECTURE.md. The path-prefix
   delta is documented in this FEATURE_PLAN.md §2.2 D3 — that's the
   single source of truth.
6. DO NOT touch any application code, frontend, alembic, or docs/* other
   than the playbook paragraph.

## Files you may touch
- k8s/dev/worker-deployment.yaml (MODIFY — add export queue to args)
- k8s/staging/worker-deployment.yaml (MODIFY — mirror)
- terraform/gcs/lifecycle.tf (NEW) OR terraform/gcs/buckets.tf
  (MODIFY — inline lifecycle rule block)
- docs/INFRASTRUCTURE_PLAYBOOK.md (MODIFY — 1 paragraph addition)

## Files you must NOT touch
- backend/** + frontend/** (zero)
- k8s/{api-deployment.yaml, frontend-deployment.yaml, postgres.yaml,
  valkey.yaml, ingress.yaml, namespace.yaml, secrets.yaml, *-cronjob.yaml}
  (out of scope)
- terraform/{compute,iam,secrets,networking,artifacts}/** (out of scope
  for this feature)
- docs/V1_FEATURE_SPEC.md + docs/BACKEND_ARCHITECTURE.md +
  docs/MVP_ARCHITECTURE.md (LOCKED)
- Any other feature's planning directory

## Final report format
1. Acceptance-criteria checklist
2. `terraform plan` output excerpt (Plan: X to add, Y to change, Z to
   destroy)
3. `kubectl apply --dry-run=server` outputs for dev + staging worker
   manifests
4. `kubectl rollout status deploy/worker -n dev` Ready confirmation
5. `kubectl logs deploy/worker -n dev | grep -E "image_precheck|export"`
   showing both queues
6. `gsutil lifecycle get gs://meesell-prod-assets | jq ...` output
   confirming the new rule lands
7. Cost impact: < ₹1/month delta (lifecycle action free)
8. INFRASTRUCTURE_PLAYBOOK.md diff paragraph (paste the new section)
9. PR opened to feature/xlsx-export/infra with infra PR template filled
10. feature_board_infra.md row updated to IN REVIEW
```

---

## Review + iteration protocol

### 8.1 Per-specialist lead-review checks

When a specialist opens their PR to `feature/xlsx-export/{group}`, the lead runs this checklist BEFORE clicking Approve.

**Backend lead reviewing services-builder PR:**

- [ ] 9-step pipeline order matches `MVP_ARCH §5.5` verbatim — step name AND step semantics
- [ ] Layer 3 guardrail at step 5 is wired BEFORE step 6 (column reorder); reject if step order is swapped
- [ ] `image.service.get_image_bytes` is called via the service surface; reject if `adapters.gcs.download_bytes` is called directly from inside `_package_images_zip`
- [ ] `catalog.service.get_product_for_export` and `customer.service.get_compliance_block` are called via service surface; reject if repository imports cross the §16 boundary
- [ ] Round-trip validation (step 9) is wired BEFORE GCS upload; reject if upload happens before validation
- [ ] Generated XLSX opens cleanly in BOTH Excel AND LibreOffice — verify by downloading the fixture-1 output to local laptop + opening in both apps; record screenshots in PR body
- [ ] All 15 golden fixtures pass: `pytest backend/tests/modules/export/test_round_trip.py -v` shows 15/15 green
- [ ] Generation budget met: integration test wall-time ≤15s for 1-product + 6-image (paste the timestamp)
- [ ] GCS path is the locked scheme: `gs://meesell-prod-assets/meesell-exports/{user_id}/{export_id}/sheet.xlsx`
- [ ] Signed URL TTL is exactly 3600 seconds; reject if 86400 (24h) or 300 (5min)
- [ ] Audit writes (`export.completed`, `export.failed`) happen via direct ORM write from `tasks.py`; reject if a helper module was created
- [ ] No `meesho_column_header` / `meesho_column_index` / `enum_codes_map` symbol appears in any file outside `modules/export/`; the §19 CI linter check is green
- [ ] Runbook at `docs/runbooks/xlsx-export-troubleshooting.md` covers all 7 error_codes from §14.H
- [ ] CI gate-5 step wired in `.github/workflows/ci.yml`
- [ ] PR template `.github/PULL_REQUEST_TEMPLATE/backend.md` filled completely — migration evidence (cite database-builder's PR), integration test results, 15-fixture roundtrip pass count
- [ ] Specialist's MEMORY.md has a session-close entry; feature_board_backend.md row is IN REVIEW with the PR link

**Backend lead reviewing api-routes-builder PR:**

- [ ] 2 routes mount at the §0.C / §17 paths exactly; endpoint inventory count is 30 (or whatever the current head is + 2)
- [ ] Pydantic schemas in `schemas.py` match §14.G verbatim; no extra fields; no M10-violating fields
- [ ] Feature flag check at POST returns 404 (not 503) when disabled; verify in the router test
- [ ] Rate limit decorator on POST; no decorator on GET
- [ ] No business logic in route handlers; the handlers delegate to service.py
- [ ] PR template filled

**Backend lead reviewing database-builder PR:**

- [ ] DDL matches `MVP_ARCH §2.5` exactly — 11 columns, 2 indexes, 2 CHECK constraints
- [ ] Down-revision SHA is the current head per the chain
- [ ] `alembic upgrade head` clean on dev DB
- [ ] `alembic downgrade -1` clean on dev DB (then re-upgrade)
- [ ] No PostgreSQL ENUM types — VARCHAR + CHECK only
- [ ] No uniqueness constraint on `(user_id, product_id)` — D1 confirms idempotency is at the experience layer
- [ ] Schema-smoke test passes for the new table
- [ ] PR template `Database migration` section filled

**Frontend lead reviewing angular-component-builder PR:**

- [ ] Zero direct PrimeNG imports in `features/export/` — grep verifies
- [ ] Zero `@angular/material/...` imports anywhere — grep verifies
- [ ] All components `standalone: true` with `ChangeDetectionStrategy.OnPush`
- [ ] Multi-error 422 render shows BOTH a toast AND an inline error list (not just one); test with mocked 422 response in the spec file
- [ ] Polling sub-component renders progress + status badge + download CTA + retry CTA states; test with each state stub
- [ ] Screenshots at 360px + 1280px attached to PR description
- [ ] Build < 90s
- [ ] PR template `.github/PULL_REQUEST_TEMPLATE/frontend.md` filled completely

**Frontend lead reviewing angular-service-builder PR:**

- [ ] Exponential backoff schedule matches the contract (1s → 2s → 4s, cap at 4s, 60s wall-time max); test traces the timing
- [ ] No `any` types; strict TypeScript clean
- [ ] No localStorage / sessionStorage writes for export state
- [ ] takeUntilDestroyed (or equivalent) on every long-lived subscription
- [ ] PR template filled

**Data lead reviewing xlsx-parser PR:**

- [ ] All 15 fixture JSONs land at the locked path with the locked name pattern
- [ ] Each fixture's `input_snapshot` + `expected_xlsx_canonical` shape matches §14.K format
- [ ] Fixture 2 typo restore: `expected_xlsx_canonical` confirms the typo-restored header surfaces via the round-trip validator's canonical re-map
- [ ] Fixture 3 Eye-Serum: 9 input compliance fields → 3 output `Details` columns; concatenation separator is `, ` (comma-space); empty inputs dropped
- [ ] Fixture 9 large dropdown: 4,481 `Compatible Models` enum values are seeded into `field_enum_values` (verify with the seed-comprehensiveness verification report)
- [ ] Fixture 15 special chars: special characters round-trip cleanly
- [ ] CI gate-5 green: `pytest backend/tests/modules/export/test_round_trip.py -v` shows 15/15
- [ ] README at `backend/tests/integration/golden_round_trip/README.md` covers fixture format + author-new-fixture procedure
- [ ] No new top-level JSON under `backend/app/data/meesho_templates/` (the rejected dispatch framing); confirm with grep
- [ ] PR template `.github/PULL_REQUEST_TEMPLATE/data.md` filled — golden roundtrip evidence + seed-comprehensiveness verification

**Infra lead reviewing own PR (self-review for the standalone dispatch):**

- [ ] `terraform plan` output: Plan: 0 to add, 1 to change, 0 to destroy (or 1 to add if lifecycle.tf is new file)
- [ ] `kubectl apply --dry-run=server` clean for both dev + staging
- [ ] Smoke deploy to dev: `kubectl rollout status deploy/worker -n dev` Ready
- [ ] Lifecycle rule visible via `gsutil lifecycle get gs://meesell-prod-assets | jq ...`
- [ ] No new bucket, IAM binding, or Service
- [ ] Cost impact statement: < ₹1/month
- [ ] PR template `.github/PULL_REQUEST_TEMPLATE/infra.md` filled

### 8.2 Re-dispatch triggers + prompt template

When a PR fails review, the lead returns the PR with comments AND a fresh dispatch. The re-dispatch is NOT a new specialist — the same specialist is dispatched with a "session-{N+1}" header and a preamble explaining the failure.

**Common failure modes + the targeted re-dispatch:**

| Failure mode | Lead | Re-dispatch preamble (prepended to the §7 template) |
|---|---|---|
| XLSX opens in Excel but fails in LibreOffice | Backend | `Previous run produced an XLSX that opens in Excel but fails in LibreOffice. Inspect the openpyxl write path in `_write_xlsx`; verify the worksheet is NOT in write_only mode; verify shared-strings encoding; verify the file is saved with `wb.save(output_stream)` not `wb.save(filename)` so the stream is closed cleanly. Re-test on BOTH Excel + LibreOffice before re-opening the PR.` |
| Image-reference column mismatch with ZIP filenames | Backend | `Previous run produced an XLSX where the image-reference column values do not match the ZIP filenames byte-for-byte. Verify your `_package_images_zip` writes filenames matching the schema's image_filename_template for the relevant category (the template is in schema_jsonb.fields[] entry for the image field). Cross-check Fixture 12 (empty optional image) and Fixture 15 (special chars). Re-run the 15-fixture round-trip before re-opening.` |
| Generation >15s on integration test | Backend | `Previous run measured wall-time of N seconds on the 1-product-6-image integration test, exceeding the 15s target (30s hard ceiling). Top suspects: (1) image.service.get_image_bytes is called sequentially per image instead of via gather/asyncio batch; (2) openpyxl row writes are buffered not streamed; (3) GCS upload happens after the worker resolves both XLSX + ZIP bytes when it could parallelise; (4) cache misses on the schema fetch (first call cold-paths). Profile with cProfile and surface the top-3 hotspots in the re-dispatch's report. Re-test the 15s target.` |
| Layer 3 guardrail not fired on bad enum | Backend | `Previous run shipped an XLSX with an unknown enum value (Fixture N showed canonical "X" → meesho_enum "X" without ExportEnumValidationError). Verify Celery task calls `_translate_enums` BEFORE writing to GCS; verify the dictionary lookup uses `field_enum_values.enum_entries[canonical]` not a fallback. Re-test with a deliberately-malformed fixture.` |
| Missing screenshot at 360px or 1280px | Frontend | `Previous PR was missing one of the required screenshots. Capture at both 360px and 1280px using the browser's responsive design mode; attach both to the PR description before re-opening.` |
| `any` type detected in TypeScript | Frontend | `Previous PR had a non-strict type leak (tsc surfaced "any" usage at file:line). Fix by typing explicitly or using `as` with a concrete type. Re-run `pnpm tsc --noEmit` and confirm clean before re-opening.` |
| Fixture N round-trip fail | Data | `Previous run produced fixture_NN_<name>.json that failed the round-trip test with mismatch on canonical field "X". Inspect: (1) is the seed for category Y populated correctly? (2) is the expected_xlsx_canonical column ordering matching schema_jsonb.fields[] index? (3) is the enum_codes_map populated for canonical "X"? Either fix the fixture, fix the seed, or escalate to backend if `_translate_enums` is mis-translating.` |
| Terraform plan unexpectedly destroys a resource | Infra | `Previous terraform plan showed Plan: A to add, B to change, C to destroy where C > 0. Lifecycle rule changes should NEVER produce destroys. Inspect: (1) is the rule clobbering an existing lifecycle on a different prefix? (2) is the rule applying at bucket-level instead of prefix-level? Use `terraform plan -target=...` to isolate the change before re-opening.` |

### 8.3 Re-dispatch ordinal + max iteration count

- The session ordinal increments on each re-dispatch: `session-1` → `session-2` → `session-3`...
- Max iteration count: **3** for backend, frontend, infra. Beyond 3 → escalate to founder.
- Max iteration count: **4** for data (xlsx-parser). Per the dispatch's note: Meesho template edge cases are surface; the 4th iteration buys headroom for the fixture-authoring path. Beyond 4 → escalate.
- The escalation message goes to the founder via the lead's own `STATUS_<domain>.md` blockers section per master plan §7.3.

### 8.4 Cross-lead dependencies during review

- **services-builder PR depends on database-builder PR merge** — because services-builder's integration test runs `alembic upgrade head` against the dev DB. database-builder MUST merge first.
- **services-builder PR depends on xlsx-parser PR merge** — because the round-trip test loads the 15 fixtures. xlsx-parser MUST merge first OR their commits can land on the same branch (`feature/xlsx-export/backend` and `feature/xlsx-export/data` can both push to `feature/xlsx-export` in parallel, then the round-trip test on `feature/xlsx-export` passes once both merge).
- **angular-component-builder PR depends on angular-service-builder PR merge** — because the component imports the service. Component-builder rebases after service-builder merges to `feature/xlsx-export/frontend`.
- **All group PRs to `feature/xlsx-export` are independent** (per master plan §2.5). The founder approves the `feature/xlsx-export → develop` PR only when all 4 group PRs are merged.

---

## Acceptance gate

The feature is considered shipped to `develop` (the V1 destination) when **all** of the following are true. The founder verifies before approving the `feature/xlsx-export → develop` PR.

### 10.1 Implementation completeness

- [ ] All 8 PRs (services-builder, api-routes-builder, database-builder, angular-component-builder, angular-service-builder, xlsx-parser, [scraper-maintainer if dispatched], infra-builder) have merged to `feature/xlsx-export`
- [ ] `feature/xlsx-export` rebased on current `develop` tip
- [ ] All 5 CI gates green on `feature/xlsx-export`: gate-1 unit, gate-2 smoke, gate-3 lint, gate-4 integration, gate-5 golden_roundtrip (15/15 fixtures)
- [ ] Endpoint inventory in `BACKEND_ARCHITECTURE.md §17` updated from 28 → 30
- [ ] Alembic head divergence check between dev and staging: zero divergence

### 10.2 Correctness verification

- [ ] **Cross-suite XLSX**: Generated XLSX from at least 3 fixtures (Sarees, Eye-Serum, FSSAI Grocery) opens cleanly in BOTH Microsoft Excel AND LibreOffice. Screenshots in the merge PR description.
- [ ] **Round-trip pass**: `pytest backend/tests/modules/export/test_round_trip.py -v` shows 15/15 green on 3 consecutive runs
- [ ] **Generation budget**: 1-product + 6-image integration test runs in ≤15s wall time on the `dev` namespace; ≤30s on the slowest tier per `MVP_ARCH §5.5.10` ceiling
- [ ] **Layer 3 guardrail**: a deliberately-malformed test fixture (invalid canonical enum) triggers `ExportEnumValidationError` and the worker marks `exports.status='failed'` with `error_code='enum_validation_failed'`
- [ ] **Image-reference match**: ALL 15 fixtures' image-reference columns match the ZIP filenames byte-for-byte
- [ ] **Idempotent retry**: a failed export → re-clicking "Generate XLSX" → fresh export_id, fresh `exports` row, fresh round-trip; verified with one fixture re-run after a forced failure

### 10.3 Documentation completeness

- [ ] OpenAPI auto-generated docs render both routes with status codes and validation_message_id keys
- [ ] Runbook at `docs/runbooks/xlsx-export-troubleshooting.md` exists and is linked from `docs/runbooks/README.md`
- [ ] `INFRASTRUCTURE_PLAYBOOK.md` xlsx-export paragraph exists
- [ ] Golden fixture README at `backend/tests/integration/golden_round_trip/README.md` exists
- [ ] `MEESHO_CATEGORY_INTELLIGENCE.md` cross-link paragraph exists
- [ ] `V1_FEATURE_SPEC.md §F9` marked `**Implemented:** YYYY-MM-DD — PR #NN`

### 10.4 Operational signals

- [ ] feature_board for backend, frontend, data, infra shows xlsx-export in "Recently merged" with PR links
- [ ] STATUS_MASTER.md sprint-ready subsection has each involved lead signed off
- [ ] Manual Meesho upload smoke completed for at least 1 generated XLSX (founder records in STATUS_BACKEND.md)
- [ ] Staging feature flag `FEATURE_XLSX_EXPORT_ENABLED=true` only AFTER 3 consecutive green CI gate-5 runs + manual Meesho upload acceptance per §2.2 D2

### 10.5 Sentinel updates

- [ ] No `meesho_column_header` / `meesho_column_index` / `enum_codes_map` symbol leaks outside `app/modules/export/` — §19 CI linter check green
- [ ] No new top-level JSON file under `backend/app/data/meesho_templates/` — confirms the rejected dispatch framing did not slip in
- [ ] No `from primeng/` import in `frontend/src/app/features/export/` — grep clean
- [ ] No `from @angular/material/` import anywhere in `frontend/` — grep clean

---

## Risk register

### 11.1 Risk #1 — Meesho changes a category template mid-V1 invalidating a fixture

**Likelihood:** Medium. The 2026-06-04 snapshot is the baseline; Meesho has a history of quarterly XLSX updates per `MEESHO_CATEGORY_INTELLIGENCE.md` §1.

**Impact:** High. A drifted template means a fixture's `expected_xlsx_canonical` is wrong → round-trip fails → CI gate-5 red → backend cannot merge to `develop` → blocked sprint.

**Mitigation:**
- The conditional `scraper-maintainer` dispatch (§7.7) is the detection mechanism. Data lead runs the quarterly diff and triggers if drift detected.
- The fixture authoring protocol (§7.6) makes each fixture independently re-authorable — no fixture depends on another.
- If gate-5 goes red mid-sprint, the leaden response is to either (a) update the affected fixture + seed in a hotfix PR, or (b) defer that fixture's coverage to V1.5 (acceptable for non-customer-facing edge cases).

### 11.2 Risk #2 — openpyxl / LibreOffice compatibility edge case on FSSAI compulsory columns

**Likelihood:** Medium. Per memory, FSSAI super-categories require compulsory food-safety columns that include long-form text. LibreOffice has occasionally rendered openpyxl-generated cells differently from Excel for >32k-char cells.

**Impact:** High. If the FSSAI Grocery fixture (#4) renders differently in LibreOffice than Excel, the seller's Meesho upload may bounce → primary value prop damaged.

**Mitigation:**
- Acceptance criterion in services-builder dispatch: manually open the generated XLSX in BOTH Excel + LibreOffice; screenshots required in PR.
- Fixture 14 (multi-line) specifically tests newline preservation; FSSAI columns inherit the same encoding path.
- If the issue surfaces, the resolution is to switch `_write_xlsx` to explicit shared-strings encoding mode OR to add a per-cell type hint (string vs long-string).

### 11.3 Risk #3 — Image bytes fetch latency under congested network blows 15s budget

**Likelihood:** Medium. The integration test runs against the dev VM tunnel; production network conditions may differ.

**Impact:** Medium. Generation time creeps from 9s baseline to 18s — over the §F9 target but under the §5.5.10 30s ceiling. Sellers see slower UX but the export still completes.

**Mitigation:**
- Acceptance criterion in services-builder dispatch: measure on the dev VM; flag any >15s result as a follow-up perf task.
- The frontend's polling backoff (1s → 2s → 4s, 60s wall-time cap) gives 4× headroom over the 15s target.
- V1.5 perf task: batch `image.service.get_image_bytes` calls via `asyncio.gather`; pre-warm the schema cache at worker startup; explore GCS read parallelism.

### 11.4 Risk #4 — Signed URL expiry mid-download for large ZIP transfers

**Likelihood:** Low. 1h signed URL TTL + browser download progress is typically <5 minutes for a ~5MB ZIP.

**Impact:** Low-Medium. Seller on slow network sees broken download mid-transfer.

**Mitigation:**
- The `get_export` endpoint generates FRESH signed URLs per response per §14.B.2 — the frontend can re-poll to refresh the URL.
- The angular-service-builder dispatch covers 503 retry logic — though 503 is mid-call, NOT mid-download. Browser-level interrupted-download retry is out of scope for V1.
- V1.5 may extend the TTL to 4h or move to resumable downloads.

### 11.5 Risk #5 — V1.5 bulk-export forces an `exports` table schema migration

**Likelihood:** High (V1.5 is committed scope).

**Impact:** Medium. The current schema is single-product (one `product_id` per row). Bulk export needs either a join table (`exports` ↔ `products`) or a JSONB array column on `exports`.

**Mitigation:**
- The database-builder dispatch is constrained to the §2.5 schema — no premature optimisation for V1.5 in V1.
- V1.5 migration will add a new table `export_products(export_id, product_id, idx)` and either (a) deprecate `exports.product_id` (nullable for V1.5 bulk-exports) or (b) keep `exports.product_id` for the first product (with `export_products` for the rest).
- Documented as a known forward debt in this risk register.

### 11.6 Risk #6 — Celery export worker OOM on large image batches

**Likelihood:** Low. V1 caps at 6 images per product × ~1MB per image = ~6MB; the worker pod's 500MiB RAM accommodates this with margin.

**Impact:** High. OOM crashes the worker pod, killing ALL in-flight export tasks (not just the failing one).

**Mitigation:**
- The infra-builder dispatch explicitly preserves the existing 250m/500MiB worker resource limits — no premature growth.
- If observed in production, the resolution is (a) stream the ZIP bytes instead of buffering, (b) bump worker memory limit to 1GiB, or (c) introduce a separate export-only worker pod (escalates to founder per master plan §7.3).

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-10 | master Director session (`mesell-xlsx-export-planning-session-1`) | Initial draft. 6 decisions locked (D-A, D-B, D-C, D1, D2, D3). 8 dispatch templates. 15-fixture matrix from §14.K. Architecture corrections vs dispatch prompt documented in pre-Decisions preamble. |
| v2 | 2026-06-10 | master Director session (`mesell-xlsx-export-amendment-session-1`) | Canonical pattern v2 conformance. Heading numeric prefixes stripped + parentheticals removed. `## Agent lineup` moved to canonical slot 2 (was slot 4). `## Branch setup` (slot 5) + `## Memory protocol` (slot 6) authored fresh. `## 6 Common dispatch template preamble` demoted to `### Common preamble` inside `## Dispatch templates`. `## 9 Cross-agent broadcast protocol` relocated as `### Cross-agent broadcast protocol` inside `## Memory protocol`. `## 12 Glossary` demoted to `### Glossary` inside `## Documentation deliverables`. Original `## 1 Status preamble` + `### 1.1 Pre-flight reality check` preserved as preamble prose before `## Decisions`. Content body preserved verbatim per amendment dispatch Case B. |
