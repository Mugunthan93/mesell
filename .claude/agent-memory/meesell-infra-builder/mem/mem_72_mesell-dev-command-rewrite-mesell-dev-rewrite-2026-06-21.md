## /mesell:dev command rewrite (mesell-dev-rewrite) — 2026-06-21

**Adoption item:** the `/mesell:dev` slash command at `.claude/commands/dev.md` was STALE — described Vite frontend (:5173/:5174), React components, `postgresql@14`, OTP code `1234`. All WRONG.

**Rewrote to the verified real stack** (branch `feat/mesell-dev-rewrite/infra`, PR #353 → develop):
- Frontend = **Angular 21** (`@angular/core ^21.2.0`) Native Federation: **shell :4200 + 7 MFEs :4201-4207** in this exact serve-static port order: mfe-pricing 4201, mfe-export 4202, mfe-onboarding 4203, mfe-dashboard 4204, mfe-catalog 4205, mfe-auth 4206, mfe-billing 4207 (from `frontend/tools/dev/serve-static.mjs` SERVERS array — authoritative, matches `federation.manifest.json`).
- Backend = FastAPI uvicorn **:8000** (`/health`, `/docs`; `/` 404 by design). Optional Celery worker.
- Data = **PostgreSQL 16** (`brew postgresql@16`) :5432 + Valkey 8 :6379. `postgresql://meesell:password@localhost:5432/meesell`.
- OTP dev bypass code = **`000000`** (`DEV_OTP_BYPASS_CODE` in `backend/app/shared/config.py`; gated `bool(DEV_OTP_BYPASS_CODE) and APP_ENV != "production"`). NOT 1234.
- Memory-safe local dev (8 GB box): prefer **`python3 tools/meesell_env.py`** (`baseline up`, `up <wt> --mfe a,b`, `status`, `down`, `gc`) — RAM-budgeted, serialized builds (ONE at a time behind a flock), reuses slot-0 baseline via runtime federation manifest. Alt path = `pnpm run dev:build-static` + `dev:serve-static` (or `dev:static all`). **NEVER `pnpm run start:all`** (8× ng serve = 3-5 GB swap-thrash, the historical hang).

**Authoritative cross-refs:** `docs/LOCAL_DEV_SETUP.md` (founder-facing canonical), `frontend/tools/dev/STATIC_DEV.md`, `Makefile` (`make dev` docker / `make dev-local` native / `make seed`).

**Process notes:**
- `.claude/commands/dev.md` IS git-tracked and NOT gitignored — editable as a normal repo file via a worktree (no settings-classifier block; that block only hits `~/.claude/settings.json` / project `.claude/settings.json`). The "edit via git-plumbing" caution in the task was a non-issue here — plain Write worked.
- Worked in worktree `/tmp/mesell-wt/mesell-dev-rewrite` off `origin/develop` (master tree was parked on `docs/plan-gate` — never git the master tree). Pruned after PR.
- PR #353 targets **develop** = the FOUNDER's gate (D1). `mergeStateStatus=BLOCKED` is the normal protected-develop state; I do NOT merge it. MERGEABLE=true, no conflicts, 1 file +163/-66.
