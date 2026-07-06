# QA Waves — history & exit criteria

One entry per QA wave: feature slugs covered, the coverage target set per
specialist, what was actually achieved, and whether the exit criteria were met.
Append a new section at the top after each wave.

## qa-pricing E2E lane completion — POST-HOC MERGE-GATE PASS on `1794da3` (direct-to-develop) — 2026-07-06 (mesell-qa-wave-pricing-coord-session-2)

**Feature slugs:** Price Calculator (apply-price flow) + Fast Catalog Form (catalog-list delete). **Specialist:** `meesell-e2e-test-writer` (opus). **Specs:** SPEC A `docs/plans/qa/spec_qa-pricing-e2e-lane-completion.md` + SPEC B group R `docs/plans/qa/spec_qa-e2e-defixme-scaffolds.md`.

**Pipeline flow (Director-sanctioned):** the writer executed BOTH specs and pushed `1794da3` DIRECTLY to develop (no lane PR / no integration branch — the same direct-to-develop pipeline the deploy work used). The QA lead ran the gate **POST-HOC** on the landed commit; a post-hoc gate can still REJECT → corrective spec. **VERDICT = PASS** (with the overlap ruling applied).

**Scope — 6 files, tests-only (+256/-79), ZERO source/board/status/memory/ci, ZERO deletions:** `flows/pricing.spec.ts` (PQE-E2E-04 + 04b), `flows/price-apply-export.spec.ts` (W3-E2-6 de-fixme), `flows/catalog-edit-delete.spec.ts` (W3-E2-4 de-fixme), `flows/category-picker.spec.ts` (CAT-E2E-03/07 fixme-reason refresh), `page-objects/pricing.page.ts` (apply trio + `applyPrice()`), `page-objects/catalog.page.ts` (catalog-list row/delete helpers).

**Coverage target (SPEC A §4) — MET:** PQE-E2E-04 authored (apply→export URL + Generate visible); PQE-E2E-04b authored (apply POST 500 → apply-error, stays on /pricing); W3-E2-6 GREEN (calc→apply→export-page-reachable — one of §4's two accepted exit states); zero remaining `test.fixme` in `price-apply-export.spec.ts`; zero hardcoded ports; every test asserts a DOM/URL visible outcome; `--list` parses clean. **SPEC B group R — MET:** W3-E2-4 de-fixme'd; W3-E2-6 via SPEC A; CAT-E2E-03/07 handled (kept fixme + testid memo — the spec-sanctioned path when live-verify is env-blocked).

**Gate evidence (independently re-verified, NOT trusting the report):** `test.fixme` 9→7 (grep of `origin/develop`); `--list` 31 tests / 16 files reconciles (23 active + 7 fixme in 15 flow specs + 1 auth.setup test); EVERY testid grep-confirmed present in `origin/develop` source — `catalog-list.component.ts` L310/326/327/370/378/391/399, `pricing.component.ts` L682/705/718 (native), `ExportPage.generateButton` L19; DOM interaction rules DOM-accurate (apply-btn = native `<button>` `[disabled]`-until-`breakdown()` → click DIRECT; delete controls = `<span data-testid>` wrapping `mee-button` → `.locator('button')`); PQE-E2E-04b sets the route-stub AFTER a real calc (no green-wash); no hardcoded ports; no assertion-free tests; no real vendor calls.

**Live pass/fail run OWED (disclosed, NOT green-washed):** the writer reported NO full pass/fail run — deployed product-creation is DOWN (`/suggest` empty + unseeded browse) and the local 8GB box is swap-blocked. Accepted under the standing e2e gate allowance: `--list` clean + source-ground-truth + LIVE-verify of the STATIC apply controls on the deployed build. The commit message discloses this; the specs do NOT claim a pass.

**OVERLAP RULING = KEEP (my call as gate owner).** W3-E2-6 is functionally identical to PQE-E2E-04 (same steps + assertions). SPEC A §3.3 leaned collapse ("do not keep a duplicate"), BUT: (a) SPEC A §4's measurable exit criterion — the one "the gate will check" — explicitly lists **"W3-E2-6 GREEN"** as an accepted state (option 1 of 2), and the writer delivered exactly that; (b) `price-apply-export.spec.ts` is a NAMED e2e artifact in the founder-facing `V1_CONFORMANCE_REPORT.md` (mapped to BOTH Feature 7 Price Calculator AND Feature 9 XLSX Export) — deleting it would orphan those refs and force a wider founder-doc edit; (c) the duplication cost is not yet incurred (E2E isn't wired into CI + both are env-blocked from running today); (d) W3-E2-6 is the natural home to extend into the full download chain when PQE-E2E-05/fake-gcs lands. So KEEP — no collapse edit, no further develop mutation for the ruling.

