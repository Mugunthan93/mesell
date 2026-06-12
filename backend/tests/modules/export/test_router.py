"""Route-level tests for §14 export endpoints.

9 tests covering the 2 route handlers per §14.B:
  POST /api/v1/products/{product_id}/export-xlsx
  GET  /api/v1/exports/{export_id}

Coverage matrix
---------------
1. test_post_export_xlsx_unauthenticated_returns_401
   — no JWT → 401.

2. test_post_export_xlsx_wrong_user_returns_404
   — product_id owned by another user → 404 (mocks
     export_service.initiate_export to raise ProductNotFoundError from
     catalog, which maps to 404 via §4.F handler).

3. test_post_export_xlsx_invalid_format_returns_422
   — request body ``format="garbage"`` → 422 (Pydantic Literal
     validation + ``extra="forbid"``; caught before service is called).

4. test_post_export_xlsx_happy_returns_202
   — mocks export_service.initiate_export to return a valid
     ExportInitiatedResponse → 202 + body shape matches.

5. test_get_export_unauthenticated_returns_401
   — no JWT → 401.

6. test_get_export_not_found_returns_404
   — mocks export_service.get_export to raise ExportNotFoundError → 404.

7. test_get_export_pending_returns_200
   — mocks service to return pending ExportResponse (no signed URLs) → 200.

8. test_get_export_ready_returns_200_with_signed_urls
   — mocks service to return ready ExportResponse with xlsx_signed_url +
     zip_signed_url → 200.

9. test_get_export_failed_returns_200_with_error
   — mocks service to return failed ExportResponse with error_code +
     error_message → 200.

Test strategy
-------------
All tests use ASGI transport against the real ``app.main.app``.  The
service module is monkeypatched at the module-attribute level so the
router logic is exercised end-to-end (auth → route dispatch → mocked
service call → response serialisation).

The fixture pattern follows ``test_customer_routes.py`` (§8 precedent):
a self-contained ``export_client`` fixture creates an ephemeral DB schema,
overrides FastAPI dependencies (get_db + get_valkey_otp), patches
module-level singletons that bypass DI (audit_mw.AsyncSessionLocal +
shared.valkey._cache_client), seeds an OTP in test Valkey DB 0, and
obtains a Bearer token via /otp/verify.  Valkey must be reachable at
``CORE_TEST_VALKEY_URL`` (default ``redis://localhost:6379``).

Unauthenticated tests use a bare ``AsyncClient`` with no Authorization
header (no fixtures that need Valkey).  Auth middleware rejects them
before any service is called.

M10 enforcement (§14.J)
-----------------------
``meesho_column_header``, ``meesho_column_index``, and ``enum_codes_map``
MUST NOT appear anywhere in this test file.
"""

from __future__ import annotations

import datetime
import hashlib
import json as _json
import os
import time as _time
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
import redis.asyncio as _redis_lib

pytestmark = pytest.mark.integration
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.modules.export.service as _export_service_mod
from app.main import app
# CI Gate-4 pass-3 (§2.1): port the pass-2 customer_client DB/Valkey precedence
# helpers to export_client (kills the 3 pre-pass-2 defects: hardcoded
# localhost:5432, hardcoded redis://localhost:6379, non-provision-aware drop_all).
from tests.conftest import _DEV_DATABASE_URL, _valkey_base
from app.modules.catalog.exceptions import ProductNotFoundError
from app.modules.export.exceptions import ExportNotFoundError
from app.modules.export.schemas import (
    ExportInitiatedResponse,
    ExportResponse,
)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
_EXPORT_TEST_PHONE = "+915550014001"
_EXPORT_TEST_OTP = "777000"

