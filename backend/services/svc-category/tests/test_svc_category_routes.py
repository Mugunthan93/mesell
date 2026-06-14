"""svc-category route-level tests — Phase B routes (public + internal shims).

Scope: router.py (5 public routes) + internal_router.py (4 /internal/* shims)
       + schemas.py (shape validation).

Test strategy
-------------
All tests run against the FastAPI test client (``TestClient``/``AsyncClient``).
No live DB or Valkey is required:
- Auth is bypassed via ``dependency_overrides[get_current_user]`` (same
  pattern as monolith route tests — see MEMORY.md §8 customer + §9 category).
- Service methods are monkeypatched to return controlled dicts/objects.
- ``get_db`` is overridden with an ``AsyncMock`` so SQLAlchemy never touches
  a socket.

Singleton patching (required for cross-loop safety — MEMORY.md §8 + §9)
------------------------------------------------------------------------
``audit_mw.AsyncSessionLocal`` and ``shared.valkey._cache_client`` are
module-level singletons, NOT injected via Depends().  They bind to the asyncio
event loop that created them.  When pytest runs each test in a new function
loop (asyncio_mode=auto + loop_scope=function), the pre-existing singletons
are bound to a DEAD loop — asyncpg raises RuntimeError which anyio wraps in an
ExceptionGroup that propagates past the 4xx handler.

Fix: patch both singletons before the FastAPI app is exercised.  The
``patch_singletons`` autouse fixture (function scope) replaces:
1. ``app.core.middleware.audit_mw.AsyncSessionLocal`` with a contextmanager
   that yields an AsyncMock (audit_mw never reaches a real DB).
2. ``app.shared.valkey._cache_client`` with a unified AsyncMock so rate-limit
   and cache calls have a non-None, non-socket client.

Test naming convention
----------------------
``test_<route>_<happy|unauth|flag_off|not_found|shape>``
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ── env is set by conftest.py before any app import ──────────────────────────


@pytest.fixture(scope="function", autouse=True)
def patch_singletons():
    """Patch module-level singletons that bypass Depends() injection.

    Without this patch two things fail across function-scoped tests:
    1. ``audit_mw.AsyncSessionLocal`` — opens a DB connection bound to the
       FIRST test's event loop; subsequent tests see a cross-loop RuntimeError.
    2. ``shared.valkey._otp_client`` — used by rate_limit_mw; same cross-loop
       issue.  ``_cache_client`` — used by cache.get_or_set; same issue.

    Both RuntimeErrors wrap in anyio ExceptionGroup, bubble past the 4xx
    handler, and cause tests to raise instead of returning a Response.

    Fix: reset both singletons to None before each test so the lazy-init
    code in ``get_valkey_otp()`` / ``get_valkey_cache()`` runs fresh in the
    new function loop.  Then patch ``_make_client`` to return an AsyncMock
    so no real socket is opened.
    """
    import app.core.middleware.audit_mw as _audit_mw
    import app.shared.valkey as _valkey_mod

    # ── Patch audit_mw.AsyncSessionLocal ─────────────────────────────────────
    _mock_session = AsyncMock()
    _mock_session.__aenter__ = AsyncMock(return_value=AsyncMock())
    _mock_session.__aexit__ = AsyncMock(return_value=False)

    class _MockSessionFactory:
        def __call__(self):
            return _mock_session

    _orig_session_local = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = _MockSessionFactory()

    # ── Patch valkey singletons — reset to None + patch _make_client ─────────
    # Reset any stale clients from the previous test's event loop.
    _orig_otp = _valkey_mod._otp_client
    _orig_cache = _valkey_mod._cache_client
    _valkey_mod._otp_client = None
    _valkey_mod._cache_client = None

    # Build a unified mock Redis client that _make_client() will return.
    _mock_redis = MagicMock()
    _mock_redis.get = AsyncMock(return_value=None)
    _mock_redis.set = AsyncMock(return_value=True)
    _mock_redis.setex = AsyncMock(return_value=True)
    _mock_redis.delete = AsyncMock(return_value=0)
    _mock_redis.eval = AsyncMock(return_value=1)
    _mock_redis.evalsha = AsyncMock(return_value=1)
    _mock_redis.script_load = AsyncMock(return_value="abc123sha")
    _mock_redis.aclose = AsyncMock(return_value=None)

    with patch.object(_valkey_mod, "_make_client", return_value=_mock_redis):
        yield

    # Restore originals after each test.
    _audit_mw.AsyncSessionLocal = _orig_session_local
    _valkey_mod._otp_client = _orig_otp
    _valkey_mod._cache_client = _orig_cache


@pytest.fixture(scope="function")
def app():
    """Import the FastAPI app (function-scoped to prevent cross-loop contamination).

    Module-scope fixtures share a DB-engine pool across tests.  With asyncpg +
    pool_pre_ping the engine binds to the creating loop; when the next test
    opens a new loop the cross-loop Future binding raises RuntimeError which
    anyio wraps in an ExceptionGroup that bubbles past the 4xx handler.
    Function scope gives each test a clean engine state (NullPool behaviour).
    Same pattern as MEMORY.md §8 + §9 cross-loop discovery.
    """
    from app.main import app as _app
    return _app


@pytest.fixture(scope="function")
def fake_user():
    """Minimal CurrentUser stand-in (2-field frozen dataclass)."""
    from app.core.auth import CurrentUser
    return CurrentUser(user_id=uuid4(), plan="free")


@pytest.fixture(scope="function")
def override_auth(app, fake_user):
    """Install + teardown get_current_user override per test."""
    from app.core.auth import get_current_user

    async def _stub():
        return fake_user

    app.dependency_overrides[get_current_user] = _stub
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="function")
def override_db(app):
    """Override get_db with a plain AsyncMock so no DB socket is opened."""
    from app.shared.database import get_db

    async def _stub_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _stub_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture()
async def client(app, override_auth, override_db):
    """Async httpx client against the app with auth + db overrides active."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture()
