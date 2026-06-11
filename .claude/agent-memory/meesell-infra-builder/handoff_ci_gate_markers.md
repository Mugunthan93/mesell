# Handoff — CI gates deselect-to-zero (exit 5) — no §19.D markers applied (infra → backend-coordinator)

**Opened:** 2026-06-11 by `meesell-infra-builder` (session `mesell-ci-activation-session-1`)
**Target lead:** `meesell-backend-coordinator`
**Feature:** ci-activation (first main pipeline activation — follow-up 3)
**Inter-lead request row:** added to `docs/status/feature_board_infra.md` → Inter-lead requests open (OPEN, 2026-06-11)
**Supersedes:** `handoff_ci_gate1_collection.md` — that one (ModuleNotFoundError at collection) is RESOLVED by `pythonpath = .` in pytest.ini (PR #73/#74/#75). This is the NEXT failure surfaced once collection started working.

## Context
Re-fired the pipeline after the Gate-1 collection fix + §5.D env-guard fix landed on develop. PR #78 (develop->main, **merge commit `218aa83d9af2396f02a9a53da291d5a9092e4415`**) merged on founder authorization. Push run `27320321536` = RED, again at Gate 1 (unit), again cascading (gates 2-5 + build + deploy SKIPPED via sequential `needs:`). 3 frontend jobs GREEN; nightly correctly skipped.

## The failure (pytest "no tests selected", exit code 5 — NOT collection, NOT test logic)
Gate 1 now gets PAST collection (the pythonpath fix worked — 823 items collected cleanly):
```
collecting ... collected 823 items / 823 deselected / 0 selected
=========================== 823 deselected in 2.03s ============================
##[error]Process completed with exit code 5.
```
`pytest -m "unit"` collected all 823 tests, then **deselected all 823** because none carry the `unit` marker -> 0 selected -> pytest exit code 5 (NO_TESTS_COLLECTED) -> shell sees non-zero -> job RED.

## Root cause (verified against develop, three ways)
The 7 §19.D markers ARE registered in `backend/pytest.ini` (markers block: unit, integration, golden_roundtrip, ai_eval, slow, smoke, perf) so --strict-markers is satisfied — but they are **applied to ZERO test functions**:
- GitHub code search `pytest.mark.<marker>` for all 7 markers -> 0 files each.
- No `pytest_collection_modifyitems` hook anywhere in the repo (-> 0) — nothing auto-tags tests by path/default.
- Direct grep of `backend/tests/test_core_auth.py` -> only `@pytest.mark.asyncio` (pytest-asyncio's own). `test_config.py` -> no pytest.mark at all.

So the suite has 823 tests, none tagged with a gate marker.

## Blast radius — SYSTEMIC, not a one-off
Every marker-gated CI gate hits the SAME exit-5:
- Gate 1 `pytest -m "unit"` -> 0 selected (CONFIRMED red this run)
- Gate 2 `pytest -m "smoke"` -> 0 selected (will be red)
- Gate 4 `pytest -m "integration"` -> 0 selected (will be red)
- Gate 5 `pytest -m "golden_roundtrip"` -> 0 selected (will be red)
- Nightly `-m "slow or perf"` and `-m "ai_eval"` -> 0 selected (will be red)
- Gate 3 (lint — 10 contracts) is NOT pytest-marker-gated -> unaffected.

Fixing only `unit` just moves the red to Gate 2. The fix must tag the whole suite across all gate buckets in one pass.

## Why infra did NOT fix it
- Test tagging / marker strategy is BACKEND-owned (which test is unit vs smoke vs integration is a backend decision). `pytest.ini` is §19.D LOCKED.
- The infra-owned ci.yml invocation `pytest -m "unit"` is CORRECT per the §19.D 6-gate contract — gate-per-marker is the agreed contract; the gap is untagged tests, not the invocation.
- No mutation to `backend/`, `pytest.ini`, or `ci.yml` this session.

## Recommended fix (backend-coordinator's call) — ONE strategy, suite-wide
1. **Explicit tagging** — `@pytest.mark.<bucket>` or module-level `pytestmark` on every test file -> §19.D bucket. Most explicit; most churn.
2. **Auto-marking conftest hook** — `pytest_collection_modifyitems` in `backend/tests/conftest.py` assigning a marker by path/filename convention (e.g. `test_*_integration.py` -> integration; everything else -> unit; the 15 XLSX round-trip fixtures -> golden_roundtrip). Lowest churn; single source of truth.
3. **Hybrid** — default everything to unit via the hook, then explicitly tag the integration/smoke/golden/ai_eval/slow/perf exceptions.

Must be COMPLETE across all gate buckets. Confirm locally before the develop->main PR: `cd backend && pytest -m unit -v` (and smoke, integration, golden_roundtrip) each report `> 0 selected`.

## After the backend fix lands
1. Backend merges fix -> develop, then develop->main PR (founder gate) -> push refires.
2. Infra re-watches. If green through Gate 5: **WIF auth + Cloud Build + IAP deploy run for the FIRST time ever** (still UNPROVEN — sequential-blocked on BOTH runs: 27318816408 at collection, 27320321536 at marker-selection).
3. First green-through-deploy -> infra verifies `https://api.mesell.xyz/health` 200 + reports deployed image tag.
4. First green materializes check-context names -> infra asks founder to add exactly the 5 gates + 3 frontend jobs to main branch protection (NOT build/deploy — push-only, deadlocks PRs; NOT nightly — schedule-only).

## State at handoff
- PR #78 merged; develop preserved (`2662e5b`); merge SHA `218aa83`.
- No mutation to backend/, pytest.ini, or ci.yml.
- GEMINI_API_KEY_CI still founder-pending (nightly-only, unrelated).
