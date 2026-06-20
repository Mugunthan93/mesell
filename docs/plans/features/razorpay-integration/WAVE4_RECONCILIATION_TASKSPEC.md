# Wave 4 — Reconciliation Celery Beat + Trial-Expiry Sweep + Integration Tests Task Spec (Razorpay Integration, V1.5)

**Feature slug:** `razorpay-integration`
**Wave:** 4 of 5 (RECONCILIATION / LOST-WEBHOOK RECOVERY + 14-DAY TRIAL-EXPIRY SWEEP + LIFECYCLE INTEGRATION TESTS)
**Target specialist:** `meesell-services-builder` (opus) — Celery tasks + reconciliation algorithm are business-logic + worker-layer, squarely this builder's lane (per the design §Agent lineup: "reconciliation Celery beat task" is listed under `meesell-services-builder`).
**Session name (dispatch header):** `mesell-razorpay-integration-backend-session-4`
**Authored by:** `meesell-backend-coordinator` (HYBRID step 1 — spec only, no code)
**Date:** 2026-06-19
**Parent design (LOCKED):** `docs/plans/features/razorpay-integration/RAZORPAY_INTEGRATION_SPEC.md` rev v4 (APPROVED 2026-06-18) §3 (state machine), §4.3 (out-of-order guards), §5 (`fetch_subscription`), §8 (idempotency/reconciliation/failure modes), §14 Wave 4; `docs/PRICING_LOCKED.md` v2.
**Predecessors (all BUILT, stacked on the integration branch):** `WAVE1_DB_TASKSPEC.md` (3 billing models + migration `f8fa7a36383f` + `users.trial_ends_at`), `WAVE2_ADAPTER_TASKSPEC.md` (6 adapter methods incl. `fetch_subscription` + idempotent webhook event router), `WAVE3_ROUTES_TASKSPEC.md` (`billing_router` + `core/plan_guard.py::resolve_entitlement` + `MeResponse.plan` widening + `start-trial`/`subscribe`/`cancel`/`subscription` endpoints).

---

## 0. CRITICAL GROUND-TRUTH — read first (verified against the live tree 2026-06-19)

Five facts the design spec does NOT state correctly for Wave 4 execution. All verified against the live tree (`git ls-tree` / `git show` on the actual branches), NOT the dispatch summary. The dispatch summary's phrase "merged/integrated into feature/razorpay" is **imprecise** — correct it before you start.

1. **BRANCH: build STACKED on `feature/razorpay-w3-billing` — NOT on `develop`, and NOT on a branch literally named `feature/razorpay`.** Verified:
   - `feature/razorpay` (the branch that literal name resolves to) **does NOT contain any billing work** — no `subscription.py`/`payment.py`/`webhook_event.py` models, no `f8fa7a36383f` migration. It is an unrelated/earlier branch. Do NOT use it.
   - The Wave 1+2+3 work is **stacked**: `feature/razorpay-integration/backend` (W1 models + migration + W2 adapter/router) → `feature/razorpay-w2-adapter` → **`feature/razorpay-w3-billing` is the most-advanced tip** and contains EVERYTHING Wave 4 consumes: the 3 billing models, migration `f8fa7a36383f`, all 6 adapter methods incl. `async def fetch_subscription(sub_id) -> RazorpaySubscription` (`adapters/razorpay.py:347`), the evolved idempotent webhook router with all `_handle_subscription_*` handlers (`modules/iam/service.py`), and `core/plan_guard.py::resolve_entitlement` (reads `(users.plan, users.trial_ends_at, subscriptions.status, current_period_end)`).
   - **Cut your Wave 4 work on `feature/razorpay-w3-billing`** (continue it). `git fetch origin && git checkout feature/razorpay-w3-billing && git pull` before starting. Confirm `backend/app/modules/iam/billing_router.py`, `backend/app/core/plan_guard.py` (with `resolve_entitlement`), and the three billing models are present in your working tree before writing any import. **If the lead has by then merged the W1–W3 stack into a single `feature/razorpay-integration` integration branch, the lead will tell you to branch off that instead — CONFIRM the base branch with the lead at dispatch (this is a coordination point because the W1–W3 stack is HELD at the founder gate, see §0.5).**

2. **NO MIGRATION IN WAVE 4 (re-verified).** The current single Alembic head on the stacked branch is **`f8fa7a36383f`** (chain: `935e55b4852c → a1b2c3d4e5f6 → f31c75438e61 → b7c2e1a9d3f4 → c2d3e4f5a6b7 → f8fa7a36383f`, single-headed and linear — confirmed live). Wave 4 is **task + test logic ONLY**. Every column Wave 4 reads (`subscriptions.status`, `current_period_end`, `tier`, `razorpay_subscription_id`, `users.plan`, `users.trial_ends_at`) already exists from Wave 1. **Do NOT create a new Alembic revision.** If at dispatch you find you genuinely need a schema change (you should not — see §6 for the one borderline case, `trial_started_at`, which is ALREADY resolved without a new column), STOP and escalate to the lead — it means a Wave 1 gap and a re-gate, not a silent Wave 4 migration.

