# Local Dev — Backend Feasibility on 8 GB RAM (No GCP)

**Status:** ASSESSMENT (no code build, no commit) · **Author:** meesell-backend-coordinator · **Date:** 2026-06-14
**Companion to:** the frontend static-serve conversion (`frontend/tools/dev`) that dropped the FE footprint from 3–5 GB to ~130 MB.
**Verdict (summary):** **FITS — minimal recipe (PG + Valkey + single uvicorn).** The full stack (+ Celery + active image precheck) also fits comfortably because the headroom assumption ("rembg/onnxruntime eats GBs") is **false in this codebase** — see §1.

---

## 0. Evidence base (files read this session)

| File | What it told us |
|---|---|
| `backend/requirements.txt` | `rembg==2.0.59`, `onnxruntime==1.19.0`, `pillow==10.4.0` are declared deps; `uvicorn[standard]`, `gunicorn`, `celery==5.4.0`. |
| `docker-compose.dev.yml` | api = `uvicorn app.main:app --reload :8000`; worker = `celery ... --concurrency=2`; postgres:16-alpine; valkey:8-alpine `--maxmemory 256mb`. |
| `backend/app/main.py` | API startup: 8 routers mounted, 6 middleware, `prewarm_top_categories()` in lifespan, `/health` checks PG+Valkey. Imports `category_router` + `catalog_router` at module top. |
| `backend/app/modules/image/tasks.py` | **The image precheck pipeline uses Pillow (steps 1–4) + Gemini vision (step 5). It does NOT import or call rembg/onnxruntime at all.** Pillow is lazy-imported *inside* `_check_jpeg` / `_check_white_background` function bodies (line 91), not at module top. |
| `backend/app/workers/celery_app.py` | 2 task modules registered (`image`, `export`). `worker_prefetch_multiplier=1`. `--concurrency=2` is a CLI flag, not pinned in conf — overridable to `1`. |
| `backend/app/ai_ops/client.py` | Line 52: `from app.adapters import gemini as gemini_adapter` (eager). |
| `backend/app/adapters/gemini.py` | Line 28: `import google.generativeai as genai` (eager, SDK only). `genai.configure(api_key=...)` + model construction are **lazy** — inside `_get_model()` (line 73+), called on first Gemini request, not at import. |
| `backend/app/adapters/__init__.py` | Imports only `MeesellError` — importing `app.adapters` alone is cheap; the cost is in `app.adapters.gemini`. |
| `backend/app/modules/category/service.py` & `catalog/service.py` | Both do top-level `from app.ai_ops import client as ai_client` (line 76). Because `main.py` mounts category + catalog routers at import, **API startup transitively eager-imports `google.generativeai`** — but that is a thin SDK, not a model load. |
| `backend/app/shared/config.py` | Pydantic Settings with a **fail-fast `_require_non_empty` validator** over **18 required env vars** (`SystemExit` at boot if any empty). `.env` already satisfies all 18 (verified by name). |
| `grep rembg\|onnxruntime backend/app/**` | **ZERO matches in application code.** Confirmed twice. |
| Live process measurement | `postgres` total RSS ≈ **10 MB** idle (all backends summed); `valkey-server` RSS ≈ **1 MB** idle. (macOS `ps rss`; both already running natively as homebrew services, PG PID 912 / Valkey PID 910.) |
| `onnxruntime` on disk | 64 MB site-packages — installed but **never loaded into a running process** by the app. |

**The single most important finding:** `rembg` + `onnxruntime` are dead weight in `requirements.txt` for V1 runtime. The image module is Pillow-deterministic + Gemini-vision. No CPU inference model is loaded. The "rembg eats GBs" assumption from the original concern does **not** apply to the current code.

---

## 1. Service-by-service RAM profile

RSS estimates below are for this machine (macOS, native homebrew PG16 + Valkey 8, CPython 3.11.14 in `backend/.venv`). "Idle" = booted, no traffic. "Active" = serving requests / running a job.

