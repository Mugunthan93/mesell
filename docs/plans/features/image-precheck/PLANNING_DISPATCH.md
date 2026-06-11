# Session Dispatch: Image Pre-check — JPEG / CMYK / Resolution / White-BG / Watermark Detection
**Session name:** `mesell-image-precheck-planning-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** READY — feature-level planning session (produces FEATURE_PLAN.md)
**Output document:** `docs/plans/features/image-precheck/FEATURE_PLAN.md`
**Prerequisite sessions:** S1 (repo management) merged to develop; auth-otp shipped; catalog-form shipped (image upload requires `catalog.service.assert_product_ownership()` — the cross-module signature locked at `BACKEND_ARCHITECTURE.md §10.A`)
**Lead involvement:** Backend (image module + Celery worker `tasks.py`) · Frontend (image uploader + polling component) · AI (watermark detection via Gemini Vision + 4 deterministic Pillow checks) · Infra (GCS bucket policy + signed-URL TTL + worker pod scaling)

---

## Why this session exists
Image Pre-check is the only feature that introduces an async work pattern in V1 — upload returns `202 ACCEPTED`, the client polls until `status=pass|fail`, and the Celery worker runs the 5-step pipeline asynchronously. It is the structural template every later async feature (XLSX Export) will mirror. The pattern locks: how the 4-slot uniform-rule is enforced as a structural DB CHECK constraint per `MVP_ARCH §0` premise #3, how the GCS tenant-isolation path `gs://meesell-images/{user_id}/{product_id}/{idx}.jpg` is enforced per `MVP_ARCH §10.8`, how the worker's direct ORM write to `image.precheck.completed` audit events works without a request-close hook, and how watermark-check informational-not-blocking behavior degrades gracefully under budget exhaustion per `BACKEND_ARCHITECTURE.md §6A.F`.

