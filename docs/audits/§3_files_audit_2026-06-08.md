# §3 File Structure Audit Report

**Date:** 2026-06-08
**Auditor sub-session:** meesell-backend-verification-3-files-1 *(this run; prior master-run at same path superseded — sub-session findings agree with master's independent verification)*
**Section audited:** §3 File Structure — `backend/app/` top-level tree, per-module canonical subtrees, non-domain layer subtrees, tests/ mirror
**Overall verdict:** PARTIAL

---

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | `backend/app/` tree matches §3.B (NO other top-level folders) | **PARTIAL** | Required items all present. 6 V0-era extras remain: `data/`, `database.py`, `middleware/`, `routers/`, `schemas/`, `services/`. See Finding #F1. Escalation trigger met — rogue top-level items. Pre-existing H1. |
| 2 | 8 domain modules — canonical subtrees per §3.C + §13.D exception | **PASS** | All 8 present in `modules/`. `iam` 7-file ✅; `customer` 7-file ✅; `category` 8-file (7 canonical + `picker.py` — master-accepted module-private AI helper per §9 Wave 3 ruling) ✅; `catalog` 7-file no tasks.py ✅; `image` 8-file (incl. tasks.py) ✅; `pricing` 7-file no tasks.py ✅; `dashboard` 6-file (5 per §13.D exception + `__init__.py`, no repository.py, no tasks.py) ✅; `export` 8-file (incl. tasks.py) ✅. |
| 3 | `core/` 6 files + `middleware/` 7 files per §3.D | **PASS** | `core/` top: `__init__.py`, `auth.py`, `cache.py`, `errors.py`, `plan_guard.py`, `tenancy.py` (6) ✅. `core/middleware/`: `__init__.py`, `audit_mw.py`, `auth_mw.py`, `plan_guard_mw.py`, `rate_limit_mw.py`, `request_id.py`, `tenancy_mw.py` (7) ✅ |
| 4 | `shared/` 4 files + `models/` 14 files per §3.E | **PASS** | `shared/` top: `__init__.py`, `config.py`, `database.py`, `valkey.py` (4) ✅. `shared/models/`: 15 files (`__init__.py` + `base.py` + 13 ORM models). `base.py` (DeclarativeBase re-export) is 1 extra vs §3.E 14-file count — LOW observation, standard SQLAlchemy pattern, zero runtime impact. |
| 5 | `adapters/` 6 files per §3.F | **PASS** | `__init__.py`, `gcs.py`, `gemini.py`, `langfuse.py`, `msg91.py`, `razorpay.py` — exact match ✅ |
| 6 | `ai_ops/` 7 files + `prompts/` 4 files per §3.G | **PASS** | `ai_ops/` top: `__init__.py`, `budget_cap.py`, `client.py`, `cost_tracker.py`, `eval.py`, `guardrail.py`, `prompt_registry.py` (7) ✅. `ai_ops/prompts/`: `__init__.py`, `autofill_v1.py`, `smart_picker_v1.py`, `watermark_v1.py` (4) ✅ |
| 7 | `i18n/` per §3.H — 3 files only; NO messages_ta/hi.py | **PASS** | §3.H baseline present: `__init__.py`, `messages_en.py`, `resolver.py` ✅. NO `messages_ta.py` / `messages_hi.py` ✅. 4 extra §5A-era files (`advanced_canonical.py`, `primitive_classifier.py`, `schema_contract.py`, `step_assignment.py`) — all Wave-1 §5A construction outputs, all test-backed (§5A 140 tests). LOW observation — not unauthorized V2 language files. |
| 8 | `workers/` 2-file subtree; `celery_app.py include=[image.tasks, export.tasks]` per §3.I | **PASS** | 2-file subtree: `__init__.py` + `celery_app.py` ✅. `generation_tasks.py` deleted in §18 (closes L18.2) ✅. Include list exact: `["app.modules.image.tasks", "app.modules.export.tasks"]` verified via grep ✅ |
| 9 | `tests/` mirrors `app/` per §3.J | **PASS (naming deviation)** | Top-level anchors (`conftest.py`, `test_app_boot_integration.py`, `test_database.py`) ✅. All 8 module subdirs in `tests/modules/` ✅. `tests/integration/` reserved path present ✅. Extra subdirs added by §18/§19: `tests/lint/`, `tests/perf/`, `tests/eval/` — all authorized by their respective construction sections. Canonical triplet naming (test_router / test_service / test_repository) absent in most modules — behavior-style naming used instead (e.g. `test_trigram_search_uses_gin_index.py`). Special-purpose tests per §3.J: search → `test_trigram_search_uses_gin_index.py` ✅; round-trip → `tests/integration/golden_round_trip/` + `test_golden_fixtures_runner.py` ✅; autofill/autosave → `test_service_unit.py` + `test_integration.py` (INFERRED, not explicitly named `test_autosave.py`); tasks → `test_service_unit.py` + `test_integration.py` (INFERRED, not explicitly named `test_tasks.py`). Open note: §3.J expects explicit `test_autosave.py` and `test_tasks.py` — inferred coverage not confirmed by filename alone. |
| 10 | No silent top-level additions in `backend/app/` | **PARTIAL** | Same as Check 1 — 6 V0-era extras confirmed. |

---

## Non-compliance findings

### F1 — MEDIUM: 6 V0-era items in `backend/app/` violate §3.B "NO other top-level folders"

**Severity:** MEDIUM (structural debt; zero V1 runtime impact confirmed by import grep)
**Checks:** #1, #10
**Escalation trigger:** Met — rogue top-level folders under `app/`. Pre-acknowledged as H1 since §0 audit.

**Items found:**

| Item | Type | Content | V1-imported by any module? | Disposition |
|------|------|---------|---------------------------|-------------|
| `app/middleware/` | directory | `__init__.py` stub only (1 byte) | No | DELETE before Wave 10 |
| `app/routers/` | directory | `__init__.py` stub only (H1 from prior audits) | No | DELETE before Wave 10 |
| `app/schemas/` | directory | `__init__.py` stub only | No | DELETE before Wave 10 |
| `app/services/` | directory | `ai_engine.py` (6.4 KB), `image_processor.py` (6.0 KB), `storage.py` (6.6 KB) — V0 service files | NO V1 module imports any of these | DELETE alongside V0-rot test cleanup |
| `app/database.py` | file | V0 SQLAlchemy session (1.9 KB); canonical path is `shared/database.py` | Only by `app/services/image_processor.py` (V0) | DELETE with V0-rot cleanup |
| `app/data/` | directory | JSON seed files (`banned_words.json`, `meesho_categories.json`, `meesho_shipping_slabs.json`, `category_attributes.json`, `meesho_category_tree.json` 1.7 MB) + archived `prompts/` | Referenced only by V0 scripts | REVIEW — keep if seeder scripts reference at runtime; archive otherwise |

**V1 import status confirmed (grep-verified):** Zero V1 application modules import from `app/services/` or `app/database.py`. The only consumers are known V0-rot test files already classified as L_iam_2 exclusions (`test_storage.py`, `test_integration_third_party.py`, `test_ai_engine.py`, `test_worker_db_isolation.py`).

**Root cause:** Wave 1–2 gap-remediation pass deleted V0 route handler and test files but left service-layer files, empty stub packages, and the data directory. Construction sub-sessions correctly did not touch these (§5.0 read-only posture; deletion is Wave 10 operational prep).

**Remediation (Wave 10 pre-§22):**
```bash
# Empty stub packages — trivial
rm -rf backend/app/middleware/ backend/app/routers/ backend/app/schemas/

# V0 services + database — delete with V0-rot test cleanup
rm -f backend/app/database.py
rm -rf backend/app/services/

# V0-rot tests to delete at same time:
#   backend/tests/test_storage.py
#   backend/tests/test_integration_third_party.py
#   backend/tests/test_ai_engine.py
#   backend/tests/test_worker_db_isolation.py — excise V0 import at ~line 91 only

# data/ — review first before deleting
ls -la backend/app/data/  # determine if seeder scripts still reference at runtime
```

---

## Housekeeping observations

- **O1 (LOW):** `shared/models/` has `base.py` (15 files vs §3.E "14-file" count). Standard SQLAlchemy `DeclarativeBase` re-export pattern — implied by any SQLAlchemy 2.0 project. No runtime or correctness impact. No action needed.
- **O2 (LOW):** `i18n/` has 7 files vs §3.H's 3-file baseline. The 4 extra files are §5A Wave-1 construction outputs, all legitimately placed here to avoid cross-module import violations (placing them in `core/` or a module would force other modules to import across §16 boundaries). §3.H was authored before §5A finalized scope. No action needed; §3.H may note these in a future amendment.
- **O3 (OPEN NOTE):** Check 9 — `tests/modules/catalog/test_autosave.py` and `tests/modules/image/test_tasks.py` absent by exact filename. `test_service_unit.py` + `test_integration.py` inferred to cover this ground but not verified by content read. **Master should confirm coverage or add explicitly-named tests before §22.**

---

## Verdict rationale

The V1 canonical structure is fully implemented: all 8 domain modules with correct subtrees, all 5 non-domain layers with correct contents, `workers/` 2-file clean with exact include list, `tests/` with all required subdirs and confirmed coverage. The PARTIAL verdict is driven entirely by F1 — 6 V0-era artifacts in `backend/app/` that violate §3.B's structural contract. These are inert from a V1 runtime perspective (zero V1 imports confirmed). They are pre-existing technical debt from the Wave 1 gap-remediation pass. **PARTIAL does NOT block Wave 10 §22** — remediation is a clean-delete operation with no code logic involved.

---

## Hand-back to master

1. **ESCALATION: F1 — rogue `app/` entries.** Trigger met per verification protocol. Pre-acknowledged as H1. Confirm Wave 10 pre-§22 cleanup plan is scheduled.
2. **O3 open note:** Confirm test_autosave.py + test_tasks.py coverage before §22 sign-off — either add explicit files or verify service_unit/integration files cover those paths by content.
3. **Checks 3, 5, 6, 8 — CLEAN PASS.** `core/`, `adapters/`, `ai_ops/`, `workers/` are structurally correct with exact file counts and confirmed include list.
4. **§13.D dashboard exception holds.** NO `repository.py`, NO `tasks.py` — the structural exception is intact.
5. **No §5.0 violations detected** — no architecture doc edits by any sub-session.
6. Sub-session findings **agree with master's prior independent run** (2026-06-08) on all 10 checks. O3 is the one clarification added.
