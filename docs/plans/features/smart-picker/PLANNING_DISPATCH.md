# Session Dispatch: Smart Category Picker — Description → Top 3 Meesho Categories
**Session name:** `mesell-smart-picker-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/smart-picker/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp feature shipped (every Smart Picker call is JWT-gated)
**Lead involvement:** Backend (category module /suggest endpoint + read-only categories table) · Frontend (Smart Picker page + service) · AI (smart_picker.v1 prompt + golden set + tree compression + top-3 ranker + confidence calibration + ILIKE fallback) · Data (only if category seed needs a refresh — typically not for V1)

---

## Why this session exists
Smart Category Picker is MeeSell's signature differentiator AI feature — no Meesho-adjacent tool ships a description→top-3-leaves picker over the 3,772-leaf category tree. It is the first AI seam in the platform and the test bed for the `ai_ops` infrastructure (per `BACKEND_ARCHITECTURE.md §6A`): cost tracking (≤₹0.05/call hard ceiling per `MVP_ARCH §8.2`), 3-layer guardrail, ₹500 daily budget cap with graceful fallback returning 200 + empty suggestions, single-flight cache helper, golden eval set with ≥80% top-5 recall target.

Getting Smart Picker right means the AI infrastructure works for the next 2 AI features (Auto-fill, Watermark check). Getting it wrong means re-architecting `ai_ops/client.py` mid-V1. This planning session locks the contract between backend route, `ai_ops` seam, prompt registry version, golden set fixture path, ILIKE fallback semantics, and the frontend's display of confidence + commission% per card.

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-smart-picker-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/smart-picker/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the Smart Category Picker feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for smart-picker. Verify:
pwd                                          # must print /private/tmp/mesell-wt/smart-picker or /tmp/mesell-wt/smart-picker
git worktree list | grep smart-picker      # must show this worktree
git branch --show-current                     # must print feature/smart-picker/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh smart-picker (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates (especially the AI template at §5.4 — eval evidence + cost analysis + guardrail compliance), §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F2 (Feature 2: Smart Category Picker) — top-3 within 3s P95, ≥80% top-3 hit rate on 50 hand-labeled seed descriptions, ILIKE fallback path, English-only V1
- docs/BACKEND_ARCHITECTURE.md §6A (AI Operations Layer — client.py 9-step flow, cost_tracker.py, guardrail.py 3 layers, budget_cap.py 80%-alarm/100%-hard-stop, prompt_registry.py, eval.py with smart_picker golden set ≥80% top-5 recall target), §9 (category module — 5 endpoint surfaces including /suggest, 8-method service surface, global-cache pre-warm at worker startup, single-flight on /field-enum)
- docs/FRONTEND_ARCHITECTURE.md — Smart Picker page lives in mfe-catalog (Phase 2 federation), pre-federation: standalone component under frontend/src/app/pages/smart-picker/
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — category is service 6 of 8 in extraction order (per BACKEND_ARCHITECTURE.md §16.H)
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — Smart Picker page is part of mfe-catalog (5th remote in federation order); pre-federation it sits in the shell
- CLAUDE.md — Gemini 2.5 Flash decision, Valkey DB 0 routing, ₹500/day AI budget
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md, .claude/agents/meesell-ai-coordinator.md, .claude/agents/meesell-data-engineer.md
- Each involved lead's MEMORY.md
- Each involved lead's docs/status/feature_board_{backend|frontend|ai|data}.md (verify smart-picker is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/smart-picker.yaml instead.

Create (or overwrite) docs/plans/features/_status/smart-picker.yaml with:
feature: "smart-picker"
session: "mesell-smart-picker-planning-session-1"
worktree: "/tmp/mesell-wt/smart-picker"
branch: "feature/smart-picker/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/smart-picker/FEATURE_PLAN.md
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
  Does this feature still match V1 spec §F2? Specifically:
    - Top-3 leaves (not top-5)
    - English-only descriptions (Hindi/Tamil pass-through to Gemini as-is, no enforcement; multilingual handling deferred to V1.5)
    - Manual tree-search fallback path exists if none of the top-3 match
    - Per-card display: full path + commission_pct + sample attributes
    - ILIKE fallback over categories.name on Gemini timeout or budget exhaustion (returning 200 + suggestions populated by trigram match, NOT 503)
    - Cost ceiling ≤₹0.05 per call (per MVP_ARCH §8.2 + §6A.F)
  Any cuts, additions, or scope flexes since the spec was locked?

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_SMART_PICKER_ENABLED). Dev default: true. Staging default: false until the golden set passes ≥80% top-5 recall and per-call cost averages ≤₹0.05 in 24-hour staging soak. When disabled, /api/v1/categories/suggest returns 404 per master plan §3.2 backend rule.

Decision 3 — Priority ordering vs sibling features
  This feature touches:
    - Backend shared code: app/ai_ops/* (3 AI features share this layer — Smart Picker, Auto-fill, Watermark check). Smart Picker is the first AI workload to ship, so it shapes the ai_ops contract. Auto-fill and Image Pre-check rebase onto Smart Picker's ai_ops surface.
    - Backend per-module code: app/modules/category/ (Smart Picker is the only V1 feature that writes to this module; other features only read).
    - Frontend shared code: AuthService (every page needs login) — no contention.
  Suggested ordering: smart-picker ships FIRST among AI features (its merge to develop unblocks ai-autofill's planning to finalize). Confirm or override.

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | api-routes-builder, services-builder, database-builder | api-routes-builder: GET /api/v1/categories/suggest route + Pydantic SuggestRequest/SuggestResponse schemas in modules/category/schemas.py; services-builder: category.service.suggest() orchestration — calls ai_ops.client.call_gemini("smart_picker.v1") with budget reservation, applies ILIKE fallback on BudgetExceededError, single-flight per cache key, returns top-3 with confidence + commission_pct + sample attributes; database-builder: read-only repository methods for categories table (already seeded per data track) — NO new tables, NO migration (categories table exists from foundation pass) |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: SmartPickerComponent (page) + CategoryCardComponent (presentational) under frontend/src/app/pages/smart-picker/ — reactive form for description, debounced suggest call, 3 cards with path + confidence% + commission% display, fallback CTA to manual tree search; angular-service-builder: CategoryService.suggest(description) wrapping HttpClient call, error handling for ILIKE-fallback case (UI shows "Quick match" badge when AI returns empty + ILIKE populated suggestions) |
| meesell-ai-coordinator | prompt-engineer, category-picker-builder | prompt-engineer: smart_picker.v1 prompt file at backend/app/ai_ops/prompts/smart_picker_v1.py — system prompt with category-tree compression strategy, few-shot examples covering 5 high-traffic super-categories (Fashion, Home, Beauty, Kitchen, Kids), JSON-mode output schema, Layer 1 guardrail prefix; category-picker-builder: full pipeline — tree compression algo (3,772 leaves → ≤8k tokens), top-3 ranker with confidence calibration, golden set fixture at tests/eval/smart_picker/golden_set.json (50 hand-labeled descriptions per V1_FEATURE_SPEC §F2), eval runner at tests/eval/smart_picker/test_recall.py |
| meesell-data-engineer | (only if categories seed refresh needed) | scraper-maintainer: re-run Meesho category scraper IF the existing seed (3,772 leaves locked) has gone stale by the time this feature ships — verify with a row-count and meesho_id-checksum diff against the live seed file first. Default: no work — categories table is already seeded from the foundation pass. |

Only include leads + specialists who actually have work. Omit empty rows.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/category/routes.py (MODIFY — add /suggest), app/modules/category/schemas.py (MODIFY — add SuggestRequest/SuggestResponse + CategorySuggestion shapes), app/modules/category/service.py (MODIFY — add suggest() method), app/modules/category/repository.py (MODIFY — add ilike_search_for_fallback method), app/ai_ops/client.py (NO CHANGE — already exposes call_gemini per §6A.A; verify smart_picker workload literal is registered), app/ai_ops/prompts/smart_picker_v1.py (NEW), backend/tests/test_category_unit.py (MODIFY — suggest service tests), backend/tests/test_smart_picker_integration.py (NEW), tests/eval/smart_picker/golden_set.json (NEW), tests/eval/smart_picker/test_recall.py (NEW)
- Frontend: frontend/src/app/pages/smart-picker/smart-picker.component.ts (NEW), frontend/src/app/pages/smart-picker/category-card.component.ts (NEW), frontend/src/app/services/category.service.ts (NEW or MODIFY if scaffold exists — add suggest method), frontend/src/app/app.routes.ts (MODIFY — register /catalogs/new route), frontend/src/app/pages/smart-picker/smart-picker.component.spec.ts (NEW)
- AI: backend/app/ai_ops/prompts/smart_picker_v1.py (NEW — content authored by prompt-engineer), tests/eval/smart_picker/golden_set.json (NEW — 50 hand-labeled descriptions), tests/eval/smart_picker/test_recall.py (NEW — pytest eval runner gating CI gate "ai_eval")
- Data: NONE in default case (categories seed already loaded); IF stale, scripts/seed_categories.py (MODIFY) + new seed input file
- Infra: NONE (no new secrets; GEMINI_API_KEY and ai_ops budget already provisioned for the iam dispatch)
- Docs: docs/V1_FEATURE_SPEC.md §F2 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §9 sentinel flip (LOCKED-on-paper → LOCKED-on-disk via PR link)

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entry for GET /api/v1/categories/suggest — query params (q description ≥10 chars), response shape (top-3 array with path/confidence/commission_pct/sample_attributes), error responses (422 description too short, 200 with empty + fallback_offered=true when budget exceeded)
- Frontend: route entry comment in app.routes.ts; SmartPickerComponent inline docstring describing the debounce + ILIKE-fallback rendering path
- AI: prompt registry entry — smart_picker.v1 registered in ai_ops/prompt_registry.py with file path reference; golden set fixture path documented in tests/eval/README.md; eval runner instructions for local + CI ai_eval gate
- Data: N/A in default case
- Infra: N/A
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F2 marked "implemented YYYY-MM-DD" with PR link; ai_eval CI gate added to .github/workflows/ci.yml referencing tests/eval/smart_picker/

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-smart-picker-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., prompt-engineer reads §6A.G + §6A.E + the 50-description golden set; category-picker-builder reads §6A.A + the tree-compression rationale in §9.B)
- Acceptance criteria (specific to that specialist's slice — e.g., prompt-engineer: smart_picker.v1 file exists, JSON-mode output schema validates against SuggestResponse, eval runner passes ≥80% top-5 recall; category-picker-builder: tree compression produces ≤8k tokens, top-3 ranker confidence calibration error <10% on golden set, ILIKE fallback returns within 200ms P95)
- Hard constraints (e.g., NO direct adapters/gemini.py import — only ai_ops.client; NO eval data leakage into prompt few-shots)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch
- Final report format (cost-per-call measurement, golden-set recall %, P95 latency)

Specialists to template:
- meesell-api-routes-builder (backend lead dispatches)
- meesell-services-builder (backend lead dispatches)
- meesell-database-builder (backend lead dispatches — minimal: read-only repo method)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)
- meesell-prompt-engineer (ai lead dispatches)
- meesell-category-picker-builder (ai lead dispatches)
- meesell-scraper-maintainer (data lead dispatches IF stale-seed check fails — otherwise omit)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., AI lead checks: per-call cost ≤₹0.05 measured via LangFuse trace + cost_tracker; recall ≥80% on golden set; no eval contamination in few-shots; Layer 1 prefix preserved; JSON-mode output validates against the Pydantic SuggestResponse model)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/ai.md` (eval evidence section MUST be populated; cost analysis section MUST show ≤₹0.05/call)
- What triggers a re-dispatch (specific failure modes — golden-set recall <80% → re-dispatch prompt-engineer with "Previous run failed recall at X%; common miss pattern is Y; revisit few-shots for Z super-category"; cost >₹0.05 → re-dispatch with "Previous run cost ₹Y/call; tree compression token count was Z; tighten compression or downgrade few-shot count"; ILIKE fallback returns >1s → re-dispatch services-builder with "verify pg_trgm GIN index is hit per EXPLAIN ANALYZE")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3 — escalate after 3 because AI iteration cost adds up against the daily budget)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/smart-picker/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., golden-set drift as Meesho category tree evolves, ILIKE fallback recall noticeably lower than AI path causing UX downgrade signal, ₹500 daily cap hitting at peak hours producing fallback storms, tree compression breaking on new super-category additions, JSON-mode regression in Gemini 2.5 Flash forcing prompt rewrite)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/smart-picker/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/smart-picker.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/smart-picker/FEATURE_PLAN.md
git add docs/plans/features/_status/smart-picker.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock smart-picker feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-smart-picker-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/smart-picker/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/smart-picker/planning \
  --title "docs(plan): lock smart-picker feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update smart-picker status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md
