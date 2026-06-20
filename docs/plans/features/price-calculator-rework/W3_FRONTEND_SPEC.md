# W3 — FRONTEND BUILD SPEC (Price Calculator Rework)

| Field | Value |
|---|---|
| Wave | **W3** (critical-path tail — binds to the W2 `PriceCalcResponse` contract) |
| Section | section-7 (`price-calculator`) — V1 Feature 7 |
| Author | `meesell-frontend-coordinator` (Frontend Lead) — HYBRID step-1 SPEC (no build, no dispatch) |
| Builders (step-2) | `meesell-angular-service-builder`, `meesell-angular-component-builder`, `meesell-angular-ui-styler` |
| Merge-gate (step-3) | `meesell-frontend-coordinator` (merge-gate squash review → `feature/section-7/frontend`) |
| Branch | `feature/section-7/frontend` (off `feature/section-7/integration`, **after W2 merges to integration**) |
| Type | code |
| Session | `mesell-price-calculator-frontend-session-1` |
| Authoritative model | `.claude/agent-memory/nexus-level-0-director/project_pricing_transfer_price_model.md` (confirmed 2026-06-19) |
| BACKEND CONTRACT (bind exactly) | `docs/plans/features/price-calculator-rework/W2_BACKEND_SPEC.md` §2.1 (request) + §2.2 (`PriceCalcResponse`) |
| Depends on | **W2 (HARD barrier)** — FE binds to the W2-frozen response contract. Breaking request rename (`extra="forbid"`) → W3 must reach develop WITH/IMMEDIATELY-AFTER W2 (see §7). |
| SUPERSEDES | the WRONG-model FE in merged-base + open/gate-stopped PR #287 (`input_cost`/`target_margin_pct` → `mrp`/`meesho_price`/`seller_price`/`commission`/`gst`/`profit`). |

> **READ THE CENSUS MODEL + W2 CONTRACT, NOT THE STALE FE.** The current `frontend/apps/mfe-pricing/src/app/*` implements the retracted DECISION-1 "server-calc P&L" wrong model. W3 deletes that contract entirely and binds to W2 §2.2. NET-PROFIT (output-GST + landed-cost) is **DEFERRED to V1.5** — NO such panel/field/input anywhere.

---

## 0. The contract W3 binds to (verbatim from W2 §2.1 / §2.2)

**Request body** — `POST /api/v1/products/{id}/price-calc`, `extra="forbid"` (a stale field 422s):
```
{
  selling_price:   string  // Decimal>0, 2dp — the listed Meesho price (sent as string, preserves 2dp)
  commission_pct?: string  // Decimal, ge 0 le 100, OPTIONAL (omit → backend defaults 0)
}
```
The OLD fields `meesho_price`, `input_cost`, `target_margin_pct`, all `override_*` are **REMOVED**. The request takes **NO category field** — backend resolves product → category → leaf_id server-side.

**Response `PriceCalcResponse`** — all money = Decimal-as-string, 2dp; parse with `Number()`:
```
{
  selling_price, shipping, total_price, commission_pct, commission_fees,
  gst_on_shipping, tds, tcs (always "0.00"), estimated_bank_settlement,  // money strings
  disclaimer: string,                                  // STATIC verbatim Meesho text
  alerts: [{ code:"NEGATIVE_SETTLEMENT", message_id:string, severity:"warning" }],  // 0 or 1
  calculated_at: string                                // ISO-8601
}
```
**Error:** unknown-category → HTTP **422** `pricing.category.no_pricing_data` (clean data-integrity 4xx, NOT 500).

**Disclaimer (render verbatim — DO NOT paraphrase):**
> Bank settlement amount may vary slightly based on the quantity in the order, Meesho commission policy at the time of the order and the actual weight of the product as calculated by our third party delivery partner.

The component reads `response.disclaimer` (server-sent literal) — do NOT hardcode a second copy in the template; render the field value. (Fallback constant allowed only if the field is ever absent; W2 always ships it.)

---

## 1. Service + model rework — `meesell-angular-service-builder`

**Files owned:** `frontend/apps/mfe-pricing/src/app/pricing.model.ts`, `pricing.service.ts`, `pricing.utils.ts`.

