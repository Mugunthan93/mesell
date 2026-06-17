# Runbook — Image Pre-check Pipeline Troubleshooting

**Owner:** `meesell-infra-builder` (infra lead)
**Feature:** image-precheck — Feature 5 of 9
**Scope:** diagnosing a stuck/failed image pre-check Celery job, re-enqueuing,
verifying GCS tenant isolation (D2 Gate 3), and cost monitoring for the
`meesell-images` bucket.
**Companion docs:** `docs/plans/features/image-precheck/FEATURE_PLAN.md`,
`docs/BACKEND_ARCHITECTURE.md §11` (image module), `§18` (Celery topology),
`docs/INFRASTRUCTURE_PLAYBOOK.md` (cluster + cost procedures).

> **Apply at OPERATIONS TIME.** Nothing here is executed during the manifests/docs
> authoring session. Every `kubectl` / `gcloud storage` command below is a live
> operation run by whoever owns the deploy/ops window. Always scope `kubectl` with
> `-n <namespace>` (dev | staging). `prod` does not exist until V1.5.

---

## 0. Pipeline at a glance (as-built, verified 2026-06-12)

```
POST /api/v1/products/{id}/images
  → image.service.upload_image  (ownership gate + format/size validation + GCS write)
  → enqueue Celery task  image.precheck  (image_id, user_id)
      ↳ modules/image/tasks.py:image_precheck_task  @shared_task(name="image.precheck",
        bind=True, max_retries=2, retry_backoff=True)
      ↳ 5-step pipeline: JPEG → RGB/CMYK → resolution → white-BG → watermark (vision)
      ↳ write_precheck_result → product_images.precheck_jsonb + status
GET /api/v1/products/{id}/images  → poll status: pending | ready | failed_precheck
```

**Key as-built facts (do not assume otherwise without re-checking the code):**

- **Queue:** the `image.precheck` task has NO `queue=` kwarg and `celery_app.py` has NO
  `task_routes` — so tasks publish to the DEFAULT `celery` queue. The worker Deployment
  runs `--concurrency=4` with NO `-Q` override and consumes that default queue. The
  dedicated `image-tasks` queue named in the feature plan is NOT wired yet (requires a
  backend `task_routes` change first — see `k8s/worker.yaml` queue-routing comment).
- **Celery transport (Valkey):** broker = `…/1`, result backend = `…/2`, app cache /
  budget counter = `…/0` (per `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` in
  `backend-secrets`).
- **Concurrency:** 4 (per FEATURE_PLAN §Infra row 4 — ~7,500 images/hr capacity).
- **Storage:** product images land in `gs://meesell-images` (separate from
  `gs://meesell-prod-assets`), path `{user_id}/{product_id}/{order_idx}.jpg`, 1-year
  DELETE lifecycle, `public_access_prevention=enforced`.
- **Feature flag:** `FEATURE_IMAGE_PRECHECK_ENABLED` — dev=true, staging=false until the
  D2 soak gates pass. When OFF, `POST …/images` → 404; `GET …/images` → empty list.

---

## 1. Inspect a stuck pre-check job

A job is "stuck" if `GET /api/v1/products/{id}/images` keeps returning `status="pending"`
well beyond the expected ~8s/image.

### 1.1 Worker health

```bash
kubectl -n dev get pods -l app=worker
kubectl -n dev logs deploy/worker --tail=120 | grep -iE "image.precheck|received|succeeded|failed|retry|ERROR"
```

