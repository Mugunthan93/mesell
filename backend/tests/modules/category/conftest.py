"""Category-module test fixtures.

The §9.J unit tests run against the **live dev Postgres tunnel** on
port 5433 (the ``db`` fixture in the top-level ``tests/conftest.py``)
because §9 reads seeded reference data: 3,772 categories, 3,566
templates, 49,259 field_enum_values rows.  Without the seed there is
nothing meaningful to assert.

The pg_trgm extension + the 3 GIN indexes (idx_categories_path_trgm,
idx_categories_leaf_name_trgm, idx_categories_super_name_trgm) only
exist on the dev tunnel DB (shipped by migration ``a1b2c3d4e5f6``), so
the EXPLAIN ANALYZE Bitmap-Index-Scan assertion in
``test_trigram_search_uses_gin_index.py`` REQUIRES this fixture.

Added: ``_disable_category_cache`` autouse fixture (QA Wave-A gap fills)
-----------------------------------------------------------------------
Route-level gap tests (test_suggest_gap_fill, test_browse_gap_fill, etc.)
make ASGI requests against the app which calls ``app.core.cache.get_or_set``
internally.  That function connects to the app's configured Valkey instance
(port 6381) which is NOT available in the local test environment.
The autouse fixture patches ``get_or_set`` to a passthrough factory-call
so all category-module route tests run without a live app Valkey.

Note: this mirrors the identical pattern in tests/modules/catalog/conftest.py
(§10-CATALOG-D1 test isolation).

Added: ``category_route_client`` fixture (PR #435 re-do / Gate-4 loop-affinity fix)
------------------------------------------------------------------------------------
D1+D2 fix: overrides ``get_db`` with a function-loop NullPool engine AND patches
``_valkey_module._otp_client`` to a fresh function-loop client.  Without these patches
the combined ``pytest -m integration`` run produces RuntimeError: Event loop is closed /
got Future attached to a different loop → 500 before any route runs.  Mirrors the
``integration/conftest.py::iam_client`` canon pattern.
"""

from __future__ import annotations

import pytest
import pytest_asyncio


# ─────────────────────────────────────────────────────────────────────────────
# category_route_client — D2-patched ASGI fixture (Gate-4 repair pattern)
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def category_route_client():
    """ASGI client with stub auth, function-loop NullPool DB, and D2 Valkey fix.

    Mirrors ``integration/conftest.py::iam_client`` exactly:

    * D1 fix: overrides ``get_db`` with a function-loop NullPool engine so
      route handlers never touch the module-level ``AsyncSessionLocal``
      (session-loop-bound engine) → kills "got Future attached to a different
      loop" from the middleware/route DB access.
    * D2 fix: swaps ``_valkey_module._otp_client`` to a fresh function-loop
      client → kills "RuntimeError: Event loop is closed" in rate_limit_mw.
    * audit_mw patch: ``AuditMiddleware`` uses ``AsyncSessionLocal`` directly
      (not via DI) — patch it to the same NullPool session-maker.
    """
    import os as _os
    import uuid as _uuid
    from dataclasses import dataclass

    import redis.asyncio as _redis_lib
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import app.core.middleware.audit_mw as _audit_mw
    import app.shared.valkey as _valkey_module
    from app.core.auth import get_current_user
    from app.main import app
    from app.shared.database import get_db
    from tests.conftest import _DEV_DATABASE_URL, _valkey_base

    @dataclass(frozen=True)
    class _StubUser:
        user_id: object = None
        plan: str = "free"

        def __post_init__(self):
            if self.user_id is None:
                object.__setattr__(self, "user_id", _uuid.uuid4())

    def _stub_dep():
        return _StubUser()

    db_url = _DEV_DATABASE_URL
    valkey_base = _valkey_base()

    # D1: function-loop NullPool engine — no connection reuse across loops.
    engine = create_async_engine(db_url, poolclass=NullPool, echo=False)
    _provisioned = bool(_os.environ.get("TEST_DATABASE_URL"))
    if not _provisioned:
        from app.shared.database import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def _db_override():
        session = TestSession()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_user] = _stub_dep

    # audit_mw uses AsyncSessionLocal directly (not via DI).
    _original_audit_session_local = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = TestSession  # type: ignore[attr-defined]

    # D2: fresh function-loop OTP client.
    _original_otp_client = _valkey_module._otp_client
    _test_otp_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    _valkey_module._otp_client = _test_otp_client  # type: ignore[assignment]

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    lifespan_db_engine = None
    lifespan_valkey_client = None

    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                lifespan_db_engine = getattr(app.state, "db_engine", None)
                lifespan_valkey_client = getattr(app.state, "valkey", None)
                yield ac

            if lifespan_db_engine is not None:
                try:
                    await lifespan_db_engine.dispose()
                except Exception:
                    pass
            if lifespan_valkey_client is not None:
                try:
                    await lifespan_valkey_client.aclose()
                except Exception:
                    pass
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        _audit_mw.AsyncSessionLocal = _original_audit_session_local  # type: ignore[attr-defined]
        _valkey_module._otp_client = _original_otp_client  # type: ignore[assignment]
        try:
            await _test_otp_client.aclose()
        except Exception:
            pass
        if not _provisioned:
            try:
                from app.shared.database import Base
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            except Exception:
                pass
        try:
            await engine.dispose()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def _disable_category_cache(monkeypatch):
    """Bypass the app Valkey cache for all category-module tests.

    Patches ``app.core.cache.get_or_set`` to call the factory directly,
    plus every consumer module that captured ``get_or_set`` by name at
    import time.  This keeps category route tests hermetic without
    requiring a live app Valkey on port 6381.
    """
    import app.core.cache as cache_mod

    async def _passthrough(key, factory, *, ttl=60, single_flight=False):
        return await factory()

    monkeypatch.setattr(cache_mod, "get_or_set", _passthrough)

    for mod_path in (
        "app.modules.category.service",
        "app.modules.customer.service",
    ):
        try:
            mod = __import__(mod_path, fromlist=["get_or_set"])
        except Exception:  # noqa: BLE001
            continue
        if hasattr(mod, "get_or_set"):
            monkeypatch.setattr(mod, "get_or_set", _passthrough)
