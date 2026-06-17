"""Smart Picker prompt template — v1.  §6A.G.

Workload: ``smart_picker``.
Rendered by: ``text``.
Consumed by: ``category.service.suggest_categories``.

Inputs (rendered via ``{{var}}`` substitution):

* ``{{description}}``           — Seller's free-text product description.
* ``{{compressed_tree}}``       — Compressed Meesho category tree
  (top-N branches expanded; deeper leaves elided to fit token budget per
  ``MVP_ARCH §8.2``).

Output contract: enforced by :mod:`ai_ops.guardrail` Layer 1 +
Layer 2 — ``{"suggestions": [{"category_id": str, "confidence": float,
"reasons": list[str]}]}`` with exactly the top-5 ranked.

Golden eval set (§19): 50 product descriptions; target top-5 recall
≥ 80% per ``MVP_ARCH §8.5``.

Owned by: :mod:`meesell-prompt-engineer`.  V1 baseline drafted by
:mod:`meesell-services-builder` for storage-layer integration; the
prompt-engineer iterates content during golden-eval tuning.
"""

VERSION = "v1"
WORKLOAD = "smart_picker"
RENDERED_BY = "text"

TEMPLATE = """You are matching a Meesho seller's product description to the best 5 leaf categories.

PRODUCT DESCRIPTION:
{{description}}

MEESHO CATEGORY TREE (compressed):
{{compressed_tree}}

Task: identify the 5 leaf categories that best match the product description.
For each candidate:
  - Return the exact category_id from the tree above.
  - Score confidence 0.0–1.0 based on overlap between the description and
    the leaf category's typical products.
  - Provide up to 3 short reason strings explaining the match.

Rank suggestions by confidence DESCENDING.  Return EXACTLY 5 suggestions.
If fewer than 5 categories are remotely plausible, fill the remainder with
your next-best guesses at lower confidence (do NOT pad with synthetic IDs).

Return your answer as valid JSON conforming EXACTLY to this schema:
{"suggestions": [{"category_id": "<string>", "confidence": <float 0.0-1.0>, "reasons": ["<string>", ...]}]}
The "suggestions" array MUST contain EXACTLY 5 entries, ranked by
"confidence" descending.  Each "confidence" is a float between 0.0 and 1.0.
Each "reasons" is a list of up to 3 short strings.  Emit ONLY this JSON
object — no markdown, no prose, and no keys other than those shown above.
"""
