# RETENTION — Category-Keyed Change Monitor (Design Spec)

| Field | Value |
|---|---|
| Document type | **Design spec** (strategy + architecture). NOT a build ticket. No code in this doc. |
| Status | **DRAFT — for founder review.** Scope = **V1.x / post-V1** (not in the locked V1 surface). |
| Author | `meesell-data-engineer` (Data Lead) |
| Session | `mesell-retention-monitor-spec-data-session-1` |
| Owns (data domain) | the category-keyed snapshot store, the diff engine reuse, the scrape budget |
| Hands off (other domains) | BACKEND owns the jobs, the `category_subscription` + `notification` models/endpoints, and the fan-out worker. INFRA owns the CronJob + GCS lifecycle + egress quota. |
| Touches LOCKED docs? | **Yes — flagged, NOT amended.** `PRICING_LOCKED.md` (billing cadence) + the scraper ToS posture in `PLAYWRIGHT_MCP_REFERENCE.md §6`. See §9. Founder ratification required before build. |
| Related | `docs/plans/features/price-calculator-rework/W6_REFRESH_SPEC.md` (the existing monthly-refresh + drift-gate pipeline this spec reuses), `docs/MEESHO_CATEGORY_INTELLIGENCE.md` (LOCKED SSoT), `backend/scripts/meesho_monthly_refresh.py`, `backend/scripts/diff_pricing_lookup.py` |

---

## 0. The problem this solves (one paragraph)

MeeSell today is a **creation tool**: a seller creates a catalog, exports the XLSX, and leaves. Catalog creation is **periodic, not daily** — so after the first month the seller has no reason to keep paying. The retention question "why am I still subscribed?" is unanswered. This spec converts the product from a one-shot creation tool into a **continuous maintenance service**: MeeSell watches the seller's Meesho categories for changes to the rules that govern their listings (compliance fields, shipping slabs, banned words, cost-relevant fields) and tells the seller — proactively — "category X changed; these N of your catalogs are affected; re-check / re-price / re-export." The seller keeps paying because the product keeps doing work between catalog-creation events. The mechanic is strictly inside the product boundary: **public Meesho category data + the seller's own catalog inputs, READ-ONLY scraping, never auto-go-live**.

---

## 1. Architecture — the key rule: key on CATEGORY, not customer

### 1.1 The one rule that makes this safe and cheap

> **Scrape the unit of CATEGORY, not per-customer-per-catalog.**

Many sellers share the same Meesho categories. If we re-scraped per customer per catalog, the same category (e.g. `Kurtis`) would be scraped once per seller who sells kurtis — N redundant fetches of identical public data. That is:
- **ToS / rate-limit / IP-ban risk** — hammering Meesho with N× the necessary requests is exactly the abusive pattern `PLAYWRIGHT_MCP_REFERENCE.md §6.3` forbids ("Cap total runs per day … hourly is abusive").
- **Wasted compute** — N identical snapshots, N identical diffs.

Instead: a category is the **shared, cached unit**. Scrape it **once** per TTL window, **diff** the new snapshot against the last, and **fan out** the change notification to **every** seller who has a catalog in that category. One scrape serves all sellers in that category.

### 1.2 Data-flow diagram

