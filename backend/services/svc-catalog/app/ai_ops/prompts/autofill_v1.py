"""Autofill prompt template — v1.  §6A.G.

Workload: ``autofill``.
Rendered by: ``text``.
Consumed by: ``catalog.service.autofill_product``.

Inputs (rendered via ``{{var}}`` substitution):

* ``{{product_spec}}``  — Seller's product description + any already-filled
  fields (rendered as a key: value list).
* ``{{schema}}``        — The per-category schema envelope (§5A.B)
  rendered as a JSON block.  The Layer 1 prefix injected by
  :mod:`ai_ops.guardrail` ALSO emits a human-readable allowed-enum
  block above this template, so the constraint signal is double-strong.

Output contract: enforced by :mod:`ai_ops.guardrail` Layer 1 +
Layer 2 — ``{"fields": {<canonical_name>: <value>}}``.  For
enum-constrained fields, value MUST be in the per-field allowlist
(Layer 2 ENFORCES; retry on violation).  For free-text fields, value
is a scalar string.

Golden eval set (§19): 30 product specs; target 0% invalid enum
values per ``MVP_ARCH §8.5``.

Owned by: :mod:`meesell-prompt-engineer`.  V1 baseline drafted by
:mod:`meesell-services-builder` for storage-layer integration; the
prompt-engineer iterates content during golden-eval tuning.
"""

VERSION = "v1"
WORKLOAD = "autofill"
RENDERED_BY = "text"

TEMPLATE = """You are filling in a Meesho seller's product attributes from a partial spec.

PRODUCT SPEC (free text + already-filled fields):
{{product_spec}}

CATEGORY SCHEMA (canonical field definitions):
{{schema}}

Task: emit one JSON object whose "fields" property maps each canonical
field name to your best value.  Constraints:
  - If the field has an allowed-enum list (see "Allowed enums per field"
    above), your value MUST be EXACTLY one of those strings — never invent
    a new value, never paraphrase, never translate.  Case-sensitive match.
  - If the field has NO allowed-enum list, emit a concise free-text string
    representing your best estimate.
  - If you cannot confidently determine a field's value, OMIT it entirely
    (do not emit null or empty string).  The seller will fill manually.
  - DO NOT include fields that are not present in the schema above.

Return your answer as valid JSON conforming EXACTLY to this schema:
{"fields": {"<canonical_field_name>": "<value>", ...}}
Emit ONLY this JSON object — no markdown, no prose, and no keys other
than "fields".  Every enum-constrained value MUST be a verbatim member
of that field's allowed-enum list.
"""
