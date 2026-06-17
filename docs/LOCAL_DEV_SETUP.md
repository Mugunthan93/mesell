# MeeSell — Local Dev Setup (Full Stack, No GCP, No Docker)

**Audience:** the founder, running the full MeeSell stack on an 8 GB Apple-Silicon Mac.
**Author:** meesell-backend-coordinator (Backend Lead) · **Date:** 2026-06-14
**Verified:** all ports, paths, RAM figures, and the FE↔BE wiring below were checked live this session.

Deep-dive companions (linked at the end):
- `docs/LOCAL_DEV_BACKEND_FEASIBILITY.md` — full backend RAM profile + why rembg/onnxruntime are non-issues.
- `frontend/tools/dev/STATIC_DEV.md` — memory-safe frontend static-serve diagnosis (lives on branch `chore/frontend/static-dev-tooling`).

---

## TL;DR — verdict

You **can** run the entire stack (frontend + backend + PostgreSQL + Valkey) locally on an 8 GB
Mac with comfortable RAM headroom, **with NO GCP and NO Docker Desktop** — everything runs as
native processes.

- Data services (PostgreSQL 16, Valkey 8) are native Homebrew services, already installed and
  running. Idle cost: Postgres ~10 MB, Valkey ~1 MB.
- Backend runs as **one** `uvicorn` process (LITE mode, ~350–450 MB). No gunicorn, no Celery for
  everyday work.
- Frontend runs **static-served** (~35–75 MB), NOT via 7 concurrent `ng serve` dev servers.

> **NEVER run `pnpm run start:all`.** It launches all 7 frontend dev servers at once (3–5 GB),
> swap-thrashes an 8 GB machine, and was the cause of the historical hang. Use the static-serve
> workflow in §4 instead.

**Canonical local API port: `8000`** (see §5 for why, and the one stale `8001` reference to ignore).

---

## Quick reference — services & commands

### Local services (live map)

| Service | URL / Port | Run as | What it is |
|---|---|---|---|
| Shell (MF host) | http://localhost:4200 | static `serve.js` | federation host |
| mfe-pricing | http://localhost:4201 | static `serve.js` | remote |
| mfe-export | http://localhost:4202 | static `serve.js` | remote |
| mfe-onboarding | http://localhost:4203 | static `serve.js` | remote |
| mfe-dashboard | http://localhost:4204 | static `serve.js` | remote |
| mfe-catalog | http://localhost:4205 | static `serve.js` | remote |
| mfe-auth | http://localhost:4206 | static `serve.js` | remote |
| Backend API | http://localhost:8000 | native `.venv` uvicorn | FastAPI — `/health`, `/docs` |
| PostgreSQL 16 | localhost:5432 | brew `postgresql@16` | DB `meesell` (13 tables); data dir `/opt/homebrew/var/postgresql@16` |
| Valkey 8 | localhost:6379 | brew `valkey` | cache / Celery broker |

Connection strings: `postgresql://meesell:password@localhost:5432/meesell` · `redis://localhost:6379`.
Note: `http://localhost:8000/` returns **404 by design** — use `/health` or `/docs`.

### Commands

| Action | Command |
|---|---|
| Data services up | `brew services start postgresql@16 && brew services start valkey` |
| Migrate DB | `cd backend && source .venv/bin/activate && alembic upgrade head` |
| Stale-stamp recovery (drift) | `psql -U mugunthansrinivasan -d meesell -c "DROP TABLE IF EXISTS alembic_version;"` then `alembic upgrade head` |
| Start backend | `cd backend && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload` |
| Build frontend (once) | `cd frontend && pnpm run dev:build-static` |
| Serve frontend (7 static) | `cd frontend && pnpm run dev:serve-static` |
| Verify routes (11/11) | `cd frontend && pnpm run dev:check-routes` |
| Frontend one-shot | `cd frontend && pnpm run dev:static all` |
| Live-API frontend (proxy /api -> :8000) | `cd frontend && pnpm --filter shell exec ng serve` |
| Health check | `curl -s localhost:8000/health` |
| Stop backend | `lsof -ti tcp:8000 \| xargs kill` |
| Stop frontend | Ctrl-C the `dev:serve-static` process (kills all 7) |
| Stop data services | `brew services stop postgresql@16 && brew services stop valkey` |

