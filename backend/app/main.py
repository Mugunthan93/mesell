"""MeeSell API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.routers import auth as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"MeeSell API starting (env={settings.APP_ENV})")
    app.state.db_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    app.state.valkey = redis.from_url(settings.VALKEY_URL, decode_responses=True)
    yield
    await app.state.valkey.aclose()
    await app.state.db_engine.dispose()
    logger.info("MeeSell API shutting down")


app = FastAPI(
    title="MeeSell API",
    description="AI-powered operating system for Meesho suppliers",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)

if settings.is_dev:
    import os

    from fastapi.staticfiles import StaticFiles

    os.makedirs("/tmp/meesell", exist_ok=True)
    app.mount("/dev-static", StaticFiles(directory="/tmp/meesell"), name="dev-static")


async def _check_postgres() -> str:
    try:
        async with app.state.db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        logger.warning(f"Postgres health check failed: {exc}")
        return "error"


async def _check_valkey() -> str:
    try:
        pong = await app.state.valkey.ping()
        return "ok" if pong else "error"
    except Exception as exc:
        logger.warning(f"Valkey health check failed: {exc}")
        return "error"


@app.get("/health")
async def health():
    """Health check endpoint with PostgreSQL and Valkey connectivity."""
    checks = {"postgres": await _check_postgres(), "valkey": await _check_valkey()}
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
