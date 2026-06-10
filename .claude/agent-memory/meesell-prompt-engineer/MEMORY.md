# Memory — meesell-prompt-engineer

## Agent Identity
Gemini prompt template specialist for MeeSell. Owns prompt templates (category_suggest, autofill, watermark_vision), Pydantic parsers, YAML eval fixtures, few-shot banks. Decentralized memory ecosystem.

## §6A storage layout & V1 baseline drafts (2026-06-06)

### Where prompts live
`backend/app/ai_ops/prompts/` — one Python module per `<workload>_v<version>`:
- `smart_picker_v1.py`
- `autofill_v1.py`
- `watermark_v1.py`

Each module exposes 4 module-level constants:
- `TEMPLATE: str` — body with `{{var}}` placeholders (Python `str.replace`-style; no Jinja2 dep in V1).
- `VERSION: str` — e.g. `"v1"`.
- `WORKLOAD: str` — must match one of `smart_picker` / `autofill` / `watermark`.
- `RENDERED_BY: str` — `"text"` for smart_picker/autofill; `"vision"` for watermark.

Loaded via `app.ai_ops.prompt_registry.resolve(prompt_id, workload)` which dynamic-imports the module by name.

### V1 baseline drafts (authored by services-builder for storage integration)
Services-builder authored V1 baseline drafts during the §6A construction dispatch to satisfy the package-load smoke test. The CONTENT is considered a starting draft, NOT a tuned prompt. **Prompt-engineer owns iteration going forward.**

- **smart_picker_v1.py** — takes `{{description}}` + `{{compressed_tree}}`; instructs Gemini to emit top-5 ranked suggestions JSON.
- **autofill_v1.py** — takes `{{product_spec}}` + `{{schema}}`; instructs Gemini to emit `{"fields": {...}}` with allowed-enum compliance.
- **watermark_v1.py** — vision-rendered; no `{{vars}}` (image bytes passed separately to `call_gemini`); emits `{"has_watermark": bool, "confidence": float}`.

### What prompt-engineer owns going forward
1. **Refining each TEMPLATE body** during §19 golden-eval tuning:
   - Smart Picker: 50-description golden set; target top-5 recall ≥ 80% per `MVP_ARCH §8.5`.
   - Autofill: 30-spec golden set; target 0% invalid enum values per `MVP_ARCH §8.5`.
   - Watermark: 30-image golden set (50/50); target accuracy ≥ 85% per `MVP_ARCH §8.5`.
2. **Few-shot example bank** for each workload — append in-line within `TEMPLATE` (no separate fixture file in V1; can be split out in V1.5).
3. **Adding `_v2`, `_v3` modules** when prompt revisions ship. V1.5 active-version dispatch via Valkey config flag `meesell:ai_ops:active_version:{workload}` is locked but DEFERRED in V1 (hardcoded `v1`).

### What is NOT prompt-engineer's concern
- **Layer 1 prefix** lives in `ai_ops/guardrail.py` `_LAYER1_PREFIX` (one prefix per workload, bonded to workload not to template). The locked rule per §6A.E: "the prefix is bonded to the workload, not to the prompt template (so it cannot be accidentally removed when prompt-engineer ships a new template version)." This means the JSON-shape constraint signal is in guardrail.py, not in your template. Your template instructs the model on *what* to do given the inputs; guardrail.py enforces the *shape* contract.
- **Enum allowlist block** is appended to autofill's Layer 1 prefix by `guardrail.apply_prompt_constraint` when `allowed_enums` is supplied. Do NOT duplicate it in the template body — guardrail.py builds the human-readable block from the caller-supplied dict.
- **Output parsing** is handled by `guardrail.parse_and_validate` Layer 2. Your template must emit JSON conforming to the locked shape per workload (see §6A.E shape per workload), but you do NOT write the parser.
- **Cost / budget / observability** all live in `ai_ops/` and you do not touch them.

### Cross-agent notes I picked up

From **meesell-services-builder MEMORY (§6A entry)**:
- `Workload = Literal["smart_picker", "autofill", "watermark"]` — exactly 3, locked. Adding a 4th requires architecture amendment.
- `client.py` runs 9 steps in order per §6A.C; you can verify by reading the module docstring.
- Per-workload graceful fallback: smart_picker/autofill set `parsed["fallback_offered"]=True`; watermark sets `parsed["watermark_check"]="skipped_budget"`. AIResponse shape is locked at 5 fields — fallback signal lives INSIDE `parsed`.
- Cost target per call: ≤ ₹0.05 average per `MVP_ARCH §8.2`. The autofill prompt's enum-allowlist block is the largest single token cost — keep schemas compressed per `MVP_ARCH §8.2`.

### Hand-offs to me from §19
When the golden-eval-set fixtures land (`tests/eval/smart_picker/fixtures.json` etc.), `ai_ops.eval.run_eval(workload)` runs each fixture end-to-end through `call_gemini`. The per-fixture dispatch logic inside `_run_one_fixture` is a stub in V1 (returns `passed=False`) — §19 wires the actual fixture-shape parser per workload (e.g. smart_picker fixture has `{description, expected_top5}`, autofill has `{spec, expected_fields, allowed_enums}`, watermark has `{image_path, expected_has_watermark}`).

You'll iterate the TEMPLATE body until `run_eval(workload).passed == True` for each of the 3 sets. Treat each tuning pass as a new template version (`_v2`, `_v3`) if the changes are substantive; in-place edits to `_v1` are fine for tuning-pass-1 only.