```
                              ┌──────────────────────────────────────────────────────┐
                              │  TRIGGERS (enqueue a category-scrape job, deduped)     │
                              │                                                        │
   onboarding complete ──────▶│  • onboard: enqueue scrape for each of the seller's    │
   (seller's existing          │           existing categories  (instant value)        │
    categories)                │  • catalog-add: enqueue scrape for the new category    │
                              │  • quarterly CronJob: enqueue scrape for ALL active     │
   seller adds a catalog ─────▶│           (subscribed) categories  (baseline refresh)  │
   in category X               └───────────────┬──────────────────────────────────────┘
                                                │ enqueue(category_id)
                                                ▼
                              ┌──────────────────────────────────────────────────────┐
                              │  DEDUPE-BY-CATEGORY GATE  (the cost saver)             │
                              │                                                        │
                              │  IF category_snapshot(X).captured_at within TTL        │
                              │     → REUSE existing snapshot. enqueue NOTHING.        │
                              │  ELSE IF a scrape job for X is already queued/running  │
                              │     → COALESCE (drop the duplicate). enqueue NOTHING.  │
                              │  ELSE → enqueue exactly ONE scrape job for X.          │
                              └───────────────┬──────────────────────────────────────┘
                                              │ (only on cache-miss + no in-flight job)
                                              ▼
        ┌──────────────────────────────────────────────────────────────────────────────┐
        │  SCRAPE  (Celery worker → meesell-scraper-maintainer / Playwright WebKit)       │
        │  ≤ 1 req / 2 s · authenticated WebKit context (Akamai-valid) · hard-stop 403/429│
        │  Captures the CATEGORY's public listing-rule surface:                          │
        │    compliance fields · shipping slab · banned words · cost-relevant fields      │
        └───────────────┬────────────────────────────────────────────────────────────────┘
                        │ writes raw snapshot
                        ▼
        ┌───────────────────────────────────┐        ┌──────────────────────────────────┐
        │  CATEGORY SNAPSHOT STORE           │        │  DIFF ENGINE                      │
        │  data/snapshots/<date>/cat_<id>... │───────▶│  reuse diff_pricing_lookup.py     │
        │  (gitignored raw) + DB row         │  new   │  pattern → PASS / REVIEW / BLOCK  │
        │  category_snapshot(category_id,    │  vs    │  classify: added / removed /      │
        │  captured_at, content_hash, blob)  │  last  │  changed (rules/shipping/banned)  │
        └───────────────────────────────────┘        └───────────────┬──────────────────┘
                                                                      │ diff non-empty
                                                                      ▼
        ┌──────────────────────────────────────────────────────────────────────────────┐
        │  FAN-OUT  (BACKEND-owned worker)                                                │
        │  WHO:  every seller with a catalog in category X                                │
        │        (SELECT user_id FROM category_subscription WHERE category_id = X)        │
        │  WHAT: flag each affected catalog → needs_recheck / needs_reprice / needs_export │
        │  MSG:  "Your category '<name>' changed: <human summary of the diff>.            │
        │         <N> of your catalogs are affected. Review them."                        │
        │  → write notification rows → deliver (in-app bell + optional email/WhatsApp)    │
        └──────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Why this is the product's retention loop

The seller experiences: *"MeeSell noticed Meesho changed the rules for my category before I did, and told me exactly which of my products to fix."* That is recurring, between-creation value — it is the answer to "why keep paying."

---

## 2. The category-keyed snapshot store + TTL / cache design

### 2.1 The snapshot unit

A **category snapshot** is the captured public rule-surface for one Meesho category at one point in time. It captures the change-relevant projection only (not the full XLSX template binary):

| Captured dimension | Why it matters to the seller | Source today |
|---|---|---|
| **Compliance fields** (required/optional flips, new mandatory fields) | A newly-required field means existing catalogs will be rejected on next upload | XLSX template parse (`category_attributes.json` derivation) |
| **Shipping slab** | Changes the seller's landed cost → re-price | `meesho_shipping_slabs.json` / pricing lookup |
| **Banned words** | A newly-banned word in an existing title/description → rejection | `banned_words.json` |
| **Cost-relevant fields** (transfer price / monetization inputs) | Changes the P&L → re-price | `meesho_pricing_lookup.json` (getTransferPrice census) |

> **NOTE — commission is intentionally NOT a snapshot dimension.** Per the Wave-1.5 won't-fix finding (data-lead memory, 2026-06-16), Meesho commission is **dynamic** (category × price-slab × time-bound promotion), has no stable published rate-card, and is correctly captured **per-product at upload time**, not as seeded/snapshotted reference data. The monitor watches shipping + transfer-price as the cost-relevant surface, never commission.

### 2.2 Store shape

Two layers, mirroring the existing committed-derived-vs-gitignored-raw split:

1. **Raw blob (gitignored).** `data/snapshots/<YYYY-MM-DD>/cat_<category_id>.json` + a sidecar `.meta.json` (source URL, capture timestamp, content hash) — exactly the `PLAYWRIGHT_MCP_REFERENCE.md §6.6` audit-trail convention. Lives on local disk during a run; the durable copy lives in the GCS `data/snapshots/` bucket with a lifecycle policy (INFRA-owned, §5).
2. **Index row (DB, BACKEND-owned).** `category_snapshot(category_id, captured_at, content_hash, dimensions_jsonb, blob_uri)`. The `content_hash` is the cheap change-detector: if the new hash equals the last row's hash, there is **no change** and the diff/fan-out path short-circuits entirely.

### 2.3 TTL / cache design

| Parameter | Value (proposed) | Rationale |
|---|---|---|
| **TTL** | **90 days** (≈ quarterly) as the V1.x default | Matches the existing quarterly-refresh cadence and the (unmeasured, see §7) low expected change frequency. **The TTL is a tunable** — §7's measurement plan re-derives it from observed per-category change frequency. |
| **Cache key** | `category_id` (NOT template_id, NOT customer_id) | Aligns with the §1.1 rule. (Avoids the G13 cache-key drift noted in the gap analysis — category is the canonical key.) |
| **Reuse rule** | on enqueue: if `now - captured_at < TTL` → reuse, enqueue nothing | The dedupe gate (§3). |
| **Coalesce rule** | if a scrape job for the same `category_id` is already queued/running → drop the duplicate | Prevents the onboarding/catalog-add/CronJob triggers from stacking N jobs for the same category. |
| **Cache store** | Valkey key `catmonitor:snapshot:<category_id>` (presence + `captured_at`), TTL-bounded; DB `category_snapshot` is the durable record | Valkey is the fast dedupe check; DB is the diff source-of-truth. Matches the existing Valkey-DB-3 caching convention in `MVP_ARCHITECTURE.md §6`. |

The TTL is deliberately **long** (90 days), not short. Sellers do not need minute-level freshness — Meesho rule changes are infrequent (§7). A long TTL is what keeps the global scrape budget (§6) tiny.

---

## 3. Enqueue triggers + dedupe-by-category

Three triggers enqueue a `scrape_category(category_id)` job. **All three pass through the same dedupe gate (§1.2 / §2.3)** — the gate is the single chokepoint that guarantees one scrape per category per TTL, regardless of how many sellers or triggers fire.

| Trigger | Fires when | What it enqueues | Dedupe behaviour |
|---|---|---|---|
| **Onboarding** | A seller completes onboarding and has existing categories (from imported/created catalogs) | one `scrape_category` job per distinct category the seller owns | Most will be cache-hits if another seller already populated that category → instant value, near-zero scrape cost |
| **Catalog-add** | A seller saves a new catalog in category X | one `scrape_category(X)` job | If X scraped within TTL → reuse (no scrape); else one scrape, then fan-out includes this seller |
| **Quarterly CronJob** | Scheduled (INFRA CronJob), once per quarter | one `scrape_category` job per **distinct active category** (i.e. every category with ≥ 1 subscription) | The baseline sweep. Naturally deduped — it iterates **distinct** categories, never per-seller |

### 3.1 How dedupe-by-category works (precise)

The unit that makes dedupe correct is the **`category_subscription`** table (BACKEND-owned):

```
category_subscription(user_id, category_id, catalog_id, subscribed_at)
   — one row per (seller, catalog) in a category
   — UNIQUE index supports: "distinct categories" and "all sellers in category X"
