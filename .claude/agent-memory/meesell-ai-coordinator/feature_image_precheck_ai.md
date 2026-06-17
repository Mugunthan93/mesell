# feature_image_precheck_ai — image-precheck (F5) AI lead memo

## Session mesell-image-precheck-ai-session-2 — 2026-06-11 — STEP 1 (audit + SPEC + branch)

### Audit verdict: PIPELINE AS-BUILT OK
`backend/app/modules/image/tasks.py` on origin/develop @ dd5ae0d carries the FULL 5-step body.
Each step verified against FEATURE_PLAN §960-967 + V1 §F5 + §11.E:
- Step 1 `_check_jpeg` (tasks.py:82) — Pillow open, format JPEG/JPG, early-exit on fail. MATCHES.
- Step 2 `_check_color_space` (tasks.py:102) — RGB/RGBA→RGB, CMYK→CMYK, L/LA/other→Gray. MATCHES.
- Step 3 `_check_resolution` (tasks.py:123) — w≥1500 AND h≥1500. MATCHES.
- Step 4 `_check_white_background` (tasks.py:129) — 4 corners, 5×5 patch, threshold 235. SEE G2.
- Step 5 `_check_watermark` (tasks.py:178) — ai_ops.client.call_gemini(prompt_id="watermark.v1",
  workload="watermark", image_bytes=...); maps has_watermark/confidence; BudgetExceededError→"skipped_budget";
  informational (does NOT gate status). MATCHES the contract.
- `_run_precheck_pipeline` (tasks.py:252) — deterministic_pass = jpeg AND color==RGB AND resolution AND
  white_bg; watermark informational. MATCHES §967.
- `image_precheck_task` @shared_task wrapper + asyncio.run. MATCHES (services-builder shell).
NO pipeline rebuild needed. Backend memo (feature_image_precheck_backend.md) independently confirms same.

### REAL GAPS (G-numbered, file:line evidence)
- **G1 (PRIMARY, real deliverable):** `backend/tests/eval/precheck_smoke/` ABSENT on origin/develop
  (git ls-tree confirmed). FEATURE_PLAN rows 25-26 + §976-992 + D2 Gate 2. 20-image deterministic smoke
  (10 bad / 10 good) + runner + __init__. Owner: meesell-image-precheck-builder. This is THE gap.
- **G2 (DEVIATION — founder ruling):** white-BG constants drift. As-built = 4 corners × **5×5** patch ×
  threshold **235** (tasks.py:152-173). FEATURE_PLAN §965 + acceptance §965 = **16×16** patch ×
  threshold **240** + ImageStat.Stat mean. Functionally similar but the smoke fixture's known-good images
  must pass whichever constants are canonical. RECOMMEND: keep as-built (5×5/235) as V1 canonical and amend
  the plan text (the plan itself says "V1 algorithm — V1.5 may iterate"), generate the 10 good fixtures to
  pass the AS-BUILT thresholds. Founder to confirm.
- **G3 (DEVIATION — founder ruling):** NO `fix_hints` map in precheck_jsonb (grep 0 on develop tasks.py).
  FEATURE_PLAN acceptance §968 + V1 §F5 line 226 ("per-check pass/fail with one-line fix hint") require it.
  As-built precheck_jsonb has 6 keys, no hints. RECOMMEND: decide whether fix hints are (a) built in
  tasks.py precheck_jsonb, (b) derived at the schema/router layer (api-routes-builder), or (c) i18n-keyed
  on the frontend. This crosses the §11.A seam (tasks.py is co-owned). If (a), it's a tasks.py edit by
  image-precheck-builder; if (b)/(c) it's NOT this specialist's scope. Founder to rule before STEP 2 so the
  SPEC scope is correct.