> ⚠️ **Never** run `pnpm run start:all` (7× `ng serve` ≈ 3–5 GB → hangs an 8 GB machine). Use `dev:static`; for a page that needs live API, run the shell alone under `ng serve`.

---

## Prerequisites

- **No Docker.** Docker Desktop is not running and not required — it would add ~1–2 GB of VM
  overhead for zero benefit. Everything here is native.
- **Homebrew** at `/opt/homebrew` (Apple Silicon).
- **PostgreSQL 16** and **Valkey 8** installed as brew services (see §1).
- **Python venv** at `backend/.venv` (Python 3.11.14) with deps installed.
- **Node + pnpm** for the frontend (workspace at `frontend/`).

---

## 1. Data services (native, no Docker)

Both run as Homebrew services and are normally already up.

| Service | Binary | Listens | Data dir | brew service | Idle RAM |
|---|---|---|---|---|---|
| PostgreSQL 16 | `/opt/homebrew/opt/postgresql@16/bin/postgres` | `localhost:5432` | `/opt/homebrew/var/postgresql@16` (~223 MB) | `postgresql@16` | ~10 MB |
| Valkey 8 | `/opt/homebrew/opt/valkey/bin/valkey-server` | `localhost:6379` | (Valkey default) | `valkey` | ~1 MB |

**Database / role:** database `meesell`, role `meesell` / password `password`. Migrations are
already applied.

Start them if they are down:

```bash
brew services start postgresql@16
brew services start valkey
```

Verify:

```bash
pg_isready -h localhost -p 5432      # -> accepting connections
redis-cli -p 6379 ping               # -> PONG  (valkey speaks the redis protocol)
```

> **Port note:** these are the **native** local ports `5432` / `6379`. They are NOT the
> `5433` / `6380` ports you may have seen in the workspace convention — those are the
> **SSH-tunnel-to-GCP** ports. Local native services do not use them. See §2.

---

## 2. `backend/.env` — local-port block

`backend/.env` is gitignored (it holds secrets), so it is NOT in the repo. To run locally you
must ensure the connection block points at the **native local ports**, not the GCP-tunnel ports.

Paste exactly this block into `backend/.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5432/meesell
VALKEY_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

**Why these ports:** `5433` and `6380` are the SSH-tunnel-to-GCP ports (the workspace dev
convention for remote DB/cache). The native Homebrew services run on the standard `5432` / `6379`.
For a fully-local run you want native, so use `5432` / `6379`.

(Valkey DB mapping per the architecture: DB 0 = sessions/OTP/rate-limits/refresh-allowlist,
DB 1 = Celery broker, DB 2 = Celery result backend, DB 3 = app cache.)

> A backup of the prior GCP-tunnel `.env` block exists at `backend/.env.bak.1781413431` if you
> ever need to switch back to the tunnel ports.

### GCP-secret stubbing (why the app boots without real GCP creds)

`backend/app/shared/config.py` has a fail-fast validator (`_require_non_empty`) over 18 required
env vars — the app exits at boot if any is empty. So `.env` keeps **dummy non-empty values** for
all the GCP / third-party secrets (MSG91, Gemini, GCS, Razorpay, LangFuse). Those code paths are
simply **not exercised** in everyday local (LITE) work:

- **OTP login** generates a **random 6-digit code** (there is NO fixed `1234` bypass). No real SMS is needed locally — the code is emitted to the backend log; read it with `grep -oE 'otp=[0-9]{6}' <backend-log> | tail -1`. Only the OTP **hash** is stored in Valkey, never the plaintext. Enter that code to complete login.
- **Gemini** is only hit on AI suggest / autofill / watermark; a placeholder key yields a graceful
  fallback envelope, not a crash.
- **GCS** is only hit on image up/download (the precheck path).
- **Razorpay / LangFuse** are webhook/observability — inert on the everyday path.

Only populate a **real** `GEMINI_API_KEY` (or real GCS creds) when you are specifically testing
those feature paths.

---

## 3. Run the backend (LITE — ~350–450 MB)

LITE = one `uvicorn` process. No gunicorn, no Celery, no rembg. This is the everyday recipe.

```bash
cd /Users/mugunthansrinivasan/Project/mesell/backend
source .venv/bin/activate

