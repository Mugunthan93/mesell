## §18 Celery wiring CONSTRUCTED (2026-06-08)

### Scope
Sub-session `meesell-backend-construction-18-celery-1`.  Solo dispatch.
§18 = the operational glue layer that lets the 2 V1 Celery tasks
(image.precheck + export.xlsx) run reliably: Valkey wiring, worker
invariants, task registration, worker JWT re-validation.

### Files modified (1)
- `backend/app/workers/celery_app.py` — full rewrite from 40 LOC →
  241 LOC.
  - §18.E: BROKER_URL + RESULT_BACKEND_URL derived from
    `settings.VALKEY_URL` via local `_build_url_for_db` helper
    (mirrors `shared.valkey._build_url_for_db`; equivalence guarded by
    `tests.test_celery_broker_db.test_broker_db_matches_shared_valkey_helper`).
  - §18.B: `include=["app.modules.image.tasks", "app.modules.export.tasks"]`
    — exactly 2 V1 modules, no V0 leftovers.
  - §18.G: `task_reject_on_worker_lost=True` preserved (session 2 G3 lock).
  - §18.F: `task_prerun` signal handler scoped to
    `{image.precheck, export.xlsx}` whitelist.  Re-validates `user_id`
    via SELECT-by-id existence check against `users` table; raises
    `Reject(requeue=False)` on miss.  Fails OPEN on transient DB error.

### Files deleted (1)
- `backend/app/workers/generation_tasks.py` — V0 leftover (catalog.generate
  + sku.regenerate decorators).  Deleted in session 2 final purge,
  accidentally restored, re-deleted here.  workers/ now matches §3.I
  canonical 2-file subtree.

### Files modified (test infra, 2)
- `backend/tests/conftest.py` — removed `CELERY_BROKER_URL` +
  `CELERY_RESULT_BACKEND` env-var defaults (was `/11` + `/12`).  Celery's
  env-var resolution order (`os.environ.get('CELERY_BROKER_URL') or
  self.first(...)`) hijacked the `Celery(broker=...)` constructor arg
  and silently broke the §18.E lock.  Replaced with defensive
  `os.environ.pop()` calls.  No test consumed these values functionally.
- `backend/tests/test_worker_db_isolation.py` — removed test #4
  (`test_generation_tasks_use_make_worker_session`) which referenced the
  deleted module.  RETIRED banner in its place.  Also removed unused
  `import pytest` (ruff F401, pre-existing).

### Tests added (5 modules, 26 sub-tests, all PASS)
- `tests/test_celery_app_include_list.py` (4) — include-list exact match,
  V0-forbidden negative, V1 tasks discoverable at boot via
  `loader.import_default_modules()`, only-2-V1-tasks cardinality.
- `tests/test_celery_broker_db.py` (4) — broker path /1,
  endswith('/1'), redis scheme, equivalence with
  `shared.valkey._build_url_for_db`.
- `tests/test_celery_result_backend_db.py` (4) — result path /2,
  endswith('/2'), redis scheme, broker+result share host:port diff DB.
- `tests/test_task_reject_on_worker_lost.py` (5) —
  `task_reject_on_worker_lost=True`, companion `task_acks_late=True`,
  `worker_prefetch_multiplier=1`, JSON serialisation locked,
  `Asia/Kolkata` timezone.
- `tests/test_worker_user_revalidation.py` (9) — filter discipline
  (non-V1 task no-op), missing-user → `Reject(requeue=False)` for both
  V1 tasks, existing-user passthrough, kwarg extraction, malformed
  user_id rejected, DB-error fail-open, no-user_id no-op, whitelist
  cardinality.

### Decisions FLAGGED (D-flag log — not in locked architecture)
**D1 — VALKEY_URL → broker_url + result_backend derivation (§18.E).**
The §14 hand-off said *"add CELERY_BROKER_URL/CELERY_RESULT_BACKEND
fields to shared/config.py Settings"*; §18 chose VALKEY_URL derivation
per the §18.E explicit lock instead.  Avoids 2 new Settings fields +
matches §5.C factory allocation discipline.  Settings cleanup of the
hand-off-suggested fields NOT REQUIRED.

