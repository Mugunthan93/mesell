# Gate 5 Visual Review — Findings Log

**Session:** mesell-ui-review-session-1
**Date:** 2026-06-11
**Reviewer:** Founder (Mugunthan) — eyes are the gate
**Session scope:** All 11 V1 routes at 360px and 1280px + 3 federated remotes verification + fallback test

---

## Review Setup Status

| Service | Port | Status |
|---------|------|--------|
| Shell | :4200 | ✅ RUNNING |
| mfe-pricing remote | :4201 | ✅ RUNNING (remoteEntry.json 200) |
| mfe-export remote | :4202 | ✅ RUNNING (remoteEntry.json 200) |
| mfe-onboarding remote | :4203 | ✅ RUNNING (remoteEntry.json 200) |

All services verified live at session start (curl 200 on all remoteEntry.json). Review began 2026-06-11.

**Browser:** Safari (Responsive Design Mode) — Chrome not available on founder's machine (resource constraint).
**Note for master session:** target users are Android/Chrome; a Chrome-engine spot-check (e.g. on an actual Android phone hitting the dev server over LAN) is recommended before prod cutover, but is NOT a Gate 5 blocker.

---

## Route Inventory

| # | Route | Type | Serves From | Review Status |
|---|-------|------|-------------|---------------|
| 1 | `/` (landing) | Shell-local | features/landing | ⬜ PENDING |
| 2 | `/login` | Shell-local | features/auth | ⬜ PENDING |
| 3 | `/signup` | Shell-local | features/auth | ⬜ PENDING |
| 4 | `/otp-verify` | Shell-local | features/auth | ⬜ PENDING |
| 5 | `/dashboard` | Shell-local | features/dashboard | ⬜ PENDING |
| 6 | `/catalogs` | Shell-local | features/catalogs | ⬜ PENDING |
| 7 | `/catalogs/new` (smart-picker) | Shell-local | features/catalog-new | ⬜ PENDING |
| 8 | `/catalogs/:id/edit` | Shell-local | features/catalog-form | ⬜ PENDING |
| 9 | `/catalogs/:id/images` | Shell-local | features/images | ⬜ PENDING |
| 10 | `/catalogs/:id/preview` | Shell-local | features/preview | ⬜ PENDING |
| 11 | `/catalogs/:id/pricing` | **FEDERATED** → mfe-pricing (:4201) | apps/mfe-pricing | ⬜ PENDING |
| 12 | `/catalogs/:id/export` | **FEDERATED** → mfe-export (:4202) | apps/mfe-export | ⬜ PENDING |
| 13 | `/profile` | **FEDERATED** → mfe-onboarding (:4203) | apps/mfe-onboarding | ⬜ PENDING |
| 14 | `/onboarding` | **FEDERATED** → mfe-onboarding (:4203) | apps/mfe-onboarding | ⬜ PENDING |

---

## Severity Legend

| Code | Meaning |
|------|---------|
| P0 | Broken — route crashes, content invisible, layout unusable |
| P1 | Ugly — layout broken, overflow, contrast fail, responsive break |
| P2 | Polish — minor spacing, alignment, color, typo nit |

---

## Findings

