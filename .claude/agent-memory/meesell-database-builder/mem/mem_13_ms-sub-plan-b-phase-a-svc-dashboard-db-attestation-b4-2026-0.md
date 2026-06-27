## MS Sub-Plan B Phase A — svc-dashboard DB attestation B4 (2026-06-13) [meesell-database-builder AUTHORITATIVE]

### Scope
VERIFY-ONLY task. Independently verified (as the correct meesell-database-builder owner per CLAUDE.md rule 1) that the dashboard module (`backend/app/modules/dashboard/`) owns ZERO tables and introduces NO Alembic chain. Worktree: `/tmp/mesell-wt/msB-backend/`, source commit `98f6a96`.

### Evidence — all 6 files read in full + grep results

Files confirmed present and read:
- `__init__.py` (lines 1-37): module docstring + `from app.modules.dashboard.router import router as dashboard_router`. No imports from SQLAlchemy, alembic, or any DB layer.
- `domain.py` (lines 1-41): post-§13.A.1 amendment — intentionally empty (`__all__: list[str] = []`). Only `from __future__ import annotations`. No ORM, no DB.
- `exceptions.py` (lines 1-62): `DashboardError` + `InvalidPaginationError` both subclass `app.core.errors.MeesellError`. No DB access, no SQLAlchemy imports.
- `schemas.py` (lines 1-98): 4 Pydantic v2 models (`DashboardQuery`, `ProductListItem`, `ProfileCompletenessSummary`, `DashboardResponse`). `from pydantic import BaseModel` only — NOT SQLAlchemy Base.
- `router.py` (lines 1-131): `GET /api/v1/products` handler. `db: Annotated[AsyncSession, Depends(get_db)]` declared as FastAPI DI parameter; immediately forwarded to `dashboard_service.list_products_for_dashboard(user_id=..., query=..., db=db)` at line 124-128 — no direct query.
- `service.py` (lines 1-150): `list_products_for_dashboard` makes exactly 2 awaits: `catalog_service.list_products(user_id=user_id, pagination=pagination, db=db)` (line 78) and `customer_service.get_onboarding_completeness(user_id=user_id, db=db)` (line 84-87). `_compose_response` is pure (no I/O, no await, no DB). `db` is never used to execute any query in this file.

#### Grep results (file:line evidence)

**SQLAlchemy ORM terms** (`Base`, `__tablename__`, `Mapped[`, `mapped_column`, `Column(`, `declarative_base`):
- `schemas.py:25` — `from pydantic import BaseModel, ConfigDict, Field` (Pydantic, NOT SQLAlchemy)
- `schemas.py:28,42,61,81` — class definitions `(BaseModel)` (Pydantic, NOT SQLAlchemy)
- `exceptions.py:35` — prose docstring "Base class for dashboard module failures" (English prose, NOT SQLAlchemy Base)
- Result: ZERO SQLAlchemy ORM hits

**Alembic terms** (`op.`, `revision`, `down_revision`, `alembic`):
- Result: NO MATCHES (zero hits across all 6 files)

**Raw query execution** (`select(`, `.execute(`, `scalars`, `scalar_one`, `fetchall`, `fetchone`, `text(`, `db.`, `session.`):
- Result: NO MATCHES (zero hits in `service.py`; `db` parameter appears only in function signatures as `AsyncSession` type annotation, never as a call site)

#### Structural checks
- `repository.py`: DOES NOT EXIST in `/tmp/mesell-wt/msB-backend/backend/app/modules/dashboard/` — deliberate §13.D deviation confirmed.
- `backend/services/`: contains only `svc-export/` — `svc-dashboard/` DOES NOT EXIST.
- `backend/alembic/versions/`: 3 files — `935e55b4852c_v1_baseline_13_tables.py`, `a1b2c3d4e5f6_pg_trgm_and_category_gin.py`, `f31c75438e61_add_idx_product_drafts_saved_at.py`. The word "dashboards" appears only at `f31c75438e61_add_idx_product_drafts_saved_at.py:10` in prose: "staleness dashboards, manual cleanup runs during V1" — zero schema action related to any dashboard table.
- Monolith Alembic head: `f31c75438e61` — UNCHANGED.

### Learning (§13.D pattern for future reference)
When a module is a pure consumer (leaf in the §2.D dependency matrix) that composes results from two other modules' service functions, the correct database-builder stance is to author NO migration, NO model file, NO Alembic chain, and NO repository.py — the §13.D structural deviation is load-bearing, not an oversight. The verification discipline for such modules is: grep for `__tablename__`, `Mapped[`, `Base`, `alembic` across the subtree (must all be zero for ORM / migration terms); confirm `AsyncSession` appears only as a forwarded parameter, never as a query-issuing call site; confirm no `repository.py` exists; confirm no entry in `backend/services/`. This pattern generalises to any future "view-only aggregation" module (e.g., a reporting module that reads from catalog + pricing).

### Memory index entry
| Entry | Type | Summary |
|---|---|---|
| MS-B B4 svc-dashboard DB attestation (AUTHORITATIVE) | project | meesell-database-builder owner; ZERO tables, ZERO migrations, ZERO model files, NO repository.py; monolith head f31c75438e61 unchanged; verified @ commit 98f6a96; all 6 files read + grep evidence at file:line |
| §13.D no-repository pattern | reference | Pure consumer modules own no DB objects; AsyncSession forwarded not queried; grep __tablename__/Mapped[/Base to confirm clean; generalises to any aggregation-only module |
| Category Seeding Wave 1 (LOCAL-ONLY) COMPLETE | project | Seed scripts import-corrected (app.config → app.shared.config; app.models.* → app.shared.models.*). make seed target added. Counts: categories=3772, field_aliases=67, templates=3566, field_enum_values=49259. Idempotency confirmed. PR #245 OPEN (feature/category-seeding → develop), commit d5e71a9. Head f31c75438e61 unchanged. |
| Stale Valkey cache blocks prewarm after fresh seed | reference | If Valkey DB 3 has a stale pre-seed empty-list category_tree key (from before seed ran), prewarm logs "0 schema entries warmed". Fix: redis-cli -n 3 DEL "meesell:v1:category_tree". The K8s deploy order (migrate → seed → API boot) naturally avoids this in non-local envs. |
| Seed script import-path pattern (post-MS-PAR-1 rebuild) | reference | All 5 seed scripts used app.config + app.models.* (pre-modular-monolith paths). Live tree has app.shared.config + app.shared.models.*. Class names (Category, Template, FieldAlias, FieldEnumValue) and settings symbol are identical in both. Mechanical substitution only; no logic change. |
| Worktree venv creation pattern | reference | Worktrees carry no .venv. Use python3.11 -m venv backend/.venv (gitignored). Install: sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-dotenv, fastapi, pyjwt, redis, prometheus_client for the full prewarm import chain. Python 3.12 not required; 3.11 works. |
| Local DB port: 5432 not 5433 | reference | .env.example shows 5433 but live local dev stack uses 5432. Probe with pg_isready before creating .env. The local .env (gitignored) must override to 5432. |

---
