## Sub-Plan A INFRA merge gate on PR #190 — APPROVE + in-gate fix (2026-06-12)

**Session:** `mesell-ms-export-infra-session-1` (gate). Reviewed tip `aafcc30` → fixed to **`234e4d2`** → APPROVE. PR comment `#issuecomment-4693636063`. Squash run by the session window (not this lane).

**THE LESSON — validate infra-against-spec'd-shape vs the ACTUAL landed sibling tree.** My earlier dispatch (commit `aafcc30`) authored the svc-export Dockerfile + worker Deployment against the SPEC'd tree shape BEFORE the backend lane (PR #189) landed the real app tree. At the gate I diffed against `origin/feature/microservices-export/backend` @ `e23080c` and found **3 defects that would have built/deployed then crash-looped or silently stalled**:
1. **gunicorn not in the landed requirements.txt.** svc-export `requirements.txt` (backend sole-writer) ships `uvicorn[standard]` but NOT gunicorn — yet the api CMD is `gunicorn app.main:app`. Would fail `executable not found`. FIX: `RUN pip install --no-cache-dir gunicorn==22.0.0` in the infra Dockerfile layer (monolith's exact pin). **Could NOT edit the backend lane's requirements.txt — sole-writer boundary.** The image layer is the correct infra-owned place to add it.
2. **worker `-A app.workers.celery_app` → `app.celery_app`.** Landed Celery instance `celery_app` lives in `app/celery_app.py`; svc-export has NO `app/workers/` package (that was the MONOLITH layout). Old path = ModuleNotFoundError at worker boot.
3. **worker `-Q celery` → `-Q svc-export`.** Landed `app/celery_app.py:39,77-78` sets `task_default_queue="svc-export"` + routes `export.xlsx`→`svc-export`. The old `-Q celery` would consume the wrong/empty queue → export jobs never picked up (silent stall, no crash — the worst kind). The aafcc30 deployment COMMENT even asserted "no task_route → default celery queue" which was FACTUALLY WRONG vs the landed code. **Read the landed code, never trust the spec-era comment.**

`app.main:app` entrypoint was correct (`main.py:58 app = FastAPI(...)`).

**Process rule cemented:** when infra authors a Dockerfile/worker-cmd ahead of (or in parallel with) the backend app tree, the merge gate MUST re-derive the entrypoint/module-path/queue-name from the LANDED tree on the sibling branch — `git show <sibling>:.../requirements.txt`, grep the celery instance + `task_default_queue` + `task_routes`, grep `app = FastAPI`. Spec-shape comments rot the moment the real tree lands.

**Gate mechanics that worked:** field-assertion pass via python+yaml.safe_load_all (kubectl can't even client-validate with the cluster unreachable — it needs the discovery doc; the yaml parse + structured assertions are the authoritative offline check). Secret scan = grep added `^+` lines for AIza../rzp_../PEM/64-hex/assigned-pw and subtract REPLACE-ME/known-non-secret. Server-dry-run deferred to deploy time per §15 F3 (documented honestly, not a dev/zero-traffic blocker).

**`task_default_queue` collision safety:** the landed celery_app namespaces broker+result keys with `global_keyprefix="svc-export:"` (§2.E), so the dedicated `svc-export` queue can't collide with the monolith's keyspace even though they share the Valkey instance (broker DB 1 / result DB 2 in dev). Good — confirms `-Q svc-export` is safe alongside the still-running monolith worker.

---
