# SPEC — Wave 6 Wave D Lane 1 · `wave6-images`

**Author:** MeeSell Frontend Lead · session `mesell-wave6-d-specs-session-1` · 2026-06-12
**Type:** HYBRID step-1 TASK SPEC (SPEC ONLY — no code, no dispatch, no git this session)
**Slice:** `wave6-images` (apps/mfe-catalog — image-uploader page, `/catalogs/:id/images`)
**Base for authoring:** develop `b348dac`. **Base for the BUILD:** POST-catalog-form-founder-gate develop (R-W6-9 execution gate — see §6).
**Parallel peer:** lane 2 `wave6-pricing` (apps/mfe-pricing) — FILE-DISJOINT (different remote).
**Master plan:** `docs/plans/wave6_api_wiring/MASTER_PLAN.md` §4.2 Wave D lane 1 + §1.2 rows 23/24 + §6 (AI boundary).

---

## 0. ONE-PARAGRAPH SUMMARY — READ THIS FIRST: this is a RECONCILE, not a greenfield wire

⛔ **CRITICAL GROUND-TRUTH (the row-26 discipline applied to MY OWN plan):** the `wave6-images` page is **ALREADY HTTP-WIRED ON DEVELOP**. The image FE wiring landed EARLY as the standalone slice `feature/image-precheck-frontend` (PR mirrors AI #122; gate PASS recorded `gate_outcome_image_precheck.md`) and IS on develop `b348dac` right now: `apps/mfe-catalog/src/app/images/image-uploader/image.service.ts` EXISTS and the component is wired off simulation (`ImageService.upload`/`pollImages`, real poll, NOT setTimeout). The Wave-6 master plan §4.2 Wave-D-lane-1 was written BEFORE that early landing and the board carries an explicit **do-not-double-dispatch** cross-ref. **Therefore `wave6-images` is NOT "build the ImageApiService + wire the upload/poll" — that is DONE.** What REMAINS is a **reconciliation to the Wave-A interceptor/ApiClient shape** + one carried follow-up. If the founder/master-session reads "wire the image pages from scratch," that is wrong — STOP and confirm scope against this §0 before any dispatch. The two real deltas are (D-IMG-1) migrate `image.service.ts` off its manual `authHeaders()` Bearer + raw `HttpClient` onto the now-landed `jwtInterceptor` + `ApiClient` (the JSDoc in the file literally says "Wave 7" should do this — Wave 6 Wave-A landed it, so it is Wave-D's job now), and (D-IMG-2) the real file-picker re-trigger for re-upload (the gate's ACCEPT-WITH-FOLLOW-UP deviation #4). **If the founder rules the early-landed image wiring is acceptable AS-IS for V1, this lane reduces to a thin reconcile PR or is closed as DONE.** Spec is written to the reconcile shape; flagged as AMBIGUITY-1 for a one-line founder/scope call at dispatch.

---

## 1. Contract inventory — DTOs cited file:line (schema = source of truth)

`image_router` mounted **UNCONDITIONALLY** in `backend/app/main.py:130` (NOT flag-gated at the include like catalog) — BUT each handler is FLAG-GATED internally by `FEATURE_IMAGE_PRECHECK_ENABLED` (`image/router.py:109` upload→404 when off; `:156` list→`{images:[]}` when off, NOT 404). Verified MOUNTED (the row-26 lesson — confirmed via `main.py:46` import + `:130` include + `router.py response_model=`).

| # | Method · Path | Request | Response | Source of truth (file:line) | Codes |
|---|---|---|---|---|---|
| 23 | `POST /products/{id}/images` | **multipart/form-data**: `file: UploadFile` (JPEG ≤10 MB) + `idx: int` Form (1-4) | **202** `ImageUploadResponse{image_id:UUID, gcs_path:str, status:'pending', idx:int 1-4, enqueued_task_id:str}` | handler `image/router.py:75-127` (`@router.post`, `response_model=ImageUploadResponse`, `status_code=202`, `@rate_limit(scope="image_upload", limit=10, window=60)`); resp `image/schemas.py` `ImageUploadResponse`; flag-guard `:109` | 202; 400 (invalid format/too large/`InvalidImageIdxError` idx∉[1,4]); 401; 404 (flag-off OR product not found/cross-tenant); 429 (10/min/user) |
| 24 | `GET /products/{id}/images` | — | **200** `ImagesListResponse{images: ImageSummary[]}` (0-4, idx ASC) | handler `image/router.py:130-` (`@router.get`, `response_model=ImagesListResponse`, `@rate_limit(scope="image_list", limit=600, window=3600)`); resp `image/schemas.py` `ImagesListResponse`+`ImageSummary`; flag-OFF returns `{images:[]}` `:156` | 200; 401; 404 (`catalog.product.not_found`); 429 (600/h per-IP) |

**Exact response shapes (transcribed field-for-field from `image/schemas.py`):**
```
ImageUploadResponse {                 # 202
  image_id: UUID
  gcs_path: str                       # GCS object path (no scheme)
  status: 'pending'                   # ← LITERAL 'pending' only
  idx: int                            # 1-4 (ge=1, le=4)
  enqueued_task_id: str               # Celery id, informational only — poll is canonical
}
ImageSummary {                        # element of ImagesListResponse.images
  image_id: UUID
  idx: int                            # 1-4
  status: 'pending' | 'ready' | 'failed_precheck'   # ← 3-value, NOT pending|pass|fail
  signed_url: str                     # GCS signed URL, TTL 1h → re-poll to refresh
  precheck_jsonb: dict                # 5 keys: jpeg_valid, color_space, resolution_pass,
                                      #         white_background, watermark_check  (default {})
  is_front: bool                      # idx == 1
  width: int | null
  height: int | null
  color_space: str | null             # 'RGB' | 'CMYK' | 'Gray'
  created_at: datetime
}
ImagesListResponse { images: ImageSummary[] }   # length 0-4, idx ASC
```

**These shapes are ALREADY transcribed correctly on develop** (gate PASS verified the remap: backend keys `jpeg_valid/color_space/resolution_pass/white_background/watermark_check` are LIVE in `image-uploader.model.ts`, the old UI keys `jpeg_format/color_space_rgb/…` exist only as absence-assertions in specs). **Re-verify at dispatch — do not re-transcribe.**

---

## 2. As-built state on develop (what EXISTS — do NOT rebuild)

Files (all under `apps/mfe-catalog/src/app/images/image-uploader/`):
- `image.service.ts` — `@Injectable()` route/component-scoped. **Uses raw `HttpClient` + manual `authHeaders()` Bearer from `AuthService.getToken()`** (FE-D5 in-memory). `catchError` matrix present (401→logout+EMPTY, 402/404/5xx→fallback, 400→EMPTY). Methods: `upload(productId, file, idx)` (multipart, 202), `pollImages(productId)` (recursive setTimeout backoff 1→2→4→8→16→30s, MAX_POLLS=6, teardown clears timer + unsubscribes). JSDoc line ~15-21: *"Uses HttpClient directly (no global JWT interceptor — Wave 6 gap)… MIGRATION: when Wave 6 adds withInterceptors([jwtInterceptor])… remove the authHeaders() helper."* **← Wave A landed exactly that. This migration note is THIS LANE'S work.**
- `image-uploader.component.ts` — OnPush standalone. Injects `ImageService` (route-scoped `providers:[ImageService]`), `ActivatedRoute`, `Router`. 6-slot→4-slot grid (header amended 6→4 in PR #118), inline precheck-report TABLE, `URL.createObjectURL` thumbnails, `is_front` badge. `onReupload()` calls `imageService.upload(productId, new File([], 'reupload-N'), idx)` — **the zero-byte File placeholder (deviation #4) — fails real multipart at runtime.**
- `image-uploader.model.ts` — pure logic + 5 backend precheck keys + `PRECHECK_HINTS` (G3 fix_hints static map, §F5 wording).
- `image-uploader.component.spec.ts` + `image.service.spec.ts` — present (gate: 48 files/521 tests when landed; develop now 57 files).

---

## 3. THE TWO REAL DELTAS (the only work in this lane)

### D-IMG-1 (P0) — migrate `image.service.ts` to the Wave-A interceptor + ApiClient shape
Wave A is on develop: `jwtInterceptor` registered in `apps/mfe-catalog/src/main.ts` (confirmed pattern — shell app.config + all 6 remote main.ts carry `withInterceptors([jwtInterceptor, refreshInterceptor, errorInterceptor])`), and `ApiClient` (`libs/core/services/api-client.service.ts`) exposes `get/post/patch/delete<T>(path, options?)` with `retryOn503?` + `withCredentials?`. The reconcile:
- **REMOVE** the `private authHeaders()` helper and every `{ headers: this.authHeaders() }` call site — the global `jwtInterceptor` now attaches `Authorization: Bearer` automatically (it reads `AuthService.getToken()`, the same in-memory FE-D5 source). Grep-assert `authHeaders` count = 0 post-edit.
- **MIGRATE** `inject(HttpClient)` → `inject(ApiClient)` from `@mesell/core`. Re-point:
  - `upload`: `this.api.post<ImageUploadResponse>('/api/v1/products/' + productId + '/images', formData)` — **NOTE: multipart.** Pass a `FormData` body (file + idx). Do NOT set `Content-Type` manually (the browser sets the multipart boundary; ApiClient/HttpClient forwards FormData untouched). **`retryOn503` MUST be FALSE/omitted on upload** (non-idempotent — would double-enqueue + double-bill GCS; same rule as export #27 POST).
  - `pollImages` GET: `this.api.get<ImagesListResponse>('/api/v1/products/' + productId + '/images')`. The GET is idempotent → `retryOn503` *could* opt-in BUT **DO NOT use ApiClient `retryOn503` — KNOWN DEFECT** (see §3.1). The component's existing recursive-setTimeout backoff poll IS the retry mechanism — preserve it (D18-class timer rule, §3.2).
- **PRESERVE** the `catchError` matrix (R-W6-1) — but note `refreshInterceptor` now owns the 401→refresh→retry path, so the service's 401 handler becomes a fallback-after-refresh-fails (logout+EMPTY), NOT the first responder. Keep it (defence-in-depth, matches #161 dashboard pattern).
- **DELETE** the Wave-7 migration JSDoc note (it's now executed).

### D-IMG-2 (P1, carried deviation #4) — real file-picker re-trigger for re-upload
`onReupload()` currently passes `new File([], 'reupload-N')` (zero-byte placeholder). Replace with a real re-trigger of the slot's `<input type="file">` so the seller picks a fresh file → `upload(productId, realFile, idx)`. This is the ui-styler/component-wiring item the image-precheck gate LOGGED as a Wave-6 follow-up. Component-builder owns it. Assert the re-upload path sends a non-empty File.

### 3.1 ⛔ ApiClient `retryOn503` is DEFECTIVE — do NOT use it
`ApiClient.applyRetry` (`api-client.service.ts:35-46`) is `retry({count:2, delay:timer(n*1000)})` with **NO error-status filter** — it retries on ANY error (400/401/404/422/network), not just 503/transient. Using `retryOn503:true` here would retry on a 422/400 (wasteful) and could re-fire through the refresh path on 401. **This lane uses NO ApiClient retry.** Idempotent-GET resilience comes from the component's bounded recursive-setTimeout poll (already correct). If a future need for true retry arises, use the **export-lane layered-retry pattern** (component-driven bounded poll/retry around a plain `api.get`), NOT the ApiClient flag. This defect is in my frozen-surface amendment bundle (§ amendment chore) to be fixed in a Wave-A-frozen-surface §7.3 chore post-Wave-D.

### 3.2 D18-class timer rule (polling)
The poll is a recursive `setTimeout` backoff (1→2→4→8→16→30s, MAX_POLLS=6), NOT `setInterval`, NOT RxJS `expand/timer` — gate ACCEPTED this as idiomatic + leak-safe. **PRESERVE it exactly** (the export lane preserves `setInterval`; here it's recursive setTimeout — same D18 principle: do not RxJS-rewrite a working bounded poll). Teardown MUST clear the timer + unsubscribe the in-flight GET on `ngOnDestroy` AND on terminal (all slots `ready`/`failed_precheck`). Spec must prove navigate-away clears the timer (the remote-side-polling precedent).

---

## 4. Exact edits (file-by-file)

All under `apps/mfe-catalog/src/app/images/image-uploader/` (+ specs). **NO file outside `apps/mfe-catalog/src/app/images/**`.** In particular: NOT `apps/mfe-catalog/src/app/catalog-form/**` (that is the Wave-C lane's territory — even though same remote), NOT `apps/mfe-catalog/src/main.ts` (interceptor registration done Wave A — FROZEN), NOT `libs/**`, NOT shell. Disjoint-from-catalog-form is the intra-remote rule (see §6/§7).

### 4.1 `image.service.ts` (EDIT — the D-IMG-1 reconcile)
- `inject(ApiClient)` from `@mesell/core` replacing `inject(HttpClient)`. Drop `HttpHeaders` import.
- `upload`: `api.post<ImageUploadResponse>(path, formData)` — FormData body, NO retryOn503, NO manual headers.
- `pollImages` GET: `api.get<ImagesListResponse>(path)` — NO retryOn503; component poll drives repetition.
- Remove `authHeaders()` + all `{headers: this.authHeaders()}`. Keep `inject(AuthService)` ONLY if still used for the 401-fallback `logout()` (likely yes — keep). Keep `inject(Router)` for the logout redirect.
- Preserve the `catchError` matrix; delete the Wave-7 JSDoc migration note.

### 4.2 `image-uploader.component.ts` (EDIT — D-IMG-2 + cleanup)
- `onReupload()`: real file-picker re-trigger (D-IMG-2). Wire the slot `<input type="file">` `.click()` (or a `viewChild` ref per slot) → on change → `upload(productId, file, idx)`.
- Remove the unused `DestroyRef` import (gate-logged nit; cosmetic, no CI break since no ESLint config — but clean it while here).
- No structural change to the precheck table / slot grid / `is_front` badge (already correct against contract).

### 4.3 Specs (EDIT in place — no file-count change)
- `image.service.spec.ts`: assert it now uses `ApiClient` (TestBed provides `ApiClient` + `provideHttpClientTesting()`); assert upload URL `/api/v1/products/{id}/images` + multipart FormData body + 202 mapping; poll URL + status mapping (pending/ready/failed_precheck); error matrix (401/404/400/429/5xx); **assert NO `Authorization` header set manually** (interceptor owns it) — i.e. the request the spec sees has no manual header (jwtInterceptor is NOT in HttpTestingController unless added; assert the service does not add one). FP3 annotation rule: adding `provideHttpClient(withFetch())` + `provideHttpClientTesting()` to TestBed is a SETUP change, not an assertion rewrite — ACCEPT-class.
- `image-uploader.component.spec.ts`: re-upload now sends a non-empty File (D-IMG-2); poll-clears-on-destroy (D18). Re-confirm discovery under `spec-apps-mfe-catalog-*`.

---

## 5. Builder sequence (serial within the lane)
1. **meesell-angular-service-builder** — §4.1 `image.service.ts` reconcile (ApiClient + authHeaders removal + multipart) + §4.3 service spec. Report TRUE branch tip (`git rev-parse HEAD`).
2. **meesell-angular-component-builder** — §4.2 `onReupload` real file-picker (D-IMG-2) + DestroyRef cleanup + §4.3 component spec. Branches off the service commit on the SAME `feature/wave6-images/frontend` branch.
3. **meesell-angular-ui-styler** — ONLY IF the re-upload re-trigger needs visual polish (file-input affordance, focus return). Likely thin/skippable — the component absorbs styling (gate noted "ui-styler NOT in scope" for the original image slice). If dispatched, the FROZEN-SURFACE GUARD header is MANDATORY (see §7).

Each dispatch prompt header:
```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/apps/mfe-catalog/src/app/images/.
SESSION: mesell-wave6-images-frontend-session-1
FROZEN (out-of-lane = STOP): libs/** (Wave-A ApiClient/interceptors), apps/mfe-catalog/src/main.ts (interceptor reg, Wave-A), apps/mfe-catalog/src/app/catalog-form/** (Wave-C lane), shell, docs/status/* (LEAD sole-writer — report evidence in return text only).
TOKEN RULE (styler): an undefined var(--mee-*) → define LOCALLY in :host/styles or re-point to an existing token; NEVER edit libs/design-tokens/.
RETRY RULE: ApiClient retryOn503 is DEFECTIVE — do NOT use it. Preserve the component's recursive-setTimeout poll (D18). No new retry.
Report your TRUE branch tip — do not infer.
```

---

## 6. Branch plan (Model C) + the R-W6-9 EXECUTION GATE

⛔ **R-W6-9 EXECUTION GATE (HARD — encode this as a dispatch precondition):** `wave6-images` and `wave6-catalog-form` are BOTH in `apps/mfe-catalog`. They are DIFFERENT pages/dirs (`images/**` vs `catalog-form/**`) → file-disjoint, but they must NOT branch the same remote concurrently (integration-branch collision risk). **The images lane MUST branch from develop ONLY AFTER `wave6-catalog-form`'s FOUNDER GATE merges to develop.** Catalog-form is STILL MOCK on develop right now (`of(KURTI_SCHEMA).pipe(delay)` confirmed) — its founder PR is imminent but NOT merged. **DO NOT cut `feature/wave6-images/integration` until `git show 'origin/develop:apps/mfe-catalog/src/app/catalog-form/services/catalog-form-api.service.ts'` shows NO `of(.*delay` (i.e. catalog-form is wired on develop).** Until then images is BLOCKED-on-sequence (board status BLOCKED with `Blocking=wave6-catalog-form founder-gate merge`, not a defect).

- Worktree: `/tmp/mesell-wt/w6d-img` off **POST-catalog-form-founder-gate develop** (at dispatch, after catalog-form merges).
- `feature/wave6-images/integration` off develop (F3-protected: PR-only, review-count 0, strict-contexts [], no force-push, no delete). `feature/wave6-images/frontend` off integration (2-3 builders serial).
- Group PR frontend→integration: LEAD gates (HYBRID step-3), squash `--admin`. `git merge origin/develop` into integration (conflict-free expected — catalog-form already landed; images `images/**` disjoint from any concurrent pricing `apps/mfe-pricing/**`). Re-certify.
- Founder-gate PR integration→develop: OPEN + LEFT OPEN [FOUNDER GATE — DO NOT MERGE]. **Lead does NOT approve (D1).**
- Fresh-worktree native-build: `pnpm install --frozen-lockfile` then `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract` (the `.pnpm/` store path); if that doesn't extract, `cd node_modules/.pnpm/esbuild@<ver>/node_modules/esbuild && node install.js` (image-precheck gate's proven fix). `./node_modules/.bin/ng build mfe-catalog` directly (NOT bare `ng build`). Revert pnpm-workspace.yaml drift before commit.
- **`ng test frontend`** is the ONLY test target (apps/** discovered under the `frontend` target's `../apps/**` glob; `ng test mfe-catalog` ERRORS — record from the image-precheck gate).

**Branch-slug note:** use `feature/wave6-images/{frontend,integration}` (Model C nested). The OLD early-landing slice was `feature/image-precheck-frontend` (FLAT, now merged/closed). Distinct slug — this is the Wave-D reconcile, not a re-extraction.

---

## 7. Parallel-lane discipline (file-disjoint with lane 2 pricing + intra-remote with catalog-form)
- This lane touches ONLY `apps/mfe-catalog/src/app/images/**`. Lane 2 (pricing) touches ONLY `apps/mfe-pricing/**` → ZERO overlap, different remotes.
- **Intra-remote (the dangerous one):** catalog-form (`catalog-form/**`) already landed on develop before this branches (R-W6-9), so there is no concurrent two-slice-one-remote branch. Images stays strictly in `images/**`. The disjointness gate `git diff --name-only develop...feature/wave6-images/frontend` MUST show every path under `apps/mfe-catalog/src/app/images/` — ANY `catalog-form/`, `libs/`, `main.ts`, or `smart-picker/` path = REJECT.
- **Frozen surfaces (out-of-lane = STOP):** `libs/core/**` (Wave-A ApiClient/interceptors/AuthService), `libs/ui-kit/**`, `libs/composites/**`, `libs/design-tokens/_tokens.css` (Wave-A frozen — token-gap rule), shell `app.config.ts`/`app.routes.ts`, `apps/mfe-catalog/src/main.ts` (interceptor reg). Consuming `@mesell/*` barrels (MeeEmptyState, ApiClient, AuthService) is READ-ONLY, allowed.
- **Barrel imports ONLY** from `@mesell/core`/`@mesell/ui-kit`/`@mesell/composites` (deep-import P0 — onboarding/dashboard lesson; the gate greps `@mesell/\(ui-kit\|composites\|core\)/` subpath = 0). The image slice already imports `AuthService from '@mesell/core'` (barrel) — keep barrel.
- **Boundary:** 0 primeng outside ui-kit.
- **TRUE-tip reporting:** builders report `git rev-parse HEAD`; lead `git fetch` + `git rev-parse origin/<branch>` + `git diff --name-only base..REAL-TIP` (a builder can push a follow-up commit after the SHA it names — the dashboard styler's STATUS_FRONTEND.md sneak-commit lesson). NO unsanctioned docs commits (`docs/status/*` is lead sole-writer).

---

## 8. Validation (lead gate — skeptical, re-run independently)
- **7 builds GREEN ≤90s (D12):** shell + 6 remotes. Record times (image-precheck gate: mfe-catalog 2.777s).
- **Full suite green, no NET drop.** Baseline = RE-COUNT at dispatch (develop today = **57** spec files; catalog-form's merge raises it — count at branch time via `git ls-tree -r --name-only origin/develop -- frontend/ | grep -c '\.spec\.ts$'`, do NOT hardcode). This lane EDITS specs in place (no file-count change expected) — a DROP = silent non-discovery = HARD REJECT (R-W6-8). Re-confirm `apps/mfe-catalog/**/*.spec.ts` discovery (`spec-apps-mfe-catalog-*`).
- **`authHeaders` removed:** `grep -rn "authHeaders" apps/mfe-catalog/src/app/images` = 0.
- **No manual Authorization header:** `grep -rn "Authorization\|Bearer" apps/mfe-catalog/src/app/images` = 0 (interceptor owns it).
- **ApiClient used, HttpClient not (in the service):** `grep "inject(ApiClient)" image.service.ts` present; `grep "inject(HttpClient)" image.service.ts` = 0.
- **NO ApiClient retryOn503:** `grep "retryOn503" apps/mfe-catalog/src/app/images` = 0 (the defect — §3.1).
- **No simulation remnants:** `grep "SIMULAT\|createObjectURL.*mock\|of(.*delay\|new File(\[\], " ` — `createObjectURL` for thumbnails is LEGIT (local preview), but `new File([], …)` in onReupload MUST be gone (D-IMG-2).
- **Contract greps:** URLs match §1 EXACTLY: `/api/v1/products/{id}/images` (both verbs). Precheck keys = backend 5 (`jpeg_valid/color_space/resolution_pass/white_background/watermark_check`); old keys 0 in LIVE code.
- **D18 timer proof:** test asserts the recursive-setTimeout poll clears on `ngOnDestroy` AND on terminal (all slots ready/failed).
- **Boundary 0:** `grep "from 'primeng" apps/mfe-catalog/src/app/images --include=*.ts | grep -v libs/ui-kit` = 0.
- **Deep-import 0 (P0):** `grep "@mesell/\(ui-kit\|composites\|core\)/" apps/mfe-catalog/src/app/images --include=*.ts` = 0.
- **localStorage/sessionStorage/withCredentials 0** (FE-D5; images has no cookie surface).
- **Singleton §6.G:** the service now injects `ApiClient` (which injects HttpClient) → confirm EXACTLY ONE `_mesell_core-*.js` chunk; `ImageService`/`ImageUploaderComponent` chunk references core via federation import-map, NO inline core dup. The image slice does NOT define AuthService — only consumes. (Same proof as #161 dashboard's `DashboardApiService`→ApiClient DI.)
- **TS strict + strictTemplates:** tsc app + spec EXIT 0.
- **a11y + screenshots** 360px + 1280px (empty slots / uploading-pending / ready-precheck-pass / failed_precheck-with-hints). Native-fed headless screenshot caveat → substitute + flag to founder UI-review (SP01-07 + dashboard precedent).
- **Disjointness diff gate:** `git diff --name-only develop...feature/wave6-images/frontend` = ALL under `apps/mfe-catalog/src/app/images/`.

---

## 9. AI-lane boundary (R-W6-10 — confirm BEFORE dispatch)
**Already resolved on develop** (the image slice landed with frontend rendering the precheck result): per `gate_outcome_image_precheck.md` + master plan §6, **AI lane = backend precheck pipeline + the `autofill.v1`/precheck prompt + eval ONLY; Frontend renders the precheck result (it is UI).** The G3 `fix_hints` map = FRONTEND static `PRECHECK_HINTS` (§F5 wording, AI lead confirmed in PR #122). **No AI FE row exists in `feature_board_ai.md` for image-precheck.** No double-wire. **Action at dispatch:** re-read `feature_board_ai.md` (1-min) to re-confirm no new AI precheck-display row appeared; if clean (expected), NO memo needed. The precheck-result table on the image-uploader page is FE-owned and already built — this lane does not touch `ai_ops/` or prompt registry.

---

## 10. STOP conditions (escalate to founder)
- **Scope surprise:** if the master-session/founder thinks this is a greenfield wire (it is a RECONCILE — §0). STOP + confirm scope.
- Backend change required (a precheck shape surprise, a flag-behaviour change) = STOP + backend memo; no client shim.
- Drift beyond §1/§3 documented = STOP (§5.3 contract-surprise class).
- Build > 90s; TS strict off; singleton dup `_mesell_core` chunk; deep-import reintroduced; branch open > 5 days.
- ApiClient `retryOn503` used anywhere (the defect — auto-reject).
- Any file touched outside `apps/mfe-catalog/src/app/images/**` (esp. `catalog-form/**`, `libs/`, `main.ts`, `docs/status/*`) = REJECT.
- R-W6-9 violated (branched before catalog-form on develop) = REJECT + rebrancch.

## 11. Acceptance (this slice COMPLETE)
1. `image.service.ts` reconciled to Wave-A shape: `inject(ApiClient)`, NO `authHeaders()`/manual Bearer (jwtInterceptor owns it), multipart upload via FormData, NO ApiClient retryOn503.
2. `onReupload()` triggers a real file-picker → non-empty File upload (D-IMG-2, deviation #4 closed).
3. `catchError` error matrix preserved (R-W6-1); D18 recursive-setTimeout poll preserved + clears on destroy/terminal.
4. Contract greps pass (URLs, 5 precheck keys); authHeaders 0; manual Authorization 0; retryOn503 0; old-precheck-keys 0 in live code.
5. 7 builds ≤90s; suite no drop; boundary 0; deep-import 0; localStorage 0; singleton intact; tsc EXIT 0.
6. Group PR lead-gated to integration; founder-gate PR integration→develop OPEN (lead does NOT approve, D1).
7. R-W6-9 honored: branched only after catalog-form on develop.

## 12. AMBIGUITIES (resolved, with the resolution baked in — listed for the founder/master-session)
- **AMBIGUITY-1 (the big one):** is this lane a RECONCILE (image FE already on develop) or a greenfield wire? **RESOLUTION:** RECONCILE — ground-truthed from develop `b348dac` (`image.service.ts` exists + wired). Spec written to the reconcile shape. If the founder rules the early-landed manual-Bearer wiring is acceptable AS-IS for V1, this lane shrinks to a thin PR or closes as DONE — confirm at dispatch (one line). Does NOT block lane-2 pricing.
- **AMBIGUITY-2:** does the styler (builder-3) participate? **RESOLUTION:** likely NO (component absorbs styling; original image slice excluded ui-styler). Dispatch only if D-IMG-2's file-input affordance needs visual polish; if so, the frozen-surface/token guard header is MANDATORY.
- **AMBIGUITY-3:** `retryOn503` on the idempotent poll GET? **RESOLUTION:** NO — ApiClient retry is defective (§3.1); the component's bounded recursive-setTimeout poll IS the resilience. Use export-lane layered retry only if a real need surfaces (it does not here).
- **AMBIGUITY-4:** does removing `authHeaders()` break the 401 path? **RESOLUTION:** No — `refreshInterceptor` (Wave A) now owns 401→refresh→retry; the service's 401→logout+EMPTY becomes a post-refresh-failure fallback (defence-in-depth, keep it). The interceptor reads the SAME `AuthService.getToken()` in-memory token, so the Bearer is still attached, just globally.
