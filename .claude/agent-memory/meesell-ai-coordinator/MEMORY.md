# Memory — meesell-ai-coordinator

## Agent Identity
AI coordinator for MeeSell. Orchestrates Gemini 2.5 Flash integration across 3 AI specialists (prompt-engineer, category-picker, image-precheck). Owns STATUS_AI.md, prompt registry index, eval organisation, cost monitoring. Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## MEMORY.md
(Index of memory files — populated as agent works)

---

## Session mesell-knowledge-sync-ai-session-1 — completed (READ-ONLY surface map)

Non-obvious findings only (the obvious file inventory is in BACKEND_ARCHITECTURE §6A and the call sites):

- **PROMPT REGISTRY FILE NAME DRIFT vs my own spec.** My agent spec + Owns section repeatedly cite `backend/app/ai/registry.py` and `backend/app/ai_engine.py` as the registry index + orchestration scaffold I own. **Neither exists.** The actual implementation is `backend/app/ai_ops/prompt_registry.py` (dynamic-import resolver, NOT a static index/ledger) and there is NO `ai_engine.py` orchestration scaffold — the 9-step orchestration lives inside `ai_ops/client.py:call_gemini`. **There is no separate cost-ledger registry data structure**: versions are hardcoded (`smart_picker.v1`/`autofill.v1`/`watermark.v1` resolved by `<name>_v<version>` module import), and cost is computed live in `cost_tracker.compute_cost_inr` (no per-prompt observed-cost table). My merge-gate checklist item "registry entry updated in registry.py with observed cost" has NO file to write to — I must either (a) treat the prompt module's VERSION constant + this MEMORY as the registry, or (b) create `app/ai/registry.py` as a new ledger. Flag to founder before first merge gate.

- **WATERMARK GOLDEN SET IS 14/16, NOT 50/50.** My own prior memory + the watermark_v1.py docstring + eval.py docstring all say "30 images (50/50 watermarked/clean)". Actual fixtures.json = 30 fixtures, **14 watermarked / 16 clean** (eval_results.json confirms). The 50/50 phrasing in 3 docstrings is stale/aspirational. Accuracy threshold ≥85% met (30/30=100% deterministic-proxy). Not blocking, but correct the docstrings when prompt-engineer next touches watermark.

- **AUTOFILL FIXTURES LIVE AT `tests/eval/fixtures.json` (ROOT), NOT `tests/eval/autofill/fixtures.json`.** The `tests/eval/autofill/` dir holds ONLY `eval_results.json` — the fixtures + runner (`run_autofill_eval.py`) sit at the eval root. BUT `ai_ops/eval.py:_fixtures_path` expects `tests/eval/<workload>/fixtures.json` for ALL workloads. So the §6A.H production runner (`ai_ops.eval.run_eval`) would find 0 autofill fixtures (looks in `tests/eval/autofill/`) while the deterministic audit runner finds 30 (root). Path mismatch to reconcile before wiring run_eval to live model.

- **EVALS ARE DETERMINISTIC TOKEN-FREE PROXIES, NOT LIVE-MODEL.** All 3 eval_results.json show 100% but these are deterministic heuristic runners (`run_eval.py`/`run_autofill_eval.py`/`run_watermark_eval.py`) that mirror picker/guardrail/watermark decision RULES — they make ZERO Gemini calls. `ai_ops/eval.py:_run_one_fixture` is still a §19 skeleton returning `passed=False` (NOT wired to call_gemini). LIVE-model accuracy is UNKNOWN until GEMINI_API_KEY lands in a staging runner. The 80/0/85 thresholds are proven against proxies only. This is the real state behind the green board.

- **VISION COST CEILING STILL UNDECIDED (blocks image-precheck dispatch).** Confirmed unchanged: text ceiling ≤₹0.05 is my locked merge gate; watermark vision runs ₹0.06–0.08 multimodal in practice. Founder pre-decision (vision exception ≤₹0.08 vs strict ≤₹0.05) still OUTSTANDING per image-precheck Risk Register R3. Do NOT dispatch prompt-engineer for watermark until settled.

- **CONTRACT vs §6A: ALIGNED.** Client 9-step flow, frozen AICallContext/AIResponse dataclasses, 3-layer guardrail (Layer1 prefix bonded-to-workload, Layer2 enum re-validate, Layer3 export-time owned by export module), budget_cap two-counter Lua reservation pattern (committed+pending vs ₹500 cap, Asia/Kolkata day), cost_tracker rates (input ₹0.0078/1k, output ₹0.031/1k per MVP_ARCH §8.2), and all 3 call sites (category.service:259 / catalog.service:626 / image.tasks:200) match the locked client signature. No drift in the seam itself.