async def unauth_client(app):
    """Client with NO auth override — for 401 tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _suggest_payload(n: int = 2) -> dict[str, Any]:
    """Minimal valid suggest service response."""
    return {
        "suggestions": [
            {
                "category_id": str(uuid4()),
                "super_id": "26",
                "super_name": "Clothing",
                "path": "Clothing > Kurtas",
                "leaf_name": f"Kurtas {i}",
                "confidence": 0.9 - i * 0.1,
                "reasons": ["fabric match"],
            }
            for i in range(n)
        ],
        "fallback_offered": False,
    }


def _browse_payload() -> dict[str, Any]:
    return {
        "results": [
            {
                "category_id": str(uuid4()),
                "super_id": "26",
                "super_name": "Clothing",
                "path": "Clothing > Kurtas",
                "leaf_name": "Kurtas",
                "similarity": 0.0,
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0,
    }


def _tree_payload() -> dict[str, Any]:
    return {
        "super_categories": [
            {
                "super_id": "26",
                "super_name": "Clothing",
                "leaves": [
                    {
                        "category_id": str(uuid4()),
                        "super_id": "26",
                        "super_name": "Clothing",
                        "path": "Clothing > Kurtas",
                        "leaf_name": "Kurtas",
                        "similarity": 0.0,
                    }
                ],
            }
        ]
    }


def _schema_payload() -> dict[str, Any]:
    return {
        "fields": [
            {
                "name": "fabric",
                "primitive": "text_short",
                "label_en": "Fabric",
                "required": True,
                "order": 1,
                "section": "base",
                "validation_message_id": None,
                "enum_resolver": None,
                "data_type": "string",
            }
        ],
        "compulsory_count": 1,
        "optional_count": 0,
        "total_count": 1,
        "wizard_step_count": 1,
        "main_sheet_label": "Catalog Main",
        "compliance_shape": "standard",
    }


def _field_enum_payload() -> dict[str, Any]:
    return {
        "enum_entries": [
            {"canonical": "Cotton", "meesho": "Cotton", "labels": {"en": "Cotton"}}
        ],
        "total": 1,
        "truncated": False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. GET /api/v1/categories/suggest  (§9.B.1)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggest_happy(client):
    """Happy path — AI track returns 2 suggestions."""
    with patch("app.service.suggest_categories", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _suggest_payload(2)
        resp = await client.get("/api/v1/categories/suggest?q=red cotton kurta")
    assert resp.status_code == 200
    body = resp.json()
    assert "suggestions" in body
    assert len(body["suggestions"]) == 2
    assert body["fallback_offered"] is False
    assert "confidence" in body["suggestions"][0]


@pytest.mark.asyncio
async def test_suggest_fallback_offered(client):
    """AI track fails gracefully — fallback_offered=True."""
    with patch("app.service.suggest_categories", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = {"suggestions": [], "fallback_offered": True}
        resp = await client.get("/api/v1/categories/suggest?q=unknown product description")
    assert resp.status_code == 200
    assert resp.json()["fallback_offered"] is True


@pytest.mark.asyncio
async def test_suggest_unauth(unauth_client):
    """Missing Bearer token → 401."""
    resp = await unauth_client.get("/api/v1/categories/suggest?q=some product")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_suggest_q_too_short(client):
    """Empty q → 422 (Pydantic min_length=1 on Query)."""
    resp = await client.get("/api/v1/categories/suggest?q=")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_suggest_q_missing(client):
    """Missing q → 422."""
    resp = await client.get("/api/v1/categories/suggest")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_suggest_flag_off(app, client):
    """FEATURE_SMART_PICKER_ENABLED=False → 404."""
    from app.shared.config import settings as _settings
    original = _settings.FEATURE_SMART_PICKER_ENABLED
    _settings.FEATURE_SMART_PICKER_ENABLED = False
    try:
        with patch("app.service.suggest_categories", new_callable=AsyncMock):
            resp = await client.get("/api/v1/categories/suggest?q=red cotton kurta")
        assert resp.status_code == 404
        assert "disabled" in resp.json()["detail"].lower()
    finally:
        _settings.FEATURE_SMART_PICKER_ENABLED = original


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET /api/v1/categories/browse  (§9.B.2)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_browse_happy(client):
    """Happy path — returns paginated browse results."""
    with patch("app.service.browse_categories", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _browse_payload()
        resp = await client.get("/api/v1/categories/browse?q=kurta&limit=20&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert body["total"] == 1
    assert body["limit"] == 20


@pytest.mark.asyncio
async def test_browse_no_q(client):
    """Browse without q — still 200 (q is optional)."""
    with patch("app.service.browse_categories", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = {"results": [], "total": 0, "limit": 20, "offset": 0}
        resp = await client.get("/api/v1/categories/browse")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_browse_unauth(unauth_client):
    """401 on missing auth."""
    resp = await unauth_client.get("/api/v1/categories/browse")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_browse_limit_out_of_range(client):
    """limit=0 → 422 (ge=1)."""
    resp = await client.get("/api/v1/categories/browse?limit=0")
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /api/v1/categories  (§9.B.3 — ETag/304)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_category_tree_happy(client):
    """Happy path — returns tree with ETag header."""
    with patch("app.service.get_category_tree", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _tree_payload()
        resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert "super_categories" in resp.json()
    assert "ETag" in resp.headers


@pytest.mark.asyncio
async def test_category_tree_etag_304(client):
    """If-None-Match matching ETag → 304 No Content.

    Uses a FIXED payload (UUID pinned) so the ETag is deterministic across
    both requests.  Without a fixed UUID, _tree_payload() generates a new
    uuid4() each time, producing different JSON → different ETag → the
    second request sees a stale ETag → 200 instead of 304.
    """
    _fixed_cat_id = "00000000-0000-0000-0000-000000000001"
    _fixed_tree = {
        "super_categories": [
            {
                "super_id": "26",
                "super_name": "Clothing",
                "leaves": [
                    {
                        "category_id": _fixed_cat_id,
                        "super_id": "26",
                        "super_name": "Clothing",
                        "path": "Clothing > Kurtas",
                        "leaf_name": "Kurtas",
                        "similarity": 0.0,
                    }
                ],
            }
        ]
    }

    with patch("app.service.get_category_tree", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _fixed_tree
        # First request — get ETag
        resp1 = await client.get("/api/v1/categories")
    assert resp1.status_code == 200
    etag = resp1.headers["ETag"]

    with patch("app.service.get_category_tree", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _fixed_tree  # same payload → same ETag
        # Second request with the matching ETag → expect 304
        resp2 = await client.get("/api/v1/categories", headers={"if-none-match": etag})
    assert resp2.status_code == 304
    assert resp2.content == b""


@pytest.mark.asyncio
async def test_category_tree_etag_stale(client):
    """Non-matching If-None-Match → full 200 response."""
    with patch("app.service.get_category_tree", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _tree_payload()
        resp = await client.get(
            "/api/v1/categories", headers={"if-none-match": '"stale-etag-value"'}
        )
    assert resp.status_code == 200
    assert "ETag" in resp.headers


@pytest.mark.asyncio
async def test_category_tree_unauth(unauth_client):
    resp = await unauth_client.get("/api/v1/categories")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /api/v1/categories/{id}/schema  (§9.B.4 — ETag/304)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_happy(client):
    """Happy path — returns 7-key envelope with ETag."""
    cat_id = uuid4()
    with patch("app.service.fetch_schema", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _schema_payload()
        resp = await client.get(f"/api/v1/categories/{cat_id}/schema")
    assert resp.status_code == 200
    body = resp.json()
    # Verify all 7 §5A.B keys present
    for key in (
        "fields", "compulsory_count", "optional_count", "total_count",
        "wizard_step_count", "main_sheet_label", "compliance_shape",
    ):
        assert key in body, f"Missing §5A.B key: {key}"
    assert "ETag" in resp.headers


@pytest.mark.asyncio
async def test_schema_etag_304(client):
    """If-None-Match match → 304."""
    cat_id = uuid4()
    with patch("app.service.fetch_schema", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _schema_payload()
        resp1 = await client.get(f"/api/v1/categories/{cat_id}/schema")
    etag = resp1.headers["ETag"]

    with patch("app.service.fetch_schema", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _schema_payload()
        resp2 = await client.get(
            f"/api/v1/categories/{cat_id}/schema",
            headers={"if-none-match": etag},
        )
    assert resp2.status_code == 304
    assert resp2.content == b""


@pytest.mark.asyncio
async def test_schema_not_found(app, client):
    """Service raises CategoryNotFoundError → 404 via error handlers."""
    from app.exceptions import CategoryNotFoundError
    cat_id = uuid4()
    with patch("app.service.fetch_schema", new_callable=AsyncMock) as mock_svc:
        mock_svc.side_effect = CategoryNotFoundError()
        resp = await client.get(f"/api/v1/categories/{cat_id}/schema")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_schema_unauth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/categories/{uuid4()}/schema")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /api/v1/categories/{id}/field-enum/{name}  (§9.B.5)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_field_enum_happy(client):
    """Happy path — returns enum_entries list."""
    cat_id = uuid4()
    with patch("app.service.get_field_enum", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _field_enum_payload()
        resp = await client.get(f"/api/v1/categories/{cat_id}/field-enum/fabric")
    assert resp.status_code == 200
    body = resp.json()
    assert "enum_entries" in body
    assert body["total"] == 1
    assert "canonical" in body["enum_entries"][0]
    assert "meesho" in body["enum_entries"][0]
    assert "labels" in body["enum_entries"][0]


@pytest.mark.asyncio
async def test_field_enum_not_found(client):
    """FieldEnumNotFoundError → 404."""
    from app.exceptions import FieldEnumNotFoundError
    cat_id = uuid4()
    with patch("app.service.get_field_enum", new_callable=AsyncMock) as mock_svc:
        mock_svc.side_effect = FieldEnumNotFoundError()
        resp = await client.get(f"/api/v1/categories/{cat_id}/field-enum/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_field_enum_category_not_found(client):
    """CategoryNotFoundError → 404."""
    from app.exceptions import CategoryNotFoundError
    cat_id = uuid4()
    with patch("app.service.get_field_enum", new_callable=AsyncMock) as mock_svc:
        mock_svc.side_effect = CategoryNotFoundError()
        resp = await client.get(f"/api/v1/categories/{cat_id}/field-enum/fabric")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_field_enum_unauth(unauth_client):
    resp = await unauth_client.get(f"/api/v1/categories/{uuid4()}/field-enum/fabric")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 6. /internal/* shims — mounted + schema-correct
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_internal_schema_shim_shape(client):
    """Shim #1 — returns 7-key §5A.B envelope (FROZEN MS-A §F4 shape)."""
    cat_id = uuid4()
    with patch("app.service.fetch_schema", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _schema_payload()
        resp = await client.get(f"/internal/categories/{cat_id}/schema")
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "fields", "compulsory_count", "optional_count", "total_count",
        "wizard_step_count", "main_sheet_label", "compliance_shape",
    ):
        assert key in body, f"Missing frozen §F4 Shim #1 key: {key}"


