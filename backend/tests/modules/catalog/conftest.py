"""Catalog-module pytest fixtures.

Per BACKEND_ARCHITECTURE.md §10.J:

* ``user`` — a logged-in seller with a completed profile.
* ``other_user`` — a second seller (for cross-tenant assertions).
* ``beauty_category`` — the canonical Beauty (super_id=19) leaf with a
  compliance-shape="collapsed" schema so the §10.J test 4 fixture lands
  on real data.  Includes inline schema with a static-enum field +
  compulsory + optional markers.
* ``stub_call_gemini`` — replaces :func:`ai_ops.client.call_gemini` with
  a deterministic stub for the Auto-fill happy path AND for the budget
  exhaustion fallback path.

The ``db`` fixture is the top-level conftest's ``db_session`` — fresh
ephemeral test DB (Postgres on :5432 via ``DATABASE_URL`` env in
``tests/conftest.py``).  The DB is reset per test (drop_all +
create_all).

``catalog_route_client`` fixture (PR #435 re-do / Gate-4 loop-affinity fix)
adds D1+D2: function-loop NullPool engine + ``get_db`` override + ``audit_mw``
patch + fresh ``_otp_client`` swap.  Mirrors ``integration/conftest.py::iam_client``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio

from app.shared.models.category import Category as CategoryORM
from app.shared.models.seller_profile import SellerProfile as SellerProfileORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User


@pytest_asyncio.fixture(loop_scope="function")
async def db(db_session):
    """Alias for the ephemeral test DB session.

    Matches the §8 customer-module convention so the test signatures
    read naturally and so the same fixture name is used across modules.
    """
    yield db_session


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user(db, phone: str) -> User:
    """Insert a User row and return it."""
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture(loop_scope="function")
async def user(db) -> User:
    return await _seed_user(db, phone="+915550010001")


@pytest_asyncio.fixture(loop_scope="function")
async def other_user(db) -> User:
    return await _seed_user(db, phone="+915550010002")


# ─────────────────────────────────────────────────────────────────────────────
# Seller profile — Beauty-eligible
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_beauty_eligible_profile(db, user_id: UUID) -> SellerProfileORM:
    """Insert a seller_profile row that satisfies Beauty (super_id=19) eligibility.

    Per §8 compliance: Beauty is ``compulsory=True`` with required keys
    ``license_registration_number / license_registration_type /
    license_expiry_date``.  Profile carries all 3 + the 7 mandatory base
    fields so :func:`customer.service.assert_eligible_for_super_id`
    returns without raising.
    """
    profile = SellerProfileORM(
        user_id=user_id,
        manufacturer_name="Test Mfr",
        manufacturer_address="1 Test Rd",
        manufacturer_pincode="560001",
        packer_name="Test Packer",
        packer_address="1 Test Rd",
        packer_pincode="560001",
        importer_name=None,
        importer_address=None,
        importer_pincode=None,
        country_of_origin="India",
        active_super_categories=["19"],
        compliance_extensions={
            "19": {
                "license_registration_number": "LIC-12345",
                "license_registration_type": "CDSCO",
                "license_expiry_date": "2030-12-31",
            }
        },
        onboarding_complete=True,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


@pytest_asyncio.fixture(loop_scope="function")
async def beauty_profile(db, user) -> SellerProfileORM:
    return await _seed_beauty_eligible_profile(db, user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Beauty / Eye-Serum category + template (collapsed compliance shape)
# ─────────────────────────────────────────────────────────────────────────────
def _build_eye_serum_schema() -> dict[str, Any]:
    """Return the §5A.B 7-key envelope for an Eye-Serum-shaped category.

    Schema carries:

    * 2 compulsory text_short fields (``product_name``, ``brand_name``).
    * 1 compulsory dropdown w/ static enum (``application_area``).
    * 1 optional text_long field (``product_description``).
    * super_id=19 + compliance_shape="collapsed" per §5A.F.
    """
    return {
        "fields": [
            {
                "name": "Product Name",
                "canonical_name": "product_name",
                "marker": "compulsory",
                "data_type": "text",
                "primitive": "text_short",
                "help_text": "Title for your listing.",
                "is_advanced": False,
                "enum_resolver": None,
                "validation_message_ids": ["validation.product_name.too_long"],
            },
            {
                "name": "Brand Name",
                "canonical_name": "brand_name",
                "marker": "compulsory",
                "data_type": "text",
                "primitive": "text_short",
                "help_text": "Brand for the listing.",
                "is_advanced": False,
                "enum_resolver": None,
                "validation_message_ids": [],
            },
            {
                "name": "Application Area",
                "canonical_name": "application_area",
                "marker": "compulsory",
                "data_type": "dropdown",
                "primitive": "dropdown_static",
                "help_text": "Where it is applied.",
                "is_advanced": False,
                "enum_resolver": "static",
                "enum_values": ["under-eye", "eyelid", "full-face"],
                # Rich at-rest inline map — this is what ``fetch_schema_dto``'s
                # ``_map_field_to_dto`` reads to DERIVE ``enum_resolver="static"``
                # + the flat ``enum_values``. Validation now reads the FLAT DTO
                # (catalog-422-fix), so a static enum MUST carry ``enum_codes_map``
                # here or the DTO mapper reclassifies it as ``"category"``.
                "enum_codes_map": {
                    "under-eye": "UNDER_EYE",
                    "eyelid": "EYELID",
                    "full-face": "FULL_FACE",
                },
                "validation_message_ids": [],
            },
            {
                "name": "Description",
                "canonical_name": "product_description",
                "marker": "optional",
                "data_type": "text",
                "primitive": "text_long",
                "help_text": "Long description.",
                "is_advanced": False,
                "enum_resolver": None,
                "validation_message_ids": [],
            },
        ],
        "compulsory_count": 3,
        "optional_count": 1,
        "total_count": 4,
        "wizard_step_count": 1,
        "main_sheet_label": "Eye-Serum",
        "compliance_shape": "collapsed",
        "super_id": "19",
        "path": "Beauty > Skin Care > Eye-Serum",
    }


@pytest_asyncio.fixture(loop_scope="function")
async def beauty_template(db) -> TemplateORM:
    """Insert a template carrying the Eye-Serum schema envelope."""
    schema = _build_eye_serum_schema()
    template = TemplateORM(
        schema_hash="test-eye-serum-hash-0001",
        schema_jsonb={
            "fields": schema["fields"],
            "compulsory_count": schema["compulsory_count"],
            "optional_count": schema["optional_count"],
            "total_count": schema["total_count"],
            "wizard_step_count": schema["wizard_step_count"],
            "main_sheet_label": schema["main_sheet_label"],
        },
        compliance_shape="collapsed",
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@pytest_asyncio.fixture(loop_scope="function")
async def beauty_category(db, beauty_template) -> CategoryORM:
    """Insert a Beauty / Eye-Serum category leaf with super_id=19.

    The category is the input to ``catalog.create_product`` step 2 +
    Auto-fill step 3 (schema fetch).
    """
    category = CategoryORM(
        meesho_leaf_id="EYE-SERUM-LEAF",
        super_id="19",
        super_name="Beauty",
        path="Beauty > Skin Care > Eye-Serum",
        leaf_name="Eye-Serum",
        template_id=beauty_template.id,
        commission_pct=Decimal("8.50"),
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@pytest.fixture
def eye_serum_schema() -> dict[str, Any]:
    """Return the schema envelope dict for unit tests that bypass the DB."""
    return _build_eye_serum_schema()


# ─────────────────────────────────────────────────────────────────────────────
# Stub for ai_ops.client.call_gemini
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def stub_call_gemini(monkeypatch):
    """Replace :func:`ai_ops.client.call_gemini` with a deterministic stub.

    The factory accepts a ``parsed`` shape — default is the Auto-fill
    happy-path output with all four Eye-Serum fields populated above the
    0.85 auto-apply floor.

    Usage::

        async def test_x(stub_call_gemini, ...):
            stub_call_gemini(parsed={"fields": {"product_name": "Glow Serum"}})
            # ... run service ...
    """
    from app.ai_ops import client as ai_ops_client
    from app.ai_ops.client import AIResponse
    from app.adapters.gemini import GeminiResponse

    state: dict[str, Any] = {
        "parsed": {
            "fields": {
                "product_name": "Glow Eye Serum",
                "brand_name": "BrightLab",
                "application_area": "under-eye",
                "product_description": "Lightweight peptide eye serum.",
            }
        },
    }
    calls: list[dict[str, Any]] = []

    async def _stub(ctx, prompt_id, prompt_vars=None, *, image_bytes=None,
                    allowed_enums=None, response_mime_type=None,
                    max_output_tokens=None):
        calls.append(
            {
                "workload": ctx.workload,
                "prompt_id": prompt_id,
                "vars_keys": list((prompt_vars or {}).keys()),
                "allowed_enums_keys": list((allowed_enums or {}).keys()),
            }
        )
        return AIResponse(
            parsed=state["parsed"],
            raw_response=GeminiResponse(
                text="", input_tokens=42, output_tokens=42,
                finish_reason="STOP", raw={"stub": True},
            ),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="stub-trace-id",
        )

    monkeypatch.setattr(ai_ops_client, "call_gemini", _stub)

    def configure(*, parsed: dict[str, Any] | None = None) -> dict[str, Any]:
        if parsed is not None:
            state["parsed"] = parsed
        return {"calls": calls, "state": state}

    return configure


@pytest.fixture
def stub_call_gemini_budget_exceeded(monkeypatch):
    """Replace :func:`ai_ops.client.call_gemini` with one that raises
    :class:`BudgetExceededError`.

    Per dispatch acceptance criterion 5 — the
    ``TestAutofillGracefulFallback`` unit covers the path where the
    exception surfaces through (V1.5 behaviour; V1 ``call_gemini``
    normally catches internally).
    """
    from app.ai_ops import client as ai_ops_client
    from app.ai_ops.budget_cap import BudgetExceededError

    async def _raise(*args, **kwargs):
        raise BudgetExceededError(
            detail="Daily AI budget exhausted (test stub)."
        )

    monkeypatch.setattr(ai_ops_client, "call_gemini", _raise)


# ─────────────────────────────────────────────────────────────────────────────
# catalog_route_client — D2-patched ASGI fixture (Gate-4 repair pattern)
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def catalog_route_client():
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


# ─────────────────────────────────────────────────────────────────────────────
# Disable category schema cache for unit tests (single-process Valkey not always live)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _disable_category_cache(monkeypatch):
    """Bypass the §4.D Valkey cache for category.service.fetch_schema.

    The schema-driven validation unit tests do NOT need Valkey live;
    by patching ``get_or_set`` to invoke the factory directly we keep
    the tests hermetic to Postgres alone.

    Patches BOTH the source module attribute AND every consumer module
    that captured ``get_or_set`` by name at import time
    (``from app.core.cache import get_or_set``).
    """
    import app.core.cache as cache_mod

    async def _passthrough_get_or_set(key, factory, *, ttl=60, single_flight=False):
        return await factory()

    # Source module.
    monkeypatch.setattr(cache_mod, "get_or_set", _passthrough_get_or_set)

    # Consumers that bound the name at import time.
    for mod_path in (
        "app.modules.category.service",
        "app.modules.customer.service",
    ):
        try:
            mod = __import__(mod_path, fromlist=["get_or_set"])
        except Exception:
            continue
        if hasattr(mod, "get_or_set"):
            monkeypatch.setattr(mod, "get_or_set", _passthrough_get_or_set)
