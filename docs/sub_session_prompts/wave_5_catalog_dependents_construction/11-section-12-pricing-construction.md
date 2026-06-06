# Sub-Session Prompt: §12 Module `pricing`
# Wave 5 of 10 — CONSTRUCTION (parallel-safe with §11 image + §13 dashboard)
# Specialist agents: meesell-api-routes-builder + meesell-services-builder
# Renames session to: meesell-backend-construction-12-pricing-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §12 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-api-routes-builder + meesell-services-builder agents operating in a dedicated construction sub-session for MeeSell §12 (Module `pricing`).

§12 is the section that resolves the latent `services/pricing_engine.py` PricingAlert import bug per §0.E by DELETING the legacy file BEFORE constructing the new module.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §12 Module `pricing` — 1 endpoint POST /products/{id}/price-calc; deterministic P&L math, NO AI
- Specialist agents: meesell-api-routes-builder (router + schemas) + meesell-services-builder (service + repository + domain + exceptions + P&L math)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-12-pricing-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §12 — A through L (esp. §12.A latent bug resolution path: DELETE `backend/app/services/pricing_engine.py` FIRST; new `modules/pricing/service.py` is the replacement; §12.B 1 endpoint; §12.C service surface incl. `summary` OPTIONAL for dashboard; §12.D repository; `PricingAlert` frozen dataclass lives in `modules/pricing/domain.py` per §3.C; §12.G 5 exception classes incl. CommissionMissingError; §12.J 4 unit + 2 integration tests).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0.E (latent bug context), §4 (core/), §5 (shared/), §9 category (CONSTRUCTED Wave 3; consumes `get_commission`), §10 catalog (CONSTRUCTED Wave 4; consumes `assert_product_ownership`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §2.5 (pricing_calcs DDL), §3.4 (endpoints), Feature 7 P&L calculator.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md`.

5. `.claude/agents/meesell-api-routes-builder.md`, `meesell-services-builder.md`.

6. Memory files.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1-4 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline. CONFIRM `backend/app/services/pricing_engine.py` still exists as the broken-import legacy file (line 23: `from app.schemas.pricing import PricingAlert` — schemas.pricing was deleted in G3).

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

**STEP 0 — DELETE LEGACY FILE FIRST.** Before authoring anything else, run `rm backend/app/services/pricing_engine.py`. Verify `git status` shows the deletion + nothing else broke (no live importer hits it per §0.E — main.py does not register a pricing router today). Confirm boot smoke test still passes after deletion. This is the locked latent bug resolution path per §12.A.

Per §3.C:

```
backend/app/modules/pricing/
├── __init__.py
├── router.py            # FastAPI APIRouter; 1 endpoint
├── service.py           # service surface incl. `summary` OPTIONAL for dashboard
├── repository.py        # PRIVATE; scope_to_user; pricing_calcs INSERT/SELECT (append-only audit trail)
├── schemas.py           # Pydantic v2 request/response models incl. PriceCalcRequest, PriceCalcResponse
├── domain.py            # PricingAlert frozen dataclass (REPLACES the deleted schemas/pricing.py PricingAlert)
└── exceptions.py        # 5 exception classes per §12.G incl. CommissionMissingError, NegativeMarginError, etc.
```

NOTE: NO `tasks.py` (pricing is synchronous; no Celery jobs).

Plus: register `pricing_router` in `backend/app/main.py`.

Locked invariants:
- 1 endpoint: `POST /api/v1/products/{id}/price-calc`.
- Deterministic P&L math — NO AI per §6A workload set (workloads are exactly `{smart_picker, autofill, watermark}`).
- `PricingAlert` frozen dataclass with 3 alert codes per §12.J: `LOW_MARGIN`, `HIGH_MRP_MULTIPLIER`, `THIN_PROFIT`.
- Cross-module gates: `catalog.assert_product_ownership(product_id, user_id)` first; `category.get_commission(category_id) -> Decimal | None` second (None → 422 `pricing.commission_missing`).
- All money math uses `Decimal` with `ROUND_HALF_EVEN`; NO `float`; NO `==` on float comparisons.
- `pricing_calcs` is APPEND-ONLY audit trail — every calc is a new INSERT, NOT an UPDATE.
- `get_last_calc(product_id, user_id)` returns most recent row.
- plan_guard NOT participating in V1.

Construction protocol:

1. **Tests first** per §12.J (4 unit + 2 integration):

   **Unit** (`backend/tests/modules/pricing/`):
   - `test_ownership_gate` — POST `/products/{other_user_product}/price-calc` → 404 `catalog.product_not_found`.
   - `test_commission_missing` — `category.get_commission` returns None (mocked) → 422 `pricing.commission_missing`.
   - `test_pnl_formula_correctness` — golden fixtures: `input_cost=100`, `target_margin_pct=30`, `commission_pct=15` → expected `seller_price=130`, `mrp≈151.52`, `profit=30`, `profit_pct=30` (subject to ROUND_HALF_EVEN). Decimal exact match.
   - `test_alert_generation` — 3 sub-cases: low-margin → `LOW_MARGIN`; high-mrp-multiplier → `HIGH_MRP_MULTIPLIER`; thin-profit → both `THIN_PROFIT` and `LOW_MARGIN`.

   **Integration** (`backend/tests/integration/test_pricing_*.py`):
   - `test_full_create_product_to_price_calc` — create product → set category → price-calc; response `commission_pct` equals seeded category `commission_pct`. End-to-end §10 + §9 + §12 wiring.
   - `test_pricing_calcs_persistence_and_get_last_calc` — verify full `input_jsonb` and `output_jsonb` snapshots written for audit; `get_last_calc` returns most recent; subsequent calc INSERTs a new row (not UPDATE — append-only audit trail).

   Fixtures: real Postgres via dev tunnel; seeded `categories.commission_pct`; mocked `catalog.assert_product_ownership` for unit tests (real for integration).

2. **Implementation** per §12.B-§12.G with locked signatures. `PricingAlert` frozen dataclass in `domain.py` replaces the deleted `schemas/pricing.py` shape.

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT patch `services/pricing_engine.py` — DELETE it first (locked latent bug resolution).
- DO NOT use `float` for money math — `Decimal` with `ROUND_HALF_EVEN` only.
- DO NOT UPDATE `pricing_calcs` rows — every calc is a new INSERT (append-only audit trail).
- DO NOT skip `scope_to_user(user_id)` on repository methods.
- DO NOT import `category.repository` or `catalog.repository` — cross-module only via service.
- DO NOT call `ai_ops.client` — pricing has NO AI in V1; AI margin guidance is V1.5+.
- DO NOT call any adapter (`gemini`, `gcs`, `msg91`, `razorpay`, `langfuse`).
- DO NOT participate in plan_guard (V1 lock).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-api-routes-builder` — router + schemas.
- `meesell-services-builder` — service + repository + domain (PricingAlert) + exceptions + P&L math.

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §12)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