### SPEC scope decision
SPEC for STEP 2 covers G1 ONLY (precheck_smoke fixture + runner) — that is unambiguous and owned by the
specialist. G2/G3 are deviations needing founder ruling; do NOT fold into the SPEC until ruled. If founder
rules G2=keep-as-built and G3=tasks.py, the SPEC gets a small addendum. The SPEC mandates PIL-generated
fixtures, NO live Gemini, NO GEMINI_API_KEY (the 4 deterministic Pillow checks are token-free; watermark
step is out of smoke scope per FEATURE_PLAN §999 "Pillow vs vision, different purpose").

### Branch / worktree
- FLAT branch `feature/image-precheck-ai` (leaf `feature/image-precheck` exists on origin → sub-ref D/F
  conflict, proven twice; flat name avoids it). Cut off origin/develop @ dd5ae0d. Pushed origin. Worktree
  /tmp/mesell-wt/image-precheck-ai. Board+STATUS committed 552b7c4, pushed.
- Master tree write guard-blocked (bg isolation) — used worktree commits + Bash heredoc for memory. Expected.

### Merge gate (STEP 3) reminders
- watermark accuracy ≥85% (already PR #58, deterministic proxy 100%).
- precheck_smoke must be 20/20 + per-image Pillow ≤2s timing assertion.
- vision per-call ≤ ₹0.08 (founder R3 exception) — N/A for the smoke fixture (no Gemini).
- registry discipline: VERSION/WORKLOAD constants + prompt_registry.resolve IS the registry (no registry.py).
- Squash-merge feature/image-precheck-ai → leaf reconstituted at group-PR time (do NOT push leaf + sub-ref together).

## Session mesell-image-precheck-ai-session-2 — 2026-06-11 — STEP 3 (MERGE GATE)

### VERDICT: PASS
Diff scope = `tests/eval/precheck_smoke/` ONLY (25 files) + my STATUS/board/FEATURE_PLAN amend. No backend/app/, FE, k8s, terraform.
Re-ran independently (master .venv, full dummy env exported per brief — conftest still fail-fasts on ~17 vars so the in-module setdefault is NOT enough for full-tree collection; export the set): **22/22 PASS, 0.26s suite, worst-case 0.028s vs 2s budget, 0 Gemini, ₹0.00.** grep confirms no call_gemini/network/_check_watermark in smoke. single-open contract honored. eval_results.json shape mirrors watermark sibling.

### Deviations adjudicated (both ACCEPTED)
- D1 in-module dummy-env setdefault: non-destructive, conftest untouched (services-builder scope), no secret leak, dummy GEMINI key never hits network. ACCEPT.
- D2 gen_fixtures.py committed: reproducibility = golden-set hygiene. ACCEPT.

### Founder rulings disposed
- G2 (white-BG 5×5/235 keep-as-built): plan §965 step-5 line + §976 docstring-acceptance line amended to match code, AI lead-direct (§F5 doc-status-line precedent; line's own "V1.5 may iterate" posture ≠ §7.3 LOCK). NOT a founder queue item.
- G3 (fix_hints = FE static map, NOT AI/backend): noted in plan §968 amendment + PR body. §968/§F5 traceability → FE slice (frontend-coordinator). Hint copy retained in plan as canonical SOURCE. NOT an AI/backend deliverable.

### Lane choice
FLAT-LANE founder-gate PR `feature/image-precheck-ai` → `develop`, titled [FOUNDER GATE — DO NOT MERGE]. Chosen over merging into frozen open #118 (backend leaf founder gate) — flat lane is its own gate, avoids touching #118.

### Discipline note
No IN REVIEW board transition this feature: master dispatched the specialist who committed direct to the flat branch (no group PR). On the AI flat-lane flow the lead opens the founder-gate PR at gate time, so the row went IN PROGRESS → MERGED/founder-gate-open in one edit. Not a defect — expected for flat lanes.

### Carry-forward
- precheck_smoke is DETERMINISTIC Pillow-only (token-free). Live watermark vision still UNKNOWN until GEMINI_API_KEY staging runner (same as the other 3 evals).
- §965/§976 plan now say 5×5/235 (was 16×16/240). If a future audit cites 16×16/240, it's reading a pre-amendment copy.