3. **NO Celery beat scheduler exists yet — Wave 4 introduces the FIRST periodic task.** Verified: `backend/app/workers/celery_app.py` registers `image.precheck` + `export.xlsx` only, has `task_routes` but **NO `beat_schedule`** and **NO `add_periodic_task`** anywhere under `backend/app/` (grep clean). `celery==5.4.0` is in `requirements.txt` — Celery's **built-in beat** is available with NO new dependency (do NOT add `redbeat`/`django-celery-beat`; the built-in static `beat_schedule` is correct for two fixed-cadence tasks). The k8s `worker.yaml` runs `celery -A app.workers.celery_app worker -Q celery,image-tasks` — there is **no `beat` process deployed**. Registering `beat_schedule` in `celery_app.py` is the code half; the **`celery beat` process must be run** for it to fire (a `k8s/worker.yaml` beat sidecar/Deployment or a `worker -B` flag) — that is an **INFRA hand-off (§8), NOT this builder's file**. The builder ships the `beat_schedule` registration + the task functions; the beat *process* is infra's.

4. **REUSE the webhook router's transition helpers — do NOT reinvent the state machine.** The W2/W3 webhook router already implements every transition Wave 4's reconciliation needs, with the exact §3.1/§4.3 guards. Wave 4 reconciliation must reuse them (or factor a shared helper), NOT write a parallel divergent copy. Specifically present on the stacked branch (`modules/iam/service.py`): `_get_subscription_by_rzp_id`, `_epoch_to_utc` (epoch-secs→UTC datetime), the GREATEST/monotonic `current_period_end` guard (lines ~1265–1269: `if sub.current_period_end is None or new_end > sub.current_period_end`), `_audit_business_effect` (writes the business `audit_events` row with a real `user_id`), and the halted/completed downgrade-to-`free` body (`user.plan = "free"` + `_audit_business_effect(event_type="billing.plan.downgraded")`). The cancelled handler deliberately leaves `users.plan` at tier until `current_period_end` and comments *"the Wave-4 reconciliation sweep does the eventual downgrade"* — that sweep is THIS wave.

5. **The W1–W3 stack is HELD at the founder gate (D1) and not on `develop`.** Wave 1's PR #300 targeted `develop` and is engineering-PASS but founder-held. Wave 4's PR therefore targets the integration flow (`feature/razorpay-w3-billing` → `feature/razorpay-integration` → develop), NOT `develop` directly. **Flag the exact PR target with the lead before opening** (known coordination point — same as Wave 2/3).

---

## 1. Scope of Wave 4 (exactly this, nothing more)

Three deliverables:

**A) Reconciliation Celery beat task** — a periodic task that recovers from LOST / missed / mis-ordered webhooks by pulling Razorpay's authoritative state via `adapter.fetch_subscription` for each non-terminal local subscription and reconciling local state, PLUS sweeping `cancelled`/`halted`/`completed` subs past `current_period_end` down to `free`. Reuses the W2/W3 webhook transition guards (§0.4).

**B) Trial-expiry sweep Celery beat task** — a periodic task that finds `free`-plan users whose `trial_ends_at` has passed (and who have no currently-entitled paid sub) and makes the trial→Free drop observable: fires the "trial ended" audit/notification trigger and optionally nulls `trial_ends_at`. NO Razorpay round-trip (the trial has no Razorpay object).

**C) Full-lifecycle integration test suite** — `backend/tests/test_razorpay_integration.py` covering the end-to-end billing flows the design §14 Wave 4 enumerates, plus the two new Wave 4 tasks. Runs against an **ISOLATED `*_test` DB** (the conftest guard already enforces this — see §9; the dev DB `meesell` was destroyed once this session by exactly this mistake).

**Out of scope for Wave 4 (explicit — DO NOT build):**
- NO Alembic migration / model change (Wave 1 owns the schema; §0.2).
- NO new API routes / routers / Pydantic schemas (Wave 3 owns those). Reconciliation + trial-sweep are **background tasks**, NOT endpoints. No OpenAPI regeneration (no contract endpoint added — §17 count unchanged).
- NO change to `core/plan_guard.py::resolve_entitlement` (Wave 3 built it; reconciliation reuses the SAME entitlement rules to decide "is this sub still entitled?" — read it, do not rewrite it). If you find a genuine resolver bug, flag to lead — do not silently patch a Wave 3 surface.
- NO change to the webhook router's `capture_razorpay_webhook` pipeline (Wave 2). You may REFACTOR a shared transition helper out of the webhook handlers so the reconciliation task and the webhook both call it — but that refactor must be **behaviour-preserving** for the webhook path and re-prove the Wave 2 webhook tests still pass.
- NO `start-trial`/`subscribe`/`cancel`/`subscription` endpoint change (Wave 3).
- NO new typed exception in the LOCKED 8-class `iam` inventory (§7.G). Background tasks log + retry on transient failure; they do not raise wire-facing exceptions.
- NO frontend, NO legal, NO AI work. The **`celery beat` process deployment** is INFRA (§8 hand-off), not this builder's code — the builder only registers `beat_schedule` in `celery_app.py`.

