# SPEC — Wave 6 Wave C Lane 1 · `wave6-catalog-form`

**Author:** MeeSell Frontend Lead · session `mesell-wave6-c-specs-session-1` · 2026-06-12
**Type:** HYBRID step-1 TASK SPEC (SPEC ONLY — no code, no git ops this session)
**Slice:** `wave6-catalog-form` (apps/mfe-catalog — catalog-form funnel page)
**Base for authoring:** develop `7e99e1d`. **Base for the BUILD:** POST-#161 develop (re-count baseline at dispatch).
**Parallel peer:** lane 2 `wave6-export` (apps/mfe-export) — FILE-DISJOINT.
**Master plan:** `docs/plans/wave6_api_wiring/MASTER_PLAN.md` §4.2 Wave C lane 1 + §1.2 rows 15/16/18/19/22 + §6.

---

## 0. One-paragraph summary

Wire the catalog-form page (`/catalogs/:id/edit`, `apps/mfe-catalog/.../catalog-form/catalog-form/catalog-form.component.ts`) from its all-mock `CatalogFormApiService` (`of(SEED).pipe(delay)`) to the real backend. Four endpoints: (#15) `GET /api/v1/categories/{id}/schema` for the dynamic field schema, (#18) `PATCH /api/v1/products/{id}` for autosave, (#22) `GET /api/v1/products/{id}/draft` for draft recovery, (#16) `GET /api/v1/categories/{id}/field-enum/{name}` for Brand-pattern dropdowns, plus (#19) `POST /api/v1/products/{id}/autofill` for the AI-fill button (FE OWNS this UI wiring — no AI FE slice exists). DISCREPANCY-1 is already resolved in Wave A (smart-picker re-point) — NOT this slice's job. The keystone difficulty is that the real `SchemaResponse.fields` is a **flat `list[dict]` with 9 LOCKED keys** (`name, canonical_name, marker, data_type, primitive, help_text, is_advanced, enum_resolver, validation_message_ids`), NOT the mock's `FieldGroup[]` with `compulsory/recommended/optional` groups and a 4-value `primitive`. This is a transcription + adapter job, not a drop-in swap.

---

## 1. AI-lane boundary resolution (READ FIRST — resolves a master-plan internal contradiction)

**Ground-truth (verified on develop `7e99e1d`, `feature_board_ai.md` + `STATUS_AI.md`):**
- The AI lane's `catalog-form` row (#56) is `autofill_v1.py` PROMPT + eval work, wired at `backend/app/modules/catalog/service.py:636`. It is BACKEND-only. The AI PR template gates on eval evidence, not screenshots.
- There is **NO AI-lane frontend slice** for autofill anywhere on the AI board (active or recently merged).
- F5 image-precheck G3 ruling: `fix_hints = FE static map`, explicitly "tracked by frontend lead", "NOT an AI/backend deliverable" — that is a Wave D concern, not Wave C.

**The contradiction:** master-plan §4.2 Wave C lane-1 line says *"Does NOT wire autofill (#19) — AI-lane boundary, §6"* — but §6 concludes *"Therefore Wave 6 Wave-C OWNS the autofill UI wiring (button → POST /autofill → overlay the AutofillResponse.suggestions onto the form)"* because no AI FE slice exists.

**RESOLUTION (lead, grounded in the as-built AI board):** §6 governs (it is the conclusion after the board check; §4.2 is the conservative pre-check default). **catalog-form Wave C OWNS the autofill HTTP call + the suggestion-overlay UI.** The AI lane owns ONLY the prompt + endpoint behaviour + eval behind `POST /products/{id}/autofill`. The autofill button + `onAutofill()` + the yellow `.mee-ai-suggested` highlight already exist in the component (mock) — this slice points them at the real endpoint. **No frontend file in this slice touches `ai_ops/` or the prompt registry.**

**Action at dispatch (NOT now):** the lead opens a confirm-memo to `meesell-ai-coordinator`: "FE Wave C wires the autofill overlay (button→POST /products/{id}/autofill→render AutofillResponse.suggestions). Confirm the AI lane is NOT also wiring this overlay." Default assumption (board-verified): they are not. Add an Inter-lead request row on the frontend board (outgoing, 48h SLA).

---

## 2. Contract inventory — DTOs cited file:line (schema = source of truth)

All verified MOUNTED in `backend/app/main.py` (the row-26 lesson: schema existence ≠ mounted contract):
- `category_router` mounted UNCONDITIONALLY (main.py L120). #15 + #16 ALWAYS available.
- `catalog_router` mounted **CONDITIONALLY** behind `if settings.FEATURE_CATALOG_FORM_ENABLED:` (main.py L127). When OFF, every `/api/v1/products/*` path → 404. #18 + #19 + #22 are flag-gated.
- `autofill` (#19) carries a SECOND flag: `if not settings.FEATURE_AI_AUTOFILL_ENABLED: 404` (catalog/router.py L213-217).

| # | Method · Path | Request schema | Response schema | Source of truth (file:line) | Flag |
|---|---|---|---|---|---|
| 15 | `GET /categories/{id}/schema` | — (ETag via `If-None-Match` header) | `SchemaResponse` | `category/schemas.py:153` (`SchemaResponse`); handler `category/router.py:219` (ETag, 304 on match) | none (always mounted) |
| 16 | `GET /categories/{id}/field-enum/{name}` | — | `FieldEnumResponse{enum_entries:EnumEntry[],total,truncated}` | `category/schemas.py:202`; `EnumEntry{canonical,meesho,labels}` L185; handler `category/router.py:268` | none |
| 18 | `PATCH /products/{id}` | `PatchProductRequest{fields?:dict, status?:'draft'\|'ready'}` (extra=forbid; ≥1 of fields/status required) | `ProductResponse` | req `catalog/schemas.py:` `PatchProductRequest`; resp `ProductResponse` (id,catalog_id,category_id,name,status,fields,ai_suggestions,created_at,updated_at); handler `catalog/router.py:163` (X-Autosave header alias `x-autosave`) | FEATURE_CATALOG_FORM_ENABLED |
| 19 | `POST /products/{id}/autofill` | `AutofillRequest{description:str(1..2000), fields_to_fill?:str[]}` (extra=forbid) | `AutofillResponse{suggestions:{[canonical]:AutofillSuggestion{value,confidence(0..1),source:'ai'}}, applied:{[k]:bool}, fallback_offered:bool}` | req+resp `catalog/schemas.py`; handler `catalog/router.py:195` | FEATURE_CATALOG_FORM_ENABLED + FEATURE_AI_AUTOFILL_ENABLED |
| 22 | `GET /products/{id}/draft` | — | `ProductDraftResponse{fields:dict, last_updated:datetime, autosave_count:int}` OR **204 no body** when never autosaved | `catalog/schemas.py` `ProductDraftResponse`; handler `catalog/router.py:345` | FEATURE_CATALOG_FORM_ENABLED |

**SchemaResponse exact shape (`category/schemas.py:153`):**
```
SchemaResponse { model_config = extra="allow"
  fields: list[dict[str, Any]]      # ← FLAT list, NOT grouped
  compulsory_count: int
  optional_count: int
  total_count: int
  wizard_step_count: int
  main_sheet_label: str             # export-only; wizard does NOT render
  compliance_shape: 'standard' | 'collapsed'
}
```
**Each `fields[*]` carries the 9 §5A.C-LOCKED keys** (verified `backend/tests/test_per_field_shape_keys.py:4-18`):
```
name                    # human label (the field's display label)
canonical_name          # snake_case key (regex [a-z][a-z0-9_]*) — the form value key
marker                  # 'compulsory' | 'optional'   ← TWO values, NOT a 3-way group
data_type               # e.g. 'dropdown', 'text', ... (drives enum_resolver requirement)
primitive               # ∈ 11 LOCKED values: text_short, text_long, number, currency,
                        #   dropdown_small, dropdown_api_search, image_upload, ... (verify full set in seed)
help_text
is_advanced             # bool — true only for ADVANCED_CANONICAL_NAMES (collapsible "advanced" section)
enum_resolver           # 'category' | 'static' when data_type=='dropdown'; else None
validation_message_ids
```
Extra keys allowed per §5A.E forward-compat (e.g. `enum_values`, `unit_suffix`) — the 9 are a SUBSET assertion.

---

## 3. The mock-vs-real shape delta (the keystone — service-builder MUST read this)

| Concern | Mock (current `catalog-form-api.service.ts` + `field-schema.model.ts`) | Real (`SchemaResponse`) | Action |
|---|---|---|---|
| Source endpoint | `getSchema(categoryId)` returns inline `KURTI_SCHEMA` | `GET /categories/{id}/schema` (category module, ETag) | Re-point to real HTTP via ApiClient |
| Container shape | `FieldGroup[]` with `group: 'compulsory'\|'recommended'\|'optional'` | flat `fields: list[dict]` + `marker: 'compulsory'\|'optional'` | **ADAPTER:** map flat→grouped. There is NO 'recommended' marker — only compulsory/optional. Decide grouping: compulsory section + (optional split by `is_advanced`: basic-optional vs advanced). DO NOT invent a 'recommended' bucket. |
| `primitive` | `'text_short'\|'text_long'\|'number'\|'enum'` | 11-value LOCKED enum (text_short, text_long, number, currency, dropdown_small, dropdown_api_search, image_upload, ...) | **ADAPTER:** map real primitives → the mee-* widget. `dropdown_small`+`dropdown_api_search`→mee-select (or async); `currency`/`number`→mee-input[type=number]; `text_long`→mee-textarea; `text_short`→mee-input; `image_upload`→SKIP (images are the separate /images page). Keep an explicit primitive→widget map function in the model file (pure, unit-tested). |
| `required` | per-field `required: boolean` | derive from `marker === 'compulsory'` | adapter sets `required` from marker |
| field key | `canonical_name` | `canonical_name` | same (good) |
| label | `display_name` | `name` | adapter renames `name`→display label |
| enum options | inline `enum_options: {label,value}[]` | NOT in schema for `dropdown_api_search` — must call #16 `field-enum` per field; `dropdown_small` may carry `enum_values` (forward-compat key) | **ADAPTER:** static small enums from `enum_values` if present; api-search enums lazy-load via #16 |

The adapter (`adaptSchemaResponse(raw): FieldGroup[]` or a new `CatalogField[]` view-model) is a **pure function in the model file** — unit-tested without TestBed, mirroring the existing `catalog-form.model.ts` pure-function pattern. Prefer a NEW view-model interface (`CatalogField`) transcribed from the 9 keys over bending the legacy `FieldGroup`/`FieldSchema` — but keep the component's existing group-section template working by producing the grouped structure the template already iterates (`compulsoryFields()`, `recommendedFields()`, `optionalFields()` computed). **Pragmatic mapping:** compulsory→compulsory; optional & !is_advanced→recommended (reuse the existing middle section as "More details"); optional & is_advanced→optional (advanced). This preserves the 3-section template with zero component-structure churn. Document this mapping explicitly in the adapter docstring.

---

## 4. The two P0 contract gaps (STOP-condition candidates — backend memos at dispatch)

### GAP-1 (P0): no `GET /products/{id}` → category_id + saved-fields recovery
The route is `/catalogs/:id/edit` where `:id` is a **product id**. To render the schema the form needs the product's `category_id`, and to resume editing it needs the saved `fields`. But:
- There is **NO `GET /products/{id}`** single-fetch endpoint (verified — catalog router has POST/PATCH/autofill/preview/DELETE/draft only).
- `GET /products/{id}/preview` (#20) returns `category_path` (a string, not `category_id`) AND is flag-gated `FEATURE_LIVE_PREVIEW_ENABLED` which **defaults FALSE** (the only default-false V1 flag) → 404 in most envs.
- `GET /products/{id}/draft` (#22) returns saved `fields` but NO `category_id`.

**Consequence:** the form cannot independently derive `category_id` from a product id alone with currently-mounted, flag-on endpoints.

**Resolution options (service-builder picks per the dispatch-time backend memo answer):**
- (A) **Pass `category_id` through navigation state** from smart-picker's `selectCategory` (which has the categoryId and the created product id). The route navigation `['/catalogs', product.id, 'edit']` could carry `state: { categoryId }`. This avoids a fetch but breaks on hard-reload/deep-link.
- (B) **Use `GET /products/{id}/draft` (#22) for fields** + obtain `category_id` from nav state, falling back to an empty-schema error state if neither is available on reload.
- (C) backend adds `category_id` to a fetch (cross-lead change = STOP this slice per §8 — do NOT build a client shim).

**DO NOT GUESS.** At dispatch, open a backend cross-lead memo: *"catalog-form needs the product's category_id + saved fields on a hard-reload of /catalogs/:id/edit. No GET /products/{id} exists; preview is flag-gated default-OFF. What is the intended recovery path?"* Until answered, the service-builder wires #15/#18/#22/#16 against a `category_id` obtained from nav-state (option A/B) and renders an explicit error/empty state when it is unavailable (R-W6-1). This is the documented interim; a 4xx surprise beyond it = STOP (§5.3).

### GAP-2 (P0): flag-gated 404s must be graceful
`FEATURE_CATALOG_FORM_ENABLED=false` → all of #18/#19/#22 return 404. `FEATURE_AI_AUTOFILL_ENABLED=false` → #19 returns 404. The error matrix MUST treat these 404s as "feature unavailable" graceful states (disable the AI-fill button / show a non-crashing banner), NOT as fatal. Mirror smart-picker's matrix (404→fallback shape).

---

## 5. Exact edits (file-by-file)

All under `apps/mfe-catalog/src/app/catalog-form/` (+ specs). NO file outside `apps/mfe-catalog/**`. The shell `app.config.ts`, `app.routes.ts`, `catalog.routes.ts`, `libs/core/**`, `libs/ui-kit/**`, `libs/composites/**` are FROZEN (Wave A + cutover surfaces) — out-of-lane edit = STOP.

### 5.1 `catalog-form/models/field-schema.model.ts` (EDIT — add real wire types + adapter)
- ADD `SchemaResponseDTO` interface transcribed field-for-field from `SchemaResponse` (the 7 envelope keys + `fields: SchemaFieldDTO[]`).
- ADD `SchemaFieldDTO` interface = the 9 LOCKED keys + `enum_values?: string[]` (forward-compat optional).
- ADD `FieldEnumResponseDTO` + `EnumEntryDTO` (canonical, meesho, labels).
- ADD pure `adaptSchemaResponse(dto: SchemaResponseDTO): FieldGroup[]` mapping flat→3-section per §3 (compulsory; optional&!advanced→recommended; optional&advanced→optional) + `mapPrimitiveToWidget(primitive): 'text'|'textarea'|'number'|'select'|'skip'` pure fn. KEEP the existing `FieldSchema`/`FieldGroup`/`SchemaResponse` legacy exports (component template depends on them) — the adapter OUTPUTS `FieldGroup[]`.
- Remove the stale `TODO(cross-cutting): reconcile with core models` comment ONLY if the reconciliation is done; otherwise leave.

### 5.2 `catalog-form/services/catalog-form-api.service.ts` (REWRITE — mock → real HTTP)
- Inject `ApiClient` from `@mesell/core` (NOT raw HttpClient — mirror #161 DashboardApiService). Stay `@Injectable()` (route-scoped via `catalog.routes.ts` `:id/edit` `providers:[CatalogFormApiService]` — already there, do NOT touch the route file).
- `getSchema(categoryId): Observable<FieldGroup[]>` → `this.api.get<SchemaResponseDTO>('/api/v1/categories/' + categoryId + '/schema').pipe(map(adaptSchemaResponse), catchError(matrix))`. ETag handling is optional for V1 (ApiClient doesn't expose response headers cleanly) — the backend serves 200 with body; 304 only fires if FE sends If-None-Match, which it will not in V1. Document: ETag deferred (no If-None-Match sent → always 200).
- `autosave(productId, fields): Observable<ProductResponse>` → `this.api.patch<ProductResponse>('/api/v1/products/' + productId, { fields }, { headers: { 'X-Autosave': 'true' } })`. NOTE: `PatchProductRequest` requires ≥1 of fields/status — sending `{fields}` satisfies it. Return type changes from `null` to `ProductResponse` (or map to void; keep the component's subscribe shape working).
- `autofill(productId, description): Observable<AutofillResponse>` → `this.api.post<AutofillResponse>('/api/v1/products/' + productId + '/autofill', { description })`. **Description is REQUIRED (1..2000)** — the component must supply it (from a product_title/description field value, or a sensible default). The old mock took no body. The component's `onAutofill()` must now pass a description string.
- ADD `getDraft(productId): Observable<ProductDraftResponse | null>` → #22; 204 → map to null.
- ADD `getFieldEnum(categoryId, fieldName): Observable<EnumEntryDTO[]>` → #16 for `dropdown_api_search` fields (lazy, on dropdown-open).
- **Error matrix (R-W6-1 — merge gate REJECTS if absent), per method:**
  - 401 → (refreshInterceptor handles silent refresh; only reaches here if refresh also failed) → rethrow/EMPTY → ErrorService surfaces; component shows error state.
  - 404 (schema/category not found OR catalog-form feature flag OFF) → graceful empty-schema + error banner; for autofill 404 (autofill flag OFF) → disable AI-fill button + toast "AI fill unavailable".
  - 402 (autofill plan-guard) → toast "AI fill quota reached"; no crash.
  - 422 (autosave: product status validation / invalid field) → surface the `{detail}` envelope, do NOT lose the user's input.
  - 400 / 5xx → graceful fallback + retry affordance.
  - Use ApiClient `retryOn503: true` opt-in on the schema GET (idempotent read) only.

### 5.3 `catalog-form/catalog-form/catalog-form.component.ts` (EDIT — wire real data + autofill description)
- `onAutofill()`: pass a description to the service. Source: the current `product_title` / a `description` field value if filled, else block with a toast "Add a product title first" (autofill needs ≥1 char). Render `AutofillResponse.suggestions` — note the real shape is `{[canonical]: {value, confidence, source}}` NOT a flat `{canonical: value}` map like the mock. The overlay must read `.value` from each suggestion (the existing `aiSuggestions` signal + `isAiSuggested` highlight expects a `Record<string, unknown>` — map `suggestions` → `{[k]: v.value}` for the highlight, and merge `.value` into `fieldValues`). Respect `fallback_offered` (show "AI couldn't fill — try manual" when true + empty suggestions).
- `ngOnInit()`: resolve `category_id` per GAP-1 resolution (nav-state or draft+nav-state); call `getDraft()` to pre-fill `fieldValues` on resume; call `getSchema(categoryId)`. Render error/empty state when category_id is unavailable (do NOT crash).
- Autosave: keep the existing 10s debounce + `performAutosave()`; it now calls the real PATCH. Keep `saveStatus` state machine.
- Keep `MeeToastService` usage. Add `ErrorService`/`NetworkService` integration consistent with #161 (offline banner) IF the styler adds the banner — coordinate in the styler step.

### 5.4 Specs (EDIT/ADD)
- `catalog-form-api.service.spec.ts` (NEW): `HttpTestingController`-style via ApiClient mock OR `provideHttpClientTesting` — assert each method's URL (`/api/v1/categories/{id}/schema`, `/api/v1/products/{id}` with `X-Autosave: true`, `/api/v1/products/{id}/autofill` body `{description}`, `/api/v1/products/{id}/draft` incl. 204→null, `/api/v1/categories/{id}/field-enum/{name}`) + the full error matrix (401/402/404/422/400/5xx fallbacks). This is the contract-conformance proof.
- `catalog-form.model.spec.ts` (NEW or EXTEND): unit-test `adaptSchemaResponse` (flat→3-section, marker→required, primitive→widget, is_advanced split, enum_values passthrough) + `mapPrimitiveToWidget`. Pure, no TestBed.
- `catalog-form.component.spec.ts` (EDIT): update for the new autofill shape (suggestions `.value` extraction), the description-required path, the draft-recovery pre-fill, the flag-OFF 404 graceful states.

---

## 6. Builder sequence (serial within the lane)

1. **meesell-angular-service-builder** — §5.1 model DTOs + adapter + §5.2 service rewrite + §5.4 service/model specs. Branch tip reported. (Foundation — components consume it.)
2. **meesell-angular-component-builder** — §5.3 component wiring + §5.4 component spec. Branches off the service-builder commit on the SAME `feature/wave6-catalog-form/frontend` branch.
3. **meesell-angular-ui-styler** — loading/error/empty/offline states for the wired form (skeleton during schema load, error banner on flag-OFF/4xx, autofill-in-flight state, suggestion-highlight polish), 360px + 1280px, a11y (aria-live on autosave status + error banner focus). Last.

Each builder dispatch prompt carries: `PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/apps/mfe-catalog/.` + `SESSION: mesell-wave6-catalog-form-frontend-session-1` + the relevant §-slice + the frozen-surface list + "report your TRUE branch tip (git rev-parse HEAD on feature/wave6-catalog-form/frontend) — do not infer."

---

## 7. Branch plan (Model C, as proven SP01-07 + Wave A/B)

- Worktree: `/tmp/mesell-wt/w6c-cat` off **POST-#161 develop** (NOT now — at dispatch, after founder merges #161).
- `feature/wave6-catalog-form/integration` off develop (F3-protected: PR-only / review-count 0 / strict-contexts-[] / no-force / no-delete).
- `feature/wave6-catalog-form/frontend` off the integration branch. All 3 builders commit here serially.
- Group PR `feature/wave6-catalog-form/frontend` → `feature/wave6-catalog-form/integration`: LEAD gates (HYBRID step-3), squash --admin (self-approve blocked → APPROVE rationale as comment, review-count-0 integration allows admin squash).
- `git merge origin/develop` into integration (conflict-free expected — disjoint from export lane + dashboard lane). Re-certify on merged tip.
- Founder-gate PR `feature/wave6-catalog-form/integration` → develop: OPEN + LEFT OPEN. **Lead does NOT approve (D1).**
- worktree native-build gotcha (memory): fresh worktree → `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract` then `./node_modules/.bin/ng build` directly (NOT `pnpm build`). Revert any pnpm-workspace.yaml drift before commit.

---

## 8. Parallel-lane discipline (file-disjoint with lane 2 export)

- Lane 1 (this) touches ONLY `apps/mfe-catalog/src/app/catalog-form/**` (+ its specs). Lane 2 (export) touches ONLY `apps/mfe-export/**`. ZERO file overlap → no integration-branch collision.
- **Shared surfaces FROZEN** (out-of-lane edit = STOP): `libs/core/**` (Wave A interceptors/ApiClient/Product), `libs/ui-kit/**`, `libs/composites/**`, `apps/shell/src/app/app.config.ts`, `apps/shell/src/app/app.routes.ts`, `apps/mfe-catalog/src/app/catalog.routes.ts` (route-scoped provider already correct), `apps/mfe-catalog/src/main.ts` (interceptor registration done in Wave A). DO NOT touch smart-picker/images/preview files in mfe-catalog (other pages; catalog-form only).
- **Barrel imports ONLY** from `@mesell/core`, `@mesell/ui-kit`, `@mesell/composites` (the deep-import P0 lesson — Wave B onboarding's profile.component.ts deep-import was a gate-blocking violation). The ONLY sanctioned deep import in the repo is `apps/shell` `provideMeeUi` (founder-approved root-bundle exception) — NOT available to this lane.
- **mfe-catalog INTRA-REMOTE ordering (R-W6-9):** catalog-form (this Wave C lane) MUST land before images (Wave D lane 1) — same remote, serialized. Do NOT branch images concurrently. This spec's merge UNBLOCKS the Wave D images branch.
- Builders report their TRUE branch tip (`git rev-parse HEAD`), never inferred (the branch-tip-verification lesson).

---

## 9. Validation (lead gate — every box before merge)

- **7 builds GREEN ≤90s (D12):** shell + all 6 remotes (`./node_modules/.bin/ng build <project>` each). Record times.
- **Full suite green, no NET drop.** Baseline = **RE-COUNT at dispatch** (develop @ 7e99e1d = 56 spec files; #161 adds ≥1 dashboard service spec → post-#161 baseline is HIGHER — count it at branch time, do NOT hardcode 56). Spec count MUST rise (new service + model specs) or hold; never drop. Re-confirm `apps/mfe-catalog/**/*.spec.ts` discovery (the SP0 cwd-glob gotcha, R-W6-8) — assert the new specs are discovered (`spec-apps-mfe-catalog-*`).
- **Boundary 0:** `grep -rn "from 'primeng" apps/mfe-catalog --include=*.ts | grep -v libs/ui-kit` = 0.
- **Deep-import 0 (P0):** `grep -rn "@mesell/\(ui-kit\|composites\|core\)/" apps/mfe-catalog/src/app/catalog-form --include=*.ts` = 0 (barrel only).
- **Mock removed:** `grep -n "of(.*).pipe(.*delay\|KURTI_SCHEMA\|AUTOFILL_RESPONSE" apps/mfe-catalog/src/app/catalog-form` = 0 in the service (constants moved to specs as fixtures if reused).
- **Contract greps:** wired URLs match §2 EXACTLY: `/api/v1/categories/{id}/schema`, `/api/v1/products/{id}` (PATCH), `/api/v1/products/{id}/autofill`, `/api/v1/products/{id}/draft`, `/api/v1/categories/{id}/field-enum/{name}`.
- **localStorage 0** (FE-D5).
- **Singleton §6.G:** this slice touches `@mesell/core` (ApiClient import) — re-run the grep: exactly one `_mesell_core` chunk in dist, AuthService/ApiClient defined once, not inlined into the mfe-catalog chunk.
- **Error matrix present** on every wired method (R-W6-1 auto-reject if absent) + paired error/empty-state UI.
- **TS strict + strictTemplates:** `tsc` app + spec EXIT 0.
- **a11y + screenshots** 360px + 1280px (loading + error + data + autofill-in-flight states). NOTE: native-fed headless build hangs post-bundle (Wave B lesson) — if screenshots can't be captured, SUBSTITUTE with a by-construction responsive argument + FLAG to founder UI-review (Wave B precedent, ACCEPT).
- **Disjointness diff gate:** `git diff --name-only develop...feature/wave6-catalog-form/frontend` = all under `apps/mfe-catalog/src/app/catalog-form/` (+ no shared-surface files).

---

## 10. STOP conditions (escalate, do NOT paper over)
- Backend change required (GAP-1 needs a new endpoint / GAP-2 surprise) = STOP + backend memo; do NOT build a client shim for a missing contract.
- Drift beyond §2/§3/§4 documented (a 4xx the schema didn't predict, e.g. autosave field-key rejection) = STOP (§5.3 contract-surprise).
- AI-lane regression: if the AI lane DID wire the autofill overlay (memo answer contradicts the board) = STOP, do not double-wire.
- Build > 90s; TS strict off; singleton dup chunk; deep-import reintroduced; branch open > 5 days.

## 11. Acceptance (this slice COMPLETE)
1. catalog-form wired: #15 schema (adapted flat→grouped), #18 autosave (X-Autosave), #22 draft-recovery, #16 field-enum, #19 autofill (real suggestions overlay). ZERO mock `of(SEED).delay` / `KURTI_SCHEMA` / `AUTOFILL_RESPONSE` in the service.
2. Every method has the error matrix + paired UI; flag-OFF 404s graceful (R-W6-1, GAP-2).
3. GAP-1 category_id recovery resolved per backend memo answer (or interim nav-state + explicit error state, documented).
4. adaptSchemaResponse + mapPrimitiveToWidget pure-unit-tested; service contract-tested (URL/method/header/body + matrix).
5. 7 builds ≤90s; suite monotonic-rise no drop; boundary 0; deep-import 0; localStorage 0; singleton intact; tsc EXIT 0.
6. Group PR lead-gated to integration; founder-gate PR integration→develop OPEN (lead does NOT approve, D1).
7. mfe-catalog ordering honored (this before Wave D images).

## 12. Hand-offs (author at dispatch, NOT now)
- **Backend memo (GAP-1):** product category_id + saved-fields recovery on /catalogs/:id/edit reload — what's the intended path? (no GET /products/{id}; preview flag-gated default-OFF). 48h SLA, inter-lead row.
- **AI memo:** confirm AI lane is NOT wiring the autofill overlay (FE owns it per §1). 48h SLA, inter-lead row.
- **Backend (informational):** AutofillResponse `suggestions` is `{[k]:{value,confidence,source}}` — confirm FE reads `.value` for the field overlay + may surface `confidence` as a display hint (V1.5).
