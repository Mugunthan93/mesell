# Commission Rate-Card Capture Runbook

| Field | Value |
|---|---|
| Document type | Operator runbook |
| Script | `backend/scripts/meesho_commission_scraper.py` |
| Author | `meesell-scraper-maintainer` (sonnet) |
| Dispatched by | `meesell-data-engineer`, session `mesell-category-seeding-session-2` |
| Date | 2026-06-16 |
| Worktree | `/private/tmp/mesell-wt/category-seeding` |
| Branch | `feature/category-seeding` |
| Prerequisite documents | `CATEGORY_SEEDING_ARCHITECTURE.md §9 Q2`, `CATEGORY_SEEDING_COMMISSION_CAPTURE.md` |

---

## §1 Purpose

This runbook covers the two-run operator procedure for capturing Meesho's category-wise commission (referral-fee) rate-card into `backend/app/data/category_commissions.json`. This feeds `categories.commission_pct` per founder decision D2.

The script uses the proven Playwright + WebKit + authenticated BrowserContext pattern from `meesho_batch_scraper.py`. It does NOT use curl or plain httpx — those are blocked by Akamai (HTTP 403/463). Akamai passes only requests that carry a valid TLS fingerprint from a real browser session.

The capture requires two runs:

- **Run 1 (discovery mode):** logs all intercepted XHR/fetch requests matching commission/fee/rate URL patterns so the operator can identify the correct API endpoint.
- **Run 2 (direct mode):** uses the identified endpoint to fetch and parse the commission JSON, propose a leaf mapping, and write the output file.

Both runs require the founder's Meesho supplier credentials and an active internet connection. Neither run commits anything — the data lead stages after review.

---

## §2 Prerequisites

### 2.1 Credentials file

The script reads `MEESHO_USERNAME` and `MEESHO_PASSWORD` from a `.env` file. The default path is:

```
~/Project/mesell/.meesho_creds.env
```

Create it if it does not exist (mode 600 — owner-read-only):

```bash
touch ~/Project/mesell/.meesho_creds.env
chmod 600 ~/Project/mesell/.meesho_creds.env
```

Edit it with:

```
MEESHO_USERNAME=<founder phone number or email>
MEESHO_PASSWORD=<supplier panel password>
```

NEVER commit this file. It is `.gitignore`d. NEVER log credentials.

To use a different path:

```bash
export MEESHO_CREDS_FILE=/path/to/other.env
```

### 2.2 Python virtual environment

The script requires `playwright` and `python-dotenv`. Align with the existing scraper environment used for `meesho_batch_scraper.py`:

```bash
cd /private/tmp/mesell-wt/category-seeding

# If a venv already exists for the batch scraper, activate it:
source .venv/bin/activate   # or wherever the project venv lives

# If starting fresh:
python3 -m venv .venv
source .venv/bin/activate
pip install playwright python-dotenv
playwright install webkit
```

Verify installation:

```bash
python -c "from playwright.async_api import async_playwright; print('playwright ok')"
```

### 2.3 Network access

The script connects to:
- `supplier.meesho.com` — login + panel navigation
- `*.meesho.com` — commission API endpoint (once discovered)

No proxy is required. No VPN is required. The browser context handles Akamai fingerprint matching automatically.

### 2.4 Working directory

All commands in this runbook are run from the worktree root:

```bash
cd /private/tmp/mesell-wt/category-seeding
```

---

## §3 Run 1: Discovery Mode

### 3.1 Purpose

Identify the correct commission/referral-fee API endpoint by navigating candidate pages and intercepting all outbound XHR/fetch requests matching `/referral|commission|fee|charge|rate|pricing/i`.

### 3.2 Command

```bash
cd /private/tmp/mesell-wt/category-seeding
python backend/scripts/meesho_commission_scraper.py
```

No environment overrides needed for discovery mode. The script detects that `COMMISSION_API_ENDPOINT` is empty and enters discovery mode automatically.

### 3.3 What happens

