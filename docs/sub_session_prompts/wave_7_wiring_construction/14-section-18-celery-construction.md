# Sub-Session Prompt: §18 Background Jobs (Celery)
# Wave 7 of 10 — CONSTRUCTION
# Specialist agent: meesell-services-builder
# Renames session to: meesell-backend-construction-18-celery-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §18 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-services-builder agent operating in a dedicated construction sub-session for MeeSell §18 (Background Jobs / Celery wiring).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §18 — `workers/celery_app.py` final wiring + task registration; the 2 V1 tasks (`image.precheck` from §11, `export.generate` from §14) get formally registered
- Specialist agent: meesell-services-builder (solo)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-18-celery-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §18 — A through J (esp. §18.B 2 V1 Celery tasks inventory; §18.C `image.precheck` task contract; §18.D `export.generate` task contract; §18.E Valkey wiring DB 1 broker + DB 2 result backend; §18.F worker JWT re-validation per §1.G rule; §18.G `task_reject_on_worker_lost=True` from session 2 G3 cleanup; §18.H cross-cutting; §18.I failure modes + DLQ policy).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §3.I `workers/celery_app.py` subtree, §5.C Valkey factories (get_valkey_broker DB 1 + get_valkey_results DB 2), §11 image (CONSTRUCTED with `image/tasks.py`), §14 export (CONSTRUCTED with `export/tasks.py`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` (no specific §; Celery is operational concern).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (Valkey DB 1 broker + DB 2 result backend).

5. `.claude/agents/meesell-services-builder.md` (own spec).

6. `.claude/agent-memory/meesell-services-builder/MEMORY.md` (esp. session 2 final purge — `task_reject_on_worker_lost=True` already configured; `include=[]` currently empty).

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1-6 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/workers/celery_app.py` current state — `include=[]`; task_reject_on_worker_lost=True; broker_url + result_backend pointing at Valkey DB 1 + 2.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.I:

```
backend/app/workers/
├── __init__.py
└── celery_app.py        # Celery app instance + task auto-discovery from modules/*/tasks.py
```

§18 is mostly a WIRING update — the task DEFINITIONS already live in `modules/image/tasks.py` (§11) and `modules/export/tasks.py` (§14). This section:

1. Populates `workers/celery_app.py` `include=[...]` list with the 2 V1 task module paths: `"app.modules.image.tasks"` and `"app.modules.export.tasks"`.

2. Verifies broker_url and result_backend point at the correct Valkey DBs (DB 1 broker, DB 2 result backend) via `get_valkey_broker()` and `get_valkey_results()` URL construction — or settings-based URL.

3. Preserves `task_reject_on_worker_lost=True` from session 2 G3 cleanup.

4. Implements §18.F worker JWT re-validation rule — when a task receives a `user_id` arg, it re-loads the user from the DB to confirm the user has not been disabled / soft-deleted between enqueue time and execution time. Token validation per `core/auth.get_current_user` cannot run inside the worker (no request context); the rule is "re-fetch the user row by user_id; if `disabled=True` or `deleted_at IS NOT NULL`, fail-fast and write audit but do NOT process the task".

5. Implements §18.I failure modes + DLQ policy:
   - `image.precheck` max_retries=2; on permanent failure, mark `product_images.status="failed_precheck"` + write `image.precheck.failed` audit.
   - `export.generate` max_retries=2; on permanent failure, mark `exports.status="failed"` + write `export.generate.failed` audit with error_code.
   - No separate Celery DLQ in V1 (single retry chain; permanent failure is database-status-driven).

Locked invariants:
- Broker: Valkey DB 1 per CLAUDE.md.
- Result backend: Valkey DB 2 per CLAUDE.md.
- `task_reject_on_worker_lost=True` (session 2 G3 lock).
- 2 V1 task modules in include list — exactly 2 (no others).
- Worker re-validates user via DB on every task that takes `user_id`.
- Sync tasks (`@shared_task` not `async def`); internal async via `asyncio.run`.

Construction protocol:

1. **Tests first**:
   - `test_celery_app_include_list.py` — assert `celery_app.conf.include` is exactly `["app.modules.image.tasks", "app.modules.export.tasks"]`.
   - `test_celery_broker_db.py` — assert `celery_app.conf.broker_url` URL ends with `/1` (DB 1).
   - `test_celery_result_backend_db.py` — assert `celery_app.conf.result_backend` URL ends with `/2` (DB 2).
   - `test_task_reject_on_worker_lost.py` — assert `celery_app.conf.task_reject_on_worker_lost == True`.
   - `test_worker_user_revalidation.py` — task with `user_id` for a soft-deleted user fails fast + writes audit + does NOT process the task.

2. **Implementation** per §18.

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT add a 3rd V1 task module to the include list (only image + export).
- DO NOT remove `task_reject_on_worker_lost=True` (session 2 G3 lock).
- DO NOT use Valkey DB 0 or DB 3 for broker/results (DB 0 = sessions/OTP; DB 3 = cache).
- DO NOT add an async event loop to the Celery worker (sync tasks only in V1).
- DO NOT skip worker user re-validation.
- DO NOT introduce a Celery DLQ in V1 (database-status-driven only).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted: `meesell-services-builder` (solo).

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §18)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. `celery_app.conf.include` exactly `["app.modules.image.tasks", "app.modules.export.tasks"]`.
2. Broker URL ends with `/1`; result backend URL ends with `/2`.
3. `task_reject_on_worker_lost=True` preserved.
4. Worker user re-validation implemented + tested.
5. `image.precheck` and `export.generate` tasks discoverable at boot (verifiable via `celery_app.tasks.keys()`).
6. Failure mode: image task permanent failure → `product_images.status="failed_precheck"` + audit; export task permanent failure → `exports.status="failed"` + audit.
7. 5 unit tests PASS.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update `.claude/agent-memory/meesell-services-builder/MEMORY.md`.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §18 Celery CONSTRUCTED ===
   Files modified: workers/celery_app.py (include list populated + worker user re-validation)
   Tests added: 5 unit
   Decisions made: <list>
   Hand-offs: §19 tests + §20 deployment (Celery deployment manifests need worker replica count)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Valkey DB allocation conflict (e.g. cache and broker share a DB by mistake).
- Worker user re-validation introduces a DB-session leak (worker pool exhaustion).
- New task module needs registration outside V1 scope.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-18-celery-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-6 CONSTRUCTED (image + export task modules exist).
4. Report "Context loaded. Ready to begin §18 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 7 of 10
- **Sequential dependency:** Wave 1-6 CONSTRUCTED (esp. §11 image + §14 export with `tasks.py`).
- **Parallel-safe?:** No — Wave 7 is sequential. §18 first, then §19 tests, then §20 deployment.
- **Expected duration estimate:** ~3-5 hours.
- **Acceptance verification by master:** (1) `python -c "from app.workers.celery_app import celery_app; print(celery_app.conf.include)"` returns the 2 expected modules; (2) `print(celery_app.conf.broker_url)` ends with `/1`; (3) `print(celery_app.conf.result_backend)` ends with `/2`; (4) `print(celery_app.conf.task_reject_on_worker_lost)` returns `True`; (5) STATUS_BACKEND.md UPDATE block present.