_NOW = datetime.datetime(2026, 6, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
_PRODUCT_ID = uuid4()
_EXPORT_ID = uuid4()
_TASK_ID = "celery-task-export-abc123"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — stub service responses
# ─────────────────────────────────────────────────────────────────────────────
def _make_initiated_response() -> ExportInitiatedResponse:
    return ExportInitiatedResponse(
        export_id=_EXPORT_ID,
        status="pending",
        enqueued_task_id=_TASK_ID,
        initiated_at=_NOW,
    )


def _make_export_response(
    status: str = "pending",
    *,
    xlsx_signed_url: str | None = None,
    zip_signed_url: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    round_trip_validated: bool | None = None,
) -> ExportResponse:
    return ExportResponse(
        export_id=_EXPORT_ID,
        product_id=_PRODUCT_ID,
        status=status,  # type: ignore[arg-type]
        format="xlsx_with_images",
        xlsx_signed_url=xlsx_signed_url,
        zip_signed_url=zip_signed_url,
        error_code=error_code,
        error_message=error_message,
        initiated_at=_NOW,
        completed_at=None,
        round_trip_validated=round_trip_validated,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: export_client — authenticated ASGI client (self-contained)
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def export_client():
    """Authenticated ASGI client for export route tests.

    Self-contained: creates an ephemeral DB schema (off-CI) / reuses the
    alembic-provisioned schema (CI), overrides FastAPI dependencies
    (get_db + get_valkey_otp) with SAVEPOINT-isolated sessions, patches
    module-level singletons (audit_mw.AsyncSessionLocal + shared.valkey
    ._cache_client), seeds an OTP, and obtains a Bearer token via /otp/verify.

    CI Gate-4 pass-3 (§2.1 + §2.2): a STRUCTURAL TWIN of the pass-2 customer_client.
    Three pre-pass-2 defects fixed here:
      * DB URL  → ``_DEV_DATABASE_URL`` (was hardcoded localhost:5432 default).
      * Valkey  → ``_valkey_base()``    (was hardcoded redis://localhost:6379).
      * schema  → provision-aware drop_all/create_all (was unconditional → wiped
                  the alembic-built pg_trgm GIN indexes + deadlocked the shared
                  meesell_test in CI).
    Plus ``loop_scope="function"`` (clears the 7 ``BaseHTTPMiddleware … Future
    attached to a different loop`` errors) and the SAVEPOINT per-test isolation
    (single shared connection + open outer txn + ``join_transaction_mode=
    "create_savepoint"`` so handler commits release savepoints; outer rollback at
    teardown leaves meesell_test byte-clean).
    """
    import app.core.middleware.audit_mw as _audit_mw
    import app.shared.valkey as _valkey_module
    from app.shared.database import Base, get_db
    from app.shared.valkey import get_valkey_otp

    db_url = _DEV_DATABASE_URL
    engine: AsyncEngine = create_async_engine(db_url, poolclass=NullPool)

    _provisioned = bool(os.environ.get("TEST_DATABASE_URL"))
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    # SAVEPOINT per-test isolation (§2.2-ii) — single shared connection, open
    # outer transaction, savepoint-mode sessionmaker (see customer_client for
    # the full rationale).  The export route handlers mock the service layer so
    # most tests do not persist, but the /otp/verify Bearer mint DOES commit a
    # ``users`` row — without the outer rollback that row leaks and the fixed
    # export phone collides on ``ix_users_phone`` across tests.
    shared_conn = await engine.connect()
    outer_txn = await shared_conn.begin()
    TestSession = async_sessionmaker(
        bind=shared_conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    valkey_base = _valkey_base()

    _otp_clients: list = []

    async def _otp_override():
        c = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
        _otp_clients.append(c)
        return c

    async def _db_override():
        # Bind to the shared savepoint connection; do NOT close it here.
        session = TestSession()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    app.dependency_overrides[get_valkey_otp] = _otp_override
    app.dependency_overrides[get_db] = _db_override

    # Patch audit_mw (uses AsyncSessionLocal directly, not via Depends).
    _original_audit_session_local = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = TestSession  # type: ignore[attr-defined]

    # Patch cache singleton so core/cache.py can reach test Valkey.
    _original_cache_client = _valkey_module._cache_client
    _test_cache_client = _redis_lib.from_url(f"{valkey_base}/3", decode_responses=True)
    _valkey_module._cache_client = _test_cache_client  # type: ignore[assignment]

    # D2 fix (Gate-4 repair-1): rate_limit_mw calls get_valkey_otp() as a
    # plain function call — NOT through FastAPI DI — so the DI override above
    # has no effect on it.  After test N's function loop closes, the stale
    # _otp_client StreamWriter's transport._loop is closed; test N+1's fixture
    # setup triggers a pipeline call that does loop.call_soon() on that closed
    # loop → RuntimeError: Event loop is closed (4 of the 13 teardown errors).
    # Same fix as customer_client (3c) and iam_client (4c).
    _original_otp_client = _valkey_module._otp_client
    _test_otp_client_singleton = _redis_lib.from_url(
        f"{valkey_base}/0", decode_responses=True
    )
    _valkey_module._otp_client = _test_otp_client_singleton  # type: ignore[assignment]

    # Seed OTP in test Valkey DB 0.
    otp_seed_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    try:
        await otp_seed_client.flushdb()
    except Exception:
        pass

    otp_hash = hashlib.sha256(_EXPORT_TEST_OTP.encode("utf-8")).hexdigest()
    otp_payload = _json.dumps(
        {
            "otp_hash": otp_hash,
            "attempts": 0,
            "expires_at": int(_time.time()) + 300,
        }
    )
    await otp_seed_client.set(f"otp:{_EXPORT_TEST_PHONE}", otp_payload, ex=300)

    # Track the lifespan-created engine + Valkey client so we can explicitly
    # dispose/close them AFTER the lifespan exits — prevents
    # ``Event loop is closed`` teardown errors (same fix as customer_client).
    _lifespan_db_engine = None
    _lifespan_valkey = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            _lifespan_db_engine = getattr(app.state, "db_engine", None)
            _lifespan_valkey = getattr(app.state, "valkey", None)
            # Obtain Bearer token via /otp/verify.
            resp = await ac.post(
                "/api/v1/auth/otp/verify",
                json={"phone": _EXPORT_TEST_PHONE, "otp": _EXPORT_TEST_OTP},
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"export_client fixture: /otp/verify failed "
                    f"({resp.status_code}): {resp.text}"
                )
            body = resp.json()
            ac.headers["Authorization"] = f"Bearer {body['access_token']}"
            yield ac

        # Lifespan has exited — explicitly dispose residual pool connections
        # while still in the function loop (prevents ``Event loop is closed``).
        if _lifespan_db_engine is not None:
            try:
                await _lifespan_db_engine.dispose()
            except Exception:
                pass
        if _lifespan_valkey is not None:
            try:
                await _lifespan_valkey.aclose()
            except Exception:
                pass

    # Teardown.
    app.dependency_overrides.clear()
    _audit_mw.AsyncSessionLocal = _original_audit_session_local
    _valkey_module._cache_client = _original_cache_client
    _valkey_module._otp_client = _original_otp_client  # type: ignore[assignment]

    for c in _otp_clients + [otp_seed_client, _test_cache_client, _test_otp_client_singleton]:
        try:
            await c.aclose()
        except Exception:
            pass

    # SAVEPOINT teardown (§2.2): roll back the outer txn (discards the committed
    # users row + any savepoint releases) → meesell_test left byte-clean.
    try:
        await outer_txn.rollback()
    except Exception:
        pass
    try:
        await shared_conn.close()
    except Exception:
        pass

    # Provision-aware schema teardown (mirrors customer_client): only drop the
    # ephemeral schema off-CI; never wipe the alembic-owned CI schema.
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: unauth_client — unauthenticated ASGI client (no Bearer)
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def unauth_client():
    """Bare ASGI client with no Authorization header.

    Requests are rejected before any service call (auth middleware sets
    request.state.user = None; get_current_user raises 401 inside the route).
    However, rate_limit_mw DOES run before auth rejection and calls
    get_valkey_otp() as a plain function — NOT via FastAPI DI.

    D2 fix (Gate-4 repair-1): patch _valkey_module._otp_client to a fresh
    function-loop-bound client so that rate_limit_mw never uses a stale
    client from a previous test's (now-closed) event loop.  Without this,
    if a previous test's export_client or another unauth_client initialized
    _otp_client in its own loop, this test's rate_limit_mw call would
    trigger loop.call_soon() on the closed loop →
    RuntimeError: Event loop is closed.  See D2 rationale in export_client
    and integration/conftest.py iam_client for the full explanation.

    CI Gate-4 pass-3 (§2.1): ``loop_scope="function"`` added so the ASGI app /
    middleware Futures bind to the test's own loop (clears the
    ``BaseHTTPMiddleware … Future attached to a different loop`` error).
    """
    import app.shared.valkey as _valkey_module
    from tests.conftest import _valkey_base

    valkey_base = _valkey_base()
    _original_otp_client = _valkey_module._otp_client
    _test_otp_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    _valkey_module._otp_client = _test_otp_client  # type: ignore[assignment]

    _lifespan_db_engine = None
    _lifespan_valkey = None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                _lifespan_db_engine = getattr(app.state, "db_engine", None)
                _lifespan_valkey = getattr(app.state, "valkey", None)
                yield ac

            # Explicit disposal to drain pending pool callbacks before loop teardown.
            if _lifespan_db_engine is not None:
                try:
                    await _lifespan_db_engine.dispose()
                except Exception:
                    pass
            if _lifespan_valkey is not None:
                try:
                    await _lifespan_valkey.aclose()
                except Exception:
                    pass
    finally:
        _valkey_module._otp_client = _original_otp_client  # type: ignore[assignment]
        try:
            await _test_otp_client.aclose()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST export-xlsx — unauthenticated → 401
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_post_export_xlsx_unauthenticated_returns_401(unauth_client):
    """No Authorization header → 401.

    ``AuthContextMiddleware`` sets ``request.state.user = None``;
    ``get_current_user`` raises ``TokenMissingError`` (401).
    The route handler and the service are never reached.
    """
    resp = await unauth_client.post(
        f"/api/v1/products/{_PRODUCT_ID}/export-xlsx",
        json={"format": "xlsx_with_images"},
    )
    assert resp.status_code == 401, (
        f"Expected 401 (no JWT), got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST export-xlsx — wrong user → 404
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_post_export_xlsx_wrong_user_returns_404(
    export_client,
    monkeypatch,
):
    """Service raises ProductNotFoundError (catalog ownership gate) → 404.

    The catalog cross-module call (assert_product_ownership) raises
    ``catalog.exceptions.ProductNotFoundError`` (status_code=404).
    Per §1.E privacy posture: product not found AND cross-tenant both
    surface as the same 404 — no ownership signal to the attacker.
    """
    async def _raises(*args: Any, **kwargs: Any) -> None:
        raise ProductNotFoundError()

    monkeypatch.setattr(_export_service_mod, "initiate_export", _raises)

    resp = await export_client.post(
        f"/api/v1/products/{uuid4()}/export-xlsx",
        json={"format": "xlsx_with_images"},
    )
    assert resp.status_code == 404, (
        f"Expected 404 (product not found / wrong user), "
        f"got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. POST export-xlsx — invalid format → 422
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_post_export_xlsx_invalid_format_returns_422(
    export_client,
    monkeypatch,
):
    """``format='garbage'`` fails Pydantic ``Literal`` validation → 422.

    ``ExportRequest`` declares ``format: Literal["xlsx_only", "xlsx_with_images"]``
    with ``extra="forbid"``.  Pydantic v2 rejects the invalid literal value
    before the route handler body runs (FastAPI returns 422 from the
    RequestValidationError handler per §4.F).
    """
    async def _should_not_be_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "Service must NOT be called when request body is invalid."
        )

    monkeypatch.setattr(_export_service_mod, "initiate_export", _should_not_be_called)

    resp = await export_client.post(
        f"/api/v1/products/{_PRODUCT_ID}/export-xlsx",
        json={"format": "garbage"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 (invalid format literal), got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. POST export-xlsx — happy path → 202
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_post_export_xlsx_happy_returns_202(
    export_client,
    monkeypatch,
):
    """Mocked service returns ``ExportInitiatedResponse`` → 202 + body shape.

    Asserts:
    - HTTP status 202 ACCEPTED.
    - Response JSON contains ``export_id``, ``status='pending'``,
      ``enqueued_task_id``, and ``initiated_at``.
    - M10: no ``meesho_column_header`` / ``meesho_column_index`` in body.
    """
    initiated = _make_initiated_response()

    async def _stub(*args: Any, **kwargs: Any) -> ExportInitiatedResponse:
        return initiated

    monkeypatch.setattr(_export_service_mod, "initiate_export", _stub)

    resp = await export_client.post(
        f"/api/v1/products/{_PRODUCT_ID}/export-xlsx",
        json={"format": "xlsx_with_images"},
    )
    assert resp.status_code == 202, (
        f"Expected 202 ACCEPTED, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body["export_id"] == str(_EXPORT_ID)
    assert body["status"] == "pending"
    assert body["enqueued_task_id"] == _TASK_ID
    assert "initiated_at" in body
    # M10 enforcement: forbidden symbols must not appear in wire response.
    body_str = _json.dumps(body)
    assert "meesho_column_header" not in body_str
    assert "meesho_column_index" not in body_str
    assert "enum_codes_map" not in body_str


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET export — unauthenticated → 401
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_export_unauthenticated_returns_401(unauth_client):
    """No Authorization header → 401."""
    resp = await unauth_client.get(f"/api/v1/exports/{_EXPORT_ID}")
    assert resp.status_code == 401, (
        f"Expected 401 (no JWT), got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. GET export — not found → 404
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_export_not_found_returns_404(
    export_client,
    monkeypatch,
):
    """Service raises ``ExportNotFoundError`` → 404.

    The repository's ``scope_to_user`` filter conflates non-existent AND
    cross-tenant into the same 404 per §4.C privacy posture.
    """
    async def _raises(*args: Any, **kwargs: Any) -> None:
        raise ExportNotFoundError()

    monkeypatch.setattr(_export_service_mod, "get_export", _raises)

    resp = await export_client.get(f"/api/v1/exports/{uuid4()}")
    assert resp.status_code == 404, (
        f"Expected 404 (export not found), got {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. GET export — pending → 200 (no signed URLs)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_export_pending_returns_200(
    export_client,
    monkeypatch,
):
    """``status='pending'`` export returns 200 with null signed URLs.

    Per §14.B.2: signed URLs are only generated when ``status='ready'``.
    A pending poll response carries ``xlsx_signed_url=null``,
    ``zip_signed_url=null``, ``error_code=null``, and
    ``round_trip_validated=null``.
    """
    pending = _make_export_response(status="pending")

    async def _stub(*args: Any, **kwargs: Any) -> ExportResponse:
        return pending

    monkeypatch.setattr(_export_service_mod, "get_export", _stub)

    resp = await export_client.get(f"/api/v1/exports/{_EXPORT_ID}")
    assert resp.status_code == 200, (
        f"Expected 200 (pending), got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body["status"] == "pending"
    assert body["xlsx_signed_url"] is None
    assert body["zip_signed_url"] is None
    assert body["error_code"] is None
    assert body["error_message"] is None
    assert body["round_trip_validated"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 8. GET export — ready → 200 with signed URLs
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_export_ready_returns_200_with_signed_urls(
    export_client,
    monkeypatch,
):
    """``status='ready'`` export returns 200 with populated signed URLs.

    Per §14.B.2: ``xlsx_signed_url`` and ``zip_signed_url`` (for
    ``xlsx_with_images`` format) are fresh GCS signed URLs (1h TTL).
    ``round_trip_validated=True`` invariant holds per ``MVP_ARCH §5.7``.
    """
    ready = _make_export_response(
        status="ready",
        xlsx_signed_url="https://storage.googleapis.com/test/sheet.xlsx?signed=1",
        zip_signed_url="https://storage.googleapis.com/test/images.zip?signed=1",
        round_trip_validated=True,
    )

    async def _stub(*args: Any, **kwargs: Any) -> ExportResponse:
        return ready

    monkeypatch.setattr(_export_service_mod, "get_export", _stub)

    resp = await export_client.get(f"/api/v1/exports/{_EXPORT_ID}")
    assert resp.status_code == 200, (
        f"Expected 200 (ready), got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body["status"] == "ready"
    assert body["xlsx_signed_url"] is not None
    assert "storage.googleapis.com" in body["xlsx_signed_url"]
    assert body["zip_signed_url"] is not None
    assert "storage.googleapis.com" in body["zip_signed_url"]
    assert body["round_trip_validated"] is True
    assert body["error_code"] is None
    assert body["error_message"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 9. GET export — failed → 200 with error fields
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_export_failed_returns_200_with_error(
    export_client,
    monkeypatch,
):
    """``status='failed'`` export returns 200 with ``error_code`` + ``error_message``.

    Per §14.B.2: failed exports surface ``error_code`` (one of the 7 codes
    per §14.H) and a human-readable ``error_message``.  The HTTP status is
    200 — the pipeline failure is a business-domain state, not a protocol
    error.  The client renders a retry CTA.
    """
    failed = _make_export_response(
        status="failed",
        error_code="enum_validation_failed",
        error_message=(
            "Export failed: an invalid value was detected. Please re-run the export."
        ),
    )

    async def _stub(*args: Any, **kwargs: Any) -> ExportResponse:
        return failed

    monkeypatch.setattr(_export_service_mod, "get_export", _stub)

    resp = await export_client.get(f"/api/v1/exports/{_EXPORT_ID}")
    assert resp.status_code == 200, (
        f"Expected 200 (failed business status), got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error_code"] == "enum_validation_failed"
    assert body["error_message"] is not None
    assert "re-run" in body["error_message"]
    assert body["xlsx_signed_url"] is None
    assert body["zip_signed_url"] is None
    assert body["round_trip_validated"] is None
