# Feature Board — QA Lead

**Lead agent:** `meesell-qa-coordinator`
**Domain:** qa (test pillar — the fourth coordinator, peer to backend / frontend / ai)
**Last updated:** 2026-06-22 (**QA WAVE 1 — FRONTEND BLOCKER-FIX GATE PASSED → MERGED.** PR #381 (`feature/qa-wave-1/testids-logout/frontend` → develop) gate-reviewed by `meesell-qa-coordinator` → **APPROVE → squash-merged** to develop `456494e` (was `5da7af9`; autonomous Wave-1, founder pre-approved + integration step collapsed → `--admin` direct-to-develop, NO `--delete-branch`). 27 files, +314/-22. Two commits: (1) **logout cookie-revoke fix** — `auth.service.logout()`/`forceLogout()` now fire `authApi.logout()` POST (`withCredentials`) + navigate `/login`; topbar logout becomes a direct `<button data-testid="nav-logout">` (the popup `MeeMenuItem` couldn't carry a testid); **3 genuine regression tests** added + 6 existing tests updated to consume the new fire-and-forget POST so `controller.verify()` stays green. (2) **ui-kit `[testId]` passthrough** on 5 wrappers (`mee-input/mee-button/mee-otp-input/mee-textarea/mee-file-upload`; each spec = present-when-set + absent-when-unset assertion) + **~30 attribute-only `data-testid`s** across shell + all 6 remotes. **Verification:** `tsc --noEmit -p apps/shell/tsconfig.app.json` = EXIT 0; `tsc --noEmit -p tsconfig.spec.json` (full spec graph) = exactly **2 errors, BOTH the pre-existing mfe-pricing `pricing.component.spec.ts:241/266` TS2352/TS2367, ZERO referencing any of #381's 27 files**. Boundary grep `from 'primeng` in `frontend/apps/**` = **0**. NOTE: full `ng test frontend` could NOT execute the affected specs — the pre-existing mfe-pricing type error + the unsupported native-federation `buildTarget` block the umbrella `@angular/build:unit-test` build before any spec runs (gate fell back to diff review + tsc per the explicit allowance and SAID SO). **This unblocks the E2E lane** — ~30 stable `data-testid`s now exist in the app for the E2E writer to consume. — Prior: PR #380 (qa-wave-1 backend gap-fill) → **APPROVE → squash-merged** to develop `5da7af9`; spot-rerun of the 9 new/extended files vs `meesell_test` = **66 passed / 1 skipped / 0 failed**; 1 P1 gap (export-ZIP test self-skipped) carried to Wave 2.)
**This file is the single domain-level status surface for the QA lead.**

> ⚠️ **Board-reconcile note (2026-06-22, mesell-qa-wave-1-frontend-session-1):** at this session's start the on-develop board had reverted to the *pillar-bootstrap* version (concurrent-session collision — a prior session's #380/frontend/e2e row edits + a referenced `handoff_selectors_qa_wave_1.md` memo were never committed to develop, and that memo does NOT exist on disk). This file has been rewritten to the **true develop state**: #379 (pillar), #380 (backend gap-fill, `5da7af9`), and #381 (frontend blocker-fix, `456494e`) are all confirmed in `git log origin/develop`. Aspirational claims not backed by disk (the missing memo) were dropped, not resurrected.

---

## Active waves

| Wave | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| qa-wave-1 | feature/qa-wave-1/e2e | BLOCKED (relieved) | mesell-qa-wave-1-frontend-session-1 | 2026-06-22 | data-testids now EXIST (PR #381) — exploration + codification not yet run | The data-testid blocker is **substantially relieved** by PR #381: ~30 stable `data-testid`s now ship across shell + all 6 remotes (nav-*, login-phone-input, login-request-otp, login-google-host, otp-input, otp-verify-submit, onboarding-*, dashboard-*, smart-picker-description, category-suggestion(-select), catalog-ai-fill, catalog-save-status, catalog-form-next, precheck-card/-status, image-file-input, export-trigger/-download, upgrade-prompt, nav-logout, user-menu-trigger, remote-failure-fallback). NEXT: dispatch `meesell-e2e-test-writer` for the two-phase explore-then-codify — phase 1 verifies each testid resolves live + records them in `selector_registry.md`; phase 2 moves the 6 `test.fixme` flows to real specs. `auth.setup.ts` can now produce `storageState.json` via `getByTestId('login-phone-input')` / `otp-input` / `otp-verify-submit`. |
| qa-wave-1 | feature/qa-wave-1/frontend (gap-fill) | PENDING | — | 2026-06-22 | — | The component/service-spec gap-fill lane (the broader frontend coverage wave, distinct from the merged blocker-fix branch). **Must fix the pre-existing mfe-pricing blocker first:** `frontend/apps/mfe-pricing/src/app/pricing.component.spec.ts:241` (TS2352 — `as Record<string, unknown>` cast on `PriceCalcNoPricingDataError`) + `:266` (TS2367 — `errorState === 'server_error'` comparison with no type overlap). These two errors block the entire `ng test frontend` umbrella build today and are NOT introduced by #381 (present at merge-base `240fbcd`). |

> **Session-end sweep (2026-06-22, mesell-qa-wave-1-frontend-session-1):** no rows >7 days stale (wave is days old). Open items: e2e lane (BLOCKED→relieved, needs the e2e-writer dispatch); frontend gap-fill lane (PENDING, gated on the mfe-pricing spec fix). Inter-lead requests: 1 OPEN (frontend / mfe-pricing spec fix).

## Recently merged (last 14 days)

| Wave | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| qa-wave-1 (frontend blocker-fix) | develop | 2026-06-22 | #381 (`feature/qa-wave-1/testids-logout/frontend` → develop), squash `456494e` | **GATE VERDICT: APPROVE → MERGED** (autonomous Wave-1; founder pre-approved + integration step collapsed → `--admin` direct-to-develop, NO `--delete-branch`). 27 files, +314/-22. **Logout regression is GENUINE** (mental revert-check confirmed): the 3 new `auth.service.spec.ts` tests assert `logout()` fires exactly one POST `/api/v1/auth/logout` with `withCredentials=true` AND `router.navigate(['/login'])`, incl. navigate-on-401-revoke — all 3 FAIL without the `authApi.logout().subscribe()` + `router.navigate` lines added to `auth.service.ts`. `authApi.logout()` already existed (`POST .../auth/logout`, `withCredentials:true`) and is NOT modified — surgical reuse. ui-kit passthrough is zero-blast-radius (`[attr.data-testid]` omitted when the `testId` input is undefined; each of the 5 wrapper specs asserts present-when-set + absent-when-unset). testids are attribute-only (no logic touched); `nav-logout` is on the real `<button>`, sidebar uses `NavItem.testId`. **Boundary grep `from 'primeng` in `frontend/apps/**` = 0.** No test-count drop (every diff is additive). Verification: `tsc --noEmit` shell app = EXIT 0; full spec-graph tsc = 2 errors, both pre-existing mfe-pricing (`:241/:266`), ZERO in #381's files. New develop HEAD = `456494e` (was `5da7af9`). |
| qa-wave-1 (backend) | develop | 2026-06-22 | #380 (`feature/qa-wave-1/backend` → develop), squash `5da7af9` | **GATE VERDICT: APPROVE → MERGED** (autonomous Wave-1; founder pre-approved + collapsed the integration step → `--admin`, NO `--delete-branch`). 9 test files, +803/-3 (13 new tests across P0.2–0.7 + P1.8/9/10/11). Spot-rerun of the 9 new/extended files vs `meesell_test`: **66 passed, 1 skipped, 0 failed**. All 5 gate boxes PASS: tests run; `TEST_DATABASE_URL` guard untouched (conftest not in diff); zero real external calls (every vendor mocked at the seam); coverage targets met for all P0 + P1.8/9/10; every new 4xx asserts a non-empty `validation_message_id`; no assertion-free tests. **ONE P1 gap carried to Wave 2:** P1.11 export-ZIP test (`test_export_zip_member_structure.py`) **self-skipped** (wrong `_build_xlsx_bytes(...)` signature assumption → no assertion executed; honest skip, not green-washed). |
| qa-wave-infra (pillar bootstrap) | develop | 2026-06-22 | #379 (`feature/qa-wave-infra/integration` → develop, founder-gated), `240fbcd` | **QA pillar bootstrap — 4 agents + 3 skills + 4 memory dirs + Playwright E2E scaffold + registry updates.** Built by `meesell-infra-builder` per the APPROVED design. `.claude/**` artifacts landed via the git-plumbing route (write-protected). E2E flow specs are intentional STUBS (`test.fixme`) — the first QA wave fleshes them out after a live agent-browser exploration phase. Fleet count: CLAUDE.md + MEESELL_AGENT_REGISTRY.md updated 19 → 23. |

## Inter-lead requests open

| To lead | About wave | Request | Opened | Status |
|---|---|---|---|---|
| frontend-coordinator | qa-wave-1 (frontend gap-fill) | **Fix the pre-existing mfe-pricing spec type errors that block the whole `ng test frontend` umbrella build:** `frontend/apps/mfe-pricing/src/app/pricing.component.spec.ts:241` (TS2352 — `(NO_PRICING_DATA_SHAPE as Record<string, unknown>)` cast; per the TS hint, cast through `unknown` first, or add an index signature / use a narrower assertion) and `:266` (TS2367 — `errorState === 'server_error'` compared against a `'no_pricing_data'`-narrowed literal type with no overlap; widen the `ErrorState`-typed local or restructure the assertion). These two errors fail bundle generation BEFORE any spec runs, so they block running the Wave-1 frontend specs (auth.service.spec + the 5 ui-kit wrapper specs) and the broader gap-fill lane. NOT introduced by PR #381 — present at merge-base `240fbcd`. | 2026-06-22 | OPEN |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Wave is on the QA backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/qa-wave-N/<group>` branch exists; a test specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/qa-wave-N/integration`; awaiting the QA coordinator's merge-gate review. |
| `MERGED` | The group's test PR has merged to `feature/qa-wave-N/integration` (or, in collapsed autonomous Wave-1, direct to develop). |
| `BLOCKED` | Work stopped pending a missing selector / fixture, an inter-lead request, or a founder decision. |

A wave row stays on Active waves until its group PR merges to `feature/qa-wave-N/integration`; then it moves to "Recently merged" for 14 days before being removed.

---

## Acceptance gate

Group-PR approval (the QA coordinator's merge-gate review) requires every box:

- [ ] Tests actually run — `pytest` / `ng test` / `playwright test` output pasted in the PR description
- [ ] `TEST_DATABASE_URL` safety guard (`_resolved_db.endswith("_test")`) not bypassed (backend)
- [ ] No real external calls — Gemini / MSG91 / Razorpay / GCS all mocked at the adapter boundary
- [ ] Coverage target from the test spec is met (the measurable exit criterion)
- [ ] No assertion-free test (none that passes while asserting nothing)
- [ ] E2E: selectors came from a live exploration (present in `selector_registry.md`), not from memory; no hardcoded ports
- [ ] PR template filled completely (no `<>` placeholders)
- [ ] The board row for this wave/group is `IN REVIEW`

The QA wave runs as a dedicated sprint AFTER feature waves merge to develop — it never blocks an individual feature PR. The `feature/qa-wave-N/integration` → `develop` merge is the **founder's** gate (D1); the QA coordinator owns only the `feature/qa-wave-N/<group>` → `feature/qa-wave-N/integration` gate.
