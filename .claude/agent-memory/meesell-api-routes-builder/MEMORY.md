# Memory — meesell-api-routes-builder

## Agent Identity
FastAPI route handler specialist for MeeSell. Owns the 16 V1 endpoints + Pydantic request/response schemas + OpenAPI metadata + route-level pytest tests. Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## MEMORY.md
(Index of memory files — populated as agent works)

---

## Session: 2026-06-05 — Router Purge (G2/G3/G5)

### Task summary
Executed 3-step purge: delete legacy routers/schemas/services, rewrite auth URLs, author boot integration test.

### Files deleted
Routers (9): catalogs.py, skus.py, images.py, pricing.py, exports.py, generation.py, quality.py, research.py
(auth.py kept — modified only)
Schemas (6): catalog.py, sku.py, image.py, pricing.py, quality.py, scrape.py
(auth.py kept)
Services (4): export_service.py, quality_engine.py, image_processor.py, meesho_scraper.py
(ai_engine.py, otp_service.py, pricing_engine.py, storage.py kept — no deleted model imports)
Tests (3): test_export_service.py, test_quality.py, test_smoke.py (dead code for deleted services)

### Files modified
- backend/app/main.py: removed 8 router imports + 8 include_router calls, kept auth_router only
- backend/app/routers/auth.py: /send-otp -> /otp/send, /verify-otp -> /otp/verify; added summary= on both endpoints
- backend/tests/test_auth.py: 4 URL string replacements (send-otp -> otp/send, verify-otp -> otp/verify)
- backend/tests/conftest.py: same URL replacements in auth_client fixture

### Files created
- backend/tests/test_app_boot_integration.py: 7 tests, all PASS

### Route types (important pattern)
FastAPI mounts its built-in OpenAPI routes (/openapi.json, /docs, /docs/oauth2-redirect, /redoc)
as `starlette.routing.Route` instances, NOT `fastapi.routing.APIRoute`.
Application endpoints are `fastapi.routing.APIRoute`.
Mount objects (e.g. StaticFiles) are `starlette.routing.Mount`.
When asserting route inventory in tests: use isinstance(r, (Route, APIRoute)) to include both.

### Auth URL pattern (locked)
prefix = "/api/v1/auth"
send:   @router.post("/otp/send")   -> POST /api/v1/auth/otp/send
verify: @router.post("/otp/verify") -> POST /api/v1/auth/otp/verify
me:     @router.get("/me")          -> GET  /api/v1/auth/me

### Blocker surfaced (hand-off to services-builder)
backend/app/workers/generation_tasks.py lines 18, 79:
  `from app.models.sku import SKU` (lazy imports inside function bodies)
The SKU model is deleted. Worker will fail at runtime.
Services-builder must rewrite generation_tasks.py to use new Product model.
This reference survived grep check 6 — coordinator is aware.

### Python version note
Project venv is Python 3.11 (not 3.12 as CLAUDE.md states).
Venv path: backend/.venv/bin/python
Always use PYTHONPATH=/Users/mugunthansrinivasan/Project/mesell/backend when running pytest
from outside the venv activate context.

### Total route count after purge
app.routes has 9 entries:
  - 4 starlette.routing.Route (FastAPI builtins: openapi, docs, oauth2-redirect, redoc)
  - 3 fastapi.routing.APIRoute (auth: otp/send, otp/verify, me)
  - 1 fastapi.routing.APIRoute (health)
  - 1 starlette.routing.Mount (/dev-static, dev-only StaticFiles)
= 8 routable (Route + APIRoute) + 1 Mount = 9 total app.routes

### Memory entry index
| Entry | Type | Summary |
|---|---|---|
| Router purge 2026-06-05 | project | G2/G3/G5 complete — 9 routers, 6 schemas, 4 services, 3 tests deleted |
| Route types pattern | reference | FastAPI builtins are Route not APIRoute; use isinstance(r, (Route, APIRoute)) |
| Auth URL pattern | reference | /otp/send, /otp/verify locked per §3.1 |
| Python venv path | reference | .venv/bin/python (3.11), PYTHONPATH needed for pytest |
| Worker blocker | reference | generation_tasks.py lazy-imports deleted SKU model — services-builder must fix |
