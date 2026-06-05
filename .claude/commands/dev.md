# `/mesell:dev` — Start Full MeeSell Dev Stack

This skill starts the complete local development environment for MeeSell: Postgres,
Valkey, API, Celery worker, and Vite frontend. It is **idempotent** — running `/dev`
a second time will skip already-running services rather than duplicate them.

---

## Step 1 — Port conflict check

Check which of the required ports are currently in use:

```bash
for port in 8001 5173 5174 6379 5432; do
  lsof -ti tcp:$port | xargs -r ps -p 2>/dev/null | tail -n +2 | awk "{print \"port $port: \", \$0}"
done
```

Rules:
- Port **5432** (Postgres): must be listening. If not → `brew services start postgresql@14`
- Port **6379** (Valkey): must be listening. If not → `brew services start valkey`
- Port **8001** (API): if uvicorn is already there, skip. If a foreign process is there, kill it first.
- Ports **5173/5174** (Frontend): if Vite is already there, skip. If a foreign process is on 5173, kill it.

## Step 2 — DB migration check

```bash
mkdir -p /tmp/mesell-logs
cd /Users/mugunthansrinivasan/Project/mesell/backend
source .venv/bin/activate
alembic current 2>&1
```

If output does not contain `(head)`, run:

```bash
alembic upgrade head 2>&1 | tee /tmp/mesell-logs/migration.log
```

**Important — stale stamp guard**: If `alembic current` shows `(head)` but tables are missing
(e.g. `relation "users" does not exist` errors), the version was stamped without actually
running migrations. Fix:

```bash
alembic stamp base && alembic upgrade head 2>&1 | tee /tmp/mesell-logs/migration.log
```

To verify tables exist after migration:
```bash
psql postgresql://meesell:password@localhost:5432/meesell -c "\dt"
# Expected: users, catalogs, skus, images, exports, alembic_version
```

## Step 3 — Start services (background, idempotent)

**API** (skip if uvicorn already on 8001):
```bash
cd /Users/mugunthansrinivasan/Project/mesell/backend && source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --log-level info \
  > /tmp/mesell-logs/api.log 2>&1 &
```

**Worker** (skip if meesell-worker process exists):
```bash
cd /Users/mugunthansrinivasan/Project/mesell/backend && source .venv/bin/activate
nohup celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 \
  --hostname=meesell-worker@%h > /tmp/mesell-logs/worker.log 2>&1 &
```

**Frontend** (skip if Vite already on 5173/5174):
```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend
nohup npm run dev -- --port 5173 > /tmp/mesell-logs/frontend.log 2>&1 &
```

## Step 4 — Health verification (wait 4 seconds)

```bash
sleep 4
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health
lsof -ti tcp:5173 > /dev/null 2>&1 && echo "Frontend OK on 5173"
pg_isready -h localhost -p 5432
redis-cli -p 6379 ping
```

## Step 5 — Register persistent monitors using the Monitor tool

Register all four with `persistent: true`. No grep filters — full raw stream so nothing is missed.

**Monitor 1** — description: `mesell API — full raw log`
```bash
tail -n 0 -f /tmp/mesell-logs/api.log 2>&1
```

**Monitor 2** — description: `mesell Worker — full raw log`
```bash
tail -n 0 -f /tmp/mesell-logs/worker.log 2>&1
```

**Monitor 3** — description: `mesell Frontend — full raw log`
```bash
tail -n 0 -f /tmp/mesell-logs/frontend.log 2>&1
```

**Monitor 4** — description: `mesell UI — browser console errors, JS exceptions, network failures`

Passive Chrome DevTools Protocol listener — watches your real browser session, no automation.

Pre-requisite: Chromium must be launched with remote debugging enabled (do this once):
```bash
open "/Applications/Google Chrome.app" --args --remote-debugging-port=9222 http://localhost:5173
```
Note: `/Applications/Google Chrome.app` is a symlink to the Playwright Chromium install — use the full path, not `-a "Google Chrome"`.

Then register the monitor:
```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend && node ui-monitor.cjs
```

Script location: `frontend/ui-monitor.cjs` (`.cjs` extension required — frontend uses `"type": "module"` so plain `.js` breaks CommonJS require).

Captures while you manually use the app:
- `console.error` / `console.warn` from React components
- Unhandled JS exceptions and React error boundaries
- HTTP 4xx/5xx from your manual API calls
- CORS and CSP violations

## Step 6 — Print status table

```
[mesell] Dev stack ready
─────────────────────────────────────────
 API      http://localhost:8001   ✅
 Frontend http://localhost:5173   ✅
 Postgres localhost:5432          ✅
 Valkey   localhost:6379          ✅
 Worker   2 concurrency           ✅
─────────────────────────────────────────
 Monitors  API / Worker / Frontend / UI Browser — full raw stream
 OTP       use +91XXXXXXXXXX  →  code: 1234
─────────────────────────────────────────
On any monitor event → read the line, dispatch specialist agent if it's an error.
```

---

## Monitor event routing

When a monitor fires with an error, dispatch the right agent immediately — never fix inline:

| Monitor         | Trigger pattern                                    | Agent to dispatch                        |
|-----------------|----------------------------------------------------|------------------------------------------|
| API errors      | `ERROR:` / 5xx / `CRITICAL:` / startup failed     | `nexus:level-3:python-developer-agent`   |
| Worker failures | `ERROR/Fork` / `retry:` / `Traceback` / exception | `nexus:level-3:python-developer-agent`   |
| Frontend errors | Build failed / `Cannot find module` / SyntaxError  | `nexus:level-3:nextjs-developer-agent`   |

Pass the exact error lines + relevant source files in the dispatch prompt.

---

## Stopping the stack

```bash
lsof -ti tcp:8001 | xargs kill -SIGTERM 2>/dev/null || true
pkill -f "meesell-worker" 2>/dev/null || true
pkill -f "celery.*app.workers.celery_app" 2>/dev/null || true
lsof -ti tcp:5173 | xargs kill -SIGTERM 2>/dev/null || true
lsof -ti tcp:5174 | xargs kill -SIGTERM 2>/dev/null || true
echo "MeeSell dev stack stopped. Postgres + Valkey left running (brew services)."
```