The watermark check is the 3rd AI workload in V1 — its golden set ≥85% accuracy target per `§6A.E` is the lowest bar of the three AI features because vision is harder than text and false negatives are acceptable in V1 (watermark step is informational per the founder's "do not penalize sellers for budget exhaustion they didn't cause" principle). This planning session locks the seam between the Pillow pipeline (deterministic 4 checks) and the Gemini Vision workload (informational 5th check), and the user-facing semantics of "ready vs ready-with-skipped-watermark".

---

## PASTE THIS PROMPT INTO THE NEW SESSION

```
SESSION: mesell-image-precheck-planning-session-1
PROJECT BOUNDARY: You are working inside the git worktree for this feature at /tmp/mesell-wt/image-precheck/. Do NOT read or write outside the worktree path, EXCEPT for the symlinked shared resources at .claude/agent-memory/ and .claude/agents/ (those point back to /Users/mugunthansrinivasan/Project/mesell/ and are intentionally shared).

## Your mission
Plan the Image Pre-check feature end-to-end. Produce a FEATURE_PLAN.md document that locks every detail about how this feature will be built — agents, code surfaces, documentation structure, dispatch templates, review protocol, iteration loop — BEFORE any production code is written.

This session produces a DOCUMENT, not code. The output is the executable plan that leads will dispatch coding agents against in later sessions.

## Step 0a — Worktree preflight (MANDATORY — run before any other step)

You must be inside the dedicated git worktree for image-precheck. Verify:
pwd                                          # must print /private/tmp/mesell-wt/image-precheck or /tmp/mesell-wt/image-precheck
git worktree list | grep image-precheck      # must show this worktree
git branch --show-current                     # must print feature/image-precheck/planning
If pwd is wrong or the worktree is missing, STOP. The launcher script scripts/launch-planning-session.sh image-precheck (run from the main project) creates the worktree. Do NOT proceed if you are not in the right worktree — concurrent branch checkouts in the main project will fight each other.

Read docs/plans/features/_WORKTREE_PROTOCOL.md once if you are unsure how worktrees work in this repo.

## Step 0 — Mandatory reads (in this order)
- docs/plans/repo_management/MASTER_PLAN.md (APPROVED) — §1 branch model, §2 merge flow, §4 session naming, §5 PR templates, §6 feature_board, §7 lead responsibilities
- docs/V1_FEATURE_SPEC.md §F5 (Feature 5: Image Pre-check) — 5 checks (JPEG, RGB, ≥1500×1500, white-BG, watermark), 8s per image worker budget, per-check pass/fail with fix hints, watermark accuracy ≥85% on 30-image seed, 6 images max per product
- docs/BACKEND_ARCHITECTURE.md §11 (image module — 2 endpoints: POST upload 202 ACCEPTED + GET poll-list 200; 4-slot uniform rule enforced as structural DB CHECK; Celery task tasks.py; signed URL TTL 1h; image.precheck.completed audit direct-ORM-write from worker; 6-method service surface incl. 4 cross-module get_image_urls/get_image_bytes/write_precheck_result/summary; 5 ImageError subclasses; V1=direct multipart per CLAUDE.md API design rule), §6A.B watermark workload literal + §6A.F graceful fallback (watermark_check = "skipped_budget" + overall status still "ready" if 4 deterministic checks pass), §11.J cross-cutting integrations (plan_guard NOT participating in V1 — 4-slot uniform rule is structural DB constraint)
- docs/FRONTEND_ARCHITECTURE.md — image uploader is part of mfe-catalog (Phase 2 federation); pre-federation under frontend/src/app/pages/image-uploader/; ImageUploaderComponent + PrecheckReportComponent with status polling
- docs/plans/microservices_migration/MASTER_PLAN.md §3.B — image is service 3 of 8 in extraction order (per BACKEND_ARCHITECTURE.md §16.H — easier extraction because Celery worker is already a separate process boundary)
- docs/plans/module_federation/MASTER_PLAN.md §4.2 — image uploader page is part of mfe-catalog (5th remote); pre-federation in the shell
- CLAUDE.md — Valkey DB 1 broker / DB 2 results, rembg deferred (mentioned in stack but white-BG check uses Pillow heuristic for V1), Gemini Vision decision, GCS bucket layout
- Each involved lead's spec: .claude/agents/meesell-backend-coordinator.md, .claude/agents/meesell-frontend-coordinator.md, .claude/agents/meesell-ai-coordinator.md, .claude/agents/meesell-infra-builder.md
- Each involved lead's MEMORY.md (especially backend-coordinator memory turn 18 for the §11 module deep content)
- Each involved lead's docs/status/feature_board_{backend|frontend|ai|infra}.md (verify image-precheck is PENDING)
- docs/plans/features/_WORKTREE_PROTOCOL.md — the worktree protocol; verify your worktree posture matches it
- docs/plans/features/_status/README.md — the YAML status-file format you will write in Step 0.5 and again in Step 8

## Step 0.5 — Write your status file (session start)

Do NOT edit the master tracker — it is now master-only and regenerated by the Director from _status/*.yaml files. Each sub-session writes its own file at docs/plans/features/_status/image-precheck.yaml instead.

Create (or overwrite) docs/plans/features/_status/image-precheck.yaml with:
feature: "image-precheck"
session: "mesell-image-precheck-planning-session-1"
worktree: "/tmp/mesell-wt/image-precheck"
branch: "feature/image-precheck/planning"
status: IN_PROGRESS
last_updated: <today's ISO 8601 UTC timestamp, e.g. 2026-06-10T14:30:00Z>
feature_plan_path: docs/plans/features/image-precheck/FEATURE_PLAN.md
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
  Does this feature still match V1 spec §F5? Specifically:
    - 5 checks: JPEG format, RGB color space (not CMYK), resolution ≥1500×1500, white-BG heuristic, watermark detection
    - 6 images max per product (matches V1 spec; structural 4-slot rule per MVP_ARCH §0 premise #3 — verify this matches the spec; the architecture memory turn 18 references 4-slot uniform rule but V1 spec says 6 images — FLAG this discrepancy to the founder for resolution before authoring FEATURE_PLAN.md)
    - 10MB per image upload limit, 60MB total per product
    - Worker completes all 5 checks within 8s per image
    - Watermark check is INFORMATIONAL — overall status "ready" if 4 deterministic Pillow checks pass even if watermark check is "skipped_budget"
    - Per-check pass/fail with one-line fix hint ("Convert image to RGB before upload")
    - Watermark accuracy ≥85% on 30-image seed test
    - Failed images marked red; user can re-upload to replace at the same slot index
  Any cuts, additions, or scope flexes since the spec was locked? RESOLVE the 4-slot vs 6-image discrepancy before proceeding.

Decision 2 — Feature flag posture
  Per master plan §3.2, confirm the flag name (suggested: FEATURE_IMAGE_PRECHECK_ENABLED). Dev default: true. Staging default: false until the 30-image watermark seed passes ≥85% accuracy AND the 4 deterministic Pillow checks pass on a smoke set of 10 known-bad / 10 known-good images AND the GCS upload path correctly enforces tenant isolation. When disabled, POST /products/{id}/images returns 404 per master plan §3.2.

Decision 3 — Priority ordering vs sibling features
  This feature touches:
    - Backend per-module code: app/modules/image/ (greenfield — no contention)
    - Backend shared code: app/adapters/gcs.py (new 3 methods: upload_bytes / download_bytes / generate_signed_url per §6.D) — single consumer in V1, no contention
    - Backend cross-module call: catalog.service.assert_product_ownership() (consumed only, no contention)
    - Infra: GCS bucket + IAM binding (single consumer in V1 for now; export will reuse the bucket)
  Confirm: image-precheck ships after catalog-form (ownership-gate dependency) and can ship in parallel with ai-autofill (no contention).

Record all answers verbatim at the top of FEATURE_PLAN.md under a `## Decisions` section.

## Step 2 — Map the agent lineup
Identify exactly which leads and specialists work on this feature. For each involved lead, fill out:

| Lead | Specialists they dispatch | What each specialist codes |
|---|---|---|
| meesell-backend-coordinator | api-routes-builder, services-builder, database-builder | api-routes-builder: 2 image routes (POST /api/v1/products/{id}/images 202 ACCEPTED with 10/min/user rate limit + 8-step flow incl. ownership gate + file validation + Pillow metadata read + slot uniqueness + GCS upload + repo insert + Celery enqueue; GET /api/v1/products/{id}/images 200 with 5-step flow incl. ownership gate + repo fetch + signed URL gen + verbatim precheck_jsonb passthrough) + Pydantic schemas (ImageUploadResponse, ImageSummary, ImagesListResponse) in modules/image/schemas.py; services-builder: 6-method image.service surface (4 are cross-module per §11.C: get_image_urls→catalog.get_preview, get_image_bytes→export, write_precheck_result→tasks.py worker context, summary→dashboard OPTIONAL) + Celery task in modules/image/tasks.py with 9-step locked flow per §11.E (sync @shared_task with asyncio.run internals for GCS+Gemini+DB); database-builder: product_images table + Alembic migration with 4-slot CHECK constraint per §11.D + 7-method MODULE-PRIVATE repository all scoped per §4.C |
| meesell-frontend-coordinator | angular-component-builder, angular-service-builder | angular-component-builder: ImageUploaderComponent (drag-drop, multipart upload progress, slot grid 1-6 per Decision 1 resolution), PrecheckReportComponent (per-check pass/fail rows with fix-hint inline, red border on failed images, re-upload affordance), under frontend/src/app/pages/image-uploader/; angular-service-builder: ImageService.upload(productId, file, slotIdx) + ImageService.pollImages(productId) with backoff polling (initial 1s, exponential to 4s, max 30s); error handling for 415 (non-JPEG/PNG rejection), 413 (size cap), 503 (GCS upload fail) |
| meesell-ai-coordinator | image-precheck-builder, prompt-engineer | image-precheck-builder: full 5-step pipeline algorithm internals — JPEG check (Pillow format detection), RGB/CMYK check (Pillow color space probe), resolution check (Pillow image.size), white-BG heuristic (Pillow corner-pixel + mean-brightness algorithm — algorithm choice documented in module header), watermark check (Gemini Vision call via ai_ops.client.call_gemini workload="watermark") with §6A.F graceful fallback returning precheck_jsonb.watermark_check = "skipped_budget"; pipeline lives inside the Celery task per §11.E; prompt-engineer: watermark.v1 vision prompt file at backend/app/ai_ops/prompts/watermark_v1.py — Gemini Vision system prompt for "is there a visible watermark / text overlay / logo overlay" classification, JSON output {has_watermark: bool, confidence: float}, 30-image golden set fixture at tests/eval/watermark/golden_set.json with 15 watermarked + 15 clean images (image GCS paths + expected labels), eval runner at tests/eval/watermark/test_accuracy.py gating ≥85% accuracy |
| meesell-infra-builder | (standalone) | GCS bucket creation + lifecycle policy (1-year retention for images, 1-hour signed URL TTL); GCS IAM binding: backend service account = roles/storage.objectAdmin scoped to gs://meesell-images/* (NOT bucket-level admin); Workload Identity binding for the Celery worker pod; k8s/dev/worker-deployment.yaml + k8s/staging mirror with Celery worker replicas (1 in dev, 2 in staging); k8s/dev/gcs-bucket-config.yaml secret ref for the bucket name; image-tasks queue declared in worker config; precheck worker concurrency = 4 (matches the 8s/image budget per §F5 acceptance) |

Only include leads + specialists who actually have work. Data lead has NO work on this feature — omit.

## Step 3 — Map the code surfaces
List every file (or file pattern) this feature will create or modify. Group by domain.
- Backend: app/modules/image/routes.py (NEW), app/modules/image/schemas.py (NEW), app/modules/image/service.py (NEW), app/modules/image/repository.py (NEW), app/modules/image/tasks.py (NEW — Celery task), app/modules/image/domain.py (NEW — 4 frozen dataclasses ProductImage/ImageUrl/ImageStatusSummary/PrecheckResult per §11.G), app/modules/image/exceptions.py (NEW — 5 ImageError subclasses per §11.H), app/shared/models/product_image.py (NEW — table model + 4-slot CHECK constraint), app/adapters/gcs.py (NEW or MODIFY — upload_bytes / download_bytes / generate_signed_url methods per §6.D), app/ai_ops/prompts/watermark_v1.py (NEW), app/ai_ops/client.py (MODIFY — verify "watermark" is in the workload Literal), app/alembic/versions/<rev>_product_images.py (NEW migration), backend/tests/test_image_unit.py (NEW — 5 unit tests per §11.K), backend/tests/test_image_precheck_integration.py (NEW — 3 integration tests per §11.K), tests/eval/watermark/golden_set.json (NEW), tests/eval/watermark/test_accuracy.py (NEW)
- Frontend: frontend/src/app/pages/image-uploader/image-uploader.component.ts (NEW), frontend/src/app/pages/image-uploader/precheck-report.component.ts (NEW), frontend/src/app/services/image.service.ts (NEW), frontend/src/app/app.routes.ts (MODIFY — register /catalogs/:id/images route), frontend/src/app/pages/image-uploader/image-uploader.component.spec.ts (NEW)
- AI: backend/app/ai_ops/prompts/watermark_v1.py (NEW — prompt-engineer authors content), tests/eval/watermark/ (NEW dir with 30-image golden set + accuracy eval runner)
- Data: NONE
- Infra: k8s/dev/worker-deployment.yaml (NEW or MODIFY — image queue + concurrency=4), k8s/staging/worker-deployment.yaml (mirror), k8s/dev/gcs-secrets.yaml (NEW — bucket name + Workload Identity ref), terraform/gcs/buckets.tf (NEW — meesell-images bucket + lifecycle policy + IAM binding)
- Docs: docs/V1_FEATURE_SPEC.md §F5 marked "implemented" once shipped, docs/BACKEND_ARCHITECTURE.md §11 sentinel flip, docs/runbooks/image-pipeline-troubleshooting.md (NEW — how to inspect a stuck precheck job, how to re-enqueue failed checks, GCS-path tenant-isolation verification command)

For each file, indicate: NEW or MODIFY. This becomes the diff scope when leads brief specialists.

## Step 4 — Define the feature documentation structure
What does "documented" mean for this feature? At minimum:
- Backend: OpenAPI entries for POST /api/v1/products/{id}/images (202 + response shape per §11.B.1) and GET /api/v1/products/{id}/images (200 + ImagesListResponse with per-image status + signed URLs); inline service-method docstrings on the 4 cross-module surfaces with consumer reference per §16.A
- Frontend: ImageUploaderComponent docstring describing the multipart upload + slot grid + retry semantics; PrecheckReportComponent docstring on per-check rendering + fix-hint copy + re-upload affordance; ImageService.pollImages docstring on backoff schedule
- AI: prompt registry entry — watermark.v1 registered in ai_ops/prompt_registry.py; golden set fixture (30 images with GCS paths + labels) documented in tests/eval/README.md; eval runner instructions for local + CI ai_eval gate; image-precheck-builder produces a module header comment in the Celery task documenting the 5-step pipeline order + the white-BG heuristic algorithm choice
- Data: N/A
- Infra: runbook entry on signed-URL TTL rotation; runbook entry on GCS bucket cost-monitoring at projected 6 images × 10MB × N sellers/month
- Cross-cutting: entry in V1_FEATURE_SPEC.md §F5 marked "implemented YYYY-MM-DD" with PR link; ai_eval CI gate extended to include tests/eval/watermark/; troubleshooting runbook linked from docs/runbooks/README.md

Define the documentation deliverables that MUST exist alongside the merged code. These become acceptance gate items.

## Step 5 — Draft dispatch templates per coding agent
For EACH specialist that will be dispatched on this feature, write the full dispatch prompt template the lead will use. Each template MUST include:
- PROJECT BOUNDARY block
- SESSION header (`mesell-image-precheck-{group}-session-{N}` format)
- Mandatory reads for the specialist (e.g., image-precheck-builder reads §11.E Celery task structure + §6A.B watermark workload + §11.J cross-cutting integrations; prompt-engineer reads §6A.G prompt-engineer scope + the 30-image golden set framing)
- Acceptance criteria (specific to that specialist's slice — e.g., image-precheck-builder: 4 deterministic Pillow checks return within 2s/image total, watermark check uses ai_ops.client only, white-BG heuristic documented in module header, watermark "skipped_budget" path tested; prompt-engineer: watermark.v1 file exists, golden set ≥85% accuracy, per-call vision cost ≤₹0.08 (vision is more expensive than text — confirm cost ceiling against ai-coordinator memory))
- Hard constraints (e.g., backend route NEVER directly invokes AI — watermark vision lives INSIDE the Celery task only per §11.E; GCS upload path MUST match gs://meesell-images/{user_id}/{product_id}/{idx}.jpg structurally per §11.I; signed URL TTL is 1h not 24h per §11.J)
- Files they may touch (the subset from Step 3)
- Files they must NOT touch
- Final report format

Specialists to template:
- meesell-api-routes-builder (backend lead dispatches)
- meesell-services-builder (backend lead dispatches)
- meesell-database-builder (backend lead dispatches — CHECK constraint is critical)
- meesell-angular-component-builder (frontend lead dispatches)
- meesell-angular-service-builder (frontend lead dispatches)
- meesell-image-precheck-builder (ai lead dispatches — the pipeline owner)
- meesell-prompt-engineer (ai lead dispatches — watermark prompt only)
- meesell-infra-builder (standalone — founder dispatches directly)

These templates live in FEATURE_PLAN.md under a `## Dispatch templates` section. They are reusable — the lead pastes one of these into the Agent() dispatch with the {N} session number filled in.

## Step 6 — Define the code review + iteration protocol
For each specialist dispatch, define:
- What the lead checks before approving the specialist's PR (e.g., backend lead checks: 4-slot CHECK constraint reverses on alembic downgrade -1 cleanly; GCS path structure enforced at repository layer; signed URL TTL =1h; precheck_jsonb shape passes through to GET response verbatim; Celery task uses asyncio.run not native async; ai lead checks: watermark golden set accuracy ≥85%; per-call vision cost ≤₹0.08; "skipped_budget" semantics tested; 4 Pillow checks within 2s budget on a 1500×1500 test image)
- The acceptance gate from `.github/PULL_REQUEST_TEMPLATE/backend.md` (migration evidence with CHECK constraint reversibility) + `.github/PULL_REQUEST_TEMPLATE/ai.md` (watermark accuracy + cost evidence) + `.github/PULL_REQUEST_TEMPLATE/infra.md` (GCS bucket + IAM binding terraform plan)
- What triggers a re-dispatch (specific failure modes — watermark accuracy <85% → re-dispatch prompt-engineer with "Previous run produced N false positives / M false negatives against the {category, image} pairs listed; tighten the prompt for those category-watermark-style combos and re-eval"; deterministic Pillow checks slower than 2s → re-dispatch image-precheck-builder with "verify Pillow opens image in single read not double-decode"; GCS upload missing tenant prefix → re-dispatch services-builder with "verify modules/image/service.py constructs path from user_id+product_id NOT just product_id"; signed URL TTL >1h → re-dispatch with "verify gcs.generate_signed_url passes 3600s expiry")
- What the re-dispatch prompt looks like (template for the "iteration" dispatch — original template + a "Previous run failed on X; fix Y by reading Z" preamble)
- Maximum iteration count before escalating to founder (suggested: 3)

## Step 7 — Author FEATURE_PLAN.md
Compile Steps 1-6 into a single canonical FEATURE_PLAN.md at `docs/plans/features/image-precheck/FEATURE_PLAN.md` with this structure:
- ## Decisions (founder D1/D2/D3 verbatim from Step 1)
- ## Agent lineup (table from Step 2)
- ## Code surfaces (table from Step 3)
- ## Documentation deliverables (Step 4)
- ## Dispatch templates (Step 5 — one subsection per specialist)
- ## Review + iteration protocol (Step 6)
- ## Acceptance gate (when this feature is "done")
- ## Risk register (top 3-5 risks specific to this feature — e.g., Gemini Vision JSON-mode regression breaking the watermark parser, GCS upload latency under congested networks blowing the 8s/image budget, watermark golden-set drift as sellers' image styles evolve, white-BG heuristic false-positive on light-but-not-white backgrounds, Celery worker pod OOM on large image batches)
- ## Revision history

## Step 8 — Update status file + commit + PR (from inside the worktree)

You are ALREADY on feature/image-precheck/planning because the worktree handles branch isolation. DO NOT run git checkout -b — the branch is yours by virtue of the worktree.

1. Update docs/plans/features/_status/image-precheck.yaml:
  - status: PLAN_READY
  - last_updated: <today's ISO 8601 UTC timestamp>
  - feature_plan_line_count: <wc -l output>
  - outstanding_founder_decisions: [list any unresolved D-flags from your Decisions section, OR empty array]
  - notes: | — short paragraph stating "ready for consolidation" or naming blockers
2. Stage and commit BOTH files in one commit:
git add docs/plans/features/image-precheck/FEATURE_PLAN.md
git add docs/plans/features/_status/image-precheck.yaml
git commit -m "$(cat <<'COMMIT_EOF'
docs(plan): lock image-precheck feature blueprint — agents, code surfaces, dispatch templates, review protocol

Session: mesell-image-precheck-planning-session-1
Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"

3. Push from the worktree:
git push -u origin feature/image-precheck/planning

4. Open PR to develop using the most-relevant lead's PR template format (template files at .github/PULL_REQUEST_TEMPLATE/{backend,frontend,ai,data,infra}.md):
gh pr create --base develop --head feature/image-precheck/planning \
  --title "docs(plan): lock image-precheck feature blueprint" \
  --body "<filled-in template>"
  
5. After PR opens: update your status file ONE MORE TIME — set status: IN_REVIEW, fill pr_number and pr_url. Stage + amend the commit OR push a follow-up commit docs(plan): update image-precheck status — IN REVIEW with PR link.
6. DO NOT touch the master tracker. The master session regenerates it by aggregating _status/*.yaml files after your session closes.
## Acceptance gate — this planning session is complete when ALL are true
- [ ] Founder decisions D1/D2/D3 recorded at top of FEATURE_PLAN.md (including the 4-slot-vs-6-image discrepancy resolution)
- [ ] Agent lineup table fully filled out (backend 3 + frontend 2 + AI 2 + infra 1 specialists named; data explicitly omitted)
- [ ] Code surfaces table covers every file the feature will create or modify
- [ ] Documentation deliverables enumerated (OpenAPI, watermark prompt registry, 30-image golden set, ai_eval gate, troubleshooting runbook, V1_FEATURE_SPEC §F5 implemented stamp)
- [ ] One dispatch template per specialist drafted (8 templates total)
- [ ] Review + iteration protocol defined (with watermark-accuracy / Pillow-timing / GCS-path / signed-URL failure-mode examples)
- [ ] FEATURE_PLAN.md committed on feature/image-precheck/planning
- [ ] PR opened to develop using AI PR template

## Hard constraints
- Do NOT touch any other feature's planning directory
- Do NOT write any production code (backend/app/modules/image/, backend/app/adapters/gcs.py, backend/app/ai_ops/prompts/watermark_v1.py, frontend/src/app/pages/image-uploader/, k8s/, terraform/, tests/eval/watermark/, etc.) — this is planning only
- Do NOT merge the PR — leave it open for founder review
- Session name in every dispatched specialist template MUST follow `mesell-image-precheck-{group}-session-{N}` per master plan §4
- The ≥85% watermark accuracy target is the only AI gate that may be informational (watermark step is non-blocking per §6A.F) — but the gate value itself remains 85%; do not lower it without founder approval
- The GCS path structure gs://meesell-images/{user_id}/{product_id}/{idx}.jpg is structural tenant isolation per MVP_ARCH §10.8 — any dispatch template that allows path variation must be rejected
```

---

## Acceptance gate (for the planning session)
- [ ] FEATURE_PLAN.md exists with all 9 sections
- [ ] Each involved lead (backend, frontend, AI, infra) has reviewed their section's dispatch templates
- [ ] PR open to develop using the AI PR template

## Hard constraints (for the planning session)
- Planning session produces a DOCUMENT, not code
- All dispatch templates inside FEATURE_PLAN.md must use the session naming convention from MASTER_PLAN §4
- All references to leads, specialists, and architecture sections must trace to specific filenames or section numbers — no vague "see the docs" phrasing
- The 4-slot vs 6-image discrepancy MUST be resolved in Decision 1 before FEATURE_PLAN.md is committed — do not author dispatch templates against an unresolved spec

---

## Revision history
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | meesell-backend-coordinator | Initial dispatch authored |
