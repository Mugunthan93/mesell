## Dev Environment Manager — tools/meesell_env.py (2026-06-21, session mesell-dev-env-manager-infra-session-1)

**PR #331** (`feature/dev-env-manager/infra` → develop, founder merges). Stdlib-only Python 3 CLI to run multiple worktree FE+BE side by side on the 8GB box without esbuild deadlock / swap thrash.

**Load-bearing discoveries about the FE federation setup (verified, not assumed):**
- Shell loads its federation manifest at RUNTIME: `frontend/apps/shell/src/main.ts` → `initFederation('federation.manifest.json')` (origin-relative fetch). **This means the baseline shell build is reusable — only the manifest needs swapping per-env. NO shell-rebuild-per-worktree required** unless `apps/shell` itself was touched. This is THE exploit.
- Manifest lives in `frontend/apps/shell/public/federation.manifest.json` (+ `.prod.json`/`.staging.json`), copied to dist root on build → served at `dist/frontend/browser/federation.manifest.json`.
- 7 MFEs now: mfe-auth, mfe-billing, mfe-catalog, mfe-dashboard, mfe-export, mfe-onboarding, mfe-pricing. Discover dynamically from `frontend/apps/mfe-*` (sorted) — do NOT hardcode.
- Shell's Angular *project* name is `frontend` (dist=`dist/frontend/browser`); MFE project names == dir names (dist=`dist/<name>/browser`). serve.js serves `dist/<project>/browser`.
- Reuse existing static server `frontend/tools/boot-smoke/serve.js` — `node serve.js <dist-dir> <port>`, SPA fallback + CORS `*` (federation cross-origin fetch needs it). Don't write a new one.
- Backend run: `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload` from `backend/` (uses `backend/.venv/bin/uvicorn` if present).
- PRIOR OUTAGE LESSON (master memory): committing worktree-pinned ports into federation.manifest.json broke the shell. So the per-env manifest is GENERATED at runtime + gitignored, never committed.

**Design decisions made:**
- Slot port scheme stride 10: backend=8000+N*10, shell=4200+N*10, mfe[i]=4201+N*10+i. Slot 0 = baseline (the `develop` worktree). Formalizes the old ad-hoc convention (master :4200/:8000, gauth-live :4210/:8010).
- Baseline tree discovered DYNAMICALLY = the worktree on branch `develop` (via `git worktree list --porcelain`), NOT the dir the script copy sits in. Bug caught in testing: running the tool from a worktree made it self-baseline (slot 0). Fix = `_discover_master_root()`. All shared state (.nexus/env-ports.json, env-state.json, .build.lock) lives in the baseline tree → one registry + one lock across all worktrees.
- Per-env manifest clobber avoided: when shell NOT touched, serve a per-slot COPY of the baseline shell dist (`.nexus/shell-dist-slot-<N>/browser`, ~16MB/404 files — cheap) so concurrent envs don't fight over one manifest. `down` removes the copy.
- Global build lock via `fcntl.flock` on `.nexus/.build.lock`; `pkill esbuild` before+after each ng build.
- RAM guard conservative (founder-locked): refuse if free<1500MB OR swap>70%. free_mb = (free+inactive+speculative pages)*pagesize; **parse page size from vm_stat header (16384 on this Mac, NOT 4096)**; swap% from `sysctl vm.swapusage`.
- `--stub` flag added for build-free smoke testing of orchestration/registry/budget logic (brief required validating WITHOUT a real 7-MFE build).

**Gitignore added:** `.nexus/env-ports.json`, `.nexus/env-state.json`, `.nexus/.build.lock`, `.nexus/serve-*.log`, `.nexus/backend-*.log`, `.nexus/shell-dist-slot-*/`.

**Scope note:** this is dev-tooling/orchestration (no GCP/K8s blast radius) — executed directly as standalone. No playbook section maps exactly; treated as operational scripting under `tools/`. PR to develop is the founder's gate (NOT mine) per D1.

---
