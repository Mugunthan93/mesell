"""Shared pytest fixtures: ephemeral DB, in-memory Valkey, FastAPI test client."""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Force dev mode + isolated test schema before importing app modules.
os.environ.setdefault("APP_ENV", "development")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://meesell:password@localhost:5432/meesell",
)
os.environ.setdefault("VALKEY_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app import models as _models  # noqa: F401,E402 — registers tables on Base.metadata
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
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
async def auth_client(client):
    phone = "+919876543210"
    await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    resp = await client.post("/api/v1/auth/verify-otp", json={"phone": phone, "otp": "1234"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    client.test_user_id = resp.json()["user"]["id"]
    return client
