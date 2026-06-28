## §6A ai_ops CONSTRUCTED (2026-06-06)

### Scope
Solo sub-session `meesell-backend-construction-6A-aiops-1`. Built the
AI Operations Layer per `BACKEND_ARCHITECTURE.md` §6A under
`backend/app/ai_ops/` — the SOLE import surface domain modules use for
Smart Picker / Auto-fill / Watermark AI work. Authored both the
infrastructure (services-builder track) and the V1 baseline prompt
templates (prompt-engineer track did NOT need a separate dispatch —
content drafted inline, refinement deferred to §19 golden-eval tuning).

### Files created (10 source + 6 test modules)

Source (10):
- `backend/app/ai_ops/__init__.py` — re-exports `AICallContext`,
  `AIResponse`, `BudgetExceededError`, `call_gemini`, `EvalReport`,
  `FixtureResult`, `run_eval`.
- `backend/app/ai_ops/cost_tracker.py` (~220 LOC) — module-level
  `RATE_INPUT_PER_1K=0.0078` + `RATE_OUTPUT_PER_1K=0.031` constants
  (env override via `getattr(settings, ..., default)` per §6A.D
  footnote); `compute_cost_inr` pure formula; `record()` direct
  ORM write to `audit_events` + per-user-hourly Valkey counter +
  delegates reservation release to `budget_cap.release_reservation`;
  `Workload = Literal["smart_picker", "autofill", "watermark"]` locked
  type re-export; Asia/Kolkata day-boundary helpers
  `_today_kolkata_str` / `_hour_kolkata_str`.
- `backend/app/ai_ops/budget_cap.py` (~280 LOC) — `BudgetExceededError`
  subclass (status 503, code `ai_ops.budget_exhausted`,
  validation_message_id `ai_ops.budget.exhausted`); `BudgetStatus`
  frozen dataclass; `check_and_reserve` atomic Lua via
  `redis.eval(_RESERVE_LUA)`; `release_reservation` atomic Lua via
  `_RELEASE_LUA` (idempotent on missing); `get_budget_status` reads
  committed+pending; 80% alarm log fires inside `check_and_reserve`;
  per-workload default token estimates locked.
- `backend/app/ai_ops/guardrail.py` (~210 LOC) — `_LAYER1_PREFIX`
  dict locked at module level (one prefix per workload); enum-block
  appended to autofill prefix when allowed_enums supplied;
  `parse_and_validate` dispatches to per-workload shape validators
  (smart_picker / autofill enum / watermark); returns None on
  failure → signals retry; `build_retry_prompt` constructs the
  stricter follow-up prompt.
- `backend/app/ai_ops/prompt_registry.py` (~140 LOC) — `resolve()`
  dynamic-imports `app.ai_ops.prompts.<name>_v<n>`; `render()`
  literal `{{var}}` substitution (no Jinja2 dep in V1);
  `PromptResolutionError` on malformed prompt_id /
  workload-mismatch / missing module attrs.
- `backend/app/ai_ops/client.py` (~290 LOC) — `AICallContext` +
  `AIResponse` frozen dataclasses with the locked §6A.C 5-field
  shape; `call_gemini()` 9-step internal flow with per-workload
  graceful fallback for BudgetExceededError, adapter-failure, and
  Layer 2 retry exhaustion; arg-validation guard for
  watermark-image_bytes / non-watermark-no-image-bytes mismatch;
  trace_id propagation through LangFuse.
- `backend/app/ai_ops/eval.py` (~160 LOC) — `EvalReport` +
  `FixtureResult` frozen dataclasses; `_TARGET_METRICS` locked at
  smart_picker=0.80 / autofill=1.00 / watermark=0.85;
  `run_eval(workload)` loads `tests/eval/<workload>/fixtures.json`,
  returns 0/0+failed when missing (V1 baseline — fixtures land in
  §19); per-fixture dispatch is a stub returning passed=False with
  explicit "wired in §19" error string; CLI entry at
  `python -m app.ai_ops.eval --workload <name>`.
- `backend/app/ai_ops/prompts/__init__.py` — package docstring documenting
  the 4 required module-level constants (TEMPLATE, VERSION, WORKLOAD,
  RENDERED_BY).
