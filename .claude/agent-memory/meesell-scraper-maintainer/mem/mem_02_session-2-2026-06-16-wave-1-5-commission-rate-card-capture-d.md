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
