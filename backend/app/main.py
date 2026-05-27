"""MeeSell API — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"MeeSell API starting (env={settings.APP_ENV})")
    yield
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


@app.get("/health")
async def health():
    """Health check endpoint."""
    # TODO: Add PostgreSQL and Valkey connectivity checks (T01)
    return {"status": "healthy", "env": settings.APP_ENV}
