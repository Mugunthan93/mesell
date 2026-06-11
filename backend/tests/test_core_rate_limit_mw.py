"""Tests for ``app.core.middleware.rate_limit_mw`` — per-IP + per-route + fail-open."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import register_error_handlers
from app.core.middleware.rate_limit_mw import (
    RateLimitMiddleware,
    rate_limit,
)
from app.core.middleware.request_id import RequestIdMiddleware

pytestmark = pytest.mark.integration


def _make_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/cheap")
    async def cheap() -> dict:
        return {"ok": True}

    @app.get("/expensive")
    @rate_limit(scope="expensive_op", limit=3, window=60)
    async def expensive() -> dict:
        return {"ok": True}

    # Order: RateLimit must wrap closer to the route than RequestId.
    # Registration here is deepest-first, same as in app.main.
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    return app


@pytest.mark.asyncio
async def test_per_ip_limit_triggers_429(use_live_valkey):
    """Hammer past ``RL_PER_IP_PER_MINUTE`` → 429 envelope.

    We patch ``settings.RL_PER_IP_PER_MINUTE`` to a tiny value so the test
    runs in <1 s.  ``X-Forwarded-For`` carries a per-test unique IP so the
    counter is isolated.
    """
    app = _make_app()
    test_ip = f"10.0.0.{uuid.uuid4().int % 250}"
    # Tiny per-IP cap.
    with patch("app.core.middleware.rate_limit_mw.settings") as mock_settings:
        mock_settings.RL_PER_IP_PER_MINUTE = 3
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            # First 3 must pass.
            for _ in range(3):
                r = await ac.get("/cheap", headers={"X-Forwarded-For": test_ip})
                assert r.status_code == 200
            # 4th must be blocked.
            r = await ac.get("/cheap", headers={"X-Forwarded-For": test_ip})
            assert r.status_code == 429
            body = r.json()
            assert body["code"] == "rate_limit.exceeded"
            assert body["validation_message_id"] == "rate_limit.exceeded"


@pytest.mark.asyncio
async def test_per_route_limit_triggers_429(use_live_valkey):
    """Per-route ``@rate_limit`` decorator caps a single endpoint."""
    app = _make_app()
    test_ip = f"10.0.1.{uuid.uuid4().int % 250}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        # First 3 hits to /expensive pass (limit=3).
        for _ in range(3):
            r = await ac.get("/expensive", headers={"X-Forwarded-For": test_ip})
            assert r.status_code == 200
        # 4th is rejected by the per-route gate.
        r = await ac.get("/expensive", headers={"X-Forwarded-For": test_ip})
        assert r.status_code == 429


@pytest.mark.asyncio
@pytest.mark.unit
async def test_valkey_unreachable_fails_open(caplog):
    """When Valkey raises, the request MUST pass + a WARNING MUST be logged."""
    from redis.exceptions import ConnectionError as RedisConnectionError

    app = _make_app()

    async def _broken_check(*args, **kwargs):
        raise RedisConnectionError("simulated outage")

    with patch(
        "app.core.middleware.rate_limit_mw._check_window",
        side_effect=_broken_check,
    ):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            with caplog.at_level("WARNING", logger="app.core.middleware.rate_limit_mw"):
                r = await ac.get("/cheap")
            # Fail-open: 200, not 429.
            assert r.status_code == 200
            # WARNING logged for the per-IP path.
            warnings = [
                rec for rec in caplog.records
                if rec.levelname == "WARNING" and "failing OPEN" in rec.message
            ]
            assert warnings, "expected a fail-open WARNING in logs"
