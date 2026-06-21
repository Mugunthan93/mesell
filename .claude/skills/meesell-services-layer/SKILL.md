---
name: meesell-services-layer
description: >-
  MeeSell's conventions for the business-logic service layer and Celery background workers.
  Use this skill WHENEVER you are creating or editing a service class, business-logic method,
  Celery task, or one of the engines (quality engine, pricing engine, image processor with
  rembg+PIL, CSV/ZIP export with openpyxl, GCS storage, Gemini call sites) in the MeeSell
  backend (backend/app/services/, backend/app/workers/) — even if the user only says "add
  the export logic", "build the quality scorer", "process the image", "calculate the price",
  or names a feature without saying "service". Do NOT use it for route handlers (defer to
  meesell-fastapi-router), ORM models (defer to meesell-alembic-migration), or AI prompt
  text (defer to meesell-gemini-prompt-budget).
---

# MeeSell Service Layer & Worker Conventions

These are the locked rules for the layer between API routes and the database. They exist so
business logic stays testable, tenant-safe, and off the request thread when it's slow. They
derive from `CLAUDE.md` "Coding Conventions" + the project structure, which win.

## The non-negotiables (and why each matters)

- **Services own business logic; routes stay thin.** A route validates input, calls a
  service, shapes the response. All real work — queries, engine logic, external calls —
  lives in a service so it can be unit-tested without a FastAPI client and reused by both
  routes and workers.

- **Async + `AsyncSession`, injected.** Service methods are `async def` and take the session
  via DI (`db: AsyncSession = Depends(get_db)`). Never open your own engine/session inside a
  service — that breaks pooling and transaction scope.

- **Tenant isolation is the service's job.** Every query filters by the owning `user_id`
  (and `tenant`/plan where relevant). The route passes `user.id`; the service must never
  return another seller's data. This is the single most important invariant in the layer.

- **Slow or external work goes to a Celery task, not the request.** Image processing (rembg
  is 3–5s/image), AI generation, and big exports run as Celery tasks on Valkey (broker DB 1,
  results DB 2). The route enqueues and returns `{job_id, status}`; the worker does the work.

- **Docstrings on every service method, structured logging, no `print`.** `logger =
  logging.getLogger(__name__)`. Logs are aggregated centrally and a `print` bypasses masking.

- **Engines are pure-ish and unit-tested.** The quality engine (rules), pricing engine (P&L /
  the locked Meesho settlement model), and parsers take inputs and return results without
  hidden I/O where possible — that's what makes them cheap to test against golden cases.

## Standard service skeleton

```python
import logging
from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.catalog import Catalog
from app.schemas.catalog import CatalogCreate

logger = logging.getLogger(__name__)


class CatalogService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create(self, user_id: UUID, data: CatalogCreate) -> Catalog:
        """Create a draft catalog owned by user_id."""
        catalog = Catalog(user_id=user_id, name=data.name, status="draft")
        self.db.add(catalog)
        await self.db.commit()
        await self.db.refresh(catalog)
        logger.info("catalog created: %s for user %s", catalog.id, user_id)
        return catalog
```

## Celery worker pattern

```python
from app.workers.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_image(self, image_id: str) -> dict:
    """rembg + PIL pipeline; runs off the request thread (3-5s/image on CPU)."""
    try:
        # ... rembg background removal, PIL normalisation, GCS upload ...
        return {"image_id": image_id, "status": "done"}
    except TransientError as exc:
        raise self.retry(exc=exc)  # transient failures retry; permanent ones record + stop
```

- Make tasks **idempotent** — Celery retries, so re-running must not double-charge, double-write,
  or double-upload. Key on the entity id.
- Use a **dead-letter path** for tasks that exhaust retries; never silently drop a failed job.

## Engine notes

- **Pricing engine** follows the locked Meesho settlement model: commission = 0%, shipping is
  a per-category CONSTANT, and the calculator runs OFFLINE (no live Meesho call). Don't
  reintroduce a commission term or a network dependency.
- **Image processor**: rembg on CPU (no GPU), PIL for resize/format normalisation, output to GCS.
- **Export**: openpyxl for the Meesho CSV/ZIP — Meesho has no upload API, so the CSV shape must
  match their template exactly.
- **GCS storage**: direct GCS (not S3), free-tier-aware; stream large files, don't load whole.

## Quick checklist before you finish a service or worker

- [ ] Logic is in a service, not the route; method is `async def` with injected `AsyncSession`
- [ ] Every query filtered by `user_id` (tenant isolation) — no cross-seller leakage
- [ ] Slow/external work runs as a Celery task returning `{job_id, status}`, not inline
- [ ] Celery tasks are idempotent + have a retry/dead-letter path
- [ ] Engines are unit-testable; pricing keeps the 0%-commission / constant-shipping / offline model
- [ ] Docstrings + `logging.getLogger(__name__)`; no `print`
- [ ] GCS streamed, not fully buffered; export matches the Meesho template exactly