- [ ] Agent lineup table fully filled out (backend 3 + frontend 2 + AI 2 + data 0-or-1 specialists named)
- [ ] Code surfaces table covers every file the feature will create or modify
- [ ] Documentation deliverables enumerated (OpenAPI, prompt registry entry, golden set fixture, ai_eval gate, V1_FEATURE_SPEC §F2 implemented stamp)
- [ ] One dispatch template per specialist drafted (7-or-8 templates total depending on data)
- [ ] Review + iteration protocol defined (with recall/cost/latency failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/smart-picker/planning
- [ ] PR opened to develop using AI PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/category/, backend/app/ai_ops/prompts/, frontend/src/app/pages/smart-picker/, tests/eval/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-smart-picker-{group}-session-{N}` per master plan §4
- Every AI specialist dispatch template MUST cite BACKEND_ARCHITECTURE.md §6A (ai_ops layer) — direct adapters/gemini.py usage is forbidden per §6A.A
- The golden-set fixture must not be committed before the ≥80% top-5 recall target is empirically validated (re-iterate prompt until it passes; do not lower the target)
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
- The ≥80% top-5 recall target and the ≤₹0.05/call cost ceiling are non-negotiable — any plan that proposes weakening them must be flagged for founder re-ratification before FEATURE_PLAN.md is committed

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
