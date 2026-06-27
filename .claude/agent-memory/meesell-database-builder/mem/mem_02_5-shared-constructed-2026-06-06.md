## §5 shared CONSTRUCTED (2026-06-06)

### Scope
Joint dispatch with `meesell-services-builder` against `BACKEND_ARCHITECTURE.md` §5 (`shared/` Foundation Layer).

### What I did (database-builder side — §5.E)
- Migrated all 13 ORM models verbatim from `backend/app/models/` → `backend/app/shared/models/`.
- Internal `from app.models.<sibling>` references rewritten to `from app.shared.models.<sibling>`.
- Authored `shared/models/__init__.py` — single canonical import surface for `from app.shared.models import (User, SellerProfile, Template, Category, FieldEnumValue, FieldAlias, Catalog, Product, ProductImage, PricingCalc, Export, AuditEvent, ProductDraft)` (the locked §5.E import path).
- Authored `shared/models/base.py` — re-exports `Base` from `shared/database.py` for backward-compat with the existing model-side import convention.
- NO schema changes. Alembic head remains `f31c75438e61`. No new migrations authored.
- Legacy `backend/app/models/` tree DELETED. Legacy `app/models/base.py` DELETED.

### Cutover scope (joint with services-builder)
Updated 14 legacy importers (master originally listed 6 — found 8 more by grep):
- `app/main.py`, `app/routers/auth.py`, `app/middleware/auth.py`, `app/middleware/plan_guard.py`
- `app/workers/celery_app.py`
- `app/services/otp_service.py`, `app/services/ai_engine.py`, `app/services/storage.py`
- `alembic/env.py`
- `tests/conftest.py`, `tests/test_database.py`, `tests/test_config.py`, `tests/test_worker_db_isolation.py`, `tests/test_middleware_auth.py`, `tests/test_middleware_plan_guard.py`

### Tests
- 42/42 schema tests (`tests/test_database.py`) — PASS against live dev Postgres via SSH tunnel (gcloud-managed, port 5433).
- 7/7 boot integration tests (`tests/test_app_boot_integration.py`) — PASS.

### Acceptance criteria status
| # | Criterion | Status |
|---|---|---|
| 1 | §5.E — 13 model files in shared/models/ matching Alembic head f31c75438e61 | PASS |
| 2 | §5.E — `__init__.py` exports all 13 single import surface | PASS |
| 3 | §5.E — SQLAlchemy 2.0 `Mapped[T]` style preserved | PASS (verbatim migration) |
| 4 | §5.E — `Base` re-exported by `shared/models/base.py` | PASS |
| 5 | 42/42 schema tests continue PASS | PASS |
| 6 | Ruff clean on touched files | PASS |

### Hand-offs queued
- §4 `core/` construction can now consume `from app.shared.models import …` per the locked single-import-surface rule.
- §4 `core/auth.py` (FE-D5 amendment) consumes `shared/database.py:get_db` + `shared/valkey.py:get_valkey_otp` + the Lua script registration helpers (`load_lua_script`, `eval_lua_script`).
- §7 (`iam` module) dispatch will populate Secret Manager values for `refresh-token-pepper` and `razorpay-webhook-secret` (declared in `shared/config.py:Settings` per §5.D, currently dev-placeholder in `.env`).

---
