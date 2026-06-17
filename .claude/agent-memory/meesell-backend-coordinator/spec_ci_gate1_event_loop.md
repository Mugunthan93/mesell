# SPEC — CI Gate-1 event-loop fix (`fix/ci-gate1-event-loop`)

**Authored:** 2026-06-12 by `meesell-backend-coordinator` (Rule-7 STEP 1 of 3).
**Consumes:** infra inter-lead request PR #145 — "Gate-1 (unit) red on develop".
**Assigned specialist:** `meesell-api-routes-builder` (rationale in §6).
**Branch:** `fix/ci-gate1-event-loop` off `origin/develop` (tip `bb7feb8`).
**Status:** STEP 3 COMPLETE — **GATE VERDICT: REJECT (close, do NOT merge PR #156).** Root problem already
solved by parallel PR #150 (`2d9b8af`) before #156 opened; #156 is a stale-base duplicate that would REGRESS
develop. See §9 OUTCOME below.

---

## 9. OUTCOME — STEP 3 merge-gate review (2026-06-12, `gate/ci-gate1-event-loop-review`)

**VERDICT: REJECT → close PR #156 unmerged. Do not bounce-and-fix; the fix is already on develop.**

### The decisive finding (independently verified)
The problem this spec targets — "Gate-1 unit RED on develop" — was **already fixed by parallel PR #150**
(`fix/gate1-eventloop`, merge SHA `2d9b8af`, merged 2026-06-12 03:02 UTC). PR #150 took an EQUIVALENT-intent
fix: dropped the `event_loop` fixture from conftest AND re-targeted the catalog monkeypatch — but via
`patch("app.modules.catalog.router.settings")` context-manager + an `unauth_client` hardening (saved
`dependency_overrides` clear + `raise_app_exceptions=False` + lifespan context to neutralise singleton
contamination across files sharing `_production_app`).

PR #156 was cut from base `a732729` (PR #152), which **predates** `2d9b8af` — confirmed:
`git merge-base --is-ancestor 2d9b8af origin/fix/ci-gate1-event-loop` → FALSE. So #156 is a stale-base
parallel duplicate. Merging it would **revert PR #150's `unauth_client` singleton-contamination hardening**
(the diff of #156-end-state vs develop strips the saved-overrides/clear/lifespan block) and swap develop's
`patch()` approach for #156's `monkeypatch.setattr` approach — a net REGRESSION, not an improvement.

### CI truth (the gate that matters)
- **develop tip `fe3f3ff` push run: Gate 1 (unit) = SUCCESS, Gate 2 (smoke) = SUCCESS, Gate 3 (lint) = SUCCESS.**
  Only Gate 4 (integration) fails — Gate 4 is ADVISORY per repo-management MASTER_PLAN §2.1.
- **PR #150's own CI: Gate 1 = pass (58s), Gate 2 = pass, Gate 3 = pass** (Python 3.12.13, pytest-asyncio
  0.24.0). The fix is proven green on CI.
- **PR #156: no CI checks ever reported** on the branch.
- Local master venv (`backend/.venv`, Py3.11, pytest-asyncio 0.24.0) shows 2 catalog flag-guard tests RED on
  develop tip BOTH full-suite AND in isolation (`got 500`/`Event loop is closed`). This is the documented
  local-macOS-Py3.11-vs-CI-Linux-Py3.12 event-loop teardown artifact (MEMORY gotcha #1 from catalog-form) — it
  does NOT reproduce on CI Gate-1 (PR #150's identical develop code is green on CI). Local red ≠ CI red here.

### Deviation adjudications (recorded for completeness; all moot under REJECT)
1. **Deviation 1 (root-cause reclassification → BRANCH 2 / importlib.reload Polluter B):** the mechanism is
   REAL — `test_config.py::_reload_config()` does `importlib.reload(app.shared.config)`, and the router holds a
   module-level `settings` binding from import time, so patching `_config_module.settings` misses the router's
   reference. VALID diagnosis. But develop's PR #150 already solved it via `patch("...router.settings")`. No
   credit owed — #156's analysis is correct yet redundant.
2. **Deviation 2 (allowlist — touched `test_catalog_routes.py`, not in spec §5 allowlist):** it IS the
   specialist's own authored file (api-routes domain) and the 6 changed lines PRESERVE test semantics (flag
   guard still proven to read settings at request time). NOT a semantic-weakening reject in isolation. **Report
   under-counted the diff: actual is +6/−6, report claimed +4/−4.** Moot under REJECT.
3. **Deviation 3 (STATUS_BACKEND.md append on my surface):** my surface; would be acceptable, but it is on the
   stale #156 branch and will be discarded with the close. The canonical STATUS entry is written on THIS gate
   branch instead.
4. **UNREPORTED 4th file:** #156 also carries `meesell-api-routes-builder/MEMORY.md +79` — the specialist's OWN
   memory (allowed, not forbidden, not my surface). The report claimed "3 files"; the PR has **4**.

### Follow-up chores queued
- **CHORE-A (close-out):** master session closes PR #156 unmerged with the REJECT comment; close PR #154 (the
  visibility-only SPEC PR) as superseded — the spec is now landed with this OUTCOME via the gate-record PR.
- **CHORE-B (latent debt, NOT fixed here):** `test_config.py::_reload_config()`'s `importlib.reload` pollution
  remains latent for any FUTURE module-level-`settings` test that patches `_config_module.settings`. PR #150's
  router-scope `patch()` neutralises it for the catalog tests TODAY, but the reload-pollution itself is
  untouched. Queue a hardening task (api-routes-builder): make `_reload_config` restore the original module/
  singleton on teardown (try/finally), OR document the "patch the consumer's binding, never `_config_module`"
  rule in the §19.D test conventions. Low priority — no live failure.
- **CHORE-C (process):** the double-/parallel-merge hazard struck AGAIN (gate1-collection PR #73/#74 lesson
  repeated). MEMORY updated: **before dispatching ANY CI-hotfix spec, grep open AND recently-merged PRs (last
  ~24h) for the same gate/file — not just open ones.** PR #150 was already merged when STEP 1 authored this spec.

## 0. The failure (verbatim diagnostic)

`develop` Gate 1 (`pytest -m "unit"` from `backend/`) is RED since commit `195b275`
(catalog-form backend slice). **13 tests fail**, ALL with the same exception:

```
RuntimeError: There is no current event loop in thread 'MainThread'
  raised from asyncio/events.py:702  (CI Python 3.12.13)
```

Failing tests (all in the new `backend/tests/unit/` dir):
- `backend/tests/unit/test_catalog_routes.py` — `TestAutofillFlagGuard` ×4, `TestCatalogFormFlagRouteMount` ×3
- `backend/tests/unit/test_catalog_unit.py` — `TestAutofillNeverAutoApplies` ×4, `TestAssertProductOwnership` ×2

These are `@pytest.mark.asyncio` + `pytest_asyncio.fixture(loop_scope="function")` + httpx
`AsyncClient`/`ASGITransport` tests. They PASS standalone but FAIL under the ordered `-m unit`
selection on CI Py3.12. The catalog-form session's prediction ("Py3.11-local-only loop-ordering
artifact, GREEN on CI") was WRONG — it reproduces under ordered selection on CI too.

---

## 1. ROOT-CAUSE INVESTIGATION — run these FIRST, before any edit

The coordinator has already done a static read of `origin/develop`. The specialist MUST
**reproduce and confirm** before touching anything. Do not trust the hypothesis blind.

### 1.1 Reproduce (CI-faithful)

From `backend/` with the Gate-1 dummy env (per `.github/workflows/ci.yml` Gate 1 job):

```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://u:p@localhost:5432/db"
export VALKEY_URL="redis://localhost:6379/0"
export JWT_SECRET="dummy"
export APP_ENV="development"
pytest -m "unit"        # expect 13 FAIL with the event-loop RuntimeError
```

- If Python 3.12 is available locally, use it (matches CI 3.12.13). If only the master
  venv (Py3.11) is available, the failure STILL reproduces under ordered `-m unit` selection
  per the diagnostic — run it there and confirm the SAME RuntimeError signature.
- Capture the FIRST failing test and the test that ran IMMEDIATELY BEFORE it
  (`pytest -m unit -v` and read the ordering).

### 1.2 Confirm the polluter by bisection

The coordinator's static read identified two pollution sources. **The specialist must
empirically confirm which one(s) actually fire**, not assume:

**Polluter A (PRIMARY hypothesis) — the redefined `event_loop` fixture.**
`backend/tests/conftest.py:271-274`:
```python
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```
This is a **hand-rolled redefinition of pytest-asyncio's reserved `event_loop` fixture**.
The repo runs **pytest-asyncio 0.24.0** (`backend/requirements.txt`), which **deprecated and
removed** the user-redefinable `event_loop` fixture. Under `asyncio_mode=auto` +
`asyncio_default_fixture_loop_scope=session` (the §19.D-locked mechanism in `backend/pytest.ini`),
this fixture: (a) creates a loop but NEVER calls `asyncio.set_event_loop(loop)` — so it is not
installed as the thread's current loop; (b) calls `loop.close()` at session teardown; (c) collides
with pytest-asyncio 0.24's own loop-management for function-scoped async fixtures. The net effect:
the thread's current-loop slot is left empty/closed, and a later `loop_scope="function"` fixture's
loop acquisition hits `events.py:702` → `RuntimeError: There is no current event loop`.

**Polluter B (CONTRIBUTING hypothesis) — `asyncio.run()` in sync test bodies.**
`backend/tests/test_worker_db_isolation.py` (lines ~79-80, ~156-157) and
`test_shared_database.py` (per the diagnostic) call `asyncio.run(...)` from SYNC (non-async)
test bodies. On Py3.12 `asyncio.run()` creates a fresh loop, runs it, then on exit calls
`asyncio.events.set_event_loop(None)` — **nulling the main thread's current loop**. Because
`tests/test_worker_db_isolation.py` sorts alphabetically BEFORE `tests/unit/test_catalog_*.py`,
these sync `asyncio.run()` calls run first and leave the thread loop-less for the later async tests
— UNLESS pytest-asyncio re-establishes a loop per function (which the broken Polluter-A fixture
prevents it from doing cleanly).

**Bisection procedure (REQUIRED):**
1. Run ONLY the catalog unit files in isolation — confirm they PASS:
   `pytest -m unit backend/tests/unit/ -v`
2. Run the full `-m unit` selection — confirm the 13 FAIL.
3. Comment OUT (do not yet delete) the `event_loop` fixture in conftest.py, re-run full
   `-m unit`. Record: do all 13 go green? (Coordinator predicts YES — Polluter A is primary.)
4. If step 3 does NOT fully fix it, additionally check Polluter B: run
   `pytest -m unit --deselect backend/tests/test_worker_db_isolation.py --deselect backend/tests/test_shared_database.py`
   with the fixture removed, and observe.
5. Record the empirical finding in the PR body "Root cause" section. **This bisection result
   drives which branch of §2's decision tree you take.**

---

## 2. FIX DESIGN — decision tree

### Decision node — driven by the §1.2 bisection result.

**BRANCH 1 (EXPECTED — Polluter A alone is the cause):**
Step-3 bisection shows all 13 go green once the `event_loop` fixture is removed.

→ **FIX: delete the redefined `event_loop` fixture** at `backend/tests/conftest.py:271-274`
(the `@pytest.fixture(scope="session") def event_loop(): ...` block). pytest-asyncio 0.24
manages the loop itself via the §19.D-locked `asyncio_default_fixture_loop_scope = session`
already present in `backend/pytest.ini`. The hand-rolled fixture is redundant AND harmful.
This is the pytest-asyncio-documented migration: "Remove any custom `event_loop` fixture;
use `asyncio_default_fixture_loop_scope` instead."

- This is the MINIMAL, lowest-blast-radius fix. PREFER IT.
- It does NOT touch `pytest.ini` (§19.D markers/asyncio/strict flags untouched — see §3 fence).
- It does NOT weaken any test or flip a global asyncio flag.

**BRANCH 2 (Polluter B also contributes — fixture removal alone insufficient):**
If after removing the fixture some catalog tests STILL fail, the `asyncio.run()` sync tests
are nulling the thread loop AND pytest-asyncio is not re-establishing it cleanly.

→ **FIX (additive to Branch 1):** make the `asyncio.run()` sync tests restore the thread's
loop on exit, scoped to the offending test bodies ONLY. The minimal, surgical form is to
save and restore the loop policy/current-loop around the `asyncio.run()` calls within
`test_worker_db_isolation.py` (and `test_shared_database.py` if it shows the same). Pattern:

```python
# inside the sync test, around the asyncio.run() call(s):
import asyncio
_prev = None
try:
    _prev = asyncio.get_event_loop_policy().get_event_loop()
except RuntimeError:
    _prev = None
try:
    asyncio.run(_single_run(1))
    asyncio.run(_single_run(2))
finally:
    if _prev is not None and not _prev.is_closed():
        asyncio.set_event_loop(_prev)
```

- PREFER a small SHARED helper or a `conftest`-level **autouse function-scoped** fixture that
  snapshots+restores the current loop around each sync test, over copy-pasting the try/finally
  into multiple test bodies. But keep it SCOPED — do not make it session-wide.
- Do NOT convert the `asyncio.run()` tests to `@pytest.mark.asyncio` async tests: their ENTIRE
  POINT is to exercise the "two sequential `asyncio.run()` calls in one prefork worker" path
  (worker DB isolation per §5.B / §18). Rewriting them as async destroys the thing under test.

**BRANCH 3 (NEITHER hypothesis holds — STOP):**
If §1.2 bisection shows the failure persists even with the `event_loop` fixture removed AND
the `asyncio.run()` tests deselected → the root cause is something the coordinator did not
identify. **STOP and report** (see §3). Do not guess further.

---

## 3. STOP-AND-REPORT FENCES (hard)

STOP, do NOT proceed, and report back to the coordinator if ANY of these is true:

1. **§19.D lock would be touched.** Do NOT edit `backend/pytest.ini` markers, `asyncio_mode`,
   `asyncio_default_fixture_loop_scope`, `testpaths`, `filterwarnings`, `addopts`, or the
   `pythonpath = .` line. These are §19.D-LOCKED (BACKEND_ARCHITECTURE.md §19.D) — changing them
   needs a §7.3 founder amendment. The fix MUST live in conftest.py / individual test files ONLY.
   (Note: the coordinator has CONFIRMED the `event_loop` fixture is NOT part of the §19.D lock —
   §19.D locks the contract, not the conftest fixture implementation — so removing it is in-scope.)
2. **A global asyncio_mode flip is needed.** The Gate-4 saga locked per-fixture `loop_scope` as
   the pattern; do NOT flip `asyncio_mode` or convert to a one-loop-for-everything posture.
3. **An assertion or test would have to be weakened/skipped** to make it pass. The fix is to
   stop the loop pollution, NOT to silence the symptom. No `@pytest.mark.skip`, no relaxed asserts.
4. **The fix needs to touch app/ source** (anything under `backend/app/`). This is a test-harness
   bug, not an app bug. If you believe app code must change, STOP and report — that is a
   different change requiring re-scoping.
5. **§1.2 Branch-3 outcome** (neither hypothesis reproduces the fix).
6. **The fix would touch `backend/tests/conftest.py` beyond the `event_loop` fixture removal +
   (Branch 2 only) an additive scoped loop-restore fixture.** Any broader conftest surgery — STOP
   and report; the coordinator will re-scope.

---

## 4. TEST / VERIFICATION PLAN

The specialist MUST paste ALL of the following into the PR "Test evidence" section:

1. **Full `-m unit` GREEN locally** (CI-faithful env per §1.1):
   `cd backend && pytest -m "unit"` → 0 failed. Paste the summary line (e.g. `XXX passed in Ys`).
   Confirm the previously-failing 13 are now in the passed count.
2. **Catalog units still pass in isolation** (regression guard — they passed before):
   `pytest -m unit backend/tests/unit/ -v` → all PASS.
3. **The `asyncio.run()` worker-isolation tests still pass** (Branch 2 sanity — must not have
   broken them): `pytest backend/tests/test_worker_db_isolation.py backend/tests/test_shared_database.py -v`
   → all collected unit tests PASS (integration ones may skip without a live tunnel — that is OK).
4. **No new warnings introduced** beyond the `filterwarnings=ignore::DeprecationWarning` baseline.
   Specifically confirm the pytest-asyncio "redefining event_loop is deprecated" warning is GONE.
5. **Ruff clean:** `cd backend && ruff check tests/` → no new violations on touched files.
6. **Collection unchanged count:** `pytest -m unit --collect-only -q | tail -1` before/after —
   the number of collected unit tests MUST be identical (you removed pollution, not tests).

---

## 5. FILE ALLOWLIST (touch ONLY these)

- `backend/tests/conftest.py` — DELETE the redefined `event_loop` fixture (Branch 1).
  Branch 2 only: ADD a narrowly-scoped autouse function-scoped loop-restore fixture.
- `backend/tests/test_worker_db_isolation.py` — Branch 2 only: wrap `asyncio.run()` calls with
  save/restore of the current loop.
- `backend/tests/test_shared_database.py` — Branch 2 only, IF §1.2 shows it also pollutes.

**FORBIDDEN (touching any of these = STOP):**
- `backend/pytest.ini` (§19.D lock)
- anything under `backend/app/` (this is a test bug, not an app bug)
- `backend/requirements.txt` (do NOT bump pytest-asyncio — 0.24.0 is correct; the bug is OUR
  redefined fixture, not the library)
- `docs/BACKEND_ARCHITECTURE.md` (no §19.D amendment — the lock is preserved by this fix)
- any `feature_board_*.md` (coordinator-owned), any other agent's memory dir

---

## 6. NAMED SPECIALIST + RATIONALE

**`meesell-api-routes-builder`** (sonnet).

Rationale: the failing tests are ROUTE-LEVEL tests (`test_catalog_routes.py` flag-guard +
route-mount tests against the FastAPI app via `ASGITransport`) plus the catalog service-unit
tests that exercise the route-adjacent autofill flow. The fix is in the shared pytest harness
(`conftest.py` fixture + sync-test loop hygiene), which is fixture/test-infrastructure work that
sits squarely in the api-routes-builder's domain (they own the route test patterns and the
httpx `AsyncClient`/`ASGITransport` fixture conventions per §19.D's per-fixture posture). The
change does NOT touch business logic, Celery tasks, AI seams, or auth middleware, so
`meesell-services-builder` (opus) is over-powered and off-domain here. api-routes-builder also
authored the catalog-form route flag-guard tests originally (commit `195b275`), so they own the
test files that regressed — they have the most context on the intended pass/fail semantics.

(Alternative considered: `meesell-services-builder` — rejected because the failure is not a
business-logic or service-layer bug; it is a test-loop-lifecycle bug in shared fixtures. opus
is not needed for a fixture deletion + scoped loop-restore.)

---

## 7. BRANCH + COMMIT CONVENTION

- **Branch:** `fix/ci-gate1-event-loop` off `origin/develop` (tip `bb7feb8`). New worktree, do
  NOT reuse the spec worktree.
- **Commit message convention** (conventional commits, matching the Gate-4 saga `fix(tests):`
  precedent):
  - Branch-1 fix: `fix(tests): drop redefined event_loop fixture — pytest-asyncio 0.24 owns the loop (Gate-1)`
  - Branch-2 add-on (if needed): `fix(tests): restore thread loop around asyncio.run() worker-isolation tests (Gate-1)`
  - Footer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- **PR:** `fix/ci-gate1-event-loop` → `develop`. Fill `.github/PULL_REQUEST_TEMPLATE/backend.md`
  COMPLETELY (no `<>` placeholders — coordinator refuses to merge otherwise). Session block:
  `mesell-ci-gate1-event-loop-backend-session-1`.
- **PR-template specifics the coordinator's STEP-3 gate will check:**
  - "Test evidence" carries ALL 6 §4 items pasted.
  - "Modules touched" lists `backend/tests/conftest.py` (+ Branch-2 files) with paths.
  - "Migration" section = N/A (no Alembic change) — state so explicitly, do not leave blank.
  - "Contract changes" = none (no endpoint/OpenAPI change) — state so explicitly.
  - Root-cause section states which §1.2 branch was taken and the bisection evidence.
  - CI Gates 1/2/3 green on the PR (Gate-1 is the one this fixes; 2/3 must not regress).

---

## 8. COORDINATOR STEP-3 GATE PREVIEW (what the merge review will enforce)

Per Rule-7 STEP 3, after the specialist opens the PR the coordinator re-runs the merge gate.
APPROVE requires: (1) §3 fences all respected — no §19.D-locked key touched, no app/ change, no
weakened assertion; (2) §4 all 6 evidence items present and green; (3) file diff within the §5
allowlist; (4) PR template fully filled, session block correct; (5) collection count unchanged.
REJECT-back-to-specialist if any fence is crossed or evidence is missing. This is a real gate —
it can bounce the PR.

This fix is a CHORE/test-harness repair on a feature-less branch, so per D1 the merge is
`fix/ci-gate1-event-loop` → `develop` directly (no `feature/{name}` integration layer — Gate-4
saga precedent, `fix(tests):` PRs #104/#107/#108/#110 squash-merged straight to develop).
