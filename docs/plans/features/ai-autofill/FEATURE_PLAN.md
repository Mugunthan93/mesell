# Feature Plan — AI Auto-fill (V1 Feature 4)

| Field | Value |
|---|---|
| Status | DRAFT (pending founder PR review on `feature/ai-autofill/planning`) |
| Feature slug | `ai-autofill` |
| Spec source | `docs/V1_FEATURE_SPEC.md §F4` |
| Architecture sources | `docs/BACKEND_ARCHITECTURE.md §6A` (AI Operations Layer) · `§10` (catalog module) · `docs/FRONTEND_ARCHITECTURE.md` (catalog-form page) |
| Repo governance | `docs/plans/repo_management/MASTER_PLAN.md` (APPROVED) — §1 branches · §2 merge flow · §4 session naming · §5.4 AI PR template · §6 feature boards · §7 lead responsibilities |
| Inputs | `docs/plans/features/ai-autofill/PLANNING_DISPATCH.md` (the brief that drove this plan) |
| Prerequisites | `smart-picker` MERGED to `develop` (establishes ai_ops integration contract) · `catalog-form` MERGED to `develop` (lands the form page that hosts the autofill UI) |
| Authored by | `mesell-ai-autofill-planning-session-1` (master session) |
| Authored on | 2026-06-10 |
| Out of scope | Production code (no `*.py`, no `*.ts` outside this `.md` document) · Merging this PR (founder reviews) · Pre-creating feature/group branches (they get created at dispatch time per §B below) |

---

## Decisions

The three founder decisions D1/D2/D3 were locked in this planning session. Two structural resolutions (A/B/C) were also locked to address gaps the brief did not cover. All five answers verbatim:

### D1 — Scope confirmation
**Locked answer:** *Lock brief verbatim + housekeeping.*

The full scope, locked:
- Only **compulsory** fields populated (Recommended / Optional left blank — this is a hard guardrail against hallucination).
- Suggestion within **5 s P95**.
- All suggested values pass field-schema validation (enum / length / regex) — **0 % invalid-enum rate** per `BACKEND_ARCHITECTURE.md §6A.E`. Non-negotiable.
- **Yellow-highlight diff UI**; user accepts or edits per-field. User edits clear the highlight.
- **Idempotent re-run** replaces previous AI suggestions in `products.ai_suggestions_jsonb`.
- On invalid enum: drop that field with a logged warning. Do NOT lower the field's value. Do NOT hallucinate a substitute.
- On budget exhaustion (`BudgetExceededError`): return **HTTP 200** + `fallback_offered=true` + empty suggestions. UI shows "AI quota reached — please fill manually" toast (NOT an error).

**The key change from `§10` lock:** Autofill writes ONLY to `products.ai_suggestions_jsonb`. User-accept is the gate that writes to `products.fields_jsonb`. The `§10` auto-apply-at-0.85-confidence-floor behaviour is **retired for autofill**. (Auto-apply for other write paths is unaffected — this is autofill-specific.)

**Method name:** Keep `catalog.service.autofill_product(product_id)`. **MODIFY** the existing method body (do NOT add a parallel `autofill_from_description` method). Description is loaded from the DB via `product_id`; the user-facing flow is "type description → autosave debounce lands description → click AI fill" so the DB has the description by the time the route fires.

**Housekeeping:** `BACKEND_ARCHITECTURE.md §6A.F` text currently says "503 with i18n message `ai_ops.budget_exhausted`" for the autofill fallback. The implemented `§10` behaviour already returns 200 + `fallback_offered=true` (confirmed via `meesell-prompt-engineer` MEMORY: "catalog returns AutofillResponse(suggestions={}, applied={}, fallback_offered=True) HTTP 200 — symmetric with §9 smart_picker"). A small **housekeeping PR** (named `chore/§6A.F-text-housekeeping`, scope: doc-text-only) will update the `§6A.F` paragraph to match implemented reality. This PR is **independent** of ai-autofill feature delivery — listed under Follow-up actions below.

### D2 — Feature flag posture
**Locked answer:** *Confirm as proposed.*

- **Flag name:** `FEATURE_AI_AUTOFILL_ENABLED`
- **Dev default:** `true`
- **Staging default:** `false` until the golden eval set passes **0 % invalid-enum rate** AND per-call cost averages **≤ ₹0.05** in a **24-hour staging soak**.
- **Backend behaviour when disabled:** `POST /api/v1/products/{id}/autofill` returns **HTTP 404** per `MASTER_PLAN.md §3.2` backend rule.
- **Frontend behaviour when disabled:** `AutofillButtonComponent` is hidden in the catalog-form page via `FeatureFlagsService` (no skeleton, no disabled state — just not rendered).
- **Flag removal:** when the feature ships to `main` per `MASTER_PLAN.md §3.2` debt rule (carrying a flag past one release is a debt item).

### D3 — Priority ordering vs sibling features
**Locked answer:** *Lock as proposed.*

`ai-autofill` ships **AFTER** both `smart-picker` AND `catalog-form` merge to `develop`.
- `smart-picker` MERGED is the gate for AI-side dispatch (ai_ops contract is stable).
- `catalog-form` MERGED is the gate for BE+FE dispatch (the form page that hosts the autofill UI exists; `catalog.service.autofill_product` exists from `§10` and only needs MODIFY).
- After both prerequisites land, `ai-autofill` may run **in parallel** with `image-precheck`. No shared file contention between those two features.

### A — Lead/Agent assignment lockdown
**Locked answer:** *Lock the canonical lineup; no other agents touch ai-autofill.*

(See "Agent lineup" section below for the table.)

### B — Branch lifecycle for this feature
**Locked answer:** *Lock the sequence; no pre-creation of feature/group branches in this planning session.*

(See "Branch setup" section below.)

### C — Cross-feature memory protocol
**Locked answer:** *Lock the 3-mechanism protocol (feature-tagged session entries + per-agent register + one-shot broadcast).*

A follow-up PR will amend `MASTER_PLAN.md §6` and `§7` so the pattern applies uniformly to all 9 V1 features. (See "Cross-feature memory protocol" section below.)

---

## Agent lineup

The 4 leads and 5 specialists (1 conditional) listed below are the **canonical lineup** for ai-autofill. No other agent in the 18-agent fleet may modify code under the ai-autofill code surfaces. Specifically out of scope and forbidden to touch ai-autofill files: `meesell-database-builder`, `meesell-auth-builder`, `meesell-infra-builder`, `meesell-angular-ui-styler`, `meesell-legal-writer`, `meesell-category-picker-builder`, `meesell-image-precheck-builder`, `meesell-scraper-maintainer`. If any of those agents is mistakenly asked to act on ai-autofill, they refuse with "defer to `meesell-<correct-role>`".

| Lead | Specialist | What they own for ai-autofill |
|---|---|---|
| `meesell-backend-coordinator` | `meesell-services-builder` | MODIFY `app/modules/catalog/service.py::autofill_product` body — load description from DB, call `ai_ops.client.call_gemini("autofill.v1", ctx, prompt_vars, allowed_enums=...)`, apply Layer 2 enum re-validation via the up-to-2-retry loop inside `call_gemini` per `§6A.C`, write per-field suggestions to `products.ai_suggestions_jsonb`, NEVER write to `products.fields_jsonb`, return `AutofillResponse(suggestions={...}, dropped_fields=[...], fallback_offered=False)` on success or `AutofillResponse(suggestions={}, dropped_fields=[], fallback_offered=True)` on `BudgetExceededError`. Remove the existing `§10` auto-apply path. Add unit tests in `backend/tests/test_catalog_unit.py` with mocked `ai_ops`. |
| `meesell-backend-coordinator` | `meesell-api-routes-builder` | ADD `POST /api/v1/products/{id}/autofill` route in `app/modules/catalog/routes.py`. ADD `AutofillRequest`, `AutofillResponse`, and `DroppedField` Pydantic v2 schemas in `app/modules/catalog/schemas.py`. Enforce `FEATURE_AI_AUTOFILL_ENABLED` flag (route returns 404 when disabled). Wire route to `catalog.service.autofill_product`. Add integration test in `backend/tests/test_ai_autofill_integration.py`. OpenAPI description MUST explicitly call out the "success with fallback_offered=true" shape. |
| `meesell-frontend-coordinator` | `meesell-angular-component-builder` | NEW `AutofillButtonComponent` and `FieldDiffComponent` under `frontend/src/app/pages/catalog-form/autofill/`. Wire `AutofillButton` into the catalog-form layout (MODIFY `catalog-form.component.ts`). Render `FieldDiff` per compulsory field that has an AI suggestion. Loading spinner during fetch. Toast on `fallback_offered=true` ("AI quota reached — please fill manually") — NOT treated as error. Per-field yellow highlight from `ai_suggestions_jsonb`; clears on user edit; accept/edit affordances. NEW spec at `frontend/src/app/pages/catalog-form/autofill/autofill.spec.ts`. |
| `meesell-frontend-coordinator` | `meesell-angular-service-builder` | MODIFY `frontend/src/app/services/catalog.service.ts` — ADD `autofill(productId: string): Observable<AutofillResponse>` method wrapping `HttpClient` POST to `/api/v1/products/{id}/autofill`. Error handler treats `fallback_offered=true` as a SUCCESS signal (drives toast in component, NOT an `error()` callback). Type the return shape against the backend `AutofillResponse` schema. Idempotent re-run replaces previous suggestions in component state via `BehaviorSubject` reset. |
| `meesell-ai-coordinator` | `meesell-prompt-engineer` | NEW `backend/app/ai_ops/prompts/autofill_v1.py` — `TEMPLATE` body refined from the V1 baseline draft per prompt-engineer MEMORY. Few-shot examples covering 5 high-traffic super-categories with enum-strict outputs. Output schema matches `AutofillResponse`. Explicit "leave field blank if unsure" instruction (anti-hallucination). NEW golden set at `tests/eval/autofill/golden_set.json` (≥30 hand-labeled `{description, category_id, expected_fields, expected_dropped}` pairs; target 50 for headroom). NEW eval runners: `tests/eval/autofill/test_enum_validity.py` (gates **0 % invalid-enum** — non-negotiable) and `tests/eval/autofill/test_recall.py` (informational — compulsory-field recall target ≥ 70 %). VERIFY `ai_ops/client.py` workload Literal includes `"autofill"` (added by `§6A` construction); MODIFY only if missing. `meesell-category-picker-builder` is NOT involved. |
| `meesell-data-engineer` | `meesell-xlsx-parser` *(CONDITIONAL)* | **ONLY** if `tests/eval/autofill/test_enum_validity.py` surfaces invalid-enum hits traceable to stale entries in `backend/app/data/field_aliases.json`. Refresh the affected `enum_values` from the latest Meesho XLSX source. Default expectation: no work — the `field_aliases` seed is stable. If triggered, the dispatch follows the conditional template under "Dispatch templates" below. |

