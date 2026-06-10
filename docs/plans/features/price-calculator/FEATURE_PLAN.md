# Price Calculator — Feature Plan (Audit + Hardening + UI Gap-fill)

| Field | Value |
|---|---|
| Document type | Feature-level executable plan |
| Feature slug | `price-calculator` |
| Status | DRAFT — awaiting founder approval |
| Authored | 2026-06-10 — `mesell-price-calculator-planning-session-1` |
| Author session | master Claude planning session (per repo-management MASTER_PLAN.md §1 Model C) |
| Parent dispatch | `docs/plans/features/price-calculator/PLANNING_DISPATCH.md` (on `repo-management/foundation`) |
| Anchor architecture | `docs/BACKEND_ARCHITECTURE.md §12 LOCKED 2026-06-05` · `docs/V1_FEATURE_SPEC.md §F7` · `docs/MVP_ARCHITECTURE.md §2.5 / §3.4` · `docs/FRONTEND_ARCHITECTURE.md` (APPROVED 2026-06-08) |
| Branch model | `feature/price-calculator` + `feature/price-calculator/{backend,frontend}` per repo-management MASTER_PLAN.md §1.2 |
| Founder decisions | D1 = Audit+Hardening+UI Gap-fill · D2 = Standard flag (dev=true, staging=false until gates) · D3 = 3-component split + extract PricingService |

---

## 0. Operating context (state audit findings)

This plan is **not greenfield**. A prior session built the pricing module on `origin/develop` before the repo-management MASTER_PLAN was ratified. The findings below shape every later section.

### 0.A — Backend state on `origin/develop` HEAD `9a2b25c`

| Surface | State | Notes |
|---|---|---|
| `backend/app/modules/pricing/__init__.py` | ✅ exists — exports `pricing_router` | 1,379 bytes |
| `backend/app/modules/pricing/router.py` | ✅ exists — `POST /api/v1/products/{id}/price-calc` registered with `@rate_limit(scope="price_calc", limit=600, window=3600)` + `@audit_event("pricing.calculated")` | 4,323 bytes |
| `backend/app/modules/pricing/schemas.py` | ✅ exists — `PriceCalcRequest` + `PriceCalcAlert` + `PriceCalcResponse` per §12.E LOCKED, all `Decimal` fields with `decimal_places=2` | 4,597 bytes |
| `backend/app/modules/pricing/domain.py` | ✅ exists — `PricingAlert` frozen dataclass + `PnLBreakdown` + `PricingCalc` per §12.F LOCKED | 5,765 bytes |
| `backend/app/modules/pricing/exceptions.py` | ✅ exists — `InvalidPriceInputError` (400) + `CommissionMissingError` (422) per §12.G | 4,575 bytes |
| `backend/app/modules/pricing/repository.py` | ✅ exists — `insert_calc` + `find_latest_by_product` with `Product.user_id == user_id` JOIN per §12.D | 7,734 bytes |
| `backend/app/modules/pricing/service.py` | ✅ exists — `calculate(user_id, product_id, request, db)` + `get_last_calc` + `_compute_pnl` + `_generate_alerts` per §12.C | 16,266 bytes |
| `backend/app/shared/models/pricing_calc.py` | ✅ exists — column-by-column ORM (`mrp`, `meesho_price`, `seller_price`, `commission_pct`, `gst_pct`, `margin`, `margin_pct`, `created_at`) | 89 lines |
| `backend/alembic/versions/935e55b4852c_v1_baseline_13_tables.py` | ✅ creates `pricing_calcs` table | head `f31c75438e61` |
| `backend/tests/modules/pricing/{conftest,test_alerts,test_commission_missing,test_ownership_gate,test_pnl_formula}.py` | ✅ exist — 4 unit-test files per §12.J | pass status to be confirmed by audit |
| `backend/tests/integration/test_pricing_persistence.py` + `test_pricing_full_flow.py` | ✅ exist per §12.J | pass status to be confirmed by audit |
| `backend/app/services/pricing_engine.py` | ❌ DOES NOT EXIST — entire `backend/app/services/` directory absent. §0.E latent `PricingAlert` import bug **ALREADY RESOLVED** by prior gap-pass purge | no further delete-legacy action required |
| `FEATURE_PRICE_CALCULATOR_ENABLED` env var | ❌ not yet wired | D2 work item |
| `categories.commission_pct` seeding | ⚠️ unverified — ORM column exists, no seed script grep-hit on commission_pct values in `backend/scripts/` | audit work item — database-builder dispatch |

### 0.B — Frontend state on `origin/develop` HEAD

| Surface | State | Notes |
|---|---|---|
| `frontend/src/app/features/pricing/pricing/pricing.component.ts` | ✅ exists — single 327-line standalone component (form + breakdown table + native `<input type="range">`) | uses `mee-*` UI Kit primitives only — no PrimeNG direct imports (FRONTEND_ARCH Layer 4 compliant) |
| `frontend/src/app/features/pricing/pricing/pricing.component.spec.ts` | ✅ exists — 212 lines | pass status TBD |
| `frontend/src/app/features/pricing/pricing/pricing.model.ts` | ✅ exists — 16 lines, `PnlBreakdown` interface | |
| `frontend/src/app/features/pricing/pricing/pricing.utils.ts` | ✅ exists — 38 lines, `computePnlBreakdown` + `formatRupee` (the local-recompute helper that powers slider-locality contract) | |
| `PnlBreakdownComponent` (standalone) | ❌ not extracted | D3 work item |
| `MarginSliderComponent` (standalone) | ❌ not extracted | D3 work item |
| `PricingService` (HttpClient wrapper) | ❌ not extracted — component calls fetch inline today | D3 work item |
| Route `/catalogs/:id/pricing` | (verify in `app.routes.ts`) | confirm or wire as part of FE dispatch |

### 0.C — Documentation defects discovered during audit

| Defect | Location | Resolution path |
|---|---|---|
| §12.B.1 step 8 prose says `pricing_calcs` rows are `{user_id, product_id, input_jsonb, output_jsonb, calculated_at}` | `docs/BACKEND_ARCHITECTURE.md` line ~4545 | **Doc fix needed**: actual ORM is column-by-column per V1_FEATURE_SPEC §F7. Column-by-column is the truth (matches `MVP_ARCH §2.5` reference). `input_jsonb`/`output_jsonb` was speculative. Resolution: services-builder dispatch updates §12.B.1 step 8 to read column-by-column persistence, removes JSONB references. |
| Original PLANNING_DISPATCH.md flagged HSN→GST mapping as a data-track verification gate | `docs/plans/features/price-calculator/PLANNING_DISPATCH.md` Decision 1 line 54 | **Obsolete**: §12.B.1 step 6 LOCKED `DEFAULT_GST_PCT = Decimal("18")` as a `pricing/service.py` module constant for V1. Per-category GST deferred to V1.5. No HSN data work for V1. This plan supersedes the PLANNING_DISPATCH on that point. |
| Original PLANNING_DISPATCH.md modelled request as `mrp + target_seller_payout` | `docs/plans/features/price-calculator/PLANNING_DISPATCH.md` Step 5 line 119 | **Obsolete**: §12.B.1 LOCKED request shape is `input_cost + target_margin_pct` (MRP is COMPUTED, not input). Code on develop matches the LOCKED shape. PLANNING_DISPATCH was speculative. |

---

## 1. Decisions

### 1.A — D1: Build framing → **Audit + Hardening + UI Gap-fill**

Treat existing `origin/develop` code as the merged baseline. This plan covers:

1. **Backend audit** (services-builder) — verify `service.py` `_compute_pnl` implements §12.B.1 step 6 formulas exactly; verify ROUND_HALF_EVEN quantization; verify `_generate_alerts` emits all 3 LOCKED codes per §12.F; verify `insert_calc` persists column-by-column (NOT JSONB); flag the §12.B.1 step 8 doc defect for fix.
2. **Backend feature flag** (api-routes-builder) — add `FEATURE_PRICE_CALCULATOR_ENABLED` env-var read; route returns 404 when disabled (matches D2 standard posture).
3. **Backend data verification** (database-builder) — verify `categories.commission_pct` is seeded for all 3,772 categories; if gaps surface, escalate to data lead (xlsx-parser dispatch — conditional, see §5 conditional template) OR author a fixup seed script depending on origin of the gap.
4. **Frontend component split** (angular-component-builder) — refactor the 327-line `PricingComponent` into three components per FRONTEND_ARCH Layer 4: `PricingComponent` (page + form + state), `PnlBreakdownComponent` (6-row table + red row when `margin < 0`), `MarginSliderComponent` (slider + local recompute via injected `recomputeFromSnapshot()`).
5. **Frontend service extraction** (angular-service-builder) — extract `PricingService` HttpClient wrapper (`calculate(productId, request)`) + `recomputeFromSnapshot(snapshot, newMrp)` helper. Enforce slider-locality contract: `PricingService.calculate` runs ONLY on initial render + on Accept click; slider ticks compute locally.
6. **Documentation** — V1_FEATURE_SPEC.md §F7 implementation stamp; §12.B.1 step 8 doc defect resolution; OpenAPI Decimal precision noted; slider-locality contract docstring.
7. **Feature-board hygiene** — every lead's `feature_board_<domain>.md` gets a row (work or NO WORK).

Greenfield rebuild (D1 option B) is rejected — would discard the working 16,266-byte service.py + integration tests. Retroactive branch hygiene only (D1 option C) is rejected — would not surface the audit findings or add the missing flag/FE split.

### 1.B — D2: Feature flag → **Standard posture (dev=true, staging=false until gates pass)**

| Aspect | Value |
|---|---|
| Flag name | `FEATURE_PRICE_CALCULATOR_ENABLED` |
| Type | Boolean env-var read by `shared/config.py` Settings class |
| Dev default | `true` |
| Staging default | `false` until ALL gates pass: (a) all 4 unit-test files green per §12.J; (b) both integration test files green; (c) `_compute_pnl` matches the 10 golden Decimal cases derived from §12.B.1 step 6 + §12.J.3 fixture (`input_cost=100`, `target_margin_pct=30`, `commission_pct=15` → `seller_price=130.00`, `mrp=151.52`, `profit=30.00`, `profit_pct=30.00`); (d) `/catalogs/:id/pricing` page first contentful paint < 500ms on dev; (e) 7 calendar days green on `dev` namespace post-merge |
| Production default | N/A — `prod` namespace deferred to V1.5 per repo-management MASTER_PLAN §3.1 |
| Disabled-state backend | `POST /api/v1/products/{id}/price-calc` returns `404` with `validation_message_id = "feature.disabled"` (new i18n key — services-builder adds) |
| Disabled-state frontend | `/catalogs/:id/pricing` route renders `<mee-empty-state>` with copy "Pricing temporarily disabled" — featureFlagGuard reads from `core/services/feature-flags.service.ts` per repo-management MASTER_PLAN §3.2 |
| Federation flag | NOT INTRODUCED — `mfe-pricing` federation pilot is OUT OF SCOPE per CLAUDE.md Decision 12 + module-federation MASTER_PLAN DRAFT status. If V1.5 federation lights up, a separate `FEATURE_MFE_PRICING_REMOTE` flag is introduced then. |
| Flag removal | When feature ships to `main` (V1.5 release), flag is removed in the staging→main hardening PR — carrying a flag past one release is debt per repo-management MASTER_PLAN §3.2 |

