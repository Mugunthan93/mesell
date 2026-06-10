"""``image`` — Image upload, 5-step pre-check pipeline, GCS orchestration module.

Owner specialists: ``meesell-api-routes-builder`` (routes + Pydantic
schemas) + ``meesell-services-builder`` (business logic, GCS
orchestration, Celery task wrapper) per BACKEND_ARCHITECTURE.md §11
(LOCKED 2026-06-05).

AI-track collaboration: ``meesell-image-precheck-builder`` owns the
5-step precheck pipeline INCLUDING the Gemini Vision watermark call
wrapped by §6A.C ``workload="watermark"``; ``meesell-prompt-engineer``
owns the watermark vision prompt content per §6A.G.

Seam (§11.A locked):
  - backend's ``image`` module owns the upload route, the GCS binary
    write, the ``product_images`` row insert with ``status='pending'``,
    the Celery enqueue, and the result write-back to ``precheck_jsonb``
    with ``status='ready'``.
  - the AI track's ``image-precheck-builder`` owns the precheck pipeline
    logic itself (JPEG, RGB, resolution, white-bg, watermark detection).

Per BACKEND_ARCHITECTURE.md §11 the module surfaces 2 endpoints:

1. ``POST  /api/v1/products/{id}/images``   — upload image (202 ACCEPTED)
2. ``GET   /api/v1/products/{id}/images``   — list product images with status

Plus Celery task ``image.precheck`` (one of only 2 modules with
``tasks.py`` per §3.C — the other is ``export``).

The public router is exposed via ``image_router`` so ``app/main.py``
can mount it with ``app.include_router(image_router)``.
"""

from app.modules.image.router import router as image_router

__all__: list[str] = ["image_router"]
