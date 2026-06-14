# Memory — meesell-angular-service-builder

## Agent Identity
Angular 18 service specialist for MeeSell. Owns services + RxJS state + HttpClient + JWT interceptor + auth guards + typed ApiClientService + typed models. Decentralized memory ecosystem.

## Session: F-001 federation subpath fix (2026-06-13)

**Branch/commit:** fix/frontend/f001-federation-subpath @ 3ae9fd3
**PR:** #203 (→ develop, IN REVIEW at merge-gate)

### Root cause (F-001)
- Native Federation registers ONE import-map key per shared package ROOT. Subpath imports
  (e.g. @mesell/ui-kit/providers, @mesell/ui-kit/input/input.component) compile fine via
  tsconfig wildcard alias but fail at runtime in the browser — es-module-shims cannot resolve
  them because no subpath key exists in the import map.
- @primeuix/themes/aura is imported INSIDE libs/ui-kit/theme.ts (inside the shared chunk).
  @primeuix/themes root is in the import map but /aura is not → second crash on chunk load.

### Fix (a)+(c) per SPEC
- (a) Rewrote all @mesell/ui-kit/<subpath> imports → barrel root @mesell/ui-kit. 4 files touched.
  libs/ui-kit/index.ts was already complete — zero new exports added.
- (c) Added @primeuix/themes + @primeuix/themes/aura to skip[] in all 7 federation configs.
  libs/ui-kit/theme.ts NOT touched — Aura import stays, bundles into _mesell_ui_kit.js (204 kB).

### Evidence
- Grep proof: 3 greps all return empty
- remoteEntry.json proof: 161 shared entries, 0 @primeuix entries in shell + mfe-auth + mfe-onboarding
- Boot smoke: 6/6 PASS (headless chromium 148.0.7778.96), zero resolveErrors

### Key learnings

**BARREL-ONLY import rule (P0 for federation):**
  RIGHT: import { MeeCardComponent } from '@mesell/ui-kit';
  WRONG: import { MeeCardComponent } from '@mesell/ui-kit/card/card.component';
  Subpaths compile via tsconfig wildcard but fail at runtime in the browser (no import-map key).

**build-green != boot-green for federation:**
  esbuild resolves tsconfig aliases at compile time. Runtime failure is browser-only (es-module-shims).
  Always run a headless browser smoke after federation changes.

**playwright on macOS arm64:**
  PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers npx playwright install chromium
  Executable: /tmp/pw-browsers/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell
  Install playwright package in /tmp/smoke-runner (NOT in frontend/ — not a frontend dep)

