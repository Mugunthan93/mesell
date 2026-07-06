# Selector registry — stable selectors found via agent-browser / Playwright

The durable exploration asset. Every live exploration deposits verified, stable
selectors here, grouped by remote. Read this FIRST every wave and only explore
flows/components NOT yet mapped — each wave gets cheaper than the last.

> STATUS (QA Wave 1 — VERIFIED LIVE 2026-06-22, slot-1 shell :4210 against develop
> tip d13ed50 with #381 testids). All entries below are LIVE-VERIFIED via Playwright
> against the running federated stack. The data-testids landed in #381 (commit
> 456494e): part 2a added a `[testId]` signal-input passthrough to 5 ui-kit wrappers;
> part 2b placed literal `data-testid`s + `[testId]` bindings across the remotes.

Port map (local dev BASELINE slot-0): shell `:4200`; remotes are ALPHABETICAL not
manifest-order — mfe-auth `:4201`, mfe-billing `:4202`, mfe-catalog `:4203`,
mfe-dashboard `:4204`, mfe-export `:4205`, mfe-onboarding `:4206`, mfe-pricing
`:4207`; backend `:8000`. A port-isolated slot N (meesell_env.py) is shell
`4200+N*10`, remotes `420(1..7)+N*10`. ALL app traffic goes through the shell
(`/api` reverse-proxied to the backend) — Playwright only needs the SHELL url.

## ui-kit wrapper testid placement — THE CRITICAL INTERACTION RULE
The `[testId]` passthrough lands on DIFFERENT inner elements per wrapper. Get this
wrong and `getByTestId(x)` resolves to a non-interactable host:
- **mee-input**  → `[attr.data-testid]` on the inner `<input pInputText>`. The
  testid'd element IS the input → `getByTestId(x).fill(value)` DIRECTLY (NO
  `.locator('input')`).
- **mee-textarea** → on the inner `<textarea>`. → `getByTestId(x).fill(value)` directly.
- **mee-button** → on the `<p-button>` HOST wrapper, NOT the inner `<button>`. The
  PrimeNG `(onClick)` only fires from the real `<button>` → click
  `getByTestId(x).locator('button').click()` (clicking the p-button host can miss).
- **mee-otp-input** → on the `<p-inputotp>` wrapper. The 6 cells are inner inputs →
  `getByTestId('otp-input').locator('input').nth(i).fill(digit)` for i in 0..5.
- **literal `data-testid=`** (dashboard-heading, nav-*, category-suggestion,
  precheck-card, precheck-status, export-download, upgrade-prompt, image-file-input,
  login-google-host, user-menu-trigger) → the element itself.