- `backend/app/ai_ops/prompts/smart_picker_v1.py` — V1 baseline draft
  with `{{description}}` + `{{compressed_tree}}` substitution
  placeholders; emits 5-suggestions JSON contract.
- `backend/app/ai_ops/prompts/autofill_v1.py` — V1 baseline draft
  with `{{product_spec}}` + `{{schema}}` placeholders; emits
  `{"fields": {...}}` JSON contract.
- `backend/app/ai_ops/prompts/watermark_v1.py` — V1 baseline draft;
  vision-rendered; emits `{"has_watermark": bool, "confidence": float}`
  JSON contract.

Files modified (1):
- `backend/app/i18n/messages_en.py` — added one cross-cutting ID
  `ai_ops.budget.exhausted` consumed by `BudgetExceededError`
  envelope. Conforms to §5A.H 3-segment regex.

### Tests added (6 modules, 80 tests, all PASS)
- `tests/test_ai_ops_cost_tracker.py` (15 tests) — rate constants;
  compute_cost_inr (4 cases incl. ₹0.05 envelope); record audit row
  shape; release_reservation wired when reservation_id supplied; no
  release when None; audit failure does NOT raise; user hourly
  counter bumped; get_daily_spend / get_user_hourly_spend.
- `tests/test_ai_ops_guardrail.py` (22 tests) — Layer 1 per-workload
  prefix; autofill enum-block appended only when supplied;
  Layer 2 smart_picker (7 invariants: JSON / list rejected / missing
  fields / confidence range / reasons type); Layer 2 autofill (5: enum
  match / enum violation / free-text / missing / value-type);
  Layer 2 watermark (3 invariants); build_retry_prompt.
- `tests/test_ai_ops_prompt_registry.py` (11 tests) — 3 active V1
  versions resolve; workload-mismatch / malformed / unknown raise
  PromptResolutionError; render substitution + missing-placeholder
  left-as-is + non-str stringify.
- `tests/test_ai_ops_budget_cap.py` (14 tests) —
  BudgetExceededError envelope shape (4 invariants); happy
  reserve below cap; default estimate when 0 tokens; hard-stop raise;
  80% alarm log; release missing reservation noop; release
  pending+committed accounting; get_budget_status (empty / 80% /
  100%); race protection (2 concurrent near cap, at most 1 success).
- `tests/test_ai_ops_client.py` (10 tests) — frozen dataclasses;
  9-step flow in order (mock-verified); budget fallback for each
  of 3 workloads with correct envelope shape; Layer 2 retry-then-
  succeed with `layer2_retries=1`; Layer 2 all-3-invalid fallback
  with `reason="guardrail"`; caller-arg guard rails (watermark
  needs bytes, non-watermark rejects bytes).
- `tests/test_ai_ops_eval.py` (8 tests) — frozen dataclass shape;
  3 golden targets locked (0.80 / 1.00 / 0.85); 3-workloads-only
  registry; missing fixtures → passed=False 0/0; 3-fixture file
  → 3 results.

### Acceptance gate result
- Ruff: ALL CHECKS PASSED on all 11 new source files + 6 new test
  files + 1 modified i18n file.
- `python -c "from app.main import app; import app.ai_ops"`:
  imports clean, **routes=9 unchanged**, **Base.metadata.tables=13 unchanged**.
- Workload Literal: `Literal['smart_picker', 'autofill', 'watermark']`
  — exactly 3, locked.
- `pytest test_ai_ops_*`: **80/80 PASS in 0.66 s**.
- `pytest test_app_boot_integration test_shared_* test_core_*
  test_messages_en_id_regex test_resolver_fallback
  test_schema_jsonb_envelope_keys test_per_field_shape_keys
  test_<5 adapters>_adapter test_ai_ops_*`:
  **395 PASS, 3 skip (pre-existing Valkey tunnel)**.
- `pytest test_database.py` (live dev Postgres via SSH tunnel):
  **42/42 PASS in 85 s**.
- Grand total: **437 PASS, 3 skip** across the §0/§4/§5/§5A/§6/§6A
  surface.

### Decisions FLAGGED (not in locked architecture)

