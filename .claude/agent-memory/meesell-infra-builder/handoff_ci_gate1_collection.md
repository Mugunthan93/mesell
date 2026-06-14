# Handoff — CI Gate 1 collection failure (infra → backend-coordinator)

**Opened:** 2026-06-11 by `meesell-infra-builder` (session `mesell-ci-activation-session-1`)
**Target lead:** `meesell-backend-coordinator`
**Feature:** ci-activation (first main pipeline activation)
**Inter-lead request row:** added to `docs/status/feature_board_infra.md` → Inter-lead requests open (OPEN, 2026-06-11)

## Context
PR #64 (develop → main, merge commit `0ea1988b18c486c214e10197f9a29707304fc845`) merged on founder authorization. Fired first real main CI pipeline (run `27318816408`). RED at Gate 1 (unit), cascaded (gates 2-5 + build + deploy skipped via sequential `needs:`). 3 frontend jobs passed; nightly correctly skipped.

## The failure (pytest COLLECTION error, exit code 4 — not test logic)
```
ImportError while loading conftest '.../backend/tests/conftest.py'.
tests/conftest.py:37: from app.shared.database import Base, get_db
E   ModuleNotFoundError: No module named 'app'
```
Whole suite fails to collect — `app` is not importable.

## Root cause (verified against origin/main)
- CI gate `unit` runs `pytest -m "unit" -v` with `working-directory: backend`.
- `backend/app/` IS a proper package (app/__init__.py, app/shared/__init__.py, app/shared/database.py present).
- BUT nothing puts `backend/` on sys.path:
  - `backend/pytest.ini` (LOCKED §19.D) sets `testpaths = tests`, NO `pythonpath`.
  - No pyproject.toml/setup.py/setup.cfg → `app` not installed; CI install step is only `pip install -r requirements.txt` (no `pip install -e .`).
  - `conftest.py` does `from app.shared.database import ...` but does NOT prepend rootdir to sys.path.
- pytest importmode=prepend + rootdir=backend inserts only the test file's dir (tests/), not rootdir → `import app` fails. Reproducible config gap, not a runner artifact.
- Affects every gate (2-5 reuse the same conftest).

## Why infra did NOT fix it
- `app` import path / pytest packaging is BACKEND-owned. `pytest.ini` is §19.D LOCKED. `backend/` is out of infra scope.
- An infra-only patch (`PYTHONPATH: backend` env on each gate step in infra-owned ci.yml) is possible but papers over a backend packaging gap. Infra will apply it only if backend-coordinator agrees that's the fix.

## Recommended fix (backend-coordinator's call) — pick ONE
1. Add `pythonpath = .` to `backend/pytest.ini` — cleanest; needs founder OK (§19.D LOCKED). Makes `cd backend && pytest` self-contained.
2. Add minimal `backend/pyproject.toml` (or setup.py) declaring the `app` package + a `pip install -e .` CI step.
3. (infra fallback, only if backend asks) `PYTHONPATH: backend` env on each gate step in ci.yml.

## After the backend fix lands
1. Backend merges fix → develop, then develop→main PR (founder gate) → push refires pipeline.
2. Infra re-watches. If green: WIF build + IAP deploy run for the FIRST time (still UNPROVEN — never executed this run).
3. First green run materializes check-context names. Infra then asks founder to add exactly the 5 gates + 3 frontend jobs to main branch protection (NOT build/deploy — push-only, would deadlock PRs; NOT nightly — schedule-only).

## State at handoff
- No mutation to backend/, pytest.ini, or ci.yml.
- PR #64 merged; develop preserved; merge SHA above.
- GEMINI_API_KEY_CI still founder-pending (nightly-only, unrelated to this failure).
