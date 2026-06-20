# Section-7 (price-calculator) — Tier-1 section-coordinator topic memory

## Session mesell-section-7-coordinator-session-1 — 2026-06-19

**Task:** AUTHOR the wave plan for the Price Calculator REWORK (correcting the wrong #285/#287 model). Plan-only — no dispatch (no Agent tool), at the check-in gate.

**State:** Wave plan AUTHORED at `docs/plans/features/price-calculator-rework/WAVE_PLAN.md`. Awaiting Tier-0 check-in-gate sign-off before any child dispatch.

### Key findings (load-bearing)
- **Confirmed model (source of truth):** `.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md`. `transfer_price = price − commission_fees − gst_on_shipping − tds − tcs`. Shipping is a PER-CATEGORY CONSTANT (price+weight independent) keyed by sscat_id; seller bears ONLY 0.18×shipping (the GST), NOT shipping itself. commission=0 default (optional override). tcs=0. tds=0.001×total_price. Verified 3,772/3,772 census + real bank payout ₹61.78 (price 70, shipping 45).
- **The WRONG model** (#285 BE merged, #287 FE): deducts FULL shipping + 4% commission + fabricated logistics/fixed fees + TCS + RTO-loss, calibrated to a RETRACTED "₹106→₹47" misread. Must be fully reworked.
- **Live BE path = modular monolith** `backend/app/modules/pricing/{service,domain,schemas,router,repository}.py` + model `backend/app/shared/models/pricing_calc.py`. The extracted `backend/services/svc-pricing` is DORMANT — ignore it.
- **FE = `frontend/apps/mfe-pricing`** (federation remote `mfe-pricing` @ :4201). `pricing.model.ts` is STALEST — still pre-#285 mock (`target_margin_pct`, `seller_price`, `commission_amount`, MRP-as-output). Total rewrite.
- **Data file does NOT exist yet** — must productionize `logs/scraper/transfer_price_census_summary.json` → `lookup` (3,772 entries) into `backend/app/data/meesho_pricing_lookup.json`. `category_commissions.json` exists but is stale/commission-based.
- **Export does NOT consume any pricing field today** (grep-confirmed). Selling price lives in `products.attributes` JSONB (no dedicated price column on product model). → drives OPEN Q1.
- **LOCKED docs to reconcile (FOUNDER-gated):** `docs/V1_FEATURE_SPEC.md` §F7 (lines 274–324) + `docs/BACKEND_ARCHITECTURE.md` §2.6 (lines 427–452) + §12.M. Do NOT auto-approve.

### Wave plan shape
- 6 waves. Critical path W1 (data) → W2 (engine) → W3 (FE). W4 (export) also blocks on W2. W5 (docs) + W6 (monthly-refresh wiring) off critical path; after W2 merges, W3/W4/W5/W6 run in parallel (zero file overlap).
- Hard barriers: W1→(W2,W6); W2→(W3,W4). Soft: W6 only needs W1's data-file contract.
- W6 ships the WIRING (fold getTransferPrice census into the EXISTING monthly category scrape — NO separate cron, founder ruling). No live scrape executed by the rework (dev-only/no-spend/no-secrets).

### Founder gates / open questions
- G-DOC (W5 LOCKED docs), G-EXPORT/Q1 (which price feeds export), G-NETPROFIT (founder net-profit layer in V1?), Q2 (sscat_id resolution — does seeded `categories` carry Meesho sscat_id?), Q3 (drop vs keep-nullable wrong columns), Q4 (TDS rounding to match census/₹61.78).

### Next action when resumed
Present the wave plan to Tier-0 (Director). On sign-off: ensure 3 branches + 3 worktrees exist, then dispatch W1 (data) first via `meesell-backend-coordinator` Tier-2 sub-session. NOTHING before sign-off.

---

## Session mesell-section-7-coordinator-session-1 (cont.) — 2026-06-19 — DIRECTOR DECISIONS BAKED IN

The Director resolved ALL decision gates; I updated `WAVE_PLAN.md` (plan-only, no dispatch). Final state:

- **G-EXPORT/Q1 — RESOLVED:** W4 feeds calculator SELLING PRICE into the Meesho template's native MRP / Meesho Price column(s). Settlement + net profit are NOT exported (on-screen only). W4 first task = data-engineer confirms canonical/`meesho_column_header` from `template_fields`; selling price lives in `products.attributes` JSONB. W4 is now backend-only, no FE, no longer Q1-blocked.
- **G-NETPROFIT — RESOLVED → DEFERRED V1.5:** stripped output-GST + landed-cost + net_profit from EVERYWHERE (§0 model, W2 contract/domain/schemas/model/migration/tests, W3 UI/service, W5 docs). V1 = settlement breakdown only (Selling price / Commission fee x% default 0 / GST 0.18×shipping / TDS 0.001×total / Estimated Bank Settlement + disclaimer).
- **G-DOC — APPROVED:** W5 kept; rewrite V1_FEATURE_SPEC §F7 + BACKEND_ARCH §12.M; founder reviews diff in PR before merge.
- **Q2 — RESOLVED:** `categories.meesho_leaf_id` = census `sscat_id` (3,772/3,772). Engine joins directly; NO mapping unit. Removed contingency from W1/W2.
- **Q3 — RESOLVED → KEEP-NULLABLE:** wrong #285 columns kept nullable + stop writing (not dropped); additive migration. (#285 on develop, not prod.)
- **Q4 — RESOLVED:** Decimal ROUND_HALF_UP 2dp, match to the paise. Golden pins SKU **TTC-BL-OR-HP-NG-P4** @ price 70/shipping 45 → ₹61.78 + census `transfer_price_at_100`.
- **STALE-HANDOFF FLAG:** added an authoritative-source banner to §0 — ALL builders follow `project_pricing_transfer_price_model.md`, NOT the SUPERSEDED `handoff_pricing_transfer_price.md` (round-4 "₹9 flat fee"). Wrong code to replace = `service.py` + `pricing_calc.py`. RETIRE stale data stubs `category_commissions.json` + `meesho_shipping_slabs.json` (deleted in W2 squash; added to §3 ownership map + §1 inventory + W2 goal).

**Doc status flipped to:** "SIGNED-OFF DECISIONS BAKED IN — awaiting final Tier-0 check-in-gate 'go'." §5 now lists all gates RESOLVED; §6 has zero open questions. Only outstanding gate = G-CHECKIN. Still NO dispatch.
