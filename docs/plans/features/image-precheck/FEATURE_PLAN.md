# Feature Plan — Image Pre-check (Feature 5)

**Feature slug:** `image-precheck`
**Session:** `mesell-image-precheck-planning-session-1`
**Date authored:** 2026-06-10
**Status:** PLAN READY — awaiting founder review
**Output of session:** This document. No production code was written.

**Drives:** `meesell-backend-coordinator` · `meesell-frontend-coordinator` · `meesell-ai-coordinator` · `meesell-infra-builder`
**Prerequisite:** `feature/catalog-form` must merge to `develop` first (image module depends on `catalog.service.assert_product_ownership()`).
**Can run parallel with:** `feature/ai-autofill` (no file contention, no contract overlap).

---

## Decisions

Founder answers recorded verbatim from `mesell-image-precheck-planning-session-1` on 2026-06-10.

### D1 — Scope confirmation (slot count)

**Answer:** 4 slots wins — amend V1 spec text.

The architecture at `BACKEND_ARCHITECTURE.md §11` is LOCKED (2026-06-05) at **4 slots** with three structural binders:

- DB-level constraint `CHECK (image_idx IN (1, 2, 3, 4))` per `MVP_ARCH §2.5` and `BACKEND_ARCHITECTURE.md §11.J`
- Pydantic `idx: int` accepted only in `[1, 2, 3, 4]` per §11.B.1
- `is_front` GENERATED column = `(order_idx == 1)` per §11.G
- Response shape `ImagesListResponse.images: list[ImageSummary] # 0-4 items` per §11.B.2

`V1_FEATURE_SPEC.md §F5` text still says "6 images max per product" and "Total upload size capped at 60 MB per product (6 × 10 MB)". The §F5 text is **stale relative to the architecture lock**. Resolution:

- **Architecture stays unchanged** — no §11 amendment.
- **V1_FEATURE_SPEC.md §F5 is amended inline** as part of this feature's PR by `meesell-backend-coordinator`: append an `AMENDMENT 2026-06-10` block (same pattern as the FE-D5 amendment from 2026-06-05) recording: 4 images max per product, 40 MB total upload cap per product (4 × 10 MB), `is_front` is the idx=1 slot. The original text is preserved with the amendment block below it for audit.
- The `meesell-image-precheck-builder` agent spec at `.claude/agents/meesell-image-precheck-builder.md` line 84 ("Total upload size capped 60 MB / product (6 × 10 MB)") is **also stale**. It is amended in the same PR by the ai lead as a one-line correction. NOT considered an architecture amendment — the agent spec is downstream of `V1_FEATURE_SPEC.md`.

No code change required from this decision. The architecture spec specialists work against was always 4 slots.

### D2 — Feature flag posture

**Answer:** `FEATURE_IMAGE_PRECHECK_ENABLED` — 3-gate staging promotion.

| Setting | Value | Where it lives |
|---|---|---|
| Flag name | `FEATURE_IMAGE_PRECHECK_ENABLED` | Backend env var per repo MASTER §3.2 |
| Dev default | `true` | `k8s/dev/api-deployment.yaml` |
| Staging default | `false` until 3 gates pass | `k8s/staging/api-deployment.yaml` |
| Behavior when OFF | `POST /api/v1/products/{id}/images` returns **404** (per repo MASTER §3.2 contract). `GET /api/v1/products/{id}/images` returns **empty list** `{images: []}` (does NOT 404 — sellers may have legacy images, the list endpoint is read-only). | `modules/image/router.py` checks `settings.FEATURE_IMAGE_PRECHECK_ENABLED` at function entry |
| Frontend gating | `/catalogs/:id/images` route guard returns to `/catalogs/:id/edit` with toast "Image upload is coming soon" when the flag is OFF. Read via `core/services/feature-flags.service.ts` (V1: build-time env; V1.5 may add remote config) per repo MASTER §3.2 | `app.routes.ts` + `featureFlagGuard` |

**Staging promotion gates (all 3 must pass for `meesell-infra-builder` to flip staging to `true`):**

1. **Gate 1 — Watermark ≥ 85% on 30-image golden set.** `pytest tests/eval/watermark/test_accuracy.py` reports `aggregate_metric ≥ 0.85`. Last green run within the previous 24h (per `feature_board_ai.md` rule and ai-coordinator §6A.H).
2. **Gate 2 — 4 deterministic Pillow checks pass on 20-image smoke fixture.** A 10-known-bad / 10-known-good fixture under `tests/eval/precheck_smoke/` (not the watermark golden set — separate, smaller, focused on JPEG/RGB/resolution/white-BG only). Acceptance: all 10 bad images report `status="failed_precheck"`; all 10 good images report `status="ready"`; per-image total Pillow time ≤ 2s.
3. **Gate 3 — GCS tenant isolation verified.** Upload one image as user A; query `gsutil ls gs://meesell-images/{userB_uuid}/` — must return zero matches (the user_id prefix must NOT appear under the wrong user). Verification command + paste in `meesell-infra-builder` self-review PR body.

When all 3 gates pass, infra-builder flips the staging env var via a `feature/feature-flag/staging-image-precheck-on` micro-feature branch (one-line K8s manifest change, infra-only). No code change in the backend; just the env-var flip.

**Flag removal:** When the feature ships to `main` per repo MASTER §3.2 ("The feature flag is removed when the feature ships to `main`"), `meesell-backend-coordinator` and `meesell-frontend-coordinator` each open a follow-up `feature/cleanup-flag-image-precheck` branch to delete the flag check + the env var. This is **tech debt to address by V1.5 launch** — not a blocker for V1 ship.

### D3 — Priority ordering vs sibling features

**Answer:** After `catalog-form` merges to `develop` — `image-precheck` and `ai-autofill` run in parallel.

```
Sprint timeline (founder's plan):
  Sprint N:    catalog-form (Feature 3) ───► develop
  Sprint N+1:  image-precheck (Feature 5) ─┐
               ai-autofill (Feature 4)    ─┴──► develop (both ship same sprint)
```

**Why this works (no contention):**

| Surface | image-precheck touches | ai-autofill touches | Conflict? |
|---|---|---|---|
| `app/modules/image/` (all files) | YES (NEW module) | NO | None — greenfield for image |
| `app/modules/catalog/service.py` | NO (only READS `assert_product_ownership`) | YES (adds `autofill_product` method) | None — image is a consumer, not a writer |
| `app/adapters/gcs.py` | YES (adds 3 methods) | NO | None — single consumer |
| `app/ai_ops/client.py` | NO (only consumes existing API) | NO (only consumes existing API) | None — both consume the locked §6A.C surface |
| `app/ai_ops/prompts/` | YES (`watermark_v1.py` NEW) | YES (`autofill_v1.py` NEW) | None — different file per workload |
| `app/ai_ops/prompt_registry.py` | YES (register `watermark.v1`) | YES (register `autofill.v1`) | YES (line 1 edit) — resolved via `feature/image-precheck/ai` rebasing on whichever lands first |
| `tests/eval/` | YES (`watermark/`) | YES (`autofill/`) | None — different subdirectory |
| Daily ₹500 AI cap (shared Valkey counter) | Watermark vision calls (₹0.05-0.08 per image) | Autofill text calls (≤₹0.05 per call) | None at code level — joint budget consumption observed in `ai_ops.budget_cap`; both implement the §6A.F graceful fallback (autofill returns 503; watermark marks "skipped_budget") |

The one micro-contention is the prompt registry index entry (both add a workload entry). Resolution: whichever feature merges to `feature/{name}` first wins; the other rebases on the new `develop` tip. Two-line file, one-line conflict, trivial.

**Cost ceiling note (carried into Risk Register):** the ai-coordinator merge gate locks per-call cost at ≤ ₹0.05 (per spec §6A.H + `meesell-ai-coordinator.md` Stop Conditions). Vision calls (watermark) are multimodal and run ~₹0.06-0.08 in practice. If the watermark per-call cost exceeds ₹0.05, the ai lead MUST escalate to founder for an exception or for a cost-ceiling amendment SPECIFIC to the vision workload (e.g., "text workloads ≤ ₹0.05, vision workloads ≤ ₹0.08"). Until then, ≤ ₹0.05 is the merge gate; an overshoot blocks the PR.

**AMENDMENT 2026-06-11 — vision cost ceiling settled:** Founder approved vision-specific exception. Merge gate for watermark/vision calls: ≤ ₹0.08 (not ≤ ₹0.05). Text workloads remain ≤ ₹0.05. The ai-coordinator will verify watermark call cost ≤ ₹0.08 per call in the PR gate decision comment. R3 is RESOLVED — no longer blocking.

---

## Agent lineup

| Lead (model) | Specialists dispatched (model) | What each specialist builds |
|---|---|---|
| `meesell-backend-coordinator` (opus) | `meesell-database-builder` (sonnet) | `shared/models/product_image.py` ORM model + Alembic migration creating `product_images` table with 4-slot CHECK constraint + `is_front` GENERATED column |
| | `meesell-services-builder` (opus) | `modules/image/service.py` (6-method surface) + `repository.py` (7-method MODULE-PRIVATE) + `domain.py` (4 frozen dataclasses) + `exceptions.py` (5 ImageError subclasses) + `tasks.py` Celery wrapper + amends `adapters/gcs.py` (3 methods) + amends `i18n/messages_en.py` (5 keys) |
| | `meesell-api-routes-builder` (sonnet) | `modules/image/router.py` (2 endpoints) + `schemas.py` (3 Pydantic models) + amends `main.py` (mount router) + unit + integration tests |
| `meesell-ai-coordinator` (opus) | `meesell-prompt-engineer` (opus) | `ai_ops/prompts/watermark_v1.py` (prompt template + Pydantic response schema) + 30-image golden fixture under `tests/eval/watermark/` + eval runner + parser tests + register entry in `ai_ops/prompt_registry.py` |
| | `meesell-image-precheck-builder` (opus) | The 5-step precheck pipeline logic INSIDE `modules/image/tasks.py` — JPEG check, RGB/CMYK check, resolution check, white-BG heuristic, watermark vision wrapper. Co-owns `tasks.py` with services-builder per §11.A seam definition (backend owns the Celery shell; AI owns the pipeline logic). Also authors the 20-image deterministic smoke fixture under `tests/eval/precheck_smoke/`. |
| `meesell-frontend-coordinator` (opus) | `meesell-angular-service-builder` (sonnet) | `core/services/image.service.ts` (multipart upload + backoff polling) + amends `app.routes.ts` (register `/catalogs/:id/images`) + `featureFlagGuard` integration for `FEATURE_IMAGE_PRECHECK_ENABLED` |
| | `meesell-angular-component-builder` (sonnet) | `features/images/image-uploader.component.ts` (drag-drop, 4-slot grid) + `features/images/precheck-report.component.ts` (per-check pass/fail rows + fix-hint inline) + unit specs |
| `meesell-infra-builder` (opus, standalone) | — (no specialists) | GCS bucket `meesell-images` creation via Terraform + 1-year lifecycle policy + Workload Identity binding + per-namespace K8s manifest updates (image-tasks queue, concurrency=4, `FEATURE_IMAGE_PRECHECK_ENABLED` env var) + `docs/runbooks/image-pipeline-troubleshooting.md` runbook |

**8 specialists total** (3 backend, 2 ai, 2 frontend, 0 data, 0 legal, 0 auth, 0 ui-styler — explicit omissions below).

**Tracks explicitly NOT participating:**
- **Data track** (`meesell-data-engineer`): no XLSX/scraper work for image-precheck.
- **Legal** (`meesell-legal-writer`): no policy doc changes; image storage is covered by existing privacy policy (no new PII surface).
- **Auth** (`meesell-auth-builder`): auth already shipped on `feature/auth-otp` per D3 sequencing; image-precheck consumes JWT via existing `get_current_user` dep.
- **UI styler** (`meesell-angular-ui-styler`): component-builder absorbs styling for the 2 new components (mee-* primitives from Layer 2 + Tailwind utilities). If founder wants a dedicated styling pass after components land, a follow-up ui-styler dispatch can be added — but not in scope for V1 ship.

### Dispatch order (critical path)

```
PHASE A (in parallel — no inter-dependency):
  meesell-database-builder    → product_images model + migration (independent: only reads MVP_ARCH §2.5)
  meesell-prompt-engineer     → watermark_v1.py + 30-image golden fixture (independent: prompt content only, no pipeline)
  meesell-infra-builder       → GCS bucket + IAM + K8s manifests + runbook (independent: cloud resources only)

PHASE B (after database-builder + prompt-engineer complete):
  meesell-services-builder    → modules/image/service.py + repository.py + domain.py + exceptions.py + tasks.py (Celery shell only) + adapters/gcs.py
                                (needs ProductImage ORM shape from database-builder; needs watermark.v1 prompt path from prompt-engineer)
  meesell-image-precheck-builder → 5-step precheck pipeline logic INSIDE tasks.py (parallel with services-builder on the same file)
                                (coordinated via the §11.A seam — services-builder owns @shared_task decorator + asyncio.run wrapper; image-precheck-builder owns the pipeline body)
                                Practical sequencing: services-builder commits the Celery shell first → image-precheck-builder rebases on that and adds the pipeline body.

PHASE C (after services-builder + image-precheck-builder complete):
  meesell-api-routes-builder  → modules/image/router.py + schemas.py + main.py mount + unit + integration tests
                                (needs domain.py + exceptions.py + service.py interfaces locked)

PHASE D (after api-routes-builder complete — backend is now testable):
  meesell-angular-service-builder  → ImageService + polling + route registration + flag guard
                                       (needs the locked API contract from api-routes-builder OpenAPI export)

PHASE E (after angular-service-builder complete):
  meesell-angular-component-builder → ImageUploaderComponent + PrecheckReportComponent
                                       (needs ImageService interface stable)
```

**Critical-path note:** PHASE A specialists can run **fully in parallel** the moment the planning PR merges. PHASE B has two specialists working on the same file (`tasks.py`) — the §11.A seam handles this cleanly because services-builder owns the wrapper shell (decorator + outer `def image_precheck_task` signature + `asyncio.run(...)` outer call) and image-precheck-builder owns the body (the 5 steps). Both work on `feature/image-precheck/backend` branch and coordinate via memos in their respective memory directories.

**5-day escalation rule (per repo MASTER §1.2):** any `feature/image-precheck/{group}` branch open > 5 calendar days without merging → lead escalates to founder. PHASE B is the risk surface for this — the services-builder + image-precheck-builder co-edit on `tasks.py` is the longest-running coordination.

---

## Code surfaces

Every file the feature creates or modifies, grouped by domain. Status: NEW | MODIFY.

### Backend