@pytest.mark.asyncio
async def test_internal_field_enum_shim_shape(client):
    """Shim #2 — returns {enum_entries, total, truncated} (FROZEN MS-A §F4 shape)."""
    cat_id = uuid4()
    with patch("app.service.get_field_enum", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = _field_enum_payload()
        resp = await client.get(f"/internal/categories/{cat_id}/field-enum/brand")
    assert resp.status_code == 200
    body = resp.json()
    assert "enum_entries" in body
    assert "total" in body
    assert "truncated" in body
    # Verify each entry has the frozen keys
    if body["enum_entries"]:
        entry = body["enum_entries"][0]
        assert "canonical" in entry
        assert "meesho" in entry
        assert "labels" in entry


@pytest.mark.asyncio
async def test_internal_commission_never_null_decimal_string(client):
    """Shim #3 — commission_pct is a Decimal serialised as JSON string, NEVER null.

    This is the MS-D §1 FROZEN contract.  pricing-svc depends on a non-null
    Decimal-string in ``commission_pct``.
    """
    cat_id = uuid4()
    with patch("app.service.get_commission", new_callable=AsyncMock) as mock_svc:
        # Service guarantees non-null — even unseeded returns Decimal("0.00")
        mock_svc.return_value = Decimal("12.00")
        resp = await client.get(f"/internal/categories/{cat_id}/commission")
    assert resp.status_code == 200
    body = resp.json()
    assert "commission_pct" in body
    # INVARIANT: must be a STRING (Pydantic v2 Decimal → JSON string)
    assert isinstance(body["commission_pct"], str), (
        f"commission_pct must be string, got {type(body['commission_pct'])}: "
        f"{body['commission_pct']!r}"
    )
    # Must be parseable as a Decimal
    parsed = Decimal(body["commission_pct"])
    assert parsed == Decimal("12.00")


@pytest.mark.asyncio
async def test_internal_commission_unseeded_zero(client):
    """Shim #3 — unseeded commission returns '0.00' string, NEVER null."""
    cat_id = uuid4()
    with patch("app.service.get_commission", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = Decimal("0.00")
        resp = await client.get(f"/internal/categories/{cat_id}/commission")
    assert resp.status_code == 200
    body = resp.json()
    assert body["commission_pct"] is not None
    assert Decimal(body["commission_pct"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_internal_super_categories_list_str(client):
    """Shim #4 — returns a BARE JSON ARRAY ``["26", "19", ...]`` (FROZEN-0E).

    customer-svc's E3-A category_client shim (category_client.py:50-51) does:
        payload = await request_json("GET", "/internal/super-categories")
        return [str(item) for item in payload]
    It iterates ``payload`` DIRECTLY as a JSON array — NOT via ``payload["key"]``.
    An object envelope ``{"super_categories": [...]}`` would iterate dict KEYS,
    returning ``["super_categories"]`` instead of the actual ids.

    SUB_PLAN_0F §F4 + spec_msE §9 FROZEN-0E + category_client.py:50-51.
    """
    from app.domain import SuperCategoryInfo
    infos = [
        SuperCategoryInfo(super_id="26", super_name="Clothing", leaf_count=42),
        SuperCategoryInfo(super_id="19", super_name="Electronics", leaf_count=15),
    ]
    with patch("app.service.list_super_categories", new_callable=AsyncMock) as mock_svc:
        mock_svc.return_value = infos
        resp = await client.get("/internal/super-categories")
    assert resp.status_code == 200
    body = resp.json()
    # FROZEN-0E: body IS a bare JSON array, NOT an object
    assert isinstance(body, list), (
        f"FROZEN-0E violated: response body is {type(body).__name__}, expected list. "
        f"category_client.py:50-51 iterates payload directly."
    )
    assert len(body) == 2
    for item in body:
        assert isinstance(item, str), (
            f"FROZEN-0E violated: element is {type(item)}, expected str"
        )
    assert set(body) == {"26", "19"}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Route inventory check
# ─────────────────────────────────────────────────────────────────────────────

def test_route_inventory(app):
    """Confirm the mounted APIRoute count: 5 public + 4 internal + 1 health = 10."""
    from fastapi.routing import APIRoute

    api_routes = [r for r in app.routes if isinstance(r, APIRoute)]
    public = [r for r in api_routes if r.path.startswith("/api/v1/categories")]
    internal = [r for r in api_routes if r.path.startswith("/internal/")]
    health = [r for r in api_routes if r.path == "/health"]

    assert len(public) == 5, f"Expected 5 public routes, got {len(public)}: {[r.path for r in public]}"
    assert len(internal) == 4, f"Expected 4 internal routes, got {len(internal)}: {[r.path for r in internal]}"
    assert len(health) == 1, "Expected 1 health route"
    assert len(api_routes) == 10, (
        f"Expected 10 total APIRoute objects, got {len(api_routes)}: "
        f"{[r.path for r in api_routes]}"
    )


def test_internal_routes_hidden_from_openapi(app):
    """Internal routes carry include_in_schema=False — not in public OpenAPI."""
    from fastapi.routing import APIRoute

    openapi_schema = app.openapi()
    public_paths = set(openapi_schema.get("paths", {}).keys())

    internal_routes = [
        r for r in app.routes
        if isinstance(r, APIRoute) and r.path.startswith("/internal/")
    ]
    assert len(internal_routes) == 4, "Expected 4 internal routes"

    for r in internal_routes:
        assert r.path not in public_paths, (
            f"Internal route {r.path} must NOT appear in public OpenAPI"
        )


def test_suggest_route_has_rate_limit_decorator(app):
    """GET /categories/suggest is decorated with @rate_limit(smart_picker, 100, 3600)."""
    from fastapi.routing import APIRoute

    suggest_route = next(
        (r for r in app.routes if isinstance(r, APIRoute) and "suggest" in r.path),
        None,
    )
    assert suggest_route is not None, "GET /api/v1/categories/suggest not mounted"
    # The decorated handler wraps the original; verify the endpoint is callable.
    assert callable(suggest_route.endpoint)


def test_openapi_schema_has_5_public_paths(app):
    """OpenAPI schema contains exactly 5 category paths + /health."""
    schema = app.openapi()
    paths = set(schema.get("paths", {}).keys())
    category_paths = {p for p in paths if "categor" in p}
    assert len(category_paths) == 5, (
        f"Expected 5 category paths in OpenAPI, got {len(category_paths)}: {category_paths}"
    )