# 1. Migrate (idempotent — safe to re-run)
alembic upgrade head

# 2. Single API process — NOT gunicorn, NOT --workers >1. One uvicorn, --reload.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

Health check (separate shell):

```bash
curl -s http://localhost:8000/health      # -> {"status":"healthy", ...}
```

**Stale-stamp guard (migration gotcha):** if `alembic current` reports `(head)` but the tables are
actually missing (e.g. the DB was reset but the version is still stamped), reset and re-apply:

```bash
alembic stamp base && alembic upgrade head
```

### Add a Celery worker — ONLY for async-job features

The worker is needed **only** when testing async jobs (image precheck or XLSX export). Skip it for
everyday work on auth, catalog form, category picker, pricing, dashboard, seller-profile. When you
do need it, run at **concurrency=1** (the compose default of 2 doubles worker memory):

```bash
source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --concurrency=1 \
  --hostname=meesell-worker@%h
```

> rembg / onnxruntime are **not imported by V1 app code** (the image pipeline is Pillow + Gemini),
> so there is no heavy CPU-inference model to load. See `LOCAL_DEV_BACKEND_FEASIBILITY.md §1`.

---

## 4. Run the frontend (memory-safe static — ~35–75 MB)

The frontend is 7 Native-Federation apps (shell + 6 MFEs). Running all 7 `ng serve` watchers
(`pnpm run start:all`) needs 3–5 GB and hangs an 8 GB machine. Instead, **build each app once,
then serve the static output** with a zero-dependency static server — ~35–75 MB total.

From `frontend/`:

```bash
pnpm run dev:build-static     # build all 7 apps (dev config), one at a time
pnpm run dev:serve-static     # serve the static dist on ports 4200–4206
pnpm run dev:check-routes      # Playwright route check — expect 11/11
```

One-shot equivalent:

```bash
pnpm run dev:static all        # build -> serve -> check, in one command
```

Port map: shell `4200`, mfe-pricing `4201`, mfe-export `4202`, mfe-onboarding `4203`,
mfe-dashboard `4204`, mfe-catalog `4205`, mfe-auth `4206`.

> These `dev:*` scripts live on branch **`chore/frontend/static-dev-tooling`** (commit
> `0c83762`). If they are not present on your current branch's `frontend/package.json`, check out
> that branch (or cherry-pick the commit) first. Deep dive: `frontend/tools/dev/STATIC_DEV.md`.

---

## 5. Frontend ↔ backend wiring (read this before you expect API calls to work)

**The honest answer: the static-served frontend does NOT reach the local backend.**

Why, precisely (verified this session):

1. The Angular app calls the API with **relative paths** — e.g. `/api/v1/seller-profile`. There is
   **no absolute base URL** anywhere in the frontend. `libs/core/services/api-client.service.ts`
   documents the convention explicitly: *"callers pass the FULL `/api/v1/...` path."* So an API
   call only resolves if something on the **same origin** forwards `/api` to the backend.
2. That forwarding is a **proxy**, and the proxy (`frontend/proxy.conf.json`) is used **only by
   `ng serve`**. It targets `http://localhost:8000`.
3. The static server (`frontend/tools/boot-smoke/serve.js`, reused by the static-serve tooling)
   has **no proxy logic** — it serves files and nothing else. The `dev:check-routes` harness passes
   11/11 precisely because it is **auth-mocked and makes no backend calls**; protected routes render
   without a backend.

**So, two real options:**

- **Static frontend (memory-safe) → no live backend calls.** Good for UI/route/render work,
  federation wiring, styling. This is the default low-RAM path and what `dev:check-routes` validates.
