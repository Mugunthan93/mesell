# Session Dispatch: XLSX Export — Meesho-Compliant Catalog Export with Image ZIP
**Session name:** `mesell-xlsx-export-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/xlsx-export/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp shipped; catalog-form shipped (export reads from products.fields_jsonb + assert_product_ownership); image-precheck shipped (export reads image bytes via `image.service.get_image_bytes` and validates precheck status=pass per `BACKEND_ARCHITECTURE.md §11.C` + §14)
**Lead involvement:** Backend (export module + Celery worker for XLSX build — service 1 of 8 in extraction order per §16.H — easiest extraction) · Frontend (export page + status poll + download) · Data (ComplianceStrategy variants + golden roundtrip fixture — owns the Meesho-evolving template shapes)

---

## Why this session exists
XLSX Export closes the loop. Without export, sellers cannot ship anything to Meesho — the platform's whole purpose collapses. It is the only V1 feature with a **golden roundtrip test** (CI gate 5 per `MASTER_PLAN §2.1`) that must pass on every backend PR to `develop` because the Meesho template format is the contract: produce an XLSX that opens cleanly in Excel + LibreOffice with column order matching Meesho's category-specific template AND image ZIP filenames matching the XLSX image-reference column.

The export module is structurally interesting because:
- It is **service 1 of 8** in microservices extraction order per `BACKEND_ARCHITECTURE.md §16.H` — the easiest extraction because it owns 1 table + 1 worker + minimal cross-module calls.
- It has the **Layer 3 guardrail** per `BACKEND_ARCHITECTURE.md §6A.C` (Export Adapter validation) — the final compliance check before the XLSX hits the seller's download.
- It uses the **ComplianceStrategy pattern** owned by the data engineer track per `MEMORY.md` references to MEESHO_CATEGORY_INTELLIGENCE — the data track owns the evolving Meesho template shapes (different super-categories have different XLSX schemas; FSSAI categories have compulsory food-safety columns; non-FSSAI categories don't).
- It uses the **async 202+poll pattern** mirroring image-precheck per `MVP_ARCH §5.5.10` (≤30s for 1 product with 6 images).

This planning session locks the seam between data's ComplianceStrategy variants, backend's export orchestration, and the golden roundtrip fixture. Getting it right means downstream V1.5 bulk-export ships cleanly; getting it wrong means the seller's XLSX bounces from the Meesho supplier panel.

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-xlsx-export-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/xlsx-export/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the XLSX Export feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for xlsx-export. Verify:
pwd                                          # must print /private/tmp/mesell-wt/xlsx-export or /tmp/mesell-wt/xlsx-export
git worktree list | grep xlsx-export      # must show this worktree
git branch --show-current                     # must print feature/xlsx-export/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh xlsx-export (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow (including CI gate 5 golden_roundtrip — required for any PR touching export), §4 session naming, §5 PR templates (especially §5.5 data template — golden roundtrip evidence + ComplianceStrategy variants), §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F9 (Feature 9: XLSX Export) — generated XLSX opens in Excel + LibreOffice, column order matches Meesho category-specific template, image ZIP filenames match XLSX image-reference column, generation ≤15s for 1 product with 6 images, validation blocks export with clear error list (Title missing, 2 images missing), category XLSX template missing → 422 "category not yet supported", image not yet pass in pre-check → block export with warning, failed generation → mark failed allow retry
- docs/BACKEND_ARCHITECTURE.md §14 (export module — to be drilled to LOCKED before this session; currently SKELETON per memory turn 22; this session's planning will note dependency on §14 LOCK before code dispatch can begin), §3.I (export is one of 2 modules with tasks.py per §3.C — the other being image), §6A.C Layer 3 guardrail (Export Adapter validation), §11.C image.service.get_image_bytes cross-module surface consumed by export
- docs/MVP_ARCHITECTURE.md §5.5.10 (export ≤30s budget per MVP_ARCH §5.5.10) + §5.5 9-step Export Adapter flow + golden roundtrip test framing
- docs/MEESHO_CATEGORY_INTELLIGENCE.md — Meesho category template variants (FSSAI vs non-FSSAI, electronics vs apparel, etc.); ComplianceStrategy pattern reference for the data track
- docs/FRONTEND_ARCHITECTURE.md — export page is the 2nd federated remote (mfe-export per module_federation MASTER_PLAN §4.2); pre-federation under frontend/src/app/pages/export/; ExportComponent + ExportProgressComponent with status polling matching image-precheck pattern
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — export is service 1 of 8 in extraction order per §16.H (EASIEST extraction — owns 1 table + 1 worker + minimal cross-module calls)
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — export is the 2nd remote (mfe-export); pre-federation in the shell
- CLAUDE.md — openpyxl + Pillow + GCS for ZIP, Valkey DB 1 broker / DB 2 results, Celery worker pod
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md, .claude/agents/meesell-data-engineer.md, .claude/agents/meesell-infra-builder.md
- Each involved lead's MEMORY.md (especially backend-coordinator memory for the §14 dependency state and data-engineer memory for the ComplianceStrategy variants)
- Each involved lead's docs/status/feature_board_{backend|frontend|data|infra}.md (verify xlsx-export is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/xlsx-export.yaml instead.

Create (or overwrite) docs/plans/features/_status/xlsx-export.yaml with:
feature: "xlsx-export"
session: "mesell-xlsx-export-planning-session-1"
worktree: "/tmp/mesell-wt/xlsx-export"
branch: "feature/xlsx-export/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/xlsx-export/FEATURE_PLAN.md
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
  Does this feature still match V1 spec §F9? Specifically:
    - Generated XLSX opens cleanly in BOTH Excel and LibreOffice (cross-suite compatibility — important for sellers on different machines)
    - Column order matches Meesho's category-specific template (ComplianceStrategy variant determines the column set — data track owns this)
    - Image ZIP filenames match XLSX image-reference column (the seller uploads the ZIP separately on Meesho's supplier panel; filename match is critical)
    - Generation completes ≤15s for 1 product with 6 images (target per §F9, harder bound 30s per MVP_ARCH §5.5.10)
    - Validation blocks export with clear error list (multi-error: "Title missing, 2 images missing, MRP not set")
    - Category XLSX template missing → 422 with "category not yet supported" (V1 may not have all Meesho category templates yet)
    - Image not yet pass in pre-check → block export with warning (cross-module dependency on image.service)
    - Failed generation → mark failed, allow retry (idempotent — re-running on same product_id replaces the failed exports row)
    - Signed download URL expires 1h (matches image precheck signed URL TTL convention per §11)
  Also resolve: Does V1 export ONE product at a time OR support multi-product batch export? Per §F9 spec it's single-product; bulk operations are deferred to V1.5 per §1 V1.5 scope. Confirm single-product for V1.

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_XLSX_EXPORT_ENABLED). Dev default: true. Staging default: false until the golden roundtrip test passes on at least 5 ComplianceStrategy variants (covering Fashion, Home, Beauty, Kitchen, Kids super-categories at minimum) AND the generated XLSX is manually verified to upload cleanly to a real Meesho supplier panel test account. When disabled, POST /api/v1/products/{id}/export-xlsx returns 404; the /catalogs/:id/export route shows "Export temporarily disabled" placeholder.

Decision 3 — Priority ordering vs sibling features
  This feature touches:
    - Backend per-module code: app/modules/export/ (greenfield)
    - Backend shared code: app/adapters/gcs.py (already established by image-precheck — no contention; export writes to a different gs:// path prefix gs://meesell-exports/{user_id}/{export_id}/)
    - Backend cross-module calls: catalog.service.assert_product_ownership + catalog.service.get_compliance_block_for_product + image.service.get_image_bytes per §2.D matrix (all consumed only, no contention)
    - Data: backend/app/data/meesho_templates/ (ComplianceStrategy variants — data track owns the evolving Meesho template shapes; this is the data track's deliverable)
    - Infra: GCS bucket reuse + Celery worker queue addition (export queue separate from image queue)
  Confirm: xlsx-export ships LAST among V1 features because it depends on catalog-form (assert_product_ownership + fields_jsonb) AND image-precheck (get_image_bytes + precheck status pass). The §14 export module section in BACKEND_ARCHITECTURE.md must be LOCKED before code dispatch can begin — this planning session does NOT block on §14 LOCK (planning a future LOCKED section is allowed) but the CODE dispatch later will. Confirm timing.

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | api-routes-builder, services-builder, database-builder | api-routes-builder: 2 export routes — POST /api/v1/products/{id}/export-xlsx (202 ACCEPTED, returns export_id + status=processing per async 202+poll pattern mirroring image-precheck per §11.B) + GET /api/v1/exports/{id} (200, returns status + signed download URL when ready); Pydantic schemas ExportInitiateRequest, ExportInitiateResponse, ExportStatusResponse in modules/export/schemas.py; services-builder: export.service surface with initiate_export (assert_product_ownership + validate compulsory fields + check image precheck pass + enqueue Celery task) + get_export_status (poll) + Celery task tasks.py orchestrating the 9-step Export Adapter flow per MVP_ARCH §5.5 (load category template via data ComplianceStrategy → load product fields → load image bytes via image.service.get_image_bytes → compose XLSX with openpyxl → compose image ZIP → upload XLSX to gs://meesell-exports/{user_id}/{export_id}/catalog.xlsx → upload ZIP to gs://meesell-exports/{user_id}/{export_id}/images.zip → write exports row → emit Layer 3 guardrail validation per §6A.C); database-builder: exports table + Alembic migration with status enum + xlsx_gcs_path + zip_gcs_path + download_url + signed-URL-expiry columns |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: ExportComponent (page with "Generate XLSX" button + validation error list when blocked) + ExportProgressComponent (polling status display with progress affordance + download button when ready), under frontend/src/app/pages/export/; multi-error validation render when initiate returns 422 with the validation error list; angular-service-builder: ExportService.initiate(productId) + ExportService.pollStatus(exportId) with backoff polling (initial 1s, exponential to 4s, max 60s for the ≤30s generation budget per MVP_ARCH §5.5.10); error handling for 422 (validation blocked), 503 (GCS upload fail) |
| meesell-ai-coordinator | (no work) | Export uses Layer 3 guardrail per §6A.C but no AI workload — Layer 3 is deterministic schema-conformance check. Confirm. |
| meesell-data-engineer | xlsx-parser, scraper-maintainer | xlsx-parser: ComplianceStrategy variants for V1 super-categories (Fashion, Home, Beauty, Kitchen, Kids minimum per Decision 2) — each variant returns the column set, column order, FSSAI-compulsory blocks, and image-reference column convention for that Meesho category template; lives in backend/app/data/meesho_templates/{super_category}.json + a Python ComplianceStrategy class per variant in backend/app/modules/export/strategies/; golden roundtrip fixture at tests/golden/xlsx_export/ — one fixture per ComplianceStrategy variant containing the input product fields + expected XLSX bytes (byte-comparison); scraper-maintainer: ONLY if a Meesho category template has changed since the last seed — re-scrape and update the relevant variant. Default: scraper not dispatched unless drift detected |
| meesell-infra-builder | (standalone) | Celery worker addition for export queue (separate from image queue) + scaling target 2 replicas in staging; GCS bucket meesell-exports (separate from meesell-images) + lifecycle policy 30-day retention for exports + IAM binding for backend SA write + worker SA read; k8s/dev/worker-deployment.yaml MODIFY (add export queue) + k8s/staging mirror; terraform/gcs/buckets.tf MODIFY (add meesell-exports bucket) |

Only include leads + specialists who actually have work. Omit empty rows.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/export/routes.py (NEW), app/modules/export/schemas.py (NEW), app/modules/export/service.py (NEW), app/modules/export/repository.py (NEW), app/modules/export/tasks.py (NEW — Celery task with 9-step Export Adapter flow per MVP_ARCH §5.5), app/modules/export/strategies/ (NEW dir — ComplianceStrategy variants per data dispatch), app/modules/export/strategies/__init__.py (NEW — strategy registry), app/modules/export/strategies/fashion.py + home.py + beauty.py + kitchen.py + kids.py (NEW — 5 V1 variants per Decision 2), app/modules/export/domain.py (NEW — ExportRequest + ExportResult + ValidationError frozen dataclasses), app/modules/export/exceptions.py (NEW — ExportError subclasses incl. CategoryTemplateMissingError, ProductValidationError, ImagePrecheckPendingError), app/shared/models/export.py (NEW — table model), app/alembic/versions/<rev>_exports.py (NEW migration), backend/tests/test_export_unit.py (NEW — strategy + validation tests), backend/tests/test_xlsx_export_integration.py (NEW — end-to-end initiate→poll→download), tests/golden/xlsx_export/fashion_roundtrip.json + home / beauty / kitchen / kids (NEW — 5 golden fixtures), tests/golden/test_roundtrip.py (NEW — pytest runner for CI gate 5 golden_roundtrip)
- Frontend: frontend/src/app/pages/export/export.component.ts (NEW), frontend/src/app/pages/export/export-progress.component.ts (NEW), frontend/src/app/services/export.service.ts (NEW), frontend/src/app/app.routes.ts (MODIFY — register /catalogs/:id/export route), frontend/src/app/pages/export/export.component.spec.ts (NEW)
- AI: NONE (Layer 3 guardrail is deterministic schema check, not AI)
- Data: backend/app/data/meesho_templates/fashion.json + home.json + beauty.json + kitchen.json + kids.json (NEW — 5 Meesho category template definitions), tests/golden/xlsx_export/*.json (5 golden fixtures co-authored with backend)
- Infra: k8s/dev/worker-deployment.yaml (MODIFY — add export queue), k8s/staging/worker-deployment.yaml (mirror), k8s/dev/gcs-secrets.yaml (MODIFY — add meesell-exports bucket name), terraform/gcs/buckets.tf (MODIFY — add meesell-exports bucket with 30d retention + IAM bindings)
- Docs: docs/V1_FEATURE_SPEC.md §F9 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §14 sentinel flip (LOCKED-on-paper → LOCKED-on-disk via PR link — §14 LOCK precedes this dispatch), docs/MEESHO_CATEGORY_INTELLIGENCE.md cross-link to ComplianceStrategy variants, docs/runbooks/xlsx-export-troubleshooting.md (NEW — how to inspect a stuck export job, how to verify XLSX validity locally, how to add a new ComplianceStrategy variant for a new super-category)

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entries for POST /api/v1/products/{id}/export-xlsx (202 + ExportInitiateResponse) and GET /api/v1/exports/{id} (200 + ExportStatusResponse with status + signed download URL); inline service-method docstrings on initiate_export documenting the 4 prereqs (ownership + compulsory fields + image precheck pass + ComplianceStrategy exists for category)
- Frontend: route entry comment in app.routes.ts; ExportComponent docstring documenting the multi-error validation render contract; ExportProgressComponent docstring on polling backoff schedule
- AI: N/A (Layer 3 guardrail is documented in §6A.C; no prompt registry entry needed)
- Data: ComplianceStrategy variants documented in backend/app/data/meesho_templates/README.md (NEW) — how to add a new variant when Meesho adds a super-category; golden fixture format documented in tests/golden/xlsx_export/README.md (NEW) — how to author a new fixture for a new variant
- Infra: runbook entry on export worker scaling + GCS cost-monitoring at projected XLSX × ZIP × N sellers/month
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F9 marked "implemented YYYY-MM-DD" with PR link; CI gate 5 golden_roundtrip entry in .github/workflows/ci.yml referencing tests/golden/test_roundtrip.py; troubleshooting runbook linked from docs/runbooks/README.md

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-xlsx-export-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., services-builder reads §14 LOCKED + MVP_ARCH §5.5 9-step Export Adapter flow + §6A.C Layer 3 guardrail + §11.C image.service.get_image_bytes cross-module signature; xlsx-parser reads MEESHO_CATEGORY_INTELLIGENCE + the 5 V1 super-category template references)
- Acceptance criteria (specific to that specialist's slice — e.g., services-builder: 9-step flow tested end-to-end, ≤15s generation budget met on 1-product-with-6-images, Layer 3 guardrail rejects malformed XLSX; xlsx-parser: 5 ComplianceStrategy variants pass golden roundtrip; xlsx opens in BOTH Excel and LibreOffice; image-reference column matches ZIP filenames exactly)
- Hard constraints (e.g., NO writes to products.fields_jsonb during export — read-only; NO Layer 3 guardrail bypass; GCS path structure gs://meesell-exports/{user_id}/{export_id}/ is structural tenant isolation; signed URL TTL = 1h not 24h)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch (especially: image.service is consumed only — do NOT touch app/modules/image/; catalog.service is consumed only — do NOT touch app/modules/catalog/)
- Final report format (golden roundtrip pass count, generation time measurement, Excel + LibreOffice open verification)

Specialists to template:
- meesell-api-routes-builder (backend lead dispatches)
- meesell-services-builder (backend lead dispatches)
- meesell-database-builder (backend lead dispatches)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)
- meesell-xlsx-parser (data lead dispatches — owns ComplianceStrategy variants + golden fixtures)
- meesell-scraper-maintainer (data lead dispatches IF Meesho template drift detected — otherwise omit)
- meesell-infra-builder (standalone — founder dispatches directly)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., backend lead checks: 9-step flow matches MVP_ARCH §5.5 verbatim; Layer 3 guardrail wired before Celery task returns; image.service.get_image_bytes is called via service surface not direct GCS access; generated XLSX opens in BOTH Excel + LibreOffice — verify with manual smoke + tests/golden roundtrip; data lead checks: 5 ComplianceStrategy variants pass golden roundtrip; column order matches Meesho template byte-for-byte for each variant; FSSAI super-categories include compulsory food-safety columns; image-reference column matches ZIP filename convention)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/backend.md` (migration + integration test evidence) + `.github/PULL_REQUEST_TEMPLATE/data.md` (golden roundtrip evidence + parser stats) + `.github/PULL_REQUEST_TEMPLATE/infra.md` (terraform plan + GCS IAM binding)
- What triggers a re-dispatch (specific failure modes — XLSX fails to open in LibreOffice → re-dispatch xlsx-parser with "previous run produced XLSX that opens in Excel but fails in LibreOffice — verify openpyxl write_only mode and shared-strings encoding"; image-reference column mismatch with ZIP filenames → re-dispatch services-builder with "verify image-reference convention matches the ComplianceStrategy variant's image_filename_template"; generation >15s → re-dispatch services-builder with "verify image.service.get_image_bytes batches calls instead of N+1; verify openpyxl row writes are streaming not buffered"; Layer 3 guardrail not fired → re-dispatch with "verify Celery task calls guardrail.validate_export_artifact BEFORE writing exports row")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3 — but golden-roundtrip iterations may iterate more because Meesho template edge cases are surface — adjust to 4 with founder consent for the xlsx-parser dispatches)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/xlsx-export/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., Meesho changing a category template mid-V1 invalidating a ComplianceStrategy variant, openpyxl/LibreOffice compatibility edge cases on FSSAI-block compulsory columns, image bytes fetch latency under congested networks blowing the 15s budget, signed URL expiry mid-download breaking large ZIP transfers, Celery export worker OOM on large image batches, V1.5 bulk-export forcing exports table schema migration)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/xlsx-export/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/xlsx-export.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/xlsx-export/FEATURE_PLAN.md
git add docs/plans/features/_status/xlsx-export.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock xlsx-export feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-xlsx-export-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/xlsx-export/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/xlsx-export/planning \
  --title "docs(plan): lock xlsx-export feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update xlsx-export status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md
