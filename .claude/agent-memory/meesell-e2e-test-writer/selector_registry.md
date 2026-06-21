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

## mfe-export (:4205/:421x) — export  [VERIFIED]
- Generate button (mee-button): `[data-testid="export-trigger"]` →
  `.locator('button').click()`.
- Download link (literal `<a download href>`, ONLY rendered in the `ready` state):
  `[data-testid="export-download"]`.
- NOTE: the provisional `export-download-button`/`export-status` testids do NOT exist.

## mfe-billing (:4202/:421x) — plans  [VERIFIED]
- Upgrade CTA (literal `<button>`, on /billing/plans, one per upgradeable paid tier):
  `[data-testid="upgrade-prompt"]`. For a free user, count ≈ 6 (3 tiers × monthly/
  annual), all visible. This is the plan-guard surface.