```

- **Distinct categories to scrape** = `SELECT DISTINCT category_id FROM category_subscription`. This is the universe the CronJob iterates and the dedupe denominator. A category with 500 sellers is **one** scrape, not 500.
- **Sellers to notify for category X** = `SELECT DISTINCT user_id FROM category_subscription WHERE category_id = X`. This is the fan-out audience (§4).
- **Dedupe at enqueue** = the gate in §1.2: TTL check (skip if fresh) + in-flight check (coalesce if a job for X is already queued). Two independent guards; either one suffices to suppress a redundant scrape.

The seller-count for a category never multiplies the scrape count. It only multiplies the (cheap, DB-only) fan-out at the end.

---

## 4. Diff → notification fan-out path

### 4.1 Diff

When a fresh snapshot lands, the diff engine compares it to the previous `category_snapshot` row for the same `category_id`. **Reuse the existing `diff_pricing_lookup.py` pattern** (already battle-tested for the monthly pricing refresh): it emits `added` / `removed` / `changed` sets per dimension and a verdict `PASS` / `REVIEW_REQUIRED` / `BLOCK`.

- `content_hash` equal → **no diff, no fan-out** (the cheap path; most categories most quarters).
- `PASS` (zero drift) → no fan-out.
- `REVIEW_REQUIRED` (rules/shipping/banned/cost changed within thresholds) → **fan out** + (for a category-rule change, optionally) data-lead review before the seller-facing copy is finalized.
- `BLOCK` (drift exceeds a hard threshold, or a scrape anomaly) → **do not fan out**; raise a `STATUS_DATA.md` blocker for data-lead + founder review. This prevents a scraper glitch (e.g. Meesho returned a truncated page) from spamming every seller with a false "your category changed."

### 4.2 Fan-out — which sellers, which catalogs, what message

| Question | Answer |
|---|---|
| **Which sellers** | `SELECT DISTINCT user_id FROM category_subscription WHERE category_id = X` — every seller with a catalog in the changed category. |
| **Which catalogs** | The specific `catalog_id`s in `category_subscription` for `(user_id, X)`. Each is **flagged** with the relevant action: `needs_recheck` (compliance change), `needs_reprice` (shipping/cost change), `needs_export` (any rule change that alters the XLSX output). |
| **What message** | A **human-readable diff summary**, not raw JSON. E.g. *"Your category 'Kurtis' added a required field 'Country of Origin' and its shipping slab rose ₹6. 3 of your catalogs are affected — review them before your next upload."* The diff dimensions map to plain-English sentence fragments (compliance / shipping / banned-word / cost), assembled per the display-layer rules in `MEESHO_CATEGORY_INTELLIGENCE.md §6`. |
| **Delivery** | In-app notification (bell) as V1.x baseline. Email / WhatsApp are additive channels gated behind a feature flag (out of scope to build here; the notification model must not assume a channel). |

### 4.3 Idempotent, de-duplicated notifications

Fan-out writes a `notification` row keyed by `(user_id, category_id, snapshot_content_hash)` with a UNIQUE constraint, so re-running the same diff (retry, re-deploy) never double-notifies a seller for the same change. The catalog flags are set idempotently (`needs_recheck = true`), never appended.

---

## 5. Infra reuse — map each piece to existing components + BACKEND handoff points

### 5.1 Reuse map (almost nothing is net-new)

| Piece needed | Existing component to reuse | Net-new work |
|---|---|---|
| Scrape a category's public rule surface | `meesell-scraper-maintainer` + the proven authenticated-WebKit Akamai-bypass tooling (`backend/scripts/meesho_batch_scraper.py`, `meesho_monthly_refresh.py`) | a thin "single-category" scrape entrypoint (vs the full-corpus batch) |
| Snapshot store (raw + index) | the gitignored-raw / committed-derived split already in use; `data/snapshots/` convention from `PLAYWRIGHT_MCP_REFERENCE.md §6.6` | the `category_snapshot` DB table (BACKEND) |
| Diff / drift gate | **`backend/scripts/diff_pricing_lookup.py`** — PASS/REVIEW_REQUIRED/BLOCK verdicts + thresholds already exist; **`meesho_monthly_refresh.py`** already orchestrates scrape→build→diff→stage with a never-overwrite-live policy | generalize the diff from "pricing rows" to "category rule dimensions" |
| Background execution | **Celery workers** (2 replicas, Valkey broker) — already in the stack per `CLAUDE.md` | the `scrape_category` + `fanout_category_change` task definitions (BACKEND) |
| Dedupe cache | **Valkey** (DB 3, version-tagged keys per `MVP_ARCHITECTURE.md §6`) | the `catmonitor:snapshot:*` keyspace + TTL |
| Quarterly trigger | the existing **monthly/quarterly refresh CronJob** posture (INFRA) | one CronJob entry that enqueues the distinct-category sweep |
| Notification delivery | (none yet — this is the one genuinely new surface) | `notification` model + endpoint + in-app bell (BACKEND + FRONTEND) |

### 5.2 BACKEND handoff points (what a backend coordinator owns)

These are the items the Data Lead **hands off** via the cross-lead memo protocol; they are NOT data-domain work:

1. **`category_subscription` table + maintenance.** Populated on catalog-add / onboarding (one row per seller-catalog-in-category). Indexed for "distinct categories" and "all sellers in category X". Alembic migration coordinated with data before any scrape ships.
2. **`category_snapshot` table.** `(category_id, captured_at, content_hash, dimensions_jsonb, blob_uri)`. The diff source-of-truth.
3. **Celery tasks.** `scrape_category(category_id)` (calls the scraper-maintainer entrypoint, honours the dedupe gate) and `fanout_category_change(category_id, snapshot_content_hash)` (the §4 fan-out).
4. **`notification` model + endpoint.** `GET /api/v1/notifications` (list, unread count) + the idempotent write contract in §4.3. Plus catalog flag columns (`needs_recheck` / `needs_reprice` / `needs_export`) on the existing catalog/product record.
5. **Trigger wiring.** Enqueue hooks on the onboarding-complete and catalog-create paths.

### 5.3 Other-lead handoffs

- **INFRA:** the quarterly CronJob (or Cloud Scheduler entry) that fires the distinct-category sweep; the GCS `data/snapshots/` bucket + lifecycle policy (e.g. retain 4 quarters of snapshots, then expire); the per-pod egress quota for the scraper. (Mirrors the existing `data ↔ infra` pair in the lead spec.)
- **AI:** none required for the monitor itself. IF a future iteration auto-suggests the *fix* for a flagged catalog (re-autofill a newly-required field), that re-uses the existing autofill golden-set handoff — but that is out of scope here.
- **FRONTEND:** the in-app notification bell + the "affected catalogs" review surface. Out of scope to design here; called out so the backend notification contract is built channel-agnostic.

---

## 6. ToS / rate-limit / robots safety + global scrape budget

### 6.1 Safety posture (inherited, non-negotiable)

All of `PLAYWRIGHT_MCP_REFERENCE.md §6` applies unchanged:
- **Own account only.** Read-only. Public category rule data only. **Never go-live, never auto-upload.** No buyer PII, no cross-account data.
- **Rate limit ≤ 1 request / 2 s**, jittered; single sequential session; never parallelize against Meesho from multiple browser sessions.
- **Hard-stops:** 403 / 429 / captcha / suspension page / 2 consecutive login failures → **halt immediately, surface to operator, do not retry-storm.** (This is already a Stop Condition in the data-lead + scraper-maintainer specs.)
- **Identify the automation** (custom User-Agent where possible) + honour `robots.txt`.
- **Audit trail:** every run writes a structured log + per-snapshot `.meta.json` sidecar; 30-day retention.

### 6.2 The global scrape budget — why category-keying makes it tiny

The category-keyed design is what keeps the budget within ToS-safe bounds. The budget is bounded by the count of **distinct active categories**, NOT by the seller count:

```
worst-case scrapes per quarter  =  COUNT(DISTINCT category_id IN category_subscription)
                                ≤  3,772  (the entire Meesho leaf corpus — only if every
                                          category had a paying seller, which it will not)
