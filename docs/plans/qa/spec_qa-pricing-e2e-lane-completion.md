# SPEC A — qa-pricing E2E lane completion

**Author:** `meesell-qa-coordinator` (session `mesell-qa-wave-pricing-coord-session-1`)
**Date:** 2026-07-06
**Target specialist:** `meesell-e2e-test-writer` (opus) — two-phase explore-then-codify
**Target branch:** `feature/qa-pricing/e2e` → `feature/qa-pricing/integration` (lane merge = QA-lead gate; `integration → develop` = founder gate)
**Baseline:** develop @ `9ebc0d9`
**Skill:** `.claude/skills/meesell-e2e-testing/SKILL.md` (two-phase mandate, config-driven ports, visible-outcome assertions)

> This is a **test spec**, not an implementation. The e2e-test-writer executes it after a
> Director dispatch. Do NOT implement here.

---

## 0. Status correction (read first — the lane premise is STALE)

The board's qa-pricing Wave-C row is `BLOCKED (selectors)` on the premise *"mfe-pricing
ships ZERO data-testid."* **That premise is no longer true on develop `9ebc0d9`.** The
mfe-pricing data-testids landed (PR #439) AND a SPEC-C apply-price control was added since
the fixme comments were written (they were verified against the older develop `a94e013`).

**Consequence:** the "add data-testids to the pricing UI" part of this lane — the
frontend-coordinator scope — is **DONE**. There is **no missing data-testid** in mfe-pricing.
The lane completion is therefore an **E2E-authoring task**, not a cross-lead selector request.
The e2e writer must still LIVE-VERIFY every selector (two-phase mandate) before codifying.

---

## 1. Missing data-testid list — EXACT (verified in source @ `9ebc0d9`)

All selectors the pricing flows need already ship in
`frontend/apps/mfe-pricing/src/app/pricing.component.ts`:

| data-testid | Line | Element / wrapper | Renders when | Interaction rule |
|---|---|---|---|---|
| `pricing-cost-input` | 441 | `[testId]` on `mee-input` (selling_price) | on load | testid IS the inner `<input>` → `getByTestId(x).fill()` directly |
| `pricing-commission-input` | 452 | `[testId]` on `mee-input` (commission_pct) | on load | fill directly |
| `pricing-calculate-btn` | 463 | `[testId]` on `mee-button` host | on load | click the inner `<button>` (`.locator('button')`) |
| `pricing-breakdown` | 544 | native `data-testid` on result region | on load (populated after calc) | region present always; assert child values after calc |
| `pricing-negative-alert` | 563 | native `data-testid` | only when `breakdown().alerts.length > 0` | assert visible on negative settlement |
| `pricing-settlement-value` | 612 | native `data-testid` on headline `<td>` | after a successful calc | `toHaveText(/₹\s?-?\d/)` |
| `pricing-disclaimer` | 625 | native `data-testid` on `<p>` | after a successful calc | non-empty server copy |
| `pricing-apply-btn` | 682 | native `data-testid` on `<button>` (Save & Continue) | on load; `[disabled]` until `breakdown()` exists | click after a calc |
| `pricing-applied-status` | 705 | native `data-testid` on `<span>` | only after apply POST returns 204 | `toBeVisible()` + text "Price applied" |
| `pricing-apply-error` | 724 | native `data-testid` on `<span>` | only when apply POST errors | assert on the negative-apply path |

**Federation note (record in `selector_registry.md` at exploration):** the source comment at
L666-675 states federation strips `[testId]` on `mee-*` wrappers, so `pricing-apply-btn` /
`pricing-applied-status` / `pricing-apply-error` are placed on **native** DOM elements. But
`pricing-cost-input` / `pricing-commission-input` / `pricing-calculate-btn` still use the
`[testId]` passthrough on `mee-*` wrappers and were LIVE-VERIFIED green in the prior wave.
This mixed convention is a live-verify hotspot — confirm each testid resolves against the
running federated stack (not just the source) before codifying. The existing page object
`frontend/e2e/page-objects/pricing.page.ts` already encodes these rules; reuse it.

**Frontend-coordinator scope:** NONE for mfe-pricing. All pricing testids are present. (The only
open frontend-testid items in the whole E2E suite are `CAT-E2E-03/07` browse-fallback + empty-state
in the *catalog* picker — see SPEC B, not this lane.)

---

## 2. Backend dependencies (verified present @ `9ebc0d9`)

- `POST /products/{id}/calc` (price-calc) — reachable in dev; PQE-E2E-02/03 already exercise it green.
- `POST /products/{id}/apply-price` — EXISTS: `backend/app/modules/pricing/router.py` L144-188 →
  `apply_price_to_product`. Returns 204 on success. This is the endpoint `onSaveContinue()`
  (pricing.component.ts L887-919) POSTs to; on 204 the component navigates to
  `/catalogs/{id}/export`.

No backend change is required for this lane.

---

## 3. E2E scenarios (coverage map)

The pricing flows live in two files. Ports/base-URLs come from `frontend/e2e/playwright.config.ts`
ONLY (mfe-pricing `:4207`, shell `:4200`, backend `:8000` at slot-0; env-overridable — never hardcode).
Every product is REAL (created via `CatalogPage.createProductViaPicker()` → real UUID → the leaf has a
pricing-lookup row). Auth via the worker-scoped authed-context fixture (`fixtures/auth.ts`, rotation-safe).

### 3.1 Already GREEN — VERIFY, do not rewrite (`flows/pricing.spec.ts`)
| ID | Assertion (visible outcome) | Status |
|---|---|---|
| PQE-E2E-02 | selling price `70` → Calculate → `pricing-settlement-value` shows `₹…`, `pricing-breakdown` + `pricing-disclaimer` visible, `pricing-negative-alert` count 0 | present, not fixme — re-run to confirm |
| PQE-E2E-03 | selling price `1` → Calculate → `pricing-negative-alert` visible + contains "negative settlement"; settlement renders negative `₹-…` | present, not fixme — re-run to confirm |

### 3.2 NEW — author (`flows/pricing.spec.ts`, append)
| ID | Steps | Visible-outcome assertion |
|---|---|---|
| **PQE-E2E-04** | createProductViaPicker → goto pricing → `calculate('70')` → wait for `pricing-settlement-value` → click `pricing-apply-btn` | (a) `pricing-applied-status` becomes visible ("Price applied") after the 204, **and/or** (b) the app navigates to `/catalogs/{id}/export` (URL assertion) and the export Generate button is visible. Assert the visible outcome the live run actually produces — `onSaveContinue()` sets `applied` **then** navigates, so the export URL is the robust anchor; the `applied-status` span may unmount on navigation. **Live-verify which is observable and assert that one** (record in `selector_registry.md`). |
| **PQE-E2E-04b** *(optional, negative)* | force the apply POST to error (Playwright `page.route('**/apply-price', route => route.fulfill({status:500}))`) → click apply | `pricing-apply-error` visible ("Could not apply price…"); NO navigation (stays on `/pricing`). Guards the SPEC-C error path. |

### 3.3 UN-FIXME — rewrite (`flows/price-apply-export.spec.ts`, W3-E2-6)
The current file is a bare `test.fixme` whose stated blockers (**"no apply control, zero testids"**
+ "export productId not fixed") are BOTH resolved on develop: `pricing-apply-btn` exists (#439/SPEC-C),
and the mfe-export productId placeholder bug is fixed (`resolveExportProductId`, confirmed in
`export.spec.ts` header + verified live in the prior wave). Rewrite W3-E2-6 as a real test:

| ID | Steps | Visible-outcome assertion |
|---|---|---|
| **W3-E2-6** | createProductViaPicker → pricing → `calculate('70')` → click `pricing-apply-btn` → land on export | URL `/catalogs/{id}/export` reached **and** `ExportPage.generateButton` visible. This is the calc→apply→**export-page-reachable** chain. The actual **download** leg stays out of scope here (env-blocked on storage — see SPEC B `PQE-E2E-05`); do NOT assert a download in W3-E2-6. |

> W3-E2-6 substantially overlaps PQE-E2E-04's navigation assertion. Author PQE-E2E-04 first; if it
> already asserts "lands on export + Generate visible", collapse W3-E2-6 into a thin alias or delete the
> redundant scaffold with a one-line note (do not keep a duplicate fixme). The e2e writer decides at
> codification which single test owns the chain; the gate will reject a leftover empty `test.fixme`.

---

## 4. Measurable exit criterion (the gate will check this)

- **All mfe-pricing selectors LIVE-VERIFIED** into `.claude/agent-memory/meesell-e2e-test-writer/selector_registry.md`
  (§ mfe-pricing) before any codification — including the apply-flow trio (`pricing-apply-btn` /
  `pricing-applied-status` / `pricing-apply-error`), which are NEW to the registry.
- **PQE-E2E-02, PQE-E2E-03, PQE-E2E-04 GREEN** on a full local stack (`workers=1`), stable ×2.
- **W3-E2-6 GREEN** (calc→apply→export-page-reachable) OR consciously collapsed into PQE-E2E-04 with a note.
- **Zero remaining `test.fixme` in `price-apply-export.spec.ts`** (the file is either a real green test or removed).
- **Zero hardcoded ports** (all from `playwright.config.ts`); **every test asserts a DOM/URL visible outcome**
  (not a network call); no real external vendor call (calc/apply hit the local backend only).
- `playwright test --list` parses/typechecks the whole suite clean.

If the full-stack live run is env-blocked (8GB swap ceiling — a recurring hazard on this box, see
`coordinator_patterns.md`), the writer MAY fall back to `playwright --list` + source ground-truth AND
disclose it, per the e2e gate allowance — but the pricing selectors MUST be live-verified at least once
(they gate PQE-E2E-04's new apply trio).

---

## 5. Recommended dispatch

`meesell-e2e-test-writer` — *"qa-pricing E2E lane completion: mfe-pricing testids are ALL present on
develop `9ebc0d9` (no frontend request needed). Live-verify the pricing selectors (esp. the new apply
trio `pricing-apply-btn/applied-status/apply-error`) into selector_registry.md, then (1) confirm the
existing PQE-E2E-02/03 green, (2) author PQE-E2E-04 apply-price → applied-status/navigate-to-export,
(3) un-fixme/rewrite price-apply-export.spec.ts W3-E2-6 as the calc→apply→export-page-reachable chain
(NOT the download). Config-driven ports; visible-outcome only; flip your board row to IN REVIEW on PR open."*
