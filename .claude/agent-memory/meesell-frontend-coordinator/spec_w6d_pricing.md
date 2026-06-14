# SPEC — Wave 6 Wave D Lane 2 · `wave6-pricing`

**Author:** MeeSell Frontend Lead · session `mesell-wave6-d-specs-session-1` · 2026-06-12
**Type:** HYBRID step-1 TASK SPEC (SPEC ONLY — no code, no dispatch, no git this session)
**Slice:** `wave6-pricing` (apps/mfe-pricing — pricing page, `/catalogs/:id/pricing`)
**Base for authoring:** develop `b348dac`. **Base for the BUILD:** develop at dispatch (re-count baseline). **Can branch at dispatch** — no intra-remote sequence gate (mfe-pricing is a solo remote, disjoint from images/mfe-catalog).
**Parallel peer:** lane 1 `wave6-images` (apps/mfe-catalog) — FILE-DISJOINT (different remote).
**Master plan:** `docs/plans/wave6_api_wiring/MASTER_PLAN.md` §4.2 Wave D lane 2 + §1.2 row 25 + §7 DECISION-1 (SERVER-calc, RULED) + R-W6-6 (Decimal wire-type).

---

## 0. ONE-PARAGRAPH SUMMARY — this is a REBUILD of the input model, not a swap

