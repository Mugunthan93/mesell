# Session Dispatch: Fast Catalog Form — Category-Specific Form with Autosave
**Session name:** `mesell-catalog-form-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/catalog-form/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp feature shipped; smart-picker feature shipped (the form lands the seller on the picked category's schema)
**Lead involvement:** Backend (catalog module — central spine — 6 endpoints including autosave coalescing per `MVP_ARCH §11.4`) · Frontend (catalog-form page + reactive form + autosave directive) · AI (the autofill prompt — shared planning surface with the ai-autofill feature) · Data (field aliases extension if a category template references new fields)

---

## Why this session exists
The catalog form is the spine of MeeSell — every product flows through it. It is the most-called module per `BACKEND_ARCHITECTURE.md §2.4` and the hardest V1.5 microservices extraction target per §21. Every other catalog-touching feature (AI Auto-fill, Image Pre-check ownership gate, Live Preview, Price Calculator, XLSX Export) consumes the catalog module's service surface. Getting the contract right here means 4 downstream features can land independently; getting it wrong means re-coordination across every backend lead.

The form also locks the autosave pattern (`PATCH /api/v1/products/{id}` with 5-min audit coalescing, per-IP-only rate limit, queue-and-retry on network drop) and the field schema rendering contract (the `templates.schema_jsonb` envelope per `BACKEND_ARCHITECTURE.md §5A`, with `is_advanced` gating per category). This planning session locks how the form composes against the picker's output, against the autofill seam, against the image uploader's ownership assertions, and against the export validator.

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-catalog-form-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/catalog-form/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the Fast Catalog Form feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for catalog-form. Verify:
pwd                                          # must print /private/tmp/mesell-wt/catalog-form or /tmp/mesell-wt/catalog-form
git worktree list | grep catalog-form      # must show this worktree
git branch --show-current                     # must print feature/catalog-form/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh catalog-form (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates, §6 feature_board, §7 lead responsibilities, §8 shared-code conflict resolution (this feature touches shared catalog code that 4 other features also touch)
- docs/V1_FEATURE_SPEC.md §F3 (Feature 3: Fast Catalog Form) — ≤50 fields, autosave every 10s + on blur, browser reload resumes from last saved state, change-category warning
- docs/BACKEND_ARCHITECTURE.md §10 (catalog module — 6 endpoints POST create / PATCH autosave / POST autofill / GET preview / DELETE soft-delete / GET draft-recover; assert_product_ownership() locked cross-module signature; 10-method service surface incl. 4 cross-module; HARDEST V1.5 extraction target per §21), §5A (Presentation Layer Contract — templates.schema_jsonb envelope with 6 keys, per-field shape with 9 keys, 11-primitive mapping, is_advanced allowlist {group_id}, compliance_shape standard/collapsed, validation_message_id convention), §11.4 (autosave 5-min audit coalescing per-IP-only)
- docs/FRONTEND_ARCHITECTURE.md — catalog-form page lives in mfe-catalog (Phase 2 federation), pre-federation under frontend/src/app/pages/catalog-form/; FieldRendererComponent maps each of 11 primitives; AutosaveDirective wraps the form group
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — catalog is service 8 of 8 (LAST) per BACKEND_ARCHITECTURE.md §16.H because of its in-degree on the cross-module call matrix
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — catalog-form is part of mfe-catalog (5th remote in federation order); pre-federation it sits in the shell
- CLAUDE.md — autosave coalescing decision, JWT-gated route protection, Pydantic v2 + SQLAlchemy 2.0
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md, .claude/agents/meesell-ai-coordinator.md, .claude/agents/meesell-data-engineer.md
- Each involved lead's MEMORY.md
- Each involved lead's docs/status/feature_board_{backend|frontend|ai|data}.md (verify catalog-form is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/catalog-form.yaml instead.

Create (or overwrite) docs/plans/features/_status/catalog-form.yaml with:
feature: "catalog-form"
session: "mesell-catalog-form-planning-session-1"
worktree: "/tmp/mesell-wt/catalog-form"
branch: "feature/catalog-form/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/catalog-form/FEATURE_PLAN.md
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
  Does this feature still match V1 spec §F3? Specifically:
    - ≤50 fields rendered per category schema (first-paint <500ms after schema fetch)
    - Inline help text from XLSX (sourced via field_aliases.help_text — data track owned)
    - Compulsory red-asterisk + form-can-not-proceed if blank
    - Autosave every 10s + on blur via PATCH /api/v1/products/{id}, debounced and per-IP rate-limited
    - Browser reload resumes from last saved state (server-of-record is products.fields_jsonb)
    - Change-category mid-edit shows warning + confirm (V1 behavior: reset fields_jsonb, keep product row id)
    - is_advanced gating: only group_id behind "Advanced fields" toggle for V1 (per ADVANCED_CANONICAL_NAMES allowlist in coordinator memory)
  Does the catalog form scope include autofill UI in V1 OR is autofill a separate feature (ai-autofill)? Per V1_FEATURE_SPEC.md autofill is Feature 4 — this plan covers ONLY the form skeleton + field rendering + autosave; autofill UI integration is planned in the ai-autofill feature dispatch.

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_CATALOG_FORM_ENABLED). Dev default: true. Staging default: false until autosave coalescing is verified under network-flap test + draft-recovery proven on browser reload. Note: because catalog-form is the spine, disabling this flag effectively disables every catalog-creation path — schedule the flag flip to staging carefully.

Decision 3 — Priority ordering vs sibling features
  This feature is the SPINE — 4 downstream features (AI Auto-fill, Image Pre-check ownership gate, Live Preview, XLSX Export) all consume catalog.service.assert_product_ownership(). It must merge to develop before any of those 4 can integration-test against a real product row. Confirm: catalog-form lands second (after auth-otp + smart-picker) and before any catalog-dependent sibling. AI Auto-fill cannot integration-test without a draft product to autofill against.

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | api-routes-builder, services-builder, database-builder | api-routes-builder: 5 catalog routes (POST /products create / PATCH /products/{id} autosave / GET /products/{id}/preview / DELETE /products/{id} soft-delete / GET /products/{id}/draft) + Pydantic schemas (ProductCreate, ProductPatch, ProductResponse, DraftResponse) in modules/catalog/schemas.py. Autofill route POST /products/{id}/autofill is OUT OF SCOPE here — owned by ai-autofill feature. services-builder: 8-method catalog.service surface — create_product, autosave_patch (with 5-min coalescing per §11.4), get_preview, soft_delete, get_draft, assert_product_ownership (cross-module, consumed by image+pricing+dashboard+export), list_products (consumed by dashboard), get_compliance_block_for_product (consumed by export); database-builder: products table + product_drafts table + Alembic migration (products extends the foundation-pass model with fields_jsonb default '{}'::jsonb + soft_delete column + draft revision counter); migration is the linchpin — every sibling feature waits on this migration head |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: CatalogFormComponent (page) + FieldRendererComponent (presentational, maps each of 11 primitives per §5A.B) + AutosaveDirective (debounce + on-blur trigger), under frontend/src/app/pages/catalog-form/; reactive form built from category schema fetched on init; compulsory-fields validator; change-category warning dialog; angular-service-builder: CatalogService.create / autosave / getDraft methods wrapping HttpClient; offline queue with retry on reconnect (network-drop edge case from V1_FEATURE_SPEC §F3) |
| meesell-ai-coordinator | (no work in this feature scope) | Autofill is its own feature (ai-autofill). Confirm with AI lead that no autofill code lands in catalog-form planning scope. |
| meesell-data-engineer | xlsx-parser (only if a category schema references a field with no help_text in field_aliases) | xlsx-parser: extend field_aliases.json with missing help_text entries for any category referenced by the smart-picker shipped surface — verify by sweeping the 50 hand-labeled descriptions' picked categories and confirming each fields[].canonical_name has a help_text row |

Only include leads + specialists who actually have work. Omit empty rows.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/catalog/routes.py (NEW or MODIFY), app/modules/catalog/schemas.py (NEW or MODIFY), app/modules/catalog/service.py (NEW or MODIFY), app/modules/catalog/repository.py (NEW or MODIFY), app/shared/models/product.py (MODIFY — extend foundation-pass model with fields_jsonb + draft + soft_delete columns), app/shared/models/product_draft.py (NEW — draft revision table for browser-reload resume), app/alembic/versions/<rev>_catalog_form.py (NEW migration), app/core/audit.py (MODIFY — add product.autosave audit event with 5-min coalescing helper per §11.4), backend/tests/test_catalog_unit.py (NEW), backend/tests/test_catalog_form_integration.py (NEW — autosave + draft-recovery + change-category flow)
- Frontend: frontend/src/app/pages/catalog-form/catalog-form.component.ts (NEW), frontend/src/app/pages/catalog-form/field-renderer.component.ts (NEW), frontend/src/app/pages/catalog-form/autosave.directive.ts (NEW), frontend/src/app/services/catalog.service.ts (NEW or MODIFY — add create/autosave/getDraft), frontend/src/app/app.routes.ts (MODIFY — register /catalogs/:id/edit route), frontend/src/app/pages/catalog-form/catalog-form.component.spec.ts (NEW)
- AI: NONE (autofill handled separately)
- Data: backend/app/data/field_aliases.json (MODIFY if missing help_text rows surface during smart-picker sweep — sweep is part of Step 1 verification)
- Infra: NONE (no new secrets; catalog uses same DB + Valkey as auth)
- Docs: docs/V1_FEATURE_SPEC.md §F3 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §10 sentinel flip, docs/MVP_ARCHITECTURE.md §11.4 cross-link to catalog.service.autosave_patch implementation, OpenAPI regenerated for the 5 catalog routes (per backend PR template)

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entries for 5 catalog routes (POST create / PATCH autosave / GET preview / DELETE soft-delete / GET draft); inline service-method docstrings on every cross-module surface (assert_product_ownership, list_products, get_compliance_block_for_product) with consumer reference per §16.A
- Frontend: route entry comment in app.routes.ts; CatalogFormComponent docstring describing the schema-fetch → reactive-form-build → autosave-cycle → draft-recovery flow; AutosaveDirective docstring on debounce + on-blur + retry semantics
- AI: N/A
- Data: field_aliases.json schema version bump (in data lead's MEMORY.md note) if rows added
- Infra: N/A
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F3 marked "implemented YYYY-MM-DD" with PR link; cross-module call sites added to tests/lint/import_rules.toml per §16.G

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-catalog-form-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., database-builder reads §10.D + MVP_ARCH §2.6 migration ordering + the foundation-pass product model state; services-builder reads §10.C + §11.4 + the cross-module signature lock at §10.A)
- Acceptance criteria (specific to that specialist's slice — e.g., services-builder: autosave_patch coalescing helper passes the 5-min window test in backend/tests/test_audit_coalescing.py; assert_product_ownership rejects cross-tenant access with IamError; 8 method signatures match §10.C verbatim)
- Hard constraints (e.g., NO direct adapters/gemini.py imports in catalog module; autosave route handler MUST use per-IP rate limit not per-user per §11.4; cross-module calls go via service.py PUBLIC surfaces only per §16.A)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch
- Final report format

Specialists to template:
- meesell-api-routes-builder (backend lead dispatches)
- meesell-services-builder (backend lead dispatches)
- meesell-database-builder (backend lead dispatches — the migration is the linchpin)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)
- meesell-xlsx-parser (data lead dispatches IF the help_text sweep finds gaps — otherwise omit)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., backend lead checks: assert_product_ownership signature matches §10.A verbatim — every sibling feature will call this method; autosave coalescing test passes; migration is reversible — alembic downgrade -1 + upgrade head + downgrade -1 produces no row drops; OpenAPI shapes match the FieldRendererComponent's expected schema)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/backend.md` (migration evidence section MUST be populated — upgrade tested + downgrade tested + alembic head diverge check)
- What triggers a re-dispatch (specific failure modes — autosave fires more than once per debounce window → re-dispatch frontend with "verify AutosaveDirective debounce is on the form-group valueChanges not individual field blur"; draft recovery returns stale fields_jsonb → re-dispatch backend with "verify GET /products/{id}/draft reads from product_drafts not products.fields_jsonb"; change-category leaves orphaned fields → re-dispatch services-builder with "verify category-change clears fields_jsonb atomically")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/catalog-form/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., migration head divergence between dev and staging because of the catalog migration's parent revision, autosave hammering Postgres under network-flap retry, change-category UX losing seller data, FieldRendererComponent failing on unmapped primitives in V1.5 category additions, downstream sibling features racing the catalog-form merge)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/catalog-form/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/catalog-form.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/catalog-form/FEATURE_PLAN.md
git add docs/plans/features/_status/catalog-form.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock catalog-form feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-catalog-form-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/catalog-form/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/catalog-form/planning \
  --title "docs(plan): lock catalog-form feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update catalog-form status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md
- [ ] Agent lineup table fully filled out (backend 3 + frontend 2 + data 0-or-1 specialists named; AI explicitly omitted)
- [ ] Code surfaces table covers every file the feature will create or modify
- [ ] Documentation deliverables enumerated (OpenAPI, cross-module signature docstrings, V1_FEATURE_SPEC §F3 implemented stamp, MVP_ARCH §11.4 cross-link, import_rules.toml entries)
- [ ] One dispatch template per specialist drafted (5-or-6 templates total depending on data)
- [ ] Review + iteration protocol defined (with autosave/draft-recovery/change-category failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/catalog-form/planning
- [ ] PR opened to develop using backend PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/catalog/, frontend/src/app/pages/catalog-form/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-catalog-form-{group}-session-{N}` per master plan §4
- The assert_product_ownership cross-module signature is the contract — every dispatch template MUST cite §10.A and forbid any rename or signature variation
- Autofill UI work is OUT OF SCOPE — flag and redirect any planning content that drifts into autofill to the ai-autofill feature dispatch
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend, data) has reviewed their section's dispatch templates
- [ ] PR open to develop using the backend PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- The catalog migration is the linchpin — any plan that ships catalog-form without a reversible, head-converged migration must be rejected

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
