# STATUS — FEATURE CATALOG (MEGA-SESSION)

**Owner:** Catalog Sub-Session (session-as-role)
**Master:** `meesell-frontend-coordinator` session
**Bootstrap prompt:** `docs/SESSION_PROMPTS_FEATURE_CATALOG.md` (paired with `docs/SESSION_PROMPTS_FEATURE_BASE.md`)
**Code root:** `frontend/src/app/features/smart-picker/` + `catalog-form/` + `images/` + `preview/` + `pricing/` + `export/`
**Routes owned:** `/catalogs/new`, `/catalogs/:id/edit`, `/catalogs/:id/images`, `/catalogs/:id/preview`, `/catalogs/:id/pricing`, `/catalogs/:id/export`
**MF-remote target (Phase 2):** catalog-mfe per FE-D13
**Special note:** THIS IS THE MEGA-SESSION. 6 feature folders, ~20+ components, 11 form primitives, ~14 endpoints. All routes share the same `productId` state context — the single biggest cohesion driver in V1.
**Created:** 2026-06-06 by frontend coordinator per FE-D12 amended grouping
**Last update:** 2026-06-06 (BOOTSTRAPPED — read pass complete; Wave 1 dispatch armed)

**Status:** BOOTSTRAPPED — 9 mandatory + targeted backend/MVP reads complete; THE SPINE contract internalised; wave plan locked; awaiting first build dispatch.

## Current Phase

**Wave 0 — Bootstrap complete. Wave 1 dispatch (smart-picker) armed and unblocked.**

## Done

- All 9 mandatory reads complete + targeted backend §10 + MVP §5 supplementary reads (see Updates Log).
- 11-primitive contract reconciled (FRONTEND §18.E supersedes MEESHO_CAT_INT §4 ambiguity — `address_group` is the 11th primitive scoped to catalog-form for Eye-Serum collapsed-compliance template, 1 of 3,772 leaves).
- Bootstrap wave plan locked: smart-picker → catalog-form (SPINE) → images → preview/pricing/export (parallel).
- Discrepancies + Q&A entries surfaced (see bottom sections).

## In Progress

- _(none — handed back to founder/master; awaiting Wave 1 dispatch authorisation per master cadence)_

## Blockers

- **Backend §14 export DRAFT** — defers Wave 4 export sub-feature only. Waves 1-3 + Wave 4 preview/pricing are unblocked.
- **Design system §5A PARTIAL LOCK (FE-D9 / FE-D10)** — placeholder hex/typeface values from coordinator best-guess; component-builder dispatch IS UNBLOCKED per FE-D9 because components consume CSS custom properties whose values land later. ui-styler restyle pass deferred until §5A FULL LOCK.
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
