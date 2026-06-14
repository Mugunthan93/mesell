"""AI Operations Layer — §6A.

This package is the SOLE import surface domain modules use for AI work.
Domain code calls :func:`call_gemini` from this package; it never touches
``adapters/gemini`` directly.  Per §3.G + §6A.C the boundary is enforced
by §19 import-linter Contract 2.

Public surface (re-exported from this ``__init__``):

* :func:`call_gemini` + :class:`AICallContext` + :class:`AIResponse` from
  :mod:`ai_ops.client` — the unified async call entry point.
* :class:`BudgetExceededError` from :mod:`ai_ops.budget_cap` — surfaced for
  ``isinstance`` checks at the worker-thread boundary (where ``client.py``
  does NOT swallow it because watermark callers want the explicit
  "skipped_budget" mapping).
* :func:`run_eval` + :class:`EvalReport` from :mod:`ai_ops.eval` — invoked
  from ``pytest -m ai_eval`` runs and from the V1.5 nightly Celery beat.

Internal modules (NOT re-exported, NOT for domain consumption):

* :mod:`ai_ops.cost_tracker`
* :mod:`ai_ops.guardrail`
* :mod:`ai_ops.prompt_registry`
* :mod:`ai_ops.prompts.*`

The §19 import-linter Contract 2 will reject any
``from app.ai_ops.cost_tracker import ...`` from under ``app/modules/``.
"""

from __future__ import annotations

from app.ai_ops.budget_cap import BudgetExceededError
from app.ai_ops.client import AICallContext, AIResponse, call_gemini
from app.ai_ops.eval import EvalReport, FixtureResult, run_eval

__all__ = [
    "AICallContext",
    "AIResponse",
    "BudgetExceededError",
    "EvalReport",
    "FixtureResult",
    "call_gemini",
    "run_eval",
]
