# `/mesell:dev` — Start Full MeeSell Dev Stack (memory-safe)

Starts the complete local MeeSell development environment on an 8 GB Apple-Silicon
Mac with **NO GCP and NO Docker**: PostgreSQL 16, Valkey 8, the FastAPI API (and
optionally the Celery worker), and the Angular 21 Module-Federation frontend
(**shell + 7 micro-frontends**) served as memory-safe static builds.

This command is **idempotent** — running it a second time skips already-running
services rather than duplicating them.

## The real stack (do not confuse with any older Vite/React notes)

| Service | URL / Port | Run as | What it is |
|---|---|---|---|
| Shell (MF host) | http://localhost:4200 | static `serve-static.mjs` | Angular 21 federation host |
| mfe-pricing | http://localhost:4201 | static server | remote |
| mfe-export | http://localhost:4202 | static server | remote |
| mfe-onboarding | http://localhost:4203 | static server | remote |
| mfe-dashboard | http://localhost:4204 | static server | remote |
| mfe-catalog | http://localhost:4205 | static server | remote |
| mfe-auth | http://localhost:4206 | static server | remote |
| mfe-billing | http://localhost:4207 | static server | remote |
| Backend API | http://localhost:8000 | native `.venv` uvicorn | FastAPI — `/health`, `/docs` |
| PostgreSQL 16 | localhost:5432 | brew `postgresql@16` | DB `meesell` (13 tables) |
| Valkey 8 | localhost:6379 | brew `valkey` | cache / Celery broker |

- **Frontend:** Angular 21 (`@angular/core ^21.2.0`) standalone components +
  `@angular-architects/native-federation`. The shell loads
  `federation.manifest.json` at runtime and federates the 7 remotes.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Celery. Run as **one**
  uvicorn process for everyday work (LITE mode, ~350–450 MB).
- **Data:** PostgreSQL 16 (Homebrew `postgresql@16`, **not** pg14) + Valkey 8.
- Connection strings: `postgresql://meesell:password@localhost:5432/meesell` ·
  `redis://localhost:6379`.
- `http://localhost:8000/` returns **404 by design** — health is `/health`, docs `/docs`.

> **NEVER run `pnpm run start:all`.** It launches all 8 `ng serve` dev servers at
> once (3–5 GB), swap-thrashes an 8 GB machine, and is the historical hang cause.
> Build once, serve static. See `docs/LOCAL_DEV_SETUP.md` and
> `frontend/tools/dev/STATIC_DEV.md` for the full diagnosis.

---

## Step 1 — Port conflict check

```bash
for port in 8000 4200 4201 4202 4203 4204 4205 4206 4207 6379 5432; do
  lsof -ti tcp:$port | xargs -r ps -p 2>/dev/null | tail -n +2 | awk "{print \"port $port: \", \$0}"
done
```

Rules:
- Port **5432** (Postgres): must be listening. If not → `brew services start postgresql@16`
- Port **6379** (Valkey): must be listening. If not → `brew services start valkey`
- Port **8000** (API): if uvicorn is already there, skip. If a foreign process is there, kill it first.
- Ports **4200–4207** (shell + 7 MFEs): if the static servers are already up, skip.

## Step 2 — Data services + DB migration

```bash
brew services start postgresql@16
brew services start valkey

mkdir -p /tmp/mesell-logs
cd /Users/mugunthansrinivasan/Project/mesell/backend
source .venv/bin/activate
alembic current 2>&1
```

If output does not contain `(head)`:

```bash
alembic upgrade head 2>&1 | tee /tmp/mesell-logs/migration.log
```

**Stale-stamp / drift recovery** — if `alembic current` shows `(head)` but tables
are missing (`relation "categories" does not exist`), the version was stamped
without running migrations:

```bash
psql -U mugunthansrinivasan -d meesell -c "DROP TABLE IF EXISTS alembic_version;"
alembic upgrade head 2>&1 | tee /tmp/mesell-logs/migration.log
```

Verify tables exist (expect 13 incl. `users`, `catalogs`, `skus`, `categories`,
`alembic_version`):

```bash
psql postgresql://meesell:password@localhost:5432/meesell -c "\dt"
```

Seed reference data (categories, etc.) if needed:

```bash
cd /Users/mugunthansrinivasan/Project/mesell && make seed
```

## Step 3 — Start the backend (idempotent)

**API** (skip if uvicorn already on 8000) — one process is enough for everyday work:

```bash
cd /Users/mugunthansrinivasan/Project/mesell/backend && source .venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level info \
  > /tmp/mesell-logs/api.log 2>&1 &
```

**Worker** (OPTIONAL — only when exercising image precheck / xlsx export; otherwise
skip to save RAM):

```bash
cd /Users/mugunthansrinivasan/Project/mesell/backend && source .venv/bin/activate
nohup celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 \
  --hostname=meesell-worker@%h > /tmp/mesell-logs/worker.log 2>&1 &
```

## Step 4 — Start the frontend (memory-safe, ONE build at a time)

Two supported paths. Prefer the env-manager on the 8 GB box.

### Path A (preferred) — `tools/meesell_env.py` (RAM-budgeted, port-isolated, serialized builds)

This is the canonical low-RAM dev manager. It builds ONE app at a time behind a
machine-wide lock and reuses the shared baseline so a worktree only rebuilds the
shell-if-touched plus the MFEs it changed.