| Service | Idle RSS | Active RSS | Notes (evidence) |
|---|---|---|---|
| **PostgreSQL 16** (native, already up) | **~10 MB** (sum of all backends, measured) | ~30–80 MB under a handful of dev connections (each backend ~3–8 MB; pool default `DB_POOL_SIZE=10` + overflow 5) | Already running (PID 912). Idle cost is negligible. The pool, not Postgres itself, is the variable — see §4 pool note. |
| **Valkey 8** (native, already up) | **~1 MB** (measured) + dataset | ~5–20 MB with sessions/OTP/cache/Celery broker keys | Already running (PID 910). `docker-compose` caps the containerised variant at `--maxmemory 256mb`; the native instance is effectively unbounded but the V1 keyspace (OTP, rate-limit, refresh-allowlist, category cache, Celery broker/result) is small. |
| **uvicorn API** (`--reload`, single proc) | **~180–300 MB** | ~250–400 MB under light dev traffic | Heaviest single piece. Loads FastAPI + SQLAlchemy async + Pydantic v2 + redis.asyncio + **`google.generativeai` SDK** (transitively, via category/catalog → ai_ops.client → adapters.gemini). `--reload` adds a watcher/reloader child (~+40–60 MB). The Gemini SDK is import-only (~tens of MB); **no model weights** load at import (`genai.configure` is lazy, inside `_get_model`). |
| **Celery worker** (`--concurrency=2`) | **~300–420 MB** (master + 2 prefork children) | ~350–500 MB while running a precheck/export job | Each prefork child re-imports the app → roughly duplicates the uvicorn baseline. `--concurrency=2` ⇒ **2× child memory**. At `--concurrency=1` this roughly halves the child overhead (~180–260 MB total). **Pillow** is lazy-imported per-call inside the task body (image tasks.py:91) so it is NOT in the idle worker footprint; it appears only while a precheck job runs (~+30–80 MB transient for an in-memory JPEG/decode). |
| **rembg + onnxruntime** | **0 MB** (not loaded) | **0 MB** (not loaded) | **Not imported anywhere in `backend/app/`.** The bg-removal model is never instantiated in V1. The 64 MB on disk is install-only dead weight. If a future feature *does* call `rembg.new_session()`, budget **~300–700 MB** for the ONNX U2-Net session + first-call cold start — but that is V1.5, not now. |

### 1.a–c specific answers

- **(a) When does the model load — lazy or eager?** There is **no rembg model load at all** in V1 code. The only "model-ish" eager import on the API path is the `google.generativeai` SDK (lightweight, no weights). Pillow image work in the worker is lazy (per-call, inside function bodies). Conclusion: **no eager heavy-model cost on either the API or the worker at boot.**
- **(b) Does the API import onnxruntime/rembg at startup?** **No.** The API startup chain (main.py → routers → services → ai_ops → adapters) pulls in `google.generativeai` (thin SDK) but **never** onnxruntime or rembg. The only startup-cost flag worth noting: the Gemini SDK is eagerly imported because category/catalog services import `ai_ops.client` at module top. This adds a small fixed cost (tens of MB), not a model.
- **(c) Is Celery needed for non-image local dev?** **No.** Celery only serves 2 async jobs: `image.precheck` and `export.xlsx`. For everyday work on auth, catalog form, category picker (the AI suggest is a synchronous request-path Gemini call, not Celery), pricing, dashboard, and seller-profile, **the worker is not required**. Skip it unless you are specifically testing image precheck or XLSX export end-to-end.

---

## 2. Feasibility verdict on 8 GB

Frontend now static-served at **~130 MB**. macOS + system processes typically resident ~2–3 GB on an 8 GB machine. Working budget for the backend stack: comfortably **3–4 GB before swap pressure**.

| Footprint | Components | Realistic total RSS | Fits in 8 GB w/ FE static (~130 MB)? |
|---|---|---|---|
| **Minimal** | PG (~10 MB idle, ~80 MB w/ dev pool) + Valkey (~20 MB) + 1x uvicorn `--reload` (~300 MB) | **~350–450 MB** | **YES — easily.** This is the everyday recipe. Even with the FE static server + a browser tab, total well under 1 GB of *new* load. |
| **Full** | Minimal + Celery `--concurrency=2` (~400 MB) + active precheck (Pillow +~80 MB transient) | **~800 MB – 1.1 GB** | **YES.** Still under ~1.1 GB of new load. The historical hang came from 7x `ng serve` (3–5 GB), not the backend. With FE static, there is ample headroom. |
| **Full, lean** | Minimal + Celery `--concurrency=1` | **~600–750 MB** | **YES, with the most margin** — recommended when you do need the worker. |

