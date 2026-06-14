# feature_image_precheck_frontend — meesell-frontend-coordinator

## Session mesell-image-precheck-frontend-session-1 — 2026-06-11 — HYBRID STEP 1 (as-built audit + 2 specialist SPECs; SPEC-only, no code, no dispatch)

### What this session did
- Repaired my own MEMORY.md merge conflict (stash markers 282-338, keep-both, both session blocks preserved). Staged in master tree to clear UU.
- Full as-built audit of the image-precheck FE surface. Branch feature/image-precheck-frontend (FLAT) cut off origin/develop dd5ae0d, pushed; worktree /tmp/mesell-wt/image-precheck-frontend. Board IN PROGRESS row + STATUS block committed on the branch (f1d0746).
- Authored 2 specialist SPECs (service-builder + component-builder), returned to master for STEP-2 dispatch. Did NOT call Task, did NOT write feature code.

### THE BIG AUDIT FINDING — the UI ALREADY EXISTS as a simulation shell
- `apps/mfe-catalog/src/app/images/image-uploader/` exists (component + model + spec) from Waves 3-5. It is the image-uploader page, OnPush standalone, mee-* + composites, 6-slot grid, **inline precheck-report TABLE in the template** (NOT a separate precheck-report.component — FEATURE_PLAN's row-4 precheck-report.component does NOT need to be a new file; the report is already inline). setTimeout SIMULATION map (slot 1 fails color_space) + setInterval poll-stub + ngOnDestroy clearInterval + URL.createObjectURL thumbnails.
- So FEATURE_PLAN frontend rows are STALE on shape: the work is NOT "create features/images/image-uploader.component + precheck-report.component" — it is "(a) create the MISSING image.service.ts; (b) REWIRE the existing image-uploader off SIMULATION onto image.service + remap the contract keys". This is the same shape as the smart-picker-wiring PORT (UI shell already shipped via SP05; wiring is the gap).

### REAL GAPS (G1-G7)
- G1 NO image.service.ts (only component + model). Multipart upload + backoff poll entirely missing.
- G2 component is SIMULATION-only (setTimeout/setInterval/createObjectURL).
- G3 precheck_jsonb KEY MISMATCH: backend ImageSummary keys jpeg_valid/color_space/resolution_pass/white_background/watermark_check (image/schemas.py on develop) vs UI model keys jpeg_format/color_space_rgb/min_resolution/white_bg/no_watermark. One-way remap of the UI model. FOUNDER CONFIRM R-IP-B.
- G4 SLOT MISMATCH: UI 0-based max-6 vs backend idx 1-based 1..4 (CHECK constraint D1-LOCKED). Header text "up to 6 images" stale (§F5 amended 6→4 in PR #118).
- G5 STATUS ENUM: UI pending|pass|fail vs backend pending|ready|failed_precheck.
- G6 NO feature-flag service/guard anywhere. Backend flag-OFF: POST→404, GET→{images:[]}. SPEC handles 404 in the service error matrix as flag-off→disabled; does NOT invent featureFlagGuard infra (deferred / separate slice). FEATURE_PLAN D2's featureFlagGuard cannot be built without a feature-flags.service that does not exist.
- G7 NO graceful-degradation error matrix (R-W6-1 P0 — merge gate REJECTS a wired service with no catchError).

### THE GOVERNING-PLAN CONFLICT (R-IP-A, FOUNDER) — load-bearing
- FEATURE_PLAN.md (docs/plans/features/image-precheck/) routes this as the `image-precheck` feature, frontend group riding the same feature alongside backend PR #118 + AI lane. Phase D/E: service-builder then component-builder.
- BUT Wave6 MASTER_PLAN.md (docs/plans/wave6_api_wiring/, status ACTIVE, founder-RULED 2026-06-11) routes image FE wiring as `wave6-images` = **Wave D lane 1**, explicitly gated behind: Wave A foundation (the jwt/refresh/error interceptor chain — image.service would use jwtInterceptor not manual Bearer if Wave A landed first); R-W6-9 (catalog-form wired before images — same remote, avoid double-branch collision; catalog-form is STILL MOCK on develop, of(KURTI_SCHEMA).pipe(delay)); R-W6-10 (AI confirm-memo before Wave D).
- These two plans prescribe DIFFERENT sequencing + DIFFERENT auth-wiring (manual Bearer now vs jwtInterceptor after Wave A). I did NOT pick — flagged to founder. My SPECs are written to the manual-Bearer-now shape (CategoryService precedent) so they work standalone IF founder picks the FEATURE_PLAN lane; if founder picks the Wave-D lane, the auth line changes to jwtInterceptor (post-Wave-A) and R-W6-9 forces catalog-form-wiring first.

### CONTRACT (authoritative, from backend image/schemas.py on develop)
- POST /api/v1/products/{id}/images — multipart (file: UploadFile, idx: int 1-4 via Form). 202 → ImageUploadResponse {image_id, gcs_path, status:'pending', idx, enqueued_task_id}. 404 when FEATURE_IMAGE_PRECHECK_ENABLED off. 10/min/user rate limit.
- GET /api/v1/products/{id}/images — 200 → ImagesListResponse {images: ImageSummary[]} (0-4, idx ASC). {images:[]} when flag off (NOT 404). 600/h per-IP.
- ImageSummary {image_id:UUID, idx:1-4, status:'pending'|'ready'|'failed_precheck', signed_url, precheck_jsonb:{5 keys}, is_front:bool(idx==1), width?, height?, color_space?, created_at}.
- precheck_jsonb keys: jpeg_valid, color_space, resolution_pass, white_background, watermark_check.

### REFERENCE PATTERN (the live one to copy)
- apps/mfe-catalog/src/app/smart-picker/services/category.service.ts — @Injectable() (no providedIn, route/component-scoped), inject(HttpClient/Router/AuthService), private authHeaders() from AuthService.getToken() (FE-D5 in-memory, never localStorage), catchError matrix (401→logout+EMPTY, 402/404/5xx→fallback shape, 400→EMPTY). NO MeeToastService injected into services (DIP). Wave-7 interceptor migration note in JSDoc.
- AuthService surface (@mesell/core): getToken():string|null, setSession(token,user), logout(), isAuthenticated computed, currentUser computed.
- provideHttpClient(withFetch()) already in shell app.config.ts + mfe-catalog main.ts. NO new root wiring needed.

### DISPATCH (returned to master)
- SERIAL, service-builder FIRST (component depends on the service interface). Both on feature/image-precheck-frontend, worktree /tmp/mesell-wt/image-precheck-frontend. ui-styler NOT in scope (component absorbs styling).
- Test baseline = 47 spec files on develop dd5ae0d. image.service.spec.ts ADDS (→48). image-uploader.component.spec.ts stays (rewritten in place, no file-count change). Below 47 = HARD REJECT.

### OPS
- Branch is FLAT feature/image-precheck-frontend (NOT feature/image-precheck/frontend) — the feature/image-precheck leaf exists (PR #118) so sub-refs are git D/F-blocked. The image-precheck-ai lane uses the same flat pattern (feature/image-precheck-ai). Sibling worktrees image-precheck-ai + image-precheck-backend in flight — left untouched.
- Edit tool worked on the FRESH worktree (board/STATUS); guard-blocked on the master-tree shared checkout (MEMORY.md) — Bash heredoc fallback for memory writes (recurring pattern).
- Master tree on develop, never branch-switched.
