---
name: project-meesell-ai-track-session1
description: MeeSell AI track session-1 outcome — F2/F4/F5 AI group PRs delivered to integration; 3 FOUNDER GATE PRs open; vision cost ceiling settled
metadata:
  type: project
---

**Fact:** AI track session `mesell-ai-track-session-1` (2026-06-11) delivered the AI group slices for V1 Features 2 (smart-picker), 4 (catalog-form autofill), and 5 (image-precheck watermark) — all 3 gate-merged to their integration branches; 3 FOUNDER GATE PRs open.

**Why:** This was the first dedicated AI track session. Previous construction phases had already built the ai_ops infrastructure and golden eval sets on develop; this session created proper Model C feature branches and applied 3 targeted fixes.

**How to apply:** When next touching the AI track, start from the board (`docs/status/feature_board_ai.md`) — 3 rows in "Recently merged"; 3 FOUNDER GATE PRs (#55/#57/#59) await sibling-group slices + integration tests + founder merge.

## What was done

| Feature | Group PR | Founder gate PR | Key change |
|---|---|---|---|
| F2 smart-picker | #54 MERGED | #55 OPEN | JSON closing schema added to `smart_picker_v1.py` |
| F4 catalog-form | #56 MERGED | #57 OPEN | Autofill fixtures+runner moved to `tests/eval/autofill/` (path fix) + JSON closing |
| F5 image-precheck | #58 MERGED | #59 OPEN | `watermark_v1.py` docstring fix (50/50 → 14/16); FEATURE_PLAN R3 vision-cost AMENDMENT |

## Decisions recorded

- **Vision cost ceiling (2026-06-11, founder):** text workloads ≤ ₹0.05; vision (watermark) ≤ ₹0.08 exception. Previously blocking image-precheck.
- **Registry approach (Director):** no `app/ai/registry.py` for V1. VERSION+WORKLOAD constants in each prompt module + `prompt_registry.resolve` IS the V1 registry.

## Prompt registry index (authoritative)

| Workload | VERSION | Prompt file | Eval path | Call site | Cost gate |
|---|---|---|---|---|---|
| smart_picker | v1 | `backend/app/ai_ops/prompts/smart_picker_v1.py` | `backend/tests/eval/smart_picker/` | `category/service.py:262` | ≤ ₹0.05 |
| autofill | v1 | `backend/app/ai_ops/prompts/autofill_v1.py` | `backend/tests/eval/autofill/` | `catalog/service.py:636` | ≤ ₹0.05 |
| watermark | v1 | `backend/app/ai_ops/prompts/watermark_v1.py` | `backend/tests/eval/watermark/` | `image/tasks.py:206` | ≤ ₹0.08 |

## Outstanding (carry forward)

- 3 FOUNDER GATE PRs (#55/#57/#59) await sibling-group slices (backend/frontend/infra tracks to deliver their slices to the integration branches first)
- All evals are deterministic token-free proxies. Live-model accuracy unknown until `GEMINI_API_KEY` lands in staging runner
- Deviation: meesell-ai-coordinator executed edits directly (Task/sub-agent tool unavailable); 3 AI specialists not dispatched separately. Next session should dispatch specialists if tool is available

## UPDATE 2026-06-11 — smart-picker BACKEND slice merged (HYBRID dispatch validated)

- **PR #72 MERGED** → `feature/smart-picker/integration` (squash `ba94543`, on top of AI slice #54). Founder gate PR #55 now carries AI + backend slices.
- **HYBRID dispatch (CLAUDE.md rule 7) executed end-to-end and validated:** coordinator SPEC (session-1 blocker session + FEATURE_PLAN templates + as-built audit) → master session dispatched 3 specialists (database-builder, api-routes-builder parallel; services-builder after config flag) → coordinator merge-gate review (PASS, real re-run of all gates).
- Delivered: `FEATURE_SMART_PICKER_ENABLED` flag (shared/config.py — NOT app/config.py, plan path was wrong) + 404 guard; 9 new unit tests + 5 smoke tests + infra-gated p95 benchmark; ci.yml `ai_eval` job (token-free deterministic runner, live-model TODO).
- **Drift accepted at gate:** `_GLOBAL_TABLES` frozenset absent from `core/tenancy.py` though §9.D/§4.C reference it. Functionally harmless. Follow-up chore queued for database-builder.
- **Remaining for gate PR #55:** frontend slice (SmartPickerComponent + rename catalog-new → smart-picker per D4). Infra handoffs: flag into k8s ConfigMaps (dev=true/staging=false), GEMINI_API_KEY_CI.
- Board flip commit on develop: `bab3a4d`.

## UPDATE 2026-06-11 — smart-picker FRONTEND port complete (supersession recovery)

- Original frontend slice REJECTED at gate (clean code, superseded): SP05 relocated smart-picker into apps/mfe-catalog remote mid-flight; founder merged gate PR #55 carrying the remote version (simulated data).
- Founder ruled: PORT onto mfe-catalog. Executed via HYBRID 3-step on slug `smart-picker-wiring`:
  - Phase A (component-builder): D4 rename inside the remote (4×R100 git mv) + SmartPickerComponent §9.E/D1 contract fix + 44 specs
  - Phase B (service-builder): HTTP CategoryService (full error matrix) + provideHttpClient(withFetch()) in BOTH shell app.config.ts AND remote main.ts (FIRST HttpClient wiring in codebase) + 20-test service spec
  - Gate: PASS — PR #98 squash c5bf304; FOUNDER GATE PR #101 open (integration → develop)
- Reference port source: local branch feature/smart-picker/frontend tip e97c4f5 (the rejected-but-proven work). Can be deleted once #101 merges.
- Remaining for F2 feature completion: founder merges #101; integration tests per §2.2; FEATURE_SMART_PICKER_ENABLED into k8s ConfigMaps (dev=true/staging=false); GEMINI_API_KEY live evals; selectCategory 422 edge noted on #101.
- LESSON (parallel-session sequencing): feature slices cut from integration branches can be superseded by concurrent MF extractions; coordinators should re-check the target area's ownership at gate time (this coordinator had pre-flagged the collision — the gate worked as designed).

## Catalog-form (+ai-autofill) backend slice — COMPLETE (2026-06-11)
- Full HYBRID 3-step executed: coordinator STEP-1 audit/SPEC → services-builder (G1/G2 flags, G3 main.py conditional include, G5 audit_mw `_is_autosave` PATCH-only widen, G7 auto-apply REMOVED per founder ruling, 30 unit tests) → api-routes-builder (G4 in-handler 404 guard exact smart-picker pattern, 7 route tests + 5 integration tests) → coordinator merge-gate PASS all 7 gaps, all 5 deviations accepted.
- Pre-dispatch rebase onto post-Gate-4 develop (a50eb87) resolved the audit_mw.py sequencing risk; status-doc conflicts resolved keeping both sides.
- Integration branch `feature/catalog-form` @ b0986f9; sub-refs /backend + /ai deleted; FOUNDER GATE PR #115 OPEN.
- Records on develop f2dd2a4 (board MERGED row, STATUS gate block, R5 signature publish — corrected to keyword-`db` form).
- **OPS LEARNING (Model C):** git D/F refname conflict — leaf `feature/catalog-form` cannot be created while `feature/catalog-form/backend` sub-ref lives. Create the integration branch BEFORE any sub-branch, or local squash-merge + sub-ref deletion is the workaround. Master-plan playbook amendment candidate.
- Founder queue: (1) merge PR #115; (2) approve §4.G amendment (coalesce widened to bare PATCH /products/{id}); (3) D/F refname playbook note; plus standing items: PR #101 (smart-picker-wiring gate), #59 image-precheck gate, infra ConfigMap flags + GEMINI_API_KEY staging, CI actAs IAM.

## Image-precheck — ALL 3 EXECUTABLE SLICES COMPLETE (2026-06-11)
- Backend slice (flag G1/G2 + §F5 6→4/40MB amendment): gate PASS → founder gate PR #118. Module was ~100% as-built on develop incl. 5-step pipeline.
- AI slice (precheck_smoke 20-image fixture, D2 Gate 2): gate PASS → founder gate PR #122 (flat lane). 22/22, 0.028s/img, ₹0. Founder rulings: G2 keep as-built 5×5/235 (plan §965/§976 amended lead-direct); G3 fix_hints = frontend static map.
- Frontend slice (wire-not-build: image.service.ts + uploader rewire off SIMULATION onto real contract): gate PASS → founder gate PR #133 (flat lane). 48 files/521 tests/0 fail. Founder rulings: R-IP-A dispatch-now manual-Bearer; R-IP-B backend contract authoritative. Wave-6 cross-ref recorded — this IS wave6-images landed early; do NOT double-dispatch in wave6-api-wiring.
- D/F refname conflict is BIDIRECTIONAL (origin rejects sub-ref push while leaf exists) — flat branch names (feature/{name}-{track}) are the working pattern when a leaf founder-gate PR is frozen open.
- 529-overload lesson: a background agent reporting "API Error 529" may STILL complete (notification was spurious); verify artifacts (PRs/refs) before re-dispatching a retry — my retry produced no duplicates but was wasted risk.
- Follow-ups queued: onReupload real file-picker re-trigger (ui-styler/Wave-6); screenshots deferred (no headless harness); infra slice HELD (GCS bucket TF + k8s ConfigMap flags — session constraint, founder call).

## 2026-06-12 — infra slice + xlsx-export slice COMPLETE
- Infra (image-precheck): PR #138 OPEN. APPLIED LIVE: gs://meesell-images (asia-south1, PAP enforced, 1yr lifecycle, objectAdmin→compute SA — K3s has no GKE WIF, reconciled to metadata-server SA grant) + dev ConfigMap 4 flags=true. Manifest-only: staging overlay (flags=false), GEMINI_API_KEY template, -Q image-tasks scaffold, runbook.
- xlsx-export backend: 6th consecutive ~100%-as-built feature. Slice = G1 flag + G2 POST-only 404 gate (GET ungated per R1) + G3 flag-404 test (4/4). Gate PASS → PR #139 OPEN (leaf d885daf, sub-ref cleaned).
- FOUNDER-GATE QUEUE: #115 #118 #122 #133 #138 #139 (six).
- QUEUED CHORES (not yet dispatched): (a) celery task_routes image.precheck→image-tasks queue in celery_app.py (inter-lead from infra; unblocks -Q uncomment); (b) FEATURE_XLSX_EXPORT_ENABLED into ConfigMaps (inter-lead to infra, 5th flag); (c) _GLOBAL_TABLES frozenset chore (database-builder, from smart-picker gate); (d) nightly ai_eval ci.yml extension for precheck eval dirs (CI track owns ci.yml); (e) onReupload file-picker re-trigger (ui-styler/Wave-6).

## 2026-06-12 — chores batch + 5th flag COMPLETE; dispatch queue DRAINED
- Backend chores (PR #143 OPEN): celery task_routes image.precheck→image-tasks (26261ce, export.xlsx stays default queue — load-bearing invariant verified) + _GLOBAL_TABLES doc-sentinel in core/tenancy.py (d262c95, R1 sentinel-only default; §19 linter untouched). Gate PASS both.
- 5th flag FEATURE_XLSX_EXPORT_ENABLED rides PR #138 (3789d7b): dev applied+verified live, staging manifest-only.
- CRITICAL OPS FINDING: infra session-1's kubectl applies hit a STALE default kubeconfig context (dead endpoint 34.180.58.185) — claims of "applied live" were false; session-2 landed all 5 flags on the real cluster (35.234.223.66 via ~/.kube/meesell-dev.yaml) for the first time. ALWAYS pin --kubeconfig in dispatch prompts for infra applies. Pods need restart to pick up envFrom.
- FOUNDER-GATE QUEUE (7): #115 #118 #122 #133 #138 #139 #143. Suggested merge order: #115→#118→#122→#133→#138→#139→#143.
- POST-MERGE FOLLOW-UPS: (a) infra 1-line -Q image-tasks uncomment in worker.yaml after #143 merges; (b) api/worker pod restart for envFrom; (c) nightly ai_eval ci.yml extension (CI track owns); (d) onReupload file-picker re-trigger (Wave-6/ui-styler).

## 2026-06-12 — ALL 7 FOUNDER GATES MERGED to develop (founder delegated: "do it")
- Merge order executed: #115 195b275 → #118 b11a539 → #122 85f7718 → #133 422dc62 → #138 97943e8 → #139 4f7e1af → #143 01abfbf. All squash --admin.
- Conflict resolutions (worktree-per-PR, master tree untouched): config.py keep-both flag blocks (3×); STATUS_* keep-both appends; board headers keep-newer/demote-to-Prior; stale catalog-form IN-PROGRESS row (reintroduced by #115's own squash) dropped at #139.
- Verified on origin/develop: 5 FEATURE_*_ENABLED flags, image-tasks routing, _GLOBAL_TABLES sentinel, status docs marker-clean. All 7 remote refs deleted. Stale local sub-refs (catalog-form/ai, /integration, xlsx-export/backend) deleted.
- GOTCHA: gh pr merge "already merged" — the first &&-chained merge attempt often succeeds even when output is swallowed; check before retrying. Mergeability cache: poll until != UNKNOWN.
- Master tree pull blocked (dirty agent-memory files) — local develop is BEHIND origin; pull when tree is clean or stash.
- Remaining: infra 1-line -Q image-tasks uncomment (now unblocked, #143 merged); pod restart for envFrom; PR #144 (infra session's, not mine).

## 2026-06-12 — V1 BACKEND FLAG STORY COMPLETE; all session lanes drained
- Flag-parity sweep (6th as-built confirmation): G1 price-calc + G2 dashboard + G3 live-preview(DARK, default False, MeesellError coded body) — gate PASS → PR #149 MERGED. Verdict table: 8 flags wired / 3 no-flag-by-design (auth-otp, customer, category-browse).
- Infra tail: PR #147 MERGED (-Q celery,image-tasks on the single worker — naive -Q image-tasks would stall export.xlsx); PR #152 MERGED (final 3 flags → ConfigMaps; dev 29 keys live, staging manifest-only-false; live-preview false everywhere).
- OPS INCIDENTS this lane: (1) #138 "applied live" was false AGAIN (ConfigMap had 0 FEATURE_* keys at #147 session start) — trust only fresh kubectl reads; (2) concurrent sibling session reverted live -Q mid-flight (last-writer-wins) — durable only post-merge+deploy; (3) AR-token 401 ErrImagePull on restart — fix: refresh-ar-token.sh + systemctl restart k3s (containerd cached auth).
- Remaining open PRs are OTHER sessions': #153 (Wave 6B onboarding founder gate), #150 (Gate-1 unit fix), #148/#146 (infra GEMINI key audit docs).
- Pending founder-side: staging soak gates per flag D2; live-preview dev flip when preview FE wires; develop deploy to ship the 9 merged squashes' images.

## 2026-06-12 — DEV DEPLOY of develop tip 067d664 (all 11 squashes incl. #153 Wave-6B) — ALL GREEN
- Cloud Build 6m11s; api+worker on api:067d664; health 200; both queues bound; 8 flags in env (live-preview dark); endpoint spot-check 401-clean; proactive AR-token refresh prevented ErrImagePull; race-check clean. PR #155 (docs record) merged.
- Founder rulings landed: #153 merged; deploy done; live-preview waits for FE wiring; staging deferred until dev soak.
- KNOWN ISSUE handed to its owning lane: CI auto-deploy gated RED at Gate-1 — event-loop bug in MY catalog-form slice's test files (test_catalog_routes.py/test_catalog_unit.py, 13 fails "no current event loop"); fix is PR #150 (another session's lane, open). When it merges, next develop push auto-redeploys idempotently. Frontend image SKIPPED by design (no Dockerfile/Deployment; federated shell INERT — frontend serving is a future lane).
