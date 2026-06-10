# Session Dispatch: Live Product Preview — Real-time Meesho-Style Render Before Publish
**Session name:** `mesell-live-preview-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/live-preview/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp shipped; catalog-form shipped (preview reads from products.fields_jsonb via catalog.service.get_preview); image-precheck shipped (preview shows uploaded images via image.service.get_image_urls, the cross-module surface locked at `BACKEND_ARCHITECTURE.md §11.C`)
**Lead involvement:** Backend (catalog preview endpoint — likely a GET on existing catalog routes per `BACKEND_ARCHITECTURE.md §10`) · Frontend (3 preview components — feed thumbnail / detail page / mobile card — Meesho CSS clone; this is a frontend-heavy feature with thin backend surface)

---

## Why this session exists
Live Product Preview is MeeSell's UX trust signal — no competitor (per `VALIDATED_PAIN_POINTS.md` theme T4 IMAGE PREVIEW MISSING) shows the seller what their listing will look like on Meesho before they upload. It is the lightest-backend feature in V1 (3h backend per `V1_FEATURE_SPEC §7` vs 10h frontend) because the heavy lifting is faithfully cloning Meesho's feed/detail/mobile CSS conventions and computing the ~30-char mobile title truncation marker. The backend surface is a thin read-only composition that the catalog module already partially exposes (`get_preview` is method 4 of the 10-method catalog service per `BACKEND_ARCHITECTURE.md §10.C`).

This planning session is the smallest cross-domain coordination on V1: backend confirms `get_preview` shape matches the frontend's three components' expectations, frontend builds the three Meesho-style components against a stable response, no AI or data or infra involvement. Getting it right is mostly a frontend visual-diff exercise. Getting it wrong (e.g., truncation marker at the wrong character index, image carousel breaking on mobile swipe) is a credibility hit because the whole point of the feature is "see what Meesho will show".

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-live-preview-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/live-preview/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the Live Product Preview feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for live-preview. Verify:
pwd                                          # must print /private/tmp/mesell-wt/live-preview or /tmp/mesell-wt/live-preview
git worktree list | grep live-preview      # must show this worktree
git branch --show-current                     # must print feature/live-preview/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh live-preview (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates (especially §5.3 frontend template — screenshot evidence at 360px + 1280px widths is the critical acceptance signal), §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F6 (Feature 6: Live Product Preview) — 3 views (feed thumbnail / product detail / mobile card), preview within 1s after page load, title truncation at ~30 chars on mobile, image carousel with swipe, "fill required fields" CTA when <1 image or title missing, qualitative visual-diff ≤10% vs real Meesho (founder manual check)
- docs/BACKEND_ARCHITECTURE.md §10 (catalog module — get_preview is method 4 of the 10-method service surface per §10.C; preview-transformation logic may be backend OR pure frontend; the GET /api/v1/products/{id}/preview endpoint is one of the 6 endpoints in the §0.C contract; PreviewResponse Pydantic shape composes products.fields_jsonb + first product_image url + category context)
- docs/FRONTEND_ARCHITECTURE.md — preview components live in mfe-catalog (Phase 2 federation); pre-federation under frontend/src/app/pages/preview/ with sub-components feed-card, detail-page, mobile-card; Meesho CSS clone scoped to a single SCSS file with token references to design-tokens layer
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — preview is part of catalog (8) extraction; no separate service
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — preview is part of mfe-catalog (5th remote); pre-federation in the shell
- CLAUDE.md — OnPush change detection convention, async pipe for HTTP, Tailwind + Material guidelines (Meesho-clone CSS is a one-off styled SCSS file, not a Tailwind class explosion; document the exception)
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md
- Each involved lead's MEMORY.md
- Each involved lead's docs/status/feature_board_{backend|frontend}.md (verify live-preview is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/live-preview.yaml instead.

Create (or overwrite) docs/plans/features/_status/live-preview.yaml with:
feature: "live-preview"
session: "mesell-live-preview-planning-session-1"
worktree: "/tmp/mesell-wt/live-preview"
branch: "feature/live-preview/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/live-preview/FEATURE_PLAN.md
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
  Does this feature still match V1 spec §F6? Specifically:
    - 3 views: feed thumbnail (the marketplace card seen in lists), product detail page (the full PDP), mobile card (the mobile-app-style render)
    - All three render within 1s after page load
    - Title truncation marker at ~30 chars on the feed thumbnail (matches Meesho mobile listing-card truncation)
    - Image carousel shows uploaded order; mobile swipe works
    - Placeholder + "fill required fields" CTA when <1 image OR title missing
    - V1 limitation: variant swatches show first variant only (full variant matrix deferred to V1.5)
    - V1 limitation: descriptions truncated at 200 chars in detail preview
    - Visual diff vs real Meesho ≤10% (qualitative — manual founder check, no automated regression bar in V1)
  Also resolve: Is the preview-transformation logic in the backend (PreviewResponse shape pre-shaped for the 3 views) OR in the frontend (PreviewResponse is the raw catalog row + image list, transformation happens in 3 component getters)? Recommendation: backend returns a structured PreviewResponse with explicit fields {title_full, title_truncated_30, description_full, description_truncated_200, mrp, meesho_price, first_image_url, image_carousel_urls, variant_swatches}; frontend renders against the structured shape. Confirm or override.

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_LIVE_PREVIEW_ENABLED). Dev default: true. Staging default: true after a single round of founder visual-diff approval against a real Meesho listing (no automated gate — qualitative). When disabled, GET /api/v1/products/{id}/preview returns 404 and the /catalogs/:id/preview route shows a "Preview unavailable" placeholder.

Decision 3 — Priority ordering vs sibling features
  This feature touches:
    - Backend per-module code: app/modules/catalog/service.py — get_preview method which catalog-form's services-builder may have already scaffolded; this dispatch adds the PreviewResponse shape on top
    - Backend cross-module call: image.service.get_image_urls() (consumed only, the cross-module signature locked at §11.C — no contention)
    - Frontend per-feature code: frontend/src/app/pages/preview/ — greenfield, no contention
  Confirm: live-preview ships after catalog-form AND image-precheck (both are read dependencies). It can ship in parallel with price-calculator (no contention).

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | api-routes-builder, services-builder | api-routes-builder: GET /api/v1/products/{id}/preview route (if not already added in catalog-form dispatch — verify with catalog-form PR) + PreviewResponse Pydantic schema with the structured shape from Decision 1 (title_full, title_truncated_30, description_full, description_truncated_200, mrp, meesho_price, first_image_url, image_carousel_urls, variant_swatches); services-builder: catalog.service.get_preview(product_id, user_id) — calls image.service.get_image_urls + reads products.fields_jsonb + categories context + computes truncation indices; returns PreviewResponse; database-builder NOT involved (read-only composition, no new tables) |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder, angular-ui-styler | angular-component-builder: 3 components under frontend/src/app/pages/preview/ — FeedThumbnailComponent (Meesho marketplace card), DetailPageComponent (full PDP render), MobileCardComponent (mobile-app card); all standalone, OnPush, render against PreviewResponse signal; image carousel with mobile swipe (Angular CDK gestures or native touch events); placeholder CTAs when fields missing; angular-service-builder: PreviewService.get(productId) wrapping HttpClient call against GET /products/{id}/preview; auto-refresh on form-save signal so preview reflects latest fields_jsonb without manual reload; angular-ui-styler: single Meesho-clone SCSS file (frontend/src/app/pages/preview/preview.scss) with documented Meesho design-language clone (typography scale, card shadow, badge colors); references design-tokens for any token-shared concerns; document Tailwind-exception rationale in the SCSS file header |
| meesell-ai-coordinator | (no work) | Preview is non-AI. Confirm. |
| meesell-data-engineer | (no work) | Confirm. |
| meesell-infra-builder | (no work) | Confirm — no new secrets, no new buckets, no manifest changes. |

Only include leads + specialists who actually have work. Omit empty rows.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/catalog/routes.py (MODIFY only if /preview route wasn't added in catalog-form dispatch — verify first), app/modules/catalog/schemas.py (MODIFY — add PreviewResponse + sub-shapes), app/modules/catalog/service.py (MODIFY — add or finalize get_preview method per Decision 1), backend/tests/test_catalog_unit.py (MODIFY — preview shape tests with mocked image.service), backend/tests/test_live_preview_integration.py (NEW — preview end-to-end with real image rows)
- Frontend: frontend/src/app/pages/preview/preview.component.ts (NEW — page container that switches between 3 views), frontend/src/app/pages/preview/feed-thumbnail.component.ts (NEW), frontend/src/app/pages/preview/detail-page.component.ts (NEW), frontend/src/app/pages/preview/mobile-card.component.ts (NEW), frontend/src/app/pages/preview/preview.scss (NEW — Meesho-clone styles), frontend/src/app/services/preview.service.ts (NEW), frontend/src/app/app.routes.ts (MODIFY — register /catalogs/:id/preview route), frontend/src/app/pages/preview/preview.component.spec.ts (NEW — including the title truncation index test against the locked ~30 char rule)
- AI: NONE
- Data: NONE
- Infra: NONE
- Docs: docs/V1_FEATURE_SPEC.md §F6 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §10 sentinel reaffirmed (no spec changes — get_preview was already in the 10-method service surface), OpenAPI regenerated for the PreviewResponse shape

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entry for GET /api/v1/products/{id}/preview with PreviewResponse shape including the title_truncated_30 / description_truncated_200 fields documented (call out that truncation is server-side for consistency across components); inline service-method docstring on get_preview describing the cross-module call to image.service.get_image_urls per §16.A
- Frontend: route entry comment in app.routes.ts; PreviewComponent docstring describing the view-switching logic (feed / detail / mobile); FeedThumbnailComponent docstring documenting the locked ~30-char title truncation contract; preview.scss header documenting Tailwind-exception rationale + Meesho design-language clone reference
- AI: N/A
- Data: N/A
- Infra: N/A
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F6 marked "implemented YYYY-MM-DD" with PR link; founder visual-diff approval screenshot pair (MeeSell preview vs real Meesho listing for the same product) attached to the merge PR per §F6 acceptance criterion

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-live-preview-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., angular-ui-styler reads V1_FEATURE_SPEC §F6 + CLAUDE.md frontend conventions + the founder-provided Meesho screenshot references; services-builder reads §10.C get_preview signature + §11.C image.service.get_image_urls cross-module surface)
- Acceptance criteria (specific to that specialist's slice — e.g., services-builder: get_preview returns PreviewResponse with title_truncated_30 computed server-side; angular-component-builder: 3 components render within 1s on initial load + swipe works on touch devices; angular-ui-styler: visual diff against real Meesho ≤10% by founder qualitative check, screenshots committed to PR)
- Hard constraints (e.g., title truncation is SERVER-SIDE only — frontend renders title_truncated_30 verbatim, no client-side truncation; image carousel uses uploaded slot order — image.service.get_image_urls returns in slot-index order)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch
- Final report format (visual screenshots at 360px + 1280px, 1s-load measurement, swipe test result)

Specialists to template:
- meesell-api-routes-builder (backend lead dispatches)
- meesell-services-builder (backend lead dispatches)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)
- meesell-angular-ui-styler (frontend lead dispatches — the Meesho CSS clone is the key value)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., backend lead checks: title_truncated_30 = title_full[:30] with no UTF-8 split — verify multibyte chars truncated at character not byte boundary; description_truncated_200 same; PreviewResponse shape matches frontend's expected fields; frontend lead checks: visual diff screenshots attached; ~30-char truncation marker visible in feed thumbnail; image carousel swipe works on touch device; OnPush change detection on all 3 components)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/frontend.md` (Visual evidence section requires screenshots at 360px + 1280px; accessibility checks for keyboard nav on the carousel) + `.github/PULL_REQUEST_TEMPLATE/backend.md` for the get_preview contract
- What triggers a re-dispatch (specific failure modes — title truncation splits UTF-8 character → re-dispatch services-builder with "use [:30] on str type after .encode/.decode roundtrip or use a unicode-safe slicer"; preview render >1s → re-dispatch frontend with "verify CDK gestures lazy-loaded, image preload sizing matches displayed pixel ratio"; visual diff >10% → re-dispatch angular-ui-styler with "Previous diff failed on {area} — examine: card shadow, badge colors, typography weights; reference the founder's annotated Meesho screenshot at <attached path>"; carousel doesn't swipe → re-dispatch with "verify HammerJS or @angular/cdk drag listener attached to scroll container")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3 — but visual-diff iterations may need a higher cap because qualitative — adjust to 4 with founder consent)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/live-preview/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., Meesho changing their feed-card design mid-V1 making the clone stale, mobile swipe failing on iOS Safari due to gesture handling, image preload bandwidth blowing the 1s render budget on slow 3G, title truncation edge cases on emoji/RTL/combining-character strings, V1 single-variant limit becoming the support-load top complaint)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/live-preview/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/live-preview.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/live-preview/FEATURE_PLAN.md
git add docs/plans/features/_status/live-preview.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock live-preview feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-live-preview-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/live-preview/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/live-preview/planning \
  --title "docs(plan): lock live-preview feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update live-preview status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md (including the server-side-truncation Decision 1 resolution)
- [ ] Agent lineup table fully filled out (backend 2 + frontend 3 specialists named; AI / data / infra explicitly omitted)
- [ ] Code surfaces table covers every file the feature will create or modify
- [ ] Documentation deliverables enumerated (OpenAPI with truncation field semantics, Meesho-clone SCSS header doc, V1_FEATURE_SPEC §F6 implemented stamp, founder visual-diff screenshots attached to merge PR)
- [ ] One dispatch template per specialist drafted (5 templates total)
- [ ] Review + iteration protocol defined (with truncation / render-budget / visual-diff / swipe failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/live-preview/planning
- [ ] PR opened to develop using frontend PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/catalog/, frontend/src/app/pages/preview/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-live-preview-{group}-session-{N}` per master plan §4
- Server-side title truncation is the contract — any dispatch template that allows client-side truncation must be rejected (consistency across 3 components depends on it)
- The Tailwind-exception SCSS file is locked to preview.scss only — do not extend the exception to other feature components
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend) has reviewed their section's dispatch templates
- [ ] PR open to develop using the frontend PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- The server-side title truncation contract is non-negotiable — the consistency depends on it

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