**Why the earlier full hang happened and why it won't now:** the machine hung when 7 live `ng serve` dev servers (3–5 GB) coexisted with the backend. The frontend is now static (~130 MB). The backend's true cost is sub-gigabyte. The constraint was the frontend, not the backend.

---

## 3. LOCAL-DEV-LITE recipe (everyday work, no GCP)

The minimal set for daily backend work. Native PG + Valkey are **already up** (no Docker). One uvicorn process. No Celery, no gunicorn, no rembg.

### 3.1 Prereqs (already true on this machine)
- PostgreSQL 16 native on `localhost:5432` (PID 912) — `pg_isready -h localhost -p 5432`
- Valkey 8 native on `localhost:6379` (PID 910) — `redis-cli -p 6379 ping`
- `backend/.venv` (Python 3.11.14) with deps installed
- `backend/.env` populated — all 18 required vars present (verified)

### 3.2 Commands (minimal — copy/paste)

```bash
cd /Users/mugunthansrinivasan/Project/mesell/backend
source .venv/bin/activate

# 1. Migrate (idempotent — safe to re-run)
alembic upgrade head

# 2. Single API process — NOT gunicorn, NOT --workers. One uvicorn, --reload.
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --log-level info

# 3. Health check (separate shell)
curl -s http://localhost:8001/health      # -> {"status":"healthy",...} when PG+Valkey reachable
```

That is the entire everyday stack: **~350–450 MB total new load.** No Celery.

### 3.3 When you DO need async jobs (image precheck / XLSX export)

Add the worker at **concurrency=1** (half the memory of the compose default `=2`):

```bash
cd /Users/mugunthansrinivasan/Project/mesell/backend && source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --concurrency=1 \
  --hostname=meesell-worker@%h
```

### 3.4 Keeping rembg cheap

No action needed: **rembg/onnxruntime are not loaded by V1 code.** The image precheck (Pillow + Gemini) is the only image path and it is light. If a future branch introduces `rembg.new_session()`, gate it behind a lazy import and a feature flag, and prefer concurrency=1 for the worker.

### 3.5 Relationship to the `/mesell:dev` skill (`.claude/commands/dev.md`)

`/mesell:dev` is the **full** stack starter and already does most of the right things — **but it is heavier than LITE and has two trim points:**

| `/mesell:dev` step | LITE verdict |
|---|---|
| Port check + start PG/Valkey if down | **KEEP** — correct; both already up here. |
| `alembic current` / `alembic upgrade head` (+ stale-stamp guard) | **KEEP** — exactly the migration handling LITE needs. The stale-stamp guard (`alembic stamp base && alembic upgrade head` when `(head)` but tables missing) is a genuinely useful gotcha. |
| Start API: `uvicorn ... --port 8001 --reload` | **KEEP** — already single-process `--reload`, the correct shape. |
| Start Worker: `celery ... --concurrency=2` | **TRIM** — drop for everyday work; when needed, run at `--concurrency=1`. This is the single biggest memory saving (~150–200 MB). |
| Start Frontend: `npm run dev` (Vite) | **TRIM / REPLACE** — this is the old heavy dev-server path. Use the new **frontend static-serve** workflow (`frontend/tools/dev`, ~130 MB) instead. Do not run Vite/ng dev servers alongside the backend. |
| 4 persistent monitors + Chrome CDP | **OPTIONAL** — fine to keep API/Worker log monitors; the UI browser monitor is FE-side. |
| Monitor-routing table dispatches `nexus:level-3:*` agents | **STALE / DO NOT USE** — violates the MeeSell ecosystem rule (only `meesell-*` agents touch MeeSell). The skill predates the 18-agent fleet. Route API/worker errors to backend specialists via meesell-backend-coordinator, not nexus agents. (Flag for the future build session to fix.) |