---

## 2. Conventions to follow (verified against the live tree)

- **New task module file:** `backend/app/workers/billing_tasks.py`. ⚠️ **§3.I canonical 2-file subtree note:** `BACKEND_ARCHITECTURE.md §3.I` documents `app/workers/` as a LOCKED canonical 2-file subtree (`__init__.py` + `celery_app.py`), and the V1 task bodies live in `modules/<name>/tasks.py` (e.g. `image/tasks.py`, `export/tasks.py`) — NOT in `workers/`. **To respect that convention, the reconciliation + trial-sweep task bodies SHOULD live in a module `tasks.py`, namely `backend/app/modules/iam/tasks.py`** (new file — the `iam` module owns billing/subscription state), and `celery_app.py`'s `include=[...]` list adds `"app.modules.iam.tasks"`, mirroring how `image.tasks`/`export.tasks` are registered. **The `beat_schedule` dict + the `include` addition go in `celery_app.py`** (the only file authorised to mutate the Celery app config). **FLAG to the lead at PR time:** adding a 3rd task module to the `include` list + a `beat_schedule` to `celery_app.py` touches the §3.I + §18.B "exactly 2 task modules" canonical inventory — that is a **§7.3 LOCKED-section amendment** (founder-gate item). Default posture: build it in `modules/iam/tasks.py` + register in `celery_app.py`, and **flag the §3.I/§18.B inventory bump to the lead** so the lead carries it to the founder gate. Do NOT self-apply a LOCKED-arch-doc edit.
- **Task decorator + names:** `@celery_app.task(name="billing.reconcile")` and `@celery_app.task(name="billing.trial_expiry_sweep")` — dotted names mirroring `image.precheck` / `export.xlsx`. Both tasks take NO per-user args (they are sweeps that query their own work set) — so they are EXEMPT from the §18.F `task_prerun` user-revalidation handler (that handler filters to `image.precheck`/`export.xlsx` by name and no-ops for anything else — verified `celery_app.py:_TASKS_REQUIRING_USER_REVALIDATION`). Do NOT add these task names to that frozenset.
- **Async-in-Celery pattern:** the existing tasks run async DB work inside the sync Celery worker via `asyncio.run(...)` over a `make_worker_session()` (NullPool) session — see `celery_app.py::_user_exists_async` for the exact precedent (`from app.shared.database import make_worker_session`). Both Wave 4 tasks are sync Celery task functions whose body does `asyncio.run(_reconcile_async())` / `asyncio.run(_trial_sweep_async())`, each opening `async with make_worker_session() as session:`. Do NOT use `AsyncSessionLocal` in the worker (cross-loop bug — documented in `celery_app.py`).
- **Reuse, don't reinvent:** import and call the W2/W3 service helpers (`_get_subscription_by_rzp_id`, `_epoch_to_utc`, `_audit_business_effect`, the GREATEST period guard, the resolve-entitlement rules) from `modules/iam/service.py` / `core/plan_guard.py`. Where a needed helper is currently a private webhook-handler-local block, factor it into a small shared function in `iam/service.py` and have BOTH the webhook handler and the reconciliation task call it (behaviour-preserving refactor — re-run Wave 2 tests).
- **Credentials via `settings` only** — the adapter already does this; the task never touches `os.getenv`.
- **No secrets/PII in logs** — log `subscription_id` (Razorpay id), `event`/`status`, counts, durations — NEVER customer email/phone (§9 of design). The reconcile task pulls `RazorpayCustomer.email`/`contact` ONLY if it must (it should not need to — `fetch_subscription` is enough); never log it.
- **`from __future__ import annotations`**; stdlib → third-party → local import blocks; `logger = logging.getLogger(__name__)`.

---

## 3. Part A — Reconciliation task (`billing.reconcile`)

### 3.1 Purpose