---

## Session mesell-image-precheck-planning-session-1 — completed (held for master consolidation)

- Feature: **image-precheck** (V1 Feature 5 — JPEG / RGB / resolution ≥1500×1500 / white-BG / watermark vision)
- FEATURE_PLAN.md: `docs/plans/features/image-precheck/FEATURE_PLAN.md` — **1,584 lines** covering 9 required sections (Decisions / Agent lineup / Code surfaces / Documentation deliverables / Dispatch templates [8] / Review + iteration protocol / Acceptance gate / Risk register / Revision history) PLUS two additions (Branch setup, Memory namespace convention) installed in response to founder concerns about coordination/branches/per-feature memory hygiene
- Outstanding founder decisions: **1 pre-decision recommended before AI dispatch** — vision per-call cost ceiling. The ai-coordinator merge gate locks ≤ ₹0.05 per call (text-call ceiling); watermark vision is multimodal and runs ₹0.06-0.08 in practice. Risk Register R3 recommends founder pre-approve either (a) a vision-specific exception (text ≤ ₹0.05 / vision ≤ ₹0.08) or (b) hold prompt-engineer to ≤ ₹0.05 strict. Either is workable; the cost ceiling needs to be settled BEFORE prompt-engineer dispatch to avoid mid-iteration escalation. D1/D2/D3 themselves are locked verbatim at the top of FEATURE_PLAN.md.

---

## Session mesell-ai-autofill-planning-session-1 — completed (held for master consolidation)

