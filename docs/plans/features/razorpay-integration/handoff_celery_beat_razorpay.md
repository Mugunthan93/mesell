# INFRA hand-off — deploy the Celery `beat` process (Razorpay Wave 4)

**From:** `meesell-services-builder` (Razorpay Wave 4, session `mesell-razorpay-integration-backend-session-4`)
**To:** `meesell-infra-builder`
**Date:** 2026-06-19
**Branch:** `feature/razorpay-w4-reconcile` (PR base `feature/razorpay`)
**Status:** REQUIRED before the two Wave-4 periodic tasks can fire (they are inert without a beat process).

---

## What Wave 4 shipped (code half — DONE)

`backend/app/workers/celery_app.py` now carries the repo's **first `beat_schedule`**:

| beat entry | task name | cadence (Asia/Kolkata, `enable_utc=True`) | crontab |
|---|---|---|---|
| `billing-reconcile-every-6h` | `billing.reconcile` | every 6 hours (00/06/12/18 IST) | `crontab(minute=0, hour="*/6")` |
| `billing-trial-expiry-sweep-daily-0200` | `billing.trial_expiry_sweep` | daily 02:00 IST | `crontab(minute=0, hour=2)` |

The task bodies live in `backend/app/modules/iam/tasks.py` (registered via `celery_app.py` `include`).

## What infra MUST deploy (process half — TODO)

The `beat_schedule` registration is **inert** without a running `celery beat` process. The k8s `worker.yaml` currently runs only `celery -A app.workers.celery_app worker -Q celery,image-tasks` — there is **no beat process**.

Choose ONE:

1. **Dedicated single-replica beat Deployment** (preferred for prod):
   ```
   celery -A app.workers.celery_app beat -l info
   ```
   **MUST be `replicas: 1`** — two beat processes double-fire EVERY scheduled task.

2. **`-B` on a single worker** (acceptable for single-node K3s / V1.5 dev):
   ```
   celery -A app.workers.celery_app worker -B -Q celery,image-tasks
   ```
   Only acceptable when there is exactly ONE such worker replica (again: a 2nd `-B` worker double-fires).

## Double-fire safety net (already in code — belt-and-braces)

Both tasks acquire a **Valkey DB-0 singleton lock** (`billing:reconcile:lock` / `billing:trial_sweep:lock`, `SET … NX EX 600`, compare-and-delete release) at task start; if not acquired, the task no-ops. This protects against accidental double-beat even if the single-replica rule is violated. The task bodies are also idempotent (reuse the webhook monotonic/guard transitions; the trial sweep uses an audit-row marker), so a double-fire is state-safe.

## This is the 2nd razorpay infra item

The first is `RAZORPAY_WEBHOOK_SECRET` Secret-Manager population (Wave 1/2). No NEW secret or config is needed for Wave 4 — `RAZORPAY_KEY_ID`/`_KEY_SECRET` (adapter auth) + `VALKEY_URL` (lock + worker session) already exist.

## No other infra change

No new env var (cadence is founder-ruled, NOT env-tunable for V1.5). No `requirements.txt` change (`celery==5.4.0` provides built-in beat — do NOT add `redbeat`/`django-celery-beat`).
