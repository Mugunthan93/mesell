# Sub-Session Prompt: §9 Module `category`
# Wave 3 of 10 — CONSTRUCTION (parallel-safe with §8 customer)
# Specialist agents: meesell-api-routes-builder + meesell-services-builder + meesell-category-picker-builder (AI track)
# Renames session to: meesell-backend-construction-9-category-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §9 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-api-routes-builder + meesell-services-builder + meesell-category-picker-builder (AI track) agents operating in a dedicated construction sub-session for MeeSell §9 (Module `category`).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §9 Module `category` — 5 endpoints (Smart Picker + browse + categories tree + schema + field-enum) + AI seam via §6A
- Specialist agents: meesell-api-routes-builder (router + schemas) + meesell-services-builder (service + repository + cache layer + browse search) + meesell-category-picker-builder (AI track; owns compressed-tree heuristics + confidence calibration)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-9-category-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §9 — A through L (esp. §9.B 5 endpoints: `/suggest` Smart Picker w/ §6A AI seam + plan_guard `smart_picker_hourly=100/h`, `/browse` pg_trgm fallback, `/categories` full tree GLOBAL cache + ETag + pre-warm, `/{id}/schema` envelope per §5A.B + ETag + top-100 pre-warm, `/{id}/field-enum/{name}` w/ MANDATORY single-flight for 291 Brand-pattern enums; §9.C 8-method service surface incl. 3 cross-module surfaces; §9.D 7-method repository MODULE-PRIVATE per §16 + NO scope_to_user anywhere — globals; §9.G 4 CategoryError; §9.J 5 unit + 3 integration tests).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0.G §12.3 (Smart Picker), §0.G §12.4 (is_advanced), §4 (core/cache.py + plan_guard.py), §5 (shared/), §6A (ai_ops/client.py; NEVER adapters/gemini.py directly per §3.G boundary).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §5.1 (Smart Picker), §6 (caching), §6.7 (single-flight), §6.8 (Brand-pattern enums), §7 (search), §7.5 (browse P95 ≤ 200 ms).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md`.

5. `.claude/agents/meesell-api-routes-builder.md`, `meesell-services-builder.md`, `meesell-category-picker-builder.md`.

6. Memory files for all 3 specialists.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1 + Wave 2 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline. NOTE: pg_trgm extension + 3 GIN indexes already shipped session 2 G4 via Alembic `a1b2c3d4e5f6_pg_trgm_and_category_gin.py` — consume, don't recreate.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.C:

```
backend/app/modules/category/
├── __init__.py
├── router.py            # FastAPI APIRouter; 5 endpoint signatures
├── service.py           # 8-method service surface (5 endpoint-mirror + 3 cross-module for pricing/customer/catalog)
├── repository.py        # 7-method PRIVATE repository; NO scope_to_user (categories/templates/field_enum_values/field_aliases are GLOBAL per `MVP_ARCH §10.2` + §4.C; §19 linter exception documented at §16.F.2)
├── schemas.py           # Pydantic v2 request/response models incl. SuggestRequest, BrowseRequest, CategoryTree, CategorySchema, FieldEnumPayload
├── domain.py            # EnumEntry value object {canonical, meesho, labels:{en:...}} per `MVP_ARCH §5.6.4`
└── exceptions.py        # 4 CategoryError subclasses per §9.G
```

Plus: register `category_router` in `backend/app/main.py`.

Locked invariants:
- 5 endpoints: `POST /api/v1/category/suggest` (Smart Picker), `GET /api/v1/category/browse` (pg_trgm), `GET /api/v1/categories` (full tree, GLOBAL cache + ETag), `GET /api/v1/categories/{id}/schema` (envelope per §5A.B + ETag), `GET /api/v1/categories/{id}/field-enum/{name}` (single-flight).
- AI seam: `ai_ops.client.call_gemini(ctx, "smart_picker", ...)` — NEVER `adapters.gemini` directly (§3.G + §19 import-linter Contract 2).
- plan_guard: `smart_picker_hourly=100/h` on `/suggest` only.
- Cache: `/categories` full tree GLOBAL + pre-warm; `/{id}/schema` top-100 pre-warm; `/{id}/field-enum/{name}` MANDATORY single-flight per §6.7 + §6.8 for the 291 Brand-pattern enums.
- NO `scope_to_user` anywhere — categories/templates/field_enum_values/field_aliases are GLOBAL (§19 linter exception 2).
- `/suggest` graceful fallback: `BudgetExceededError` → 200 with empty suggestions + `fallback_offered=True` (NOT 503).
- `/suggest` Layer 2 invalid-category-id retry: §6A retries with stricter prompt; after 2 retries → 200 with empty suggestions + `fallback_offered=true`.
- `meesho` value in `/field-enum` response is M10-compliant (backend-internal canonicalisation lookup for catalog/export; frontend reads `canonical` + `labels.en` only).
- Browse P95 ≤ 200 ms target per `MVP_ARCH §7.5`; uses Bitmap Index Scan on `idx_categories_path_trgm`.
- Heaviest cache consumer in codebase — all 5 endpoints cache-eligible.

Construction protocol:

1. **Tests first** per §9.J (5 unit + 3 integration):

   **Unit** (`backend/tests/modules/category/`):
   - `test_trigram_search_uses_gin_index` — `search_via_trigram("kurti", ...)` triggers Bitmap Index Scan on `idx_categories_path_trgm` per EXPLAIN ANALYZE; P95 < 200ms over 100 iterations.
   - `test_schema_fetch_envelope_conformance` — 6 top-level keys per §5A.B; every `fields[]` entry has 9 keys per §5A.C; count invariants hold; `compliance_shape ∈ {"standard", "collapsed"}`.
   - `test_field_enum_returns_labelled_payload` — every `EnumEntry` carries `{canonical, meesho, labels: {en: ...}}`; single_flight=True enforced (2 concurrent cache-miss → 1 repo query).
   - `test_suggest_graceful_fallback_on_budget` — mocked `ai_ops.client.call_gemini` raises `BudgetExceededError` → response is 200 with `SuggestResponse(suggestions=[], fallback_offered=True)` NOT 503.
   - `test_suggest_layer2_invalid_id_retry` — mocked AI returns invalid `category_id` → §6A retries; after 2 retries → 200 + empty suggestions + `fallback_offered=true`.

   **Integration** (`backend/tests/integration/test_category_*.py`):
   - `test_smart_picker_to_schema_to_catalog_wizard_flow` — `/suggest?q=...` returns top-5 → seller picks suggestion[0] → `/{id}/schema` → catalog wizard PATCH → validation succeeds.
   - `test_browse_to_schema_to_catalog_wizard_flow` — `/browse?q=kurti` ranked → seller picks leaf → `/{id}/schema` → wizard renders per §5A.B.
   - `test_etag_round_trip` — GET `/categories` returns ETag X; second GET with `If-None-Match: X` → 304 Not Modified per §4.D.

   Fixtures: real Postgres + Valkey via dev tunnel; mocked `ai_ops.client.call_gemini` (deterministic fixture responses for Smart Picker tests).

2. **Implementation** per §9.B-§9.G with locked signatures. AI track's `meesell-category-picker-builder` owns the compressed-tree compression, confidence calibration, top-K selection algorithm INSIDE the prompt context handed to `ai_ops.client.call_gemini`. The backend invocation shape is `call_gemini(ctx, "smart_picker", query=..., compressed_tree=...)`.

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT add `scope_to_user` to category repository methods — globals.
- DO NOT import `adapters.gemini` — only `ai_ops.client.call_gemini` (§3.G + §16.E Contract 2).
- DO NOT call `category.repository` from any other module — service.py is the public surface.
- DO NOT INSERT/UPDATE/DELETE on `categories`, `templates`, `field_enum_values`, `field_aliases` at runtime — seed-time tables owned by DATABASE track.
- DO NOT return 503 on `BudgetExceededError` — return 200 + `fallback_offered=True`.
- DO NOT expose `meesho` value to frontend in the `/field-enum` response body (frontend MUST read `canonical` + `labels.en` only; `meesho` is backend-internal canonicalisation per M10).
- DO NOT skip single-flight on `/field-enum` (mandatory per §6.8).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-api-routes-builder` — router + schemas.
- `meesell-services-builder` — service + repository + cache layer + browse search + domain + exceptions.
- `meesell-category-picker-builder` (AI track) — compressed-tree heuristics + confidence calibration + top-K selection inside the prompt context.

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §9)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 5 endpoints mounted per §9.B.
2. NO `scope_to_user` in `modules/category/repository.py` (grep-verifiable).
3. NO `from app.adapters.gemini` in any `modules/category/` file (grep-verifiable).
4. `/suggest` returns 200 + `fallback_offered=True` on `BudgetExceededError` (test-verifiable).
5. `/field-enum` enforces single-flight via Valkey SETNX (test-verifiable: 2 concurrent → 1 repo call).
6. `/categories` and `/{id}/schema` cache hits use ETag (304 round-trip test-verifiable).
7. Browse P95 ≤ 200 ms verified.
8. 4 CategoryError exceptions per §9.G with `validation_message_id` from §5A.
9. 5 unit + 3 integration tests PASS per §9.J.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update all 3 specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §9 category CONSTRUCTED ===
   Files created: modules/category/{7 files}; main.py mount
   Tests added: 5 unit + 3 integration
   Decisions made: <list>
   Hand-offs: §10 catalog (consumes fetch_schema, get_field_enum, assert_category_exists), §12 pricing (consumes get_commission), §14 export (consumes fetch_schema + fetch_xlsx_aliases), §8 customer (consumes super_id distinct set)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- pg_trgm extension missing (escalate — should already be in §5 baseline).
- AI prompt content blocked on prompt-engineer.
- Schema envelope shape mismatch between §5A.B and category's `fetch_schema` return type.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-9-category-1`
2. Read REQUIRED READING.
3. Confirm Wave 1 + Wave 2 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §9 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 3 of 10
- **Sequential dependency:** Wave 1 + Wave 2 complete.
- **Parallel-safe?:** Yes — runs in parallel with §8 customer (07-section-8-customer-construction.md). Both are leaf modules with no cross-module dependency between them.
- **Expected duration estimate:** ~10-14 hours (heaviest cache consumer + AI track coordination).
- **Acceptance verification by master:** (1) `grep -r "scope_to_user" backend/app/modules/category/repository.py` returns nothing; (2) `grep -r "from app.adapters.gemini" backend/app/modules/category/` returns nothing; (3) ETag round-trip integration test PASS; (4) single-flight behavior on `/field-enum` PASS; (5) STATUS_BACKEND.md UPDATE block present.
