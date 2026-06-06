# Sub-Session Prompt: §10 Module `catalog`
# Wave 4 of 10 — CONSTRUCTION
# Specialist agents: meesell-api-routes-builder + meesell-services-builder + meesell-prompt-engineer (AI track)
# Renames session to: meesell-backend-construction-10-catalog-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §10 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-api-routes-builder + meesell-services-builder + meesell-prompt-engineer (AI track) agents operating in a dedicated construction sub-session for MeeSell §10 (Module `catalog`).

§10 is the **central spine** — calls §8 customer + §9 category; called by §11 image + §12 pricing + §13 dashboard + §14 export. It is also the HARDEST V1.5 extraction target per §21.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §10 Module `catalog` — 6 endpoints + autofill orchestration + autosave (most-called module per §2.4)
- Specialist agents: meesell-api-routes-builder (router + schemas) + meesell-services-builder (service + repository + domain + exceptions + autosave coalescing) + meesell-prompt-engineer (AI track; owns `autofill.v1` prompt content per §6A.G)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-10-catalog-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §10 — A through L (esp. §10.B 6 endpoints: POST create + PATCH autosave + POST autofill + GET preview + DELETE soft-delete + GET draft-recover; §10.C 10-method service surface incl. 4 cross-module surfaces (`assert_product_ownership` for image/pricing/dashboard/export; `list_products` for dashboard; `get_product_for_export` for export; `get_validation_summary` for dashboard); §10.D repository; §10.G exceptions; §10.J 5 unit + 3 integration tests).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §4 (core/), §5 (shared/), §5A (i18n/), §6A (ai_ops/client.call_gemini "autofill" workload), §8 customer (CONSTRUCTED Wave 3; consumes `assert_eligible_for_super_id`), §9 category (CONSTRUCTED Wave 3; consumes `fetch_schema`, `get_field_enum`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §2.4 (DDL catalogs/products/product_drafts), §3.4 (endpoints), §5.2 (Autofill), §11.4 (autosave coalescing — per-IP-only with 5-min audit), §11.6 (draft recovery contract), §12.4 (is_advanced gates group_id).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md`.

5. `.claude/agents/meesell-api-routes-builder.md`, `meesell-services-builder.md`, `meesell-prompt-engineer.md`.

6. Memory files for all 3 specialists.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1 + Wave 2 + Wave 3 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.C:

```
backend/app/modules/catalog/
├── __init__.py
├── router.py            # FastAPI APIRouter; 6 endpoint signatures
├── service.py           # 10-method service surface (6 endpoint-mirror + 4 cross-module)
├── repository.py        # PRIVATE repository; scope_to_user(user_id) on every method
├── schemas.py           # Pydantic v2 request/response models
├── domain.py            # AutofillResponse, ExportSnapshot, ProductValidationSummary value objects
└── exceptions.py        # exceptions per §10.G (ProductNotFoundError, ValidationFailedError, ProfileIncompleteForCategoryError, DraftNotFoundError, PlanLimitExceededError)
```

NOTE: V1 catalog DOES NOT have `tasks.py` per §3.C lock (Auto-fill runs sync from FastAPI in V1; if §6A later moves it async, `catalog/tasks.py` is added then).

Plus: register `catalog_router` in `backend/app/main.py`.

Locked invariants:
- 6 endpoints: `POST /api/v1/products`, `PATCH /api/v1/products/{id}` (autosave via `X-Autosave: true` header), `POST /api/v1/products/{id}/autofill`, `GET /api/v1/products/{id}/preview`, `DELETE /api/v1/products/{id}`, `GET /api/v1/products/{id}/draft`.
- AI Auto-fill via `ai_ops.client.call_gemini(ctx, "autofill", ...)` with §6A.F graceful fallback returning 200 + `fallback_offered=true` (NOT 503).
- Autosave: PATCH per-IP-only with 5-min audit coalescing per `MVP_ARCH §11.4`.
- Cross-module ownership-assertion seam (`assert_product_ownership(product_id, user_id)`) consumed by image/pricing/dashboard/export per philosophy M6.
- create_product step 3 chains: `category.assert_category_exists → customer.assert_eligible_for_super_id → repository.insert` (any one fails → 422 fail-fast).
- plan_guard: `create_product` raises `PlanLimitExceededError` (402) when active products ≥ 100 (Free tier).
- Draft recovery: `GET /products/{id}/draft` returns 200 with last autosave snapshot OR 204 if no draft. `product_drafts.(user_id, product_id) UNIQUE` per `MVP_ARCH §2.4`.
- Schema-driven validation per §5A.B/C/D: `patch_product` calls `category.fetch_schema(category_id)` then validates `fields_jsonb` against the schema envelope.

Construction protocol:

1. **Tests first** per §10.J (5 unit + 3 integration):

   **Unit** (`backend/tests/modules/catalog/test_service_unit.py`):
   - `TestOwnershipEnforcement` — `assert_product_ownership` raises `ProductNotFoundError` for: (a) non-existent product, (b) product owned by another user, (c) soft-deleted product (`deleted_at IS NOT NULL`). 3 test methods.
   - `TestSchemaDrivenValidation` — `patch_product` raises `ValidationFailedError` with correct `validation_message_id` for: (a) unknown canonical_name (`validation.fields.unknown_key`), (b) text overflow (`validation.{canonical}.too_long`), (c) static-enum miss (`validation.{canonical}.invalid_enum_value`), (d) category-enum miss, (e) multi-violation surfaces first as `validation_message_id` + rest in `details`. 5 test methods.
   - `TestAutofillGracefulFallback` — `autofill_product` returns `AutofillResponse(suggestions={}, applied={}, fallback_offered=True)` with HTTP 200 (NOT 503) when `ai_ops.client.call_gemini` raises `BudgetExceededError`. 1 test method.
   - `TestAutosaveDraftUpsert` — `patch_product` with `is_autosave=True` writes through to `product_drafts` via `upsert_draft`; `is_autosave=False` does NOT touch `product_drafts`; second autosave on same product increments `autosave_count` and replaces `fields`. 3 test methods.
   - `TestPlanGuardEnforcement` — `create_product` raises `PlanLimitExceededError` (402) when `repository.count_active_products` returns 100; rate-limit decorator firing mocked separately. 1 test method.

   **Integration** (`backend/tests/modules/catalog/test_integration.py`):
   - `TestFullProductLifecycle` — End-to-end: create → autofill → PATCH autosave → PATCH manual save with status=ready → preview. Stub `ai_ops.client.call_gemini` returns deterministic suggestions.
   - `TestDraftRecoveryAfterSimulatedClose` — Create → autosave 3 times via 3 PATCHes with `X-Autosave: true` → `GET /products/{id}/draft` → verify `autosave_count=3`, `fields` matches latest snapshot, `last_updated >= third PATCH`. Then WITHOUT autosaving → 204.
   - `TestCrossModuleOwnershipAssertion` — Simulates image module's call into `catalog.service.assert_product_ownership`; verifies raises `ProductNotFoundError` for user A's product when called with user B's `user_id`. Structural M6 enforcement.

   Fixtures: logged-in user with completed seller profile + Beauty super_id eligibility; stub `ai_ops.client.call_gemini` returning deterministic high-confidence suggestions for Auto-fill happy path; standard `category_with_schema` fixture (Beauty / Eye-Serum canonical compliance-shape test).

2. **Implementation** per §10.B-§10.G with locked signatures. Prompt-engineer authors `autofill.v1` content in `ai_ops/prompts/autofill_v1.py` (already storage-structured in Wave 1 §6A).

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT create `catalog/tasks.py` — V1 Auto-fill runs sync (§3.C lock).
- DO NOT skip `scope_to_user(user_id)` on any repository method.
- DO NOT import `category.repository`, `customer.repository`, `image.repository`, `pricing.repository` — cross-module only via service.
- DO NOT import `adapters.gemini` — only `ai_ops.client.call_gemini` (§3.G + §16.E Contract 2).
- DO NOT return 503 on `BudgetExceededError` from autofill — return 200 + `fallback_offered=True`.
- DO NOT do schema-driven validation inline in `router.py` — validation belongs in `service.py` (using schema from `category.fetch_schema`).
- DO NOT skip the create_product 3-step chain (category exists → customer eligible → insert).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-api-routes-builder` — router + schemas.
- `meesell-services-builder` — service + repository + domain + exceptions + autosave coalescing.
- `meesell-prompt-engineer` (AI track) — `autofill.v1` prompt content in `ai_ops/prompts/autofill_v1.py`.

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §10)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve. (The `services/pricing_engine.py` PricingAlert import bug is §12's problem per §0.E — explicitly NOT catalog's problem.)

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 6 endpoints mounted per §10.B.
2. NO `catalog/tasks.py` file (V1 lock).
3. `scope_to_user(user_id)` on every repository method.
4. NO `from app.adapters.gemini` in any `modules/catalog/` file.
5. AutofillGracefulFallback test PASS — `BudgetExceededError` → 200 with `fallback_offered=True`.
6. Autosave writes through to `product_drafts` table via `upsert_draft`; coalescing per `MVP_ARCH §11.4` (5-min audit window).
7. Draft recovery returns 200 with snapshot OR 204 if no draft.
8. `assert_product_ownership` correctly enforces 3 ProductNotFound cases (not exists, other user's, soft-deleted).
9. `create_product` chain: category exists → customer eligible → insert.
10. 5 unit + 3 integration tests PASS per §10.J.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update all 3 specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §10 catalog CONSTRUCTED ===
   Files created: modules/catalog/{7 files}; main.py mount; ai_ops/prompts/autofill_v1.py finalized
   Tests added: 5 unit + 3 integration
   Decisions made: <list>
   Hand-offs: §11 image (consumes assert_product_ownership), §12 pricing (consumes assert_product_ownership), §13 dashboard (consumes list_products + get_validation_summary), §14 export (consumes get_product_for_export)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Schema envelope mismatch between §5A.B and `category.fetch_schema` actual return.
- Autosave coalescing 5-min window vs FE-D5 refresh window collision (escalate — separate keyspaces but verify).
- Prompt-engineer escalates on autofill.v1 invalid-enum frequency exceeding §6A.E Layer 2 retry budget.
- Plan limit (100 active products) needs founder ratification.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-10-catalog-1`
2. Read REQUIRED READING.
3. Confirm Wave 1 + Wave 2 + Wave 3 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §10 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 4 of 10
- **Sequential dependency:** Wave 1 + Wave 2 + Wave 3 complete (§8 customer + §9 category both CONSTRUCTED).
- **Parallel-safe?:** No — Wave 4 is single-section. §10 is the central spine; Waves 5 + 6 + 7 depend on it.
- **Expected duration estimate:** ~14-18 hours (highest-complexity module).
- **Acceptance verification by master:** (1) absence of `backend/app/modules/catalog/tasks.py`; (2) `grep -c "scope_to_user" backend/app/modules/catalog/repository.py` matches method count; (3) `grep -r "from app.adapters.gemini" backend/app/modules/catalog/` returns nothing; (4) 5 unit + 3 integration tests PASS; (5) STATUS_BACKEND.md UPDATE block present.
