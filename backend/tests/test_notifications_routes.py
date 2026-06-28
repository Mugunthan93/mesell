"""Route-level tests for the monitor notifications endpoint (Wave-4 Unit N).

``GET /api/v1/notifications`` — ``FEATURE_CATEGORY_MONITOR_ENABLED`` flag-gated.

Coverage matrix
---------------
1. **Tenancy** — user A's token returns ONLY user A's notifications; user B's
   rows are NEVER returned.
2. **401** — missing Bearer token → 401.
3. **Envelope** — ``{data, total, page, unread_count}`` shape correct; items are
   ``NotificationItem`` shaped; order is ``created_at DESC``.
4. **unread_only** — ``?unread_only=true`` filters to ``is_read=false`` rows only.
5. **Pagination** — ``?page=2&limit=1`` returns the second-oldest row (DESC order).
6. **unread_count** — always reflects the full unread count across ALL pages.
7. **Flag-gate (OFF → 404 absent)** — route count pin at 34 (google-auth off) or
   35 (google-auth on); ``GET /api/v1/notifications`` absent from route map.
8. **Flag-gate (ON → present)** — route count pin at 35 or 36; route present.

Database usage
--------------
Disposable ``meesell_test`` DB only — NEVER the live ``meesell`` DB (3772 cats).
The fixture chain inserts two users + notification rows under the guard that
``DATABASE_URL`` ends in ``_test``.
"""

from __future__ import annotations

import hashlib
import json as _json
import time as _time
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
import redis.asyncio as _redis_lib
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.routing import Route

from app.main import app
from tests.conftest import _DEV_DATABASE_URL, _valkey_base

pytestmark = pytest.mark.integration

# ── Non-routable test phones (safe synthetic range) ──────────────────────────
_PHONE_A = "+915550099911"
_PHONE_B = "+915550099912"
_OTP_A = "991991"
_OTP_B = "992992"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _route_map(test_app: FastAPI) -> dict[str, set[str]]:
    """Return {path: {methods}} for all Route + APIRoute entries."""
    result: dict[str, set[str]] = {}
    for r in test_app.routes:
        if isinstance(r, (Route, APIRoute)):
            result[r.path] = set(r.methods or [])
    return result


def _otp_redis_payload(otp: str) -> str:
    otp_hash = hashlib.sha256(otp.encode()).hexdigest()
    return _json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(_time.time()) + 300}
    )


