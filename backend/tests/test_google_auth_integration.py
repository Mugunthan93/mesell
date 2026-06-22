"""google-auth integration test (coordinator-owned, design §H.5).

Full route → service → repository → DB → token-issuance round-trip for
POST /api/v1/auth/google/verify, with ONLY the Google adapter mocked (we
cannot mint a real Google ID-token in CI).  Proves:

* a first Google login creates a Google-only user (phone NULL) and issues an
  access JWT + refresh cookie that participate in the shared FE-D5 session;
* the issued access token authenticates GET /api/v1/auth/me (phone == None);
* the issued refresh cookie rotates via POST /api/v1/auth/refresh (the
  Google-issued session uses the SAME provider-agnostic refresh path);
* cross-provider linking: a phone user who later Google-verifies the SAME
  verified email resolves to the SAME user_id (auto-link).

DB-fidelity policy (conftest): these tests run ONLY when ``TEST_DATABASE_URL``
is set (CI Gate 4) and auto-skip on a laptop with no provisioned test DB.  The
google-route is flag-gated, so the test mounts ``iam_google_router`` onto the
app and forces ``FEATURE_GOOGLE_AUTH_ENABLED`` true for the duration.

NOTE: the linking-rule matrix + adapter edge cases are unit-covered in
``backend/services/svc-iam/tests/test_service_google.py`` and
``test_adapter_google.py`` (byte-parity twins of the monolith iam code).

HARNESS NOTE (2026-06-20, me-phone-nullable fix): the original google_client
fixture (PR #295) used ``client.app`` (httpx.AsyncClient has no ``.app``) and
called ``client.post(...)`` synchronously without ``await`` — so every test in
this file ERRORED before reaching any assertion.  It also did not bind
``get_db``/``get_valkey_otp`` to function-loop clients, so a Google-created user
committed inside the request was invisible to the SAME request's ``/me`` lookup
(separate connection → 403) and Valkey singletons leaked across loops
(``Event loop is closed``).  The fixture below re-wires the flow against the
async ``httpx.AsyncClient`` using the proven ``iam_client`` pattern
(function-loop NullPool engine, commit-for-real, module-singleton patches,
phone-prefix cleanup).  Harness-only; no production behaviour changed.
"""

from __future__ import annotations

import hashlib
import json as _json
import os
import time as _time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
import redis.asyncio as _redis_lib
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.core.middleware.audit_mw as _audit_mw
import app.shared.valkey as _valkey_module
from app.adapters.google import GoogleClaims
from app.main import app
from app.shared.config import settings
from app.shared.database import Base, get_db
from app.shared.valkey import get_valkey_otp
from tests.conftest import _DEV_DATABASE_URL, _valkey_base
from tests.integration._cookie_helpers import extract_refresh_cookie

# Phone prefix used by the OTP-path test below; cleaned up in teardown.
_GA_PHONE_PREFIX = "+919876500"


def _claims(email, sub):
    return GoogleClaims(sub=sub, email=email, email_verified=True, name="S", picture=None)


async def _cleanup(db_url: str) -> None:
    """Delete this file's test users (google emails + the OTP phone prefix)."""
    import asyncpg

    pg_dsn = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        conn = await asyncpg.connect(pg_dsn)
    except Exception:
        return
    try:
        await conn.execute("DELETE FROM users WHERE phone LIKE $1", f"{_GA_PHONE_PREFIX}%")
        await conn.execute("DELETE FROM users WHERE email LIKE 'link-%@example.com'")
        await conn.execute("DELETE FROM users WHERE email = 'newseller@example.com'")
    except Exception:
        pass
    finally:
        await conn.close()


