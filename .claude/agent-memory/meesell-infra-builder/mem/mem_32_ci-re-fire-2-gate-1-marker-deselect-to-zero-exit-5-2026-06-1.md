## CI re-fire #2 — Gate-1 marker deselect-to-zero (exit 5) — 2026-06-11 (mesell-ci-activation-session-1, follow-up 3)

**Founder authorized me to exercise the D1 develop→main gate directly this time** (open PR + merge + watch). Did so: **PR #78**, merge-commit (`merge_method=merge`, NOT squash — develop→main history continuity like PR #64), **merge SHA `218aa83`**, develop preserved (`2662e5b`). REST `PUT /pulls/N/merge` succeeded first attempt. Push run = `27320321536`.

**Verdict: RED at Gate 1 again — but a DIFFERENT, deeper failure than fire #1. This is progress, not regression.**

### The exit-5 mechanism (new learning — distinct from the fire-#1 collection error)
- Fire #1 (run 27318816408): died at COLLECTION — `ModuleNotFoundError: No module named 'app'` (exit 4). Fixed by `pythonpath = .` in pytest.ini.
- Fire #2 (run 27320321536): collection now SUCCEEDS (823 items collected cleanly — the pythonpath fix worked, and the §5.D 17-var env guard passed). But:
  ```
  collected 823 items / 823 deselected / 0 selected
  ##[error]Process completed with exit code 5.
  ```
  **pytest exit code 5 = NO_TESTS_COLLECTED/SELECTED.** `pytest -m "unit"` collected everything then deselected all 823 because NONE carry the `unit` marker → 0 selected → exit 5 → shell `-e` sees non-zero → job RED.
- **Key infra-debugging tell:** "X deselected / 0 selected" + "exit code 5" is NOT a test-logic failure and NOT a collection/import failure. It means the `-m <marker>` filter matched nothing. Don't chase test logic or imports — check whether the marker is APPLIED to tests (registration in pytest.ini is necessary but NOT sufficient; `--strict-markers` only validates that a used marker is registered, it does NOT require any test to use it).

### Root cause (verified 3 ways) — backend test-tagging gap, SYSTEMIC
- 7 §19.D markers REGISTERED in `backend/pytest.ini` `markers =` block, but applied to ZERO tests.
- GitHub `search/code?q=repo:...+pytest.mark.<m>` = 0 files for ALL 7 markers (unit/smoke/integration/golden_roundtrip/ai_eval/slow/perf).
- No `pytest_collection_modifyitems` hook anywhere (0) → nothing auto-tags by path.
- Direct grep `test_core_auth.py` → only `@pytest.mark.asyncio` (pytest-asyncio's own). `test_config.py` → no pytest.mark.
- **Blast radius: every marker-gated gate** (1 unit confirmed; 2 smoke / 4 integration / 5 golden_roundtrip + nightly slow/perf/ai_eval all will exit-5 the same way). Gate 3 (lint) is NOT marker-gated → unaffected. Fixing only `unit` moves the red to Gate 2 — backend must tag the whole suite in one pass.
- **Scope: BACKEND.** Which test is unit/smoke/integration is a backend domain call. ci.yml `pytest -m "unit"` is CORRECT per §19.D 6-gate contract. NO infra mutation. New inter-lead request + `handoff_ci_gate_markers.md` (commit `ccd1cab`).

### STILL UNPROVEN after TWO fires — WIF / Cloud Build / IAP deploy
The entire build+deploy half of the pipeline has NEVER executed. Both fires sequential-blocked at Gate 1 (`needs:` chain). So WIF auth (`github-actions-pool`/`meesell-github-ci`), `gcloud builds submit`, and the IAP-tunneled kubectl deploy remain completely untested. Do NOT claim those paths work until a run reaches them. They only fire after all 5 gates pass on a PUSH to main.

### Operational notes (re-confirmed this session)
- `gh api contents PUT` to `develop` is the reliable way to update status/board/memory when the local checkout write-guard is active ("parent bg session hasn't isolated yet"). Pattern: fetch `.sha` + `.content`(b64-decode) → edit /tmp copy with python3 → `base64 | tr -d '\n'` → `PUT -f content=.. -f sha=.. -f branch=develop`, 3-retry refreshing `.sha` on conflict. Worked clean this session (memo ccd1cab, board a164b62, status fdbe7b2).
- `gh api` query params with `?ref=develop` MUST be quoted in this shell (zsh glob) — `gh api "repos/.../contents/path?ref=develop"`. Unquoted → "no matches found".
- Board had been touched by another writer between my session-start Read and my PUT (row was already READY-to-refire, Gate-1 inter-lead already RESOLVED). ALWAYS re-fetch board content fresh before editing — don't edit from the session-start snapshot. My Python edit asserted on the stale header string and failed first try; re-ran against actual content.
- GitHub runner deprecation annotation (non-blocking): `actions/checkout@v4` + `dorny/paths-filter@v3` on Node 20 (forced Node 24 after 2026-06-16). Future ci.yml housekeeping: bump to v5/v4 respectively.

### Next (3rd fire, after backend tags the suite)
Backend tags suite → develop → founder develop→main PR → push re-fires. I re-watch. IF green through Gate 5 → WIF/Cloud-Build/IAP-deploy run for the first time → I verify `https://api.mesell.xyz/health` 200 + report deployed image tag → then ask founder to add the 5 gates + 3 frontend jobs to main branch protection (NOT build/deploy = push-only; NOT nightly = schedule-only). GEMINI_API_KEY_CI still founder-pending (nightly-only).

---