### 1.C — D3: Frontend component split → **3-component refactor + extract PricingService**

Split per V1_FEATURE_SPEC §F7 ("Frontend: `PricingComponent`, `PnlBreakdownComponent`, `MarginSliderComponent`") + FRONTEND_ARCH Layer 4 enforcement (no PrimeNG direct imports outside `src/app/ui/`).

| Component | Owns |
|---|---|
| `PricingComponent` (page) | `/catalogs/:id/pricing` route binding; reactive form (`input_cost`, `target_margin_pct`); subscribes to `PricingService.calculate()` result; passes snapshot + breakdown signal down to children; persists on Accept |
| `PnlBreakdownComponent` (presentational) | 6-row table: MRP / Meesho Price / Commission (% + ₹) / GST (% + ₹) / Seller Payout / Net Margin (% + ₹). Red `var(--mee-color-error)` row class when `margin < 0`. `@Input() breakdown: PnlBreakdown`. `OnPush`. |
| `MarginSliderComponent` (interactive) | Native range slider (no `mee-slider` primitive in UI Kit yet — confirmed via FRONTEND_ARCH inventory). `@Input() snapshot: PnlBreakdown`. `@Output() breakdownChange = new EventEmitter<PnlBreakdown>()`. On every slider tick: calls injected `pricingService.recomputeFromSnapshot(snapshot, newMrp)` locally. NO API call per tick. |
| `PricingService` (Angular service) | `calculate(productId: string, request: PriceCalcRequest): Observable<PriceCalcResponse>` — wraps `HttpClient.post`. Plus `recomputeFromSnapshot(snapshot: PnlBreakdown, newMrp: Decimal): PnlBreakdown` — pure function importable into `MarginSliderComponent`. Lives at `frontend/src/app/features/pricing/pricing/pricing.service.ts`. |

Slider-locality contract (mandatory):
- `PricingService.calculate()` is invoked exactly ONCE on initial form submit + exactly ONCE on Accept click. NOT per slider tick.
- `MarginSliderComponent` re-emits a recomputed breakdown using only the snapshotted `commission_pct` + `gst_pct` from the last `calculate()` response.
- Chrome DevTools Network tab MUST show zero `/price-calc` requests during slider drag — this is a frontend-lead PR review gate.

Spec test extension: existing `pricing.component.spec.ts` (212 lines) must be split into 3 spec files mirroring the new component boundaries; the new `pricing.service.spec.ts` MUST include the 10 golden Decimal cases as parametrized tests against `recomputeFromSnapshot` (the same fixture the backend uses).

---

## 2. Agent lineup

Per CLAUDE.md MeeSell Agent Ecosystem Rules: only `meesell-*` agents handle MeeSell work. The master Claude session dispatches coordinators; coordinators dispatch their specialists.

### 2.A — Active leads + specialists

| Lead (coordinator) | Specialist | Slice for `price-calculator` | Files in scope (subset of §3) |
|---|---|---|---|
| **meesell-backend-coordinator** | `meesell-services-builder` | Audit `service.py` against §12.C LOCKED; verify ROUND_HALF_EVEN on every monetary `_q()`; verify `_generate_alerts` emits all 3 codes per §12.F thresholds; resolve §12.B.1 step 8 doc defect (column-by-column truth); add `feature.disabled` i18n key | `backend/app/modules/pricing/service.py` (audit-only, no rewrite unless audit finds drift); `docs/BACKEND_ARCHITECTURE.md` §12.B.1 step 8 (doc fix); `backend/app/i18n/messages_en.py` (1 new key) |
| meesell-backend-coordinator | `meesell-api-routes-builder` | Add `FEATURE_PRICE_CALCULATOR_ENABLED` settings field; gate the route handler — return `404` with `validation_message_id="feature.disabled"` when flag is `false`; verify OpenAPI shows Decimal precision on all monetary fields | `backend/app/shared/config.py` (add 1 Settings field); `backend/app/modules/pricing/router.py` (add 3-line flag check); `backend/tests/modules/pricing/test_feature_flag.py` (NEW test file) |
| meesell-backend-coordinator | `meesell-database-builder` | Verify `categories.commission_pct` is populated for all 3,772 categories on dev DB; produce a coverage report (count rows where `commission_pct IS NULL`); if gaps, author fixup seed `backend/scripts/seed_category_commissions.py` (NOT a migration — the column already exists) | `backend/scripts/seed_category_commissions.py` (CONDITIONAL — only if gaps surface); `docs/status/feature_board_backend.md` (mark BLOCKED-data if gap exceeds threshold and escalate to data lead) |
| **meesell-frontend-coordinator** | `meesell-angular-component-builder` | Split the 327-line monolithic `PricingComponent` into 3 standalone components per D3; preserve the existing `pricing.utils.computePnlBreakdown` as the canonical local-recompute helper; spec files split to mirror | `frontend/src/app/features/pricing/pricing/pricing.component.ts` (refactor — page only); `frontend/src/app/features/pricing/pricing/pnl-breakdown.component.ts` (NEW); `frontend/src/app/features/pricing/pricing/margin-slider.component.ts` (NEW); `*.spec.ts` for each (NEW × 2 + refactor × 1) |
| meesell-frontend-coordinator | `meesell-angular-service-builder` | Extract `PricingService` with `calculate()` (HttpClient) + `recomputeFromSnapshot()` (pure function); featureFlagGuard wiring for `/catalogs/:id/pricing` route | `frontend/src/app/features/pricing/pricing/pricing.service.ts` (NEW); `frontend/src/app/app.routes.ts` (MODIFY — add featureFlagGuard to the existing pricing route); `frontend/src/app/core/services/feature-flags.service.ts` (MODIFY if not present — add `price_calculator` boolean) |
| **meesell-ai-coordinator** | (NO WORK) | Confirmed — pricing is deterministic per §12.H. No `ai_ops.client` invocation, no prompt, no eval set. | NONE |
| **meesell-data-engineer** | `meesell-xlsx-parser` (CONDITIONAL) | Activates ONLY if backend database-builder reports `commission_pct` NULL count > 0. If activated: extract commission_pct from per-category XLSX templates already parsed under `backend/app/data/`; produce a JSON map that the database-builder fixup seed consumes. | `backend/app/data/category_commissions.json` (CONDITIONAL — only on activation) |
| **meesell-infra-builder** | (NO WORK) | No new secrets, no new buckets, no manifest changes. The `FEATURE_PRICE_CALCULATOR_ENABLED` env var ships in ConfigMap (handled by routes-builder + standard CI/CD per repo-management MASTER_PLAN §3.4). Federation pilot deferred per CLAUDE.md D12. | NONE |
| **meesell-legal-writer** | (NO WORK) | Confirmed — no new legal copy. Existing UI strings ("Shipping not included in V1") already authored. | NONE |

### 2.B — Why this lineup is slim

The original PLANNING_DISPATCH.md assumed greenfield → 5-6 specialists. Reality is that backend was substantially built in a prior session. The audit framing means specialists are doing 1-2 days of work each, not 4-10 days. AI/data/infra/legal explicitly carry NO work in this feature; their feature-board rows acknowledge non-participation so they don't accidentally pick up the feature.

---

## 3. Branch creation protocol

Per repo-management MASTER_PLAN.md §1.2 + §2.1. Sessions named per §4.1: `mesell-price-calculator-{group}-session-{N}`.

### 3.A — Branches this planning session creates

| Branch | Parent | Purpose | Status |
|---|---|---|---|
| `feature/price-calculator/planning` | `origin/develop` | Hosts THIS document (FEATURE_PLAN.md) for founder review | ✅ created |

### 3.B — Branches the leads create after FEATURE_PLAN merges to develop

