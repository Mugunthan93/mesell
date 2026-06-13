"""svc-pricing — standalone Feature 7 Price Calculator microservice (MS Sub-Plan D).

Extracted from the monolith ``app.modules.pricing`` (BACKEND_ARCHITECTURE.md
§12 LOCKED 2026-06-05) per the validated MS extraction recipe.  The business
logic (``service.py`` / ``repository.py`` / ``domain.py`` / ``exceptions.py``)
is vendored byte-for-byte under the §16.G discipline; the only changes vs the
monolith are the 2 import-line rewires (catalog/category → HTTP shims) and the
§0.6 ProductORM elimination.

A leaf-with-2-calls service on the cross-module graph (§2.D matrix:
``pricing → catalog`` for ownership + category_id, ``pricing → category`` for
commission; both ✓).  Owns the ``pricing_calcs`` table exclusively, bound to
the ``pricing`` Postgres schema (moved ``public`` → ``pricing`` in MS-D Phase A;
append-only audit trail per §12.B.1 step 8 + D4).

NO AI track collaboration — pricing is deterministic math per §6A + §12.H (no
``ai_ops``/Gemini call, no vendor adapter — spec §0.3).  NO Celery (§0.2 /
§0.8).

The package root re-exports nothing at import time — ``main.py`` mounts the
router import-tolerantly so the app boots before ``router.py`` (delivered by
meesell-api-routes-builder, Phase B) lands.
"""