@pytest_asyncio.fixture(loop_scope="function")
async def google_client(monkeypatch):
    """Async ASGI client with the google_router mounted, function-loop safe.

    Mirrors the proven ``iam_client`` fixture: function-loop NullPool engine,
    commit-for-real sessions (so a request-committed row is visible to the same
    request's later DB read and to the test body), module-singleton patches for
    audit + Valkey, and phone/email cleanup at teardown.  The Google adapter is
    mocked at the service layer per test.

    Yields ``(client, iam_service, monkeypatch, Session)``.
    """
    from app.modules.iam import iam_google_router
    from app.modules.iam import service as iam_service

    db_url = _DEV_DATABASE_URL
    valkey_base = _valkey_base()
    provisioned = bool(os.environ.get("TEST_DATABASE_URL"))

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

    # Module-level singletons that bypass FastAPI DI.
    _orig_audit_sl = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = TestSession  # type: ignore[attr-defined]
    _orig_cache_client = _valkey_module._cache_client
    _test_cache_client = _redis_lib.from_url(f"{valkey_base}/3", decode_responses=True)
    _valkey_module._cache_client = _test_cache_client  # type: ignore[assignment]
    _orig_otp_client = _valkey_module._otp_client
    _test_otp_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    _valkey_module._otp_client = _test_otp_client  # type: ignore[assignment]

    # Mount the flag-gated google router (production mount is off by default).
    if not any(
        getattr(r, "path", "") == "/api/v1/auth/google/verify" for r in app.routes
    ):
        app.include_router(iam_google_router)

    await _cleanup(db_url)

    lifespan_db_engine = None
    lifespan_valkey_client = None
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            async with app.router.lifespan_context(app):
                lifespan_db_engine = getattr(app.state, "db_engine", None)
                lifespan_valkey_client = getattr(app.state, "valkey", None)
                yield ac, iam_service, monkeypatch, TestSession
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
        _audit_mw.AsyncSessionLocal = _orig_audit_sl  # type: ignore[attr-defined]
        _valkey_module._cache_client = _orig_cache_client  # type: ignore[assignment]
        _valkey_module._otp_client = _orig_otp_client  # type: ignore[assignment]
        for c in (*_otp_clients, _test_cache_client, _test_otp_client):
            try:
                await c.aclose()
            except Exception:
                pass
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
        try:
            await _cleanup(db_url)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_google_first_login_then_me_then_refresh(google_client):
    client, iam_service, monkeypatch, _Session = google_client
    monkeypatch.setattr(
        iam_service.google_adapter,
        "verify_id_token",
        AsyncMock(return_value=_claims("newseller@example.com", "g-sub-int-1")),
    )

    # 1. First Google login → 200 + access token + refresh cookie.
    resp = await client.post("/api/v1/auth/google/verify", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    access = body["access_token"]
    assert access and body["token_type"] == "bearer"
    refresh_cookie = extract_refresh_cookie(resp)
    assert refresh_cookie, "google/verify must Set-Cookie refresh_token"

    # 2. The access token authenticates /me — and a Google-only user has NO
    #    phone, so /me must return 200 with phone == None.  This is the fix:
    #    MeResponse.phone is ``str | None`` (was ``str`` → 422
    #    validation.phone.string_type for Google-only users).
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 200, me.text
    assert me.json()["phone"] is None  # Google-only user has no phone

    # 3. The refresh cookie rotates via the shared FE-D5 path.  httpx drops the
    #    ``Domain=.mesell.xyz`` cookie, so propagate it explicitly.
    refresh = await client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["access_token"]


@pytest.mark.asyncio
async def test_google_only_user_catalog_nav_stays_authenticated(google_client):
    """Regression guard for the "Google sign-in → view catalog → logged out" bug
    (gauth-catalog-logout, 2026-06-21).

    A real Google sign-in creates a phone-NULL user (``phone=NULL``,
    ``google_sub`` set).  The founder reported that navigating to view the
    catalog logged the user out — the suspicion being a phone-NULL gap on the
    catalog path mirroring the #322 ``/auth/me`` 422 (phone-NULL) defect.

    The browser repro (agent-browser, the real Google-only dev user) showed the
    user STAYS logged in: the historical logout was the federation
    auth-singleton stale-bundle artifact fixed in #373 (FED-1), NOT a
    phone-NULL backend/guard gap.  This test LOCKS that finding at the
    route→dependency layer: the Google-only user's access token must
    authenticate the EXACT request the catalog page fires — ``GET /products``,
    whose handler depends on ``get_current_user`` — and return 200, never 401.

    ``get_current_user`` decodes the JWT ``sub`` and verifies the user row
    exists; it has NO phone dependency, so a phone-NULL user must pass.  If a
    future change ever introduces a phone-NULL assumption on the authenticated
    catalog path, this test fails loudly.
    """
    client, iam_service, monkeypatch, _Session = google_client
    monkeypatch.setattr(
        iam_service.google_adapter,
        "verify_id_token",
        AsyncMock(return_value=_claims("catalog-nav@example.com", "g-sub-catnav")),
    )

    # 1. Google sign-in → phone-NULL user + access token (the founder's flow).
    resp = await client.post("/api/v1/auth/google/verify", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text
    access = resp.json()["access_token"]

    # 2. /me confirms this is a Google-only (phone-NULL) user.
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 200, me.text
    assert me.json()["phone"] is None  # Google-only user — the bug's precondition

    # 3. THE BUG PATH: navigating to view the catalog fires GET /products.  For
    #    a phone-NULL user this must return 200 (authenticated), NOT 401 — a 401
    #    here is exactly what would force the FE interceptor → refresh → logout
    #    cascade the founder observed.
    products = await client.get(
        "/api/v1/products", headers={"Authorization": f"Bearer {access}"}
    )
    assert products.status_code == 200, (
        f"Google-only (phone-NULL) user must stay authenticated on the catalog "
        f"nav path; got {products.status_code}: {products.text}"
    )
    body = products.json()
    assert "products" in body and "total" in body  # locked list-response shape


@pytest.mark.asyncio
async def test_google_links_to_existing_phone_user_by_email(google_client):
    """Cross-provider: a phone user + a Google login on the SAME verified email
    resolve to the SAME user_id (auto-link, design §E rule 2).

    Also the regression guard for the audit-userid fix (2026-06-20): on the
    LINK path the ``audit_events`` rows (``auth.login.success`` +
    ``auth.google.linked``) must persist with a NON-NULL ``user_id`` equal to
    the linked user.  Before the fix, the bidirectional ``back_populates``
    relationship caused SQLAlchemy's unit-of-work to emit
    ``UPDATE audit_events SET user_id=NULL`` at the outer commit →
    ``NotNullViolationError``.  Making ``User.audit_events`` ``viewonly`` (and
    dropping the ``back_populates`` on both sides) stops the UoW from nulling
    the child FK.
    """
    from sqlalchemy import delete, select

    from app.shared.models.audit_event import AuditEvent
    from app.shared.models.user import User

    client, iam_service, monkeypatch, Session = google_client

    shared_email = f"link-{uuid.uuid4().hex[:8]}@example.com"
    seed_phone = f"+9197{uuid.uuid4().int % 100000000:08d}"
    async with Session() as seed_session:
        phone_user = User(
            phone=seed_phone,
            email=shared_email,
            plan="free",
            last_login_at=datetime.now(timezone.utc),
        )
        seed_session.add(phone_user)
        await seed_session.commit()
        await seed_session.refresh(phone_user)
        original_id = phone_user.id

    monkeypatch.setattr(
        iam_service.google_adapter,
        "verify_id_token",
        AsyncMock(return_value=_claims(shared_email, "g-sub-int-link")),
    )

    resp = await client.post("/api/v1/auth/google/verify", json={"credential": "tok"})
    assert resp.status_code == 200, resp.text

    async with Session() as verify_session:
        refreshed = await verify_session.get(User, original_id)
        assert refreshed is not None
        assert refreshed.google_sub == "g-sub-int-link"
        assert refreshed.phone is not None  # phone preserved

    # CRUX: the link-path audit rows must persist with a NON-NULL user_id equal
    # to the linked user.  This is the assertion the bug used to break — the
    # outer-commit ``UPDATE audit_events SET user_id=NULL`` raised
    # NotNullViolationError before the fix, so the rows never committed.
    async with Session() as audit_session:
        rows = (
            (
                await audit_session.execute(
                    select(AuditEvent).where(AuditEvent.user_id == original_id)
                )
            )
            .scalars()
            .all()
        )
    event_types = {r.event_type for r in rows}
    assert "auth.login.success" in event_types, event_types
    assert "auth.google.linked" in event_types, event_types
    assert all(r.user_id == original_id for r in rows)  # every row non-null + linked

    # Cleanup: with the fix, audit_events RESTRICT-references the user, so the
    # child rows MUST be deleted before the user row (else FK RESTRICT blocks).
    async with Session() as cleanup_session:
        await cleanup_session.execute(
            delete(AuditEvent).where(AuditEvent.user_id == original_id)
        )
        row = await cleanup_session.get(User, original_id)
        if row is not None:
            await cleanup_session.delete(row)
        await cleanup_session.commit()


@pytest.mark.asyncio
async def test_me_phone_is_string_for_otp_user(google_client):
    """Regression guard for the phone-nullable relaxation: a PHONE/OTP user's
    ``GET /auth/me`` still returns ``phone`` as a non-null E.164 string.

    The ``phone: str | None`` relaxation on ``MeResponse`` (so Google-only
    users can return ``None``) must NOT degrade the OTP path — an OTP-verified
    user always carries a phone, and the response must still type it as ``str``.
    This seeds an OTP into the test Valkey, verifies it (issuing the access
    token through the real route → service → repo → DB path), then asserts
    ``/me`` returns ``phone`` as a string.
    """
    client, _iam_service, _monkeypatch, _Session = google_client

    phone = f"{_GA_PHONE_PREFIX}001"  # +919876500001 (10-digit IN mobile) — matches cleanup prefix
    otp = "654321"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = _json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(_time.time()) + 300}
    )
    valkey = await get_valkey_otp()
    await valkey.set(f"otp:{phone}", payload, ex=300)

    verify = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
    )
    assert verify.status_code == 200, verify.text
    access = verify.json()["access_token"]

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["phone"] is not None
    assert isinstance(body["phone"], str)
    assert body["phone"].startswith("+")


