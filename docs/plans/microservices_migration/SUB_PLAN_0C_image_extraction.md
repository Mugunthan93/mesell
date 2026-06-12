# SUB-PLAN C — `image` Service Extraction

**STATUS: DRAFT — PHASE 1 (spec authoring) complete; PHASE 2 (execution) GATED.**
Authored under session `mesell-ms-image-session-1` (2026-06-12, MS-C Phase 1)
by `meesell-backend-coordinator` (HYBRID rule STEP 1 — SPEC + sub-plan only,
NO service code, NO specialist dispatch, NO extraction execution). This is the
**image** extraction sub-plan of the Microservices Migration MASTER_PLAN
(v1.3), implementing MASTER_PLAN §4 row **C** (`image`, complexity **M**) and
parallel-program wave **MS-2** (B dashboard ‖ C image).

> ## ⚠️ EXECUTION GATE — PHASE 2 IS BLOCKED
>
> Per `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md`
> (wave table) execution of THIS sub-plan opens **only when BOTH**:
> 1. **MS-A's (`export`) founder-gate PR `feature/microservices-export/integration` → `develop` is MERGED.** As of authoring, the three MS-A branches (`.../integration`, `.../backend`, `.../infra`) all sit at `c859955` (= origin/develop tip) — the founder-gate PR is OPEN/in-flight, **NOT merged**. `export` is NOT yet extracted.
> 2. **The MS-A extraction RECIPE exists** (the validated SP-01-pilot pattern recorded in the backend lead's memory) — to be consumed and reconciled before any MS-C dispatch.
>
> **Until both conditions hold, NO branch is cut, NO specialist is dispatched, NO code is written for MS-C.** This document and its companion task spec (`.claude/agent-memory/meesell-backend-coordinator/spec_msC_backend.md`) freeze the plan now (docs-only, fully parallel per MS-PAR-1) so Phase 2 is a fast execution once the gate opens.
>
> **Reconcile-before-dispatch rule.** When MS-A's final HTTP-shim contract doc lands, re-verify the export→image `list_images` shape (§3.E below) against it. If MS-A's contract doc drifts from spec_msA §0.4 row 6, **STOP and escalate to the master session — never improvise a contract** (per common-rules #5 + the `get_image_bytes` cautionary tale, §0.9).

> Authoritative inputs read for this sub-plan (all at `origin/develop` = `c859955`):
> - `docs/plans/microservices_migration/MASTER_PLAN.md` (v1.3 — §1.A/§1.C, §2.B/§2.C/§2.D/§2.E, §3.A/§3.A.1/§3.B/§3.C, §4 row C, §5.A–§5.G, §6 Risks)
> - `docs/plans/microservices_migration/SUB_PLAN_01_export_extraction.md` (the canonical 11-section shape template + A1/A2 LOCKED posture)
> - `.claude/agent-memory/meesell-backend-coordinator/spec_msA_backend.md` (§0.4 frozen cross-module call-site table — **row 6 freezes the export→image `list_images` shim**; §0.1 branch divergence)
> - `.claude/agent-memory/meesell-backend-coordinator/handoff_msA_infra.md` (infra-handoff pattern)
> - `docs/sub_session_prompts/microservices_execution/00-ms-parallel-program-dispatch.md` (common rules 1–9, wave structure)
> - `docs/BACKEND_ARCHITECTURE.md` §6.D (GCS), §6A (ai_ops), §11 (image module contract), §16/§16.G (call-site preservation), §18 (Celery), §21 (extraction roadmap)
> - As-built source @ `origin/develop` `c859955`: `backend/app/modules/image/` (8 files), `backend/app/adapters/gcs.py`, `backend/app/workers/celery_app.py`, `backend/app/main.py`, `backend/app/ai_ops/` (7 files + 3 prompts), `backend/app/core/middleware/` (6 files)

---

## 0. GROUND TRUTH — re-verified against SOURCE 2026-06-12 (Wave-6 law: every contract cited file:line from source, never plan prose)

### 0.1 Branch / tree state — cut point
- **origin/develop tip = `c859955`** (`docs(infra): final dev redeploy ... (#179)`). Confirmed via `git rev-parse origin/develop`.
- **Local `develop` HEAD = `6d6ee51`** is DIVERGED local-only (`docs(dispatch): MS parallel program ...`) — NOT an ancestor of `c859955`; the local working-tree MASTER_PLAN.md is pre-rekey. **Cut all MS-C branches from `origin/develop` (`c859955`)**, never local develop (carries forward the spec_msA §0.1 divergence rule).
- This Phase-1 spec was authored in a worktree cut from `origin/develop`: `git worktree add /tmp/mesell-wt/msC-spec -b docs/msC-subplan-image origin/develop`.

### 0.2 image module = 8 files — CONFIRMED
`backend/app/modules/image/`: `__init__.py`, `domain.py`, `exceptions.py`, `repository.py`, `router.py`, `schemas.py`, `service.py`, `tasks.py` = 8 files (canonical 7-file layout + `tasks.py`; image is one of only 2 modules with `tasks.py` — the other is `export` — per §3.C / `__init__.py` docstring).

### 0.3 image IS AI-consuming (A1/D6 applies — UNLIKE export)
Unlike export (deterministic, no ai_ops), image **calls Gemini** at `tasks.py:206`:
```
response = await ai_client.call_gemini(ctx, prompt_id="watermark.v1", prompt_vars={}, image_bytes=image_bytes)
```
with `ctx = ai_client.AICallContext(workload="watermark", user_id=user_id)` (`tasks.py:200`), imported lazily at `tasks.py:198` (`from app.ai_ops import budget_cap, client as ai_client`). `BudgetExceededError` graceful fallback at `tasks.py:212-214` → `"skipped_budget"`, non-blocking. **Per founder ruling A1/D6 (MASTER_PLAN §2.E RESOLVED banner + §5.D): `ai_ops/` is VENDORED into svc-image (no `ai-ops-svc` until V2); the ₹500 daily budget brake stays SHARED via Valkey DB 0.** See §4 (ai_ops vendoring surface) below.

### 0.4 rembg — DECLARED dependency, ZERO live call sites (decision §3.G below)
- `grep -rni rembg backend/app` = **EMPTY** (zero references in any `.py`). 
- `rembg==2.0.59` IS present at `backend/requirements.txt:14` (alongside `pillow==10.4.0:15` + `onnxruntime==1.19.0:16` — rembg's ONNX backend).
- **The live precheck pipeline is Pillow steps 1–4 + ai_ops Gemini watermark step 5** (`tasks.py:82-247`): `_check_jpeg` (Pillow open), `_check_color_space` (Pillow mode), `_check_resolution` (Pillow size), `_check_white_background` (Pillow corner-sample), `_check_watermark` (ai_ops Gemini). NO background-removal step runs in V1.
- **There is NO rembg call site to move.** The "rembg surface" the dispatch prompt references is a *declared/planned* background-removal dependency, NOT a live call. Decision §3.G below resolves whether svc-image carries rembg in `requirements.txt` (and pays its image-size/model-download cost) or defers it. **Do NOT invent a rembg call site.**

### 0.5 Mounted routes — VERIFIED in main.py (row-26 lesson: count mounted APIRoute objects, not schema classes)
- `backend/app/main.py:46` `from app.modules.image import image_router`
- `backend/app/main.py:126` `app.include_router(image_router)` (preceded by the `:125` `§11 image` comment)
- The router (`image/router.py:68`) is `APIRouter(prefix="/api/v1", tags=["image"])`. **Exactly 2 mounted routes** (verified from `router.py` source decorators):

| # | Route | Method/Status | Decorators (router.py) | Deps |
|---|---|---|---|---|
| 1 | `POST /api/v1/products/{id}/images` | 202 ACCEPTED, `response_model=ImageUploadResponse` | `@rate_limit(scope="image_upload", limit=10, window=60)` (`:85`) + `@audit_event("image.upload.received")` (`:86`) | `Depends(get_current_user)` (`:89`) + `Depends(get_db)` (`:90`); multipart `file: UploadFile` + `idx: int = Form` |
| 2 | `GET /api/v1/products/{id}/images` | 200 OK, `response_model=ImagesListResponse` | `@rate_limit(scope="image_list", limit=600, window=3600)` (`:131`) — per-IP polling, NO audit | `Depends(get_current_user)` (`:134`) + `Depends(get_db)` (`:135`) |

NOTE the path param is `{id}` (not `{product_id}`). Route 1 fail-fast `idx not in (1,2,3,4)` guard at `router.py:110` raises `InvalidImageIdxError`.

### 0.6 Cross-module call sites OUT of the image module — RE-CITED FROM SOURCE
Every outbound `<callee>_service.<method>` / cross-module import in `backend/app/modules/image/`:

| # | Call site | Callee (signature cited from callee source) | Returns | Shim plan |
|---|---|---|---|---|
| 1 | `service.py:53` import `from app.modules.catalog import service as catalog_service` | — | — | becomes `core/extracted_clients/catalog_client.py` re-export |
| 2 | `service.py:162` `catalog_service.assert_product_ownership(product_id, user_id, db=db)` (upload_image step 1) | `catalog/service.py` `assert_product_ownership(product_id: UUID, user_id: UUID, db: AsyncSession) -> None` (raises ProductNotFoundError) | None | catalog `/internal/products/{id}/ownership-check` shim — **catalog still in-process (MS-5 LAST)** → shim base URL = monolith ClusterIP |
| 3 | `service.py:248` `catalog_service.assert_product_ownership(product_id, user_id, db=db)` (list_images step 1) | same as #2 | None | same shim as #2 |
| 4 | `tasks.py:198` import `from app.ai_ops import budget_cap, client as ai_client` | — | — | VENDORED in-process per A1/D6 (NOT an HTTP shim) — see §4 |
| 5 | `tasks.py:206` `ai_client.call_gemini(ctx, prompt_id="watermark.v1", prompt_vars={}, image_bytes=image_bytes)` | `ai_ops/client.py` `call_gemini(ctx, prompt_id, prompt_vars, *, image_bytes=...) -> AIResponse` | `AIResponse` (`.parsed` dict) | VENDORED ai_ops (in-process), shared budget brake Valkey DB 0 |

**image's ONLY outbound HTTP shim is to `catalog` (`assert_product_ownership`, 2 call sites, same method).** ai_ops is vendored (in-process), not a shim. The §16.G contract is ABSOLUTE: call sites at `service.py:162` + `:248` stay byte-for-byte; only the import at `service.py:53` changes from `from app.modules.catalog import service as catalog_service` to `from app.core.extracted_clients import catalog_client as catalog_service` (re-exporting the same symbol name).

### 0.7 image as a CALLEE — the 3 inbound surfaces (from §1.C matrix + service.py public methods)
image's `service.py` exposes 6 public methods (`service.py:426` `__all__`); 4 are cross-module surfaces (§11.C). Their callers:

| Inbound surface | image method (signature from source) | Caller | Shim status at MS-C time |
|---|---|---|---|
| **export → image** (FROZEN by MS-A §0.4 row 6) | `list_images(user_id, product_id, *, db) -> ImagesListResponse` (`service.py:232`) | export-svc (already extracted at MS-1) | **svc-image MUST expose `/internal/products/{id}/images` shim** — this is the MS-A frozen contract |
| catalog → image | `get_image_urls(product_id, user_id, *, db) -> list[ImageUrl]` (`service.py:280`) | catalog (in-process, MS-5 LAST) | catalog still calls image in-process during MS-C; the shim is added when catalog extracts (MS-5). NOT an MS-C deliverable. |
| dashboard → image (OPTIONAL) | `summary(user_id, product_ids, *, db) -> dict[UUID, ImageStatusSummary]` (`service.py:386`) | dashboard (MS-2 ‖ partner) — §1.C keeps dashboard at the locked matrix; dashboard does NOT opt into image.summary in V1 per §13.D | NOT wired in V1 — OPTIONAL surface only; no MS-C shim |
| (worker self-call) | `write_precheck_result(...)` (`service.py:346`) | `tasks.py:308`/`:350` (same service, worker context) | intra-service — no shim |

**`get_image_bytes` (`service.py:319`) is NOT called by export.** It exists but the export pipeline consumes `list_images` (signed-URL refs), NOT raw bytes — confirmed at `export/service.py:185` (`image_service.list_images(user_id=..., product_id=..., db=db)`; import `export/service.py:83`). This is the spec_msA §0.4 correction (the MASTER_PLAN §1.C "get_image_bytes" cell is STALE; the frozen contract is `list_images`). **The MS-C `/internal/*` shim implements `list_images`, NOT `get_image_bytes`.**

### 0.8 GCS call sites — every `adapters/gcs` usage in the image module (these move with svc-image)

| Call site | Method | Purpose |
|---|---|---|
| `service.py:52` import `from app.adapters import gcs as gcs_adapter` | — | adapter import |
| `service.py:195` `gcs_adapter.upload_bytes(path=gcs_path, data=file_bytes, content_type="image/jpeg")` | upload_bytes (`gcs.py:95`) | upload_image step 6 |
| `service.py:254` `gcs_adapter.generate_signed_url(path=..., ttl_seconds=settings.GCS_SIGNED_URL_TTL_SECONDS, method="GET")` | generate_signed_url (`gcs.py:161`) | list_images signed URL (1h TTL) |
| `service.py:300` `gcs_adapter.generate_signed_url(...)` | generate_signed_url | get_image_urls (catalog preview) |
| `service.py:340` `gcs_adapter.download_bytes(path=image.gcs_path)` | download_bytes (`gcs.py:139`) | get_image_bytes (export ZIP, V1.5 path) |
| `service.py:410` `gcs_adapter.generate_signed_url(...)` | generate_signed_url | summary (dashboard front-image) |
| `tasks.py:268` import `from app.adapters import gcs as gcs_adapter` | — | worker adapter import |
| `tasks.py:285` `gcs_adapter.download_bytes(path=image_row.gcs_path)` | download_bytes | precheck pipeline step 1 (fetch bytes) |

GCS path convention (`service.py:96` `_gcs_path_for`): `meesell-images/{user_id}/{product_id}/{idx}.jpg` per §6.D + `MVP_ARCH §10.8` (tenancy seam). Adapter credentials = GCP ADC from pod SA (`gcs.py:13-17`). svc-image needs `storage.objectAdmin` on the `meesell-images/` prefix.

### 0.9 Celery worker — as-built (the worker split surface; dispatch prompt's "workers/image_tasks" is STALE)
- The image Celery task lives **IN THE MODULE** at `backend/app/modules/image/tasks.py` — `@shared_task(name="image.precheck", bind=True, max_retries=2, retry_backoff=True)` (`tasks.py:415-421`), entrypoint `image_precheck_task(self, image_id, user_id)` (`tasks.py:421`), runs `asyncio.run(_run_precheck_pipeline(...))` (`tasks.py:445`).
- `backend/app/workers/` contains ONLY `celery_app.py` (+ `__init__.py`) — there is NO `workers/image_tasks.py` (dispatch-prompt phrase is stale). Ground the worker-split in `modules/image/tasks.py` + `workers/celery_app.py`.
- **`celery_app.py` as-built (queue/routing):**
  - `celery_app = Celery("meesell", broker=BROKER_URL, backend=RESULT_BACKEND_URL, include=["app.modules.image.tasks", "app.modules.export.tasks"])` (`celery_app.py:98-106`). Broker = Valkey **DB 1** (`:91`), results = **DB 2** (`:92`).
  - **There is NO `task_routes` / per-task `queue=` config** (`grep task_route|queue celery_app.py` = none) — both `image.precheck` and `export.xlsx` go to the **default queue**. The svc-image worker gets its **own dedicated queue** (`svc-image`) on extraction.
  - `task_prerun` signal handler `_revalidate_user_pre_task` (`celery_app.py:203`) enforces §18.F worker JWT re-validation for `{"image.precheck", "export.xlsx"}` (`:125-128`) — svc-image's vendored celery_app keeps this for `image.precheck` ONLY.
  - Locked worker invariants (move verbatim): `task_serializer/result_serializer/accept_content="json"` (`:109-111`), `task_acks_late=True` (`:115`), `task_reject_on_worker_lost=True` (`:117` SESSION-2 G3 LOCK), `worker_prefetch_multiplier=1` (`:118`), `timezone="Asia/Kolkata"`+`enable_utc=True` (`:112-113`), `task_track_started=True` (`:114`).
  - **MS-A precedent:** SUB_PLAN_01 §"Code surfaces" assigns svc-export its own single-task Celery app with queue `svc-export`, keys prefixed `svc-export:` (§2.E). svc-image mirrors this: single-task app (`include=["app.tasks"]`), queue `svc-image`, broker DB 1 / results DB 2, keys prefixed `svc-image:`.
  - **IN-FLIGHT NUANCE — monolith `image.precheck` queue routing (founder PR #143, OPEN, NOT yet on origin/develop c859955).** The backend-chores PR #143 (board row, OPEN→develop) adds `task_routes={"image.precheck": {"queue": "image-tasks"}}` to the MONOLITH `workers/celery_app.py` (verified: that queue name is `image-tasks`, NOT `svc-image`; `export.xlsx` stays default-queue). When #143 merges to develop, the monolith image task routes to `image-tasks`. **This does NOT change the svc-image extraction target** — the extracted service gets its OWN dedicated queue `svc-image` regardless. But at Phase 2, RE-READ `workers/celery_app.py` from the then-current develop: if #143 has merged, the strangler-window monolith routes `image.precheck`→`image-tasks`, and the cutover removal (§3 monolith-side) must drop that route entry too. Cite the THEN-live state, not this snapshot.

### 0.10 DB tables owned — `product_images` (cite shared/models)
- image owns **1 table: `product_images`** (MASTER_PLAN §1.A row image; §2.D maps it to schema `image`). ORM at `backend/app/shared/models/product_image.py` (referenced `repository.py:53` `from app.shared.models.product_image import ProductImage as ProductImageORM`).
- Repository joins through `products` (`repository.py:52` `from app.shared.models.product import Product as ProductORM`) because `product_images` has NO direct `user_id` column (§11-IMAGE-D1 deviation, `repository.py:17-39`) — tenancy via `scope_to_user(select(ProductORM.id), user_id)` (`repository.py:93`, `:164`, `:206`, `:264`, `:297`, `:339`).
- **CROSS-SCHEMA READ HAZARD (Risk #5-class — escalate at Phase 2 if unresolved):** the tenancy join reads `products` (catalog-owned, schema `catalog` after MS-5). At MS-C time catalog is STILL in `public`/in-process, so the join works in-process. But svc-image is being extracted to schema `image` while it must read `products`. **This is the one structural wrinkle vs export** (export owns its read path). Resolution options (decide at Phase 2 against the MS-A recipe): (a) keep the `product_images`↔`products` join in-process until catalog extracts (image-svc reads both `image.product_images` and `public.products` via a read grant during the strangler window), OR (b) replace the join-based tenancy with the `assert_product_ownership` HTTP shim result (the shim already proves ownership; the repository can then scope by `product_id` alone). **Option (b) aligns with §2.D "no cross-schema reads — a service that needs another service's data goes through HTTP, never SQL"** and is the recommended target; flag to infra for the transitional grant either way. ESCALATE to master session if the MS-A recipe doesn't cover this join pattern.

### 0.11 Test count — re-counted at authoring (validation floor)
- `grep -rn "def test_" backend/tests/` = **649** test functions (matches MS-A §0.9 baseline — no new tests landed between MS-A authoring and now).
- image's own tests = **29** `def test_` across `backend/tests/modules/image/` (`test_service_unit.py`, `test_integration.py`, `conftest.py`) + the `list_images`-related assertion in `backend/tests/modules/export/test_front_image_check.py:140-142` (asserts `list_images` NOT called for `xlsx_only` — a cross-module contract test that svc-image's `/internal` shim must keep satisfiable).
- **VALIDATION FLOOR RULE (merge gate):** the full-suite `def test_` count must be **MONOTONIC (≥ 649 live baseline)** — the extraction ADDS svc-image tests, removes none until the strangler 7-day window closes. **Do NOT assert the stale "823"** (the dispatch-prompt figure is a collected-items/parametrize count, not `def test_`); quote the LIVE `def test_` count at PR time and assert monotonic-vs-baseline-649.

---

## 1. Decisions

This sub-plan inherits the LOCKED A1/A2 rulings (D6/D7) from MS-A and adds two image-specific decisions (§3.G rembg, §0.10 cross-schema join).

### C1 — `ai_ops/` placement — VENDORED into svc-image (LOCKED via founder ruling D6/A1, 2026-06-10)
image is AI-consuming (§0.3). Per D6/A1 (MASTER_PLAN §2.E RESOLVED banner): `ai_ops/` is a **vendored Python-package copy inside svc-image's image** (no `ai-ops-svc` until V2). The watermark call (`tasks.py:206`) runs in-process inside the Celery worker. The ₹500 daily budget brake stays SHARED via Valkey DB 0 (the two counters `ai:cost:daily:{date}` + `ai:cost:pending:{date}` + reservation keys `ai:budget:reservation:{id}` per `budget_cap.py:28-37`) — svc-image reads/writes the SAME DB-0 keyspace as any other AI-consuming service, so the global cap stays coordinated. **No new ruling needed; this is the LOCKED posture applied to its FIRST extraction** (image is the first AI-consuming service to extract; category/catalog follow at MS-4/MS-5).

### C2 — Middleware vendoring — 6-mw chain vendored, LOCAL JWT (LOCKED via D7/A2, 2026-06-10)
Per D7/A2 (MASTER_PLAN §5.A): svc-image vendors the 6-middleware chain (`CORS → request_id → auth_mw → tenancy_mw → rate_limit_mw → plan_guard_mw → audit_mw`) from `backend/app/core/middleware/` (6 files confirmed: `request_id.py`, `auth_mw.py`, `tenancy_mw.py`, `rate_limit_mw.py`, `plan_guard_mw.py`, `audit_mw.py`). JWT verified LOCALLY via vendored `core/auth.py` + shared `JWT_SECRET`. **image uses 5 of 6 actively** (see §3.F): `plan_guard_mw` RUNS but is NO-OP for image (image participates in no plan_guard resource per §11.J — the 4-slot rule is a structural DB CHECK constraint, not plan_guard). `rate_limit_mw` IS used (both routes carry `@rate_limit`). `audit_mw` IS used (`image.upload.received` on POST; the `image.precheck.completed` worker audit is a direct ORM write, §15.E exception).

### C3 — Extraction order — image is MS-2 (wave), §3.B position 3 (CONFIRMATION)
MASTER_PLAN §3.B locks image at position 3 ("Worker pod already a separate process per §11.L; cross-module call to catalog becomes the FIRST live HTTP shim — proves §16.G in practice"). The parallel program (MS-PAR-1) runs image in **wave MS-2 alongside dashboard** (B ‖ C). Confirmation, not a new ruling.

---

## 2. Agent lineup

| Lead | Specialists dispatched (PHASE 2 only — GATED) | What each builds |
|---|---|---|
| `meesell-backend-coordinator` (orchestrator) | — | Authored this sub-plan + `spec_msC_backend.md` + `handoff_msC_infra.md`; owns the merge gate for `feature/microservices-image/backend` → `.../integration`; reviews extracted code against §16.G; consumes + reconciles the MS-A recipe before dispatch; updates `feature_board_backend.md`. |
| → `meesell-services-builder` (opus) | service.py + tasks.py + repository.py + domain.py + exceptions.py extraction; the `catalog_client` HTTP shim (`assert_product_ownership`); ai_ops VENDORING (per C1); standalone `main.py` (6-mw, plan_guard NO-OP); single-task Celery app (queue `svc-image`); trimmed Settings; the `/internal/products/{id}/images` callee shim BODY (service method behind it). |
| → `meesell-api-routes-builder` (sonnet) | router.py (2 public routes) + schemas.py; **+ the `/internal/products/{id}/images` route** (the MS-A frozen `list_images` callee shim — image is a CALLEE of export, UNLIKE export which had none); regenerate standalone OpenAPI. |
| → `meesell-database-builder` (sonnet) | Alembic schema-split moving `product_images` from `public` to schema `image`; `version_table_schema="image"`; Risk#5 integrity pre-scan; the §0.10 cross-schema-`products`-read transitional grant decision (coordinate with infra). |
| `meesell-image-precheck-builder` (AI track — collaboration, NOT a backend specialist) | — | Verifies the 5-step precheck pipeline STILL OPERATES in the extracted worker (the pipeline internals `tasks.py:82-247` are AI-track-owned; the backend extraction must not alter pipeline behavior). Consulted at merge-gate review, not dispatched as a backend builder. |
| `meesell-infra-builder` (standalone, via cross-lead memo `handoff_msC_infra.md`) | — | svc-image Dockerfile (rembg/Pillow image-size per §3.G), K8s api + dedicated Celery-worker deployments, Traefik route, Postgres `image` schema/role + transitional `products` read grant, GCS SA, Valkey budget-brake DB-0 access, queue wiring. **D3 VM-fit flag (§7) — image+rembg is the heaviest container.** |

### Dispatch order (critical path — PHASE 2)
```
PHASE A (parallel — no inter-dependency):
  meesell-database-builder  → Alembic schema-split (product_images public→image); §0.10 cross-schema-products-read decision
  [INFRA LANE — meesell-infra-builder per handoff_msC_infra.md]

PHASE B (depends on A — service code targets the new schema):
  meesell-services-builder  → service/tasks/repository/domain/exceptions; catalog_client shim; ai_ops vendoring; main.py; single-task Celery app (queue svc-image)
  meesell-api-routes-builder→ router.py (2 public) + schemas.py + /internal/products/{id}/images shim route (parallel once service signatures frozen)

PHASE C (depends on B — integration; LEAD-owned, not specialist):
  meesell-backend-coordinator → hybrid-mode CI wiring; test_image_extraction.py; merge-gate review; board MERGED flip
```
Iteration cap **3** per specialist (MS-A §"Review + iteration protocol").

---

## 3. Code surfaces

The `backend/services/svc-image/` tree is the new home; the old `backend/app/modules/image/` tree is DELETED only after hybrid-mode CI passes ≥7 days (MASTER_PLAN §3.C) — until then both coexist (strangler fig).

### Backend — new service tree (`backend/services/svc-image/`)

| File | Tag | Description | Owner |
|---|---|---|---|
| `app/main.py` | NEW | Standalone FastAPI; mounts the 2 public image routes + the `/internal/products/{id}/images` route; registers the 6-mw chain (plan_guard NO-OP) + `core/errors` handlers; `/health` + `/metrics`. | services-builder |
| `app/router.py` | NEW (from `modules/image/router.py`) | 2 public routes verbatim: `POST /api/v1/products/{id}/images` 202 (preserve `@rate_limit(scope="image_upload",limit=10,window=60)` + `@audit_event("image.upload.received")` + the `idx not in (1,2,3,4)` fast-fail at line 110); `GET /api/v1/products/{id}/images` 200 (preserve `@rate_limit(scope="image_list",limit=600,window=3600)`, no audit). | api-routes-builder |
| `app/internal_router.py` (or `/internal/*` in `router.py`) | NEW | `GET /internal/products/{id}/images` → calls `service.list_images(user_id, product_id, db=db)` → returns `ImagesListResponse`. Forwards caller JWT for ownership re-validation. **THE MS-A FROZEN CALLEE SHIM (§3.E).** NOT Traefik-exposed (cluster-DNS only). | api-routes-builder |
| `app/service.py` | NEW (from `modules/image/service.py`) | 6 public methods byte-for-byte (`upload_image`, `list_images`, `get_image_urls`, `get_image_bytes`, `write_precheck_result`, `summary`). ONLY the catalog import (`service.py:53`) changes → `from app.core.extracted_clients import catalog_client as catalog_service` (§16.G: call sites `:162`/`:248` UNCHANGED). | services-builder |
| `app/tasks.py` | NEW (from `modules/image/tasks.py`) | `image_precheck_task` (`name="image.precheck"`), `asyncio.run` internals, 5-step pipeline (4 Pillow + 1 ai_ops watermark), direct-ORM `image.precheck.completed` audit (`_emit_precheck_completed_audit`). ai_ops imports (`tasks.py:198`) resolve to the VENDORED `app.ai_ops` (C1). | services-builder |
| `app/repository.py` | NEW (from `modules/image/repository.py`) | 7 module-private methods bound to schema `image`. **§0.10 cross-schema-`products`-read resolution applied here** (recommended Option (b): scope by `product_id` post-ownership-shim rather than the in-SQL `products` join, OR keep the transitional `public.products` read grant). | services-builder + database-builder |
| `app/domain.py` | NEW (from `modules/image/domain.py`) | 4 frozen dataclasses (`ProductImage`, `ImageUrl`, `ImageStatusSummary`, `PrecheckResult`) + 2 Literals (`ImageStatus`, `WatermarkCheckOutcome`). | services-builder |
| `app/schemas.py` | NEW (from `modules/image/schemas.py`) | `ImageUploadResponse`, `ImageSummary`, `ImagesListResponse` (PRIVATE wire-shape). | api-routes-builder |
| `app/exceptions.py` | NEW (from `modules/image/exceptions.py`) | `ImageError` hierarchy (5 subclasses: InvalidImageFormat/TooLarge/InvalidIdx/SlotOccupied/NotFound). | services-builder |
| `app/celery_app.py` | NEW | Single-task (`include=["app.tasks"]`), queue **`svc-image`**, broker Valkey DB 1 / results DB 2, keys prefixed **`svc-image:`** (§2.E). Keep `task_prerun` JWT re-validation for `image.precheck` (the §18.F handler scoped to the one task) + all locked worker invariants (§0.9). | services-builder |
| `app/core/extracted_clients/catalog_client.py` | NEW | HTTP shim re-exporting `assert_product_ownership(product_id, user_id, db=...)` → `GET catalog-svc/internal/products/{id}/ownership-check`. **catalog is in-process until MS-5** → shim base URL = **monolith ClusterIP** (`monolith-svc:8001`), not a not-yet-existent catalog-svc (R4 hybrid posture). | services-builder |
| `app/ai_ops/**` | NEW (VENDORED, C1) | Copy of `backend/app/ai_ops/` — `client.py`, `cost_tracker.py`, `guardrail.py`, `budget_cap.py`, `prompt_registry.py`, `eval.py`, `__init__.py` + `prompts/watermark_v1.py` (the ONLY prompt image needs; `autofill_v1.py`/`smart_picker_v1.py` may be omitted to trim — confirm prompt_registry `resolve()` doesn't eager-import all 3). Budget brake reads SHARED Valkey DB 0. | services-builder |
| `app/adapters/gcs.py` | NEW (VENDORED) | Copy of `backend/app/adapters/gcs.py` (4 methods; image uses upload_bytes/download_bytes/generate_signed_url). ADC from pod SA. | services-builder |
| `app/shared/{database,config,valkey}.py` | NEW (vendored) | TRIMMED Settings: `DATABASE_URL`@schema `image`, `VALKEY_URL`, `JWT_SECRET`, `GCS_*`, `GEMINI_API_KEY`, `LANGFUSE_*`, `AI_OPS_*`, `APP_ENV`. **image NEEDS GEMINI+LANGFUSE** (AI-consuming, UNLIKE export). NO MSG91/RAZORPAY. | services-builder |
| `app/core/middleware/*` | NEW (vendored) | 6-mw chain (C2). | services-builder |
| `app/core/{auth,tenancy,errors,audit,cache}.py` | NEW (vendored) | `auth.py` (local JWT), `tenancy.py` (`scope_to_user`), `errors.py` (MeesellError envelope), `audit.py` (direct-write API for the worker audit). | services-builder |
| `app/i18n/messages_en.py` | NEW (vendored subset) | The 5 image `validation_message_id` strings (`validation.image.invalid_format`, `.too_large`, `.invalid_idx`, `image.slot.occupied`, `image.not.found` — `i18n/messages_en.py:146-161`). | services-builder |
| `requirements.txt` | NEW | fastapi, sqlalchemy, asyncpg, celery, redis, httpx, **pillow==10.4.0**, google-cloud-storage, **+ ai_ops deps (gemini SDK, langfuse)**, **rembg==2.0.59 + onnxruntime==1.19.0 per §3.G decision**. NO msg91/razorpay/openpyxl. PIN same versions as monolith (R5-class). | services-builder |
| `alembic/` | NEW | Own chain rooted at schema `image`; `version_table_schema="image"`. | database-builder |
| `tests/test_image_extraction.py` | NEW | Hybrid-mode integration test (in-process + HTTP-shim). | backend-coordinator |
| `Dockerfile` | NEW (placeholder) | infra lead authors on infra branch (rembg/Pillow image-size per §3.G). | infra-builder |

### 3.E — The `/internal/*` CALLEE shim image MUST expose (MS-A FROZEN — §0.7 + spec_msA §0.4 row 6)

image is a **CALLEE of export** (export was extracted at MS-1). The MS-A HTTP-shim contract doc froze ONE image endpoint that svc-image must implement:

```
image-svc  GET /internal/products/{id}/images
  ← list_images(user_id: UUID, product_id: UUID, *, db: AsyncSession) -> ImagesListResponse
     (image/service.py:232 ; ImagesListResponse = list[ImageSummary], schemas.py:86)
     Body shape (schemas.py:50-95, ImageSummary): image_id(UUID), idx(1-4), status(Literal pending|ready|failed_precheck),
       signed_url(str, GCS signed URL TTL 1h), precheck_jsonb(dict, 5 keys), is_front(bool), width/height(int|None),
       color_space(str|None), created_at(datetime).
  Caller (export-svc image_client) forwards user JWT in Authorization for ownership re-validation.
  NOT Traefik-exposed (K3s cluster-DNS only per §2.C).
```

**Reconcile rule:** when MS-A's final shim-contract doc lands, diff this shape against it. If MS-A froze `get_image_bytes` instead of `list_images` (the stale MASTER_PLAN §1.C wording) — **STOP, escalate to master session, do NOT implement both.** spec_msA §0.4 row 6 already corrected this to `list_images`; the corrected contract is authoritative.

### 3.F — A2 middleware: which of the 6 apply to image
| Middleware | image uses? | Evidence |
|---|---|---|
| CORS | yes (chain head) | standard, all services |
| request_id | yes | `X-Request-ID` propagation per §5.E |
| auth_mw / `get_current_user` | yes | both routes `Depends(get_current_user)` (`router.py:89`,`:134`) |
| tenancy_mw | yes | `request.state.user_id` feeds `scope_to_user` in repository |
| rate_limit_mw | yes | `@rate_limit` on BOTH routes (`router.py:85`,`:131`) — shared Valkey DB 0 per §5.C |
| plan_guard_mw | **NO-OP** | image participates in no plan_guard resource (§11.J — 4-slot rule is structural DB CHECK, not plan_guard); mw runs but matches nothing |
| audit_mw | yes (POST only) | `@audit_event("image.upload.received")` on POST (`router.py:86`); GET has none; worker `image.precheck.completed` is a direct ORM write (§15.E exception, `tasks.py:370`) |

### 3.G — rembg DECISION (declared dependency, ZERO live call sites — §0.4)

**State (re-verified §0.4):** `rembg==2.0.59` is in `backend/requirements.txt:14` (with its `onnxruntime==1.19.0:16` backend) but has **ZERO references in `backend/app/**`** (`grep -rni rembg backend/app` = empty). The live V1 precheck pipeline is **Pillow steps 1–4 + ai_ops Gemini watermark step 5** (`tasks.py:82-247`) — **NO background-removal step executes**. rembg is a *declared/planned* surface, not a live call site. **There is no rembg call to move.**

**DECISION — DEFER rembg from svc-image's V1.5 `requirements.txt` (recommended).** Rationale:
- Carrying rembg+onnxruntime adds **~300MB+ image weight** (u2net ONNX model ~170MB, downloaded on first run unless pre-baked into the image) + a multi-hundred-MB inference working set — directly worsening the §7 D3 VM-fit risk on the heaviest container, for a dependency that **runs nothing in V1**.
- The extraction's §16.G/§3.A discipline is "move the LIVE behavior byte-for-byte." rembg has no live behavior to preserve; carrying it is scope-creep, not extraction fidelity.
- If/when a background-removal precheck step is added (a future AI-track feature owned by `meesell-image-precheck-builder` + `meesell-prompt-engineer`), rembg is re-added to svc-image's `requirements.txt` in THAT feature's PR — with its own D3 VM-fit re-assessment and model-pre-bake decision at that time.

**ALTERNATIVE (if founder/AI-lead wants the planned bg-removal surface live in V1.5):** carry `rembg==2.0.59`+`onnxruntime==1.19.0` in svc-image `requirements.txt`, **pre-bake the u2net model into the Docker image** (avoid first-run download in the pod), and size the worker for ONNX inference (worker lim → ~2.5Gi, §7) — and raise the D3 VM ask proactively since image+rembg is the container that triggers it.

**The sub-plan reports the TRUE state and recommends DEFER; the final carry/defer call is a Phase-2 founder/AI-lead confirmation (it touches AI-track scope + infra image size). The `requirements.txt` row in §3 lists rembg/onnxruntime as conditional-on-this-decision, NOT a default include. Do NOT invent a rembg call site to justify carrying it.**

### Backend — monolith-side strangler changes (LEAD-owned, apply only AT cutover)
| File | Tag | Description |
|---|---|---|
| `backend/app/modules/image/` (8 files) | KEEP-then-DELETE | live until hybrid-mode CI green ≥7 days, then deleted (§3.C). |
| `backend/app/main.py:46`+`:126` | MODIFY (at cutover) | remove `image_router` import + mount; Traefik routes image paths to svc-image. Until cutover stays mounted (both modes). Minimal+additive shared-file edit per common-rule #4 — PLANNED here, NOT executed now. |
| `backend/app/workers/celery_app.py:103` | MODIFY (at cutover) | remove `"app.modules.image.tasks"` from `include=[...]`; drop `image.precheck` from `_TASKS_REQUIRING_USER_REVALIDATION` (`:125`). Minimal+additive; PLANNED, NOT executed now. |

### Infra (placeholders only — owned by infra lead, land on infra branch — see `handoff_msC_infra.md`)
| File | Tag | Description |
|---|---|---|
| `backend/services/svc-image/Dockerfile` | NEW (placeholder) | FROM python:3.12-slim; **§3.G rembg/onnxruntime adds ~300MB+ model+lib weight** if carried. |
| `k8s/svc-image/deployment.yaml` | NEW (placeholder) | api 1 replica + **dedicated Celery worker 1 replica** (consumes `svc-image` queue); sizing per §7 (heaviest container). |
| `k8s/svc-image/service.yaml` | NEW (placeholder) | ClusterIP `svc-image:8001`. |
| Traefik IngressRoute | NEW (placeholder) | `/api/v1/products/{id}/images*` → svc-image:8001; `/internal/*` NOT exposed. |
| Postgres `image` schema + role | NEW (placeholder) | `CREATE SCHEMA image; GRANT ... TO image_user;` + `GRANT INSERT ON public.audit_events TO image_user` (worker audit) + §0.10 transitional `GRANT SELECT ON public.products TO image_user` (until catalog extracts at MS-5, if Option (a) chosen). |

---

## 4. ai_ops vendoring surface (C1 / D6 — the precise vendored package)

Per D6/A1, svc-image vendors `ai_ops/` in-process (no ai-ops-svc). Files to copy from `backend/app/ai_ops/`:
- `client.py` — sole AI import surface; `AICallContext` (dataclass, `client.py:70`) + `call_gemini(ctx, prompt_id, prompt_vars, *, image_bytes=...)` + `_fallback_parsed` workload-specific graceful fallback (`client.py:111`).
- `budget_cap.py` — `check_and_reserve` / `release_reservation`; **SHARED brake** via Valkey DB 0 counters `ai:cost:daily:{YYYY-MM-DD}` + `ai:cost:pending:{YYYY-MM-DD}` + reservation keys `ai:budget:reservation:{id}` (`budget_cap.py:26-48`); ₹500 daily cap, 00:00 IST reset, 25h TTL. svc-image reads/writes the SAME keyspace as all AI services (no per-service prefix on the budget keys — the cap is GLOBAL per D6).
- `cost_tracker.py` — gemini-2.5-flash rate constants; direct-write to `audit_events` (the §6A.D documented exception).
- `guardrail.py` — Layer 1 prompt prefix + Layer 2 enum re-validation (watermark output `{has_watermark, confidence}` validated per §6A.E, up to 2 retries).
- `prompt_registry.py` — `resolve()` version pinning; image needs `watermark.v1`.
- `eval.py` — `run_eval()` (the watermark golden set, accuracy ≥85%); optional for runtime but keep for CI parity.
- `prompts/watermark_v1.py` — the watermark vision prompt content (owned by `meesell-prompt-engineer`). `autofill_v1.py` + `smart_picker_v1.py` are NOT needed by image — **confirm at Phase 2 whether `prompt_registry.resolve()` eager-imports all 3** (`backend/app/ai_ops/prompts/__init__.py`); trim if safe, keep all 3 if the registry barrel-imports.

Env svc-image needs for ai_ops: `GEMINI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `AI_OPS_*` (daily cap config). These go to svc-image's Secret Manager mount (per §5.D — `langfuse-secret-key` already populated per §22 audit). **Cross-lane handoff to AI lead:** the `watermark.v1` prompt version pin must NOT drift during extraction — see `handoff` note in §8.

---

## 5. Documentation deliverables (PHASE 2 gate conditions)
- svc-image standalone OpenAPI (2 public endpoints + 3 schemas + 1 `/internal` route).
- **HTTP-shim contract doc** — image's OUTBOUND shim (catalog `assert_product_ownership`, pointing at monolith ClusterIP during MS-C) + image's INBOUND shim it newly EXPOSES (`/internal/products/{id}/images` per §3.E). Consume the MS-A contract doc; reconcile the `list_images` shape; record any drift escalation.
- `BACKEND_ARCHITECTURE.md §11` amendment ("Extracted to svc-image V1.5" note) — **§11 is LOCKED → FOUNDER APPROVAL REQUIRED** before this lands (§7.3). Do NOT self-amend a LOCKED section.
- `MASTER_PLAN.md §4 row C` annotation flip ("Sub-Plan C IN EXECUTION").
- `docs/runbooks/svc-image-rollback.md` (§6 below, specialized for image).
- Hybrid-mode CI config note: image's HTTP-mode CI needs export-svc standalone (export CALLS image's new `/internal` shim) + monolith ClusterIP for catalog (image's outbound shim target). category/dashboard not needed for image's own CI.

---

## 6. Rollback (per MASTER_PLAN §3.C, specialized for image)
1. Traefik IngressRoute for image paths → back to monolith ClusterIP.
2. `core/extracted_clients/catalog_client.py` re-exports in-process `service.py` (1-line / 1-revert per §16.G).
3. export-svc's `image_client` shim base URL → back to monolith ClusterIP (export consumes image's `/internal`).
4. `product_images` schema → back to `public` (`alembic downgrade` the schema-split); restore any §0.10 transitional grant state.
5. `kubectl delete deployment svc-image` (api + worker).
6. Re-add `app.modules.image.tasks` to monolith celery_app `include` if it was removed; re-run hybrid-mode CI pure in-process; document root cause in runbook "Rollback Log".
Rollback allowed any time BEFORE MS-C declared complete (7-day green window). Tasks are row-level idempotent (`celery_app.py:30-33` G3 lock) — re-execution is safe.

---

## 7. D3 VM-fit note — svc-image is the HEAVIEST container (FLAG FOR WAVE-2 DEPLOY)

**EXPLICIT RISK FLAG.** Per the parallel-program D3 checkpoint + MASTER_PLAN §3.A.1: the current `e2-standard-2` node fits "roughly the monolith + 2–3 small services." svc-image is **NOT a small service**:
- The Celery worker runs **Pillow image decode + (if §3.G carries rembg) ONNX-runtime background-removal model inference** — both CPU+memory heavy. image precheck on a 1500×1500+ JPEG holds the full image in memory (10MB cap per `service.py:79`) plus Pillow's decoded bitmap.
- **rembg==2.0.59 + onnxruntime==1.19.0** (if carried per §3.G) add **~300MB+ to the image** (the u2net ONNX model alone is ~170MB, downloaded on first run unless pre-baked) and a multi-hundred-MB memory working set during inference.
- MS-A sized svc-export worker at 200m/512Mi (XLSX build). **svc-image worker will need MORE** — provisional ask: api 50m/128Mi req (light), **worker 500m/1Gi req, 1000m/2Gi lim** (Pillow + ai_ops; +rembg pushes lim toward 2.5Gi). This is a Phase-2 infra-lane number to validate, NOT locked here.
- **D3 TRIGGER ASSESSMENT:** monolith + svc-export (MS-1) + svc-dashboard (MS-2 partner, tiny) + svc-image (MS-2, heavy) may be the point the node fills. **If infra capacity math shows overflow during the MS-2 deploy, STOP and ask the founder for the D3 upgrade (e2-standard-4, ~₹2,600/mo) — plan-pre-approved but the SPEND gets a fresh founder ask at that moment (MASTER_PLAN §3.A.1 standing rule). Never provision the VM without it.** This is the most likely D3-trigger point in the early waves — flag it loudly in `handoff_msC_infra.md`.

---

## 8. Validation (PHASE 2 merge-gate, lead-owned)
- Full backend suite `def test_` count MONOTONIC ≥ **649** baseline (§0.11) — quote LIVE count at PR time; do NOT hardcode 823.
- image's own 29 tests green in BOTH modes (monolith pre-flip + extracted svc-image), plus `export/test_front_image_check.py:140-142` `list_images`-not-called assertion still satisfiable against the `/internal` shim (or no-tunnel baseline: pure-function/contract subset green, infra-gated skips documented per the auth-otp no-tunnel pattern).
- `ruff` clean on `backend/services/svc-image/`.
- import-linter: svc-image must keep Contract 2 (domain→`adapters.gemini` FORBIDDEN — AI only via `ai_ops.client`); Contract 5 (ai_ops confined to category/catalog/**image**) — image is an ALLOWED ai_ops consumer, so the vendored ai_ops is in-bounds.
- §16.G: `git diff` of extracted `service.py` vs monolith shows ONLY the catalog import line (`service.py:53`) changed — ZERO changes to call sites `:162`/`:248`.
- ai_ops vendoring: the watermark call still fires `call_gemini(ctx,"watermark.v1",...)`; budget brake still hits SHARED Valkey DB 0 (an integration test asserts the `ai:cost:daily:{date}` counter increments cross-service).
- NO tautological tests (pricing lesson): the hybrid integration test asserts REAL behavior (an `image.precheck.completed` audit row lands; the `/internal/products/{id}/images` shim returns the real `ImagesListResponse` shape with signed URLs; the watermark `skipped_budget` fallback path resolves status to `ready` when steps 1-4 pass).
- Rollback runbook present (§6) per §3.C.
- **Cross-schema-`products`-join (§0.10) resolved** — either the HTTP-shim-scoped repository (Option b, recommended) OR the documented transitional `public.products` read grant (Option a); the merge gate verifies no silent cross-schema SQL read survives into the locked target.

---

## 9. Branch plan (Model C — PHASE 2 only; cut from origin/develop)

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/microservices-image/integration` | `origin/develop` | Integration; merge commits only; F3 protection (PR-only, review-count 0, checks=[], no force-push/deletions, enforce_admins false) | backend lead (merge approval) + founder (integration→develop gate) |
| `feature/microservices-image/backend` | `…/integration` | All backend specialist extraction work | backend specialists |
| `feature/microservices-image/infra` | `…/integration` | Dockerfile, K8s (api + worker), Postgres schema/role/grants, Traefik route, GCS SA | meesell-infra-builder |

Worktrees per dispatch under `/tmp/mesell-wt/msC-*` (e.g. `/tmp/mesell-wt/msC-services`, `/tmp/mesell-wt/msC-db`, `/tmp/mesell-wt/msC-routes`). NEVER `git add -A` in a worktree — scope every stage to `backend/services/svc-image/` (PILOT op-learning #3). Shared-file edits (main.py mount removal, celery_app include) are minimal+additive and PLANNED in §3, NOT executed at extraction start; integration branch merges `origin/develop` BEFORE the founder-gate PR opens (common-rule #4).

**PR flow:** group → integration is the LEAD gate (squash). integration → develop is the **FOUNDER gate (left OPEN — lead does NOT approve)**, per D1. Parallel-lane discipline with MS-B (dashboard): MS-C diffs stay in `backend/services/svc-image/` surfaces; shared files additive.

---

## 10. Acceptance gate (PHASE 2 — DONE when)
- [ ] MS-A founder gate merged + MS-A recipe consumed/reconciled (THE PHASE-2 PRECONDITION).
- [ ] `feature/microservices-image/backend` PR merged to `.../integration` (backend lead gate).
- [ ] `feature/microservices-image/infra` PR merged to `.../integration` (infra lead gate).
- [ ] Hybrid-mode CI green in BOTH modes (in-process monolith + svc-image-as-pod) ≥7 days, incl. export-svc calling image's `/internal` shim.
- [ ] `pytest backend/services/svc-image/tests/test_image_extraction.py` green.
- [ ] V1_FEATURE_SPEC Feature 5 (Image Pre-check) acceptance criteria still met against the extracted service.
- [ ] Watermark P95 / precheck pipeline behavior unchanged (AI-track `meesell-image-precheck-builder` sign-off).
- [ ] CI gates 1/2/3 green; 4/5 advisory.
- [ ] Documentation deliverables landed (OpenAPI, §11 amendment w/ founder approval, runbook, shim-contract reconciliation).
- [ ] §0.10 cross-schema-`products`-read resolved (no silent cross-schema SQL in target).
- [ ] D3 VM-fit confirmed (svc-image fits node, OR founder D3 ask raised+approved before deploy).
- [ ] `feature_board_backend.md` row reflects MERGED.
- [ ] Founder approval on `feature/microservices-image/integration` → `develop` PR.

---

## 11. Risk register (image-specific subset of MASTER_PLAN §6)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RC1 | The cross-schema `product_images`↔`products` tenancy join (§0.10) breaks when `product_images` moves to schema `image` but `products` stays in `public`/catalog | **High** | High | Recommended Option (b): scope repository by `product_id` AFTER the `assert_product_ownership` HTTP shim proves ownership (aligns §2.D "no cross-schema SQL"). Fallback Option (a): transitional `GRANT SELECT ON public.products TO image_user` during strangler window. Decide at Phase 2 vs MS-A recipe; ESCALATE if recipe silent. |
| RC2 | svc-image worker (Pillow + rembg/ONNX) overflows the e2-standard-2 node at MS-2 deploy (§7) | Medium | High | §7 D3-fit flag; infra capacity math BEFORE deploy; fresh founder D3 ask if overflow. rembg deferral (§3.G) cuts ~300MB if chosen. |
| RC3 | ai_ops budget-brake desync — svc-image's vendored copy double-counts or mis-reads the GLOBAL ₹500 cap | Low | Medium | Budget keys (`ai:cost:daily/pending`, reservation) stay UN-prefixed in shared Valkey DB 0 (NOT `svc-image:`-prefixed) per C1/D6 — the cap is global. Integration test asserts cross-service counter coherence. |
| RC4 | The `/internal/products/{id}/images` callee shim drifts from the MS-A frozen `list_images` shape (the `get_image_bytes` cautionary tale) | Medium | Medium | §3.E freezes the shape from `image/service.py:232` + `schemas.py`; reconcile against MS-A's final contract doc BEFORE Phase 2; STOP+escalate on drift, never improvise. |
| RC5 | Watermark `watermark.v1` prompt version pin drifts during extraction → eval regression | Low | Medium | Pin frozen via `prompt_registry.resolve("watermark.v1")`; cross-lane handoff to AI lead (§8); golden eval (accuracy ≥85%) re-run in CI. |
| RC6 | Celery queue split — `image.precheck` loses broker/result keyspace moving from shared monolith app to svc-image's own app | Low | High | Keys re-prefixed `svc-image:` (§2.E); tasks row-level idempotent (G3 lock) — re-run safe; one-off Valkey backfill at cutover. |

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-12 | mesell-ms-image-session-1 (MS-C Phase 1) | Initial DRAFT. Sub-Plan C authored per MASTER_PLAN §4 row C + SUB_PLAN_01 shape template, AS-BUILT grounded at origin/develop c859955, file:line citations throughout. ai_ops vendoring (C1/D6), 6-mw vendoring (C2/D7), `/internal/list-images` callee shim frozen per MS-A §0.4 row 6 (`list_images` NOT `get_image_bytes`), rembg decision (§3.G — declared dep, zero call sites), §0.10 cross-schema-products-join hazard surfaced, D3 VM-fit flag (heaviest container, §7). Execution PHASE 2 GATED on MS-A founder gate + recipe. |

---

**END OF SUB-PLAN C — PHASE 1 (spec) DRAFT; PHASE 2 (execution) GATED on MS-A founder gate + recipe.**