- [ ] Agent lineup table fully filled out (backend 3 + frontend 2 + data 1-or-2 + infra 1 specialists named; AI explicitly omitted)
- [ ] Code surfaces table covers every file the feature will create or modify (INCLUDING 5 V1 ComplianceStrategy variants + 5 golden fixtures + meesell-exports GCS bucket)
- [ ] Documentation deliverables enumerated (OpenAPI with 202+poll semantics, ComplianceStrategy README, golden fixture README, troubleshooting runbook, V1_FEATURE_SPEC §F9 implemented stamp, CI gate 5 golden_roundtrip wired)
- [ ] One dispatch template per specialist drafted (7-or-8 templates total depending on data)
- [ ] Review + iteration protocol defined (with LibreOffice / image-ref-mismatch / generation-budget / Layer-3-bypass failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/xlsx-export/planning
- [ ] PR opened to develop using data PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/export/, backend/app/data/meesho_templates/, frontend/src/app/pages/export/, k8s/, terraform/, tests/golden/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-xlsx-export-{group}-session-{N}` per master plan §4
- The golden roundtrip test is non-negotiable for CI gate 5 — any dispatch template that allows skipping the roundtrip on PR must be rejected
- The cross-suite Excel + LibreOffice open requirement is part of §F9 acceptance — any dispatch template that tests only Excel must be rejected
- The §14 export module section in BACKEND_ARCHITECTURE.md must be LOCKED before any code dispatch begins — planning is allowed against the SKELETON; code dispatch must wait. Flag the §14 LOCK gating in the dispatch templates explicitly.
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend, data, infra) has reviewed their section's dispatch templates
- [ ] PR open to develop using the data PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- The golden roundtrip + cross-suite (Excel+LibreOffice) requirements are non-negotiable
- The §14 LOCK is a pre-code gate, not a pre-planning gate — planning may proceed against SKELETON

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