Expected: worker pods `Running`; logs show `Task image.precheck[...] received` then
`succeeded`. If pods are `CrashLoopBackOff` / `ImagePullBackOff`, jump to
`INFRASTRUCTURE_PLAYBOOK.md §12.1` (pod won't start) and §12 (AR token refresh).

### 1.2 Is the worker consuming the queue?

```bash
# Active + reserved tasks across workers
kubectl -n dev exec deploy/worker -- celery -A app.workers.celery_app inspect active
kubectl -n dev exec deploy/worker -- celery -A app.workers.celery_app inspect reserved
kubectl -n dev exec deploy/worker -- celery -A app.workers.celery_app inspect stats | grep -iE "pool|concurrency"
```

Expected: `concurrency: 4`. If `inspect active` hangs or returns nothing, the worker
isn't connected to the broker — check `CELERY_BROKER_URL` and Valkey reachability (§1.3).

### 1.3 Broker / backend (Valkey) introspection

```bash
# Pending messages on the default queue (tasks enqueued but not yet picked up)
kubectl -n dev exec valkey-0 -- sh -c 'valkey-cli -a "$VALKEY_PASSWORD" -n 1 LLEN celery'
# Result backend keys (completed/failed task results)
kubectl -n dev exec valkey-0 -- sh -c 'valkey-cli -a "$VALKEY_PASSWORD" -n 2 KEYS "celery-task-meta-*" | head'
```

A growing `LLEN celery` with idle workers = workers not draining the queue (worker down,
or wrong `-Q`). `LLEN celery` = 0 but status still `pending` = the task ran but the
result write-back failed — check worker logs for the `write_precheck_result` step.

### 1.4 DB row state

```bash
kubectl -n dev exec postgres-0 -- psql -U meesell -d meesell -c \
  "SELECT id, status, left(precheck_jsonb::text, 80) AS precheck, created_at
   FROM product_images WHERE product_id = '<PRODUCT_UUID>' ORDER BY order_idx;"
```

`status='pending'` with old `created_at` and empty `precheck_jsonb` = the worker never
completed. `status='failed_precheck'` = pipeline ran and a check failed (expected for bad
images — read `precheck_jsonb` for which check).

---

## 2. Re-enqueue a failed / lost pre-check

Use when a job was lost (worker died mid-task, broker flushed) and the row is stuck
`pending`. Do NOT re-enqueue a legitimately `failed_precheck` row (the image genuinely
failed a check — the seller must re-upload).

```bash
# Re-enqueue by calling the task directly from a one-off python in the api pod.
kubectl -n dev exec deploy/api -- python -c "
from app.modules.image.tasks import image_precheck_task
image_precheck_task.delay('<IMAGE_UUID>', '<USER_UUID>')
print('re-enqueued image.precheck for <IMAGE_UUID>')
"
```

Then re-poll (§1.4). If it sticks again, the problem is upstream (worker/broker) — fix
that first (§1.1–1.3) before re-enqueuing.

---

## 3. GCS tenant-isolation verification (D2 Gate 3)

**This is the FEATURE_PLAN §D2 Gate 3 acceptance check** — it must pass (and the output
pasted in the infra self-review PR) before `meesell-infra-builder` flips the staging flag
to `true`.

The contract: an image uploaded by user A must live ONLY under `gs://meesell-images/{A}/`
and must NEVER appear under any other user's prefix. The path prefix is the tenant
boundary; `public_access_prevention=enforced` + uniform bucket-level access mean no object
is ever publicly reachable.

```bash
# 1. As user A, upload one image (via the API or the test harness). Note A's user_id (uuidA)
#    and a different user uuidB.
# 2. Confirm A's image exists under A's prefix:
gcloud storage ls "gs://meesell-images/<uuidA>/" --recursive
#    Expected: the uploaded object (…/<product_id>/<idx>.jpg).
# 3. Confirm A's image does NOT appear under B's prefix:
gcloud storage ls "gs://meesell-images/<uuidB>/" --recursive | grep "<uuidA>" \
  && echo "FAIL — cross-tenant leak" || echo "PASS — no cross-tenant object"
# 4. Confirm the bucket forbids public access (belt-and-braces):
gcloud storage buckets describe gs://meesell-images \
  --format="value(public_access_prevention,uniform_bucket_level_access.enabled)"
#    Expected: enforced  True
```

Gate 3 PASSES when step 3 prints `PASS — no cross-tenant object` and step 4 prints
`enforced  True`. Paste all four steps' output into the staging-flag-flip PR body.

---

## 4. Cost monitoring (`meesell-images` bucket)

Projected V1 footprint: up to **4 images × 10 MB = 40 MB per product** (per D1 — the
4-slot uniform rule). Standard-class storage in `asia-south1` is the dominant cost; the
1-year DELETE lifecycle bounds total accumulation.

```bash
# Current bucket size + object count (single source of truth for storage cost)
gcloud storage du -s gs://meesell-images
gcloud storage ls -r gs://meesell-images/** | wc -l    # rough object count

# Lifecycle confirmation (objects age out at 365 days)
gcloud storage buckets describe gs://meesell-images --format="json(lifecycle_config)"

# Project-wide billing budget (per INFRASTRUCTURE_PLAYBOOK.md §13)
gcloud beta billing budgets list \
  --billing-account=$(gcloud billing accounts list --format="value(ACCOUNT_ID)" | head -1)
```

**Rule of thumb:** 1,000 sellers × 40 MB = ~40 GB → well within asia-south1 standard
storage at a few rupees/GB-month. The image-precheck bucket is NOT a material cost driver
at V1 traffic. If `gcloud storage du -s` shows growth far beyond the seller-count
projection, suspect a re-upload loop (clients retrying failed uploads) or a missing
lifecycle expiry — re-confirm the lifecycle rule above.

Escalate per the playbook §13 thresholds (50% notify / 75% pause non-essential / 90% STOP)
against the project budget, not the bucket alone — GCS is a small slice of the total.

---

## 5. Cross-reference — flipping the staging flag (post-gate)

When all three D2 gates pass (watermark ≥85%, the 4 deterministic Pillow checks on the
20-image smoke fixture, and the §3 tenant-isolation check above), flip
`FEATURE_IMAGE_PRECHECK_ENABLED` to `true` in `k8s/overlays/staging/config.yaml` via a
one-line `feature/feature-flag/staging-image-precheck-on` micro-feature branch
(infra-only, no backend change). Validate `kubectl apply -k k8s/overlays/staging
--dry-run=server` clean, then apply. This is the D2 staging-promotion mechanism.