@pytest.mark.asyncio
async def test_google_verify_409_on_google_sub_collision(google_client):
    """Edge case 4 (design §E rule 3): email owned by different google_sub → 409.

    When the incoming Google credential's verified email matches an existing
    user whose google_sub is NON-NULL and DIFFERENT from the incoming sub,
    the service raises GoogleIdentityConflictError (409,
    code="iam.google_identity_conflict").  No tokens are issued.

    Arrange: seed a user with google_sub="g-sub-original" on a unique email;
             present a credential with the SAME email but sub="g-sub-attacker".
    Act: POST /auth/google/verify.
    Assert: 409; code="iam.google_identity_conflict";
            validation_message_id non-empty (P0 item 14); no access_token.
    """
    from datetime import datetime, timezone

    from app.shared.models.user import User

    client, iam_service, monkeypatch, Session = google_client
    shared_email = f"conflict-{uuid.uuid4().hex[:8]}@example.com"

    async with Session() as seed_session:
        seeded_user = User(
            google_sub="g-sub-original",
            email=shared_email,
            plan="free",
            last_login_at=datetime.now(timezone.utc),
        )
        seed_session.add(seeded_user)
        await seed_session.commit()

    monkeypatch.setattr(
        iam_service.google_adapter,
        "verify_id_token",
        AsyncMock(return_value=_claims(shared_email, "g-sub-attacker")),
    )

    resp = await client.post("/api/v1/auth/google/verify", json={"credential": "tok"})

    assert resp.status_code == 409, (
        f"Expected 409 on google_sub collision, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("code") == "iam.google_identity_conflict", (
        f"code must be 'iam.google_identity_conflict'; got {body!r}"
    )
    # P0 item 14: validation_message_id must be a non-empty string.
    msg_id = body.get("validation_message_id", "")
    assert isinstance(msg_id, str) and msg_id, (
        f"409 must have non-empty validation_message_id; got {body!r}"
    )
    # No access_token is issued on a 409.
    assert "access_token" not in body, (
        f"409 must NOT issue an access_token; got {body!r}"
    )


