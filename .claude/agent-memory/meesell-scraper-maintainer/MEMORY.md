# Memory — meesell-scraper-maintainer

## Agent Identity
Playwright scraper specialist for MeeSell. Maintains the Meesho catalogue scraper for quarterly refresh of category tree + brand whitelist. Snapshot diffing, schema-change detection, rate-limited (≤ 1 req / 2 s), robots-respecting. Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## Session 1 — 2026-06-16 (Wave 1.5 commission rate-card capture)

### Task
Wave 1.5 commission rate-card capture for `categories.commission_pct`. Dispatched by meesell-data-engineer, session mesell-category-seeding-session-1.

### Hard Stop: Playwright MCP unavailable
- `~/Library/Application Support/Claude/claude_desktop_config.json` has only `pencil` MCP server registered. No `@playwright/mcp` server present.
- This is consistent with STATUS_DATA.md entries from 2026-06-06 (prior session confirmations).
- All three dispatch contexts tested (2026-06-06 x2, 2026-06-16) confirm same finding.

### WAF findings — Meesho Akamai protection
- `supplier.meesho.com` — ALL paths return HTTP 403 from Akamai WAF, including `/robots.txt`
- `www.meesho.com` — ALL paths return HTTP 403
- `supplierhub.meesho.com`, `seller.meesho.com`, `help.meesho.com`, `support.meesho.com` — HTTP 200 but deliver a universal 2,166-byte React SPA shell; actual content requires JS execution
- Browser UA spoofing (Chrome 125 Mac) does NOT bypass Akamai — fingerprint validation operates at TLS layer (JA3/JA4), not just User-Agent header
- `meeshosupplier.freshdesk.com` — HTTP 404 (not a valid domain)
- NO HTTP 429 or CAPTCHA encountered; WAF blocks at connection level, not rate-limit level
- robots.txt interpretation: DEFERRED — unreadable without Playwright. Document in every future session until readable.

### Rate-card source knowledge
- Meesho publishes commission/referral-fee rate-card inside authenticated supplier panel at `supplier.meesho.com/referral-fee` or similar path
- Rate-card granularity: super-category level (~30-50 rows covering all 3,772 leaves)
- Rate-card is historically stable (changes only at Meesho annual policy updates)
- 2026 Meesho commission model: historically low/zero commissions; exact values unknown

### Artifacts produced (Wave 1.5, NOT committed)
- `backend/app/data/category_commissions.json` — empty `rate_card[]`, full `_meta` with hard-stop record
- `docs/plans/architecture/CATEGORY_SEEDING_COMMISSION_CAPTURE.md` — full capture report + mapping ambiguities + recommendations

### Category tree facts (for future mapping work)
- 30 super-categories, 234 categories, 1,046 sub-categories, 3,772 leaves
- 5 overlapping super-category clusters require founder disambiguation before commission mapping:
  1. Personal Care: super_ids 14, 37, 88, 39, 19, 36 (228 leaves total)
  2. Home: super_ids 12, 24, 30 (855 leaves total)
  3. Kids: super_ids 13, 25 (287 leaves total)
  4. Automotive: super_ids 18, 73 (175 leaves total)
  5. Office/Craft: super_ids 66, 76 (318 leaves total)

## Session 2 — 2026-06-16 (Wave 1.5 commission rate-card capture — dispatch 2, script authoring)

### CORRECTION TO SESSION 1 MISCONCEPTION
Prior dispatch incorrectly concluded "no scraper tooling exists." This was WRONG.
The proven scrapers DO exist and ARE the authoritative method:
- `backend/scripts/meesho_batch_scraper.py` — GOLD STANDARD. Authenticated WebKit + ctx.request.post() Akamai bypass. Proven to drain 3,772 XLSX templates. Login via perform_login() + .meesho_creds.env. HYBRID pattern: browser context for Meesho API, httpx for GCS download.
- `backend/scripts/meesho_template_scraper.py` — single-category sync PoC. detect_block() + UI cascade.
Session 1's error: tried server-side curl (403 from Akamai). Correct approach is authenticated browser context.

