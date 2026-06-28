## Session mesell-test-markers-19d-backend-session-1 — 2026-06-11 — §19.D marker classification PR #85 merge-gate (Rule-7 step 3)
> NOTE (landed late via PR #88 closeout, AFTER the Gate-4 saga entries below): this work chronologically
> PRECEDES the ci-gate4 sessions. The CI-INT-DB-PROVISION request it opened was SUPERSEDED by the Gate-4
> saga (#104→#110, conftest `_provision_test_schema`) — `pytest -m integration` reaches exit 0. Kept for the trail.

**Context:** I authored the marker-classification spec (step 1); api-routes-builder executed (step 2, commit 859626f, PR #85); this session ran the REAL merge gate (step 3). Third and final step of the CI-gate saga (PR #74 pythonpath → PR #76 env vars → PR #85 markers).

**Verdict: APPROVE-WITH-GATE-FIXES.** Merged to develop, squash `34d8b47` (admin — branch protection requires the advisory Gate-4). develop `90e3f0e → 34d8b47`.

**Gate review (spec §8):**
- Marks-only fence VERIFIED CLEAN: 100 files all under backend/tests/; zero non-marker added lines; all 23 deletions are pytestmark single→list conversions; zero test-body edits; perf/ + pre-existing integration marks untouched; conftest/pytest.ini/ci.yml/docs untouched.
- Proofs reconciled: unit 597 / smoke 26 / integration 191 / golden 18 / complement 0 = 823.
- Judgment calls UPHELD: golden_fixtures_runner→golden_roundtrip (db = local function param, not a fixture — the §14.K trap I flagged in the spec); iam_dual_pepper→unit (fakeredis); export integration tests (monkeypatch-only)→unit per §19.D real-vs-mock (behaviour not folder).

**The 10 CI failures (run 27322069138) → 3 groups, 3 rulings:**
- GROUP 1 (in fence, fixed b2af630): test_shared_database.py — `test_get_db_yields_async_session` + `test_make_worker_session_yields_working_session` execute `SELECT 1` on real Postgres but carried blanket `pytestmark = pytest.mark.unit` → selected into Gate 1 → OSError 5432. Fix: dropped blanket mark, per-test marked the 6 static/mock tests `unit` and the 2 real-DB tests `integration` only.
- GROUP 2 (lead-owned wiring, fixed b2af630): `ModuleNotFoundError: No module named 'openpyxl'`. ROOT CAUSE = genuine PRODUCTION dep gap: app/modules/export/service.py lines 736/767 import openpyxl at runtime (§14) but it was ABSENT from backend/requirements.txt. Export would fail in any deployed namespace. Fix: added `openpyxl==3.1.5`.
- GROUP 3 (out of fence → lead-authorized exception, fixed b5c9a29 + 8433a5e): test_config.py ×5 STALE-API (`app.config`→`app.shared.config`; `CORS_ORIGINS`/`cors_origin_list`→`CORS_ALLOWED_ORIGINS`) + test_worker_db_isolation `async_session_maker`→`AsyncSessionLocal`. Marker correct; tiny symbol renames authorized as lead-scoped gate exceptions (isolated commits, diffs reviewed in PR comments).

**CI convergence (run 27322416827, HEAD 8433a5e): Gate 1 unit (594 passed) / Gate 2 smoke / Gate 3 lint ALL GREEN.** Gate 4 integration FAIL but selection-clean (192 selected, zero collection errors) → was infra ticket CI-INT-DB-PROVISION at the time (since SUPERSEDED — see note above). Gate 5 skipped. Advisory per §2.1, NOT a merge blocker.

**Commit trail:** 859626f (specialist marks-only) · b2af630 (Group-1+2) · b5c9a29 (Group-3 config) · 8433a5e (worker stale-symbol).

**Specialist discipline note:** api-routes-builder's MEMORY.md write for this session was guard-blocked (decentralized rule 4). Its learnings live in PR #85 body + my gate comments. I did NOT write its memory for it.
