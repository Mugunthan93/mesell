## Localhost :4200 shell swap — DIRTY master tree → CLEAN develop worktree — 2026-06-18

**Task class:** localhost dev-stack ops (single-agent fast mode, dev-only, ₹0). Founder-approved. The natural follow-up to the same-day :4205 mfe-catalog rebuild (memory above): after #278 merged to develop @ `0087562`, the SHELL on :4200 was still `ng serve` from the DIRTY master tree (old code, no "My Live Listings" nav). This task swaps the :4200 process to serve from the clean worktree so the nav item shows — WITHOUT disturbing the master tree's 20+ uncommitted source edits (fully reversible: it's just a process swap).

**Recipe that worked (reusable — swap which tree :4200's ng serve runs from):**
1. Confirm clean worktree: `git -C <wt> rev-parse HEAD` == `git -C <master> rev-parse origin/develop`, and `grep -rn "<nav label>" <wt>/frontend/apps/shell/src/`.
2. Identify old :4200 owner: `lsof -nP -iTCP:4200 -sTCP:LISTEN` → pid; confirm cwd is the MASTER tree via `lsof -p <pid> -d cwd` (look for `/Users/.../mesell/frontend`). `ps -o command -p <pid>` shows `ng serve frontend --port 4200 (frontend)`.
3. `kill <pid>` (process-only — NEVER git/stash/commit in the master tree; the founder's source edits stay in place). Confirm `:4200 free`.
4. From `<wt>/frontend`: `nohup ./node_modules/.bin/ng serve frontend --port 4200 > /tmp/meesell-4200-cleanserve.log 2>&1 & disown`. proxyConfig is AUTO-applied (angular.json shell serve target has `"proxyConfig": "proxy.conf.json"` → `/api`→`localhost:8000`); no `--proxy-config` flag needed.
5. Poll log for "Watch mode enabled" / "Application bundle generation complete" (NOT a hang this time — ng SERVE stays alive in watch mode, unlike ng BUILD which hangs-after-complete per the :4205 lesson). Federation cold-cache warm ("This only needs to be done once") fired first; benign.

**VERIFICATION GOTCHA — grep the right chunk, not main.js.** In this Angular 21 native-federation shell, `main.js` is a 288-byte bootstrap STUB. The nav lives in the lazy `shell-component` chunk (e.g. `chunk-T57KXLHD.js`, name `shell-component`, ~11kB — find its hashed name in the ng serve build-output table in the log). `curl :4200/main.js | grep -c "My Live Listings"` = 0 (EXPECTED, not a failure). `curl :4200/chunk-T57KXLHD.js | grep -c "My Live Listings"` = 1 (the real proof). Also `:4200/catalogs/live` = 200.

**Proxy reaching backend — how to prove it (vs ng serve SPA fallback):** `curl -D - :4200/api/v1/health` headers show `server: uvicorn` + `content-type: application/json` even on a 404 — that's FastAPI's own JSON 404, proving the proxy forwards to :8000 (SPA fallback would return HTML 200). Backend real health route = `/health` (200 direct on :8000), NOT `/api/v1/health` (404). Don't use /api/v1/health as a liveness check; use /health.

**Ports after swap:** :4200 NEW pid 65133 (node, IPv6 [::1]:4200, clean develop). :4205 pid 61644 (static mfe-catalog, IPv4) UNTOUCHED, 200. :8000 pid 13356/49654 (uvicorn) UNTOUCHED.

**REVERT to founder's master-tree edits later:** `kill <new-4200-pid>` then `cd /Users/mugunthansrinivasan/Project/mesell/frontend && ng serve frontend --port 4200`.

**Scope note:** swapping which built tree an `ng serve` runs from = deploy-boundary serving role (OK as founder-directed local ops). Distinct from `ng new`/installing app deps as feature dev (NOT mine, 2026-06-08 DECLINE). No master-tree git ops, no cluster/secrets/terraform.

---
