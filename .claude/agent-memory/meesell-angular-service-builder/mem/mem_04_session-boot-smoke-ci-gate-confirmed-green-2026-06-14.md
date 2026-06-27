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
