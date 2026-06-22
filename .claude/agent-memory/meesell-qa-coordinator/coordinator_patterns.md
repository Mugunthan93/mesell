# Coordinator patterns — cross-wave learning

Recurring gaps in what BUILDERS ship, observed at the merge gate. Each entry feeds
the next wave's spec automatically so every wave is smarter than the last. Format:
`pattern → which builder/lane → what to pre-empt in the next spec`.

## Seeded from prior project memory (2026-06-22)
- **Backend routes ship without error-path tests** → backend lane → every route in
  a spec must require ≥1 happy-path AND ≥1 error-path test.
- **Missing i18n fallback keys render blank errors** (e.g. `validation.generic.missing`,
  `validation.size_in_ltrs.invalid_enum_value`, `auth.token.missing`) → backend i18n →
  assert that a 422/validation message resolves to a non-empty string, not a raw key.
- **FE/BE contract drift surfaces as runtime 4xx** (e.g. suggest GET→POST 405;
  autofill reading `product_title` vs canonical `product_name`) → integration/E2E →
  assert the actual method + payload shape against the live OpenAPI.
- **Federation auth-singleton regression** (shell→remote nav logs the user out when
  `@mesell/core` is not deduped) → E2E → the `logout-guard` flow is the sentinel; keep it.
- **Assertion-free / `assert True` tests** slip in under time pressure → all lanes →
  reject at the gate; a test that asserts nothing is a defect.


## From Wave 1 — e2e lane (PR #385, 2026-06-22)
- **PROVISIONAL selectors written before exploration are frequently WRONG** → E2E lane →
  the registry must be LIVE-VERIFIED before codification; ~8 of the bootstrap provisional
  selectors were stale/renamed. The two-phase mandate (explore→codify) caught all of them.
  Keep enforcing: a selector that is not in `selector_registry.md` as LIVE-VERIFIED is a reject.
- **Federation singleton staleness bites the SHARED LIB, not just remotes** → E2E/frontend →
  a stale shell-hosted `@mesell/ui-kit` singleton makes `[testId]` passthroughs silently no-op
  even when the rebuilt remote bundle contains the string. Rebuilding remotes is NOT enough —
  the SHELL (singleton host) must be rebuilt too. (federation_quirks.md, Wave-1.)
- **Single-use rotating refresh token breaks shared `storageState`** → E2E auth setup →
  the standard "auth.setup saves one storageState → all flows reuse it" pattern 401s the 2nd
  flow. The robust pattern is a worker-scoped shared authed context (one login per worker).
  Bake this into every future E2E wave's auth fixture; do NOT regress to plain storageState reuse.
- **Hardcoded placeholder IDs in feature code surface only at the E2E/integration layer** →
  E2E → mfe-export shipped `productId='current-product-id'` (a unit/component test mocking the
  service would never catch it). The full-flow E2E export-download test is the only guard;
  keep flows that exercise REAL created entities (createProductViaPicker → real UUID) rather
  than stubbing the id.

## From Wave 3 — catalog vertical execution (PRs #396/#394, 2026-06-22)