<!-- Format per finding:
### F-NNN — [Route] @ [width]
- **Severity:** P0 / P1 / P2
- **Screenshot:** (filename if dropped in docs/ui-review/)
- **Description:** (founder's words verbatim)
- **Fix type:** styling-only (→ ui-styler) | logic/routing/federation (→ master session)
-->

### F-001 — Shell bootstrap @ ALL routes, ALL widths — BLANK WHITE SCREEN

> ## ✅ RESOLVED — PR #203 (squash `1ae5939`), 2026-06-13
> **Fix:** approach **(a)** barrel imports for `@mesell/ui-kit/*` (no subpath imports of the shared kit — `app.config.ts` + the 3 mfe-auth pages rewritten to import `provideMeeUi` / wrappers from the `@mesell/ui-kit` root barrel) + approach **(c)** **unshare `@primeuix/themes`** (added to `skip[]` in all 7 `federation.config.js`, so Aura bundles into the `_mesell_ui_kit.js` consumer chunk and is never resolved via the import map).
> **Verification (lead, on merged tip `1ae5939` = origin/develop):**
> - Real **headless-Chromium boot smoke: 6/6 routes PASS**, ZERO "Unable to resolve specifier"; `/login` renders the real mfe-auth form (not a 404). Screenshots: `docs/ui-review/f001-boot-{root,login,profile}-{360,1280}px.png`; harness: `docs/ui-review/f001-smoke.js`.
> - `grep -rn "@mesell/ui-kit/" apps libs --include='*.ts'` = **EMPTY** on origin/develop (no subpath imports remain).
> - All **7** `federation.config.js` carry `@primeuix/themes` + `@primeuix/themes/aura` in `skip[]` (F-001 comments inline).
> **Note:** F-001 is resolved (shell boots), but **Gate 5 visual review itself stays PAUSED** — see Gate Verdict below.

- **Severity:** **P0** (entire shell dead — no route renders)
- **Screenshot:** founder's Safari capture 2026-06-11 08:17 (console errors visible)
- **Description (founder):** "http://localhost:4200/ itself not showing."
- **Console errors (verbatim):**
  1. `Error: Unable to resolve specifier '@mesell/ui-kit/providers' imported from http://localhost:4200/chunk-37AVMFOC.js — es-module-shims.js:2211`
  2. `Unhandled Promise Rejection: Error: Unable to resolve specifier '@primeuix/themes/aura' imported from http://localhost:4200/_mesell_ui_kit.js`
- **Fix type:** **federation config / logic — MASTER SESSION** (out of scope for ui-styler per session brief; also touches Wave 2 conflict surfaces)

**Diagnosis (session investigation, 2026-06-11):**
- `src/app/app.config.ts:8` → `import { provideMeeUi } from '@mesell/ui-kit/providers'` (subpath import of a federation-shared package)
- `libs/ui-kit/theme.ts` → imports `@primeuix/themes/aura` (subpath import)
- Shell's `remoteEntry.json` shared list (164 entries) contains ONLY the root entries `@mesell/ui-kit`, `@mesell/core`, `@mesell/composites`, `@primeuix/themes` — **no subpath entries** for `/providers` or `/aura`. (Contrast: `primeng/*` subpaths ARE individually shared — `primeng/api`, `primeng/button`, etc.)
- Native Federation externalizes shared packages at build time → at runtime es-module-shims must resolve them via the import map → subpath keys missing → bootstrap throws → blank screen.
- Build gates pass because esbuild resolves the tsconfig wildcard path `@mesell/ui-kit/*` at compile time — this failure is **runtime-only, browser-only**.
- Introduced in SP0 itself: commit `e51761b` (PR #40, 2026-06-10) added the `providers` subpath import. The shell has likely never bootstrapped in a browser since federation init. SP1–SP3 gates were build/test/boundary gates, not browser-runtime gates.
- NOT Safari-specific: import-map resolution is browser-agnostic (es-module-shims shim path shown in trace).

**Candidate fix directions (for master session to evaluate — NOT executed here):**
  a. Re-export `provideMeeUi` from the ui-kit barrel (`libs/ui-kit/index.ts`) and import from `@mesell/ui-kit` root — removes the subpath import entirely (smallest change); same for re-exporting Aura usage internally inside the shared bundle... note theme.ts is INSIDE the ui-kit shared bundle, so its `@primeuix/themes/aura` import still needs (b) or bundling.
  b. Add explicit `sharedMappings`/shared entries for the subpaths in `federation.config.js` (shell + all 3 remote configs).
  c. Skip/unshare `@primeuix/themes` so Aura gets bundled into consumers (theme is shell-only per MASTER_PLAN §6.2 — may be acceptable).
- **Regression guard suggestion:** add a CI browser-boot smoke test (headless chromium loads `/login`, asserts non-empty body + zero console errors) — build-green ≠ boot-green.

---

## Fallback Test Results

| Remote | Kill & Reload | Fallback shown (not crash) | Restart & works |
|--------|---------------|---------------------------|-----------------|
| mfe-pricing (:4201) | ⬜ | ⬜ | ⬜ |
| mfe-export (:4202) | ⬜ | ⬜ | ⬜ |
| mfe-onboarding (:4203) | ⬜ | ⬜ | ⬜ |

---

## Gate Verdict

**UPDATE 2026-06-13 — F-001 RESOLVED (PR #203 / `1ae5939`); Gate 5 visual review remains ❌ PAUSED (0/14 routes reviewed).**

The original blocker is cleared: the shell now bootstraps in a real browser (headless-Chromium boot smoke 6/6 routes PASS, `/login` renders the real mfe-auth form). The route inventory above, however, is still **0/14 reviewed** — F-001 prevented any visual finding from being made, and the founder-eyes visual pass has not yet been re-run.

➡️ **Gate 5 is UNBLOCKED to schedule but NOT yet passed.** Schedule `mesell-ui-review-session-2` (scope = 6 remotes / 7 dev servers, ports 4200–4206) to actually walk the 14 routes at 360 px + 1280 px. Until that session runs and clears, Gate 5 stays open.

---

**Historical (superseded by the update above):**

❌ **FAIL — review BLOCKED at route 1 of 14 by F-001 (P0)**

The shell fails to bootstrap in the browser (blank white screen, all routes). Zero of the 14 routes could be visually reviewed at either width. The fallback test could not be run (the failure mode renders identically to a remote-load failure — except no RemoteFailureComponent appears because the shell itself never boots).

**Founder ruling (2026-06-11):** Pause Gate 5. Hand F-001 to the master session for proper dispatch. Gate 5 resumes in a follow-up session once the shell boots.

---

## Fix Batches Dispatched

| Batch | Branch | Routes covered | PR # | Status |
|-------|--------|---------------|------|--------|
| *(none — review blocked before any styling finding could be made)* | | | | |

---

## Handoff to Master Session

1. **F-001 (P0) — ✅ DONE (PR #203 / `1ae5939`, 2026-06-13).** Federation import-map subpath failure RESOLVED via approach (a) barrel imports for `@mesell/ui-kit/*` + (c) unshare `@primeuix/themes` across all 7 `federation.config.js`. Routed exactly as suggested: `meesell-frontend-coordinator` SPEC → `meesell-angular-service-builder` (HYBRID step 2) → lead merge-gate review (HYBRID step 3). Lead-verified: headless-Chromium 6/6 routes PASS, origin/develop subpath grep EMPTY. See the RESOLVED banner on the F-001 finding above.
2. **Process gap** — SP0–SP3 shipped with build/test/boundary gates only; none caught a shell that cannot boot. Recommend a browser-boot smoke gate (headless chromium, assert non-empty body + zero console errors on `/login`) added to the federation gate set before SP04/SP05 merge.
3. **Gate 5 re-run** — schedule a fresh `mesell-ui-review-session-2` after F-001 merges. All 4 dev-server services were verified healthy (this session's setup work is reusable: 4 terminals, ports 4200–4203, founder now has Safari Responsive Design Mode configured).
4. **Browser note** — founder's machine is Safari-only (no Chrome, resource constraint). Recommend Android-phone-over-LAN or headless Playwright for any Chrome-engine verification; not a Gate 5 blocker.
5. **Wave 2 merged on top of an unbootable shell (observed 2026-06-12)** — the federation manifest now lists 6 remotes: the original 3 plus `mfe-dashboard` (:4204), `mfe-catalog` (:4205), `mfe-auth` (:4206), with matching `start:*` scripts in package.json. Founder's 2026-06-12 browser check confirms: (a) F-001 still reproduces verbatim (`@mesell/ui-kit/providers` + `@primeuix/themes/aura` unresolvable → shell never bootstraps), and (b) the 3 new remotes' load failures are caught gracefully by `handleRemoteLoadError` (fallback wiring works). Consequence: **none of the 6 remotes — including all Wave 2 UI — has ever been seen rendering in a browser.** The F-001 fix dispatch and the browser-boot smoke gate (item 2) are now blocking ALL merged frontend work, not just the original 3 remotes. Escalate priority accordingly; review scope for `mesell-ui-review-session-2` grows to 6 remotes / 7 dev servers (ports 4200–4206).
6. **pnpm-workspace.yaml allowBuilds chore — ✅ LANDED via PR #203 (`1ae5939`, 2026-06-13).** The `allowBuilds` entries that carried literal pnpm placeholder text ("set this to true or false") — which made every `pnpm start:*` hard-fail with `ERR_PNPM_IGNORED_BUILDS` — were flipped to `true` (all five: @parcel/watcher, esbuild, lmdb, msgpackr-extract, nice-napi) and **committed** as part of the F-001 fix PR. No longer working-tree-only, so it can no longer be reverted by a `git restore`/regenerate. (Historical context below retained for the record.)
   - *Historical:* the placeholder version was committed in `7001b44`; founder fixed it in-tree 2026-06-11, it regenerated by 2026-06-12, and it was re-fixed and finally committed under #203.

---

### F-001 rebase guard (added 2026-06-13 — post-#203; CORRECTED 2026-06-13)

**Correction note:** an earlier version of this section claimed the four `feature/wave6-*/frontend` branches were the at-risk in-flight branches needing a rebase. That was factually wrong. A regression assessment found the truth below.

**The four `feature/wave6-*/frontend` branches are already merged and SAFE — no action needed.**

- `feature/wave6-dashboard/frontend` → merged via PR #153
- `feature/wave6-onboarding/frontend` → merged via PR #161
- `feature/wave6-catalog-form/frontend` → merged via PR #164
- `feature/wave6-export/frontend` → merged via PR #167

All four were squash-merged to develop and **deleted from origin BEFORE the F-001 fix** (#203). The F-001 fix now sits on TOP of their content as develop HEAD, so they cannot re-introduce F-001. Any stale `/tmp` worktrees pointing at them are leftover refs only — not a risk.

**`feature/mfe-cutover/frontend` (tip `0c17aa0`) — RETIRED, deleted from origin 2026-06-13 (founder decision).** No longer an at-risk in-flight branch; the rebase-guard warning that previously lived here is now moot. It was the SP07 shell-cutover sub-branch; its 2 commits (D43 shell relocation `src/`→`apps/shell/src/`; D44 version-pinned prod/staging manifest templates + CSP smoke harness) already reached develop via the `feature/mfe-cutover/integration` path → **PR #105** (SP07 cutover close-out). Its only divergent content was the stale pre-F-001 versions of `app.config.ts` + auth/onboarding components (the broken `@mesell/ui-kit/<subpath>` imports) — strictly worse than develop, zero unique unmerged value. Retired, not rebased. **There is no longer any in-flight frontend branch carrying the F-001 regression.**

**General rule (retained):** any in-flight frontend branch predating #203 must pass the rebase + grep + `skip:` guard before merge — the build stays green and tests pass, but the shell goes blank in the browser if F-001 is re-introduced. The frontend lead enforces this at the merge gate.

### Two follow-ups carried to session-2 (tracked in `docs/status/STATUS_FRONTEND.md`)

(a) **Permanent CI boot-smoke gate** — promote the headless browser-boot smoke to a standing CI federation gate that carries **anti-false-pass selector assertions**: assert the REAL component selector is mounted AND the route is not-a-404, *not merely* a non-empty body. F-001 reached merge because a naive boot smoke would pass against a static-server 404 (a 404 page is non-empty). This gate would have caught it pre-merge. (Frontend lead + infra/CI.)

(b) **Authenticated `/profile` capture** — capture the `/profile` card via a founder-Safari OTP session during `mesell-ui-review-session-2` (the route is auth-guarded; boot smoke proved it loads, but a visual capture needs a real session). (Founder + frontend lead.)
