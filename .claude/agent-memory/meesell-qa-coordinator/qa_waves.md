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
