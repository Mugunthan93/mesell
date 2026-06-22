# Category Seeding — Commission Rate-Card Capture Report

| Field | Value |
|---|---|
| Document type | Capture report (Wave 1.5 — commission rate-card) |
| Author | `meesell-scraper-maintainer` (sonnet) |
| Dispatched by | `meesell-data-engineer`, session `mesell-category-seeding-session-1` |
| Date | 2026-06-16 |
| Worktree | `/private/tmp/mesell-wt/category-seeding` |
| Branch | `feature/category-seeding` |
| Authorising architecture | `CATEGORY_SEEDING_ARCHITECTURE.md §9 Q2` (D2 Phase 2 — real commission values, two-phase, scrape-sourced) |
| Status | **HARD STOP — no data captured** |

---

## §1 Mission

Capture Meesho's published seller commission / referral-fee rate-card (the category-wise commission percentage table Meesho publishes for suppliers in the supplier panel / seller help / pricing docs), structure it as JSON at `backend/app/data/category_commissions.json`, and produce a best-effort proposed mapping from rate-card category entries to the 3,772 leaf categories in `meesho_category_tree.json`. No seeding; the data lead and founder review before any backfill runs.

---

## §2 Hard Stop Encountered

### 2.1 Primary block — Playwright MCP unavailable

The Playwright MCP browser tool family (`mcp__playwright__browser_navigate`, `browser_snapshot`, etc.) is **not available** in this dispatch context. Inspection of `~/Library/Application Support/Claude/claude_desktop_config.json` confirms only one MCP server is registered: `pencil`. No Playwright MCP server is present.

This is not a transient failure. Prior sessions recorded the same finding:

> `STATUS_DATA.md` entries 2026-06-06 10:30 and 11:00: "Playwright MCP tools unavailable in this environment"

Without a real browser execution context, it is not possible to load Meesho's commission pages, which are React Single-Page Applications that deliver a 2,166-byte HTML shell and populate all actual content via JavaScript. Server-side HTTP requests (curl) receive only this shell — no commission data.

### 2.2 Secondary block — Akamai WAF blocks all server-side requests