- **Live API calls → run the shell under `ng serve`** (not the static server) so `proxy.conf.json`
  forwards `/api → http://localhost:8000`. This costs more RAM than the static path; run the
  **shell only** (port 4200), not all 7, to keep memory in check. There is currently no proxy in the
  static server, so this is the only way to exercise real endpoints end-to-end against the local
  backend.

**CORS caveat for the `ng serve` path:** with `proxy.conf.json`, the browser request is same-origin
(`localhost:4200` → proxy → backend), so CORS is usually a non-issue. But if you ever point the
frontend at the backend **directly** (absolute URL, cross-origin), note that `backend/.env` ships
with `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000` — it does **NOT** include
`http://localhost:4200`. Add `http://localhost:4200` to `CORS_ALLOWED_ORIGINS` in that case.
(`config.py` rejects `*`, so you must list the origin explicitly.)

### The `8000` vs `8001` port discrepancy — resolved

You will see two ports referenced in the repo. Use **`8000`**:

| Source | Port | Status |
|---|---|---|
| `frontend/proxy.conf.json` (PR #212, 2026-06-13 — newest decision) | **8000** | **CANONICAL** — the only thing that actually wires FE→BE today |
| `docker-compose.dev.yml` (`uvicorn ... --port 8000`) | **8000** | agrees |
| `CLAUDE.md` ("FastAPI on :8001") and `/mesell:dev` skill (`.claude/commands/dev.md`) | 8001 | **STALE** — predates the federated proxy; ignore for local FE↔BE work |

Run the backend on **8000** (as in §3) so it matches the frontend proxy. (If you follow the older
`/mesell:dev` skill and it boots uvicorn on 8001, the frontend proxy will not find it — repoint one
of them so they agree on 8000.)

---

## 6. Verify (cold-start checklist)

```bash
# Data services up
pg_isready -h localhost -p 5432            # accepting connections
redis-cli -p 6379 ping                     # PONG

# Backend healthy
curl -s http://localhost:8000/health       # {"status":"healthy", ...}

# Frontend routes (static path)
cd frontend && pnpm run dev:check-routes   # 11/11
```

---

## 7. RAM budget (8 GB machine)

| Component | RAM | Notes |
|---|---|---|
| Frontend (static-served) | **~35–75 MB** | vs 3–5 GB for `pnpm run start:all` — never run start:all |
| Backend LITE (PG + Valkey + 1 uvicorn) | **~350–450 MB** | everyday recipe |
| Backend full (+ Celery + active precheck) | **~0.8–1.1 GB** | only when testing async jobs; use worker `--concurrency=1` |

Everything fits with margin. The real RAM pressure on this machine is **VS Code (~0.84 GB)** and
**Claude Code (~1.05 GB)** — not the MeeSell stack. Deep dive:
`docs/LOCAL_DEV_BACKEND_FEASIBILITY.md`.

---

## Cold-start command sequence (copy-paste)

```bash
# --- data services (skip if already running) ---
brew services start postgresql@16
brew services start valkey

# --- backend (LITE) ---
cd /Users/mugunthansrinivasan/Project/mesell/backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info &
curl -s http://localhost:8000/health      # {"status":"healthy"}

# --- frontend (memory-safe static; no live backend calls) ---
cd /Users/mugunthansrinivasan/Project/mesell/frontend
pnpm run dev:static all                    # build -> serve (4200-4206) -> check (11/11)

# --- OR: frontend with LIVE backend calls (shell only, more RAM) ---
# cd /Users/mugunthansrinivasan/Project/mesell/frontend
# pnpm --filter shell exec ng serve         # uses proxy.conf.json: /api -> :8000
```

---

## Deep-dive links

- **Backend feasibility / RAM profile:** `docs/LOCAL_DEV_BACKEND_FEASIBILITY.md`
- **Frontend static-serve tooling:** `frontend/tools/dev/STATIC_DEV.md` (branch `chore/frontend/static-dev-tooling`)

> `frontend/RUNBOOK.md` exists but is currently **untracked** (not in git), so it is not
> cross-linked here. If it is committed later, link it from this section.
