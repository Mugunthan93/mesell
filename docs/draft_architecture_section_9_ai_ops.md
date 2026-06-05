> **STATUS: INTEGRATED** into docs/MVP_ARCHITECTURE.md (2026-06-04 evening). This file is archival only. See the canonical version in MVP_ARCHITECTURE.md.

# Section 9 — AI Model Operations (Gemini 2.5 Flash)

**Status:** Draft (awaiting cost validation and final eval framework)

MeeSell uses **Google Gemini 2.5 Flash** (locked decision per CLAUDE.md item 3) for three core AI workloads: Smart Category Picker (text→JSON), AI Auto-fill (text+schema→JSON), and Image Watermark Detection (vision→JSON). This section specifies operational constraints, cost ceilings, fallback behavior, and monitoring for V1 launch.

---

## 9.1 Three Workloads and Rate Limits

### Smart Category Picker
- **Input:** seller's natural-language product description (e.g., "Blue cotton saree with mirror work")
- **Output:** JSON `{"top_n": [{"leaf_id": "10003", "confidence": 0.93}, ...]}` (TOP-5 leaves)
- **Gemini API usage:** 1 call per picker request; ~8K input tokens (compressed 3-level category tree) + ~200 output tokens
- **Rate limit ceiling per seller per hour:** 100 calls/hour (soft cap; alarm if exceeded)
- **Rate limit ceiling global per day:** 500 calls/day for V1 launch

### AI Auto-fill
- **Input:** product description + schema (compulsory fields + allowed enum values); ~3K input tokens
- **Output:** JSON `{"field_1": {"value": "...", "confidence": 0.91}, ...}` + validation pass/fail per field
- **Gemini API usage:** 1 call per product; ~3K input tokens (per-category schema) + ~1K output tokens (JSON mode)
- **Rate limit ceiling per seller per hour:** 50 calls/hour (soft cap; alarm if exceeded)
- **Rate limit ceiling global per day:** 200 calls/day for V1 launch

### Image Watermark Detection
- **Input:** single JPEG image (already validated for resolution + RGB)
- **Output:** JSON `{"has_watermark": boolean, "confidence": 0.87, "explanation": "..."}`
- **Gemini API usage:** 1 vision call per image; ~10K token equivalent (image embedding + analysis)
- **Rate limit ceiling per seller per hour:** 30 images/hour (soft cap; alarm if exceeded)
- **Rate limit ceiling global per day:** 100 images/day for V1 launch

**Gemini 2.5 Flash published limits (verify before launch):** 2,000 RPM per project, 400,000 TPM. MeeSell's per-hour ceilings ensure we stay well below these.

---

## 9.2 Token Budget and Estimated Cost Per Call

### Smart Category Picker
| Component | Tokens | Notes |
|-----------|--------|-------|
| Compressed category tree (3 levels) | 8,000 | Precomputed once per day, reused |
| Seller's description | 150–300 | Variable; safety budget 500 |
| JSON schema contract | 100 | Fixed prompt instruction |
| **Input total** | ~8,500 | |
| **Output (top-5 + confidence)** | ~200–300 | JSON mode; predictable |
| **Cost per call** | ₹0.02–0.03 | At ~₹0.05 per 1K input + ₹0.20 per 1K output |

### AI Auto-fill
| Component | Tokens | Notes |
|-----------|--------|-------|
| Product description | 200–400 | Seller provided |
| Category schema (compulsory fields only) | 2,500–3,000 | Per-category enum-constrained list |
| Prompt instructs enum enforcement | 150 | Fixed |
| **Input total** | ~3,000–3,500 | |
| **Output (field suggestions JSON)** | 800–1,200 | JSON mode; parser validates |
| **Cost per call** | ₹0.02–0.04 | |

### Image Watermark Detection
| Component | Tokens | Notes |
|-----------|--------|-------|
| Image (base64 embedded in request) | ~10,000 equiv. | Gemini counts images as fixed cost (~4K tokens per image) |
| Prompt instructions | 100 | Fixed |
| **Input total** | ~10,100 equiv. | |
| **Output (JSON)** | 100–300 | Text analysis of image; JSON mode |
| **Cost per call** | ₹0.01–0.02 | Vision pricing differs from text; verify against Gemini rate card |

**Cost ceiling per call (all three workloads combined):** target ≤₹0.05 average. Current estimates are **within budget**.

---

## 9.3 Fallback Strategy on Outage

### Smart Category Picker
- **On timeout or error:** return HTTP 200 with `fallback: true` and empty `top_n` array
- **Frontend behavior:** display manual browse UI (per §3.3 MVP_ARCHITECTURE.md — seller can search/filter the full category tree)
- **Seller impact:** ~3 extra taps to find category manually; no blocker to catalog creation

### AI Auto-fill
- **On timeout or error:** return HTTP 200 with `skipped: true` and empty suggestions object
- **Frontend behavior:** show toast banner "AI is temporarily busy. Please fill these fields manually."
- **Seller impact:** seller must type values directly; form validation still enforces enum constraints