All Meesho domains are protected by Akamai Edge Security. Every URL probed returned either HTTP 403 (Akamai Access Denied, Reference #18.*) or the same 2,166-byte SPA shell:

| URL probed | Result |
|---|---|
| `https://supplier.meesho.com/referral-fee` | HTTP 403 |
| `https://supplier.meesho.com/pricing` | HTTP 403 |
| `https://supplier.meesho.com/help` | HTTP 403 |
| `https://supplier.meesho.com/robots.txt` | HTTP 403 (WAF blocks even robots.txt) |
| `https://www.meesho.com/referral-fee` | HTTP 403 (Akamai Access Denied) |
| `https://www.meesho.com/info/referral-fees` | HTTP 403 |
| `https://www.meesho.com/info/supplier-pricing` | HTTP 403 |
| `https://www.meesho.com/robots.txt` | HTTP 403 |
| `https://supplierhub.meesho.com/` | HTTP 200 — SPA shell only (2,166 bytes, no content without JS) |
| `https://supplierhub.meesho.com/referral-fee` | HTTP 404 |
| `https://seller.meesho.com/` | HTTP 200 — SPA shell only (2,166 bytes, identical) |
| `https://seller.meesho.com/pricing` | HTTP 404 |
| `https://seller.meesho.com/fees` | HTTP 404 |
| `https://help.meesho.com/` | HTTP 200 — SPA shell only (2,166 bytes, identical) |
| `https://support.meesho.com/` | HTTP 200 — SPA shell only (2,166 bytes, identical) |
| `https://images.meesho.com/images/supplier-hub/referral-fee.pdf` | HTTP 404 |

All 17 probe attempts used the browser-standard `User-Agent` string `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36`, rate-limited to 1 request per 2–3 seconds.

### 2.3 robots.txt status

`supplier.meesho.com/robots.txt` returns HTTP 403 — the WAF blocks it before serving the file. robots.txt interpretation is therefore deferred to an interactive Playwright session where the browser can load it under a real TLS fingerprint. No Disallow rules can be confirmed or denied at this time.

### 2.4 What was NOT hit

- No HTTP 429 (rate limit) — the WAF blocks at the TLS/UA fingerprint layer, not the rate layer.
- No CAPTCHA — the WAF returns hard 403s, not CAPTCHA challenges.
- No account suspension risk — no authenticated session was attempted.

---

## §3 Source identification (attempted)

Meesho's commission / referral-fee rate-card is published at `supplier.meesho.com` inside the authenticated supplier panel, typically under a "Pricing" or "Referral Fee" section. It is also sometimes linked from the supplier help centre. The URL patterns tried:

- `supplier.meesho.com/referral-fee` — canonical path mentioned in Meesho seller documentation
- `supplier.meesho.com/pricing` — alternate documented path
- `supplierhub.meesho.com/referral-fee` — Meesho Supplier Hub variant
- Public help domains (`help.meesho.com`, `support.meesho.com`) — all SPA shells

None of these were reachable via server-side HTTP. The authenticated supplier panel (`supplier.meesho.com/*`) requires browser-level TLS fingerprinting (JA3/JA4 matching a real Chromium instance) to pass the Akamai WAF, then OTP login to see the actual rate-card table.

---

## §4 Coverage

| Metric | Value |
|---|---|
| Rate-card rows captured | 0 |
| Super-categories covered | 0 / 30 |
| Category-level entries | 0 / 234 |
| Leaves mappable | 0 / 3,772 |
| Coverage % | 0% |

---

## §5 Category tree inventory (ready for mapping, awaiting rate-card)

The full category tree is committed and clean. Once rate-card values are supplied, the mapping can be computed in a single Python script run.

### 5.1 Scale

| Level | Count |
|---|---|
| Super-categories (Level 0) | 30 |
| Categories (Level 1) | 234 |
| Sub-categories (Level 2) | 1,046 |
| Leaves (Level 3) | 3,772 |

### 5.2 Super-category index (with leaf counts — the mapping target)

| super_id | Super-category | Categories | Leaves |
|---|---|---|---|
| 10 | Men Fashion | 3 | 106 |
| 11 | Women Fashion | 8 | 165 |
| 12 | Home & Living | 12 | 38 |
| 13 | Kids & Toys | 8 | 284 |
| 14 | Personal Care & Wellness | 6 | 9 |
| 15 | Mobiles & Tablets | 1 | 2 |
| 16 | Consumer Electronics | 10 | 248 |
| 17 | Appliances | 1 | 8 |
| 18 | Automotive | 2 | 3 |
| 19 | Beauty & Personal Care | 6 | 73 |
| 24 | Home Utility | 1 | 1 |
| 25 | Kids | 2 | 3 |
| 26 | Grocery | 12 | 321 |
| 29 | Women | 2 | 14 |
| 30 | Home & Kitchen | 13 | 816 |
| 34 | Health & Wellness | 28 | 117 |
| 36 | Beauty & Makeup | 12 | 43 |
| 37 | Personal Care | 16 | 97 |
| 39 | Men'S Grooming | 2 | 4 |
| 66 | Craft & Office Supplies | 3 | 6 |
| 68 | Sports & Fitness | 14 | 362 |
| 73 | Automotive Accessories | 3 | 172 |
| 75 | Pet Supplies | 13 | 128 |
| 76 | Office Supplies & Stationery | 6 | 312 |
| 77 | Industrial & Scientific Products | 7 | 89 |
| 78 | Musical Instruments | 9 | 149 |
| 80 | Books | 27 | 163 |
| 83 | Bags, Luggage & Travel Accessories | 4 | 27 |
| 88 | Mens Personal Care & Grooming | 2 | 2 |
| 131 | Eye Utility | 1 | 10 |

### 5.3 Known mapping ambiguities (must resolve before backfill)

Meesho's rate-card uses broad category names. Our tree has overlapping super-categories that may map to the same rate-card entry:

1. **Personal Care cluster** — Three overlapping super-categories will likely share a single rate-card entry:
   - super_id=14 "Personal Care & Wellness" (9 leaves)
   - super_id=37 "Personal Care" (97 leaves)
   - super_id=88 "Mens Personal Care & Grooming" (2 leaves)
   - super_id=39 "Men'S Grooming" (4 leaves)
   - super_id=19 "Beauty & Personal Care" (73 leaves)
   - super_id=36 "Beauty & Makeup" (43 leaves)

2. **Home cluster** — Multiple overlapping home super-categories:
   - super_id=12 "Home & Living" (38 leaves)
   - super_id=24 "Home Utility" (1 leaf)
   - super_id=30 "Home & Kitchen" (816 leaves)

3. **Kids cluster** — Two super-categories:
   - super_id=13 "Kids & Toys" (284 leaves)
   - super_id=25 "Kids" (3 leaves)

4. **Automotive cluster** — Two super-categories:
   - super_id=18 "Automotive" (3 leaves)
   - super_id=73 "Automotive Accessories" (172 leaves)

5. **Office/Craft cluster**:
   - super_id=66 "Craft & Office Supplies" (6 leaves)
   - super_id=76 "Office Supplies & Stationery" (312 leaves)

The founder must confirm which rate-card entry maps to which super-category for these overlapping groups before any backfill runs.

---

## §6 Proposed mapping format (for when rate-card is supplied)

Once rate-card values are available, `backend/app/data/category_commissions.json` should be populated with entries of this shape:

```json
{
  "meesho_category": "Fashion",
  "commission_pct": 15.0,
  "source_url": "https://supplier.meesho.com/referral-fee",
  "captured_at_note": "2026-06-16 interactive session by founder",
  "maps_to_super_ids": ["10", "11", "29"],
  "maps_to_super_names": ["Men Fashion", "Women Fashion", "Women"],
  "leaf_count_covered": 285,
  "ambiguity_flag": false,
  "ambiguity_note": null
}
```

The `maps_to_super_ids` array enables the backfill script (`scripts/seed_category_commissions.py`) to do a single UPDATE ... WHERE super_id IN (...) per rate-card row, achieving full coverage of all 3,772 leaves in at most 30-50 UPDATE statements.

---

## §7 Recommendation to the data lead

### Option A — Founder manually copies the rate-card (RECOMMENDED for V1)

The founder logs into the Meesho supplier panel interactively, navigates to the referral-fee / pricing page, and supplies the commission table as a CSV, screenshot, or typed list. The data lead or scraper-maintainer structures it into `category_commissions.json` and authors `scripts/seed_category_commissions.py`. No Playwright session required.

**Fastest path to unblocking the pricing engine.** The rate-card is a ~30-50 row table and is stable (changes only at Meesho's annual policy revision). Manual capture is proportionate.

### Option B — Add Playwright MCP to Claude Desktop and re-dispatch (PREFERRED for monthly refresh — interim; moving to monthly, usage-driven per the locked scraper-cadence design)

Add the `@playwright/mcp` server to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Then re-dispatch `meesell-scraper-maintainer` in an interactive session with the founder's supplier panel credentials available. The scraper can:
1. Navigate to `supplier.meesho.com/login`
2. OTP-authenticate (founder provides phone + OTP interactively)
3. Navigate to the referral-fee page
4. Intercept the API response (network interception per `PLAYWRIGHT_MCP_REFERENCE §5` Strategy 3B)
5. Write `category_commissions.json` with full rate-card

This is the correct path for monthly refresh automation.

### Option C — Deferred NULL (not recommended beyond V1)

Leave `commission_pct = NULL` permanently and handle it at the pricing engine layer (already done: `CommissionMissingError` 422 when NULL, per architecture D2). This unblocks V1 catalog creation but means the pricing calculator cannot give accurate P&L breakdowns. The founder's D2 ruling explicitly requires real values, so Option C is only acceptable as a temporary state.

### Recommendation

**Do Option A now** (manual copy, fast), **set up Option B** (Playwright MCP config) for the monthly refresh path. Do not extend Option C past Wave 1.5.

---

## §8 Accuracy caveats (for when data is captured)

1. Meesho's commission structure may have nuances not visible in the rate-card table alone:
   - Commission may vary by product price band (e.g. lower % for high-value items)
   - Promotional / introductory rates may apply to new categories
   - The rate-card may show "0%" for some categories (e.g. Grocery) — this is a genuine value, not missing data

2. The rate-card granularity is likely super-category level, not leaf level. A single rate-card row would apply to all 816 leaves under "Home & Kitchen". The proposed mapping must preserve this granularity clearly so the pricing engine can distinguish "not set" (NULL) from "genuinely 0%".

3. If Meesho's commission structure turns out to be flat (e.g. 0% for all categories, as has been their historical model for certain periods), this should be reported faithfully — it materially changes D2's value and may make the backfill trivially simple (one UPDATE setting all rows to 0.00).

---

## §9 Artifacts produced

| Artifact | Path | Status |
|---|---|---|
| Structured rate-card JSON | `backend/app/data/category_commissions.json` | Created — empty `rate_card: []`, full `_meta` with hard-stop record |
| This capture report | `docs/plans/architecture/CATEGORY_SEEDING_COMMISSION_CAPTURE.md` | Created |
| `scripts/seed_category_commissions.py` | (to be authored once JSON is populated) | NOT CREATED — no data to seed |

---

## §10 STATUS_DATA.md update

See the UPDATE block appended to `docs/status/STATUS_DATA.md` for this session.