Safety net for any webhook that Razorpay delivered but we missed (we 5xx'd / were down / event permanently lost) or applied out of order. It makes Razorpay the authoritative source: for each local subscription that could still drift, pull Razorpay's truth and converge local state — using the **same idempotent/monotonic guards as the webhook router** so it never fights the webhook path.

### 3.2 Cadence (FOUNDER DECISION NEEDED — see §10 R1)

**Recommendation: every 6 hours** (`crontab(minute=0, hour="*/6")`). Rationale: Razorpay's own webhook retry window spans hours/days, so a frequent reconcile is redundant and burns `fetch_subscription` API calls; a 6-hourly pass closes any permanently-lost-webhook gap well within a billing cycle while keeping Razorpay API volume tiny (one `fetch_subscription` per non-terminal sub per pass). The design §8 says "daily" for the divergence sweep; **6h is a tightening of that** for faster drift recovery — flag the exact cadence to the founder (R1). A nightly (`hour=2`) pass is the conservative fallback that matches the design's literal "daily".

### 3.3 Query scope (which subscriptions get reconciled)

Two disjoint work sets in ONE task pass:

**Set 1 — Razorpay round-trip reconcile (non-terminal, Razorpay-backed subs):**
- `SELECT * FROM subscriptions WHERE razorpay_subscription_id IS NOT NULL AND status IN ('created','authenticated','active','past_due','halted')`.
- EXCLUDE LTD rows (`razorpay_order_id IS NOT NULL` / `current_period_end IS NULL` perpetual sentinel / `tier='ltd'`) — LTD is a one-time Orders purchase with no subscription object to fetch; never call `fetch_subscription` on it.
- EXCLUDE terminal `cancelled`/`completed`/`expired` from the round-trip (no point re-fetching a dead sub) — but they ARE handled by Set 2 below.
- For each: `rzp = await adapter.fetch_subscription(sub.razorpay_subscription_id)`; map `rzp.status` (Razorpay vocabulary) → our status via the SAME §3.1 table the webhook uses; converge:
  - `current_period_end`: set via **GREATEST(local, `_epoch_to_utc(rzp.current_end)`)** — monotonic, never rewind (reuse the webhook guard).
  - `status`: apply the §3.1 guarded transition (e.g. Razorpay says `active` but we have `created`/`past_due` → activate + grant `users.plan=tier` + write `audit_events`; Razorpay says `halted` but we have `active` → downgrade `users.plan='free'` + audit). NEVER re-activate a locally-`cancelled` sub (Razorpay won't report it active anyway, but guard regardless).
  - Idempotency: if local already equals Razorpay's truth, no-op (no write, no audit) — the common case.

**Set 2 — local-clock terminal sweep (no Razorpay call needed):**
- `SELECT * FROM subscriptions WHERE status IN ('cancelled','halted','completed') AND current_period_end IS NOT NULL AND current_period_end < now()` → the seller's paid period has ended → **downgrade `users.plan='free'`** (reuse the halted-handler downgrade body) + write a `billing.plan.downgraded` `audit_events` row, IF the user is not already `free` and has no OTHER currently-entitled sub. This is the eventual-downgrade the cancelled handler defers to Wave 4 (§0.4). Guard: do NOT downgrade a user who has a *different* active sub (re-check via the same `resolve_entitlement`/`_subscription_is_entitled` predicate Wave 3 built — don't downgrade someone who upgraded into a new sub).

### 3.4 Algorithm (the exact pass)

```
async def _reconcile_async():
    async with make_worker_session() as session:
        # --- Set 1: Razorpay round-trip ---
        subs = await fetch_non_terminal_razorpay_subs(session)   # the §3.3 Set 1 query
        for sub in subs:
            try:
                rzp = await razorpay_adapter.fetch_subscription(sub.razorpay_subscription_id)
            except RazorpayAdapterError as exc:
                logger.warning("reconcile: fetch failed sub=%s: %r (skip, retry next pass)", sub.razorpay_subscription_id, exc)
                continue                                          # per-sub isolation: one failure never aborts the pass
            await reconcile_one(session, sub, rzp)                # reuse §3.1 webhook transition guards
        # --- Set 2: local terminal sweep ---
        ended = await fetch_terminal_subs_past_period(session)    # the §3.3 Set 2 query
        for sub in ended:
            await downgrade_if_no_other_entitlement(session, sub) # reuse halted-downgrade body + Wave3 entitlement predicate
        await session.commit()
    logger.info("reconcile: done set1=%d set2=%d converged=%d downgraded=%d", ...)
```

- **Per-sub isolation:** a `fetch_subscription` failure or a single bad row MUST NOT abort the whole pass — `try/except` per sub, log + continue. Transient Razorpay outages are caught next pass.
- **Commit posture:** either one commit at the end (simpler, all-or-nothing per pass) OR commit-per-sub (more resilient, partial progress survives a crash mid-pass). **Recommend commit-per-sub** (each sub's convergence is independent + idempotent, so partial progress is safe and a crash doesn't lose all work). Builder's choice — flag which you chose and why.
- **Idempotency / no fighting the webhook:** because every write reuses the SAME guarded transition + GREATEST monotonic period guard as the webhook, a reconcile and a concurrent webhook for the same sub converge to the same state regardless of order. Reconcile NEVER does anything a correct webhook wouldn't — it only fills gaps. No double-grant (status already at target → no-op), no period rewind (GREATEST), no re-activate-cancelled (guard).

### 3.5 Locking / avoiding double-processing (FOUNDER/LEAD note — see §10 R3)

A single beat process firing one task at the configured cadence is the simple case (no overlap if the pass finishes inside the cadence interval). To be robust against (a) two beat processes accidentally deployed, (b) a pass running longer than its interval, add a **Valkey advisory lock**: `SET billing:reconcile:lock <token> NX EX <ttl>` at task start (DB 0, the sessions/locks DB per CLAUDE.md mapping); if not acquired, the task no-ops with an INFO log (another pass is running). Release on completion. TTL = a few × the expected pass duration (e.g. 600s). This mirrors a standard Celery singleton-task pattern and reuses the existing Valkey DB-0 client (`app.shared.valkey`). Same lock pattern for the trial sweep (`billing:trial_sweep:lock`). **Recommend implementing the lock** (cheap insurance against double-processing); flag if you defer it.

---

## 4. Part B — Trial-expiry sweep task (`billing.trial_expiry_sweep`)

### 4.1 Purpose

Make the 14-day app-side Pro trial → Free drop **observable**. Entitlement already reverts *implicitly* the instant the clock passes `trial_ends_at` (Wave 3's `resolve_entitlement` compares the timestamp live — verified `plan_guard.py:345` `if plan == "free" and user.trial_ends_at is not None`). The sweep exists to (a) fire the "your trial ended" audit/notification trigger and (b) optionally null `trial_ends_at` so the user isn't re-swept. NO Razorpay round-trip (the trial has no Razorpay object — §3.7 of design).

### 4.2 Cadence (FOUNDER DECISION — see §10 R2)

**Recommendation: daily at a quiet hour** (`crontab(minute=0, hour=2)` IST — `enable_utc=True` + `timezone="Asia/Kolkata"` are set in `celery_app.py`, so `hour=2` is 02:00 IST). A trial boundary is day-granular; an hourly sweep is wasteful. Daily is ample and matches "your trial ended this morning" UX. Flag the exact hour to the founder (R2).

### 4.3 Query + transition

- `SELECT id, plan, trial_ends_at FROM users WHERE trial_ends_at IS NOT NULL AND trial_ends_at < now() AND plan = 'free'` — only `free`-plan users still carrying an expired trial timestamp (a user who converted to paid has `plan != 'free'` and is excluded; their `trial_ends_at` is moot — paid entitlement wins per Wave 3).
- **Guard against double-processing the same user:** if you null `trial_ends_at` on sweep (recommended), the `WHERE trial_ends_at IS NOT NULL` clause makes the sweep idempotent — a swept user won't match next pass. If you do NOT null it, add a marker (e.g. an `audit_events` "already fired" check) to avoid re-firing the notification daily forever. **Recommend: null `trial_ends_at` after writing the audit row** — it is the cleanest idempotency and matches design §3.7 ("optionally nulls `trial_ends_at`"). This does NOT lose the "ever trialed" fact for abuse-guard purposes — see §6.
- **Transition (exact):** the user STAYS `plan='free'` (they were already `free` during the trial — the trial granted Pro *entitlement* via `plan_guard`, never a plan-string change). The sweep does NOT change `users.plan`. It:
  1. writes a business `audit_events` row `event_type="billing.trial.expired"` (real `user_id`, via `_audit_business_effect`) — the notification/analytics trigger.
  2. (recommended) `user.trial_ends_at = NULL`.
- Per-user isolation + commit-per-user (or batched commit) same posture as §3.4/§3.5; Valkey lock per §3.5.

### 4.4 Interaction with the one-trial-per-phone abuse guard (Q3)

Pricing v2 §8 Q3 (ruled 2026-06-18): **one trial per verified phone**. Wave 3's `start-trial` endpoint enforces this. ⚠️ **If the sweep nulls `trial_ends_at`, the "ever trialed" fact must survive elsewhere** so a user cannot re-trial after expiry. **Confirm with the lead how Wave 3 implemented the once-guard:** if Wave 3 keyed it on a separate `trial_started_at` column or an `audit_events`-history check, nulling `trial_ends_at` is safe. If Wave 3 keyed it ONLY on `trial_ends_at IS NOT NULL`, then nulling it would re-open the trial → in that case the sweep must NOT null `trial_ends_at` (use a different idempotency marker). **This is a Wave-3↔Wave-4 coupling — verify the Wave 3 once-guard mechanism before deciding whether to null.** (Inspect Wave 3's `billing_router.py` start-trial handler + plan_guard; the `start-trial` 409 logic reveals the once-key.) Do NOT add a `trial_started_at` column (that would be a Wave 4 migration — out of scope; if the once-guard genuinely needs a new column, that is a Wave 1/3 gap → escalate to lead, do not patch silently).

---

## 5. Part C — Integration test suite (`backend/tests/test_razorpay_integration.py`)

The broader lifecycle suite the design §14 Wave 4 enumerates, PLUS coverage of the two Wave 4 tasks. The Wave-2-scoped webhook-router unit tests already live in `test_razorpay_webhook_router.py` (do NOT duplicate them — this suite is the END-TO-END lifecycle + the new tasks). Follow existing `tests/` conventions: the rolled-back `AsyncSession` fixture, `pytestmark` integration marking where a DB is needed (Gate 4), signed webhook fixtures (HMAC-sign with a test `RAZORPAY_WEBHOOK_SECRET`). Mock the Razorpay SDK / adapter for `fetch_subscription` (return crafted `RazorpaySubscription` dataclasses — never hit live Razorpay).

### 5.1 Required coverage (design §14 Wave 4 list + Wave 4 tasks)

**Lifecycle (drives the webhook router end-to-end via signed events):**
1. **Full subscription lifecycle** — subscribe (creates `created` sub) → `subscription.activated` (active + `users.plan=tier`) → `subscription.charged` renewal (period extended, payment row) → `subscription.pending` (`past_due`) → `subscription.halted` (`users.plan='free'`).
2. **Cancel** — `subscription.cancelled` → status `cancelled`, `users.plan` stays at tier until `current_period_end`.
3. **LTD** — `payment.captured` for an LTD order → `users.plan='ltd'` permanent, LTD sub `status='active'` + `current_period_end IS NULL`; replay idempotent.
4. **Starter** — `subscription.activated` for a `starter`-tier sub → `users.plan='starter'`; `resolve_entitlement` returns `"starter"` with the 150-SKU cap (assert against `plan_guard`).
5. **Annual** — `pro_annual`/`business_annual` subscribe→activate path resolves to the right effective entitlement.
6. **Upgrade-immediate / downgrade-at-period-end** — `subscription.updated` upgrade lands new tier immediately; downgrade lands at next-cycle `charged` (F4).
7. **Idempotent replay** — same signed event twice → zero double side effects.
8. **Out-of-order guard** — late older `charged` does not rewind `current_period_end` (GREATEST); `charged` after `cancelled` does not re-activate.
9. **Signature-fail 401** — bad signature → `WebhookSignatureInvalidError`, no state mutation.

**Trial (NO Razorpay):**
10. **Trial grant** — `start-trial` → `trial_ends_at` set, `resolve_entitlement` returns `"pro"` while `now() < trial_ends_at` though `plan='free'`.
11. **Trial expiry sweep** — set `trial_ends_at` in the past, run `billing.trial_expiry_sweep` (call the async body directly with a test session) → `billing.trial.expired` audit row written, `trial_ends_at` nulled (if that's the chosen impl), `users.plan` STILL `'free'`, entitlement reverts to `"free"`. Idempotent: a 2nd sweep is a no-op (no match).
12. **Trial→pay supersede** — a trialist who subscribes: paid entitlement wins over the (still-set) trial; after activation `resolve_entitlement` returns the paid tier.

**Reconciliation (Wave 4 task):**
13. **Lost-webhook recovery** — local sub stuck at `created`/`past_due`; mock `fetch_subscription` to return Razorpay `active` with a `current_end` → run `billing.reconcile` async body → local converges to `active` + `users.plan=tier` + `current_period_end` set + `audit_events` written.
14. **Reconcile is idempotent / no-op when already converged** — local already matches Razorpay → reconcile writes nothing (assert no new audit row, status unchanged).
15. **Reconcile monotonic period** — mock `fetch_subscription` returning an EARLIER `current_end` than local → `current_period_end` unchanged (GREATEST).
16. **Reconcile terminal sweep (Set 2)** — `cancelled` sub with `current_period_end < now()` → reconcile downgrades `users.plan='free'` + audit; a `cancelled` sub whose user has ANOTHER active sub is NOT downgraded.
17. **Reconcile skips LTD** — an LTD row (`current_period_end IS NULL`, `razorpay_subscription_id IS NULL`) is never passed to `fetch_subscription` (assert the mock is not called for it).
18. **Reconcile per-sub isolation** — make `fetch_subscription` raise for one sub → that sub is skipped, the OTHER subs in the pass still reconcile (the raise does not abort the pass).

### 5.2 Test invocation of the tasks

Call the async task bodies directly (`await _reconcile_async(session)` / `await _trial_sweep_async(session)`) with the test rolled-back session — do NOT spin a real Celery worker or beat in tests. Patch the module-level `razorpay_adapter` (or its `fetch_subscription`) with an `AsyncMock` returning crafted `RazorpaySubscription` dataclasses. The Valkey lock (§3.5) should be a no-op / patched in tests (or use the test fakeredis the suite already uses).

---

## 6. The `trial_started_at` / once-guard question (RESOLVED — no migration)

The design §7.4a floated *"a separate `trial_started_at` if 'ever trialed' must be distinguished from 'currently trialing'."* **Wave 4 does NOT add this column.** Resolution path (verify against Wave 3 at dispatch, §4.4): the one-trial-per-phone guard is Wave 3's `start-trial` responsibility and is keyed on either (a) a Wave-3 column already added, or (b) an `audit_events`-history lookup (`billing.trial.started` rows are permanent and keyed to `user_id`/phone). Either way the "ever trialed" fact is durable WITHOUT a new Wave 4 column, so the sweep can safely null `trial_ends_at`. **If, at dispatch, you discover Wave 3 keyed the once-guard solely on `trial_ends_at IS NOT NULL` (so nulling re-opens the trial), do NOT null it in the sweep — use an audit-row idempotency marker instead — and flag the design wrinkle to the lead.** No schema change either way.

---

## 7. Typed-exception / config posture

- **NO new `iam` exception.** Background tasks do not raise wire-facing exceptions; they log + skip + retry next pass. The LOCKED 8-class `iam/exceptions.py` inventory is untouched.
- **NO new config.** `RAZORPAY_KEY_ID`/`_KEY_SECRET` (adapter auth) + `VALKEY_URL` (lock + worker session) all exist. The `beat_schedule` cadence constants live in `celery_app.py` as literals (or a tiny module constant) — NOT new env vars (cadence is founder-ruled, not env-tunable for V1.5). If the founder wants cadence env-tunable later, that's a follow-up.
- **`requirements.txt`** — NO change. `celery==5.4.0` provides built-in beat; no `redbeat`/`django-celery-beat`.

---

## 8. Branch + PR + hand-offs

- **Branch:** continue on `feature/razorpay-w3-billing` (the most-advanced stacked tip — §0.1). `git fetch && git checkout feature/razorpay-w3-billing && git pull` first. **Confirm the base branch + PR target with the lead before opening** (the W1–W3 stack is founder-held; the lead may have consolidated to a `feature/razorpay-integration` integration branch by your dispatch — §0.1/§0.5).
- **PR target:** the integration flow (group branch → `feature/razorpay-integration` → develop). NOT `develop` directly (founder owns integration→develop, D1).
- **PR template:** fill `.github/PULL_REQUEST_TEMPLATE/backend.md` COMPLETELY — no `<>` placeholders. Required:
  - State **"NO migration this wave"** with the verified single head `f8fa7a36383f`.
  - Modules/files touched: `app/modules/iam/tasks.py` (NEW), `app/workers/celery_app.py` (`include` + `beat_schedule`), possibly a behaviour-preserving shared-helper refactor in `app/modules/iam/service.py`, `backend/tests/test_razorpay_integration.py` (NEW).
  - Contract changes: **NONE** — no endpoint added, OpenAPI NOT regenerated.
  - Cross-module check: tasks live in `iam` + `workers`, touch only `iam`/`shared.models`/`adapters`/`core.plan_guard` (read) — **no new `✗ → ✓` in the §2.D matrix** (`iam` is the all-`✗` module). Confirm no new cross-module DOMAIN call.
  - **FLAG the §3.I / §18.B canonical-inventory bump** (3rd task module + `beat_schedule`) as a §7.3 LOCKED-section amendment for the lead → founder gate. Do NOT self-edit `BACKEND_ARCHITECTURE.md`.
  - Test evidence: paste the actual `pytest backend/tests/test_razorpay_integration.py` run output (run against an isolated `*_test` DB — §9).
  - "Session" block = `mesell-razorpay-integration-backend-session-4`.
- **First commit footer** carries the session name.
- **On PR open:** YOU (the specialist) set the `feature_board_backend.md` `razorpay-integration` row to `IN REVIEW` + clear `Current session` (D2). The lead then runs the HYBRID step-3 merge-gate review.
- **INFRA hand-off (REQUIRED — the beat process):** the `beat_schedule` registration is inert without a running `celery beat` process. Author a memo `handoff_celery_beat_razorpay.md` (lead writes it at dispatch, OR the builder flags it): infra must deploy the beat process — either a dedicated `k8s/worker.yaml` beat Deployment (`celery -A app.workers.celery_app beat -l info`) with a single replica (beat MUST be singleton — two beat processes double-fire), or add `-B` to one worker (simpler for single-node K3s; acceptable for V1.5). This is the SECOND infra item for razorpay (the first is `RAZORPAY_WEBHOOK_SECRET` SM population). The Valkey reconcile/trial lock (§3.5) is the belt-and-braces guard against accidental double-beat.

---

## 9. 🛑 TEST-DB-ISOLATION REQUIREMENT (NON-NEGOTIABLE — read before running ANY test)

**The dev DB `meesell` was destroyed once this session by running tests against it. Do NOT repeat this.**

- **The conftest already enforces a `*_test` guard** (`backend/tests/conftest.py:13-27`): it resolves `DATABASE_URL` from `TEST_DATABASE_URL` (default `...localhost:5432/meesell_test`) and **REFUSES to run if the resolved DB name does not end in `_test`** (raises before any fixture connects). This guard is exactly what protects the live dev DB. **Do NOT bypass, weaken, or monkeypatch it.**
- Run the suite via `make test` OR explicitly `TEST_DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5432/meesell_rzpw4_test pytest backend/tests/test_razorpay_integration.py` — a **disposable `*_test` DB** (provision one, e.g. `meesell_rzpw4_test`; NEVER `meesell`).
- **VERIFY before the run:** `SELECT current_database();` ≠ `meesell`. The first line of your test evidence MUST show the resolved test DB name ending in `_test`.
- **NEVER** run `pytest` with `DATABASE_URL` pointed at `meesell`, and **NEVER** run `make seed` / any seed script against the test DB or the dev DB during this wave.
- Valkey: use the standard `localhost:6379` (the suite's fakeredis or a disposable Valkey DB — NEVER flush a shared Valkey DB the dev stack uses; the reconcile/trial locks live in DB 0, so in tests patch the lock or point at a throwaway DB).
- CI Gate 4 (integration) provisions its own `meesell_test` schema (`conftest._provision_test_schema`) — the suite auto-runs there safely.

---

## 10. Founder/lead decisions needed before the build

| # | Decision | Recommendation | Why it matters |
|---|---|---|---|
| **R1** | Reconciliation cadence. | **Every 6 hours** (`crontab(minute=0, hour="*/6")`). Conservative fallback = nightly `hour=2` (matches design §8 literal "daily"). | Trades Razorpay `fetch_subscription` API volume vs drift-recovery latency. Tiny API cost either way (one fetch per non-terminal sub per pass). |
| **R2** | Trial-expiry sweep cadence. | **Daily at 02:00 IST** (`crontab(minute=0, hour=2)`). | Trial boundary is day-granular; hourly is wasteful. |
| **R3** | Beat process deployment + double-fire guard. | Single-replica beat Deployment OR `worker -B` (single-node K3s) — infra owns; **builder adds the Valkey singleton lock** (§3.5) regardless. | Two beat processes double-fire every task. Lock is cheap insurance. |
| **R4** | §3.I / §18.B canonical-inventory amendment. | Build in `modules/iam/tasks.py` + register in `celery_app.py`; **flag the inventory bump (2→3 task modules + first `beat_schedule`) to the founder via the lead** per §7.3. Do NOT self-edit the LOCKED arch doc. | `BACKEND_ARCHITECTURE.md §3.I/§18.B` lock "exactly 2 task modules, no `beat_schedule`" — Wave 4 legitimately needs a 3rd + beat; founder must ratify the amendment. |
| **R5** | Trial once-guard ↔ sweep null coupling (§4.4/§6). | Verify Wave 3's once-guard key; null `trial_ends_at` on sweep ONLY if the once-guard fact survives elsewhere (separate column or audit history). | Nulling `trial_ends_at` could re-open the trial if Wave 3 keyed the once-guard solely on it. No new column either way. |

---

## 11. Acceptance criteria (the lead's merge-gate checklist for this PR)

- [ ] `billing.reconcile` task: §3.3 two-set query scope; reuses webhook transition guards (`_get_subscription_by_rzp_id`, `_epoch_to_utc`, GREATEST period guard, `_audit_business_effect`, halted-downgrade body) — NOT a divergent re-implementation; per-sub `try/except` isolation; LTD rows excluded from `fetch_subscription`; idempotent / no-op when already converged.
- [ ] `billing.trial_expiry_sweep` task: §4.3 query (`free` + `trial_ends_at < now()`); writes `billing.trial.expired` audit; idempotent (no double-fire); `users.plan` unchanged (stays `free`); trial-once-guard coupling resolved per R5 (no new column).
- [ ] Both tasks live in `app/modules/iam/tasks.py`, registered via `celery_app.py` `include` + `beat_schedule`; dotted task names `billing.reconcile` / `billing.trial_expiry_sweep`; NOT added to the §18.F `task_prerun` frozenset; async body via `asyncio.run` + `make_worker_session` (NullPool) — NOT `AsyncSessionLocal`.
- [ ] Valkey singleton lock (§3.5) on both tasks (or deferral explicitly flagged).
- [ ] §3.I/§18.B canonical-inventory bump (3rd task module + first `beat_schedule`) FLAGGED to lead as a §7.3 founder-gate amendment; `BACKEND_ARCHITECTURE.md` NOT self-edited.
- [ ] NO new Alembic migration; head still `f8fa7a36383f` (re-verified). NO model/schema change. NO new `iam` exception. NO new endpoint / OpenAPI regen. NO `requirements.txt` change.
- [ ] Any `iam/service.py` refactor is behaviour-preserving; Wave 2 webhook-router tests (`test_razorpay_webhook_router.py`) STILL pass.
- [ ] `core/plan_guard.py::resolve_entitlement` reused (read-only) to decide sub entitlement in the Set-2 downgrade guard — NOT rewritten.
- [ ] Tests §5.1 items 1–18 present and PASSING against an isolated `*_test` DB; test-evidence first line shows the resolved DB name ends in `_test`; CI Gates 1/2/3 green; Gate 4 result pasted.
- [ ] No secrets/PII in logs (ids + status + counts only).
- [ ] PR template fully filled; session block = `mesell-razorpay-integration-backend-session-4`; board row `IN REVIEW`; branch/target coordination with the lead confirmed (§8); INFRA beat-process hand-off memo raised.
- [ ] Zero out-of-scope changes.
```
