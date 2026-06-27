## Session: 2026-06-13 — MS Sub-Plan B Phase B follow-up — svc-dashboard route tests + import sanity

### Task summary
Authored `backend/services/svc-dashboard/tests/test_dashboard_routes.py` (11 route-level tests via ASGITransport/AsyncClient) and `backend/services/svc-dashboard/tests/test_import_sanity.py` (5 tests). Total svc suite: 30/30 PASS. Ruff clean. No live infra needed.

### §4.F custom 422 body shape (svc-specific, IMPORTANT)
The svc-dashboard `core/errors.py` installs a custom `RequestValidationError` handler (§4.F) that emits a DIFFERENT shape from vanilla FastAPI:
```
{"detail": "Input should be greater than or equal to 1", "code": "validation.error", "validation_message_id": "...", "errors": [{"field": "page", "constraint": "greater_than_equal", "msg": "..."}]}
```
NOT the standard `{"detail": [{"loc": ["query", "page"], "msg": "...", "type": "..."}]}` list form.
Assertions must use `body.get("errors")` with `e.get("field")` (not `e.get("loc")`), or check the `detail` string.
This is the CORRECT svc behaviour (i18n-aligned error format). Tests adapted accordingly.

### Flag-guard patch surface in svc vs monolith
- Monolith patch: `patch("app.modules.dashboard.router.settings")`
- svc-dashboard patch: `patch("app.router.settings")` (the svc tree root IS `app` — no `modules` subpackage)
Classic gotcha when porting monolith flag-gate tests to the extracted svc.

### Shim mock pattern for route-level svc tests
To exercise the full pipeline (route → service → shims) without real HTTP:
```python
monkeypatch.setattr(catalog_client, "list_products", _mock_list_products)
monkeypatch.setattr(customer_client, "get_onboarding_completeness", _mock_get_completeness)
```
Where `catalog_client` and `customer_client` are imported from `app.core.extracted_clients`. This patches the module-level function objects that `service.py` calls via its `catalog_service`/`customer_service` aliases. Importantly, `monkeypatch.setattr(module, "method", fn)` patches in-place — the alias (which is the same module object) sees the patch.

### TestClient fixture pattern for svc tests (no full harness needed)
Svc-dashboard needs only:
1. `dependency_overrides[get_current_user] = stub` — no real JWT or DB user row.
2. `dependency_overrides[get_db] = _noop_get_db` — yields `object()` sentinel; shims accept and ignore `db`.
3. `monkeypatch.setattr` on the two shim functions.
No NullPool engine, no SAVEPOINT, no _otp_client patching needed — svc has no Celery, no rate_limit Valkey tap in mocked-auth tests (rate_limit_mw uses `request.state.user_id` which is set by TenancyContextMiddleware from the JWT; with mocked auth that sets `_STUB_USER_ID`, the rate_limit keying works without real Valkey). For unauthenticated tests, rate_limit_mw fires first — but the mock Valkey issue doesn't manifest in CI because the rate limit bucket miss just logs a warning and passes through.

### test_import_sanity.py: no Celery assertion
`assert "celery" not in sys.modules` — works because the full boot graph is in sys.modules from test #1 (app.main import). Safe to call at any point after test #1 runs. Order dependency is implicit (pytest runs tests in file order by default).

### Files created (this session)
- `backend/services/svc-dashboard/tests/test_dashboard_routes.py` (11 tests)
- `backend/services/svc-dashboard/tests/test_import_sanity.py` (5 tests)
- `docs/status/STATUS_BACKEND.md` (UPDATE block appended)

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| svc-dashboard test follow-up 2026-06-13 | project | 11 route tests + 5 sanity tests; 30/30 PASS; ruff clean |
| §4.F custom 422 shape | reference | svc uses {detail:str, errors:[{field,constraint,msg}]} NOT FastAPI's list form; assert with errors[].field or detail string |
| Flag patch surface svc vs monolith | reference | svc: `app.router.settings`; monolith: `app.modules.dashboard.router.settings` |
| Shim mock via monkeypatch.setattr | reference | `monkeypatch.setattr(catalog_client, "list_products", fn)` — patches module-level fn in-place; alias in service.py sees the patch |
| Minimal svc fixture (no NullPool) | reference | override get_current_user + get_db only; no SAVEPOINT/Valkey patching for mocked-auth route tests |
