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

## From qa-onboarding Wave A — backend gate (2026-06-22)
- **Backend test writer's deferrals were BOTH honest this wave** (a good sign): the OB-BE-24 flag-OFF skip
  is a genuine process-singleton limitation (a sibling test mounts the flag-gated router onto the
  shared `app.main.app` in-process), and OB-BE-38 DPDP was a real schema gap, NOT a coverage hole.
  Gate lesson: VERIFY the schema-gap claim yourself (`grep consent` → 0 hits) before accepting a
  "not modelled, no test" deferral; don't let a writer hand-wave a missing assertion as a spec gap.
- **`assert True` is NOT automatically a green-washed test.** The 2 nullable-CHECK positive cases end
  in `assert True`, but the load-bearing assertion is the `await db_session.flush()` line ABOVE it —
  the CHECK constraint fires on flush; reaching `assert True` IS the proof it didn't raise. Read the
  whole test body before rejecting an `assert True` — distinguish "operation completed without raising"
  (legitimate) from "asserts nothing meaningful" (reject).
- **A flag-gated route mounted onto a process-wide app singleton defeats per-test flag isolation** →
  backend lane → when a spec needs to assert BOTH flag-ON and flag-OFF behaviour for the same route,
  require an app-FACTORY fixture (fresh ASGI app per test), not the shared `app.main.app` import.
  Pre-empt this in the next backend spec that touches a feature-flag-gated mount.
- **Gate env recipe for re-running integration tests locally:** the app's §5.D startup guard requires
  ~13 env vars (REFRESH_TOKEN_PEPPER, MSG91_*, RAZORPAY_*, GCS_*, LANGFUSE_*, AUDIT_PII_SALT,
  CORS_ALLOWED_ORIGINS). Copy them dummy from `.github/workflows/ci.yml`'s integration job. The DB must
  be at `alembic upgrade head` (the integration conftest expects a PRE-MIGRATED `*_test` DB, it does
  not build schema). Local PG is on 5432 (CI uses 5433). The backend `.venv` (py3.11) has the deps;
  the base interpreter does not.
- **A specialist may open the group PR against the WRONG base (`develop` not `…/integration`).** GitHub
  then blocks retargeting if the squash already landed on integration ("no new commits between base and
  head"). The QA gate is still satisfiable: post the APPROVE verdict + close the PR with the squash SHA
  recorded. Watch for this — `develop` is the FOUNDER's gate, never the QA group-PR target.
- **The master-tree git guard blocks branch-ref moves from `/Users/.../mesell`.** To land the board
  gate-record on the integration branch, commit in a worktree and `git push origin HEAD:refs/heads/<branch>`.
  Do NOT `git branch -f` from the master checkout (guard-master-tree-git blocks it).
