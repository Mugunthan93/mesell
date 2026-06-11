# Session Dispatch: AI Auto-fill — Gemini Fills Product Attributes from Minimal Input
**Session name:** `mesell-ai-autofill-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/ai-autofill/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp shipped; smart-picker shipped (autofill reuses the ai_ops infrastructure smart-picker established); catalog-form shipped (autofill writes to products.fields_jsonb via catalog.service.autosave_patch)
**Lead involvement:** Backend (ai_ops integration + autofill seam in catalog) · Frontend (autofill UI chips/diff inside the catalog-form page) · AI (autofill prompt + Layer 2 enum-guardrail compliance + golden eval set) · Data (only if a field enum is unstable and the guardrail surfaces invalid-enum hits)

---

## Why this session exists
AI Auto-fill is the second-most-leveraged AI feature in V1. The acceptance bar is unusually strict — **0% invalid-enum rate** on the golden set per `BACKEND_ARCHITECTURE.md §6A.E` is non-negotiable because every autofilled value must pass the Pydantic FieldRendererComponent validator (no client-side coercion). It is the only AI feature with a Layer 2 guardrail (enum re-validation + up-to-2 retries per §6A.C) and the only one that returns 200 + `fallback_offered=true` empty result when the budget cap fires per §6A.F — UI must handle the empty-suggestions case as a non-error.

The feature sits inside the catalog-form page UX but is a separate planning unit because (a) its acceptance criteria are pure AI eval, (b) its prompt-engineering work is largely orthogonal to the form rendering, and (c) it can ship behind a feature flag after catalog-form lands without blocking that feature. This planning session locks the boundary between catalog module and ai_ops, the diff/chip UI pattern, and the per-call cost budget against the ₹500/day cap.

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-ai-autofill-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/ai-autofill/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the AI Auto-fill feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)
You must be inside the dedicated git worktree for ai-autofill. Verify:

pwd                                          # must print /private/tmp/mesell-wt/ai-autofill or /tmp/mesell-wt/ai-autofill
git worktree list | grep ai-autofill         # must show this worktree
git branch --show-current                     # must print feature/ai-autofill/planning

If pwd is wrong or the worktree is missing, STOP. The launcher script `scripts/launch-planning-session.sh ai-autofill` (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read `docs/plans/features/_WORKTREE_PROTOCOL.md` once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates (especially §5.4 AI template — eval evidence section requires 0% invalid-enum rate evidence), §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F4 (Feature 4: AI Auto-fill) — only compulsory fields populated, suggestion within 5s P95, all values pass field-schema validation, user-edit override clears yellow highlight, idempotent re-run
- docs/BACKEND_ARCHITECTURE.md §6A (AI Operations Layer — Layer 1 prefix + Layer 2 enum re-validation with up-to-2 retries + Layer 3 forward-ref to export; cost_tracker.py per-call cost; budget_cap.py with §6A.F graceful fallback returning 200 + fallback_offered=true; prompt_registry resolver), §10 (catalog module — POST /products/{id}/autofill route + service.autofill_from_description() + writes to products.fields_jsonb and products.ai_suggestions_jsonb)
- docs/FRONTEND_ARCHITECTURE.md — autofill UI is an enhancement to the catalog-form page; AutofillButtonComponent + FieldDiffComponent (yellow highlight, accept/edit per-field semantics) under frontend/src/app/pages/catalog-form/autofill/
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — depends on catalog (8) and category (6) extraction; autofill seam lives in catalog module so it ships when catalog ships
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — autofill UI is part of mfe-catalog (5th remote); pre-federation in the shell alongside catalog-form
- CLAUDE.md — Gemini 2.5 Flash JSON-mode decision, agent fleet (prompt-engineer + category-picker-builder; image-precheck-builder NOT involved in autofill)
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md, .claude/agents/meesell-ai-coordinator.md, .claude/agents/meesell-data-engineer.md
- Each involved lead's MEMORY.md (especially ai-coordinator memory for ai_ops contract surface established by smart-picker)
- Each involved lead's docs/status/feature_board_{backend|frontend|ai|data}.md (verify ai-autofill is PENDING)
- `docs/plans/features/_WORKTREE_PROTOCOL.md` — the worktree protocol; verify your worktree posture matches it
- `docs/plans/features/_status/README.md` — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)
Do NOT edit the master tracker — it is now master-only and regenerated by the Director from `_status/*.yaml` files. Each sub-session writes its own file at `docs/plans/features/_status/ai-autofill.yaml` instead.

Create (or overwrite) `docs/plans/features/_status/ai-autofill.yaml` with:
```yaml
feature: ai-autofill
session: mesell-ai-autofill-planning-session-1
worktree: /tmp/mesell-wt/ai-autofill
branch: feature/ai-autofill/planning
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/ai-autofill/FEATURE_PLAN.md
feature_plan_line_count: null
pr_number: null
pr_url: null
outstanding_founder_decisions: []
notes: |
  Planning session opened in worktree.
```

DO NOT commit this file yet — it will be committed alongside FEATURE_PLAN.md in Step 8.

If your status file already exists and shows `IN_PROGRESS` (a prior session was interrupted): proceed but flag this in the `## Decisions` section of your FEATURE_PLAN.md so the founder knows.

## Step 1 — Surface scope decisions to the founder
Before drafting the plan, ask the founder to lock these 3 questions:

Decision 1 — Scope confirmation
  Does this feature still match V1 spec §F4? Specifically:
    - Only compulsory fields populated (Recommended / Optional left blank — important guardrail against hallucination)
    - Suggestion within 5s P95
    - All suggested values pass field-schema validation (enum / length / regex) — 0% invalid-enum rate per §6A.E
    - Yellow-highlight diff UI; user accepts or edits per-field
    - Idempotent re-run replaces previous AI suggestions in products.ai_suggestions_jsonb
    - On invalid enum: drop that field with a logged warning, do NOT lower the field's value, do NOT hallucinate a substitute
    - On budget exhaustion: return 200 + fallback_offered=true + empty suggestions (UI shows "AI quota reached — please fill manually" toast, not an error)
  Any cuts, additions, or scope flexes since the spec was locked?

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_AI_AUTOFILL_ENABLED). Dev default: true. Staging default: false until the golden eval set passes 0% invalid-enum rate AND per-call cost averages ≤₹0.05 in 24-hour staging soak. When disabled, POST /products/{id}/autofill returns 404 per master plan §3.2 backend rule; the autofill button is hidden in the catalog-form page via FeatureFlagsService.

Decision 3 — Priority ordering vs sibling features
  This feature touches:
    - Backend shared code: app/ai_ops/* (smart-picker established this; autofill consumes the established contract — no contention if smart-picker is merged first)
    - Backend per-module code: app/modules/catalog/service.py (adds autofill_from_description method); catalog-form's services-builder dispatch must complete before this dispatch begins
    - Frontend per-feature code: frontend/src/app/pages/catalog-form/ — additive (chips/diff/button components); no contention with catalog-form rendering
  Confirm: ai-autofill ships after smart-picker AND catalog-form. The ai-autofill feature branch can be opened in parallel with image-precheck once the prerequisites are merged.

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | services-builder, api-routes-builder | services-builder: catalog.service.autofill_from_description(product_id, user_id, description) → calls ai_ops.client.call_gemini("autofill.v1", context={...}) with budget reservation, applies Layer 2 enum re-validation + up-to-2 retries per §6A.C, writes results to products.ai_suggestions_jsonb (NOT directly to fields_jsonb — user must accept first), returns AutofillResponse with per-field suggestion + dropped fields list; api-routes-builder: POST /api/v1/products/{id}/autofill route + AutofillRequest/AutofillResponse Pydantic schemas in modules/catalog/schemas.py (catalog-form's api-routes-builder already added the autosave/create/preview/draft routes — this dispatch ADDS the autofill route only) |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: AutofillButtonComponent (loading state, error-toast on budget-exhaustion fallback_offered=true), FieldDiffComponent (per-field yellow highlight, accept/edit affordance, clears highlight on user edit), under frontend/src/app/pages/catalog-form/autofill/; angular-service-builder: CatalogService.autofill(productId, description) wrapping HttpClient call, error handling for the fallback_offered=true case (shows "AI quota reached" toast — NOT treated as error), idempotent re-run replaces previous suggestions in component state |
| meesell-ai-coordinator | prompt-engineer | prompt-engineer: autofill.v1 prompt file at backend/app/ai_ops/prompts/autofill_v1.py — system prompt with Layer 1 prefix per §6A.C, few-shot examples covering 5 high-traffic super-categories with enum-strict outputs, JSON-mode output schema matching AutofillResponse, explicit "leave field blank if unsure" instruction (anti-hallucination); golden eval set at tests/eval/autofill/golden_set.json (50 hand-labeled description+category pairs with expected populated fields and expected dropped fields); eval runner at tests/eval/autofill/test_enum_validity.py (gates 0% invalid-enum rate) and test_recall.py (informational — recall % of compulsory-fields populated). category-picker-builder NOT involved (different workload) |
| meesell-data-engineer | (only if the golden eval surfaces enum drift) | xlsx-parser: ONLY if eval surfaces invalid-enum hits caused by stale field_aliases.enum_values — refresh from latest XLSX source. Default: no work — the field_aliases seed is stable. |

Only include leads + specialists who actually have work. Omit empty rows.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/catalog/routes.py (MODIFY — add /autofill route only; catalog-form dispatch already added the other 4), app/modules/catalog/schemas.py (MODIFY — add AutofillRequest/AutofillResponse + DroppedField shape), app/modules/catalog/service.py (MODIFY — add autofill_from_description method only; catalog-form dispatch already added the other 8 methods), app/ai_ops/prompts/autofill_v1.py (NEW), app/ai_ops/client.py (NO CHANGE if smart-picker already added "autofill" to the workload Literal; otherwise MODIFY to add it), backend/tests/test_catalog_unit.py (MODIFY — autofill service tests with mocked ai_ops), backend/tests/test_ai_autofill_integration.py (NEW), tests/eval/autofill/golden_set.json (NEW), tests/eval/autofill/test_enum_validity.py (NEW), tests/eval/autofill/test_recall.py (NEW informational)
- Frontend: frontend/src/app/pages/catalog-form/autofill/autofill-button.component.ts (NEW), frontend/src/app/pages/catalog-form/autofill/field-diff.component.ts (NEW), frontend/src/app/pages/catalog-form/catalog-form.component.ts (MODIFY — wire AutofillButton into form layout, render FieldDiff per field), frontend/src/app/services/catalog.service.ts (MODIFY — add autofill method), frontend/src/app/pages/catalog-form/autofill/autofill.spec.ts (NEW)
- AI: backend/app/ai_ops/prompts/autofill_v1.py (NEW — prompt-engineer authors content), tests/eval/autofill/ (NEW dir with golden set + 2 eval runners)
- Data: backend/app/data/field_aliases.json (MODIFY only if enum drift surfaces in eval)
- Infra: NONE (no new secrets; GEMINI_API_KEY + budget already provisioned)
- Docs: docs/V1_FEATURE_SPEC.md §F4 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §6A sentinel reaffirmed (Layer 2 enum-validation receipt visible in autofill_v1.py)

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entry for POST /api/v1/products/{id}/autofill — request shape (description, optional category_id override), response shape (suggestions per field + dropped fields with drop reason + fallback_offered flag), error responses (200 + empty + fallback_offered on budget exhaustion is the new "success-with-fallback" shape — call this out explicitly in the OpenAPI description)
- Frontend: AutofillButtonComponent docstring describing the loading state + the fallback_offered=true "AI quota reached" toast handling; FieldDiffComponent docstring on accept/edit semantics and yellow-highlight-on-suggestion / clear-on-edit cycle
- AI: prompt registry entry — autofill.v1 registered in ai_ops/prompt_registry.py; golden set fixture path documented in tests/eval/README.md (alongside smart-picker entry); eval runner instructions for local + CI ai_eval gate; Layer 2 retry semantics documented inline in autofill_v1.py header comment
- Data: field_aliases.json version bump in data lead's memory (only if rows added)
- Infra: N/A
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F4 marked "implemented YYYY-MM-DD" with PR link; ai_eval CI gate extended to include tests/eval/autofill/

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-ai-autofill-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., prompt-engineer reads §6A.C Layer 1 prefix + §6A.E golden-set framing + autofill-specific anti-hallucination instruction; services-builder reads §10.C catalog service surface + §6A.C Layer 2 enum re-validation flow + the smart-picker services-builder PR as the reference implementation for ai_ops integration)
- Acceptance criteria (specific to that specialist's slice — e.g., prompt-engineer: autofill.v1 file exists, golden set passes 0% invalid-enum rate, recall ≥70% on compulsory fields, per-call cost ≤₹0.05; services-builder: autofill_from_description applies up-to-2 retries on Layer 2 enum re-validation failures, drops fields that fail after retries with logged warning, returns AutofillResponse with dropped fields visible; api-routes-builder: route returns 200 + fallback_offered=true + empty on BudgetExceededError, NOT 503)
- Hard constraints (e.g., NO direct adapters/gemini.py import — only ai_ops.client; NO writes to products.fields_jsonb in autofill_from_description — only to ai_suggestions_jsonb; NO hallucinated enum values — fail-closed by dropping the field)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch
- Final report format (per-call cost, invalid-enum rate, compulsory-field recall, P95 latency)

Specialists to template:
- meesell-services-builder (backend lead dispatches)
- meesell-api-routes-builder (backend lead dispatches)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)
- meesell-prompt-engineer (ai lead dispatches)
- meesell-xlsx-parser (data lead dispatches IF enum drift surfaces — otherwise omit)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., AI lead checks: invalid-enum rate = 0% on golden set; cost ≤₹0.05/call; "leave field blank if unsure" instruction present in prompt; Layer 1 prefix preserved; JSON-mode output validates against AutofillResponse Pydantic model; no eval-set contamination in few-shots)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/ai.md` (invalid-enum rate row MUST show 0%; cost row MUST show ≤₹0.05)
- What triggers a re-dispatch (specific failure modes — invalid-enum rate >0% → re-dispatch prompt-engineer with "Previous run produced N invalid enums against the {category, field} pairs listed; tighten the few-shot for those category-field combos and re-eval"; recall <70% → re-dispatch with "Previous run filled only X/Y compulsory fields; verify the field-blank-if-unsure instruction isn't over-applying"; cost >₹0.05 → re-dispatch with "Previous run cost ₹Y/call; reduce few-shot count or compress field schema context"; UI shows error toast on fallback_offered=true → re-dispatch frontend with "verify CatalogService.autofill handles fallback_offered=true as success+toast not error")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/ai-autofill/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., golden-set enum drift after a Meesho category template refresh, Layer 2 retry storm under enum-strict prompt, Gemini JSON-mode regression dropping the schema-compliance guarantee, frontend treating fallback_offered=true as error, per-call cost creeping above ₹0.05 as few-shot count grows)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)
You are ALREADY on `feature/ai-autofill/planning` because the worktree handles branch isolation. DO NOT run `git checkout -b` — the branch is yours by virtue of the worktree.

1. Update `docs/plans/features/_status/ai-autofill.yaml`:
  - `status: PLAN_READY`
  - `last_updated: <today's ISO 8601 UTC timestamp>`
  - `feature_plan_line_count: <wc -l output>`
  - `outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]`
  - `notes: |` — short paragraph stating "ready for consolidation" or naming blockers

2. Stage and commit BOTH files in one commit:
```
git add docs/plans/features/ai-autofill/FEATURE_PLAN.md
git add docs/plans/features/_status/ai-autofill.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock ai-autofill feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-ai-autofill-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"
```

3. Push from the worktree:
```
git push -u origin feature/ai-autofill/planning
```

4. Open PR to develop using the most-relevant lead's PR template format (template files at `.github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md`):
```
gh pr create --base develop --head feature/ai-autofill/planning \
  --title "docs(plan): lock ai-autofill feature blueprint" \
  --body "<filled-in template>"
```

5. After PR opens: update your status file ONE MORE TIME — set `status: IN_REVIEW`, fill `pr_number` and `pr_url`. Stage + amend the commit OR push a follow-up commit `docs(plan): update ai-autofill status — IN REVIEW with PR link`.

6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.

## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md
- [ ] Agent lineup table fully filled out (backend 2 + frontend 2 + AI 1 + data 0-or-1 specialists named)
- [ ] Code surfaces table covers every file the feature will create or modify
- [ ] Documentation deliverables enumerated (OpenAPI with fallback_offered semantics, prompt registry entry, golden set fixture, ai_eval gate, V1_FEATURE_SPEC §F4 implemented stamp)
- [ ] One dispatch template per specialist drafted (5-or-6 templates total depending on data)
- [ ] Review + iteration protocol defined (with invalid-enum/recall/cost/UI-error failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/ai-autofill/planning
- [ ] PR opened to develop using AI PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/ai_ops/prompts/autofill_v1.py, backend/app/modules/catalog/, frontend/src/app/pages/catalog-form/autofill/, tests/eval/autofill/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-ai-autofill-{group}-session-{N}` per master plan §4
- The 0% invalid-enum rate target is non-negotiable — any plan that proposes weakening it must be flagged for founder re-ratification before FEATURE_PLAN.md is committed
- Autofill writes ONLY to products.ai_suggestions_jsonb — never directly to products.fields_jsonb. User-accept is the gate. Any dispatch template that omits this rule must be rejected
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend, AI, data) has reviewed their section's dispatch templates
- [ ] PR open to develop using the AI PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- The 0% invalid-enum target and the ≤₹0.05/call cost ceiling are non-negotiable

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
