# feature_image_precheck_session_1_handoff.md
# meesell-angular-service-builder — Session mesell-image-precheck-frontend-session-1 — 2026-06-11

## What this session did
Built the missing ImageService (G1) + extended the model with backend contract types (G3 R-IP-B).
Spec: 15 tests, HttpTestingController. Build GREEN 2.992s. Tests 47→48 spec files, 482 passed, 0 fail.

## Files created / modified
- NEW: frontend/apps/mfe-catalog/src/app/images/image-uploader/image.service.ts
- NEW: frontend/apps/mfe-catalog/src/app/images/image-uploader/image.service.spec.ts
- MODIFIED (additive): frontend/apps/mfe-catalog/src/app/images/image-uploader/image-uploader.model.ts

## Commits
- 9f30dc8 feat(frontend): ImageService HTTP wiring + contract types — image-precheck FE slice G1
- 4571a89 test(frontend): image.service.spec.ts — 15 tests, 47→48 spec files, 0 fail
- 5cc77aa docs(frontend): image-precheck service-builder STEP 2 complete — STATUS update

Branch: feature/image-precheck-frontend (FLAT, pushed to origin)
Worktree: /tmp/mesell-wt/image-precheck-frontend

## ImageService public API (for component-builder)
@Injectable()  // NO providedIn — component lists in providers[]
upload(productId: string, file: File, idx: number): Observable<ImageUploadResponse>
listImages(productId: string): Observable<ImagesListResponse>
pollImages(productId: string): Observable<ImagesListResponse>

Import path: ./image.service (same directory as image-uploader.component.ts)
Contract types: PrecheckJsonb / ImageSummary / ImagesListResponse / ImageUploadResponse
from ./image-uploader.model

## pollImages() implementation note
Uses recursive Observable constructor with setTimeout (NOT setInterval, NOT RxJS timer/expand).
- Each poll fires setTimeout(delayMs) -> HTTP GET -> if hasPending && pollIndex < MAX_POLLS: recurse
- Teardown: clearTimeout(timerHandle) + httpSub?.unsubscribe() — no leaked handles
- Test with vi.useFakeTimers() BEFORE the subscription (not necessarily before TestBed setup)
- DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000], MAX_POLLS = 6

## Error matrix (canonical)
upload():     401->logout+navigate('/login')+EMPTY; 402/404/400/5xx->EMPTY
listImages(): 401->logout+navigate('/login')+EMPTY; 404/400/5xx->of({images:[]})
pollImages(): same as listImages per poll (handleListError shared); hard cap 6 polls

## PrecheckJsonb keys (R-IP-B — exact backend names)
jpeg_valid, color_space (boolean), resolution_pass, white_background, watermark_check
One-way remap vs legacy FE model:
  jpeg_format -> jpeg_valid
  color_space_rgb -> color_space
  min_resolution -> resolution_pass
  white_bg -> white_background
  no_watermark -> watermark_check

## Component-builder hand-off requirements
1. ImageUploaderComponent.providers = [ImageService] (feature-scoped)
2. Replace SIMULATION map + setInterval + URL.createObjectURL with upload() -> pollImages()
3. Remap precheck_jsonb keys (G3)
4. Fix slot count: 6->4 (G4), change 0-based slot_index to 1-based idx
5. Fix status enum: pending|pass|fail -> pending|ready|failed_precheck (G5)
6. 404 on upload = feature disabled (ImageService returns EMPTY; show disabled state)
7. DO NOT add featureFlagGuard

## Test pattern reuse notes for pollImages spec
- vi.useFakeTimers() BEFORE subscription
- vi.advanceTimersByTime(delay + 500) to ensure timer fires; flush HTTP after advance
- controller.verify() in afterEach catches any leaked poll requests
