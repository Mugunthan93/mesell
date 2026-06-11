# SPEC + OUTCOME — CI Gate-1 pytest-collection fix

**Authored:** 2026-06-11 by `meesell-backend-coordinator`
**Rule 7 three-step:** STEP 1 (SPEC) → STEP 2 (specialist executes) → STEP 3 (coordinator merge-gate review). All 3 COMPLETE.
**Source failure:** CI run `27318816408` (first main pipeline, PR #64 merge SHA `0ea1988b18c486c214e10197f9a29707304fc845`), Gate 1 (unit) exit code 4 at pytest COLLECTION.
**Infra handoff (incoming):** `.claude/agent-memory/meesell-infra-builder/handoff_ci_gate1_collection.md` (infra-owned).
**Session token:** `mesell-ci-gate1-fix-session-1`

---

## 1. Root cause (coordinator-verified)

- CI runs `pytest -m "unit" -v` with `working-directory: backend` (bare invocation). `rootdir` = `backend/`.
- pytest `importmode=prepend` inserts, per collected file, the first ancestor dir WITHOUT `__init__.py`.
- The tree has NO `tests/__init__.py` and NO `tests/modules/__init__.py`, but HAS deeper `__init__.py`
  (e.g. `tests/modules/category/__init__.py`). So prepend stops at `tests/` or `tests/modules/` — never at
  `backend/`. `backend/` never lands on `sys.path` → `from app... import` raises `ModuleNotFoundError`.
- No `pyproject.toml`/`setup.py` → no editable install; CI install is only `pip install -r requirements.txt`.
- Works locally only because local runs `python -m pytest` (prepends CWD). On a clean path `import app` fails.

### 1.A — §19.D lock ruling (coordinator's call)

`pythonpath = .` is ADDITIVE and semantics-preserving — does NOT touch the locked marker set, asyncio_mode,
asyncio_default_fixture_loop_scope, testpaths, filterwarnings, or addopts. §19.D governs the TEST CONTRACT,
not a byte-for-byte ini mandate (proven: the as-built `[pytest]` ini already diverges from the illustrative
`[tool.pytest.ini_options]` toml block). NO founder §7.3 amendment required. One-line sentinel comment cites
the ruling. Fallback (if contested) = conftest sys.path shim, zero locked-file touch.

### 1.B — Option chosen

(a) `pythonpath = .` in pytest.ini — CHOSEN (smallest correct diff, backend-owned, idiomatic pytest≥7.0,
`pytest==8.3.0` pinned). Rejected: (b) pyproject.toml + `pip install -e .` (couples to infra ci.yml lane,
over-engineered) and (c) conftest shim (held in reserve only).

## 2. Exact change

`backend/pytest.ini`: insert `pythonpath = .` + sentinel comment into the `[pytest]` section. Nothing else
changes. Do NOT alter testpaths/markers/asyncio/addopts; do NOT convert ini→toml; do NOT create
`backend/__init__.py`, `tests/__init__.py`, `tests/modules/__init__.py`, `pyproject.toml`, `setup.py`; do
NOT edit conftest.py; do NOT touch ci.yml (infra-owned).

## 3. Verification gate (specialist before PR; coordinator re-verifies at step 3)

1. `cd backend && env -u PYTHONPATH python -m pytest -m "unit" --collect-only -q` — exits without
   `ModuleNotFoundError: No module named 'app'`.
2. Full collection count identical to baseline (823).
3. Gate-3 lint-imports green (27 contracts).
4. Sentinel present, zero locked-value changes, ≤2 files all backend/, PR off origin/develop → develop, OPEN.

## 4. Specialist + scope fence

`meesell-api-routes-builder` (sonnet) executed STEP 2. MUST NOT touch ci.yml, frontend/, k8s/, conftest,
test logic, the 5 test_config.py failures, or any locked pytest.ini key beyond the additive pythonpath.

---

## 5. OUTCOME (STEP 3 — coordinator merge-gate, 2026-06-11)

**VERDICT: APPROVE → merged.** PR #73 (branch `fix/ci-gate1-collection`), squash SHA
`1e95b2a95fe76cf7753d746969e5a3309683fac8` → develop. Remote ref deleted, worktree + local branch removed.

- All acceptance criteria PASS against the REAL diff: +4 lines (pythonpath + 3-line sentinel) in
  `backend/pytest.ini`, 1 file; no forbidden files; conftest unchanged; zero locked-value changes; PR
  template fully filled; single commit off origin/develop; no migration/endpoint/contract (§17 stays 28).
- Independent corroboration: re-ran clean-path collection from the live worktree — `import app` barrier
  GONE; next barrier = config.py SystemExit on §5.D env vars (= Finding B). Fix proven.

### Deviations (non-blocking)
- Branch named `fix/ci-gate1-collection` (spec proposed `fix/ci-gate1-pytest-collection`).
- No `Session:` footer token in the commit (standalone CI hotfix, not a feature-group PR — D2 session-block
  format does not formally apply).

### P0 — DOUBLE-MERGE (the important learning)
A PARALLEL DUPLICATE PR #74 (branch `fix/ci-gate1-pytest-collection` — the spec's originally-planned branch
name; an abandoned earlier specialist attempt, worktree `824bc99`) was OPEN and merged to develop ~28s AFTER
#73. Because #74 placed the `pythonpath` key at a DIFFERENT line than #73, git detected NO conflict and BOTH
applied → develop's `backend/pytest.ini` had TWO `pythonpath = .` lines → pytest rejected config-load:
`ERROR: pytest.ini:42: duplicate name 'pythonpath'` — breaking ALL 5 gates (worse than the original bug).
**Repaired** to a single key in closeout PR #75. Verified config loads clean afterward.

**LESSON:** before authoring a fix spec, search for ALREADY-OPEN PRs solving the same problem. The spec's
planned branch name had already been used by an earlier attempt that became PR #74; that PR was never
reconciled before this session dispatched a second one. Two PRs for one hotfix racing into develop is a
merge-gate hazard the lead must scan for at step 1, not discover at step 3.

### Finding A — backend DEBT (recorded, NOT fixed)
ZERO tests carry the `unit` marker. `pytest -m "unit"` collects 823 / deselects 823 / selects 0 — Gate 1
goes GREEN running NOTHING. RECOMMENDATION: queue a dedicated marker-classification task (future session) to
triage ~823 tests into unit/integration/smoke/slow/perf per §19.D. Out of scope for a collection hotfix; do
NOT batch into the fix PR. Owner when scheduled: api-routes-builder or services-builder by test slice.

### Finding B — handed to infra (inter-lead OPEN)
ci.yml Gate-1 `env:` block missing 5 §5.D-required vars: `GCS_BUCKET`, `GCS_PROJECT_ID`,
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `CORS_ALLOWED_ORIGINS` → config SystemExit at boot. Memo
`handoff_ci_gate1_envvars.md`; inter-lead row OPEN on the board; 48h SLA. ci.yml is infra-owned (no direct edit).

### Docs / surfaces landed (closeout PR #75)
- §19.D AS-BUILT NOTE (additive) in `docs/BACKEND_ARCHITECTURE.md` — records pythonpath=. + double-merge/repair, cites PR #73.
- `feature_board_backend.md`: #73 in Recently merged; Finding B inter-lead row OPEN.
- `STATUS_BACKEND.md`: full UPDATE block.
- `handoff_ci_gate1_envvars.md`: Finding B memo.
