# Sub-Session Prompt: §3 File Structure — VERIFICATION
# Wave 8 of 10 — VERIFICATION (parallel-safe with §0, §1, §2, §17)
# Master self-audit (no specialist dispatch)
# Renames session to: meesell-backend-verification-3-files-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Audit context loaded. Ready to begin §3 verification" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are operating in a dedicated VERIFICATION sub-session for MeeSell §3 (File Structure).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION. Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under verification: §3 File Structure — directory tree, per-module canonical 7-file subtree, non-domain layer subtrees, tests/ mirror
- Sub-session naming: `/rename meesell-backend-verification-3-files-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §3 (the section being audited; esp. §3.B top-level tree, §3.C per-module canonical subtree, §3.D core/, §3.E shared/, §3.F adapters/, §3.G ai_ops/, §3.H i18n/, §3.I workers/, §3.J tests/ mirror).
2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §16 inter-module rules (esp. §16.F structural exceptions).
3. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md`.
4. `/Users/mugunthansrinivasan/Project/mesell/backend/`.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

Audit checklist for §3:

1. **`backend/app/` tree matches §3.B** — `ls backend/app/` shows: `__init__.py`, `main.py`, `modules/`, `adapters/`, `core/`, `ai_ops/`, `i18n/`, `shared/`, `workers/`. NO other top-level folders.

2. **Each domain module has the 7-file canonical subtree per §3.C**:
   - iam: 7 files (router.py, service.py, repository.py, schemas.py, domain.py, exceptions.py, __init__.py); NO tasks.py (locked exception).
   - customer: 7 files; NO tasks.py.
   - category: 7 files; NO tasks.py.
   - catalog: 7 files; NO tasks.py (V1 lock; sync autofill).
   - image: 8 files (incl. tasks.py).
   - pricing: 7 files; NO tasks.py.
   - dashboard: 5 files (NO repository.py per §13.D exception + NO tasks.py).
   - export: 8 files (incl. tasks.py).

3. **`core/` 6 files + middleware subdir per §3.D**:
   - `core/` top: __init__.py, auth.py, tenancy.py, cache.py, plan_guard.py, errors.py (6 files).
   - `core/middleware/`: __init__.py, request_id.py, auth_mw.py, tenancy_mw.py, rate_limit_mw.py, plan_guard_mw.py, audit_mw.py (7 files).

4. **`shared/` 4 files + models/ per §3.E**:
   - `shared/`: __init__.py, database.py, valkey.py, config.py (4 files).
   - `shared/models/`: __init__.py + 13 ORM models = 14 files.

5. **`adapters/` 5 files per §3.F**:
   - __init__.py, gemini.py, msg91.py, gcs.py, razorpay.py, langfuse.py (6 files including __init__.py).

6. **`ai_ops/` 6 files per §3.G**:
   - __init__.py, client.py, cost_tracker.py, guardrail.py, budget_cap.py, prompt_registry.py, eval.py (7 files including __init__.py).
   - Plus `ai_ops/prompts/` subdir with __init__.py + smart_picker_v1.py + autofill_v1.py + watermark_v1.py.

7. **`i18n/` package per §3.H** — `__init__.py`, `messages_en.py`, `resolver.py`; NO `messages_ta.py` or `messages_hi.py` in V1.

8. **`workers/celery_app.py` per §3.I** — single Celery app file; `include=["app.modules.image.tasks", "app.modules.export.tasks"]`.

9. **`tests/` mirrors `app/` per §3.J** — `tests/modules/<module>/test_router.py + test_service.py + test_repository.py` for each domain module; special-purpose tests: `category/test_search.py`, `catalog/test_autosave.py`, `image/test_tasks.py`, `export/test_round_trip.py`.

10. **No silent additions** — `ls backend/app/` shows ONLY the locked top-level peers; no rogue folders.

Plus universal: no regressions; import-linter PASS; STATUS_BACKEND.md has CONSTRUCTED entries.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT write production code.
- DO NOT amend LOCKED sections.
- DO NOT modify codebase to fix non-compliance — REPORT.
- DO NOT touch STATUS_MASTER.md.
- DO NOT touch projects outside MeeSell.

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT
═══════════════════════════════════════════════════════════════

```
# §3 File Structure Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-3-files-1
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results
| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | backend/app/ top-level matches §3.B | PASS/FAIL | ls output |
| 2 | Per-module canonical 7-file subtree (with dashboard 5 + iam/customer/category/pricing/dashboard no tasks.py exceptions) | PASS/FAIL | per-module file list |
| 3 | core/ 6 files + middleware 7 files | PASS/FAIL | ls |
| 4 | shared/ 4 files + models/ 14 files | PASS/FAIL | ls |
| 5 | adapters/ 5 vendor files + __init__.py | PASS/FAIL | ls |
| 6 | ai_ops/ 6 files + prompts/ subdir | PASS/FAIL | ls |
| 7 | i18n/ package, V1 = en only | PASS/FAIL | ls |
| 8 | workers/celery_app.py include list | PASS/FAIL | grep |
| 9 | tests/ mirrors app/ | PASS/FAIL | ls tree |
| 10 | No silent top-level additions | PASS/FAIL | ls |

## Non-compliance findings
## Verdict rationale
## Hand-back to master
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Save audit at `docs/audits/§3_files_audit_<YYYY-MM-DD>.md`.
2. Append STATUS_BACKEND.md UPDATE block.
3. Report back to master under 300 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Rogue top-level folder under `app/` (escalate — architectural breach).
- Module missing canonical files (e.g. customer missing schemas.py).
- Dashboard HAS repository.py (structural exception broken).

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-verification-3-files-1`
2. Read REQUIRED READING.
3. Confirm all 16 construction sections CONSTRUCTED.
4. Report "Audit context loaded. Ready to begin §3 verification." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 8 of 10
- **Sequential dependency:** All 16 construction sections CONSTRUCTED.
- **Parallel-safe?:** Yes — parallel with §0, §1, §2, §17.
- **Expected duration estimate:** ~2-3 hours.
- **Acceptance verification by master:** read audit; spot-check per-module file counts; on PASS proceed.