**D2 — §18.F enforcement layer = task_prerun signal handler, not
in-task call.**
§18.F LOCKED prose specifies `_validate_user_or_abort` lives inside
each `tasks.py`.  The §11.E + §14.E LOCKED CONSTRUCTED tasks.py files
do NOT include the call — adding it would breach §5.0 NON-NEGOTIABLE.
§18 enforces at the worker layer via a Celery `task_prerun` signal
handler scoped to the 2 V1 task names.  Same observable invariant;
LOCKED §11/§14 code untouched.

**D3 — V1 User model has NO `disabled` / `deleted_at` columns.**
§18.F prose mentions both conditions; V1 reduces to SELECT-by-id
existence check.  V1.5 ships soft-delete columns; the prerun handler
extends to `WHERE id=$1 AND disabled=False AND deleted_at IS NULL`
without a §18 amendment.

**D4 — Workers env-var pollution cleanup (conftest.py).**
Tests/conftest.py previously set `CELERY_BROKER_URL=/11` +
`CELERY_RESULT_BACKEND=/12` to avoid accidental GCP worker pickup;
Celery's env-var resolution order hijacked the §18.E lock.  Defensive
`os.environ.pop` replaces the `setdefault` calls.

**D5 — Local `_build_url_for_db` helper duplicates `shared.valkey`
copy.**
Rationale: avoid an import cycle between `workers/` and
`shared/valkey` + Celery wants URL strings not Redis clients.  Two
helpers are equivalence-tested.

**D6 — V1 `_user_exists_sync` fails OPEN on DB transient error.**
Spec §18.F doesn't prescribe behaviour on DB outage; we favour
task-body retry (the standard error path) over hard reject (which
loses an audit trail of WHY).  Tested.

**D7 — Whitelist hard-coded to `{image.precheck, export.xlsx}`.**
Adding a 3rd entry silently expands §18.F enforcement to a task that
hasn't been audited for the `(entity_id, user_id)` positional contract.
Tested.

### Acceptance gate (7 dispatch-brief criteria)
1. include list exactly `[image.tasks, export.tasks]`              — PASS
2. broker /1; result_backend /2                                    — PASS
3. `task_reject_on_worker_lost=True` preserved                     — PASS
4. Worker user re-validation implemented + tested (9 sub-tests)   — PASS
5. image.precheck + export.xlsx discoverable at boot              — PASS
6. Failure mode wiring (deferred to §11.E + §14.E ownership)      — PASS
7. 5 unit-test modules with 5+ sub-tests (delivered 5 mods/26 subs)— PASS

Plus universal: boot smoke PASS (34 routes); ruff clean on all 7
touched files; §18 regression 26/26 PASS; Wave 1-3 cross-cutting
regression 230 PASS + 3 PRE-EXISTING failures (test_worker_db_isolation
test #2 / test #3 / test #5 reference V0 `app/database.py` broken
import + `async_session_maker` legacy name — predate §18).

### Latent bugs CLOSED in this sub-session
**L18.1 — `settings.CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`
non-existent.**  Settings fields broke celery_app.py boot
(AttributeError at import).  CLOSED by VALKEY_URL derivation per §18.E.
The §14 hand-off entry "§18 settings: add CELERY_BROKER_URL/
CELERY_RESULT_BACKEND fields" is now SUPERSEDED — V1 uses VALKEY_URL
derivation; no Settings fields needed.

**L18.2 — workers/generation_tasks.py V0 leftover.**  Violated §3.I
canonical 2-file subtree.  CLOSED by deletion.

### Hand-offs queued
- **§19 test infrastructure**: V0-rot cleanup backlog includes
  `test_worker_db_isolation.py` 3 PRE-EXISTING failures (V0
  `app/database.py` with broken `from app.config import settings`
  import; legacy `async_session_maker` references vs V1
  `AsyncSessionLocal`; V0 `app/services/image_processor.run_pipeline`).
  Out of §18 scope; not a regression.