**Lead approval chain (per `MASTER_PLAN.md §2.1`):** Each specialist's PR on `feature/ai-autofill/{group}` → `feature/ai-autofill` is reviewed and merged by **the group's lead**. The aggregated `feature/ai-autofill` → `develop` PR is reviewed and merged by the **founder** per `MASTER_PLAN.md §2.2`. The founder is the sole reviewer at the integration layer; leads are the sole reviewers at the group layer.

---

## Code surfaces

Every file the feature will create (NEW) or modify (MODIFY), grouped by domain. This becomes the diff scope when leads brief specialists; specialists MUST NOT touch files outside this list.

### Backend
| File | Disposition | Owner | Notes |
|---|---|---|---|
| `backend/app/modules/catalog/routes.py` | MODIFY | api-routes-builder | ADD `/autofill` route only. catalog-form dispatch already added the other 4 catalog routes. |
| `backend/app/modules/catalog/schemas.py` | MODIFY | api-routes-builder | ADD `AutofillRequest`, `AutofillResponse`, `DroppedField` shapes. |
| `backend/app/modules/catalog/service.py` | MODIFY | services-builder | MODIFY `autofill_product` body only. The `§10` auto-apply path is removed. Other catalog service methods are NOT touched. |
| `backend/app/ai_ops/client.py` | VERIFY (likely NO-CHANGE) | prompt-engineer | Read first. `§6A` construction added `"autofill"` to the workload Literal. MODIFY only if missing. |
| `backend/app/ai_ops/prompts/autofill_v1.py` | NEW (or MODIFY of baseline draft) | prompt-engineer | Per `prompt-engineer` MEMORY a V1 baseline draft exists (authored by services-builder during `§6A` construction for storage integration). prompt-engineer iterates the TEMPLATE body and few-shot bank to pass eval gates. |
| `backend/tests/test_catalog_unit.py` | MODIFY | services-builder | ADD `autofill_product` service tests with mocked `ai_ops.client`. Cover happy path, dropped-field path, `fallback_offered=true` path, idempotent re-run path. |
| `backend/tests/test_ai_autofill_integration.py` | NEW | api-routes-builder | End-to-end route test with `ai_ops` mocked at the adapter boundary. Cover 200 success, 200 fallback, 404 flag-disabled. |
| `tests/eval/autofill/golden_set.json` | NEW | prompt-engineer | ≥30 fixtures (target 50). Schema: `{description, category_id, expected_fields: {canonical: value}, expected_dropped: [canonical]}`. |
| `tests/eval/autofill/test_enum_validity.py` | NEW | prompt-engineer | Gates **0 % invalid-enum rate**. CI gate `ai_eval` (nightly) includes this. |
| `tests/eval/autofill/test_recall.py` | NEW (informational) | prompt-engineer | Reports compulsory-field recall. Target ≥ 70 % — informational only (no CI gate). |

### Frontend
| File | Disposition | Owner | Notes |
|---|---|---|---|
| `frontend/src/app/pages/catalog-form/autofill/autofill-button.component.ts` | NEW | angular-component-builder | Standalone, OnPush. Loading state. Emits `(triggered)` event consumed by `CatalogFormComponent`. |
| `frontend/src/app/pages/catalog-form/autofill/field-diff.component.ts` | NEW | angular-component-builder | Standalone, OnPush. Inputs: `suggestion`, `currentValue`. Outputs: `(accept)`, `(reject)`. Yellow highlight on suggestion present, clears on user edit. |
| `frontend/src/app/pages/catalog-form/catalog-form.component.ts` | MODIFY | angular-component-builder | Mount `AutofillButton` in form header area. Render `FieldDiff` per compulsory field with an `ai_suggestions_jsonb` entry. Wire `(triggered)` to `CatalogService.autofill(productId)`. |
| `frontend/src/app/services/catalog.service.ts` | MODIFY | angular-service-builder | ADD `autofill(productId: string): Observable<AutofillResponse>`. Type the response. Treat `fallback_offered=true` as success → component displays toast. |
| `frontend/src/app/pages/catalog-form/autofill/autofill.spec.ts` | NEW | angular-component-builder | Karma+Jasmine spec covering the 4 UI scenarios: empty, suggestions present, user edit clears highlight, fallback toast. |

### AI
| File | Disposition | Owner | Notes |
|---|---|---|---|
| `backend/app/ai_ops/prompts/autofill_v1.py` | NEW (or MODIFY) | prompt-engineer | See Backend table above. |
| `tests/eval/autofill/golden_set.json` | NEW | prompt-engineer | See Backend table above. |
| `tests/eval/autofill/test_enum_validity.py` | NEW | prompt-engineer | See Backend table above. |
| `tests/eval/autofill/test_recall.py` | NEW | prompt-engineer | See Backend table above. |

### Data
| File | Disposition | Owner | Notes |
|---|---|---|---|
| `backend/app/data/field_aliases.json` | MODIFY *(CONDITIONAL)* | xlsx-parser | ONLY if eval surfaces invalid-enum hits caused by stale `enum_values`. Default: no work. |

### Infra
None. No new secrets — `GEMINI_API_KEY` + budget are already provisioned. No new ingress paths (the `/autofill` route is mounted under the existing `/api/v1/products` prefix). No new K8s manifests.

### Docs
| File | Disposition | Owner | Notes |
|---|---|---|---|
| `docs/V1_FEATURE_SPEC.md §F4` | MODIFY (status stamp) | backend lead at feature-PR merge | Add "implemented YYYY-MM-DD" stamp with PR link after `feature/ai-autofill` → `develop` merges. |
| `docs/BACKEND_ARCHITECTURE.md §6A.F` | NOT modified by this feature | — | The `§6A.F` doc-text-housekeeping (503 → 200+fallback) is a SEPARATE PR (see Follow-up actions). Not in this feature's diff scope. |
| `tests/eval/README.md` | MODIFY (one line) | prompt-engineer | Add entry pointing at `tests/eval/autofill/` alongside the smart-picker entry. |

---

## Documentation deliverables

Every item below MUST exist alongside the merged code before the `feature/ai-autofill` → `develop` PR is approved. These become acceptance gate items.

### Backend
- **OpenAPI entry** for `POST /api/v1/products/{id}/autofill`:
  - Request: `AutofillRequest { /* may be empty body; product_id from path */ }` (with optional `category_id` override field reserved for V1.5 — explicitly marked deprecated-on-arrival in V1 to lock the seam).
  - Response: `AutofillResponse { suggestions: { canonical: value }, dropped_fields: [DroppedField { canonical, reason }], fallback_offered: bool }`.
  - Status codes: `200` (success — including `fallback_offered=true` on budget exhaustion), `400` (invalid request), `403` (plan_guard hourly limit hit — distinct from budget cap), `404` (product not found OR `FEATURE_AI_AUTOFILL_ENABLED=false`), `422` (category schema missing). Explicit OpenAPI description note: "On budget exhaustion, this endpoint returns 200 with `fallback_offered=true` — clients MUST handle as success, not error."
