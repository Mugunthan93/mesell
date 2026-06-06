# Sub-Session Prompt: §6A AI Operations Layer
# Wave 1 of 10 — CONSTRUCTION
# Specialist agents: meesell-services-builder + meesell-prompt-engineer (AI track)
# Renames session to: meesell-backend-construction-6A-aiops-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy the block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §6A construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-services-builder + meesell-prompt-engineer (AI track) agents operating in a dedicated construction sub-session for MeeSell §6A (AI Operations Layer).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §6A AI Operations Layer (`ai_ops/` 6-file subtree + 3 workloads: smart_picker, autofill, watermark)
- Specialist agents: meesell-services-builder (primary; owns client.py, cost_tracker.py, guardrail.py, budget_cap.py, eval.py, prompt_registry.py infrastructure) + meesell-prompt-engineer (AI track; owns prompt CONTENT inside prompt_registry storage layout)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-6A-aiops-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §6A — A through K (esp. §6A.B 3 workloads `Literal["smart_picker", "autofill", "watermark"]`, §6A.C client.py sole import surface + AICallContext + AIResponse frozen dataclasses + 9-step internal flow, §6A.D cost_tracker.py gemini-2.5-flash rates as module constants + audit_events direct-write exception, §6A.E guardrail.py Layer 1 prompt prefix + Layer 2 enum re-validation with up-to-2 retries (Layer 3 forward-referenced to §14 export), §6A.F budget_cap.py 80%-alarm + 100%-hard-stop with workload-specific graceful fallback + reservation-pattern race protection, §6A.G prompt_registry.py resolve() + Python-module prompt storage, §6A.H eval.py run_eval() with 3 golden sets).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §0 (F3 3-layer guardrail), §4 (core/), §5 (shared/Settings), §6 (adapters/gemini.py — wrapped by §6A.C; domain modules NEVER call directly per §3.G boundary rule).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §5 (AI pipeline), §8 (AI ops), §9.7 (guardrails). Cited; not amended.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (Decision 3 Gemini 2.5 Flash).

5. `.claude/agents/meesell-services-builder.md` and `.claude/agents/meesell-prompt-engineer.md` (own specs).

6. Memory: `.claude/agent-memory/meesell-services-builder/MEMORY.md` and `.claude/agent-memory/meesell-prompt-engineer/MEMORY.md`.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm §5, §4, §5A, §6 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.G:

```
backend/app/ai_ops/
├── __init__.py
├── client.py            # the wrapper every module uses — ai_ops.client.call_gemini(ctx, workload, **kwargs)
├── cost_tracker.py      # per-call tokens × ₹/1K persistence; audit_events direct-write exception per §6A.D
├── guardrail.py         # Layer 1 prompt prefix + Layer 2 parser enum re-validation with up-to-2 retries
├── budget_cap.py        # ₹500 daily cap + 80% alarm + 100% hard-stop with per-workload fallback + reservation pattern
├── prompt_registry.py   # resolve(prompt_name) → prompt template; Python-module storage layout
├── eval.py              # run_eval(golden_set) → metrics; 3 golden sets: smart_picker, autofill, watermark
└── prompts/             # storage location for prompt-engineer content
    ├── __init__.py
    ├── smart_picker_v1.py
    ├── autofill_v1.py
    └── watermark_v1.py
```

Locked invariants:
- 3 AI workloads: `Literal["smart_picker", "autofill", "watermark"]` — exactly these three in V1 (per §6A.B). Pricing AI margin guidance is V1.5+, NOT V1.
- ₹500 daily cap timezone Asia/Kolkata per §6A.F.
- Per-workload graceful fallback per §6A.F:
  - `smart_picker` budget-exhausted → return empty suggestions + `fallback_offered=True`, HTTP 200 (NOT 503).
  - `autofill` budget-exhausted → return empty fields + `fallback_offered=True`, HTTP 200.
  - `watermark` budget-exhausted → `precheck_jsonb.watermark_check = "skipped_budget"` AND overall status still `"ready"` (informational, non-blocking).
- AICallContext + AIResponse are frozen dataclasses per §6A.C.
- 9-step internal flow in `client.call_gemini`: (1) resolve prompt, (2) budget reservation, (3) Layer 1 prefix injection, (4) adapters.gemini call, (5) Layer 2 enum re-validation, (6) up to 2 retries on Layer 2 failure, (7) cost record, (8) langfuse trace emit, (9) return AIResponse.
- Cost tracker writes directly to `audit_events` table — locked documented exception to audit_mw post-commit pattern (per §6A.D + §15.E exception list).
- Per-user feature budgets (50/h autofill, 100/h picker) are NOT in §6A — they live in §4.E plan_guard.

Construction protocol:

1. **Tests first**:
   - `test_client_call_gemini_flow.py` — 9-step flow happy path; verify each step fires in order via mocks.
   - `test_cost_tracker.py` — gemini-2.5-flash rates are correct module constants; audit_events row written on call success.
   - `test_guardrail_layer1.py` — prompt prefix injected correctly.
   - `test_guardrail_layer2.py` — invalid enum from Gemini triggers retry; 3rd invalid → returns last AIResponse with `valid=False`.
   - `test_budget_cap_80_alarm.py` — at 80% utilization, alarm emitted (log + Prometheus counter); calls still succeed.
   - `test_budget_cap_100_hardstop.py` — at 100%, `BudgetExceededError` raised; reservation pattern prevents race conditions.
   - `test_per_workload_fallback.py` — each of 3 workloads has the locked fallback shape.
   - `test_prompt_registry_resolve.py` — `resolve("autofill.v1")` returns the autofill_v1 template.
   - `test_eval_run_eval.py` — 3 golden sets defined (Smart Picker top-5 recall ≥ 80%, Autofill 0% invalid enums, Watermark accuracy ≥ 85%).