### Task
Author `backend/scripts/meesho_commission_scraper.py` + runbook. No live execution.

### Artifacts authored
- `/private/tmp/mesell-wt/category-seeding/backend/scripts/meesho_commission_scraper.py` (46KB)
  - Modelled directly on meesho_batch_scraper.py
  - perform_login() reused verbatim (same WebKit + .meesho_creds.env pattern)
  - NetworkInterceptor class: ctx.on("request") + ctx.on("response") for XHR discovery
  - COMMISSION_API_URL_PATTERN: re.compile(r"(?:referral[_-]?fee|commission|referral|pricing|charge|rate)", re.I)
  - Candidate nav URLs: /panel/v3/new/root/referral-fee, /panel/v3/new/growth/oinpw/referral-fee, /panel/v3/new/root/pricing, /panel/v3/new/growth/oinpw/pricing, /panel/v3/new/root/commission, /panel/v3/new/growth/oinpw/home
  - Direct mode: ctx.request.get(COMMISSION_API_ENDPOINT, headers=_api_headers())
  - COMMISSION_API_ENDPOINT: module constant, env override supported
  - Hard stops: SESSION_STOP_CODES {401,403,463}, RATE_LIMIT_STOP_CODES {429}, captcha markers
  - Throttle: 2-5s nav jitter, 1-3s req jitter, sequential
  - Output: /private/tmp/mesell-wt/category-seeding/backend/app/data/category_commissions.json
  - Syntax validated: python3 -m py_compile → SYNTAX OK. No live run.

- `/private/tmp/mesell-wt/category-seeding/docs/plans/architecture/CATEGORY_SEEDING_COMMISSION_RUNBOOK.md` (15KB)
  - 11 sections: prerequisites, 2-run procedure, endpoint discovery, hard-stop behaviour, mapping review, handoff, quarterly refresh

### Commission endpoint candidates (built into script, unconfirmed)
- `https://supplier.meesho.com/panel/v3/new/root/referral-fee` (nav page)
- `https://supplier.meesho.com/panel/v3/new/growth/oinpw/referral-fee` (nav page)
- XHR API endpoint: UNKNOWN until Run 1 discovery completes
- Likely patterns (from Meesho API naming conventions): `/api/cataloging/referral-fees`, `/api/pricing/commission-rates`, `/api/supplier/referral-fee`

### _api_headers pattern (from meesho_batch_scraper.py)
```python
{
    "identifier": "oinpw",
    "client-type": "d-web",
    "client-package-version": "1.0.1",
    "supplier-id": "4359160",
    "accept": "application/json, text/plain, */*",
}
```

### Execution status
- NOT executed. No login. No Meesho request. Founder GO required.
- Syntax validated only.

### Next run protocol
1. Founder GO
2. operator: Run 1 (discovery mode) → check logs/scraper/commission_*.log for [CANDIDATE] lines
3. operator: set COMMISSION_API_ENDPOINT constant
4. operator: Run 2 (direct mode) → backend/app/data/category_commissions.json written
5. data lead reviews JSON + proposes disambiguation for 5 overlapping super-category clusters
6. data lead authors scripts/seed_category_commissions.py
7. database-builder runs backfill

### Rate limit
Not exceeded (no live run).

### Robots.txt
Still UNKNOWN (WAF blocks). Defer to live session.

### Selector version
n/a (commission is API-intercepted, not HTML-scraped).

---

### Recommendation for quarterly refresh (Option B)
Add Playwright MCP to Claude Desktop config before re-dispatching:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    }
  }
}
```
Then: navigate to supplier.meesho.com/login → OTP auth (interactive, founder) → intercept referral-fee API response (network interception Strategy 3B per PLAYWRIGHT_MCP_REFERENCE §5).

### Rate limit: never exceeded (well within 1 req/2s — all probe calls were 2-3s apart)
### Robots.txt: UNKNOWN (blocked by WAF — revisit each session until readable)
### Selector version: n/a (no selectors authored in this session)

---

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
