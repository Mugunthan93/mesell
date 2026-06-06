"""Prompt template storage — §6A.G.

Per :mod:`ai_ops.prompt_registry`, every prompt module exposes:

* ``TEMPLATE: str``     — Jinja2-style ``{{var}}`` body.
* ``VERSION: str``      — ``"v1"``, ``"v2"``, ...
* ``WORKLOAD: str``     — one of ``"smart_picker"`` / ``"autofill"`` /
  ``"watermark"``.
* ``RENDERED_BY: str``  — ``"text"`` or ``"vision"``.

Content ownership: :mod:`meesell-prompt-engineer` per §6A.G + the §2.3/§2.4/§2.5
AI-track collaboration notes.  The V1 baselines authored here are
considered drafts; the prompt-engineer refines them as the 3 golden
eval sets land in §19 (see :mod:`ai_ops.eval`).

V1.5 A/B routing is locked in §6A.G but DEFERRED in V1 — the active
version is hardcoded to ``v1`` for each workload.
"""