# ── Dev/test Google-verify bypass (PROD-HARD-DISABLED) ──────────────────────
# These three tests mirror the OTP-bypass contract
# (test_iam_dev_otp_bypass.py): (a) dev success, (b) prod force-disable —
# the load-bearing security test, (c) regression.  Unlike the tests above,
# they DO NOT mock ``verify_id_token`` — the whole point is to exercise the
# REAL adapter with the sentinel.  Only the lowest-level Google library call
# (``id_token.verify_oauth2_token``) is mocked, so a non-sentinel credential
# still flows through the real adapter logic.

_DEV_GOOGLE_SENTINEL = "dev-google:e2e-sub-001:e2e.user@example.com"


def _patch_real_google_verify_to_reject(monkeypatch) -> None:
    """Mock the LOWEST-level Google library call so the real adapter path is
    deterministic offline: any token reaching ``verify_oauth2_token`` is
    rejected exactly like a forged credential (ValueError → 401).
    """

    def _reject(*_args, **_kwargs):
        raise ValueError("Invalid token signature (mocked real Google verify).")

    monkeypatch.setattr(
        "app.adapters.google.id_token.verify_oauth2_token", _reject
    )


@pytest.mark.asyncio
async def test_dev_google_bypass_success(google_client):
    """(a) APP_ENV != production + feature on + sentinel credential →
    /auth/google/verify 200; issues tokens; creates the dual-identity user with
    the SYNTHETIC sub/email landed.  No real Google verify is called.
    """
    from app.shared.models.user import User

    client, _iam_service, monkeypatch, Session = google_client
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "FEATURE_GOOGLE_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "DEV_GOOGLE_BYPASS_TOKEN", _DEV_GOOGLE_SENTINEL)
    # If the bypass ever leaks to the real call, this makes it fail loudly.
    _patch_real_google_verify_to_reject(monkeypatch)

    resp = await client.post(
        "/api/v1/auth/google/verify", json={"credential": _DEV_GOOGLE_SENTINEL}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"], "bypass success must mint an access token"
    assert body["token_type"] == "bearer"
    assert extract_refresh_cookie(resp), "bypass success must emit a refresh cookie"

    # The synthetic identity from the sentinel must have landed as a real
    # dual-identity Google-only user (phone NULL, google_sub + email set).
    from sqlalchemy import select

    async with Session() as s:
        row = (
            await s.execute(
                select(User).where(User.google_sub == "e2e-sub-001")
            )
        ).scalar_one_or_none()
    assert row is not None, "bypass must create the synthetic user"
    assert row.email == "e2e.user@example.com"
    assert row.phone is None  # Google-only dual-identity user

    # Cleanup the synthetic user.
    from sqlalchemy import delete

    from app.shared.models.audit_event import AuditEvent

    async with Session() as s:
        await s.execute(delete(AuditEvent).where(AuditEvent.user_id == row.id))
        u = await s.get(User, row.id)
        if u is not None:
            await s.delete(u)
        await s.commit()


@pytest.mark.asyncio
async def test_prod_force_disable(google_client):
    """(b) LOAD-BEARING SECURITY TEST.  APP_ENV=production + the sentinel set →
    the bypass is FORCE-DISABLED; the sentinel is treated as an ordinary
    credential and hits the REAL verify → rejected → 401.  No synthetic claims,
    no user created, no tokens issued.
    """
    from sqlalchemy import select

    from app.shared.models.user import User

    client, _iam_service, monkeypatch, Session = google_client
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "FEATURE_GOOGLE_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "DEV_GOOGLE_BYPASS_TOKEN", _DEV_GOOGLE_SENTINEL)
    # In prod the sentinel must reach this real-verify call and be rejected.
    _patch_real_google_verify_to_reject(monkeypatch)

    resp = await client.post(
        "/api/v1/auth/google/verify", json={"credential": _DEV_GOOGLE_SENTINEL}
    )
    assert resp.status_code == 401, (
        f"prod must force-disable the bypass and reject the sentinel; "
        f"got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("code") == "iam.google_token_invalid", body
    assert "access_token" not in body

    # Absolutely NO synthetic user may have been created.
    async with Session() as s:
        row = (
            await s.execute(
                select(User).where(User.google_sub == "e2e-sub-001")
            )
        ).scalar_one_or_none()
    assert row is None, "prod force-disable must NOT create the synthetic user"


@pytest.mark.asyncio
async def test_dev_google_bypass_regression(google_client):
    """(c) Regression under conditions where the bypass must NOT fire:

    1. Bypass OFF (sentinel empty) + the sentinel-looking credential →
       real verify → 401 (unchanged behaviour).
    2. Bypass ON but a NON-sentinel credential → real verify → 401
       (the bypass only fires on an exact sentinel match).
    """
    from sqlalchemy import select

    from app.shared.models.user import User

    client, _iam_service, monkeypatch, Session = google_client
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "FEATURE_GOOGLE_AUTH_ENABLED", True)
    _patch_real_google_verify_to_reject(monkeypatch)

    # 1. Bypass OFF — even the sentinel string is just an ordinary credential.
    monkeypatch.setattr(settings, "DEV_GOOGLE_BYPASS_TOKEN", "")
    r_off = await client.post(
        "/api/v1/auth/google/verify", json={"credential": _DEV_GOOGLE_SENTINEL}
    )
    assert r_off.status_code == 401, r_off.text
    assert r_off.json().get("code") == "iam.google_token_invalid", r_off.text

    # 2. Bypass ON, but a credential that is NOT the sentinel → real verify.
    monkeypatch.setattr(settings, "DEV_GOOGLE_BYPASS_TOKEN", _DEV_GOOGLE_SENTINEL)
    r_nonmatch = await client.post(
        "/api/v1/auth/google/verify",
        json={"credential": "some-other-real-looking-token"},
    )
    assert r_nonmatch.status_code == 401, r_nonmatch.text
    assert r_nonmatch.json().get("code") == "iam.google_token_invalid", r_nonmatch.text

    # No synthetic user from either non-firing path.
    async with Session() as s:
        row = (
            await s.execute(
                select(User).where(User.google_sub == "e2e-sub-001")
            )
        ).scalar_one_or_none()
    assert row is None, "no bypass should have fired → no synthetic user"