## Shell (:4200) — topbar + sidebar + remote fallback  [VERIFIED]
- Topbar logout (DIRECT button, #381 restructured it OUT of the popup menu):
  `[data-testid="nav-logout"]` — `getByTestId('nav-logout').click()`.
- Topbar user-menu trigger (opens the My-Profile popup): `[data-testid="user-menu-trigger"]`.
- Sidebar nav items (DESKTOP sidebar only; render at viewport ≥ ~640px; each is an
  `<a routerLink>` with `[attr.data-testid]="item.testId"`):
  `nav-home` (/dashboard), `nav-catalogs` (/catalogs), `nav-new-product`
  (/catalogs/new), `nav-categories` (/categories/browse), `nav-profile` (/profile),
  `nav-plans` (/billing/plans). (Source: sidebar.nav-groups.ts.)
- Remote-load fallback (D12 RemoteFailureComponent): `[data-testid="remote-failure-fallback"]`.
- NOTE: there is NO `nav-account` (the provisional registry was wrong → it's `nav-profile`).

## mfe-auth (:4201 baseline / :421x slot) — login / otp-verify  [VERIFIED]
- Phone input (mee-input): `[data-testid="login-phone-input"]` → fill the **10-digit**
  number ONLY (validator `/^[6-9]\d{9}$/`; the `+91` is a display prefix; the
  component prepends `+91` before POST). Filling `+91…` leaves the form INVALID and
  the request button DISABLED.
- Request-OTP button (mee-button): `[data-testid="login-request-otp"]` →
  `.locator('button').click()`. On success navigates to `/otp-verify` with `{phone}`
  in router state.
- Google host div: `[data-testid="login-google-host"]` (GIS renders an iframe button
  INTO this div; not headlessly clickable — see google-signin flow).
- OTP input (mee-otp-input): `[data-testid="otp-input"]` → 6 inner cells; fill each.
- Verify button (mee-button): `[data-testid="otp-verify-submit"]` → `.locator('button').click()`.
- signup page exists at `/signup` (not used by flows).

## mfe-onboarding (:4206/:421x) — onboarding + profile  [VERIFIED]
- Business name (mee-input): `[data-testid="onboarding-business-name"]` → fill directly.
  (City defaults to "Tirupur" and is pre-valid; GST optional → only business name needed.)
- Submit button (mee-button): `[data-testid="onboarding-submit"]` → `.locator('button').click()`.
- IMPORTANT product reality: onboarding `onSubmit()` is a MOCK `setTimeout(1500)` →
  `router.navigate(['/dashboard'])`. It does NOT call any API and does NOT persist
  `onboarding_complete`. So a fresh OTP user ALWAYS lands on /onboarding (because
  /auth/me.onboarding_complete stays false), fills the form, and is routed to
  /dashboard purely client-side.

## mfe-dashboard (:4204/:421x) — landing + dashboard  [VERIFIED]
- Dashboard heading (mee-page-header, title "Home"): `[data-testid="dashboard-heading"]`.
- Empty state: `[data-testid="dashboard-empty-state"]`.
- Product row: `[data-testid="dashboard-product-row"]` (one per catalog/product).
- NOTE: the provisional `catalog-list` / `catalog-card` testids do NOT exist —
  use `dashboard-product-row` / `dashboard-empty-state`.

## mfe-catalog (:4203/:421x) — smart-picker / images / form  [VERIFIED]
- Smart-picker description (mee-textarea, /catalogs/new):
  `[data-testid="smart-picker-description"]` → fill directly (10–500 chars). Triggers
  a 400ms-debounced POST /categories/suggest (Gemini-backed — takes SEVERAL seconds;
  wait up to ~25s for suggestions to render).
- Category suggestion card (literal, in CategoryCardComponent):
  `[data-testid="category-suggestion"]` (top-3 rendered).
- "Use this category" button (mee-button): `[data-testid="category-suggestion-select"]`
  → `.first().locator('button').click()`. This POSTs to create a product then
  navigates to `/catalogs/{REAL-UUID}/edit` — THIS is how you get a real productId.
- AI-fill button (mee-button, on edit form): `[data-testid="catalog-ai-fill"]`.
- Form next button (mee-button): `[data-testid="catalog-form-next"]`.
- Save status (literal, on edit form): `[data-testid="catalog-save-status"]`.
- Image file input (literal): `[data-testid="image-file-input"]` — this is the HIDDEN
  re-upload input (display:none, aria-hidden), used ONLY for per-slot re-upload AFTER
  a slot exists. The PRIMARY upload is via `<mee-file-upload>` → `<p-fileupload
  mode="advanced" [customUpload]>` which renders its OWN native input + a "Choose"/
  "Upload"/"Cancel" button row (no testid on the primary input). Drive it with
  `page.locator('p-fileupload input[type=file]').first().setInputFiles(jpg)` then
  click the `Upload` button (`p-fileupload >> getByRole('button',{name:/^upload$/i})`).
- Precheck result card (literal, mee-card per slot): `[data-testid="precheck-card"]`.
- Precheck status badge (literal, mee-status-badge): `[data-testid="precheck-status"]`
  (text is "ready"/"failed"/"pending" — there is NO numeric "precheck-score" testid;
  the provisional `precheck-score` does NOT exist).
- categories browse page exposed at /categories/browse.

### Wave-3 RE-VERIFIED LIVE (develop @ a94e013, agent-browser, baseline shell :4200)
- `catalog-save-status` host is ALWAYS present on `/catalogs/:id/edit` — its TEXT
  switches idle('' empty) -> "Saving…" -> "Saved" -> error. ASSERT THE "Saved" TEXT,
  NOT mere visibility (visibility alone is not a save proof; the host never hides).
  Used by W3-E2-1 `flows/wizard-save.spec.ts`.
- `catalog-form-next` (mee-button -> inner `<button>`) — RE-VERIFIED present on edit form.
- `catalog-ai-fill` (mee-button -> inner `<button>`) — RE-VERIFIED present on edit form
  (page-object helper `CatalogPage.aiFill`).
- EDIT A SCHEMA-DRIVEN FIELD (no per-field testid): category-schema fields render inside
  `mee-input` / `mee-textarea` wrappers. Target the first editable field with the
  STRUCTURAL selector `mee-input input, mee-textarea textarea`
  (`CatalogPage.firstEditableField`). Callers MUST guard on `.count()` before
  interacting — when the dev backend has not populated the field schema the accordion
  shows "Compulsory (0)" and there are NONE. Only non-testid selector in the Wave-3
  codified path (structural fallback; schema fields carry no stable testid).

### Wave-3 CONFIRMED-ABSENT (do NOT invent — verified live + grep on develop @ a94e013)
- LIVE PREVIEW PAGE IS RETIRED (#278). No `/catalogs/:id/preview` route, no preview
  component. catalog-list "Preview" button repointed to `/edit` (#395). No frontend
  preview surface -> W3-E2-2 is `test.fixme`. Backend `GET /products/{id}/preview` still
  exists (BE lane covers it). Un-fixme ONLY if a frontend preview page is reintroduced.
- catalog-list has NO per-row data-testid and NO delete control. List renders per-product
  cards with "Edit" + "Preview" mee-buttons ONLY (grep: zero delete|remove|trash); cards/
  buttons carry no testid/[testId] -> W3-E2-4 is `test.fixme`. Un-fixme when the list
  gains a delete control + per-row testids (e.g. catalog-list-row / catalog-list-delete),
  LIVE-VERIFIED.
- mfe-pricing has NO data-testid and NO apply-price control. `pricing.component.ts` has a
  "Calculate" mee-button (no testid) + a read-only P&L breakdown; no apply button ->
  W3-E2-6 is `test.fixme`. Un-fixme when pricing gains testids on calc + result + an apply
  control, LIVE-VERIFIED.
- The real export download selector is `export-download` (NOT `export-download-button`).
  Literal `<a download href>` rendered ONLY in the `ready` state; trigger is
  `export-trigger`. (`export-download-button` / `export-status` do NOT exist.)

## mfe-export (:4205/:421x) — export  [VERIFIED]
- Generate button (mee-button): `[data-testid="export-trigger"]` →
  `.locator('button').click()`.
- Download link (literal `<a download href>`, ONLY rendered in the `ready` state):
  `[data-testid="export-download"]`.
- NOTE: the provisional `export-download-button`/`export-status` testids do NOT exist.
- RECONCILE (QA Wave C, qa-pricing 2026-06-22): the brief asked to reconcile
  `export-download-button` vs `export-download`. CONFIRMED LIVE: the real anchor is
  `data-testid="export-download"` (a literal `<a download href>`); `export-download-btn`
  is only a CSS class. The ExportPage page object (`downloadLink` → `export-download`)
  is ALREADY correct — no change needed.
- PRODUCTID BUG FIXED (was the Wave-1 `test.fixme` reason): `export.component.ts`
  `onGenerate()` now calls `resolveExportProductId(this.route.snapshot.paramMap)` (line
  ~425). VERIFIED LIVE: clicking `export-trigger` on `/catalogs/{realPid}/export` POSTs
  to `/api/v1/products/{realPid}/export-xlsx` (the REAL UUID, NOT the old
  `current-product-id` placeholder). For a DRAFT product the backend returns 422 with a
  real "Your product isn't ready…/A front image is required" validation message rendered
  in the LEFT panel checklist (`<ul aria-label="Items to resolve before export">` → `<li>`
  items; the not-ready copy ALSO surfaces via `notReadyMessage()`). NO `data-testid` on
  these list items → assert by visible text (e.g. `getByText(/isn't ready/i)`).
- The `ready` state + the `export-download` link remain UNREACHABLE in LOCAL dev — NOT
  the placeholder bug anymore, but (a) no DRAFT product is `ready` (needs all fields +
  a front image) and (b) the `ready`→signed-URL path needs GCS, which 502s in local dev
  (no creds). So the actual file-download stays `test.fixme` with the UPDATED reason.

## mfe-pricing (:4207 baseline alphabetical / :421x slot) — price-calc  [VERIFIED 2026-06-22 QA Wave C]
> LIVE-VERIFIED against the running federated stack with the integration-tip mfe-pricing
> build (#439 testids: 3 `[testId]` passthroughs + 4 literal `data-testid`s), shell routed
> to `catalogs/:id/pricing`. The remote LOADS (remote-failure-fallback count 0).
- Selling-price input (mee-input → `[testId]` passthrough lands on the inner `<input>`):
  `[data-testid="pricing-cost-input"]` → `getByTestId('pricing-cost-input').fill(value)`
  DIRECTLY (NO `.locator('input')`).
- Commission % input (mee-input, optional override): `[data-testid="pricing-commission-input"]`
  → fill directly. Omit (leave blank) for the default-0% path.
- Calculate button (mee-button → `[testId]` on the `<p-button>` host):
  `[data-testid="pricing-calculate-btn"]` → `.locator('button').click()`. Disabled while
  the form is invalid (no selling price) or a calc is in-flight.
- Result region (literal, ALWAYS present on load — it is the `#resultRegion` container):
  `[data-testid="pricing-breakdown"]`. Populated with the 5-row settlement table AFTER a
  successful calc.
- Headline settlement value (literal, the "Estimated Bank Settlement" row value, rendered
  ONLY after a successful calc): `[data-testid="pricing-settlement-value"]`. LIVE: cost
  70 → `₹57.62`; cost 1 → `₹-11.31` (negative, server-authoritative).
- Disclaimer (literal `<p>`, server-sent text, rendered ONLY after a successful calc):
  `[data-testid="pricing-disclaimer"]`. LIVE text: "Bank settlement amount may vary
  slightly based on the quantity in the order, Meesho commission policy at the time of
  the order and the actual…".
- NEGATIVE_SETTLEMENT alert (literal, rendered ONLY when settlement < 0):
  `[data-testid="pricing-negative-alert"]`. LIVE: appears for cost 1 (settlement ₹-11.31),
  text "This selling price results in a negative settlement — the fees exceed your price.".
  For a positive calc its count is 0 (NOT rendered) — assert `count()===0` / not-visible.
- RENDER ORDER on load: cost-input + commission-input + calculate-btn + breakdown region
  are present immediately; settlement-value + disclaimer appear post-calc; negative-alert
  only on a negative settlement.
- DATA DEPENDENCY: price-calc 200 requires the product's category leaf to have a pricing
  lookup row. A category picked via the smart-picker (a census leaf) HAS one (LIVE: a real
  product calc'd ₹57.62). A category with no lookup row → 422 `pricing.category.no_pricing_data`
  (no settlement renders).

## mfe-billing (:4202/:421x) — plans  [VERIFIED]
- Upgrade CTA (literal `<button>`, on /billing/plans, one per upgradeable paid tier):
  `[data-testid="upgrade-prompt"]`. For a free user, count ≈ 6 (3 tiers × monthly/
  annual), all visible. This is the plan-guard surface.

## qa-catalog Wave C (e2e) — catalog selectors (2026-06-22) [SCRIBED BY QA-COORD, write-protection workaround per #387]
> The e2e-test-writer's slot-2 stack was torn down by an external event; the Wave-C
> live exploration was ENVIRONMENT-BLOCKED (8GB-box swap ceiling refused `meesell_env up`).
> The picker/edit selectors below were RE-CONFIRMED from SOURCE on
> `feature/qa-catalog/integration` @ `3476b0e`; the gate independently re-ran
> `playwright test --list` (CLEAN, 19/9). The two browse-fallback/empty-state selectors
> are SOURCE-DERIVED, NOT yet agent-browser live-verified → their flows are `test.fixme`.

### LIVE-VERIFIED (registry, source-confirmed @ 3476b0e) — used by CAT-E2E-04 GREEN guard
- Smart-picker description (mee-textarea): `[data-testid="smart-picker-description"]`
  (smart-picker.component.ts L145) → fill directly.
- Category suggestion card (literal): `[data-testid="category-suggestion"]`
  (category-card.component.ts L43). `category-suggestion-select` CTA = L76 `[testId]`.
- AI-fill button: `[data-testid="catalog-ai-fill"]` → `.locator('button')` (CAT-E2E-06).
- Save status: `[data-testid="catalog-save-status"]` → `toHaveText(/saved/i)` (CAT-E2E-05).
- Schema-driven edit fields ship NO testid → structural fallback
  `mee-input input[type="text"]` (first fillable) / `mee-input input, mee-textarea textarea`
  (filled-count). Same structural pattern as Wave-3.

### SOURCE-DERIVED, NOT yet live-verified (CAT-E2E-03/07 are test.fixme until verified)
- Browse-fallback link (under cards when `fallback_offered=true` AND results):
  `getByRole('button', { name: /browse all categories if none of the suggestions match/i })`
  — source: `<button class="mee-browse-link">` with that aria-label. NO data-testid.
- Picker empty-state (when `fallback_offered=true` AND zero suggestions):
  `getByRole('status', { name: /no automatic suggestions found/i })`
  — source: `<mee-empty-state role="status">`. NO data-testid.
- Empty-state CTA: `getByRole('button', { name: /^browse all categories$/i })`. NO data-testid.
- → HAND-OFF filed → frontend-coordinator: add `data-testid` so CAT-E2E-03/07 can be un-fixme'd.

## gis-stub-button (test-injected, #483)
- `gis-stub-button` — test-injected (not an app testid) by `AuthPage.installGisStub()`; drives the GIS callback with the dev-bypass sentinel.

## qa-pricing e2e lane completion (2026-07-06) — SUPERSEDES two CONFIRMED-ABSENT entries above [SCRIBED BY QA-COORD, isolated-writer scribe]
> The commit `1794da3` (direct-to-develop pipeline) de-fixme'd W3-E2-4 + W3-E2-6 and authored
> PQE-E2E-04/04b. Source-ground-truthed @ develop `c5529f6`; the pricing apply trio was
> LIVE-VERIFIED on the DEPLOYED build (GH-Pages + Fly) 2026-07-06. These entries SUPERSEDE the
> stale "mfe-pricing has NO apply-price control" + "catalog-list has NO delete control" lines in
> the Wave-3 CONFIRMED-ABSENT block (both resolved by #439/SPEC-C and #425 respectively).

### mfe-pricing apply-price trio — NATIVE elements (testid IS the element; NO `.locator('button')`)
Federation strips `[testId]` on `mee-*` wrappers, so these three were placed on NATIVE DOM
elements with a LITERAL `data-testid` (source comment pricing.component.ts L666-675; verified L682/L705/L718 @ `c5529f6`). This differs from the calc trio (`pricing-cost-input`/`-commission-input` are `[testId]` passthroughs on `mee-input`; `pricing-calculate-btn` is `[testId]` on the `mee-button` host → `.locator('button')`).
- `[data-testid="pricing-apply-btn"]` — IS the native `<button>` ("Save & Continue"). Click DIRECTLY (`getByTestId('pricing-apply-btn').click()`, NO `.locator('button')`). `[disabled]="!breakdown() || appliedStatus()==='applying'"` → DISABLED on load; enables ONLY after a successful calc → assert `toBeEnabled()` AFTER calc, then click. On the 204 `onSaveContinue()` navigates to `/catalogs/:id/export`.
- `[data-testid="pricing-applied-status"]` — native `<span>` ("Price applied"), rendered ONLY after the apply POST returns 204, and MAY unmount as the flow navigates to export. Count 0 on load. Do NOT anchor a nav test on it — assert the EXPORT URL + `ExportPage.generateButton` instead (the robust visible outcome).
- `[data-testid="pricing-apply-error"]` — native `<span>` ("Could not apply price…"), rendered ONLY when the apply POST errors (`appliedStatus()==='error'`). Count 0 on load. Force it by `page.route('**/apply-price', r => r.fulfill({status:500}))` set AFTER a real calc (keeps the breakdown genuine — no green-wash).

### mfe-catalog catalog-list rows + inline delete (#425 testids, `77b5db0`)
`catalog-empty` LIVE-VERIFIED on the DEPLOYED build 2026-07-06; the per-row controls are SOURCE-ground-truthed @ `c5529f6` (a live row could not render on deployed — product-creation is down there, see federation_quirks).
- `[data-testid="catalog-row"]` — one `<div>` per product; carries `[attr.data-product-id]="cat.id"`. Anchor a specific row by `[data-testid="catalog-row"][data-product-id="${id}"]` (page object `CatalogPage.rowFor(id)`).
- `[data-testid="catalog-empty"]` — empty-state `<div>` when there are no catalogs.
- `catalog-edit-btn` / `catalog-delete-btn` / `catalog-delete-confirm` / `catalog-delete-cancel` — each is a `<span data-testid>` WRAPPING a `<mee-button>` → click the inner `<button>` (`.getByTestId(x).locator('button')`; page-object helpers `editButtonIn/deleteButtonIn/deleteConfirmIn/deleteCancelIn(row)`). Delete UX is an INLINE confirm (no dialog): `catalog-delete-btn` → swaps the row to a "Delete this catalog?" affordance → `catalog-delete-confirm` → DELETE `/products/{id}` → row removed. Assert `rowFor(id).toHaveCount(0)`.

### auth — OTP send path (harness note)
The OTP send endpoint is `POST /auth/otp/send`; the dev bypass code `000000` only matches AFTER a send has SEEDED the OTP for that phone (the bypass is validated against a seeded record, not accepted unconditionally). So a login must POST `/auth/otp/send` first, then verify with `otp:'000000'`. (Rate limit: 3 sends / 3600s per IP — see federation_quirks; the worker-scoped fixture logs in ONCE per worker.)
