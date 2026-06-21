# Selector registry — stable selectors found via agent-browser

The durable exploration asset. Every `agent-browser` session deposits verified,
stable selectors here, grouped by remote. Read this FIRST every wave and only
explore flows/components NOT yet mapped — each wave gets cheaper than the last.

> STATUS (bootstrap, 2026-06-22): The app currently ships **ZERO `data-testid`
> attributes** (verified across `frontend/apps/`). NOTHING below is verified yet —
> the entries are the PROVISIONAL selector contract that the page objects + flow
> stubs assume. The first exploration phase must (a) confirm which surfaces exist,
> (b) get `data-testid`s added to the components (memo → frontend lead via the
> coordinator), and (c) replace each provisional entry with a LIVE-VERIFIED one.

Port map (local dev): shell `:4200`; mfe-pricing `:4201`, mfe-export `:4202`,
mfe-onboarding `:4203`, mfe-dashboard `:4204`, mfe-catalog `:4205`, mfe-auth
`:4206`, mfe-billing `:4207`.

## Shell (:4200) — routing, navbar/sidebar, auth  [PROVISIONAL]
- Nav home: `[data-testid="nav-home"]`
- Nav catalogs: `[data-testid="nav-catalogs"]`
- Nav categories: `[data-testid="nav-categories"]`
- Nav account: `[data-testid="nav-account"]`
- Logout: `[data-testid="nav-logout"]`
- Remote-load fallback (D12): `[data-testid="remote-failure-fallback"]`

## mfe-auth (:4206) — login / signup / otp-verify  [PROVISIONAL]
- Phone input: `[data-testid="login-phone-input"]`
- Request OTP: `[data-testid="login-request-otp"]`
- OTP input: `[data-testid="otp-input"]`
- Verify submit: `[data-testid="otp-verify-submit"]`

## mfe-dashboard (:4204) — landing + dashboard  [PROVISIONAL]
- Dashboard heading: `[data-testid="dashboard-heading"]`
- Catalog list: `[data-testid="catalog-list"]`
- Catalog card: `[data-testid="catalog-card"]`

## mfe-catalog (:4205) — list / new wizard / images / live  [PROVISIONAL]
- Wizard next / back: `[data-testid="wizard-next"]` / `[data-testid="wizard-back"]`
- Save draft: `[data-testid="save-draft"]`
- Category search: `[data-testid="category-search"]`
- Category suggestion: `[data-testid="category-suggestion"]`
- Image file input: `[data-testid="image-file-input"]`
- Precheck result card / score: `[data-testid="precheck-result-card"]` / `[data-testid="precheck-score"]`

## mfe-export (:4202) — export  [PROVISIONAL]
- Export download button: `[data-testid="export-download-button"]`
- Export status: `[data-testid="export-status"]`
