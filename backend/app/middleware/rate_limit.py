"""Valkey-backed sliding-window rate limiter.

Keys::
    ratelimit:{user_id}:{bucket}:{window_seconds}

Each window holds a sorted set of request timestamps; expired entries are
trimmed on every check. Returns ``True`` if the request is within budget.
"""

import logging
import time
import uuid
from dataclasses import dataclass

import redis.asyncio as redis
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


@dataclass
class Limit:
    bucket: str
    per_minute: int | None = None
    per_day: int | None = None


# Per-endpoint budgets (extend as routers grow).
LIMITS: dict[str, Limit] = {
    "generate": Limit("generate", per_minute=5, per_day=50),
    "images": Limit("images", per_minute=20, per_day=200),
    "pricing": Limit("pricing", per_minute=30, per_day=500),
    "scrape": Limit("scrape", per_minute=3, per_day=30),
}


def _key(user_id: uuid.UUID | str, bucket: str, window: int) -> str:
    return f"ratelimit:{user_id}:{bucket}:{window}"


async def _check_window(
    valkey: redis.Redis, user_id: uuid.UUID | str, bucket: str, window: int, limit: int
) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds)."""
    now = time.time()
    key = _key(user_id, bucket, window)
    cutoff = now - window
    async with valkey.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        pipe.zadd(key, {f"{now}:{int(now * 1000) % 1_000_000}": now})
        pipe.expire(key, window)
        _, count, _, _ = await pipe.execute()
    if count >= limit:
        # Find earliest member to compute retry-after.
        oldest = await valkey.zrange(key, 0, 0, withscores=True)
        retry = window - int(now - oldest[0][1]) if oldest else window
        return False, max(retry, 1)
    return True, 0


async def enforce(valkey: redis.Redis, user_id: uuid.UUID | str, bucket: str) -> None:
    """Raise ``HTTPException(429)`` if the request would exceed ``LIMITS[bucket]``."""
    limit = LIMITS.get(bucket)
    if limit is None:
        return

    retry_after = 0
    if limit.per_minute:
        ok, retry = await _check_window(valkey, user_id, bucket, 60, limit.per_minute)
        retry_after = max(retry_after, retry) if not ok else retry_after
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {bucket} (per-minute)",
                headers={"Retry-After": str(retry_after)},
            )
    if limit.per_day:
        ok, retry = await _check_window(valkey, user_id, bucket, 86400, limit.per_day)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily quota exhausted for {bucket}",
                headers={"Retry-After": str(retry)},
            )
