## Localhost dev-stack ADVANCE — rebuild-4205 worktree 0087562(#278) → b28ef2f(#281 auth fix) — 2026-06-18

**Task class:** localhost dev-stack ops (single-agent fast mode, dev-only, ₹0). Founder-directed. Advance the EXISTING long-lived serving worktree `/private/tmp/mesell-wt/rebuild-4205` (which serves BOTH :4205 static mfe-catalog AND :4200 shell ng serve) from `0087562` (#278) to develop tip `b28ef2f` (#281 auth refresh-stampede fix + #278 My Live Listings), then restart both processes from it.

**Outcome (all green):** worktree HEAD now `b28ef2f`. mfe-catalog rebuilt fresh. :4200 + :4205 restarted from the advanced tree. :8000 untouched. Master tree's 20+ dirty edits NEVER touched.

**Pids (old→new):** :4200 65133→**89742** (node ng serve, IPv6 [::1], cwd=worktree). :4205 61644→**89622** (node serve.js static, IPv4). :8000 13356 master UNCHANGED (uvicorn `--reload` worker recycled 49654→89775 on its OWN — NOT me; never restart :8000).

**HTTP:** :4200/=200, :4205/=200, :4200/catalogs/live=200, :4205/remoteEntry.json=200, :8000/health=200, :4200/api/v1/health proxy headers `server: uvicorn`+`application/json` (proxy→:8000 live).

**Recipe (reusable to ADVANCE an existing serving worktree to a new develop tip — vs the from-scratch `worktree add` recipe above):**
1. Preflight gate 1: `git -C <master> fetch origin develop`; `git merge-base --is-ancestor <newtip> origin/develop && echo ON` (don't trust `cat-file -t`, that's true for OPEN PR refs too).
2. Worktree was CLEAN + detached → `git -C <wt> checkout <newtip>` works directly (no branch dance). Confirm HEAD + `grep -c refreshShared libs/core/services/auth.service.ts`.
3. `pnpm install --config.dangerously-allow-all-builds=true` → "Already up to date" (no dep delta #278→#281).
4. `rm -rf dist/mfe-catalog` (stale dist checked out with the prior HEAD) → `nohup ng build mfe-catalog > log 2>&1 &`. GREEN at "Application bundle generation complete [3.7s]". live-listings chunk `chunk-F6YNRQX7.js` (12.44kB) present. Native-federation HANG-after-complete recurred (pid 0.0% CPU, no recent dist writes) → killed wrapper + `pkill -9 -f "rebuild-4205/frontend/node_modules.*esbuild"`; dist survives.
5. Kill old :4205 → `nohup node tools/boot-smoke/serve.js dist/mfe-catalog/browser 4205 &`.
6. Kill old :4200 → `nohup ./node_modules/.bin/ng serve frontend --port 4200 &` (proxyConfig auto from angular.json). "Watch mode enabled" at poll 2 (~10s). shell-component chunk `chunk-T57KXLHD.js` (11.09kB).

**CRITICAL — how to PROVE the auth fix is in the SERVED :4200 bundle when :4200 is `ng serve` (Vite dev mode), NOT a static build:** you CANNOT curl a static chunk by name for the symbol — Vite serves `@mesell/core` (the shared lib holding AuthService) as on-demand transformed modules over versioned ESM URLs the BROWSER requests, and it 403/404s arbitrary curl probes (`/@fs/...`=403 fs-allow guard, `/libs/core/...`=404) BY DESIGN. main.js is a 288-byte stub; the app chunks (`chunk-T57KXLHD.js` shell-component, `chunk-IYKZVWVP.js` bootstrap) do NOT inline the lib symbols → `grep refreshShared`=0 on all of them (EXPECTED, not a failure). The authoritative served-bundle proof for a Vite ng-serve shell is the CHAIN:
   (a) ng serve process cwd == the advanced worktree: `lsof -a -p <pid> -d cwd` → `/private/tmp/mesell-wt/rebuild-4205/frontend`;
   (b) that worktree's `libs/core/services/auth.service.ts` has `refreshShared`×6 + `forceLogout`×7;
   (c) the served bootstrap chunk `chunk-IYKZVWVP.js` imports `from "@mesell/core"` (authGuard, jwtInterceptor) → core IS wired into the served graph.
This is DIFFERENT from the static :4205 case where the built chunk file IS curl-able for the symbol. Report the count as the SOURCE count (6/7) + the cwd-chain proof, and state explicitly that grep-on-served-chunk=0 is expected for Vite dev mode.

**Worktree left IN PLACE** (long-lived serving worktree; :4205 pid 89622 serves out of its dist/, :4200 pid 89742 ng-serves from it). Cleanup only when a future rebuild supersedes it.

---