**pnpm-workspace.yaml allowBuilds fix (PR #203):**
  Placeholder values were in develop until PR #203. Now all 5 entries = true.
  DO NOT overwrite this file on branch checkout — already correct.

### Re-spin evidence session (2026-06-13) — PR #203 prior evidence was FALSE PASS

**FALSE PASS ANATOMY:**
- Prior smoke served `dist/` with `python -m http.server` — NO SPA history-fallback
- `/login` and `/profile` returned Python 404 page (not Angular) → screenshots showed "Error response / Error code: 404"
- `body.length > 0` and `zeroSpecifierErrors` passed trivially on 404 bodies (Angular never ran)

**CORRECT SERVING PATTERN for SPA smoke:**
- Use `ng serve <project> --port <N> --no-open` for each app
- native-federation builder provides proper SPA history-fallback (all paths → index.html)
- Verify: `curl http://localhost:4200/login` MUST return 200 (not 404) before driving browser
- Wait for each remote's `remoteEntry.json` → 200 before running assertions

**PORT MAP (confirmed from angular.json architect.serve-original.options.port):**
- shell (frontend): 4200 | mfe-pricing: 4201 | mfe-export: 4202 | mfe-onboarding: 4203
- mfe-dashboard: 4204 | mfe-catalog: 4205 | mfe-auth: 4206

**Playwright global installation pattern:**
- `npx playwright install chromium` → downloads headless shell to ~/Library/Caches/ms-playwright/
- `npm install -g playwright` → installs globally
- Run script via: `NODE_PATH=/usr/local/lib/node_modules node smoke-script.js`
- `/Applications/Google Chrome.app` symlink may be broken — always re-install via npx

**Worktree + node_modules pattern:**
- Isolated worktree has NO node_modules — `ln -s /main/project/frontend/node_modules worktree/frontend/node_modules`
- Verify main project and fix branch are at compatible angular.json versions

**Local develop vs origin/develop divergence trap:**
- Local `develop` can be N commits behind `origin/develop`
- Check: `git log HEAD..origin/develop | wc -l`
- Fix: apply files from fix branch via `git show <sha>:<path> > <path>`
- If app.config.ts imports jwtInterceptor/refreshInterceptor from @mesell/core → need origin/develop version of libs/core/index.ts

**F-001 smoke re-run results (6/6 PASS, commit f35ea3d):**
- / @ 360+1280px: RemoteFailureComponent (cloud_off/Retry) — D12 fallback, shell booted
- /login @ 360+1280px: real LoginComponent — "Welcome back", mee-input, Continue button rendered
- /profile @ 360+1280px: authGuard fired → redirect to /login → LoginComponent (proves guard + singleton cross)
- Zero "Unable to resolve specifier" across all routes/widths
- @primeuix/themes absent from mfe-auth + mfe-onboarding + shell remoteEntry.json
- PR #203 updated; comment added: https://github.com/Mugunthan93/mesell/pull/203#issuecomment-4697814639

## Session: boot-smoke CI gate — confirmed GREEN (2026-06-14)

**Branch:** ci/frontend/boot-smoke @ 88e6262
**PR:** #213 (→ develop, READY FOR FOUNDER MERGE — D1 gate)
**CI Run:** 27477214257 — conclusion: success
**URL:** https://github.com/Mugunthan93/mesell/actions/runs/27477214257/job/81218610137

### Root cause of original hang (CI run 27476389960)
- `ng build --configuration development` ALSO hangs on NF cold-start (~31 min before timeout).
  The stall is NOT production-only: NF's "Preparing shared npm packages" runs in BOTH dev and
  production build modes. The `--configuration development` fix was NOT sufficient.
- `ng serve` (webpack-dev-server) avoids this stall entirely: it defers the shared-package
  scan to lazy first-request rather than doing it upfront at build time.

### Lockfile drift: macOS pnpm vs Linux CI (LOCKED PATTERN)
- Running `pnpm install --lockfile-only` on macOS (pnpm 11.5.2) injects `esbuild@0.27.3` as
  optional peer of webpack into 15+ Angular build-webpack snapshot key strings.
  Linux CI does not include this peer → frozen-lockfile install fails with hash mismatch.
- RULE: NEVER regenerate pnpm-lock.yaml on macOS for this project. Always restore
  origin/develop baseline, then HAND-PATCH the 3 sections (importers/packages/snapshots)
  for any new devDep additions.
- Validated: lockfile surgical patch (19 additions, 0 drift removals) → `pnpm install --frozen-lockfile`
  SUCCESS on CI Linux runner.

### CI boot-smoke performance achieved (ng serve path)
- All 7 dev servers ready in ~2 min (step 9: 19:48:27 → 19:50:24 UTC)
- Total job time: 4m 10s (was 90m+ timeout → conclusion: cancelled)
- Timeout headroom: 10m 50s remaining out of 15m budget
- Readiness gate: 480s max budget, actual: ~120s

### start-all.mjs pattern (validated)
- Zero-dependency Node.js script, 190 lines
- Spawns 7 named pnpm scripts (start:shell, start:mfe-*) via child_process.spawn
- Per-line ANSI prefix by server label for CI log readability
- SIGTERM → 3s grace → SIGKILL teardown on SIGINT/SIGTERM
- Path: frontend/tools/dev/start-all.mjs

### setsid + PGID pattern (validated on GitHub Actions Ubuntu)
- `setsid pnpm run start:all > /tmp/start-all.log 2>&1 &` creates new process group
- Store `$!` → that IS the PGID leader
- Teardown: `kill -- -"$PGID"` kills all children + parent atomically
- Fallback `kill "$PGID"` handles edge cases

### Boot smoke readiness gate assertions
- Poll `localhost:4200/` (root) for shell — NOT /index.html
- Poll `localhost:420{1..6}/remoteEntry.json` for each remote
- Assert `curl localhost:4200/login` → HTTP 200 (SPA history fallback proof)
- Playwright test step unchanged from original harness

### Hand-off
PR #213 is waiting for founder D1 merge. Do NOT merge without founder approval.