1. WebKit launches headless.
2. The script logs into `supplier.meesho.com` using credentials from `~/.meesho_creds.env`.
3. A network interceptor is attached to the BrowserContext.
4. The script navigates six candidate panel pages:
   - `/panel/v3/new/root/referral-fee`
   - `/panel/v3/new/growth/oinpw/referral-fee`
   - `/panel/v3/new/root/pricing`
   - `/panel/v3/new/growth/oinpw/pricing`
   - `/panel/v3/new/root/commission`
   - `/panel/v3/new/growth/oinpw/home` (dashboard, as a baseline)
5. Every outbound request whose URL contains a commission-related keyword is logged with prefix `[CANDIDATE]`.
6. Every 200 JSON response from a matched request is logged with prefix `[RESPONSE CAPTURED]` including the top-level keys and a 500-character body preview.
7. At the end, the script writes a discovery summary to `backend/app/data/category_commissions.json` (overwriting the existing placeholder) and prints a summary table.
8. Browser closes cleanly.

### 3.4 Reading the log

The log is written to:
```
logs/scraper/commission_YYYY-MM-DD_HH-MM.log
```

Scan for lines prefixed `[CANDIDATE]` and `[RESPONSE CAPTURED]`:

```
[CANDIDATE] GET https://supplier.meesho.com/api/cataloging/referral-fees (type=xhr)
[CANDIDATE] GET https://supplier.meesho.com/api/pricing/commission-rates (type=fetch)
[RESPONSE CAPTURED] https://supplier.meesho.com/api/cataloging/referral-fees — keys=['data', 'status'] — preview={"data":[...
```

### 3.5 Identifying the correct endpoint

The operator must review the candidate list and identify which URL returns the category-wise commission rate-card. Signs of the correct endpoint:

- Response keys contain words like `data`, `categories`, `items`, `fees`, `commissions`, `rate_card`
- The list entries contain a category/super-category name field and a rate/percentage field
- The response is a list (or a dict with a list value), not a single flat object

If the `[RESPONSE CAPTURED]` body preview already shows the commission table structure, the discovery is complete. If only `[CANDIDATE]` lines appear (no response bodies), proceed to §3.6.

### 3.6 If no responses are captured

The interceptor captures responses asynchronously. If the page does not fire XHR calls for commission data during the navigation window, try:

1. Log into the supplier panel interactively (headed mode): set `headless=False` in the `browser.launch()` call, navigate manually to the referral-fee page, and observe network requests in the DevTools Network tab.
2. Alternatively, use the Playwright MCP browser tools (if configured in Claude Desktop) per `docs/PLAYWRIGHT_MCP_REFERENCE.md §1.2` (`browser_network_requests` + `browser_network_request`).

---

## §4 Endpoint Discovery Step — Setting the Constant

Once the correct endpoint is identified from Run 1, set it for Run 2 via the environment variable:

```bash
export COMMISSION_API_ENDPOINT="https://supplier.meesho.com/api/cataloging/referral-fees"
# (replace with the actual URL from your log)
```

Alternatively, edit the module constant in `backend/scripts/meesho_commission_scraper.py`:

```python
# Line ~107 (approx):
COMMISSION_API_ENDPOINT: str = os.environ.get("COMMISSION_API_ENDPOINT", "").strip()
```

Change to:

```python
COMMISSION_API_ENDPOINT: str = "https://supplier.meesho.com/api/cataloging/referral-fees"
```

This constant is the only line that needs editing between runs. Commit the update to pin the endpoint for monthly refreshes (interim; moving to monthly, usage-driven per the locked scraper-cadence design).

---

## §5 Run 2: Direct Mode

### 5.1 Purpose

Fetch the commission rate-card from the identified endpoint, parse it into the agreed JSON structure, propose a leaf mapping against `meesho_category_tree.json`, and write the output file.

### 5.2 Command

```bash
cd /private/tmp/mesell-wt/category-seeding
export COMMISSION_API_ENDPOINT="https://supplier.meesho.com/api/cataloging/referral-fees"
python backend/scripts/meesho_commission_scraper.py
```

