## Session mesell-housekeeping-v1-backend-session-1 — 2026-06-10

First workload under the Model C repo convention. Worked in a git worktree at
`/tmp/mesell-wt/housekeeping-backend` (branch `feature/housekeeping-v1-backend`); master tree
untouched except memory (hardlinked, NOT a symlink — same inode 145223394 as canonical, so writes land).

### Task
Verify-then-delete dead backend files from the 2026-06-10 knowledge-sync audit. 5 candidates.

### Deleted (2)
- `backend/__init__.py` — 0-byte stray package marker. grep proof: no `import backend.` /
  `from backend.` anywhere in backend/ frontend/ scripts/ k8s/ .github/ Makefile
  docker-compose.dev.yml (only unrelated "backend-secrets" comment in k8s/postgres.yaml).
- `backend/app/data/prompts/catalog_generation.txt` — superseded by app/ai_ops/prompts.
  grep proof: zero refs to `catalog_generation` / `data/prompts` outside docs/. The prompts/
  dir held no other file (no __init__.py) -> dir auto-removed by FS; git doesn't track empty dirs.

### KEPT (3) — references found, "keep on any doubt"
- `category_attributes.json` + `meesho_categories.json` — BOTH loaded by `app/data/__init__.py`
  (`load_attributes()` / `load_categories()` / `get_category_config()` / `is_valid_category()`)
  AND asserted by the LIVE collected test `tests/test_data_helpers.py` (7 tests, content-dependent
  e.g. `is_valid_category("Kurtis") is True`). Deleting them would break that test. Do NOT delete
  without first retiring `app/data/__init__.py` loaders + that test.
- `meesho_category_tree.json` (1.7 MB) — 7 references: scripts/seed_categories.py, seed_all.py,
  parse_meesho_xlsx.py, meesho_batch_scraper.py, backend/scripts/archived/...webkit.py,
  backend/tests/eval/smart_picker/run_eval.py. CURRENT pipeline artifact — confirmed.

### grep method
From worktree root: grep -rn "<substr>" backend/ frontend/ scripts/ k8s/ .github/ Makefile
docker-compose.dev.yml 2>/dev/null | grep -v "<candidate itself>" | grep -v "^docs/". Searched
bare filename AND import/path forms (data/prompts, from backend., function names like
load_categories). ANY hit outside candidate+docs => KEEP.

### Test collection (proof for deletion-only change)
- BEFORE: 815 collected, 0 errors. AFTER: 815 collected, 0 errors. Unchanged.

### Env gotcha (Model C worktree)
- Worktrees do NOT carry the gitignored backend/.venv. System python3.9 fails collection with
  MappedAnnotationError: Mapped[str | None] (3.9 can't resolve PEP 604 in SQLAlchemy mapped
  annotations). Solution: run the MASTER tree's interpreter
  /Users/mugunthansrinivasan/Project/mesell/backend/.venv/bin/python (3.11, has deps) against the
  worktree code with PYTHONPATH=/tmp/mesell-wt/housekeeping-backend/backend. Interpreter-only
  use of master venv does NOT modify the master checkout.
- Config validation SystemExits at import unless ~13 secret env vars are set. Pass them as dummy
  values via `env VAR=dummy ...` (the §20.5 CI dummy-env pattern). Note: `export VAR=val python -m`
  trips zsh ("not valid in this context: -m") — use `env` prefix, not inline export, on this shell.

### Git / PR
- Commit 1 (deletions): 6b41038 — staged via git -C <wt> add -A backend/ (scopes to backend/,
  avoids the .claude/ symlink churn the worktree shows as deleted/untracked).
- Commit 2 (board): c535bb9 — feature_board_backend.md row -> IN REVIEW.
- Pushed feature/housekeeping-v1-backend. PR #28 -> base feature/housekeeping-v1,
  head feature/housekeeping-v1-backend. Full backend.md template filled, "N/A — deletion-only"
  where genuinely inapplicable.

### Friction with the convention itself
- The backend PR template assumes branch shape feature/{name}/backend, but this session's
  prescribed branch is the flat feature/housekeeping-v1-backend (no nested slash). Filled the
  template with the actual branch; flagged inline. Lead may want to reconcile template wording vs
  the flat group-branch naming used here.
- The worktree's .claude/ appears as a big block of deleted+untracked files in git status
  (memory dirs replaced by hardlinks/symlinks at setup). Harmless because staging is scoped to
  backend/ and docs/, but it's noise — worth a .git/info/exclude or sparse setup next time.

---

---
