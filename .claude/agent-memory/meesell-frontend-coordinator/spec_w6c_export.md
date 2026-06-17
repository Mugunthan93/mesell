# SPEC — Wave 6 Wave C Lane 2 · `wave6-export`

**Author:** MeeSell Frontend Lead · session `mesell-wave6-c-specs-session-1` · 2026-06-12
**Type:** HYBRID step-1 TASK SPEC (SPEC ONLY — no code, no git ops this session)
**Slice:** `wave6-export` (apps/mfe-export — export page)
**Base for authoring:** develop `7e99e1d`. **Base for the BUILD:** POST-#161 develop (re-count baseline at dispatch).
**Parallel peer:** lane 1 `wave6-catalog-form` (apps/mfe-catalog) — FILE-DISJOINT.
**Master plan:** `docs/plans/wave6_api_wiring/MASTER_PLAN.md` §4.2 Wave C lane 2 + §1.2 rows 27/28.

---

## 0. One-paragraph summary

Extract a NEW `ExportApiService` from the inline `setInterval` mock inside `apps/mfe-export/src/app/export.component.ts` and wire it to the real backend: (#27) `POST /api/v1/products/{id}/export-xlsx` (202, initiate) and (#28) `GET /api/v1/exports/{export_id}` (status poll). PRESERVE the D18 timer pattern (proven SP02 mfe-export extraction) — keep a `setInterval` poll loop, do NOT RxJS-rewrite it; just point it at the real poll endpoint and `clearInterval` on `ngOnDestroy`. The biggest delta from the mock: the backend poll response is **status-based** (`pending` | `ready` | `failed`) and carries **NO `progress_pct` field** — the current fake 0→100 progress bar has no backend source and must be retired in favour of a status indicator (indeterminate spinner during `pending`).

---

## 1. Contract inventory — DTOs cited file:line (schema = source of truth)

`export_router` mounted UNCONDITIONALLY in `backend/app/main.py:146` — BUT each handler is FLAG-GATED internally (`FEATURE_XLSX_EXPORT_ENABLED`; 404 when off). Verified MOUNTED (the row-26 lesson).

| # | Method · Path | Request | Response | Source of truth (file:line) | Codes |
|---|---|---|---|---|---|
| 27 | `POST /products/{product_id}/export-xlsx` | `ExportRequest{format:'xlsx_only'\|'xlsx_with_images'='xlsx_with_images'}` (extra=forbid) | **202** `ExportInitiatedResponse{export_id:UUID, status:'pending', enqueued_task_id:str, initiated_at:datetime}` | req `export/schemas.py:26`; resp `export/schemas.py:39`; handler `export/router.py` (`initiate_export`, flag-guard 404) | 202, 400, 401, 404 (flag-off / product not found / cross-tenant), 422 (product status!='ready' → `export.product_not_ready`; front image missing when format=xlsx_with_images → `export.front_image_missing`) |
| 28 | `GET /exports/{export_id}` | — | **200** `ExportResponse{export_id:UUID, product_id:UUID, status:'pending'\|'ready'\|'failed', format, xlsx_signed_url?:str\|null, zip_signed_url?:str\|null, error_message?:str\|null, error_code?:str\|null, initiated_at:datetime, completed_at?:datetime\|null, round_trip_validated?:bool\|null}` | resp `export/schemas.py:48`; handler `export/router.py` (`get_export`) | 200 (any status), 401, 404 (not found / cross-tenant) |

**Exact response shapes:**
```
ExportInitiatedResponse {           # export/schemas.py:39  — 202
  export_id: UUID
  status: 'pending'                 # ← LITERAL 'pending', NOT 'processing'
  enqueued_task_id: str
  initiated_at: datetime
}
ExportResponse {                    # export/schemas.py:48  — 200 poll
  export_id, product_id: UUID
  status: 'pending' | 'ready' | 'failed'
  format: 'xlsx_only' | 'xlsx_with_images'
  xlsx_signed_url: str | null       # populated when status='ready' (fresh 1h GCS signed URL)
  zip_signed_url:  str | null       # populated when status='ready' AND format='xlsx_with_images'
  error_message:   str | null       # populated when status='failed'
  error_code:      str | null
  initiated_at: datetime
  completed_at: datetime | null     # always null in V1 (no DDL column)
  round_trip_validated: bool | null # true when status='ready'
  # NO progress_pct field
}
```

---

## 2. Mock-vs-real delta (the keystone — service-builder MUST read this)

| Concern | Mock (`export.component.ts` + `export.model.ts`) | Real | Action |
|---|---|---|---|
| Trigger | inline `onGenerate()` starts a fake `setInterval` progress timer | `POST /products/{id}/export-xlsx` → 202 `{export_id, status:'pending', ...}` | service.initiate(productId, format) returns the export_id |
| Progress | `progress` signal 0→100 by `PROGRESS_TICK=10` per 500ms; `MOCK_DOWNLOAD_URL` | **NO progress_pct on the wire.** Poll returns status only | **RETIRE the fake progress bar.** Replace with status-based UI: `pending`→indeterminate spinner + "Generating…"; `ready`→download; `failed`→retry. Keep mee-progress-bar ONLY as indeterminate (no value) or remove it. |
| Status enum | `ExportStatus = 'idle'\|'processing'\|'ready'\|'failed'` (UI-local) | wire = `'pending'\|'ready'\|'failed'` | Keep a UI-local status (`idle` is pre-trigger; map wire `pending`→UI `processing` for the existing template, OR rename — document the mapping). The template's 4 states stay; the SOURCE of the state is the poll. |
| Poll | none (fake timer self-completes) | `GET /exports/{export_id}` on an interval until `ready`/`failed` | **D18 timer-preserve:** `setInterval` poll (e.g. every 2s, exponential backoff per FRONTEND_ARCH §11 — backend GET note says "frontend uses exponential backoff"); `clearInterval` on terminal status AND `ngOnDestroy`. |
| Download | `window.open(MOCK_DOWNLOAD_URL)` | `window.open(xlsx_signed_url)` (and zip_signed_url for xlsx_with_images) | read the real signed URL from the `ready` poll response; URLs expire 1h → re-poll to refresh |
| Validation checklist | `SIMULATED_PASSING_CHECKS` (title_ok/category_ok/fields_ok/images_ok) gates the Generate button | **NO backend endpoint** computes these. The real readiness gate is the 422 `export.product_not_ready` on initiate | see GAP-1 below |
| `ExportTriggerResponse{export_id}` (model) | declared, UNUSED | replace with `ExportInitiatedResponse` DTO | transcribe real shape |
| format | not sent | `ExportRequest.format` defaults `xlsx_with_images` | send `{format: 'xlsx_with_images'}` (V1 default — exports images + xlsx) |

---

## 3. GAP-1 (P0): validation-checklist UI has no backend source
The left-panel "Pre-export checklist" (4 PASS/FAIL rows) is driven by `SIMULATED_PASSING_CHECKS` — there is **no backend endpoint** that returns these booleans. The real readiness signal is the **422 `export.product_not_ready` / `export.front_image_missing`** raised by `POST export-xlsx`.

**Resolution options (decide per dispatch-time scope ruling):**
- (A) **Retain the checklist as client-derived/simulated for V1** (it is a UX affordance, not a contract) — keep `SIMULATED_PASSING_CHECKS` as a display-only constant, clearly comment it as not-backend-backed, and let the REAL gate be the 422 handler (on initiate-422, show "Product not ready — complete required fields / add a front image" and surface `error_code`). LOW-risk, smallest diff.
- (B) Derive the checklist from data the FE already has (product status from a prior fetch) — but the export page has no product fetch wired and GAP-1-catalog (no GET /products/{id}) blocks a clean source. Heavier.
- (C) Remove the checklist entirely and rely solely on the 422 surface. Cleaner contract, larger UI change.

**RECOMMENDATION:** Option A for V1 (retain as display-only + real 422 gate is authoritative). **DO NOT GUESS** beyond this — at dispatch, confirm with a one-line note in the PR / a backend memo if the founder wants the checklist driven by a real endpoint (none exists in V1). The 422 handler is MANDATORY regardless of option (R-W6-1).

---

## 4. Exact edits (file-by-file)

All under `apps/mfe-export/src/app/` (+ specs). NO file outside `apps/mfe-export/**`. Shared surfaces FROZEN (libs/**, shell, app.routes, main.ts interceptor registration done in Wave A) — out-of-lane edit = STOP.

### 4.1 `export.model.ts` (EDIT)
- ADD `ExportInitiatedResponse` (export_id, status:'pending', enqueued_task_id, initiated_at) + `ExportResponseDTO` (the full #28 shape per §1) + `ExportRequest` (format literal). Transcribe field-for-field.
- REMOVE / repurpose the unused `ExportTriggerResponse{export_id}` (superseded by `ExportInitiatedResponse`).
- KEEP `ValidationChecks` + `SIMULATED_PASSING_CHECKS` + `buildCheckItems`/`allChecksPassed`/`canGenerate` IF Option A (mark `SIMULATED_PASSING_CHECKS` as display-only, not-backend-backed). REMOVE `MOCK_DOWNLOAD_URL` (real signed URL from poll). The fake-progress pure fns (`nextProgress`, `isProgressComplete`, `retryState`) — remove `nextProgress`/`isProgressComplete` (no progress on wire); keep `retryState` adjusted.
- ADD a pure `isTerminalStatus(s): boolean` (`s==='ready' || s==='failed'`) + a wire→UI status mapper if renaming.

### 4.2 `export.service.ts` (NEW — `apps/mfe-export/src/app/export.service.ts`)
- `@Injectable()` route-scoped (provided via `ExportComponent.providers[]` — D28a/D32, tree-shakes with the route chunk; mirror #161 DashboardApiService). Inject `ApiClient` from `@mesell/core` (NOT raw HttpClient).
- `initiate(productId: string, format = 'xlsx_with_images'): Observable<ExportInitiatedResponse>` → `this.api.post<ExportInitiatedResponse>('/api/v1/products/' + productId + '/export-xlsx', { format })`.
- `poll(exportId: string): Observable<ExportResponseDTO>` → `this.api.get<ExportResponseDTO>('/api/v1/exports/' + exportId)`. (Single GET; the component's setInterval drives repetition — D18 timer-preserve.)
- **Error matrix (R-W6-1 — auto-reject if absent):**
  - 401 → refreshInterceptor handles; if reaches here, EMPTY/rethrow → ErrorService.
  - 404 (initiate: flag-off OR product not found; poll: export not found) → graceful: "Export unavailable" banner; do NOT crash the poll loop.
  - 422 (initiate: `export.product_not_ready` / `export.front_image_missing`) → surface `{detail}`/`error_code` as an actionable message; do NOT retry automatically.
  - 400 / 5xx → fallback + retry affordance. `retryOn503: true` opt-in ONLY on the poll GET (idempotent), NOT on the POST initiate (non-idempotent — would double-enqueue).

### 4.3 `export.component.ts` (EDIT — wire real initiate + poll, retire fake progress)
- Inject `ExportApiService` (add to `providers:[ExportApiService]`). Read `product_id` from the route — **NOTE:** the export route is `catalogs/:id/export` in the shell (`apps/shell/src/app/app.routes.ts:97`), where `:id` is the **product id**. The remote `ExportComponent` reads it via `ActivatedRoute` `snapshot.params['id']` (the param flows through the loadComponent boundary). The current mock does NOT read the route id — ADD it.
- `onGenerate()`: `service.initiate(productId, 'xlsx_with_images')` → on 202 set `exportStatus='processing'` + store `export_id` → START the `setInterval` poll (D18 pattern, 2s, backoff). On initiate-422 → show the not-ready message (GAP-1 Option A), do NOT start polling.
- Poll tick: `service.poll(exportId)` → on `ready` → `clearInterval` + set `ready` + store `xlsx_signed_url` (+ zip_signed_url); on `failed` → `clearInterval` + set `failed` + show `error_message`; on `pending` → keep polling (no progress bar — indeterminate spinner). Cap poll attempts (e.g. 60 = 2min) → timeout state.
- RETIRE the fake `progress` 0→100 logic. Either remove `progress` signal + `mee-progress-bar value` OR switch to indeterminate. Keep `clearPollInterval()` (already correct) + `ngOnDestroy` clear (D18 — proven SP02, must prove navigate-away clears the timer).
- `onDownload()`: `window.open(this.downloadUrl())` where downloadUrl is the real `xlsx_signed_url`.
- `onRetry()`: re-trigger `onGenerate()` (a new initiate → new export_id), not just a state reset.

### 4.4 Specs
- `export.service.spec.ts` (NEW): assert initiate URL `/api/v1/products/{id}/export-xlsx` + body `{format:'xlsx_with_images'}` + 202 mapping; poll URL `/api/v1/exports/{id}` + status mapping (pending/ready/failed); full error matrix (401/404/422/400/5xx); `retryOn503` on poll only.
- `export.model.spec.ts` (EDIT): drop fake-progress tests; add `isTerminalStatus` + adjusted `retryState`; keep `buildCheckItems`/`allChecksPassed`/`canGenerate` if Option A.
- `export.component.spec.ts` (EDIT): real initiate→poll→ready→download flow with fake timers; poll-clears-on-destroy (D18); 422-not-ready path; failed-status path. Re-confirm discovery under `spec-apps-mfe-export-*`.

---

## 5. Builder sequence (serial within the lane)
1. **meesell-angular-service-builder** — §4.1 model DTOs + §4.2 NEW export.service.ts + §4.4 service/model specs. Report TRUE branch tip.
2. **meesell-angular-component-builder** — §4.3 component wiring (initiate+poll+route-id+download) + §4.4 component spec. Branches off the service commit on the SAME `feature/wave6-export/frontend` branch.
3. **meesell-angular-ui-styler** — status-based states (indeterminate spinner for pending, ready download card, failed/retry, not-ready 422 message), 360px + 1280px, a11y (aria-live on status region). Last.

Each dispatch prompt: `PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/apps/mfe-export/.` + `SESSION: mesell-wave6-export-frontend-session-1` + the §-slice + frozen-surface list + "report your TRUE branch tip — do not infer."

---

## 6. Branch plan (Model C)
- Worktree: `/tmp/mesell-wt/w6c-exp` off **POST-#161 develop** (at dispatch, after #161 merges).
- `feature/wave6-export/integration` off develop (F3-protected). `feature/wave6-export/frontend` off integration (3 builders serial).
- Group PR frontend→integration: LEAD gates (step-3), squash --admin. `git merge origin/develop` into integration (conflict-free expected). Re-certify.
- Founder-gate PR integration→develop: OPEN + LEFT OPEN. **Lead does NOT approve (D1).**
- Fresh-worktree native-build: `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract` → `./node_modules/.bin/ng build` directly. Revert pnpm-workspace.yaml drift before commit.

---

## 7. Parallel-lane discipline (file-disjoint with lane 1 catalog-form)
- This lane touches ONLY `apps/mfe-export/**`. Lane 1 touches ONLY `apps/mfe-catalog/src/app/catalog-form/**`. ZERO overlap → no collision.
- Shared surfaces FROZEN (out-of-lane edit = STOP): `libs/core/**` (Wave A ApiClient/interceptors), `libs/ui-kit/**`, `libs/composites/**`, shell `app.config.ts`/`app.routes.ts`, `apps/mfe-export/src/main.ts` (interceptor registration done Wave A — do NOT touch).
- **Barrel imports ONLY** from `@mesell/core`/`@mesell/ui-kit`/`@mesell/composites` (deep-import P0 — Wave B onboarding lesson). The only sanctioned deep import in the repo is shell `provideMeeUi` (not available here).
- Builders report TRUE branch tip (`git rev-parse HEAD`), never inferred.

---

## 8. Validation (lead gate)
- **7 builds GREEN ≤90s (D12):** shell + 6 remotes. Record times.
- **Full suite green, no NET drop.** Baseline = RE-COUNT at dispatch (develop @ 7e99e1d = 56 spec files; #161 raises it — count at branch time, do NOT hardcode). mfe-export currently has 1 spec (`export.component.spec.ts`); this slice adds `export.service.spec.ts` + `export.model.spec.ts` → count MUST rise. Re-confirm `apps/mfe-export/**/*.spec.ts` discovery (R-W6-8).
- **Boundary 0:** `grep "from 'primeng" apps/mfe-export --include=*.ts | grep -v libs/ui-kit` = 0.
- **Deep-import 0 (P0):** `grep "@mesell/\(ui-kit\|composites\|core\)/" apps/mfe-export/src/app --include=*.ts` = 0 (barrel only).
- **Mock removed:** `grep "MOCK_DOWNLOAD_URL\|setInterval.*PROGRESS\|of(.*delay" apps/mfe-export/src/app/export.component.ts` = 0 fake-progress (a real poll `setInterval` is EXPECTED per D18 — distinguish: real poll calls `service.poll`, fake progress incremented a counter).
- **Contract greps:** URLs match §1 EXACTLY: `/api/v1/products/{id}/export-xlsx`, `/api/v1/exports/{id}`.
- **localStorage 0** (FE-D5).
- **Singleton §6.G:** touches `@mesell/core` (ApiClient) — one `_mesell_core` chunk, not inlined into mfe-export chunk.
- **D18 timer proof:** test asserts `clearInterval` fires on `ngOnDestroy` AND on terminal status (navigate-away clears the poll — the remote-side-polling precedent, SP02).
- **Error matrix present** (R-W6-1 auto-reject if absent) incl. the 422 not-ready surface.
- **TS strict + strictTemplates:** tsc app + spec EXIT 0.
- **a11y + screenshots** 360px + 1280px (idle / generating-pending / ready-download / failed states). Native-fed headless screenshot caveat → substitute + flag to founder UI-review if needed (Wave B precedent).
- **Disjointness diff gate:** `git diff --name-only develop...feature/wave6-export/frontend` = all under `apps/mfe-export/`.

---

## 9. STOP conditions
- Backend change required (a real validation-checklist endpoint, or a poll shape surprise) = STOP + backend memo; no client shim.
- Drift beyond §1/§2/§3 documented = STOP (§5.3 contract-surprise).
- Build > 90s; TS strict off; singleton dup chunk; deep-import reintroduced; branch open > 5 days.
- (No AI-lane interaction in this lane — export has no AI surface.)

## 10. Acceptance (this slice COMPLETE)
1. export wired: #27 initiate (202, format=xlsx_with_images) + #28 status-poll (pending→ready/failed) + real signed-URL download. ZERO `MOCK_DOWNLOAD_URL` / fake-progress.
2. D18 timer preserved (setInterval poll, clears on terminal + ngOnDestroy, proven by spec).
3. Error matrix incl. 422 not-ready surface; flag-off 404 graceful (R-W6-1).
4. Status-based UI (no progress_pct); validation checklist resolved per GAP-1 (Option A display-only + 422 authoritative, or scope-ruled alternative).
5. service contract-tested (URL/method/body + matrix); model pure-tested.
6. 7 builds ≤90s; suite monotonic-rise no drop; boundary 0; deep-import 0; localStorage 0; singleton intact; tsc EXIT 0.
7. Group PR lead-gated to integration; founder-gate PR integration→develop OPEN (lead does NOT approve, D1).

## 11. Hand-offs (author at dispatch if needed, NOT now)
- **Backend memo (only if scope ruling chooses NOT Option A):** "export validation-checklist has no backend source; is a readiness endpoint wanted, or is the 422 initiate gate the V1 contract?" Default: 422 is authoritative, checklist is display-only → no memo needed.
- No AI hand-off (export has no AI surface).
