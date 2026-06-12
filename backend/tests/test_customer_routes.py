"""Route-level tests for §8 customer endpoints.

Tests all 5 endpoints per §8.B using the ``iam_client`` fixture pattern from
``tests/integration/conftest.py`` (ASGI transport against live app, no get_db override,
uses ``settings.DATABASE_URL`` — localhost:5432 ephemeral in test env).

Coverage matrix
---------------
- GET /seller-profile: no row → 404 customer.profile.not_found; after PATCH → 200.
- PATCH /seller-profile: valid base → 200 + §8.E SellerProfileResponse keys;
  invalid pincode → 422; subset semantics preserves existing fields.
- PATCH /seller-profile/active-categories: unknown super_id → 422
  validation.super_category.unknown; empty list → 422.
- PATCH /seller-profile/compliance/{super_id}: super_id not in active → 404
  customer.super_category.not_declared; Grocery without fssai_license_number → 422
  customer.compliance.missing_fields; valid Grocery payload → 200.
- GET /seller-profile/required-fields: new seller → 200, all completed=False;
  after full PATCH → blocking base fields completed=True + onboarding_complete=True.
- Each protected endpoint without Bearer → 401 auth.token_missing.

Integration strategy
--------------------
``iam_client`` provides a live ASGI client with access_token pinned in headers (via
/otp/verify after direct Valkey OTP seed).  All customer service calls go through
the REAL service layer against the ephemeral 5432 DB (schema created by ``db_engine``).

The ``iam_client`` fixture lives in ``tests/integration/conftest.py``.  This test
file imports it explicitly via ``pytest_plugins`` (the conftest is in a sub-package
path that pytest discovers automatically from the configured testpaths).

Categories table caveat
-----------------------
The ephemeral DB (create_all) has ZERO category rows (seed scripts are not run).
``customer.service.set_active_categories`` validates each super_id against
``SELECT DISTINCT super_id FROM categories``; with an empty categories table,
ANY super_id is invalid.

Workaround for tests that need to exercise the "valid super_id" path:
monkeypatch ``app.modules.customer.service._get_super_id_set`` to return a frozen
set containing the test super_ids.  The 401 tests still work without monkeypatching
(they fail before the service is called).
"""

from __future__ import annotations