- Feature: **ai-autofill** (V1 Feature 4 — Gemini fills compulsory product fields from description; 0% invalid-enum rate non-negotiable per §6A.E)
- FEATURE_PLAN.md: `docs/plans/features/ai-autofill/FEATURE_PLAN.md` — **855 lines** covering all 9 required sections (Decisions / Lead-Agent assignment / Branch lifecycle / Code surfaces / Documentation deliverables / Dispatch templates [5 unconditional + 1 conditional] / Cross-feature memory protocol / Review + iteration protocol / Acceptance gate / Risk register / Follow-up actions / Revision history) PLUS three structural additions (Lead/Agent lockdown, Branch lifecycle section, Cross-feature memory protocol) installed in response to founder ratification of structural resolutions A/B/C
- Outstanding founder decisions: **NONE for this feature** — D1/D2/D3 are locked verbatim at the top of FEATURE_PLAN.md (D1=brief verbatim + §6A.F housekeeping, D2=FEATURE_AI_AUTOFILL_ENABLED with 24h staging soak, D3=after smart-picker+catalog-form). Structural resolutions A/B/C also locked.
- Three follow-up PRs queued (separate from feature delivery, separate from this consolidation): `chore/§6A.F-text-housekeeping` (doc-text 503→200+fallback), `docs/master-plan-amend-cross-feature-memory` (promote resolution C to MASTER_PLAN.md §6/§7 so the per-feature memory pattern applies to all 9 V1 features), and `chore/broadcast-ai-autofill-feature-register` (one-shot fan-out of feature register stubs to all 18 agents' MEMORY.md after this PR merges).
- **Coordination interrupt deviation — REPORTING HONESTLY:** my session committed (`5da5379`) + pushed (`origin/feature/ai-autofill/planning`) + opened PR #4 (https://github.com/Mugunthan93/mesell/pull/4) BEFORE the coordination interrupt arrived. Mid-session, a sibling sub-session also switched the working branch causing my commit to initially land on `feature/catalog-form/planning`; I recovered via cherry-pick (commit moved to `feature/ai-autofill/planning`) + `git branch -f feature/catalog-form/planning origin/develop` (restored catalog-form to clean develop state, no work lost). All git mutations from my session are now reported here for master consolidation reconciliation. From the moment the interrupt arrived I have run ZERO state-changing git commands — only read-only `git status`, `git log`, `git show`, `git ls-remote`. The remote `origin/feature/ai-autofill/planning` and remote PR #4 still exist and may need master action (close PR / re-target branch / consolidate into the master's batch).

---

## Session mesell-smart-picker-planning-session-1 — completed (held for master consolidation)

- Feature: **smart-picker** (V1 Feature 2 — description → top-5 Meesho leaves; UI renders top-3; differentiator AI feature; first AI workload to ship per D3, shapes the `ai_ops/` contract for ai-autofill + image-precheck to rebase on)
- FEATURE_PLAN.md: `docs/plans/features/smart-picker/FEATURE_PLAN.md` — **959 lines** covering all 9 required sections (Decisions / Agent lineup / Code surfaces / Documentation deliverables / Dispatch templates [7 mandatory + 1 conditional] / Review + iteration protocol / Acceptance gate / Risk register / Revision history) PLUS three additions (Mandatory read declaration at top per G4, Cross-group merge ordering rule "AI first → backend rebases", Shared MEMORY DISCIPLINE block reproduced in every dispatch template per G3). Architectural tensions surfaced and resolved with founder in-session: (a) top-3 vs top-5 → backend returns up to 5, FE shows top 3; (b) ILIKE-inside-/suggest vs `fallback_offered=true` routing to `/browse` → graceful 200 + flag (architecture-aligned); (c) frontend folder `catalog-new` → `smart-picker` rename per FRONTEND_ARCHITECTURE §4 line 418.
- Outstanding founder decisions: **NONE for this feature** — all 8 decisions (G1 full lineup, G2 planning-now + group-branches-lazy, G3 4-part per-feature memory + feature_board PENDING + dispatch-template MEMORY DISCIPLINE block, G4 FEATURE_PLAN.md mandatory read; D1 arch-aligned scope, D2 standard `FEATURE_SMART_PICKER_ENABLED` flag with 24h staging soak, D3 Smart Picker first among AI features, D4 rename `catalog-new` → `smart-picker`) locked verbatim at the top of FEATURE_PLAN.md.
- Critical existing-scaffold note: the smart picker backend is ALREADY scaffolded (per commits `c9a2312` AI eval golden sets + `43abd23` V1 backend construction complete). `backend/app/modules/category/` carries `router.py:88 suggest_categories` route + `service.py:192 suggest_categories()` service + `picker.py` (369-line ranker pipeline). `backend/app/ai_ops/` carries the full client/cost_tracker/guardrail/budget_cap/prompt_registry/eval seam. `backend/app/ai_ops/prompts/smart_picker_v1.py` (156 lines) exists. `backend/tests/eval/smart_picker/` carries `fixtures.json` + `run_eval.py`. Execution dispatches are VALIDATE + iterate, NOT build-from-zero — the plan's Code Surfaces table reflects this with VERIFY + MODIFY statuses rather than NEW statuses on most backend files.
- **Coordination interrupt deviation — REPORTING HONESTLY:** my session committed (`b903f42` after rebase, was `cdbf4d5` pre-rebase) + pushed (`origin/feature/smart-picker/planning`) + opened PR #6 (https://github.com/Mugunthan93/mesell/pull/6) BEFORE the coordination interrupt arrived. Mid-session, the initial commit landed on `feature/auth-otp/planning` (the working tree had been switched by a sibling sub-session); I recovered via `git branch -f feature/smart-picker/planning HEAD` (moved smart-picker pointer to my commit) + `git reset --hard HEAD~1` (restored auth-otp/planning back to its prior tip `c1a41e9`, no auth-otp work lost) + `git rebase --onto origin/develop c1a41e9` (replayed my commit onto a clean develop parent so the planning PR is linear). All git mutations from my session are now reported here for master consolidation reconciliation. From the moment the interrupt arrived I have run ZERO state-changing git commands — only read-only `git status`, `git log`, `git show`, `git ls-remote`. The remote `origin/feature/smart-picker/planning` and remote PR #6 still exist and may need master action (close PR / re-target branch / consolidate into the master's batch).

---

## Session mesell-ai-track-session-1 — completed (AI track EXECUTION, F2/F4/F5 delivered to integration)

**Outcome:** all 3 AI group PRs gate-merged to their integration branches; 3 founder-gate PRs opened (left open per D1).

| Feature | Workload | Group PR (merged→integration) | Founder gate PR (open→develop) | Eval |
|---|---|---|---|---|
| F2 smart-picker | smart_picker | #54 | #55 | top-5 recall 100% (≥80%) |
| F4 catalog-form | autofill | #56 | #57 | invalid-enum 0% (=0%) + drop controls 2/2 |
| F5 image-precheck | watermark | #58 | #59 | accuracy 100% (≥85%) |

**Changes shipped (contained validation/integration edits — brief pre-specified each):**
- smart_picker_v1.py: added closing JSON-schema instruction (final TEMPLATE paragraph), aligned to guardrail Layer 2 `{suggestions:[{category_id,confidence,reasons}]}`. Layer 1 prefix already opens with the shape; this closes it. VERSION stays v1 (content edit, contract unchanged).
- autofill: `git mv` fixtures.json + run_autofill_eval.py from `tests/eval/` root → `tests/eval/autofill/` (so `ai_ops.eval._fixtures_path` = `tests/eval/<workload>/fixtures.json` resolves). FIXED a latent bug in the runner: `_RESULTS_PATH = _HERE/"autofill"/"eval_results.json"` would double-nest once the runner moved INTO autofill/ → changed to `_HERE/"eval_results.json"`. autofill_v1.py: closing JSON instruction `{fields:{name:value}}`.
- watermark_v1.py: docstring `50/50 watermarked/clean` → `14 watermarked / 16 clean` (the long-standing stale text my prior memory flagged). TEMPLATE already had the JSON output instruction — no body change. image-precheck FEATURE_PLAN.md R3: appended AMENDMENT recording founder's vision cost-ceiling exception.

**DECISIONS / gaps RESOLVED this session:**
- **Vision cost ceiling SETTLED** (was the long-outstanding blocker in my memory): founder approved text ≤ ₹0.05 / **vision ≤ ₹0.08**. Recorded in image-precheck FEATURE_PLAN R3 AMENDMENT 2026-06-11. My watermark merge gate is now ≤ ₹0.08, NOT ≤ ₹0.05. image-precheck is UNBLOCKED.
- **Registry file drift RESOLVED** per Director §1.2: do NOT create `app/ai/registry.py` for V1. The VERSION+WORKLOAD constants in each prompt module + `prompt_registry.resolve('<wl>.v1','<wl>')` dynamic import IS the V1 registry. My merge-gate "registry entry updated" = verify VERSION/WORKLOAD set + resolves. Confirmed all 3.
- **Autofill fixture path mismatch RESOLVED** (was flagged in my surface-map memory): fixtures now under `tests/eval/autofill/`.
- **Watermark 50/50 docstring drift RESOLVED.**

**STILL TRUE / carry forward:**
- Evals are DETERMINISTIC TOKEN-FREE PROXIES (100% on all 3). Live-model accuracy UNKNOWN until GEMINI_API_KEY lands in a staging runner; `ai_ops.eval._run_one_fixture` is still a skeleton (passed=False). LangFuse traces + real per-call cost ($/₹ + tokens) are N/A until then. I marked LangFuse fields "N/A for V1" in all 3 PRs (NOT placeholders).
- All 3 call sites stay wired to the locked `call_gemini` signature: `category/service.py:262`, `catalog/service.py:636`, `image/tasks.py:206`. 5-step precheck pipeline fully present in `image/tasks.py` (`_check_jpeg/_check_color_space/_check_resolution/_check_white_background/_check_watermark`, `_run_precheck_pipeline`, `image_precheck_task`) — no backend-plumbing blocker.
- Guardrail Layer 2 validators are the AUTHORITATIVE output contract — they do NOT validate the brief's extra `fallback_offered` (autofill) / `watermark_type`+`reason` (watermark) keys. I aligned all prompt JSON instructions to the GUARDRAIL shape, not the brief's superset, to avoid the model emitting fields the guardrail silently drops. If a future spec wants those fields, the guardrail validator must be extended FIRST (backend coordination), then the prompt.

**ENVIRONMENT DEVIATION — REPORTING HONESTLY:** the Task/sub-agent dispatch tool was NOT available in this execution context (`No such tool available: Task`). I could NOT dispatch the 3 AI specialists (prompt-engineer / category-picker-builder / image-precheck-builder). The brief enumerated the EXACT mechanical edits per feature, so as lead I executed those contained validation/integration edits directly at the merge seam (the lead owns the integration seams; these were not open-ended specialist authoring). No few-shot banks, no new prompt versions, no pipeline rewrites — only the brief's specified edits. Future sessions: dispatch specialists when the tool is available; prompt-engineer should own any genuine prompt-content iteration.

**GIT HYGIENE this session (clean — Model C respected):** all 3 features built in worktrees under `/tmp/mesell-wt/` (`smart-picker-ai`, `catalog-form-ai`, `image-precheck-ai`), each removed after its founder-gate PR opened. Master tree stayed on develop throughout. Integration branches created lazily off origin/develop. Status/board/this-memory committed via a detached `/tmp/mesell-wt/status-develop` worktree pushed direct to develop (F2 status-only exception, Master Plan §2). 3 integration branches now on origin: `feature/{smart-picker,catalog-form,image-precheck}/integration`. The 3 `/ai` group branches remain on origin (GitHub auto-delete may reap them post-merge; harmless).
