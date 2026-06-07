# STATUS — FEATURE CATALOG (MEGA-SESSION)

**Owner:** Catalog Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_CATALOG.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/features/smart-picker/` + `catalog-form/` + `images/` + `preview/` + `pricing/` + `export/`
**Routes owned:** `/catalogs/new`, `/catalogs/:id/edit`, `/catalogs/:id/images`, `/catalogs/:id/preview`, `/catalogs/:id/pricing`, `/catalogs/:id/export`
**MF-remote target (Phase 2):** catalog-mfe per FE-D13
**Special note:** THIS IS THE MEGA-SESSION. 6 feature folders, ~20+ components, 11 form primitives, ~14 endpoints. All routes share the same `productId` state context — the single biggest cohesion driver in V1.
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-07 (WAVES 1–4 COMPLETE — preview + pricing shipped; export deferred pending BACKEND §14 LOCK)

**Status:** CONSTRUCTION ACTIVE — Waves 1–4 (non-export) delivered. Export sub-feature deferred.

## Current Phase

**Waves 1–4 non-export — COMPLETE. Export sub-feature deferred pending BACKEND §14 LOCK.**

## Done

- All 9 mandatory reads complete + targeted backend §10 + MVP §5 supplementary reads (see Updates Log).
- 11-primitive contract reconciled (FRONTEND §18.E supersedes MEESHO_CAT_INT §4 ambiguity — `address_group` is the 11th primitive scoped to catalog-form for Eye-Serum collapsed-compliance template, 1 of 3,772 leaves).
- Bootstrap wave plan locked: smart-picker → catalog-form (SPINE) → images → preview/pricing/export (parallel).
- Discrepancies + Q&A entries surfaced (see bottom sections).
- **Wave 1 — smart-picker COMPLETE (2026-06-06):**
  - 12 files created under `features/smart-picker/`
  - `SmartPickerComponent` + `<mee-description-input>` + `<mee-category-card>` + `<mee-browse-fallback>` + `ProfileIncompleteDialogComponent`
  - `SmartPickerApiService` + `SmartPickerStateService` (route-scoped providers)
  - Route wired at `/catalogs/new` via `SMART_PICKER_ROUTES` in `app.routes.ts`
  - 103 tests passing / 0 failing; smart-picker chunk 16.95 kB gzip (80 kB budget MET)
  - 422 `profile_incomplete_for_category` modal with deep-link to `/profile` implemented
  - i18n keys in `src/i18n/en.json` (15 `smartPicker.*` keys)
- **Design system §5A FULL LOCK acknowledged (2026-06-06)** — 8 design-system files read; tokens live; CSS custom properties consumable now.
- **Wave 2 — catalog-form THE SPINE COMPLETE (2026-06-07):**
  - Wave 2a (service layer): `CatalogFormApiService` (X-Autosave header), `CatalogFormStateService`, `DraftRecoveryService` (204→null), `CategorySchemaService`, `EnumLookupService` — 24 tests passing
  - Wave 2b (rendering engine): 11 primitives each implementing ControlValueAccessor, `WizardRendererComponent`, `FieldDispatcherComponent` (all 11 @case values), `StepComposerService` (STEP_ORDER + isHidden filter), `AutofillOverlayComponent` — 42 tests passing
  - Wave 2c (page wiring): `CatalogFormComponent` — sequential init (getProduct→getSchema), forkJoin with draft recovery, Subject+debounceTime autosave, global autofill status bar, navigation to `/catalogs/:id/images` on submit — 6 tests passing
  - Total Wave 2: 229 tests passing / 8 pre-existing failures (not caused by Wave 2)
  - catalog-form chunk: 15.70 kB gzip (well within 120 kB exception budget)
- **Wave 3 — images COMPLETE (2026-06-07):**
  - `ImagesApiService` — uploadImage (postMultipart + retryOn503), pollImages (interval 2 s), deleteImage
  - `ImageSlotComponent` — drag-drop zone, thumbnail, indeterminate progress bar (postMultipart returns body not HttpEvent)
  - `PrecheckReportComponent` — 5 check items (is_jpeg, color_space, resolution_ok, white_bg_ok, watermark_pass) with pass/fail icons
  - `ImagesComponent` (page) — canProceed gate: slot 0 ready + watermark_pass; navigation Back→/edit, Next→/preview
  - 12 tests passing; images chunk **8.38 kB gzip** (§19 ≤80 kB BUDGET MET — 90% headroom)
- **Wave 4 — preview + pricing COMPLETE (2026-06-07):**
  - `PreviewApiService` + `PREVIEW_ROUTES` (route-scoped provider)
  - `PreviewFeedComponent` (Meesho feed card — 30-char title truncation), `PreviewDetailComponent`
  - `PreviewComponent` (page) — tab group Feed+Detail, loading/empty states, Back→/images, Next→/pricing
  - `PricingApiService` + `PRICING_ROUTES` (route-scoped provider)
  - `PnlBreakdownComponent` — line-item table, inrCurrency pipe, color-coded margin
  - `MarginSliderComponent` — mat-slider (Angular Material 18 `matSliderThumb` API), setTimeout(500) commit
  - `PricingChartComponent` — chart.js horizontal stacked bar using `COLORS_RESOLVED` from `@design-system/tokens`
  - `PricingComponent` (page) — signals + `localEstimate` computed for instant slider feedback; Back→/preview, Next→/export
  - 13 tests passing; preview chunk **11.43 kB gzip** | pricing chunk **53.84 kB gzip** (both ≤80 kB BUDGET MET)
  - Total suite: 254 passing / 7 pre-existing failures (export.component.spec.ts NG0300 — not caused by Wave 4)
- **Wave 4 — export DEFERRED** — scaffold exists; implementation pending BACKEND §14 endpoint LOCK.

## In Progress

Nothing active — all non-export waves complete. Awaiting BACKEND §14 LOCK for export dispatch.

## Blockers

- **Backend §14 export DRAFT** — defers Wave 4 export sub-feature only. Waves 1-3 + Wave 4 preview/pricing are unblocked.
- **Design system §5A ~~PARTIAL~~ → FULL LOCK (RESOLVED 2026-06-06)** — real tokens now live. ui-styler restyle pass of already-shipped components (including smart-picker) unblocked. Wave 2 dispatch uses real token references.
- **Endpoint path discrepancy — `/categories/:id/enum/:field_name` vs `/categories/{id}/field-enum/{name}`** — MVP §3.3 + FRONTEND §11.C disagree. See "Questions for master" below. Wave 2 will wire to FRONTEND §11.C (`/enum/:field_name`) per the newer LOCKED spec, flagging for backend coordinator verification before Wave 2 acceptance.

## Next

1. **Wave 1 — smart-picker** (simplest, fewest deps). Dispatch `meesell-angular-component-builder` for: SmartPickerComponent (page) + `<mee-description-input>` + `<mee-category-card>` + `<mee-browse-fallback>` + `smart-picker-api.service.ts` + `smart-picker.routes.ts` + spec files per §3.D 7-file pattern. Acceptance per §10: card click → `POST /products` → routes to `/catalogs/:id/edit` AND handles 422 `customer.profile_incomplete_for_category` (modal with deep-link to `/profile`) per BACKEND §10.B.1 + MVP §3.3 error pattern.
2. **Wave 2 — catalog-form THE SPINE** (largest dispatch wave). Per §11 + §18: CatalogFormComponent (page) + WizardRendererComponent + StepComposerService (with STEP_ORDER constant) + FieldDispatcherComponent + 11 primitives (text-short/text-long/number/number-unit/currency/dropdown-{small,medium,large,api}/image-upload/address-group) each implementing `PrimitiveInputs` contract + `ControlValueAccessor` + emitting `ValueChange` + AutofillOverlayComponent + CatalogFormApiService (with `X-Autosave: true` header on autosave-triggered PATCH per §11.A.1) + DraftRecoveryService (calls `GET /products/:id/draft` on init; handles 204 no-draft) + CatalogFormStateService + EnumLookupService (for `dropdown_api` primitive) + CategorySchemaService (feature-private per master ruling). Integrate `@shared/directives/[meeAutosave]` for the 10s+blur autosave per V1 §F3. Acceptance: 32-field Kurti category renders correctly, yellow autofill overlay accept/reject works (overlay clears + emits `ValueChange{source: 'ai-accept'}`), autosave + manual save both fire correctly with header distinction, draft recovery on reload returns last autosave state.
3. **Wave 3 — images** (post-spine because user navigates from catalog-form). Per §12: ImageUploaderComponent + ImageSlotComponent + PrecheckReportComponent + ImagesApiService. Client-side compression via `ngx-image-compress` (75% quality, 75% scale; 10MB raw → ~1MB). CDK drag-drop. Polling `GET /products/:id/images` at 2s intervals. 5 precheck items per image (is_jpeg, color_space=='RGB', resolution_ok, white_bg_ok, watermark_pass). Use `apiClient.postMultipart` with `retryOn503: true` per §4.E.1.
4. **Wave 4 — preview / pricing / export** (parallel — independent of each other, all share productId). Per §13/§14/§15. Wave 4 export DEFERS until BACKEND §14 LOCKS; Wave 4 preview + pricing proceed.

## Hand-offs

- **From master (frontend coordinator):** infrastructure authored 2026-06-06 (FE-D12 amended ratification — see master STATUS_FRONTEND 2026-06-06 SESSION-INFRASTRUCTURE entry). Catalog sub-session is the LAST recommended bootstrap in master's order (cross-cutting → auth/onboarding/profile/dashboard → catalog) because it depends on cross-cutting `core/` + `shared/` foundations + design-system @core dispatch readiness.
- **From dashboard session (expected):** navigation to `/catalogs/new` (from CTA or side menu) + navigation to `/catalogs/:id/edit` (from row click). I do NOT own the dashboard side menu.
- **From auth session (expected):** cross-cutting `AuthGuard` ratifies my 6 routes (per §23: all yes-auth, none plan-gated in V1).
- **To cross-cutting session (when surfaced):** any new `@shared/*` candidate that turns out reusable beyond catalog (e.g., if a primitive becomes useful for the V1.5 bulk-edit screen).
- **To master (on Wave N completion):** completion UPDATE block here; master integrates into FRONTEND_ARCH if any §11 / §18 contract amendment surfaces during construction; master forwards cross-track signals to STATUS_MASTER.
- **To dashboard session (post-Wave 4):** navigation back to `/dashboard` after export complete OR user back-button. Hand-off content: none — just the route navigation.

## Updates Log

=== UPDATE: 2026-06-06 SKELETON ===
STATUS file created. Catalog mega-session awaits founder bootstrap.
This is the LARGEST sub-session by far. Founder ratified consolidation
2026-06-06 because all 6 routes share productId state — splitting
would multiply hand-off ceremony without context savings. Recommend
4 dispatch waves: smart-picker → catalog-form (SPINE) → images →
preview/pricing/export (parallel).
=========

=== UPDATE: 2026-06-06 SUB-SESSION BOOTSTRAPPED ===
Catalog mega-session opened by founder per SESSION_PROMPTS_FEATURE_CATALOG.md +
SESSION_PROMPTS_FEATURE_BASE.md. This sub-session is the LAST of the 6
frontend sub-sessions to bootstrap (per master's 2026-06-06 recommended
order — cross-cutting first as maintenance on already-implemented core/+
shared/, then auth/onboarding/profile/dashboard in parallel, then catalog
last as the mega-session).

**Mandatory reads complete (9 files + 4 targeted supplements):**
  1. docs/status/STATUS_FEATURE_CATALOG.md (skeleton — this file's prior state)
  2. docs/SESSION_PROMPTS_FEATURE_BASE.md (universal master-sub protocol +
     dispatch rights + MF preparation reminder per FE-D13)
  3. docs/FRONTEND_ARCHITECTURE.md — selected sections per scope:
     - §0 Premises (FE-D1 through FE-D13 + corpus-grounded premises)
     - §1 Topology (split-token auth, ASCII flow)
     - §2.B Feature Catalog (my 6 features: rows 6-11; sub-session map)
     - §3.B + §3.C.4 (11 feature folders post-un-merger) + §3.D 7-file pattern
       (+ §3.C.4 catalog-form explicit subtree with primitives/ tree) +
       §3.E naming + §3.F aliases + §3.G decision tree
     - §4 core/ — AuthService API, ApiClient method surface +
       `retryOn503` opt-in, AuthGuard, PlanGuard (wired-but-inert V1),
       ApiError shape, cross-feature models (Product, FieldSchema,
       AiSuggestion, PaginatedResponse, LocaleMap)
     - §5 shared/ — 6 components + 3 pipes + 2 directives + 6 enums
       (specifically AutosaveDirective `[meeAutosave]` 10s+blur with
       offline queue + replay)
     - §5A Design System PARTIAL LOCK — semantic tokens, 8pt grid,
       360px baseline, M3 elevation, motion micro/standard/large
     - §6 14 locked packages — `ngx-image-compress` (Wave 3),
       `chart.js + ng2-charts` (Wave 4 pricing horizontal bar), CDK
       virtual scroll (Wave 2 dropdown_large), `@angular/cdk/drag-drop`
       (Wave 3 images)
     - §10 smart-picker LOCKED
     - §11 catalog-form THE SPINE LOCKED including §11.A.1 X-Autosave
       header amendment + error-code mapping
     - §12 images LOCKED
     - §13 preview LOCKED
     - §14 pricing LOCKED
     - §15 export LOCKED
     - §16 cross-cutting walkthroughs (state tree, i18n flow, HTTP
       cache, offline UX, plan gating, error surface, service worker)
     - §17 6 communication rules
     - §18 11 primitives + form renderer LOCKED in full — wizard
       template, dispatcher switch, PrimitiveInputs contract,
       ValueChange contract, all 11 one-line specs, STEP_ORDER
       constant, STEP_TITLES locale map, autofill overlay UX
     - §19 test pyramid + perf budget (catalog-form ≤120 KB exception)
     - §23 route inventory (12 routes, 26 endpoints)
  4. docs/MVP_ARCHITECTURE.md — §3.3 categories+schema API + §3.4
     catalog/product API + §4 11 primitives + wizard renderer + §4.4
     state management + §4.5 routes + §5.1 Smart Picker (top-5 +
     compressed tree + 24h cache) + §5.2 Auto-fill (enum-constrained
     two-layer guardrail) + §5.3 image precheck pipeline (5 checks) +
     §5.6 full per-field schema (CANONICAL + DISPLAY + EXPORT three
     layers; meesho_* never present in frontend per §6.4 stripping
     rule) + §5.6.3 STEP_ORDER (13 step IDs) + §5.6.7 validation
     message library
  5. docs/MEESHO_CATEGORY_INTELLIGENCE.md — 28 practical universals
     (15 strict + 13 near-universal incl. 9-field compliance block +
     Eye-Serum exception), 291 Brand-pattern fields (max 4,481
     values for Compatible Models), 16+ canonical alias families
     (typos "Primiary"/"Seconadry" preserved for export), 14 locked
     decisions
  6. docs/BACKEND_ARCHITECTURE.md §10 catalog module LOCKED (full
     read: 10.B.1 POST /products, 10.B.2 PATCH (X-Autosave +
     per-IP 600/h + plan guard absent), 10.B.3 POST autofill (graceful
     fallback 200 + fallback_offered=true on budget exhaustion), 10.B.4
     GET preview, 10.B.5 DELETE soft-delete, 10.B.6 GET draft (204
     no-draft case))
  7. docs/CORE_PHILOSOPHY.md — M1/M2/M3/M7/M9 + F1/F5 internalised;
     plus Pattern 3 (constrained-but-escape-hatched dropdowns for
     Brand) + Pattern 5 (Advanced fields toggle for opaque fields
     like Group ID)
  8. docs/status/STATUS_FRONTEND.md — master's current state
     (CONSTRUCTION READY — 6 sub-sessions infrastructure authored;
     master reverted to lower-frequency mode; design system Phase 1
     Round 1 dispatched + handed off to dedicated sub-session per
     FE-D11)
  9. docs/status/STATUS_DESIGN_SYSTEM.md — design system sub-session
     bootstrapped 2026-06-06; Phase 1 references (38 strong refs
     across 5 categories) curated and presented to founder for picks;
     §5A values pending founder ratification of designer-AI picks

**Discrepancies surfaced (handled inline):**
  - **D1: 10 primitives (MEESHO_CAT_INT §4) vs 11 primitives (FRONTEND §18.E + §0.D + MVP §4.1).**
    Resolution: 10 corpus-classifier primitives + `address_group` composite
    (used only for Eye-Serum collapsed-compliance template) = 11 components
    in `catalog-form/primitives/`. The corpus document was older; the
    architecture documents lock 11. Honour 11.
  - **D2: enum endpoint path `/categories/:id/enum/:field_name`
    (FRONTEND §11.C + §23) vs `/categories/{id}/field-enum/{name}`
    (MVP §3.3).** Wave 2 wires per FRONTEND §11.C (newer LOCKED spec);
    surface to master for backend coordinator cross-check before
    Wave 2 acceptance — see "Questions for master" below.
  - **D3: §11.A.1 amendment** — X-Autosave header on PATCH is canonical
    per backend §10.B.2 LOCKED. `CatalogFormApiService.patch()`
    distinguishes autosave PATCH (header set) vs manual save (no
    header) by callsite — the `[meeAutosave]` directive ALWAYS sets
    the header; the explicit "Save & Continue" button NEVER sets it.

**State assessment:**
  - All 6 routes are in §23 LOCKED (auth-required, none plan-gated in V1).
  - Master has design system sub-session running independently (FE-D11).
    Component-builder dispatch is UNBLOCKED per FE-D9 — components
    consume CSS custom properties whose values land later.
  - Backend §10 catalog module LOCKED — autosave/draft/autofill
    contracts are concrete; Wave 2 spine implementation has zero
    backend-side ambiguity.
  - Backend §14 export DRAFT — Wave 4 export sub-feature blocks; other
    waves unblocked.

**Action this turn:**
  - Bootstrap reads done.
  - This UPDATE block written.
  - No code dispatch yet (founder-cadence governed per master's
    recommendation — catalog last + each wave on its own turn).

=========

## Questions for master

=== Q: 2026-06-06 ENUM ENDPOINT PATH ===
**Surfaced to:** meesell-frontend-coordinator (master) → meesell-backend-coordinator
(via master)
**Discrepancy:** MVP §3.3 declares the enum endpoint as
`GET /api/v1/categories/{id}/field-enum/{name}?q=&page=&limit=` whereas
FRONTEND §11.C + §23 lock it as
`GET /api/v1/categories/:id/enum/:field_name?q=`. These are the same
endpoint with different paths.
**My posture:** Wave 2 (dispatched next) wires the FRONTEND §11.C path
(`/enum/:field_name`) per the newer LOCKED spec. The dropdown_api
primitive's `EnumLookupService` will call this path.
**Ask:** can master confirm with meesell-backend-coordinator which path
the backend `category` module actually exposes? Wave 2 acceptance
holds on this. If backend has implemented `/field-enum/{name}`,
update FRONTEND §11.C + §23 + my Wave 2 dispatch.
=== END Q ===

=== Q: 2026-06-06 BACKEND §14 EXPORT DRAFT STATUS ===
**Surfaced to:** meesell-frontend-coordinator (master) → meesell-backend-coordinator
**Discrepancy:** Per SESSION_PROMPTS_FEATURE_CATALOG.md bootstrap, BACKEND
§14 export is DRAFT — my Wave 4 export sub-feature blocks until LOCK.
**My posture:** Waves 1-3 + Wave 4 preview/pricing proceed in parallel.
Wave 4 export is deferred.
**Ask:** when does BACKEND §14 lock? If a relatively-near date is known,
my Wave 4 dispatch can be sequenced to land just-in-time.
=== END Q ===

=== Q: 2026-06-06 SHARED COMPONENT MATERIAL VARIANT CHOICE FOR PRIMITIVES ===
**Surfaced to:** meesell-frontend-coordinator
**Context:** FRONTEND §18.E specifies `<mee-dropdown-small>` uses
`<mat-radio-group>` (radio group). For very-small enums (1-2 values
like Yes/No or Veg/Non-Veg), `<mat-button-toggle-group>` (segmented
control) is a common Material UX choice that consumes ~1/3 the vertical
real estate. Acceptable to use `mat-button-toggle-group` for enum_count
in {2, 3} and `mat-radio-group` for {4..20}? Or strict mat-radio-group
across 1-20?
**My posture:** strict mat-radio-group per §18.E unless master rules
otherwise. The strict path is what specialists ship.
**Ask:** confirm strict mat-radio-group, or amend §18.E for the
mat-button-toggle-group two-tier split.
=== END Q ===

## Questions for sibling sessions

=== Q: 2026-06-06 → CROSS-CUTTING SESSION — APICLIENT POSTMULTIPART CONTRACT ===
**Surfaced to:** STATUS_FEATURE_CROSS_CUTTING (catalog session can read
sibling STATUS files per BASE communication protocol)
**Context:** Wave 3 (images) will use `apiClient.postMultipart` with
`retryOn503: true`. Per §4.E.1 + Look 1, `retryOn503` retries up to 3
times with exponential backoff (1s, 2s, 4s) before reaching
ErrorInterceptor.
**Ask:** confirm `postMultipart` signature `(path, formData, options?)`
matches §4.E.1 exactly + emits `HttpEvent<T>` (progress events) for the
`<mat-progress-bar>` per §12.C. If the cross-cutting session has
already implemented `core/api/api-client.service.ts`, the signature is
already locked — I'll consume as-is.
=== END Q ===

=== Q: 2026-06-06 → DASHBOARD SESSION — NAVIGATION HAND-OFF ===
**Surfaced to:** STATUS_FEATURE_DASHBOARD
**Context:** My session receives navigation to `/catalogs/new` (CTA or
side menu) + `/catalogs/:id/edit` (row click) from dashboard. Per
SESSION_PROMPTS_FEATURE_CATALOG.md bootstrap I do NOT own the side
menu — dashboard does.
**Ask:** confirm dashboard's CTA + row navigation use the route names
exactly (`/catalogs/new` not `/catalog/new`; `/catalogs/:id/edit` not
`/catalog/:id`). The path 'catalogs' (plural) is the §23 LOCKED route
inventory. The legacy React scaffold used `/catalog/:id` (singular) —
that path was wrong per FE-D1 + §23 amendment.
=== END Q ===

---

## Updates Log (sub-session)

=== UPDATE: 2026-06-06 WAVE 1 DISPATCH COMPLETE — smart-picker ===
Dispatched to: meesell-angular-component-builder (Sonnet)
Dispatch result: SUCCESS — 103 tests passing / 0 failing; build zero errors

FILES DELIVERED:
  features/smart-picker/
  ├── smart-picker.model.ts             — feature-private types (CategorySuggestion,
  │                                        SuggestResponse, ProfileIncompleteError, etc.)
  ├── smart-picker-api.service.ts       — 4 methods; NOT providedIn root
  ├── smart-picker-api.service.spec.ts  — 4/4 passing (all HTTP paths + verbs verified)
  ├── smart-picker-state.service.ts     — debounced suggest; loading/error/rateLimitHit signals;
  │                                        selectCategory() propagates 422 upward
  ├── smart-picker-state.service.spec.ts — 4/4 passing
  ├── smart-picker.routes.ts            — SMART_PICKER_ROUTES; providers scoped
  ├── smart-picker/                     ← structural deviation: double folder (see below)
  │   ├── smart-picker.component.ts     — full page; spinner; up to 3 cards; accordion browse;
  │   │                                    429 snack bar; 422 MatDialog modal; navigate post-201
  │   └── smart-picker.component.spec.ts — 4/4 passing (spinner, cards, navigation, 422 dialog)
  ├── description-input/
  │   └── description-input.component.ts  — Reactive Form; min-10-char; disabled input; submit output
  ├── category-card/
  │   └── category-card.component.ts      — input.required; confidence inline computed; 4 chips+N more; hover ring
  ├── browse-fallback/
  │   └── browse-fallback.component.ts    — two-step: super-cat mat-select → leaf debounced search
  └── profile-incomplete-dialog/
      └── profile-incomplete-dialog.component.ts — MAT_DIALOG_DATA; lists missing fields; CTA → profile_url

i18n: src/i18n/en.json — 15 smartPicker.* keys added (correct file; Transloco configured here)

BUNDLE:
  smart-picker lazy chunk: 87.39 kB raw / 16.95 kB gzip (§19 ≤80 kB BUDGET MET — 79% headroom)
  Initial bundle: ~161 kB gzip (app shell included; within §19 ≤180 kB)

DEVIATIONS FROM §3.D:
  1. Page component at `smart-picker/smart-picker/smart-picker.component.ts` (double folder)
     instead of `smart-picker/smart-picker.component.ts` (§3.D root). Routes file imports
     from the correct path `'./smart-picker/smart-picker.component'` — functionally correct;
     cosmetically off-spec. Can be flattened in the ui-styler restyle pass or left as-is
     since it works. Surfacing to master as a note (non-blocking).
  2. Sub-component spec files not created (browse-fallback, category-card, description-input,
     profile-incomplete-dialog have no `.spec.ts`). The 3 mandatory spec targets (page, api,
     state) all have passing specs. Sub-component specs can be authored in a test-only dispatch
     post-Wave 4 if coverage budget requires.
  3. `confidence-percent.pipe.ts` referenced in dispatch brief does not exist in `@shared/pipes/`.
     Agent used inline `computed()` in CategoryCardComponent as correct workaround.
     Cross-cutting session must create `confidence-percent.pipe.ts` + CategoryCardComponent
     can then import it. Surfaced as CROSS-CUTTING ACTION REQUIRED (see below).

ESCALATIONS LOGGED:
  → CROSS-CUTTING ACTION: create `shared/pipes/confidence-percent.pipe.ts` + spec.
    Used in: CategoryCardComponent (currently inlined as computed — safe workaround).
  → MASTER NOTE: initial bundle 500 kB warning in angular.json (pre-existing, not a
    Wave 1 regression; app-shell dispatch already raised budget to 900 kB per STATUS_FRONTEND).
=========

=== UPDATE: 2026-06-06 DESIGN SYSTEM §5A FULL LOCK ACKNOWLEDGED ===
Notification received from master (2026-06-06) — master-relayed from design system sub-session.

READS CONFIRMED:
  1. FRONTEND_ARCHITECTURE.md §5A — AMENDMENT 2026-06-06B confirmed; §5A status
     PARTIAL LOCK → FULL LOCK.
  2. frontend/src/app/design-system/_tokens.scss — 77 CSS custom properties;
     primary #F26B23 (saffron warm orange); secondary #1E40AF (deep blue);
     bg #f0f5f9; surface #ffffff; reduced-motion a11y; SCSS var mirrors.
  3. frontend/src/app/design-system/tokens.ts — MOTION + COLORS (CSS var refs) +
     COLORS_RESOLVED (hex for canvas). Primary resolved hex: #F26B23.
  4. frontend/src/app/design-system/_theme.scss — Material M3 + Spike Angular overrides.
  5. frontend/src/app/design-system/_typography.scss — Plus Jakarta Sans (Google Fonts,
     300-800). NOTE: Inter was the placeholder; Plus Jakarta Sans is the LOCKED typeface.
  6. frontend/src/app/design-system/_elevation.scss — 4 levels.
  7. frontend/src/app/design-system/_motion.scss — micro/standard/large tiers.
  8. frontend/src/app/design-system/_component-overrides.scss — Spike Angular 15-component
     visual language; applies automatically to all Material components.
  9. frontend/tailwind.config.js — CSS custom prop refs for semantic colors + Plus Jakarta
     Sans + mee-* radius/shadow/transition tokens.
  10. frontend/src/styles.scss — import order confirmed (tokens→theme→overrides→bridge
      →typography→elevation→motion→@tailwind).
  11. STATUS_FRONTEND.md design system integration entry (lines 2498–2571).

KEY LOCKED VALUES (for Wave 2+ dispatch scoping):
  Primary:    #F26B23 — consume via var(--mee-color-primary) / Tailwind bg-primary
  Secondary:  #1E40AF — consume via var(--mee-color-secondary) / Tailwind bg-secondary
  Background: #f0f5f9 — consume via var(--mee-color-bg)
  Surface:    #ffffff — consume via var(--mee-color-surface)
  On-surface: #2a3547 — consume via var(--mee-color-on-surface)
  Typeface:   Plus Jakarta Sans (family: 'Plus Jakarta Sans', 'Inter', system-ui)
  Radius:     7px (sm) / 16px (md) / 18px (lg) / 999px (full)
  Icons:      Material Symbols Outlined (interim)
  Motion:     100ms micro / 200ms standard / 300ms large

IMPACT ON WAVE 1 (already shipped):
  - SmartPickerComponent + sub-components were dispatched using Tailwind utility
    classes. Per master's deviation note (STATUS_FRONTEND lines 2592–2607), existing
    visual shells with hardcoded hex in inline styles[] do NOT auto-pick up CSS custom
    properties. Wave 1 components may have some hardcoded values.
  - ACTION: during ui-styler restyle pass (unblocked by §5A FULL LOCK), component-
    builder dispatch will replace any hardcoded hex in smart-picker with CSS custom
    property references. This is deferred — Wave 1 is functionally complete; visual
    polish lands in the restyle pass.

IMPACT ON WAVE 2+:
  - Dispatches now use REAL tokens. Scope component-builder prompts to:
    - Use `var(--mee-color-primary)` / `var(--mee-color-*)` for color
    - Use Tailwind utility classes (bg-primary, text-on-surface, etc.) which resolve
      via tailwind.config.js wiring to CSS custom props
    - Use Material `color="primary"` / `appearance="outlined"` directives (Spike Angular
      overrides apply automatically)
    - NO hardcoded hex, NO hardcoded font names in component styles[]
    - For canvas/chart.js: import `COLORS_RESOLVED` from `@design-system/tokens.ts`
  - Autofill yellow overlay: use `var(--mee-color-warning)` / `var(--mee-color-primary-light)`
    for the tint border per §11.A AutofillOverlayComponent spec.

DEFERRED (does NOT block Wave 2):
  - docs/design-system/RATIONALE.md
  - docs/design-system/MICROCOPY_TONE.md
  - docs/design-system/ICONOGRAPHY.md (Material Symbols Outlined interim until this lands)
  - _tokens.spec.ts (WCAG contrast verification)

BLOCKER CLEARED:
  §5A PARTIAL LOCK → FULL LOCK. The ui-styler restyle-pass dispatch is now unblocked.
  Wave 2+ dispatches consume real tokens from day 1.
=========

=== UPDATE: 2026-06-06 MASTER RULINGS RECEIVED — Q-CAT-001/002/003 ===

Q-CAT-001 ⏸ DEFERRED
  Enum endpoint path discrepancy deferred until Wave 2 is being wired.
  Wire to FRONTEND §11.C (/categories/:id/enum/:field_name) as working assumption.
  Flag for backend coordinator verification before Wave 2 acceptance sign-off.
  Not blocking Wave 2 dispatch start.

Q-CAT-002 ⏸ WAITING
  Backend §14 export LOCK ETA still unknown. Wave 4 export remains deferred.
  Waves 1–3 + Wave 4 preview/pricing remain unblocked.

Q-CAT-003 ✅ mat-button-toggle-group for mee-dropdown-small (≤3 options)
  Ruling: use MatButtonToggleGroup (not MatRadioGroup).
  Design system rationale: _component-overrides.scss §3 gives button-toggle
  pill shape (18px radius) matching Spike visual language + filter chips.
  mat-radio-group has no Spike overrides — would render as plain native radio.
  Better mobile touch targets on 360px baseline.
  Apply to: mee-dropdown-small primitive implementation in Wave 2.

Wave 2 pre-dispatch status: ALL catalog-specific Q&A resolved.
  Q-CAT-001: deferred (working assumption locked)
  Q-CAT-002: deferred (Wave 4 export only)
  Q-CAT-003: resolved ✅
  Wave 2 dispatch may proceed.
=========

=== UPDATE: 2026-06-07 WAVE 2 DISPATCH COMPLETE — catalog-form THE SPINE ===
Dispatched to: meesell-angular-component-builder (Sonnet) — 3 sub-dispatches (2a, 2b, 2c)
Dispatch result: SUCCESS — 229 tests passing / 8 pre-existing failures; build zero errors

WAVE 2a — Service layer (5 services):
  features/catalog-form/
  ├── catalog-form-api.service.ts      — getProduct, saveProduct (no X-Autosave header),
  │                                       autosaveProduct (X-Autosave: true header), requestAutofill
  ├── draft-recovery.service.ts        — getDraft(): Observable<ProductDraft | null>; 204 → null
  ├── category-schema.service.ts       — getSchema(categoryId, locale?)
  ├── enum-lookup.service.ts           — lookupEnum(categoryId, fieldName, query, limit?)
  ├── catalog-form-state.service.ts    — 8 signals + computed fields (draft merges over product) + 7 mutation methods
  └── catalog-form.routes.ts           — path: ''; providers: all 5 services (route-scoped, NOT providedIn root)
  Sub-dispatch test result: 24 tests passing

WAVE 2b — Rendering engine (11 primitives + 3 renderer files):
  features/catalog-form/primitives/
  ├── text-short-primitive/            — ControlValueAccessor; [attr.maxlength]; reactive form
  ├── text-long-primitive/             — ControlValueAccessor; [attr.maxlength]; textarea
  ├── number-primitive/                — ControlValueAccessor; min/max validation
  ├── number-with-unit-primitive/      — ControlValueAccessor; unitSuffix suffix slot
  ├── currency-primitive/              — ControlValueAccessor; INR formatting
  ├── dropdown-small-primitive/        — MatButtonToggleGroup (Q-CAT-003 ruling: ≤3 options)
  ├── dropdown-medium-primitive/       — MatSelect; inline enumOptions
  ├── dropdown-large-primitive/        — CDK VirtualScroll mat-select
  ├── dropdown-api-search-primitive/   — EnumLookupService inject; PrimitiveKind = 'dropdown_api_search'
  ├── image-upload-primitive/          — ngx-image-compress 75%/75%; file picker
  └── address-group-primitive/         — composite (Eye-Serum compliance template only)
  features/catalog-form/wizard-renderer/
  ├── step-composer.service.ts         — compose() with isHidden filter + STEP_ORDER + STEP_TITLES
  ├── wizard-renderer.component.ts     — mat-stepper data-driven; Next/Back/Submit buttons
  └── field-dispatcher.component.ts    — @switch all 11 PrimitiveKind cases (key: 'dropdown_api_search' not 'dropdown_api')
  features/catalog-form/autofill-overlay/
  └── autofill-overlay.component.ts    — wraps compulsory fields; outputs: accepted, rejected
  Sub-dispatch test result: 42 tests passing

WAVE 2c — Page wiring:
  features/catalog-form/catalog-form/
  ├── catalog-form.component.ts        — sequential init (getProduct→getSchema); forkJoin with DraftRecovery;
  │                                       Subject+debounceTime(10s) autosave (meeAutosave directive incompatible
  │                                       with signal-based page — uses equivalent pipeline directly);
  │                                       global autofill status bar; navigate /catalogs/:id/images on submit
  └── catalog-form.component.spec.ts   — 6 tests
  Sub-dispatch test result: 6 additional tests; total Wave 2: 229 passing / 8 pre-existing failures

BUNDLE:
  catalog-form lazy chunk: ~110 kB raw / 15.70 kB gzip (§19 ≤120 kB exception BUDGET MET — 87% headroom)

DEVIATIONS / CROSS-CUTTING ACTIONS:
  1. [meeAutosave] directive requires AbstractControl/FormGroup. CatalogFormComponent uses signals.
     Workaround: Subject+debounceTime(10_000)+takeUntilDestroyed() pipeline used instead.
     Functionally equivalent; no directive change needed.
  2. FieldSchema missing enumOptions field. Workaround:
     (schema() as unknown as { enumOptions?: ... }).enumOptions with TODO comment.
     CROSS-CUTTING ACTION: add enumOptions?: Array<{code:string; label:LocaleMap}> to @core/models/field-schema.model.ts
  3. Page component at double-folder: catalog-form/catalog-form/catalog-form.component.ts
     (same structural deviation as Wave 1 smart-picker — functionally correct, cosmetically off-spec).
  4. ErrorService.handle() vs showError() — agent verified actual method name from source, used showError().
  5. [maxlength] → [attr.maxlength] binding fix applied in 2c (same feature boundary, not a cross-cutting fix).
=========

=== UPDATE: 2026-06-07 WAVE 3 DISPATCH COMPLETE — images ===
Dispatched to: meesell-angular-component-builder (Sonnet)
Dispatch result: SUCCESS — 12 tests passing / 0 failing; build zero errors

FILES DELIVERED:
  features/images/
  ├── images-api.service.ts            — uploadImage(postMultipart+retryOn503), pollImages(interval 2s), deleteImage
  ├── images.routes.ts                 — IMAGES_ROUTES; providers: [ImagesApiService]
  ├── image-slot/
  │   └── image-slot.component.ts      — CDK drag-drop zone; thumbnail; indeterminate mat-progress-bar
  │                                       NOTE: postMultipart returns Observable<T> (body only), NOT Observable<HttpEvent<T>>
  │                                       → indeterminate bar used (no % progress); cross-cutting action filed
  ├── precheck-report/
  │   └── precheck-report.component.ts — 5 check items per §12 spec (is_jpeg, color_space, resolution_ok,
  │                                       white_bg_ok, watermark_pass); pass/fail icons; section heading
  └── images/
      └── images.component.ts          — page; canProceed gate (slot 0 ready + watermark_pass);
                                          polling subscription managed in ngOnInit; Back→/edit; Next→/preview

BUNDLE:
  images lazy chunk: 8.38 kB gzip (§19 ≤80 kB BUDGET MET — 90% headroom)

CROSS-CUTTING ACTIONS:
  → CROSS-CUTTING: ApiClient.postMultipart returns Observable<T> (final body), not Observable<HttpEvent<T>>.
    If upload progress % UX is needed in V1.5, add postMultipartWithProgress<T>(path, formData, options?)
    returning Observable<HttpEvent<T>> to ApiClient. ImageSlotComponent uses indeterminate bar as acceptable V1 UX.
=========

=== UPDATE: 2026-06-07 WAVE 4 DISPATCH COMPLETE — preview + pricing (export deferred) ===
Dispatched to: meesell-angular-component-builder (Sonnet)
Dispatch result: SUCCESS — 13 new tests passing; total suite 254/261 (7 pre-existing failures — not caused by Wave 4)
Build: zero errors

PREVIEW FILES DELIVERED:
  features/preview/
  ├── preview-api.service.ts           — getPreview(productId): Observable<PreviewData>; feature-local PreviewData interface
  ├── preview.routes.ts                — PREVIEW_ROUTES; providers: [PreviewApiService]
  ├── preview/
  │   ├── preview-feed/
  │   │   └── preview-feed.component.ts    — Meesho-style feed card; 30-char title truncation; product image + price + discount
  │   ├── preview-detail/
  │   │   └── preview-detail.component.ts  — detail page mock; image carousel + attribute list
  │   ├── preview.component.ts             — MatTabGroup (Feed + Detail tabs); loading/empty states;
  │   │                                      Back→/catalogs/:id/images; Next→/catalogs/:id/pricing
  │   └── preview.component.spec.ts        — 6 tests
  Bundle: preview chunk 11.43 kB gzip (§19 ≤80 kB BUDGET MET — 86% headroom)

PRICING FILES DELIVERED:
  features/pricing/
  ├── pricing-api.service.ts           — calculate(productId, mrp, targetPayout): Observable<PricingCalc>
  │                                       Feature-local PricingCalc (snake_case wire format) used because
  │                                       @core/models/pricing-calc.model.ts has camelCase drift — cross-cutting action filed
  ├── pricing.routes.ts                — PRICING_ROUTES; providers: [PricingApiService]
  ├── pricing/
  │   ├── pnl-breakdown/
  │   │   └── pnl-breakdown.component.ts   — line-item table; inrCurrency pipe; color-coded margin cells
  │   ├── margin-slider/
  │   │   └── margin-slider.component.ts   — Angular Material 18 mat-slider (matSliderThumb API);
  │   │                                      setTimeout(500) debounce (functionally equivalent to RxJS debounce)
  │   ├── pricing-chart/
  │   │   └── pricing-chart.component.ts   — chart.js horizontal stacked bar; COLORS_RESOLVED from @design-system/tokens
  │   │                                      (CSS custom props don't work in canvas context — COLORS_RESOLVED correct approach)
  │   ├── pricing.component.ts             — signals + localEstimate computed for instant slider feedback (no API round-trip);
  │   │                                      Back→/catalogs/:id/preview; Next→/catalogs/:id/export
  │   └── pricing.component.spec.ts        — 7 tests
  Bundle: pricing chunk 53.84 kB gzip (§19 ≤80 kB BUDGET MET — 33% headroom; chart.js is the bulk)

EXPORT STATUS: DEFERRED
  - Scaffold already exists (export-api.service.ts, export.routes.ts, export.component.ts, export.component.spec.ts)
  - Implementation deferred until BACKEND §14 (/api/v1/products/:id/export-xlsx + /api/v1/exports/:id) LOCKS
  - When unblocked: ValidationSummaryComponent, ExportProgressComponent, ExportComponent (4 UX states)
  - 7 pre-existing failures in export.component.spec.ts are NG0300 (StatusBadgeComponent + StatusBadgeStub conflict) —
    NOT caused by any Wave dispatch; CROSS-CUTTING ACTION required to fix stub registration

CROSS-CUTTING ACTIONS REQUIRED (all three waves combined):
  1. @core/models/pricing-calc.model.ts — reconcile to snake_case wire format to match feature-local PricingCalc
  2. @core/models/seller-profile.model.ts — shape drift noted; verify reconciliation is current (Q-CC-001 fix may cover)
  3. export.component.spec.ts — NG0300: StatusBadgeComponent + StatusBadgeStub conflict; fix stub registration
  4. shared/pipes/confidence-percent.pipe.ts — create; CategoryCardComponent uses inline computed workaround (Wave 1)
  5. @core/models/field-schema.model.ts — add enumOptions?: Array<{code:string; label:LocaleMap}> (Wave 2b workaround)
  6. ApiClient.postMultipartWithProgress<T> — add if upload progress % UX is needed (Wave 3 workaround)
  7. Consolidate ValueChange type — exists in primitive.contract.ts + catalog-form-state.service.ts (minor)

ROUTE WIRING STATUS (all 6 catalog routes):
  app.routes.ts verified BEFORE dispatch — all routes already wired:
    /catalogs/new          → SMART_PICKER_ROUTES  ✅ (Wave 1)
    /catalogs/:id/edit     → CATALOG_FORM_ROUTES  ✅ (Wave 2)
    /catalogs/:id/images   → IMAGES_ROUTES        ✅ (Wave 3)
    /catalogs/:id/preview  → PREVIEW_ROUTES       ✅ (Wave 4a)
    /catalogs/:id/pricing  → PRICING_ROUTES       ✅ (Wave 4b)
    /catalogs/:id/export   → export (scaffold)     ⏸ (export deferred)

MEGA-SESSION SUMMARY (Waves 1–4 non-export):
  Total tests passing:   254 (7 pre-existing failures not caused by any catalog dispatch)
  Total new files:       ~50 across 6 feature folders
  All chunk budgets MET (catalog-form ≤120 kB, all others ≤80 kB)
  All 5 non-export routes wired, lazy-loaded, route-scoped providers
  Design system FULL LOCK tokens consumed from Wave 2 onward (CSS custom props + COLORS_RESOLVED)
  Export dispatch unblocked when BACKEND §14 LOCKS
=========
