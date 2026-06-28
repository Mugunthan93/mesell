## Memory index
| Entry | Type | Summary |
|---|---|---|
| Session 2026-06-05 final purge | project | 10 files deleted (3 workers + 7 tests), 1 modified (celery_app.py); backend declared construction-ready |
| pricing_engine import blocker | reference | services/pricing_engine.py line 23 imports deleted app.schemas.pricing.PricingAlert; fix in construction |
| celery_app.py include pattern | reference | include=[] when task modules absent; re-populate with ["app.workers.image_tasks", ...] when V1 tasks ship |
| task_reject_on_worker_lost | reference | Added to celery conf per services-builder ALWAYS rule |
| V1 head revision (DB) | reference | f31c75438e61 (chain: 935e55b4852c → a1b2c3d4e5f6 → f31c75438e61) |
| §4 core/ services slice 2026-06-06 | project | 11 files + 7 test files (39 tests) — errors, tenancy, cache, plan_guard, 5 middleware + app/main wiring |
| Rate-limit JSONResponse-inline decision | reference | BaseHTTPMiddleware raises bypass FastAPI exception handlers — middleware MUST return Response, not raise |
| Plan guard product_count needs db kwarg | reference | enforce_plan_limit(resource="product_count", db=AsyncSession) — local import of Product model to avoid core/→domain imports |
| Per-route rate-limit via decorator + manual route match | reference | @rate_limit(scope,limit,window) attaches __rate_limit__; mw walks app.router.routes[r].matches(scope) — request.scope["route"] is None at BaseHTTPMiddleware entry |
| use_live_valkey fixture | reference | tests/conftest.py loop_scope="function" — points singletons at localhost:6379, flushes scratch DBs around test |
| Middleware registration deepest-first | reference | Starlette stores users[0]=outermost; register Audit FIRST then PlanGuard → RateLimit → Tenancy → Auth → RequestId → CORS to achieve §4.H runtime order |
| i18n resolver deferred wire | reference | errors._resolve_message_id() lazy-imports app.i18n.resolver; falls back to mid or fallback; no code change needed when §5A lands |
| auth URL pattern (routes) | reference | /api/v1/auth/otp/send, /otp/verify, /me — locked by api-routes-builder |
| Python venv path | reference | backend/.venv/bin/python (3.11); PYTHONPATH=backend/ for pytest |
| app/i18n/ pattern (DB) | reference | versioned schema_jsonb constants; services producing schema_jsonb MUST import here |

---
