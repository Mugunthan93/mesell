# SPEC — CI Gate-4 (integration) cross-loop contamination fix

**Authored:** 2026-06-12 by `meesell-backend-coordinator` (Rule 7 three-step, STEP 1 of 3).
**Session token:** `mesell-gate4-loop-contamination-session-1`
**Predecessor saga:** Gate-4 passes 1–4 (#104→#110) reached exit-0 on the *then*-visible suite. PR #150 (squash `2d9b8af`) fixed Gate-1 unit collection/loop hygiene, which **un-skipped/unmasked** a latent integration regression that the prior Gate-1 collection failure had been hiding. This is the honest-merge follow-up: **NO override this time** — all 13 checks must go green on the PR.
**Source failure:** develop run `27391715982` (post-#150 merge, SHA `2d9b8af`), Gate 4 = `6 failed, 162 passed, 16 skipped, 723 deselected, 13 errors`.
**STEP 2:** named specialist executes. **STEP 3:** coordinator merge-gate review (real gate — can reject).

---

## 1. The exact failing inventory (19 nodes: 6 failed + 13 errors)

### FAILED (6)
1. `tests/integration/test_customer_cross_module_eligibility.py::test_assert_eligibility_raises_when_super_not_declared` — cross-loop (`got Future attached to a different loop`, BaseHTTPMiddleware)
2. `tests/integration/test_customer_cross_module_eligibility.py::test_assert_eligibility_succeeds_when_all_gates_pass` — cross-loop
3. `tests/integration/test_customer_full_onboarding_flow.py::test_full_onboarding_flow_drives_flag_true` — cross-loop
4. `tests/integration/test_iam_replay_attack.py::test_replay_of_old_refresh_cookie_after_rotation_returns_401` — cross-loop
5. `tests/test_shared_database.py::test_get_db_yields_async_session` — cross-loop (`got Future attached to a different loop`, app-global engine)
6. `tests/modules/catalog/test_integration.py::TestFullProductLifecycle::test_full_lifecycle` — `AssertionError: assert False is True` at L80 (`assert autofill_result.applied.get("product_name") is True`). **CLASSIFY THIS ONE (see §2.C) — likely a downstream symptom of the same loop contamination corrupting the `db` fixture's autofill write, NOT a genuine G7 regression. Specialist MUST confirm before touching the assertion.**

### ERRORS (13) — all `RuntimeError: Event loop is closed` at teardown
- `tests/modules/export/test_router.py` ×4: `test_post_export_xlsx_wrong_user_returns_404`, `test_post_export_xlsx_happy_returns_202`, `test_get_export_not_found_returns_404`, `test_get_export_ready_returns_200_with_signed_urls`
- `tests/test_customer_routes.py` ×9: all `TestPatchSellerProfile` (×3), `TestPatchActiveCategories` (×2), `TestPatchComplianceExtension` (×2), `TestGetSellerProfile` (×1), `TestGetRequiredFields` (×1)

---

## 2. Root cause (coordinator diagnosis — verified against the merged tree, not just quoted)

### 2.A — The mechanism (cross-loop contamination via the app-global engine + session-default loop)

ONE-SENTENCE ROOT CAUSE: **Integration tests that drive the real FastAPI app through `BaseHTTPMiddleware` resolve `Depends(get_db)` against the *app-global* `AsyncSessionLocal`/engine (a module-import-time singleton whose pool binds to the first loop that touches it — the session loop, via the `scope="session"` autouse seed/migration fixture), while the test itself runs on a function-scoped loop; the middleware then awaits a Future created on the session loop, raising `got Future attached to a different loop` (and `Event loop is closed` at teardown when the session loop is torn down before the function-scoped connections close).**

Verified facts (merged develop @ `2d9b8af`):
- `backend/pytest.ini` (LOCKED §19.D) sets `asyncio_default_fixture_loop_scope = session`. So any async fixture WITHOUT an explicit `loop_scope="function"` runs on the **session loop**.
- PR #150 correctly **removed** the stale `scope="session" def event_loop()` fixture from root `conftest.py` (that was a separate Gate-1 hazard). Its removal is good and must STAY removed.
- `tests/integration/conftest.py::iam_client` HAS `loop_scope="function"` BUT its docstring states verbatim: *"Does NOT override `Depends(get_db)` — routes resolve the dep against `settings.DATABASE_URL`"*. So requests through `iam_client` hit the **app-global** `get_db`/`AsyncSessionLocal` engine, which is NOT born in the function loop. That is the contamination seam for failures 1–4.
- `tests/test_shared_database.py::test_get_db_yields_async_session` (failure 5) calls `get_db()` **directly** (the app-global generator) under a bare `@pytest.mark.asyncio` — same app-global-engine-on-wrong-loop seam.
- The ALREADY-FIXED twin pattern is the proof: `customer_client` (`tests/test_customer_routes.py`) and `export_client` (`tests/modules/export/test_router.py`) BOTH create a **function-loop NullPool engine** and `app.dependency_overrides[get_db] = _db_override` (verified at `test_customer_routes.py` L200, `test_router.py` analogous). Yet they STILL throw `Event loop is closed` at teardown (the 13 errors) because the **lifespan** (`async with app.router.lifespan_context(app)`) boots `app.state.db_engine`/`app.state.valkey` on a loop that mismatches teardown order. So the override fixes the *request-path* engine but not the *lifespan-state* engine.

### 2.B — Why it surfaced NOW (the skip cascade)
Before #150, Gate-1 unit died at collection (`ModuleNotFoundError: No module named 'app'` → later the `event_loop` fixture hazard). That collection death masked a chunk of integration discovery on the prior substrate, so the contaminated nodes were not all being exercised to a hard red. #150's clean Gate-1 path (and the conftest `event_loop` removal that shifts every fixture onto the pytest.ini session-default loop) **unmasked** the latent contamination. LESSON for memory: *a Gate-1 fix can unmask a latent Gate-4 regression via the skip/collection cascade — always re-baseline Gate-4 after any conftest/pytest.ini change.*

### 2.C — The catalog `test_full_lifecycle` outlier (failure 6) — DIAGNOSE, do not presuppose
- It uses the `db` fixture (function-loop, savepoint-isolated per pass-3) + `stub_call_gemini`, NOT `iam_client`. Its `assert autofill_result.applied.get("product_name") is True` (L80) fails as `assert False is True` (i.e. `.get()` returned `None`/`False`).
- The as-built `app/modules/catalog/service.py` STILL auto-applies on the confidence-floor path (L685 `applied[name]=True` when `confidence >= _AUTO_APPLY_CONFIDENCE_FLOOR`). So the assertion is **NOT obviously stale** — if the stub returns `product_name` at sufficient confidence, `applied["product_name"]` SHOULD be `True`.
- TWO HYPOTHESES the specialist MUST distinguish (read the stub + run the single test in isolation):
  - **H1 (likely): loop-contamination symptom.** Under the same wrong-loop corruption, the autofill JSONB write (`update_fields_jsonb`) or the stub interaction silently no-ops, leaving `applied` empty. **If H1: the §3 loop fix makes this test pass with NO assertion edit.** Run it in isolation post-fix to confirm.
  - **H2 (less likely): genuine G7 drift.** The catalog-form G7 ruling ("remove auto-apply; writes ONLY to `ai_suggestions_jsonb`, `applied` always False") may have been intended to zero out the auto-apply path, and the as-built service retains a stale auto-apply branch. **If H2: this is an APP bug, NOT a test bug — STOP and escalate to the coordinator; it is OUT of this test-only fence and needs a separate catalog-service ticket + founder confirmation of G7 scope. Do NOT silently flip the test assertion to mask an app-behavior question.**
- DEFAULT EXPECTATION: H1. The fix in §3 should clear all 6 failures including this one with zero assertion edits. Only if it does NOT clear after the loop fix does the H1/H2 fork matter.

---

## 3. The fix pattern (test-harness/fixtures only — LOCKED conftest blocks untouched)

The canon established by the Gate-4 saga (#104–#110) and the customer_client/export_client twins is: **every engine and every app-state binding a test touches must be born in, and die in, the test's own function-scoped loop.** Apply that uniformly to the contaminated fixtures.

### 3.A — Primary fix: function-loop lifespan + get_db override on the iam-routed path
For the integration fixtures that drive the real app (`iam_client` in `tests/integration/conftest.py`, and any helper `_make_session_factory()` in the 3 failing integration files):
1. Override `app.dependency_overrides[get_db]` with a function-loop NullPool engine session (mirror the `customer_client`/`export_client` pattern verbatim — same `async_sessionmaker(join_transaction_mode="create_savepoint")` substrate from pass-3). The `iam_client` "no get_db override" design is the defect; give it the override.
2. Ensure the lifespan-state engine (`app.state.db_engine`) and `app.state.valkey` are either (a) also bound on the function loop, or (b) the lifespan is entered/exited entirely within the function loop so teardown order matches. The `Event loop is closed` teardown errors (13) come from lifespan-state outliving the loop — closing the lifespan engine inside the same function-loop fixture scope (explicit `await engine.dispose()` in teardown BEFORE the loop ends) is the canonical close-out.
3. Do NOT reintroduce a `def event_loop()` fixture — #150 removed it deliberately; the fix is correct fixture loop_scope + function-loop engines, NOT a custom loop fixture.

### 3.B — `test_shared_database.py::test_get_db_yields_async_session` (failure 5)
This test exercises the app-global `get_db()` generator directly. Two acceptable in-fence fixes (specialist's call):
- **Preferred:** rebind the test to a function-loop engine by patching `app.shared.database.AsyncSessionLocal` (or the engine) to a NullPool engine created inside the test's loop for the duration of the test, then restore. Keeps the test's intent (verify `get_db` yields an `AsyncSession` and reaches Postgres) while killing the cross-loop Future.
- **Alternative:** mark/structure so the app-global engine is initialized on the test's loop. Whichever is cleaner — the bar is the test goes green AND no app code changes.
- Do NOT change `app/shared/database.py` (app code, out of fence). The two sibling tests (`test_get_db_commits_on_success`, `test_get_db_rolls_back_on_exception`) already pass (they mock `AsyncSessionLocal`) — leave them untouched.

### 3.C — The 13 `Event loop is closed` teardown errors
These are predominantly the customer/export route fixtures' lifespan teardown. The fix is teardown hygiene: dispose the lifespan/state engine + close the Valkey client INSIDE the function-loop fixture's finally-block, BEFORE the function loop is torn down. Verify by running `tests/test_customer_routes.py` and `tests/modules/export/test_router.py` in isolation — zero teardown errors is the gate.

---

## 4. HARD constraints (the fence)

**MAY touch (test-harness/fixtures ONLY):**
- `backend/tests/integration/conftest.py` (the `iam_client` fixture + helpers) — give it the function-loop get_db override + lifespan teardown hygiene.
- `backend/tests/integration/test_customer_cross_module_eligibility.py` (`_make_session_factory` / fixture usage)
- `backend/tests/integration/test_customer_full_onboarding_flow.py` (`_make_session_factory` / fixture usage)
- `backend/tests/integration/test_iam_replay_attack.py` (fixture usage)
- `backend/tests/test_shared_database.py` (function-loop rebinding of the one failing test only)
- `backend/tests/test_customer_routes.py` (teardown hygiene only — request-path override already correct)
- `backend/tests/modules/export/test_router.py` (teardown hygiene only)
- `backend/tests/modules/catalog/test_integration.py` — ONLY IF H1 confirmed false AND the failure persists post-loop-fix AND it is proven test-stale (not app-bug). DEFAULT: do not touch; the loop fix should clear it.
- `docs/status/STATUS_BACKEND.md` (append-only close-out block).

**MUST NOT touch:**
- `backend/pytest.ini` — **LOCKED §19.D**. `asyncio_mode=auto`, `asyncio_default_fixture_loop_scope=session`, markers, addopts, the `pythonpath=.` key (#150) — all frozen. NO new markers. NO loop-scope flip in the ini.
- `.github/workflows/ci.yml` — infra-owned.
- `backend/app/**` — NO application code. (If catalog L80 turns out to be H2 app-bug, STOP and escalate — do NOT fix app code in this pass and do NOT mask it via a test edit.)
- `backend/alembic/**`.
- The LOCKED conftest blocks: the `scope="session" autouse` seed/migration fixture (line 156), the `db_engine`/`db_session`/`db` savepoint-isolation fixtures (pass-3 canon), the `_ensure_seed`/BE-SEED-1 skip logic. These are the pass-1→pass-4 substrate — they are CORRECT and FINAL. Add function-loop bindings to the *contaminated* fixtures; do NOT rewrite the savepoint harness.
- Do NOT reintroduce a `def event_loop()` fixture (#150 removed it on purpose).
- §2.D cross-module matrix, §16 import-linter rules, §17 endpoint count (stays 28) — untouched. No FE/AI/data contract memo (test-only).

---

## 5. Acceptance bar (NO override — must merge honestly)

- `cd backend && pytest -m integration -v` (CI env shape, pass-3 savepoint substrate) → **exit 0**, ZERO failures, ZERO errors. Skips = the justified BE-SEED-1 set only.
  - BEFORE: `6 failed, 162 passed, 16 skipped, 13 errors` (develop @ `2d9b8af`).
  - AFTER target: `0 failed, ≥181 passed, ~16 skipped, 0 errors` (the 6 failures → pass, the 13 errors → pass; ≥ the #110 baseline of 175p/17skip, accounting for the wave's added tests). Show the 19 newly-green node names in PR Test-evidence.
- ALL 13 PR checks green: Gate 1/2/3 + Gate 4 + Gate 5 (advisory) + 8 frontend units + detect. **NO `--admin`.** If Gate 4 is still red on the PR, REJECT back to specialist with the new failure pasted (no silent block).
- Confirm `git diff` touches ONLY the §4 MAY-touch files. Zero `app/`, `ci.yml`, `pytest.ini`, `alembic/`, LOCKED-conftest-block diff.
- Run each previously-failing file in ISOLATION post-fix (`pytest tests/integration/test_iam_replay_attack.py -v` etc.) AND in the full `-m integration` set — both must be green (catches loop-ordering artifacts that only appear in-suite).

---

## 6. Named specialist

`meesell-api-routes-builder` (sonnet). RATIONALE: this is pytest/FastAPI test-harness wiring (fixture loop-scope, `dependency_overrides[get_db]`, ASGI lifespan teardown order) — the same test-tooling domain as PR #150, which api-routes-builder executed cleanly. NO business logic, NO service-data semantics (the pass-4 pricing/is_leaf test-data work that warranted services-builder is DONE and not in this inventory). The one judgment call (catalog H1/H2 fork) is a STOP-and-escalate, not a service edit. Sonnet correct.

**ESCALATION TRIGGER:** if catalog `test_full_lifecycle` proves to be H2 (genuine G7 app-drift, app code wrong), the specialist STOPS, reports H2 to the coordinator, and that becomes a SEPARATE three-step (services-builder on `app/modules/catalog/service.py` + founder confirmation of the G7 auto-apply scope) — explicitly OUT of this test-only pass.

---

## 7. Model C git plan

- Base: `origin/develop` tip (re-fetch to confirm; was `fe3f3ff` at spec authoring, post-#150 + later docs merges).
- Branch: `fix/gate4-loop-contamination`
- Worktree: `/tmp/mesell-wt/gate4-fix` (confirm free; `/tmp/mesell-wt/gate1-fix` was cleaned this session).
  - `git -C /Users/mugunthansrinivasan/Project/mesell fetch origin`
  - `git -C /Users/mugunthansrinivasan/Project/mesell worktree add /tmp/mesell-wt/gate4-fix -b fix/gate4-loop-contamination origin/develop`
- Standalone CI hotfix (no `feature/{name}/backend` parent) → PR targets `develop`, D1 group-gate N/A; develop→main stays the founder's gate.
- Commit message:
  ```
  fix(tests): Gate-4 — kill cross-loop contamination in iam/customer/export/shared-db integration fixtures

  PR #150 (Gate-1 fix) unmasked a latent Gate-4 regression: integration
  tests driving the real app through BaseHTTPMiddleware resolved get_db
  against the app-global session-loop engine while running on a
  function-scoped loop -> "got Future attached to a different loop" /
  "Event loop is closed". Give the iam_client path a function-loop
  get_db override + lifespan teardown hygiene, mirroring the
  customer_client/export_client twins. Test-harness only;
  pytest.ini (§19.D) + app code + LOCKED conftest blocks untouched.

  6 failed + 13 errors -> 0/0. No override; all 13 checks green.

  Session: mesell-gate4-loop-contamination-session-1
  ```
- PR body fills `.github/PULL_REQUEST_TEMPLATE/backend.md` completely; N/A sections explicit (no `<>` placeholders); paste BEFORE/AFTER exit-0 evidence + the 19 newly-green node names + interpreter version.
- STEP-3 merge-gate (coordinator): diff confined to §4 fence; pytest.ini/app/ci.yml/alembic untouched; LOCKED conftest blocks untouched; before/after exit-0; isolation + in-suite both green; §17 stays 28; no FE/AI/data memo; squash-merge; delete branch via `gh api -X DELETE`; clean worktree; board → MERGED + Recently merged; STATUS block; notify infra "Gate-4 GREEN — develop→main re-fire clean."

## 8. Tickets
- BE-GATE4-LOOP-1 — OPEN (this spec). Closes on exit-0 honest merge.
- BE-CATALOG-G7-AUTOAPPLY-1 — CONDITIONAL/OPEN-pending-H1-test. Only materializes if catalog L80 proves H2 (app-drift). Tracked here so it is not lost; NOT in this pass's scope.
