# MeeSell — Smart Category Picker (V1 Feature 2) — FEATURE PLAN

**Status:** DRAFT 2026-06-10 — awaiting founder review on PR `feature/smart-picker/planning` → `develop`.
**Feature slug:** `smart-picker`
**V1 spec section:** `docs/V1_FEATURE_SPEC.md §F2` (Feature 2: Smart Category Picker)
**Backend arch section:** `docs/BACKEND_ARCHITECTURE.md §6A` (AI Operations Layer) + `§9` (category module)
**Frontend arch section:** `docs/FRONTEND_ARCHITECTURE.md §4` (Layer 4 — Features → `features/smart-picker/`)
**Repo management:** `docs/plans/repo_management/MASTER_PLAN.md` (APPROVED 2026-06-10)
**Author of this plan:** Master session (Director) — initiated by founder dispatch `mesell-smart-picker-planning-session-1`
**Planning branch:** `feature/smart-picker/planning` (off `develop`)
**Planning PR template:** `.github/PULL_REQUEST_TEMPLATE/ai.md` (AI is the most-involved track — eval gating is the primary acceptance signal)

---

> **Any lead or specialist working on the `smart-picker` feature MUST read this document at session start, in addition to the lead-spec / specialist-spec Mandatory First Action checklist.** This rule is per Governance Decision G4 (locked 2026-06-10). The FEATURE_PLAN supersedes any conflicting interpretation of the dispatch prompt; if the FEATURE_PLAN and a lead spec disagree, the FEATURE_PLAN wins for THIS feature only — escalate the conflict to the founder for permanent reconciliation.

---

## Decisions

All eight decisions were locked by the founder in session `mesell-smart-picker-planning-session-1` (2026-06-10). Verbatim record below.

### Governance decisions (G1–G4)

**G1 — Lead + specialist lineup: locked as "Full lineup per dispatch prompt".**

- Backend lead dispatches three specialists: `meesell-api-routes-builder`, `meesell-services-builder`, `meesell-database-builder`.
- Frontend lead dispatches two specialists: `meesell-angular-component-builder`, `meesell-angular-service-builder`.
- AI lead dispatches two specialists: `meesell-prompt-engineer`, `meesell-category-picker-builder`.
- Data lead dispatches `meesell-scraper-maintainer` **only if** the staleness check fails (default: no dispatch).
- `meesell-angular-ui-styler` is NOT in the lineup; the Smart Picker page composes existing `mee-*` primitives + Layer 1 design tokens — no styling primitives are added.

Total specialists in scope: **7 mandatory + 1 conditional = 8 max**.

**G2 — Branch creation strategy: locked as "Planning now, group branches lazy".**

- `feature/smart-picker/planning` is created NOW (this session) off `develop` for this planning PR.
- `feature/smart-picker` (integration branch) is created LAZILY, off `develop`, by the first lead-on-deck for execution AFTER the planning PR merges to develop.
- `feature/smart-picker/{backend,frontend,ai,data}` group branches are created LAZILY, off `feature/smart-picker`, by each group's lead WHEN their lead dispatches their first specialist on this feature.
- Per Master Plan §1.4: branches are short-lived (hours to days, not weeks); rebase, don't merge, on integration pulls.

**G3 — Memory + feature_board discipline: locked as "4-part convention".**

1. **Per-feature memory filename convention.** Every agent who touches this feature writes/appends to a file named `feature_smart_picker_<slice>.md` inside their `.claude/agent-memory/meesell-<role>/` directory. `<slice>` describes the agent's contribution (e.g., `feature_smart_picker_prompt_v1_iteration.md`, `feature_smart_picker_service_suggest_wiring.md`, `feature_smart_picker_component_three_cards.md`).
2. **MEMORY.md index section.** Every agent's `MEMORY.md` gets a `## Per-feature memory` section that groups all `feature_*.md` files BY feature slug. Lookup pattern: "find all my notes on smart-picker" = scan the `smart-picker` subsection.
3. **`feature_board` PENDING rows added NOW.** Each of the four leads (backend, frontend, AI, data) adds a `PENDING` row for `smart-picker` to their `docs/status/feature_board_<domain>.md` during the planning-PR-merge step (see §10 Acceptance gate). Notes column points at this document.
4. **Dispatch template MEMORY DISCIPLINE block.** Every specialist dispatch template (see §6 Dispatch templates) includes an explicit `MEMORY DISCIPLINE` block — read at session start, write at session close. No exceptions.

**G4 — FEATURE_PLAN.md is a mandatory read for active features.**

If the `smart-picker` feature appears in a lead's `feature_board` Active features table, OR a lead is about to dispatch a specialist on this feature, OR a specialist is being dispatched on this feature, THEN this `FEATURE_PLAN.md` is a mandatory read at session start. The rule is per-feature (lives inside this document) and does NOT amend any LOCKED section of a lead spec. The rule applies to specialists too. The lead's dispatch template MUST explicitly cite this document path: `docs/plans/features/smart-picker/FEATURE_PLAN.md`.

### Scope decisions (D1–D4)

**D1 — Scope confirmation: locked as "Arch-aligned".**