def _now_ts() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(loop_scope="function")
async def notifications_fixture():
    """Seed two users (A + B) + notification rows; yield two auth clients.

    Returns ``(client_a, client_b, token_a, token_b, notification_ids_a)``
    so tenancy tests can verify user A never sees user B's rows.

    Self-contained pattern (mirrors test_customer_routes.py):
    - NullPool ephemeral engine with SAVEPOINT isolation.
    - audit_mw.AsyncSessionLocal + shared.valkey singletons patched.
    - OTP seeded in test Valkey DB 0; tokens obtained via /otp/verify.
    - ROLLBACK on teardown → disposable DB is left clean.
    """
    import os

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

    shared_conn = await engine.connect()
    outer_txn = await shared_conn.begin()
    TestSession = async_sessionmaker(
        bind=shared_conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    valkey_base = _valkey_base()

    async def _otp_override():
        return _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)

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

    app.dependency_overrides[get_valkey_otp] = _otp_override
    app.dependency_overrides[get_db] = _db_override

    _original_audit = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = TestSession  # type: ignore[attr-defined]

    _original_cache = _valkey_module._cache_client
    _valkey_module._cache_client = _redis_lib.from_url(
        f"{valkey_base}/3", decode_responses=True
    )  # type: ignore[assignment]

    _original_otp_singleton = _valkey_module._otp_client
    _valkey_module._otp_client = _redis_lib.from_url(
        f"{valkey_base}/0", decode_responses=True
    )  # type: ignore[assignment]

    # ── Seed OTPs ──────────────────────────────────────────────────────────
    otp_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    try:
        await otp_client.flushdb()
    except Exception:
        pass
    await otp_client.set(f"otp:{_PHONE_A}", _otp_redis_payload(_OTP_A), ex=300)
    await otp_client.set(f"otp:{_PHONE_B}", _otp_redis_payload(_OTP_B), ex=300)
    await otp_client.aclose()

    # ── Enable the flag for these tests ────────────────────────────────────
    from app.shared.config import settings as _settings

    _orig_flag = _settings.FEATURE_CATEGORY_MONITOR_ENABLED
    _settings.FEATURE_CATEGORY_MONITOR_ENABLED = True

    _lifespan_db_engine = None
    _lifespan_valkey = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with app.router.lifespan_context(app):
            _lifespan_db_engine = getattr(app.state, "db_engine", None)
            _lifespan_valkey = getattr(app.state, "valkey", None)

            # Obtain tokens for both users via /otp/verify.
            resp_a = await client.post(
                "/api/v1/auth/otp/verify", json={"phone": _PHONE_A, "otp": _OTP_A}
            )
            assert resp_a.status_code == 200, f"user A verify failed: {resp_a.text}"
            token_a: str = resp_a.json()["access_token"]

            resp_b = await client.post(
                "/api/v1/auth/otp/verify", json={"phone": _PHONE_B, "otp": _OTP_B}
            )
            assert resp_b.status_code == 200, f"user B verify failed: {resp_b.text}"
            token_b: str = resp_b.json()["access_token"]

            # Resolve user IDs from /auth/me.
            me_a = (
                await client.get(
                    "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}
                )
            ).json()
            user_id_a = uuid.UUID(me_a["user_id"])

            me_b = (
                await client.get(
                    "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}
                )
            ).json()
            user_id_b = uuid.UUID(me_b["user_id"])

            # ── Seed notifications via direct DB insert ─────────────────────
            # We need a category row to satisfy the FK on notifications.category_id.
            # Insert a minimal category + template via raw sqlalchemy.
            from sqlalchemy import text

            cat_id = uuid.uuid4()
            tmpl_id = uuid.uuid4()

            async with TestSession() as s:
                # Template (FK dep for category)
                await s.execute(
                    text(
                        "INSERT INTO templates (id, schema_hash, schema_jsonb, parser_version) "
                        "VALUES (:id, :hash, :jsonb, :pv)"
                    ),
                    {
                        "id": str(tmpl_id),
                        "hash": "testhash001",
                        "jsonb": _json.dumps({}),
                        "pv": "n1.0",
                    },
                )
                # Category (FK dep for notification)
                await s.execute(
                    text(
                        "INSERT INTO categories "
                        "(id, meesho_leaf_id, leaf_name, super_id, super_name, path, template_id) "
                        "VALUES (:id, :mlid, :ln, :sid, :sn, :path, :tid)"
                    ),
                    {
                        "id": str(cat_id),
                        "mlid": "NR-001",
                        "ln": "Test Category",
                        "sid": "99",
                        "sn": "Test Super",
                        "path": "Test Super > Test Category",
                        "tid": str(tmpl_id),
                    },
                )
                # Notifications for user A (2 rows: one read, one unread).
                notif_a1_id = uuid.uuid4()
                notif_a2_id = uuid.uuid4()
                await s.execute(
                    text(
                        "INSERT INTO notifications "
                        "(id, user_id, category_id, content_hash, payload_jsonb, is_read, read_at, created_at) "
                        "VALUES (:id, :uid, :cid, :ch, :pay, false, NULL, :cat)"
                    ),
                    {
                        "id": str(notif_a1_id),
                        "uid": str(user_id_a),
                        "cid": str(cat_id),
                        "ch": "hash_a_unread_001",
                        "pay": _json.dumps({"summary": "First unread", "diff_dimensions": [], "affected_catalog_ids": []}),
                        "cat": "2026-06-22T10:00:00+00:00",
                    },
                )
                await s.execute(
                    text(
                        "INSERT INTO notifications "
                        "(id, user_id, category_id, content_hash, payload_jsonb, is_read, read_at, created_at) "
                        "VALUES (:id, :uid, :cid, :ch, :pay, true, :rat, :cat)"
                    ),
                    {
                        "id": str(notif_a2_id),
                        "uid": str(user_id_a),
                        "cid": str(cat_id),
                        "ch": "hash_a_read_002",
                        "pay": _json.dumps({"summary": "Second read", "diff_dimensions": [], "affected_catalog_ids": []}),
                        "rat": "2026-06-22T11:00:00+00:00",
                        "cat": "2026-06-22T09:00:00+00:00",
                    },
                )
                # Notification for user B (1 row — must NEVER appear in user A's response).
                notif_b1_id = uuid.uuid4()
                await s.execute(
                    text(
                        "INSERT INTO notifications "
                        "(id, user_id, category_id, content_hash, payload_jsonb, is_read, created_at) "
                        "VALUES (:id, :uid, :cid, :ch, :pay, false, :cat)"
                    ),
                    {
                        "id": str(notif_b1_id),
                        "uid": str(user_id_b),
                        "cid": str(cat_id),
                        "ch": "hash_b_unread_001",
                        "pay": _json.dumps({"summary": "B unread", "diff_dimensions": [], "affected_catalog_ids": []}),
                        "cat": "2026-06-22T12:00:00+00:00",
                    },
                )
                await s.commit()

            yield {
                "client": client,
                "token_a": token_a,
                "token_b": token_b,
                "user_id_a": user_id_a,
                "user_id_b": user_id_b,
                "notif_a1_id": notif_a1_id,  # unread, created 10:00
                "notif_a2_id": notif_a2_id,  # read, created 09:00
                "notif_b1_id": notif_b1_id,  # user B's notification
            }

        # ── Lifespan teardown (mirrors customer_client pattern) ──────────────
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

    # ── Singleton + dependency teardown ───────────────────────────────────────
    _settings.FEATURE_CATEGORY_MONITOR_ENABLED = _orig_flag

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_valkey_otp, None)

    _audit_mw.AsyncSessionLocal = _original_audit
    _valkey_module._cache_client = _original_cache  # type: ignore[assignment]
    _valkey_module._otp_client = _original_otp_singleton  # type: ignore[assignment]

    try:
        await outer_txn.rollback()
    except Exception:
        pass
    try:
        await shared_conn.close()
    except Exception:
        pass
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: unauth_client — for 401 tests (no DB, no Valkey, no flag needed)
# ─────────────────────────────────────────────────────────────────────────────
#
# ``app`` is a module-level singleton: the flag-gated mount ran at import time
# (flag was False), so ``/api/v1/notifications`` is NOT in ``app``.  For the
# 401 tests we build a MINIMAL throwaway FastAPI that wires in the real
# ``notifications_router`` plus the same auth middleware stack as the shared
# ``app``.  This lets us test the JWT auth dependency without a live DB.