Or with a custom creds file:

```bash
MEESHO_CREDS_FILE=~/Project/mesell/.meesho_creds.env \
COMMISSION_API_ENDPOINT="https://supplier.meesho.com/api/cataloging/referral-fees" \
python backend/scripts/meesho_commission_scraper.py
```

### 5.3 What happens

1. WebKit launches headless.
2. Login proceeds as in Run 1.
3. The script fires `ctx.request.get(COMMISSION_API_ENDPOINT, headers=_api_headers(...))` — from the authenticated browser context, so Akamai sees a fingerprint-valid request.
4. The response JSON is parsed by `parse_commission_body()` using a multi-key best-effort strategy.
5. Parsed entries are mapped against the 3,772-leaf category tree via `propose_leaf_mapping()`.
6. Results are written to `backend/app/data/category_commissions.json`.
7. A summary is printed to stdout.
8. Browser closes.

### 5.4 Expected output file

`backend/app/data/category_commissions.json` will have this top-level shape:

```json
{
  "_meta": { ... },
  "rate_card": [
    {
      "meesho_category": "Fashion",
      "commission_pct": 15.0,
      "source_url": "https://supplier.meesho.com/api/...",
      "captured_at_note": "2026-06-16T...",
      "raw_entry": { ... }
    }
  ],
  "proposed_leaf_mapping": [
    {
      "rate_card_category": "Fashion",
      "commission_pct": 15.0,
      "matched_super_ids": ["10", "11", "29"],
      "matched_super_names": ["Men Fashion", "Women Fashion", "Women"],
      "leaf_count_covered": 285,
      "match_confidence": "partial",
      "ambiguity_flag": false,
      "ambiguity_note": null
    }
  ],
  "unmatched_super_categories": [
    "super_id=131 (Eye Utility, 10 leaves)"
  ],
  "ambiguity_notes": []
}
```

### 5.5 If the parser does not recognise the response shape

The `parse_commission_body()` function uses a multi-key best-effort strategy for common envelope structures. If the response has an unexpected shape, the raw body is stored under `_UNKNOWN_STRUCTURE_` in `rate_card` for manual review. Check the log for:

```
Could not find a list of rows in commission response. Storing raw body for manual review.
```

In this case, the operator or data lead must inspect `raw_entry` in the output JSON and update `parse_commission_body()` to handle the actual key names.

---

## §6 Throttling and Hard-Stop Behaviour

### 6.1 Throttle

The script inserts jittered delays between all navigations and requests:
- Between page navigations: 2–5 seconds (randomised)
- Between API requests: 1–3 seconds (randomised)

This keeps effective request rate well below 1 request per 2 seconds, consistent with the rate limit constraint in the scraper agent spec and with `meesho_batch_scraper.py`'s proven posture.

### 6.2 Hard stops

The script aborts immediately (without retry) on any of:

| Condition | Action |
|---|---|
| HTTP 401 / 403 / 463 from any Meesho API | Log `HARD STOP`, abort, exit code 1 |
| HTTP 429 (rate limited) | Log `HARD STOP`, abort, exit code 1 |
| CAPTCHA page detected | Log `HARD STOP`, abort, exit code 1 (NEVER solve) |
| Login does not redirect (2 attempts) | Log `HARD STOP`, abort, exit code 1 |

On hard stop, the script logs the abort reason and exits. The operator must investigate before retrying. Do not retry-storm — this risks IP-level blocking and account suspension.

### 6.3 What to do on 403 / 463

These codes indicate either:
1. The authenticated session expired during the run — re-run from scratch (fresh login).
2. Akamai detected anomalous traffic — wait 30–60 minutes before retrying.
3. The endpoint URL is wrong — confirm from Run 1 discovery log.

---

## §7 Mapping Review Step

After Run 2 completes, the data lead and founder must review `proposed_leaf_mapping` before any backfill runs.

### 7.1 The 5 overlapping super-category clusters