**Net:** LITE = `/mesell:dev` minus the Celery worker, minus the Vite frontend, with the FE replaced by the static server. The migration + API steps carry over verbatim.

---

## 4. Risks + mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | **rembg/onnxruntime cold-start + model memory** | **Non-issue in V1** — not imported by app code. Documented here so a future contributor does not "optimize" a path that does not exist. If rembg is ever wired: lazy `new_session()`, feature-flag it, worker `--concurrency=1`, budget ~300–700 MB. |
| R2 | **Celery `--concurrency=2` doubles worker memory** | Use `--concurrency=1` locally (each prefork child re-imports the full app ~= one uvicorn baseline). `worker_prefetch_multiplier=1` is already pinned in `celery_app.py` (fairness, not memory, but harmless). Concurrency is a CLI flag, not pinned in `conf` — safe to override. |
| R3 | **API eagerly imports `google.generativeai` at startup** (via category/catalog → ai_ops.client → adapters.gemini) | Accept it — it is a thin SDK (tens of MB), **no model weights** (`genai.configure` + model build are lazy in `_get_model`, first-request only). No mitigation required; noted so nobody mistakes it for a heavy load. |
| R4 | **Any service eagerly loading a model at import** | Audited: **none.** Pillow is lazy (per-call in tasks.py:91 / service.py:112). Gemini SDK is import-only. onnxruntime/rembg uninvoked. The API/worker boot has no heavy-model cost. |
| R5 | **DB migration / seed needs** | `alembic upgrade head` before first API call. Stale-stamp guard (from `/mesell:dev` step 2): if `alembic current` says `(head)` but tables are missing -> `alembic stamp base && alembic upgrade head`. Category/field-alias seeds (if the picker/catalog features are exercised) are separate seed scripts owned by meesell-database-builder — run only if testing those features. |
| R6 | **GCP-only secrets the fail-fast validator requires** (`config.py` `_require_non_empty`, 18 vars) | `.env` already has all 18 populated with dev/stub values, so the app **boots today**. The runtime behaviours that *call out* to GCP/third-parties degrade gracefully or are avoidable locally: **MSG91** (OTP) — dev OTP is the fixed code `1234` per `/mesell:dev` (no real SMS send needed for login); **Gemini** — only hit on AI suggest/autofill/watermark; budget cap + graceful fallback (§6A.F) means a bad/placeholder key yields a fallback envelope, not a crash; **GCS** — only hit on image up/download (precheck path); **Razorpay/LangFuse** — webhook/observability, inert on the everyday path. **Mitigation:** keep dummy non-empty values in `.env` (satisfies the validator), and simply do not exercise the GCP-dependent feature paths in LITE. Only populate a real `GEMINI_API_KEY` when actively testing AI features; only real GCS creds when testing image precheck. |
| R7 | **DB connection-pool memory under load** | `DB_POOL_SIZE=10` + `DB_MAX_OVERFLOW=5` (config.py). Each connection is a PG backend (~3–8 MB). For LITE you can lower `DB_POOL_SIZE` to 5 in `.env` if you want to shave PG memory — optional, not required at 8 GB. |
| R8 | **`prewarm_top_categories()` at lifespan startup hits Valkey/PG** | Already wrapped in try/except in main.py (line 67) — failure is logged and swallowed, boot proceeds with a cold cache. No action. |

---

## 5. Ready-to-dispatch prompt (FUTURE build session)

The following builds the backend local-dev orchestrator + runbook, mirroring `frontend/tools/dev`. It is a **chore** (tooling + docs, no feature code), so per CLAUDE.md HYBRID rule-7 it goes through **meesell-backend-coordinator in single-agent fast mode** (the lead executes directly — no specialist 3-step ceremony, since this touches only `backend/tools/dev/`, a Makefile target, and a runbook doc, none of which is module feature code).

