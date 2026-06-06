# Sub-Session Prompt: §11 Module `image`
# Wave 5 of 10 — CONSTRUCTION (parallel-safe with §12 pricing + §13 dashboard)
# Specialist agents: meesell-api-routes-builder + meesell-services-builder + meesell-image-precheck-builder (AI track)
# Renames session to: meesell-backend-construction-11-image-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §11 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-api-routes-builder + meesell-services-builder + meesell-image-precheck-builder (AI track) agents operating in a dedicated construction sub-session for MeeSell §11 (Module `image`).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §11 Module `image` — 2 endpoints (POST upload 202 + GET poll 200) + Celery task wrapper for 5-step precheck
- Specialist agents: meesell-api-routes-builder (router + schemas) + meesell-services-builder (service + repository + tasks.py Celery wrapper + GCS path enforcement) + meesell-image-precheck-builder (AI track; owns 5-step precheck pipeline algorithm internals) + meesell-prompt-engineer collaboration on `watermark.v1` (already storage-structured in Wave 1 §6A; finalize content here)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-11-image-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §11 — A through M (esp. §11.B.1 POST 202 8-step flow incl. ownership gate + file validation + Pillow metadata read + slot uniqueness + GCS upload + repository insert + Celery enqueue; §11.B.2 GET 200 5-step flow; §11.C 6-method service surface incl. 4 cross-module surfaces; §11.D 7-method PRIVATE repository; §11.E Celery task `@shared_task(name="image.precheck", bind=True, max_retries=2)` with 9-step locked flow; §11.G 4 frozen dataclasses; §11.H 5 ImageError subclasses; §11.J cross-cutting incl. watermark INSIDE Celery task only, plan_guard NOT participating, signed URLs 1h TTL, audit `image.precheck.completed` direct ORM write; §11.K 5 unit + 3 integration tests).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §4 (core/), §5 (shared/), §6.D (gcs adapter 4 methods + path convention), §6A (ai_ops for watermark workload INSIDE Celery task only), §10 catalog (CONSTRUCTED Wave 4; consumes `assert_product_ownership`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §0 premise #3 (4-slot uniform rule — structural DB CHECK constraint), §2.5 (product_images DDL), §5.3 (precheck), §10.8 (GCS layout `gs://meesell-images/{user_id}/{product_id}/{image_idx}.jpg`).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (API design: multipart/form-data, max 10MB per image).

5. `.claude/agents/meesell-api-routes-builder.md`, `meesell-services-builder.md`, `meesell-image-precheck-builder.md`.

6. Memory files for all 3 specialists.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1 + Wave 2 + Wave 3 + Wave 4 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.C:

```
backend/app/modules/image/
├── __init__.py
├── router.py            # 2 endpoints
├── service.py           # 6-method service (incl. 4 cross-module: get_image_urls for catalog, get_image_bytes for export, write_precheck_result for Celery worker context, summary OPTIONAL for dashboard)
├── repository.py        # 7-method PRIVATE; scope_to_user; soft_delete_by_idx internal helper (catalog cascade + V1.5 re-upload — NOT exposed)
├── schemas.py           # ImageUploadResponse, ImageSummary, ImagesListResponse
├── domain.py            # ProductImage, ImageUrl, ImageStatusSummary, PrecheckResult frozen dataclasses
├── exceptions.py        # 5 ImageError subclasses per §11.H
└── tasks.py             # @shared_task(name="image.precheck", bind=True, max_retries=2); 9-step pipeline; sync task with asyncio.run for GCS+Gemini+DB
```

NOTE: `tasks.py` is one of only 2 modules with a `tasks.py` per §3.C (the other is `export`).

Plus: register `image_router` in `backend/app/main.py`. The `workers/celery_app.py` `include=[]` list gets populated with `"app.modules.image.tasks"` (final population in §18 Celery construction).

Locked invariants:
- 2 endpoints: `POST /api/v1/products/{id}/images` (202 ACCEPTED, 10/min/user rate limit), `GET /api/v1/products/{id}/images` (200, per-IP fallback only).
- 4-slot uniform rule (`idx ∈ {1,2,3,4}`) — structural DB CHECK constraint per `MVP_ARCH §2.5`. plan_guard NOT participating.
- GCS path: `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + `MVP_ARCH §10.8`.
- Signed URLs: 1h TTL.
- Watermark step is INFORMATIONAL, NOT BLOCKING per founder ruling: on `BudgetExceededError` → `precheck_jsonb.watermark_check = "skipped_budget"` AND overall status still `"ready"` if 4 deterministic Pillow-based steps pass.
- Watermark vision via `ai_ops.client.call_gemini(ctx, "watermark", ...)` INSIDE the Celery task only — backend route NEVER directly invokes AI.
- V1 = direct multipart through FastAPI per CLAUDE.md API design; V1.5 may add direct-to-GCS upload.
- Celery task is SYNC (`@shared_task`, NOT `async def`) with `asyncio.run(...)` for GCS+Gemini+DB internals — Celery V1 has no coroutine support.
- `image.precheck.completed` audit event written via direct ORM write inside service (worker has no request-close hook) — locked exception per §11.J + §15.E exception list.
- DELETE-image endpoint is NOT exposed in V1.

Construction protocol:

1. **Tests first** per §11.K (5 unit + 3 integration):

   **Unit** (`backend/tests/modules/image/`):
   - `test_ownership_gate_enforcement` — POST `/products/{other_user_product}/images` → 404 (`catalog.assert_product_ownership` first action; bytes never reach GCS).
   - `test_file_validation` — non-JPEG → 400 `validation.image.invalid_format`; > 10 MB → 400 `validation.image.too_large`; idx 5 → 400 `validation.image.invalid_idx`. Separate test methods.
   - `test_slot_uniqueness` — POST with idx=2 when existing non-deleted image at slot 2 → 409 `image.slot_occupied`.
   - `test_gcs_path_construction` — path EXACTLY `meesell-images/{user_id}/{product_id}/{idx}.jpg`. Verified via mock `adapters.gcs.upload_bytes` assertion.
   - `test_celery_task_enqueue` — `image_precheck_task.delay` called with correct args (`image_id`, `user_id`) after successful POST.

   **Integration** (`backend/tests/integration/test_image_*.py`):
   - `test_full_upload_poll_ready` — POST → poll GET until `status="ready"` (with timeout) → verify `precheck_jsonb` 5 keys: `jpeg_valid`, `color_space`, `resolution_pass`, `white_background`, `watermark_check`.
   - `test_watermark_budget_exhaustion` — mock `ai_ops.client.call_gemini` raises `BudgetExceededError` → verify `precheck_jsonb.watermark_check == "skipped_budget"` AND `status == "ready"` (informational, non-blocking).
   - `test_cross_module_url_fetch` — `catalog.service.get_preview` calls `image.service.get_image_urls` → verify returned `list[ImageUrl]` has signed URLs ordered by idx with `is_front=True` on idx=1 only.

   Fixtures: real Postgres + Valkey + GCS test bucket via dev tunnel; mocked `ai_ops.client.call_gemini` for watermark step.

2. **Implementation** per §11.B-§11.J. AI track's `meesell-image-precheck-builder` owns the 5-step pipeline algorithm internals (JPEG validity / RGB color space / resolution / white background detection / watermark detection); backend's `image/tasks.py` is the Celery wrapper around their pipeline class.

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT add a DELETE-image endpoint in V1.
- DO NOT skip `scope_to_user(user_id)` on any repository method.
- DO NOT import `catalog.repository` or `export.repository` — cross-module only via service.
- DO NOT import `adapters.gemini` — only `ai_ops.client.call_gemini` INSIDE the Celery task.
- DO NOT invoke `ai_ops.client.call_gemini` from `router.py` or `service.py` — watermark is Celery-task-only.
- DO NOT make watermark blocking — informational only; if budget exhausted, status still "ready".
- DO NOT make `tasks.py` async — Celery V1 is sync; use `asyncio.run(...)` for inside-task GCS/AI/DB calls.
- DO NOT expose `soft_delete_by_idx` via an endpoint in V1 (internal helper only).
- DO NOT add `plan_guard` to image endpoints (4-slot rule is structural DB constraint).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-api-routes-builder` — router + schemas.
- `meesell-services-builder` — service + repository + domain + exceptions + tasks.py Celery wrapper.
- `meesell-image-precheck-builder` (AI track) — 5-step precheck pipeline internals + watermark detection logic.
- `meesell-prompt-engineer` (AI track) — finalize `watermark.v1` content in `ai_ops/prompts/watermark_v1.py` (storage already structured in Wave 1 §6A).

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §11)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 2 endpoints mounted per §11.B.
2. `tasks.py` exists with `@shared_task(name="image.precheck", bind=True, max_retries=2)`.
3. `image/tasks.py` listed in `workers/celery_app.py` include list (defer final list to §18).
4. GCS path EXACTLY matches `meesell-images/{user_id}/{product_id}/{idx}.jpg` (grep + test).
5. `precheck_jsonb` has all 5 keys: jpeg_valid, color_space, resolution_pass, white_background, watermark_check.
6. Watermark budget exhaustion test PASS — `"skipped_budget"` + status `"ready"`.
7. `ai_ops.client.call_gemini` invoked ONLY in tasks.py, NOT in router.py or service.py (grep-verifiable).
8. 5 ImageError exceptions per §11.H with `validation_message_id` from §5A.
9. Direct ORM audit write for `image.precheck.completed` from worker.
10. 5 unit + 3 integration tests PASS per §11.K.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update all specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §11 image CONSTRUCTED ===
   Files created: modules/image/{8 files incl. tasks.py}; main.py mount; watermark_v1.py finalized
   Tests added: 5 unit + 3 integration
   Decisions made: <list>
   Hand-offs: §10 catalog already CONSTRUCTED (consumes get_image_urls); §14 export (consumes get_image_bytes); §18 celery_app.py include list update
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- GCS bucket not provisionable in dev/staging.
- Celery worker can't acquire DB session inside task (`asyncio.run` event loop edge case).
- Pillow library version incompatibility on the precheck pipeline.
- Watermark prompt false-positive rate > §6A.H 85% accuracy gate.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-11-image-1`
2. Read REQUIRED READING.
3. Confirm Wave 1 + Wave 2 + Wave 3 + Wave 4 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §11 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 5 of 10
- **Sequential dependency:** Wave 1-4 CONSTRUCTED (esp. §10 catalog for `assert_product_ownership`).
- **Parallel-safe?:** Yes — runs in parallel with §12 pricing (11-section-12-pricing-construction.md) + §13 dashboard (12-section-13-dashboard-construction.md). All 3 call catalog (locked by now); no inter-dependency between them.
- **Expected duration estimate:** ~10-14 hours.
- **Acceptance verification by master:** (1) `grep -rn "ai_ops.client.call_gemini" backend/app/modules/image/router.py backend/app/modules/image/service.py` returns nothing (Celery-task-only); (2) `grep -n "@shared_task" backend/app/modules/image/tasks.py` confirms task registration; (3) GCS path test PASS; (4) watermark budget exhaustion test PASS; (5) STATUS_BACKEND.md UPDATE block present.
