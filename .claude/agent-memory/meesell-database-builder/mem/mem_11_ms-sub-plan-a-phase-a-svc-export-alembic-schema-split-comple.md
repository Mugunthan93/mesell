## MS Sub-Plan A Phase A — svc-export Alembic schema-split COMPLETE (2026-06-12)

### Scope
Sub-session dispatched by `meesell-backend-coordinator` per `spec_msA_backend.md` §3.C. Task: author and validate the standalone Alembic migration chain for `svc-export`, effecting the `public.exports` → `export.exports` schema move called for by MASTER_PLAN §2.D (schema-per-service isolation, V1.5 prep). Commit 5747189 on `feature/microservices-export/backend` (worktree `/tmp/mesell-wt/msA-backend/`).

### What was built (4-file standalone chain)

| File | Path | Purpose |
|---|---|---|
| `alembic.ini` | `backend/services/svc-export/alembic.ini` | Standalone chain config. `sqlalchemy.url` intentionally blank — URL injected via `DATABASE_URL` env var to avoid configparser `%`-interpolation. `script_location = alembic`. |
| `env.py` | `backend/services/svc-export/alembic/env.py` | Async env with `version_table_schema="export"` — the chain's version row lands in `export.alembic_version`, not `public.alembic_version`. `target_metadata = None` (hand-authored DDL only). `transaction_per_migration=True`. |
| `script.py.mako` | `backend/services/svc-export/alembic/script.py.mako` | Standard Alembic mako template (unmodified default). |
| `e7a3c1f9b42d_move_exports_to_export_schema.py` | `backend/services/svc-export/alembic/versions/` | Revision `e7a3c1f9b42d`, `down_revision=None` (root of chain). |

`upgrade()`: (1) Risk#5 integrity pre-scan — orphaned `exports.user_id` count; raises `RuntimeError` with up to 20 detail rows on non-zero (hard abort, no partial move); (2) `CREATE SCHEMA IF NOT EXISTS export`; (3) `ALTER TABLE public.exports SET SCHEMA export`. `downgrade()`: `ALTER TABLE export.exports SET SCHEMA public`.

### Monolith head status
`f31c75438e61` — UNCHANGED. The two chains are fully independent (different version tables in different schemas).

### Validated round-trip (local Homebrew Postgres 16.11 — NOT the dev tunnel)
Dev tunnel down (`nc -zv localhost 5433` refused). Scratch DB `meesell_svc_export_test` seeded with valid users/exports pair. Results: upgrade → `e7a3c1f9b42d (head)` in export schema, `public.exports` gone, `export.exports` + `export.alembic_version` present; orphan-abort test PASSED (RuntimeError, clean rollback); downgrade restored `public.exports`; full round-trip PASSED.

### Critical env.py gotcha — schema must exist BEFORE context.configure()
Alembic's `_ensure_version_table()` runs at `context.configure()` time and needs `export.alembic_version` creatable — if the schema doesn't exist yet, Postgres errors before any migration code runs. Fix (load-bearing): in `do_run_migrations()`, execute `CREATE SCHEMA IF NOT EXISTS export` + `connection.commit()` BEFORE `context.configure(...)`. The commit is required so the schema DDL is visible to configure-time internal queries (asyncpg implicit-transaction visibility).

### Reusable schema-split recipe (for waves MS-2..5)
1. `backend/services/<svc>/alembic.ini` with `sqlalchemy.url =` blank — URL via env var only (configparser `%`-interpolation trap).
2. `env.py`: `version_table_schema="<svc_schema>"` (one distinct schema per chain, never reuse); `target_metadata = None` unless the service owns its own ORM Base; `transaction_per_migration=True`; `CREATE SCHEMA IF NOT EXISTS <svc_schema>` + `connection.commit()` at top of `do_run_migrations()` BEFORE `context.configure()`.
3. First migration: `down_revision = None` (root); `ALTER TABLE public.<table> SET SCHEMA <svc_schema>`.
4. Local Homebrew PG16 is a valid validation substitute when the dev tunnel is down — identical DDL behavior to K3s Supabase PG16 for these operations.
5. Risk#5 pattern: always pre-scan FK integrity before a schema move; `SELECT COUNT(*) ... WHERE NOT EXISTS (...)` + raise on non-zero + emit up to 20 detail rows.

### Memory index entry
| Entry | Type | Summary |
|---|---|---|
| MS Sub-Plan A Phase A svc-export schema-split | project | 4-file standalone Alembic chain; head e7a3c1f9b42d; version_table_schema="export"; monolith head f31c75438e61 unchanged; round-trip validated on local Homebrew PG 16.11 |
| schema-split env.py gotcha | reference | CREATE SCHEMA + commit MUST precede context.configure() — _ensure_version_table() needs schema visible at configure time |
| schema-split recipe for MS-2..5 | reference | version_table_schema per service; blank sqlalchemy.url; Risk#5 orphan-abort pattern; commit DDL before context.configure() |

---