```text
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside that path.
ROUTING: This is a CHORE (local-dev tooling + runbook). Per CLAUDE.md HYBRID rule-7,
meesell-backend-coordinator executes this DIRECTLY in single-agent fast mode — no
specialist dispatch, no 3-step merge-gate ceremony. It touches only backend/tools/dev/,
a Makefile target, and a doc — zero module feature code, zero migrations, zero schemas.

TASK: Build a memory-safe LOCAL-DEV-LITE backend orchestrator + runbook for an 8 GB
machine with NO GCP, mirroring the frontend static-serve workflow at frontend/tools/dev.

BACKGROUND (verified in docs/LOCAL_DEV_BACKEND_FEASIBILITY.md):
- PG 16 + Valkey 8 already run natively (homebrew services, ports 5432/6379). No Docker.
- rembg/onnxruntime are NOT imported by app code — ignore them; do NOT load any model.
- Celery is OPTIONAL (only image.precheck + export.xlsx). LITE default = no worker.
- backend/.venv is Python 3.11.14; backend/.env satisfies all 18 required config vars.
- /mesell:dev (.claude/commands/dev.md) is the heavy full-stack skill; LITE = it minus
  Celery, minus the Vite frontend, with FE replaced by the static server.

DELIVERABLES:
1. backend/tools/dev/ orchestrator (shell script and/or a Makefile target, e.g.
   `make dev-lite`) that:
   a. Verifies (does NOT install) native PG on :5432 and Valkey on :6379; clear error
      with the `brew services start` hint if either is down.
   b. Activates backend/.venv, runs `alembic upgrade head` with the stale-stamp guard
      (if `alembic current` shows (head) but tables missing -> `alembic stamp base &&
      alembic upgrade head`).
   c. Boots ONE uvicorn process: `uvicorn app.main:app --port 8001 --reload`
      (NEVER gunicorn, NEVER --workers >1).
   d. Health-checks GET http://localhost:8001/health, asserting {"status":"healthy"};
      non-zero exit + last log lines on failure.
   e. Does NOT start Celery by default. Provide an opt-in flag/target (e.g.
      `make dev-lite-worker`) that adds `celery ... --concurrency=1` (NOT 2).
   f. Does NOT start any frontend (FE has its own static-serve tool).
   g. Idempotent: re-running skips an already-listening :8001; clean teardown target.
2. A runbook at docs/runbooks/backend-local-dev-lite.md: the LITE recipe, the
   concurrency=1 worker opt-in, the GCP-secret stubbing note (dummy non-empty .env values
   satisfy the fail-fast validator; only populate real GEMINI_API_KEY / GCS creds when
   testing those paths; dev OTP = 1234, no real MSG91 send), the RAM table from the
   feasibility doc, and a "what to trim from /mesell:dev" subsection.
3. Do NOT modify backend/app/, migrations, schemas, or requirements.txt. Do NOT remove
   rembg/onnxruntime from requirements.txt in this chore (separate decision — flag it as
   a follow-up for founder: "V1 runtime never imports rembg/onnxruntime; candidate to drop
   ~64 MB install weight, but defer to V1.5 image-enhancement scoping").

ACCEPTANCE:
- `make dev-lite` boots PG-check -> migrate -> single uvicorn -> green /health, total new
  RSS < ~500 MB, on an 8 GB machine with the FE static server running.
- Worker opt-in runs at concurrency=1.
- Runbook committed; feasibility doc cross-linked.
- Update docs/status/feature_board_backend.md + STATUS_BACKEND.md per the update protocol
  (board row IN PROGRESS -> MERGED, STATUS UPDATE block). No founder-gate PR needed for a
  chore on a non-feature branch — confirm branch/merge handling with the founder.
```

---

## 6. One-line carry-forwards
- **Follow-up for founder (deferred):** `rembg` + `onnxruntime` are never imported by V1 app code (Pillow + Gemini do the image work). Candidate to drop ~64 MB install weight from `requirements.txt` — defer the decision to V1.5 image-enhancement scoping, do not remove in the chore.
- **`/mesell:dev` stale-agent-routing:** its monitor table dispatches `nexus:level-3:*` agents — violates the MeeSell `meesell-*`-only rule; flag for the build session to correct.