| # | File | Status | Owner | Notes |
|---|------|--------|-------|-------|
| 1 | `backend/app/modules/image/__init__.py` | NEW | `meesell-services-builder` | Empty or re-exports public surface |
| 2 | `backend/app/modules/image/service.py` | NEW | `meesell-services-builder` | 6-method surface per §11.C: `upload_image`, `list_images`, `get_image_urls` (cross-module → catalog), `get_image_bytes` (cross-module → export V1.5), `write_precheck_result` (worker context), `summary` (optional cross-module → dashboard) |
| 3 | `backend/app/modules/image/repository.py` | NEW | `meesell-services-builder` | 7-method MODULE-PRIVATE per §11.D: `insert`, `find_by_product`, `find_by_id`, `find_by_slot`, `update_precheck_result`, `soft_delete_by_idx`, `summarize_by_products` |
| 4 | `backend/app/modules/image/domain.py` | NEW | `meesell-services-builder` | 4 frozen dataclasses per §11.G: `ProductImage`, `ImageUrl`, `ImageStatusSummary`, `PrecheckResult` |
| 5 | `backend/app/modules/image/exceptions.py` | NEW | `meesell-services-builder` | 5 ImageError subclasses per §11.H: `InvalidImageFormatError`, `ImageTooLargeError`, `InvalidImageIdxError`, `ImageSlotOccupiedError`, `ImageNotFoundError` |
| 6 | `backend/app/modules/image/tasks.py` | NEW | `meesell-services-builder` (shell) + `meesell-image-precheck-builder` (pipeline body) | Single `@shared_task(name="image.precheck", bind=True, max_retries=2)` per §11.E. Services-builder owns the decorator + `asyncio.run(...)` wrapper + `write_precheck_result` write-back. Image-precheck-builder owns the 5-step pipeline body. |
| 7 | `backend/app/modules/image/router.py` | NEW | `meesell-api-routes-builder` | 2 endpoints per §11.B: `POST /api/v1/products/{id}/images` (202) + `GET /api/v1/products/{id}/images` (200) |
| 8 | `backend/app/modules/image/schemas.py` | NEW | `meesell-api-routes-builder` | 3 Pydantic v2 models per §11.F: `ImageUploadResponse`, `ImageSummary`, `ImagesListResponse` |
| 9 | `backend/app/shared/models/product_image.py` | NEW | `meesell-database-builder` | SQLAlchemy 2.0 `Mapped[T]` model per `MVP_ARCH §2.5` with **4-slot CHECK constraint** + `is_front` GENERATED column |
| 10 | `backend/alembic/versions/<rev>_product_images.py` | NEW | `meesell-database-builder` | `upgrade()` + `downgrade()`; CHECK constraint `(image_idx IN (1,2,3,4))` is reversible via DROP TABLE on downgrade |
| 11 | `backend/app/shared/models/__init__.py` | MODIFY | `meesell-database-builder` | Export `ProductImage` |
| 12 | `backend/app/adapters/gcs.py` | NEW or MODIFY | `meesell-services-builder` | Add 3 methods per §6.D: `upload_bytes(path, data, content_type) -> str`, `download_bytes(path) -> bytes`, `generate_signed_url(path, ttl_seconds, method) -> str`. Specialist checks if file already exists (created during catalog-form for preview signed URLs — if so, MODIFY; if not, NEW). |
| 13 | `backend/app/adapters/__init__.py` | MODIFY (conditional) | `meesell-services-builder` | Export `GCSAdapter` if newly created |
| 14 | `backend/app/ai_ops/prompts/watermark_v1.py` | NEW | `meesell-prompt-engineer` | Vision prompt template + Pydantic response schema `{has_watermark: bool, confidence: float}` per §6A.G |
| 15 | `backend/app/ai_ops/prompts/__init__.py` | MODIFY | `meesell-prompt-engineer` | Export `WATERMARK_V1_TEMPLATE` + `WatermarkResponse` |
| 16 | `backend/app/ai_ops/prompt_registry.py` | MODIFY | `meesell-prompt-engineer` | Add registry entry: `("watermark.v1", workload="watermark", template=WATERMARK_V1_TEMPLATE, rendered_by="vision")` per §6A.G |
| 17 | `backend/app/ai_ops/client.py` | READ-ONLY (verify) | `meesell-services-builder` | Verify `"watermark"` is already in the `Literal["smart_picker", "autofill", "watermark"]` workload type per §6A.B — it IS per the locked spec; no code change needed. Specialist confirms via grep + reports in final review. |
| 18 | `backend/app/i18n/messages_en.py` | MODIFY | `meesell-services-builder` | Add 5 keys per §11.J: `validation.image.invalid_format`, `validation.image.too_large`, `validation.image.invalid_idx`, `image.slot_occupied`, `image.not_found` |
| 19 | `backend/app/main.py` | MODIFY | `meesell-api-routes-builder` | Mount `image_router` via `app.include_router(image_router)` |
| 20 | `backend/app/config.py` | MODIFY | `meesell-services-builder` | Add `FEATURE_IMAGE_PRECHECK_ENABLED: bool = True`, `GCS_SIGNED_URL_TTL_SECONDS: int = 3600`, `GCS_BUCKET_IMAGES: str` (Secret Manager ref or env) |
| 21 | `backend/tests/unit/image/test_router.py` | NEW | `meesell-api-routes-builder` | 5 unit tests per §11.K: ownership gate, file validation, slot uniqueness, GCS path construction, Celery enqueue |
| 22 | `backend/tests/integration/test_image_precheck_integration.py` | NEW | `meesell-api-routes-builder` | 3 integration tests per §11.K: full upload→poll→ready flow, watermark budget exhaustion → "skipped_budget", cross-module URL fetch |
| 23 | `backend/tests/eval/watermark/golden_set.json` | NEW | `meesell-prompt-engineer` | 30 images (15 watermarked + 15 clean), each entry: `{gcs_path, expected_has_watermark: bool, notes}` per §6A.H |
| 24 | `backend/tests/eval/watermark/test_accuracy.py` | NEW | `meesell-prompt-engineer` | Eval runner — loads golden_set.json, runs `ai_ops.client.call_gemini` against each, asserts `aggregate_metric ≥ 0.85` |
| 25 | `backend/tests/eval/precheck_smoke/fixtures.json` | NEW | `meesell-image-precheck-builder` | 20-image deterministic smoke: 10 known-bad (1 PNG, 1 CMYK, 1 <1500×1500, 1 dark BG, 6 mixed) + 10 known-good. For Gate 2 of D2. |
| 26 | `backend/tests/eval/precheck_smoke/test_pillow_checks.py` | NEW | `meesell-image-precheck-builder` | Eval runner — verifies all 10 bad → `failed_precheck`; all 10 good → `ready`; per-image Pillow total ≤ 2s |

### Frontend

| # | File | Status | Owner | Notes |
|---|------|--------|-------|-------|
| 1 | `frontend/src/app/features/images/image-uploader.component.ts` | NEW | `meesell-angular-component-builder` | Drag-drop region; 4-slot grid (idx=1 marked as "Front image"); multipart upload progress; uses `mee-file-upload`, `mee-card`, `mee-button` per FRONTEND_ARCHITECTURE.md Layer 2/4 boundary |
| 2 | `frontend/src/app/features/images/image-uploader.component.html` | NEW | `meesell-angular-component-builder` | Template — 4-slot grid + drag zone + per-slot status |
| 3 | `frontend/src/app/features/images/image-uploader.component.spec.ts` | NEW | `meesell-angular-component-builder` | Component unit tests |
| 4 | `frontend/src/app/features/images/precheck-report.component.ts` | NEW | `meesell-angular-component-builder` | Per-check pass/fail rows with one-line fix hint inline; red border on `failed_precheck`; uses `mee-badge`, `mee-status-badge` (Layer 3 composite), `mee-empty-state` |
| 5 | `frontend/src/app/features/images/precheck-report.component.html` | NEW | `meesell-angular-component-builder` | Template — 5-row pass/fail report (jpeg/rgb/resolution/white-bg/watermark) |
| 6 | `frontend/src/app/features/images/precheck-report.component.spec.ts` | NEW | `meesell-angular-component-builder` | Component unit tests |
| 7 | `frontend/src/app/core/services/image.service.ts` | NEW | `meesell-angular-service-builder` | `upload(productId, file, slotIdx)` (multipart POST) + `pollImages(productId)` with backoff polling (initial 1s, exponential ×2 to 4s, max 30s); typed against OpenAPI |
| 8 | `frontend/src/app/core/services/image.service.spec.ts` | NEW | `meesell-angular-service-builder` | Service unit tests; mock HttpClient |
| 9 | `frontend/src/app/app.routes.ts` | MODIFY | `meesell-angular-service-builder` | Register `/catalogs/:id/images` → lazy-load `ImageUploaderComponent`; gated by `featureFlagGuard('FEATURE_IMAGE_PRECHECK_ENABLED')` per D2 |
| 10 | `frontend/src/app/core/services/feature-flags.service.ts` | MODIFY (conditional) | `meesell-angular-service-builder` | Add `FEATURE_IMAGE_PRECHECK_ENABLED` to the build-time flag set; reads `environment.featureFlags.imagePrecheckEnabled` |

**Architecture pre-federation note (correction to dispatch prompt):** The dispatch prompt said `frontend/src/app/pages/image-uploader/`. The actual canonical path per `FRONTEND_ARCHITECTURE.md` is `frontend/src/app/features/images/` (Layer 4 — features). This plan uses the architecture-canonical path. Module federation (per `module_federation/MASTER_PLAN.md` §4.2) puts `mfe-catalog` as the 5th remote and image-uploader becomes part of `mfe-catalog`; pre-federation it lives at the path above.

**No PrimeNG direct import** — Layer 4 rule per FRONTEND_ARCHITECTURE.md. All UI primitives come via `@mee/ui` barrel.

### AI

| # | File | Status | Owner | Notes |
|---|------|--------|-------|-------|
| 1 | `backend/app/ai_ops/prompts/watermark_v1.py` | NEW | `meesell-prompt-engineer` | (Listed in Backend table above — repeated here for AI track visibility) Vision prompt: system instruction "Is there a visible watermark / text overlay / logo overlay on this image" + JSON output `{has_watermark: bool, confidence: float}` per §6A.G + Layer 1 hallucination prefix per §6A.E |
| 2 | `backend/tests/eval/watermark/` (NEW dir) | NEW | `meesell-prompt-engineer` | 30-image golden set + accuracy eval runner — covered in Backend table rows 23-24 |
| 3 | `backend/tests/eval/README.md` | MODIFY | `meesell-prompt-engineer` | Add a "watermark" section documenting the golden set composition + eval invocation |

### Data

**NONE** — no XLSX, scraper, brand-master, or seed changes.

### Infra

| # | File / resource | Status | Owner | Notes |
|---|-----------------|--------|-------|-------|
| 1 | `infra/terraform/modules/gcs/buckets.tf` | NEW or MODIFY | `meesell-infra-builder` | Create `meesell-images` bucket in `asia-south1` with: standard storage class, uniform bucket-level access (NO ACLs), lifecycle policy DELETE after 1 year, public access prevention enforced |
| 2 | `infra/terraform/modules/gcs/iam.tf` | NEW or MODIFY | `meesell-infra-builder` | Workload Identity binding: backend service account = `roles/storage.objectAdmin` scoped to `meesell-images/*` (NOT bucket-level admin); Celery worker pod inherits via WIF per §3.4 secret strategy |
| 3 | `k8s/dev/api-deployment.yaml` | MODIFY | `meesell-infra-builder` | Add `FEATURE_IMAGE_PRECHECK_ENABLED=true` env var; add `GCS_BUCKET_IMAGES=meesell-images-dev` env var; add `GCS_SIGNED_URL_TTL_SECONDS=3600` env var |
| 4 | `k8s/dev/worker-deployment.yaml` | NEW or MODIFY | `meesell-infra-builder` | Celery worker: declare `image-tasks` queue; precheck worker concurrency = 4 (matches 8s/image × 4 = 32s budget per minute × 60 min ≈ 7,500 images/hour capacity); replicas = 1 in dev |
| 5 | `k8s/staging/api-deployment.yaml` | MODIFY | `meesell-infra-builder` | Add `FEATURE_IMAGE_PRECHECK_ENABLED=false` (per D2) + `GCS_BUCKET_IMAGES=meesell-images-staging` + same TTL |
| 6 | `k8s/staging/worker-deployment.yaml` | NEW or MODIFY | `meesell-infra-builder` | image-tasks queue; concurrency = 4; replicas = 2 in staging |
| 7 | `k8s/dev/gcs-secrets.yaml` | NEW (conditional) | `meesell-infra-builder` | Only if WIF requires k8s secret refs (per infra-builder MEMORY check); else WIF binding is sufficient — verify before creating |
| 8 | `docs/runbooks/image-pipeline-troubleshooting.md` | NEW | `meesell-infra-builder` | How to inspect a stuck precheck job (Celery + Valkey introspection); how to re-enqueue failed checks; GCS-path tenant-isolation verification command (D2 Gate 3); cost monitoring at projected 4 images × 10 MB × N sellers/month |

### Docs