- **"Contamination" in a lane diff is usually a STALE INTEGRATION BASE, not specialist scope creep** → all lanes / merge-gate → before rejecting a non-test file in a test-lane PR, check `diff <(git show develop:<f>) <(git show <branch>:<f>)`. If IDENTICAL to develop, it is a develop commit the branch inherited because the integration branch was cut at an older develop tip. FIX = fast-forward `integration` to current develop (verify `merge-base --is-ancestor` first) BEFORE merging; then the lane's net-new is just its own files. Do NOT reject the specialist for it.
- **Frontend component specs use the pure-function-mirror pattern, not TestBed render** (PrimeNG 21 + Angular 21 ngModule-null TestBed crash, documented as angular-component-builder Wave-5 F8) → frontend lane → the spec re-implements the component's logic inline and asserts against the copy. This is a WEAKER guard than a render test (drift between the real component and the mirror goes undetected), but it is the accepted codebase-wide pattern. At the gate: VERIFY the mirror faithfully matches the real component logic (read both); accept it as a contract guard; flag it (not reject) so the founder knows a TestBed-render upgrade is owed once the PrimeNG/Angular issue is fixed. The SERVICE specs (HTTP boundary) DO use real TestBed + HttpTestingController — require that for any service lane.
- **A regression guard must assert the NEGATIVE, not just the positive** → all lanes → W3-FE-5 done right: it asserts `product_name` is the seed AND that `product_title` does NOT win when `product_name` is present (the actual bug was reading `product_title`). A guard that only asserts the happy key would stay green if the bug came back. Spec the negative assertion explicitly.
- **Narrow infra-gate skips (DB-connection-refused / openpyxl-importorskip) are acceptable; assertion-free skips are not** → backend lane → a `pytest.skip()` that only fires on a genuine `Connection refused`/missing-optional-dep and otherwise runs the full assertion is fine. The reject line is a skip that NEVER asserts (the Wave-1 P1.11 self-skip) or a `pytest.skip()` at the top of the test body unconditionally.
- **The Valkey port default in conftest is `:6381` (CI), not `:6379` (local)** → backend lane / gate environment → any test on the rate-limit/plan-guard Valkey path 500s locally unless a Valkey runs on 6381 OR `TEST_VALKEY_URL` is overridden. Expect ~2 such pre-existing failures (`test_flag_gate.py`) in any broad local backend run; confirm they're byte-identical at base and disclose, don't treat as new.


## Wave-3 e2e gate — recurring patterns
- STALE-BASE / LANE-DELETION HAZARD is now confirmed RECURRING on E2E lanes (Wave-2 AND Wave-3). E2E branches get cut from
  develop, so their merge-base with the wave integration branch pre-dates the BE/FE lane merges. ALWAYS run
  `git diff --diff-filter=D --name-only integration..e2e` BEFORE squashing; if it shows lane-file deletions, merge
  integration INTO the e2e branch first, then squash. Make this a standing pre-squash check for every multi-lane wave.
- SCOPE-CREEP FALSE POSITIVE: files like `dead_route_guard.mjs` / `ci.yml` can appear in a lane PR diff purely because the
  branch carries develop commits the integration base lacks. Before rejecting for scope creep, check `git cat-file -e
  origin/develop:<file>` — if it's already on develop, it's a base-divergence artifact, not the specialist's edit.
- BOARD IN-REVIEW SOFT GAP persists across ALL e2e lanes (Wave-1/2/3): the e2e specialist leaves its row PENDING on PR open
  instead of flipping to IN REVIEW. Same omission seen on backend lanes. Low-cost product-side fix; gate keeps setting the
  final MERGED state and logging it. Consider baking the IN-REVIEW flip into the e2e-writer dispatch spec.
- HONEST SKIP-GATING is the correct posture for env-blocked E2E (W3-E2-1): gate on the precondition (suggestions present /
  schema fields present) with a documented `test.skip` reason rather than letting the flow fail red on an env gap. Verify
  the skip does NOT green-wash (it must still assert the visible outcome when the precondition IS met).

