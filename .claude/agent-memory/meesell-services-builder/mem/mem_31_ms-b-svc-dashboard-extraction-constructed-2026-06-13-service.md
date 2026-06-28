## MS-B svc-dashboard extraction CONSTRUCTED (2026-06-13, services-builder Phase B heavy lift)

### Scope
Worktree /tmp/mesell-wt/msB-backend, branch feature/microservices-dashboard/backend. Created backend/services/svc-dashboard/ (35 source files) by mirroring the svc-export pilot, trimmed for dashboard. dashboard = LEAF CONSUMER: owns NO tables (§13.D, no Alembic), runs NO Celery worker (pure read §13.I), exposes NO /internal/* (zero inbound). 2 OUTBOUND shims only (catalog + customer). No git ops (session commits).

### §16.G diff-proof (the load-bearing acceptance) — PROVEN TWO WAYS
1. Raw `diff` of monolith modules/dashboard/service.py vs extracted: ONLY lines 36-43 (the import block) differ. Call sites :78/:84 + _compose_response byte-for-byte unchanged.
2. AST recursive-strip (recipe §2 validated method): `ast.NodeTransformer` with visit_Import/visit_ImportFrom→None (recursive — catches lazy in-body imports) + strip module docstring (first bare-string Expr) → `ast.dump` IDENTICAL. This is the mathematically-conclusive proof; re-run it in CI.
3. _compose_response purity: AST walk for `ast.Await` nodes inside the FunctionDef → ZERO; `inspect.iscoroutinefunction` → False. GOTCHA: substring 'await' in source matches the DOCSTRING ("No await") — do NOT use string-grep for purity; use AST Await-node count.

### Import-line rewrite (the ONLY change to service.py)
- `from app.modules.catalog import service as catalog_service` → `from app.core.extracted_clients import catalog_client as catalog_service`
- `from app.modules.catalog.domain import (PaginatedProductsInternal, Pagination,)` → `from app.core.extracted_clients.catalog_client import (PaginatedProductsInternal, Pagination,)`
- `from app.modules.customer import service as customer_service` → `from app.core.extracted_clients import customer_client as customer_service`
- `from app.modules.customer.domain import ProfileCompleteness` → `from app.core.extracted_clients.customer_client import ProfileCompleteness`
- `from app.modules.dashboard.schemas import (...)` → `from app.schemas import (...)`  (flat tree; schemas.py is api-routes-builder's lane)
The re-export-as-same-symbol trick (`import catalog_client as catalog_service`) is what keeps the call sites unchanged. Preserve the ORIGINAL symbol order inside multi-name imports (DashboardQuery, DashboardResponse, ProductListItem, ProfileCompletenessSummary).

### Shim signatures (frozen — SUB_PLAN_0B §"Shim 1/2")
- `catalog_client.list_products(*, user_id: UUID, pagination, db: Any = None) -> PaginatedProductsInternal` → `GET /internal/products?page=&limit=`. user_id is NOT in the URL — callee derives tenant from forwarded JWT sub (kwarg accepted for call-site parity only). db accepted+ignored. Vendors Product (11 fields, kw_only), Pagination (page/limit), PaginatedProductsInternal (items/total/page/limit). Empty inventory → items:[],total:0 at 200 (NOT 404).
- `customer_client.get_onboarding_completeness(*, user_id: UUID, db: Any = None) -> ProfileCompleteness` → `GET /internal/seller-profile/{user_id}/onboarding-completeness`. METHOD NAME = get_onboarding_completeness, NOT get_profile_completeness (plan-prose was wrong; wrong name = re-dispatch trigger). user_id IS in URL path. Vendors ProfileCompleteness (5 fields: base_complete_count, base_total_count, extension_complete_count, extension_total_count, onboarding_complete). Missing profile → zero-shape at 200 (NOT 404). NOTE: monolith doesn't expose this endpoint yet (customer extracts MS-3/E) — shim built vs FROZEN contract, mock-tested.
- _transport.py copied VERBATIM from svc-export (only contextvar names renamed svc_export_*→svc_dashboard_*): httpx.AsyncClient, Timeout(timeout=5.0, connect=2.0), _RETRYABLE_STATUSES=frozenset({503,504}), EXACTLY 1 retry on those only, JWT (Authorization Bearer) + X-Request-ID from contextvars set by RequestContextMiddleware. set_worker_context retained for parity (no worker call site).

### Trimmed Settings (REQUIRED_FIELDS = DATABASE_URL, VALKEY_URL, JWT_SECRET, AUDIT_PII_SALT, CORS_ALLOWED_ORIGINS, MONOLITH_INTERNAL_BASE_URL, APP_ENV)
- Carries FEATURE_TRACKING_DASHBOARD_ENABLED (bool, default True) — the router 404 guard reads it. NO gemini/langfuse/msg91/razorpay/GCS (verified via `Settings.model_fields` check = []). DB pool tiny: DB_POOL_SIZE=2, DB_MAX_OVERFLOW=1 (smallest of any svc — dashboard does no owned data access; pool exists only for auth existence-check + audit). shared/database.py drops make_worker_session (no Celery). shared/valkey.py keeps only get_valkey_otp (DB 0 — rate-limit + audit-coalesce). shared/models = user + audit_event only (NO dashboard model — owns no tables); audit_event bound to public.

### Middleware chain (vendored verbatim, 6-mw §4.H)
request_id → request_context (extraction-support, NOT in 6-count) → auth → tenancy → rate_limit → plan_guard (INERT — dashboard plan_guard-excluded §13.I) → audit (INERT on read-only GET — write-method gate §13.B). main.py registers deepest-first; boots to 8 user_middleware (CORS + 6-chain + request_context; ServerErrorMiddleware not counted as it's framework). 5 error handlers. /health + /metrics. Router include is import-tolerant (try/except ImportError) so main.py boots clean before api-routes-builder lands router.py.

### Verification env GOTCHA (reusable)
- macOS system python3 = 3.9 → `@dataclass(kw_only=True)` raises TypeError (kw_only is 3.10+). The catalog Product/Pagination dataclasses use kw_only. Must verify on py3.11+. No master venv in this worktree (recipe says backend/.venv but it was absent). FIX: `/opt/homebrew/bin/python3.11 -m venv /tmp/x && pip install` the trimmed deps (fastapi/sqlalchemy[asyncio]/httpx/redis/pyjwt/pydantic-settings/prometheus-client + asyncpg). asyncpg is imported EAGERLY by create_async_engine at app.shared.database module load → must be installed for main.py boot test (it's a real boot dep, not optional).
- service.py import test needs a TEMP app/schemas.py stub (api-routes-builder's deliverable). Created stub, ran test, DELETED stub + purged all __pycache__ + temp venv before finishing. Do NOT leave the stub — it's the other lane's file.
- ruff is /opt/homebrew/bin/ruff (NOT in any venv). `ruff check backend/services/svc-dashboard/` → clean.

### Hand-offs
- api-routes-builder (Phase B next): service sig FROZEN `await list_products_for_dashboard(user_id, query, db)`; author app/router.py (1 route) + app/schemas.py (4 classes). main.py wiring ready.
- lead Phase C: re-run §16.G AST proof in CI; wire-shape parity once schemas land.
- infra-builder: Dockerfile/k8s/Traefik/ConfigMap/audit-grant = infra lane (handoff_msB_infra.md), api-only 1 replica no worker.

---