### Reference paths
- Templates: `backend/app/ai_ops/prompts/<workload>_v<version>.py`
- Layer 1 prefixes (read-only for me): `backend/app/ai_ops/guardrail.py` `_LAYER1_PREFIX`
- Layer 2 parsers (read-only for me): `backend/app/ai_ops/guardrail.py` `parse_and_validate` + shape validators
- Cost formula (read-only for me): `backend/app/ai_ops/cost_tracker.py` `compute_cost_inr`
- Eval runner: `backend/app/ai_ops/eval.py` `run_eval`
- 3 target metrics locked: smart_picker=0.80, autofill=1.00, watermark=0.85 per `MVP_ARCH §8.5`

## Memory index
| Entry | Type | Summary |
|---|---|---|
| §6A storage layout 2026-06-06 | reference | prompt CONTENT lives in `ai_ops/prompts/<workload>_v<version>.py` with 4 required module-level constants (TEMPLATE/VERSION/WORKLOAD/RENDERED_BY); V1 baselines drafted by services-builder, ownership transfers to prompt-engineer for §19 golden-eval tuning |
| Layer 1 prefix is NOT mine | reference | guardrail.py owns the workload-bonded JSON-shape prefix; prompt-engineer template body excludes the prefix concern |
| 3 golden targets | reference | smart_picker 80% top-5 recall / autofill 100% conformance (0% invalid enum) / watermark 85% accuracy per MVP_ARCH §8.5 |
| Output shape locks | reference | smart_picker emits `{"suggestions": [{"category_id", "confidence", "reasons"}]}`; autofill emits `{"fields": {<canonical>: <value>}}`; watermark emits `{"has_watermark": bool, "confidence": float}` |
| Versioning | reference | V1 ships `_v1` per workload, hardcoded; V1.5 A/B routing via Valkey flag `meesell:ai_ops:active_version:{workload}` is locked but DEFERRED |
| Per-call cost target | reference | ≤ ₹0.05 average per MVP_ARCH §8.2 — autofill's enum-allowlist block is the largest single token cost |

## §10 catalog autofill.v1 — CONSUMED 2026-06-07 (sub-session 1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| autofill.v1 template inputs (consumed by §10) | reference | catalog.service.autofill_product passes {{product_spec}} = "<description>\n\nAlready filled:\n  k: v\n...\n\nFill only these fields:\n  - k\n..."; {{schema}} = "- {canonical} ({data_type}, {marker}) allowed=[...]\n..." with top-10 enum preview per field |
| autofill output → AutofillSuggestion mapping | reference | service treats every emitted field with confidence=0.9 (D4); maps to AutofillSuggestionInternal(canonical_name, value, confidence, source="ai"); auto-apply floor 0.85 per MVP_ARCH §5.2 |
| autofill graceful fallback shape | reference | parsed.fields empty / malformed / fallback_offered=True → catalog returns AutofillResponse(suggestions={}, applied={}, fallback_offered=True) HTTP 200 — symmetric with §9 smart_picker |
| Layer 2 enum guardrail integration | reference | catalog._resolve_allowed_enums builds the dict — static reads inline enum_values; category fetches via category.service.get_field_enum; passed to call_gemini.allowed_enums kwarg |

## §11 watermark.v1 — CONSUMED 2026-06-07 (sub-session: meesell-backend-construction-11-image-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| watermark.v1 template inputs (consumed by §11) | reference | image.tasks._check_watermark passes prompt_vars={} (no template variables) and image_bytes=<bytes from GCS download>; rendered_by="vision"; Layer 1 prefix enforced by guardrail.apply_prompt_constraint per §6A.E |
| watermark.v1 expected output contract | reference | {"has_watermark": bool, "confidence": float ∈ [0,1]} — Layer 2 guardrail validates shape per §6A.E; fallback on malformed → outcome "uncertain" + confidence None |
| watermark fallback envelope | reference | call_gemini internally returns parsed = {"has_watermark": None, "confidence": 0.0, "watermark_check": "skipped_budget"} on BudgetExceededError per §6A.F; tasks._check_watermark detects via parsed.get("watermark_check") == "skipped_budget" |
| watermark output → PrecheckResult mapping | reference | _check_watermark returns (outcome, confidence): outcome ∈ {"no_watermark", "has_watermark", "uncertain", "skipped_budget"}; PrecheckResult.watermark_check carries it verbatim; PrecheckResult.watermark_confidence carries the float or None |
| watermark is INFORMATIONAL (founder ruling) | reference | overall image status="ready" if 4 deterministic checks pass — watermark outcome does NOT gate status; budget exhaustion is non-blocking; sellers not penalised |
| watermark.v1 template is V1 baseline | reference | TEMPLATE already drafted in ai_ops/prompts/watermark_v1.py (services-builder seeded during Wave 1 §6A); content covers: watermark definition (semi-transparent logo / text stamp / signature / "for sale only" marker), what it is NOT (printed brand label / sticker / texture), output JSON contract, false-positive bias rationale (Meesho rejects at listing time so flag saves a later rejection). Ready for §19 golden-eval tuning |
| watermark.v1 golden eval target | reference | 30 images, 50/50 watermarked/clean, target accuracy ≥ 85% per MVP_ARCH §8.5; fixtures live in tests/eval/watermark/fixtures.json (to be created); maintained by meesell-image-precheck-builder per §6A.H |
