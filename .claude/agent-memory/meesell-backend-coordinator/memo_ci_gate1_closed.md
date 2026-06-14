# MEMO — CI Gate-1 pytest-collection fix CLOSED (PR #74 merged) + infra follow-up

**From:** `meesell-backend-coordinator`
**To:** `meesell-infra-builder` (decentralized-sharing: you read this from my memory per CLAUDE.md rule 3)
**Date:** 2026-06-11
**Session:** `mesell-ci-gate1-fix-session-1`
**Re:** Closure of `handoff_ci_gate1_collection.md` (infra-owned) + ONE remaining infra action

---

## 1. What landed (your inter-lead handoff is RESOLVED on the backend side)

- **PR #74** (`fix/ci-gate1-pytest-collection` → develop) MERGED, squash SHA `bb09aea343dfc182ac494ed3c4bdf563a72b6f36`. develop tip = `bb09aea` (before the two docs commits 33aa765 + e0a12c4).
- The fix: a single additive `pythonpath = .` (+ 6-line §19.D lock-citation comment) in `backend/pytest.ini`. NO other file. Backend-owned (Option a of the spec — deliberately did NOT touch `.github/workflows/ci.yml`, which is YOUR lane).
- Root cause confirmed: CI invokes `pytest` as a **script** (not `python -m pytest`); the script form does NOT add CWD to sys.path. Under importmode=prepend with no `tests/__init__.py` / `tests/modules/__init__.py`, prepend inserts the test-package root (`tests/` or `tests/modules/`), never rootdir — so `from app.shared.database import ...` in conftest raised `ModuleNotFoundError: No module named 'app'` (exit 4). `pythonpath = .` prepends rootdir (= `backend/`). The project venv masked this locally because `python -m pytest` DOES add CWD.
- Verified in a throwaway venv (Py 3.14.3) replicating the CI script-invocation exactly: BEFORE = 'app' import error; AFTER = error GONE.

## 2. ONE remaining infra action (NEW inter-lead request — OPEN on my board)

PR #74 moved the Gate-1 failure mode from **"import error, exit 4"** to **"app §5.D startup-guard abort, exit 1"**. After the path fix, collection reaches the app's own config guard (`app.shared.config`), which fails-fast on empty/unset required env vars.

I audited the Gate-1 (`unit`) env block in ci.yml (job-level env lines ~78-88, plus top-level env lines ~56-64). The app's FATAL list names **13** required vars. The Gate-1 block provides **8**. **5 are MISSING:**

| Missing var | Suggested CI dummy |
|---|---|
| `GCS_BUCKET` | `ci-dummy-gcs-bucket` |
| `GCS_PROJECT_ID` | `ci-dummy-gcs-project` |
| `LANGFUSE_PUBLIC_KEY` | `ci-dummy-langfuse-public` |
| `LANGFUSE_SECRET_KEY` | `ci-dummy-langfuse-secret` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:4200` (NEVER `*` per §5.D CORS lock; a real-shaped origin keeps the `list[str]` validator happy) |

**Until these 5 are added, the full main pipeline will still abort at Gate-1's startup guard (sys.exit(1)).** The same dummy set is shared by Gates 2 (smoke), 3 (lint), 4 (integration), 5 (golden_roundtrip), and the nightly job — they currently have the SAME 8-of-13 gap. Please add all 5 to **every** job env block that runs app code (each job declares its own `env:` — the top-level env only carries infra vars like PROJECT_ID/REGION). Gate-3 lint has a thinner env (only SECRET_KEY/JWT_SECRET/APP_ENV at line ~162) — confirm whether import-linter/AST contracts import app config; if they do, it needs the full 13 too.

This is YOUR lane (ci.yml is infra-owned — the whole reason I chose the pytest.ini option over a ci.yml edit). I did not touch it.

## 3. Pipeline re-fire note (for the Director, not infra)

A `develop → main` PR is what re-fires the pipeline (CI triggers only on push/PR to main). I did NOT open it (founder's gate per D1). Recommendation: open it AFTER infra closes the 5-var gap, otherwise the first main run will red at the config guard rather than proving the collection fix green.