@pytest_asyncio.fixture(loop_scope="function")
async def unauth_client():
    """Throwaway ASGI client with notifications_router mounted and real auth stack.

    The shared ``app`` singleton was built at import time with the monitor flag
    False — the route is absent.  This stub mounts the router unconditionally
    plus the error handlers + auth middleware so that auth errors translate to
    proper HTTP 401 responses.
    """
    from fastapi import FastAPI as _FastAPI

    from app.core.errors import register_error_handlers
    from app.core.middleware.auth_mw import AuthContextMiddleware
    from app.core.middleware.rate_limit_mw import RateLimitMiddleware
    from app.core.middleware.request_id import RequestIdMiddleware
    from app.modules.monitor.router import router as _notif_router

    stub_app = _FastAPI()
    register_error_handlers(stub_app)
    # Minimal middleware that handles JWT auth (mirrors main.py registration order).
    stub_app.add_middleware(RateLimitMiddleware)
    stub_app.add_middleware(AuthContextMiddleware)
    stub_app.add_middleware(RequestIdMiddleware)
    stub_app.include_router(_notif_router)

    async with AsyncClient(
        transport=ASGITransport(app=stub_app), base_url="http://test"
    ) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


# ── 1. Tenancy ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenancy_user_a_sees_only_own_notifications(notifications_fixture):
    """User A's token returns only user A's notifications — never user B's."""
    f = notifications_fixture
    resp = await f["client"].get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {f['token_a']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    returned_ids = {item["id"] for item in body["data"]}
    # User B's notification MUST NOT appear.
    assert str(f["notif_b1_id"]) not in returned_ids
    # Both of user A's notifications must appear (default limit=20).
    assert str(f["notif_a1_id"]) in returned_ids
    assert str(f["notif_a2_id"]) in returned_ids


@pytest.mark.asyncio
async def test_tenancy_user_b_sees_only_own_notifications(notifications_fixture):
    """User B's token returns only user B's notification — never user A's."""
    f = notifications_fixture
    resp = await f["client"].get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {f['token_b']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    returned_ids = {item["id"] for item in body["data"]}
    assert str(f["notif_b1_id"]) in returned_ids
    assert str(f["notif_a1_id"]) not in returned_ids
    assert str(f["notif_a2_id"]) not in returned_ids


# ── 2. 401 without JWT ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_401_without_jwt(unauth_client):
    """Missing Bearer token → 401."""
    resp = await unauth_client.get("/api/v1/notifications")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_401_with_malformed_bearer(unauth_client):
    """Malformed Bearer token → 401."""
    resp = await unauth_client.get(
        "/api/v1/notifications",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401


# ── 3. Envelope shape ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_envelope_shape_and_order(notifications_fixture):
    """Response envelope: data/total/page/unread_count; order created_at DESC."""
    f = notifications_fixture
    resp = await f["client"].get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {f['token_a']}"},
    )
    assert resp.status_code == 200
    body = resp.json()

    # Required top-level keys.
    assert "data" in body
    assert "total" in body
    assert "page" in body
    assert "unread_count" in body

    # User A has 2 notifications.
    assert body["total"] == 2
    assert body["page"] == 1
    # User A has 1 unread notification.
    assert body["unread_count"] == 1

    # Item shape.
    for item in body["data"]:
        assert "id" in item
        assert "category_id" in item
        assert "content_hash" in item
        assert "payload" in item
        assert "is_read" in item
        assert "read_at" in item
        assert "created_at" in item

    # Order: created_at DESC — notif_a1 (10:00) > notif_a2 (09:00).
    assert len(body["data"]) == 2
    assert body["data"][0]["id"] == str(f["notif_a1_id"])
    assert body["data"][1]["id"] == str(f["notif_a2_id"])


@pytest.mark.asyncio
async def test_unread_only_filter(notifications_fixture):
    """?unread_only=true returns only is_read=false rows."""
    f = notifications_fixture
    resp = await f["client"].get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {f['token_a']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Only the unread notification is returned.
    assert body["total"] == 1
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == str(f["notif_a1_id"])
    assert body["data"][0]["is_read"] is False
    # unread_count reflects the full unread count (still 1 for user A).
    assert body["unread_count"] == 1


# ── 4. Pagination ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pagination_page_2(notifications_fixture):
    """?page=2&limit=1 returns the second item (DESC order)."""
    f = notifications_fixture
    resp = await f["client"].get(
        "/api/v1/notifications?page=2&limit=1",
        headers={"Authorization": f"Bearer {f['token_a']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 2
    assert body["total"] == 2  # total across ALL pages
    assert len(body["data"]) == 1
    # Page 2 with limit 1 → second-oldest = notif_a2 (09:00, is_read=True).
    assert body["data"][0]["id"] == str(f["notif_a2_id"])


@pytest.mark.asyncio
async def test_unread_count_is_total_not_page(notifications_fixture):
    """unread_count reflects all unread rows regardless of page/limit."""
    f = notifications_fixture
    # Request only the read notification (page 2 of limit-1 gives the read one).
    resp = await f["client"].get(
        "/api/v1/notifications?page=2&limit=1",
        headers={"Authorization": f"Bearer {f['token_a']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Even though the page item is the READ notification, unread_count is still 1.
    assert body["unread_count"] == 1
    assert body["data"][0]["is_read"] is True


# ── 5. Flag-gate: route absent when FEATURE_CATEGORY_MONITOR_ENABLED=False ────
#
# ``app`` is a module-level singleton built at import time.  The flag-gated
# ``if settings.FEATURE_CATEGORY_MONITOR_ENABLED: app.include_router(…)``
# runs once during ``import app.main``.  In the test environment the default
# is False, so the notifications router is NOT in the shared ``app``.
#
# Tests 5a/5b verify the OFF branch against the shared ``app`` (imported at
# collection time with the flag False).
#
# Tests 6a/6b verify the ON branch by building a MINIMAL throwaway FastAPI
# app that unconditionally includes ``notifications_router`` — proving the
# router delivers the expected path when the flag IS enabled.  A throwaway
# avoids module-reload side-effects while still exercising the router
# registration contract.

def test_flag_off_route_absent():
    """Route is NOT in the shared app (flag was False at import time)."""
    route_map = _route_map(app)
    assert "/api/v1/notifications" not in route_map, (
        "Notifications route must NOT be mounted when the monitor flag is off. "
        f"Mounted paths: {sorted(route_map)}"
    )


def test_flag_off_route_count_unchanged():
    """Route count matches the expected base when monitor flag is off."""
    from app.shared.config import settings as _settings

    route_map = _route_map(app)
    # Base 34 paths; +1 if google-auth flag is on (also determined at import time).
    expected = 35 if _settings.FEATURE_GOOGLE_AUTH_ENABLED else 34
    assert len(route_map) == expected, (
        f"Expected {expected} routes (monitor flag OFF), got {len(route_map)}. "
        f"Paths: {sorted(route_map)}"
    )


# ── 6. Flag-gate: notifications_router path contract (throwaway app) ──────────

def test_flag_on_notifications_router_has_get_route():
    """notifications_router registers GET /api/v1/notifications when included."""
    from fastapi import FastAPI as _FastAPI

    from app.modules.monitor.router import router as _notif_router

    throwaway = _FastAPI()
    throwaway.include_router(_notif_router)
    tmap = _route_map(throwaway)

    assert "/api/v1/notifications" in tmap, (
        "notifications_router must register /api/v1/notifications. "
        f"Registered paths: {sorted(tmap)}"
    )
    assert "GET" in tmap["/api/v1/notifications"], (
        f"GET must be present on /api/v1/notifications, "
        f"got methods: {tmap['/api/v1/notifications']}"
    )


def test_flag_on_notifications_router_adds_exactly_one_path():
    """Including notifications_router adds exactly 1 new distinct path."""
    from fastapi import FastAPI as _FastAPI

    from app.modules.monitor.router import router as _notif_router

    baseline = _FastAPI()
    baseline_count = len(_route_map(baseline))

    with_router = _FastAPI()
    with_router.include_router(_notif_router)
    with_router_count = len(_route_map(with_router))

    assert with_router_count == baseline_count + 1, (
        f"notifications_router must add exactly 1 path key. "
        f"Baseline={baseline_count}, with_router={with_router_count}. "
        f"Paths: {sorted(_route_map(with_router))}"
    )
