## Session: 2026-06-12 — Gate-4 cross-loop contamination fix (fix/gate4-loop-contamination)

### Task summary
Fixed 6 FAILED + 13 ERROR integration tests unmasked by PR #150 (Gate-1 event-loop fix).
Root cause: `iam_client` fixture had `loop_scope="function"` but NO `get_db` override —
routes resolved `Depends(get_db)` against the app-global `AsyncSessionLocal`, whose asyncpg
pool was bound to the session loop. Function-scoped tests get their own loop → `RuntimeError:
got Future attached to a different loop`. Starlette's `BaseHTTPMiddleware` + anyio TaskGroup
wrapped this as an ExceptionGroup that bypassed test assertions.

Secondary root cause (13 ERRORs): `app.state.db_engine` (pooled, `pool_pre_ping=True`) created
by lifespan schedules asyncpg pool callbacks via `loop.call_soon()`. These fire AFTER the
function loop teardown → `Event loop is closed` teardown errors.

### Authoritative spec
`.claude/agent-memory/meesell-backend-coordinator/spec_ci_gate4_loop_contamination.md`
on branch `origin/docs/gate1-resolved-gate4-spec` (locked before this session).

### Files modified (test harness only — app/ untouched)

**1. `backend/tests/integration/conftest.py` — PRIMARY FIX (complete rewrite)**
- Old: 118 lines, iam_client had NO `get_db` override
- New: ~264 lines, mirrors `customer_client` / `export_client` twin pattern
- Key additions:
  - `_cleanup_users_by_phone_prefix(db_url)` — accepts explicit `db_url` param; uses NullPool
  - `iam_client` fixture: full NullPool engine + SAVEPOINT isolation + DI overrides
  - Patches: `audit_mw.AsyncSessionLocal`, `shared.valkey._cache_client`
  - Explicit lifespan-state disposal (see pattern below)
  - Provision-aware schema setup: skip drop_all/create_all when `TEST_DATABASE_URL` set
  - Phone prefix `+9155500` — non-routable Indian test numbers

**2. `backend/tests/test_shared_database.py` — MODIFIED**
- `test_get_db_yields_async_session`: patched `AsyncSessionLocal` with per-test NullPool
  session-maker instead of using app-global session-loop-bound engine.
- Added `create_async_engine` to SQLAlchemy import line.

**3. `backend/tests/test_customer_routes.py` — MODIFIED**
- Added lifespan-state tracking + explicit disposal after lifespan exits (inside async body).

**4. `backend/tests/modules/export/test_router.py` — MODIFIED**
- Same lifespan teardown hygiene applied to both `export_client` and `unauth_client` fixtures.

### Canonical iam_client fixture pattern (LOCKED)

```python
@pytest_asyncio.fixture(loop_scope="function")
async def iam_client():
    import redis.asyncio as _redis_lib
    db_url = _DEV_DATABASE_URL
    valkey_base = _valkey_base()

    # 1. NullPool engine (no Future binding)
    engine = create_async_engine(db_url, poolclass=NullPool, echo=False)
    _provisioned = bool(os.environ.get("TEST_DATABASE_URL"))
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    # 2. SAVEPOINT per-test isolation
    shared_conn = await engine.connect()
    outer_txn = await shared_conn.begin()
    TestSession = async_sessionmaker(
        bind=shared_conn, expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    # 3. FastAPI DI overrides
    app.dependency_overrides[get_valkey_otp] = _otp_override
    app.dependency_overrides[get_db] = _db_override

    # 4. Module-level singleton patches
    _audit_mw.AsyncSessionLocal = TestSession
    _valkey_module._cache_client = _redis_lib.from_url(f"{valkey_base}/3", ...)

    # 5. Pre-test cleanup (NullPool engine)
    await _cleanup_users_by_phone_prefix(db_url)

    # 6. Boot lifespan + yield + teardown
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            lifespan_db_engine = getattr(app.state, "db_engine", None)
            lifespan_valkey_client = getattr(app.state, "valkey", None)
            yield ac
        # CRITICAL: explicit disposal AFTER lifespan exits, WITHIN async body
        if lifespan_db_engine is not None:
            try: await lifespan_db_engine.dispose()
            except Exception: pass
        if lifespan_valkey_client is not None:
            try: await lifespan_valkey_client.aclose()
            except Exception: pass

    # finally: restore singletons, rollback outer_txn, dispose engine, pop overrides
```

