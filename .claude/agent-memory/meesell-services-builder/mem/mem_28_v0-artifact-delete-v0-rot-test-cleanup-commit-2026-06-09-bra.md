## V0 ARTIFACT DELETE + V0-ROT TEST CLEANUP + COMMIT (2026-06-09, branch claude/meesell-project-setup-Tl7DS)

### Scope
Solo micro-dispatch. Pre-§22 §3 audit item "V0-rot tests" + V0 source purge. infra-builder had halted at Step 2 because 4 V0-era test files imported soon-to-be-deleted paths. Closes the L_iam_2 V0-rot item flagged in my §19 memory. Commit `43abd23`. DO NOT touch BACKEND_ARCHITECTURE.md (§5.0).

### What I did
1. Surgical excise — `backend/tests/test_worker_db_isolation.py` (the ONE file kept):
   - Repointed two `patch("app.database.create_async_engine"|"async_sessionmaker")` targets -> `app.shared.database.*` (the V1 module). Preserved the still-valid `test_make_worker_session_disposes_engine_after_each_call` V1 test rather than deleting it.
   - REMOVED entire `test_run_pipeline_uses_make_worker_session_not_global_session_maker` (it did `import app.services.image_processor` + `inspect.getsource(ip_mod.run_pipeline)` — pure V0). Replaced with a RETIRED comment block (merged with the existing #4 RETIRED block).
   - Result: file has NO live import / patch-target of `app.services`/`app.database` (only prose mentions inside the RETIRED comment). 4 V1 isolation tests preserved.
   - KEPT: `async_session_maker` string literals in assertion messages (lines ~38-41, ~114-115) — they assert about V1 SOURCE CONTENT (get_db must contain it; make_worker_session must NOT), NOT module imports. Do not strip these.
2. Deleted 3 pure-V0 test files: `test_storage.py` (imports app.services.storage -> V1 is app.adapters.gcs), `test_ai_engine.py` (app.services.ai_engine -> V1 app.adapters.gemini), `test_integration_third_party.py` (both). V1 equivalents covered by tests/test_gcs_adapter.py + test_gemini_adapter.py.
3. Deleted 5 V0 source artifacts: `app/middleware/`, `app/routers/`, `app/schemas/`, `app/services/`, `app/database.py`. `app/data/` PRESERVED (separate decision pending — do NOT delete).
4. Verified clean collection: `cd backend && .venv/bin/python -m pytest --collect-only -q` -> exit 0, 815 tests, 0 errors.
5. Staged + committed backend/app + requirements.txt + pytest.ini + Dockerfile(.worker) + alembic/ + tests/ + scripts/ + .gitlab-ci.yml + docs/. Commit 43abd23, 274 files, +35429/-4275.

### CRITICAL CATCH — §5.0 guard
`git add docs/` swept in a pre-existing 208-line working-tree modification to `docs/BACKEND_ARCHITECTURE.md` (NOT authored by me — already M in the tree). Per §5.0 NON-NEGOTIABLE I ran `git reset HEAD docs/BACKEND_ARCHITECTURE.md` BEFORE committing. Verified post-commit: `git show --name-only 43abd23 | grep BACKEND_ARCHITECTURE` -> NOT in commit. The 208-line mod remains UNCOMMITTED in the working tree for its owner to disposition.
LESSON: whenever a task says "git add docs/" AND "do not touch <doc>", reset that doc OUT of the index before committing — `git add <dir>/` stages ALL pre-existing modifications in that dir, not only yours.

### Secrets scan (locked routine for commit tasks)
Before every commit: filenames `git diff --cached --name-only | grep -iE "\.env|secret|\.pem$|\.key$"` + added content `git diff --cached | grep "^\+" | grep -iE "AKIA[0-9A-Z]{16}|BEGIN .*PRIVATE KEY|AIza[0-9A-Za-z_-]{30,}|sk_live_|rzp_live_|xoxb-"`. This task: all clean.

### Left unstaged (intentional / out of scope)
- `backend/tests/eval/smart_picker/fixtures.json` (M) — pre-existing mod, AI-coordinator territory, not mine.
- `backend/tests/eval/smart_picker/eval_results.json` (??) — untracked runtime eval artifact, gitignore candidate.
- frontend/, k8s/, .claude/agent-memory/, themes/, archive/ — deliberately excluded per the staging instruction.

### Env facts re-confirmed
- venv = `backend/.venv/bin/python` (Python 3.11.14, NOT 3.12 as CLAUDE.md claims).
- pytest MUST run from `backend/` (pytest.ini + import_rules.toml + AST scanners resolve relative to backend/).
- V1 DB module is `app.shared.database` (engine, AsyncSessionLocal, make_worker_session, get_db). Old `app.database` is GONE.

---