| Branch | Parent | Created by | When | Command |
|---|---|---|---|---|
| `feature/price-calculator` | `origin/develop` | Backend lead (largest contributor) | Step 1 — immediately after this FEATURE_PLAN PR merges to develop | `git checkout origin/develop && git checkout -b feature/price-calculator && git push -u origin feature/price-calculator` |
| `feature/price-calculator/backend` | `feature/price-calculator` | Backend lead | Step 2 — when backend lead opens the first backend specialist dispatch (services-builder is typically first) | `git checkout feature/price-calculator && git checkout -b feature/price-calculator/backend && git push -u origin feature/price-calculator/backend` |
| `feature/price-calculator/frontend` | `feature/price-calculator` | Frontend lead | Step 3 — after backend lead has at least one backend slice landed on `feature/price-calculator`, OR in parallel if frontend slice does not depend on backend changes (it doesn't — frontend reads from existing API contract) | `git checkout feature/price-calculator && git checkout -b feature/price-calculator/frontend && git push -u origin feature/price-calculator/frontend` |

### 3.C — Merge sequence

```
1. specialists push to feature/price-calculator/{backend,frontend}
2. specialist opens PR → feature/price-calculator (using group PR template per MASTER_PLAN §5)
3. lead reviews + squash-merges per MASTER_PLAN §2.1 (lead is the approver, NOT the founder)
4. when ALL participating group PRs are merged: backend lead opens feature/price-calculator → develop PR
5. founder approves + merges with merge-commit (NOT squash) per MASTER_PLAN §2.2
6. develop carries the merged feature; deploys to dev namespace continuously per §3.1
7. branches deleted within 24h of merge per §1.4
```

### 3.D — What this planning session DOES NOT do

- Does NOT cut `feature/price-calculator`. That is the backend lead's first action in their kickoff session.
- Does NOT cut `feature/price-calculator/{backend,frontend}`. Each lead does that when they dispatch.
- Does NOT modify any production code under `backend/app/` or `frontend/src/`.

---

## 4. Cross-agent awareness & memory hygiene

Per founder concern: a single specialist works on multiple features over time; without discipline they lose track of which memory entry belongs to which feature. This section installs the 3-layer hygiene that every involved agent honors.

### 4.A — Awareness broadcast (one-time, at plan lock)

When this FEATURE_PLAN.md PR merges to `develop`, every one of the 5 leads adds a row to their `docs/status/feature_board_<domain>.md`. EVEN THE LEADS WITH NO WORK — they need to know NOT to pick up the feature.

| Board file | Row to add |
|---|---|
| `docs/status/feature_board_backend.md` | `price-calculator \| — \| PENDING \| — \| 2026-06-1X \| none \| Awaiting kickoff — see docs/plans/features/price-calculator/FEATURE_PLAN.md §5 services-builder dispatch first` |
| `docs/status/feature_board_frontend.md` | `price-calculator \| — \| PENDING \| — \| 2026-06-1X \| none \| Awaiting kickoff — see docs/plans/features/price-calculator/FEATURE_PLAN.md §5 angular-component-builder + angular-service-builder dispatches` |
| `docs/status/feature_board_ai.md` | `price-calculator \| — \| NOT PARTICIPATING \| — \| 2026-06-1X \| none \| Deterministic math per BACKEND_ARCHITECTURE §12.H — no AI seam. Do NOT pick up. See FEATURE_PLAN §2.A row "meesell-ai-coordinator (NO WORK)"` |
| `docs/status/feature_board_data.md` | `price-calculator \| — \| CONDITIONAL \| — \| 2026-06-1X \| backend — commission_pct seed verification \| Activate xlsx-parser ONLY if database-builder reports gap. See FEATURE_PLAN §5 conditional dispatch.` |
| `docs/status/feature_board_infra.md` | `price-calculator \| — \| NOT PARTICIPATING \| — \| 2026-06-1X \| none \| No new secrets, no manifests, federation deferred per CLAUDE.md D12. Do NOT pick up.` |

Each lead also appends a one-line entry to their own `MEMORY.md`:

```
## Feature awareness — price-calculator — 2026-06-1X
Plan locked at docs/plans/features/price-calculator/FEATURE_PLAN.md.
My domain participation: <work | NO WORK | CONDITIONAL>.
Slice: <one-line summary of §2.A row>.
Branch model: feature/price-calculator/<group> per FEATURE_PLAN §3.
Memory tagging: every pricing session entry MUST end H2 with "— Feature: price-calculator" per §4.B.
```

This is a mandatory step in EVERY lead's first session that follows this PR merge. The lead's spec rewrite (repo-management MASTER_PLAN §9.1) inherits this protocol.

### 4.B — Per-feature memory tagging (every session, every agent)

Every MEMORY.md entry in every agent (lead OR specialist) that does work on `price-calculator` MUST use this exact session-entry header format:

```
## Session mesell-price-calculator-{group}-session-{N} — YYYY-MM-DD — Feature: price-calculator

**Files touched:**
- backend/app/modules/pricing/service.py (audit findings)
- ...

**Decisions made (citing FEATURE_PLAN sections):**
- §1.A audit: confirmed _compute_pnl matches §12.B.1 step 6 formulas
- §1.B flag: added FEATURE_PRICE_CALCULATOR_ENABLED to shared/config.py
- ...

**Next session inheritance:**
- <what the next session in this (feature × group) tuple must read first>

**Cross-references:**
- docs/plans/features/price-calculator/FEATURE_PLAN.md §1.A / §5.A
- docs/BACKEND_ARCHITECTURE.md §12.B.1 (LOCKED)
```

Three locked rules:
1. **H2 ends with `— Feature: price-calculator`** — this is the grep-anchor for future cross-feature audits. The agent's memory can be filtered by `grep "Feature: price-calculator" MEMORY.md` to recover everything done on this feature.
2. **At least one FEATURE_PLAN section citation per entry** — proves the session advanced something the plan tracked.
3. **`feature_board_<domain>.md` row's `Last touched` + `Current session` columns updated BEFORE writing the memory entry** — so the board is current even if the memory write fails.

These rules are enforced by the lead's PR review checklist for the specialist's PR (a memory diff is one of the checklist items).

### 4.C — Cross-specialist sync surface (handoff memos)

When one specialist makes a change another specialist must know about:

| Trigger | Originating action | Receiving action |
|---|---|---|
| services-builder resolves §12.B.1 step 8 doc defect | Writes `.claude/agent-memory/meesell-services-builder/handoff_price-calculator_doc-defect.md` (one paragraph) + opens a row in `docs/status/feature_board_backend.md` "Inter-lead requests open" → `frontend` (informational; FE doesn't change but should know the persistence shape is column-by-column) | Frontend lead reads memo at start of next pricing session; closes the inter-lead row |
| api-routes-builder adds `FEATURE_PRICE_CALCULATOR_ENABLED` 404 behavior | Writes handoff memo summarizing the 404 response shape (`validation_message_id="feature.disabled"`) → `frontend` | angular-service-builder reads memo; ensures the featureFlagGuard treats this 404 as "feature off", not "error" |
| database-builder finds `commission_pct` gap | Writes handoff memo with the NULL-row count + a sample of affected category IDs → `data` | data-engineer activates xlsx-parser per §5 conditional template; closes the row when seed is shipped |
| angular-component-builder splits components, changes a public interface that any other feature consumes | Writes handoff memo to → `frontend` shared composites lead (self, since the same lead owns shared composites) | No-op for V1 — Pricing components aren't currently re-used in other features. But the protocol is set so this surface exists for future features. |

The §7.5 "Cross-lead coordination" protocol in repo-management MASTER_PLAN applies — escalate to founder if a handoff request goes 48h without acknowledgement.

---

## 5. Code surfaces

Every file the feature audit/hardening dispatches will create or modify. Grouped by domain. The "Status" column says what each dispatch does to the file.

### 5.A — Backend

| File | Status | Specialist | Why |
|---|---|---|---|
| `backend/app/modules/pricing/__init__.py` | DO NOT TOUCH | — | Already correct per §0.A |
| `backend/app/modules/pricing/router.py` | MODIFY | api-routes-builder | Add `FEATURE_PRICE_CALCULATOR_ENABLED` flag check at top of handler — return 404 with `validation_message_id="feature.disabled"` when disabled |
| `backend/app/modules/pricing/schemas.py` | DO NOT TOUCH | — | Already matches §12.E LOCKED |
| `backend/app/modules/pricing/service.py` | AUDIT (modify only if drift found) | services-builder | Verify `_compute_pnl` formulas match §12.B.1 step 6 byte-for-byte; verify ROUND_HALF_EVEN; verify `_generate_alerts` emits all 3 codes per §12.F thresholds (LOW_MARGIN profit_pct<10, HIGH_MRP_MULTIPLIER mrp/input_cost>3, THIN_PROFIT profit<50). Modify ONLY if drift; otherwise no-op |
| `backend/app/modules/pricing/domain.py` | DO NOT TOUCH | — | Already matches §12.F LOCKED |
| `backend/app/modules/pricing/exceptions.py` | DO NOT TOUCH | — | Already matches §12.G LOCKED |
| `backend/app/modules/pricing/repository.py` | AUDIT (modify only if drift found) | services-builder | Verify `find_latest_by_product` JOIN on `Product.user_id == user_id` is intact (M6 structural enforcement); verify `insert_calc` is append-only (no UPDATE method exists) |
| `backend/app/shared/models/pricing_calc.py` | DO NOT TOUCH | — | Already matches V1_FEATURE_SPEC §F7 DDL column-by-column |
| `backend/app/shared/config.py` | MODIFY | api-routes-builder | Add `feature_price_calculator_enabled: bool = True` Settings field |
| `backend/app/i18n/messages_en.py` | MODIFY | services-builder | Add 1 new key: `"feature.disabled": "This feature is temporarily disabled."` (used by the 404 path) |
| `backend/alembic/versions/<rev>_pricing_calcs.py` | DO NOT CREATE | — | Table already in baseline migration `935e55b4852c`. No new migration needed |
| `backend/app/services/pricing_engine.py` | N/A | — | Already deleted in prior gap-pass. §0.E latent bug already resolved. No further action |
| `backend/tests/modules/pricing/test_alerts.py` | RE-RUN, FIX IF FAIL | services-builder | Confirm green |
| `backend/tests/modules/pricing/test_commission_missing.py` | RE-RUN, FIX IF FAIL | services-builder | Confirm green |
| `backend/tests/modules/pricing/test_ownership_gate.py` | RE-RUN, FIX IF FAIL | services-builder | Confirm green |
| `backend/tests/modules/pricing/test_pnl_formula.py` | RE-RUN + EXTEND | services-builder | Confirm green + add the 10 golden Decimal cases as parametrized cases (see §1.B gate (c)) |
| `backend/tests/modules/pricing/test_feature_flag.py` | NEW | api-routes-builder | Test: flag=true → 200; flag=false → 404 with `feature.disabled` |
| `backend/tests/integration/test_pricing_persistence.py` | RE-RUN, FIX IF FAIL | services-builder | Confirm green |
| `backend/tests/integration/test_pricing_full_flow.py` | RE-RUN, FIX IF FAIL | services-builder | Confirm green |
| `backend/scripts/seed_category_commissions.py` | NEW (CONDITIONAL) | database-builder | Only if `commission_pct` NULL count > 0 on dev DB |
| `backend/app/data/category_commissions.json` | NEW (CONDITIONAL) | xlsx-parser (data) | Only if seed gap activates the xlsx-parser dispatch |

### 5.B — Frontend

| File | Status | Specialist | Why |
|---|---|---|---|
| `frontend/src/app/features/pricing/pricing/pricing.component.ts` | REFACTOR | angular-component-builder | Reduce from 327 lines to ~150 lines — owns route binding, reactive form, state orchestration. Delegates table to `PnlBreakdownComponent`, slider to `MarginSliderComponent` |
| `frontend/src/app/features/pricing/pricing/pricing.component.spec.ts` | REFACTOR | angular-component-builder | Trim to page-level tests only — table/slider tests move to child component specs |
| `frontend/src/app/features/pricing/pricing/pricing.model.ts` | DO NOT TOUCH (or extend with new types) | angular-component-builder | Existing `PnlBreakdown` interface stays. May add `PriceCalcRequest`/`PriceCalcResponse` types if not already present (verify) |
| `frontend/src/app/features/pricing/pricing/pricing.utils.ts` | DO NOT TOUCH | — | `computePnlBreakdown` + `formatRupee` stay — they are the slider-locality helpers. `PricingService.recomputeFromSnapshot` is a thin wrapper around `computePnlBreakdown` |
| `frontend/src/app/features/pricing/pricing/pnl-breakdown.component.ts` | NEW | angular-component-builder | 6-row table; `@Input() breakdown: PnlBreakdown`; red row when `margin < 0`; OnPush |
| `frontend/src/app/features/pricing/pricing/pnl-breakdown.component.spec.ts` | NEW | angular-component-builder | Renders 6 rows; red class applied when margin negative |
| `frontend/src/app/features/pricing/pricing/margin-slider.component.ts` | NEW | angular-component-builder | Native range slider; injects `PricingService`; emits `breakdownChange` on every tick via local recompute |
| `frontend/src/app/features/pricing/pricing/margin-slider.component.spec.ts` | NEW | angular-component-builder | Slider drag emits N breakdowns; NO `HttpClient` mock activations expected during drag |
| `frontend/src/app/features/pricing/pricing/pricing.service.ts` | NEW | angular-service-builder | `calculate()` + `recomputeFromSnapshot()`; standalone injectable |
| `frontend/src/app/features/pricing/pricing/pricing.service.spec.ts` | NEW | angular-service-builder | `calculate()` hits HttpClient; `recomputeFromSnapshot()` passes the 10 golden Decimal cases |
| `frontend/src/app/features/pricing/pricing/index.ts` | NEW or MODIFY | angular-component-builder | Public barrel for the feature (preferred Layer 4 pattern) |
| `frontend/src/app/core/services/feature-flags.service.ts` | VERIFY OR MODIFY | angular-service-builder | Confirm `price_calculator: boolean` is present; if not, add. Read from build-time env per repo-management MASTER_PLAN §3.2 |
| `frontend/src/app/app.routes.ts` | MODIFY | angular-service-builder | Add `featureFlagGuard` to the `/catalogs/:id/pricing` route entry. If route doesn't exist yet, add it |
| `frontend/src/app/core/guards/feature-flag.guard.ts` | VERIFY OR NEW | angular-service-builder | Standard pattern — redirect to `<mee-empty-state>` placeholder route or render inline; matches existing FE convention |

### 5.C — AI / Data / Infra / Legal

NONE for V1 except the conditional data dispatch in §5.A.

### 5.D — Documentation

| File | Status | Owner | Change |
|---|---|---|---|
| `docs/BACKEND_ARCHITECTURE.md` §12.B.1 step 8 | DOC FIX | services-builder | Change prose from "Persist to `pricing_calcs` table: `{user_id, product_id, input_jsonb, output_jsonb, calculated_at}`" → "Persist to `pricing_calcs` table column-by-column per V1_FEATURE_SPEC §F7 DDL: `{product_id, mrp, meesho_price, seller_price, commission_pct, gst_pct, margin, margin_pct, created_at}`. JSONB persistence was speculative — actual ORM is column-by-column, validated by `shared/models/pricing_calc.py` and the §F7 DDL." |
| `docs/BACKEND_ARCHITECTURE.md` §12 STATUS block | DOC AMENDMENT | services-builder | Append: "**2026-06-1X amendment:** §0.E latent `services/pricing_engine.py` PricingAlert import bug confirmed resolved by prior gap-pass purge — entire `backend/app/services/` dir absent on develop. No construction action required." |
| `docs/V1_FEATURE_SPEC.md` §F7 | IMPLEMENTATION STAMP | services-builder | Append after acceptance-criteria block: "**Implemented 2026-06-1X via PR #N** (post-audit + hardening + UI gap-fill — see `docs/plans/features/price-calculator/FEATURE_PLAN.md`)" |
| `backend/app/modules/pricing/service.py` (`calculate` docstring) | DOCSTRING EXTENSION | services-builder | Reference §12.B.1 step 8 column-by-column persistence; reference column-by-column DDL (NOT JSONB); reference ROUND_HALF_EVEN quantization rule |
| `frontend/src/app/features/pricing/pricing/margin-slider.component.ts` (class docstring) | NEW DOCSTRING | angular-component-builder | "Slider-locality contract: this component invokes `PricingService.recomputeFromSnapshot` locally on every tick. It MUST NOT call `PricingService.calculate` (the HttpClient surface). Frontend-lead PR review verifies zero `/price-calc` requests during slider drag via Chrome DevTools." |
| `frontend/src/app/features/pricing/pricing/pnl-breakdown.component.ts` (class docstring) | NEW DOCSTRING | angular-component-builder | "6-row P&L breakdown per V1_FEATURE_SPEC §F7 acceptance criteria. Row sequence: MRP / Meesho Price / Commission / GST / Seller Payout / Net Margin. Red `var(--mee-color-error)` row class applied when `breakdown.margin < 0` (negative-margin warning)." |

---

## 6. Documentation deliverables

"Documented" means the following artifacts ALL exist by the time `feature/price-calculator → develop` PR merges:

1. **Backend API** — OpenAPI shows `POST /api/v1/products/{id}/price-calc` with full `PriceCalcRequest` + `PriceCalcResponse` Decimal-precision fields. Confirm via `curl http://api-dev/openapi.json | jq '.paths."/api/v1/products/{id}/price-calc"'` paste in the PR description.
2. **Backend service** — `service.calculate` docstring describes snapshotting semantics (commission_pct + gst_pct captured at calc time into `pricing_calcs` row; subsequent reads return frozen snapshot via `get_last_calc`).
3. **Backend doc defect resolution** — `BACKEND_ARCHITECTURE.md §12.B.1 step 8` amended to column-by-column truth.
4. **Backend i18n** — `i18n/messages_en.py` carries the new `feature.disabled` key (English string; V1.5 may add Tamil/Hindi).
5. **Frontend slider-locality docstring** — `MarginSliderComponent` class docstring explicitly states the no-API-call-per-tick contract.
6. **Frontend breakdown docstring** — `PnlBreakdownComponent` class docstring explicitly states the 6-row sequence + negative-margin red warning.
7. **Frontend route** — `app.routes.ts` entry for `/catalogs/:id/pricing` has a `featureFlagGuard` and an inline comment citing this FEATURE_PLAN §1.B.
8. **Cross-cutting feature-spec stamp** — `V1_FEATURE_SPEC.md §F7` carries the "Implemented YYYY-MM-DD via PR #N" stamp linking back to FEATURE_PLAN.md.
9. **Cross-cutting feature board** — every lead's `feature_board_<domain>.md` row is in the correct state (MERGED on backend + frontend, NOT PARTICIPATING acknowledged on ai/infra, CONDITIONAL closed on data).
10. **Cross-cutting memory** — every involved specialist's `MEMORY.md` has at least one session-tagged entry per §4.B format.

The lead's PR approval checklist for `feature/price-calculator → develop` MUST tick all 10 items.

---

## 7. Dispatch templates

One subsection per specialist that will be dispatched. Each template is copy-paste-ready — the lead fills in `{N}` (session ordinal) and the date when they dispatch.

Standard prelude (used by all templates):

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

MEMORY TAGGING (per FEATURE_PLAN §4.B):
Every memory entry you write MUST use this H2 heading format:
  ## Session mesell-price-calculator-{group}-session-{N} — YYYY-MM-DD — Feature: price-calculator

FEATURE BOARD HYGIENE (per FEATURE_PLAN §4.A + §6 deliverable 9):
- BEFORE you start: update docs/status/feature_board_<your-domain>.md row to IN PROGRESS;
  populate "Current session" with this session name.
- ON PR open: update the row to IN REVIEW; clear "Current session"; populate PR link in Notes.
- ON BLOCKER: update Status to BLOCKED; populate Blocking column per MASTER_PLAN §6.4 format.
```

### 7.A — `meesell-services-builder` dispatch (backend audit + doc defect + i18n)

```
SESSION: mesell-price-calculator-backend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.
DISPATCHED BY: meesell-backend-coordinator (per FEATURE_PLAN §2.A)
FEATURE: price-calculator (per FEATURE_PLAN.md §1.A — Audit + Hardening + UI Gap-fill)

## Your mission
Audit the existing `backend/app/modules/pricing/service.py` (16,266 bytes, already on develop) against the LOCKED contract in `docs/BACKEND_ARCHITECTURE.md §12`. Resolve the §12.B.1 step 8 documentation defect identified in FEATURE_PLAN.md §0.C. Add the `feature.disabled` i18n key in `app/i18n/messages_en.py`.

## Mandatory reads (in this order)
- docs/plans/features/price-calculator/FEATURE_PLAN.md (this plan — full)
- docs/BACKEND_ARCHITECTURE.md §12 (LOCKED) — especially §12.B.1 step 6 (P&L formula chain) + §12.B.1 step 8 (persistence — the doc defect) + §12.C (service public surface) + §12.F (PricingAlert thresholds: LOW_MARGIN profit_pct<10, HIGH_MRP_MULTIPLIER mrp/input_cost>3, THIN_PROFIT profit<50)
- docs/MVP_ARCHITECTURE.md §2.5 (pricing_calcs DDL — column-by-column)
- docs/V1_FEATURE_SPEC.md §F7 (Feature 7 spec)
- backend/app/modules/pricing/service.py (target of audit)
- backend/app/modules/pricing/{domain,exceptions,repository,schemas}.py (cross-references — read-only for context)
- backend/app/shared/models/pricing_calc.py (the truth on persistence shape)
- backend/tests/modules/pricing/{test_alerts,test_commission_missing,test_ownership_gate,test_pnl_formula}.py (the existing unit tests)
- backend/tests/integration/test_pricing_persistence.py + test_pricing_full_flow.py (existing integration tests)
- .claude/agent-memory/meesell-services-builder/MEMORY.md (your own memory — start here)
- .claude/agent-memory/meesell-backend-coordinator/MEMORY.md (turn 19 onwards — pricing §12 context)

## Acceptance criteria (audit findings PR is APPROVED only when ALL true)
1. Audit report posted in PR description: confirms or contests each of the following against the LOCKED contract:
   - `_compute_pnl` implements §12.B.1 step 6 formula chain exactly:
       seller_price = input_cost × (1 + target_margin_pct/100)
       mrp = seller_price / (1 - commission_pct/100 - (gst_pct/100) × (commission_pct/100))
       commission_amount = mrp × commission_pct / 100
       gst_amount = commission_amount × gst_pct / 100
       meesho_price = mrp
       profit = seller_price - input_cost
       profit_pct = profit / input_cost × 100
   - Every monetary value passes through `Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)` — NO `float()` calls anywhere in the chain.
   - `gst_pct` resolves to module constant `DEFAULT_GST_PCT = Decimal("18")` for V1 (NOT per-category — V1.5+).
   - `_generate_alerts` emits the 3 LOCKED codes at the LOCKED thresholds (LOW_MARGIN when profit_pct<10, HIGH_MRP_MULTIPLIER when mrp/input_cost>3, THIN_PROFIT when profit<50).
   - `calculate` enforces the §12.B.1 flow steps 2-9 in order; raises `CommissionMissingError` (422) when `category.service.get_commission` returns None.
   - `insert_calc` persists COLUMN-BY-COLUMN (matches `shared/models/pricing_calc.py`) — NOT input_jsonb/output_jsonb. This is the §12.B.1 step 8 doc defect — the code is correct; the doc is wrong.
2. All 4 unit-test files + 2 integration-test files pass against the audited service.py. Paste `pytest -m "unit and pricing"` and `pytest -m "integration and pricing"` summaries in PR.
3. `test_pnl_formula.py` extended with the 10 golden Decimal cases derived from §12.B.1 step 6 + §12.J.3 fixture. Each case is a parametrized `pytest.param` with `(input_cost, target_margin_pct, commission_pct, expected_mrp, expected_seller_price, expected_profit, expected_profit_pct)`. The 10 cases MUST include:
   - The §12.J.3 golden: input_cost=100, target_margin_pct=30, commission_pct=15 → seller_price=130.00, mrp≈151.52, profit=30.00, profit_pct=30.00
   - A negative-margin case (low input_cost relative to commission)
   - A LOW_MARGIN alert case (profit_pct<10)
   - A HIGH_MRP_MULTIPLIER alert case (mrp/input_cost>3)
   - A THIN_PROFIT alert case (profit<50)
   - 5 more spanning the realistic Tirupur seller range (₹50-₹5000 input_cost, 5-50% target margin)
4. `BACKEND_ARCHITECTURE.md §12.B.1 step 8` prose amended to read column-by-column truth (see FEATURE_PLAN §5.D row for the exact replacement text).
5. `BACKEND_ARCHITECTURE.md §12` STATUS block appended with the 2026-06-1X amendment confirming §0.E latent bug is resolved (see FEATURE_PLAN §5.D).
6. `app/i18n/messages_en.py` gains 1 new key: `"feature.disabled": "This feature is temporarily disabled."`
7. `service.calculate` docstring extended to cite §12.B.1 step 8 column-by-column persistence semantics.
8. Memory entry follows §4.B format with at least one cross-reference to FEATURE_PLAN.md.

## Hard constraints
- NO float math on currency anywhere — Decimal only with ROUND_HALF_EVEN quantization.
- NO new Alembic migration — the pricing_calcs table is in baseline `935e55b4852c`.
- NO production code changes EXCEPT (a) drift fixes in `service.py` if audit finds drift, (b) the new i18n key, (c) the service.calculate docstring extension.
- NO touching `domain.py` / `exceptions.py` / `repository.py` / `schemas.py` — they're correct per the audit framing in FEATURE_PLAN §5.A.
- DO NOT add a feature-flag check inside `service.calculate` — that belongs at the route boundary (api-routes-builder owns it per §7.B).
- DO NOT delete `backend/app/services/pricing_engine.py` — the file does not exist; the §0.E latent bug is already resolved.

## Files you may touch
- backend/app/modules/pricing/service.py (drift fix + docstring extension only)
- backend/app/i18n/messages_en.py (add 1 key)
- docs/BACKEND_ARCHITECTURE.md (§12.B.1 step 8 doc fix + §12 STATUS amendment)
- docs/V1_FEATURE_SPEC.md (§F7 implementation stamp)
- backend/tests/modules/pricing/test_pnl_formula.py (extend with 10 golden cases)
- .claude/agent-memory/meesell-services-builder/MEMORY.md (session entry per §4.B)
- docs/status/feature_board_backend.md (your row updates per §4.A)

## Files you must NOT touch
- backend/app/services/* (directory does not exist — do not recreate)
- backend/app/modules/pricing/{domain,exceptions,repository,schemas,router,__init__}.py
- backend/app/shared/models/pricing_calc.py
- backend/alembic/versions/*
- frontend/* (out of domain)
- Anything under another feature's planning directory

## Branch
You are working on `feature/price-calculator/backend`. If the branch does not exist, the backend lead creates it from `feature/price-calculator` per FEATURE_PLAN §3.B before dispatching you.

## Final report format
- Audit findings table (one row per §12 contract clause: clause | matched | drift detected | drift severity | action taken)
- pytest summaries for unit + integration suites
- The 10 golden Decimal cases as a code block
- The exact diff applied to `BACKEND_ARCHITECTURE.md §12.B.1 step 8`
- Feature-board row update confirmation
- Memory entry (cite session H2 heading)
```

### 7.B — `meesell-api-routes-builder` dispatch (feature flag wiring)

```
SESSION: mesell-price-calculator-backend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.
DISPATCHED BY: meesell-backend-coordinator (per FEATURE_PLAN §2.A)
FEATURE: price-calculator (per FEATURE_PLAN.md §1.B — Feature flag posture)

## Your mission
Add the `FEATURE_PRICE_CALCULATOR_ENABLED` Settings field; gate `POST /api/v1/products/{id}/price-calc` to return 404 with `validation_message_id="feature.disabled"` when the flag is `false`. Write the unit test for both states.

## Mandatory reads (in this order)
- docs/plans/features/price-calculator/FEATURE_PLAN.md §1.B (flag posture) + §5.A row for router.py + §6 deliverable 1
- docs/plans/repo_management/MASTER_PLAN.md §3.2 (feature-flag protocol — backend section)
- docs/BACKEND_ARCHITECTURE.md §12.B.1 (the locked endpoint contract)
- backend/app/modules/pricing/router.py (target)
- backend/app/shared/config.py (target — add Settings field)
- backend/app/i18n/messages_en.py (must contain `feature.disabled` — services-builder ships this in §7.A; if not yet shipped, you wait or hold)
- backend/app/core/errors.py (to understand the validation_message_id → response envelope mapping)
- backend/tests/modules/pricing/conftest.py (test fixtures)
- .claude/agent-memory/meesell-api-routes-builder/MEMORY.md (your own memory)
- .claude/agent-memory/meesell-services-builder/handoff_price-calculator_doc-defect.md (if present — read the upstream context)

## Acceptance criteria
1. `shared/config.py` `Settings` class has new field `feature_price_calculator_enabled: bool = True` (dev default true per FEATURE_PLAN §1.B; staging overrides via env var).
2. `modules/pricing/router.py` `price_calc` handler adds a single guard at the top BEFORE calling `pricing_service.calculate`:
   ```python
   if not settings.feature_price_calculator_enabled:
       raise HTTPException(
           status_code=404,
           detail={"validation_message_id": "feature.disabled"},
       )
   ```
   (Or equivalent using the existing error-envelope pattern — match what `core/errors.py` expects. Do NOT bypass the §4.F envelope.)
3. New test file `backend/tests/modules/pricing/test_feature_flag.py`:
   - Test 1: flag=true → request returns 200 with valid `PriceCalcResponse`.
   - Test 2: flag=false → request returns 404 with body `{"detail": {"validation_message_id": "feature.disabled"}}` (or whatever envelope shape `core/errors.py` produces — match it).
   - Use `monkeypatch` or fixture override to flip the flag per test.
4. OpenAPI snapshot: confirm `curl http://localhost:8001/openapi.json | jq '.paths."/api/v1/products/{id}/price-calc"'` shows the Decimal-typed fields with `multipleOf: 0.01`. Paste output in PR.
5. Memory entry follows §4.B format.
6. Handoff memo to angular-service-builder: `.claude/agent-memory/meesell-api-routes-builder/handoff_price-calculator_flag-404-shape.md` — one paragraph describing the 404 response shape so FE treats it as "off", not "error".

## Hard constraints
- DO NOT add the flag check in `service.calculate` — flag belongs at the route boundary.
- DO NOT change the request/response Pydantic schemas — §12.E LOCKED.
- DO NOT add a separate `feature.disabled` exception subclass — the 404 here is route-level, not service-level. Use `HTTPException` direct (or the existing `core/errors.py` helper if one exists for ad-hoc 404).
- The Settings field name MUST be exactly `feature_price_calculator_enabled` (the env var is `FEATURE_PRICE_CALCULATOR_ENABLED` — Pydantic auto-uppercases).

## Files you may touch
- backend/app/shared/config.py
- backend/app/modules/pricing/router.py
- backend/tests/modules/pricing/test_feature_flag.py (NEW)
- .claude/agent-memory/meesell-api-routes-builder/MEMORY.md
- .claude/agent-memory/meesell-api-routes-builder/handoff_price-calculator_flag-404-shape.md (NEW)
- docs/status/feature_board_backend.md (row updates)

## Files you must NOT touch
- backend/app/modules/pricing/service.py (services-builder territory)
- backend/app/i18n/messages_en.py (services-builder territory)
- backend/app/modules/pricing/{schemas,domain,exceptions,repository}.py
- frontend/*

## Branch
You are working on `feature/price-calculator/backend`. Rebase on the latest tip after services-builder lands the i18n key + audit changes.

## Final report format
- The 2-line `config.py` diff
- The router.py diff (should be < 10 lines)
- pytest summary for test_feature_flag.py (both cases pass)
- OpenAPI excerpt for the endpoint
- Confirmation that the handoff memo is written
```

### 7.C — `meesell-database-builder` dispatch (commission_pct seed verification)

```
SESSION: mesell-price-calculator-backend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.
DISPATCHED BY: meesell-backend-coordinator (per FEATURE_PLAN §2.A)
FEATURE: price-calculator (per FEATURE_PLAN.md §5.A row "database-builder")

## Your mission
Verify that `categories.commission_pct` is populated on the dev database for the 3,772 active categories. If gaps surface, write a fixup seed script (NOT a migration) under `backend/scripts/`. If the gap source is in the per-category XLSX templates, escalate to data lead.

## Mandatory reads (in this order)
- docs/plans/features/price-calculator/FEATURE_PLAN.md §5.A row for database-builder + §0.A row for commission_pct seeding
- docs/BACKEND_ARCHITECTURE.md §9 (category module — owns `categories.commission_pct` column) + §12.B.1 step 4 (pricing reads commission via `category.service.get_commission`)
- backend/app/shared/models/category.py (column definition: `commission_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))`)
- backend/scripts/ (look for existing category seeding logic — e.g., `meesho_batch_scraper.py`)
- backend/app/data/category_attributes.json + meesho_category_tree.json (current seed sources)
- .claude/agent-memory/meesell-database-builder/MEMORY.md
- .claude/agent-memory/meesell-data-engineer/MEMORY.md (last 3 turns — context on XLSX parsing pipeline)

## Acceptance criteria
1. Coverage report posted in PR: SQL `SELECT COUNT(*) FILTER (WHERE commission_pct IS NULL) AS nulls, COUNT(*) AS total FROM categories;` — paste output for dev DB.
2. If `nulls = 0` → done. Update feature_board_backend.md row to MERGED for the database-builder slice. Memory entry confirms verification.
3. If `nulls > 0`:
   a. Investigate origin: are the NULL rows from a known seed gap (xlsx-parser didn't extract from those templates) OR a data-track issue?
   b. If gap is in per-category XLSX templates and requires re-parsing → open inter-lead row in feature_board_backend.md → data; write handoff memo `.claude/agent-memory/meesell-database-builder/handoff_price-calculator_commission-gap.md` with the NULL category IDs (or representative sample); STATUS=BLOCKED until data lead returns the gap fixed.
   c. If gap is fillable from `category_attributes.json` directly → write `backend/scripts/seed_category_commissions.py` (idempotent, takes JSON path + DB URL, runs `UPDATE categories SET commission_pct = ? WHERE id = ? AND commission_pct IS NULL`). Run it against dev DB. Re-run the coverage check; confirm `nulls = 0`.
4. Memory entry follows §4.B format. Cite FEATURE_PLAN §5.A and the coverage SQL.

## Hard constraints
- DO NOT create a new Alembic migration — the `commission_pct` column already exists.
- DO NOT write to the categories table outside the fixup seed script (no inline psql).
- DO NOT modify `category` module ORM, service, or repository (category lead's territory; backend-coordinator approves cross-module changes).
- DO NOT touch the XLSX parser — that is data-engineer + xlsx-parser territory.

## Files you may touch
- backend/scripts/seed_category_commissions.py (NEW — CONDITIONAL on nulls>0)
- .claude/agent-memory/meesell-database-builder/MEMORY.md
- .claude/agent-memory/meesell-database-builder/handoff_price-calculator_commission-gap.md (CONDITIONAL — if escalating to data)
- docs/status/feature_board_backend.md (row updates; inter-lead row if escalating)

## Files you must NOT touch
- backend/alembic/versions/*
- backend/app/shared/models/category.py
- backend/app/modules/category/*
- backend/app/data/category_attributes.json (data-engineer territory)

## Branch
You are working on `feature/price-calculator/backend`. Rebase on services-builder + api-routes-builder tips.

## Final report format
- Coverage SQL + output
- Decision tree result (a/b/c above) with the path you took
- If seed script written: the diff + the script's stdout from the dev run
- If escalating: link to the handoff memo
- Memory entry
```

### 7.D — `meesell-angular-component-builder` dispatch (3-component split)

```
SESSION: mesell-price-calculator-frontend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.
DISPATCHED BY: meesell-frontend-coordinator (per FEATURE_PLAN §2.A)
FEATURE: price-calculator (per FEATURE_PLAN.md §1.C — 3-component split)

## Your mission
Refactor the 327-line monolithic `PricingComponent` into three standalone components per V1_FEATURE_SPEC §F7 + FRONTEND_ARCH Layer 4 rules. Preserve the existing `pricing.utils.computePnlBreakdown` local-recompute helper — wire it through the new `PricingService.recomputeFromSnapshot()` (which the angular-service-builder ships in §7.E).

## Mandatory reads (in this order)
- docs/plans/features/price-calculator/FEATURE_PLAN.md §1.C (D3 decision) + §5.B (frontend file table) + §6 deliverables 5 + 6 (docstring contracts)
- docs/V1_FEATURE_SPEC.md §F7 (the canonical 3-component list)
- docs/FRONTEND_ARCHITECTURE.md (Layer 4 rules — features import ONLY from @mee/ui, @mee/shared, @mee/layouts, ./services; ZERO PrimeNG direct imports)
- frontend/src/app/features/pricing/pricing/pricing.component.ts (existing 327-line target — split source)
- frontend/src/app/features/pricing/pricing/pricing.component.spec.ts (existing 212-line spec — split source)
- frontend/src/app/features/pricing/pricing/pricing.model.ts (existing types)
- frontend/src/app/features/pricing/pricing/pricing.utils.ts (the slider-locality helper — preserve)
- frontend/src/app/ui/index.ts (the mee-* primitives barrel — confirm available primitives)
- frontend/src/app/shared/index.ts (the composites barrel — confirm available composites)
- .claude/agent-memory/meesell-angular-component-builder/MEMORY.md
- .claude/agent-memory/meesell-frontend-coordinator/MEMORY.md (recent turns on Layer 4 patterns)

## Acceptance criteria
1. `pricing.component.ts` is reduced to ~150 lines max. It owns:
   - `/catalogs/:id/pricing` route binding
   - Reactive form (input_cost, target_margin_pct) — use `MeeInputComponent` for inputs
   - Calls `PricingService.calculate()` ONCE on form submit; ONCE on Accept click
   - Holds the breakdown signal that flows down to `PnlBreakdownComponent` + `MarginSliderComponent`
   - Page header via `PageHeaderComponent`
2. `pnl-breakdown.component.ts` (NEW) is a presentational standalone component:
   - `@Input() breakdown: PnlBreakdown` (use the existing model in pricing.model.ts)
   - Renders 6 rows in this exact order: MRP / Meesho Price / Commission (% + ₹) / GST (% + ₹) / Seller Payout / Net Margin (% + ₹)
   - Applies red row class (`bg-[var(--mee-color-error-light)]` or equivalent) when `breakdown.margin < 0`
   - `ChangeDetectionStrategy.OnPush`
   - NO PrimeNG direct import. Use `mee-card` wrapper or plain semantic `<table>` with Tailwind utilities.
3. `margin-slider.component.ts` (NEW) is an interactive standalone component:
   - `@Input() snapshot: PnlBreakdown` (the last server-returned breakdown — the snapshot for local recompute)
   - `@Output() breakdownChange = new EventEmitter<PnlBreakdown>()` (emits on every tick)
   - Uses native `<input type="range">` (no `mee-slider` primitive in UI Kit yet — that's a future UI Kit addition)
   - On input event: calls `inject(PricingService).recomputeFromSnapshot(snapshot, newMrp)` locally → emits the result
   - NO calls to `PricingService.calculate()` anywhere in this component.
   - `ChangeDetectionStrategy.OnPush`
4. Class docstring on `MarginSliderComponent` MUST include verbatim: "Slider-locality contract: this component invokes `PricingService.recomputeFromSnapshot` locally on every tick. It MUST NOT call `PricingService.calculate` (the HttpClient surface). Frontend-lead PR review verifies zero `/price-calc` requests during slider drag via Chrome DevTools." (per FEATURE_PLAN §6 deliverable 5)
5. Class docstring on `PnlBreakdownComponent` MUST include verbatim: "6-row P&L breakdown per V1_FEATURE_SPEC §F7 acceptance criteria. Row sequence: MRP / Meesho Price / Commission / GST / Seller Payout / Net Margin. Red `var(--mee-color-error)` row class applied when `breakdown.margin < 0` (negative-margin warning)." (per §6 deliverable 6)
6. Spec files mirror the component boundaries:
   - `pricing.component.spec.ts` trimmed to page-level tests (route binding, form submit triggers PricingService.calculate exactly ONCE)
   - `pnl-breakdown.component.spec.ts` (NEW) — renders 6 rows; red class applies when margin negative; OnPush honored
   - `margin-slider.component.spec.ts` (NEW) — drag emits N breakdowns; HttpClient spy shows 0 calls during drag
7. Memory entry per §4.B + handoff memo to angular-service-builder if any contract changes ripple to the service surface.

## Hard constraints
- NO PrimeNG direct imports anywhere in `features/pricing/`. Use `@mee/ui` primitives + native HTML for the slider.
- NO Angular Material imports anywhere in `features/pricing/`. (FRONTEND_ARCH explicitly bans both — Layer 4 rule.)
- NO API call per slider tick. This is the slider-locality contract — non-negotiable. Verified in the spec file (HttpClient spy).
- NO touching `pricing.utils.ts` — it stays as the canonical compute helper. `PricingService.recomputeFromSnapshot` wraps it.
- NO touching backend code.
- DO NOT add new dependencies to package.json.

## Files you may touch
- frontend/src/app/features/pricing/pricing/pricing.component.ts (refactor)
- frontend/src/app/features/pricing/pricing/pricing.component.spec.ts (refactor)
- frontend/src/app/features/pricing/pricing/pnl-breakdown.component.ts (NEW)
- frontend/src/app/features/pricing/pricing/pnl-breakdown.component.spec.ts (NEW)
- frontend/src/app/features/pricing/pricing/margin-slider.component.ts (NEW)
- frontend/src/app/features/pricing/pricing/margin-slider.component.spec.ts (NEW)
- frontend/src/app/features/pricing/pricing/index.ts (NEW barrel — preferred Layer 4 pattern)
- frontend/src/app/features/pricing/pricing/pricing.model.ts (extend if new types needed — verify first)
- .claude/agent-memory/meesell-angular-component-builder/MEMORY.md
- docs/status/feature_board_frontend.md (row updates)

## Files you must NOT touch
- frontend/src/app/features/pricing/pricing/pricing.utils.ts (the slider-locality helper — leave alone)
- frontend/src/app/features/pricing/pricing/pricing.service.ts (angular-service-builder territory)
- frontend/src/app/app.routes.ts (angular-service-builder territory — featureFlagGuard wiring)
- frontend/src/app/ui/* (UI Kit — out of scope for this dispatch)
- backend/*

## Branch
You are working on `feature/price-calculator/frontend`. Frontend lead cuts this branch from `feature/price-calculator` when dispatching you.

## Final report format
- File-level diff summary table (line counts per file before/after)
- `ng test --watch=false --include="src/app/features/pricing/**/*.spec.ts"` summary (all green)
- `ng build` size delta (paste bundle size before/after — should be neutral or improve due to OnPush)
- Manual verification: open `/catalogs/:id/pricing` in dev, drag the slider 10 times, attach Chrome DevTools Network tab screenshot showing zero `/price-calc` requests during the drag
- Memory entry
```

### 7.E — `meesell-angular-service-builder` dispatch (PricingService + feature-flag guard wiring)

```
SESSION: mesell-price-calculator-frontend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.
DISPATCHED BY: meesell-frontend-coordinator (per FEATURE_PLAN §2.A)
FEATURE: price-calculator (per FEATURE_PLAN.md §1.B + §1.C)

## Your mission
Extract `PricingService` from the existing `PricingComponent`. Provide `calculate()` (HttpClient wrapper) and `recomputeFromSnapshot()` (pure local-recompute helper). Wire `featureFlagGuard` on the `/catalogs/:id/pricing` route per the locked D2 flag posture.

## Mandatory reads (in this order)
- docs/plans/features/price-calculator/FEATURE_PLAN.md §1.B (flag) + §1.C (FE split) + §5.B (file table) + §6 deliverable 7 (route docstring)
- docs/plans/repo_management/MASTER_PLAN.md §3.2 (frontend feature-flag protocol)
- docs/V1_FEATURE_SPEC.md §F7 (response shape)
- docs/BACKEND_ARCHITECTURE.md §12.B.1 (PriceCalcRequest/Response — must match)
- frontend/src/app/features/pricing/pricing/pricing.utils.ts (the canonical compute helper — your `recomputeFromSnapshot` wraps this)
- frontend/src/app/features/pricing/pricing/pricing.model.ts (existing types — extend if needed)
- frontend/src/app/features/pricing/pricing/pricing.component.ts (read the existing inline HttpClient calls — your extraction source)
- frontend/src/app/app.routes.ts (current route table — add featureFlagGuard)
- frontend/src/app/core/services/feature-flags.service.ts (verify or extend)
- frontend/src/app/core/guards/ (existing guard patterns — match the convention)
- frontend/src/app/core/interceptors/auth.interceptor.ts (read to understand HttpClient + Bearer token setup)
- .claude/agent-memory/meesell-angular-service-builder/MEMORY.md
- .claude/agent-memory/meesell-api-routes-builder/handoff_price-calculator_flag-404-shape.md (the upstream 404 response shape contract — match the FE handling)

## Acceptance criteria
1. `pricing.service.ts` (NEW) standalone injectable:
   ```typescript
   @Injectable({ providedIn: 'root' })
   export class PricingService {
     private readonly http = inject(HttpClient);
     calculate(productId: string, request: PriceCalcRequest): Observable<PriceCalcResponse> {
       return this.http.post<PriceCalcResponse>(`/api/v1/products/${productId}/price-calc`, request);
     }
     recomputeFromSnapshot(snapshot: PnlBreakdown, newMrp: number): PnlBreakdown {
       return computePnlBreakdown({ ...snapshot, mrp: newMrp });
     }
   }
   ```
   (Adjust to actual types in `pricing.model.ts` — exact field names match backend §12.E.)
2. `pricing.service.spec.ts` (NEW):
   - `calculate()` test: HttpClient mock returns canned response → service emits it.
   - `recomputeFromSnapshot()` test: parametrized over the 10 golden Decimal cases (same fixture as backend test_pnl_formula.py per §7.A acceptance criterion 3). Each case asserts the recomputed breakdown matches expected values within ±0.01.
3. `feature-flags.service.ts` extended (or created if absent) to expose `priceCalculator: boolean` flag — read from `environment.featureFlags.priceCalculator` (build-time env per repo-management MASTER_PLAN §3.2).
4. `feature-flag.guard.ts` (verify or create) — generic functional guard `featureFlagGuard(flagName: keyof FeatureFlags): CanActivateFn`. Returns true if flag enabled; redirects to `/feature-disabled?feature=price-calculator` (or shows inline placeholder — match existing FE convention) when false.
5. `app.routes.ts` MODIFY — `/catalogs/:id/pricing` route entry adds `canActivate: [featureFlagGuard('priceCalculator')]`. Inline comment: `// FEATURE_PRICE_CALCULATOR_ENABLED gating per FEATURE_PLAN.md §1.B`
6. HTTP error handling: if backend returns 404 with `validation_message_id="feature.disabled"` (per the upstream handoff memo), the service-level errorInterceptor recognizes it and routes to the placeholder — NOT to the generic error toast. (If errorInterceptor doesn't have feature-flag-aware handling yet, add a narrow check for this validation_message_id.)
7. Memory entry per §4.B.

## Hard constraints
- NO direct PrimeNG/Material imports.
- NO new HttpClient instance — use the global one via `inject(HttpClient)`.
- The `recomputeFromSnapshot` MUST be pure (no service-state mutation, no HTTP) so the slider-locality contract is preserved.
- The featureFlagGuard MUST be reusable (not pricing-specific) — other features will reuse it (smart-picker, image-precheck, etc.).
- DO NOT touch `pricing.utils.ts` — wrap it, don't reinvent it.
- DO NOT touch component files — that is angular-component-builder territory.

## Files you may touch
- frontend/src/app/features/pricing/pricing/pricing.service.ts (NEW)
- frontend/src/app/features/pricing/pricing/pricing.service.spec.ts (NEW)
- frontend/src/app/features/pricing/pricing/pricing.model.ts (extend if needed)
- frontend/src/app/core/services/feature-flags.service.ts (verify/extend)
- frontend/src/app/core/guards/feature-flag.guard.ts (verify/create)
- frontend/src/app/app.routes.ts (modify pricing route entry)
- frontend/src/app/core/interceptors/error.interceptor.ts (add feature.disabled handling — narrow)
- frontend/src/environments/environment.ts + environment.staging.ts (add featureFlags.priceCalculator)
- .claude/agent-memory/meesell-angular-service-builder/MEMORY.md
- docs/status/feature_board_frontend.md (row updates)

## Files you must NOT touch
- frontend/src/app/features/pricing/pricing/pricing.component.ts (component-builder territory)
- frontend/src/app/features/pricing/pricing/pnl-breakdown.component.ts (component-builder territory)
- frontend/src/app/features/pricing/pricing/margin-slider.component.ts (component-builder territory)
- frontend/src/app/features/pricing/pricing/pricing.utils.ts (do not modify)
- frontend/src/app/ui/* (UI Kit — out of scope)
- backend/*

## Branch
You are working on `feature/price-calculator/frontend`. Rebase on the angular-component-builder tip before opening your PR.

## Final report format
- pricing.service.ts diff (full)
- pricing.service.spec.ts diff (full)
- app.routes.ts diff (the 1-line guard addition + comment)
- feature-flag guard diff (if new) or grep-confirmation it already exists
- error.interceptor.ts diff (the feature.disabled narrow handler)
- `ng test --watch=false --include="src/app/features/pricing/**/*.service.spec.ts"` summary (all green)
- Memory entry
```

### 7.F — `meesell-xlsx-parser` dispatch (CONDITIONAL — only if commission_pct gap)

```
SESSION: mesell-price-calculator-data-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.
DISPATCHED BY: meesell-data-engineer (per FEATURE_PLAN §2.A — CONDITIONAL)
FEATURE: price-calculator (per FEATURE_PLAN.md §5.A row "xlsx-parser CONDITIONAL")

## Activation precondition
This dispatch is INERT until `meesell-database-builder` posts a handoff memo at `.claude/agent-memory/meesell-database-builder/handoff_price-calculator_commission-gap.md` reporting commission_pct NULL count > 0 with category IDs. If no such memo exists, do NOT proceed.

## Your mission
Extract `commission_pct` from per-category XLSX templates already parsed under `backend/app/data/`. Produce a JSON map `{category_id: commission_pct}` consumable by `backend/scripts/seed_category_commissions.py` (which database-builder ships in §7.C).

## Mandatory reads
- docs/plans/features/price-calculator/FEATURE_PLAN.md §2.A row + §5.A
- .claude/agent-memory/meesell-database-builder/handoff_price-calculator_commission-gap.md (the activation memo)
- backend/scripts/meesho_batch_scraper.py + meesho_template_scraper.py (existing parser code)
- backend/app/data/category_attributes.json (current attribute extraction)
- backend/app/data/meesho_category_tree.json (the canonical 3,772 category list)
- docs/PLAYWRIGHT_MCP_REFERENCE.md (your standard reference)
- .claude/agent-memory/meesell-xlsx-parser/MEMORY.md
- .claude/agent-memory/meesell-data-engineer/MEMORY.md

## Acceptance criteria
1. `backend/app/data/category_commissions.json` (NEW) — JSON map `{category_id_uuid: commission_pct_decimal_string}` for all categories where database-builder reported NULL.
2. Coverage report: number of categories successfully extracted vs total NULL count. If < 100% coverage, flag the remaining in PR description with reasoning (template-format mismatch, XLSX doesn't carry commission, etc.).
3. Handoff memo close: append "RESOLVED" line to database-builder's memo + push back to backend lead via inter-lead row close.
4. Memory entry per §4.B.

## Hard constraints
- DO NOT write directly to the categories DB table — your output is JSON; database-builder runs the UPDATE.
- DO NOT modify category ORM, parser pipeline scripts, or seed dataclasses beyond what's needed to add commission extraction.
- DO NOT re-scrape Meesho — work only from already-parsed local XLSX templates.

## Files you may touch
- backend/app/data/category_commissions.json (NEW)
- backend/scripts/ (possibly a one-off extractor script if existing parser doesn't carry the commission column — name it `extract_category_commissions.py`)
- .claude/agent-memory/meesell-xlsx-parser/MEMORY.md
- docs/status/feature_board_data.md (row updates)

## Files you must NOT touch
- backend/app/shared/models/category.py
- backend/app/modules/category/*
- backend/alembic/versions/*

## Branch
If the data lead has not cut `feature/price-calculator/data` yet, request it before pushing. Otherwise work on that branch.

## Final report format
- Coverage report (extracted vs total NULL count)
- The JSON map file (or a representative excerpt + line count)
- Handoff memo close-out line
- Memory entry
```

---

## 8. Review + iteration protocol

### 8.A — What the lead checks before approving each specialist's PR

| Specialist | Lead's PR-review checklist (must-tick) |
|---|---|
| services-builder | (1) Audit findings table is complete + matches §12 LOCKED clause-by-clause; (2) all unit + integration tests pass (paste summaries); (3) 10 golden Decimal cases extension lands in `test_pnl_formula.py`; (4) `BACKEND_ARCHITECTURE.md §12.B.1 step 8` doc fix matches FEATURE_PLAN §5.D verbatim; (5) NO `services/pricing_engine.py` recreation; (6) memory entry tagged per §4.B; (7) `feature_board_backend.md` row reflects IN REVIEW |
| api-routes-builder | (1) `feature_price_calculator_enabled` Settings field exists with `True` default; (2) router 404 path returns `feature.disabled` validation_message_id via the `core/errors.py` envelope (NOT raw `HTTPException`); (3) `test_feature_flag.py` covers both states; (4) OpenAPI snapshot shows Decimal types intact; (5) handoff memo to angular-service-builder exists; (6) memory entry tagged per §4.B |
| database-builder | (1) coverage SQL output pasted; (2) if `nulls > 0`: either fixup seed script lands AND `nulls = 0` after re-run, OR clean escalation to data lead is documented (memo + inter-lead row); (3) NO new Alembic migration; (4) NO direct UPDATEs outside the seed script; (5) memory entry tagged per §4.B |
| angular-component-builder | (1) `pricing.component.ts` ≤ 150 lines (was 327); (2) 2 NEW components (`pnl-breakdown` + `margin-slider`) exist with class docstrings matching FEATURE_PLAN §6 deliverables 5 + 6 verbatim; (3) NO PrimeNG/Material direct imports anywhere in `features/pricing/` (grep-verified); (4) Chrome DevTools screenshot proves zero `/price-calc` requests during slider drag; (5) `ng test` for pricing specs green; (6) `ng build` bundle size delta is neutral or improved; (7) memory entry tagged per §4.B |
| angular-service-builder | (1) `PricingService` exists at the spec'd path with `calculate()` + `recomputeFromSnapshot()`; (2) `pricing.service.spec.ts` runs the 10 golden Decimal cases AND they all pass; (3) `featureFlagGuard` wired on `/catalogs/:id/pricing` route with the inline FEATURE_PLAN §1.B comment; (4) `error.interceptor.ts` recognizes `feature.disabled`; (5) memory entry tagged per §4.B; (6) handoff memo from api-routes-builder is acknowledged-closed |
| xlsx-parser (conditional) | (1) `category_commissions.json` exists with non-empty content; (2) coverage report posted; (3) database-builder handoff memo carries RESOLVED line; (4) inter-lead row on feature_board_data.md closed; (5) memory entry tagged per §4.B |

### 8.B — Acceptance gate from `.github/PULL_REQUEST_TEMPLATE/{backend,frontend}.md`

Per repo-management MASTER_PLAN §5.2 (backend) + §5.3 (frontend):

- **Backend PRs** (`feature/price-calculator/backend → feature/price-calculator`): migration evidence (N/A — no migration this feature), Module touched: `app/modules/pricing/` + `app/shared/config.py`, Contract changes: none (route flag-gate is additive — backwards-compatible 404), Integration test path: `backend/tests/integration/test_pricing_*.py`, CI gates 1+2+3 green.
- **Frontend PRs** (`feature/price-calculator/frontend → feature/price-calculator`): Components touched: 3 new + 1 refactored, Layer architecture compliance: Layer 4 only, Build evidence: `pnpm build` < 90s, Bundle size delta noted, Routes: featureFlagGuard added to `/catalogs/:id/pricing`, Visual evidence: screenshots at 360 px + 1280 px + Chrome DevTools no-network-call screenshot.

### 8.C — Re-dispatch triggers (specific failure modes → re-dispatch prompt)

| Failure mode | Re-dispatch preamble |
|---|---|
| Decimal math off by 0.01 in audit findings | "Previous run reported drift in `_compute_pnl` Decimal precision. Re-audit with explicit `Decimal.getcontext().prec` verification + `ROUND_HALF_EVEN` confirmation per Python default. Verify NO `float()` cast anywhere in the chain — use ruff regex search `\\bfloat\\(` on `service.py`. Re-run the 10 golden cases; if any drift, identify the exact line and fix." |
| `_generate_alerts` missing one of LOW_MARGIN / HIGH_MRP_MULTIPLIER / THIN_PROFIT codes | "Previous run's `_generate_alerts` audit found code-emit gap. Re-verify against §12.F locked thresholds: LOW_MARGIN profit_pct<10, HIGH_MRP_MULTIPLIER mrp/input_cost>3, THIN_PROFIT profit<50. Multiple alerts may fire simultaneously. Test each independently + in combination (low input_cost case triggers BOTH THIN_PROFIT and LOW_MARGIN per §12.F)." |
| PricingAlert referenced from `app/schemas/pricing.py` (does not exist) | "Previous run located PricingAlert in wrong path. The legacy `app/schemas/pricing.py` is DELETED — does not exist. PricingAlert lives at `app/modules/pricing/domain.py` per §12.F + §3.C per-module subtree. Re-locate imports; the existing service.py + repository.py + router.py already import from the correct location — verify nothing creates a parallel schemas-level PricingAlert." |
| Slider triggers network call per tick (Chrome DevTools shows `/price-calc` during drag) | "Previous run violated slider-locality contract per FEATURE_PLAN §1.C. MarginSliderComponent MUST call `pricingService.recomputeFromSnapshot()` locally on tick — NEVER `pricingService.calculate()`. Verify the subscription in `margin-slider.component.ts` `onSliderInput()` handler; verify the test spec spies on HttpClient and asserts 0 calls during a multi-tick drag." |
| PrimeNG direct import found in any of the 3 new components | "Previous run violated FRONTEND_ARCH Layer 4 rule. NO `import { ... } from 'primeng/...'` in `frontend/src/app/features/pricing/**`. Use `@mee/ui` primitives or plain HTML. Re-grep `grep -r 'from .primeng/' frontend/src/app/features/pricing/` — expected 0 results." |
| Feature flag check inside `service.calculate` (should be at route boundary) | "Previous run misplaced the FEATURE_PRICE_CALCULATOR_ENABLED check inside `service.py`. The flag belongs at the route boundary per FEATURE_PLAN §1.B + §7.B. Move the guard to `modules/pricing/router.py` `price_calc` handler; service.calculate stays unaware of the flag." |
| `commission_pct` seed gap escalation goes 48h without acknowledgement | "Previous database-builder dispatch opened inter-lead row to data lead 48h ago — no acknowledgement. Escalate to founder via STATUS_MASTER.md blockers section per MASTER_PLAN §7.5. Hold the backend group PR open with BLOCKED status until data lead returns." |
| `BACKEND_ARCHITECTURE.md §12.B.1 step 8` doc fix not done | "Previous services-builder dispatch left the §12.B.1 step 8 prose at the OLD (input_jsonb/output_jsonb) wording. The actual code persists column-by-column per `shared/models/pricing_calc.py`. Apply the exact replacement text per FEATURE_PLAN §5.D row." |

### 8.D — Re-dispatch template (generic)

The lead pastes this preamble in front of the original template from §7 + adjusts the SESSION number to `{N+1}`:

```
RE-DISPATCH — Previous session mesell-price-calculator-{group}-session-{N} returned with the following failure(s):
- <failure mode from §8.C>
- <link to PR comment / lead review note>

Fix-by reading:
- <specific FEATURE_PLAN section that addresses the failure>
- <specific BACKEND_ARCHITECTURE or FRONTEND_ARCHITECTURE clause>
- <the previous session's memory entry — read your own H2 entry for context>

Then execute the original dispatch (§7.{A-F}) verbatim with the additional acceptance criterion: the previous failure mode does not recur.
```

### 8.E — Maximum iteration count

**3 iterations max** per specialist. If a specialist's PR is still failing review after the 3rd dispatch:
1. Lead escalates to founder via STATUS_MASTER.md blockers section.
2. Founder evaluates: (a) re-scope the work (split into smaller dispatches), (b) replace the specialist with a different one (e.g., services-builder → coordinator authors the slice directly), (c) defer the slice to V1.5.
3. The decision is recorded in `docs/plans/features/price-calculator/FEATURE_PLAN.md` revision history.

---

## 9. Acceptance gate — when is `price-calculator` "done"?

This feature is DONE when ALL of the following are true:

1. **All 5 default dispatches** (services-builder + api-routes-builder + database-builder + angular-component-builder + angular-service-builder) have merged their group PRs to `feature/price-calculator`.
2. **Conditional xlsx-parser dispatch**: either inert (commission_pct=0 NULL) OR completed (data merged + handoff memo RESOLVED).
3. **All 6 documentation deliverables** per §6 are landed (OpenAPI verified, docstrings present, doc defect resolved, F7 stamp applied, feature board updated, memory tagged).
4. **CI gates 1-5 green** on `feature/price-calculator` per MASTER_PLAN §5.
5. **`feature/price-calculator → develop` PR** is opened by backend lead, approved by founder, merged with merge-commit (NOT squash per MASTER_PLAN §2.2).
6. **Dev namespace soak**: feature flag flipped ON in dev for 7 days without P0/P1 alerts.
7. **Staging gate evaluation**: per FEATURE_PLAN §1.B gates (a)-(e). When all pass, founder flips staging flag to ON via Settings env var.
8. **Feature board entries** transition: every lead's `feature_board_<domain>.md` row for `price-calculator` is in `MERGED` status (or `NOT PARTICIPATING` for ai/infra, `CONDITIONAL: NOT ACTIVATED` for data if no gap surfaced); rows move to "Recently merged" within 14 days.
9. **V1_FEATURE_SPEC.md §F7** carries the "Implemented YYYY-MM-DD via PR #N" stamp.

---

## 10. Risk register

Top 5 risks specific to this feature.

### R1 — Decimal precision regression on Pydantic schema serialization

**Severity:** HIGH. **Likelihood:** MEDIUM.

When `PriceCalcResponse` (which has many `Decimal` fields) is serialized to JSON for HTTP transport, Pydantic v2 may emit floats if `model_config` isn't strict. A response field that should be `Decimal("151.52")` could become `151.52` (float) on the wire, then the frontend parses it as JS number, then any precision-sensitive comparison drifts.

**Mitigation:**
- Services-builder audit verifies `model_config = ConfigDict(...)` on `PriceCalcResponse` doesn't include any float coercion. Add `json_encoders={Decimal: str}` if not present.
- Frontend `PricingResponse` interface types monetary fields as `string` (not `number`) when parsed; the FE recompute converts via the existing `pricing.utils` helpers which work in Decimal-string space.
- `pricing.service.spec.ts` parametrized 10 golden Decimal cases assert exact match — any drift surfaces in CI.

### R2 — `commission_pct` seed gap surfacing late

**Severity:** MEDIUM. **Likelihood:** LOW.

If `categories.commission_pct` is NULL for any of the 3,772 categories at the time pricing goes live, real sellers hit 422 `pricing.commission_missing` and bounce off. The PLANNING_DISPATCH.md flagged HSN→GST as the worry but that's obsolete; the real risk is `commission_pct` coverage.

**Mitigation:**
- Database-builder dispatch's first action: coverage SQL (per §7.C acceptance criterion 1).
- Conditional xlsx-parser dispatch closes any gap before the feature flag flips on staging.
- Staging gate (§1.B (a)-(e)) blocks until coverage is 100%.

### R3 — Slider triggers network call per tick on mobile (touch event vs mouse event)

**Severity:** MEDIUM. **Likelihood:** MEDIUM.

The slider-locality contract is enforced via spec file (HttpClient spy). But the spec file may run only with mouse events. On real mobile, touch events may bypass the `oninput` handler the spec mocks, leading to a real device emitting network calls per tick — never caught by automated test.

**Mitigation:**
- Manual mobile verification step in §7.D final report (component-builder runs Chrome DevTools mobile emulation + screenshots).
- Frontend lead's review checklist (§8.A row "angular-component-builder" item 4) requires the screenshot.
- V1.5 follow-up: add Playwright touch-event coverage to `pricing.component.spec.ts`.

### R4 — Federation pilot scope creep delaying V1 ship

**Severity:** LOW. **Likelihood:** LOW.

The module-federation MASTER_PLAN.md identifies `mfe-pricing` as the 1st pilot remote. A future session may try to fold the federation work into this feature's V1 dispatch, blowing scope.

**Mitigation:**
- D3 explicitly locks: 3-component split lives in shell (`src/app/features/pricing/`), NOT in `mfe-pricing` remote. Federation deferred per CLAUDE.md Decision 12 + module-federation MASTER_PLAN remaining DRAFT (Acceptance Gate per §9 of that plan: founder approval pending, Wave 6 not complete).
- Any future dispatch that proposes federation work on this feature must open a separate planning session per the dispatch prompt's Decision 3 escape clause.

### R5 — V1.5 RTO/shipping addition forces `pricing_calcs` schema migration

**Severity:** LOW. **Likelihood:** HIGH (V1.5 will add RTO).

V1_FEATURE_SPEC §F7 explicitly says "RTO/shipping deferred to V1.5". When V1.5 lights up, `pricing_calcs` table will need new columns (`rto_cost`, `shipping_cost`, etc.), the formula chain in §12.B.1 step 6 widens, and `PriceCalcRequest`/`Response` Pydantic schemas extend.

**Mitigation (V1, not active):**
- Service-builder docstring on `calculate()` explicitly notes the formula is V1 — V1.5 may extend.
- `PriceCalcRequest` already carries `override_commission_pct` + `override_gst_pct` as V1.5+ fields (V1 ignores) per §12.E — sets the precedent for backwards-compatible additive widening.
- This risk does NOT block V1; it's flagged here so V1.5 planning starts from "what does pricing_calcs need to look like" rather than "we forgot RTO".

---

## 11. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | master Claude planning session (`mesell-price-calculator-planning-session-1`) | Initial DRAFT. Founder decisions D1/D2/D3 locked verbatim from session AskUserQuestion responses. State audit findings recorded (backend already on develop; FE partially built; §0.E latent bug already resolved; HSN concern obsolete; §12.B.1 step 8 doc defect identified). Operating model (agent lineup + branch creation + memory hygiene) addresses founder concerns A/B/C surfaced in this session. |

---

*End of FEATURE_PLAN.md — DRAFT.*
*On founder approval, this plan becomes the executable blueprint for `feature/price-calculator/{backend,frontend}` dispatches.*
*Next step on approval: backend lead cuts `feature/price-calculator` from develop, then `feature/price-calculator/backend`, then dispatches `meesell-services-builder` per §7.A.*
