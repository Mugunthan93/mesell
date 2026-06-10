# Session Dispatch: Price Calculator — P&L Breakdown with Commission and GST
**Session name:** `mesell-price-calculator-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/price-calculator/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp shipped; smart-picker shipped (commission_pct + HSN come from the picked category — read-only access); catalog-form shipped (price-calc writes to pricing_calcs scoped by product_id, cross-module ownership via `catalog.service.assert_product_ownership` per `BACKEND_ARCHITECTURE.md §10.A`)
**Lead involvement:** Backend (pricing module — 1 endpoint POST /products/{id}/price-calc + deterministic P&L math + pricing_calcs table) · Frontend (P&L breakdown component + margin slider — first federated remote per `docs/plans/module_federation/MASTER_PLAN.md §4.2`)

---

## Why this session exists
Price Calculator is the **monetization-clarity** feature — sellers can't price products correctly without seeing commission + GST + shipping deductions broken out per category. Per `VALIDATED_PAIN_POINTS.md` theme T5 PRICING CONFUSION there are 5+ external calculators for Meesho sellers because the platform doesn't surface this math anywhere. It is also the **first frontend federated remote** per the module federation master plan (`mfe-pricing` is the pilot remote) because the math UI is self-contained, has a tight contract surface (POST + PriceCalcResponse shape), and serves as the federation pattern reference for the next 5 remotes.

Pricing is the **only deterministic AI-free V1 feature** that creates a database row (versus the read-only dashboard or stateless preview). The math is locked to `MVP_ARCHITECTURE.md §3.4 pricing math` and the test bar is unit-precision (every test case must produce exactly the same Decimal to 2 places). It is the smallest construction surface in V1 (4h backend + 5h frontend per `V1_FEATURE_SPEC §7`) which makes it the ideal pilot for the federated-remote pattern and the canonical "deterministic feature" reference for `plan_guard NOT participating` modules per backend coordinator memory turn 19.

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-price-calculator-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/price-calculator/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the Price Calculator feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for price-calculator. Verify:
pwd                                          # must print /private/tmp/mesell-wt/price-calculator or /tmp/mesell-wt/price-calculator
git worktree list | grep price-calculator      # must show this worktree
git branch --show-current                     # must print feature/price-calculator/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh price-calculator (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates, §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F7 (Feature 7: Price Calculator) — calculation within 200ms, breakdown shows MRP / Meesho Price / Commission / GST / Seller Payout / Net Margin, slider live-updates <100ms refresh, commission and GST snapshotted at calc time, negative-margin red warning, MRP < seller payout → 400, category missing commission → fallback to category-group average flagged in response, RTO/shipping deferred to V1.5
- docs/BACKEND_ARCHITECTURE.md §12 (pricing module — 1 endpoint POST /products/{id}/price-calc; deterministic P&L math NO AI; resolves §0.E latent services/pricing_engine.py PricingAlert import bug via delete-legacy + write-clean path; new PricingAlert frozen dataclass lives in modules/pricing/domain.py per §3.C per-module subtree; plan_guard NOT participating in V1)
- docs/MVP_ARCHITECTURE.md §3.4 (pricing math — the canonical formula chain: meesho_price = mrp × (1 - commission_pct/100); seller_price = meesho_price - (meesho_price × gst_pct/100); margin = seller_price - cost_basis; margin_pct = margin / mrp × 100)
- docs/FRONTEND_ARCHITECTURE.md — pricing components live in mfe-pricing (1st federated remote — the pilot per module_federation MASTER_PLAN §4.2); PricingComponent + PnlBreakdownComponent + MarginSliderComponent; pricing is the smallest self-contained remote suitable for the federation pattern reference
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — pricing is service 4 of 8 in extraction order (per BACKEND_ARCHITECTURE.md §16.H — clean extraction because owns 1 table + 1 endpoint + no cross-module write)
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — pricing is the 1st remote (mfe-pricing pilot); this feature's planning includes the federation seam decisions (webpack module federation config, shared singleton list, route exposure)
- CLAUDE.md — Pydantic v2 + SQLAlchemy 2.0, Decimal precision (no float math on currency), Decision 12 (Module Federation deferred to Phase 2 — but the master plan supersedes this for V1 federation pilot)
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md
- Each involved lead's MEMORY.md (especially backend-coordinator turn 19 for the §12 module deep content and the latent pricing_engine.py PricingAlert import bug resolution path)
- Each involved lead's docs/status/feature_board_{backend|frontend}.md (verify price-calculator is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/price-calculator.yaml instead.

Create (or overwrite) docs/plans/features/_status/price-calculator.yaml with:
feature: "price-calculator"
session: "mesell-price-calculator-planning-session-1"
worktree: "/tmp/mesell-wt/price-calculator"
branch: "feature/price-calculator/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/price-calculator/FEATURE_PLAN.md
feature_plan_line_count: null
pr_number: null
pr_url: null
outstanding_founder_decisions: []
notes: |
  Planning session opened in worktree.
 
DO NOT commit this file yet — it will be committed alongside FEATURE_PLAN.md in Step 8.

If your status file already exists and shows IN_PROGRESS (a prior session was interrupted): proceed but flag this in the ## Decisions section of your FEATURE_PLAN.md so the founder knows.
## Step 1 — Surface scope decisions to the founder
Before drafting the plan, ask the founder to lock these 3 questions:

Decision 1 — Scope confirmation
  Does this feature still match V1 spec §F7? Specifically:
    - Calculation within 200ms (pure deterministic math, no I/O beyond category fetch)
    - Breakdown: MRP, Meesho Price, Commission, GST, Seller Payout, Net Margin (6 line items)
    - MarginSliderComponent live-updates the breakdown <100ms refresh (client-side recompute, no API call per slider tick)
    - commission_pct and gst_pct SNAPSHOTTED at calc time into pricing_calcs row (resilient to later category edits)
    - Negative-margin scenarios show red warning
    - V1 limitation: RTO/shipping deferred — UI shows note "Shipping not included in V1"
    - V1 limitation: GST rate sourced from category HSN — verify the data track has HSN-rate mapping; if not, FLAG to founder before planning
    - V1 limitation: category missing commission falls back to category-group average with flag in response
  Also resolve: Is the slider's <100ms refresh done by re-calling the API per tick OR by computing locally on the frontend (server returns the full breakdown once; frontend recomputes for sliders using the snapshotted commission/gst)? Recommendation: frontend computes locally for slider ticks; backend is called only on initial render and on accept. Confirm or override.

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_PRICE_CALCULATOR_ENABLED). Dev default: true. Staging default: false until the math passes the locked test fixture set (10 known-output Decimal cases from MVP_ARCH §3.4) AND the federated-remote loads in <500ms from the shell. When disabled, POST /api/v1/products/{id}/price-calc returns 404; the /catalogs/:id/pricing route shows "Pricing temporarily disabled" placeholder. Federation flag is separate from the feature flag — the federated remote may be enabled/disabled independently of the API endpoint.

Decision 3 — Priority ordering vs sibling features
  This feature touches:
    - Backend per-module code: app/modules/pricing/ (greenfield except for the latent services/pricing_engine.py PricingAlert import bug — resolved via delete-legacy + write-clean per §12 + memory turn 19)
    - Backend shared code: none (pricing owns its own domain.py + service.py + repository.py)
    - Frontend per-feature code: frontend/src/app/pages/pricing/ (greenfield) OR mfe-pricing remote if federation pilot proceeds in V1
  Confirm: price-calculator ships after catalog-form (ownership-gate dependency) AND smart-picker (commission_pct + HSN from categories). It can ship in parallel with live-preview AND image-precheck (no contention).

  Also confirm whether the federation pilot (mfe-pricing) ships as part of THIS feature's V1 dispatch OR is deferred. If deferred, the price-calculator components live in the shell at frontend/src/app/pages/pricing/ for V1 and migrate to mfe-pricing in a later sprint. Recommendation: ship the components in the shell for V1; do federation work as a separate planning session AFTER V1 to avoid coupling feature delivery to the federation pilot risk. The module_federation master plan explicitly says "Module Federation deferred to Phase 2" per CLAUDE.md Decision 12 — confirm this aligns with the planning intent.

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | api-routes-builder, services-builder, database-builder | api-routes-builder: POST /api/v1/products/{id}/price-calc route + PriceCalcRequest (mrp, target_seller_payout or target_margin_pct) + PriceCalcResponse Pydantic schemas with Decimal fields (use Pydantic v2 Decimal validator at 2 decimal places) in modules/pricing/schemas.py; services-builder: pricing.service.calculate(product_id, user_id, request) — calls catalog.service.assert_product_ownership + category.service.get_category_for_pricing (returns commission_pct + gst_pct + group_id for fallback) per §2.D matrix; deterministic math per MVP_ARCH §3.4; PricingAlert frozen dataclass in modules/pricing/domain.py for negative-margin warnings; writes snapshot row to pricing_calcs; database-builder: pricing_calcs table + Alembic migration + delete-legacy of services/pricing_engine.py + clean re-author to resolve §0.E latent PricingAlert import bug per memory turn 19 |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: PricingComponent (page) + PnlBreakdownComponent (6-row table with red-warning row when margin negative) + MarginSliderComponent (Angular Material slider with <100ms client-side recompute on tick), under frontend/src/app/pages/pricing/; reactive form for MRP + target_seller_payout; on slider tick: client recomputes locally using last-fetched commission + gst snapshot; on Accept: POST to backend to persist; angular-service-builder: PricingService.calculate(productId, request) wrapping HttpClient call; provides a local helper recomputeFromSnapshot(snapshot, newMrp) for the slider ticks (no API call per tick) |
| meesell-ai-coordinator | (no work) | Pricing is non-AI per §12. Confirm. |
| meesell-data-engineer | (only if HSN-to-GST mapping is missing) | xlsx-parser: ONLY if Decision 1 surfaces that categories.gst_pct is unpopulated for some categories — extend seed with HSN → gst_pct mapping. Default: no work — assume data track has provided HSN rates. Verify before planning. |
| meesell-infra-builder | (no work) | No new secrets, no new buckets, no manifest changes for V1 if federation is deferred. Confirm. |

Only include leads + specialists who actually have work. Omit empty rows.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/pricing/routes.py (NEW), app/modules/pricing/schemas.py (NEW), app/modules/pricing/service.py (NEW), app/modules/pricing/repository.py (NEW), app/modules/pricing/domain.py (NEW — PricingAlert frozen dataclass per §12 + memory turn 19), app/shared/models/pricing_calc.py (NEW — table model), app/alembic/versions/<rev>_pricing_calcs.py (NEW migration), backend/app/services/pricing_engine.py (DELETE — legacy file with broken PricingAlert import per §0.E and memory turn 19), backend/tests/test_pricing_unit.py (NEW — 10 locked Decimal test cases from MVP_ARCH §3.4), backend/tests/test_price_calculator_integration.py (NEW — end-to-end calc + persistence)
- Frontend: frontend/src/app/pages/pricing/pricing.component.ts (NEW), frontend/src/app/pages/pricing/pnl-breakdown.component.ts (NEW), frontend/src/app/pages/pricing/margin-slider.component.ts (NEW), frontend/src/app/services/pricing.service.ts (NEW), frontend/src/app/app.routes.ts (MODIFY — register /catalogs/:id/pricing route), frontend/src/app/pages/pricing/pricing.component.spec.ts (NEW — including slider recompute test against the 10 locked Decimal cases)
- AI: NONE
- Data: backend/app/data/categories.json or seed script (MODIFY only if HSN→gst_pct mapping missing — Decision 1 verification)
- Infra: NONE for V1 if federation is deferred per Decision 3
- Docs: docs/V1_FEATURE_SPEC.md §F7 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §12 sentinel flip (LOCKED-on-paper → LOCKED-on-disk via PR link; resolves the §0.E latent bug at the same time), docs/MVP_ARCHITECTURE.md §3.4 cross-link to pricing.service.calculate implementation

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entry for POST /api/v1/products/{id}/price-calc with PriceCalcRequest + PriceCalcResponse shapes; Decimal precision documented (2 places, no float); inline service-method docstring on calculate describing the snapshotting semantics (commission_pct + gst_pct frozen at calc time)
- Frontend: route entry comment in app.routes.ts; MarginSliderComponent docstring documenting the local-recompute contract (NO API call per tick); PnlBreakdownComponent docstring on the 6-row breakdown + negative-margin red warning
- AI: N/A
- Data: HSN-rate mapping documentation in seed file header (if Decision 1 verification requires data work)
- Infra: N/A
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F7 marked "implemented YYYY-MM-DD" with PR link; the §0.E latent pricing_engine.py PricingAlert bug resolution noted in BACKEND_ARCHITECTURE.md §12 LOCKED block

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-price-calculator-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., services-builder reads §12 + MVP_ARCH §3.4 math + the 10 locked Decimal test cases + memory turn 19 PricingAlert resolution path; database-builder reads the §0.E latent bug + memory turn 19 + the delete-legacy clean-rewrite plan)
- Acceptance criteria (specific to that specialist's slice — e.g., services-builder: all 10 locked Decimal test cases pass exactly to 2 decimal places, commission_pct + gst_pct snapshotted into pricing_calcs row, negative-margin returns PricingAlert in response; database-builder: pricing_calcs migration is reversible, services/pricing_engine.py is deleted (not refactored — clean rewrite per memory turn 19); api-routes-builder: 200ms P95 latency on the math endpoint, 400 on MRP < seller_payout)
- Hard constraints (e.g., NO float math on currency — Decimal only; NO API call per slider tick — frontend recomputes locally from snapshot; snapshot = freeze commission_pct + gst_pct at calc time, do NOT re-fetch on subsequent calls for the same pricing_calc id)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch
- Final report format (10 Decimal test pass receipts, P95 latency, slider recompute timing measurement)

Specialists to template:
- meesell-api-routes-builder (backend lead dispatches)
- meesell-services-builder (backend lead dispatches)
- meesell-database-builder (backend lead dispatches — migration + legacy delete)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)
- meesell-xlsx-parser (data lead dispatches IF HSN-rate gap surfaces — otherwise omit)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., backend lead checks: all 10 locked Decimal cases pass; pricing_calcs migration upgrade + downgrade clean; services/pricing_engine.py removed from repo; PricingAlert lives in modules/pricing/domain.py NOT app/schemas/pricing.py; frontend lead checks: slider recompute <100ms client-side measured via chrome devtools performance; no network call per slider tick verified in chrome DevTools network tab; OnPush change detection enforced)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/backend.md` (migration evidence — pricing_calcs migration reversible) + `.github/PULL_REQUEST_TEMPLATE/frontend.md` (visual evidence including slider responsiveness video)
- What triggers a re-dispatch (specific failure modes — Decimal math off by 0.01 → re-dispatch services-builder with "verify Decimal context precision = 28 and rounding = ROUND_HALF_EVEN per Python default; do not use float intermediates"; slider triggers network call per tick → re-dispatch frontend with "verify MarginSliderComponent subscribes to slider value changes and recomputes locally; PricingService.calculate is called only on Accept button click"; PricingAlert lives in wrong location → re-dispatch with "delete and re-author per memory turn 19 + §12 — domain.py per-module subtree, NOT app/schemas/")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/price-calculator/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1, including federation-pilot deferral and slider-locality)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., HSN-rate mapping gap surfacing late, Decimal precision regression on Pydantic schema serialization, MarginSliderComponent firing too many recomputes on mobile causing jank, federation pilot scope creep delaying V1 ship, V1.5 RTO/shipping addition forcing pricing_calcs schema migration)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/price-calculator/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/price-calculator.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/price-calculator/FEATURE_PLAN.md
git add docs/plans/features/_status/price-calculator.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock price-calculator feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-price-calculator-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/price-calculator/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/price-calculator/planning \
  --title "docs(plan): lock price-calculator feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update price-calculator status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md (including federation deferral + slider-locality + HSN verification)
