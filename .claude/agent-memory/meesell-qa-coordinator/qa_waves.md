# QA Waves — history & exit criteria

One entry per QA wave: feature slugs covered, the coverage target set per
specialist, what was actually achieved, and whether the exit criteria were met.
Append a new section at the top after each wave.

## Onboarding Wave C — Playwright E2E (two-phase) — 2026-06-22 — MERGED TO INTEGRATION

**Session:** `mesell-qa-onboarding-e2e-session-1` (coordinator GATE).
**PR #411** `feature/qa-onboarding/e2e` (`1a13128`) → `feature/qa-onboarding/integration` (`7e86054`).
**Verdict:** APPROVE (8/8) → squash-merged → integration tip **`e5a44a3`** (was `7e86054`). Branch preserved. `integration → develop` is the FOUNDER's gate — NOT touched. **ALL THREE qa-onboarding lanes now coexist in integration** (backend `aa4345d`, frontend #407 `7e86054`, e2e #411 `e5a44a3`).

**Coverage:** OB-E2E-01..08, 11 passed / 3 test.fixme / 0 failed, stable ×2 (writer's run). All 8 IDs covered (01/03 folded into one persist+resume flow; 02/04 folded into one wrong-OTP→resume flow to stay under the OTP-send budget). New page objects `auth.page.ts` + `onboarding.page.ts`; new fixtures `rate-limit.ts` + `global-setup.ts`; extended `fixtures/auth.ts` + `flows/onboarding.spec.ts` + `flows/logout-guard.spec.ts`.

**OB-E2E-03 = the #399 data-loss regression guard (CONFIRMED not assertion-free):** asserts `expect((await patch).status()).toBe(200)` on `PATCH /seller-profile` AND, after `clearCookies()` + re-login the SAME user, `waitForURL(/\/dashboard/)` + `expect(page.url()).not.toMatch(/\/onboarding/)` + dashboard heading visible. Ground-truthed against integration SOURCE: `onboarding.component.ts` L314 genuinely `this.sellerProfile.patchProfile(payload).subscribe(...)` (NOT the old setTimeout mock).

**What the gate executed vs reviewed statically:** the live Playwright re-run was NOT performed — the running dev stack was CONTAMINATED/inconsistent (slot-1 shell :4210 + mfe-auth :4211 + mfe-onboarding :4216 up; other remotes on slot-0-style ports; NO backend reachable: :8000/health=404, :8010 down). Per the checklist's explicit allowance, fell back to RIGOROUS static review: full diff (clean, 9 files = 8 e2e + board, ZERO app source), every page-object/fixture/spec read line-by-line, and SOURCE ground-truthing of every selector + the persist fix against integration tip `7e86054`. All 5 selector claims verified present in source (onboarding-submit L224; Manufacturer/Packer Name+Pincode labels L176/188/194/206; "set this up later" `<a>` L239; patchProfile L314; onboarding-business-name = 0 occurrences/removed).

**Gate boxes (all PASS):** (1) writer pasted 11/3/0 ×2; gate static + source ground-truth (live re-run blocked, disclosed). (2) N/A backend DB guard. (3) no real external calls — dev OTP `000000`, no real Google/MSG91; GCS/Google are the `test.fixme` blockers. (4) coverage met — every GREEN flow asserts a VISIBLE outcome (URL/DOM/redirect/PATCH-200). (5) no assertion-free tests; 3 fixme carry real assertions in-body. (6) selectors LIVE-VERIFIED + source-ground-truthed; zero hardcoded ports (from `playwright.config.ts`); getByLabel/getByRole/getByTestId. (7) PR template complete. (8) board flipped IN REVIEW by the specialist (`f787541`) — discipline improvement.

**NO stale-base hazard:** merge-base(e2e, integration) == integration tip `7e86054` exactly → `git diff integration..e2e --name-status | grep '^D'` empty. Wave B frontend specs verified PRESERVED.

**3 test.fixme (honest, logged):** google-click (cross-origin GIS OAuth iframe, not drivable headless); export-download (mfe-export route-productId PRODUCT BUG, Wave-1 carry); image-precheck-result (local dev has no GCS creds → 502 before rembg). Each body keeps the real assertions.

**2 product bugs found LIVE (filed → frontend-coordinator, NOT swallowed):** (1) NEW — onboarding pincode NOT-NULL 500: form sends `null` for empty manufacturer/packer pincode but `seller_profile` columns are NOT NULL → 500 `NotNullViolationError`. Fix candidates: FE make pincode required and/or BE make columns nullable / 422-not-500 (Director deciding owner). (2) mfe-export route-productId placeholder (Wave-1 carry, still blocking export-download). Tests fill valid pincodes so they pass.
## Wave 3 — catalog vertical (backend + frontend EXECUTED + MERGED to integration) — 2026-06-22

**Session:** `mesell-qa-wave-3-coord-session-1` (merge-gate execution — HYBRID step 3, both lanes).
**Specialists:** `meesell-backend-test-writer` (#396), `meesell-frontend-test-writer` (#394). E2E lane NOT yet dispatched.

**Verdict: BOTH PASS.** Backend squash `edb875f`, frontend squash `4571048`, both into `feature/qa-wave-3/integration`. Backend-test-writer memory scribed (PR #400 `804d317`, sanctioned write-protection workaround). Board published to develop (PR #401 `4ea1974`).

**Backend (#396) — re-ran independently, 59 passed / 0 failed:**
- Covered the largest TRUE backend gap (Live Preview W3-BE-1/2/3/5), the P1.11 export-ZIP carry-forward (genuinely un-skipped, asserts member names against the REAL `_write_xlsx(XlsxRowSpec)`/`_package_images_zip()` signatures), PIL boundaries against the REAL `_check_*` functions, and an asserting watermark eval ≥85%.
- The 2 broader-suite failures (`test_flag_gate.py`) = Valkey-6381 refused locally — proven pre-existing by being byte-identical at the integration base + NOT in the PR diff. Disclose, don't reject.

**Frontend (#394) — re-ran full `ng test` (total 1697), all 5 authored files GREEN:**
- The 73 reds are ALL pre-existing W2-FE carry-forward (verified: none in the catalog vertical, none touched by the diff). The 73↔78 run-to-run jitter is the known flaky refresh.interceptor/auth-write unhandled-rejection race.
- W3-FE-2 (service) is the only one with a real HTTP boundary (`HttpTestingController` + `verify()`); the component specs (FE-1/3/4/5/8) use the pure-function-mirror pattern (see coordinator_patterns).

**MERGE-MECHANICS LESSON (important, reusable):** the backend branch's diff vs the integration base showed CONTAMINATION (infra-builder MEMORY.md, STATUS_INFRA.md, +4/+23) — but it was NOT scope creep. The integration branch was created at an OLD develop tip (`6a02669`); develop had since advanced (`3c63b55`) with infra housekeeping PRs #388/#389/#390. The backend branch was cut off the NEWER develop, so those already-merged develop commits appeared as net-new vs the stale integration base. **FIX: fast-forward `integration` to current develop BEFORE squash-merging the lanes** (verified `git merge-base --is-ancestor integration develop` first → clean ff). After the refresh, the backend net-new was exactly the 7 test-lane files. ALWAYS check whether a "contaminating" file is identical to develop before rejecting — it's usually a stale integration base, not specialist misbehaviour.

**Exit criteria MET** for backend + frontend lanes. Deferred/gated: W3-BE-11 (cost ceiling, no founder number), W3-FE-6 + W3-E2-3 (mfe-export productId fix not on develop), W3-E2-5 (GCS env), and the entire W3-E2 e2e lane (not dispatched). For the founder: `integration → develop` (FOUNDER's gate) is READY and currently contains BOTH backend + frontend lanes; the e2e lane is a future dispatch.

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


## QA Wave 3 (catalog vertical) — E2E lane (PR #409) — gate session mesell-qa-wave-3-e2e-session-1
- VERDICT: PASS -> squash-merged into `feature/qa-wave-3/integration` `c382f84` (was `4571048`; branch preserved `8128b68`).
- SCAFFOLD lane (founder-approved): W3-E2-1 codified + honestly skip-gated; W3-E2-2/4/6 documented `test.fixme` with exact
  inline un-fixme conditions; W3-E2-3 un-fixme condition documented; W3-E2-5 fixme (GCS).
- Gate re-ran `npx playwright test --config e2e/playwright.config.ts --list` = 16 tests / 13 files, parse+typecheck clean.
  Full live run NOT required (env blocks real + documented + founder-approved). tsc spot-check: zero errors in the spec
  files themselves (only `process`/`node:fs` lib-resolution noise from an ad-hoc tsc invocation, not project tsconfig).
- WAVE 3 NOW FULLY ASSEMBLED: backend `edb875f` + frontend `4571048` + e2e `c382f84` coexist in integration. Ready for
  the FOUNDER's integration->develop gate.
- STALE-BASE HAZARD (2nd time, after Wave-2 e2e): the e2e branch's merge-base with integration (develop `3c63b55`)
  pre-dated the #396/#394 lane merges -> naive squash would DELETE 4 BE + 4 FE lane files. Reconcile = merge integration
  INTO the e2e branch first (zero conflicts) -> clean-additive squash, ZERO deletions.
- NON-SCOPE-CREEP confirmation: `dead_route_guard.mjs` + `ci.yml` in the diff are develop #403 (already on develop),
  present only via the stale base — NOT authored by the e2e writer. Always check provenance before flagging scope creep.
- FOUNDER NOTE captured on the board: integration->develop diff shows mfe-export/auth SOURCE files as changed, but they
  are byte-identical to the merge-base on integration (QA never touched them) — they differ only because develop advanced
  (#398 mfe-export + #406 auth). A 3-way merge-commit reconciles cleanly; QA contribution stays tests-only.
- 6 inter-lead requests logged (FE: catalog-list delete+testids; FE: mfe-pricing apply+testids; FE: Live Preview page
  reintroduction; infra/backend: Gemini-dev OR no-spend fixture-product seam; FE: PR #398 to develop; infra: lockfile
  @playwright/test@1.52.0).

## qa-image-ai Wave A backend gate (PR #431) — 2026-06-22 — REJECTED (one file)

**Session:** mesell-qa-wave-image-ai-backend-session-1 (gate). **Plan:** docs/testing/IMAGE_AI_QA_WAVE_PLAN.md.
**Branch:** feature/qa-image-ai/backend (8ff7021) -> feature/qa-image-ai/integration (stale base 3c63b55, ancestor of develop).

**Real lane delta** (`git diff origin/develop...backend`): exactly 7 Wave A test files, +1657/-32.
(PR-vs-base showed 67 files / +5793 = already-on-develop qa-onboarding history the integration branch hadn't absorbed.)

**RAN vs `meesell_test`** (full CI env replicated; PYTEST_RUN_SLOW=1; local pg :5432 meesell_test + valkey :6379):
- 6 of 7 files TOGETHER = 38 passed / 1 skipped (skip = perf test honest `<20 events` guard).
- `test_route_integration.py` (IMG-BE-01/07/09/11) = 2 failed / 2 passed run as a unit, 3x deterministic.
  Each class PASSES alone. Failure = `_otp_client` closed-loop singleton -> rate_limit_mw 500, NOT a route
  assertion. File is `@pytest.mark.integration` -> CI Gate-4 (`pytest -m integration`, one process) would red.

**Content verification (all GREEN):** IA-RED-1 genuinely fixed (perf reads event_type="ai.call"/cost_inr/occurred_at +
asserts <=Rs0.05; revert-check confirms); AI-BE-13 producer contract real (captures live cost_tracker.record); zero
real Gemini/GCS (adapter seam); no assertion-free tests; IMG-BE-07=502; IA-RED-2 TestStubStateGuards locks stub
(0/30) VALID NOW + TestRunnerAggregationLogic scorer-independent.

**Verdict:** REJECT scoped to test_route_integration.py fixture. Re-dispatch backend writer: reuse the loop-bound
`_otp_client` client fixture from `tests/integration/conftest.py`; rerun the file as a UNIT -> 4/4. develop UNTOUCHED,
branch NOT deleted, PR left open + verdict commented.

**Owed/owned:** IA-RED-2 stub-guard retirement (memo -> ai-coordinator); fast-forward integration to develop's tip on re-do.
