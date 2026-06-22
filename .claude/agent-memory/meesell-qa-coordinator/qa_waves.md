# QA Waves — history & exit criteria

One entry per QA wave: feature slugs covered, the coverage target set per
specialist, what was actually achieved, and whether the exit criteria were met.
Append a new section at the top after each wave.
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