### 1.1 `pricing.model.ts` — total rewrite to the W2 contract
- **DELETE** the entire wrong contract: `PriceCalcRequest{input_cost, target_margin_pct}`; response fields `mrp/meesho_price/seller_price/commission_pct(as-output)/commission_amount/gst_pct/gst_amount/profit/profit_pct`; `AlertCode` union `LOW_MARGIN/HIGH_MRP_MULTIPLIER/THIN_PROFIT`; `PriceCalcCommissionMissingError`; the `ALERT_MESSAGES` keys `pricing.low_margin/high_mrp_multiplier/thin_profit`.
- **NEW** `PriceCalcRequest`:
  ```ts
  export interface PriceCalcRequest {
    selling_price: string;          // Decimal>0, 2dp
    commission_pct?: string;        // optional; omit the key when not overriding
  }
  ```
- **NEW** `PriceCalcResponse` — exactly the W2 §2.2 fields, all money as `string`:
  `selling_price, shipping, total_price, commission_pct, commission_fees, gst_on_shipping, tds, tcs, estimated_bank_settlement` (string) + `disclaimer: string` + `alerts: PriceCalcAlert[]` + `calculated_at: string`.
- **NEW** `PriceCalcAlert`: `{ code: 'NEGATIVE_SETTLEMENT'; message_id: string; severity: 'warning' }`. `AlertCode = 'NEGATIVE_SETTLEMENT'` (single literal). `AlertSeverity = 'warning'`.
- **Typed error shapes** (rename `commission_missing` → category-pricing):
  - `PriceCalcUnavailableError { kind:'unavailable'; reason:'flag_off'|'not_found' }` (404) — KEEP.
  - **NEW** `PriceCalcNoPricingDataError { kind:'no_pricing_data'; detail:string; error_code:string }` (422 `pricing.category.no_pricing_data`) — replaces `commission_missing`.
  - `PriceCalcValidationError { kind:'validation'; detail:string }` (400/422 Pydantic) — KEEP.
  - `PriceCalcServerError { kind:'server_error' }` (5xx/network) — KEEP.
  - `PriceCalcErrorShape` = union of the above 4.
- **`ALERT_MESSAGES`** static map → single entry: `'pricing.alert.negative_settlement': 'This selling price results in a negative settlement — the fees exceed your price.'` (transloco still unwired — Wave-2B drop; render `ALERT_MESSAGES[message_id] ?? message_id`). Match the W2 i18n key name (`pricing.alert.negative_settlement`) — flag to i18n owner if W2's `message_id` differs.

### 1.2 `pricing.service.ts` — adapt to the new shapes
- `calc(productId, body: PriceCalcRequest)` — POST via `inject(ApiClient)` from `@mesell/core` (jwtInterceptor attaches Bearer; NO raw HttpClient, NO manual auth headers). KEEP `retryOn503` **OFF** (POST non-idempotency — the existing comment stands).
- `_handleError` degradation matrix:
  - `401` → `EMPTY` (refresh/logout owns it) — UNCHANGED.
  - `404` → `PriceCalcUnavailableError` (flag-off vs not_found by detail sniff) — UNCHANGED.
  - **`422`** → branch on `error_code`/detail: if `pricing.category.no_pricing_data` → `PriceCalcNoPricingDataError`; else (Pydantic field constraint, e.g. `selling_price<=0`) → `PriceCalcValidationError`. (W2 maps unknown-category to 422 with that code; Pydantic body-validation also returns 422 — disambiguate by `error_code`.)
  - `400` → `PriceCalcValidationError` (defensive; W2 primarily uses 422).
  - `5xx`/non-HTTP → `PriceCalcServerError`.
