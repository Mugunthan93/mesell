---
name: meesell-gemini-prompt-budget
description: >-
  MeeSell's conventions for authoring Gemini 2.5 Flash prompts, JSON-mode contracts, and
  staying under the per-call cost ceiling. Use this skill WHENEVER you are writing or
  editing an AI prompt, prompt template, few-shot bank, output parser, or eval fixture for
  the MeeSell AI pipeline (category suggest, catalog autofill, watermark/image vision) —
  even if the user only says "improve the AI", "make the category picker better", "the
  autofill is wrong", or names an AI feature without saying "prompt" or "Gemini". Apply it
  for any Gemini call site, JSON output shape, token-budget, or cost concern. Do NOT use it
  for non-AI backend logic (defer to the fastapi-router / services conventions).
---

# MeeSell Gemini Prompt & Cost Conventions

These are the locked conventions for every Gemini call in MeeSell. They exist so AI output
is parseable, deterministic enough to test, and cheap enough that a ₹499/month seller is
still profitable. They derive from `CLAUDE.md` Key Decision #3 (Gemini 2.5 Flash, not
GPT-4) and the cost discipline recorded in project memory, which win.

## The non-negotiables (and why each matters)

- **Gemini 2.5 Flash, never a bigger model.** Flash is ~10x cheaper and sufficient for
  catalog text. Reaching for a Pro-tier model for routine generation blows the unit
  economics. If a task seems to "need" a bigger model, first try better prompting and a
  tighter context.

- **Cost ceiling: ≤ ₹0.05 per call for routine generation.** Catalog text, autofill, and
  category suggestion must each stay under this. The dominant cost driver is usually the
  *input* context (e.g. dumping the whole category tree), not the output — compress the
  context before reaching for a cheaper model. The smart-picker cost overage in memory was
  tree-dominated, not description-dominated.

- **JSON mode with an explicit schema contract.** Every structured call requests JSON and
  validates the response against a known shape before use. A free-text response that the
  code then regex-scrapes is fragile and silently breaks when Gemini rephrases.

- **A parser that fails loudly.** If the JSON doesn't match the contract, raise/return a
  typed error and fall back (e.g. ILIKE search for category suggest) — never feed
  half-parsed AI output downstream as if it were valid.

- **Few-shot examples earn their tokens.** Include only the examples that change behaviour.
  Each example is input context you pay for on every call — prune ruthlessly and measure.

- **Every prompt has an eval fixture.** A golden set of input→expected-output pairs lives
  alongside the prompt so a prompt edit can be measured for regression (recall for category
  suggest, field accuracy for autofill) before it ships to staging.

## Prompt template shape

```python
# Keep the system instruction stable and the variable context minimal.
SYSTEM = (
    "You are a Meesho catalog assistant. Return ONLY valid JSON matching the schema. "
    "Be concise. Do not invent attributes that are not supported by the input."
)

# Compress context: send the top-K relevant category leaves, not the whole 3,772-row tree.
USER_TEMPLATE = """Product description:
{description}

Candidate categories (id: name):
{candidate_block}

Return JSON: {{"top_3": [{{"category_id": "...", "confidence": 0.0}}]}}
"""
```

The compression step (pre-filter to candidate leaves via embedding/keyword) is what keeps
the call under the cost ceiling — do it before the Gemini call, not inside the prompt.

## Output contract + parsing

```python
import json
from pydantic import BaseModel, ValidationError

class CategorySuggestion(BaseModel):
    category_id: str
    confidence: float

class CategorySuggestResponse(BaseModel):
    top_3: list[CategorySuggestion]

def parse_suggest(raw: str) -> CategorySuggestResponse | None:
    try:
        return CategorySuggestResponse.model_validate_json(raw)
    except (json.JSONDecodeError, ValidationError):
        logger.warning("gemini suggest returned unparseable JSON; falling back to ILIKE")
        return None  # caller falls back to keyword search
```

## Cost discipline workflow

1. Estimate input + output tokens for a representative call.
2. Multiply by the Flash rate; convert to ₹. If > ₹0.05, the fix is almost always
   **shrink the input context** (fewer candidates, shorter few-shots), not a different model.
3. Tighten knobs like a max-candidate cap (e.g. the `_MAX_LEAVES_PER_SUPER` lever) only
   while watching the golden-eval recall — never trade recall blindly for cost.
4. Record the per-call cost in the cost meter so regressions are visible.

## Quick checklist before you finish a prompt task

- [ ] Targets Gemini 2.5 Flash (not a Pro-tier model)
- [ ] Estimated per-call cost ≤ ₹0.05; input context compressed
- [ ] JSON mode with an explicit schema contract
- [ ] Parser validates and fails loudly with a defined fallback
- [ ] Few-shot examples pruned to only those that change behaviour
- [ ] A golden eval fixture exists and was checked for regression
- [ ] Per-call cost recorded in the cost meter