- Backend `/suggest` returns up to **top-5** category suggestions per `BACKEND_ARCHITECTURE.md §9.E SuggestResponse.suggestions = Field(max_length=5)`.
- Frontend renders **top-3 cards** in the primary view per V1 spec §F2 (the seller does not see ranks 4 + 5 by default — they remain in the response payload for V1.5 expansion).
- On `BudgetExceededError` from `ai_ops.client.call_gemini` per `§6A.F` → response is **HTTP 200** with `SuggestResponse(suggestions=[], fallback_offered=True)` per `§9.B.1` flow step 3. The frontend recognises `fallback_offered=true` and surfaces a CTA button that routes the seller to the Manual Browse page (`/categories/browse`, served by `§9.B.2` `GET /api/v1/categories/browse` over the pg_trgm GIN indexes). NO ILIKE fallback inside `/suggest` — the architecture explicitly contracts an empty-suggestions response plus the flag.
- Per-card display: `path` + `commission_pct` + `reasons` (short human-readable rationale strings from the AI track ranking per `§9.E CategorySuggestion.reasons: list[str]`). `sample_attributes` are NOT inline in the `/suggest` payload — they are fetched on category selection via `GET /api/v1/categories/{id}/schema` per `§9.B.4` (this matches the existing `catalog` module's wizard flow).
- Cost ceiling per call: **≤ ₹0.05** average per `MVP_ARCH §8.2` + `§6A.D` rate constants. Hard daily cap: ₹500 per `§6A.F`.
- Language: **English-only V1**. Hindi/Tamil/Tamizh input passes through to Gemini as-is with no enforcement; multilingual handling deferred to V1.5.
- Golden set target: **top-5 recall ≥ 80%** on the 50-description hand-labeled fixture at `backend/tests/eval/smart_picker/fixtures.json` per `§6A.H`.

**D2 — Feature flag posture: locked as "Standard".**

- Flag name: **`FEATURE_SMART_PICKER_ENABLED`** (env var on FastAPI app per Master Plan §3.2 backend rule).
- Dev default: `true`.
- Staging default: `false` until a 24-hour staging soak demonstrates BOTH (a) top-5 recall ≥ 80% on the golden set AND (b) per-call cost averages ≤ ₹0.05.
- When disabled, `GET /api/v1/categories/suggest` returns **HTTP 404** per Master Plan §3.2.
- Staging promotion from `false → true` is a **manual founder action** after soak verification. No auto-promote on metric crossing.
- The flag is **removed** when the feature ships to `main`. Carrying it past one release is a debt item per Master Plan §3.2.

**D3 — Priority ordering vs sibling AI features: locked as "Smart Picker first".**

- `smart-picker` is the first AI workload to merge to `develop`.
- `ai-autofill` and `image-precheck` planning may advance in parallel, but their `feature/{name}` → `develop` merges rebase onto Smart Picker's `ai_ops` integration tip.
- Rationale: `backend/app/ai_ops/` is shared infrastructure for all three AI features. Smart Picker's scaffold already exists (`§6A` client/cost_tracker/guardrail/budget_cap/prompt_registry/eval; `§9` category module; `ai_ops/prompts/smart_picker_v1.py`; `tests/eval/smart_picker/fixtures.json`). Shipping it FIRST validates the ai_ops contract end-to-end (cost tracking, 3-layer guardrail, graceful fallback, golden-set CI gate) so the auto-fill and watermark builds can iterate against a proven seam rather than an untested one.

**D4 — Frontend folder naming: locked as "Smart-picker (rename)".**

- The existing scaffold at `frontend/src/app/features/catalog-new/` is renamed to `frontend/src/app/features/smart-picker/` to match `FRONTEND_ARCHITECTURE.md §4` line 418 (LOCKED 2026-06-05).
- Route URL `/catalogs/new` stays — the folder name reflects the feature, not the URL segment.
- The rename happens as the FIRST commit on the `feature/smart-picker/frontend` group branch. `meesell-angular-component-builder` owns the rename PR + the component build; the rename is a `git mv` operation preserving file history.
- All existing files inside `catalog-new/` (`catalog-new.component.ts`, `services/`, `smart-picker.model.ts`, `catalog-new.component.spec.ts`) are renamed accordingly: `smart-picker.component.ts`, `services/`, `smart-picker.model.ts`, `smart-picker.component.spec.ts`. Class names update (`CatalogNewComponent → SmartPickerComponent`).

---

## Agent lineup

Reflecting Decision G1.

| Lead | Group branch | Specialists dispatched | What each specialist codes | Conditional? |
|---|---|---|---|---|
| `meesell-backend-coordinator` | `feature/smart-picker/backend` | `meesell-api-routes-builder` | Verifies `GET /api/v1/categories/suggest` route in `backend/app/modules/category/router.py` against `§9.B.1`. Verifies Pydantic schemas in `backend/app/modules/category/schemas.py` against `§9.E` (`SuggestQuery`, `SuggestResponse`, `CategorySuggestion`). Adds the `FEATURE_SMART_PICKER_ENABLED` flag guard returning 404 when disabled per D2. Adds route-level integration smoke test asserting the 404 behaviour. Confirms OpenAPI emits for the route with full request/response schema. | No |
| | | `meesell-services-builder` | Verifies `category.service.suggest_categories(user_id, q)` against `§9.B.1` flow steps 1–6: SuggestQuery validation → `plan_guard.enforce_plan_limit("smart_picker_hourly", 100/h)` → `core/cache.get_or_set(key="smart_picker:{sha256(q)}:v{cache_version}", ttl=900)` → on cache miss `ai_ops.client.call_gemini(ctx, "smart_picker.v1", {description, compressed_tree})` → Layer 2 validation via `repository.assert_category_exists_uncached` → on `BudgetExceededError` return `SuggestResponse(suggestions=[], fallback_offered=True)` per D1 → enrich each surviving suggestion with `super_id/super_name/path/leaf_name` from the in-process category tree. Authors `backend/tests/integration/test_smart_picker_integration.py` covering: graceful-fallback shape, Layer 2 retry exhaustion path, cache hit shape, and the `/browse` round-trip from a populated `fallback_offered=true` response. Confirms i18n message ids `validation.suggest_q.too_short_or_long` + `category.not_found` are present in `backend/app/i18n/messages_en.py`. | No |
| | | `meesell-database-builder` | Verifies the existing `categories` table state at `head` Alembic revision matches `§9.D` repository signatures: `search_via_trigram` hits `Bitmap Index Scan on idx_categories_path_trgm` per EXPLAIN ANALYZE; `assert_category_exists_uncached` returns a fast existence boolean; pg_trgm GIN indexes (idx_categories_path_trgm, idx_categories_leaf_name_trgm, idx_categories_super_name_trgm) exist and are non-empty. Authors a 100-iteration P95 < 200 ms benchmark fixture for `search_via_trigram("kurti", ...)` proving the index is hit under realistic load. NO new tables. NO new migration. If any `§9.D` method is missing or wrong-shaped, escalates to backend lead before patching the repository file. | No |
| `meesell-frontend-coordinator` | `feature/smart-picker/frontend` | `meesell-angular-component-builder` | FIRST commit: `git mv frontend/src/app/features/catalog-new/ frontend/src/app/features/smart-picker/` per D4 + rename class names (`CatalogNewComponent` → `SmartPickerComponent`). THEN: builds `SmartPickerComponent` (page) — reactive form with `description` field (10 ≤ len ≤ 500 chars), 400 ms debounce on form-change, signal-backed loading state, signal-backed suggestion list (length 0..5; render top 3), `fallback_offered` flag handling. Builds `CategoryCardComponent` (presentational) — accepts a `CategorySuggestion` input, renders `path` + `commission_pct%` badge + `reasons[]` as a short bullet list. Uses `mee-textarea`, `mee-card`, `mee-button`, `mee-badge`, `mee-skeleton` from `@mee/ui`. When `fallback_offered=true` AND `suggestions.length === 0`: renders an empty-state card with CTA button "Browse all categories" routing to `/categories/browse`. When `fallback_offered=true` AND `suggestions.length > 0`: renders the suggestions normally and adds a secondary "Browse if none match" link below the cards. Per-card "Use this category" CTA → calls `CategoryService.selectCategory(category_id)` which routes to `/catalogs/:id/edit` (existing flow). | No |
| | | `meesell-angular-service-builder` | Builds `CategoryService.suggest(description: string): Observable<SuggestResponse>` at `frontend/src/app/features/smart-picker/services/category.service.ts` — `HttpClient.get<SuggestResponse>('/api/v1/categories/suggest', { params: { q: description } })`. Threads through the global JWT interceptor automatically (no per-request auth). Error handling: 401 → AuthService logout flow; 402 → toast "Daily AI quota exceeded — try again later or browse manually" + emit empty `SuggestResponse(fallback_offered=true)` so the component renders the fallback UI; 400 → toast the i18n message id back to the user; 503 → toast generic AI-unavailable + fallback shape. Builds `CategoryService.browseRedirect(): void` calling `Router.navigate(['/categories/browse'])` so the component delegates the routing decision to the service. Builds `CategoryService.selectCategory(category_id: UUID): Observable<Catalog>` if not yet present in the existing service — POSTs to `/api/v1/catalogs` with the picked category, returns the catalog with its `id`, then routes to `/catalogs/:id/edit`. | No |
| `meesell-ai-coordinator` | `feature/smart-picker/ai` | `meesell-prompt-engineer` | Iterates `backend/app/ai_ops/prompts/smart_picker_v1.py` until `backend/tests/eval/smart_picker/run_eval.py` reports top-5 recall ≥ 80% on the 50-description fixture. Maintains the file at the canonical path per `§6A.G` (`backend/app/ai_ops/prompts/smart_picker_v1.py`). Verifies prompt content covers: (i) Layer 1 JSON-shape prefix per `§6A.E` ("Return strictly the JSON shape `{category_id: string, confidence: number, reasons: string[]}`."), (ii) few-shot bank with 5+ examples covering the top traffic super-categories (Fashion, Home & Kitchen, Beauty, Kids & Baby, Electronics — confirm against `meesho_category_tree.json` super_id distribution), (iii) compressed-tree variable substitution (`{compressed_tree}` placeholder), (iv) `temperature=0` lock per `§6A.B`. NO test-fixture contamination — the prompt's few-shot examples MUST NOT be drawn from the 50-description golden set. Registers `smart_picker.v1` in `backend/app/ai_ops/prompt_registry.py` if not already present. | No |
| | | `meesell-category-picker-builder` | Verifies `backend/app/modules/category/picker.py` against `§2.3 AI-track collaboration` + `§9.B.1` flow step 3 sub-bullets: tree compression algorithm transforms the 3,772-leaf category tree into a ≤ 8,000-token prompt-ready string (measure with `tiktoken`); the compression output is module-private-cached so amortisation works across consecutive `/suggest` calls; top-5 ranker reads Gemini's JSON-mode response and produces `CategorySuggestion[]`. Authors / maintains `backend/tests/eval/smart_picker/fixtures.json` (50 hand-labeled descriptions). Authors / maintains `backend/tests/eval/smart_picker/run_eval.py` — the pytest-based runner that gates the CI `ai_eval` job. The runner reports: top-1 recall %, top-3 recall %, top-5 recall %, per-call average cost in ₹, P95 latency in ms, per-fixture pass/fail. Iterates the ranker (NOT the prompt — that's prompt-engineer's domain) until top-5 recall ≥ 80%. Verifies confidence calibration: predicted confidence vs empirical hit-rate Brier score < 0.10. | No |
| `meesell-data-engineer` | `feature/smart-picker/data` | `meesell-scraper-maintainer` | **Conditional dispatch only.** Lead runs a staleness check FIRST: row-count and `meesho_id` checksum diff between the committed `backend/app/data/meesho_category_tree.json` and the live Meesho category page. If diff < 1% by row count AND checksum matches: NO DISPATCH; data lead writes a one-line note to `docs/status/STATUS_DATA.md` and the feature_board row stays `PENDING` until merged. If diff ≥ 1% OR checksum mismatches: scraper-maintainer runs the Playwright scraper, produces a snapshot under `data/snapshots/<YYYY-MM-DD>/`, diffs against the prior snapshot, and emits the refresh changelog entry. Re-seeding the Postgres `categories` table is a backend-coordinator activity NOT a data activity — data hands off the JSON; backend lands the seed migration. | YES — only if staleness check fails |

**Specialists NOT in the lineup (and why):**

- `meesell-angular-ui-styler` — Smart Picker page composes existing `mee-*` primitives + Layer 1 design tokens. No new styling primitive, no new design token, no theming change. The component-builder consumes the existing Tailwind 4 utility classes for layout. If a11y or mobile breakpoint issues surface during the frontend lead's PR review, the lead may add `angular-ui-styler` as a conditional pickup for a follow-up slice.
- `meesell-auth-builder` — Smart Picker is JWT-gated through the global middleware chain. No new auth surface, no new MSG91/JWT/refresh-token concern. Auth already lands at the `iam` module per `§7` (separately shipped under `feature/auth-otp`).
- `meesell-image-precheck-builder` — Wrong workload. Picker is a text→category task, no Vision pipeline involved.
- `meesell-infra-builder` — Gemini API key, LangFuse secret, ai_ops budget Valkey DB are already provisioned for the foundation pass. No new secret, no new IAM binding, no new K3s manifest. The `FEATURE_SMART_PICKER_ENABLED` env var lands in the existing dev/staging ConfigMaps — backend-coordinator owns that thin wiring during the api-routes-builder dispatch.
- `meesell-xlsx-parser` — Category seed comes from the scraper, not from XLSX. (The XLSX path feeds the `templates` + `field_enum_values` tables consumed by `§9.B.4` `/schema` — that surface is touched by Smart Picker only on category selection AFTER the picker fires, not during `/suggest`.)
- `meesell-legal-writer` — No copy strings beyond inline UI labels (which the component-builder writes). No legal disclosure needed for AI-driven suggestions in V1.

---

## Code surfaces

Every file the feature will create, modify, or rename. The `Status` column uses: **NEW** (file does not exist), **MODIFY** (file exists and will change), **RENAME** (file moves via `git mv`), **VERIFY** (file exists; specialist confirms shape matches the spec; modify only if drift found), **NO CHANGE** (file is referenced but not touched).

### Backend (`feature/smart-picker/backend`)

| Path | Status | Specialist | Diff scope |
|---|---|---|---|
| `backend/app/modules/category/router.py` | VERIFY + MODIFY | api-routes-builder | Confirm `/suggest` route matches `§9.B.1` (rate_limit decorator, response_model, Depends chain). Add `FEATURE_SMART_PICKER_ENABLED` flag guard returning 404. |
| `backend/app/modules/category/schemas.py` | VERIFY | api-routes-builder | Confirm `SuggestQuery`, `SuggestResponse`, `CategorySuggestion` match `§9.E` field-for-field. NO change unless drift. |
| `backend/app/modules/category/service.py` | VERIFY + MODIFY | services-builder | Confirm `suggest_categories(user_id, q)` matches `§9.B.1` flow. Tighten cache key to `smart_picker:{sha256(q)}:v{cache_version}` if not already; verify graceful-fallback branch returns 200-shape per D1. |
| `backend/app/modules/category/picker.py` | VERIFY + MODIFY | category-picker-builder | Confirm tree compression ≤ 8 k tokens; tighten ranker if golden set < 80%. |
| `backend/app/modules/category/repository.py` | VERIFY | database-builder | Confirm `search_via_trigram` + `assert_category_exists_uncached` shapes match `§9.D`. NO change unless drift. |
| `backend/app/modules/category/exceptions.py` | VERIFY | api-routes-builder | Confirm `SuggestQueryInvalidError` + `CategoryNotFoundError` shapes match `§9.G`. NO change unless drift. |
| `backend/app/ai_ops/client.py` | NO CHANGE | (none) | Specialist verifies the `"smart_picker"` Literal is one of the 3 workloads enumerated per `§6A.B`. |
| `backend/app/ai_ops/prompts/smart_picker_v1.py` | MODIFY | prompt-engineer | Iterate prompt + few-shots until eval ≥ 80% top-5 recall. |
| `backend/app/ai_ops/prompt_registry.py` | VERIFY + MODIFY | prompt-engineer | Confirm `smart_picker.v1` registry entry exists per `§6A.G`; add if missing. |
| `backend/app/ai_ops/eval.py` | NO CHANGE | (none) | Verified to expose `run_eval(workload="smart_picker")` per `§6A.H`. |
| `backend/app/config.py` | MODIFY | api-routes-builder | Add `FEATURE_SMART_PICKER_ENABLED: bool = True` (dev default) to Pydantic Settings per D2. |
| `backend/tests/modules/category/test_suggest_unit.py` | NEW or MODIFY | services-builder | Service-layer unit tests covering `§9.J` unit-test items #1, #4, #5. |
| `backend/tests/integration/test_smart_picker_integration.py` | NEW | services-builder | Full-flow integration tests per `§9.J` integration items #1, #2, #3. |
| `backend/tests/eval/smart_picker/fixtures.json` | VERIFY + MODIFY | category-picker-builder | Confirm 50 hand-labeled descriptions present; expand if fewer. No description from this fixture may appear in the prompt's few-shot bank (data-leakage prevention). |
| `backend/tests/eval/smart_picker/run_eval.py` | VERIFY + MODIFY | category-picker-builder | Runner reports top-1 / top-3 / top-5 recall + cost + P95 latency + Brier score. Gates CI `ai_eval` job. |
| `backend/tests/eval/smart_picker/eval_results.json` | MODIFY | category-picker-builder | Last-run results snapshot; updated by every iteration. NOT used by code — for human inspection only. |

### Frontend (`feature/smart-picker/frontend`)

| Path | Status | Specialist | Diff scope |
|---|---|---|---|
| `frontend/src/app/features/catalog-new/` → `frontend/src/app/features/smart-picker/` | RENAME | angular-component-builder | `git mv` per D4. First commit on the branch. |
| `frontend/src/app/features/smart-picker/smart-picker.component.ts` | NEW (post-rename of catalog-new.component.ts) | angular-component-builder | `SmartPickerComponent` standalone, OnPush, signals for state, reactive form with debounce, top-3 card render + fallback CTA. |
| `frontend/src/app/features/smart-picker/category-card.component.ts` | NEW | angular-component-builder | `CategoryCardComponent` presentational — path + commission% + reasons[] + "Use this" CTA. |
| `frontend/src/app/features/smart-picker/services/category.service.ts` | NEW or MODIFY | angular-service-builder | `CategoryService.suggest(description)` + `browseRedirect()` + `selectCategory(category_id)`. |
| `frontend/src/app/features/smart-picker/smart-picker.model.ts` | VERIFY | angular-service-builder | Confirm `CategorySuggestion` and `SuggestResponse` TypeScript interfaces match backend `§9.E` field-for-field. Adjust if drift. |
| `frontend/src/app/features/smart-picker/smart-picker.component.spec.ts` | NEW (post-rename of catalog-new.component.spec.ts) | angular-component-builder | Vitest unit tests for the component covering: empty input shows nothing; valid input fires service.suggest with debounce; 3 cards render on populated response; fallback CTA renders when `fallback_offered=true`. |
| `frontend/src/app/app.routes.ts` | VERIFY | angular-component-builder | Confirm `/catalogs/new` route loads the renamed `SmartPickerComponent` via `loadComponent`. Update import path if rename touched it. |

### AI cross-cutting (`feature/smart-picker/ai`)

These overlap with the Backend table because `ai_ops/` lives under `backend/`. The AI branch's PR may touch:

| Path | Status | Specialist | Diff scope |
|---|---|---|---|
| `backend/app/ai_ops/prompts/smart_picker_v1.py` | MODIFY | prompt-engineer | (Same row as above — AI branch owns the content; backend branch sees the PR's diff as a peer-merge from the AI branch when both rebase onto `feature/smart-picker`.) |
| `backend/app/ai_ops/prompt_registry.py` | VERIFY + MODIFY | prompt-engineer | (Same row as above.) |
| `backend/tests/eval/smart_picker/fixtures.json` | VERIFY + MODIFY | category-picker-builder | (Same row as above.) |
| `backend/tests/eval/smart_picker/run_eval.py` | VERIFY + MODIFY | category-picker-builder | (Same row as above.) |
| `backend/app/modules/category/picker.py` | VERIFY + MODIFY | category-picker-builder | (Same row as above. NOTE: this file LIVES in the category module per the existing scaffold, but the AI track owns the ranking pipeline content per `§2.3` AI-track collaboration. The AI branch's PR diff includes this file; backend lead reviews for module-boundary correctness; AI lead reviews for ranking correctness. Cross-lead coordination required at merge time.) |

> **Shared-file note:** `picker.py` and the `ai_ops/` files are touched by both AI and backend branches in different ways. Per Master Plan §8.1: this is detected by the `check-shared-touches` CI job. The branches MUST be merged in a deterministic order — `feature/smart-picker/ai` first, then `feature/smart-picker/backend` rebases on the AI tip. See §6 Review + iteration protocol for the merge-order rule.

### Data (`feature/smart-picker/data`)

| Path | Status | Specialist | Diff scope |
|---|---|---|---|
| `backend/app/data/meesho_category_tree.json` | NO CHANGE (default) | (none) | Verified up-to-date by data lead's staleness check. |
| `data/snapshots/<YYYY-MM-DD>/` | NEW (conditional) | scraper-maintainer | Only if staleness check fails. New scrape output. |
| `scripts/seed_categories.py` (or equivalent) | MODIFY (conditional) | scraper-maintainer + data-engineer lead | Only if staleness check fails. Updates the seeder. Cross-lead handoff to backend lead for the Alembic seed migration. |

### Infra (`feature/smart-picker/infra`)

| Path | Status |
|---|---|
| (none) | NO CHANGE — no new secret, no new IAM, no new K3s manifest. Flag env var lands via backend's `config.py` and the existing dev/staging ConfigMaps. |

### Docs (touched by various leads as part of their group PRs)

| Path | Status | Owner | Diff scope |
|---|---|---|---|
| `docs/V1_FEATURE_SPEC.md` §F2 | MODIFY (post-ship, not on this planning PR) | Master session | Add "implemented YYYY-MM-DD" stamp + PR link after `feature/smart-picker` → `develop` merge. |
| `docs/BACKEND_ARCHITECTURE.md` §9 | NO CHANGE | (none) | Already LOCKED. No amendment expected unless implementation discovers a spec error (which would itself escalate to founder per §7.3 of repo management master plan). |
| `docs/FRONTEND_ARCHITECTURE.md` §4 | NO CHANGE | (none) | Folder name already specifies `smart-picker/` per locked line 418. Frontend rename brings reality into compliance, no doc amendment needed. |
| `docs/status/feature_board_backend.md` | MODIFY | backend lead | Add `PENDING` row for smart-picker during the planning-PR-merge step. |
| `docs/status/feature_board_frontend.md` | MODIFY | frontend lead | Add `PENDING` row for smart-picker during the planning-PR-merge step. |
| `docs/status/feature_board_ai.md` | MODIFY | AI lead | Add `PENDING` row for smart-picker during the planning-PR-merge step. |
| `docs/status/feature_board_data.md` | MODIFY | data lead | Add `PENDING` row for smart-picker during the planning-PR-merge step. |

### CI/CD

| Path | Status | Owner | Diff scope |
|---|---|---|---|
| `.github/workflows/ci.yml` | MODIFY | services-builder (backend lead reviews) | Add `ai_eval` job (nightly + on-demand) running `pytest backend/tests/eval/smart_picker/` against a dev-tunnel Postgres + Valkey. The job sets `GEMINI_API_KEY` from the CI workload-identity-federated SA. Failing the recall threshold marks the job RED; the AI lead's merge gate consumes the latest job status per AI PR template gate "ai_eval green within last 24h". |

---

## Documentation deliverables

Per Decision G4, this list is the documentation acceptance gate for the feature. ALL items MUST be present (or N/A-justified) before the `feature/smart-picker` → `develop` PR is approved.

### Backend
- [ ] OpenAPI entry for `GET /api/v1/categories/suggest` auto-generated. Verifies: query param `q` (1 ≤ len ≤ 500), `200` returns `SuggestResponse` with `suggestions: list[CategorySuggestion]` (max 5) + `fallback_offered: bool`, `400` returns the i18n message `validation.suggest_q.too_short_or_long`, `402` returns the plan-guard envelope, `404` when feature flag disabled, no `503` documented (graceful fallback uses 200).
- [ ] Inline docstring on `category.service.suggest_categories` summarising the §9.B.1 flow steps.
- [ ] Inline docstring on `category.picker.compress_tree` (or equivalent function) summarising the compression heuristic + the ≤ 8 k token budget.

### Frontend
- [ ] Inline JSDoc on `SmartPickerComponent` class describing the debounce + fallback CTA rendering path + the `fallback_offered` flag handling.
- [ ] Inline JSDoc on `CategoryService.suggest` describing the error-handling matrix (401/402/400/503).
- [ ] `app.routes.ts` comment noting `/catalogs/new` → `SmartPickerComponent` (renamed from `CatalogNewComponent` per D4).

### AI
- [ ] `backend/app/ai_ops/prompt_registry.py` carries an entry for `smart_picker.v1` pointing at `backend/app/ai_ops/prompts/smart_picker_v1.py`. Entry includes: workload, version, fixture path, last observed cost.
- [ ] `backend/tests/eval/README.md` (NEW if absent) documents the golden set fixture format + the run command + the threshold targets (top-5 recall ≥ 80% for smart_picker).
- [ ] `backend/app/ai_ops/prompts/smart_picker_v1.py` top-of-file docstring records: prompt version, last eval-run date, last observed top-5 recall, last observed per-call cost, link to this `FEATURE_PLAN.md`.
- [ ] LangFuse trace sample link pasted in the AI PR body — proves cost-tracking integration fires end-to-end.

### Data
- [ ] (Default case) Data lead's staleness-check note appended to `docs/status/STATUS_DATA.md` with `categories` row count + `meesho_id` checksum.
- [ ] (Conditional) If scraper-maintainer dispatched: refresh changelog entry in data lead's memory + diff summary in PR body.

### Cross-cutting
- [ ] `docs/V1_FEATURE_SPEC.md §F2` stamped "implemented YYYY-MM-DD" with PR link (post-ship, on a follow-up doc PR).
- [ ] `.github/workflows/ci.yml` carries the `ai_eval` job referencing `backend/tests/eval/smart_picker/` — gate green within 24h of the AI PR's merge.

---

## Branch setup

| Branch | Cut from | Purpose | Who commits |
|---|---|---|---|
| `feature/smart-picker` | `develop` | Integration branch | Lead coordinators (merge approval only) |
| `feature/smart-picker/backend` | `feature/smart-picker` | Backend specialist work | meesell-backend-coordinator specialists |
| `feature/smart-picker/ai` | `feature/smart-picker` | AI/ML specialist work | meesell-ai-coordinator specialists |
| `feature/smart-picker/frontend` | `feature/smart-picker` | Frontend specialist work | meesell-frontend-coordinator specialists |

### Creation commands
```
git checkout develop && git pull
git checkout -b feature/smart-picker feature/smart-picker
git push -u origin feature/smart-picker
git checkout -b feature/smart-picker/backend feature/smart-picker
git push -u origin feature/smart-picker/backend
git checkout -b feature/smart-picker/ai feature/smart-picker
git push -u origin feature/smart-picker/ai
git checkout -b feature/smart-picker/frontend feature/smart-picker
git push -u origin feature/smart-picker/frontend
```

### PR flow (coding stage)
```
feature/smart-picker/backend → feature/smart-picker   (reviewer: meesell-backend-coordinator)
feature/smart-picker/ai → feature/smart-picker         (reviewer: meesell-ai-coordinator)
feature/smart-picker/frontend → feature/smart-picker   (reviewer: meesell-frontend-coordinator)
feature/smart-picker → develop                         (reviewer: founder)
```

### Rebase strategy
If a sibling group PR lands first, rebase the next group PR onto the updated feature/smart-picker tip before requesting review.

---

## Memory protocol

Memories leads MUST read at coding-session start:
- `.claude/agent-memory/meesell-ai-coordinator/MEMORY.md`
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md`
- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md`

Cross-feature memos: smart-picker depends on catalog-form's category_id contract; read `meesell-backend-coordinator/catalog_form_feature.md` if catalog-form is already delivered.

Naming convention for new memos: `smart_picker_feature.md` (specifically: `feature_smart_picker_<slice>.md` inside the contributing agent's memory directory per Decision G3).

### Memory discipline

```
## MEMORY DISCIPLINE (per Governance Decision G3 + G4)

At session start, in this order, READ:
1. Your own memory: .claude/agent-memory/meesell-<your-role>/MEMORY.md (the index)
2. Under the index's "## Per-feature memory > smart-picker" subsection, read EVERY listed feature_smart_picker_*.md file in your own directory.
3. docs/plans/features/smart-picker/FEATURE_PLAN.md (this entire document — mandatory per G4)
4. Cross-agent: read the latest feature_smart_picker_*.md files (if any) in:
   - .claude/agent-memory/meesell-backend-coordinator/
   - .claude/agent-memory/meesell-frontend-coordinator/
   - .claude/agent-memory/meesell-ai-coordinator/
   - .claude/agent-memory/meesell-data-engineer/
   (Read only — never write to another agent's memory directory.)

At session close, WRITE/APPEND to:
- .claude/agent-memory/meesell-<your-role>/feature_smart_picker_<your-slice>.md
  Where <your-slice> is a kebab-case tag describing your contribution
  (e.g., "prompt-v1-iteration", "service-suggest-wiring", "component-three-cards").
  Sections to include:
    ## Session header — session name + date
    ## Files touched — bullet list of paths with NEW/MODIFY/RENAME/VERIFY status
    ## What was done — bullet list of contributions
    ## Eval / test / metric results (mandatory for AI specialists; optional for others)
    ## Open items — what remains for the next session (if any)
    ## Cross-feature gotchas — observations that affect ai-autofill, image-precheck, or other features
    ## Next-session brief — one paragraph for future-self
- .claude/agent-memory/meesell-<your-role>/MEMORY.md
  Add a one-line entry under "## Per-feature memory > smart-picker":
  - [feature_smart_picker_<your-slice>.md](feature_smart_picker_<your-slice>.md) — one-line description
```

---

## Dispatch templates

Each template below is the **exact prompt the lead pastes into the `Agent()` call**, with the `{N}` session number substituted for the actual ordinal. Templates are reusable across iteration cycles — the re-dispatch protocol (see §7) prepends an "Iteration brief" preamble.

> **Naming convention reminder (per Master Plan §4):** every session name MUST follow `mesell-smart-picker-{group}-session-{N}`. The {group} token is one of `backend`, `frontend`, `ai`, `data`. No abbreviations.

> **Memory discipline applies to ALL templates.** The MEMORY DISCIPLINE block is identical across all templates and is reproduced verbatim in each. Do not omit it.

### Shared MEMORY DISCIPLINE block (reproduced verbatim in every template)

```
## MEMORY DISCIPLINE (per Governance Decision G3 + G4)

At session start, in this order, READ:
1. Your own memory: .claude/agent-memory/meesell-<your-role>/MEMORY.md (the index)
2. Under the index's "## Per-feature memory > smart-picker" subsection, read EVERY listed feature_smart_picker_*.md file in your own directory.
3. docs/plans/features/smart-picker/FEATURE_PLAN.md (this entire document — mandatory per G4)
4. Cross-agent: read the latest feature_smart_picker_*.md files (if any) in:
   - .claude/agent-memory/meesell-backend-coordinator/
   - .claude/agent-memory/meesell-frontend-coordinator/
   - .claude/agent-memory/meesell-ai-coordinator/
   - .claude/agent-memory/meesell-data-engineer/
   (Read only — never write to another agent's memory directory.)

At session close, WRITE/APPEND to:
- .claude/agent-memory/meesell-<your-role>/feature_smart_picker_<your-slice>.md
  Where <your-slice> is a kebab-case tag describing your contribution
  (e.g., "prompt-v1-iteration", "service-suggest-wiring", "component-three-cards").
  Sections to include:
    ## Session header — session name + date
    ## Files touched — bullet list of paths with NEW/MODIFY/RENAME/VERIFY status
    ## What was done — bullet list of contributions
    ## Eval / test / metric results (mandatory for AI specialists; optional for others)
    ## Open items — what remains for the next session (if any)
    ## Cross-feature gotchas — observations that affect ai-autofill, image-precheck, or other features
    ## Next-session brief — one paragraph for future-self
- .claude/agent-memory/meesell-<your-role>/MEMORY.md
  Add a one-line entry under "## Per-feature memory > smart-picker":
  - [feature_smart_picker_<your-slice>.md](feature_smart_picker_<your-slice>.md) — one-line description
```

### Template 1 — `meesell-api-routes-builder` (Backend lead dispatches)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-backend-session-{N}
LEAD: meesell-backend-coordinator
BRANCH: feature/smart-picker/backend (off feature/smart-picker)

## Your mission
Verify (and tighten where drift is found) the GET /api/v1/categories/suggest route + Pydantic schemas + feature-flag guard, so the route is production-ready for V1 Feature 2 (Smart Category Picker). Add the route-level integration smoke test asserting the 404-when-disabled behaviour.

## Mandatory reads (in this order)
1. Your own memory at .claude/agent-memory/meesell-api-routes-builder/MEMORY.md + every feature_smart_picker_*.md you've already written
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (the whole file — per G4)
3. docs/BACKEND_ARCHITECTURE.md §9.B.1 (the /suggest endpoint contract) + §9.E (Pydantic schemas) + §9.G (exception hierarchy) + §6A.A (ai_ops boundary)
4. docs/V1_FEATURE_SPEC.md §F2 (Feature 2 spec)
5. docs/plans/repo_management/MASTER_PLAN.md §3.2 (feature flag posture) + §5.2 (backend PR template) + §4 (session naming)

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with api-routes-builder and <your-slice> with route-validation-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] Route GET /api/v1/categories/suggest exists at backend/app/modules/category/router.py and matches §9.B.1: response_model=SuggestResponse, Depends(get_current_user), @rate_limit(scope="smart_picker", limit=100, window=3600), query param q (1 ≤ len ≤ 500).
- [ ] SuggestQuery + SuggestResponse + CategorySuggestion in backend/app/modules/category/schemas.py match §9.E field-for-field (no extra fields, no missing fields, no type drift).
- [ ] FEATURE_SMART_PICKER_ENABLED added to backend/app/config.py as Pydantic Settings env var (default True).
- [ ] Route guard returns 404 with body {"detail": "Smart Picker is disabled in this environment"} when the flag is False.
- [ ] Integration smoke test backend/tests/integration/test_suggest_flag_404.py asserts the 404 path AND asserts the 200 path under default config.
- [ ] OpenAPI emits for the route (verify with `pytest backend/tests/ -k openapi` or `curl localhost:8001/openapi.json | jq .paths`); response_model and query param shape both appear.
- [ ] CI gates 1 (unit) + 2 (smoke) + 3 (lint) green locally.

## Hard constraints (refuse to proceed if violated)
- DO NOT import adapters.gemini directly — the ai_ops boundary per §6A.A forbids it. Only ai_ops.client is the legal import surface.
- DO NOT touch backend/app/modules/category/service.py — that is services-builder's slice.
- DO NOT touch backend/app/modules/category/picker.py — that is category-picker-builder's slice.
- DO NOT touch any file under backend/app/ai_ops/ — that is prompt-engineer's slice.
- DO NOT alter §9.B.1 flow semantics (graceful fallback, top-5 max_length, etc.) — those are locked. If you find a drift, escalate to the backend lead before editing.

## Files you may touch
- backend/app/modules/category/router.py
- backend/app/modules/category/schemas.py (verify only; modify only if drift)
- backend/app/modules/category/exceptions.py (verify only)
- backend/app/config.py (add the flag)
- backend/tests/integration/test_suggest_flag_404.py (NEW)

## Files you must NOT touch
- backend/app/modules/category/service.py
- backend/app/modules/category/picker.py
- backend/app/modules/category/repository.py
- backend/app/ai_ops/** (entire tree)
- backend/tests/eval/** (entire tree)
- frontend/** (entire tree)
- docs/** (you may READ; you may NOT modify any locked section)

## Final report format (paste into PR body + STATUS_BACKEND.md)
- Files touched: <bullet list with NEW/MODIFY/VERIFY status>
- /suggest contract conformance vs §9.B.1: <PASS / drift items if any>
- Schema conformance vs §9.E: <PASS / drift items if any>
- 404-when-disabled test: <PASS / log>
- OpenAPI emission: <PASS / openapi.json excerpt>
- Lint + unit + smoke gates: <PASS / log>
- session-close memory file: <path + one-line summary>
```

### Template 2 — `meesell-services-builder` (Backend lead dispatches)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-backend-session-{N}
LEAD: meesell-backend-coordinator
BRANCH: feature/smart-picker/backend (off feature/smart-picker)

## Your mission
Verify (and tighten where drift is found) category.service.suggest_categories() end-to-end against §9.B.1, including: cache key/TTL, plan_guard call, ai_ops.client invocation shape, Layer 2 validation via repository, graceful fallback on BudgetExceededError (200 + empty + fallback_offered=true per D1), enrichment of surviving suggestions from the in-process category tree. Author the full integration test suite covering all four flow branches.

## Mandatory reads (in this order)
1. Your own memory at .claude/agent-memory/meesell-services-builder/MEMORY.md + every feature_smart_picker_*.md you've already written
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (the whole file — per G4)
3. docs/BACKEND_ARCHITECTURE.md §9.B.1 (full flow) + §9.C (service surface) + §6A.A + §6A.C (ai_ops client) + §6A.E (3-layer guardrail) + §6A.F (budget cap fallback semantics) + §4.D (cache helper) + §4.E (plan_guard)
4. docs/V1_FEATURE_SPEC.md §F2
5. docs/plans/repo_management/MASTER_PLAN.md §3.2 + §5.2 + §4

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with services-builder and <your-slice> with service-suggest-wiring-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] category.service.suggest_categories(user_id, q) matches §9.B.1 flow steps 1–6:
    1. SuggestQuery validation
    2. plan_guard.enforce_plan_limit(user_id, plan, "smart_picker_hourly", 1)
    3. core/cache.get_or_set(key="smart_picker:{sha256(q)}:v{cache_version}", ttl=900, ...)
    4. On miss: ai_ops.client.call_gemini(ctx, "smart_picker.v1", {description: q, compressed_tree: <compressed>}) with allowed_enums=None
    5. Layer 2 via repository.assert_category_exists_uncached for each returned category_id; up-to-2 retries from §6A; final exhaustion → empty suggestions + fallback_offered=true
    6. On BudgetExceededError → return SuggestResponse(suggestions=[], fallback_offered=True) — status 200 per D1
    7. Enrich each surviving suggestion with super_id/super_name/path/leaf_name from the pre-warmed category tree
    8. Cache the enriched SuggestResponse + return
- [ ] Integration test file backend/tests/integration/test_smart_picker_integration.py covers (per §9.J integration test plan + D1 fallback shape):
    - Cache hit shape (deterministic round-trip)
    - Cache miss flow (ai_ops mocked deterministic)
    - Graceful fallback on BudgetExceededError (200, empty, flag=true)
    - Layer 2 invalid-category-id → retry → exhaustion → empty + flag=true (200)
    - /suggest → /browse round-trip when fallback_offered=true (asserts the /browse endpoint accepts and ranks via pg_trgm)
- [ ] Unit tests in backend/tests/modules/category/test_suggest_unit.py cover §9.J unit items #4 + #5 (graceful fallback, Layer 2 retry path) with the ai_ops client mocked.
- [ ] i18n message ids `validation.suggest_q.too_short_or_long` + `category.not_found` exist in backend/app/i18n/messages_en.py.
- [ ] All CI gates 1 (unit) + 2 (smoke) + 3 (lint) green locally. Gate 4 (integration) green locally.

## Hard constraints (refuse to proceed if violated)
- DO NOT import adapters.gemini directly per §6A.A + §16.D.2. Only ai_ops.client.call_gemini is legal.
- DO NOT raise HTTPException(503) on BudgetExceededError — graceful fallback is locked at 200 per §9.B.1 + D1. Raising 503 is a CI-failing pattern.
- DO NOT modify backend/app/modules/category/router.py — that's api-routes-builder's slice.
- DO NOT modify backend/app/modules/category/picker.py — that's category-picker-builder's slice.
- DO NOT modify any file under backend/app/ai_ops/ — that's prompt-engineer/AI lead's slice.
- DO NOT alter §9.B.1 cache key format — it's a contract used by ops to invalidate the global cache during quarterly category refresh.
- DO NOT widen the route's max_length for the suggestions list — §9.E locks it at 5; D1 confirms.

## Files you may touch
- backend/app/modules/category/service.py
- backend/tests/modules/category/test_suggest_unit.py (NEW or MODIFY)
- backend/tests/integration/test_smart_picker_integration.py (NEW)
- backend/app/i18n/messages_en.py (add missing message ids only; do not modify existing ids)
- .github/workflows/ci.yml (add ai_eval job; coordinate with AI lead via inter-lead memo)

## Files you must NOT touch
- backend/app/modules/category/router.py
- backend/app/modules/category/picker.py
- backend/app/modules/category/repository.py (database-builder owns; if a method is missing, escalate to backend lead)
- backend/app/ai_ops/** (entire tree)
- frontend/** (entire tree)
- docs/** (read only)

## Final report format
- Files touched: <bullet list>
- §9.B.1 conformance: <PASS / drift items>
- Integration test coverage: <count + which branches>
- Graceful fallback shape (assert in test): <200 + empty + flag=true confirmed>
- All gates: <PASS / log>
- session-close memory file: <path + one-line summary>
```

### Template 3 — `meesell-database-builder` (Backend lead dispatches)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-backend-session-{N}
LEAD: meesell-backend-coordinator
BRANCH: feature/smart-picker/backend (off feature/smart-picker)

## Your mission
Verify the existing categories-table repository methods match §9.D signatures + the pg_trgm GIN indexes are exercised by search_via_trigram. Author the P95 < 200 ms benchmark fixture proving idx_categories_path_trgm is hit under realistic load. NO new tables. NO new migration. If a method is missing or wrong-shaped, escalate to the backend lead before patching.

## Mandatory reads (in this order)
1. Your own memory + feature_smart_picker_*.md files
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (per G4)
3. docs/BACKEND_ARCHITECTURE.md §9.D (repository surface) + §9.J unit-test item #1 (trigram-search P95 < 200 ms benchmark) + §4.C (global-data carve-out — NO tenancy scope on categories table) + the database-builder memory at .claude/agent-memory/meesell-database-builder/MEMORY.md (session 2 G4 commit established the GIN indexes)
4. docs/plans/repo_management/MASTER_PLAN.md §5.2 (Backend PR template)

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with database-builder and <your-slice> with repository-verification-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] search_via_trigram(db, q, super_id, limit, offset) → (rows, total_count) signature matches §9.D verbatim.
- [ ] assert_category_exists_uncached(db, category_id) → bool signature matches §9.D verbatim.
- [ ] EXPLAIN ANALYZE on search_via_trigram("kurti", super_id=None, 20, 0) shows "Bitmap Index Scan on idx_categories_path_trgm" (paste in PR body).
- [ ] EXPLAIN ANALYZE for the super_id filter path uses idx_categories_super_name_trgm (paste).
- [ ] P95 < 200 ms benchmark fixture at backend/tests/modules/category/test_trigram_p95.py runs 100 iterations against the dev-tunnel Postgres + reports P95 latency.
- [ ] Benchmark passes (P95 < 200 ms) on the dev-tunnel DB at HEAD revision.
- [ ] _GLOBAL_TABLES set in core/tenancy.py includes 'categories' (the §4.C carve-out documented in the existing module).

## Hard constraints (refuse to proceed if violated)
- NO new Alembic migration. NO new tables. The categories table is sealed at the foundation revision per §0.D.
- DO NOT add user_id scoping to any categories-table query — categories is GLOBAL data per §4.C.
- DO NOT modify the GIN indexes — they were locked in session 2 G4 per the database-builder memory.
- If §9.D method shape drift is found, OPEN AN INTER-LEAD REQUEST to the backend lead before editing repository.py.

## Files you may touch
- backend/tests/modules/category/test_trigram_p95.py (NEW)
- backend/app/modules/category/repository.py (modify ONLY if a §9.D method is missing or drifted, and ONLY after lead approval)

## Files you must NOT touch
- backend/alembic/versions/** (entire tree — NO new migration)
- backend/app/modules/category/router.py
- backend/app/modules/category/service.py
- backend/app/modules/category/picker.py
- backend/app/ai_ops/** (entire tree)
- frontend/** (entire tree)
- core/tenancy.py (verify only)

## Final report format
- §9.D method conformance: <PASS / drift items>
- EXPLAIN ANALYZE output (path index hit): <paste>
- EXPLAIN ANALYZE output (super_name index hit): <paste>
- P95 latency over 100 iterations: <Xms>
- Benchmark PASS/FAIL: <result>
- session-close memory file: <path + one-line summary>
```

### Template 4 — `meesell-angular-component-builder` (Frontend lead dispatches)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-frontend-session-{N}
LEAD: meesell-frontend-coordinator
BRANCH: feature/smart-picker/frontend (off feature/smart-picker)

## Your mission
1. RENAME frontend/src/app/features/catalog-new/ → frontend/src/app/features/smart-picker/ (per D4) as the FIRST commit on this branch. Use `git mv` to preserve file history. Update class name CatalogNewComponent → SmartPickerComponent.
2. Build SmartPickerComponent (page) — reactive form for description (10..500 chars, 400 ms debounce on form-change), signal-backed loading + suggestions + fallback_offered states, top-3 card render via CategoryCardComponent, fallback CTA routing to /categories/browse.
3. Build CategoryCardComponent (presentational) — accepts CategorySuggestion input, renders path + commission_pct + reasons[] + "Use this category" CTA.
4. Author Vitest unit tests for both components.

## Mandatory reads (in this order)
1. Your own memory + feature_smart_picker_*.md files
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (per G4)
3. docs/FRONTEND_ARCHITECTURE.md (whole document — focus §4 Layer 4 + §6 Path Aliases + §8 Wave 2E + the @mee/ui contracts in §2)
4. docs/V1_FEATURE_SPEC.md §F2 + §3 (user journey item 5 for /catalogs/new)
5. docs/plans/repo_management/MASTER_PLAN.md §5.3 (Frontend PR template) + §4 (session naming) + §3.2 (frontend feature flag pattern)

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with angular-component-builder and <your-slice> with component-three-cards-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] First commit on branch: `git mv frontend/src/app/features/catalog-new frontend/src/app/features/smart-picker` + class renames inside the moved files. History preserved (`git log --follow` works).
- [ ] SmartPickerComponent is standalone, OnPush, signals for state. Reactive form (FormBuilder, FormGroup, FormControl with Validators.minLength(10), Validators.maxLength(500)).
- [ ] Description field on form value-changes pipe (debounceTime(400), distinctUntilChanged()) triggers CategoryService.suggest(description).
- [ ] Top-3 cards render via @for-loop on suggestions().slice(0, 3) — never more than 3 visible.
- [ ] When fallback_offered=true AND suggestions.length===0: render mee-card empty state with mee-button CTA "Browse all categories" routing to /categories/browse via Router.navigate.
- [ ] When fallback_offered=true AND suggestions.length > 0: render the 3 cards AND a secondary "Browse if none match" link below.
- [ ] CategoryCardComponent is standalone, OnPush, takes @Input() suggestion: CategorySuggestion + emits @Output() picked = new EventEmitter<UUID>(). Renders the path as a breadcrumb, commission_pct% as a mee-badge severity='info', reasons[] as a max-3-item bullet list (truncate to 3 if more).
- [ ] PrimeNG imports ZERO — only @mee/ui, @mee/shared, @mee/layouts, @angular/* (per FRONTEND_ARCHITECTURE.md §4 non-negotiable rule).
- [ ] Vitest unit test smart-picker.component.spec.ts covers: invalid input shows nothing; valid input fires service.suggest with debounce; 3 cards render on populated SuggestResponse; fallback CTA renders when fallback_offered=true AND suggestions empty; secondary "Browse if none match" link renders when fallback_offered=true AND suggestions non-empty.
- [ ] Vitest unit test category-card.component.spec.ts covers: path/commission/reasons render; picked emits with correct category_id on CTA click.
- [ ] Build pass: `pnpm build` < 90 s (CLAUDE.md Decision 12). Bundle delta noted in PR body.
- [ ] Screenshots at 360 px and 1280 px attached to PR body.
- [ ] Keyboard nav works (Tab through input → cards → CTAs; Enter activates).

## Hard constraints (refuse to proceed if violated)
- NO direct PrimeNG imports — they live only in @mee/ui (FRONTEND_ARCHITECTURE.md §4 non-negotiable #1).
- NO Angular Material imports (CLAUDE.md Decision 10).
- NO NgModules — standalone everywhere (CLAUDE.md Decision 9).
- NO new mee-* primitive — compose existing ones (mee-textarea, mee-card, mee-button, mee-badge, mee-skeleton). If a new primitive is needed, escalate to frontend lead.
- NO change to app.routes.ts route definition — /catalogs/new keeps loading the (now-renamed) SmartPickerComponent.
- NO direct HttpClient call in the component — go through CategoryService (DIP per FRONTEND_ARCHITECTURE.md §1).
- NO inline styles — use Tailwind 4 utility classes + design tokens.

## Files you may touch
- frontend/src/app/features/smart-picker/** (the entire renamed tree)
- frontend/src/app/app.routes.ts (update import path post-rename only)

## Files you must NOT touch
- frontend/src/app/features/catalog-new/** (after the git mv, this path ceases to exist; do not re-create)
- frontend/src/app/ui/** (Layer 2 abstraction wall — no new primitives without lead approval)
- frontend/src/app/core/** (services-builder's slice)
- frontend/src/app/design-system/** (Layer 1 — ui-styler's slice)
- backend/** (entire tree)
- docs/** (read only)

## Final report format
- git mv evidence: <commit SHA + `git log --follow` confirmation>
- Files touched: <bullet list post-rename>
- @mee/ui primitives used: <list>
- PrimeNG/Material grep: <empty result confirms isolation>
- Build time: <X seconds>
- Bundle delta: <+/- KB>
- Screenshots 360 / 1280: <attached>
- Vitest pass count + coverage: <log>
- a11y notes: <keyboard nav + contrast checks>
- session-close memory file: <path + one-line summary>
```

### Template 5 — `meesell-angular-service-builder` (Frontend lead dispatches)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-frontend-session-{N}
LEAD: meesell-frontend-coordinator
BRANCH: feature/smart-picker/frontend (off feature/smart-picker)

## Your mission
Build CategoryService.suggest(description) wrapping HttpClient.get<SuggestResponse>('/api/v1/categories/suggest') with the full error matrix (401/402/400/503), browseRedirect() routing helper, and selectCategory(category_id) catalog-creation + navigation helper. Verify the TypeScript model file matches backend §9.E.

## Mandatory reads (in this order)
1. Your own memory + feature_smart_picker_*.md files
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (per G4)
3. docs/FRONTEND_ARCHITECTURE.md (whole document — focus on services + core/interceptors + the AuthService contract referenced from FE-D5)
4. docs/BACKEND_ARCHITECTURE.md §9.B.1 (the contract you are calling) + §9.E (Pydantic schemas this service mirrors in TypeScript) — for TypeScript model alignment ONLY; do not import or read backend code
5. docs/V1_FEATURE_SPEC.md §F2
6. docs/plans/repo_management/MASTER_PLAN.md §5.3 + §4

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with angular-service-builder and <your-slice> with service-suggest-error-matrix-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] CategoryService.suggest(description: string): Observable<SuggestResponse> — HttpClient.get<SuggestResponse>('/api/v1/categories/suggest', { params: { q: description } }) with JWT auto-attached via the global interceptor.
- [ ] Error mapping in catchError:
    - 401 → AuthService.logout() + return EMPTY (or rethrow if AuthService handles)
    - 402 → MeeToastService.warn("Daily AI quota exceeded — try again later or browse manually") + return of(SuggestResponse(suggestions=[], fallback_offered=true)) (lets the component render the fallback UI)
    - 400 → MeeToastService.error(translate the i18n message id) + return EMPTY (component handles empty)
    - 503 → MeeToastService.error("Smart Picker unavailable — please try Manual Browse") + return of(SuggestResponse(suggestions=[], fallback_offered=true))
    - 5xx other → MeeToastService.error("Something went wrong") + rethrow
- [ ] CategoryService.browseRedirect(): void — Router.navigate(['/categories/browse']).
- [ ] CategoryService.selectCategory(category_id: UUID): Observable<Catalog> — POST /api/v1/catalogs with { category_id }, returns the new catalog row, then Router.navigate(['/catalogs', catalog.id, 'edit']).
- [ ] smart-picker.model.ts TypeScript interfaces:
    - SuggestResponse { suggestions: CategorySuggestion[]; fallback_offered: boolean }
    - CategorySuggestion { category_id: string; super_id: string; super_name: string; path: string; leaf_name: string; confidence: number; reasons: string[] }
  Both match backend §9.E field-for-field; suggestions.length max 5 documented in JSDoc.
- [ ] Vitest unit tests cover: happy path (HttpClient mock returns SuggestResponse, service emits it), 402 fallback (component-friendly empty shape emitted), 400 message id translated, 401 logout fired.
- [ ] All CI gates 1 (unit) + 3 (lint) green locally.

## Hard constraints (refuse to proceed if violated)
- NO custom JWT handling — the global interceptor at frontend/src/app/core/interceptors/auth.interceptor.ts does the work.
- NO direct localStorage / sessionStorage for tokens — per CLAUDE.md Decision 14 amendment + FE-D5: access JWT in memory only, refresh token in HttpOnly cookie owned by backend.
- NO PrimeNG/Material imports in this service.
- NO change to the component file — component-builder's slice.
- DO NOT widen the SuggestResponse type beyond §9.E + V1.5 forward-compat (sample_attributes is NOT in the V1 response payload per D1).

## Files you may touch
- frontend/src/app/features/smart-picker/services/category.service.ts
- frontend/src/app/features/smart-picker/smart-picker.model.ts (verify; modify only if drift)
- frontend/src/app/features/smart-picker/services/category.service.spec.ts (NEW)

## Files you must NOT touch
- frontend/src/app/features/smart-picker/smart-picker.component.ts (component-builder's slice)
- frontend/src/app/features/smart-picker/category-card.component.ts (component-builder's slice)
- frontend/src/app/core/** (root-level core wiring; lead's domain)
- frontend/src/app/ui/** (Layer 2 abstraction wall)
- backend/** (entire tree)
- docs/** (read only)

## Final report format
- Files touched: <bullet list>
- Error matrix coverage: <401/402/400/503 each — PASS/FAIL with test name>
- §9.E TypeScript alignment: <PASS / drift items>
- Vitest pass count: <log>
- Lint: <PASS / log>
- session-close memory file: <path + one-line summary>
```

### Template 6 — `meesell-prompt-engineer` (AI lead dispatches)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. Stay inside backend/app/ai_ops/ and backend/tests/eval/.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-ai-session-{N}
LEAD: meesell-ai-coordinator
BRANCH: feature/smart-picker/ai (off feature/smart-picker)

## Your mission
Iterate the smart_picker.v1 prompt template at backend/app/ai_ops/prompts/smart_picker_v1.py until the eval at backend/tests/eval/smart_picker/run_eval.py reports top-5 recall ≥ 80% on the 50-description golden fixture, with per-call cost ≤ ₹0.05 average. Verify the prompt-registry entry exists in backend/app/ai_ops/prompt_registry.py. No eval-data leakage into few-shots.

## Mandatory reads (in this order)
1. Your own memory + feature_smart_picker_*.md files
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (per G4)
3. docs/BACKEND_ARCHITECTURE.md §6A (whole section — focus §6A.A, §6A.B "smart_picker" workload, §6A.E Layer 1 prefix, §6A.G prompt_registry contract, §6A.H eval thresholds)
4. docs/V1_FEATURE_SPEC.md §F2 (acceptance criteria — top-3 hit rate ≥ 80%)
5. backend/tests/eval/smart_picker/fixtures.json (the golden set — read every description to understand the distribution but do NOT incorporate any of these descriptions into your few-shots)
6. backend/app/data/meesho_category_tree.json (the 3,772-leaf tree — sample a subset; do not load whole file into prompt unless the compression has already produced a digest)
7. docs/plans/repo_management/MASTER_PLAN.md §5.4 (AI PR template) + §4 (session naming)
8. AI coordinator's per-feature memory and registry index

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with prompt-engineer and <your-slice> with prompt-v1-iteration-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] backend/app/ai_ops/prompts/smart_picker_v1.py contains:
    - TEMPLATE: str — the full prompt with {description} and {compressed_tree} placeholders
    - VERSION = "v1"
    - WORKLOAD = "smart_picker"
    - rendered_by = "text"
    - Top-of-file docstring: prompt version, last eval-run date, last observed top-5 recall %, last observed per-call cost ₹, link to docs/plans/features/smart-picker/FEATURE_PLAN.md
- [ ] Prompt includes Layer 1 JSON-shape prefix per §6A.E: "Return strictly the JSON shape `{category_id: string, confidence: number, reasons: string[]}`."
- [ ] Few-shot bank includes 5+ examples covering Fashion / Home & Kitchen / Beauty / Kids & Baby / Electronics super-categories.
- [ ] NO few-shot example matches any description in backend/tests/eval/smart_picker/fixtures.json (data-leakage prevention — check via substring match script or manual diff).
- [ ] backend/app/ai_ops/prompt_registry.py contains a registry entry for "smart_picker.v1" pointing at this file, with fixture path and observed cost field populated.
- [ ] Eval `pytest backend/tests/eval/smart_picker/run_eval.py` reports:
    - top-5 recall ≥ 80% (HARD GATE)
    - per-call avg cost ≤ ₹0.05 (HARD GATE)
    - top-3 recall reported (no threshold; informational)
    - top-1 recall reported (no threshold; informational)
- [ ] LangFuse trace sample link pasted in PR body — confirms cost-tracking integration fires.

## Hard constraints (refuse to proceed if violated)
- DO NOT call adapters.gemini.generate_text directly. Use ai_ops.client.call_gemini per §6A.A.
- DO NOT use any description from backend/tests/eval/smart_picker/fixtures.json in the few-shot bank. This is data-leakage; it invalidates the eval. If you find one accidentally added, remove it BEFORE running eval.
- DO NOT raise the temperature from 0 (locked at temperature=0 per §6A.B for smart_picker workload determinism).
- DO NOT touch backend/app/modules/category/ — that is the category-picker-builder + backend track's slice.
- DO NOT touch tests/eval/smart_picker/run_eval.py or fixtures.json — category-picker-builder owns those.
- DO NOT lower the 80% recall target. If you can't meet it after iteration, escalate to AI lead (re-dispatch protocol §6).

## Files you may touch
- backend/app/ai_ops/prompts/smart_picker_v1.py
- backend/app/ai_ops/prompt_registry.py (verify; modify only if registry entry missing)

## Files you must NOT touch
- backend/tests/eval/smart_picker/** (category-picker-builder's slice)
- backend/app/ai_ops/client.py, cost_tracker.py, guardrail.py, budget_cap.py, eval.py (locked seam contracts)
- backend/app/modules/category/** (backend track + category-picker-builder)
- frontend/** (entire tree)
- docs/** (read only)

## Final report format
- Files touched: <bullet list>
- Prompt version: smart_picker.v1
- Eval results: top-1 / top-3 / top-5 recall %
- Per-call avg cost: ₹X
- Per-call P95 latency: <Xms>
- LangFuse trace sample: <link>
- Data-leakage check: <PASS — no fixture description in few-shots>
- Few-shot super-category coverage: <Fashion / Home / Beauty / Kids / Electronics — all PASS>
- session-close memory file: <path + one-line summary>
```

### Template 7 — `meesell-category-picker-builder` (AI lead dispatches)

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. Stay inside backend/app/modules/category/picker.py + backend/tests/eval/smart_picker/.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-ai-session-{N}
LEAD: meesell-ai-coordinator
BRANCH: feature/smart-picker/ai (off feature/smart-picker)

## Your mission
Validate (and tighten where needed) the Smart Picker pipeline at backend/app/modules/category/picker.py — tree compression (3,772 leaves → ≤ 8,000 tokens), top-5 ranker confidence calibration, fallback path. Author / maintain the 50-description golden set at backend/tests/eval/smart_picker/fixtures.json AND the runner at run_eval.py. Iterate the RANKER (not the prompt — that's prompt-engineer's slice) until eval ≥ 80% top-5 recall AND Brier-score calibration error < 0.10.

## Mandatory reads (in this order)
1. Your own memory + feature_smart_picker_*.md files
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (per G4)
3. docs/BACKEND_ARCHITECTURE.md §6A.A + §6A.B + §6A.H (eval contract) + §9.A (AI-track collaboration) + §9.B.1 (the flow the picker participates in) + §9.E (CategorySuggestion shape — the ranker emits this)
4. docs/V1_FEATURE_SPEC.md §F2
5. AI coordinator's per-feature memory (for prior compression decisions if any)
6. backend/app/data/meesho_category_tree.json (the 3,772-leaf tree — your compression input)
7. docs/plans/repo_management/MASTER_PLAN.md §5.4 (AI PR template) + §4

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with category-picker-builder and <your-slice> with picker-pipeline-validation-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] backend/app/modules/category/picker.py exposes:
    - compress_tree(tree: dict) -> str — produces a prompt-ready compressed digest, measured ≤ 8,000 tokens via tiktoken (tiktoken-cl100k_base or equivalent)
    - The compression output is cached at module-private scope so consecutive /suggest calls within a worker amortise the compression cost
    - rank_top5(gemini_response: dict, tree: dict) -> list[CategorySuggestion] — translates Gemini JSON-mode output into the CategorySuggestion list, ordered by confidence DESC, length 0..5
- [ ] backend/tests/eval/smart_picker/fixtures.json carries ≥ 50 hand-labeled descriptions, each with:
    - description: str (the input)
    - expected_top5: list[str] (5 acceptable category_ids — the ranker's top-5 must contain at least one)
    - super_id_hint: str (for diagnostic — which super-category the description belongs to)
- [ ] backend/tests/eval/smart_picker/run_eval.py is a pytest-compatible runner exposing test_smart_picker_recall and a CLI mode (`python -m backend.tests.eval.smart_picker.run_eval`). The runner reports:
    - top-1 / top-3 / top-5 recall %
    - per-call avg cost ₹ (from ai_ops.cost_tracker)
    - P95 latency ms (Gemini call + compression + ranking)
    - Brier score for confidence calibration (predicted confidence vs empirical hit-rate)
    - per-fixture pass/fail with description + expected vs returned top-5
- [ ] Eval gates (HARD):
    - top-5 recall ≥ 80%
    - per-call avg cost ≤ ₹0.05
    - Brier score < 0.10
- [ ] backend/tests/eval/smart_picker/eval_results.json — snapshot of the latest run with all metrics. Committed for human inspection (NOT used by code).

## Hard constraints (refuse to proceed if violated)
- DO NOT modify backend/app/ai_ops/prompts/smart_picker_v1.py — that is prompt-engineer's slice.
- DO NOT modify backend/app/ai_ops/client.py or any ai_ops/ infrastructure — those are locked §6A contracts.
- DO NOT touch backend/app/modules/category/router.py, service.py, schemas.py, repository.py — those are backend track's slices.
- DO NOT call adapters.gemini.generate_text directly — all Gemini calls go through ai_ops.client.call_gemini per §6A.A.
- DO NOT lower the 80% recall, 0.10 Brier, or ₹0.05 cost target. If you can't meet them after iteration, escalate to AI lead (re-dispatch protocol §6).
- DO NOT add any description to fixtures.json that already appears in a few-shot example in prompts/smart_picker_v1.py (data-leakage prevention).

## Files you may touch
- backend/app/modules/category/picker.py
- backend/tests/eval/smart_picker/fixtures.json
- backend/tests/eval/smart_picker/run_eval.py
- backend/tests/eval/smart_picker/eval_results.json (snapshot of latest run)

## Files you must NOT touch
- backend/app/ai_ops/prompts/** (prompt-engineer's slice)
- backend/app/ai_ops/client.py, cost_tracker.py, guardrail.py, budget_cap.py, eval.py, prompt_registry.py (locked seams)
- backend/app/modules/category/router.py, service.py, schemas.py, repository.py, exceptions.py, domain.py
- frontend/** (entire tree)
- docs/** (read only)

## Final report format
- Files touched: <bullet list>
- Compression token count (max across fixtures): <X tokens>
- Eval results: top-1 / top-3 / top-5 recall %
- Per-call avg cost: ₹X
- P95 latency: <Xms>
- Brier calibration score: <X>
- Data-leakage check: <PASS — no fixture description in few-shots>
- session-close memory file: <path + one-line summary>
```

### Template 8 — `meesell-scraper-maintainer` (Data lead dispatches — CONDITIONAL)

> Dispatched ONLY IF the data lead's staleness check fails (row count diff ≥ 1% OR `meesho_id` checksum mismatch between committed `meesho_category_tree.json` and live Meesho page). Otherwise the data lead writes a one-line "no refresh needed" note to STATUS_DATA.md and the smart-picker data row stays PENDING until merged.

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell. Stay inside scripts/, backend/app/data/, and data/.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-smart-picker-data-session-{N}
LEAD: meesell-data-engineer
BRANCH: feature/smart-picker/data (off feature/smart-picker)

## Your mission
Run the Playwright scraper to refresh the Meesho category tree. Produce a new snapshot under data/snapshots/<YYYY-MM-DD>/, diff against the prior snapshot, and update backend/app/data/meesho_category_tree.json. Honour the ≤ 1 req / 2 s rate limit. Halt and escalate on any 403/429.

## Mandatory reads (in this order)
1. Your own memory + feature_smart_picker_*.md files
2. docs/plans/features/smart-picker/FEATURE_PLAN.md (per G4)
3. docs/PLAYWRIGHT_MCP_REFERENCE.md
4. docs/MEESHO_CATEGORY_INTELLIGENCE.md (LOCKED — read for selector + tree shape reference)
5. data lead's per-feature memory + prior refresh changelog entries
6. docs/plans/repo_management/MASTER_PLAN.md §5.5 (Data PR template) + §4

[Insert the SHARED MEMORY DISCIPLINE block here verbatim, replacing <your-role> with scraper-maintainer and <your-slice> with refresh-YYYY-MM-DD-or-equivalent]

## Acceptance criteria (every box must be checked before you open the PR)
- [ ] data/snapshots/<YYYY-MM-DD>/ contains the raw scrape output (gitignored).
- [ ] Diff against the prior snapshot is logged in PR body — added/removed/modified leaves count.
- [ ] backend/app/data/meesho_category_tree.json updated with the new data, schema version bumped per data lead's versioning convention.
- [ ] No 403 / 429 events during the run. If any: HALT, do NOT commit, escalate to data lead.
- [ ] Coverage report: <X/3772 leaves parsed cleanly>.
- [ ] Schema-diff impact assessment: does any field in the JSON shape change? If yes → coordinate Alembic migration with backend lead via inter-lead memo BEFORE committing.

## Hard constraints
- ≤ 1 request per 2 seconds (User-Agent compliance per CLAUDE.md scraper rule).
- HALT on 403/429 — do NOT retry without escalation.
- NO writes to backend/app/models/ — schema asks go through backend lead via cross-lead memo.

## Files you may touch
- data/snapshots/<YYYY-MM-DD>/** (gitignored)
- backend/app/data/meesho_category_tree.json
- (optionally) scripts/seed_categories.py if seeder needs adjustment — coordinate with backend lead

## Files you must NOT touch
- backend/app/models/** (schema asks → backend lead)
- backend/alembic/versions/** (migrations → backend lead)
- backend/app/modules/category/** (read-only consumers of the JSON)
- frontend/** (entire tree)
- docs/MEESHO_CATEGORY_INTELLIGENCE.md (read only; LOCKED)

## Final report format
- Snapshot path: <data/snapshots/YYYY-MM-DD/>
- Diff vs prior snapshot: <+X / -Y / ~Z leaves>
- Coverage: <X/3772>
- Schema-diff impact: <NO / YES — see memo handoff_*.md>
- 403/429 events: <NONE>
- session-close memory file: <path + one-line summary>
```

---

## Review + iteration protocol

Per Decision G1's lineup, each lead reviews their group's PR against the merge-gate checklist in `.claude/agents/meesell-<lead>.md` § "Merge gate". Below: the additional smart-picker-specific checks, the re-dispatch failure modes, and the iteration cap.

### Cross-group merge ordering (critical)

`backend/app/ai_ops/prompts/smart_picker_v1.py`, `backend/app/modules/category/picker.py`, `backend/tests/eval/smart_picker/run_eval.py`, and `backend/tests/eval/smart_picker/fixtures.json` are touched by BOTH the AI group and the backend group (per the §3 Code surfaces "Shared-file note"). The merge order is:

1. **`feature/smart-picker/ai` merges to `feature/smart-picker` FIRST.** This pin establishes the prompt version + golden set baseline.
2. **`feature/smart-picker/backend` rebases on the AI tip and then merges.** The backend tests for `service.suggest_categories` consume the locked prompt + fixture.
3. **`feature/smart-picker/frontend` may merge at any time after the AI merge** — it depends only on the §9.E response shape (locked) + the `/categories/browse` route (already shipped).
4. **`feature/smart-picker/data` may merge at any time** — if dispatched at all (default: not dispatched).

The lead opening the `feature/smart-picker` → `develop` PR is the LEAD WITH THE LARGEST CONTRIBUTION — for smart-picker, the AI lead (prompt + ranker + golden set are the differentiator surfaces). Per Master Plan §2.2 the FOUNDER approves this PR.

### Per-specialist lead PR check additions (smart-picker-specific)

| Specialist | Smart-picker-specific lead check (in addition to standard PR template) |
|---|---|
| `meesell-api-routes-builder` | 404-when-disabled test passes locally; OpenAPI shows the `q` query param with the 1–500 length bound; no 503 documented (graceful fallback is 200) |
| `meesell-services-builder` | All four integration test branches (cache hit, cache miss, graceful fallback, Layer 2 exhaustion) pass; no `HTTPException(503)` raised on `BudgetExceededError`; `i18n/messages_en.py` carries `validation.suggest_q.too_short_or_long` + `category.not_found` |
| `meesell-database-builder` | EXPLAIN ANALYZE evidence for both GIN-index hits pasted in PR body; P95 < 200 ms over 100 iterations |
| `meesell-angular-component-builder` | `git mv` history preserved (`git log --follow smart-picker.component.ts` shows the catalog-new origin); ZERO PrimeNG/Material imports in feature files (grep evidence in PR body); both fallback rendering branches covered by Vitest |
| `meesell-angular-service-builder` | All 4 error-matrix cases (401/402/400/503) have Vitest coverage; TypeScript model interfaces match §9.E field-for-field; HttpClient call uses query params (not body) |
| `meesell-prompt-engineer` | Top-5 recall ≥ 80% from latest eval run; per-call cost ≤ ₹0.05; LangFuse trace link valid; data-leakage check PASS (no fixture description in few-shots); prompt-registry entry present in `prompt_registry.py` |
| `meesell-category-picker-builder` | Top-5 recall ≥ 80%; Brier calibration < 0.10; compression ≤ 8 k tokens; P95 latency reported; fixtures.json size ≥ 50; eval runner exposes pytest entry point |
| `meesell-scraper-maintainer` (conditional) | Zero 403/429; coverage ≥ 95%; schema-diff impact assessed and (if changed) backend memo opened |

### Re-dispatch failure modes (and the exact iteration prompts)

If a specialist's PR fails the lead's check, the lead re-dispatches with the ORIGINAL TEMPLATE prefixed by an "Iteration brief" preamble. The preamble template:

```
## Iteration brief — re-dispatch attempt {M} of 3

Previous session: mesell-smart-picker-<group>-session-{N-1}
Previous PR: <link to closed/draft PR>
Why this iteration is needed:
<one-line failure summary from the lead's review>

Specific failure mode and fix path:
<one paragraph from the table below — choose by failure mode>

Constraints unchanged from session-{N-1}. Resume per the original template below.

---
[Original specialist template, verbatim]
```

The "Specific failure mode and fix path" paragraph by failure mode:

| Failure mode | Detected by | Re-dispatch fix-path paragraph |
|---|---|---|
| **Top-5 recall < 80% on smart_picker eval** | AI lead's PR review (`pytest backend/tests/eval/smart_picker/run_eval.py` output in PR body) | "Previous eval run reported top-5 recall at {X}%. The most-missed super-category was {SC} ({Y}% local recall). Iterate the few-shot bank to add 1–2 representative {SC} examples (NOT drawn from fixtures.json). Verify per-call cost stays ≤ ₹0.05 after the few-shot additions. Target: ≥ 80% top-5 recall on the next run." |
| **Per-call cost > ₹0.05** | AI lead's PR review (cost_tracker output in PR body) | "Previous run cost averaged ₹{X}/call. Tree compression token count was {Y}. Tighten compression (drop low-traffic super-category sub-trees from the digest) OR downgrade the few-shot count (target 3–4 examples instead of 5+). Re-measure cost AND recall — recall floor is still 80%." |
| **Brier calibration > 0.10** | AI lead's PR review (run_eval.py Brier output) | "Previous Brier score was {X}. The ranker over-confident on {SC} super-category (predicted {P}%, actual {A}%). Adjust the confidence floor in rank_top5 — clamp predictions in the 50–95% range; do NOT emit 99%+ confidence on any single suggestion. Re-run eval; keep recall ≥ 80% AND Brier < 0.10." |
| **ILIKE `/browse` fallback P95 > 200 ms** | Backend lead's PR review (services-builder's integration test output) OR database-builder's benchmark | "Previous /browse P95 was {X}ms. EXPLAIN ANALYZE showed {INDEX} was {USED/UNUSED}. Verify pg_trgm GIN index is hit per §9.J item #1; if not, escalate to database-builder. If the index IS hit, the issue is row-count growth — adjust the LIMIT path or pre-warm cache for the top 100 queries." |
| **Graceful fallback raises 503 instead of 200** | Backend lead's PR review (integration test fails) | "Previous test test_graceful_fallback_returns_200 failed at line {L} with HTTPException(503). The §9.B.1 contract is explicit: BudgetExceededError → return SuggestResponse(suggestions=[], fallback_offered=True) with status 200. Remove the raise; replace with the explicit return. Re-run the four integration test branches." |
| **PrimeNG import detected in feature file** | Frontend lead's PR review (grep `from 'primeng/'` in features/smart-picker/) | "Previous PR imported PrimeNG from feature code at {FILE}:{LINE}. This violates FRONTEND_ARCHITECTURE.md §4 non-negotiable rule #1. Refactor to compose via @mee/ui primitives ({mee-textarea / mee-card / mee-button / mee-badge / mee-skeleton}). If a primitive is missing, ESCALATE to frontend lead — do NOT bypass the abstraction wall." |
| **Build time > 90 s** | Frontend lead's PR review (pnpm build output) | "Previous build took {X}s, exceeding CLAUDE.md Decision 12 limit of 90s. Investigate: bundle chunk size, lazy-load boundaries, deferred imports. The smart-picker feature is lazy-loaded via app.routes.ts — confirm no eager import path leaked from a shared lib." |
| **403/429 on scraper run** | Data lead's PR review (scraper log) | "Previous scraper run triggered {403/429}. HALT — do NOT retry. Inter-lead memo to infra lead is required to discuss User-Agent rotation OR rate-limit relaxation. Bring evidence: full HTTP request/response from the failed attempt." |

### Maximum iteration cap

**Maximum 3 iterations per specialist before founder escalation.**

Rationale: AI iteration burns the daily ₹500 budget cap. A single Smart Picker recall eval at 50 descriptions × ~₹0.04/call ≈ ₹2 — but iterating 3 times across 3 specialists at peak (prompt-engineer + category-picker-builder + cross-deps) can sum to ₹10–20/day. 3 iterations × 8 specialists = up to ₹100/day on eval alone. Beyond 3 iterations is a signal that the feature spec, the architecture seam, or the agent's slice scope is wrong — and that's a founder decision, not an iteration loop.

Each lead tracks iteration count per specialist in their `feature_board_<domain>.md` Notes column. On the 4th iteration request: lead writes to `STATUS_MASTER.md` blockers section and pings the founder.

---

## Acceptance gate

This feature is "DONE" when ALL boxes are checked:

### Per-group merges (Step 1 per Master Plan §2.1)
- [ ] `feature/smart-picker/backend` → `feature/smart-picker` merged by backend lead.
- [ ] `feature/smart-picker/frontend` → `feature/smart-picker` merged by frontend lead.
- [ ] `feature/smart-picker/ai` → `feature/smart-picker` merged by AI lead.
- [ ] `feature/smart-picker/data` → `feature/smart-picker` merged by data lead (OR documented "no work needed" note from data lead).

### Integration tests on `feature/smart-picker` (Step 2 per Master Plan §2.2)
- [ ] `backend/tests/integration/test_smart_picker_integration.py` PASS — all 5 integration branches green.
- [ ] `backend/tests/modules/category/test_suggest_unit.py` PASS — all 5 unit test cases green per §9.J.
- [ ] `backend/tests/modules/category/test_trigram_p95.py` PASS — P95 < 200 ms.
- [ ] `backend/tests/eval/smart_picker/run_eval.py` PASS — top-5 recall ≥ 80%, per-call cost ≤ ₹0.05, Brier < 0.10.
- [ ] `frontend/src/app/features/smart-picker/**.spec.ts` PASS — all Vitest cases green.
- [ ] CI gates 1 + 2 + 3 + 4 + 5 all green on `feature/smart-picker`.
- [ ] `ai_eval` nightly job green within last 24h on `feature/smart-picker`.

### Feature flag posture (per D2)
- [ ] `FEATURE_SMART_PICKER_ENABLED` env var present in `backend/app/config.py`.
- [ ] Dev ConfigMap sets the flag to `true`.
- [ ] Staging ConfigMap sets the flag to `false`. (Founder flips to `true` AFTER 24h soak.)
- [ ] When disabled, the route returns 404 (integration test confirms).

### Documentation deliverables (per §4)
- [ ] All Backend / Frontend / AI / Data documentation items in §4 checked.

### Soak (post-merge to develop)
- [ ] 24-hour soak on `develop` (dev namespace) shows zero P0/P1 alerts on the `/suggest` route.
- [ ] LangFuse trace dashboard shows per-call cost averaging ≤ ₹0.05 over the 24h window.
- [ ] Eval re-runs within the 24h window confirm recall stayed ≥ 80%.

### Founder approval
- [ ] Founder approves the `feature/smart-picker` → `develop` PR opened by the AI lead.
- [ ] Founder flips `FEATURE_SMART_PICKER_ENABLED=true` on staging after 24h staging soak confirms recall + cost gates.

### Post-merge housekeeping
- [ ] `docs/V1_FEATURE_SPEC.md §F2` stamped "implemented YYYY-MM-DD" with PR link (follow-up doc PR).
- [ ] All 4 leads' `feature_board_<domain>.md` rows moved from Active to Recently merged.
- [ ] All 4 group branches deleted within 24h of merge per Master Plan §1.4.

---

## Risk register

Top 5 feature-specific risks. Each carries an owner + mitigation + escalation trigger.

| # | Risk | Owner | Mitigation | Escalation trigger |
|---|---|---|---|---|
| R1 | **Golden-set drift as Meesho category tree evolves.** A leaf renames, a super_id reorgs, or commission rates shift — the 50-description fixture's expected_top5 lists go stale; recall drops without anyone noticing until a real seller's flow breaks. | AI lead | Each `feature/smart-picker/data` refresh PR triggers an inter-lead memo to AI lead. AI lead re-runs the eval against the new tree, updates fixtures.json if a leaf renamed, re-baselines top-5 recall. Memory file `feature_smart_picker_drift_log.md` tracks every refresh × eval cycle. | Eval recall drops below 80% on the post-refresh re-run. |
| R2 | **ILIKE `/browse` fallback recall noticeably lower than the AI path → UX downgrade signal.** When `fallback_offered=true` fires and the seller clicks "Browse", the pg_trgm match for their description may not surface the right category — the seller feels punished for the AI being unavailable. | Backend lead + Frontend lead | The fallback path is `/browse?q=<original description>`; backend confirms pg_trgm + path/leaf/super-name GIN coverage matches the AI path's coverage breadth. Frontend's empty-state CTA copy frames it as "Browse all categories" (not "try the slow path") to set expectations. | Production telemetry shows >20% of fallback clicks bounce without selecting a category within 60 s. (V1: telemetry not in scope; manual review.) |
| R3 | **₹500 daily cap hits at peak hours → fallback storms.** Sellers concentrated in Tirupur evening hours can collectively burn the cap; every subsequent `/suggest` returns `fallback_offered=true` until midnight reset (Asia/Kolkata). The fallback CTA gets hammered, /browse latency may spike. | Backend lead + Infra lead | (1) The 100/h/user plan_guard cap upstream of the daily cap means per-user burn rate is bounded. (2) `/browse` is cached + GIN-indexed so the storm is absorbed. (3) Prometheus alarm at 80% daily spend (per §6A.F) warns the founder before the storm. | Daily 80% alarm fires twice in a single week → escalate to founder for cap increase or per-user throttle tightening. |
| R4 | **Tree compression breaks on new super-category additions.** Compression heuristic is calibrated to the current 3,772-leaf tree. A Meesho refresh adds a new super-category branch (e.g., "Pet supplies") with deep sub-tree; the compressor exceeds the 8 k token budget OR drops information about the new branch entirely, tanking recall on its descriptions. | AI lead (category-picker-builder) | After every data refresh that touches super-category count, category-picker-builder re-runs the compression on the new tree and reports the max token count. If > 8 k, the compression heuristic needs adjustment (drop lowest-traffic super-category sub-trees first). | Compression output exceeds 8 k tokens on the new tree. |
| R5 | **JSON-mode regression in Gemini 2.5 Flash → prompt rewrite.** Gemini periodically updates JSON-mode parsing behaviour. A model update could break the strict `{category_id, confidence, reasons}` parse, sending the response through the Layer 2 retry path until exhaustion. Visible signal: layer2_retries > 0 in the AIResponse field, recall drops, cost rises. | AI lead | (1) The `ai_ops/eval.py` runner reports layer2_retries per fixture — non-zero on more than 5% of fixtures is the early-warning signal. (2) prompt-engineer's iteration cycle includes a "JSON-mode soundness check" — if retries spike, downgrade the prompt to `response_mime_type='text/plain'` with explicit JSON instructions as a temporary hardening. (3) LangFuse dashboard surfaces the retry-rate metric. | layer2_retries > 0 on more than 10% of fixtures in a single eval run. |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-10 | mesell-smart-picker-planning-session-1 | Initial FEATURE_PLAN.md authored. Founder governance decisions G1–G4 locked (full lineup, planning-branch-now + group-branches-lazy, 4-part memory convention, FEATURE_PLAN.md mandatory read for active features). Founder scope decisions D1–D4 locked (arch-aligned scope with backend top-5 / frontend top-3 / graceful fallback to /browse, standard flag posture, Smart Picker ships first among AI features, frontend folder renames catalog-new → smart-picker). Agent lineup (7 mandatory + 1 conditional specialists across 4 leads), code surfaces (backend / frontend / AI / data / docs / CI), documentation deliverables, 8 specialist dispatch templates, review + iteration protocol (cross-group merge order, smart-picker-specific lead checks, 8 re-dispatch failure modes, 3-iteration cap), acceptance gate, and 5-item risk register all drafted. |
| v2 | 2026-06-10 | mesell-smart-picker-amendment-session-1 | Pattern conformance — Branch setup and Memory protocol added, ad-hoc sections relocated. Added ## Branch setup section (was missing): branch table, creation commands, PR flow, rebase strategy. Added ## Memory protocol section (absorbed MEMORY DISCIPLINE content): mandatory read list, cross-feature memo notes, naming convention, memory discipline subsection. Relocated ad-hoc ## ⚠️ Mandatory read declaration to preamble prose (before ## Decisions). Verified 11 canonical h2 headings in locked order. |
