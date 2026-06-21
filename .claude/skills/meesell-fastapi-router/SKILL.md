---
name: meesell-fastapi-router
description: >-
  MeeSell's canonical conventions for writing FastAPI route handlers, routers,
  and their Pydantic schemas. Use this skill WHENEVER you are creating or editing
  any FastAPI endpoint, APIRouter, route handler, request/response schema, or
  pagination/error/auth wiring in the MeeSell backend (backend/app/routers/,
  backend/app/schemas/) — even if the user only says "add an endpoint", "build a
  route", "wire up an API", or names a feature without saying the word "router".
  Apply it for anything touching /api/v1/ surface, JWT-protected routes, file
  uploads, or background-job-returning endpoints. Do NOT use it for pure service-layer
  logic (defer to the services builder) or DB models (defer to the database builder).
---

# MeeSell FastAPI Router Conventions

These are the locked, non-negotiable conventions for every FastAPI endpoint in the
MeeSell backend. They exist so that all 16+ V1 endpoints behave identically from the
client's perspective, so the OpenAPI surface stays consistent, and so tenant/auth
safety is never accidentally dropped. Follow them by default — they are derived from
`CLAUDE.md` "Key Decisions" and "Coding Conventions", which win over any other guidance.

## The non-negotiables (and why each matters)

- **Async everything.** Every route handler is `async def`. FastAPI runs sync handlers
  in a threadpool, which silently serialises our DB-bound work and breaks the async
  SQLAlchemy session contract. There is no such thing as a sync handler in this codebase.

- **`AsyncSession` only.** Inject the session and use `await` on every query. A
  synchronous query against the async engine raises at runtime and corrupts the
  connection pool. Never reach for the sync `Session`.

- **Pydantic v2 schemas for every request and response.** Request bodies are typed
  Pydantic models; responses declare `response_model=...`. This is what generates the
  OpenAPI contract the Angular typed API client depends on — an untyped `dict` response
  breaks frontend codegen and hides breaking changes.

- **`/api/v1/` prefix on every router.** Set it once on the `APIRouter(prefix=...)`.
  Versioning lives in the path so we can ship v2 without breaking live sellers.

- **Raise `HTTPException`, never return raw error strings.** Errors must surface as a
  proper status code plus the standard body `{"detail": "human-readable message"}`.
  Returning a string with a 200 makes failures invisible to the client and to monitoring.

- **JWT Bearer auth via dependency.** Protected routes take
  `user: User = Depends(get_current_user)`. Never parse the Authorization header by hand —
  the dependency centralises validation, revocation checks, and the plan-guard seam.

- **Structured logging only.** `logger = logging.getLogger(__name__)` at module top;
  never `print()`. Logs are aggregated and masked centrally; a `print` bypasses that and
  can leak PII.

- **snake_case** for functions and variables, **PascalCase** for schema classes.

## Standard router skeleton

Use this shape as the starting point for any new router. Adjust the entity, not the structure.

```python
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.catalog import CatalogCreate, CatalogResponse
from app.services.catalog_service import CatalogService
from app.middleware.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/catalogs", tags=["catalogs"])

@router.post("/", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog(
    data: CatalogCreate,
    user: User = Depends(get_current_user),
    service: CatalogService = Depends(),
) -> CatalogResponse:
    return await service.create(user_id=user.id, data=data)
```

Keep business logic in the service layer — the route handler validates input, calls the
service, and shapes the response. A handler that runs queries directly is a smell; push
that down to a service so it stays testable and tenant-safe.

## Pagination

List endpoints accept `?page=1&limit=20` and return the standard envelope. Keep the keys
exactly `data`, `total`, `page` so the frontend can use one generic paginator everywhere.

```python
@router.get("/", response_model=CatalogListResponse)
async def list_catalogs(
    page: int = 1,
    limit: int = 20,
    user: User = Depends(get_current_user),
    service: CatalogService = Depends(),
) -> CatalogListResponse:
    items, total = await service.list(user_id=user.id, page=page, limit=limit)
    return CatalogListResponse(data=items, total=total, page=page)
```

## Errors

Every failure path raises `HTTPException` with the right status. The body is always
`{"detail": "..."}` with a message a seller could understand. Examples:

```python
if catalog is None:
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Catalog not found")
if catalog.user_id != user.id:
    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your catalog")
```

Never return `{"error": ...}` or a bare string — `detail` is the one error shape the
frontend interceptor knows how to surface via the snackbar.

## File uploads

Image/file uploads are `multipart/form-data`, capped at 10 MB per file. Validate the size
and content type in the handler and reject oversized or wrong-type uploads with a 413 / 415
before they reach storage.

```python
from fastapi import UploadFile, File

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

@router.post("/{catalog_id}/images", status_code=status.HTTP_202_ACCEPTED)
async def upload_image(
    catalog_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: ImageService = Depends(),
) -> dict:
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds 10 MB")
    job = await service.enqueue_precheck(user_id=user.id, catalog_id=catalog_id, contents=contents)
    return {"job_id": str(job.id), "status": "processing"}
```

## Background jobs

Any endpoint that kicks off async work (image precheck, AI generation, export) returns
immediately with `{"job_id": "...", "status": "processing"}` and a `202 Accepted`. The
client polls a `GET` status endpoint. Never block the request on Celery work — sellers on
slow mobile connections will time out.

## Quick checklist before you finish a route

- [ ] `async def` handler
- [ ] `response_model=` set (or an explicit documented shape)
- [ ] `Depends(get_current_user)` on anything non-public
- [ ] Router has `/api/v1/...` prefix and a `tags=[...]`
- [ ] Errors raise `HTTPException` with `{"detail": ...}`
- [ ] List route uses `page`/`limit` and the `{data,total,page}` envelope
- [ ] Uploads enforce the 10 MB cap
- [ ] Long work returns `{job_id, status}` + 202, never blocks
- [ ] `logging.getLogger(__name__)`, no `print()`
- [ ] No raw SQL / direct queries in the handler — call a service
