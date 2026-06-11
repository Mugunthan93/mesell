# Sub-Plan 02 — mfe-export: EXECUTED (the 2nd extraction; first multi-remote manifest)

**Status:** EXECUTED 2026-06-11. Group PR #60 (frontend→integration) squash-merged `565d754`.
Founder-gate PR (integration→develop) OPEN. WAVE 1 parallel with SP03 (onboarding).

## Headline
SP02 copied the SP01 pilot recipe (sub_plan_01_pricing.md) verbatim and it WORKED with zero
toolchain re-derivation (D15 validated). features/export/ → apps/mfe-export/ Native Federation
remote; shell route /catalogs/:id/export → loadRemoteWithFallback('mfe-export','./ExportComponent')
(SP01 helper REUSED, not re-authored). The recipe is now proven reusable across two remotes —
SP03–06 can copy it with confidence.

## What was the same as SP01 (recipe held exactly)
- angular.json project key = `frontend` (shell) + new sibling `mfe-export` (native-federation:build
  → esbuild @angular/build:application; KEY GOTCHA: index.html REQUIRED — authored apps/mfe-export/src/index.html
  with `<app-export>` host element + declared `"index"` in the esbuild options). Port 4202 (pricing=4201).
- federation.config.js: token-for-token copy of mfe-pricing's; ONLY `name` ('mfe-export') + `exposes`
  ('./ExportComponent') differ. shareAll singleton:true + skip rxjs + ignoreUnusedDeps:true.
- @mesell/core CORRECTLY ABSENT from mfe-export's remoteEntry shared[] (export has no AuthService —
  ignoreUnusedDeps omits it; ui-kit + composites present). Same as pricing. Singleton runtime proof = SP03.
- pnpm worktree fix: `pnpm install --config.dangerously-allow-all-builds=true` (~4.7s, package files CLEAN,
  no .npmrc, no pnpm-workspace.yaml drift). esbuild binary extracted in .pnpm/@esbuild+darwin-arm64@0.27.3/.
  Then `./node_modules/.bin/ng build <proj>` directly (NOT `pnpm build`). CONFIRMED clean again.
- Test discovery: BOTH globs (angular.json `../apps/**/*.spec.ts` + tsconfig.spec `apps/**/*.spec.ts`)
  ALREADY covered apps/mfe-export/ from SP01 — RE-CONFIRM only, ZERO edits needed. export spec discovered at
  `spec-apps-mfe-export-src-app-export.component`. Tests 42 files/406 == SP01 baseline EXACTLY (no drop, R-SP2-3 PASS).
- Tailwind @source "../apps" already in styles.css from SP01 — no edit.
- Benign build WARNs: [shared-mappings] Internal lib '@mesell/<x>' does not contain an entryPoint (deep-import
  libs w/o barrels) + 'No meta data found for shared lib @primeuix/styles/<x>'. Ignore. Build succeeds.

## What was NEW in SP02 (the surfaces beyond the pilot)
- **TWO-remote manifest (R-SP2-4) — PROVEN.** manifest = {mfe-pricing:4201, mfe-export:4202}. Both served +
  curled: both remoteEntry.json → 200 SIMULTANEOUSLY; export exposed chunk (ExportComponent-XZ5IULI2.js) → 200;
  broken URL → 404 (D12 fallback path). Native Federation resolves multiple manifest entries with no ordering
  quirk. The shell build ships the 2-entry manifest verbatim into dist/frontend/browser/. SP03+ can add the Nth
  entry safely — multi-remote manifest is no longer an unknown.
- **D18 timer-preserve across boundary.** export.component has setInterval job-polling (pollingIntervalId,
  10/500ms→100% in ~5s) cleared in ngOnDestroy→clearPollInterval (also on ready + onRetry). Moved as R100 pure
  rename — ZERO logic edits, NOT rewritten to RxJS. The federation boundary does NOT alter Angular lifecycle:
  the shell destroys the remote on navigate-away → ngOnDestroy fires → clearInterval. Proof form: structural
  (R100 byte-identical preservation of ngOnDestroy→clearInterval) + the existing nextProgress/isProgressComplete/
  retryState pure-fn tests cover the tick math. Full in-browser navigate-away assertion handed forward (SP01
  headless precedent — no browser in build env). This is the PRECEDENT for remote-side data-service polling
  (MASTER_PLAN §4.2). For SP04 dashboard's DashboardApiService + any Wave-6 real polling: same pattern holds.