Founder RULED (§7 DECISION-1, 2026-06-11): **pricing is SERVER-calc.** Wire `mfe-pricing` to `POST /api/v1/products/{id}/price-calc` (#25) and RETIRE the client-side P&L math. ⛔ **The catch (ground-truthed from both sides): the as-built FE input model is INCOMPATIBLE with the backend request, not just renamed.** The FE form collects `{mrp, target_margin}` (MRP = selling price, the seller sets it; +a native MRP slider) and `computePnlBreakdown(mrp, margin)` derives meesho_price=`mrp*0.5` with hardcoded `COMMISSION_PCT=5/GST_PCT=5`. The backend `POST /price-calc` expects `{input_cost: Decimal (COGS, gt 0), target_margin_pct: Decimal (0-500, %)}` and **computes mrp/meesho_price/seller_price ITSELF** from category commission/GST tables (which drift — the whole reason server-calc was ruled). So `mrp` (FE input) is a backend OUTPUT, and `input_cost` (backend input) does NOT exist in the FE form at all. **This is a form REBUILD: replace the MRP-input + MRP-slider with an `input_cost` input + a `target_margin_pct` input; MRP becomes a server-returned RESULT row.** The client `computePnlBreakdown` + `COMMISSION_PCT`/`GST_PCT` constants DIE entirely; `formatRupee` SURVIVES as a display helper. Plus R-W6-6: the response is all `Decimal` — verify the JSON wire-type (string vs number) before authoring the TS interface (backend has NO `json_encoders`/float config, so FastAPI/Pydantic v2 serialises `Decimal`→JSON **string** by default — the TS interface fields are `string`, parsed for display).

---

## 1. Contract inventory — DTOs cited file:line (schema = source of truth)

`pricing_router` mounted **UNCONDITIONALLY** in `backend/app/main.py:134` — BUT the handler is FLAG-GATED internally by `FEATURE_PRICE_CALCULATOR_ENABLED` (`pricing/router.py:96-99` → **404** when off). Verified MOUNTED (the row-26 lesson — `main.py:47` import + `:134` include + `router.py:71 response_model=PriceCalcResponse`).

| # | Method · Path | Request | Response | Source of truth (file:line) | Codes |
|---|---|---|---|---|---|
| 25 | `POST /products/{id}/price-calc` | `PriceCalcRequest{input_cost:Decimal(gt 0,2dp), target_margin_pct:Decimal(ge 0,le 500,2dp,default 30), override_commission_pct?:Decimal\|null, override_gst_pct?:Decimal\|null}` (extra=forbid) | **200** `PriceCalcResponse{mrp, meesho_price, seller_price, commission_pct, commission_amount, gst_pct, gst_amount, profit, profit_pct, alerts[], calculated_at}` | req `pricing/schemas.py PriceCalcRequest`; resp `pricing/schemas.py PriceCalcResponse`; handler `pricing/router.py:69-99` (`response_model`, `status_code=200`, `@rate_limit(scope="price_calc", limit=600, window=3600)`); flag-guard `:96` | 200; 400 (`validation.price.invalid_input` — Pydantic constraint fail); 401; 404 (flag-off OR product not found/cross-tenant); 422 (`pricing.commission.missing` — category has no usable commission rate) |

**Exact shapes (transcribed field-for-field from `pricing/schemas.py`):**
```
PriceCalcRequest {                    # body
  input_cost: Decimal                 # gt 0, decimal_places=2 — COGS per unit, INR (REQUIRED, no default)
  target_margin_pct: Decimal          # ge 0, le 500, 2dp, DEFAULT 30 — profit % of input_cost
  override_commission_pct: Decimal|null  # V1.5 Pro override — V1 IGNORES it. Send omitted/null.
  override_gst_pct: Decimal|null         # V1.5 Pro override — V1 IGNORES it. Send omitted/null.
}
PriceCalcResponse {                   # 200
  mrp:               Decimal          # ← server-COMPUTED (was a FE INPUT in the mock)
  meesho_price:      Decimal
  seller_price:      Decimal
  commission_pct:    Decimal          # server-resolved from category table (NOT hardcoded 5)
  commission_amount: Decimal
  gst_pct:           Decimal          # server-resolved (NOT hardcoded 5)
  gst_amount:        Decimal
  profit:            Decimal
  profit_pct:        Decimal
  alerts: PriceCalcAlert[]
  calculated_at:     datetime
}
PriceCalcAlert {
  code:       'LOW_MARGIN' | 'HIGH_MRP_MULTIPLIER' | 'THIN_PROFIT'
  message_id: str                     # validation_message_id — RESOLVED CLIENT-SIDE via i18n (§5A.H)
  severity:   'warning' | 'info'
}
```

### 1.1 ⛔ R-W6-6 — Decimal wire-type (VERIFY at dispatch, baked resolution here)
All monetary/pct fields are Python `Decimal`. The backend has **NO `json_encoders` and NO float coercion** (`grep json_encoder/float pricing/schemas.py + main.py` = none — verified). **Pydantic v2 + FastAPI serialise `Decimal` → JSON STRING by default** (e.g. `"899.00"`, not `899`). **Therefore the TS interface fields are `string`** (not `number`), and the component parses them (`Number(res.mrp)` or keeps string for display via `formatRupee`). **R-W6-6 resolution:** TS interface = `string` for mrp/meesho_price/seller_price/commission_pct/commission_amount/gst_pct/gst_amount/profit/profit_pct; `calculated_at` = ISO `string`. **At dispatch, the service-builder MUST confirm the actual serialised shape** against a live/Gate-4 sample (one `curl` or a Gate-4 fixture) before finalising — if it comes back as `number`, flip the interface. **DO NOT GUESS number** — the default is string; assume string, verify, flip only on evidence. NaN-in-P&L is the R-W6-6 failure mode if this is wrong.

---

## 2. As-built state on develop (what DIES vs what SURVIVES)

Files (all under `apps/mfe-pricing/src/app/` — FLAT, no `pricing/` subdir):
- `pricing.component.ts` — OnPush standalone. Reactive form `{mrp:[899], target_margin:[150]}` + native MRP range slider (100-5000). `onCalculate()` is **SYNCHRONOUS client-calc**: `breakdown.set(computePnlBreakdown(mrp, margin))`. Renders a P&L table (MRP, Meesho Price, Commission %, GST %, Seller Payout, Net Margin, Net Margin %) + POSITIVE/NEGATIVE badge + "Shipping not included in V1" disclaimer + Save&Continue→`/catalogs/:id/export`. `calculating` signal exists "Reserved for future async API wiring." NO service, NO HttpClient, NO inject of ApiClient.
- `pricing.utils.ts` — **`computePnlBreakdown(mrp, margin)` (the client math: `meesho_price=mrp*0.5`, `COMMISSION_PCT=5`, `GST_PCT=5`, derived amounts) ← DIES.** `formatRupee(amount)` (Indian-rupee string) ← **SURVIVES** as a display helper.
- `pricing.model.ts` — `PnlBreakdown{mrp, meesho_price, commission_pct, commission_amt, gst_pct, gst_amt, seller_payout, net_margin, net_margin_pct}` (all `number`, mock keys) ← REPLACED by the real DTOs. `PriceCalcRequest{mrp, target_margin}` (mock) ← REPLACED.
- `pricing.component.spec.ts` (the only spec; mfe-pricing = 1 spec file on develop) + `public-api.ts`.

### 2.1 What dies / what survives (precise)
| Symbol | Fate |
|---|---|
| `computePnlBreakdown` + `COMMISSION_PCT` + `GST_PCT` (pricing.utils.ts) | **DIE** — server computes commission/GST from category tables |
| `formatRupee` (pricing.utils.ts) | **SURVIVES** — display helper (adapt to accept string\|number) |
| `PnlBreakdown` interface (pricing.model.ts) | **REPLACED** by `PriceCalcResponse` DTO (real keys: `commission_amount` not `commission_amt`, `seller_price`, `profit`/`profit_pct` not `net_margin`/`net_margin_pct`) |
| `PriceCalcRequest{mrp, target_margin}` (mock) | **REPLACED** by real `PriceCalcRequest{input_cost, target_margin_pct}` |
| `form{mrp, target_margin}` + MRP slider + `sliderMrp`/`onSliderInput`/`onMrpInput` | **REBUILT** → `form{input_cost, target_margin_pct}`. MRP is now a RESULT, not an input — drop the MRP slider (it adjusted an input that no longer exists). (If the founder wants to keep a slider, it would adjust `target_margin_pct` — see AMBIGUITY-2.) |
| P&L table rows | **REMAP** to real keys + ADD `seller_price`/`profit`/`profit_pct` rows; commission/GST % now from server (not literal 5) |
| POSITIVE/NEGATIVE badge | keep, drive off `profit > 0` (was `net_margin > 0`) |
| `alerts[]` rendering | **NEW** — render server alerts (severity warning/info, message_id→i18n) |
| `onSaveContinue()` → `/catalogs/:id/export` | keep (unchanged) |

---

## 3. THE SERVER-CALC WIRE (the work)

### 3.1 Degradation matrix (P0 — R-W6-1, the founder's explicit "never silently-wrong local math")
DECISION-1 said the retired client math must NOT silently re-appear. **Pricing without backend = an EXPLICIT ERROR STATE, never a fallback to local arithmetic.** The merge gate REJECTS any `computePnlBreakdown`-style fallback. Matrix:
- **401** → `refreshInterceptor` handles (Wave A); if it reaches the service, EMPTY + ErrorService (logout path).
- **404** (flag-off `FEATURE_PRICE_CALCULATOR_ENABLED` OR product not found) → graceful: "Price Calculator is unavailable" banner (MeeAlertBanner) + the breakdown stays empty. NO local math.
- **422** (`pricing.commission.missing`) → actionable message: "Pricing isn't available for this category yet" + surface `error_code`/`detail`. NO retry.
- **400** (`validation.price.invalid_input`) → caller-validated; show field error (the form should prevent most via Validators).
- **5xx** → "Couldn't calculate price — try again" + retry affordance (re-submit). NOT local math.
- **offline** → MeeOfflineBanner (NetworkService.online).
- The breakdown signal stays `null` on any error → the existing `@else` empty-state copy shows (adapt copy to "calculation unavailable" vs "enter values").

### 3.2 ⛔ retry: ApiClient `retryOn503` is DEFECTIVE — do NOT use it
`ApiClient.applyRetry` (`api-client.service.ts:35-46`) = `retry({count:2, delay:timer(n*1000)})` with **NO error-status filter** — retries on ANY error (400/422/401/network). On a POST it would also be **non-idempotent double-fire risk**. **This lane uses NO ApiClient retry.** `price-calc` is a POST — even a correct 503-only retry would be questionable on a non-idempotent verb (though price-calc has no side effects, it's a pure compute — but the FE treats it as POST). If a transient-retry affordance is wanted, use the **export-lane layered pattern** (a user-driven "try again" button re-submitting, NOT an automatic ApiClient retry). Default: NO retry, explicit 5xx error + manual re-submit. This defect is in the frozen-surface amendment bundle (post-Wave-D §7.3 chore).

### 3.3 Debounce (R-W6-6 latency note)
The mock recomputed synchronously on every input/slider move. The server round-trip must NOT fire on every keystroke. **Wire calc to the explicit "Calculate" button** (already exists) — do NOT auto-fire on input change. (If a live-recalc-on-change UX is wanted later, debounce ≥400ms per the smart-picker precedent — but V1 = button-triggered, simplest + cheapest.)

---

## 4. Exact edits (file-by-file)

All under `apps/mfe-pricing/src/app/` (+ specs). **NO file outside `apps/mfe-pricing/**`.** Shared surfaces FROZEN: `libs/**` (Wave-A ApiClient/interceptors), shell, `apps/mfe-pricing/src/main.ts` (interceptor registration done Wave A — confirmed present, do NOT touch).

### 4.1 `pricing.model.ts` (REPLACE the mock interfaces)
- ADD `PriceCalcRequest{input_cost: string, target_margin_pct: string}` (send as strings to preserve Decimal precision, OR numbers if backend accepts — Pydantic Decimal accepts JSON number AND string; SAFEST is string to avoid float rounding. Verify at dispatch). Omit the V1.5 overrides (do not send them).
- ADD `PriceCalcResponse` (all 9 monetary/pct fields as `string` per §1.1, `alerts: PriceCalcAlert[]`, `calculated_at: string`) + `PriceCalcAlert{code, message_id, severity}` — transcribe field-for-field.
- REMOVE `PnlBreakdown` + the mock `PriceCalcRequest{mrp, target_margin}`.

### 4.2 `pricing.utils.ts` (gut the math, keep the formatter)
- **DELETE** `computePnlBreakdown`, `COMMISSION_PCT`, `GST_PCT`.
- **KEEP** `formatRupee` — adapt signature to `formatRupee(amount: string | number): string` (parse string Decimal → format). Add a tiny `parseDecimal(s: string): number` helper if needed for the POSITIVE/NEGATIVE computed + margin coloring.

### 4.3 `pricing.service.ts` (NEW — `apps/mfe-pricing/src/app/pricing.service.ts`)
- `@Injectable()` route/component-scoped (provided via `PricingComponent.providers[]` — D28a/D32, tree-shakes with the route chunk; mirror #161 DashboardApiService + export-lane). Inject `ApiClient` from `@mesell/core` (NOT raw HttpClient — interceptors via main.ts).
- `calc(productId: string, body: PriceCalcRequest): Observable<PriceCalcResponse>` → `this.api.post<PriceCalcResponse>('/api/v1/products/' + productId + '/price-calc', body)`. **NO retryOn503** (§3.2).
- `catchError` matrix per §3.1 (401/404/422/400/5xx → typed error surface; NEVER a local-math fallback).

### 4.4 `pricing.component.ts` (REBUILD the input model, wire the service)
- Inject `PricingApiService` (add to `providers:[PricingApiService]`), keep `ActivatedRoute` (`productId`) + `Router`.
- **REBUILD the form:** `{ input_cost: [<sensible default e.g. 300>, [Validators.required, Validators.min(0.01)]], target_margin_pct: [30, [Validators.required, Validators.min(0), Validators.max(500)]] }`. Labels: "Input cost (COGS per unit)" + "Target margin %". **DROP the MRP slider + `sliderMrp`/`onSliderInput`/`onMrpInput`** (MRP is now a result). Field error computed signals adapt to the new controls.
- `onCalculate()`: if form valid → `calculating.set(true)` → `service.calc(productId, {input_cost: String(...), target_margin_pct: String(...)})` → subscribe: next → map response into a `breakdown` signal (now `PriceCalcResponse|null`), `calculating.set(false)`; error → matrix (§3.1), `breakdown.set(null)`, set an `errorState` signal. **NO synchronous local compute.**
- **REMAP the P&L table** to real keys: MRP (`res.mrp`), Meesho Price (`res.meesho_price`), Seller Price (`res.seller_price` — NEW row), Commission (`res.commission_pct`% → `res.commission_amount`), GST (`res.gst_pct`% → `res.gst_amount`), Profit (`res.profit` — was "Net Margin"), Profit % (`res.profit_pct`). `marginIsPositive` computed off `parseDecimal(res.profit) > 0`.
- **ADD alerts rendering:** for each `res.alerts`, a MeeBadge/MeeAlertBanner with severity (warning/info) + message resolved from `message_id` (i18n — if no transloco wired, render `message_id` as a stable key or a static map; note the i18n gap, do not invent copy). Keep simple — a list of alert chips.
- Keep `onSaveContinue()` → `/catalogs/:id/export`. Keep the "Shipping not included in V1" disclaimer.

### 4.5 Specs
- `pricing.service.spec.ts` (NEW): TestBed provides `ApiClient` + `provideHttpClientTesting()`; assert calc URL `/api/v1/products/{id}/price-calc` + body `{input_cost, target_margin_pct}` (NOT mrp/target_margin); response→breakdown mapping; full error matrix (401/404/422/400/5xx → NO local-math fallback); NO retryOn503. Decimal-string parsing tested.
- `pricing.component.spec.ts` (EDIT): drop client-math tests; new form `{input_cost, target_margin_pct}`; calc→subscribe→table maps real keys; 404/422 error states; assert `computePnlBreakdown` is GONE (import removed). Re-confirm discovery under `spec-apps-mfe-pricing-*`.
- `public-api.ts` / model spec: drop `PnlBreakdown`/client-math exports if referenced.

---

## 5. Builder sequence (serial within the lane)
1. **meesell-angular-service-builder** — §4.1 model DTOs (R-W6-6 string-Decimal) + §4.3 NEW `pricing.service.ts` + §4.2 utils gut + §4.5 service/model specs. **MUST verify the Decimal wire-type first** (§1.1) — assume string, confirm, flip only on evidence. Report TRUE branch tip.
2. **meesell-angular-component-builder** — §4.4 form rebuild (input_cost/target_margin_pct, drop slider) + service wiring + table remap + alerts + §4.5 component spec. Branches off the service commit on the SAME `feature/wave6-pricing/frontend` branch.
3. **meesell-angular-ui-styler** — server-calc states (calculating spinner, error/404/422 banners, alert chips by severity, result table), 360px + 1280px, a11y (aria-live on result/error region). Last. **FROZEN-SURFACE GUARD header MANDATORY** (the dashboard-styler `_tokens.css` violation lesson — see §7).

Each dispatch prompt header:
```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/apps/mfe-pricing/.
SESSION: mesell-wave6-pricing-frontend-session-1
FROZEN (out-of-lane = STOP): libs/** (Wave-A ApiClient/interceptors + design-tokens), apps/mfe-pricing/src/main.ts (interceptor reg, Wave-A), shell, docs/status/* (LEAD sole-writer — report evidence in return text only).
TOKEN RULE (styler): an undefined var(--mee-*) → define LOCALLY in :host/styles or re-point to an existing token; NEVER edit libs/design-tokens/_tokens.css (Wave-A frozen).
RETRY RULE: ApiClient retryOn503 is DEFECTIVE — do NOT use it. price-calc is POST → NO auto-retry; explicit 5xx error + manual re-submit (export-lane pattern).
NO LOCAL MATH: the retired computePnlBreakdown must NOT reappear as any fallback — server-calc only; backend-unreachable = explicit error state.
Report your TRUE branch tip — do not infer.
```

---

## 6. Branch plan (Model C) — can branch at dispatch (NO intra-remote gate)
- mfe-pricing is a SOLO remote, disjoint from images/mfe-catalog → **no R-W6-9-style sequence gate; `wave6-pricing` can branch at dispatch** (does NOT wait on catalog-form). Runs in PARALLEL with `wave6-images` (different remotes).
- Worktree: `/tmp/mesell-wt/w6d-pri` off develop (at dispatch).
- `feature/wave6-pricing/integration` off develop (F3-protected: PR-only, review-count 0, strict-contexts [], no force-push, no delete). `feature/wave6-pricing/frontend` off integration (3 builders serial).
- Group PR frontend→integration: LEAD gates (HYBRID step-3), squash `--admin`. `git merge origin/develop` into integration (conflict-free expected — pricing `apps/mfe-pricing/**` disjoint from any concurrent images `apps/mfe-catalog/**`). Re-certify.
- Founder-gate PR integration→develop: OPEN + LEFT OPEN [FOUNDER GATE — DO NOT MERGE]. **Lead does NOT approve (D1).**
- Fresh-worktree native-build: `pnpm install --config.dangerously-allow-all-builds=true` (SP01 pricing-pilot proven, ~4s) OR `pnpm rebuild esbuild @parcel/watcher lmdb msgpackr-extract`; if esbuild won't extract, `cd node_modules/.pnpm/esbuild@<ver>/node_modules/esbuild && node install.js`. `./node_modules/.bin/ng build mfe-pricing` directly. Revert pnpm-workspace.yaml drift before commit. `ng test frontend` is the ONLY test target (`ng test mfe-pricing` ERRORS).
- Per-app run script convention exists: `start:mfe-pricing` (:4201) already in package.json (the ui-scripts chore).

---

## 7. Parallel-lane discipline (file-disjoint with lane 1 images)
- This lane touches ONLY `apps/mfe-pricing/**`. Lane 1 (images) touches ONLY `apps/mfe-catalog/src/app/images/**` → ZERO overlap, different remotes. Both integration branches cut from the SAME develop → union conflict-free (SP02‖SP03 + Wave-B precedent).
- **Frozen surfaces (out-of-lane = STOP):** `libs/core/**` (Wave-A ApiClient/interceptors/AuthService), `libs/ui-kit/**`, `libs/composites/**`, `libs/design-tokens/_tokens.css` (Wave-A frozen — the dashboard-styler `--mee-color-surface-variant` violation: an undefined token gets defined LOCALLY in `:host`, NEVER in the shared file), shell `app.config.ts`/`app.routes.ts`, `apps/mfe-pricing/src/main.ts`. Consuming `@mesell/*` barrels is READ-ONLY, allowed.
- **Barrel imports ONLY** from `@mesell/core`/`@mesell/ui-kit`/`@mesell/composites` (deep-import P0). The as-built pricing component already imports barrel `MeeBadge/Button/Card/Input` + `PageHeader` — keep barrel; ADD `MeeAlertBanner`/`MeeOfflineBanner` (Wave-A composites) for the degradation UI (confirm selectors at dispatch — they were NEW in Wave A).
- **Boundary:** 0 primeng outside ui-kit.
- **TRUE-tip reporting:** builders report `git rev-parse HEAD`; lead `git fetch` + `git rev-parse origin/<branch>` + `git diff --name-only base..REAL-TIP` (the dashboard styler's STATUS_FRONTEND.md sneak-commit lesson — a builder can push a follow-up after the SHA it names). NO unsanctioned `docs/status/*` commits (lead sole-writer).

---

## 8. Validation (lead gate — skeptical, re-run independently)
- **7 builds GREEN ≤90s (D12):** shell + 6 remotes. Record times (SP01 pilot: mfe-pricing fast).
- **Full suite green, no NET drop.** Baseline = RE-COUNT at dispatch (develop today = **57** spec files; concurrent images edits-in-place; count at branch time, do NOT hardcode). mfe-pricing currently = 1 spec (`pricing.component.spec.ts`); this slice ADDS `pricing.service.spec.ts` (+ maybe model spec) → count MUST RISE. Re-confirm `apps/mfe-pricing/**/*.spec.ts` discovery (`spec-apps-mfe-pricing-*`, R-W6-8).
- **Client math GONE:** `grep -rn "computePnlBreakdown\|COMMISSION_PCT\|GST_PCT\|mrp \* 0.5" apps/mfe-pricing/src/app` = 0. `formatRupee` MAY remain (display helper).
- **No local-math fallback in the service:** the `catchError` branches return error/EMPTY, NEVER a computed breakdown (R-W6-1, DECISION-1 — manual review of every catch branch).
- **ApiClient used, no retryOn503:** `grep "inject(ApiClient)" pricing.service.ts` present; `grep "retryOn503" apps/mfe-pricing/src/app` = 0; `grep "inject(HttpClient)" pricing.service.ts` = 0.
- **Contract greps:** URL matches §1 EXACTLY: `/api/v1/products/{id}/price-calc`. Request body keys = `input_cost` + `target_margin_pct` (NOT `mrp`/`target_margin`): `grep "input_cost\|target_margin_pct"` present; `grep "target_margin\b" | grep -v target_margin_pct` = 0 in the wire path.
- **Decimal wire-type confirmed** (§1.1) — service spec asserts string-Decimal parsing; PR body notes the verified serialised shape (string vs number).
- **Boundary 0:** `grep "from 'primeng" apps/mfe-pricing --include=*.ts | grep -v libs/ui-kit` = 0.
- **Deep-import 0 (P0):** `grep "@mesell/\(ui-kit\|composites\|core\)/" apps/mfe-pricing/src/app --include=*.ts` = 0 (barrel only).
- **localStorage/sessionStorage/withCredentials 0** (FE-D5; pricing has no cookie surface).
- **Singleton §6.G:** `PricingApiService`→ApiClient DI → confirm EXACTLY ONE `_mesell_core-*.js` chunk, no inline core dup (mfe-pricing previously had `@mesell/core` ABSENT from remoteEntry since it had no core consumer — NOW it consumes ApiClient via the service, so core SHOULD appear shared; re-run §6.G to confirm it's shared-singleton, NOT inlined into the pricing chunk). This is a NEW core consumer for this remote — extra scrutiny (the SP01 pilot had core absent; this changes that).
- **TS strict + strictTemplates:** tsc app + spec EXIT 0.
- **a11y + screenshots** 360px + 1280px (input form / calculating / result-table-with-alerts / 404-unavailable / 422-no-commission states). Native-fed headless screenshot caveat → substitute + flag to founder UI-review.
- **Disjointness diff gate:** `git diff --name-only develop...feature/wave6-pricing/frontend` = ALL under `apps/mfe-pricing/`.

---

## 9. STOP conditions (escalate to founder)
- Backend change required (the Decimal wire-type is a surprise, or a request-shape mismatch) = STOP + backend memo; no client shim.
- Drift beyond §1/§2/§3 documented = STOP (§5.3 contract-surprise).
- **Any local-math fallback** reintroduced (DECISION-1 violation) = AUTO-REJECT.
- ApiClient `retryOn503` used = AUTO-REJECT (the defect).
- Build > 90s; TS strict off; singleton dup `_mesell_core` chunk; deep-import reintroduced; branch open > 5 days.
- Any file outside `apps/mfe-pricing/**` (esp. `libs/design-tokens/_tokens.css`, `main.ts`, `docs/status/*`) = REJECT.

## 10. Acceptance (this slice COMPLETE)
1. pricing wired to #25 SERVER-calc: form `{input_cost, target_margin_pct}` → `POST /price-calc` → real `PriceCalcResponse` rendered (mrp/meesho_price/seller_price/commission/gst/profit/profit_pct + alerts). ZERO `computePnlBreakdown`/`COMMISSION_PCT`/`GST_PCT` client math.
2. MRP-input + MRP-slider replaced by input_cost input (MRP is now a server RESULT row).
3. Decimal wire-type verified (§1.1) + parsed correctly (no NaN).
4. Degradation matrix (§3.1): 404/422/5xx → explicit error state, NEVER local math (R-W6-1 + DECISION-1).
5. NO ApiClient retryOn503; service contract-tested (URL/method/body + matrix); model pure-tested.
6. 7 builds ≤90s; suite monotonic-rise no drop; boundary 0; deep-import 0; localStorage 0; singleton intact (core now shared for this remote, not inlined); tsc EXIT 0.
7. Group PR lead-gated to integration; founder-gate PR integration→develop OPEN (lead does NOT approve, D1).

## 11. Hand-offs (author at dispatch if needed, NOT now)
- **Backend memo (informational, low-priority):** confirm the Decimal serialised wire-type (string vs number) for `price-calc` — default-assumption is string (no json_encoders); a Gate-4 fixture or one curl settles it. Only escalate if it's a surprise.
- **AI:** none — pricing has NO AI surface (no autofill/precheck). No memo.
- **i18n note (NOT a memo, a flag):** `PriceCalcAlert.message_id` is meant to resolve client-side via i18n, but transloco is NOT wired (dropped in the Wave 2B re-scaffold — knowledge-sync finding). For V1, render `message_id` as a stable key OR a small static FE map (like image-precheck's `PRECHECK_HINTS`) — do NOT invent alert copy. Flag the i18n gap in the PR body; a transloco-enable chore is separate (post-Wave-D).

## 12. AMBIGUITIES (resolved, with resolution baked in — for founder/master-session)
- **AMBIGUITY-1 (the big one):** the FE input model (`mrp`) ≠ backend input (`input_cost`) — is this a rename or a rebuild? **RESOLUTION:** REBUILD — `input_cost` (COGS) is a genuinely different quantity from `mrp` (selling price, which the server now COMPUTES). The form must collect `input_cost` + `target_margin_pct`; MRP moves to the result table. Ground-truthed from `pricing/schemas.py` + the as-built component. This is the load-bearing catch — a naive builder would have mapped `mrp→input_cost` and shipped a wrong calculator.
- **AMBIGUITY-2:** keep the MRP slider? **RESOLUTION:** DROP it — it adjusted MRP, which is no longer an input. If the founder wants a slider UX, it would adjust `target_margin_pct` (0-500) — flag as an optional polish item, NOT default. V1 = two numeric inputs + Calculate button (simplest, matches server-calc round-trip model).
- **AMBIGUITY-3:** Decimal as string or number on the wire? **RESOLUTION:** STRING (Pydantic v2 + FastAPI default, no json_encoders confirmed). TS interface = `string`, parsed for display. VERIFY at dispatch with a live/Gate-4 sample; flip only on evidence (R-W6-6).
- **AMBIGUITY-4:** retry on the price-calc POST? **RESOLUTION:** NO ApiClient retry (defective §3.2) + it's a POST. Explicit 5xx error + a user-driven "try again" re-submit (export-lane pattern). NO auto-retry.
- **AMBIGUITY-5:** send the V1.5 override fields (`override_commission_pct`/`override_gst_pct`)? **RESOLUTION:** NO — omit them (V1 ignores them server-side; sending null is harmless but omitting is cleaner with `extra="forbid"` tolerating absence since they have defaults). Do NOT expose override inputs in the V1 UI.
- **AMBIGUITY-6:** `message_id` i18n resolution? **RESOLUTION:** transloco not wired (Wave-2B drop) → render via a small static FE map or the raw key; do NOT invent copy; flag the i18n gap. Separate transloco chore post-Wave-D.