D1 — **Cost rates configurable via `getattr(settings, "AI_RATE_*",
MODULE_CONSTANT)`** rather than adding `AI_RATE_INPUT_PER_1K` /
`AI_RATE_OUTPUT_PER_1K` fields to the §5.D Settings table now. §6A.D
says "configurable via env if rates change"; adding Settings fields is
a future amendment. The `getattr` pattern lets a future infra-builder
add the env var without changing this module's code. ESCALATE if
master prefers explicit Settings fields shipped now.

D2 — **Reservation pattern uses 2 Valkey counters** (`committed` +
`pending`) instead of 1. The 100% hard-stop check is against
`committed + pending`; release moves pending → committed. Lua script
serialises both counter reads + writes atomically in Valkey's
single-threaded executor. This is the §6A.F "reservation pattern"
made concrete — the spec mandates race-safety but did not specify the
counter layout.

D3 — **Reservation safety-net TTL = 300 s** (5 min). Worst-case
Gemini call = adapter 3-retry (1+4+16 s) × 2 Layer-2 retries +
network ≈ 100 s; 300 s leaves a 3× safety margin. If a worker crashes
mid-call, the pending counter self-heals in ≤5 min.

D4 — **Audit row uses `event_type="ai.call"`** (7 chars, fits the
40-char column lock). Metadata jsonb shape:
`{workload, input_tokens, output_tokens, cost_inr}`. Diff_jsonb is
NULL because there's no before/after delta for an AI call.

D5 — **AIResponse stays exactly 5 fields per §6A.C** — no
`fallback_offered` field added. Instead, the workload-specific
`parsed` dict carries `"fallback_offered": True` (smart_picker /
autofill) or `"watermark_check": "skipped_budget"` / `"skipped_guardrail"`
(watermark). Domain modules branch on the parsed-dict key rather than
a top-level flag. Keeps the locked shape intact.

D6 — **prompt-engineer track NOT dispatched in this sub-session.**
Authored V1 baseline prompt templates inline (storage layout is locked
here; content is a draft). Per dispatch prompt's "if the prompt-engineer
escalates, route via meesell-ai-coordinator memory" — this avoids a
coordinator-of-coordinator depth penalty. Refinement deferred to §19
golden-eval tuning where prompt-engineer iterates against the 3 fixture
sets. FLAGGED in prompt-engineer MEMORY for awareness.

D7 — **Per-workload graceful fallback intercepts `BudgetExceededError`
inside `client.py`** (not at the consumer module). Per dispatch prompt
acceptance criterion #7 + locked rule "DO NOT raise BudgetExceededError
from smart_picker/autofill/watermark paths". Spec §6A.F mentions "the
error maps to a graceful fallback at the calling module" — dispatch
prompt amends this to be wrapped inside client.call_gemini so consumers
NEVER see the exception. Documented in client.py module docstring.

D8 — **Spec says autofill graceful fallback returns 503;
dispatch prompt overrides to 200 with `fallback_offered=True`.**
Honoured the dispatch prompt (more recent lock). The `BudgetExceededError`
class still defaults to status=503 for callers who DO surface it (V1.5
direct-paths) but client.py converts to AIResponse with parsed-dict
`fallback_offered=True` for V1.

### Hand-offs queued