## Spec discipline note (important for SP03–06)
- export.component.spec.ts deliberately uses NO TestBed (Angular21+PrimeNG21 JIT throws "Cannot read properties
  of null (reading 'ngModule')" in vitest+jsdom). The pattern: extract logic into export.model.ts pure functions
  (decorator-free) + test those directly; component wiring validated by build gate + headless serve. I did NOT
  add a TestBed timer-cleanup test (would break the established no-TestBed discipline + is a test-pattern change
  beyond pure relocation scope). The component injects(Router) so bare `new ExportComponent()` needs an injection
  context — confirming TestBed-free direct instantiation is not viable here. D18 proof is structural + the existing
  pure-fn coverage + handed-forward browser assertion. RESPECT this no-TestBed pattern for all moved feature specs.

## D17 — export.model stays remote-private (NOT promoted to libs/core)
ExportStatus/ValidationChecks/check builders/MOCK_DOWNLOAD_URL moved WITH the component. Forward note:
when Wave 6 wires the real export-job-status API, ExportStatus MAY become a backend-contract type → at THAT
point it is a @mesell/core/models candidate + a frontend↔backend memo. NOT a SP02 action.

## Parallel-wave ops (SP03 concurrent — the append-race learnings)
- **Board/STATUS append-race is REAL and recurred.** Both SP02 + SP03 + an AI-track session committed to develop
  concurrently. My board IN PROGRESS row + SP03's onboarding row collided in the shared master tree's working copy;
  resolved keep-both (both rows on develop). The master tree had 3-7 dirty sibling agent-memory files throughout
  (backend/infra/ai/nexus-director) that I NEVER touched — they block `git pull --rebase` ("unstaged changes").
- **The reliable F2-commit-to-develop pattern when the master tree is dirty + origin moves under you:**
  1. Edit my own sole-writer file (board/STATUS) on disk.
  2. `git add <my-file-path-only>` (path-scoped — never `git add -A`, never touch sibling dirty files).
  3. `git commit <my-file>` ; `git push origin HEAD:develop`.
  4. If push REJECTED (origin advanced): `git fetch origin develop` then `git reset --mixed origin/develop`
     (moves HEAD to origin tip, KEEPS my edit as an unstaged working-tree change, leaves sibling dirty files
     untouched because my edit is path-disjoint). Then re-add + re-commit + re-push (now fast-forward). This
     AVOIDS rebase (which the dirty sibling files block) and AVOIDS stash (which would touch sibling files).
  5. Verify `git diff origin/develop -- <my-file>` shows ONLY my intended change before committing.
- **CRITICAL git mistake I made + recovered (DON'T repeat):** when setting up the integration worktree for the
  founder-gate merge, my LOCAL integration branch was STALE at bb37f5f (the branch-create point), while
  origin/feature/mfe-export/integration had advanced to 565d754 (the PR #60 squash-merge with the SP02 code).
  I ran `git merge origin/develop` which FAST-FORWARDED my stale local to develop tip — SILENTLY DROPPING the
  SP02 code (565d754 is on the integration line, not on develop). FIX: `git reset --hard origin/feature/mfe-export/integration`
  FIRST (to get the real tip with the code), THEN `git merge origin/develop`. LESSON: after a group PR merges to
  integration, ALWAYS `git fetch` + reset the integration worktree to `origin/feature/<name>/integration` BEFORE
  merging develop into it. Verify `ls apps/<remote>/` is PRESENT before pushing the founder-gate branch.
- **gh pr merge --squash --admin --delete-branch:** GitHub merge LANDED (565d754) but local branch-delete errored
  ("used by worktree at /tmp/mesell-wt/sp02-export"). Recover: `git worktree remove --force` + prune FIRST, then
  `git push origin --delete feature/mfe-export/frontend`. Recurring pattern (memory).
- Worktrees: sp02-* paths ONLY (sp02-export for frontend branch, sp02-integration for the founder-gate merge).
  Never switched the master tree's branch. SP03's sp03-* worktrees + sibling worktrees (auth-otp-infra, mf-sp0,
  legal-v1-legal) left untouched.

## D13 hosting — DEFERRED (founder ruling, parallel-wave morning)
All hosting criteria are "locally proven" class (same as the pilot). NO new infra hosting request opened — the
SP01 request (handoff_mf_pricing_deploy.md) already covers the GCS/CDN/remotes.mesell.xyz surface. A
second-remote prefix memo (handoff_mf_export_deploy.md) records the mfe-export/{version}/ prefix + the
dorny/paths-filter matrix fan-out (C-CI-1) for when hosting lands at SP04-05. Noted in the founder-gate PR body.

## §9.A scorecard (re-confirm, not re-derive — toolchain already proven by SP01)
1. Remote builds → remoteEntry.json: PASS (3.43s, name mfe-export, 1 expose, core omitted).
2. Shell builds ≤90s esbuild preserved: PASS (2.89s).
3. No shared-lib duplication (static singleton): PASS (core absent/uniform; ui-kit+composites shared).
4. Remote loads in shell: LOCALLY-PROVEN (served remoteEntry 200 + chunk 200; full browser mount handed fwd).
5. D12 fallback on load failure: PASS (broken URL 404 → .catch → RemoteFailureComponent; reused helper).
6. Test count == baseline: PASS (42/406 == SP01; export spec discovered, 0 drop, 0 fail).
7. 360/1280 screenshots: LOCALLY-PROVEN (pure-rename zero-visual-delta; no headless browser).
8. Hosting/GCS: LOCALLY-PROVEN/infra (D13 deferred; localhost dev-validated).
NEW: two-remote manifest (R-SP2-4): PASS. D18 timer-preserve: PASS (structural + pure-fn coverage).
Result: 5 PASS + 3 locally-proven + 2 new-surface PASS / 0 FAIL.

## Forward contract for SP03 (mfe-onboarding — the AuthService singleton sub-plan)
- SP03 is the TWO-expose remote (onboarding + profile) + D21 AuthLayout promotion to @mesell/composites +
  D22 AuthService singleton C1-C5 runtime proof (the migration's auth go/no-go). It runs CONCURRENTLY with SP02
  (Wave 1) — when SP03 also reaches its founder gate, whoever merges to develop SECOND must `git merge origin/develop`
  + keep-both the shared shell files (app.routes.ts route entries, manifest entries, angular.json projects). As of
  SP02's founder-gate open, develop did NOT yet have the onboarding remote, so SP02's integration merge was conflict-free.
- The 3-entry manifest (pricing+export+onboarding) will appear once BOTH founder gates merge. The 2-entry proof here
  de-risks it.
