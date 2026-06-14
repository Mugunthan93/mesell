# Handoff — image-tasks Celery queue (infra → backend)

**Opened:** 2026-06-12
**Session:** mesell-image-precheck-infra-session-1
**From:** meesell-infra-builder
**To:** meesell-backend-coordinator
**Feature:** image-precheck (Feature 5)
**Status:** CLOSED — RESOLVED 2026-06-12 (mesell-infra-tail-session-1)

## RESOLUTION (2026-06-12)

Backend landed `task_routes={"image.precheck":{"queue":"image-tasks"}}` in
`celery_app.py` (#143). Infra then activated the worker queue split: `worker.yaml`
args now carry `-Q celery,image-tasks` (BOTH queues named — image.precheck is
routed to image-tasks; export.xlsx has no route so it stays on the default
`celery` queue; once `-Q` is set Celery stops auto-consuming `celery`, so
omitting it would stall export.xlsx). Applied live to dev (server-dry-run clean).
Verified via `celery inspect active_queues`: both worker pods bind
`{celery, image-tasks}`. Delivered on `chore/infra-tail-image-queue` → develop
(founder-gated). This memo is CLOSED.

---

### Original request (historical)

## Request

image-precheck FEATURE_PLAN §Infra row 4 specifies a dedicated **`image-tasks`
Celery queue** at concurrency=4. Infra cannot wire this unilaterally without
breaking the pipeline.

## Why infra alone can't do it (as-built, verified 2026-06-12)

- `backend/app/modules/image/tasks.py:415` — `@shared_task(name="image.precheck", ...)`
  has **no `queue=` kwarg**.
- `backend/app/workers/celery_app.py` — **no `task_routes` / `task_queues`** config.
- So `image.precheck` publishes to the **default `celery` queue**, which the worker
  (`--concurrency=4`, no `-Q`) consumes. The pipeline works today.

If infra adds `-Q image-tasks` to the worker NOW, the worker consumes only `image-tasks`
while tasks still publish to `celery` -> the pipeline stalls.

## What backend needs to do (the unblock)

Add routing in `celery_app.py`:

    celery_app.conf.task_routes = {
        "image.precheck": {"queue": "image-tasks"},
    }

(or a `queue="image-tasks"` kwarg on the decorator).

## What infra already did this slice

- `k8s/worker.yaml`: kept `--concurrency=4`; left a **commented-out** `-Q image-tasks`
  scaffold + "uncomment after backend lands task_routes" note. No functional break.
- After backend merges routing to develop, infra opens a one-line follow-up micro-feature
  to uncomment `-Q image-tasks`.

## No SLA pressure

Pipeline is FUNCTIONAL today on the default queue. This is queue-isolation optimization,
not a blocker. Infra is waiting on backend; feature is unblocked meanwhile.
