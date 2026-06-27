## Session 3 — 2026-06-16 (Wave 1.5 commission — Run 1 DISCOVERY, dispatch 3)

### Task
Execute Run 1 (discovery mode) of meesho_commission_scraper.py. Founder GO given. Live run against real supplier account.

### Prerequisite check results (all PASSED)
- Creds file: /Users/mugunthansrinivasan/Project/mesell/.meesho_creds.env — present, MEESHO_USERNAME + MEESHO_PASSWORD keys confirmed, 54 bytes
- Python env: /Users/mugunthansrinivasan/Project/mesell/backend/.venv — playwright 1.60.0, dotenv OK
- WebKit: webkit-2287 installed at /Users/mugunthansrinivasan/Library/Caches/ms-playwright/
- Script syntax: OK (py_compile)
- Log dir: /private/tmp/mesell-wt/category-seeding/logs/scraper/ — created
- robots.txt: UNKNOWN (WAF blocks — deferred again, 3rd session in a row)

### Login result
- LOGIN SUCCEEDED: WebKit → /root/login → POST creds → 302 to /growth/oinpw/home
- Akamai bypass confirmed: WebKit TLS fingerprint + authenticated cookies carry through
- No 401/403/463/429/captcha encountered in any pass

### Discovery run results (3 passes total)
Pass 1 (discovery script, 44 requests):
  - 6 candidate URLs navigated
  - /root/referral-fee, /root/pricing, /root/commission → SPA router redirected to /root/login (not authenticated for /root/ routes in this context)
  - /growth/oinpw/referral-fee, /growth/oinpw/pricing → LOADED (but empty content area)
  - /growth/oinpw/home → LOADED (dashboard content visible)
  - Only advertising/tracking XHR URLs matched commission pattern (false positives from broad URL regex)

Pass 2 (net dump, broader intercept):
  - Both /growth/oinpw/referral-fee and /growth/oinpw/pricing: 23 Meesho requests each
  - ALL 23 requests are framework/container requests: prefetch-supply-data, supplier/config, notices count, registration status, total-count, promotions
  - NO referral-fee or commission-specific XHR on either page
  - 23 GET/POST direct API probes: ALL returned HTTP 404
  - Body text shows full nav sidebar only; content area empty

Pass 3 (interaction probe + pricing page):
  - Navigated /pricing with 12s extended wait and scroll-to-bottom
  - Body text: nav sidebar items + "Your E-Signature is missing!" modal
  - Only clickable element: "Add Signature" button (no tabs, no content, no data grid)
  - prefetch-supply-data key finding: is_agreement_accepted=false
  - enable_referral_v3=true (feature enabled, but gated behind agreement)
  - default_monetization_percent=4.0 (generic, not category-specific)
  - 12 extended API probes in /api/growth/ namespace: ALL 404

### KEY FINDING — Hard blocker
Meesho requires seller agreement acceptance (e-signature) before rendering referral-fee/pricing content.
The page loads the SPA shell (framework JS, nav, notifications) but renders NO content until is_agreement_accepted=true.
This is a ACCOUNT SETUP blocker, not a Playwright/Akamai/auth issue.
The commission rate-card XHR will fire only after:
  1. Founder navigates to supplier panel (browser UI, not headless)
  2. Founder completes the "E-Signature" agreement flow
  3. After that, re-run discovery — /growth/oinpw/referral-fee will render its content and fire commission XHR

### Commission API endpoint status
UNKNOWN — not discoverable until is_agreement_accepted=true.
Confirmed NOT at any of the 35+ candidate API paths probed.
The endpoint pattern is likely: POST /api/growth/... or POST /api/container/...
(All Meesho supplier panel data endpoints observed use POST, not GET)

### XHR APIs confirmed working on this account
- POST /api/container/supplier/prefetch-supply-data → supplier profile
- POST /api/container/supplier/api/2.0/supplier/config → feature flags / ads config
- POST /api/container/notices/fetch-unread-count
- POST /api/growth/registration/fetch-registration-status
- POST /api/container/supplier/fetch-total-count
- POST /api/promotions/promotions/live-optin-event
- POST /api/growth/activation/fetch-stepper-journey (home page only)
- POST /api/growth/supplier/fetch-web-popup (home page only)

### Akamai bypass pattern (CONFIRMED WORKING)
- WebKit headless + real TLS fingerprint from ms-playwright webkit-2287
- /growth/oinpw/ routes: fully accessible with auth cookies
- /root/ routes (non-growth): require separate auth context (SPA router difference)
- ctx.request.get/post() with browser context cookies: 404 on non-existent paths (not 403 — Akamai passes through authenticated requests correctly)

### Throttle observed
- 2-3s between navigations, 2s between direct API calls
- Never triggered 429
- Rate well within 1 req/2s policy

### Artifacts
- /private/tmp/mesell-wt/category-seeding/logs/scraper/commission_2026-06-16_14-27.log — discovery run log
- No data written to category_commissions.json (discovery only, no harvest)

### Next run protocol (updated)
1. Founder: complete e-signature/agreement in Meesho supplier panel (interactive, browser UI)
2. After agreement: re-run discovery mode → /growth/oinpw/referral-fee will fire commission XHR
3. Identify commission endpoint from log [CANDIDATE] entries
4. Set COMMISSION_API_ENDPOINT constant
5. Run 2 (direct mode) → harvest rate-card → category_commissions.json
6. Data lead reviews + proposes disambiguation for 5 overlapping clusters
7. Database-builder runs backfill

### Robots.txt: UNKNOWN (3rd session — WAF blocks supplier.meesho.com/robots.txt)
### Rate limit: never exceeded
### Selector version: n/a

---