- **`autofill_product` docstring** in `catalog/service.py`: documents the user-accept-gate invariant ("writes only to `ai_suggestions_jsonb`; never to `fields_jsonb`"), the Layer 2 retry semantics ("up to 2 retries on enum violations, then drop"), and the budget-fallback shape.

### Frontend
- **`AutofillButtonComponent` docstring** describing loading state lifecycle, the `(triggered)` event contract, and the `fallback_offered=true` toast handling (cite the i18n key for the toast text).
- **`FieldDiffComponent` docstring** on accept/edit per-field semantics and the yellow-highlight-on-suggestion / clear-on-edit cycle. Cite the design token for the yellow highlight (must reuse an existing token — no new tokens added).
- **`CatalogService.autofill` JSDoc**: documents the success-with-fallback contract and that callers MUST NOT treat `fallback_offered=true` as error.

### AI
- **Prompt registry entry**: `autofill.v1` registered via the existing `ai_ops/prompt_registry.py` dynamic-import resolver. Prompt-engineer confirms the 4 required constants (`TEMPLATE`, `VERSION`, `WORKLOAD`, `RENDERED_BY`) are present and match the workload Literal `"autofill"`.
- **Golden set fixture documentation**: a one-paragraph entry in `tests/eval/README.md` describing the fixture schema, the 0 %-invalid-enum gate, the informational recall target, and the local-run command.
- **`autofill_v1.py` header comment** documenting Layer 1 prefix bonding (which lives in `guardrail.py` — referenced, not duplicated) and the up-to-2-retry Layer 2 contract.
- **`ai_eval` CI gate extension**: confirm `.github/workflows/ci.yml` includes `pytest tests/eval/autofill/` in its `ai_eval` nightly job (smart-picker's PR adds the gate; this feature confirms it covers autofill).

### Data
- IF `xlsx-parser` is triggered: a one-paragraph entry in `meesell-data-engineer` MEMORY noting the version bump on `field_aliases.json` and the affected categories.

### Cross-cutting
- **`docs/V1_FEATURE_SPEC.md §F4`** stamped "implemented YYYY-MM-DD" with the feature PR link.
- **No** modification to `MASTER_PLAN.md` from this feature — the `§6/§7` amendment (resolution C) is a SEPARATE PR.

---

## Branch setup

This planning session creates exactly ONE branch. All other branches in the ai-autofill family are created later, by the relevant lead, at dispatch time.

### Created in this planning session
| Branch | Parent | Purpose | Lifetime |
|---|---|---|---|
| `feature/ai-autofill/planning` | `origin/develop` | Carries this `FEATURE_PLAN.md`. Merges to `develop` after founder review. | Deleted 24 h after planning PR merges. |

### Created LATER (NOT in this session)
| Order | Branch | Parent | Created by | Created when | Lifetime |
|---|---|---|---|---|---|
| 1 | `feature/ai-autofill` | `develop` | Founder OR the first lead to dispatch | **AFTER** `smart-picker` AND `catalog-form` both merge to `develop` per D3 | Deleted 24 h after `feature/ai-autofill` → `develop` PR merges |
| 2 | `feature/ai-autofill/ai` | `feature/ai-autofill` | `meesell-ai-coordinator` | When AI lead dispatches `prompt-engineer` (can run first, decoupled from BE/FE in calendar but not in merge order) | Deleted 24 h after group PR merges |
| 3 | `feature/ai-autofill/backend` | `feature/ai-autofill` | `meesell-backend-coordinator` | When backend lead dispatches `services-builder` and/or `api-routes-builder` | Deleted 24 h after group PR merges |
| 4 | `feature/ai-autofill/frontend` | `feature/ai-autofill` | `meesell-frontend-coordinator` | When frontend lead dispatches `angular-component-builder` and/or `angular-service-builder` | Deleted 24 h after group PR merges |
| 5 | `feature/ai-autofill/data` *(CONDITIONAL)* | `feature/ai-autofill` | `meesell-data-engineer` | ONLY if `xlsx-parser` is triggered by enum drift in eval | Deleted 24 h after group PR merges |

**Group-PR merge order to `feature/ai-autofill`:** No strict order required between BE / FE / AI groups. The `feature/ai-autofill` → `develop` integration PR is gated on ALL three (plus data if triggered) having merged to `feature/ai-autofill` per `MASTER_PLAN.md §2.5`.

**Slug discipline:** `ai-autofill` is the locked slug. Never `ai_autofill`, `aiautofill`, `autofill`, `ai-auto-fill`. Session names, branch names, file paths, board entries, and PR titles all use `ai-autofill`.

---

## Memory protocol

### Required reads at coding-session start

Memories leads MUST read at coding-session start:
- `.claude/agent-memory/meesell-ai-coordinator/MEMORY.md`
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md`
- `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md`
- `.claude/agent-memory/meesell-data-engineer/MEMORY.md`

### Cross-feature memo contracts

- ai-autofill consumes the category tree contract from `smart-picker` — the `ai_ops` integration contract (workload Literal, allowed_enums shape) established by smart-picker is the dependency gate for the AI lead dispatch.
- ai-autofill consumes the catalog-form page surface from `catalog-form` — the `catalog-form.component.ts` mounting point and the `CatalogService` base class shape from catalog-form are required before frontend specialists can build autofill wiring.

### Naming convention for new memos

Naming convention for new memos created during this feature: `ai_autofill_feature.md` (under each specialist agent's memory directory, e.g. `.claude/agent-memory/meesell-services-builder/ai_autofill_feature.md`).

### Cross-feature memory protocol (mechanisms)

This protocol applies to every specialist dispatched on ai-autofill. It will be promoted to a `MASTER_PLAN.md` amendment after this planning PR merges so it applies uniformly to all 9 V1 features (resolution C ratified by founder in this session).

#### Mechanism 1 — Feature-tagged session entries (MANDATORY)

Every session entry appended to an agent's `MEMORY.md` MUST begin with this exact header:

```markdown
## Session mesell-ai-autofill-{group}-session-{N} — YYYY-MM-DD
**Feature:** ai-autofill
**My slice:** <one-line description of this session's specific work>
**Branch:** feature/ai-autofill/{group}
**PR:** #<num> (filled in at PR-open time)

### What I did
- ...

### What I learned
- ...

### Pointers for future sessions on ai-autofill
- ...
```

Rationale: `grep "Feature: ai-autofill" .claude/agent-memory/meesell-*/MEMORY.md` returns every entry across the fleet that touched this feature. Attribution is mechanical, not interpretive.

#### Mechanism 2 — "Features I'm involved in" register

Each involved agent's `MEMORY.md` gets a top-level register table, updated whenever the agent is newly dispatched on a feature or a feature's status changes. The register must appear ABOVE the session-entries list. Format:

```markdown
## Features I'm involved in
| Feature | My slice | Branch pattern | Plan | Status |
|---|---|---|---|---|
| smart-picker | <slice> | feature/smart-picker/{group} | docs/plans/features/smart-picker/FEATURE_PLAN.md | <Status> |
| catalog-form | <slice> | feature/catalog-form/{group} | docs/plans/features/catalog-form/FEATURE_PLAN.md | <Status> |
| ai-autofill | <slice> | feature/ai-autofill/{group} | docs/plans/features/ai-autofill/FEATURE_PLAN.md | <Status> |
```

The agent reads this register at session start. Status values follow `MASTER_PLAN.md §6.3`: `PENDING · IN PROGRESS · IN REVIEW · MERGED · BLOCKED`.

#### Mechanism 3 — One-shot fan-out broadcast at planning-PR merge

When the founder merges this planning PR to `develop`, a **single broadcast pass** writes a short feature-register stub to **every agent in the 18-agent fleet** — both involved and not-involved. The broadcast is the FIRST action listed under Acceptance gate below.

For involved agents, the stub:

```markdown
## Feature register entry — ai-autofill (broadcast YYYY-MM-DD)
- Spec: docs/V1_FEATURE_SPEC.md §F4
- Plan: docs/plans/features/ai-autofill/FEATURE_PLAN.md
- My role: <slice>
- Branch pattern: feature/ai-autofill/{group}
- Sibling features currently in flight: smart-picker, catalog-form, image-precheck
- I will be dispatched when: <prerequisite from D3>
- I will NOT be dispatched if: <out-of-scope trigger>
```

For NOT-involved agents (e.g. `meesell-database-builder`, `meesell-auth-builder`, `meesell-infra-builder`, `meesell-angular-ui-styler`, `meesell-legal-writer`, `meesell-category-picker-builder`, `meesell-image-precheck-builder`, `meesell-scraper-maintainer`), the stub:

```markdown
## Feature register entry — ai-autofill (broadcast YYYY-MM-DD)
- Spec: docs/V1_FEATURE_SPEC.md §F4
- Plan: docs/plans/features/ai-autofill/FEATURE_PLAN.md
- My role: NONE — I am NOT involved in ai-autofill. Refuse with "defer to meesell-<correct-role>" if asked.
```

#### Read protocol at session start (for every involved specialist)

1. Read this `FEATURE_PLAN.md` in full.
2. Read own `MEMORY.md` — scan ONLY entries tagged `Feature: ai-autofill` plus general/reference entries. Ignore other-feature entries unless cross-cutting.
3. Read the "Features I'm involved in" register at top of own `MEMORY.md`.
4. Read the lead's `docs/status/feature_board_<domain>.md` to see all active features the lead is touching.
5. Read sibling-specialist `MEMORY.md` files referenced in the dispatch template's Mandatory reads list (filtered the same way — only `Feature: ai-autofill` plus general entries).

#### Write protocol at session close (for every involved specialist)

1. Append the Mechanism 1 session entry with mandatory header to own `MEMORY.md`.
2. Update the Mechanism 2 register row for ai-autofill.
3. Update the lead's `feature_board_<domain>.md` row per `MASTER_PLAN.md §6.5`.
4. Confirm 1+2+3 in the final report (it is a check-list item in every dispatch template).

---

## Dispatch templates

Five reusable dispatch templates below. The lead pastes one of these into an `Agent()` dispatch with the `{N}` session number filled in. Each template includes the PROJECT BOUNDARY block, the SESSION header, mandatory reads, acceptance criteria, hard constraints, files in/out of scope, the final report format, and the cross-feature memory protocol session-close.

### Dispatch template — `meesell-services-builder` (backend)

```
SESSION: mesell-ai-autofill-backend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Your mission
MODIFY the existing `catalog.service.autofill_product(product_id)` method to satisfy V1 §F4 ai-autofill acceptance: writes ONLY to `products.ai_suggestions_jsonb`, applies up-to-2 Layer 2 enum re-validation retries via `ai_ops.client.call_gemini`, drops fields that fail after retries with a logged warning, returns `AutofillResponse` with per-field suggestions + dropped fields + `fallback_offered` flag. The existing §10 auto-apply path is REMOVED for autofill.

## Mandatory reads (in this order)
- docs/V1_FEATURE_SPEC.md §F4
- docs/BACKEND_ARCHITECTURE.md §6A.C (Layer 2 enum re-validation + up-to-2 retries)
- docs/BACKEND_ARCHITECTURE.md §6A.F (budget cap + graceful fallback; note: §6A.F text says 503 but catalog returns 200+fallback_offered=true — the implemented behaviour is canonical)
- docs/BACKEND_ARCHITECTURE.md §10 (catalog module surface; the autofill seam)
- docs/plans/features/ai-autofill/FEATURE_PLAN.md (this plan — your single source of truth)
- .claude/agent-memory/meesell-services-builder/MEMORY.md — scan only entries tagged "Feature: ai-autofill" + general/reference entries; ignore other-feature entries
- .claude/agent-memory/meesell-prompt-engineer/MEMORY.md — the §10 catalog autofill.v1 consumption entry for the {{product_spec}}/{{schema}} contract
- docs/status/feature_board_backend.md — see all features the backend lead is currently touching
- The smart-picker services-builder PR diff (when it exists) as the REFERENCE implementation for ai_ops.client integration pattern
- The existing `app/modules/catalog/service.py::autofill_product` body — read in full before modifying

## Acceptance criteria
- `autofill_product(product_id, user_id)` signature retained; description loaded from DB by product_id (do NOT add a `description` parameter)
- Calls `ai_ops.client.call_gemini` with workload `"autofill"`, `prompt_id="autofill.v1"`, and `allowed_enums` populated from `category.service.fetch_schema(product.category_id)`
- Applies the §6A.C up-to-2 Layer 2 retries (these happen INSIDE `call_gemini`; service-side just consumes `AIResponse.layer2_retries`)
- On `AIResponse.parsed.fields` empty AND `fallback_offered=True` → returns `AutofillResponse(suggestions={}, dropped_fields=[], fallback_offered=True)` HTTP 200 — NOT 503
- On Layer 2 final-failure for a specific field → drops the field from suggestions; adds entry to `dropped_fields` with `reason="invalid_enum_after_retries"`; emits structured log warning
- Writes per-field suggestions to `products.ai_suggestions_jsonb` (UPSERT shape — replaces previous entry for the same canonical name; idempotent re-run)
- DOES NOT write to `products.fields_jsonb` (user-accept is the gate; that path lives in `catalog.service.accept_suggestion` per existing §10)
- The §10 auto-apply branch is REMOVED from this method
- 5 s P95 latency target on a single-product autofill (validated in integration test below)
- Unit tests in `backend/tests/test_catalog_unit.py`: happy path · dropped-field path · fallback path · idempotent re-run path · auto-apply-NOT-fired regression test

## Hard constraints
- NO direct import of `adapters/gemini.py` — ONLY `ai_ops.client.call_gemini`
- NO writes to `products.fields_jsonb` from this method — never
- NO hallucinated enum values — fail-closed by dropping the field
- NO new method `autofill_from_description` — MODIFY existing `autofill_product`
- NO 503 on budget exhaustion — must be 200 + `fallback_offered=true`
- The §10 auto-apply-at-0.85-floor path MUST be removed from this method (and only this method — other §10 service methods retain their existing auto-apply behaviour)

## Files you may touch
- backend/app/modules/catalog/service.py (autofill_product method only)
- backend/tests/test_catalog_unit.py (autofill test additions)

## Files you MUST NOT touch
- Any other method in catalog/service.py
- backend/app/modules/catalog/routes.py (api-routes-builder owns)
- backend/app/modules/catalog/schemas.py (api-routes-builder owns)
- backend/app/ai_ops/* (NOT yours; prompt-engineer owns prompts/autofill_v1.py)
- backend/app/adapters/* (vendor isolation boundary)
- Any frontend file
- Any other feature's planning dir under docs/plans/features/

## Final report format
| Metric | Value | Target | Status |
|---|---|---|---|
| Per-call cost (₹, avg) | <X.XX> | ≤ 0.05 | ✅/❌ |
| P95 latency (ms) | <XXX> | ≤ 5000 | ✅/❌ |
| Invalid-enum rate (from eval set passthrough) | <X> % | 0 % | ✅/❌ |
| Compulsory-field recall | <XX> % | ≥ 70 % informational | — |
| Auto-apply removed (regression test) | yes/no | yes | ✅/❌ |
| §10 other-method behaviour preserved | yes/no | yes | ✅/❌ |

## Session close — cross-feature memory protocol (MANDATORY)
1. Append a `## Session mesell-ai-autofill-backend-session-{N} — YYYY-MM-DD` entry to your MEMORY.md with header line `**Feature:** ai-autofill`, `**My slice:** services-builder MODIFY autofill_product`, `**Branch:** feature/ai-autofill/backend`, `**PR:** #<num>`
2. Update your "Features I'm involved in" register row for ai-autofill with new Status
3. Confirm both updates in your final report
```

### Dispatch template — `meesell-api-routes-builder` (backend)

```
SESSION: mesell-ai-autofill-backend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Your mission
ADD the `POST /api/v1/products/{id}/autofill` route in `app/modules/catalog/routes.py` and ADD `AutofillRequest`, `AutofillResponse`, `DroppedField` Pydantic v2 schemas in `app/modules/catalog/schemas.py`. Enforce `FEATURE_AI_AUTOFILL_ENABLED` flag (route returns 404 when disabled). Wire route to `catalog.service.autofill_product`. Write the integration test.

## Mandatory reads (in this order)
- docs/V1_FEATURE_SPEC.md §F4
- docs/BACKEND_ARCHITECTURE.md §10 (catalog router structure)
- docs/BACKEND_ARCHITECTURE.md §6A.F (budget cap fallback — note 200+fallback_offered=true is canonical despite §6A.F text saying 503)
- docs/plans/repo_management/MASTER_PLAN.md §3.2 (404 on disabled feature flag)
- docs/plans/repo_management/MASTER_PLAN.md §5.2 (Backend PR template)
- docs/plans/features/ai-autofill/FEATURE_PLAN.md (this plan)
- .claude/agent-memory/meesell-api-routes-builder/MEMORY.md — scan only ai-autofill-tagged + general/reference entries
- .claude/agent-memory/meesell-services-builder/MEMORY.md — to confirm the autofill_product signature you are wiring to
- docs/status/feature_board_backend.md

## Acceptance criteria
- Route: `POST /api/v1/products/{id}/autofill` with path param `id: UUID`, empty body allowed
- Returns `AutofillResponse` on success (HTTP 200)
- Returns `AutofillResponse(suggestions={}, dropped_fields=[], fallback_offered=True)` on `BudgetExceededError` from service — HTTP 200, NOT 503
- Returns HTTP 404 when `settings.FEATURE_AI_AUTOFILL_ENABLED == False`
- Returns HTTP 404 when product does not exist OR belongs to a different user
- Returns HTTP 403 when `core/plan_guard.py::enforce_plan_limit("ai_autofill")` raises (hourly cap)
- Returns HTTP 422 when category schema is missing for the product's category
- OpenAPI generated; description explicitly notes the success-with-fallback shape
- Integration test `backend/tests/test_ai_autofill_integration.py` covers: 200 success · 200 fallback · 404 flag-disabled · 404 product-not-found · 403 plan-guard · 422 schema-missing
- AutofillResponse schema: `{ suggestions: dict[str, Any], dropped_fields: list[DroppedField], fallback_offered: bool }` where `DroppedField = { canonical: str, reason: str }`

## Hard constraints
- NO bypass of services layer — route MUST call `catalog.service.autofill_product`
- NO 503 anywhere in this route — budget exhaustion returns 200 + fallback_offered=true
- NO new method names — service method is `autofill_product`, route path is `/autofill`
- NO logic in the route beyond auth/flag/schema-fetch — keep the route thin
- Plan-guard MUST run BEFORE the service call (per §4 middleware order)

## Files you may touch
- backend/app/modules/catalog/routes.py (ADD autofill route only)
- backend/app/modules/catalog/schemas.py (ADD AutofillRequest, AutofillResponse, DroppedField)
- backend/tests/test_ai_autofill_integration.py (NEW)
- backend/app/config.py (ADD FEATURE_AI_AUTOFILL_ENABLED to Settings if not yet present)

## Files you MUST NOT touch
- catalog/service.py body (services-builder owns)
- Any other route or schema
- Any ai_ops/* file
- Any frontend file

## Final report format
| Metric | Value | Target | Status |
|---|---|---|---|
| OpenAPI generated | yes/no | yes | ✅/❌ |
| 200 success path test | pass/fail | pass | ✅/❌ |
| 200 fallback_offered path test | pass/fail | pass | ✅/❌ |
| 404 flag-disabled test | pass/fail | pass | ✅/❌ |
| 403 plan-guard test | pass/fail | pass | ✅/❌ |
| 422 schema-missing test | pass/fail | pass | ✅/❌ |
| Route latency P95 (ms) | <XXX> | ≤ 5000 | ✅/❌ |

## Session close — cross-feature memory protocol (MANDATORY)
1. Append `## Session mesell-ai-autofill-backend-session-{N}` entry to MEMORY.md with feature attribution header
2. Update "Features I'm involved in" register
3. Confirm both in final report
```

### Dispatch template — `meesell-angular-component-builder` (frontend)

```
SESSION: mesell-ai-autofill-frontend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Your mission
Build `AutofillButtonComponent` and `FieldDiffComponent` under `frontend/src/app/pages/catalog-form/autofill/`. Wire the button into the catalog-form layout and render a FieldDiff per compulsory field that has an AI suggestion. Loading state, fallback toast, yellow highlight on suggestion present, clear on user edit.

## Mandatory reads (in this order)
- docs/V1_FEATURE_SPEC.md §F4
- docs/FRONTEND_ARCHITECTURE.md (catalog-form page section; ui-kit primitives section)
- docs/plans/repo_management/MASTER_PLAN.md §5.3 (Frontend PR template)
- docs/plans/features/ai-autofill/FEATURE_PLAN.md (this plan)
- .claude/agent-memory/meesell-angular-component-builder/MEMORY.md — scan ai-autofill-tagged + general/reference entries
- .claude/agent-memory/meesell-angular-service-builder/MEMORY.md — to confirm CatalogService.autofill signature you are calling
- docs/status/feature_board_frontend.md
- The existing catalog-form.component.ts file in full (catalog-form dispatch landed it; you wire INTO it)

## Acceptance criteria
- `AutofillButtonComponent` (standalone, OnPush) with `@Input() productId: string`, `@Input() loading: boolean`, `@Output() triggered = new EventEmitter<void>()`
- `FieldDiffComponent` (standalone, OnPush) with `@Input() canonicalName: string`, `@Input() suggestion: any`, `@Input() currentValue: any`, `@Output() accept = new EventEmitter<any>()`, `@Output() reject = new EventEmitter<void>()`
- Yellow highlight on FieldDiff when `suggestion !== undefined`; clears when user edits the field value (handled via parent component's value-change subscription, NOT internal state)
- AutofillButton shows mat-spinner while `loading=true`
- On `fallback_offered=true` from CatalogService.autofill: parent component opens MatSnackBar with i18n key `ai.quota.exhausted` — NOT treated as error
- catalog-form.component.ts MODIFIED to: mount AutofillButton in form header · subscribe to autofill() · render FieldDiff per compulsory field with `ai_suggestions_jsonb[canonical]` populated · clear `ai_suggestions_jsonb[canonical]` on user edit of that field
- spec.ts covers: empty state · suggestions present · user edit clears highlight · fallback toast appears
- Build < 90 s (CLAUDE.md Decision 12)
- Bundle delta < +20 KB
- Screenshots at 360 px and 1280 px in PR
- Tailwind utility classes only — no inline styles, no new design tokens

## Hard constraints
- NO direct `fetch()` or `HttpClient` call — MUST go through `CatalogService.autofill`
- NO error toast on `fallback_offered=true` — that is a success path with a notification
- NO internal state mutation that bypasses `ai_suggestions_jsonb` shape from backend
- NO new design tokens — reuse existing yellow-highlight token
- Standalone components only — no NgModule
- OnPush change detection mandatory

## Files you may touch
- frontend/src/app/pages/catalog-form/autofill/autofill-button.component.ts (NEW)
- frontend/src/app/pages/catalog-form/autofill/field-diff.component.ts (NEW)
- frontend/src/app/pages/catalog-form/autofill/autofill.spec.ts (NEW)
- frontend/src/app/pages/catalog-form/catalog-form.component.ts (MODIFY — wire AutofillButton + FieldDiff)

## Files you MUST NOT touch
- frontend/src/app/services/catalog.service.ts (service-builder owns)
- frontend/src/app/services/* (any other service)
- frontend/src/app/ui/* (ui-kit primitives — boundary)
- Any backend file
- Any other page component

## Final report format
| Metric | Value | Target | Status |
|---|---|---|---|
| Build time (s) | <X> | < 90 | ✅/❌ |
| Bundle delta (KB) | <+X> | < +20 | ✅/❌ |
| Spec passes (4 scenarios) | pass/fail | all pass | ✅/❌ |
| Screenshot 360 px attached | yes/no | yes | ✅/❌ |
| Screenshot 1280 px attached | yes/no | yes | ✅/❌ |
| Fallback toast verified | yes/no | yes | ✅/❌ |
| New design tokens introduced | <count> | 0 | ✅/❌ |

## Session close — cross-feature memory protocol (MANDATORY)
1. Append `## Session mesell-ai-autofill-frontend-session-{N}` entry with feature attribution header
2. Update "Features I'm involved in" register
3. Confirm both in final report
```

### Dispatch template — `meesell-angular-service-builder` (frontend)

```
SESSION: mesell-ai-autofill-frontend-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Your mission
MODIFY `frontend/src/app/services/catalog.service.ts` to add an `autofill(productId: string): Observable<AutofillResponse>` method wrapping the HttpClient POST to `/api/v1/products/{id}/autofill`. Error handling MUST treat `fallback_offered=true` as a success signal (component handles the toast).

## Mandatory reads (in this order)
- docs/V1_FEATURE_SPEC.md §F4
- docs/FRONTEND_ARCHITECTURE.md (services section)
- docs/plans/repo_management/MASTER_PLAN.md §5.3 (Frontend PR template)
- docs/plans/features/ai-autofill/FEATURE_PLAN.md (this plan)
- .claude/agent-memory/meesell-angular-service-builder/MEMORY.md — scan ai-autofill-tagged + general/reference entries
- .claude/agent-memory/meesell-api-routes-builder/MEMORY.md — confirm the AutofillResponse JSON shape you are typing against
- docs/status/feature_board_frontend.md
- The existing catalog.service.ts file in full

## Acceptance criteria
- Method signature: `autofill(productId: string): Observable<AutofillResponse>`
- HttpClient POST to `/api/v1/products/${productId}/autofill`
- TypeScript interface `AutofillResponse { suggestions: Record<string, unknown>; dropped_fields: Array<{ canonical: string; reason: string }>; fallback_offered: boolean }` declared in this file or a shared `core/models/` file
- `catchError` handler: on HTTP 404 (flag disabled) and HTTP 403 (plan guard), rethrow as typed error so component shows the right message. On HTTP 200 with `fallback_offered=true`, pass through as success (do NOT throw).
- Idempotent re-run: subsequent calls replace `BehaviorSubject` state in the consuming component cleanly (no leak)
- Unit test covering: 200 success · 200 fallback (passthrough not error) · 404 error · 403 error

## Hard constraints
- NO direct component-level `fetch()` allowed in dispatching this — service is the boundary
- NO `fallback_offered=true` treated as error — it is a success notification
- Typed return shape — no `any`
- RxJS `Observable<T>` not `Promise<T>`
- No new HttpInterceptor — JWT interceptor already handles auth

## Files you may touch
- frontend/src/app/services/catalog.service.ts (ADD autofill method + AutofillResponse interface if not in core/models)
- frontend/src/app/services/catalog.service.spec.ts (ADD autofill tests)
- frontend/src/app/core/models/autofill.model.ts (NEW, OPTIONAL — only if interfaces are kept in core/models pattern)

## Files you MUST NOT touch
- Any component file
- Any other service
- Any backend file
- The JWT interceptor

## Final report format
| Metric | Value | Target | Status |
|---|---|---|---|
| Method signature matches spec | yes/no | yes | ✅/❌ |
| 200 success test | pass/fail | pass | ✅/❌ |
| 200 fallback passthrough test | pass/fail | pass | ✅/❌ |
| 404 error test | pass/fail | pass | ✅/❌ |
| 403 error test | pass/fail | pass | ✅/❌ |
| Idempotent re-run verified | yes/no | yes | ✅/❌ |

## Session close — cross-feature memory protocol (MANDATORY)
1. Append `## Session mesell-ai-autofill-frontend-session-{N}` entry with feature attribution header
2. Update "Features I'm involved in" register
3. Confirm both in final report
```

### Dispatch template — `meesell-prompt-engineer` (AI)

```
SESSION: mesell-ai-autofill-ai-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Your mission
Author the `autofill.v1` prompt content at `backend/app/ai_ops/prompts/autofill_v1.py`, build the golden eval set at `tests/eval/autofill/golden_set.json`, and write the eval runners. The acceptance bar is 0% invalid-enum rate on the golden set with per-call cost ≤ ₹0.05 average. This is the differentiating surface of the feature.

## Mandatory reads (in this order)
- docs/V1_FEATURE_SPEC.md §F4
- docs/BACKEND_ARCHITECTURE.md §6A.C (Layer 1 prefix + Layer 2 enum re-validation flow; note: Layer 1 prefix lives in guardrail.py NOT your template)
- docs/BACKEND_ARCHITECTURE.md §6A.E (golden-set framing; 0% invalid-enum rate target is non-negotiable)
- docs/BACKEND_ARCHITECTURE.md §6A.G (prompt registry — 4 required constants per workload)
- docs/MVP_ARCHITECTURE.md §8.2 (per-call cost target ≤ ₹0.05)
- docs/plans/repo_management/MASTER_PLAN.md §5.4 (AI PR template — your eval evidence section requires 0% invalid-enum rate evidence)
- docs/plans/features/ai-autofill/FEATURE_PLAN.md (this plan)
- .claude/agent-memory/meesell-prompt-engineer/MEMORY.md — read in full (the §6A storage layout entry, the §10 catalog autofill.v1 entry, and the 3-target-locks reference are critical)
- .claude/agent-memory/meesell-services-builder/MEMORY.md — confirm the {{product_spec}} and {{schema}} variable contract
- docs/status/feature_board_ai.md
- The existing `backend/app/ai_ops/prompts/autofill_v1.py` baseline draft (authored by services-builder during §6A construction — your job is to refine, not start from scratch)
- The smart-picker prompt-engineer PR diff (when it exists) as the REFERENCE implementation for prompt-engineer dispatch flow

## Acceptance criteria
- `autofill_v1.py` exists with the 4 required constants (TEMPLATE, VERSION="v1", WORKLOAD="autofill", RENDERED_BY="text")
- TEMPLATE includes few-shot examples covering 5 high-traffic super-categories (sarees, kurtas, dresses, shoes, kitchenware — confirm against MEESHO_CATEGORY_INTELLIGENCE.md)
- TEMPLATE includes explicit "leave field blank if unsure" instruction (anti-hallucination signal)
- TEMPLATE output shape matches `{"fields": {<canonical>: <value>}, "fallback_offered": false}` (the fallback_offered flag is set elsewhere — see prompt-engineer MEMORY notes)
- NO Layer 1 prefix in your template (guardrail.py owns it — bonded to workload)
- NO enum allowlist block inline in template (guardrail.apply_prompt_constraint appends it from caller-supplied allowed_enums dict)
- Golden set at `tests/eval/autofill/golden_set.json`: ≥ 30 fixtures, target 50 for headroom; schema `{description, category_id, expected_fields: {canonical: value}, expected_dropped: [canonical]}`
- `tests/eval/autofill/test_enum_validity.py`: runs the golden set through `ai_ops.eval.run_eval("autofill")`, asserts aggregate invalid-enum rate == 0%
- `tests/eval/autofill/test_recall.py`: runs golden set, reports compulsory-field recall as informational metric (no hard gate)
- Per-call cost ≤ ₹0.05 average over the 30+ golden set runs
- LangFuse trace sample link in final report
- `tests/eval/README.md` updated with autofill entry alongside smart-picker

## Hard constraints
- NO eval-set contamination in few-shots (golden-set descriptions MUST NOT appear in your TEMPLATE few-shot examples; verify by string-diff)
- NO Layer 1 prefix in template (lives in guardrail.py)
- NO enum allowlist block in template (guardrail.py appends from caller dict)
- NO hallucinated enum values — Layer 2 will drop; your prompt MUST instruct the model to leave blank rather than guess
- DO NOT modify `ai_ops/guardrail.py`, `ai_ops/cost_tracker.py`, `ai_ops/budget_cap.py`, `ai_ops/prompt_registry.py`
- VERIFY `ai_ops/client.py` workload Literal includes "autofill"; MODIFY only if missing (most likely already present from §6A construction — read first)
- DO NOT modify any catalog/* file, route, or schema (backend specialists own those)
- DO NOT modify any frontend file

## Files you may touch
- backend/app/ai_ops/prompts/autofill_v1.py (NEW or MODIFY existing baseline)
- backend/app/ai_ops/client.py (ONLY IF "autofill" Literal missing — verify first)
- tests/eval/autofill/golden_set.json (NEW)
- tests/eval/autofill/test_enum_validity.py (NEW)
- tests/eval/autofill/test_recall.py (NEW)
- tests/eval/README.md (MODIFY — one entry added)

## Files you MUST NOT touch
- backend/app/modules/catalog/* (backend specialists own)
- backend/app/ai_ops/guardrail.py · cost_tracker.py · budget_cap.py · prompt_registry.py · eval.py (locked)
- backend/app/adapters/gemini.py (vendor isolation)
- Any frontend file
- backend/app/data/field_aliases.json (data lead's surface)

## Final report format
| Metric | Value | Target | Status |
|---|---|---|---|
| Invalid-enum rate (golden set) | <X> % | 0 % | ✅/❌ |
| Compulsory-field recall (informational) | <XX> % | ≥ 70 % | — |
| Per-call cost (₹, avg over 30+ runs) | <X.XX> | ≤ 0.05 | ✅/❌ |
| Daily projected spend at expected QPS | ₹<XX> | < ₹500 cap | ✅/❌ |
| LangFuse trace sample link | <url> | present | ✅/❌ |
| Eval-set contamination check (few-shot vs golden) | pass/fail | pass | ✅/❌ |
| Layer 1 prefix NOT in template | pass/fail | pass | ✅/❌ |
| Enum allowlist NOT in template | pass/fail | pass | ✅/❌ |

## Session close — cross-feature memory protocol (MANDATORY)
1. Append `## Session mesell-ai-autofill-ai-session-{N}` entry to MEMORY.md with feature attribution header, the TEMPLATE iteration notes, and the per-call cost trend across iterations
2. Update "Features I'm involved in" register
3. Confirm both in final report
```

### Dispatch template — `meesell-xlsx-parser` (data) *(CONDITIONAL)*

This template is dispatched **ONLY** if the AI lead's `test_enum_validity.py` surfaces invalid-enum hits AND root-cause analysis attributes them to stale `enum_values` in `backend/app/data/field_aliases.json`. Default expectation: this template is NOT used for ai-autofill.

```
SESSION: mesell-ai-autofill-data-session-{N}
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

## Your mission
Refresh the `enum_values` for the specific category/field pairs flagged by prompt-engineer's eval run. Source is the latest Meesho category XLSX template per docs/PLAYWRIGHT_MCP_REFERENCE.md cadence. Surgical update only — do NOT rebuild the entire field_aliases.json.

## Mandatory reads (in this order)
- docs/plans/features/ai-autofill/FEATURE_PLAN.md (this plan — confirm you are triggered by the conditional path)
- docs/V1_FEATURE_SPEC.md §F3 (Smart Picker — adjacent dependency on field_aliases)
- docs/MEESHO_CATEGORY_INTELLIGENCE.md
- docs/PLAYWRIGHT_MCP_REFERENCE.md
- docs/plans/repo_management/MASTER_PLAN.md §5.5 (Data PR template)
- .claude/agent-memory/meesell-xlsx-parser/MEMORY.md — scan ai-autofill-tagged + general/reference entries
- .claude/agent-memory/meesell-prompt-engineer/MEMORY.md — read the eval failure report that triggered this dispatch
- docs/status/feature_board_data.md

## Acceptance criteria
- Surgical update: only the {category, field} pairs flagged by prompt-engineer's eval failure report are refreshed
- Pre-update count, post-update count, and diff summary documented in final report
- Re-run of prompt-engineer's `test_enum_validity.py` against the updated `field_aliases.json` shows 0% invalid-enum rate
- amendment to MEESHO_CATEGORY_INTELLIGENCE.md included in the same PR (per master plan §5.5 data PR template rule)

## Hard constraints
- NO rebuild of the entire `field_aliases.json` — surgical update only
- NO change to schema or shape — only `enum_values` lists for specific entries
- NO change to any other data file

## Files you may touch
- backend/app/data/field_aliases.json (surgical update only)
- docs/MEESHO_CATEGORY_INTELLIGENCE.md (amendment)

## Files you MUST NOT touch
- Any other JSON in backend/app/data/
- Any code file
- Any other feature's planning dir

## Final report format
| Metric | Value | Target | Status |
|---|---|---|---|
| Rows pre-update | <N> | — | — |
| Rows post-update | <N> | — | — |
| Affected {category, field} pairs | <list> | matches eval report | ✅/❌ |
| Re-run invalid-enum rate | <X> % | 0 % | ✅/❌ |
| MEESHO_CATEGORY_INTELLIGENCE.md amendment included | yes/no | yes | ✅/❌ |

## Session close — cross-feature memory protocol (MANDATORY)
1. Append `## Session mesell-ai-autofill-data-session-{N}` entry to MEMORY.md with feature attribution header
2. Update "Features I'm involved in" register
3. Confirm both in final report
```

---

## Review + iteration protocol

For each specialist dispatch, this section defines what the lead checks before approving the specialist's PR, what triggers a re-dispatch, what the re-dispatch prompt looks like, and the maximum iteration count.

### Per-specialist approval checks

| Specialist | Lead | What lead verifies before approving group PR |
|---|---|---|
| services-builder | backend-coordinator | `autofill_product` body MODIFIED to write only `ai_suggestions_jsonb` · §10 auto-apply path REMOVED · Layer 2 retries consumed from `AIResponse.layer2_retries` · graceful fallback returns 200+`fallback_offered=true` · all 5 unit-test scenarios pass · per-call cost ≤ ₹0.05 in unit test mocks · session memory entry present with feature attribution |
| api-routes-builder | backend-coordinator | route returns 200 on success and on `BudgetExceededError` (NOT 503) · 404 when flag disabled · plan_guard runs before service call · OpenAPI description explicitly mentions success-with-fallback shape · all 6 integration-test scenarios pass · session memory entry present |
| angular-component-builder | frontend-coordinator | AutofillButton + FieldDiff standalone+OnPush · yellow highlight clears on user edit · fallback toast NOT treated as error · screenshots at 360 + 1280 px · build < 90 s · bundle delta < +20 KB · no new design tokens · session memory entry present |
| angular-service-builder | frontend-coordinator | `autofill()` returns `Observable<AutofillResponse>` typed · `fallback_offered=true` passes through as success · 4 unit-test scenarios pass · session memory entry present |
| prompt-engineer | ai-coordinator | `autofill_v1.py` has all 4 required constants · "leave field blank if unsure" instruction present · Layer 1 prefix NOT in template · enum allowlist NOT in template · golden set ≥ 30 fixtures · test_enum_validity.py asserts 0% · per-call cost ≤ ₹0.05 over 30+ runs · LangFuse trace link · eval-set contamination check passes · session memory entry present |
| xlsx-parser (conditional) | data-engineer | surgical update only (no full rebuild) · re-run of prompt-engineer's eval shows 0% · MEESHO_CATEGORY_INTELLIGENCE.md amendment included · session memory entry present |

### Acceptance gate from `.github/PULL_REQUEST_TEMPLATE/ai.md`

For the AI specialist's PR specifically — non-negotiable rows from the template:
- Invalid-enum rate row MUST show `0%`
- Per-call cost row MUST show `≤ ₹0.05`
- Layer 1 prompt-prefix constraint preserved (verified by reading guardrail.py — should be untouched)
- Layer 2 enum re-validation passes for the new prompt (test_enum_validity.py output pasted)
- LangFuse trace sample link present

### Failure modes and re-dispatch triggers

| Failure mode | Detection | Re-dispatch target | Re-dispatch preamble |
|---|---|---|---|
| Invalid-enum rate > 0% | `test_enum_validity.py` fails | prompt-engineer | "Previous run produced N invalid enums against the {category, field} pairs listed below: [LIST]. Tighten the few-shot for those category-field combos. Verify the 'leave blank if unsure' instruction is present and clearly worded. Re-eval. Cite the failing pairs in your final report." |
| Compulsory-field recall < 70% (informational, not blocking but worth iterating) | `test_recall.py` reports | prompt-engineer | "Previous run filled only X/Y compulsory fields across the golden set. Verify the 'leave blank if unsure' instruction isn't over-applying. Check few-shot examples — they should show populated fields where description is clear. Re-eval." |
| Per-call cost > ₹0.05 | cost report in final summary | prompt-engineer | "Previous run cost ₹Y/call avg. Reduce few-shot count or compress schema context. Confirm allowed_enums block is being added by guardrail.py (not inlined in your template). Re-eval and report new cost." |
| 5s P95 latency exceeded | integration test fails | services-builder | "Previous run P95 = X ms. Profile the autofill_product call. Likely culprits: schema fetch latency, AI call latency, JSONB upsert latency. Add timing logs and re-run integration test." |
| §10 auto-apply path detected in regression test | regression test fails | services-builder | "Previous run still wrote to fields_jsonb during autofill. Remove the auto-apply branch entirely from autofill_product. Add explicit regression test asserting fields_jsonb is UNTOUCHED before user-accept." |
| UI shows error toast on `fallback_offered=true` | spec.ts fallback scenario fails | angular-component-builder | "Previous run treated fallback_offered=true as an error. Verify catalog-form.component.ts subscribes to autofill() success path including fallback_offered=true and opens MatSnackBar with i18n key `ai.quota.exhausted` (NOT error). Re-run spec." |
| CatalogService.autofill throws on `fallback_offered=true` | spec.ts fails | angular-service-builder | "Previous run treated fallback_offered=true as catchError. Verify the catchError handler distinguishes HTTP 4xx (rethrow) from HTTP 200 with fallback_offered=true (pass through). Re-run spec." |
| OpenAPI does not mention success-with-fallback shape | reviewer check on PR | api-routes-builder | "Previous OpenAPI generation does not document the fallback_offered=true success shape. Add explicit description note to the @router.post decorator. Re-generate openapi.yaml and confirm the note appears." |

### Re-dispatch prompt template

For every re-dispatch, the lead prepends the following preamble to the ORIGINAL dispatch template (above), then dispatches the same specialist:

```
## RETRY DISPATCH — iteration {M} of max 3
**Previous attempt:** mesell-ai-autofill-{group}-session-{N-1}
**Why this retry:** <one-paragraph failure mode from table above>
**What to fix:** <specific re-dispatch preamble from table above>
**Mandatory NEW reads on top of the original template's reads:**
- The previous session's session-close entry in your own MEMORY.md (read it; learn from it)
- The previous session's PR comments (if PR was opened)
- The previous session's failing test output (paste it in your final report)

[BELOW: the original dispatch template verbatim]
```

### Maximum iteration count

**Max 3 iterations per specialist** before escalating to the founder.

If iteration 3 still fails, the lead writes a one-paragraph escalation memo to `.claude/agent-memory/meesell-<lead>/handoff_ai_autofill_escalation.md` and adds a `BLOCKED — founder` row to `feature_board_<domain>.md`. The founder decides: continue (lift the 3-iteration cap), pivot (revise the FEATURE_PLAN.md), or defer (move ai-autofill to V1.5 with a documented blocker).

---

## Acceptance gate

The ai-autofill feature is "done" — i.e. the `feature/ai-autofill` → `develop` PR is approvable by the founder — when ALL of the following are true:

### Pre-dispatch (verified before any group branch is created)
- [ ] D3 prerequisites met: `smart-picker` AND `catalog-form` are MERGED to `develop`
- [ ] This `FEATURE_PLAN.md` is MERGED to `develop`
- [ ] The one-shot fan-out broadcast (Mechanism 3) has been executed — every agent in the 18-agent fleet has the ai-autofill feature register entry in their MEMORY.md
- [ ] `feature/ai-autofill` branch exists off `develop`
- [ ] Every involved lead has updated their `feature_board_<domain>.md` with an `ai-autofill` row in `PENDING` status

### Code completeness
- [ ] `services-builder` PR merged to `feature/ai-autofill` — `autofill_product` body MODIFIED, §10 auto-apply path removed
- [ ] `api-routes-builder` PR merged — `/autofill` route + schemas + integration test
- [ ] `angular-component-builder` PR merged — AutofillButton + FieldDiff + catalog-form wiring + spec
- [ ] `angular-service-builder` PR merged — `CatalogService.autofill` + typed response + spec
- [ ] `prompt-engineer` PR merged — `autofill_v1.py` + golden set + 2 eval runners + README entry
- [ ] (CONDITIONAL) `xlsx-parser` PR merged if triggered

### Quality gates
- [ ] CI gates 1+2+3 green on `feature/ai-autofill` (unit, smoke, lint)
- [ ] CI gate 4 integration green
- [ ] Nightly `ai_eval` job green within last 24 hours covering `tests/eval/autofill/`
- [ ] `test_enum_validity.py` shows **0 %** invalid-enum rate
- [ ] Per-call cost averaged over 30+ golden-set runs is **≤ ₹0.05**
- [ ] P95 latency over 30+ integration test runs is **≤ 5 s**
- [ ] Regression test confirms `products.fields_jsonb` is NEVER written by `autofill_product`
- [ ] Frontend spec confirms `fallback_offered=true` produces a toast, not an error

### Documentation
- [ ] OpenAPI entry for `POST /api/v1/products/{id}/autofill` includes the success-with-fallback shape note
- [ ] `tests/eval/README.md` includes the autofill entry
- [ ] `autofill_v1.py` header comment documents Layer 2 retry semantics
- [ ] `AutofillButtonComponent` + `FieldDiffComponent` + `CatalogService.autofill` docstrings/JSDoc present
- [ ] `docs/V1_FEATURE_SPEC.md §F4` stamped "implemented YYYY-MM-DD" with feature-PR link
- [ ] Every specialist's session memory entry uses the Mechanism 1 header format
- [ ] Every involved agent's "Features I'm involved in" register shows ai-autofill = `MERGED`

### Feature flag posture
- [ ] `FEATURE_AI_AUTOFILL_ENABLED=true` in `dev` namespace deployment env vars
- [ ] `FEATURE_AI_AUTOFILL_ENABLED=false` in `staging` namespace deployment env vars (will flip to true after 24h staging soak per D2)
- [ ] Backend returns 404 when flag is false (verified in integration test)
- [ ] Frontend hides AutofillButton when flag is false (verified in spec)

### Acceptance gate for THIS planning session

Before the founder merges this planning PR to `develop`, ALL of the following must be true (mirrors the brief's Step 8 acceptance):
- [x] Founder decisions D1/D2/D3 recorded at top of this FEATURE_PLAN.md
- [x] Founder structural resolutions A/B/C recorded
- [x] Agent lineup table fully filled out (backend 2 + frontend 2 + AI 1 + data 0-or-1 specialists named)
- [x] Branch lifecycle for this feature specified
- [x] Code surfaces table covers every file the feature will create or modify
- [x] Documentation deliverables enumerated
- [x] One dispatch template per specialist drafted (5 unconditional + 1 conditional = 6 total)
- [x] Cross-feature memory protocol defined (3 mechanisms)
- [x] Review + iteration protocol defined (with all failure-mode examples)
- [x] Acceptance gate enumerated
- [x] Risk register populated
- [ ] FEATURE_PLAN.md committed on `feature/ai-autofill/planning` (next step in this session)
- [ ] PR opened to `develop` using AI PR template (next step in this session)

---

## Risk register

The top 5 risks specific to this feature, with mitigation owners.

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | **Golden-set enum drift after Meesho category template refresh.** Meesho periodically updates category XLSX templates; the `field_aliases.json` `enum_values` may go stale, causing the prompt to emit values that pass our internal allowlist but fail Meesho's actual schema at export time. | Medium | High (Layer 2 returns "valid" but Layer 3 export-time validation later fails the user's export — silent regression) | The conditional `xlsx-parser` dispatch template above. Quarterly scraper refresh per `meesell-scraper-maintainer` cadence. Add a Layer 3 regression smoke test that round-trips a golden-set autofill through to XLSX export. | data-engineer + ai-coordinator |
| R2 | **Layer 2 retry storm under enum-strict prompt.** If the prompt's enum allowlist block is too aggressive or the model is borderline, every call hits the up-to-2 retries → 3 Gemini calls per autofill request → cost balloons from ₹0.04 to ₹0.12+. | Medium | High (per-call cost target violated; daily ₹500 cap hit hours earlier than expected) | Cost-monitoring alarm at ₹0.08/call (above target but below 2x retry cost). Prompt-engineer iterates `_v2` if avg retries per call exceed 0.3. | ai-coordinator |
| R3 | **Gemini JSON-mode regression drops schema-compliance guarantee.** Google has historically tightened/loosened JSON-mode behaviour silently; a model update may break the strict JSON shape parsing in Layer 2. | Low | High (every autofill call fails validation → falls through to `fallback_offered=true` → users see "AI quota reached" toast that has nothing to do with quota) | The eval gate (`test_enum_validity.py`) running nightly catches this within 24 hours. Add a discriminator log line "fallback_reason" to the service (values: `budget`, `enum_failure_after_retries`, `parse_failure`) so the toast text can be diversified in V1.5 if needed. V1: still shows the same toast — observability fix only. | ai-coordinator + services-builder |
| R4 | **Frontend treats `fallback_offered=true` as error.** Easy bug — service's `catchError` is permissive and component's success handler is strict, leading to a misleading error UX. | Medium | Medium (users see "Failed to load autofill" toast instead of "AI quota reached" — confusing but not data-loss) | The dispatch template's hard constraint + the spec test scenario "fallback toast appears" must pass. The frontend lead's approval check explicitly verifies this. The angular-service-builder dispatch template has a separate unit test for the passthrough. | frontend-coordinator |
| R5 | **Per-call cost creeps above ₹0.05 as few-shot count grows.** Prompt-engineer iterates `_v2`, `_v3` adding more few-shots to improve recall; each few-shot adds ~150-200 input tokens; at 5 few-shots × 200 tokens = 1000 tokens just for examples. Adding the enum allowlist block on top can push input tokens past 2000 → cost approaches ₹0.07. | High | Medium (target violation; daily cap hit faster; eventual budget pressure) | Cost regression metric per iteration in the AI PR template. Hard rule: `_v2` is only acceptable if (avg cost change vs `_v1`) ≤ +5% OR (invalid-enum-rate change) is the dominant driver. Prompt-engineer compresses schema context (top-10 enum preview per field, not full list) per existing prompt-engineer MEMORY note. | ai-coordinator |
| R6 | **§10 auto-apply regression risk.** Future services-builder dispatches on OTHER features (e.g. live-preview, profile) may inadvertently re-introduce auto-apply behaviour into autofill_product because the catalog service module is shared. | Medium | High (silent return to auto-apply violates D1 lock; user-accept gate disappears without anyone noticing) | The dispatch template's regression test for "autofill_product does NOT write fields_jsonb" stays in `test_catalog_unit.py` permanently. Pre-commit hook (V1.5) could grep for `fields_jsonb` writes inside `autofill_product`. V1: the test is the gate. | backend-coordinator |

---

### Follow-up actions (NOT in this PR)

Three follow-up actions are queued from this planning session. None of them are in this PR — each gets its own separate PR after this one merges:

1. **`chore/§6A.F-text-housekeeping`** — small doc-text-only PR updating `BACKEND_ARCHITECTURE.md §6A.F` to reflect implemented reality (200 + `fallback_offered=true` instead of 503 with i18n key). Author: backend-coordinator. Scope: ~10 lines of prose.
2. **`docs/master-plan-amend-cross-feature-memory`** — PR amending `MASTER_PLAN.md §6 (feature_board)` and `§7 (lead responsibilities)` to bake the 3-mechanism cross-feature memory protocol + the Lead/Agent assignment pattern + the Branch lifecycle pattern into the canonical FEATURE_PLAN.md template that all 9 V1 features inherit. Author: backend-coordinator (drafts) + all leads (review). Scope: 2 new subsections in `§6`, 1 new subsection in `§7`, and a template appendix.
3. **`chore/broadcast-ai-autofill-feature-register`** — after this planning PR merges to `develop`, run the one-shot fan-out broadcast pass writing the feature-register stubs to all 18 agents' `MEMORY.md` files. Author: master session. Scope: 18 small append-only edits, one per agent's MEMORY.md.

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| v1 | 2026-06-10 | mesell-ai-autofill-planning-session-1 (master) | Initial DRAFT authored. Founder D1/D2/D3 locked. Founder structural resolutions A (Lead/Agent assignment), B (Branch lifecycle), C (Cross-feature memory protocol) locked. Three follow-up PRs queued. |
| v2 | 2026-06-10 | mesell-ai-autofill-amendment-session-1 | Canonical pattern v2 conformance: Lead/Agent assignment → Agent lineup; Branch lifecycle for this feature → Branch setup; ## Memory protocol added (consolidated 5 ad-hoc cross-feature memory h2 sections as subsections); ## Follow-up actions demoted to h3 under ## Risk register; 11 canonical h2 headings verified in locked order. |