- [ ] Agent lineup table fully filled out (backend 3 + frontend 2 + data 0-or-1 specialists named; AI / infra explicitly omitted)
- [ ] Code surfaces table covers every file the feature will create or modify (INCLUDING the services/pricing_engine.py delete)
- [ ] Documentation deliverables enumerated (OpenAPI with Decimal semantics, slider-locality docstring, V1_FEATURE_SPEC §F7 implemented stamp, §0.E latent bug resolution note in §12 LOCKED block)
- [ ] One dispatch template per specialist drafted (5-or-6 templates total depending on data)
- [ ] Review + iteration protocol defined (with Decimal-precision / slider-locality / PricingAlert-location failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/price-calculator/planning
- [ ] PR opened to develop using backend PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/pricing/, frontend/src/app/pages/pricing/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-price-calculator-{group}-session-{N}` per master plan §4
- Decimal-precision math is the contract — any dispatch template that allows float currency math must be rejected
- The federation pilot (mfe-pricing) is OUT OF SCOPE for V1 per CLAUDE.md Decision 12 unless Decision 3 explicitly overrides — flag federation work as a separate planning session if founder wants V1 federation pilot
- The §0.E latent services/pricing_engine.py PricingAlert import bug MUST be resolved via DELETE-LEGACY-and-CLEAN-REWRITE per memory turn 19 — any dispatch template that proposes editing the legacy file in place must be rejected
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend) has reviewed their section's dispatch templates
- [ ] PR open to develop using the backend PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- Decimal-precision math is non-negotiable

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
