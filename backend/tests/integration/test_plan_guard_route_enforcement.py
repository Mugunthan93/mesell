"""qa-auth-contract backend lane — BE-AUTH-15: plan-guard route-level enforcement.

Covers:
- BE-AUTH-15: A free-tier user at the product_count limit → 402 through a real
              POST /products HTTP request.  A paid (pro) user under the limit
              → NOT 402 (plan-guard passes; response may fail for other reasons).

This fills the route-enforcement gap:
  * ``test_core_plan_guard.py`` covers 15 UNIT cases (math + limits).
  * This test covers the ROUTE seam: real HTTP request → middleware/guard fires
    → 402 envelope with non-empty detail + validation_message_id.

Strategy:
  * Uses ``enforce_plan_limit`` mocked as an AsyncMock on the catalog service's
    captured reference (``app.modules.catalog.service.enforce_plan_limit``).
    This avoids seeding 50 real products while still exercising the route's
    enforcement seam end-to-end.
  * Free-user mock: raises PlanLimitExceededError → 402.
  * Pro-user mock: returns normally → NOT 402 (may get other error from validation).

Fixture pattern:
  * A dedicated ``plan_guard_client`` fixture that mirrors the ``iam_client``
    pattern (function-loop NullPool, commit-for-real, cleanup-by-phone-prefix).
  * Verifies two users (free + pro) via /otp/verify; upgrades the pro user's
    plan column directly via ORM.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import redis.asyncio as _redis_lib
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.core.middleware.audit_mw as _audit_mw
import app.shared.valkey as _valkey_module
from app.core.plan_guard import PlanLimitExceededError
from app.main import app
from app.shared.database import Base, get_db
from app.shared.models.audit_event import AuditEvent
from app.shared.models.user import User
from app.shared.valkey import get_valkey_otp
from tests.conftest import _DEV_DATABASE_URL, _valkey_base

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

_PHONE_FREE = "+9155500150"
_PHONE_PRO = "+9155500151"


def _otp_payload(otp: str) -> str:
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    return json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(time.time()) + 300}
    )


async def _cleanup_phones(Session, phones):
    """Delete audit_events + users for the given phone list (FK order)."""
    async with Session() as s:
        for ph in phones:
            user_ids_q = select(User.id).where(User.phone == ph)
            await s.execute(delete(AuditEvent).where(AuditEvent.user_id.in_(user_ids_q)))
            await s.execute(delete(User).where(User.phone == ph))
        await s.commit()


@pytest_asyncio.fixture(loop_scope="function")
async def plan_guard_client():
    """ASGI client + two pre-seeded users (free + pro) for plan-guard route tests.

    Mirrors the ``iam_client`` fixture pattern (NullPool, commit-for-real,
    cleanup-by-phone).  Yields a 4-tuple:
        (client, TestSession, free_access_token, pro_access_token)
    """
    provisioned = bool(os.environ.get("TEST_DATABASE_URL"))
    db_url = _DEV_DATABASE_URL
    valkey_base = _valkey_base()

    engine = create_async_engine(db_url, poolclass=NullPool, echo=False)
    if not provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    _otp_clients: list = []

    async def _otp_override():
        c = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
        _otp_clients.append(c)
        return c

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

    # Patch audit_mw.AsyncSessionLocal (bypasses DI).
    _orig_audit_sl = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = TestSession  # type: ignore[attr-defined]

    # Patch module-level Valkey singletons (loop-affinity guard).
    _orig_cache = _valkey_module._cache_client
    _orig_otp = _valkey_module._otp_client
    _test_cache = _redis_lib.from_url(f"{valkey_base}/3", decode_responses=True)
    _test_otp = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    _valkey_module._cache_client = _test_cache  # type: ignore[assignment]
    _valkey_module._otp_client = _test_otp  # type: ignore[assignment]

    # Pre-cleanup residue from any prior run.
    await _cleanup_phones(TestSession, [_PHONE_FREE, _PHONE_PRO])

    free_token: str = ""
    pro_token: str = ""

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                valkey = await _otp_override()

                # Verify the free user to get an access token.
                await valkey.set(f"otp:{_PHONE_FREE}", _otp_payload("150150"), ex=300)
                r_free = await ac.post(
                    "/api/v1/auth/otp/verify",
                    json={"phone": _PHONE_FREE, "otp": "150150"},
                )
                assert r_free.status_code == 200, (
                    f"free user verify failed: {r_free.status_code}: {r_free.text}"
                )
                free_token = r_free.json()["access_token"]

                # Verify the pro user.
                await valkey.set(f"otp:{_PHONE_PRO}", _otp_payload("151151"), ex=300)
                r_pro = await ac.post(
                    "/api/v1/auth/otp/verify",
                    json={"phone": _PHONE_PRO, "otp": "151151"},
                )
                assert r_pro.status_code == 200, (
                    f"pro user verify failed: {r_pro.status_code}: {r_pro.text}"
                )
                pro_token = r_pro.json()["access_token"]

                # Upgrade the pro user's plan column directly.
                async with TestSession() as upd:
                    result = await upd.execute(select(User).where(User.phone == _PHONE_PRO))
                    u = result.scalar_one_or_none()
                    if u is not None:
                        u.plan = "pro"
                    await upd.commit()

                yield ac, TestSession, free_token, pro_token

    finally:
        _audit_mw.AsyncSessionLocal = _orig_audit_sl  # type: ignore[attr-defined]
        _valkey_module._cache_client = _orig_cache  # type: ignore[assignment]
        _valkey_module._otp_client = _orig_otp  # type: ignore[assignment]
        for c in _otp_clients:
            try:
                await c.aclose()
            except Exception:
                pass
        for c in (_test_cache, _test_otp):
            try:
                await c.aclose()
            except Exception:
                pass
        await _cleanup_phones(TestSession, [_PHONE_FREE, _PHONE_PRO])
        if not provisioned:
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
            except Exception:
                pass
        try:
            await engine.dispose()
        except Exception:
            pass
        app.dependency_overrides.pop(get_valkey_otp, None)
        app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# BE-AUTH-15a — free-tier user at limit → 402
# ─────────────────────────────────────────────────────────────────────────────

async def test_free_user_at_product_limit_gets_402(plan_guard_client):
    """BE-AUTH-15: free-tier user at the product_count cap → 402 via real route.

    Arrange: free user (plan=free); patch enforce_plan_limit to raise
             PlanLimitExceededError (simulates the 50-product cap without
             seeding 50 real products — exercises the route enforcement seam).
    Act: POST /api/v1/products.
    Assert: 402; non-empty detail; non-empty validation_message_id.
    """
    client, _Session, free_token, _pro_token = plan_guard_client

    async def _at_limit(*args, **kwargs):
        raise PlanLimitExceededError(resource="product_count", current=50, limit=50)

    # Patch target: catalog.service captures enforce_plan_limit at import time;
    # patching the source module attribute alone does not reach the captured ref.
    with patch(
        "app.modules.catalog.service.enforce_plan_limit",
        new=AsyncMock(side_effect=_at_limit),
    ):
        resp = await client.post(
            "/api/v1/products",
            json={
                "category_id": "00000000-0000-0000-0000-000000000000",
                "name": "Test Product",
            },
            headers={"Authorization": f"Bearer {free_token}"},
        )

    assert resp.status_code == 402, (
        f"free-tier at limit must be 402; got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    detail = body.get("detail", "")
    assert detail, f"402 must have non-empty detail; got {body!r}"
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"402 must have non-empty validation_message_id; got {body!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# BE-AUTH-15b — pro user under limit passes plan-guard
# ─────────────────────────────────────────────────────────────────────────────

async def test_pro_user_under_limit_passes_plan_guard(plan_guard_client):
    """BE-AUTH-15: pro-tier user with enforce_plan_limit passing → NOT 402.

    Arrange: pro user (plan=pro); patch enforce_plan_limit to be a no-op.
    Act: POST /api/v1/products (may fail for other reasons like schema validation
         or missing category — that is fine; we only assert it is NOT 402 from
         the plan-guard).
    Assert: status != 402.
    """
    client, _Session, _free_token, pro_token = plan_guard_client

    async def _passes(*args, **kwargs):
        return  # no-op — limit not exceeded

    with patch(
        "app.modules.catalog.service.enforce_plan_limit",
        new=AsyncMock(side_effect=_passes),
    ):
        resp = await client.post(
            "/api/v1/products",
            json={
                "category_id": "00000000-0000-0000-0000-000000000000",
                "name": "Test Product",
            },
            headers={"Authorization": f"Bearer {pro_token}"},
        )

    # Must NOT be 402 from plan-guard.
    assert resp.status_code != 402, (
        f"pro-tier user under limit must NOT get 402; "
        f"got {resp.status_code}: {resp.text}"
    )
