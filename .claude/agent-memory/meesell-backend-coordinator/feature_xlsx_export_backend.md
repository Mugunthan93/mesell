# feature_xlsx_export_backend.md — XLSX Export (V1 Feature 9) backend lead memo

Governing plan: `docs/plans/features/xlsx-export/FEATURE_PLAN.md` (PLAN READY, 1853 lines).
Architecture: `BACKEND_ARCHITECTURE.md §14` (export module — LOCKED 2026-06-05).

## STEP 1 (2026-06-12, mesell-xlsx-export-backend-session-1) — as-built audit + branch + SPECs

**VERDICT: 5th consecutive burn-rebuild feature. Module ~100% BUILT on develop @ 48ec697.**
Same pattern held for auth-otp / smart-picker / catalog-form / image-precheck. AUDIT-FIRST paid off again.

### BUILT (do NOT re-author)
- All 8 export module files (`backend/app/modules/export/*.py`).
- Full 9-step pipeline in `service.py`: `_run_export_pipeline` (L290) orchestrates resolve_schema/select_strategy/
  build_row/apply_strategy/translate_enums (Layer-3 guardrail L637)/reorder/restore_aliases/write_xlsx (openpyxl L731)/
  round_trip_validate (L759)/package_images_zip (L824).
- 3 ComplianceStrategy concretes + MeeshoExportAdapter (`domain.py`); 7 exceptions (`exceptions.py`).
- `tasks.py` export_xlsx_task (bind=True) → asyncio.run(_run_export_pipeline).
- `router.py` POST /products/{id}/export-xlsx (202, @rate_limit export_initiate 10/3600, @audit_event) + GET /exports/{id}.
- `main.py` L142 registers export_router UNCONDITIONALLY (this is the G2/G3 surface — no flag gate).
- `exports` table in baseline migration `935e55b4852c` L157. Single head `f31c75438e61`. database-builder = SKIP.
- Cross-module contracts wired & correct: catalog.assert_product_ownership(product_id, user_id, db) [R5 keyword-db];
  catalog.get_product_for_export; customer.get_compliance_block(user_id, db); image.list_images(user_id, product_id, *, db)
  front-image gate L185 (idx==1 & status=='ready'). NOTE: ZIP packager calls gcs.download_bytes(path) directly, NOT
  image.get_image_bytes — get_image_bytes is the §11.C published surface but not a live export call site.
- Tests: 10 unit + 6 router + 3 integration (happy/blocked-by-failed-precheck/round-trip-failure) + perf +
  15 golden fixtures + `test_golden_fixtures_runner.py` (gate-5 @pytest.mark.golden_roundtrip). Lint contract-9 present.
- CI gate-5 WIRED ci.yml L378-485; marker registered pytest.ini L27. `openpyxl==3.1.5` already in requirements (PR #85).

### REAL GAPS (only 2.5)
- **G1** — `FEATURE_XLSX_EXPORT_ENABLED` absent. `shared/config.py` L184 has only FEATURE_SMART_PICKER_ENABLED.
  Add bool default True in §3.2 block (L179-184), smart-picker comment style + D2 staging-gate note.
- **G2** — export `router.py` initiate_export (L102+) has NO flag-gate, doesn't import settings. PROVEN PATTERN =
  smart-picker `category/router.py:117` in-handler 404 (NOT catalog-form's main.py conditional-include — that pattern's
  PR #115 still OPEN to develop). FEATURE_PLAN D2: POST 404 when disabled; GET stays UNGATED (in-flight poll).
- **G3** — no flag-404 test (smart-picker has test_suggest_flag_404.py). Bundle with G2.

### SPECIALIST LINEUP RULING
- **api-routes-builder** owns G1+G2+G3 in ONE slice (config flag + router 404 + test). ONLY code dispatch.
- services-builder VERIFY-ONLY (no gap). database-builder SKIP/VERIFY-ONLY (table in baseline).
- No parallelism — single specialist.

### FOUNDER RULINGS
- R1 (recommend) — confirm GET /exports/{id} stays UNGATED (POST-only flag short-circuit per D2). Not hard-blocking.
- R2 (FYI only) — plan §3.1 names gate-5 runner `test_round_trip.py`; as-built is `test_golden_fixtures_runner.py`.
  Gate-5 wired & green to as-built path. PR-body note, no amendment.

### BRANCH
feature/xlsx-export/backend off origin/develop @ 48ec697, pushed @ 48ec697, worktree /tmp/mesell-wt/xlsx-export-backend.
D/F playbook: leaf feature/xlsx-export NOT created; reconstituted at gate time. No D/F conflict on origin.

### microservices-export vs xlsx-export DISTINCTION
`microservices-export` board row = POST-V1 extraction of the export MODULE (`docs/plans/microservices_migration/`,
SUB_PLAN_01). xlsx-export = V1 Feature 9 (the export feature code in `backend/app/modules/export/`). ZERO file overlap.

### GOTCHAS carried forward
- Py3.11 master-venv session-loop ordering artifact: new async test dirs give false reds at tail-of-full-suite; run in
  isolation; CI Py3.12 green (catalog-form precedent).
- D/F refname: leaf cannot coexist with sub-refs; reconstitute leaf at gate time via local squash.