2. **Implementation**: 6 ai_ops files + 3 prompt content files. Prompt CONTENT is owned by `meesell-prompt-engineer` — coordinate the prompt strings with their dispatch; infrastructure code is `meesell-services-builder`.

3. **Acceptance**: tests pass; ruff clean; boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT allow domain modules to import `adapters/gemini.py` directly (per §3.G boundary lock — `ai_ops/client.py` is the sole import surface; §19 import-linter Contract 2 enforces this).
- DO NOT add a 4th AI workload — the Literal is locked to `{"smart_picker", "autofill", "watermark"}`. Any 4th workload requires architecture amendment.
- DO NOT change the ₹500 cap or the Asia/Kolkata timezone.
- DO NOT raise `BudgetExceededError` from `smart_picker`/`autofill`/`watermark` paths — the per-workload graceful fallback is the contract; raising propagates to the consumer module which is wrong shape.
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-services-builder` — owns the 6 infrastructure files (client.py, cost_tracker.py, guardrail.py, budget_cap.py, prompt_registry.py, eval.py).
- `meesell-prompt-engineer` (AI track) — owns prompt CONTENT inside `prompts/{smart_picker,autofill,watermark}_v1.py`. The storage layout is locked here; the prompt strings (Layer 1 prefix + few-shot examples + enum constraint phrases) are theirs.

You ARE NOT permitted: any other dispatch. NOTE: coordinator usually delegates AI-track work via `meesell-ai-coordinator`, but for this sub-session you may dispatch `meesell-prompt-engineer` directly to avoid coordinator-of-coordinator depth. If the prompt-engineer escalates, route via `meesell-ai-coordinator` memory.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §6A)
═══════════════════════════════════════════════════════════════

`langfuse-secret-key` — consumed by `client.py` step 8 (LangFuse trace emit). NOT populated during this dispatch; documented as Secret Manager ref in `Settings.LANGFUSE_SECRET_KEY`. Populated during §20 deployment construction. Your job is to consume from `Settings`, not provision.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. `ai_ops/client.py` — `call_gemini(ctx: AICallContext, workload: WorkloadLiteral, **kwargs) -> AIResponse` with the 9-step internal flow.
2. `AICallContext` and `AIResponse` are frozen dataclasses (or `@dataclass(frozen=True)`).
3. 3 workloads exactly: `Literal["smart_picker", "autofill", "watermark"]`.
4. `cost_tracker.py` writes to `audit_events` table directly (locked exception per §6A.D); gemini-2.5-flash rates are module constants matching `MVP_ARCH §8.2`.
5. `guardrail.py` Layer 1 + Layer 2 wired; up to 2 retries on Layer 2 failure.
6. `budget_cap.py` enforces ₹500 daily cap Asia/Kolkata; 80% alarm + 100% hard-stop; reservation pattern prevents races.
7. Per-workload graceful fallback wired: smart_picker / autofill return 200 + `fallback_offered=True`; watermark returns `"skipped_budget"` + status still ready.
8. `prompt_registry.py` `resolve(prompt_name)` returns the template; storage at `ai_ops/prompts/<name>_v<version>.py`.
9. `eval.py` `run_eval(golden_set)` defined; 3 golden sets stubbed (full fixture data lands in §19 tests construction).

Plus universal: all tests pass; ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update both specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §6A ai_ops CONSTRUCTED ===
   Files created: ai_ops/{client.py, cost_tracker.py, guardrail.py, budget_cap.py, prompt_registry.py, eval.py} + prompts/{smart_picker_v1.py, autofill_v1.py, watermark_v1.py}
   Tests added: 9 unit test classes
   Decisions made: <list>
   Hand-offs: §9 category (consumes smart_picker.v1) + §10 catalog (consumes autofill.v1) + §11 image task (consumes watermark.v1)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Reservation pattern race not provable to be safe (e.g. Valkey TTL edge case).
- Prompt-engineer needs a 4th workload (escalate — locked at 3).
- Cost rates change (escalate — locked at module constants).
- Layer 2 enum re-validation ambiguity (e.g. retry count vs response shape).

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-6A-aiops-1`
2. Read REQUIRED READING.
3. Confirm §5 + §4 + §5A + §6 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §6A construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 1 of 10
- **Sequential dependency:** §5, §4, §5A, §6 CONSTRUCTED.
- **Parallel-safe?:** No — Wave 1 sequential. §6A is the last Wave 1 step.
- **Expected duration estimate:** ~8-12 hours (infrastructure-heavy; prompt-engineer coordination).
- **Acceptance verification by master:** (1) `grep -r "from app.adapters.gemini import" backend/app/modules/` returns nothing (the §3.G boundary holds); (2) workload Literal exactly 3 values; (3) ₹500 + Asia/Kolkata constants present; (4) cost_tracker writes to audit_events table directly (grep `audit_events` in `ai_ops/cost_tracker.py`); (5) STATUS_BACKEND.md UPDATE block present.