### Image Watermark Detection
- **On timeout or error:** return `{"watermark_check": "skipped", "skipped_reason": "service_error"}`
- **Frontend behavior:** show info banner "Watermark check skipped. Please verify your image has no visible branding or watermarks."
- **Seller impact:** image uploads succeed but marked as "pending_manual_review"; compliance officer flags at export time if needed

**Timeout threshold:** 10 seconds per call (Celery task timeout). If exceeded, graceful degradation, not error.

---

## 9.4 Prompt Versioning and A/B Testing

Prompt templates live in `/backend/app/ai/prompts/`:

```
backend/app/ai/prompts/
├── category_picker_v1.py         # Current production (high-precision, top-5)
├── category_picker_v2.py         # Experimental (faster, top-3)
├── autofill_v1.py                # Current production (enum-constrained, confidence > 0.80)
├── autofill_v1_5.py              # Experimental (adds user-intent inference)
└── watermark_vision_v1.py        # Current production (binary + explanation)
```

Active version configured in `backend/app/config.py`:

```python
class AIConfig(BaseSettings):
    CATEGORY_PICKER_VERSION: str = "v1"  # env var, can switch without restart
    AUTOFILL_VERSION: str = "v1"
    WATERMARK_VERSION: str = "v1"
```

**A/B testing in V1.5:** introduce a `user.ai_experiment_group` field; dispatch ~10% of calls to v2 variants, track accuracy + latency separately.

---

## 9.5 Eval Framework and Golden Test Sets