## From Onboarding Wave C — e2e lane gate (PR #411, 2026-06-22)
- **The e2e specialist FLIPPED its board row to IN REVIEW on PR open this time** (`f787541`) → e2e lane → the long-standing board-IN-REVIEW omission (Wave-1 #385, Wave-2 #408, Wave-3 #409 all left it PENDING) was FIXED this wave. Keep reminding at dispatch; it is starting to land.
- **No stale-base hazard when the lane branch is cut from the CURRENT integration tip** → all lanes → merge-base(e2e, integration) == integration tip exactly → `git diff integration..e2e --name-status | grep '^D'` empty → clean-additive squash, no reconcile needed. This is the FIRST later-lane in the qa-onboarding wave to NOT hit a stale base (Wave B #407 was also clean). The fix is procedural: cut the lane branch from the LIVE integration tip, not from develop. Still ALWAYS run the `grep '^D'` check before merging.
- **A no-testid form is still cleanly E2E-testable via `getByLabel` / `getByRole`** → e2e/frontend → the post-#399 onboarding form ships zero field testids (mee-input wrappers), but each renders a real `<label [for]>` so `getByLabel(substring)` is a stable, accessibility-grounded selector; the error banner's `role="alert"` and the skip link's `role="button"` are likewise stable. Prefer role/label selectors over begging the FE for testids when the semantic HTML is already correct — fewer cross-lead memos. (Still record them in `selector_registry.md` as LIVE-VERIFIED.)
- **A contaminated/half-rebuilt running stack is the DEFAULT state the gate finds** → e2e gate mechanics → when the gate wants to independently re-run Playwright, the already-running stack is frequently a mix of slots (some remotes on slot-0 ports, others on slot-1) with no reachable backend. Do NOT trust it for a gate re-run; either stand up a clean fully-aligned slot or DISCLOSE the fallback to rigorous static + source ground-truthing (the checklist explicitly allows this). SOURCE ground-truthing (grep the integration-tip SOURCE for every claimed selector + the persist fix) is a HIGH-confidence substitute for a live re-run on a tests-only e2e PR.

## From qa-image-ai Wave A gate (PR #431, 2026-06-22) — REJECTED (one file)
- **A new full-stack `AsyncClient(ASGITransport(app=app))` integration test that hand-rolls its OWN
  client fixture (instead of reusing the established `tests/integration/conftest.py` client) RE-OPENS
  a KNOWN, already-solved `_otp_client` event-loop bug** -> backend lane -> `rate_limit_mw._check_window`
  calls the `get_valkey_otp()` SINGLETON; across multiple `AsyncClient` lifespans in one process the
  singleton keeps a redis conn bound to a CLOSED loop -> `RuntimeError: Event loop is closed` -> the
  middleware returns 500 BEFORE the route logic runs. Symptom: each test PASSES ALONE but the file
  FAILS as a unit (here 2/4). Fix documented verbatim in `integration/conftest.py` ("D2 fix /
  Gate-4 repair-1": patch `_valkey_module._otp_client` to a fresh function-loop-bound client).
  PRE-EMPT in every backend spec that drives the full ASGI middleware stack: REQUIRE reuse of the
  loop-bound-`_otp_client` client fixture. A new ad-hoc `AsyncClient(app=app)` fixture is a gate
  smell — check it runs as a UNIT, not just per-test.
- **Run the file/lane AS CI WILL run it, not just per-test** -> all lanes -> CI Gate-4 runs
  `pytest -m "integration"` = ALL integration tests in ONE process. A test that passes in isolation
  but fails in-process WILL red the integration->develop gate (the Wave-2 PR #421 lesson, new costume).
  At the gate, run the new files TOGETHER in one process. "Passes when I run just this test" is NOT proof.
- **A stale integration-branch base inflates the PR diff but is NOT a content defect** -> all QA waves ->
  when `feature/<slug>/integration` lags develop, the PR-vs-base diff balloons with already-merged
  history (here 67 files vs the real 7). Compute `git diff origin/develop...<branch>` for the TRUE
  lane delta, and fast-forward integration to develop's tip BEFORE merging. Don't reject on diff size.
- **A stub-locking guard becomes a landmine when the parallel lane removes the stub** -> AI/eval lane ->
  `TestStubStateGuards` (asserts the `_run_one_fixture` stub's 0/N) reds the instant the IA-RED-2 real
  scorer lands. A guard asserting a TEMPORARY state must have its retirement OWNED by whoever lands the
  state change; record it on the board + a memo at gate time. (handoff_eval_stubguard_iared2_image_ai.md.)