```

- At ≤ 1 req / 2 s, even the absolute worst case of **all 3,772 leaves** is ≈ 2.1 hours of sequential scraping **once per quarter** — well inside "a quarterly enumeration pass is fine; hourly is abusive."
- In reality the active-category count is a small fraction of 3,772 (only categories sellers actually use), so a real quarterly sweep is minutes-to-tens-of-minutes.
- **Per-customer scraping would have blown this**: N sellers × their categories = potentially 100×–1000× more requests for identical data. Category-keying collapses that to one-scrape-per-category.

### 6.3 Zero-spend

- **Playwright compute only** — the scraper runs on the existing Celery worker pods (CPU). **No external API spend.** No Gemini, no paid data feed.
- The only incremental cost is GCS storage for `data/snapshots/` (tiny — JSON projections, lifecycle-expired after 4 quarters) and worker CPU-seconds during the quarterly sweep. Both are well inside the existing ₹500/mo infra envelope; INFRA confirms in the handoff.

---

## 7. Measurement plan — change frequency → notification cadence → honest billing cadence

### 7.1 Do historical snapshots exist to measure change frequency? — **NO (not yet).**

Verified at authoring time:
- `backend/app/data/meesho_category_tree.json` has **one** git commit in its history (`687ced1`) — a single generation, no series to diff.
- `backend/app/data/meesho_pricing_lookup.json` has **one** git commit (`6674941`, the W1 productionization) — again a single generation.
- `data/snapshots/` **does not exist**; there is no captured time-series of category rule-surfaces.
- What DOES exist is the **machinery** to produce a series: `meesho_monthly_refresh.py` (scrape → build → diff → stage) + `diff_pricing_lookup.py` (the drift classifier). The refresh pipeline has run a census once (`transfer_price_census.jsonl`, 2026-06-19) but there is no second census to diff against.

**Conclusion:** change frequency **cannot be quantified today** — there is exactly one snapshot generation, so the diff denominator is zero. The number is unknown, not "low" or "high." This spec therefore **defines the metric + the collection plan** rather than reporting a value.

### 7.2 The metric to collect

> **`category_change_rate(category_id)` = fraction of refresh windows in which the `diff_pricing_lookup`-style verdict ≠ PASS for that category.**

Collected as: each quarterly sweep writes, per category, a `diff_verdict` (PASS / REVIEW_REQUIRED / BLOCK) and the changed-dimension set. After **K** sweeps, `category_change_rate = (# windows with a non-PASS verdict) / K`. Aggregate to a corpus-wide **`mean_quarterly_change_rate`** and a **per-super-category** breakdown (compliance-heavy supers — Grocery/FSSAI, Electronics/BIS — are expected to change more often than, say, Sarees).

### 7.3 Collection plan (how to get the first real number)

1. Land the `category_snapshot` store (BACKEND) + the single-category scrape entrypoint (DATA).
2. Run the quarterly sweep **twice** (two windows ⇒ first diffable pair). Each sweep is the §6.2 distinct-category pass.
3. From sweep N→N+1, compute `category_change_rate` per category and the corpus mean. Record in the **refresh changelog** (data-lead memory) per the standing changelog discipline.
4. After ~3–4 quarters (K≥3), the rate stabilizes enough to **re-derive the TTL** (§2.3) and to set the billing-cadence honesty (§7.5).

Until then, the V1.x defaults stand: **TTL = 90 days, quarterly sweep**.

### 7.4 How the rate sizes notification cadence

- If `mean_quarterly_change_rate` is **low** (most categories change < once/quarter — the likely case given Meesho's stable templates): a **quarterly** sweep is sufficient; sellers get a notification only in the rare quarter their category actually changes. Notifications are **event-driven, not scheduled** — silence is the norm, which keeps the signal high.
- If a **subset** of supers (e.g. Grocery/FSSAI compliance) changes more often: those supers can be put on a **tighter sweep** (e.g. monthly) while the long tail stays quarterly — a per-super TTL. The metric (§7.2 per-super breakdown) is exactly what decides this. The scrape budget (§6.2) stays tiny because tighter cadence applies only to the few volatile supers.

### 7.5 How the rate sizes the HONEST billing cadence

This is the strategic crux, and it **touches `PRICING_LOCKED.md`** (§9 — flagged for founder ratification, not amended here):

- `PRICING_LOCKED.md` bills **monthly** (₹499 Pro / ₹1,999 Business). The retention thesis is "the product does work between catalog-creation events." For that to be **honest**, the product must do *enough* between-events work to justify a monthly charge.
- If the measured change rate shows categories change **roughly quarterly**, then the *monitoring value* is delivered quarterly — and a purely-monitoring justification for a *monthly* charge would be thin. Two honest resolutions, for the founder to choose:
  - **(a) Keep monthly billing**, and ensure the monthly value is the **bundle** (creation + monitoring + re-price + re-export), with monitoring as one retention pillar among several — not the sole monthly justification.
  - **(b) Offer a quarterly billing option** aligned to the real monitoring cadence (e.g. a "maintenance" plan billed quarterly), so the charge matches when the work actually happens.
- **The data, once collected (§7.3), is the input to that pricing decision.** This spec does not pre-decide it — it makes the dependency explicit and routes it to the founder. **No `PRICING_LOCKED.md` edit happens without founder ratification.**

---

## 8. Scope, phasing, non-goals

| | |
|---|---|
| **Scope** | **V1.x / post-V1.** Not in the locked V1 surface. Build only after founder ratifies §9. |
| **In scope (this spec)** | the architecture, the category-keyed snapshot + TTL design, the dedupe-by-category gate, the diff→fan-out path, the infra-reuse map, the safety/budget posture, the measurement plan. |
| **Out of scope (deferred / other domains)** | the `notification`/`category_subscription` DB models + endpoints (BACKEND build), the CronJob + GCS lifecycle (INFRA build), the in-app bell UI (FRONTEND build), auto-*fixing* a flagged catalog (future AI iteration), email/WhatsApp channels (flagged, additive). |
| **Non-goals (hard)** | NO per-customer scraping. NO auto-go-live / auto-upload to Meesho. NO commission as a snapshot dimension (dynamic — won't-fix per Wave 1.5). NO real-time / hourly scraping (ToS-abusive). NO external API spend. |

---

## 9. LOCKED-doc decisions flagged for founder ratification (NOT amended here)

This spec **does not** edit any LOCKED doc. The following two locked decisions are **touched** and require **founder ratification** before any build:

1. **`PRICING_LOCKED.md` — billing cadence (§7.5).** The monthly-vs-quarterly billing-cadence question is downstream of the measured `category_change_rate`. Ratification needed: *does monitoring justify monthly billing as part of the bundle (option a), or do we add a quarterly "maintenance" billing option (option b)?* This is a pricing-strategy decision reserved to the founder per `MASTER_PLAN.md §7.3`. **No edit to `PRICING_LOCKED.md` is proposed until the data exists and the founder rules.**

2. **Scraper ToS posture — `PLAYWRIGHT_MCP_REFERENCE.md §6` (LOCKED reference) + `MEESHO_CATEGORY_INTELLIGENCE.md` (LOCKED SSoT).** This spec adds a **recurring, scheduled** scrape cadence (quarterly sweep) on top of the existing one-shot corpus parse. The §6 safety rules already cover read-only + rate-limit + hard-stops, so no rule is being *changed* — but introducing a *standing recurring scrape against Meesho* is a posture decision the founder should explicitly ratify (it shifts MeeSell from "scraped once at build time" to "scrapes Meesho on a schedule forever"). Ratification needed: *founder confirms a standing quarterly read-only category scrape is within the operator's intended ToS posture.* No amendment to either LOCKED doc is proposed.

Per `MASTER_PLAN.md §7.3` and `docs/MEESHO_CATEGORY_INTELLIGENCE.md`'s LOCKED-amendment rule (founder escalation required for LOCKED changes), both are escalation items — surfaced here, not actioned.

---

## 10. Open questions for the founder

1. **Billing cadence (§7.5 / §9.1):** option (a) keep monthly + bundle monitoring, or (b) add a quarterly maintenance billing option — decided after measurement, but which direction is preferred a priori?
2. **Notification channels:** in-app bell only for V1.x, or include email/WhatsApp from the start (cost + consent implications)?
3. **Per-super tighter cadence (§7.4):** is it acceptable to scrape compliance-heavy supers (Grocery/FSSAI, Electronics/BIS) monthly while the long tail stays quarterly, if the data justifies it?
4. **Standing recurring scrape (§9.2):** confirm a forever-scheduled quarterly read-only category scrape is within the intended ToS posture.
5. **Snapshot retention:** 4 quarters of `data/snapshots/` in GCS before lifecycle-expiry — enough history for the measurement plan, or keep longer?

---

*End of design spec. DRAFT — V1.x / post-V1. Founder review + §9 ratification required before any build dispatch.*