**Inter-lead moves:** CLOSED 2 OPEN rows (frontend W3-E2-4 catalog-list delete+testids → resolved by #425; frontend W3-E2-6 mfe-pricing apply+testids → resolved by #439). OPENED 1 (frontend `smart-picker-browse-fallback` / `smart-picker-empty` / `smart-picker-empty-browse` for CAT-E2E-03/07). Isolated-writer learnings scribed into its 3 knowledge files (selector_registry / federation_quirks / flow_status) + its MEMORY index.

**Reusable lessons (→ coordinator_patterns):** (1) when a spec's measurable EXIT criterion lists two acceptable outcomes (keep-green OR collapse), the gate cannot reject the writer for choosing the keep-green one, even if a prose §3.3 note leaned the other way — the exit criterion governs. (2) A test FILE can be load-bearing beyond its assertions: check `V1_CONFORMANCE_REPORT.md` (and the wave plan) for a by-path reference BEFORE ruling to delete/collapse a spec file. (3) Post-hoc direct-to-develop gate: no PR → no IN-REVIEW board discipline applies; the gate scribes the board straight to MERGED-on-develop.

## Wave 3 — catalog vertical — `integration → develop` MERGED (FOUNDER-DIRECTED) — 2026-06-22 (mesell-qa-wave-3-coord-session-2)

**The founder directed "merge gate PR #460 whenever ready."** The QA lead ran the FULL merge-gate FIRST, then merged on that explicit instruction. PR **#460** (`feature/qa-wave-3/integration → develop`) → **APPROVE → MERGED** as a true **merge-commit `e7470bf`** (`--admin`; develop `17171d1` → `e7470bf` → board `9b89f19`). Branch `feature/qa-wave-3/integration` (`ab1aa6d`) RETAINED. Board-tracker PR **#461 CLOSED as moot**.

**Normally the FOUNDER's D1 gate** (PR title literally `[FOUNDER GATE — DO NOT MERGE BY LEAD]`). The lead merged ONLY on the explicit founder directive for this PR. Standing D1 unchanged.

**Scope: TESTS-ONLY — 12 files (+2599/-59), ZERO source/board/status/memory/ci, ZERO deletions.** 4 net-new backend pytest + 1 upgraded `test_export_zip_member_structure.py` + 1 eval artifact `eval_results.json` (trivial 0.028→0.0278; `gemini_calls:0`) + 2 FE specs (`browse`, `live-listings`) + 4 e2e flows (`catalog-edit-delete`/`live-preview`/`price-apply-export`/`wizard-save`).

**GATE INDEPENDENTLY RE-RAN (decisive: tests written for qa-wave-3, develop advanced ~72 commits since — confirm GREEN vs CURRENT develop):**
- Backend = **59 passed / 0 failed / 0 skipped**. 50 DB-independent (unit+eval) + the 3 integration files RUN TOGETHER one-process (CI-Gate-4 style) = 9/0/0; happy + cross-tenant-404 + unauth-401 + autosave-reflect + export-ZIP ran for real (DB-infra `pytest.skip` did NOT fire → no green-wash).
- Frontend = **44 passed / 0 failed / 0 skipped** (standalone vitest 4.1.8). browse W3-FE-3a..i (20) + live-listings W3-FE-4a..i (24); W3-FE-8 unknown-key non-blank regression guard (negative assertion present).
- E2E = **29 specs / 16 files parse+typecheck CLEAN** (`playwright --list`). Founder-approved SCAFFOLD: `wizard-save` (W3-E2-1) live skip-gated (real UUID + autosave "Saved" TEXT + listed product; skips only on genuine env gaps); W3-E2-2/4/6 `test.fixme` with inline un-fixme conditions.
- CI checks on the head commit CONFIRMED GREEN: Gate 1-5 (incl. Gate 4 one-process) + all 8 FE matrix units (incl. mfe-catalog).

**8 gate boxes all PASS:** tests-run (re-reproduced + CI-corroborated); `TEST_DATABASE_URL` `_test` guard intact (not in diff); zero real Gemini/MSG91/Razorpay/GCS (dummy env + adapter mocks); coverage met; no assertion-free tests; E2E selectors live-verified + honest skip-gating + zero hardcoded ports; PR template complete; tests-only.

**KEY MECHANICS LESSONS (reusable — see coordinator_patterns):** (1) the conftest `_provision_test_schema` autouse fixture AUTO-reprovisions `meesell_test` from the BRANCH's own migrations when `TEST_DATABASE_URL` is set — resolved a DB-vs-branch alembic mismatch (`meesell_test` stamped at `480c10b0219f`, NOT in this branch's history; fixture dropped + `upgrade head` to `e9415bdcae20`) with zero manual steps. (2) pure-function-mirror / imported-model-fn FE specs (no Angular/TestBed/PrimeNG imports) run via STANDALONE `vitest run <files>` when the native-federation `@angular/build:unit-test` builder refuses to scope `--include` (every narrow include form = "No tests found"; only the broad `**/*.spec.ts` walks them). (3) develop advancing 72 commits past the rebase point did NOT block merge — `mergeStateStatus: CLEAN` because the 3 develop advances (#480/#481/#482) and the 3 QA-lane commits touch disjoint files; merge-commit reconciled with zero conflicts. (4) `git -C <worktree> commit` works; `cd <worktree> && git commit` tripped the master-tree-git guard's cwd heuristic — use `-C`.

## qa-auth-contract salvage wave — `integration → develop` PR OPENED for the FOUNDER (2026-06-22, mesell-qa-wave-2-coord-session-1)

**The salvage wave is fully assembled and handed to the founder's gate.** PR **#445** (`feature/qa-auth-contract/integration` → `develop`) is OPEN — NOT merged (D1: integration→develop is the founder's). Title prefixed `[FOUNDER GATE] … DO NOT MERGE until founder review`.