### Category Picker Golden Set
- **File:** `evals/category_picker_golden.yaml`
- **Size:** 50 natural-language descriptions (diverse: apparel, food, electronics, beauty)
- **Ground truth:** hand-annotated top-3 correct leaf IDs (seller or coordinator manually categorizes each example)
- **Pass criteria:** ≥80% recall@5 (the model's top-5 must include the correct leaf for ≥40 of 50 examples)
- **Automation:** CI runs this before every Gemini API version upgrade

### Auto-fill Golden Set
- **File:** `evals/autofill_golden.yaml`
- **Size:** 30 product specs (5 per super-category: Apparel, Grocery, Electronics, Beauty, Home & Kitchen)
- **Ground truth:** hand-filled product data for each spec (e.g., "Blue cotton saree" → brand="...", fabric="Cotton", weight_grams="200")
- **Pass criteria:** (1) **0% invalid enum values** — no suggestion outside the allowed enum for that category; (2) **≥70% field accuracy** — suggestion exactly matches ground truth or is synonymous (e.g., "Silk" vs "Mulberry Silk" both correct for fabric)
- **Automation:** CI fails if any invalid enum leaked through; tracking scores per super-category

### Image Watermark Golden Set
- **File:** `evals/watermark_golden/` (30 sample JPEGs)
- **Composition:** 15 images with visible watermarks (brand logo, URL stamp, copyright mark), 15 without
- **Ground truth:** binary label per image (has_watermark: true/false)
- **Pass criteria:** ≥85% accuracy (28 of 30 correct classifications)
- **Automation:** nightly run against Gemini, alert if accuracy drops below threshold

**Eval runner:** `/scripts/run_ai_evals.py` (Bash + Python). Output: JSON report with per-workload metrics, printed to stdout and appended to `.evals/eval_log.jsonl` for trending.

---

## 9.6 Tracing and Observability via LangFuse

Every AI call is traced using **LangFuse SDK** (Python `langfuse` library, async decorator pattern).

### Tracing instrumentation

```python
from langfuse.decorators import observe

@observe(name="category_picker")
async def suggest_categories(description: str) -> dict:
    """Calls Gemini category picker, traces input/output/cost."""
    # LangFuse automatically captures:
    # - input: {"description": "..."}
    # - output: {"top_n": [...]}
    # - tokens_in, tokens_out (from Gemini response)
    # - latency_ms
    # - cost_usd (computed from token counts)
    result = await gemini_client.suggest_categories(description)
    return result
```

### LangFuse dashboard metrics

- **Per-call trace:** input, output, tokens, latency, cost, error (if any)
- **Cost attribution:** tag with `user_id` + `workload` so costs are rolled up per seller
- **Golden test eval result:** if trace matches golden test ID, append `eval_passed: true/false`
- **Latency distribution:** P50 / P95 / P99 per workload
- **Error rate:** % of calls returning error or timeout

### Alerts

- **Cost threshold:** alert when any user's daily AI cost > ₹2
- **Error rate:** alert if error rate > 5% in 1-hour window
- **Latency regression:** alert if P95 latency > 8 seconds (baseline)

---

## 9.7 Hallucination Guardrails (M7 Enforcement)

**MANDATE M7** (Core Philosophy) states: "AI works in canonical space. Validation checks against the Meesho enum codes. **AI never produces values that wouldn't survive export.**"

Three-layer enforcement:

### Layer 1: Prompt-level constraint
Gemini's prompt instruction explicitly forbids free-text enum suggestions:

```
"For each enum field below, you MUST choose ONLY from the allowed_values list. 
Never invent or suggest values outside this list. 
If no good match exists, return null."

Example:
  FIELD: Fabric
  ALLOWED: ["Cotton", "Silk", "Polyester", "Wool", "Linen"]
  SELLER INPUT: "cotton-silk blend"
  YOUR SUGGESTION: "Silk" (closest match in list) OR null (too ambiguous)
  NEVER: "Cotton-Silk blend" (not in list)
```

### Layer 2: Parser-level rejection
The `autofill_parser.py` validates every suggestion before storage:

```python
def validate_autofill_suggestion(field: FieldSchema, suggestion: str) -> bool:
    """Reject suggestions outside the field's enum."""
    if field.data_type != "dropdown":
        return True  # non-enum fields always valid
    
    if suggestion not in field.allowed_values:
        logger.warning(f"Invalid enum: {field.name}={suggestion}")
        return False  # drop this suggestion
    
    return True
```

Invalid suggestions are dropped silently (not stored in `ai_suggestions_jsonb`).

### Layer 3: Backend re-validation at export time
When exporting (Export Adapter), the system re-validates every enum value before writing to XLSX:

```python
def validate_for_export(row: dict, schema: TemplateSchema) -> None:
    """Final check: no invalid enums make it to Meesho."""
    for field in schema.fields:
        if field.data_type == "dropdown":
            value = row.get(field.canonical_name)
            if value and value not in field.allowed_values:
                raise EnumNotFoundError(
                    f"{field.name}: {value} is not in Meesho's allowed list"
                )
```

**Result:** even if Layers 1 and 2 fail, Layer 3 catches the error before XLSX generation, preventing invalid exports.

---

## 9.8 Cost Monitoring and Budget Alarms

### Daily cost dashboard
Backend exposes `/api/v1/admin/costs?date=2026-06-04` (coordinator-only):

```json
{
  "date": "2026-06-04",
  "global_total_usd": 0.83,
  "global_total_inr": 69,
  "by_workload": {
    "category_picker": {"calls": 340, "cost_usd": 0.34},
    "autofill": {"calls": 210, "cost_usd": 0.42},
    "watermark": {"calls": 95, "cost_usd": 0.07}
  },
  "by_seller_top_10": [
    {"seller_id": "seller_123", "cost_usd": 0.12},
    ...
  ]
}
```

Data sourced from Valkey `cost:{date}` hash updated in real-time by each AI call.

### Cost alarm triggers

1. **Per-seller per-day cap:** ₹2
   - When seller's daily cost > ₹2, backend returns HTTP 429 for subsequent AI calls
   - Seller sees: "You've reached your daily AI quota. Try again tomorrow."

2. **Global daily cap:** ₹500
   - Hard stop: when global cost > ₹500, ALL non-admin users get 429
   - Admin/coordinator can force-allow for urgent cases
   - Alert email sent immediately to founder + operations

3. **Error rate alarm:** >5% error rate in 1-hour window
   - Indicates possible Gemini outage or quota exhaustion
   - Alert to ops Slack channel; on-call engineer investigates

4. **Latency alarm:** P95 latency > 10 seconds
   - Possible regional Gemini service degradation
   - Alert to ops; no auto-mitigation (fallback is soft, not hard)

---

## 9.9 Observability Checklist

- [ ] LangFuse SDK initialized in `backend/app/config.py` (project key injected)
- [ ] All three workloads wrapped with `@observe` decorator
- [ ] Cost tracking per user stored in Valkey `cost:{user_id}:{date}` (updated per call)
- [ ] Daily cost roll-up cron job at 00:00 UTC → `/admin/costs` endpoint
- [ ] Golden test eval runner CI integration (runs before merge, passes/fails PR)
- [ ] Alert configuration in monitoring tool (Prometheus / CloudWatch / custom)
- [ ] Prompt versioning config in `backend/app/config.py` (switch via env var)

---

## 9.10 V1 Operational Readiness

Before launch, confirm:

1. **Rate limit ceiling testing:** load-test picker with 100 calls/min, autofill with 50 calls/min, ensure no 429 from Gemini (we stay within 2K RPM)
2. **Cost math signed off:** founder confirms ₹2/seller/day + ₹500/day global caps are acceptable burn
3. **Fallback UX tested:** picker fallback to manual browse, autofill fallback to manual fill, watermark fallback to skip — all three flows tested end-to-end
4. **Golden evals baselined:** all three golden sets run, baseline accuracy recorded (picker ≥80%, autofill 0% invalid, watermark ≥85%)
5. **LangFuse dashboard live:** cost + latency + error rate visible in real-time
6. **On-call runbook written:** if Gemini goes down or costs spike, what does the duty engineer do?

**Estimated readiness sprint:** 3–4 days (post-backend-foundation).

---

**Total AI operational cost for V1:** ~₹0.50–0.70/product created (picker + autofill + ~2 images watermark-checked). At ₹500/day cap ≈ 700–1,000 products/day can use AI fully. Sustainable for Phase 1 (100–200 active sellers expected at launch).