```bash
cd /Users/mugunthansrinivasan/Project/mesell

# First time / fallback: build develop's shell + ALL MFEs (slot 0 baseline)
python3 tools/meesell_env.py baseline up

# In a worktree, bring up only what you touched (reuses baseline for the rest):
python3 tools/meesell_env.py up <worktree-name> --mfe mfe-catalog,mfe-pricing

# Inspect:
python3 tools/meesell_env.py status     # running envs + free RAM + swap%
python3 tools/meesell_env.py ports <worktree-name>
python3 tools/meesell_env.py down <worktree-name>
python3 tools/meesell_env.py gc         # reap orphaned processes
```

### Path B — static build + serve (all 8 apps, baseline only)

```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend
pnpm run dev:build-static          # build all 8 apps, ONE at a time (watchdog)
pnpm run dev:serve-static          # serve dist/<app>/browser on 4200–4207 (foreground)
# or one-shot (build + serve bg + route-check + stop):
pnpm run dev:static all
```

Verify federation routes resolve:

```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend && pnpm run dev:check-routes
```

> If you only need the backend wired to a live-reload shell (single app, not all 8),
> `cd frontend && pnpm --filter shell exec ng serve` proxies `/api` → `:8000`. This
> is fine for shell-only work but does NOT federate the remotes.

## Step 5 — Health verification (wait ~4 seconds)

```bash
sleep 4
curl -s -o /dev/null -w "API /health: %{http_code}\n" http://localhost:8000/health
for p in 4200 4201 4202 4203 4204 4205 4206 4207; do
  lsof -ti tcp:$p > /dev/null 2>&1 && echo "frontend OK on $p"
done
pg_isready -h localhost -p 5432
redis-cli -p 6379 ping
```

## Step 6 — Register persistent monitors using the Monitor tool

Register with `persistent: true`. No grep filters — full raw stream so nothing is missed.

**Monitor 1** — `mesell API — full raw log`
```bash
tail -n 0 -f /tmp/mesell-logs/api.log 2>&1
```

**Monitor 2** — `mesell Worker — full raw log` (only if the worker is running)
```bash
tail -n 0 -f /tmp/mesell-logs/worker.log 2>&1
```

**Monitor 3** — `mesell Frontend — full raw build/serve log`
```bash
tail -n 0 -f /tmp/mesell-logs/frontend.log 2>&1
```

**Monitor 4** — `mesell UI — browser console errors, JS exceptions, network failures`

Passive Chrome DevTools Protocol listener — watches your real browser session, no automation.

Launch Chromium once with remote debugging pointed at the **shell** on :4200:
```bash
open "/Applications/Google Chrome.app" --args --remote-debugging-port=9222 http://localhost:4200
```
Note: `/Applications/Google Chrome.app` is a symlink to the Playwright Chromium install — use the full path.

Captures while you manually use the app:
- `console.error` / `console.warn` from Angular components
- Unhandled JS exceptions and Angular error handlers
- HTTP 4xx/5xx from your manual API calls
- Native-Federation singleton warnings, CORS and CSP violations

## Step 7 — Print status table

```
[mesell] Dev stack ready
─────────────────────────────────────────────────
 API        http://localhost:8000   ✅  (/health, /docs)
 Shell      http://localhost:4200   ✅  (MF host)
 MFEs       :4201–:4207             ✅  (7 remotes)
 Postgres   localhost:5432          ✅  (postgresql@16)
 Valkey     localhost:6379          ✅
 Worker     optional (concurrency 2)
─────────────────────────────────────────────────
 Monitors   API / Worker / Frontend / UI Browser — full raw stream
 OTP        dev bypass code: 000000  (DEV_OTP_BYPASS_CODE, dev only)
─────────────────────────────────────────────────
On any monitor event → read the line, dispatch the right specialist agent.
```

---

## Monitor event routing

When a monitor fires with an error, dispatch the right `meesell-*` agent — never fix inline:

| Monitor         | Trigger pattern                                          | Agent to dispatch                |
|-----------------|---------------------------------------------------------|----------------------------------|
| API errors      | `ERROR:` / 5xx / `CRITICAL:` / startup failed           | `meesell-backend-coordinator`    |
| Worker failures | `ERROR/Fork` / `retry:` / `Traceback` / exception       | `meesell-backend-coordinator`    |
| Frontend errors | build failed / `Cannot find module` / federation error  | `meesell-frontend-coordinator`   |

Pass the exact error lines + relevant source files in the dispatch prompt.

---

## Stopping the stack

```bash
# Backend
lsof -ti tcp:8000 | xargs kill -SIGTERM 2>/dev/null || true
pkill -f "meesell-worker" 2>/dev/null || true
pkill -f "celery.*app.workers.celery_app" 2>/dev/null || true

# Frontend (env-manager path)
python3 /Users/mugunthansrinivasan/Project/mesell/tools/meesell_env.py down <worktree-name> 2>/dev/null || true
# Frontend (static-serve path): Ctrl-C the dev:serve-static process, or:
for p in 4200 4201 4202 4203 4204 4205 4206 4207; do lsof -ti tcp:$p | xargs kill -SIGTERM 2>/dev/null || true; done

echo "MeeSell dev stack stopped. Postgres + Valkey left running (brew services)."
```

---

## See also

- `docs/LOCAL_DEV_SETUP.md` — canonical full-stack local dev guide (verified live).
- `frontend/tools/dev/STATIC_DEV.md` — memory-safe frontend static-serve diagnosis.
- `tools/meesell_env.py --help` — the RAM-budgeted env manager (per-subcommand `--help`).
- `Makefile` — `make dev` (Docker full stack), `make dev-local` (native backend), `make seed`.
