## Phase 4 — Smoke Tests COMPLETE (2026-06-05)

### Files authored / patched
| File | Purpose | LOC |
|---|---|---|
| `backend/tests/conftest.py` | PATCHED — added dev_engine (session) + db (function, loop_scope=function) fixtures | +77 |
| `backend/tests/test_database.py` | NEW — 40 smoke tests across 8 categories | 621 |

### Test results (all pass)
- 40/40 tests pass — 0 failures
- Wall time: 83.05s
- Zero test data leaked to dev Postgres (all 9 mutable tables still at 0 rows post-run)
- Seeded reference counts unchanged: templates=3566, categories=3772, field_enum_values=49259, field_aliases=67

### Test categories and counts
| Category | Tests | Result |
|---|---|---|
| A. CRUD per table | 13 (one per model) | 13/13 pass |
| B. JSONB round-trip | 8 (one per JSONB column) | 8/8 pass |
| C. FK enforcement | 5 | 5/5 pass |
| D. Unique constraint enforcement | 3 | 3/3 pass |
| E. CHECK constraint enforcement | 2 | 2/2 pass |
| F. Computed column (is_front) | 2 | 2/2 pass |
| G. Server-default verification | 3 | 3/3 pass |
| H. Seeded data sanity (read-only) | 4 | 4/4 pass |
| Total | 40 | 40/40 |

### Real schema bugs surfaced
None. All constraints, defaults, and computed columns behaved exactly as modeled.

### Critical gotcha: pytest-asyncio 0.24 + asyncpg loop scoping
Problem: pytest.ini has asyncio_default_fixture_loop_scope = session.
SESSION-scoped async fixtures run in the session event loop.
FUNCTION-scoped tests and fixtures run in a per-test function-scoped loop.
asyncpg Protocols attach Futures to the event loop running when the connection is established.
Cross-scope access raises: RuntimeError: Task got Future attached to a different loop

Fix (canonical for this project):
  Use @pytest_asyncio.fixture(loop_scope="function") on the db fixture.
  Create a fresh NullPool engine INSIDE the fixture body.
  Every engine/connection/Protocol/Future is created and disposed within the same function loop.

Pattern for future test files that need transaction rollback:
  @pytest_asyncio.fixture(loop_scope="function")
  async def db() -> AsyncSession:
      eng = create_async_engine(DEV_URL, poolclass=NullPool, echo=False)
      try:
          async with eng.connect() as conn:
              await conn.begin()
              Session = async_sessionmaker(bind=conn, expire_on_commit=False, class_=AsyncSession)
              session = Session()
              try:
                  yield session
              finally:
                  await session.close()
                  await conn.rollback()
      finally:
          await eng.dispose()

For read-only session-scoped fixtures (section H pattern), session-scoped NullPool engine works
because there is no SQLAlchemy async greenlet switching — plain conn.execute(text(...)) only.

### Timestamp comparison tolerance
test_server_default_created_at uses 30s tolerance for created_at vs local now().
Port-forward adds ~5ms latency. 30s is safe. Do not tighten below 10s without on-cluster access.

### Conftest app.main guard
Legacy routers (catalogs.py, skus.py, images.py) still import deleted models (app.models.image, app.models.sku).
conftest.py guards the import with try/except. client and auth_client fixtures call pytest.skip() when app is None.
api-routes-builder must delete or rewrite those legacy routers before route tests can run.

### Final database track summary
- 13 tables validated against PG16 (Supabase self-hosted, K3s dev namespace)
- Baseline migration: 935e55b4852c
- Seed counts: field_aliases=67, templates=3566, categories=3772, field_enum_values=49259
- All 40 smoke tests pass, zero test data leakage
- DATABASE TRACK COMPLETE — ready for backend API track

---

---