### Double-dispose pattern (LOCKED for lifespan teardown hygiene)
When a fixture boots a FastAPI lifespan that creates a pooled engine (`app.state.db_engine`
with `pool_pre_ping=True`), you MUST explicitly dispose that engine AFTER the lifespan
exits but while still inside the fixture's async body (function loop active). This drains
pending asyncpg pool callbacks BEFORE the function loop is torn down. Without this,
`Event loop is closed` teardown errors fire on every test.

The same applies to `app.state.valkey` (async Redis client) — explicit `aclose()` needed.

Pattern:
```python
async with app.router.lifespan_context(app):
    lifespan_db_engine = getattr(app.state, "db_engine", None)
    lifespan_valkey_client = getattr(app.state, "valkey", None)
    yield ac
# Here: lifespan has exited its own dispose calls, but callbacks still pending
if lifespan_db_engine is not None:
    try: await lifespan_db_engine.dispose()  # drain asyncpg pool callbacks
    except Exception: pass
if lifespan_valkey_client is not None:
    try: await lifespan_valkey_client.aclose()
    except Exception: pass
```

### Gate-1 unmasks Gate-4 lesson
Removing a session-scope `event_loop` fixture (PR #150) correctly shifts all session-scoped
fixtures to the session event loop. This unmasks latent cross-loop contamination in any
fixture that did NOT override `get_db`. Lesson: every fixture that boots a FastAPI lifespan
MUST override `get_db` with a NullPool session-maker bound to the fixture's own loop, regardless
of whether it looks like it "works" with the session-scope fixture present.

### `_valkey_base()` helper — precedence chain
Strips trailing `/<db>` from Valkey URLs to prevent `/0/0` double-suffix.
Precedence: `TEST_VALKEY_URL > VALKEY_URL > CORE_TEST_VALKEY_URL > redis://localhost:6379`
Defined in `tests/conftest.py`. Import: `from tests.conftest import _DEV_DATABASE_URL, _valkey_base`

### `_DEV_DATABASE_URL` — precedence chain (LOCKED)
`TEST_DATABASE_URL > DEV_DATABASE_URL > baked K3s-dev DSN`
Defined in `tests/conftest.py`. Required by any test module that needs a per-fixture NullPool engine.

### Phone prefix convention
Every integration test uses `+9155500XXXXX` range — non-routable Indian SIM numbers.
Safe to DELETE-by-prefix at teardown. Hard-coded in `_INTEGRATION_PHONE_PREFIX`.

### Local env note (Gate-4 session)
Dev tunnel to postgres (port 5433) NOT available locally during this session.
Only Valkey on port 6379 available. Integration tests require live DB → CI is the
formal acceptance confirmation. Unit tests (634 passing) verified no regressions.
4 pre-existing unit failures on `origin/develop` baseline CONFIRMED pre-existing
(verified via git stash + baseline run before our changes).

### Worktree + PR
- Worktree: `/tmp/mesell-wt/gate4-fix/`
- Branch: `fix/gate4-loop-contamination`
- Commit SHA: `6c5941f`
- PR: #159 → develop (OPEN, awaiting coordinator STEP 3)

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| Gate-4 cross-loop fix 2026-06-12 | project | 4 test harness files fixed; PR #159 open for coordinator STEP 3 |
| NullPool + get_db override rule | reference | Every fixture that boots FastAPI lifespan MUST override get_db with NullPool session |
| Double-dispose lifespan teardown | reference | Explicit dispose()/aclose() after lifespan exits, while still in async body |
| Gate-1 unmasks Gate-4 lesson | reference | Removing session event_loop fixture reveals latent cross-loop contamination |
| _valkey_base() / _DEV_DATABASE_URL | reference | Imported from tests/conftest.py; precedence chains locked |
| Integration phone prefix | reference | +9155500XXXXX range; non-routable; safe for DELETE-by-prefix teardown |

---