**Latent bug to resolve during this dispatch:** `backend/app/services/pricing_engine.py` — DELETE first per §12.A. The file is unimportable today but no live importer hits it (no pricing router in main.py). After deletion, the new `modules/pricing/service.py` IS the replacement. Verify boot smoke test still passes after `rm`.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. `backend/app/services/pricing_engine.py` DELETED (verified by `git status` + absence on disk).
2. 1 endpoint mounted per §12.B.
3. `PricingAlert` frozen dataclass in `modules/pricing/domain.py` with 3 alert codes (LOW_MARGIN, HIGH_MRP_MULTIPLIER, THIN_PROFIT).
4. All money math uses `Decimal` (grep-verifiable: no `float()` calls in pricing math).
5. `pricing_calcs` is append-only (grep-verifiable: no `UPDATE` on `pricing_calcs` in repository).
6. Cross-module gates: `assert_product_ownership` first, then `get_commission`; None commission → 422.
7. `scope_to_user(user_id)` on every repository method.
8. NO adapter imports.
9. NO `ai_ops.client` imports.
10. 4 unit + 2 integration tests PASS per §12.J.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update both specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §12 pricing CONSTRUCTED ===
   Files created: modules/pricing/{7 files}; main.py mount
   Files deleted: backend/app/services/pricing_engine.py (latent bug resolved per §0.E + §12.A)
   Tests added: 4 unit + 2 integration
   Decisions made: <list>
   Hand-offs: §13 dashboard MAY consume pricing.summary OPTIONAL (kept §2.D at 8 ✓ — dashboard does NOT opt in for V1 per founder ruling)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Boot smoke test FAILS after `rm services/pricing_engine.py` (escalate — a live importer was discovered).
- Decimal precision edge case (e.g. division-by-zero with margin_pct=100%).
- Founder ruling needed on a 4th alert code.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-12-pricing-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-4 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §12 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 5 of 10
- **Sequential dependency:** Wave 1-4 CONSTRUCTED (esp. §10 catalog for `assert_product_ownership` + §9 category for `get_commission`).
- **Parallel-safe?:** Yes — runs in parallel with §11 image + §13 dashboard.
- **Expected duration estimate:** ~6-8 hours.
- **Acceptance verification by master:** (1) `ls backend/app/services/pricing_engine.py` returns no such file; (2) `pytest backend/tests/test_app_boot_integration.py` PASS after deletion; (3) `grep -rn "float(" backend/app/modules/pricing/` returns nothing in math paths; (4) `grep -n "UPDATE.*pricing_calcs" backend/app/modules/pricing/repository.py` returns nothing (append-only); (5) STATUS_BACKEND.md UPDATE block present.