- **§20 deployment (Celery worker pod manifests)**: consume the locked
  `BROKER_URL` / `RESULT_BACKEND_URL` string-form invariants — broker
  on `/1`, results on `/2`; single Valkey instance.  Worker pod
  replica count per §18.C (image: 2 pods × concurrency=4 = 8 max) +
  §18.D (export: 2 pods × concurrency=2 = 4 max).  §20 picks whether
  to separate worker pools (4 total worker pods, 2 per queue) OR mix
  (2 pods × concurrency=4 with prefetch=1 for fairness).
- **V1.5 User model migration**: add `disabled BOOL DEFAULT false`,
  `deleted_at TIMESTAMPTZ NULL`.  The §18.F task_prerun handler
  extends to `WHERE id=$1 AND disabled=False AND deleted_at IS NULL`
  without requiring a §18 amendment.
- **API routes builder**: the §14 `service.initiate_export` enqueue
  pattern was `export_xlsx_task.delay(str(export.id), str(user_id))`.
  §18 confirms this is the correct pattern; no settings change needed.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §18 Celery wiring CONSTRUCTED | project | celery_app.py rewritten 40→241 LOC; broker/result derive from VALKEY_URL via local _build_url_for_db; task_prerun signal handler enforces §18.F user re-validation without touching LOCKED §11/§14 tasks.py |
| §18-CELERY-D1 VALKEY_URL derivation | reference | broker = _build_url_for_db(settings.VALKEY_URL, 1); result_backend = _build_url_for_db(settings.VALKEY_URL, 2). NO CELERY_BROKER_URL/CELERY_RESULT_BACKEND Settings fields needed |
| §18-CELERY-D2 task_prerun signal handler | reference | @task_prerun.connect handler in workers/celery_app.py filters to {image.precheck, export.xlsx} whitelist; raises Reject(requeue=False) on missing user. §11/§14 LOCKED tasks.py NOT modified |
| §18-CELERY-D3 User model V1 fields | reference | V1 User has only (id, phone, email, plan, created_at, last_login_at). No disabled/deleted_at — V1.5 adds those + handler extension is forward-compat |
| §18-CELERY-D4 conftest env-var pollution | reference | tests/conftest.py CELERY_BROKER_URL=/11 + CELERY_RESULT_BACKEND=/12 setdefault calls REMOVED (replaced with os.environ.pop). Celery env-var resolution hijacked broker= constructor arg |
| §18-CELERY-D5 _build_url_for_db duplication | reference | Local copy in workers/celery_app.py mirrors shared.valkey copy; avoids import cycle + Celery wants URL strings. Equivalence guarded by test_broker_db_matches_shared_valkey_helper |
| §18-CELERY-D6 fail-open on transient DB error | reference | _user_exists_sync returns True on RuntimeError in _user_exists_async; task body retries via repo layer + Celery autoretry. §18.F observability rule |
| §18-CELERY-D7 whitelist cardinality lock | reference | _TASKS_REQUIRING_USER_REVALIDATION = frozenset({"image.precheck", "export.xlsx"}). Adding a 3rd entry silently expands enforcement; tested |
| Workers §3.I subtree | reference | workers/ MUST contain exactly __init__.py + celery_app.py. generation_tasks.py / image_tasks.py / scrape_tasks.py are all V0 leftovers; deletion is the correct cleanup |
| Celery env-var resolution order | reference | os.environ.get('CELERY_BROKER_URL') wins over Celery(broker=...) constructor arg. Document at celery/app/utils.py:103. Tests/conftest MUST NOT set these env vars or §18.E lock is silently bypassed |
| V0 pre-existing rot (V0 path scan) | reference | app/database.py exists with broken `from app.config import settings` import; legacy app.services.image_processor.run_pipeline still references async_session_maker. test_worker_db_isolation.py test #2/#3/#5 fail because of this. Out of §18 scope; §19 V0 cleanup backlog |
| §18 hand-offs | reference | §20 worker pod manifests consume BROKER_URL/RESULT_BACKEND_URL invariants; V1.5 User migration adds disabled+deleted_at columns (handler is forward-compat); §14 enqueue pattern `export_xlsx_task.delay(str(export.id), str(user_id))` confirmed |

---
