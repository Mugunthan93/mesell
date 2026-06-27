## MS Sub-Plan A Phase B — svc-export router extraction (2026-06-12)

| Memory key | type | content |
| ---------- | ---- | ------- |
| svc-export router.py import path | reference | In extracted svc-export, service import is `from app import service as export_service` (NOT `from app.modules.export import service`) — the svc-export tree root IS the module |
| svc-export schemas.py import path | reference | `from app.schemas import ExportInitiatedResponse, ExportRequest, ExportResponse` (flat `app.schemas`, not `app.modules.export.schemas`) |
| FastAPI route.status_code = None for default 200 | reference | FastAPI only sets `route.status_code` when explicitly passed to the decorator. GET routes with implicit 200 have `route.status_code = None`. Assert `(route.status_code is None or route.status_code == 200)` for default-200 routes. |
| FastAPI dependant.dependencies ARE Dependant objects | reference | In FastAPI 0.115, items in `route.dependant.dependencies` are `Dependant` objects directly (NOT wrappers with `.dependant`). They have `.call` and `.dependencies`. Recurse on the child directly. |
| route.dependencies vs route.dependant.dependencies | reference | `route.dependencies` = decorator-level `dependencies=[Depends(...)]` only. `route.dependant.dependencies` = ALL parameter-level `Depends()`. To find `get_current_user`, walk `route.dependant.dependencies` recursively. |
| E402 in main.py mid-module imports | reference | Mid-module `from app.router import ...` after app construction (middleware must register first) raises E402 — fix with `# noqa: E402`, do NOT move to top. |
| svc-export test run command | reference | `PYTHONPATH=<worktree>/backend/services/svc-export <repo>/backend/.venv/bin/pytest tests/ -v` (monolith .venv has all deps incl. fastapi 0.115) |
| svc-export isolation guard | reference | STATUS_BACKEND.md + agent MEMORY.md writes blocked by worktree isolation guard in this session. Include full content in final report for session relay. |

**MS Sub-Plan A Phase B summary (2026-06-12):** delivered `backend/services/svc-export/app/router.py` (2 routes verbatim: POST /api/v1/products/{product_id}/export-xlsx 202 + @rate_limit export_initiate 10/3600; GET /api/v1/exports/{export_id} 200 no rate_limit) + authoritative `schemas.py` (wire shapes byte-equivalent) + `openapi.json` (2 endpoints, 3 business schemas) + `tests/test_export_routes.py` (7 non-tautological mounted-route tests). Zero /internal/* (leaf consumer). 26/26 svc-export tests PASS, ruff clean. Commit `a3a8e71`.

---