- NEVER a local-math fallback (the wrong model's client P&L is dead — AUTO-REJECT if re-introduced).

### 1.3 `pricing.utils.ts` — keep, extend formatting
- KEEP `parseDecimal(string|number)` and `formatRupee`. **CHANGE** `formatRupee` to show 2-decimal paise precision (settlement is ₹61.78 — rounding to whole rupees would hide the paise the model is proven to). Use `n.toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})` → `"₹61.78"`. Add `formatPct(string|number)` → `"x%"` for the commission row label.

---

## 2. Component rework — `meesell-angular-component-builder`

**Files owned:** `frontend/apps/mfe-pricing/src/app/pricing.component.ts`.

### 2.1 Reactive form (selling-price-driven; net-profit DEFERRED)
- `FormBuilder` group:
  - `selling_price`: `['', [Validators.required, Validators.min(0.01)]]` (>0; numeric).
  - `commission_pct`: `['', [Validators.min(0), Validators.max(100)]]` — OPTIONAL; when blank/empty the service body OMITS the key (do NOT send `""`).
- **DELETE** all wrong-model controls: `input_cost`, `target_margin_pct`, margin slider, MRP-as-input. No output-GST / landed-cost / net-profit controls (V1.5).
- OnPush; signals for `loading`, `result: PriceCalcResponse|null`, `errorState: PricingErrorState`.
- `onCalculate()`: build `{ selling_price: String(value), ...(commissionPct ? {commission_pct:String(commissionPct)} : {}) }`; set loading; subscribe to `service.calc(productId, body)`.

### 2.2 Result → UI row mapping (mirror Meesho — EXACT rows, V1 final)
On a 200 `PriceCalcResponse`, render the breakdown card with these rows in order; each maps one response field to one row via `formatRupee`:

| UI row label | Response field | Notes |
|---|---|---|
| Selling price | `selling_price` | echo of input; plain row |
| Commission fee (`{commission_pct}%`) | `commission_fees` | label interpolates `commission_pct` via `formatPct`; shown even when 0% (`Commission fee (0%) → ₹0.00`) |
| GST | `gst_on_shipping` | label just "GST" (it is the 18%-on-shipping term); deduction |
| TDS | `tds` | deduction |
| **Estimated Bank Settlement** | `estimated_bank_settlement` | **HEADLINE** — emphasized row (see styler §4) |
| _disclaimer_ | `disclaimer` | muted fine-print rendered BELOW the headline (not a table row) |

- **`tcs`** is always `"0.00"` and is NOT shown as a row (zero, no Meesho line for it) — but DO read it from the contract so the model stays exhaustive. (If founder later wants it visible, it's a one-row add.)
- **DO NOT render** any of: full-shipping deduction line, WDRP price, fabricated logistics/fixed fees, input-cost, margin, net-profit, output-GST, landed-cost, MRP-as-output. (grep gate — §5.)
- `shipping` and `total_price` are returned by the contract but are NOT primary breakdown rows in the Meesho-mirror layout (shipping is buyer-paid pass-through; the seller only bears GST-on-it). OPTIONAL: a small muted "Shipping (buyer-paid): ₹{shipping}" context line MAY be shown to explain why GST is small — styler's call (§4). Default = omit to keep the card clean; do not invent a deduction from it.

### 2.3 States (degradation — bind to service shapes)
- **loading** → `mee-spinner` (the ui-kit `MeeSpinnerComponent` is now available — frozen-surface PR #176 merged; REMOVE the local `.mee-pricing__spinner` CSS bridge + the `:host --mee-color-surface-variant` stopgap, which is now Layer-1 per #176).
- **idle / first-visit** → "Enter a selling price to estimate your settlement" empty state.
- **`unavailable`** (404) → "Price Calculator unavailable" banner (flag-off or product-not-found wording by `reason`).
- **`no_pricing_data`** (422) → inline message "Pricing isn't available for this category yet" (surface `detail`). This is the §1 422 path — render gracefully, NOT a crash/500.
- **`validation`** (400/422-Pydantic) → inline field error near the input.
- **`server_error`** (5xx/network) → `mee-alert-banner` with a retry affordance (re-fire `onCalculate()`).
- **negative-settlement alert** → when `response.alerts[]` contains `NEGATIVE_SETTLEMENT`, render a `warning` `mee-alert-banner` ABOVE/beside the settlement row, copy from `ALERT_MESSAGES[message_id] ?? message_id`. The settlement row still shows the (negative) value, styled as a warning.
- Surface errors via inline banners (the file's house style; `MeeAlertBanner`) — snackbar optional but inline is the established pattern in this component.

### 2.4 Imports stay boundary-clean
Keep the existing import set (`@mesell/composites`: MeeAlertBanner, MeeOfflineBanner, PageHeader; `@mesell/ui-kit`: MeeBadge, MeeButton, MeeCard, MeeInput) + ADD `MeeSpinner` from `@mesell/ui-kit`. ZERO `primeng` imports outside `libs/ui-kit` (boundary gate). Barrel imports only (`@mesell/ui-kit`, NOT `@mesell/ui-kit/spinner` subpath — F-001 lesson: subpath imports of shared packages break Native-Federation runtime).

---

## 3. Styling — `meesell-angular-ui-styler`

**Files owned:** the `styles: [...]` block inside `pricing.component.ts` (component-scoped CSS only — this MFE has no separate `.scss`).

- **Breakdown card:** Tailwind + the existing `mee-card` shell; a clean two-column table (label left muted, value right, tabular-nums for rupee alignment). Mobile-first — Tirupur sellers on 360px phones: the card must be single-column-friendly, no horizontal scroll, large tap targets on the input + Calculate button.
- **Headline emphasis:** "Estimated Bank Settlement" row is visually dominant — larger font weight/size, primary token colour, a top divider separating it from the deduction rows. It is the answer the seller came for.
- **Deduction rows** (Commission/GST/TDS): muted, smaller, with a leading "−" or right-aligned negative styling so they read as subtractions from selling price.
- **Disclaimer:** muted fine-print (`--mee-color-on-surface-muted`, ~12px) directly under the headline. Never primary-coloured; it is a caveat, not a CTA.
- **Negative-settlement state:** the headline value turns warning/red; the `mee-alert-banner` uses the warning token.
- **a11y:** input has an associated `<label>`; Calculate button keyboard-reachable; colour contrast ≥ WCAG AA on the headline + disclaimer (disclaimer muted but still ≥4.5:1); `aria-live="polite"` on the result region so the settlement is announced after calculate; spinner via `mee-spinner` (already `role=status`/`aria-busy`). NO hardcoded hex — all `var(--mee-*)` tokens (the local `--mee-color-surface-variant` stopgap is REMOVED; now resolves from Layer-1 per #176).

---

## 4. Tests

**Files:** `frontend/apps/mfe-pricing/src/app/pricing.service.spec.ts`, `pricing.component.spec.ts`.

### 4.1 Service spec (`meesell-angular-service-builder`)
- Posts the NEW body: `{selling_price:"70"}` (no commission key) → asserts request body shape; with override `{selling_price:"100", commission_pct:"2"}` → asserts both keys sent.
- Parses a real `PriceCalcResponse` fixture (the ₹61.78 case) — `Number(res.estimated_bank_settlement) === 61.78`.
- **422 `pricing.category.no_pricing_data`** → flush a 422 with that `error_code` → asserts emitted `{kind:'no_pricing_data'}` (REAL flush via HttpTestingController + firstValueFrom; reverting the mapping must fail the test — not tautological).
- 422 Pydantic (no that code) → `{kind:'validation'}`; 404 → `{kind:'unavailable'}`; 5xx + network → `{kind:'server_error'}`; 401 → EMPTY (firstValueFrom rejects).

### 4.2 Component spec (`meesell-angular-component-builder`)
- **₹61.78 fixture** (the golden anchor): selling 70 → settlement 61.78. Fixture: `{ selling_price:"70.00", shipping:"45.00", total_price:"115.00", commission_pct:"0.00", commission_fees:"0.00", gst_on_shipping:"8.10", tds:"0.12", tcs:"0.00", estimated_bank_settlement:"61.78", disclaimer:"<verbatim>", alerts:[], calculated_at:"2026-06-19T00:00:00Z" }`. Drive `onCalculate()`, assert the rendered card shows the 5 core rows + the formatted values (`₹70.00`, `Commission fee (0%) → ₹0.00`, GST `₹8.10`, TDS `₹0.12`, **Estimated Bank Settlement ₹61.78**) and the disclaimer text.
- **"Estimated Bank Settlement" label present** + emphasized container present.
- **Negative-settlement alert**: fixture with `estimated_bank_settlement:"-5.00"` + `alerts:[{code:'NEGATIVE_SETTLEMENT', message_id:'pricing.alert.negative_settlement', severity:'warning'}]` → asserts the warning banner renders (red/warning state).
- **422 handling**: service emits `{kind:'no_pricing_data'}` → component renders the "Pricing isn't available for this category yet" inline message (NOT a crash, NOT the empty state).
- **GREP GATE (zero dead tokens):** the spec/component contain ZERO references to `target_margin_pct`, `input_cost`, `seller_price`, `meesho_price`, `commission_amount`, `gst_pct`, `profit`, `HIGH_MRP_MULTIPLIER`, `THIN_PROFIT`, `LOW_MARGIN`, `net_profit`, `output_gst`, `landed_cost`, `wdrp`, `mrp`, `logistics_fee`, `fixed_fee`. (Lead enforces at merge-gate via `grep`.)

---

## 5. File ownership map (no overlap; W3 touches NO backend/export/docs)

| File | Owner | Action |
|---|---|---|
| `frontend/apps/mfe-pricing/src/app/pricing.model.ts` | service-builder | total rewrite → W2 contract DTOs + 4 error shapes + single alert + ALERT_MESSAGES |
| `frontend/apps/mfe-pricing/src/app/pricing.service.ts` | service-builder | new request/response; 422 `no_pricing_data` mapping; retryOn503 stays OFF |
| `frontend/apps/mfe-pricing/src/app/pricing.utils.ts` | service-builder | `formatRupee` 2dp paise + `formatPct`; keep `parseDecimal` |
| `frontend/apps/mfe-pricing/src/app/pricing.service.spec.ts` | service-builder | rewrite to new body/shapes + 422 real-flush |
| `frontend/apps/mfe-pricing/src/app/pricing.component.ts` (logic + template) | component-builder | reactive form (selling_price + optional commission); 5-row breakdown + disclaimer; state matrix; MeeSpinner; remove wrong-model UI |
| `frontend/apps/mfe-pricing/src/app/pricing.component.ts` (`styles:[...]` block) | ui-styler | breakdown card, headline emphasis, disclaimer fine-print, negative-state, a11y, mobile-first; remove local spinner CSS + surface-variant stopgap |
| `frontend/apps/mfe-pricing/src/app/pricing.component.spec.ts` | component-builder | ₹61.78 fixture, 5-row render, negative alert, 422 handling, grep gate |
| `frontend/apps/mfe-pricing/src/app/public-api.ts` | (no change) | still exports `PricingComponent` only |

**Build-order:** service-builder (model+service+utils) → component-builder (component logic+template+spec) → ui-styler (styles+a11y) last. ui-styler edits ONLY the `styles:[...]` block; component-builder owns the template markup — coordinate the seam (styler classes the structure component-builder authors). Both edit the same file → SERIAL, not parallel, on `pricing.component.ts`.

**W3 does NOT touch:** `backend/**` (W2/W4), `docs/V1_FEATURE_SPEC.md` / `docs/BACKEND_ARCHITECTURE.md` (W5 — LOCKED, founder-gated), `libs/**` (frozen shared surfaces — boundary 0), any export file (`apps/mfe-export/**`).

---

## 6. Merge-gate checklist (lead, step-3)

- PR template `.github/PULL_REQUEST_TEMPLATE/frontend.md` fully filled, no `<>` placeholders.
- `pnpm build` for `mfe-pricing` + `shell` < 90s (D12); bundle delta noted (the wrong-model removal + MeeSpinner should be ~neutral).
- Screenshots at 360px + 1280px (native-fed headless caveat → if unavailable, founder Gate-5 UI-review note, SP01-07 precedent).
- a11y: keyboard nav, contrast on headline + disclaimer, `aria-live` result region.
- CI gates 1 (unit) + 3 (lint) GREEN.
- GREP GATE PASS (§4.2 dead-token list = 0 in live code).
- §6.G singleton non-drift: exactly ONE `_mesell_core` chunk in mfe-pricing dist; ApiClient/AuthService not inlined.
- boundary 0 (no primeng outside libs/ui-kit), deep-import 0, localStorage/sessionStorage/withCredentials 0 (FE-D5).
- board row `IN REVIEW` (specialist sets on PR-open per D2); lead flips `MERGED` on merge.

---

## 7. MERGE-COORDINATION NOTE (CRITICAL — flag to master session)

**W3 MUST reach develop together-with or immediately-after W2.** The request rename is a BREAKING change with `extra="forbid"`:
- Old FE body `{input_cost, target_margin_pct}` → W2 backend 422s (`extra="forbid"` rejects unknown fields).
- New FE body `{selling_price, commission_pct?}` → only valid once W2 ships the new request schema.
- If W2 lands on develop WITHOUT W3, the live pricing calculator 422s on every calculate (old body vs new `extra="forbid"` schema). If W3 lands WITHOUT W2, the new body hits the old schema and 422s the other way.

**Action for the master/section session:** merge W2 (`feature/section-7/backend`) and W3 (`feature/section-7/frontend`) into `feature/section-7/integration` as a PAIR, and have the founder gate `feature/section-7/integration → develop` carry BOTH (or W3 immediately behind W2 with no develop window in between). The section-coordinator owns the integration→develop gate, not this lead (D1).

**Static-remote rebuild:** after the integration→develop merge, the **`mfe-pricing` remote at :4201 (static serve.js build)** MUST be rebuilt (`ng build mfe-pricing` → restart :4201) per the localhost federation rebuild workflow — the shell at :4200 federates to the static build and will NOT pick up the change on a plain refresh. Owner = the localhost-monitoring/master session post-merge.

**i18n follow-up (non-blocking):** the alert `message_id` key (`pricing.alert.negative_settlement`) + optional `pricing.disclaimer` key → flag to the i18n owner. transloco is unwired (Wave-2B drop); V1 renders the static `ALERT_MESSAGES` map + the server-sent `disclaimer` literal. Coordinate the exact key name with W2's `message_id` value to avoid a blank render (the `validation.generic.missing` class of bug — see master memory).
