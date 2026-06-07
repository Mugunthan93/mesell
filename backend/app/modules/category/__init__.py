"""``category`` domain module — BACKEND_ARCHITECTURE.md §9.

Surfaces 5 read-only endpoints (Smart Picker, Browse, Tree, Schema,
Field-Enum).  This package currently contains the AI-track contribution
only: :mod:`.picker` — pure-Python helpers (tree compression, confidence
calibration, top-K selection) consumed by the services-builder's
``service.suggest_categories`` per §9.B.1 / §9.C.

Per the §9.A AI seam, the prompt content lives in
:mod:`app.ai_ops.prompts.smart_picker_v1` (owned by
``meesell-prompt-engineer``); the Gemini call shape lives in
:mod:`app.ai_ops.client` (owned by ``meesell-ai-coordinator``).  This
sub-package owns only the pure deterministic helpers — no I/O, no
adapter coupling.

The public router is exposed via ``category_router`` so ``app/main.py``
can mount it with ``app.include_router(category_router)``.
"""

from app.modules.category.router import router as category_router

__all__: list[str] = ["category_router"]