import hashlib
import json as _json
import time as _time
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import _DEV_DATABASE_URL, _valkey_base

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Phone for test OTP seed — all-digit, within non-routable +9155500XXXXX range
# ─────────────────────────────────────────────────────────────────────────────
_CUSTOMER_TEST_PHONE = "+915550099901"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: customer_client — authenticated ASGI client + Valkey seeded
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(loop_scope="function")
async def customer_client():
    """Authenticated ASGI client for customer route tests.

    Self-contained: creates its own ephemeral schema, overrides FastAPI
    dependencies (get_db + get_valkey_otp), patches module-level singletons
    that bypass DI (audit_mw.AsyncSessionLocal + shared.valkey cache client),
    seeds an OTP, and obtains a Bearer token via /otp/verify.

    NullPool on both the fixture engine AND the audit_mw patch prevents
    the asyncpg pool from binding connections to a specific event loop,
    which is the root cause of the ``RuntimeError: Task got Future attached
    to a different loop`` seen with pooled engines in tests.

    Valkey cache (DB 3) is patched at the module-level singleton in
    ``app.shared.valkey`` so ``core/cache.py get_or_set`` (called by
    customer_service.get_required_fields) reaches the test Valkey, not
    the production port from settings.VALKEY_URL.
    """
    import os
    import redis.asyncio as _redis_lib
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        async_sessionmaker,
        create_async_engine,
    )

    import app.core.middleware.audit_mw as _audit_mw
    import app.shared.valkey as _valkey_module
    from app.shared.database import Base, get_db
    from app.shared.valkey import get_valkey_otp

    # ── 1. Build an ephemeral NullPool engine + schema ─────────────────────
    # NullPool: no connection reuse → no asyncpg Future loop-binding issues.
    #
    # CI Gate-4 pass-2 fix: the DB URL now flows through ``_DEV_DATABASE_URL``
    # (TEST_DATABASE_URL > DEV_DATABASE_URL > baked K3s-dev DSN) — identical
    # precedence to every other DB fixture in tests/conftest.py.  The previous
    # ``localhost:5432`` literal default pointed at the wrong port (CI maps the
    # ephemeral meesell_test db on 5433) → asyncpg connection failures.
    db_url = _DEV_DATABASE_URL
    engine: AsyncEngine = create_async_engine(db_url, poolclass=NullPool)

    # Provision-aware schema setup (mirrors the db_engine fixture in
    # tests/conftest.py): when ``TEST_DATABASE_URL`` is set (CI), the
    # session-scoped ``_provision_test_schema`` autouse fixture has already run
    # ``alembic upgrade head`` against meesell_test — building the pg_trgm
    # extension + the category GIN trigram indexes that ``create_all`` cannot
    # reproduce.  Running drop_all/create_all here would DESTROY those indexes
    # AND contend with the per-test ``db`` transaction on the shared physical
    # db.  So we SKIP the drop_all/create_all when provisioned and let alembic
    # own the schema.  Off-CI (laptop, no TEST_DATABASE_URL) the prior
    # drop_all+create_all per-fixture behaviour is preserved byte-for-byte.
    _provisioned = bool(os.environ.get("TEST_DATABASE_URL"))
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    # ── 1b. SAVEPOINT per-test isolation (CI Gate-4 pass-3, §2.2-ii) ───────
    # The route handlers really call ``await session.commit()`` (e.g. the
    # PATCH /seller-profile flow persists a SellerProfile row).  The previous
    # ``_db_override`` opened a fresh session per call and committed straight
    # into the shared ``meesell_test`` db with NOTHING ever cleaning the rows up
    # → committed rows (incl. the fixed-phone ``users`` row minted by /otp/verify)
    # accumulated session-wide → ``ix_users_phone`` / ``products_user_id_fkey``
    # IntegrityErrors AND cross-test contamination.
    #
    # THE FIX: a SINGLE test-scoped connection with an OPEN outer transaction.
    # Every override session binds to THAT connection via an
    # ``async_sessionmaker(join_transaction_mode="create_savepoint")`` — so a
    # handler ``commit()`` RELEASES a SAVEPOINT instead of ending the outer txn.
    # On teardown ``outer.rollback()`` discards EVERYTHING the test wrote, so the
    # shared ``meesell_test`` is left byte-clean for the next test.  The audit_mw
    # ``AsyncSessionLocal`` patch (3a below) binds to the SAME connection + the
    # SAME savepoint sessionmaker, so audit writes are rolled back too (else they
    # would leak past the outer rollback).
    #
    # LOCAL-DEV GUARD: off-CI the connection is on the ephemeral schema this
    # fixture just built (drop_all/create_all) and is dropped on teardown — the
    # outer-rollback leaves that ephemeral DB unchanged; the live dev DB is never
    # mutated (this fixture only ever touches ``_DEV_DATABASE_URL`` == the test
    # DB in CI, and an ephemeral local schema off-CI).
    #
    # RISK (SQLAlchemy ≥2.0 required for ``join_transaction_mode`` — stack is
    # 2.0.x): a handler that writes via a RAW connection OUTSIDE the injected
    # session would escape the savepoint.  Verified by grep that the customer
    # service layer writes ONLY through the injected AsyncSession (no raw
    # connection bypass).
    shared_conn = await engine.connect()
    outer_txn = await shared_conn.begin()
    TestSession = async_sessionmaker(
        bind=shared_conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    # ── 2. Override FastAPI DI (get_db + get_valkey_otp) ───────────────────
    # CI Gate-4 pass-2 fix: resolve the Valkey base via the shared
    # ``_valkey_base()`` helper (TEST_VALKEY_URL > VALKEY_URL >
    # CORE_TEST_VALKEY_URL > redis://localhost:6379, with the trailing
    # ``/<db>`` suffix stripped so the ``/0`` and ``/3`` appends below never
    # produce the ``/0/0`` double-suffix trap).  The previous hardcoded
    # ``redis://localhost:6379`` default ignored CI's TEST_VALKEY_URL/VALKEY_URL
    # (6381): every /otp/verify reached a refused 6379, so the OTP seed/verify
    # path failed and the customer routes returned 429 across the suite.
    valkey_base = _valkey_base()

    _otp_clients: list = []

    async def _otp_override():
        c = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
        _otp_clients.append(c)
        return c

    async def _db_override():
        # Sessions bind to the shared connection (savepoint mode): a handler
        # ``commit()`` releases a SAVEPOINT, never the outer transaction.  Do
        # NOT close the shared connection here — it is owned by the fixture and
        # rolled back wholesale at teardown.
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

    # ── 3. Patch module-level singletons that bypass DI ───────────────────
    # 3a. audit_mw uses AsyncSessionLocal directly (not via Depends).
    #     Patch it to use our NullPool TestSession so it can write audit rows
    #     without hitting the production engine's pool (which may be bound
    #     to a different event loop context).
    _original_audit_session_local = _audit_mw.AsyncSessionLocal
    _audit_mw.AsyncSessionLocal = TestSession  # type: ignore[attr-defined]

    # 3b. core/cache.py calls get_valkey_cache() which reads the module-level
    #     _cache_client singleton in app.shared.valkey.  Force it to the test
    #     Valkey at DB 3 so get_required_fields can cache without hitting 6381.
    _original_cache_client = _valkey_module._cache_client
    _test_cache_client = _redis_lib.from_url(f"{valkey_base}/3", decode_responses=True)
    _valkey_module._cache_client = _test_cache_client  # type: ignore[assignment]

    # ── 4. Seed OTP in test Valkey DB 0 ───────────────────────────────────
    otp_seed_client = _redis_lib.from_url(f"{valkey_base}/0", decode_responses=True)
    try:
        await otp_seed_client.flushdb()
    except Exception:
        pass

    phone = _CUSTOMER_TEST_PHONE
    otp = "888000"
    otp_hash = hashlib.sha256(otp.encode("utf-8")).hexdigest()
    payload = _json.dumps(
        {"otp_hash": otp_hash, "attempts": 0, "expires_at": int(_time.time()) + 300}
    )
    await otp_seed_client.set(f"otp:{phone}", payload, ex=300)

    # ── 5. Boot lifespan + obtain Bearer token ─────────────────────────────
    # Track the lifespan-created engine + Valkey client so we can explicitly
    # dispose/close them AFTER the lifespan exits (still inside the async
    # context) to drain pending asyncpg pool callbacks before the function
    # loop is torn down — prevents ``Event loop is closed`` teardown errors.
    _lifespan_db_engine = None
    _lifespan_valkey = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        async with app.router.lifespan_context(app):
            _lifespan_db_engine = getattr(app.state, "db_engine", None)
            _lifespan_valkey = getattr(app.state, "valkey", None)
            resp = await ac.post(
                "/api/v1/auth/otp/verify", json={"phone": phone, "otp": otp}
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"customer_client fixture: /otp/verify failed "
                    f"({resp.status_code}): {resp.text}"
                )
            body = resp.json()
            ac.headers["Authorization"] = f"Bearer {body['access_token']}"
            me_resp = await ac.get("/api/v1/auth/me")
            ac.test_user_id = me_resp.json()["user_id"]  # type: ignore[attr-defined]
            yield ac

        # Lifespan has exited (lifespan teardown already ran dispose/aclose).
        # Explicitly dispose again while still inside the AsyncClient context
        # and the function loop to drain any residual asyncpg pool callbacks.
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

    # ── 6. Teardown ────────────────────────────────────────────────────────
    # Restore module-level singletons.
    _audit_mw.AsyncSessionLocal = _original_audit_session_local  # type: ignore[attr-defined]
    _valkey_module._cache_client = _original_cache_client  # type: ignore[assignment]

    for c in _otp_clients:
        try:
            await c.aclose()
        except Exception:
            pass
    try:
        await _test_cache_client.aclose()
    except Exception:
        pass
    try:
        await otp_seed_client.aclose()
    except Exception:
        pass

    # SAVEPOINT teardown (CI Gate-4 pass-3): roll back the outer transaction so
    # every row the test committed (released as savepoints) is discarded → the
    # shared meesell_test is left byte-clean.  Close the shared connection before
    # any drop_all / dispose.
    try:
        await outer_txn.rollback()
    except Exception:
        pass
    try:
        await shared_conn.close()
    except Exception:
        pass

    # Provision-aware teardown: when CI-provisioned, alembic owns the schema —
    # dropping it here would wipe the pg_trgm/GIN indexes for the rest of the
    # session and deadlock against other open transactions.  Only drop when we
    # created the schema ourselves (laptop / no TEST_DATABASE_URL).
    if not _provisioned:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    app.dependency_overrides.pop(get_valkey_otp, None)
    app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_VALID_PROFILE_PAYLOAD: dict[str, Any] = {
    "manufacturer_name": "Apex Textiles Pvt Ltd",
    "manufacturer_address": "Plot 12, Industrial Estate, Coimbatore, Tamil Nadu",
    "manufacturer_pincode": "641001",
    "packer_name": "Apex Textiles Pvt Ltd",
    "packer_address": "Plot 12, Industrial Estate, Coimbatore, Tamil Nadu",
    "packer_pincode": "641001",
    "country_of_origin": "India",
}

_REQUIRED_SELLER_PROFILE_KEYS = {
    "user_id",
    "manufacturer_name",
    "manufacturer_address",
    "manufacturer_pincode",
    "packer_name",
    "packer_address",
    "packer_pincode",
    "importer_name",
    "importer_address",
    "importer_pincode",
    "country_of_origin",
    "active_super_categories",
    "compliance_extensions",
    "onboarding_complete",
    "created_at",
    "updated_at",
}


# ─────────────────────────────────────────────────────────────────────────────
# §8.B.1 — GET /api/v1/seller-profile
# ─────────────────────────────────────────────────────────────────────────────

class TestGetSellerProfile:
    """Tests for GET /api/v1/seller-profile (§8.B.1)."""

    async def test_get_profile_when_no_row_returns_404(self, customer_client):
        """GET /seller-profile before any PATCH → 404 customer.profile.not_found."""
        resp = await customer_client.get("/api/v1/seller-profile")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["validation_message_id"] == "customer.profile.not_found"

    async def test_get_profile_after_upsert_returns_200(self, customer_client):
        """GET /seller-profile after a successful PATCH → 200 + SellerProfileResponse."""
        patch_resp = await customer_client.patch(
            "/api/v1/seller-profile",
            json=_VALID_PROFILE_PAYLOAD,
        )
        assert patch_resp.status_code == 200, (
            f"PATCH failed: {patch_resp.status_code}: {patch_resp.text}"
        )

        resp = await customer_client.get("/api/v1/seller-profile")
        assert resp.status_code == 200
        body = resp.json()
        assert _REQUIRED_SELLER_PROFILE_KEYS.issubset(set(body.keys())), (
            f"Missing keys: {_REQUIRED_SELLER_PROFILE_KEYS - set(body.keys())}"
        )
        assert body["manufacturer_name"] == _VALID_PROFILE_PAYLOAD["manufacturer_name"]
        assert body["country_of_origin"] == "India"

    async def test_get_profile_without_bearer_returns_401(self, customer_client):
        """GET /seller-profile without Authorization → 401."""
        # Remove the Authorization header for this request.
        resp = await customer_client.get(
            "/api/v1/seller-profile",
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert "validation_message_id" in body


# ─────────────────────────────────────────────────────────────────────────────
# §8.B.2 — PATCH /api/v1/seller-profile
# ─────────────────────────────────────────────────────────────────────────────

class TestPatchSellerProfile:
    """Tests for PATCH /api/v1/seller-profile (§8.B.2)."""

    async def test_patch_with_valid_base_returns_200_and_seller_profile_response(
        self, customer_client
    ):
        """PATCH /seller-profile with valid base fields → 200 + SellerProfileResponse."""
        resp = await customer_client.patch(
            "/api/v1/seller-profile",
            json=_VALID_PROFILE_PAYLOAD,
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert _REQUIRED_SELLER_PROFILE_KEYS.issubset(set(body.keys()))
        assert body["manufacturer_name"] == "Apex Textiles Pvt Ltd"
        assert body["manufacturer_pincode"] == "641001"
        assert body["country_of_origin"] == "India"
        assert isinstance(body["active_super_categories"], list)
        assert isinstance(body["compliance_extensions"], dict)
        assert isinstance(body["onboarding_complete"], bool)

    async def test_patch_with_invalid_pincode_returns_422(self, customer_client):
        """PATCH /seller-profile with non-6-digit pincode → 422.

        ``Field(pattern=r'^\\d{6}$')`` on ``manufacturer_pincode`` fires at
        Pydantic schema layer — status 422 before service is called.
        """
        resp = await customer_client.patch(
            "/api/v1/seller-profile",
            json={**_VALID_PROFILE_PAYLOAD, "manufacturer_pincode": "ABC123"},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for invalid pincode, got {resp.status_code}: {resp.text}"
        )

    async def test_patch_with_pincode_too_short_returns_422(self, customer_client):
        """PATCH /seller-profile with a 4-digit pincode → 422."""
        resp = await customer_client.patch(
            "/api/v1/seller-profile",
            json={**_VALID_PROFILE_PAYLOAD, "packer_pincode": "1234"},
        )
        assert resp.status_code == 422

    async def test_patch_subset_semantics_preserves_existing_fields(self, customer_client):
        """Subsequent PATCH with partial body preserves fields not in payload."""
        # First upsert.
        await customer_client.patch(
            "/api/v1/seller-profile",
            json=_VALID_PROFILE_PAYLOAD,
        )
        # Second PATCH with only country_of_origin.
        resp = await customer_client.patch(
            "/api/v1/seller-profile",
            json={"country_of_origin": "China"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["manufacturer_name"] == _VALID_PROFILE_PAYLOAD["manufacturer_name"]
        assert body["country_of_origin"] == "China"

    async def test_patch_without_bearer_returns_401(self, customer_client):
        """PATCH /seller-profile without Authorization → 401."""
        resp = await customer_client.patch(
            "/api/v1/seller-profile",
            json=_VALID_PROFILE_PAYLOAD,
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# §8.B.3 — PATCH /api/v1/seller-profile/active-categories
# ─────────────────────────────────────────────────────────────────────────────

class TestPatchActiveCategories:
    """Tests for PATCH /api/v1/seller-profile/active-categories (§8.B.3)."""

    async def test_unknown_super_id_returns_422(self, customer_client):
        """PATCH /seller-profile/active-categories with an unknown super_id → 422.

        Categories table is EMPTY in the ephemeral test DB — any super_id is unknown.
        Service raises InvalidSuperCategoryError (422 validation.super_category.unknown).
        """
        await customer_client.patch(
            "/api/v1/seller-profile",
            json=_VALID_PROFILE_PAYLOAD,
        )

        resp = await customer_client.patch(
            "/api/v1/seller-profile/active-categories",
            json={"active_super_categories": ["99999"]},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for unknown super_id, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["validation_message_id"] == "validation.super_category.unknown"

    async def test_empty_array_returns_422(self, customer_client):
        """PATCH /seller-profile/active-categories with empty list → 422.

        ``PatchActiveCategoriesRequest`` has ``min_length=1``.
        """
        await customer_client.patch("/api/v1/seller-profile", json=_VALID_PROFILE_PAYLOAD)

        resp = await customer_client.patch(
            "/api/v1/seller-profile/active-categories",
            json={"active_super_categories": []},
        )
        assert resp.status_code == 422

    async def test_patch_active_categories_without_bearer_returns_401(self, customer_client):
        """PATCH /seller-profile/active-categories without Authorization → 401."""
        resp = await customer_client.patch(
            "/api/v1/seller-profile/active-categories",
            json={"active_super_categories": ["26"]},
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401

    async def test_patch_active_categories_with_valid_super_id_returns_200(
        self, customer_client, monkeypatch
    ):
        """PATCH /seller-profile/active-categories → 200 when super_id is valid.

        Monkeypatches ``customer.service._get_super_id_set`` to return ``{"26"}``
        so the test does not require a seeded categories table.
        """
        import app.modules.customer.service as _customer_service

        async def _mock_get_super_id_set(db):  # noqa: ARG001
            return {"26", "19", "13", "16", "80"}

        monkeypatch.setattr(_customer_service, "_get_super_id_set", _mock_get_super_id_set)

        await customer_client.patch("/api/v1/seller-profile", json=_VALID_PROFILE_PAYLOAD)

        resp = await customer_client.patch(
            "/api/v1/seller-profile/active-categories",
            json={"active_super_categories": ["26"]},
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["active_super_categories"] == ["26"]


# ─────────────────────────────────────────────────────────────────────────────
# §8.B.4 — PATCH /api/v1/seller-profile/compliance/{super_id}
# ─────────────────────────────────────────────────────────────────────────────

class TestPatchComplianceExtension:
    """Tests for PATCH /api/v1/seller-profile/compliance/{super_id} (§8.B.4)."""

    async def test_compliance_for_super_id_not_in_active_returns_404(
        self, customer_client
    ):
        """PATCH /seller-profile/compliance/26 when 26 not in active → 404.

        Service raises SuperCategoryNotDeclaredError
        (404 customer.super_category.not_declared).
        """
        await customer_client.patch("/api/v1/seller-profile", json=_VALID_PROFILE_PAYLOAD)

        resp = await customer_client.patch(
            "/api/v1/seller-profile/compliance/26",
            json={"fssai_license_number": "10012345678901", "fssai_expiry": "2027-12-31"},
        )
        assert resp.status_code == 404, (
            f"Expected 404 for undeclared super_id, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["validation_message_id"] == "customer.super_category.not_declared"

    async def test_grocery_compliance_without_fssai_returns_422(
        self, customer_client, monkeypatch
    ):
        """PATCH /seller-profile/compliance/26 (Grocery) without fssai_license_number → 422.

        Per master ruling 4 + §8.F: Grocery (super_id='26') compulsory=True.
        Missing required key → ComplianceExtensionMissingFieldsError (422
        customer.compliance.missing_fields).
        """
        import app.modules.customer.service as _customer_service

        async def _mock_get_super_id_set(db):  # noqa: ARG001
            return {"26", "19", "13", "16", "80"}

        monkeypatch.setattr(_customer_service, "_get_super_id_set", _mock_get_super_id_set)

        await customer_client.patch("/api/v1/seller-profile", json=_VALID_PROFILE_PAYLOAD)
        patch_resp = await customer_client.patch(
            "/api/v1/seller-profile/active-categories",
            json={"active_super_categories": ["26"]},
        )
        assert patch_resp.status_code == 200, (
            f"Failed to set active categories: {patch_resp.text}"
        )

        # Attempt compliance patch WITHOUT required fssai_license_number.
        resp = await customer_client.patch(
            "/api/v1/seller-profile/compliance/26",
            json={"fssai_expiry": "2027-12-31"},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for missing fssai_license_number, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert body["validation_message_id"] == "customer.compliance.missing_fields"

    async def test_grocery_compliance_with_valid_payload_returns_200(
        self, customer_client, monkeypatch
    ):
        """PATCH /seller-profile/compliance/26 with valid Grocery payload → 200."""
        import app.modules.customer.service as _customer_service

        async def _mock_get_super_id_set(db):  # noqa: ARG001
            return {"26", "19", "13", "16", "80"}

        monkeypatch.setattr(_customer_service, "_get_super_id_set", _mock_get_super_id_set)

        await customer_client.patch("/api/v1/seller-profile", json=_VALID_PROFILE_PAYLOAD)
        await customer_client.patch(
            "/api/v1/seller-profile/active-categories",
            json={"active_super_categories": ["26"]},
        )

        resp = await customer_client.patch(
            "/api/v1/seller-profile/compliance/26",
            json={"fssai_license_number": "10012345678901", "fssai_expiry": "2027-12-31"},
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert "26" in body["compliance_extensions"]

    async def test_compliance_without_bearer_returns_401(self, customer_client):
        """PATCH /seller-profile/compliance/26 without Authorization → 401."""
        resp = await customer_client.patch(
            "/api/v1/seller-profile/compliance/26",
            json={"fssai_license_number": "10012345678901"},
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# §8.B.5 — GET /api/v1/seller-profile/required-fields
# ─────────────────────────────────────────────────────────────────────────────

class TestGetRequiredFields:
    """Tests for GET /api/v1/seller-profile/required-fields (§8.B.5)."""

    async def test_required_fields_for_new_seller_returns_200_all_incomplete(
        self, customer_client
    ):
        """GET /seller-profile/required-fields for new seller → 200, all completed=False."""
        resp = await customer_client.get("/api/v1/seller-profile/required-fields")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert "base_fields" in body
        assert "extension_fields" in body
        assert "completed" in body
        assert isinstance(body["base_fields"], list)
        assert len(body["base_fields"]) == 10, (
            f"Expected 10 base fields, got {len(body['base_fields'])}"
        )
        assert isinstance(body["extension_fields"], dict)
        # For a new seller with no profile, all 10 base fields should be incomplete.
        completed = body["completed"]
        for key, val in completed.items():
            assert val is False, (
                f"Expected field {key!r} to be incomplete for new seller, got True"
            )

    async def test_required_fields_after_full_patch_shows_blocking_fields_completed(
        self, customer_client
    ):
        """GET /seller-profile/required-fields after full PATCH → blocking fields = True.

        After patching all 7 blocking base fields (6 LM + country_of_origin),
        ``onboarding_complete`` is True (no compulsory super categories declared).
        The required-fields response ``completed`` map should reflect this.
        """
        resp = await customer_client.patch(
            "/api/v1/seller-profile",
            json=_VALID_PROFILE_PAYLOAD,
        )
        assert resp.status_code == 200
        assert resp.json()["onboarding_complete"] is True

        resp2 = await customer_client.get("/api/v1/seller-profile/required-fields")
        assert resp2.status_code == 200
        body = resp2.json()
        completed = body["completed"]
        blocking_fields = (
            "manufacturer_name",
            "manufacturer_address",
            "manufacturer_pincode",
            "packer_name",
            "packer_address",
            "packer_pincode",
            "country_of_origin",
        )
        for field in blocking_fields:
            assert completed.get(field) is True, (
                f"Expected base field {field!r} to be completed, got {completed.get(field)}"
            )

    async def test_required_fields_without_bearer_returns_401(self, customer_client):
        """GET /seller-profile/required-fields without Authorization → 401."""
        resp = await customer_client.get(
            "/api/v1/seller-profile/required-fields",
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401
