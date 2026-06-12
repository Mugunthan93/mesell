"""Shared pytest fixtures: ephemeral DB, in-memory Valkey, FastAPI test client."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force dev mode + isolated test schema before importing app modules.
os.environ.setdefault("APP_ENV", "development")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://meesell:password@localhost:5432/meesell",
)
os.environ.setdefault("VALKEY_URL", "redis://localhost:6381/15")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use")
# NOTE (§18 sub-session 2026-06-08): the previous ``CELERY_BROKER_URL``
# + ``CELERY_RESULT_BACKEND`` env-var defaults were removed.  Per §18.E
# the worker derives both URLs from ``settings.VALKEY_URL`` via the
# local ``_build_url_for_db`` helper (DB 1 broker, DB 2 result
# backend).  Setting the env vars at conftest level hijacked Celery's
# resolution order (env wins over ``Celery(broker=...)`` constructor
# arg) and silently broke the §18.E lock.  Tests do NOT enqueue real
# Celery work, so the previous redirect-to-/11+/12 guard is
# unnecessary.
# Defensive removal in case a prior process leaked these into the
# inherited environment (pytest re-uses parent shell env).
os.environ.pop("CELERY_BROKER_URL", None)
os.environ.pop("CELERY_RESULT_BACKEND", None)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.shared.database import Base, get_db  # noqa: E402
from app.shared import models as _models  # noqa: F401,E402 — registers tables on Base.metadata

# app.main imports legacy routers that reference deleted model files (sku.py,
# image.py) from the pre-V1 era.  Those routers are out-of-scope for the
# database track.  Guard the import so that the database smoke tests
# (test_database.py) can load conftest without error.  The client/auth_client
# fixtures that depend on app will be skipped automatically when app is None.
try:
    from app.main import app  # noqa: E402
    _APP_IMPORT_ERROR: Exception | None = None
except Exception as _exc:  # noqa: BLE001
    app = None  # type: ignore[assignment]
    _APP_IMPORT_ERROR = _exc

# ── Dev / test Postgres URL (the ``dev_engine`` + ``db`` fixtures) ────────────
# Precedence (LOCKED — CI Gate-4 harness fix 2026-06-11):
#   TEST_DATABASE_URL  >  DEV_DATABASE_URL  >  baked K3s-dev local default
# Rationale: CI (Gate 4) sets ``TEST_DATABASE_URL`` (meesell_test on 5433) but
# does NOT set ``DEV_DATABASE_URL``.  Previously these fixtures honoured ONLY
# ``DEV_DATABASE_URL`` → they fell through to the baked K3s-dev DSN (wrong db
# ``meesell`` + wrong password) → asyncpg InvalidPassword / InvalidCatalogName
# failures across test_database.py and every integration flow.  The top-of-file
# ``DATABASE_URL`` (L14-17) ALREADY honours ``TEST_DATABASE_URL``; this aligns
# the ``_DEV_DATABASE_URL`` fixtures with that same precedence so the WHOLE
# harness points at one DB in CI.
# LOCAL-DEV GATE: with NO ``TEST_DATABASE_URL`` set, resolution falls through to
# ``DEV_DATABASE_URL`` then the baked dev DSN — byte-for-byte the prior laptop
# behaviour (the founder's port-forward exposes K3s dev Postgres on 5433).
_DEV_DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DEV_DATABASE_URL")
    or "postgresql+asyncpg://meesell:j3w%2F6o%2F7k%2FJwjPu1J4OqDpFStho7IsK%2F0lRYnwmbN6Q%3D@localhost:5433/meesell"
)


# ── Live-Valkey base-URL resolution (CI Gate-4 harness fix 2026-06-11) ────────
# The two live-Redis fixtures (``use_live_valkey``, ``valkey``) build per-DB
# client URLs by APPENDING ``/{db_index}`` to a base URL.  The base must NOT
# already carry a trailing ``/<db>`` path component, or concatenation produces
# an invalid double-suffix (e.g. ``redis://host:6381/0`` + ``/0`` →
# ``redis://host:6381/0/0`` — the redis-py URL parser rejects this).
#
# CI sets ``TEST_VALKEY_URL = redis://localhost:6381/0`` (already ends in /0),
# so the naive ``f"{base}/0"`` produced the /0/0 trap.  ``_valkey_base()``
# resolves the canonical base with precedence and strips any trailing
# ``/<digit>`` so the per-DB index can be appended cleanly.
#
# Precedence (LOCKED): TEST_VALKEY_URL > VALKEY_URL > CORE_TEST_VALKEY_URL
#                      > redis://localhost:6379 (bare default).
# LOCAL-DEV GATE: with none of TEST_VALKEY_URL / VALKEY_URL set, resolution
# falls through to CORE_TEST_VALKEY_URL (the prior laptop override) then the
# bare 6379 default — byte-for-byte the prior behaviour.


def _strip_valkey_db_suffix(url: str) -> str:
    """Strip a trailing ``/<db-index>`` path segment from a redis URL base.

    ``redis://h:6381/0`` → ``redis://h:6381``;  ``redis://h:6379`` unchanged.
    Only a final all-digit segment is removed (a real DB index); any other
    path is left intact.  Trailing slashes are also normalised away so the
    caller can always re-append exactly one ``/{db_index}``.
    """
    base = url.rstrip("/")
    scheme_sep = "://"
    idx = base.find(scheme_sep)
    if idx == -1:
        return base
    authority = base[idx + len(scheme_sep):]
    slash = authority.find("/")
    if slash == -1:
        # No path component at all — e.g. redis://host:6379
        return base
    head = base[: idx + len(scheme_sep) + slash]  # scheme://host:port
    tail = authority[slash + 1:]  # everything after the first '/'
    last = tail.rsplit("/", 1)[-1]
    if last.isdigit():
        # Drop the trailing DB-index segment; keep any prefix path.
        prefix = tail.rsplit("/", 1)[0] if "/" in tail else ""
        return f"{head}/{prefix}".rstrip("/") if prefix else head
    return base


def _valkey_base() -> str:
    """Resolve the canonical Valkey base URL (no trailing DB index) per precedence."""
    raw = (
        os.environ.get("TEST_VALKEY_URL")
        or os.environ.get("VALKEY_URL")
        or os.environ.get("CORE_TEST_VALKEY_URL")
        or "redis://localhost:6379"
    )
    return _strip_valkey_db_suffix(raw)


# ── CI schema provisioning (Class 3 — CI Gate-4 harness fix 2026-06-11) ───────
# In CI (Gate 4) the ``meesell_test`` database is created EMPTY by the
# postgres:16 service container.  Gate 4 runs ``pytest -m integration`` directly
# with NO ``alembic upgrade head`` step, so the schema + the ``pg_trgm``
# extension + the category GIN trigram indexes (migration a1b2c3d4e5f6) are all
# absent → "relation categories does not exist" / "gin_trgm_ops does not exist".
#
# ``create_all`` cannot substitute: it builds ORM tables but NOT the pg_trgm
# extension nor the trigram GIN indexes (those live only in the Alembic
# migration body).  So we run the REAL Alembic chain
# (935e55b4852c → a1b2c3d4e5f6 → f31c75438e61) against ``TEST_DATABASE_URL``.
#
# GATING (critical): this fixture runs ONLY when ``TEST_DATABASE_URL`` is set.
#   * CI sets it → provisioning runs against the ephemeral meesell_test db.
#   * A laptop dev-tunnel run does NOT set it → the fixture is a NO-OP and the
#     live K3s dev DB (already migrated via the real chain) is NEVER mutated.
#
# Execution model: ``alembic/env.py`` calls ``asyncio.run()`` internally, which
# cannot be nested inside pytest-asyncio's running loop.  We therefore invoke
# ``alembic upgrade head`` in a SUBPROCESS (clean interpreter, its own loop)
# with ``DATABASE_URL`` pointed at the test DB (env.py reads
# ``settings.DATABASE_URL``).  The ``CREATE EXTENSION`` is issued first over a
# short-lived asyncpg connection for defensive ordering.


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _provision_test_schema():
    """Session-scoped, autouse: provision the CI ``meesell_test`` schema.

    No-op unless ``TEST_DATABASE_URL`` is present (CI sets it; laptop runs do
    not).  Creates the ``pg_trgm`` extension then runs ``alembic upgrade head``
    against ``TEST_DATABASE_URL`` so the full V1 schema + GIN trigram indexes
    exist before any integration test touches the DB.
    """
    import logging as _logging

    _log = _logging.getLogger(__name__)

    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url:
        # LOCAL-DEV GATE: never migrate the live dev DB from a laptop run.
        yield
        return

    # 1. Clean slate + extension.  We DROP the public schema and recreate it so
    #    ``alembic upgrade head`` always starts from a truly empty database.
    #    This is required because the top-level ``db_engine`` fixture does
    #    ``Base.metadata.create_all`` against the SAME db (DATABASE_URL ==
    #    TEST_DATABASE_URL in CI); a create_all that committed (its drop_all
    #    teardown may not have run if a prior process was interrupted) would
    #    leave ORM tables behind WITHOUT an ``alembic_version`` row, making the
    #    baseline migration fail with DuplicateTable.  DROP SCHEMA guarantees
    #    the migration owns the schema.  Safe: gated on TEST_DATABASE_URL, which
    #    only the ephemeral CI ``meesell_test`` db ever sets (never the live
    #    dev DB).  CREATE EXTENSION is issued before the migration that defines
    #    the pg_trgm GIN indexes (defensive ordering).
    import asyncpg  # local import — only needed on the CI/test path

    # asyncpg needs a libpq DSN (no SQLAlchemy ``+asyncpg`` driver suffix).
    pg_dsn = test_db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(pg_dsn)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE;")
        await conn.execute("CREATE SCHEMA public;")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    finally:
        await conn.close()

    # 2. alembic upgrade head in a subprocess (env.py uses asyncio.run; running
    #    it in-process would nest event loops).  DATABASE_URL drives env.py.
    import asyncio as _asyncio
    import sys as _sys

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sub_env = dict(os.environ)
    sub_env["DATABASE_URL"] = test_db_url

    proc = await _asyncio.create_subprocess_exec(
        _sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        cwd=backend_dir,
        env=sub_env,
        stdout=_asyncio.subprocess.PIPE,
        stderr=_asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed during test schema provisioning:\n"
            + out.decode("utf-8", errors="replace")
        )
    _log.info("CI test schema provisioned (pg_trgm + alembic upgrade head).")
    yield


# ── Reference-seed presence gate (BE-SEED-1) ─────────────────────────────────
# LIFTED into conftest (CI Gate-4 pass-3, §2.3): the seed-absence helper +
# skip reason were authored in ``tests/test_database.py`` (pass-2, for the 4
# ``test_seeded_*`` tests).  Pass-3 extends the same skip to the 4 category-seed
# integration tests (tests/modules/category/*) + ``test_is_advanced_flag_set_for_group_id``,
# all of which assert against the PROD reference seed (3772 categories / 49259
# field_enum_values / 3566 templates / 67 aliases loaded by the DATABASE-track
# seed scripts) that CI's schema-only ``meesell_test`` never loads.  Lifting the
# helper here lets BOTH test_database.py and the category seed tests import it
# from a single source of truth.  Tracked: BE-SEED-1 (CI-scoped seed fixture or
# nightly-only seeded data gate).
_SEED_SKIP_REASON = (
    "Reference seed data absent (CI meesell_test is schema-only, no prod data "
    "seed). Tracked: BE-SEED-1."
)


async def _seed_data_absent(conn) -> bool:
    """True when the PROD reference seed is absent → schema-only DB (CI).

    SIGNAL CHOICE (CI Gate-4 pass-2 deviation, carried forward — FLAGGED): the
    spec specified ``COUNT(categories) == 0`` as the gate.  Route-level fixtures
    (customer_client / iam_client / category flows) COMMIT a handful of
    ``categories`` rows into the shared ``meesell_test`` db, so by the time the
    read-only seeded tests run ``categories`` is non-empty (typically 1) even
    though the PROD seed is absent — which would defeat a literal
    ``categories == 0`` gate.  ``field_enum_values`` is the pollution-robust
    equivalent: it is populated ONLY by the 49 259-row DATABASE-track enum seed
    and by NO test fixture (verified 0 after a full integration run).  An empty
    ``field_enum_values`` is therefore the unambiguous "no prod seed" signal
    that survives committing-fixture residue.  Honours the spec INTENT (skip
    when the prod seed is absent) where the literal categories gate cannot.

    Accepts either a raw asyncpg-style connection or a SQLAlchemy async
    connection (callers pass ``dev_engine.connect()`` results).
    """
    result = await conn.execute(text("SELECT COUNT(*) FROM field_enum_values"))
    return result.scalar_one() == 0


@pytest_asyncio.fixture(loop_scope="function")
async def db_engine():
    """Engine for the ``client`` / ``db_session`` fixtures.

    Two modes, selected by ``TEST_DATABASE_URL`` presence:

    * CI / provisioned mode (``TEST_DATABASE_URL`` set):
      the schema is OWNED by the session-scoped ``_provision_test_schema``
      fixture (``alembic upgrade head`` — incl. the pg_trgm GIN indexes that
      ``create_all`` cannot build).  This fixture therefore does NOT
      drop_all / create_all.  Doing so would (a) destroy the GIN indexes the
      integration tests rely on, and (b) DEADLOCK with the function-scoped
      ``db`` fixture: ``db`` holds an open ``BEGIN`` transaction on the SAME
      meesell_test DB while this fixture's teardown ``DROP TABLE`` blocks on
      ``db``'s relation locks (both fixtures now resolve to the same DB once
      ``_DEV_DATABASE_URL`` honours ``TEST_DATABASE_URL``).  Per-test isolation
      in this mode is provided by the ``db`` fixture's ROLLBACK and by the
      integration suites' own DELETE-by-prefix / self-seeding cleanup.

    * Local-dev mode (no ``TEST_DATABASE_URL``):
      byte-for-byte the prior behaviour — drop_all + create_all an ephemeral
      schema on ``DATABASE_URL`` (the bare dev Postgres) and drop_all on
      teardown.  ``db`` resolves to a DIFFERENT physical DB (the K3s dev DSN)
      in this mode, so there is no cross-fixture lock contention.
    """
    provisioned = bool(os.environ.get("TEST_DATABASE_URL"))
    # NullPool: do NOT reuse connections across awaits.  asyncpg Protocols (and
    # their Futures) attach to whatever event loop is running when a connection
    # is first established; a pooled connection built in one loop and reused
    # from a function-scoped loop raises "Task got Future attached to a
    # different loop".  NullPool + loop_scope="function" keeps every connection
    # born and closed in the test's own loop (mirrors the ``db`` fixture).
    engine = create_async_engine(
        os.environ["DATABASE_URL"], poolclass=NullPool, pool_pre_ping=True
    )
    if not provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    yield engine
    if not provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db_session(db_engine):
    """Per-test async session with connection-outer-transaction + ROLLBACK.

    CI Gate-4 pass-3 (Class B crux): the previous body yielded a PLAIN session
    (``async with Session() as session: yield session``) with NO per-test
    transaction + rollback.  In NON-provisioned (laptop) mode the ``db_engine``
    fixture's per-test ``drop_all``/``create_all`` masked the gap; but pass-1
    made ``db_engine`` provision-aware (it SKIPS the schema reset on the shared
    CI ``meesell_test`` db), so in provisioned (CI) mode there was ZERO per-test
    isolation: any row a test committed accumulated session-wide with nothing
    cleaning it → fixed-phone module fixtures (``user`` with a hard-coded
    ``+91…`` number) collided on ``ix_users_phone`` / ``products_user_id_fkey``
    (the 14 ``IntegrityError`` class).

    The fix mirrors the (correctly-isolated) ``db`` fixture below in shape:
    open a single connection on the (provision-aware) ``db_engine``, BEGIN an
    outer transaction, bind a session to that connection (in SAVEPOINT mode so
    in-test ``commit()`` calls release a savepoint instead of ending the outer
    txn), yield it, then ROLLBACK the outer transaction on teardown so every row
    the test wrote is discarded.  ``loop_scope="function"`` (inherited on the
    decorator) keeps the connection + its asyncpg Futures bound to the test's own
    loop.

    CROSS-CONNECTION VISIBILITY (CI Gate-4 pass-3): several integration tests
    (image upload→precheck, etc.) write through this session, ``commit()``, then
    read the row back through a SEPARATE worker session built from a
    MODULE-BOUND ``AsyncSessionLocal`` (e.g. ``app.modules.image.tasks`` binds
    the name at import time and opens ``async with AsyncSessionLocal() as
    session`` inside the precheck pipeline).  Under a plain outer-txn-rollback
    the worker's OWN connection cannot see the test's uncommitted-to-outer-txn
    writes → "image not found".  To keep those tests green WITHOUT sacrificing
    per-test rollback isolation, we REBIND every module-bound ``AsyncSessionLocal``
    (the 5 worker-style consumers) to a savepoint-mode sessionmaker on the SAME
    shared connection for the test's duration — the worker therefore joins the
    test's transaction (sees its committed-to-savepoint writes); the single
    outer ROLLBACK at teardown discards everything the test AND the worker wrote.
    All rebinds are save/restored so no state leaks across tests.  This mirrors
    the route-client ``audit_mw.AsyncSessionLocal`` savepoint rebind (§2.2-ii).

    KNOWN RESIDUAL (FLAGGED): ``test_pricing_persistence::test_get_last_calc``
    asserts on distinct ``created_at`` from a fresh transaction's ``NOW()`` per
    commit; savepoints share the outer transaction's clock, so that one test
    cannot pass under any single-transaction isolation (it was ALREADY red —
    IntegrityError — before pass-3, so this is red-to-red, not a regression).

    GUARD (local-dev no-regression): in NON-provisioned mode this still operates
    on the ephemeral schema ``db_engine`` built for the test and rolls it back —
    behaviourally equivalent for local dev; the live dev DB is never mutated.
    """
    # The worker-style modules that bind ``AsyncSessionLocal`` at import time
    # (so a patch of ``app.shared.database.AsyncSessionLocal`` alone would NOT
    # reach the already-bound name).  Rebinding each module attribute makes the
    # worker sessions join the test connection.
    import importlib

    _WORKER_SESSIONLOCAL_MODULES = (
        "app.modules.image.tasks",
        "app.modules.export.tasks",
        "app.modules.iam.service",
        "app.ai_ops.cost_tracker",
        "app.core.middleware.audit_mw",
    )

    async with db_engine.connect() as conn:
        await conn.begin()
        Session = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        _saved: list[tuple] = []
        for _modname in _WORKER_SESSIONLOCAL_MODULES:
            try:
                _mod = importlib.import_module(_modname)
            except Exception:  # noqa: BLE001
                continue
            if hasattr(_mod, "AsyncSessionLocal"):
                _saved.append((_mod, _mod.AsyncSessionLocal))
                _mod.AsyncSessionLocal = Session  # type: ignore[attr-defined]
        session = Session()
        try:
            yield session
        finally:
            await session.close()
            for _mod, _orig in _saved:
                _mod.AsyncSessionLocal = _orig  # type: ignore[attr-defined]
            await conn.rollback()


@pytest_asyncio.fixture(loop_scope="function")
async def client(db_engine):
    if app is None:
        pytest.skip(
            f"app.main could not be imported (legacy router import error): {_APP_IMPORT_ERROR}"
        )
    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # Drive lifespan manually so app.state.valkey is set up.
        async with app.router.lifespan_context(app):
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client, use_live_valkey):
    """Authenticated test client per §7 iam FE-D5 contract.

    Bypasses /otp/send (avoids MSG91 vendor call) by pre-seeding the OTP
    record into Valkey DB 0 directly, then calls /otp/verify and pins the
    returned ``access_token`` as Bearer on every subsequent request.
    """
    import hashlib
    import json as _json
    import time as _time

    from app.shared import valkey as _vk_mod

    phone = "+919876543210"
    otp = "999000"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = _json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(_time.time()) + 300}
    )
    valkey = await _vk_mod.get_valkey_otp()
    await valkey.set(f"otp:{phone}", payload, ex=300)

    resp = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    body = resp.json()
    client.headers["Authorization"] = f"Bearer {body['access_token']}"
    # Resolve user_id via /me so tests can assert ownership without leaking JWT.
    me_resp = await client.get("/api/v1/auth/me")
    client.test_user_id = me_resp.json()["user_id"]  # type: ignore[attr-defined]
    return client


# ── §4 core/ fixtures ─────────────────────────────────────────────────────────
# ``use_live_valkey`` replaces the ``shared.valkey`` factory functions with
# per-test factories that create a FRESH Redis client IN THE CURRENT EVENT
# LOOP on every call.  The substitution is performed via ``monkeypatch`` —
# automatically reverted by pytest on teardown.  No module-level singleton
# survives the test, so a session-loop-bound client from an earlier test
# (e.g. ``test_database.py`` activating ``dev_engine`` in the session loop)
# can NEVER leak into a function-scoped test body.
#
# Why per-call fresh client (not pivot-the-singleton):
#   asyncpg / redis-py Protocols attach to whatever loop is running when the
#   first await on the connection happens.  If a singleton is built in the
#   session loop, awaiting it later from a function loop raises
#       RuntimeError: Task ... got Future ... attached to a different loop
#   By building each client inside the current (function-scoped) loop the
#   Future <-> loop attachment is always correct.
#
# Why monkeypatch the consumer modules too:
#   Every consumer in ``app/core/`` and the test modules themselves did
#   ``from app.shared.valkey import get_valkey_otp`` at import time, which
#   binds a LOCAL name in their own namespace.  Patching only
#   ``app.shared.valkey.get_valkey_otp`` would miss those captured refs.
#   We patch the name in every consumer namespace.

@pytest_asyncio.fixture(loop_scope="function")
async def use_live_valkey(monkeypatch):
    """Per-test live Redis at CORE_TEST_VALKEY_URL (default redis://localhost:6379).

    Monkeypatches ``get_valkey_otp`` / ``get_valkey_cache`` in ``app.shared.valkey``
    AND in every consumer module that captured the function by name at import
    time, to return a Redis client created IN THE CURRENT EVENT LOOP per call.
    No module singleton mutation survives — the patch is reverted by pytest's
    monkeypatch on teardown, guaranteeing zero cross-test loop pollution.
    Clients are ``aclose``d in teardown before the loop dies.
    """
    import redis.asyncio as _redis_lib  # local import — keeps top of conftest light
    import app.shared.valkey as _valkey_mod

    # Resolve base with TEST_VALKEY_URL > VALKEY_URL > CORE_TEST_VALKEY_URL >
    # default, stripping any trailing ``/<db>`` so the per-DB append below
    # never produces the ``/0/0`` double-suffix (see _valkey_base docstring).
    base = _valkey_base()
    created: list = []

    async def _otp():
        c = _redis_lib.from_url(f"{base}/0", decode_responses=True)
        created.append(c)
        return c

    async def _cache():
        c = _redis_lib.from_url(f"{base}/3", decode_responses=True)
        created.append(c)
        return c

    # 1. Patch the source module.
    monkeypatch.setattr(_valkey_mod, "get_valkey_otp", _otp)
    monkeypatch.setattr(_valkey_mod, "get_valkey_cache", _cache)

    # 2. Patch every consumer module that captured the function by name at
    #    import time (``from app.shared.valkey import get_valkey_*``).
    #    We import each consumer lazily so conftest module-load stays cheap
    #    and so a missing consumer (e.g. test runs without the middleware
    #    being importable) does not block the fixture.
    for mod_path, fn_name, factory in (
        ("app.core.cache", "get_valkey_cache", _cache),
        ("app.core.plan_guard", "get_valkey_otp", _otp),
        ("app.core.middleware.rate_limit_mw", "get_valkey_otp", _otp),
        ("app.core.middleware.audit_mw", "get_valkey_otp", _otp),
        # §7 iam router — captured ``get_valkey_otp`` at import time.
        ("app.modules.iam.router", "get_valkey_otp", _otp),
    ):
        try:
            mod = __import__(mod_path, fromlist=[fn_name])
        except Exception:
            continue
        if hasattr(mod, fn_name):
            monkeypatch.setattr(mod, fn_name, factory)

    # 3. Patch test modules that bound the same names at import time so
    #    helper calls inside the tests also see the fresh-per-call factory.
    #    pytest loads test files as TOP-LEVEL modules (bare ``test_core_cache``,
    #    not ``tests.test_core_cache``) when ``testpaths = tests`` is set
    #    without ``__init__.py`` packages — so look both up in sys.modules.
    import sys as _sys
    for mod_name, fn_name, factory in (
        ("test_core_cache", "get_valkey_cache", _cache),
        ("test_core_plan_guard", "get_valkey_otp", _otp),
    ):
        # Try both flat and dotted variants.
        for candidate in (mod_name, f"tests.{mod_name}"):
            mod = _sys.modules.get(candidate)
            if mod is not None and hasattr(mod, fn_name):
                monkeypatch.setattr(mod, fn_name, factory)

    # 4. Defensively NUKE any singleton that a previous test/session-scope
    #    fixture bound to a (potentially dead) loop.  We do NOT restore them
    #    — any future code path that bypasses the patched factory will
    #    re-create lazily, which still happens in a live loop.
    _valkey_mod._otp_client = None
    _valkey_mod._cache_client = None

    # 5. Pre-flush scratch DBs so each test sees a clean slate.
    pre_otp = await _otp()
    pre_cache = await _cache()
    try:
        await pre_otp.flushdb()
        await pre_cache.flushdb()
    except Exception:
        pass

    yield

    # 6. Teardown — flush + aclose every client created during the test.
    #    Run before the function loop dies; swallow errors to keep teardown
    #    robust if Valkey vanished mid-test.
    for c in created:
        try:
            await c.flushdb()
        except Exception:
            pass
        try:
            await c.aclose()
        except Exception:
            pass


# ── Phase 4 smoke-test fixtures ───────────────────────────────────────────────
# These fixtures hit the live dev Postgres (port-forwarded K3s instance).
# The `db` fixture wraps every test in a transaction that is ROLLED BACK on
# teardown — no test data ever persists to the shared dev DB.
#
# Architecture:
#   dev_engine (session scope)  — Used ONLY by seeded-data tests (section H)
#                                  for read-only queries.  Created in the
#                                  session event loop.
#   db         (function scope) — Creates its own NullPool engine, one
#                                  connection, one transaction.  Everything is
#                                  created and destroyed within the SAME
#                                  function-scoped event loop that pytest-asyncio
#                                  0.24 assigns to each test.  This avoids all
#                                  cross-loop Future attachment issues.
#
# Why per-test NullPool engine (not a session-scoped pool):
#   pytest-asyncio 0.24 with asyncio_default_fixture_loop_scope=session runs
#   SESSION-scoped fixtures in the session event loop, but FUNCTION-scoped
#   fixtures (and tests) each run in a freshly created function-scoped event
#   loop.  asyncpg Protocols (and their Futures) are attached to the loop that
#   is running when the connection is first established.  If a session-scoped
#   engine is used and its pool Protocols were created in the session loop, any
#   attempt to await them from a function-scoped loop raises:
#     RuntimeError: Task ... got Future ... attached to a different loop
#   The fix: create a fresh NullPool engine INSIDE the function-scoped `db`
#   fixture — the engine, connection, and all Futures are born in the same
#   function loop and disposed before that loop closes.
#
# Important: tests must use session.flush() not session.commit().  commit()
# would commit the transaction, defeating the rollback.


@pytest_asyncio.fixture(scope="session")
async def dev_engine():
    """Session-scoped engine for seeded-data tests (section H read-only queries).

    Uses NullPool to avoid asyncpg loop attachment issues: since section H
    tests are plain SELECT statements that don't write anything, there is no
    need for a transaction — each query opens/closes a connection atomically.
    """
    eng = create_async_engine(_DEV_DATABASE_URL, poolclass=NullPool, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="function")
async def db() -> AsyncSession:
    """Per-test async session with a fresh NullPool engine + ROLLBACK on teardown.

    Each test gets its own engine (NullPool), connection, and transaction.
    All engine/connection/Future objects are created and destroyed within the
    same function-scoped event loop.

    loop_scope="function" is set explicitly so that asyncpg Protocols, Futures,
    and Tasks are all attached to the same function-scoped event loop that
    pytest-asyncio 0.24 uses to run each test.  Without this, the session-scoped
    default loop (asyncio_default_fixture_loop_scope=session in pytest.ini) would
    create a loop-mismatch with the function-scoped loop used by the test runner.
    """
    eng = create_async_engine(_DEV_DATABASE_URL, poolclass=NullPool, echo=False)
    try:
        async with eng.connect() as conn:
            await conn.begin()
            Session = async_sessionmaker(
                bind=conn, expire_on_commit=False, class_=AsyncSession
            )
            session = Session()
            try:
                yield session
            finally:
                await session.close()
                await conn.rollback()
    finally:
        await eng.dispose()


# ── §19.D — pytest fixture posture (LOCKED 2026-06-06) ──────────────────────
#
# Per ``BACKEND_ARCHITECTURE.md`` §19.D the 6 fixtures consumed by per-module
# unit + integration tests are:
#
#   * ``db``                   — real Postgres via dev tunnel, per-test
#                                 ROLLBACK at teardown (DEFINED ABOVE).
#   * ``valkey``               — real Valkey via dev tunnel, per-test FLUSHDB
#                                 on DB 0 / 1 / 2 / 3 at teardown.
#   * ``mock_ai_ops_client``   — :class:`unittest.mock.AsyncMock` substituting
#                                 :func:`app.ai_ops.client.call_gemini` for
#                                 unit + integration tests. Real Gemini calls
#                                 are reserved for the ``ai_eval`` marker.
#   * ``mock_msg91_adapter``   — substitutes :func:`app.adapters.msg91.send_otp`
#                                 for OTP-related tests (no quota burn).
#   * ``mock_gcs_adapter``     — substitutes the 4 ``app.adapters.gcs.*`` async
#                                 surfaces with an in-memory bytes dict.
#   * ``mock_razorpay_adapter``— substitutes :func:`app.adapters.razorpay
#                                 .verify_webhook_signature` for webhook tests.
#
# Real-vs-mock policy (locked at §19.D): ``db`` + ``valkey`` are ALWAYS real
# in V1 (no SQLite, no fakeredis) — schema-fidelity bugs SQLite masks are too
# expensive to find at runtime. Adapter layer is ALWAYS mocked per-test
# except in the dedicated golden-fixture + AI-eval suites.


@pytest_asyncio.fixture(loop_scope="function")
async def valkey(use_live_valkey):
    """§19.D — real Valkey via dev tunnel, per-test FLUSHDB across all 4 DBs.

    Builds on :func:`use_live_valkey` (which already monkeypatches the
    ``app.shared.valkey`` factories to per-call clients in the function loop)
    and adds a teardown that flushes DB 0 + DB 1 + DB 2 + DB 3 to guarantee
    no test data leaks across tests.

    Yields a dict of pinned async clients (one per logical Valkey DB) so a
    test can inspect or seed any DB by name without re-deriving the URL::

        async def test_thing(valkey, db):
            await valkey["cache"].set("foo", "bar")
            await valkey["otp"].set(f"otp:+91XYZ", "...")

    Per-DB key (matches §1.B + §5.C + §15.C convention):
        * ``valkey["otp"]``     — DB 0 (OTP / rate-limit / session / refresh)
        * ``valkey["broker"]``  — DB 1 (Celery broker)
        * ``valkey["results"]`` — DB 2 (Celery result backend)
        * ``valkey["cache"]``   — DB 3 (app cache)

    Teardown order: FLUSHDB on each client → aclose each client. Errors are
    swallowed so the fixture survives Valkey-vanish-mid-test scenarios.
    """
    import redis.asyncio as _redis_lib

    # Same precedence + /0/0-guard as ``use_live_valkey`` (see _valkey_base).
    base = _valkey_base()
    clients: dict[str, "_redis_lib.Redis"] = {}
    for name, db_index in (("otp", 0), ("broker", 1), ("results", 2), ("cache", 3)):
        clients[name] = _redis_lib.from_url(
            f"{base}/{db_index}", decode_responses=True
        )

    try:
        # Pre-flush so the test sees a clean slate. Defensive — earlier tests
        # may have left keys behind despite their own teardown.
        for client in clients.values():
            try:
                await client.flushdb()
            except Exception:
                pass
        yield clients
    finally:
        for client in clients.values():
            try:
                await client.flushdb()
            except Exception:
                pass
            try:
                await client.aclose()
            except Exception:
                pass


@pytest_asyncio.fixture
async def mock_ai_ops_client(monkeypatch):
    """§19.D — AsyncMock substituting :func:`app.ai_ops.client.call_gemini`.

    Returns the :class:`unittest.mock.AsyncMock` so tests can assert on
    call shapes::

        async def test_autofill(mock_ai_ops_client):
            mock_ai_ops_client.return_value = {"name": "Red Kurti", ...}
            ...
            mock_ai_ops_client.assert_awaited_once()

    Default return value is an empty dict — tests override per scenario.

    The mock is installed BOTH on the source module (``app.ai_ops.client``)
    AND on every consumer module that imported ``call_gemini`` by name at
    module-load time (the §6A.A 3 AI-workload modules — category, catalog,
    image). Without the per-consumer patch the consumer's local binding
    would still call the real adapter.
    """
    from unittest.mock import AsyncMock

    mock = AsyncMock(return_value={})

    # Patch the source module first.
    import app.ai_ops.client as _client_mod
    monkeypatch.setattr(_client_mod, "call_gemini", mock)

    # Patch every known consumer per §6A.A. Imports that didn't capture the
    # symbol locally are silently skipped (lazy / module-not-built cases).
    for mod_path in (
        "app.modules.category.service",
        "app.modules.catalog.service",
        "app.modules.image.service",
        "app.modules.image.tasks",
    ):
        try:
            mod = __import__(mod_path, fromlist=["call_gemini"])
        except Exception:
            continue
        if hasattr(mod, "call_gemini"):
            monkeypatch.setattr(mod, "call_gemini", mock)

    return mock


@pytest_asyncio.fixture
async def mock_msg91_adapter(monkeypatch):
    """§19.D — substitute :func:`app.adapters.msg91.send_otp` with AsyncMock.

    Returns the mock so tests can assert call arguments. Default return value
    is a minimal :class:`app.adapters.msg91.Msg91Response`-compatible mapping
    so the OTP send path completes its happy path.

    Patches both ``app.adapters.msg91.send_otp`` AND every known consumer
    that bound the symbol at import time (per the §15.H + §7.B flow,
    primarily ``app.modules.iam.service`` + ``app.modules.iam.router``).
    """
    from unittest.mock import AsyncMock

    mock = AsyncMock(return_value={"type": "success", "message": "sent"})

    import app.adapters.msg91 as _msg91_mod
    monkeypatch.setattr(_msg91_mod, "send_otp", mock)

    for mod_path in (
        "app.modules.iam.service",
        "app.modules.iam.router",
    ):
        try:
            mod = __import__(mod_path, fromlist=["send_otp"])
        except Exception:
            continue
        if hasattr(mod, "send_otp"):
            monkeypatch.setattr(mod, "send_otp", mock)

    return mock


@pytest_asyncio.fixture
async def mock_gcs_adapter(monkeypatch):
    """§19.D — substitute the 4 ``app.adapters.gcs.*`` async surfaces.

    Backed by an in-memory ``dict[str, bytes]`` keyed by GCS path so write
    + read round-trip behaviour is preserved per test::

        async def test_export_pipeline(mock_gcs_adapter):
            # Write happens transparently — the stored bytes are inspectable:
            assert "meesell-exports/user-1/abc.xlsx" in mock_gcs_adapter.storage

    Returns the fixture object itself with attributes:

      * ``.storage``  — ``dict[str, bytes]`` of uploaded objects
      * ``.upload_bytes`` / ``.download_bytes`` / ``.generate_signed_url``
        / ``.delete`` — the AsyncMocks patched onto :mod:`app.adapters.gcs`

    The signed-URL mock returns a deterministic placeholder so tests can
    assert URL shape without depending on real GCS signing.
    """
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    storage: dict[str, bytes] = {}

    async def _upload_bytes(path, data, content_type, *, bucket=None):
        storage[path] = bytes(data)
        return None

    async def _download_bytes(path, *, bucket=None):
        try:
            return storage[path]
        except KeyError as exc:
            raise FileNotFoundError(f"gcs mock: {path}") from exc

    async def _generate_signed_url(
        path, *, bucket=None, ttl_seconds=None, method="GET"
    ):
        return f"https://storage.googleapis.test/{bucket or 'mock'}/{path}?token=mock"

    async def _delete(path, *, bucket=None):
        storage.pop(path, None)

    import app.adapters.gcs as _gcs_mod

    upload_mock = AsyncMock(side_effect=_upload_bytes)
    download_mock = AsyncMock(side_effect=_download_bytes)
    sign_mock = AsyncMock(side_effect=_generate_signed_url)
    delete_mock = AsyncMock(side_effect=_delete)

    monkeypatch.setattr(_gcs_mod, "upload_bytes", upload_mock)
    monkeypatch.setattr(_gcs_mod, "download_bytes", download_mock)
    monkeypatch.setattr(_gcs_mod, "generate_signed_url", sign_mock)
    monkeypatch.setattr(_gcs_mod, "delete", delete_mock)

    # Patch consumers that captured the names at import time (image upload,
    # export pipeline, storage service).
    for mod_path, names in (
        ("app.modules.image.service",
         ("upload_bytes", "download_bytes", "generate_signed_url", "delete")),
        ("app.modules.image.tasks",
         ("upload_bytes", "download_bytes", "generate_signed_url", "delete")),
        ("app.modules.export.tasks",
         ("upload_bytes", "download_bytes", "generate_signed_url", "delete")),
        ("app.modules.export.service",
         ("upload_bytes", "download_bytes", "generate_signed_url", "delete")),
    ):
        try:
            mod = __import__(mod_path, fromlist=list(names))
        except Exception:
            continue
        for name in names:
            if hasattr(mod, name):
                target = {
                    "upload_bytes": upload_mock,
                    "download_bytes": download_mock,
                    "generate_signed_url": sign_mock,
                    "delete": delete_mock,
                }[name]
                monkeypatch.setattr(mod, name, target)

    return SimpleNamespace(
        storage=storage,
        upload_bytes=upload_mock,
        download_bytes=download_mock,
        generate_signed_url=sign_mock,
        delete=delete_mock,
    )


@pytest_asyncio.fixture
async def mock_razorpay_adapter(monkeypatch):
    """§19.D — substitute :func:`app.adapters.razorpay.verify_webhook_signature`.

    Returns a :class:`unittest.mock.MagicMock` so tests can pre-set the
    boolean return value per scenario (signature pass / signature fail).
    Default return is ``True`` — the happy path.
    """
    from unittest.mock import MagicMock

    mock = MagicMock(return_value=True)

    import app.adapters.razorpay as _rzp_mod
    monkeypatch.setattr(_rzp_mod, "verify_webhook_signature", mock)

    for mod_path in (
        "app.modules.iam.service",
        "app.modules.iam.router",
    ):
        try:
            mod = __import__(mod_path, fromlist=["verify_webhook_signature"])
        except Exception:
            continue
        if hasattr(mod, "verify_webhook_signature"):
            monkeypatch.setattr(mod, "verify_webhook_signature", mock)

    return mock
