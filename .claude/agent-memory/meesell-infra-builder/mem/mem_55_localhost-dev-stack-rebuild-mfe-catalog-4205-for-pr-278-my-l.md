## Localhost dev-stack rebuild — mfe-catalog :4205 for PR #278 "My Live Listings" — 2026-06-18

**Task class:** localhost dev-stack ops rebuild (single-agent fast mode, dev-only, ₹0 spend). Documented workflow pattern (master memory "localhost session rebuilds mfe-catalog"): static catalog remote on :4205 must be rebuilt after catalog feature merges because the shell :4200 federates to the STATIC build and won't pick up changes on refresh.

**Outcome:** mfe-catalog rebuilt from clean worktree off origin/develop (tip `0087562`, PR #278). New :4205 serving fresh dist. `/catalogs/live` resolves 200 via shell. ₹0, no cluster/secrets/terraform touched, master tree's 20+ dirty edits NEVER touched.

**Exact recipe that worked (reusable for any 420x remote rebuild):**
1. `git -C <master> fetch origin develop` → confirm tip.
2. `git -C <master> worktree add --detach /private/tmp/mesell-wt/rebuild-4205 origin/develop` (detached = read-only build, no branch, no commits). Confirm HEAD + feature dir exists.
3. `cd /private/tmp/mesell-wt/rebuild-4205/frontend && pnpm install --config.dangerously-allow-all-builds=true` (~6s, picks up xlsx@0.18.5).
4. `rm -rf dist/mfe-catalog` first (a STALE dist/ gets checked out with the worktree — mtimes = checkout time, NOT a real build; remove it so "fresh build" is provable by existence/mtime), then `nohup ./node_modules/.bin/ng build mfe-catalog > <log> 2>&1 & disown`. Build to a LOG FILE, not `| tail` (tail buffers until exit → zero incremental visibility; a log file lets you watch federation progress and diagnose a hang).
5. Kill old :4205 (`lsof -nP -iTCP:4205 -sTCP:LISTEN -t` → kill), relaunch from frontend dir: `nohup node tools/boot-smoke/serve.js dist/mfe-catalog/browser 4205 > <log> 2>&1 & disown`.
6. Verify: `curl -s -o /dev/null -w "%{http_code}" http://localhost:4205/` =200, remoteEntry.json =200, the feature chunk =200, the xlsx chunk =200, :4200 =200, AND `http://localhost:4200/catalogs/live` =200.

**Build result (GREEN):** "Application bundle generation complete [3.291s]". Chunks confirmed in `dist/mfe-catalog/browser/`: `live-listings.component-OKYKU52J.js` + `chunk-F6YNRQX7.js` (live-listings-component 12.44kB) + `xlsx.E4BdgQhUHf.js` (609KB async chunk). Only warning = catalog-form CSS 52 bytes over 4kB budget (benign, not a failure). remoteEntry name=`mfe-catalog`, exposes `['./CatalogRoutes','./BrowseComponent']` — the `/live` route lives UNDER `./CatalogRoutes` (not a separate federation expose key; don't grep remoteEntry for "live-listings", it won't be there).

**Direct-URL reachability (the founder-note check):** `http://localhost:4200/catalogs/live` returns 200 + the shell SPA HTML (`<title>Frontend</title>`, `app-root`). The shell on :4200 runs ng serve from the DIRTY master tree (old code) so the "My Live Listings" SIDEBAR NAV ITEM does NOT appear — but the route is reachable by direct URL because the shell delegates `/catalogs/*` to the rebuilt remote. Confirmed the live-listings chunk contains the #278 "View on Meesho"/"Live Listing" strings.

**CRITICAL GOTCHA — native-federation `ng build` HANGS after completion on this box.** TWICE the `ng build mfe-catalog` process sat at 0.0% CPU / 22MB RSS and never self-exited. First attempt I mistook the cold federation-cache warm ("Building federation artefacts / This only needs to be done once") for a real stall and killed it prematurely. Reality: the build was fine; the process just doesn't terminate after writing output. DIAGNOSIS PROTOCOL: when `ng build` appears stuck, check (a) log file tail for "Application bundle generation complete" + "Output location", (b) `find dist/.../browser -newermt "-60 seconds"` = no recent writes, (c) `ps -o %cpu` = 0.0 twice 2s apart. If all three: the build is DONE, the wrapper is just hanging → `kill <pid>` (then `pkill -9` + clean its esbuild service `pkill -f "rebuild-4205/frontend/node_modules.*esbuild"`). dist survives the kill. Do NOT wait indefinitely; do NOT re-run (wastes ~minutes of federation warm).

**Contention note:** a concurrent `ng serve mfe-catalog` from another worktree (`.claude/worktrees/design-figma-ui-screens`) + a sakai-ng esbuild were running. Box had 31% mem free (not OOM). The first build's apparent stall was the federation cold-cache step, not contention — but be aware multiple ng processes share esbuild service ports/state.

**Toolchain:** node v22.15.0, pnpm 11.5.2, Angular 21.2.16 / @angular/build 21.2.14, native-federation 21.2.3. `/private/tmp` (NOT `/tmp`) explicit paths (macOS symlink). Worktree files root:wheel. serve.js at `frontend/tools/boot-smoke/serve.js` (3881 bytes), prints "serve.js: <dir> → http://127.0.0.1:<port> [SPA fallback ON]".

**Cleanup deferred:** worktree `/private/tmp/mesell-wt/rebuild-4205` left IN PLACE — the :4205 serve.js (pid 61644) serves out of its dist/, so removing the worktree would break the running server. This is a long-lived serving worktree until the next rebuild supersedes it. (Same pattern as other 420x serving worktrees.)

---