| # | File | Action | Owner | When |
|---|------|--------|-------|------|
| 1 | `docs/V1_FEATURE_SPEC.md §F5` | Amend inline: 6→4 images, 60MB→40MB cap (per D1 resolution) | `meesell-backend-coordinator` | In PR `feature/image-precheck/backend` (so it's reviewed alongside the structural code) |
| 2 | `docs/V1_FEATURE_SPEC.md §F5` | Stamp "implemented YYYY-MM-DD PR#N" | `meesell-backend-coordinator` | After `feature/image-precheck` → `develop` merges |
| 3 | `docs/BACKEND_ARCHITECTURE.md §11` | Sentinel comment referencing the merge commit that proves §11 is LOCKED-on-disk | `meesell-backend-coordinator` | After `feature/image-precheck` → `develop` merges |
| 4 | `.claude/agents/meesell-image-precheck-builder.md` | One-line correction: "Total upload size capped 60 MB / product (6 × 10 MB)" → "Total upload size capped 40 MB / product (4 × 10 MB)" per D1 | `meesell-ai-coordinator` | In PR `feature/image-precheck/ai` |
| 5 | `docs/runbooks/README.md` | Add link to `image-pipeline-troubleshooting.md` | `meesell-infra-builder` | In PR `feature/image-precheck/infra` |

---

## Documentation deliverables

These must exist alongside the merged code. Each is an acceptance gate item the lead checks before approving the group PR.

| # | Deliverable | Owner | PR location |
|---|-------------|-------|-------------|
| 1 | **OpenAPI entries** for `POST /api/v1/products/{id}/images` (202 + `ImageUploadResponse` shape per §11.B.1) and `GET /api/v1/products/{id}/images` (200 + `ImagesListResponse` with per-image status + signed URLs per §11.B.2). Auto-generated from Pydantic schemas; reviewed in PR body | `meesell-api-routes-builder` | `feature/image-precheck/backend` |
| 2 | **Inline service-method docstrings** on the 4 cross-module surfaces (`get_image_urls`, `get_image_bytes`, `write_precheck_result`, `summary`) per §16.A — each docstring names the consumer module and the §10/§13/§14 section that locks the contract | `meesell-services-builder` | `feature/image-precheck/backend` |
| 3 | **Celery task module header comment** in `tasks.py` documenting the 5-step pipeline order + the white-BG heuristic algorithm choice (e.g., "Pillow corner-pixel sampling on 4 corners × 16-pixel patches; mean brightness ≥ 240 for each patch") + the §6A.F graceful fallback contract | `meesell-image-precheck-builder` | `feature/image-precheck/ai` (shared file — coordinated with backend lead) |
| 4 | **Prompt registry entry** — `watermark.v1` registered in `ai_ops/prompt_registry.py` with template path + workload + rendered_by | `meesell-prompt-engineer` | `feature/image-precheck/ai` |
| 5 | **30-image golden set fixture** documented in `tests/eval/README.md` with composition (15 watermarked + 15 clean), source attribution (where the 30 images came from — public domain test set or founder-supplied), and the eval invocation `pytest tests/eval/watermark/test_accuracy.py` | `meesell-prompt-engineer` | `feature/image-precheck/ai` |
| 6 | **20-image deterministic smoke fixture** documented in `tests/eval/README.md` with breakdown of bad/good categories per Gate 2 of D2 | `meesell-image-precheck-builder` | `feature/image-precheck/ai` |
| 7 | **ImageUploaderComponent docstring** describing multipart upload + 4-slot grid + retry semantics + flag-OFF behavior | `meesell-angular-component-builder` | `feature/image-precheck/frontend` |
| 8 | **PrecheckReportComponent docstring** on per-check rendering + fix-hint copy + red-border `failed_precheck` styling | `meesell-angular-component-builder` | `feature/image-precheck/frontend` |
| 9 | **ImageService.pollImages docstring** on backoff schedule (1s → 2s → 4s, max 30s total) + retry on transient 503 | `meesell-angular-service-builder` | `feature/image-precheck/frontend` |
| 10 | **`image-pipeline-troubleshooting.md` runbook** — Celery job introspection, GCS tenant-isolation verification (D2 Gate 3), cost monitoring | `meesell-infra-builder` | `feature/image-precheck/infra` |
| 11 | **ai_eval CI gate** extended in `.github/workflows/ci.yml` to include `pytest tests/eval/watermark/` and `pytest tests/eval/precheck_smoke/` in the nightly job | `meesell-infra-builder` | `feature/image-precheck/infra` |
| 12 | **V1_FEATURE_SPEC.md §F5 implementation stamp** after develop merge (deliverable #2 in Docs code surfaces table above) | `meesell-backend-coordinator` | Post-develop-merge follow-up |
| 13 | **BACKEND_ARCHITECTURE.md §11 sentinel** after develop merge (deliverable #3 in Docs code surfaces table above) | `meesell-backend-coordinator` | Post-develop-merge follow-up |

---

## Branch setup

> **When to create:** After PR for this `feature/image-precheck/planning` branch merges to `develop` AND the founder confirms `feature/catalog-form` has merged to `develop` (per D3 sequencing). Until both preconditions met, the coding branches DO NOT exist.

### Branches to create (all cut from `develop`, after `catalog-form` merges)

| Branch | Cut from | Purpose | Who commits here |
|--------|----------|---------|-----------------|
| `feature/image-precheck` | `develop` | Integration branch — sub-branches merge into here; final PR to `develop` | Only merge commits from sub-branches |
| `feature/image-precheck/backend` | `feature/image-precheck` | All backend specialist work | `meesell-database-builder`, `meesell-services-builder`, `meesell-api-routes-builder` |
| `feature/image-precheck/ai` | `feature/image-precheck` | All AI specialist work | `meesell-prompt-engineer`, `meesell-image-precheck-builder` |
| `feature/image-precheck/frontend` | `feature/image-precheck` | All frontend specialist work | `meesell-angular-service-builder`, `meesell-angular-component-builder` |
| `feature/image-precheck/infra` | `feature/image-precheck` | All infra work (standalone) | `meesell-infra-builder` |

### Creation commands (run by founder after this planning PR merges + catalog-form has merged)

```bash
# Ensure develop is current
git checkout develop && git pull origin develop

# Create integration branch
git checkout -b feature/image-precheck
git push -u origin feature/image-precheck

# Create 4 group branches from the integration branch
git checkout -b feature/image-precheck/backend feature/image-precheck
git push -u origin feature/image-precheck/backend

git checkout -b feature/image-precheck/ai feature/image-precheck
git push -u origin feature/image-precheck/ai

git checkout -b feature/image-precheck/frontend feature/image-precheck
git push -u origin feature/image-precheck/frontend

git checkout -b feature/image-precheck/infra feature/image-precheck
git push -u origin feature/image-precheck/infra

# Return to integration branch
git checkout feature/image-precheck
```

### PR flow (coding stage)

```
feature/image-precheck/backend  ──┐
feature/image-precheck/ai       ──┤
feature/image-precheck/frontend ──┼──► feature/image-precheck ──► develop
feature/image-precheck/infra    ──┘
```

- Each group branch opens a PR to `feature/image-precheck` (NOT directly to `develop`)
- `feature/image-precheck/backend` PR reviewed and merged by `meesell-backend-coordinator`
- `feature/image-precheck/ai` PR reviewed and merged by `meesell-ai-coordinator`
- `feature/image-precheck/frontend` PR reviewed and merged by `meesell-frontend-coordinator`
- `feature/image-precheck/infra` PR self-reviewed by `meesell-infra-builder`, then merged
- Integration PR (`feature/image-precheck` → `develop`) opened only after **all 4 group PRs** are merged; founder does final review per repo MASTER §2.2

### PR templates

| PR | Template file |
|----|--------------|
| `feature/image-precheck/backend` → `feature/image-precheck` | `.github/PULL_REQUEST_TEMPLATE/backend.md` |
| `feature/image-precheck/ai` → `feature/image-precheck` | `.github/PULL_REQUEST_TEMPLATE/ai.md` |
| `feature/image-precheck/frontend` → `feature/image-precheck` | `.github/PULL_REQUEST_TEMPLATE/frontend.md` |
| `feature/image-precheck/infra` → `feature/image-precheck` | `.github/PULL_REQUEST_TEMPLATE/infra.md` |
| `feature/image-precheck` → `develop` | `.github/PULL_REQUEST_TEMPLATE/feature.md` (NEW — to be drafted in repo MASTER §9.2 sub-plan; until then use ai.md as fallback per dispatch instruction "AI is the most-involved lead — image-precheck-builder + prompt-engineer + the ≥85% accuracy gate are the primary acceptance signal") |

### Rebase strategy (per repo MASTER §1.4 rule 2)

When ANY of the 4 group PRs merges to `feature/image-precheck`, the other 3 in-flight branches **rebase** onto the new tip (never merge). Specifically:

```bash
# Example: ai branch merged first. backend rebases:
git checkout feature/image-precheck/backend
git fetch origin
git rebase origin/feature/image-precheck
git push --force-with-lease origin feature/image-precheck/backend
```

The lead supervises this rebase to avoid losing in-flight work. The `--force-with-lease` flag is mandatory (NOT `--force`) so a concurrent specialist push isn't silently overwritten.

### Cleanup (post-merge)

- `feature/image-precheck/{group}` branches: deleted within 24h of each group's PR merge (GitHub auto-delete enabled).
- `feature/image-precheck`: deleted within 24h of merging to `develop`.

---

## Memory protocol

This plan installs a **per-feature memory namespace** convention to solve the multi-feature-in-flight problem: when a specialist (e.g. `meesell-services-builder`) works on `image-precheck` AND `ai-autofill` in parallel, its memory must not become a tangle of "which observation belongs to which feature."

### Memories the coding-session leads MUST read at session start

Every coding session for `image-precheck` opens with the lead reading these `MEMORY.md` files in order:

1. `.claude/agent-memory/meesell-ai-coordinator/MEMORY.md` — most-involved lead per Agent lineup; carries the watermark-cost decision and the §F5 D1/D2/D3 ratification
2. `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md` — owns §11 image module lock, the 4-slot CHECK constraint, the §11.A seam between services-builder and image-precheck-builder
3. `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` — owns the Layer 4 path correction `features/images/` (NOT `pages/image-uploader/`) and the `featureFlagGuard` integration
4. `.claude/agent-memory/meesell-infra-builder/MEMORY.md` — owns the GCS bucket layout, IAM scope, K8s manifest contracts, runbook location

Each specialist additionally reads its OWN memory before any task per the `meesell-*` agent spec mandatory-first-action protocol.

### Cross-feature memos

This feature consumes a contract from a prior feature: `catalog.service.assert_product_ownership(product_id, user_id)` from `feature/catalog-form`. The consumer is `meesell-services-builder` (image module). The consuming agent reads the producer's session-close memo at:

- `.claude/agent-memory/meesell-services-builder/feature_catalog_form_session_*_handoff.md` (whichever the latest session is)

If this memo is missing or stale (older than 14 days), the lead opens an inter-lead request via `feature_board_backend.md` "Inter-lead requests open" pointing at the producer.

### File naming

Every agent that touches `image-precheck` writes feature-scoped notes to files prefixed `feature_image_precheck_*.md` inside its own memory directory at `.claude/agent-memory/meesell-<role>/`. Examples:

```
.claude/agent-memory/meesell-services-builder/
├── MEMORY.md                                          ← index (must add "Features in flight" section)
├── feature_image_precheck_celery_task_design.md       ← scoped to image-precheck
├── feature_image_precheck_gcs_path_lock.md            ← scoped to image-precheck
├── feature_image_precheck_session_1_handoff.md        ← scoped to image-precheck
├── feature_ai_autofill_session_1_handoff.md           ← scoped to ai-autofill (future)
└── reference_*.md / project_*.md                      ← cross-feature topics (existing pre-feature convention)
```

The single convention picked for THIS feature is `feature_image_precheck_*.md` (NOT the file-system-sorted variant `image_precheck_feature_*.md`). Leads enforce one convention per feature per `_CANONICAL_PATTERN.md` §6 guidance.

### MEMORY.md index addition (one-time, when first feature work starts)

Every agent adds a new section to its `MEMORY.md`:

### Features in flight

| Feature slug | Status | Last entry | Files |
|---|---|---|---|
| image-precheck | IN PROGRESS | YYYY-MM-DD | feature_image_precheck_*.md |
| ai-autofill | PENDING | — | — |
| smart-picker | MERGED YYYY-MM-DD | YYYY-MM-DD | feature_smart_picker_session_*.md (kept for 14d) |

This is the per-feature index. The existing `MEMORY.md (Index)` section at the top remains the cross-feature topic index. Both coexist.

### Per-feature first-action protocol

Every dispatch template in `## Dispatch templates` includes this line in its "Mandatory reads" block:

```bash
ls .claude/agent-memory/meesell-<my-role>/feature_image_precheck_*.md 2>/dev/null
```

The specialist runs this command first, then reads every file found, BEFORE reading the broader spec docs. This is the per-feature context-resume protocol — recovering "what did I (or my previous session) leave undone on THIS feature."

### Session-close memory entries

Every specialist must, before declaring `Status: COMPLETE`:

1. Append a session-close note to `feature_image_precheck_session_{N}_handoff.md`. Format:
   ```markdown
   ## Session mesell-image-precheck-{group}-session-{N} — YYYY-MM-DD
   Files touched: <list>
   Locked decisions: <list>
   Open items: <list — for next session or other specialist>
   Blockers carried: <list — what cannot be closed without other agents>
   Next-step recommendation: <single sentence>
   Hand-off to: <other specialist or lead>
   ```
2. Update the `### Features in flight` table in `MEMORY.md` — change Last entry date + Files list.

The lead's merge gate REJECTS PRs where the specialist's memory write is missing (founder visibility into specialist discipline). Specialists report `Memory update: DONE | SKIPPED (reason)` in the Final Report — SKIPPED requires a written reason in the PR comments.

### Lead pre-seeding (before any specialist dispatch)

Each of the 4 leads, BEFORE dispatching their first specialist on `image-precheck`, writes one bootstrap file to their own memory:

```
.claude/agent-memory/meesell-<lead-role>/feature_image_precheck_lead_bootstrap.md
```

Contents:
- Pointer to this `FEATURE_PLAN.md` (path + commit SHA at planning lock time)
- The dispatch order from `## Agent lineup → Dispatch order (critical path)` above (lead's group only)
- The branch creation commands from `## Branch setup` above (the lead's own group branch)
- The merge-gate checklist for the lead's group (from `## Review + iteration protocol` below)

This is the lead's "what am I responsible for on this feature" cheat sheet — readable in 60 seconds at the start of every session.

---

## Dispatch templates

Eight templates total. Each is the **exact prompt** the lead pastes into `Agent()` when dispatching a specialist. Session number `{N}` is filled in by the lead from the `feature_board_<domain>.md` (starts at 1; resumes at `{N+1}` after context break).

### Template A — `meesell-database-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** A (first, independent)
**Branch:** `feature/image-precheck/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-backend-session-{N}
Lead: meesell-backend-coordinator

## Your mission
Create the `product_images` SQLAlchemy ORM model and the Alembic migration that creates the `product_images` table with a 4-slot CHECK constraint and the `is_front` GENERATED column.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-database-builder/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-database-builder/MEMORY.md
3. docs/MVP_ARCHITECTURE.md §2.5 (product_images table — authoritative DDL including the 4-slot CHECK constraint and `is_front` GENERATED column)
4. docs/BACKEND_ARCHITECTURE.md §11.J (DB-level enforcement — confirms "the 4-slot uniform rule per `MVP_ARCH §0` premise #3 is the structural limit (DB-level `CHECK` constraint)")
5. docs/BACKEND_ARCHITECTURE.md §3.E (shared/models/ subtree layout)
6. docs/BACKEND_ARCHITECTURE.md §5 (foundation layer — SQLAlchemy 2.0 `Mapped[T]` conventions)
7. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Backend (rows 9-11)

## Acceptance criteria
- [ ] `backend/app/shared/models/product_image.py` created with `ProductImage` SQLAlchemy 2.0 typed ORM model:
  - `id`: UUID PK, `server_default=func.gen_random_uuid()`
  - `product_id`: UUID FK to `products(id)` ON DELETE CASCADE, indexed
  - `gcs_path`: TEXT NOT NULL
  - `order_idx`: INTEGER NOT NULL — column named `order_idx` per V1 spec §F5 data model; alias `image_idx` accepted in MVP_ARCH §2.5 — pick `order_idx` to match the V1 spec; document the choice in the model docstring
  - `is_front`: BOOLEAN GENERATED ALWAYS AS (order_idx = 1) STORED
  - `width`: INTEGER NULL
  - `height`: INTEGER NULL
  - `color_space`: VARCHAR(8) NULL  (RGB | CMYK | Gray)
  - `precheck_jsonb`: JSONB NOT NULL DEFAULT '{}'::jsonb
  - `status`: VARCHAR(16) NOT NULL DEFAULT 'pending' (pending | ready | failed_precheck)
  - `deleted_at`: TIMESTAMPTZ NULL (soft delete per §11.D)
  - `created_at`: TIMESTAMPTZ NOT NULL DEFAULT now()
  - `__tablename__ = "product_images"`
  - **CHECK constraint** at table level: `CHECK (order_idx IN (1, 2, 3, 4))` (per D1 — 4 slots, NOT 6)
- [ ] Alembic migration at `backend/alembic/versions/<rev>_product_images.py`:
  - `upgrade()`: CREATE TABLE product_images with all columns + the CHECK constraint + an index on `product_id` + a UNIQUE constraint on `(product_id, order_idx) WHERE deleted_at IS NULL` (partial index for the slot-uniqueness gate per §11.B.1 step 4)
  - `downgrade()`: DROP TABLE product_images (the CHECK is reversibly dropped with the table)
  - `down_revision` chains from the current alembic head — confirm head via `alembic heads`
  - Migration tested locally: `alembic upgrade head` succeeds; `alembic downgrade -1` succeeds; no head divergence between dev and staging
- [ ] `backend/app/shared/models/__init__.py` exports `ProductImage`
- [ ] No other files modified

## Hard constraints
- The CHECK constraint is `(order_idx IN (1, 2, 3, 4))` — NOT `(order_idx IN (1..6))`. This is D1-locked.
- `is_front` is GENERATED ALWAYS AS — NOT a regular column with a trigger. The DB enforces it; nothing else touches it.
- `precheck_jsonb` is JSONB NOT NULL DEFAULT '{}'::jsonb — NOT a regular VARCHAR or TEXT.
- `status` is a VARCHAR(16) with Python-side enum values (no Postgres ENUM type) per §0.D style.
- Partial unique index on `(product_id, order_idx) WHERE deleted_at IS NULL` — this enforces the slot uniqueness AT THE DB LAYER, complementing the §11.B.1 step 4 service-level check.
- TIMESTAMPTZ on all timestamps — NOT TIMESTAMP.
- UUID PK via `server_default=func.gen_random_uuid()` — NOT Python-side `default=uuid4()`.
- Do NOT add columns beyond the 11 listed (no `caption`, no `tags`, no `uploaded_by_ip` — V1 scope only).
- `alembic.ini` and `alembic/env.py` — READ-ONLY.

## Files you MAY touch
- `backend/app/shared/models/product_image.py` (NEW)
- `backend/app/shared/models/__init__.py` (MODIFY — add ProductImage export)
- `backend/alembic/versions/<rev>_product_images.py` (NEW)

## Files you must NOT touch
- Any file under `backend/app/modules/`
- `backend/app/core/`, `backend/app/config.py`, `backend/app/main.py`
- Any file under `backend/app/adapters/`
- Any test files (test plan owned by api-routes-builder per FEATURE_PLAN.md)
- Any frontend, AI, or infra files

## Final report format
```
REPORT: meesell-database-builder
Session: mesell-image-precheck-backend-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/shared/models/product_image.py
- backend/alembic/versions/<actual_rev>_product_images.py (down_revision: <prior_head>)

Files modified:
- backend/app/shared/models/__init__.py

CHECK constraint verified: ✅ `CHECK (order_idx IN (1, 2, 3, 4))` at table level (paste pg_dump excerpt)
Partial UNIQUE index verified: ✅ `(product_id, order_idx) WHERE deleted_at IS NULL` (paste pg_dump excerpt)

Migration test results:
- alembic upgrade head: PASS | FAIL (paste output)
- alembic downgrade -1: PASS | FAIL (paste output — must reverse cleanly)
- alembic upgrade head (again, post-downgrade): PASS | FAIL (round-trip verification)

Memory update: DONE (.claude/agent-memory/meesell-database-builder/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Blockers / notes:
<none | specific issue>
```
```

---

### Template B — `meesell-services-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** B (after database-builder + prompt-engineer complete)
**Branch:** `feature/image-precheck/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-backend-session-{N}
Lead: meesell-backend-coordinator

## Your mission
Build the image module's service layer + repository + domain + exceptions + the Celery task SHELL (decorator + asyncio.run wrapper, NO pipeline body), the GCS adapter methods, and the i18n keys. The Celery task body (the 5-step pipeline) is owned by `meesell-image-precheck-builder` per §11.A seam — your scope is the wrapper, not the body.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-services-builder/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-services-builder/MEMORY.md
3. docs/BACKEND_ARCHITECTURE.md §11 (FULL — A through M; the entire image module spec)
4. docs/BACKEND_ARCHITECTURE.md §6.D (GCS adapter contract — upload_bytes, download_bytes, generate_signed_url signatures)
5. docs/BACKEND_ARCHITECTURE.md §6A (AI Operations Layer — confirm `ai_ops.client.call_gemini` is the SOLE way to invoke Gemini per §6A.A + §6A.B)
6. docs/BACKEND_ARCHITECTURE.md §16.A-E (inter-module communication rules — service.py is PUBLIC, repository.py is PRIVATE)
7. docs/BACKEND_ARCHITECTURE.md §5A.D (i18n validation_message_id convention `{domain}.{field}.{constraint}`)
8. docs/MVP_ARCHITECTURE.md §10.8 (GCS tenant isolation path convention)
9. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Backend (rows 1-6, 12-13, 18, 20)

## Acceptance criteria
- [ ] `backend/app/modules/image/__init__.py` created (empty or re-exports)
- [ ] `backend/app/modules/image/domain.py` created with 4 frozen dataclasses per §11.G:
  - `ProductImage`: 11-field mirror of the DB row (id, product_id, user_id, gcs_path, order_idx, is_front, width, height, color_space, precheck_jsonb, status, created_at)
  - `ImageUrl`: cross-module return type (image_id, idx, signed_url, is_front)
  - `ImageStatusSummary`: cross-module return type (product_id, total_images, ready_count, failed_count, pending_count, front_image_signed_url)
  - `PrecheckResult`: internal (jpeg_valid, color_space, resolution_pass, white_background, watermark_check Literal["no_watermark","has_watermark","uncertain","skipped_budget"], watermark_confidence)
- [ ] `backend/app/modules/image/exceptions.py` created with 5 ImageError subclasses per §11.H (all inherit from `app.shared.exceptions.MeesellError`):
  - `ImageError` (base), `InvalidImageFormatError` (400, `validation.image.invalid_format`), `ImageTooLargeError` (400, `validation.image.too_large`), `InvalidImageIdxError` (400, `validation.image.invalid_idx`), `ImageSlotOccupiedError` (409, `image.slot_occupied`), `ImageNotFoundError` (404, `image.not_found`)
- [ ] `backend/app/modules/image/repository.py` created — MODULE-PRIVATE per §16; 7 async methods per §11.D, all using `scope_to_user(user_id)`:
  - `insert`, `find_by_product`, `find_by_id`, `find_by_slot`, `update_precheck_result`, `soft_delete_by_idx`, `summarize_by_products`
- [ ] `backend/app/modules/image/service.py` created — PUBLIC; 6 async methods per §11.C:
  - `upload_image(user_id, product_id, file, idx) -> ProductImage` (endpoint backing for POST per §11.B.1 — cross-module call to `catalog.service.assert_product_ownership` per §10.C as step 1; file validation; Pillow metadata read; slot check; GCS upload via `adapters.gcs.upload_bytes` with the LOCKED path `meesell-images/{user_id}/{product_id}/{idx}.jpg`; repository insert; `image_precheck_task.delay(image_id, user_id)` enqueue)
  - `list_images(user_id, product_id) -> ImagesListResponse` (endpoint backing for GET per §11.B.2 — ownership gate; repository fetch; per-row signed URL via `adapters.gcs.generate_signed_url(path, ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS, method="GET")`)
  - `get_image_urls(product_id, user_id) -> list[ImageUrl]` (CROSS-MODULE — consumed by `catalog.service.get_preview` per §10.B.4. Returns signed URLs ONLY for status='ready' images, ordered by idx, with `is_front` flag.)
  - `get_image_bytes(image_id, user_id) -> bytes` (CROSS-MODULE — consumed by `export.service` per §14. Downloads from GCS via `adapters.gcs.download_bytes`. Returns raw bytes.)
  - `write_precheck_result(image_id, user_id, precheck_jsonb, status) -> None` (CROSS-MODULE / worker context — consumed by `image.tasks` per §11.E. Atomic single-row UPDATE.)
  - `summary(user_id, product_ids) -> dict[UUID, ImageStatusSummary]` (CROSS-MODULE / OPTIONAL — consumed by dashboard per §11.C / §13. Locked here even though §2.D matrix kept dashboard at 8 ✓.)
- [ ] `backend/app/modules/image/tasks.py` SHELL created — per §11.E:
  - `@shared_task(name="image.precheck", bind=True, max_retries=2, retry_backoff=True, autoretry_for=(AdapterError,))` synchronous task
  - Outer signature `def image_precheck_task(self, image_id: UUID, user_id: UUID) -> None`
  - Inside: `asyncio.run(...)` wrapper that calls a stub function `await _run_precheck_pipeline(image_id, user_id) -> PrecheckResult` — the stub raises `NotImplementedError("pipeline body is owned by meesell-image-precheck-builder per §11.A seam")`
  - After the stub returns (will be filled in by image-precheck-builder), call `await image.service.write_precheck_result(image_id, user_id, result.precheck_jsonb, result.status)`
  - Module header docstring documents the 9-step locked flow per §11.E + the §11.A seam (your scope vs image-precheck-builder's scope)
  - Direct ORM write of `image.precheck.completed` audit event after `write_precheck_result` returns (per §11.E)
- [ ] `backend/app/adapters/gcs.py` — if file exists from catalog-form: MODIFY adding 3 methods per §6.D. If file does not exist: NEW.
  - `async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str` — returns `gs://` URI
  - `async def download_bytes(self, path: str) -> bytes`
  - `async def generate_signed_url(self, path: str, ttl_seconds: int, method: Literal["GET", "PUT"] = "GET") -> str`
  - Settings sourced from `shared/config.settings` — NEVER `os.getenv()`
- [ ] `backend/app/i18n/messages_en.py` MODIFIED with 5 new keys per §11.J:
  - `validation.image.invalid_format`: "Only JPEG images are supported. Convert your file before upload."
  - `validation.image.too_large`: "Image exceeds 10 MB. Compress or resize and try again."
  - `validation.image.invalid_idx`: "Image slot must be 1, 2, 3, or 4."
  - `image.slot_occupied`: "Slot already has an image. Delete the existing image before uploading."
  - `image.not_found`: "Image not found."
- [ ] `backend/app/config.py` MODIFIED:
  - Add `FEATURE_IMAGE_PRECHECK_ENABLED: bool = True`
  - Add `GCS_SIGNED_URL_TTL_SECONDS: int = 3600`
  - Add `GCS_BUCKET_IMAGES: str` (env-driven; default `"meesell-images-dev"`)
- [ ] Verify `backend/app/ai_ops/client.py` Literal type — confirm `"watermark"` is in `Literal["smart_picker", "autofill", "watermark"]`. It IS per §6A.B. Report verification in final report. NO code change.

## Hard constraints
- The Celery task BODY (the 5-step pipeline) is OWNED BY `meesell-image-precheck-builder`. Your `tasks.py` ships with a `NotImplementedError` stub for the pipeline call. Image-precheck-builder will fill it in.
- GCS path is `meesell-images/{user_id}/{product_id}/{idx}.jpg` — STRUCTURALLY LOCKED per §6.D + MVP_ARCH §10.8. Path constructed FROM `user_id` (NOT just `product_id`) — this is the tenant isolation enforcement at the object-storage layer.
- Signed URL TTL is 1h (3600 seconds) — NOT 24h.
- `service.py` is the PUBLIC surface. Every cross-module caller (catalog, export, dashboard) imports from here. `repository.py` is MODULE-PRIVATE — no other module may import it per §16.C rule 2.
- The 4 cross-module surfaces (`get_image_urls`, `get_image_bytes`, `write_precheck_result`, `summary`) MUST have docstrings naming their consumer (e.g., "Called by catalog.service.get_preview per §10.B.4").
- Watermark vision call DOES NOT happen in your scope (it's in the pipeline body owned by image-precheck-builder). Your `tasks.py` only wires the wrapper; the `ai_ops.client.call_gemini` call site lives in image-precheck-builder's code.
- ALL adapters/ imports come from `shared/config.settings` — NEVER `os.getenv()`.
- The repository `scope_to_user(user_id)` join goes through `products.user_id` (per §11.D doc on `find_by_product`) — the `product_images` table does NOT have its own `user_id` column; tenancy flows through the FK.

## Files you MAY touch
- `backend/app/modules/image/__init__.py` (NEW)
- `backend/app/modules/image/service.py` (NEW)
- `backend/app/modules/image/repository.py` (NEW)
- `backend/app/modules/image/domain.py` (NEW)
- `backend/app/modules/image/exceptions.py` (NEW)
- `backend/app/modules/image/tasks.py` (NEW — SHELL only, body is `NotImplementedError` stub)
- `backend/app/adapters/gcs.py` (NEW or MODIFY)
- `backend/app/adapters/__init__.py` (MODIFY conditionally)
- `backend/app/i18n/messages_en.py` (MODIFY — add 5 keys)
- `backend/app/config.py` (MODIFY — 3 new settings)

## Files you must NOT touch
- `backend/app/modules/image/router.py` (owned by api-routes-builder)
- `backend/app/modules/image/schemas.py` (owned by api-routes-builder)
- `backend/app/main.py` (owned by api-routes-builder)
- `backend/app/shared/models/product_image.py` (owned by database-builder — READ, don't modify)
- `backend/app/ai_ops/` (your verification of client.py is READ-ONLY; the prompt and registry are owned by prompt-engineer)
- The Celery task BODY in `tasks.py` (owned by image-precheck-builder — your stub raises `NotImplementedError`)
- Any test files
- Any frontend, AI fixture, or infra files

## Final report format
```
REPORT: meesell-services-builder
Session: mesell-image-precheck-backend-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/modules/image/__init__.py
- backend/app/modules/image/service.py (6-method PUBLIC surface)
- backend/app/modules/image/repository.py (7-method MODULE-PRIVATE)
- backend/app/modules/image/domain.py (4 frozen dataclasses)
- backend/app/modules/image/exceptions.py (5 ImageError subclasses)
- backend/app/modules/image/tasks.py (SHELL — pipeline body stubbed as NotImplementedError)
- backend/app/adapters/gcs.py (3 methods) | MODIFIED (3 methods added)

Files modified:
- backend/app/i18n/messages_en.py (5 keys added)
- backend/app/config.py (3 settings added)
- backend/app/adapters/__init__.py (if newly created)

GCS path verification: ✅ All call sites construct `meesell-images/{user_id}/{product_id}/{idx}.jpg` (paste 3 grep lines proving)
Signed URL TTL: ✅ `ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS` (= 3600 default)
ai_ops.client Literal verification: ✅ `"watermark"` present in `Literal["smart_picker", "autofill", "watermark"]` at line <N>

Memory update: DONE (.claude/agent-memory/meesell-services-builder/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Hand-off to meesell-image-precheck-builder: Celery task shell ready at backend/app/modules/image/tasks.py. Stub function `_run_precheck_pipeline(image_id, user_id) -> PrecheckResult` raises NotImplementedError. Fill in the 5-step pipeline body.

Blockers / notes:
<none | specific issue>
```
```

---

### Template C — `meesell-api-routes-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** C (after services-builder + image-precheck-builder complete)
**Branch:** `feature/image-precheck/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-backend-session-{N}
Lead: meesell-backend-coordinator

## Your mission
Create the image module router (2 endpoints), Pydantic schemas, wire router into main.py, and author the 5 unit + 3 integration tests per §11.K.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-api-routes-builder/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-api-routes-builder/MEMORY.md
3. docs/BACKEND_ARCHITECTURE.md §11.B (BOTH endpoint contracts — §11.B.1 POST + §11.B.2 GET)
4. docs/BACKEND_ARCHITECTURE.md §11.F (Pydantic schemas — ImageUploadResponse, ImageSummary, ImagesListResponse)
5. docs/BACKEND_ARCHITECTURE.md §11.K (test plan — 5 unit + 3 integration tests)
6. docs/BACKEND_ARCHITECTURE.md §4.E (rate-limit decorator pattern; `@rate_limit(scope="image_upload", limit="10/min", key="user_id")` for POST)
7. docs/BACKEND_ARCHITECTURE.md §5A (presentation layer envelope)
8. docs/V1_FEATURE_SPEC.md §F5 (acceptance criteria for the feature)
9. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Backend (rows 7-8, 19, 21-22) + §Decisions / D2 (feature flag check)

## Acceptance criteria
- [ ] `backend/app/modules/image/schemas.py` created with Pydantic v2 models per §11.F:
  - `ImageUploadResponse`: `image_id: UUID`, `gcs_path: str`, `status: Literal["pending"]`, `idx: int`, `enqueued_task_id: str`
  - `ImageSummary`: `image_id: UUID`, `idx: int`, `status: Literal["pending","ready","failed_precheck"]`, `signed_url: str`, `precheck_jsonb: dict`, `is_front: bool`, `width: int | None`, `height: int | None`, `color_space: str | None`, `created_at: datetime`
  - `ImagesListResponse`: `images: list[ImageSummary]`  # 0-4 items per D1
- [ ] `backend/app/modules/image/router.py` created with `APIRouter(prefix="/api/v1/products", tags=["images"])`:
  - `POST /{product_id}/images` → calls `image.service.upload_image`. Accepts `multipart/form-data` with `file: UploadFile` and `idx: int = Form(...)`. Rate-limited `@rate_limit(scope="image_upload", limit="10/min", key="user_id")`. Returns 202 + ImageUploadResponse. Status codes: 400, 401, 404 (ownership), 409 (slot occupied), 415 (non-JPEG).
  - `GET /{product_id}/images` → calls `image.service.list_images`. JWT required. Per-IP rate limit only. Returns 200 + ImagesListResponse. Status codes: 200, 401, 404.
  - **Feature flag check at function entry** of both routes (per D2): `if not settings.FEATURE_IMAGE_PRECHECK_ENABLED: raise HTTPException(status_code=404)` on POST; `return ImagesListResponse(images=[])` on GET when flag is OFF.
- [ ] `backend/app/main.py` MODIFIED:
  - Import `image_router` from `app.modules.image.router`
  - Mount: `app.include_router(image_router)`
- [ ] `backend/tests/unit/image/test_router.py` created with 5 unit tests per §11.K:
  1. Ownership gate: POST `/products/{other_user_product}/images` → 404 (mock `catalog.service.assert_product_ownership` to raise `ProductNotFoundError`)
  2. File validation: non-JPEG file → 400 `validation.image.invalid_format`; > 10 MB file → 400 `validation.image.too_large`; `idx=5` → 400 `validation.image.invalid_idx`
  3. Slot uniqueness: POST with `idx=2` when existing non-deleted image at slot 2 → 409 `image.slot_occupied`
  4. GCS path construction: confirm path EXACTLY equals `meesell-images/{user_id}/{product_id}/{idx}.jpg` via mocked `adapters.gcs.upload_bytes` argument assertion
  5. Celery task enqueue: verify `image_precheck_task.delay(image_id, user_id)` was called via mocked Celery client
- [ ] `backend/tests/integration/test_image_precheck_integration.py` created with 3 integration tests per §11.K:
  1. Full upload → poll → ready flow: POST upload → poll GET until `status == "ready"` (with timeout) → verify `precheck_jsonb` has 5 keys (jpeg_valid, color_space, resolution_pass, white_background, watermark_check) with correct types per §11.G PrecheckResult dataclass
  2. Watermark budget exhaustion: mock `ai_ops.client.call_gemini` to raise `BudgetExceededError` → verify `precheck_jsonb.watermark_check == "skipped_budget"` AND overall `status == "ready"` (confirms §6A.F graceful fallback)
  3. Cross-module URL fetch: `catalog.service.get_preview` calls `image.service.get_image_urls` → verify returned `list[ImageUrl]` has signed URLs ordered by idx with `is_front=True` set ONLY on idx=1 entry
- [ ] OpenAPI summary + description on each route — these become the auto-generated API docs

## Hard constraints
- Routes prefixed `/api/v1/products` (the parent resource — image is a sub-resource); FastAPI router prefix is `/api/v1/products` and route paths are `/{product_id}/images`
- Status code 202 on POST (NOT 200 or 201) — upload persisted synchronously, precheck enqueued asynchronously
- Multipart upload via FastAPI `UploadFile` + `Form(...)` — V1 is direct multipart per CLAUDE.md API design ("File uploads: multipart/form-data, max 10MB per image"); V1.5 may add direct-to-GCS upload per §11.L
- The Pydantic Literal `idx: int` accepted is strictly `[1, 2, 3, 4]` per D1 — confirmed by the §11.B.1 spec text; route-level Pydantic validation rejects `idx=5+` BEFORE reaching the service
- Audit event `image.upload.received` is emitted by middleware (audit_mw) on 2xx — you do NOT write the audit call directly; the middleware reads response status and config per §4.G
- GET endpoint has NO audit (read-only polling per §11.J)
- Feature flag check returns 404 on POST (per D2 + master plan §3.2) — NOT 503. 404 mimics "endpoint doesn't exist" so clients can't probe the feature.
- GET when flag OFF returns 200 + empty `{images: []}` — NOT 404 (sellers may have legacy images and the read should remain idempotent)
- Integration tests run against real Postgres + Valkey via dev tunnel per §19 — mocks for `ai_ops.client.call_gemini` only (deterministic watermark fixtures)

## Files you MAY touch
- `backend/app/modules/image/router.py` (NEW)
- `backend/app/modules/image/schemas.py` (NEW)
- `backend/app/main.py` (MODIFY — mount image_router)
- `backend/tests/unit/image/__init__.py` (NEW)
- `backend/tests/unit/image/test_router.py` (NEW)
- `backend/tests/integration/test_image_precheck_integration.py` (NEW)

## Files you must NOT touch
- `backend/app/modules/image/service.py` (owned by services-builder — READ, don't modify)
- `backend/app/modules/image/domain.py` (owned by services-builder — READ)
- `backend/app/modules/image/exceptions.py` (owned by services-builder — READ)
- `backend/app/modules/image/tasks.py` (owned by services-builder + image-precheck-builder)
- `backend/app/modules/image/repository.py` (owned by services-builder — READ only if needed)
- `backend/app/adapters/`, `backend/app/shared/models/`, `backend/app/core/`, `backend/app/config.py`
- `backend/app/ai_ops/`
- Any frontend, AI fixture, or infra files

## Final report format
```
REPORT: meesell-api-routes-builder
Session: mesell-image-precheck-backend-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/modules/image/router.py (2 endpoints)
- backend/app/modules/image/schemas.py (3 Pydantic models)
- backend/tests/unit/image/test_router.py (5 tests)
- backend/tests/integration/test_image_precheck_integration.py (3 tests)

Files modified:
- backend/app/main.py (image_router mounted)

Endpoint list:
- POST /api/v1/products/{product_id}/images (202; rate 10/min/user; feature-flag-gated)
- GET /api/v1/products/{product_id}/images (200; per-IP rate limit; feature-flag returns empty list when OFF)

Unit test results:
pytest tests/unit/image/test_router.py -v: PASS | FAIL (paste summary; must be 5/5)

Integration test results:
pytest tests/integration/test_image_precheck_integration.py -v: PASS | FAIL (paste summary; must be 3/3)

OpenAPI delta (run `make openapi` or equivalent):
- Added: POST /api/v1/products/{product_id}/images
- Added: GET /api/v1/products/{product_id}/images
- Updated endpoint count: <prior+2>

Memory update: DONE (.claude/agent-memory/meesell-api-routes-builder/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Blockers / notes:
<none | specific issue>
```
```

---

### Template D — `meesell-prompt-engineer`

**Dispatched by:** `meesell-ai-coordinator`
**Phase:** A (first, independent — can run parallel with database-builder + infra-builder)
**Branch:** `feature/image-precheck/ai`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-ai-session-{N}
Lead: meesell-ai-coordinator

## Your mission
Author the `watermark.v1` Gemini Vision prompt template, the response Pydantic schema, the 30-image golden fixture (15 watermarked + 15 clean), the eval runner, and register the prompt in the prompt registry. NO pipeline code — pipeline is owned by `meesell-image-precheck-builder`.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-prompt-engineer/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-prompt-engineer/MEMORY.md
3. docs/BACKEND_ARCHITECTURE.md §6A.G (prompt_registry contract — PromptTemplate dataclass + file layout under `ai_ops/prompts/`)
4. docs/BACKEND_ARCHITECTURE.md §6A.B (workload list — confirm `"watermark"` Literal)
5. docs/BACKEND_ARCHITECTURE.md §6A.E Layer 1 (prompt-prefix constraint — workload-specific prefix)
6. docs/BACKEND_ARCHITECTURE.md §6A.H (eval — target: watermark accuracy ≥ 85% on 30-image golden set)
7. docs/V1_FEATURE_SPEC.md §F5 (acceptance: watermark accuracy ≥ 85%)
8. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Backend rows 14-16, 23-24 + §Decisions / D1 (4 slots — affects fixture naming `{user_id}/{product_id}/1.jpg` style)

## Acceptance criteria
- [ ] `backend/app/ai_ops/prompts/watermark_v1.py` created with:
  - `TEMPLATE: str` — Gemini Vision system + user prompt. System: "You are a strict reviewer for a marketplace seller's product photograph. Determine if the image contains a visible watermark, text overlay, logo overlay, copyright marker, brand stamp, or any superimposed text/logo (excluding the actual product itself)." User: "Analyze this image. Return STRICTLY JSON of shape `{has_watermark: bool, confidence: float}`. confidence is in [0.0, 1.0]. Do NOT include any other field, prose, or markdown."
  - `VERSION: str = "v1"`
  - `WORKLOAD: str = "watermark"`
  - `RENDERED_BY: Literal["text", "vision"] = "vision"`
  - `class WatermarkResponse(BaseModel)`: `has_watermark: bool`, `confidence: float = Field(ge=0.0, le=1.0)`
- [ ] `backend/app/ai_ops/prompts/__init__.py` MODIFIED:
  - Export `TEMPLATE as WATERMARK_V1_TEMPLATE`, `WatermarkResponse`
- [ ] `backend/app/ai_ops/prompt_registry.py` MODIFIED:
  - Add a registry entry: workload="watermark", prompt_id="watermark.v1", template=watermark_v1.TEMPLATE, version="v1", rendered_by="vision"
- [ ] `backend/tests/eval/watermark/golden_set.json` created with **30 entries** (15 watermarked + 15 clean):
  - Each entry: `{"gcs_path": "tests/eval/watermark/fixtures/<filename>.jpg", "expected_has_watermark": true|false, "notes": "<source attribution + watermark style if applicable>"}`
  - 15 watermarked: mix of styles (subtle bottom-corner logo, opaque diagonal text, small URL stamp, repeating pattern overlay, signature-style autograph, Meesho-specific seller logos)
  - 15 clean: mix of legitimate product photos (white background, lifestyle, multi-angle, partial-flat-lay)
  - Source attribution: if founder-supplied, note "founder-provided 2026-MM-DD"; if synthesized for the test (Pillow-rendered text overlay on public-domain images), note "synthesized via tests/eval/watermark/synthesize.py"
- [ ] `backend/tests/eval/watermark/fixtures/` directory with the 30 actual .jpg files (committed to git if size permits — confirm total fixture size < 30 MB before commit; if larger, use Git LFS or store paths to GCS dev bucket)
- [ ] `backend/tests/eval/watermark/test_accuracy.py` created — eval runner:
  - Loads `golden_set.json`
  - For each entry: invokes `ai_ops.client.call_gemini(AICallContext(workload="watermark", user_id=TEST_USER_ID), prompt_id="watermark.v1", prompt_vars={}, image_bytes=<file bytes>)`
  - Parses `AIResponse.parsed` as `WatermarkResponse`
  - Computes `accuracy = sum(predicted_has_watermark == expected_has_watermark) / 30`
  - **Asserts `accuracy ≥ 0.85`** (the locked threshold per §6A.H + AI lead Stop Conditions)
  - Reports per-fixture pass/fail + the aggregate metric
- [ ] `backend/tests/eval/README.md` updated with a "watermark" section documenting golden set composition + invocation `pytest tests/eval/watermark/test_accuracy.py`
- [ ] `backend/tests/test_prompts.py` (parser unit tests) updated with a test for `WatermarkResponse` parsing — feeds 3 sample JSON strings (valid, malformed, extra-fields) and asserts parser behavior per §6A.E Layer 2

## Hard constraints
- Per-call vision cost: TARGET ≤ ₹0.05 (the ai lead merge gate). MEASURE actual per-call cost on a 5-image sample run; report in final report. If observed cost > ₹0.05 per call, FLAG for founder escalation (do NOT silently exceed; per `meesell-ai-coordinator.md` Stop Conditions).
- Few-shot examples: NONE for vision (per `meesell-prompt-engineer.md` constraint — 4-example cap, but vision few-shot is high-cost; V1 keeps it zero-shot). If accuracy < 85% after 3 iteration cycles, escalate to ai lead for few-shot consideration.
- The response shape is STRICTLY `{has_watermark: bool, confidence: float}` — NO extra fields. Layer 2 guardrail rejects responses with extra fields.
- `models/gemini-2.5-flash` is the locked model (per CLAUDE.md Decision 3). Do NOT switch models even for vision.
- The 30-image golden set is the regression gate — any prompt change MUST re-run this eval and meet ≥ 85% before merging.
- Layer 1 prefix is prepended by `ai_ops.guardrail.apply_prompt_constraint` per §6A.E — your TEMPLATE string is the BASE prompt; the Layer 1 prefix is NOT inside your file (it's bonded to the workload by guardrail.py per §6A.E).
- Fixture images: if any image contains a real person's face, use only images with explicit usage rights or anonymize/pixelate the face before commit. Founder must confirm fixture source if synthesized.

## Files you MAY touch
- `backend/app/ai_ops/prompts/watermark_v1.py` (NEW)
- `backend/app/ai_ops/prompts/__init__.py` (MODIFY — export the new template)
- `backend/app/ai_ops/prompt_registry.py` (MODIFY — register watermark.v1)
- `backend/tests/eval/watermark/golden_set.json` (NEW)
- `backend/tests/eval/watermark/fixtures/` (NEW — 30 .jpg files)
- `backend/tests/eval/watermark/test_accuracy.py` (NEW)
- `backend/tests/eval/watermark/synthesize.py` (NEW — if synthesizing fixtures)
- `backend/tests/eval/README.md` (MODIFY)
- `backend/tests/test_prompts.py` (MODIFY — add WatermarkResponse parser test)

## Files you must NOT touch
- `backend/app/ai_ops/client.py` (READ-ONLY — sole import surface, do not modify)
- `backend/app/ai_ops/guardrail.py`, `cost_tracker.py`, `budget_cap.py`, `eval.py` (READ-ONLY)
- `backend/app/modules/image/` (the precheck pipeline is owned by image-precheck-builder; your scope ends at the prompt + eval)
- `backend/app/ai_ops/prompts/autofill_v1.py`, `smart_picker_v1.py` (those are different feature scopes)
- Any backend services/router/migration files
- Any frontend or infra files

## Final report format
```
REPORT: meesell-prompt-engineer
Session: mesell-image-precheck-ai-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/ai_ops/prompts/watermark_v1.py
- backend/tests/eval/watermark/golden_set.json (30 entries: 15 watermarked, 15 clean)
- backend/tests/eval/watermark/fixtures/ (30 .jpg files; total size: <MB>)
- backend/tests/eval/watermark/test_accuracy.py
- backend/tests/eval/watermark/synthesize.py (if synthesized — note source)

Files modified:
- backend/app/ai_ops/prompts/__init__.py (added WATERMARK_V1_TEMPLATE + WatermarkResponse exports)
- backend/app/ai_ops/prompt_registry.py (registered watermark.v1)
- backend/tests/eval/README.md (added watermark section)
- backend/tests/test_prompts.py (added WatermarkResponse parser test)

Eval result on golden set:
- Accuracy: <XX.X>% (target ≥ 85%) — must be ≥ 85% to merge
- Per-call avg latency: <X.X>s
- Per-call avg cost: ₹<X.XX> (target ≤ ₹0.05 — if exceeded, FLAG)
- Total run cost: ₹<X.XX> (30 calls)
- LangFuse trace sample link: <paste>

Parser tests:
pytest tests/test_prompts.py::test_watermark_parser -v: PASS | FAIL

Memory update: DONE (.claude/agent-memory/meesell-prompt-engineer/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Hand-off to meesell-image-precheck-builder: prompt registered at `watermark.v1`; call via `ai_ops.client.call_gemini(AICallContext(workload="watermark", ...), prompt_id="watermark.v1", prompt_vars={}, image_bytes=...)`.

Blockers / notes:
<none | specific issue — especially: per-call cost > ₹0.05 if observed>
```
```

---

### Template E — `meesell-image-precheck-builder`

**Dispatched by:** `meesell-ai-coordinator`
**Phase:** B (after prompt-engineer + services-builder shell — image-precheck-builder fills in the pipeline body)
**Branch:** `feature/image-precheck/ai`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-ai-session-{N}
Lead: meesell-ai-coordinator

## Your mission
Fill in the 5-step precheck pipeline body inside `backend/app/modules/image/tasks.py` (the Celery shell is already in place from services-builder; the `_run_precheck_pipeline` stub is awaiting implementation). Also author the 20-image deterministic smoke fixture for Gate 2 of D2.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-image-precheck-builder/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-image-precheck-builder/MEMORY.md
3. .claude/agent-memory/meesell-prompt-engineer/feature_image_precheck_session_*_handoff.md (read the prompt-engineer hand-off — the watermark.v1 registration details)
4. .claude/agent-memory/meesell-services-builder/feature_image_precheck_session_*_handoff.md (read the services-builder hand-off — confirm the `_run_precheck_pipeline` stub function signature)
5. docs/BACKEND_ARCHITECTURE.md §11.E (the 9-step locked outline for the Celery task — your scope is steps 2-7; steps 1, 8, 9 are services-builder's)
6. docs/BACKEND_ARCHITECTURE.md §6A.B + §6A.C + §6A.F (workload="watermark"; call_gemini interface; graceful fallback on BudgetExceededError → "skipped_budget")
7. docs/V1_FEATURE_SPEC.md §F5 (acceptance: 5 checks within 8s/image worker budget; per-check pass/fail with fix hint)
8. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Backend rows 6, 25-26 + §Decisions D2 Gate 2 (Pillow smoke)
9. `backend/app/modules/image/tasks.py` (the current state — services-builder shipped the shell)
10. `backend/app/ai_ops/prompts/watermark_v1.py` (prompt-engineer's deliverable)

## Acceptance criteria
- [ ] Implement `_run_precheck_pipeline(image_id: UUID, user_id: UUID) -> PrecheckResult` inside `backend/app/modules/image/tasks.py` — REPLACE the `NotImplementedError` stub from services-builder. The function:
  1. Fetches image bytes from GCS via `adapters.gcs.download_bytes(path=image.gcs_path)`
  2. **Step 1: JPEG check** — `Image.open(BytesIO(bytes))`; check `img.format == "JPEG"`. Fail → `jpeg_valid=False`, status="failed_precheck", EARLY EXIT (skip subsequent steps).
  3. **Step 2: RGB/CMYK check** — `img.mode` ∈ {"RGB", "RGBA"} → `color_space="RGB"`, OK; "CMYK" → `color_space="CMYK"`, FAIL; otherwise `color_space="Gray"`, fail. Records `color_space` field unconditionally.
  4. **Step 3: Resolution check** — `img.size` = `(width, height)`; pass iff `width ≥ 1500 AND height ≥ 1500`.
  5. **Step 4: White-BG heuristic** — Sample 4 corners of the image, each a 5×5 px patch. Compute mean brightness per channel over the patch. Pass iff all 4 patches have mean brightness ≥ 235 (out of 255). Document the algorithm in the module header docstring per §11.A "the 5-step precheck pipeline algorithm internals — image-precheck-builder owns the JPEG / RGB / resolution / white-bg / watermark logic". The 4-corner choice + 5×5 patch size + 235 threshold are V1 algorithm — V1.5 may iterate. **AMENDMENT 2026-06-11 (G2 founder ruling, AI lead-direct per §F5 doc-status-line precedent):** this line originally read `16×16 patch × 240 threshold`; the as-built `tasks.py` shipped `5×5 patch × 235 threshold`. Founder RULED keep-as-built; plan text amended to match the code (the line's own "V1 algorithm — V1.5 may iterate" posture authorizes this as a doc-level constant correction, NOT a §7.3 founder-LOCK change). Corner=255 known-good fixtures clear either threshold, so Gate 2 evidence is valid under both.
  6. **Step 5: Watermark vision** — Call `await ai_ops.client.call_gemini(AICallContext(workload="watermark", user_id=user_id), prompt_id="watermark.v1", prompt_vars={}, image_bytes=bytes)`. Parse `AIResponse.parsed` as `{has_watermark: bool, confidence: float}`. Map result: `has_watermark=False AND confidence ≥ 0.8` → `watermark_check="no_watermark"`; `has_watermark=True AND confidence ≥ 0.8` → `"has_watermark"`; `confidence < 0.8` → `"uncertain"`. **On `BudgetExceededError`** (raised by call_gemini per §6A.F): `watermark_check="skipped_budget"` (INFORMATIONAL — does NOT fail the overall image; per the founder's locked decision).
  7. **Aggregate**: build `PrecheckResult(jpeg_valid, color_space, resolution_pass, white_background, watermark_check, watermark_confidence)`. Set `status="ready"` iff `jpeg_valid AND color_space=="RGB" AND resolution_pass AND white_background` (4 deterministic steps); else `status="failed_precheck"`. **Watermark step is INFORMATIONAL, not blocking** — even `"has_watermark"` or `"skipped_budget"` does NOT prevent status="ready".
  8. Build a `precheck_jsonb` dict suitable for the §11.G `PrecheckResult` shape — additionally include a `fix_hints: dict[str, str]` map for the 4 deterministic checks that failed:
     - `jpeg_valid=False` → fix_hint `"Save your image as JPEG. PNG and other formats are not accepted."`
     - `color_space != "RGB"` → fix_hint `"Convert your image to RGB color mode. CMYK is not supported."`
     - `resolution_pass=False` → fix_hint `"Use an image at least 1500×1500 pixels. Smaller images look low-quality on Meesho."`
     - `white_background=False` → fix_hint `"Use a plain white background. Mixed or dark backgrounds reduce conversion."`
     - For the watermark step: ALWAYS include a hint (informational): `"Avoid watermarks, text overlays, or logos. Meesho rejects products with branded photography."` (per V1 spec §F5 "fix hint" requirement)
  - **AMENDMENT 2026-06-11 (G3 founder ruling): `fix_hints` is a FRONTEND static map, NOT an AI/backend deliverable.** Founder RULED the per-check fix-hint strings live as a static map on the frontend (the FE model already carries `PRECHECK_HINTS`, confirmed by the FE coordinator's audit). The backend `precheck_jsonb` emits the per-check boolean pass/fail; the FE keys its hint copy off those booleans. The §968 / §F5 "per-check pass/fail with one-line fix hint" acceptance traceability therefore points at the **FE slice** (`meesell-frontend-coordinator`), not at `tasks.py`. The hint strings quoted above are retained here as the canonical copy SOURCE for the FE map (single source of truth for the wording); they are NOT built into `tasks.py`.
- [ ] Module header docstring in `tasks.py` documents: (a) the 5-step pipeline ORDER, (b) the white-BG heuristic ALGORITHM CHOICE (4 corners × 5×5 patches × mean brightness ≥ 235), (c) the watermark "informational not blocking" contract, (d) the §11.A seam boundary (your scope vs services-builder's scope).
- [ ] Per-image total time budget: **all 4 deterministic Pillow checks ≤ 2 seconds**; watermark vision adds ~3-5 seconds; total ≤ 8 seconds per §F5 acceptance. Add a timing assertion to the smoke test (Gate 2).
- [ ] `backend/tests/eval/precheck_smoke/__init__.py` (NEW)
- [ ] `backend/tests/eval/precheck_smoke/fixtures.json` (NEW) — 20 entries: 10 known-bad + 10 known-good. Composition:
  - Known-bad (must produce `failed_precheck`):
    1. PNG file (jpeg_valid=False)
    2. CMYK JPEG (color_space=CMYK)
    3. 1000×1000 JPEG (resolution_pass=False)
    4. Dark gray background JPEG (white_background=False)
    5. 800×800 PNG (multi-fail: jpeg + resolution)
    6. CMYK 1200×1200 (multi-fail: color_space + resolution)
    7. Colorful textured background JPEG (white_background=False)
    8. JPEG with hue tint (still NOT pure white BG)
    9. Black BG product JPEG
    10. Lifestyle photo with grass BG
  - Known-good (must produce `ready`, ignoring watermark step):
    1-10. 10 product JPEGs with white BG ≥ 1500×1500 RGB
- [ ] `backend/tests/eval/precheck_smoke/fixtures/` directory with the 20 actual files
- [ ] `backend/tests/eval/precheck_smoke/test_pillow_checks.py` (NEW) — runs all 4 Pillow checks against each fixture; asserts all 10 bad → `failed_precheck` AND all 10 good → `ready`; asserts per-image Pillow total time ≤ 2 seconds (use `time.monotonic()`)

## Hard constraints
- Watermark vision call uses `ai_ops.client.call_gemini` ONLY — NEVER `adapters/gemini.py` directly (per §16.D.2 + the §6A.A boundary)
- Watermark step is INFORMATIONAL, not blocking — even `"has_watermark"` does NOT set `status="failed_precheck"`. ONLY the 4 deterministic checks gate status.
- `BudgetExceededError` → `watermark_check="skipped_budget"` AND overall `status="ready"` if the 4 deterministic steps passed. This is the founder's locked decision per §6A.F.
- Pillow is opened ONCE per image (single `Image.open(BytesIO)` read), then the 4 checks consume the in-memory `img` object — NOT 4 separate opens (cost + latency).
- The fixture set under `precheck_smoke/` is DISTINCT from the watermark `golden_set/` — different scope (Pillow vs vision), different purpose (D2 Gate 2 vs Gate 1).
- Do NOT change the watermark prompt or the watermark eval — those are prompt-engineer's scope. Your scope is the CONSUMER side of the prompt (the call site + the response mapping).
- The Celery task is synchronous (`@shared_task` without `async def`); your `_run_precheck_pipeline` is `async def` and is invoked via `asyncio.run(...)` from the outer task — services-builder already wired this.
- Per-image latency target: ≤ 8 seconds total per §F5 acceptance. If your implementation routinely exceeds, escalate to ai lead BEFORE merging.

## Files you MAY touch
- `backend/app/modules/image/tasks.py` (MODIFY — replace `_run_precheck_pipeline` stub with the 5-step body + flesh out the module header docstring)
- `backend/tests/eval/precheck_smoke/__init__.py` (NEW)
- `backend/tests/eval/precheck_smoke/fixtures.json` (NEW)
- `backend/tests/eval/precheck_smoke/fixtures/` (NEW — 20 files)
- `backend/tests/eval/precheck_smoke/test_pillow_checks.py` (NEW)

## Files you must NOT touch
- `backend/app/modules/image/service.py`, `repository.py`, `domain.py`, `exceptions.py` (owned by services-builder — READ, don't modify)
- The Celery `@shared_task` decorator + the outer `asyncio.run(...)` wrapper in `tasks.py` (owned by services-builder — your scope is the pipeline body ONLY)
- `backend/app/ai_ops/prompts/watermark_v1.py` (owned by prompt-engineer — READ, don't modify)
- `backend/app/ai_ops/client.py`, `guardrail.py`, `cost_tracker.py`, `budget_cap.py` (READ-ONLY — these are owned by `ai_ops/` layer, not modifiable here)
- `backend/app/modules/image/router.py`, `schemas.py` (owned by api-routes-builder)
- `backend/tests/eval/watermark/` (owned by prompt-engineer)
- Any backend services/migration/adapter files outside the scope above
- Any frontend or infra files

## Final report format
```
REPORT: meesell-image-precheck-builder
Session: mesell-image-precheck-ai-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files modified:
- backend/app/modules/image/tasks.py (_run_precheck_pipeline filled in; module header documents 5-step + white-BG algorithm + watermark contract + §11.A seam)

Files created:
- backend/tests/eval/precheck_smoke/__init__.py
- backend/tests/eval/precheck_smoke/fixtures.json (10 bad + 10 good)
- backend/tests/eval/precheck_smoke/fixtures/ (20 files; total <MB>)
- backend/tests/eval/precheck_smoke/test_pillow_checks.py

Pipeline body verification:
- Step 1 JPEG check: implemented (early exit on fail) ✅
- Step 2 RGB/CMYK check: implemented (Pillow img.mode) ✅
- Step 3 Resolution check: implemented (img.size ≥ 1500×1500) ✅
- Step 4 White-BG check: implemented (4-corner × 16x16 patches × mean ≥ 240) ✅
- Step 5 Watermark vision: implemented (call_gemini workload="watermark"; "skipped_budget" on BudgetExceededError) ✅

Smoke test result:
pytest tests/eval/precheck_smoke/test_pillow_checks.py -v: PASS | FAIL (must be 20/20)
Per-image Pillow total time (worst case): <X.X>s (target ≤ 2s)
Per-image full pipeline time (avg incl. watermark): <X.X>s (target ≤ 8s)

Memory update: DONE (.claude/agent-memory/meesell-image-precheck-builder/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Blockers / notes:
<none | specific issue — especially: per-image total > 8s>
```
```

---

### Template F — `meesell-angular-service-builder`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** D (after backend group PR merges to feature/image-precheck — API contract is locked)
**Branch:** `feature/image-precheck/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-frontend-session-{N}
Lead: meesell-frontend-coordinator

## Your mission
Build the `ImageService` (multipart upload + backoff polling), register the `/catalogs/:id/images` route with the `featureFlagGuard`, and integrate the build-time `FEATURE_IMAGE_PRECHECK_ENABLED` flag.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-angular-service-builder/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-angular-service-builder/MEMORY.md
3. docs/FRONTEND_ARCHITECTURE.md (FULL — focus on Layer 4 boundaries, signals + RxJS pattern, HttpClient interceptors)
4. docs/V1_FEATURE_SPEC.md §F5 (user journey + UX requirements)
5. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Frontend rows 7-10 + §Decisions / D1 (4 slots) + §Decisions / D2 (flag posture)
6. The merged backend OpenAPI export for the 2 image endpoints (run `make openapi` if available, or read `backend/openapi.json` if checked in)
7. `frontend/src/app/core/interceptors/auth.interceptor.ts` (existing JWT interceptor — your upload calls inherit Bearer token from this)
8. `frontend/src/app/core/guards/auth.guard.ts` (existing — your `featureFlagGuard` follows a parallel pattern)

## Acceptance criteria
- [ ] `frontend/src/app/core/services/image.service.ts` (NEW):
  - `@Injectable({ providedIn: 'root' })`
  - `inject(HttpClient)`, `inject(AuthService)`, `inject(ApiClientService)` (typed wrapper if it exists; else direct HttpClient)
  - `upload(productId: string, file: File, slotIdx: number): Observable<ImageUploadResponse>`:
    - Constructs `FormData` with `file` and `idx`
    - `POST /api/v1/products/{productId}/images`
    - Reports upload progress via `{ reportProgress: true, observe: 'events' }`
    - Maps HTTP events to a typed `UploadProgress | UploadComplete` discriminated union
    - On 415 → `catchError` mapping to user-facing message "Only JPEG images are supported"
    - On 413 → "Image exceeds 10 MB"
    - On 503 → "Upload service temporarily unavailable. Try again in a moment." + auto-retry once with 2s delay
    - On 404 (feature flag OFF) → "Image upload is not available yet" + route guard prevents reaching this in normal flow
  - `pollImages(productId: string): Observable<ImagesListResponse>`:
    - `GET /api/v1/products/{productId}/images`
    - Backoff polling: emit immediately, then `interval`-style with delay 1s → 2s → 4s (capped). STOP polling when ALL images have `status` ≠ `"pending"` (i.e. all are `ready` OR `failed_precheck`). Use `takeWhile` + `switchMap`.
    - Maximum total polling duration: 30 seconds. After that, complete the observable and surface a "polling timeout — refresh to retry" toast.
    - Returns the final list (or current snapshot on timeout)
  - Typed return models: `ImageUploadResponse`, `ImageSummary`, `ImagesListResponse` — match the OpenAPI shape EXACTLY (the type contract is sourced from backend OpenAPI; if a TypeScript codegen is wired, use it; else hand-write)
- [ ] `frontend/src/app/core/services/image.service.spec.ts` (NEW):
  - Mocks `HttpClient` (HttpTestingController)
  - Tests `upload()`: progress events, 415, 413, 503 retry, 404 flag-off
  - Tests `pollImages()`: backoff timing, stop condition on all-ready, 30s timeout
- [ ] `frontend/src/app/app.routes.ts` MODIFIED:
  - Register `/catalogs/:id/images` → lazy-loaded `ImageUploaderComponent` (loadComponent)
  - Apply `authGuard` (existing) + `featureFlagGuard('FEATURE_IMAGE_PRECHECK_ENABLED')` (new — see below) — the route is GUARDED, not unconditional
- [ ] `frontend/src/app/core/guards/feature-flag.guard.ts` (NEW or MODIFY if exists):
  - `featureFlagGuard(flagName: string): CanActivateFn` factory
  - Reads `inject(FeatureFlagsService).isEnabled(flagName)` synchronously
  - If disabled: `return inject(Router).parseUrl('/catalogs/' + route.params['id'] + '/edit')` + dispatch a toast "Image upload is coming soon"
  - If enabled: `return true`
- [ ] `frontend/src/app/core/services/feature-flags.service.ts` (MODIFY or NEW):
  - `@Injectable({ providedIn: 'root' })`
  - `isEnabled(flagName: string): boolean` — reads from `environment.featureFlags` at build time per FRONTEND_ARCHITECTURE V1 build-time env pattern
  - Add `imagePrecheckEnabled: boolean` to `environment.featureFlags`
- [ ] `frontend/src/environments/environment.ts` MODIFIED: add `featureFlags.imagePrecheckEnabled = true` (dev default per D2)
- [ ] `frontend/src/environments/environment.staging.ts` MODIFIED: add `featureFlags.imagePrecheckEnabled = false` (staging default per D2)

## Hard constraints
- HttpClient interceptor chain (JWT bearer + error handling) is wired in `app.config.ts` — your service does NOT manually attach `Authorization` headers; the interceptor does it
- Multipart upload: `Content-Type: multipart/form-data` is set AUTOMATICALLY by the browser when `FormData` is the body. DO NOT manually set `Content-Type` — that breaks the multipart boundary
- Backoff polling: NEVER use `setInterval` directly — use RxJS `interval()` + `concatMap` per FRONTEND_ARCHITECTURE.md ("RxJS for async; HTTP, WebSocket, timers — RxJS")
- Polling STOP CONDITION is "all images have status ≠ pending" — NOT "any single image is ready". This prevents premature exit when 1 image is ready but others are still pending.
- The route is registered at `/catalogs/:id/images` — matches V1 spec §6 frontend routes table (the architecture-canonical path is `features/images/` per Layer 4)
- The component path is `frontend/src/app/features/images/image-uploader.component.ts` (NOT `pages/image-uploader/` — the architecture is `features/`)
- Strict TypeScript: no `any`, no `as unknown` — match OpenAPI types exactly
- featureFlagGuard is SYNCHRONOUS (V1: build-time env, signal-style); V1.5 may add remote config + async resolution

## Files you MAY touch
- `frontend/src/app/core/services/image.service.ts` (NEW)
- `frontend/src/app/core/services/image.service.spec.ts` (NEW)
- `frontend/src/app/core/services/feature-flags.service.ts` (NEW or MODIFY)
- `frontend/src/app/core/guards/feature-flag.guard.ts` (NEW)
- `frontend/src/app/app.routes.ts` (MODIFY — register new route)
- `frontend/src/environments/environment.ts` (MODIFY — add flag default true)
- `frontend/src/environments/environment.staging.ts` (MODIFY — add flag default false)

## Files you must NOT touch
- `frontend/src/app/features/images/image-uploader.component.ts` (owned by component-builder)
- `frontend/src/app/features/images/precheck-report.component.ts` (owned by component-builder)
- Any `frontend/src/app/ui/` files (UI Kit primitives — Layer 2 boundary; not your scope)
- Any backend, AI, or infra files

## Final report format
```
REPORT: meesell-angular-service-builder
Session: mesell-image-precheck-frontend-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/core/services/image.service.ts (upload + pollImages)
- frontend/src/app/core/services/image.service.spec.ts
- frontend/src/app/core/services/feature-flags.service.ts (if new)
- frontend/src/app/core/guards/feature-flag.guard.ts

Files modified:
- frontend/src/app/app.routes.ts (/catalogs/:id/images registered with featureFlagGuard)
- frontend/src/environments/environment.ts (featureFlags.imagePrecheckEnabled = true)
- frontend/src/environments/environment.staging.ts (featureFlags.imagePrecheckEnabled = false)
- frontend/src/app/core/services/feature-flags.service.ts (if existed)

Service test results:
pnpm test --include='**/image.service.spec.ts' --watch=false: PASS | FAIL (paste summary)

Build evidence:
pnpm build: PASS | FAIL — duration <X>s (target <90s)

Memory update: DONE (.claude/agent-memory/meesell-angular-service-builder/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Hand-off to meesell-angular-component-builder: ImageService injection signature is `inject(ImageService)`; methods `upload(productId, file, slotIdx)` and `pollImages(productId)` return typed Observables. Route is at `/catalogs/:id/images`.

Blockers / notes:
<none | specific issue>
```
```

---

### Template G — `meesell-angular-component-builder`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** E (after angular-service-builder completes)
**Branch:** `feature/image-precheck/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-frontend-session-{N}
Lead: meesell-frontend-coordinator

## Your mission
Build the `ImageUploaderComponent` (drag-drop + 4-slot grid + upload progress) and the `PrecheckReportComponent` (per-check pass/fail rows + fix-hint inline + red-border failed images). Both Layer 4 components using `mee-*` primitives from `@mee/ui` and composites from `@mee/shared`.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-angular-component-builder/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-angular-component-builder/MEMORY.md
3. .claude/agent-memory/meesell-angular-service-builder/feature_image_precheck_session_*_handoff.md (the ImageService interface)
4. docs/FRONTEND_ARCHITECTURE.md (FULL — focus on Layer 4 features, mee-file-upload, mee-card, mee-badge, mee-status-badge, OnPush, signals)
5. docs/V1_FEATURE_SPEC.md §F5 (user journey + acceptance criteria)
6. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Frontend rows 1-6 + §Decisions / D1 (4 slots — render 4 slots, NOT 6)

## Acceptance criteria
- [ ] `frontend/src/app/features/images/image-uploader.component.ts` (NEW):
  - `@Component({ selector: 'mee-image-uploader', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush, imports: [CommonModule, MeeFileUpload, MeeCard, MeeButton, MeeBadge, MeePageHeader, PrecheckReportComponent, ...] })`
  - Template:
    - `mee-page-header` with title "Product images" + subtitle "Upload up to 4 images. The first is the front image."
    - A `@for` loop over `slots = [1, 2, 3, 4]` (literal array — D1 lock) rendering 4 `mee-card`s in a 2×2 or 1×4 responsive grid (Tailwind: `grid grid-cols-2 md:grid-cols-4 gap-4`)
    - Each card shows: slot number (1-4), "Front image" badge if idx=1, the current image thumbnail if uploaded (with upload progress overlay if uploading), or a `mee-file-upload` if empty
    - On file dropped/selected: invoke `imageService.upload(productId, file, slotIdx)`; subscribe to the progress observable; update local signal with progress
    - On 409 (slot occupied): show toast "Image already in that slot. Delete it first to replace." (V1 does not expose delete — for V1 this is informational only; V1.5 will add a delete button per §11.M)
    - Below the grid: `<mee-precheck-report [images]="images()">` — child component renders the per-image status
  - Signals: `images = signal<ImageSummary[]>([])`, `uploading = signal<Map<number, number>>(new Map())` (slotIdx → progress %), `productId = computed(() => ...)`
  - Lifecycle: `ngOnInit()` starts `imageService.pollImages(productId).subscribe()` and updates `images()` signal; unsubscribes via `takeUntilDestroyed()`
  - Docstring on the class documents the multipart upload + 4-slot grid + retry semantics + flag-OFF behavior (the route guard handles flag-OFF; if a user reaches the component, the flag is ON)
- [ ] `frontend/src/app/features/images/image-uploader.component.html` (NEW): template per above
- [ ] `frontend/src/app/features/images/image-uploader.component.spec.ts` (NEW): renders 4 slots, fires upload on file drop, displays progress, shows toast on 409
- [ ] `frontend/src/app/features/images/precheck-report.component.ts` (NEW):
  - `@Component({ selector: 'mee-precheck-report', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush, imports: [CommonModule, MeeCard, MeeBadge, MeeStatusBadge, ...] })`
  - Input: `@Input({ required: true }) images!: ImageSummary[];`
  - Template:
    - For each image, render a `mee-card` with the image thumbnail (signed_url) on the left, status badge top-right (`mee-status-badge [status]="image.status"`), and a 5-row pass/fail list per the `precheck_jsonb` content:
      - JPEG ✓/✗ + fix_hint
      - RGB ✓/✗ + fix_hint
      - Resolution ≥1500×1500 ✓/✗ + fix_hint
      - White background ✓/✗ + fix_hint
      - Watermark check: ✓ "no_watermark" (green) | ⚠ "has_watermark" (yellow) | ⚠ "uncertain" (yellow) | ⏸ "skipped_budget" (gray) + fix_hint inline
    - **Red border on `failed_precheck` images** (Tailwind `border-2 border-red-500` on the outer card)
    - **Yellow border on `ready` images with `watermark_check != "no_watermark"`** (informational visual signal)
    - **Green border on `ready` images with `watermark_check == "no_watermark"`** (full pass)
    - Re-upload affordance: a "Replace image" button beneath each failed image — V1 stub that emits a `replaceImage` event to the parent (parent handles re-upload via the same upload flow; the existing image is NOT deleted in V1 because there's no DELETE endpoint per §11.M, so the affordance is informational only with a "Coming soon" tooltip)
  - Docstring on the class documents the per-check rendering + fix-hint copy convention + the border-color contract
- [ ] `frontend/src/app/features/images/precheck-report.component.html` (NEW): template per above
- [ ] `frontend/src/app/features/images/precheck-report.component.spec.ts` (NEW): renders 5 rows per image; correct borders for 3 status combos; correct badge per watermark_check value

## Hard constraints
- LAYER 4 FEATURE: ONLY imports from `@mee/ui`, `@mee/shared`, `@mee/layouts`, `@mee/core`, Angular core, RxJS, the generated API client. NO direct `primeng/*` imports. NO `@angular/material/*` imports. The ESLint rule enforces this.
- Standalone components only (no NgModules).
- `ChangeDetectionStrategy.OnPush` on both components.
- Signals for component-local state; RxJS for HTTP/async; `async` pipe in template (NOT manual subscribe in template).
- **4 SLOTS, NOT 6** — the slot loop is `[1, 2, 3, 4]` literal. The "Front image" label appears on idx=1 only.
- Mobile-first responsive design: at 360 px width, 2×2 grid; at 1280 px+, 1×4 grid (per FRONTEND_ARCHITECTURE.md non-negotiable rule 7).
- Accessibility: keyboard nav on `mee-file-upload` (Tab + Enter), aria-label on each slot, color contrast ≥ 4.5:1 for fix hints, the red/yellow/green border MUST be paired with text labels (color-blind safe).
- The fix_hint text in the precheck_jsonb is authored by `meesell-image-precheck-builder` — do NOT re-author; render verbatim.

## Files you MAY touch
- `frontend/src/app/features/images/image-uploader.component.ts` (NEW)
- `frontend/src/app/features/images/image-uploader.component.html` (NEW)
- `frontend/src/app/features/images/image-uploader.component.spec.ts` (NEW)
- `frontend/src/app/features/images/precheck-report.component.ts` (NEW)
- `frontend/src/app/features/images/precheck-report.component.html` (NEW)
- `frontend/src/app/features/images/precheck-report.component.spec.ts` (NEW)
- `frontend/src/app/features/images/image-uploader.component.scss` (NEW — minimal SCSS for Tailwind-extended styling only; mostly Tailwind utilities)

## Files you must NOT touch
- `frontend/src/app/core/services/image.service.ts` (owned by service-builder — READ, don't modify)
- `frontend/src/app/core/services/feature-flags.service.ts` (owned by service-builder)
- `frontend/src/app/app.routes.ts` (owned by service-builder)
- Any file under `frontend/src/app/ui/` (Layer 2 — only the UI Kit team modifies; you CONSUME via `@mee/ui` barrel)
- Any file under `frontend/src/app/shared/` (Layer 3 composites — same boundary)
- Any backend, AI, or infra files

## Final report format
```
REPORT: meesell-angular-component-builder
Session: mesell-image-precheck-frontend-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/features/images/image-uploader.component.ts
- frontend/src/app/features/images/image-uploader.component.html
- frontend/src/app/features/images/image-uploader.component.spec.ts
- frontend/src/app/features/images/precheck-report.component.ts
- frontend/src/app/features/images/precheck-report.component.html
- frontend/src/app/features/images/precheck-report.component.spec.ts
- frontend/src/app/features/images/image-uploader.component.scss (if needed)

Component test results:
pnpm test --include='**/image-uploader.component.spec.ts' --watch=false: PASS | FAIL
pnpm test --include='**/precheck-report.component.spec.ts' --watch=false: PASS | FAIL

Build evidence:
pnpm build: PASS | FAIL — duration <X>s (target <90s)
Bundle delta: +<KB> (image-uploader chunk) +<KB> (precheck-report chunk)

Screenshots attached:
- 360 px: 2×2 grid, empty state ✅
- 360 px: 2×2 grid, all 4 slots filled with 2 ready + 1 failed_precheck + 1 pending ✅
- 1280 px: 1×4 grid, all states ✅

Accessibility checks:
- Keyboard nav on file-upload: PASS
- Aria-labels on slots: PASS
- Color contrast on red/yellow/green borders + fix hint text: PASS (≥ 4.5:1)
- Color-blind safe (status text accompanies color): PASS

PrimeNG import boundary verification:
- grep -r "primeng" frontend/src/app/features/images/: ZERO matches ✅
- grep -r "@angular/material" frontend/src/app/features/images/: ZERO matches ✅

Memory update: DONE (.claude/agent-memory/meesell-angular-component-builder/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Blockers / notes:
<none | specific issue>
```
```

---

### Template H — `meesell-infra-builder`

**Dispatched by:** Founder directly (standalone — no parent lead)
**Phase:** A (first, independent — parallel with backend Phase A specialists)
**Branch:** `feature/image-precheck/infra`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-image-precheck-infra-session-{N}
Lead: meesell-infra-builder (self)

## Your mission
Provision the GCS `meesell-images` bucket via Terraform, configure Workload Identity for the API and Celery worker, update K8s manifests in `dev` and `staging` namespaces with the feature flag and GCS env vars + image-tasks queue config, and author the `image-pipeline-troubleshooting.md` runbook.

## Mandatory reads (in this order)
1. Run `ls .claude/agent-memory/meesell-infra-builder/feature_image_precheck_*.md 2>/dev/null` and read every file found.
2. .claude/agent-memory/meesell-infra-builder/MEMORY.md
3. docs/INFRASTRUCTURE_PLAYBOOK.md (FULL — strict playbook-following per your agent spec)
4. docs/BACKEND_ARCHITECTURE.md §6.D (GCS contract — path convention, signed URL TTL, bucket layout)
5. docs/BACKEND_ARCHITECTURE.md §11.I (image module's adapter usage — confirms the 3 methods consumed)
6. docs/plans/features/image-precheck/FEATURE_PLAN.md §Code surfaces / Infra rows 1-8 + §Decisions / D2 (3 staging gates) + §Documentation deliverables row 10
7. Current state of `infra/terraform/` and `k8s/dev/` + `k8s/staging/` directories — discover via `ls` what already exists vs needs to be created

## Acceptance criteria
- [ ] **GCS bucket `meesell-images` provisioned via Terraform:**
  - Region: `asia-south1` (per CLAUDE.md region lock)
  - Storage class: STANDARD
  - Uniform bucket-level access: ENABLED (NO per-object ACLs)
  - Public access prevention: ENFORCED
  - Lifecycle rule: DELETE objects after 365 days (1-year retention)
  - Two distinct bucket names per environment: `meesell-images-dev`, `meesell-images-staging` (per repo MASTER §3.4 secret strategy)
  - Versioning: DISABLED (V1 simplicity; V1.5 may enable for soft-delete recovery)
- [ ] **IAM bindings via Terraform:**
  - Backend API service account (existing): grant `roles/storage.objectAdmin` SCOPED to `meesell-images-dev/*` (NOT bucket-level admin — least privilege)
  - Celery worker service account (existing): same binding
  - For staging: parallel bindings to `meesell-images-staging/*`
  - Workload Identity Federation: confirm both pods inherit credentials via WIF (NO JSON service account keys committed; per `.github/workflows/ci.yml` line 25 + repo MASTER §3.4)
- [ ] **`infra/terraform/modules/gcs/buckets.tf` (NEW or MODIFY)**: Terraform resource definitions for the buckets + lifecycle policy
- [ ] **`infra/terraform/modules/gcs/iam.tf` (NEW or MODIFY)**: Terraform resource definitions for the IAM bindings
- [ ] **`infra/terraform/environments/dev.tfvars` and `staging.tfvars` (MODIFY)**: bucket names + service account refs
- [ ] **`k8s/dev/api-deployment.yaml` (MODIFY)**:
  - Add env var `FEATURE_IMAGE_PRECHECK_ENABLED=true`
  - Add env var `GCS_BUCKET_IMAGES=meesell-images-dev`
  - Add env var `GCS_SIGNED_URL_TTL_SECONDS=3600`
- [ ] **`k8s/dev/worker-deployment.yaml` (NEW or MODIFY)**:
  - Celery worker pod
  - Queue declaration: include `image-tasks` queue (alongside any existing queue)
  - Worker concurrency: `--concurrency=4` (matches §F5 acceptance: 8s/image × 4 concurrent = ~7,500 images/hour capacity at 1 replica)
  - Replicas: 1 in dev
  - Env vars: same set as api-deployment (GCS_BUCKET_IMAGES, GCS_SIGNED_URL_TTL_SECONDS, plus FEATURE_IMAGE_PRECHECK_ENABLED for symmetry though worker reads from DB regardless)
- [ ] **`k8s/staging/api-deployment.yaml` (MODIFY)**:
  - Add env var `FEATURE_IMAGE_PRECHECK_ENABLED=false` (per D2)
  - Add env var `GCS_BUCKET_IMAGES=meesell-images-staging`
  - Add env var `GCS_SIGNED_URL_TTL_SECONDS=3600`
- [ ] **`k8s/staging/worker-deployment.yaml` (NEW or MODIFY)**: same as dev but replicas=2, GCS_BUCKET_IMAGES=meesell-images-staging
- [ ] **`docs/runbooks/image-pipeline-troubleshooting.md` (NEW)** — at minimum these sections:
  - "Inspecting a stuck precheck job" — Celery introspection (`celery -A app.workers.celery_app inspect active`, Valkey DB 1 broker introspection (`KEYS celery-task-meta-*`), the image's row in PostgreSQL (`SELECT * FROM product_images WHERE id = ?`)
  - "Re-enqueueing a failed precheck" — how to manually re-fire `image_precheck_task.delay(image_id, user_id)` via a one-off Python REPL
  - "GCS tenant-isolation verification command" (D2 Gate 3): the exact `gsutil ls gs://meesell-images-{env}/<other_user_uuid>/` invocation that confirms tenant boundaries are not crossed
  - "Cost monitoring" — projected: at 4 images × 10 MB × N sellers/month, ₹X GCS storage + ₹Y per-call vision cost; LangFuse dashboard link for `workload=watermark`
  - "Rotating the signed-URL TTL" — how to change `GCS_SIGNED_URL_TTL_SECONDS` env var without breaking in-flight signed URLs (the env-var rotation is rolling; existing URLs continue to work until their original TTL expires)
- [ ] **`docs/runbooks/README.md` (MODIFY)**: add link to `image-pipeline-troubleshooting.md`
- [ ] **`.github/workflows/ci.yml` (MODIFY)**: extend the nightly `ai_eval` job to include `pytest tests/eval/watermark/` and `pytest tests/eval/precheck_smoke/` (per Documentation deliverables row 11)

## Hard constraints
- Bucket name STRUCTURE: `meesell-images-{env}` (NOT `meesell-images` shared across envs; NOT `mesell-images` with single-s) — per repo MASTER §3 environment strategy
- Path STRUCTURE inside bucket: `{user_id}/{product_id}/{idx}.jpg` per §6.D + MVP_ARCH §10.8 — this is enforced AT THE APPLICATION LAYER (services-builder), but Workload Identity scope must ALLOW this entire path (per-user prefix is NOT a separate IAM binding; objectAdmin on the bucket path covers it)
- NO public ACLs, NO signed URLs longer than 1 hour (the TTL is the application-layer concern; bucket policy MUST allow signed URL generation but should NOT pre-grant public read)
- NO JSON service account keys committed — Workload Identity Federation per repo MASTER §3.4
- Terraform plan must show: `Plan: <add> to add, <change> to change, 0 to destroy` for `dev` resources. Any destroy on staging requires explicit founder sign-off per `meesell-infra-builder.md` Merge Gate rule
- Cost impact: GCS storage at 4 images × 10 MB × 100 sellers/month ≈ 4 GB/month → ₹X/month at GCS standard rates. Flag in PR body if total monthly cost projection > ₹500
- Staging env var `FEATURE_IMAGE_PRECHECK_ENABLED=false` does NOT change with this PR — it stays false until ALL 3 gates of D2 pass and you (or founder) open a separate `feature/feature-flag/staging-image-precheck-on` micro-branch to flip it (per D2 protocol)
- The `image-tasks` Celery queue name MUST match what `tasks.py` declares as the task `name="image.precheck"` routes to — confirm with services-builder via memo if uncertain

## Files you MAY touch
- `infra/terraform/modules/gcs/buckets.tf` (NEW or MODIFY)
- `infra/terraform/modules/gcs/iam.tf` (NEW or MODIFY)
- `infra/terraform/environments/dev.tfvars` (MODIFY)
- `infra/terraform/environments/staging.tfvars` (MODIFY)
- `k8s/dev/api-deployment.yaml` (MODIFY)
- `k8s/dev/worker-deployment.yaml` (NEW or MODIFY)
- `k8s/staging/api-deployment.yaml` (MODIFY)
- `k8s/staging/worker-deployment.yaml` (NEW or MODIFY)
- `k8s/dev/gcs-secrets.yaml` (NEW conditional — only if WIF requires k8s secret refs)
- `docs/runbooks/image-pipeline-troubleshooting.md` (NEW)
- `docs/runbooks/README.md` (MODIFY)
- `.github/workflows/ci.yml` (MODIFY)
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` (MODIFY — append a "GCS image buckets" section reflecting live state)

## Files you must NOT touch
- Any file under `backend/app/`, `backend/tests/`, `backend/alembic/`
- Any file under `frontend/src/`
- Other modules' Terraform (only `gcs/` is in scope for this dispatch)
- Other namespaces' K8s manifests (no `prod/` — deferred per repo MASTER §3)

## Final report format
```
REPORT: meesell-infra-builder
Session: mesell-image-precheck-infra-session-{N}
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- infra/terraform/modules/gcs/buckets.tf | MODIFIED
- infra/terraform/modules/gcs/iam.tf | MODIFIED
- k8s/dev/worker-deployment.yaml (if new)
- k8s/staging/worker-deployment.yaml (if new)
- docs/runbooks/image-pipeline-troubleshooting.md

Files modified:
- infra/terraform/environments/dev.tfvars
- infra/terraform/environments/staging.tfvars
- k8s/dev/api-deployment.yaml
- k8s/staging/api-deployment.yaml
- docs/runbooks/README.md
- .github/workflows/ci.yml (added watermark + precheck_smoke eval jobs)
- docs/INFRASTRUCTURE_ARCHITECTURE.md

Terraform plan output (paste exact):
```
Plan: <X> to add, <Y> to change, <Z> to destroy.
```

kubectl dry-run output (paste exact):
```
deployment.apps/api-dev configured (server dry run)
deployment.apps/worker-dev created (server dry run)
deployment.apps/api-staging configured (server dry run)
deployment.apps/worker-staging created (server dry run)
```

Smoke deploy to dev namespace:
kubectl get pods -n dev | grep -E 'api|worker': all Ready ✅
GCS bucket created: gsutil ls gs://meesell-images-dev/ returns empty bucket ✅
IAM binding verified: gcloud projects get-iam-policy ... shows objectAdmin on meesell-images-dev/* ✅

Cost projection:
- GCS storage at 4 images × 10 MB × 100 sellers/month = ~4 GB/month at ₹X/month
- Watermark vision cost at 100 sellers × 4 images × ₹0.05 per call = ₹20/month (within budget)
- Total monthly cost impact: ₹<XX> (under ₹500 threshold ✅ | over ₹500 — flagging for founder)

Memory update: DONE (.claude/agent-memory/meesell-infra-builder/feature_image_precheck_session_{N}_handoff.md written) | SKIPPED (reason: <why>)
MEMORY.md "Features in flight" updated: DONE | SKIPPED

Blockers / notes:
<none | specific issue>
```
```

---

## Review + iteration protocol

For each specialist's PR, the lead applies a domain-specific checklist BEFORE clicking merge. Common failure modes have predefined re-dispatch templates. Max 3 iteration cycles per specialist before founder escalation.

### Backend lead (`meesell-backend-coordinator`) review checks

For `feature/image-precheck/backend` → `feature/image-precheck` PR:

| # | Check | Acceptance gate | Failure → re-dispatch |
|---|-------|-----------------|-----------------------|
| B1 | 4-slot CHECK constraint reversibility | `alembic downgrade -1` cleanly drops the constraint along with the table; round-trip `upgrade-downgrade-upgrade` succeeds | Re-dispatch `meesell-database-builder` with preamble "Previous run: downgrade failed because the CHECK was applied as a named constraint that the migration didn't drop explicitly. Use `op.create_check_constraint(...)` in upgrade and rely on `op.drop_table` in downgrade." |
| B2 | GCS path structure | Grep `app/modules/image/service.py` + `tasks.py` for `f"meesell-images/"` or `path =` patterns — every path constructed includes BOTH `user_id` AND `product_id` segments (NOT just `product_id`) | Re-dispatch `meesell-services-builder` with preamble "Previous run constructed GCS path as `meesell-images/{product_id}/{idx}.jpg` — missing user_id prefix. The structural tenant isolation requires `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + MVP_ARCH §10.8. Fix every call site (`upload_image`, `download_bytes` callers, `generate_signed_url` callers)." |
| B3 | Signed URL TTL | Grep `app/modules/image/service.py` for `generate_signed_url` calls — every call passes `ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS` (= 3600); no hardcoded `86400` or `24*3600` | Re-dispatch `meesell-services-builder` with preamble "Previous run used a 24h TTL on signed URLs. The §11.J locked TTL is 1h. Use `settings.GCS_SIGNED_URL_TTL_SECONDS` (default 3600)." |
| B4 | precheck_jsonb passthrough | `GET /api/v1/products/{id}/images` integration test — query the DB row directly, compare `product_images.precheck_jsonb` to the API response `images[i].precheck_jsonb` — VERBATIM equality (same JSON shape, same keys, same values) | Re-dispatch `meesell-api-routes-builder` with preamble "Previous run reshaped `precheck_jsonb` in the response — e.g., flattened nested keys or renamed fields. The §11.B.2 contract is VERBATIM passthrough. Return `row.precheck_jsonb` unchanged." |
| B5 | Celery task — sync wrapper + async internals | Open `tasks.py` — confirm: outer `def image_precheck_task(self, image_id, user_id)` is SYNCHRONOUS; inside, `asyncio.run(...)` wraps the async pipeline body. NOT `async def image_precheck_task` (Celery doesn't natively support coroutines in V1) | Re-dispatch `meesell-services-builder` with preamble "Previous run declared the Celery task as `async def` — Celery V1 does not support native coroutines. The wrapper must be sync; use `asyncio.run(...)` to invoke async internals. Per §11.E." |
| B6 | Import-linter rules respected | Run `pytest tests/lint/test_import_rules.py` — image module's repository is not imported by any other module; image's schemas not cross-imported; ai_ops not imported by anything outside image/category/catalog | Re-dispatch the offending specialist (typically services-builder if image/repository.py is leaked; api-routes-builder if schemas.py is leaked) with preamble "Previous run created an import that violates §16 (specific contract <N>). Fix the import per §16.C rule <K>." |

### AI lead (`meesell-ai-coordinator`) review checks

For `feature/image-precheck/ai` → `feature/image-precheck` PR:

| # | Check | Acceptance gate | Failure → re-dispatch |
|---|-------|-----------------|-----------------------|
| A1 | Watermark golden set accuracy ≥ 85% | `pytest tests/eval/watermark/test_accuracy.py` — assertion passes; reported accuracy ≥ 0.85 | Re-dispatch `meesell-prompt-engineer` with preamble: "Previous run scored <X>% on the 30-image golden set. Specifically, false positives on [list of fixture IDs with watermark style — e.g., #5 subtle bottom-corner logo, #12 small URL stamp] and false negatives on [list — e.g., #18 clean lifestyle, #22 white-BG]. Tighten the prompt for these patterns; consider adding a 'small text overlays count as watermarks' clause; re-run eval." |
| A2 | Per-call vision cost ≤ ₹0.05 | The `test_accuracy.py` output reports per-call avg cost; merge gate rejects > ₹0.05 | If cost > ₹0.05 AND ≤ ₹0.08: ESCALATE TO FOUNDER for a vision-specific ceiling exception (per Risk Register R3). If cost > ₹0.08: re-dispatch `meesell-prompt-engineer` with preamble "Previous run cost ₹<X> per call — token usage too high. Shorten the system prompt; reduce `max_output_tokens` to 64; re-run eval." |
| A3 | "skipped_budget" semantics tested | Run `pytest tests/integration/test_image_precheck_integration.py::test_watermark_budget_exhaustion` — the test mocks `call_gemini` to raise `BudgetExceededError`, asserts `precheck_jsonb.watermark_check == "skipped_budget"` AND status == "ready" | Re-dispatch `meesell-image-precheck-builder` with preamble "Previous run failed the budget-exhaustion test. The pipeline should set `watermark_check='skipped_budget'` on `BudgetExceededError` AND keep `status='ready'` if the 4 deterministic checks passed. Per §6A.F + §11.E step 6 graceful fallback." |
| A4 | 4 Pillow checks ≤ 2s per image | Smoke test `pytest tests/eval/precheck_smoke/test_pillow_checks.py` — assertion on per-image Pillow timing | Re-dispatch `meesell-image-precheck-builder` with preamble "Previous run had Pillow timing of <X>s per image — exceeds 2s budget. Verify Pillow opens the image ONCE per call (NOT 4 times — once per check). Use a single `Image.open(BytesIO)` then pass `img` to each check function." |
| A5 | Prompt registry entry present | `from app.ai_ops.prompt_registry import resolve; t = resolve("watermark.v1", "watermark")` — succeeds and returns the correct PromptTemplate | Re-dispatch `meesell-prompt-engineer` with preamble "Previous run did not register `watermark.v1` in `prompt_registry.py`. Add the entry: workload='watermark', prompt_id='watermark.v1', template=..., rendered_by='vision'." |

### Frontend lead (`meesell-frontend-coordinator`) review checks

For `feature/image-precheck/frontend` → `feature/image-precheck` PR:

| # | Check | Acceptance gate | Failure → re-dispatch |
|---|-------|-----------------|-----------------------|
| F1 | 4-slot grid (NOT 6) | Grep `frontend/src/app/features/images/image-uploader.component.{ts,html}` for `[1, 2, 3, 4]` literal OR `Array(4)` or `range(1,4)` — slot count is 4. NO `[1..6]`, NO `Array(6)` | Re-dispatch `meesell-angular-component-builder` with preamble "Previous run rendered 6 slots. The D1-locked decision is 4 slots. Update the template loop to `[1, 2, 3, 4]`." |
| F2 | PrimeNG import boundary | `grep -r "primeng" frontend/src/app/features/images/` — ZERO matches. All UI primitives via `@mee/ui` | Re-dispatch `meesell-angular-component-builder` with preamble "Previous run directly imported `primeng/*` in a feature file — violates Layer 4 rule. Replace with `mee-*` wrapper from `@mee/ui`." |
| F3 | Backoff polling shape | Read `frontend/src/app/core/services/image.service.ts` — `pollImages` uses RxJS `interval` + `takeWhile`; backoff progression is 1s → 2s → 4s; total ≤ 30s | Re-dispatch `meesell-angular-service-builder` with preamble "Previous run used `setInterval` directly or had wrong backoff progression. Use RxJS `interval` + `concatMap` per FRONTEND_ARCHITECTURE.md; backoff 1s → 2s → 4s; total cap 30s." |
| F4 | Feature flag guard | Read `frontend/src/app/app.routes.ts` — `/catalogs/:id/images` has BOTH `authGuard` AND `featureFlagGuard('FEATURE_IMAGE_PRECHECK_ENABLED')` applied. Build for staging env confirms `featureFlags.imagePrecheckEnabled = false` | Re-dispatch `meesell-angular-service-builder` with preamble "Previous run missed the featureFlagGuard. Apply both guards to the route." |
| F5 | Build under 90s | `pnpm build` completes in < 90 seconds | If 80-90s: warn in PR but allow. If > 90s: re-dispatch the most recent specialist with preamble "Previous run took <X>s. Investigate bundle size; remove unused imports." |
| F6 | Accessibility | Screenshots at 360px + 1280px attached; keyboard nav verified; color contrast ≥ 4.5:1; status colors paired with text labels | Re-dispatch `meesell-angular-component-builder` with preamble "Previous run failed <specific a11y check>. Fix per FRONTEND_ARCHITECTURE.md non-negotiable rules." |

### Infra lead (`meesell-infra-builder`, self-review) checks

For `feature/image-precheck/infra` → `feature/image-precheck` PR:

| # | Check | Acceptance gate | Failure → self-re-dispatch |
|---|-------|-----------------|-----------------------|
| I1 | Terraform plan shows zero destroys on shared resources | `terraform plan` for `dev` shows `Plan: X to add, Y to change, 0 to destroy` (or destroys ONLY on net-new staging resources you're creating from scratch) | Re-author Terraform with preamble (self-note): "Previous run staged a destroy on a shared resource. Review the plan diff and either ack the destroy in PR body with founder pre-approval, or refactor to avoid the destroy." |
| I2 | kubectl dry-run clean | `kubectl apply --dry-run=server -f k8s/dev/api-deployment.yaml` exits 0 with `configured (server dry run)` output | Fix the manifest syntax; re-run dry-run |
| I3 | GCS bucket exists in dev after smoke deploy | `gsutil ls gs://meesell-images-dev/` returns successfully (empty bucket is OK) | Investigate Terraform state — re-run `terraform apply` for dev; check IAM if 403 |
| I4 | IAM binding scoped (NOT bucket-level admin) | `gcloud projects get-iam-policy ...` shows the binding is on `meesell-images-dev/*` path (NOT bucket-wide `roles/storage.admin`) | Re-author IAM Terraform with stricter scope |
| I5 | Workload Identity Federation paths | `kubectl describe sa <backend-sa> -n dev` shows the WIF annotation; NO JSON key file referenced anywhere in the manifest | Fix the SA binding |
| I6 | Worker concurrency = 4 | `kubectl get deployment worker-dev -n dev -o yaml | grep concurrency` shows `--concurrency=4` in the command args | Fix the deployment spec |
| I7 | Runbook present + linked | `docs/runbooks/image-pipeline-troubleshooting.md` exists with the 5 required sections; `docs/runbooks/README.md` links it | Add missing sections / link |

### Re-dispatch template (generic)

When a check fails, the lead re-dispatches the specialist with this preamble prepended to the original template:

```
PROJECT BOUNDARY: <as before>
SESSION: mesell-image-precheck-{group}-session-{N+1}  ← incremented from prior session
Lead: <lead role>

## Iteration {2 or 3}

Previous run (session-{N}) failed acceptance check <X>: <one-line summary>.

Specifically: <details — file + line + observed value vs expected — be precise>.

Re-read <specific section of FEATURE_PLAN.md or BACKEND_ARCHITECTURE.md> before retrying.

The rest of this dispatch is identical to the original Template <A-H>:

<original template body>
```

### Maximum iteration count

**3 iterations per specialist** before founder escalation. After iteration 3 fails the same check:

1. Lead writes a memo to `.claude/agent-memory/meesell-<lead-role>/handoff_escalation_image_precheck_<specialist>.md` documenting:
   - The check that keeps failing
   - The 3 attempts the specialist made
   - Lead's hypothesis for why it's failing
   - Lead's recommended escalation path (founder decision required, architecture amendment, scope reduction, model upgrade)
2. Lead adds a `BLOCKED` row to `feature_board_<domain>.md` with the escalation memo path
3. Lead surfaces to founder via `STATUS_MASTER.md` blockers section
4. **NO further specialist dispatch on this slice until founder rules**

---

## Acceptance gate

The feature is "done" (ready for `feature/image-precheck` → `develop` PR by founder review) when **ALL** of the following are true:

- [ ] All 4 group PRs (`backend`, `ai`, `frontend`, `infra`) merged to `feature/image-precheck`
- [ ] **Backend group**: 5 CI gates green (unit, smoke, lint, integration, golden_roundtrip not applicable here); 5 unit + 3 integration tests pass per §11.K; OpenAPI exported with 2 new endpoints; import-linter passes
- [ ] **AI group**: watermark golden set accuracy ≥ 85% on the last run within the previous 24h; per-call vision cost ≤ ₹0.05 (or founder-approved exception per Risk Register R3); precheck_smoke 20/20 pass; `nightly ai_eval` job green in CI
- [ ] **Frontend group**: `pnpm build` < 90 seconds; bundle delta reasonable (~< 30KB total per route chunk); 360px + 1280px screenshots attached; accessibility checks pass; PrimeNG boundary verified via grep
- [ ] **Infra group**: Terraform plan applied; GCS bucket live in dev; IAM bindings scoped per least-privilege; worker pod running; runbook published
- [ ] **`V1_FEATURE_SPEC.md §F5` amended inline** with the D1 decision (4 slots, 40 MB cap) as an AMENDMENT block
- [ ] **`.claude/agents/meesell-image-precheck-builder.md` line 84 corrected** to match D1
- [ ] **All 4 leads have updated their `feature_board_<domain>.md`** rows to `MERGED` and moved to "Recently merged"
- [ ] **All 8 specialists have written `feature_image_precheck_session_*_handoff.md`** to their respective memory directories AND updated their `MEMORY.md` "Features in flight" section per the §Memory protocol
- [ ] **No specialist exceeded 3 iteration cycles** without founder escalation
- [ ] **No `feature/image-precheck/{group}` branch open > 5 calendar days** without lead escalation
- [ ] **Staging flag `FEATURE_IMAGE_PRECHECK_ENABLED` remains `false`** at this stage — the 3-gate staging promotion happens via a SEPARATE `feature/feature-flag/staging-image-precheck-on` micro-branch after this feature lands on develop (per D2)

After all gates pass, `meesell-backend-coordinator` (largest contributor — backend has the most files in this feature) opens the `feature/image-precheck` → `develop` PR for founder review.

---

## Risk register

Top 5 risks specific to this feature.

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | **Gemini Vision JSON-mode regression breaks the watermark parser.** Gemini API changes the JSON output shape silently (extra field, renamed field, wrapped in `{response: {...}}`) — the `WatermarkResponse` Pydantic parser rejects, Layer 2 retries, eventually returns safe fallback. Accuracy drops to 0% on the golden set; the watermark step becomes effectively dead. | Medium | P0 | Layer 2 guardrail re-validation per §6A.E catches parser failures. Eval runner asserts shape match — a regression surfaces immediately. Mitigation: prompt-engineer pins the model version in `models/gemini-2.5-flash`, treats the prompt registry as the rollback point (revert to a prior version if v1 degrades). Operational: ai lead checks LangFuse traces weekly for parser failure rate; >5% triggers an investigation. |
| R2 | **GCS upload latency blows the 8s/image budget under congested networks.** Slow user uplink + GCS regional latency push the multipart upload past 8s; Celery task starts before bytes are fully written; pipeline fails or watermark step times out. | Medium | P1 | Bytes are validated + Pillow-read BEFORE GCS upload (§11.B.1 step 3) — the 8s budget is for the WORKER pipeline, not the user-facing upload. The route returns 202 immediately after GCS write succeeds; the user experience does NOT block on the 8s budget. Mitigation: services-builder confirms `adapters.gcs.upload_bytes` uses chunked upload (>5MB threshold) and the `httpx.AsyncClient` has a 30s timeout (allows slow networks). Operational: infra-builder watches Prometheus `gcs_upload_duration_seconds` p95 — alert if > 15s. |
| R3 | **Watermark per-call vision cost exceeds the locked ≤₹0.05 ceiling.** Vision calls are multimodal; observed cost in practice may be ₹0.06-0.08. The ai-coordinator merge gate rejects PRs with cost > ₹0.05. | High | P1 | Prompt-engineer measures per-call cost on a 5-image sample run before opening PR. If observed > ₹0.05: prompt-engineer escalates to founder for a vision-specific ceiling (e.g., "text ≤ ₹0.05, vision ≤ ₹0.08") via a `meesell-ai-coordinator.md` Stop Conditions amendment. **Founder pre-decision recommended** before prompt-engineer dispatch to avoid mid-iteration escalation. Mitigation: shorten the system prompt; use `max_output_tokens=64` since the response is just `{has_watermark: bool, confidence: float}`. |
| R4 | **White-BG heuristic false-positive on light-but-not-white backgrounds.** 4-corner × 16px patches with mean ≥ 240 threshold rejects images with very light gray, cream, or off-white backgrounds that Meesho would accept. Sellers' legitimate products fail; conversion friction. | High | P1 | The threshold (240) and patch count (4) and patch size (16x16) are V1 algorithm choices documented in the module header. V1.5 iteration: image-precheck-builder gathers founder-reported false-positives, tunes threshold to 235 or moves to a histogram-based heuristic. Mitigation: the white-BG check is one of 4 deterministic checks; failing it does NOT block re-upload — the user sees a clear "Use plain white background" fix hint and can re-shoot. Acceptable V1 friction trade-off given the founder's pull-only-good-images-on-Meesho philosophy. |
| R5 | **Celery worker pod OOM on large image batches.** A user uploads 4 × 10 MB images simultaneously; worker concurrency=4 + Pillow `Image.open` holds 4 × 40 MB of decoded bitmaps in memory + Gemini SDK overhead → potentially > 1 GB RSS. Worker pod K8s memory limit (default ~1Gi) triggers OOM kill. | Low | P1 | Worker concurrency = 4 is matched to the 8s/image budget (concurrent capacity), not to a memory budget. Mitigation: infra-builder sets worker pod memory limit to **2 Gi** (currently ungrounded — confirm in K8s manifests). Pillow `img.close()` called explicitly after each precheck. If OOMs are observed in dev, reduce concurrency to 2 and accept the throughput hit. Operational: infra-builder watches `pod_memory_working_set_bytes` p95 — alert if > 1.5 Gi. |
| R6 (watch) | **30-image golden set staleness as seller image styles evolve.** Watermark detection performance is bound to the fixture. As real-world watermarks evolve (TikTok-style large translucent overlays, AI-generated watermarks), the V1 golden set undertests against the production distribution. | Medium | P2 | Quarterly re-baseline of the golden set by prompt-engineer (add 10 fresh watermark examples; retire 5 outdated ones). Tied to the data scraper refresh cadence per `meesell-scraper-maintainer`'s quarterly window. V1.5: add a "report incorrect classification" hook in the frontend; collect founder-flagged misclassifications as new fixture candidates. |

---

## Revision history

| Version | Date | Author | Change |
|---------|------|--------|--------|
| v1 | 2026-06-10 | mesell-image-precheck-planning-session-1 | Initial draft. D1/D2/D3 locked. 8 dispatch templates. Review protocol with 3-iteration max. 5 risks + 1 watch item. Branch creation playbook + memory namespace convention added. Awaiting founder review. |
| v2 | 2026-06-10 | mesell-image-precheck-amendment-session-1 | Canonical pattern v2 conformance — reordered Code surfaces + Documentation deliverables before Branch setup + Memory protocol per `_CANONICAL_PATTERN.md` locked order; renamed `## Memory namespace convention` → `## Memory protocol`; demoted ad-hoc `## Features in flight` h2 to `### Features in flight` h3 inside Memory protocol; added `### Memories the coding-session leads MUST read at session start` and `### Cross-feature memos` subsections per canonical §6 spec; renamed Risk register column `Severity` → `Impact` and reordered columns to canonical `Likelihood | Impact`; added `### Session-close memory entries` with the 5-field canonical handoff format. Pre-amendment audit found 11 of 11 canonical sections present (no missing universal-gap sections), 4 mis-ordered, 1 ad-hoc heading at wrong depth. |

---

*End of FEATURE_PLAN.md*
*Next step on founder approval: this PR merges to `develop`. Then catalog-form merges. Then leads create the 4 coding branches per `## Branch setup` and dispatch their Phase A specialists in parallel.*
