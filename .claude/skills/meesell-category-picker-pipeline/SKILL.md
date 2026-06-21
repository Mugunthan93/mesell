---
name: meesell-category-picker-pipeline
description: >-
  MeeSell's conventions for the Smart Category Picker — the description→top-3-leaf pipeline
  over the 3,772-node Meesho category tree. Use this skill WHENEVER you are creating or editing
  the category suggestion pipeline: tree compression, the embedding/keyword pre-filter, the
  top-3 ranker, confidence calibration, the ILIKE fallback, or the golden test fixture — even
  if the user only says "the category picker is wrong", "improve category matching", "it
  suggests bad categories", or "make smart-picker cheaper". Do NOT use it for the raw Gemini
  prompt text/cost rules in general (defer to meesell-gemini-prompt-budget) or the XLSX tree
  source itself (defer to meesell-xlsx-category-parser).
---

# MeeSell Smart Category Picker Conventions

These are the locked rules for turning a seller's free-text product description into the top-3
Meesho leaf categories. They exist so suggestions are accurate, cheap, and never block catalog
creation. They derive from `CLAUDE.md` Feature 2, the cost ceiling, and the smart-picker cost
findings in project memory, which win.

## The non-negotiables (and why each matters)

- **Pre-filter before the model — never send the whole tree.** The 3,772-leaf tree is the
  dominant cost driver. Compress it: use an embedding/keyword pre-filter to pick a small
  candidate set (top-K leaves), and only that set goes to the ranker. Sending the full tree is
  what blew the ≤₹0.05/call ceiling in the recorded findings — the fix is fewer candidates,
  not a cheaper model.

- **Top-3, with calibrated confidence.** Return exactly the top 3 leaves, each with a
  confidence score that actually means something — a 0.9 should be right ~9/10 times. The UI
  and downstream autofill rely on this calibration to decide when to auto-pick vs ask the seller.

- **Always have a deterministic fallback.** If the model returns unparseable output, times out,
  or the candidate set is empty, fall back to an ILIKE keyword search over category names so the
  seller is never stuck with zero options. The pipeline degrades, it never dead-ends.

- **A golden fixture gates every change.** A fixed set of description→expected-leaf cases lives
  with the pipeline. Measure **recall@3** on it before and after any change — a tuning tweak
  that improves cost but tanks recall is a regression, not an optimization.

- **Cost knobs are tuned against recall, never blindly.** Levers like the per-super-category
  leaf cap (`_MAX_LEAVES_PER_SUPER`) trade cost for recall. Tighten them only while watching the
  golden recall number; the recorded guidance was to tighten 50→~15-20 *gated on recall*, not to
  slash blindly.

## Pipeline shape

```
description
   │
   ▼  (1) pre-filter: embedding/keyword similarity over leaf names+synonyms
candidate_leaves  (top-K, e.g. 15-20 — the cost lever)
   │
   ▼  (2) rank: Gemini 2.5 Flash scores candidates -> top-3 + confidence (JSON contract)
top_3 [{category_id, confidence}]
   │
   ├─ parse OK ──► calibrate confidence ──► return
   └─ parse fail / empty / timeout ──► (3) ILIKE fallback over category names ──► return
```

The compression in step (1) is what keeps step (2) under the cost ceiling. Do the heavy
narrowing in cheap local code; reserve the model for ranking a short list.

## Output contract

```python
class LeafSuggestion(BaseModel):
    category_id: str
    confidence: float  # calibrated 0..1

class CategorySuggestResponse(BaseModel):
    top_3: list[LeafSuggestion]
```

Validate the model's JSON against this before use; on failure, log and fall back to ILIKE.

## Evaluating a change

1. Run the golden fixture; record **recall@3** and mean per-call ₹ cost BEFORE.
2. Make the change.
3. Re-run; compare recall@3 and cost. Ship only if recall holds (or improves) within the cost
   ceiling. If recall drops, the change is rejected regardless of the cost win.

## Quick checklist before you finish a picker change

- [ ] Tree is pre-filtered to a small candidate set; full tree never sent to the model
- [ ] Returns top-3 with calibrated confidence
- [ ] Deterministic ILIKE fallback on parse-fail / empty / timeout — never dead-ends
- [ ] JSON output validated against the contract
- [ ] Golden fixture run; recall@3 measured before/after; no recall regression
- [ ] Cost knobs (e.g. leaf cap) tuned against recall, per-call ₹ within the ceiling