**Refresh outcome:** merged `origin/develop` INTO integration (merge-commit `a2eee1d`) — **ZERO conflicts**; the on-disk board collision flagged at the prior e2e gate did NOT recur (origin/develop's board merged additively with the integration board via ort). Integration tip went `4aa12da` → `f17814c` (the board-reconcile commit on top of the merge). Pushed clean.

**Post-refresh diff `git diff origin/develop...HEAD` = exactly 17 tests-only files + the board (+1596/-67), ZERO app source, ZERO deletions** — 8 backend integration tests, 3 frontend `*.spec.ts`, 6 e2e harness/flow files. Verified twice (`grep -vE` for any non-test/non-board path = NONE).

**15 auth behaviors (all gate-reviewed + independently re-run at their lane gates):** backend 9 (PR #440, `8adbd57`), frontend 3 (PR #438, `3caa18d`), e2e 3 (PR #441, `4aa12da`). #427's clear-cookie-on-401-refresh fix (`e60cedd`) already landed separately on develop — NOT part of this PR.

**Board RECONCILED from origin/develop (NOT clobbered):** took develop's CURRENT board as base (concurrent qa-pricing/qa-image-ai/qa-catalog rows ALL preserved); flipped the backend (PR #440) + e2e (PR #441) rows PLANNED→MERGED-to-integration (frontend #438 was already MERGED on develop's board); added the 3 carry-forwards as Inter-lead requests; added the LAND-prep session-end sweep. This DISCHARGES the "BOARD-RECONCILE OWED" item from the prior e2e gate entry.

**3 carry-forwards filed (Inter-lead requests):** INFRA-1 (manifest port-MAPPING vs running stack + playwright default `REMOTE_PORTS` encode declaration-order = the no-op-by-default trap → align to alphabetical or document the override); INFRA-2 (stale deployed mfe-onboarding pre-#399 bundle → rebuild dev remotes); GIS-seam (a `DEV_GOOGLE_BYPASS` dev-gated google verify seam to un-fixme E2E-AUTH-06 success → auth-builder/ai).

**Worktree cleanup:** the LAND worktree is removed post-push; master tree untouched (all work in worktrees).

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

## qa-auth-contract salvage wave — CLOSED on develop
qa-auth-contract salvage wave CLOSED on develop (#445 `e83e6f2`); follow-ons #480 google-seam (`b10cc77`) + #483 google-success E2E (`17171d1`) landed. All gate-reviewed + independently re-run.

## WAVE-B (2026-07-06, mesell-qa-wave-pricing-coord-session-1) — PR #435 retrospective gate + 2 specs
**Part 1 — PR #435 (qa-catalog Wave-A backend re-do): retrospective merge-gate = PASS (already merged).**
The Wave-B task asked me to merge/reject PR #435, but its premise was STALE: #435 was ALREADY MERGED
(integration squash `c8f42554`, 2026-06-22) and the whole qa-catalog wave reached develop via PR #470
merge-commit `494c7838` the same day. I could not (and must not) re-merge; instead I ran a retrospective
gate: (1) `c8f42554` is an ancestor of `origin/develop` (`9ebc0d9`); (2) both original reject reasons are
cleared on develop in source — all 6 gap-fill files consume the loop-bound `catalog_route_client`/
`category_route_client` conftest fixtures (zero `_make_client`/`lifespan_context`), and CAT-BE-19
(`test_field_enum_unknown_category_404`) is a hard `assert resp.status_code == 404` (masking skip gone);
(3) re-ran the 6 previously-failing files TOGETHER in one process vs `meesell_test` (CI dummy env, local
PG:5432 / Valkey:6379, full §5.D secrets) = **24 passed / 7 skipped / 0 FAILED** — the 7 skips are all the
honest seed-conditional CAT-BE-11/13/14/16/18/20/21, the loop-affinity `Event loop is closed` 500 is GONE.
Verdict recorded on the board + reported. LESSON: when a Wave task names a PR to gate, VERIFY its live
state first (`gh pr view … --json state,mergeCommit` + `git merge-base --is-ancestor <mergeCommit> origin/develop`)
— a stale board/founder snapshot can point you at an already-landed PR; the correct action is a retrospective
gate + a board reconcile, not a re-merge attempt.

**Part 2 — two specs authored (not implemented):**
- SPEC A `docs/plans/qa/spec_qa-pricing-e2e-lane-completion.md` — mfe-pricing testids are ALL present on
  develop `9ebc0d9` (10 testids incl. the SPEC-C apply trio `pricing-apply-btn`/`applied-status`/`apply-error`,
  L441-724); the "ZERO data-testid" board premise was STALE (they landed #439 + SPEC-C). Lane completion is
  an E2E-authoring task, not a frontend selector request: PQE-E2E-02/03 verify, NEW PQE-E2E-04 (apply-price
  204 → applied-status/navigate-to-export), W3-E2-6 un-fixme (calc→apply→export-page-reachable). Backend
  `POST /products/{id}/apply-price` exists (pricing/router.py L144).
- SPEC B `docs/plans/qa/spec_qa-e2e-defixme-scaffolds.md` — all 9 `test.fixme` re-verified @ `9ebc0d9`:
  2 already-resolved (W3-E2-4 catalog-edit-delete via #425 delete UI+testids; W3-E2-6 via #439), 2 frontend
  live-verify (CAT-E2E-03/07), 2 seed (CAT-E2E-05/06), 1 Gemini (CAT-E2E-06), 2 storage (PQE-E2E-05 export,
  image-precheck), 1 product-gap (W3-E2-2 live-preview retired #278 — escalate, not enablement).
  STORAGE DECISION = **fake-gcs-server** (GCS-JSON-API emulator + `STORAGE_EMULATOR_HOST`) NOT MinIO (adapter
  is `google.cloud.storage`, MinIO is S3 → would need an adapter rewrite) NOT a paid GCS bucket (spend +
  non-hermetic). GEMINI DECISION = **Playwright canned-JSON route-stub** of `POST /autofill` (hermetic, no
  spend, matches the existing /suggest stub; real-AI quality stays in the nightly `ai_eval` GEMINI_API_KEY_CI
  job). 4 OPEN QUESTIONs flagged non-blocking (OQ-1 fake-gcs signed-URL for export download; OQ-2 live-preview
  delete-vs-retain; OQ-3 seed full-tree vs pin+stub; OQ-4 CI container acceptance).