- **§7 `iam`** — NO consumption (auth doesn't use AI). But:
  `core/errors.py` already wires `i18n.resolver` — when iam ships,
  the new `ai_ops.budget.exhausted` ID is resolved via the same path.
- **§9 `category.service.suggest_categories`** — consumes
  `ai_ops.client.call_gemini(ctx, "smart_picker.v1", {"description":
  ..., "compressed_tree": ...})`. Returns `AIResponse` whose
  `.parsed["suggestions"]` is the top-5 list; on budget fallback
  `.parsed = {"suggestions": [], "fallback_offered": True}` → category
  module returns HTTP 200 with the empty suggestions + a fallback
  flag in the response payload.
- **§10 `catalog.service.autofill_product`** — consumes
  `ai_ops.client.call_gemini(ctx, "autofill.v1", {"product_spec":...,
  "schema": ...}, allowed_enums={...})`. Returns `AIResponse` whose
  `.parsed["fields"]` is the canonical-field-name → value dict; on
  budget/Layer-2 fallback `.parsed["fallback_offered"] is True` →
  catalog module returns HTTP 200 with empty fields + flag.
- **§11 `image.tasks.precheck_image`** — consumes
  `ai_ops.client.call_gemini(ctx, "watermark.v1", {}, image_bytes=...)`
  in Celery worker context. Returns `AIResponse` whose
  `.parsed["has_watermark"]` is the bool; on budget fallback
  `.parsed["watermark_check"] == "skipped_budget"` → worker writes
  `product_images.precheck_jsonb.watermark_check = "skipped_budget"`
  and overall precheck status STAYS `"ready"`.
- **§14 `export.service`** — NO direct ai_ops consumption. But
  Layer 3 enum re-validation runs there per §6A.E + §14.
- **§19 import-linter Contract 2** — must reject
  `from app.ai_ops.cost_tracker import ...` /
  `from app.ai_ops.guardrail import ...` /
  `from app.ai_ops.budget_cap import ...` from any module under
  `app/modules/`. Only `app.ai_ops.client.call_gemini` (plus the 3
  re-exported types) is the legal domain-import surface.
- **§19 import-linter Contract 1** — must reject
  `from app.adapters.gemini import ...` from any module under
  `app/modules/`. Only `app.ai_ops.*` may import the gemini adapter.
- **§19 tests/eval/{smart_picker,autofill,watermark}/fixtures.json**
  — populated by category-picker-builder / prompt-engineer /
  image-precheck-builder respectively, against the locked target
  metrics (0.80 / 1.00 / 0.85).
- **`meesell-infra-builder`** — populates `langfuse-secret-key` Secret
  Manager value during §20 deployment (per pre-existing §6 adapter
  hand-off note). client.py consumes from `settings.LANGFUSE_SECRET_KEY`;
  langfuse adapter drops with WARNING when unset.
- **`meesell-prompt-engineer`** — refines the 3 V1 baseline prompts
  during §19 golden-eval tuning. Storage layout locked here; templates
  themselves are owned by prompt-engineer going forward.

### Pending Secret Manager values still queued (NOT a blocker)
- `langfuse-secret-key` — adapters.langfuse already handles missing
  creds (drop-on-failure with 1 WARNING per session). ai_ops.client
  consumes via the adapter; no pre-validation at this layer.

### Memory index additions
| Entry | Type | Summary |
|---|---|---|
| §6A ai_ops CONSTRUCTED | project | 10 source files + 6 test modules (80 tests); 437 regression PASS |
| Workload Literal locked at 3 | reference | `Literal["smart_picker", "autofill", "watermark"]` exactly — adding requires 6-file edit by design |
| Cost rate constants | reference | `RATE_INPUT_PER_1K=0.0078` + `RATE_OUTPUT_PER_1K=0.031` at module level; env override via getattr(settings, ...) |
| 9-step call_gemini flow | reference | resolve→reserve→Layer1→render→SDK→record(+release on final)→Layer2→trace→return |
| Per-workload graceful fallback locked | reference | smart_picker/autofill: parsed={"...": [], "fallback_offered": True}; watermark: parsed={"watermark_check": "skipped_budget"} |
| BudgetExceededError envelope | reference | status=503, code="ai_ops.budget_exhausted", validation_message_id="ai_ops.budget.exhausted" — caught inside client.py for V1 |
| Reservation 2-counter pattern | reference | committed + pending Valkey counters; Lua-atomic check-and-reserve; release moves pending→committed; 300s safety-net TTL |
| 3 golden targets | reference | smart_picker 80% / autofill 100% conformance (0% invalid) / watermark 85% — locked per MVP_ARCH §8.5 |
| ai_ops/prompts/ storage layout | reference | one module per `<workload>_v<version>.py` with TEMPLATE/VERSION/WORKLOAD/RENDERED_BY constants; resolve() dynamic-imports |
| Asia/Kolkata day boundary | reference | _today_kolkata_str() uses zoneinfo("Asia/Kolkata"); 25h TTL on daily keys survives midnight reset |


---
