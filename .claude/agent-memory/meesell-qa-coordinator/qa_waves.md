# QA Waves — history & exit criteria

One entry per QA wave: feature slugs covered, the coverage target set per
specialist, what was actually achieved, and whether the exit criteria were met.
Append a new section at the top after each wave.

## Wave 1 — e2e lane (codify) — 2026-06-22 — MERGED (PR #385, develop squash `70fe9f3`)

**Session:** `mesell-qa-wave-1-e2e-session-1` (merge-gate review, autonomous mode — founder pre-approved → `--admin`).
**Specialist:** `meesell-e2e-test-writer` (opus).
**Scope:** all 8 critical seller flows from the e2e taxonomy.
**Exit criterion (spec):** every taxonomy flow codified with a VISIBLE-outcome assertion; flaky/blocked flows marked `test.fixme` with a logged reason — MET.

**Result:** `playwright test --workers=1` = **9 passed / 3 test.fixme**, stable across 3 runs (9 PNG screenshots `/tmp/e2e-run/screens/`, verified genuine 1280x720 RGB).
- GREEN (each asserts DOM/URL): onboarding, catalog-creation, category-picker, plan-guard, **logout-guard** (FED-1 sentinel — URL=/login + `goBack()` stays /login + dashboard-heading count 0 + crosses the federation boundary pre-logout; confirms the #381 logout fix E2E), google-signin(render: GIS host + injected iframe), image-precheck(uploader renders), export(page + Generate render for a real product).
- `test.fixme` (all ADDRESSED with logged reasons in `federation_quirks.md`): export-download (**product bug** — mfe-export hardcodes `productId='current-product-id'`), image-precheck-result (no GCS local → 502), google-click (headless cross-origin OAuth + non-allow-listed origin).

**Gate notes (what made this a clean PASS):**
- Selectors all `getByTestId(...)` / page objects, live-verified against #381 testids on slot-1 shell :4210; `selector_registry.md` corrected from PROVISIONAL → LIVE-VERIFIED (~8 provisional selectors were wrong, e.g. `nav-account`→`nav-profile`, `precheck-result-card`→`precheck-card`, `export-download-button`→`export-trigger`/`export-download`, `category-search`→`smart-picker-description`).
- Zero hardcoded ports — all base URLs from `playwright.config.ts` (env-overridable). No token injected to localStorage (Decision #14 honoured).
- Auth architecture is the durable Wave-2+ asset: the single-use rotating refresh token breaks plain shared-`storageState` reuse (2nd flow 401s); the suite uses a **worker-scoped authed-context fixture** (`fixtures/auth.ts`) — one OTP login per worker, seeded from the setup project's storageState (zero extra OTP sends).
- No assertion-free tests; plan-guard even adds a negative assertion (remote-failure-fallback count 0).

**Merge mechanics:** PR base was a STALE develop (cut before #383/#384) → the only conflict was `feature_board_qa.md` (my sole-writer surface). Hand-resolved in a worktree by combining #383/#384 rows + the e2e updates, pushed to the PR branch, then squash-merged `--admin`. Branch preserved (NO `--delete-branch`).

**Findings owed to the TEST_REPORT / Wave 2:** (1) the mfe-export route-productId product bug (filed → frontend-coordinator); (2) the 3 `test.fixme` (un-fixme conditions logged); (3) carry-forward also includes the 61 pre-existing frontend reds (#383 gate) + the backend P1 export-ZIP self-skip (#380 gate).

## qa-onboarding — Wave A (backend) — GATE PASSED (2026-06-22, mesell-onboarding-testing-session-2)

**Slug:** `qa-onboarding`. Branch model: `feature/qa-onboarding/{backend,frontend,e2e}` → `feature/qa-onboarding/integration` (QA gate) → develop (founder gate, D1).
**Plan:** `docs/testing/ONBOARDING_QA_WAVE_PLAN.md` §2 Wave A + §3.A/§3.B. **Specialist:** `meesell-backend-test-writer`. **PR #391**.

**VERDICT: APPROVE → squash on integration (`aa4345d`); board gate-record (`2ff4b6f`).** 3 files / 15 cases:
`test_iam_onboarding_coverage.py` (11: OB-BE-01/02/05/06/07/16/17/18/22/23/24), `test_iam_nullable_identity_check.py` (3: OB-BE-25), `test_customer_onboarding_coverage.py` (1: OB-BE-31).

**Gate RE-RAN (did NOT trust the report)** vs `meesell_test` @ alembic head `e9415bdcae20`, CI dummy-env recipe (from `.github/workflows/ci.yml` integration job; local PG 5432 not CI 5433):
- 3 new files = **14 passed / 1 skipped / 0 failed** (exact match to report).
- existing iam/customer suites (otp-rate-limit, dev-otp-bypass, full-onboarding-flow, google-integration, customer-routes) = **28 passed / 1 skipped / 0 failed** — no regressions.

**All 7 boxes pass:** conftest NOT in diff (`endswith("_test")` guard L24 untouched); MSG91 monkeypatched + Google `AsyncMock` (zero real calls; Valkey=local DB15); every 4xx asserts non-empty `validation_message_id` (OB-BE-22/23 pin `auth.google.token_invalid` / `auth.google.email_unverified`); the 2 nullable-CHECK `assert True` cases are load-bearing (the flush fires the CHECK) — NOT green-washed; OB-BE-27/30/32/33/34 GENUINELY pre-exist in `test_customer_routes.py` (L382/503/581/601/681/705) — not double-counted.

**2 HONEST carry-forward gaps:** OB-BE-24 (Google flag-OFF 404 SKIPPED — OB-BE-22/23 mount the google router onto the shared `app.main.app` in-process so flag-OFF can't isolate; clear message; covered at app-factory level via `FEATURE_GOOGLE_AUTH_ENABLED=False`, config.py:305. True test needs a fresh ASGI app per test). OB-BE-38 (DPDP consent — grep confirms ZERO `consent`/`dpdp` columns in V1 customer schema; filed as SPEC gap in writer `deferred_coverage.md`; not invented).

**Process note:** PR #391 base was `develop` (founder's gate, wrong target). Squash content already on integration (`git diff integration backend`=empty); posted APPROVE + closed #391 (GitHub refused retarget: "no new commits"). Board commit pushed from a worktree (`HEAD:refs/heads/...integration`) because the master-tree git guard blocks branch moves.

**`qa-wave-2 (auth)` SUPERSEDED by `qa-onboarding`** (founder this session) — auth cases fold in; 2 HIGH FE reds (W2-FE-1/2) → Wave B. Do NOT cut `feature/qa-wave-2/*`.

**Waves B + C PENDING** — hard-dep A→B→C. Wave B needs the onboarding-`onSubmit` PRODUCT fix (component is a `setTimeout` mock that never calls `patchProfile()` → seller profile lost; owner `meesell-angular-component-builder` via memo to frontend-coordinator). Wave C resume flow (OB-E2E-03) only reachable after that fix lands.
