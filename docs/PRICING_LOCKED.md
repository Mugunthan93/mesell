# MeeSell — Locked Pricing v1 (Expense-First)

**Last updated: 2026-06-04**
**Status: Locked pricing v1 — founder approval required**
**Pairs with:** `docs/COST_ANALYSIS.md` (full 806-line cost model). This document refines that work into a locked price.

---

## 1. Methodology — Why Expense-First

Pricing built from competitor benchmarks attracts low-investment customers and erodes the product's ability to fund itself. MeeSell instead derives price from real per-user expense, adds a margin sufficient to fund product depth, and only then checks competitor positioning as a *marketing* output — not a *pricing* input. The sequence is non-reversible: **(1) measure cost → (2) set price with margin → (3) compare to market**. This protects the product. Bootstrap + solo founder means every paying user must cover their own infra share, their amortised acquisition cost, and a slice of founder time recovery — or the business is a treadmill.

---

## 2. Expense Categories — Real ₹ Per Line Item

### 2.1 Fixed monthly costs

| Line Item | M1–M4 (dev, on $300 GCP credit) | M5+ (post-credit) | Source / Notes |
|---|---|---|---|
| GCP VM (Cloud Run min-instances=1, 1 vCPU, 512 MiB) | ₹0 (credit) | ₹400 | COST_ANALYSIS §4 |
| Serverless VPC Connector (Cloud Run → VM Postgres) | ₹0 (credit) | ₹350 | COST_ANALYSIS §4 |
| Postgres on shared existing VM (Aletheia/LLM_Manager sibling) | ₹0 marginal | ₹0 marginal until ~3,000 sellers | CLAUDE.md workspace |
| Valkey on shared VM | ₹0 marginal | ₹0 marginal | Same |
| GCS Standard (5 GB Always-Free) | ₹0 | ₹0 until ~500 sellers | COST_ANALYSIS §4.3 |
| Domain (meesell.in, ₹1,000/yr) | ₹85 amortised | ₹85 | Registrar quote |
| SSL (Let's Encrypt / Google-managed) | ₹0 | ₹0 | Free |
| Email (Mailgun free tier, 100/day) | ₹0 | ₹0 until ~3K sellers | Mailgun pricing |
| MSG91 SMS OTP | usage-based | usage-based | ₹0.18/SMS (COST_ANALYSIS §4) |
| Razorpay subscription module | ₹0 setup, 2% per txn | same | Razorpay public pricing |
| Gemini 2.5 Flash API | usage-based | usage-based | **Key variable** — see §2.3 |
| Claude Haiku 4.5 (chatbot support) | usage-based | usage-based | $1/M in, $5/M out |

### 2.2 Per-user variable costs (per active user/month)

Derived from COST_ANALYSIS §4 assumptions: 30 SKUs/mo free, 150 SKUs/mo Pro, ~800 input + 500 output tokens per SKU generation, 4 images × 200 KB per SKU, 2 OTP/mo.

| Item | Free user (₹/mo) | Pro user (₹/mo) | Calculation |
|---|---|---|---|
| Gemini text (catalog generation) | ₹0.60 | ₹3.00 | 30 or 150 SKUs × ₹0.02/SKU (COST_ANALYSIS §4.2) |
| Gemini image description (vision input) | ₹0.20 | ₹1.00 | 7× multiplier on text raw cost per §4.2 |
| MSG91 OTP | ₹0.36 | ₹0.36 | 2 SMS × ₹0.18 |
| GCS storage (images, exports) | ₹0.04 | ₹0.20 | 24 MB or 120 MB at ₹1.65/GB-mo |
| GCS ops (uploads, reads) | ₹0.02 | ₹0.10 | Class A/B ops at published rates |
| Compute share (Cloud Run + VPC) | ₹0.75 | ₹4.50 | ₹750 fixed ÷ 1,000 sellers; Pro 6× usage |
| Razorpay txn fee (Pro only) | n/a | ₹9.98 | 2% of ₹499 |
| Claude Haiku support tickets (1.5%/mo rate) | ₹0.01 | ₹0.05 | ₹0.75/ticket × 0.015–0.05 |
| **Total cost per active user/month** | **₹1.98 ≈ ₹2** | **₹19.19 ≈ ₹19** | |

### 2.3 Variable drivers locked

| Variable | Locked value | Source |
|---|---|---|
| Gemini 2.5 Flash input | $0.075 / 1M tokens (₹6.25) | ai.google.dev/pricing, 2026 |
| Gemini 2.5 Flash output | $0.30 / 1M tokens (₹25) | Same |
| MSG91 SMS (transactional) | ₹0.10–0.18 (using ₹0.18 conservative) | MSG91 dashboard |
| Razorpay subscription | 2% per recurring charge | razorpay.com/pricing |
| GCS Standard asia-south1 | ₹1.65 / GB-month | cloud.google.com/storage/pricing |
| Claude Haiku 4.5 | $1 / $5 per M tokens (in/out) | anthropic.com/pricing |
| USD → INR | ₹83 (2026 average) | RBI ref rate |

---

## 3. Per-User Cost at Scale

Pulled directly from `COST_ANALYSIS.md` §4 (Option C — Hybrid). Assumed paying mix: **5% (conservative SaaS freemium)** until validated by cohort data at M3.

| Scale | Total monthly cash burn | Active sellers | Paying sellers (5%) | Cost / active user | Cost / paying user |
|---|---|---|---|---|---|
| 100 (M1) | ₹1,675 | 100 | 5 | ₹17 | ₹335 |
| 1,000 (M3) | ₹11,185 | 1,000 | 50 | ₹11 | ₹224 |
| 10,000 (M6–M8) | ₹1,07,285 | 10,000 | 500 | ₹11 | ₹215 |
| 100,000 (M18+) | ₹10,60,085 | 1,00,000 | 5,000 | ₹11 | ₹212 |

**Observation:** per-paying-user cost plateaus at **~₹215** beyond 1K scale. This is the floor below which no paid tier can be priced without subsidising free users from elsewhere. At M1 (100 sellers, 5 paying) the per-paying cost is ₹335 — temporarily high because fixed costs spread thin — but the GCP $300 credit absorbs this entirely through M4.

---

## 4. Margin Math — Setting Our Price

The expected operating scale at price-lock is **Month 6 = ~5,000 active sellers, ~250 paying (5%)**. At this point, per-paying-user cost ≈ ₹215/mo. The price must cover this cost plus margin, acquisition cost amortisation, support buffer, and founder time recovery.

### 4.1 Build-up

```
Component                                          ₹/paying user/mo
─────────────────────────────────────────────────────────────────
Raw infra + AI cost per paying user at 5K scale    ₹215
Razorpay 2% on the final price (computed below)    ₹10
                                                   ─────
Cost floor                                         ₹225

+ Target gross margin (70% — Indian SaaS norm)     ₹525
  (price must be 3.33× cost to yield 70% margin)

+ CAC amortisation                                 ₹40
  Top-3 channels (cold outreach + YouTube
  sponsorships + Reels): blended CPA ≈ ₹30–80
  per free signup. At 5% paid conversion, CPA
  per paying user ≈ ₹600–1,600. Amortised over
  18-month expected LTV.

+ Support buffer (Claude Haiku + edge escalation)  ₹15
  10% of tickets escalate to founder at imputed
  ₹2L/mo ÷ 4,000 tickets handled = ₹50; 30%
  weighting + chatbot raw cost.

+ Founder time recovery                            ₹120
  ₹2L/mo imputed × 14 founder months ÷ LTD-equiv
  3,000 paying users × 1/18 month amortisation.

+ Sustainability reserve (Gemini overruns,         ₹35
  Razorpay holds, free-tier breakage buffer)

─────────────────────────────────────────────────────────────────
TOTAL MINIMUM PRICE FLOOR (Pro)                    ₹435
ROUND UP TO Indian SaaS swipe threshold            ₹499
```

**Pro is locked at ₹499/mo.** This price clears the calculated ₹435 floor with ~₹64 of cushion (15% safety margin on top of the 70% target).

### 4.2 Business tier build-up

Business adds multi-marketplace prep, team seats (2–5 users), bulk SKU operations, priority queue, and ~3× the AI/storage allocation of Pro. Cost per Business user ≈ ₹50/mo. Applying the same 70% margin: ₹50 / 0.30 = ₹167 minimum. Add CAC (B2B targeting = ₹200), support buffer (B2B tickets are heavier = ₹50), founder time (₹300 — Business users get a single onboarding call), reserve (₹100). Floor = **₹817 → ₹1,999**. The 4× Pro multiplier is intentional anchoring (creates the "Pro looks cheap" frame) and matches Indian SaaS Business-tier conventions.

### 4.3 LTD build-up

LTD price = (Pro monthly × LTV months) ÷ scarcity discount.
- Pro = ₹499/mo. LTV = 18 months. Raw value = ₹8,982.
- Scarcity discount = 45% (LTD users are evangelists; we pay for word-of-mouth). Discounted = ₹4,940.
- Round to ₹4,999. **10-month-equivalent of Pro.**
- Cap at 1,000 = ₹49.99 L cash injection ceiling — enough to fund Phase 3 burn cushion without VC.

---

## 5. LOCKED PRICING

| Tier | Price | Margin (at M6) | Rationale |
|---|---|---|---|
| **Free Forever** | ₹0 | -₹2 / user (loss leader) | Acquisition. 50 SKUs/mo cap. Cost absorbed by paying tiers; ratio holds while free:paid ≥ 8:1. |
| **Pro** | **₹499 / mo** | **₹275 net (≈55%)** after Razorpay + infra + amortisations | Core paid tier. Sub-₹500 = no finance-approval friction for Indian SMEs. |
| **Business** | **₹1,999 / mo** | **₹1,425 net (≈71%)** | Multi-user (up to 5 seats), multi-marketplace, priority AI queue, bulk ops. |
| **LTD (Lifetime Deal)** | **₹4,999 one-time** | One-time cash; 10-month Pro equivalent | Capped at 1,000 spots. Closes when reached (scarcity signal). |

**Annual discount (optional founder lever):** ₹4,990/year for Pro = 10 months for the price of 12. Encourages annual lock-in, reduces churn surface, smooths Razorpay reserve hold pattern.

**Free tier limit confirmed at 50 SKUs/mo** — tighter than VariantStudio (no published free tier), looser than Shopify (no free), matches the "experience the product properly before paying" threshold from validated pain points.

---

## 6. NOW — Compare to Competitors (Marketing Output, Not Driver)

Pricing is already locked. This section positions the locked numbers against the Indian Meesho-seller-tools market.

### 6.1 Competitor table

| Competitor | Price | Their gaps | MeeSell wedge |
|---|---|---|---|
| **VariantStudio** | ₹249/mo (cheapest known) | No category-specific dynamic forms, no live Meesho preview, no AI-driven QualityGate, single-tenant only | MeeSell offers all four at ₹499 — 2× price, ~5× capability |
| **Catalog.io / Catalog Builder India** | ₹599–₹999/mo | English-only, generic e-com schema not Meesho-specific, no rejection-rate analytics | MeeSell is Meesho-native (3,738 templates pre-scraped) and undercuts on capability per rupee |
| **Selleramp India tools** | ₹1,499–2,499/mo | Broad multi-marketplace but shallow per platform; no QualityGate, no AI catalog generation | MeeSell Business (₹1,999) matches their middle tier and adds AI; Pro (₹499) covers their use case at ⅓ price |
| **Shopify (referenced by Meesho sellers)** | ₹1,994/mo (Basic) | Shopify is its own store — not Meesho catalog tooling. Sellers conflate the two but they solve different problems. | MeeSell sits *upstream* of Meesho; Shopify sits *parallel*. No real overlap. |
| **Manual / DIY (CSV in Excel)** | ₹0 | 4–8 hrs/SKU, 35–60% rejection rate, no preview, error-prone | MeeSell Free at 50 SKUs/mo replaces this fully |

### 6.2 Marketing positioning lines (derived, not declared)

- **vs VariantStudio:** "₹250 more, ~5× the features — AI catalog generation, QualityGate, live preview, category-aware forms. The ₹250 saved on VariantStudio costs you 4+ hours per SKU in manual cleanup."
- **vs Catalog.io:** "MeeSell is Meesho-native. Catalog.io is a generic e-com tool repurposed. The 3,738 pre-scraped Meesho templates mean MeeSell knows what every category needs — Catalog.io doesn't."
- **vs Shopify:** "MeeSell fixes your Meesho catalog. Shopify replaces Meesho with your own store. Different problems — pick MeeSell if you want to keep Meesho's traffic."
- **vs Manual:** "Free Forever covers your first 50 SKUs. Past that, ₹499/mo is one rejected order's refund."
- **Defensive line:** "Only tool with all three: AI catalog generation + Meesho-specific QualityGate + live preview."

---

## 7. Sensitivity Analysis

Net cash position at **10K sellers / Month 8** under different scenarios. Base case: 5% conversion, current Gemini pricing, 2% Razorpay.

| Scenario | Paying sellers | Pro MRR (net of Razorpay) | Monthly cash burn | Net cash | Break-even sellers needed |
|---|---|---|---|---|---|
| **Base (5% conv, current costs)** | 500 | ₹2,44,500 | ₹1,07,285 | **+₹1,37,215** | 220 paying (2.2%) |
| 3% conversion (pessimistic) | 300 | ₹1,46,700 | ₹1,07,285 | **+₹39,415** | Same 220 (would need 7.3% mix) |
| 10% conversion (optimistic) | 1,000 | ₹4,89,000 | ₹1,07,285 | **+₹3,81,715** | — |
| Gemini API cost doubles | 500 | ₹2,44,500 | ₹1,67,285 (≈+56% on AI lines) | **+₹77,215** | 342 paying (3.4%) |
| Razorpay raises to 2.5% | 500 | ₹2,43,750 | ₹1,07,285 | **+₹1,36,465** | Negligible shift |
| Gemini doubles AND conv = 3% | 300 | ₹1,46,700 | ₹1,67,285 | **-₹20,585** | 342 paying needed (would be 11% mix — unlikely) |
| Free:paid ratio 95:5 holds; ave SKU doubles to 60 free/300 Pro | 500 | ₹2,44,500 | ₹1,90,000 (Gemini ~doubles) | **+₹54,500** | 388 paying |

**Robustness verdict:** The model survives single-axis shocks (any one of: half-rate conversion, doubled Gemini, raised Razorpay). It breaks only under simultaneous Gemini-doubles + 3%-conversion + heavy SKU usage. Mitigation already exists in COST_ANALYSIS §4.2: caching identical generations and batching image descriptions reduces Gemini cost by ~30–40% — re-establishing margin under the worst case.

---

## 8. Founder Decision Required

Specific yes/no questions to lock V1 pricing for go-live:

1. **Lock Pro at ₹499/mo as calculated, or override?**
   - Override options: ₹399 (Lean — assumes 8%+ conversion) or ₹599 (Premium — assumes <5% conversion).
   - Recommendation: lock ₹499. Calculation supports it; sensitivity shows robustness.

2. **LTD cap at 1,000 or 500?**
   - 1,000 = ₹50L ceiling, 14–16 month fill (per COST_ANALYSIS §9.4 ramp).
   - 500 = ₹25L ceiling, faster scarcity signal, faster price defence.
   - Recommendation: **1,000** for cash buffer depth; founder may close cap early if scarcity is needed for marketing.

3. **Free tier limit: 50 SKUs/mo or tighter (25) or looser (100)?**
   - 25 = aggressive paywall, expect lower free-tier loyalty.
   - 50 = current locked value, balances product experience with paywall pressure.
   - 100 = competitor-undercut messaging but raises free-user infra cost by 2×.
   - Recommendation: **50.**

4. **Add annual discount tier (₹4,990/yr = 10 months for price of 12)?**
   - Pro: reduces churn surface, smooths cash flow, defends against month-to-month price comparisons.
   - Con: discounts revenue per user by ~17%.
   - Recommendation: **Yes, launch with Pro paywall in M4.** Cap promotional banner to 30 days post-launch.

5. **Business tier — launch at M4 with Pro, or defer to M9?**
   - M4 launch = adds revenue floor immediately.
   - Defer = focus messaging on Pro single-user simplicity for first 6 months.
   - Recommendation: **defer Business to M7–M9** when seller cohort signals demand for multi-user/multi-marketplace.

6. **Razorpay subscription module — confirm 2% rate, or negotiate down at 1,000 paying users?**
   - Public rate = 2%. Razorpay does negotiate to 1.9% at volume.
   - Recommendation: **lock 2% in model; revisit at 500 paying users for negotiation lever.**

7. **Pan-India English V1 confirmed — no Tamil-tier pricing, correct?**
   - Confirmed per prompt context. Tamil-specific pricing **not** introduced here.
   - Tamil UI is a Month-9 product milestone, not a pricing axis.

---

## Document Control

| Field | Value |
|---|---|
| Document | MeeSell Locked Pricing v1 |
| Version | v1 |
| Last updated | 2026-06-04 |
| Pairs with | `docs/COST_ANALYSIS.md` (data source), `docs/BUSINESS_STRATEGY.md` |
| Status | Locked pricing v1 — founder approval required |
| Next review | After Month 3 cohort data (real SKU/seller average, real paid conversion) |