Meesho's rate-card uses broad category names. Our tree has 30 super-categories, many with overlapping names. These five clusters require founder confirmation:

| Cluster | super_ids | Total leaves |
|---|---|---|
| Personal Care | 14, 37, 88, 39, 19, 36 | 228 |
| Home | 12, 24, 30 | 855 |
| Kids | 13, 25 | 287 |
| Automotive | 18, 73 | 175 |
| Office/Craft | 66, 76 | 318 |

For each cluster, the founder must confirm: "rate-card entry X applies to ALL of these super-ids" or "rate-card entry X applies only to super-ids Y, Z".

This disambiguation is required before `scripts/seed_category_commissions.py` is authored.

### 7.2 Zero-commission entries

Meesho historically runs zero commission (0%) for some categories (e.g. Grocery). If any rate-card entry shows `"commission_pct": 0.0`, this is a genuine value, not missing data. The output JSON distinguishes `0.0` (genuine zero) from `null` (not captured). The backfill must preserve this distinction.

### 7.3 Unmatched super-categories

Super-categories in `unmatched_super_categories` have no corresponding rate-card entry by name. These need manual assignment:
- Check whether the rate-card uses a different name for the same category.
- Check whether Meesho's rate-card simply does not cover these categories (which may indicate they are new or have a blanket default rate).

---

## §8 Post-Capture Handoff

When the data lead is satisfied with the reviewed `category_commissions.json`:

1. **Author `scripts/seed_category_commissions.py`** — idempotent backfill script that reads `category_commissions.json` and issues `UPDATE categories SET commission_pct = ? WHERE super_id = ?` statements. This is a separate task, separate dispatch.
2. **Run the seed locally** via `make seed` or equivalent, verify `SELECT super_id, commission_pct FROM categories LIMIT 10` shows non-NULL values.
3. **Commit `category_commissions.json`** — it is a structured data file, not a snapshot; it is committed to git.
4. **Do NOT commit `.meesho_creds.env`**.
5. **Update `docs/status/STATUS_DATA.md`** with the capture date, rate-card row count, leaf coverage, and hand-off to database-builder.

---

## §9 Monthly Refresh (interim; moving to monthly, usage-driven per the locked scraper-cadence design)

For the next monthly refresh:
1. Confirm `COMMISSION_API_ENDPOINT` is still set correctly (endpoint may have changed).
2. Run in direct mode (Run 2 only, if endpoint is stable).
3. Diff the new `rate_card` against the prior committed JSON — Meesho commission changes are rare but happen at annual policy revisions.
4. If diff shows changes, re-run the mapping review step and update the seed script.

The scraper agent memory (`/.claude/agent-memory/meesell-scraper-maintainer/MEMORY.md`) records the endpoint and rate-limit observations from each run.

---

## §10 Audit Trail

Each run writes a rotating log at:

```
logs/scraper/commission_YYYY-MM-DD_HH-MM.log
```

Logs include: timestamp, phase, action, outcome, HTTP status codes (but NEVER credentials). Retain for 30 days per §6.6 of `PLAYWRIGHT_MCP_REFERENCE.md`.

---

## §11 Quick Reference

```bash
# Prerequisites check
python -c "from playwright.async_api import async_playwright; print('playwright ok')"
playwright install webkit

# Run 1: discovery
cd /private/tmp/mesell-wt/category-seeding
python backend/scripts/meesho_commission_scraper.py
# → check logs/scraper/commission_*.log for [CANDIDATE] and [RESPONSE CAPTURED] lines

# After identifying endpoint:
export COMMISSION_API_ENDPOINT="https://supplier.meesho.com/api/..."

# Run 2: direct fetch
python backend/scripts/meesho_commission_scraper.py
# → output: backend/app/data/category_commissions.json

# Validate syntax (no execution, no login):
python3 -m py_compile backend/scripts/meesho_commission_scraper.py && echo "SYNTAX OK"

# Do NOT commit credentials:
git status --porcelain | grep meesho_creds   # should return nothing
```
